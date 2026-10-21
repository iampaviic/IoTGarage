// Entrance + exit barrier node (ESP32, 2x SG90 servo, 2x IR sensor) - osoba 4
//
// Subscribes  garage/gate/<entrance|exit>/command   {"requestId","command":"OPEN|CLOSE|RESET",...}
// Publishes   garage/gate/<gate>/state (retained)  on every change, as command ack, every 30 s
// The state machine (lib/GateLogic) runs locally: auto close, safety reverse, buttons and LEDs
// keep working when Wi-Fi, MQTT or the edge computer are down.
//
// Serial commands: "open e|x", "close e|x", "reset e|x", "status"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <time.h>

#include "GateController.h"
#include "config.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#warning "include/secrets.h missing - copy include/secrets.example.h; building with example values"
#include "secrets.example.h"
#endif

struct GateRuntime {
    GateController ctrl;
    Servo servo;
    float angle;
    bool irStable, irRaw;
    uint32_t irChangedMs;
    bool btnStable, btnRaw;
    uint32_t btnChangedMs, btnPressedMs;
    bool btnLongDone;
};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
GateRuntime gates[2];
uint32_t lastLoopMs = 0, lastPeriodicMs = 0, lastHeartbeatMs = 0, lastWifiTryMs = 0, lastMqttTryMs = 0;
uint32_t beepUntil = 0;
char statusTopic[64];

bool timeValid() { return time(nullptr) > 1600000000; }

void putTimestamp(JsonDocument& doc) {
    if (!timeValid()) {
        doc["timestamp"] = nullptr;
        return;
    }
    char ts[24];
    time_t now = time(nullptr);
    struct tm t;
    gmtime_r(&now, &t);
    strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%SZ", &t);
    doc["timestamp"] = ts;
}

void publishState(uint8_t i, const GateEvent* ev, const char* source) {
    GateRuntime& g = gates[i];
    Serial.printf("[%s] %s present=%d %s %s\n", GATES[i].name, GateController::stateName(ev ? ev->state : g.ctrl.state()),
                  ev ? ev->vehiclePresent : g.ctrl.vehiclePresent(), ev && ev->requestId[0] ? ev->requestId : "",
                  ev && ev->reason ? ev->reason : "");
    if (!mqtt.connected()) return;
    JsonDocument doc;
    doc["gate"] = GATES[i].payloadName;
    doc["state"] = GateController::stateName(ev ? ev->state : g.ctrl.state());
    doc["vehiclePresent"] = ev ? ev->vehiclePresent : g.ctrl.vehiclePresent();
    if (ev && ev->requestId[0]) doc["requestId"] = ev->requestId;
    else doc["requestId"] = nullptr;
    doc["success"] = ev ? ev->success : true;
    if (ev && ev->reason) doc["reason"] = ev->reason;
    else doc["reason"] = nullptr;
    doc["source"] = ev ? ev->source : source;
    doc["deviceId"] = DEVICE_ID;
    putTimestamp(doc);
    char topic[48], buf[320];
    snprintf(topic, sizeof topic, "garage/gate/%s/state", GATES[i].name);
    size_t n = serializeJson(doc, buf, sizeof buf);
    mqtt.publish(topic, (const uint8_t*)buf, n, true);
}

void publishHeartbeat() {
    if (!mqtt.connected()) return;
    JsonDocument doc;
    doc["deviceId"] = DEVICE_ID;
    doc["deviceType"] = "GATE_CONTROLLER";
    doc["uptimeS"] = millis() / 1000;
    doc["fwVersion"] = FW_VERSION;
    doc["rssi"] = WiFi.RSSI();
    doc["freeHeap"] = ESP.getFreeHeap();
    doc["ip"] = WiFi.localIP().toString();
    putTimestamp(doc);
    char buf[256];
    size_t n = serializeJson(doc, buf, sizeof buf);
    mqtt.publish("garage/system/heartbeat", (const uint8_t*)buf, n, false);
}

