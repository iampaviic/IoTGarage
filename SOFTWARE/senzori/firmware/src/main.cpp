// Parking spot sensor node (ESP32 + up to 6 HC-SR04), owner: Toma. Varijanta B: talks to ThingsBoard directly.
//
// The node is the gateway device "esp32-spots" in ThingsBoard (MQTT user name = access token) and
// speaks for the devices ParkingSpot-01..06 through the ThingsBoard Gateway MQTT API:
//   v1/gateway/connect          {"device":"ParkingSpot-03","type":"ParkingSpot"}       after every (re)connect
//   v1/gateway/telemetry        {"ParkingSpot-03":[{state, stateCode, occupied, distanceCm, sensorStatus}]}
//                               when a spot changes, every 30 s and after every reconnect
//   v1/devices/me/telemetry     {freeSpots, occupiedSpots, unknownSpots, totalSpots} with every change,
//                               + heartbeat {uptimeS, rssi, freeHeap} every 30 s
//   v1/devices/me/attributes    {fwVersion, ip, deviceType, spotCount} after every (re)connect
//   v1/devices/me/rpc/request/+ sim {"spot":"P03","occupied":true|false|null}, simOff, status
// Timestamps come from ThingsBoard (time of receipt). When the node disappears, ThingsBoard
// notices the closed connection and its rule chain marks the spots UNKNOWN / OFFLINE.
// Never blocks: Wi-Fi and MQTT reconnect in the background while the sensors and LEDs keep running.
//
// Serial commands (115200 baud):
//   status            print all spots
//   cal               toggle calibration output "CAL,<spot>,<raw cm>" (for tools/kalibracija.py)
//   sim <n> <0|1|x>   force spot n free / occupied / broken (simulation mode)
//   sim off           back to real sensors
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "OccupancyFilter.h"
#include "config.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#warning "include/secrets.h missing - copy include/secrets.example.h; building with example values"
#include "secrets.example.h"
#endif
#if USE_LED_STRIP
#include <Adafruit_NeoPixel.h>
Adafruit_NeoPixel strip(SPOT_COUNT, LED_STRIP_PIN, NEO_GRB + NEO_KHZ800);
#endif

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

OccupancyFilter filters[SPOT_COUNT];
float lastRawCm[SPOT_COUNT];
int8_t simOverride[SPOT_COUNT];  // -1 = real sensor, 0 free, 1 occupied, 2 broken
bool calibration = false;

uint8_t nextSensor = 0;
uint32_t lastSensorMs = 0, lastHeartbeatMs = 0, lastWifiTryMs = 0, lastMqttTryMs = 0;

