// Entrance + exit barrier node (ESP32, 2x SG90 servo, 2x IR sensor), owner: Luka. Varijanta B: ThingsBoard.
//
// The node is the gateway device "esp32-gates" in ThingsBoard (MQTT user name = access token) and
// speaks for the devices EntranceGate and ExitGate through the ThingsBoard Gateway MQTT API:
//   v1/gateway/telemetry  {"EntranceGate":[{state, stateCode, vehiclePresent, lastSource}]}
//                         on every change and every 30 s;
//                         + vehicleArrived:true when a vehicle reaches a CLOSED gate (the rule chain
//                         then asks ALPR to read the plate and decides)
//   v1/gateway/rpc        in:  {"device":"EntranceGate","data":{"id":7,"method":"open|close|reset|deny"}}
//                         out: {"device":"EntranceGate","id":7,"data":{"success":true,"state":"OPENING"}}
//   v1/devices/me/telemetry  heartbeat {uptimeS, rssi, freeHeap}; attributes {fwVersion, ip} after connecting
// The state machine (lib/GateLogic) runs locally: auto close, safety reverse, buttons and LEDs
// keep working when Wi-Fi or ThingsBoard are down.
//
// Serial commands: "open e|x", "close e|x", "reset e|x", "status"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <PubSubClient.h>
#include <WiFi.h>

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
    bool arrived;            // vehicle reached the closed gate -> vehicleArrived for the rule chain
    long rpcId;              // RPC waiting for the answer of the state machine (-1 = none)
    char rpcRequestId[24];
};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
GateRuntime gates[2];
uint32_t lastLoopMs = 0, lastPeriodicMs = 0, lastWifiTryMs = 0, lastMqttTryMs = 0;
uint32_t beepUntil = 0;

int stateCode(GateState s) { return (int)s; }  // 0 CLOSED, 1 OPENING, 2 OPEN, 3 CLOSING, 4 ERROR

bool publishJson(const char* topic, JsonDocument& doc) {
    if (!mqtt.connected()) return false;
    char buf[384];
    size_t n = serializeJson(doc, buf, sizeof buf);
    return mqtt.publish(topic, (const uint8_t*)buf, n, false);
}

void publishState(uint8_t i, const GateEvent* ev, const char* source, bool arrived = false) {
    GateRuntime& g = gates[i];
    GateState s = ev ? ev->state : g.ctrl.state();
    bool present = ev ? ev->vehiclePresent : g.ctrl.vehiclePresent();
    Serial.printf("[%s] %s present=%d %s %s%s\n", GATES[i].name, GateController::stateName(s), present,
                  ev && ev->requestId[0] ? ev->requestId : "", ev && ev->reason ? ev->reason : "",
                  arrived ? " vehicleArrived" : "");
    JsonDocument doc;
    JsonObject v = doc[GATES[i].device].add<JsonObject>();  // no ts -> ThingsBoard uses the time of receipt
    v["state"] = GateController::stateName(s);
    v["stateCode"] = stateCode(s);
    v["vehiclePresent"] = present;
    v["lastSource"] = ev ? ev->source : source;
    if (ev && ev->requestId[0]) {
        v["lastCommandSuccess"] = ev->success;
        if (ev->reason) v["lastCommandReason"] = ev->reason;
    }
    if (arrived) v["vehicleArrived"] = true;
    publishJson("v1/gateway/telemetry", doc);
}

void answerRpc(uint8_t i, long id, bool success, const char* state, const char* reason) {
    JsonDocument doc;
    doc["device"] = GATES[i].device;
    doc["id"] = id;
    doc["data"]["success"] = success;
    doc["data"]["state"] = state;
    if (reason) doc["data"]["reason"] = reason;
    else doc["data"]["reason"] = nullptr;
    publishJson("v1/gateway/rpc", doc);
}

void publishHeartbeat() {
    JsonDocument doc;
    doc["uptimeS"] = millis() / 1000;
    doc["rssi"] = WiFi.RSSI();
    doc["freeHeap"] = ESP.getFreeHeap();
    publishJson("v1/devices/me/telemetry", doc);
}

