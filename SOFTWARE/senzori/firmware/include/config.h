// Pin map, thresholds and timing of the parking spot sensor node.
// Keep the pin table in sync with PROJEKT/maketa/shema-spajanja.md
#pragma once
#include <stdint.h>

#define FW_VERSION "0.1.0"
#define DEVICE_ID  "esp32-spots"

// ---------------------------------------------------------------- spots
// HC-SR04 mounted ABOVE each spot looking down: empty spot = distance to the
// floor (~14 cm), parked car = distance to the roof (~6-7 cm).
// ECHO is 5 V -> use a voltage divider (1 kOhm / 2 kOhm) to 3.3 V!
// GPIO 34-39 are input-only, perfect for ECHO.
#define SPOT_COUNT 6

struct SpotPins {
    const char* id;
    uint8_t trigPin;
    uint8_t echoPin;
    float occupiedBelowCm;   // filtered distance below this -> OCCUPIED
    float freeAboveCm;       // filtered distance above this -> FREE (between = hysteresis, keep state)
};

// Calibrate with tools/kalibracija.py and copy the proposed thresholds here.
static const SpotPins SPOTS[SPOT_COUNT] = {
    {"P01", 23, 36, 10.0f, 12.0f},
    {"P02", 22, 39, 10.0f, 12.0f},
    {"P03", 21, 34, 10.0f, 12.0f},
    {"P04", 19, 35, 10.0f, 12.0f},
    {"P05", 18, 32, 10.0f, 12.0f},
    {"P06",  5, 33, 10.0f, 12.0f},
};

// ---------------------------------------------------------------- filter
#define FILTER_CONFIRM_COUNT   3      // same new state 3 times in a row before switching
#define FILTER_MAX_INVALID     5      // this many failed readings in a row -> UNKNOWN
#define SENSOR_MIN_CM          2.0f   // HC-SR04 blind zone
#define SENSOR_MAX_CM          60.0f  // anything farther is impossible on the model
#define ECHO_TIMEOUT_US        6000   // ~1 m round trip; keeps one reading short

// ---------------------------------------------------------------- timing
#define SENSOR_GAP_MS          60     // pause between two sensors (no ultrasonic cross-talk)
#define HEARTBEAT_MS           30000  // republish all spots + heartbeat
#define RECONNECT_MS           5000

// ---------------------------------------------------------------- LEDs (optional)
// One WS2812B LED per spot on a single data pin: green free, red occupied, blue unknown.
#define USE_LED_STRIP          1
#define LED_STRIP_PIN          25
#define LED_BRIGHTNESS         40     // 0-255, keep low: the 5 V supply is shared with the sensors