// ------------------------------------------------------------------ helpers
float readDistanceCm(const SpotPins& s) {
    digitalWrite(s.trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(s.trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(s.trigPin, LOW);
    unsigned long us = pulseIn(s.echoPin, HIGH, ECHO_TIMEOUT_US);
    if (us == 0) return 0.0f;  // no echo
    return us * 0.0343f / 2.0f;
}

void showLed(uint8_t i) {
#if USE_LED_STRIP
    uint32_t c;
    switch (filters[i].state()) {
        case SpotState::Free: c = strip.Color(0, 255, 0); break;
        case SpotState::Occupied: c = strip.Color(255, 0, 0); break;
        default: c = strip.Color(0, 0, 255); break;
    }
    strip.setPixelColor(i, c);
    strip.show();
#endif
}

void spotDevice(uint8_t i, char* out, size_t len) {  // "P03" -> "ParkingSpot-03"
    snprintf(out, len, "%s%s", SPOT_DEVICE_PREFIX, SPOTS[i].id + 1);
}

bool publishJson(const char* topic, JsonDocument& doc) {
    if (!mqtt.connected()) return false;
    char buf[384];
    size_t n = serializeJson(doc, buf, sizeof buf);
    return mqtt.publish(topic, (const uint8_t*)buf, n, false);
}

// ------------------------------------------------------------------ ThingsBoard
void publishSpot(uint8_t i) {
    JsonDocument doc;
    char device[24];
    spotDevice(i, device, sizeof device);
    JsonObject v = doc[device].add<JsonObject>();  // {"ParkingSpot-03":[{...}]}, no ts -> server time
    const OccupancyFilter& f = filters[i];
    v["state"] = f.stateName();
    v["stateCode"] = f.state() == SpotState::Free ? 0 : (f.state() == SpotState::Occupied ? 1 : -1);
    if (f.state() != SpotState::Unknown) v["occupied"] = f.state() == SpotState::Occupied;
    if (f.filteredCm() >= 0) v["distanceCm"] = roundf(f.filteredCm() * 10) / 10;
    // simulated broken sensor (mode 2) reports the real fault status so alarms can be tested
    v["sensorStatus"] = (simOverride[i] == 0 || simOverride[i] == 1) ? "SIMULATED" : f.statusName();
    publishJson("v1/gateway/telemetry", doc);
}

void addCounts(JsonDocument& doc) {
    uint8_t free = 0, occupied = 0;
    for (uint8_t i = 0; i < SPOT_COUNT; i++) {
        if (filters[i].state() == SpotState::Free) free++;
        else if (filters[i].state() == SpotState::Occupied) occupied++;
    }
    doc["freeSpots"] = free;          // the rule chain copies these to the Garage asset
    doc["occupiedSpots"] = occupied;
    doc["unknownSpots"] = SPOT_COUNT - free - occupied;
    doc["totalSpots"] = SPOT_COUNT;
}

void publishCounts() {
    JsonDocument doc;
    addCounts(doc);
    publishJson("v1/devices/me/telemetry", doc);
}

void publishHeartbeat() {
    JsonDocument doc;
    addCounts(doc);
    doc["uptimeS"] = millis() / 1000;
    doc["rssi"] = WiFi.RSSI();
    doc["freeHeap"] = ESP.getFreeHeap();
    publishJson("v1/devices/me/telemetry", doc);
}

void publishAll() {
    for (uint8_t i = 0; i < SPOT_COUNT; i++) publishSpot(i);
    publishHeartbeat();
}

void spotChanged(uint8_t i) {
    publishSpot(i);
    publishCounts();
    showLed(i);
}

void applySim(uint8_t i, int8_t mode) {
    simOverride[i] = mode;
    filters[i].reset();
    float d = mode == 1 ? 6.5f : (mode == 0 ? 14.0f : 0.0f);
    for (int k = 0; k < 10; k++) filters[i].update(d);
    spotChanged(i);
}

void simOff() {
    for (uint8_t i = 0; i < SPOT_COUNT; i++) {
        simOverride[i] = -1;
        filters[i].reset();  // UNKNOWN until the real sensor confirms a state
        spotChanged(i);
    }
}

// RPC to esp32-spots (dashboard, simulation): v1/devices/me/rpc/request/<id>
void onMessage(char* topic, byte* payload, unsigned int len) {
    const char* prefix = "v1/devices/me/rpc/request/";
    if (strncmp(topic, prefix, strlen(prefix)) != 0) return;
    char responseTopic[64];
    snprintf(responseTopic, sizeof responseTopic, "v1/devices/me/rpc/response/%s", topic + strlen(prefix));
    JsonDocument req, res;
    if (deserializeJson(req, payload, len)) return;
    const char* method = req["method"] | "";
    res["success"] = true;
    if (!strcmp(method, "sim")) {  // {"spot":"P03","occupied":true|false|null}
        const char* id = req["params"]["spot"] | "";
        JsonVariant v = req["params"]["occupied"];
        bool found = false;
        for (uint8_t i = 0; i < SPOT_COUNT; i++) {
            if (!strcmp(id, SPOTS[i].id)) {
                applySim(i, v.isNull() ? 2 : (v.as<bool>() ? 1 : 0));
                found = true;
            }
        }
        if (!found) {
            res["success"] = false;
            res["reason"] = "UNKNOWN_SPOT";
        }
    } else if (!strcmp(method, "simOff")) {
        simOff();
    } else if (!strcmp(method, "status")) {
        for (uint8_t i = 0; i < SPOT_COUNT; i++) res[SPOTS[i].id] = filters[i].stateName();
    } else {
        res["success"] = false;
        res["reason"] = "UNSUPPORTED";
    }
    publishJson(responseTopic, res);
}

void onConnected() {
    // announce the spots: ThingsBoard links ParkingSpot-01..06 to this gateway (creates them if missing)
    for (uint8_t i = 0; i < SPOT_COUNT; i++) {
        JsonDocument doc;
        char device[24];
        spotDevice(i, device, sizeof device);
        doc["device"] = device;
        doc["type"] = "ParkingSpot";
        publishJson("v1/gateway/connect", doc);
    }
    mqtt.subscribe("v1/devices/me/rpc/request/+", 1);
    JsonDocument attrs;
    attrs["fwVersion"] = FW_VERSION;
    attrs["ip"] = WiFi.localIP().toString();
    attrs["deviceType"] = "SPOT_SENSORS";
    attrs["spotCount"] = SPOT_COUNT;
    publishJson("v1/devices/me/attributes", attrs);
    publishAll();  // states after (re)connect
}

void ensureConnections() {
    uint32_t now = millis();
    if (WiFi.status() != WL_CONNECTED) {
        if (now - lastWifiTryMs > RECONNECT_MS) {
            lastWifiTryMs = now;
            Serial.println("WiFi: connecting...");
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
        return;
    }
    if (mqtt.connected() || now - lastMqttTryMs < RECONNECT_MS) return;
    lastMqttTryMs = now;
    Serial.printf("ThingsBoard: connecting to %s:%d\n", TB_HOST, TB_PORT);
    if (!mqtt.connect(DEVICE_ID, TB_TOKEN, nullptr)) {
        // rc 4/5 = wrong access token (check TB_TOKEN and the device esp32-spots in ThingsBoard)
        Serial.printf("ThingsBoard: failed, rc=%d\n", mqtt.state());
        return;
    }
    Serial.println("ThingsBoard: connected");
    onConnected();
}

// ------------------------------------------------------------------ serial
void handleSerial() {
    static char line[48];
    static uint8_t pos = 0;
    while (Serial.available()) {
        char c = Serial.read();
        if (c != '\n' && c != '\r') {
            if (pos < sizeof line - 1) line[pos++] = c;
            continue;
        }
        line[pos] = 0;
        pos = 0;
        if (!strcmp(line, "status")) {
            for (uint8_t i = 0; i < SPOT_COUNT; i++)
                Serial.printf("%s %-8s filtered=%.1f raw=%.1f status=%s%s\n", SPOTS[i].id, filters[i].stateName(),
                              filters[i].filteredCm(), lastRawCm[i], filters[i].statusName(),
                              simOverride[i] >= 0 ? " (SIM)" : "");
            Serial.printf("WiFi=%d ThingsBoard=%d\n", WiFi.status() == WL_CONNECTED, mqtt.connected());
        } else if (!strcmp(line, "cal")) {
            calibration = !calibration;
            Serial.printf("calibration output %s\n", calibration ? "ON" : "OFF");
        } else if (!strcmp(line, "sim off")) {
            simOff();
            Serial.println("simulation off");
        } else if (!strncmp(line, "sim ", 4)) {
            int n = atoi(line + 4);
            const char* v = strrchr(line, ' ') + 1;
            if (n >= 1 && n <= SPOT_COUNT) applySim(n - 1, *v == 'x' ? 2 : (*v == '1' ? 1 : 0));
        } else if (line[0]) {
            Serial.println("commands: status | cal | sim <n> <0|1|x> | sim off");
        }
    }
}

// ------------------------------------------------------------------ setup / loop
void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.printf("\nIoT Garage spot sensors %s, %d spots\n", FW_VERSION, SPOT_COUNT);
    for (uint8_t i = 0; i < SPOT_COUNT; i++) {
        pinMode(SPOTS[i].trigPin, OUTPUT);
        digitalWrite(SPOTS[i].trigPin, LOW);
        pinMode(SPOTS[i].echoPin, INPUT);
        FilterConfig c;
        c.occupiedBelowCm = SPOTS[i].occupiedBelowCm;
        c.freeAboveCm = SPOTS[i].freeAboveCm;
        c.confirmCount = FILTER_CONFIRM_COUNT;
        c.maxInvalid = FILTER_MAX_INVALID;
        c.minValidCm = SENSOR_MIN_CM;
        c.maxValidCm = SENSOR_MAX_CM;
        filters[i] = OccupancyFilter(c);
        simOverride[i] = -1;
        lastRawCm[i] = 0;
    }
#if USE_LED_STRIP
    strip.begin();
    strip.setBrightness(LED_BRIGHTNESS);
    for (uint8_t i = 0; i < SPOT_COUNT; i++) showLed(i);
#endif
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    lastWifiTryMs = millis();
    mqtt.setServer(TB_HOST, TB_PORT);
    mqtt.setBufferSize(512);
    mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
    mqtt.setCallback(onMessage);
}

void loop() {
    ensureConnections();
    mqtt.loop();
    handleSerial();

    uint32_t now = millis();
    if (now - lastSensorMs >= SENSOR_GAP_MS) {  // one sensor per slot -> no cross-talk
        lastSensorMs = now;
        uint8_t i = nextSensor;
        nextSensor = (nextSensor + 1) % SPOT_COUNT;
        if (simOverride[i] < 0) {
            float d = readDistanceCm(SPOTS[i]);
            lastRawCm[i] = d;
            if (calibration) Serial.printf("CAL,%s,%.1f\n", SPOTS[i].id, d);
            if (filters[i].update(d)) {
                Serial.printf("%s -> %s (%.1f cm, %s)\n", SPOTS[i].id, filters[i].stateName(),
                              filters[i].filteredCm(), filters[i].statusName());
                spotChanged(i);
            }
        }
    }
    if (now - lastHeartbeatMs >= HEARTBEAT_MS) {
        lastHeartbeatMs = now;
        publishAll();
    }
}
