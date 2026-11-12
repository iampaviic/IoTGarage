// Pin map and timing of the barrier node. Keep in sync with
// PROJEKT/maketa/shema-spajanja.md
#pragma once
#include <stdint.h>

#define FW_VERSION "0.2.0"
#define DEVICE_ID  "esp32-gates"   // gateway device in ThingsBoard, also the MQTT client id

struct GatePins {
    const char* name;        // short name for the serial monitor: "entrance" / "exit"
    const char* device;      // ThingsBoard device: "EntranceGate" / "ExitGate" (profile Gate)
    uint8_t servoPin;        // SG90 signal (servo powered from the 5 V supply, NOT from the ESP32)
    uint8_t irPin;           // FC-51 IR obstacle sensor at the barrier line (LOW = vehicle)
    uint8_t ledRedPin;
    uint8_t ledGreenPin;
    uint8_t buttonPin;       // manual open button to GND (INPUT_PULLUP); hold 3 s = RESET
    uint8_t closedAngle;     // calibrate: arm straight across the lane
    uint8_t openAngle;       // calibrate: arm turned along the island (the printed arm swings horizontally)
};

static const GatePins GATES[2] = {
    {"entrance", "EntranceGate", 13, 34, 25, 26, 18, 0, 90},
    {"exit",     "ExitGate",     14, 35, 27, 33, 19, 0, 90},
};

#define IR_ACTIVE_LOW        1      // FC-51 pulls the output LOW when it sees something
#define IR_DEBOUNCE_MS       80
#define BUTTON_DEBOUNCE_MS   50
#define BUTTON_RESET_MS      3000

#define SERVO_DEG_PER_S      120    // smooth movement, also limits current peaks
#define GATE_MOVE_MS         1000   // time the state machine allows for opening/closing
#define CLOSE_AFTER_PASS_MS  2000
#define AUTO_CLOSE_MS        10000
#define MAX_REVERSALS        3

#define BUZZER_PIN           23     // optional active buzzer, beeps when the barrier closes; 0 = none
#define PERIODIC_STATE_MS    30000  // state of both gates + heartbeat
#define RECONNECT_MS         5000
#define MQTT_KEEPALIVE_S     30     // ThingsBoard closes a silent connection after 1.5x this
