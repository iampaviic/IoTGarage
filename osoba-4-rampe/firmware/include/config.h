// Pin map and timing of the barrier node. Keep in sync with
// osoba-2-maketa/elektronika/shema-spajanja.md
#pragma once
#include <stdint.h>

#define FW_VERSION "0.1.0"
#define DEVICE_ID  "esp32-gates"

struct GatePins {
    const char* name;        // topic name: "entrance" / "exit"
    const char* payloadName; // payload name: "ENTRANCE" / "EXIT"
    uint8_t servoPin;        // SG90 signal (servo powered from the 5 V supply, NOT from the ESP32)
    uint8_t irPin;           // FC-51 IR obstacle sensor at the barrier line (LOW = vehicle)
    uint8_t ledRedPin;
    uint8_t ledGreenPin;
    uint8_t buttonPin;       // manual open button to GND (INPUT_PULLUP); hold 3 s = RESET
    uint8_t closedAngle;     // calibrate: barrier horizontal
    uint8_t openAngle;       // calibrate: barrier vertical
};

static const GatePins GATES[2] = {
    {"entrance", "ENTRANCE", 13, 34, 25, 26, 18, 0, 90},
    {"exit",     "EXIT",     14, 35, 27, 33, 19, 0, 90},
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
#define PERIODIC_STATE_MS    30000
#define RECONNECT_MS         5000
