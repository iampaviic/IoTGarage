// Parking spot sensor node (ESP32 + up to 6 HC-SR04) - osoba 3
//
// Publishes garage/parking/spot/<id>/telemetry (retained) when a spot changes,
// every 30 s and after every reconnect; heartbeat on garage/system/heartbeat;
// Last Will "offline" on garage/system/status/esp32-spots.
// Never blocks: Wi-Fi and MQTT reconnect in the background while the sensors keep running.
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
#include <time.h>

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
bool simulation = false;
bool calibration = false;

uint8_t nextSensor = 0;
uint32_t lastSensorMs = 0, lastHeartbeatMs = 0, lastWifiTryMs = 0, lastMqttTryMs = 0;
char statusTopic[64];

// ------------------------------------------------------------------ helpers
bool timeValid() { return time(nullptr) > 1600000000; }

void isoNow(char* out, size_t len) {
    time_t now = time(nullptr);
    struct tm t;
    gmtime_r(&now, &t);
    strftime(out, len, "%Y-%m-%dT%H:%M:%SZ", &t);
}

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

// ------------------------------------------------------------------ MQTT
void publishSpot(uint8_t i) {
    if (!mqtt.connected()) return;
    JsonDocument doc;
    const OccupancyFilter& f = filters[i];
    doc["spotId"] = SPOTS[i].id;
    doc["state"] = f.stateName();
    if (f.state() == SpotState::Unknown) doc["occupied"] = nullptr;
    else doc["occupied"] = f.state() == SpotState::Occupied;
    if (f.filteredCm() >= 0) doc["distanceCm"] = roundf(f.filteredCm() * 10) / 10;
    else doc["distanceCm"] = nullptr;
    // simulated broken sensor (mode 2) reports the real fault status so alarms can be tested
    doc["sensorStatus"] = (simOverride[i] == 0 || simOverride[i] == 1) ? "SIMULATED" : f.statusName();
    doc["deviceId"] = DEVICE_ID;
    doc["uptimeMs"] = millis();
    if (timeValid()) {
        char ts[24];
        isoNow(ts, sizeof ts);
        doc["timestamp"] = ts;
    } else {
        doc["timestamp"] = nullptr;  // edge uses the receive time
    }
    char topic[64], buf[256];
    snprintf(topic, sizeof topic, "garage/parking/spot/%s/telemetry", SPOTS[i].id);
    size_t n = serializeJson(doc, buf, sizeof buf);
    mqtt.publish(topic, (const uint8_t*)buf, n, true);
}

void publishHeartbeat() {
    if (!mqtt.connected()) return;
    JsonDocument doc;
    doc["deviceId"] = DEVICE_ID;
    doc["deviceType"] = "SPOT_SENSORS";
    doc["uptimeS"] = millis() / 1000;
    doc["fwVersion"] = FW_VERSION;
    doc["rssi"] = WiFi.RSSI();
    doc["freeHeap"] = ESP.getFreeHeap();
    doc["ip"] = WiFi.localIP().toString();
    if (timeValid()) {
        char ts[24];
        isoNow(ts, sizeof ts);
        doc["timestamp"] = ts;
    } else {
        doc["timestamp"] = nullptr;
    }
    char buf[256];
    size_t n = serializeJson(doc, buf, sizeof buf);
    mqtt.publish("garage/system/heartbeat", (const uint8_t*)buf, n, false);
}

void applySim(uint8_t i, int8_t mode) {
    simOverride[i] = mode;
    filters[i].reset();
    float d = mode == 1 ? 6.5f : (mode == 0 ? 14.0f : 0.0f);
    for (int k = 0; k < 10; k++) filters[i].update(d);
    publishSpot(i);
    showLed(i);
}

void onMessage(char* topic, byte* payload, unsigned int len) {
    // simulation hook: garage/sim/spot/P03 {"occupied": true|false|null}
    JsonDocument doc;
    if (deserializeJson(doc, payload, len)) return;
    const char* id = strrchr(topic, '/') + 1;
    for (uint8_t i = 0; i < SPOT_COUNT; i++) {
        if (strcmp(id, SPOTS[i].id) == 0) {
            JsonVariant v = doc["occupied"];
            applySim(i, v.isNull() ? 2 : (v.as<bool>() ? 1 : 0));
        }
    }
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
    Serial.printf("MQTT: connecting to %s:%d\n", MQTT_HOST, MQTT_PORT);
    const char* will = "{\"deviceId\":\"" DEVICE_ID "\",\"online\":false}";
    bool ok = strlen(MQTT_USER) ? mqtt.connect(DEVICE_ID, MQTT_USER, MQTT_PASSWORD, statusTopic, 1, true, will)
                                : mqtt.connect(DEVICE_ID, statusTopic, 1, true, will);
    if (!ok) {
        Serial.printf("MQTT: failed, rc=%d\n", mqtt.state());
        return;
    }
    Serial.println("MQTT: connected");
    mqtt.publish(statusTopic, "{\"deviceId\":\"" DEVICE_ID "\",\"online\":true}", true);
    mqtt.subscribe("garage/sim/spot/+", 1);
    for (uint8_t i = 0; i < SPOT_COUNT; i++) publishSpot(i);  // states after reconnect
    publishHeartbeat();
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
            Serial.printf("WiFi=%d MQTT=%d time=%d\n", WiFi.status() == WL_CONNECTED, mqtt.connected(), timeValid());
        } else if (!strcmp(line, "cal")) {
            calibration = !calibration;
            Serial.printf("calibration output %s\n", calibration ? "ON" : "OFF");
        } else if (!strcmp(line, "sim off")) {
            for (uint8_t i = 0; i < SPOT_COUNT; i++) { simOverride[i] = -1; filters[i].reset(); }
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
    snprintf(statusTopic, sizeof statusTopic, "garage/system/status/%s", DEVICE_ID);
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
    configTime(0, 0, NTP_SERVER);  // UTC
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setBufferSize(512);
    mqtt.setKeepAlive(30);
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
                publishSpot(i);
                showLed(i);
            }
        }
    }
    if (now - lastHeartbeatMs >= HEARTBEAT_MS) {
        lastHeartbeatMs = now;
        for (uint8_t i = 0; i < SPOT_COUNT; i++) publishSpot(i);
        publishHeartbeat();
    }
}