void onMessage(char* topic, byte* payload, unsigned int len) {
    JsonDocument doc;
    if (deserializeJson(doc, payload, len)) {
        Serial.println("ignoring invalid JSON command");
        return;
    }
    for (uint8_t i = 0; i < 2; i++) {
        char t[48];
        snprintf(t, sizeof t, "garage/gate/%s/command", GATES[i].name);
        if (strcmp(topic, t) == 0)
            gates[i].ctrl.command(doc["command"] | "", doc["requestId"] | "", "MQTT", millis());
    }
}

void ensureConnections() {
    uint32_t now = millis();
    if (WiFi.status() != WL_CONNECTED) {
        if (now - lastWifiTryMs > RECONNECT_MS) {
            lastWifiTryMs = now;
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
        return;
    }
    if (mqtt.connected() || now - lastMqttTryMs < RECONNECT_MS) return;
    lastMqttTryMs = now;
    const char* will = "{\"deviceId\":\"" DEVICE_ID "\",\"online\":false}";
    bool ok = strlen(MQTT_USER) ? mqtt.connect(DEVICE_ID, MQTT_USER, MQTT_PASSWORD, statusTopic, 1, true, will)
                                : mqtt.connect(DEVICE_ID, statusTopic, 1, true, will);
    if (!ok) {
        Serial.printf("MQTT: failed rc=%d\n", mqtt.state());
        return;
    }
    Serial.println("MQTT: connected");
    mqtt.publish(statusTopic, "{\"deviceId\":\"" DEVICE_ID "\",\"online\":true}", true);
    mqtt.subscribe("garage/gate/entrance/command", 1);
    mqtt.subscribe("garage/gate/exit/command", 1);
    for (uint8_t i = 0; i < 2; i++) publishState(i, nullptr, "BOOT");
    publishHeartbeat();
}

void readInputs(uint8_t i, uint32_t now) {
    GateRuntime& g = gates[i];
    bool ir = digitalRead(GATES[i].irPin) == (IR_ACTIVE_LOW ? LOW : HIGH);
    if (ir != g.irRaw) {
        g.irRaw = ir;
        g.irChangedMs = now;
    } else if (ir != g.irStable && now - g.irChangedMs >= IR_DEBOUNCE_MS) {
        g.irStable = ir;
        g.ctrl.setVehicle(ir, now);
    }
    bool pressed = digitalRead(GATES[i].buttonPin) == LOW;
    if (pressed != g.btnRaw) {
        g.btnRaw = pressed;
        g.btnChangedMs = now;
    } else if (pressed != g.btnStable && now - g.btnChangedMs >= BUTTON_DEBOUNCE_MS) {
        g.btnStable = pressed;
        if (pressed) {
            g.btnPressedMs = now;
            g.btnLongDone = false;
            g.ctrl.button(now);
        }
    }
    if (g.btnStable && !g.btnLongDone && now - g.btnPressedMs >= BUTTON_RESET_MS) {
        g.btnLongDone = true;
        g.ctrl.resetButton(now);
    }
}

void driveOutputs(uint8_t i, uint32_t now, uint32_t dtMs) {
    GateRuntime& g = gates[i];
    float target = g.ctrl.targetOpen() ? GATES[i].openAngle : GATES[i].closedAngle;
    if (g.ctrl.state() != GateState::Error) {
        float step = SERVO_DEG_PER_S * dtMs / 1000.0f;
        if (fabsf(target - g.angle) <= step) g.angle = target;
        else g.angle += target > g.angle ? step : -step;
        g.servo.write((int)roundf(g.angle));
    }
    GateState s = g.ctrl.state();
    bool blink = (now / 250) % 2;
    digitalWrite(GATES[i].ledGreenPin, s == GateState::Open || (s == GateState::Opening && blink));
    digitalWrite(GATES[i].ledRedPin, s == GateState::Closed || s == GateState::Closing ||
                                         (s == GateState::Error && blink) || (s == GateState::Opening && !blink));
}

void handleSerial() {
    static char line[24];
    static uint8_t pos = 0;
    while (Serial.available()) {
        char c = Serial.read();
        if (c != '\n' && c != '\r') {
            if (pos < sizeof line - 1) line[pos++] = c;
            continue;
        }
        line[pos] = 0;
        pos = 0;
        char cmd[8] = "", which = 0;
        if (sscanf(line, "%7s %c", cmd, &which) >= 1) {
            if (!strcmp(cmd, "status")) {
                for (uint8_t i = 0; i < 2; i++)
                    Serial.printf("%s %s present=%d angle=%.0f\n", GATES[i].name,
                                  GateController::stateName(gates[i].ctrl.state()), gates[i].ctrl.vehiclePresent(),
                                  gates[i].angle);
                continue;
            }
            uint8_t i = which == 'x' ? 1 : 0;
            char rid[24];
            snprintf(rid, sizeof rid, "serial-%lu", (unsigned long)millis());
            for (char* p = cmd; *p; p++) *p = toupper(*p);
            gates[i].ctrl.command(cmd, rid, "SERIAL", millis());
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.printf("\nIoT Garage gates %s\n", FW_VERSION);
    snprintf(statusTopic, sizeof statusTopic, "garage/system/status/%s", DEVICE_ID);
    GateTiming t;
    t.moveMs = GATE_MOVE_MS;
    t.closeAfterPassMs = CLOSE_AFTER_PASS_MS;
    t.autoCloseMs = AUTO_CLOSE_MS;
    t.maxReversals = MAX_REVERSALS;
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    for (uint8_t i = 0; i < 2; i++) {
        GateRuntime& g = gates[i];
        g.ctrl = GateController(t);
        pinMode(GATES[i].irPin, INPUT);  // GPIO 34/35 have no pull-up: FC-51 drives the line itself
        pinMode(GATES[i].buttonPin, INPUT_PULLUP);
        pinMode(GATES[i].ledRedPin, OUTPUT);
        pinMode(GATES[i].ledGreenPin, OUTPUT);
        g.servo.setPeriodHertz(50);
        g.servo.attach(GATES[i].servoPin, 500, 2400);
        g.angle = GATES[i].closedAngle;
        g.servo.write(GATES[i].closedAngle);
        g.irRaw = g.irStable = false;
        g.btnRaw = g.btnStable = false;
        g.irChangedMs = g.btnChangedMs = g.btnPressedMs = 0;
        g.btnLongDone = true;
    }
    if (BUZZER_PIN) pinMode(BUZZER_PIN, OUTPUT);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    lastWifiTryMs = millis();
    configTime(0, 0, NTP_SERVER);
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setBufferSize(512);
    mqtt.setKeepAlive(30);
    mqtt.setCallback(onMessage);
    lastLoopMs = millis();
}

void loop() {
    ensureConnections();
    mqtt.loop();
    handleSerial();
    uint32_t now = millis();
    uint32_t dt = now - lastLoopMs;
    lastLoopMs = now;
    for (uint8_t i = 0; i < 2; i++) {
        readInputs(i, now);
        gates[i].ctrl.tick(now);
        GateEvent ev;
        while (gates[i].ctrl.popEvent(ev)) {
            publishState(i, &ev, ev.source);
            if (ev.state == GateState::Closing && BUZZER_PIN) beepUntil = now + 150;
        }
        driveOutputs(i, now, dt);
    }
    if (BUZZER_PIN) digitalWrite(BUZZER_PIN, now < beepUntil);
    if (now - lastPeriodicMs >= PERIODIC_STATE_MS) {
        lastPeriodicMs = now;
        for (uint8_t i = 0; i < 2; i++) publishState(i, nullptr, "PERIODIC");
    }
    if (now - lastHeartbeatMs >= 30000) {
        lastHeartbeatMs = now;
        publishHeartbeat();
    }
    delay(5);
}