// RPC from the rule chain / dashboard to EntranceGate or ExitGate
void onMessage(char* topic, byte* payload, unsigned int len) {
    if (strcmp(topic, "v1/gateway/rpc") != 0) return;
    JsonDocument doc;
    if (deserializeJson(doc, payload, len)) {
        Serial.println("ignoring invalid RPC JSON");
        return;
    }
    const char* device = doc["device"] | "";
    long id = doc["data"]["id"] | -1L;
    const char* method = doc["data"]["method"] | "";
    for (uint8_t i = 0; i < 2; i++) {
        if (strcmp(device, GATES[i].device) != 0) continue;
        GateRuntime& g = gates[i];
        if (!strcmp(method, "deny")) {  // operator or rule chain refused the vehicle: short beep, stay closed
            beepUntil = millis() + 400;
            answerRpc(i, id, true, GateController::stateName(g.ctrl.state()), nullptr);
            return;
        }
        char cmd[8];
        if (!strcmp(method, "open")) strcpy(cmd, "OPEN");
        else if (!strcmp(method, "close")) strcpy(cmd, "CLOSE");
        else if (!strcmp(method, "reset")) strcpy(cmd, "RESET");
        else {
            answerRpc(i, id, false, GateController::stateName(g.ctrl.state()), "INVALID_COMMAND");
            return;
        }
        // the state machine answers with an event carrying this requestId; loop() sends it back as the RPC answer
        g.rpcId = id;
        snprintf(g.rpcRequestId, sizeof g.rpcRequestId, "rpc-%ld", id);
        g.ctrl.command(cmd, g.rpcRequestId, "RPC", millis());
    }
}

void onConnected() {
    for (uint8_t i = 0; i < 2; i++) {  // ThingsBoard links EntranceGate / ExitGate to this gateway
        JsonDocument doc;
        doc["device"] = GATES[i].device;
        doc["type"] = "Gate";
        publishJson("v1/gateway/connect", doc);
    }
    mqtt.subscribe("v1/gateway/rpc", 1);
    JsonDocument attrs;
    attrs["fwVersion"] = FW_VERSION;
    attrs["ip"] = WiFi.localIP().toString();
    attrs["deviceType"] = "GATE_CONTROLLER";
    publishJson("v1/devices/me/attributes", attrs);
    for (uint8_t i = 0; i < 2; i++) publishState(i, nullptr, "BOOT");
    publishHeartbeat();
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
    if (!mqtt.connect(DEVICE_ID, TB_TOKEN, nullptr)) {
        // rc 4/5 = wrong access token (check TB_TOKEN and the device esp32-gates in ThingsBoard)
        Serial.printf("ThingsBoard: failed rc=%d\n", mqtt.state());
        return;
    }
    Serial.println("ThingsBoard: connected");
    onConnected();
}

void readInputs(uint8_t i, uint32_t now) {
    GateRuntime& g = gates[i];
    bool ir = digitalRead(GATES[i].irPin) == (IR_ACTIVE_LOW ? LOW : HIGH);
    if (ir != g.irRaw) {
        g.irRaw = ir;
        g.irChangedMs = now;
    } else if (ir != g.irStable && now - g.irChangedMs >= IR_DEBOUNCE_MS) {
        g.irStable = ir;
        if (ir && g.ctrl.state() == GateState::Closed) g.arrived = true;
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
                Serial.printf("WiFi=%d ThingsBoard=%d\n", WiFi.status() == WL_CONNECTED, mqtt.connected());
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
        g.arrived = false;
        g.rpcId = -1;
        g.rpcRequestId[0] = 0;
    }
    if (BUZZER_PIN) pinMode(BUZZER_PIN, OUTPUT);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    lastWifiTryMs = millis();
    mqtt.setServer(TB_HOST, TB_PORT);
    mqtt.setBufferSize(512);
    mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
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
        GateRuntime& g = gates[i];
        readInputs(i, now);
        g.ctrl.tick(now);
        GateEvent ev;
        while (g.ctrl.popEvent(ev)) {
            publishState(i, &ev, ev.source);
            if (g.rpcId >= 0 && !strcmp(ev.requestId, g.rpcRequestId)) {
                answerRpc(i, g.rpcId, ev.success, GateController::stateName(ev.state), ev.reason);
                g.rpcId = -1;
            }
            if (ev.state == GateState::Closing && BUZZER_PIN) beepUntil = now + 150;
        }
        if (g.arrived) {
            g.arrived = false;
            publishState(i, nullptr, "SENSOR", true);
        }
        driveOutputs(i, now, dt);
    }
    if (BUZZER_PIN) digitalWrite(BUZZER_PIN, now < beepUntil);
    if (now - lastPeriodicMs >= PERIODIC_STATE_MS) {
        lastPeriodicMs = now;
        for (uint8_t i = 0; i < 2; i++) publishState(i, nullptr, "PERIODIC");
        publishHeartbeat();
    }
    delay(5);
}
