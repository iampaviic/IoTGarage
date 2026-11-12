// Copy this file to secrets.h (secrets.h is git-ignored) and fill in your values.
#pragma once

#define WIFI_SSID     "IoTGarage"
#define WIFI_PASSWORD "change-me"

// ThingsBoard (varijanta B): the laptop or server running ThingsBoard, its MQTT port and the
// access token of the gateway device "esp32-gates" (provision.py prints it; use a secret one for the demo)
#define TB_HOST       "192.168.1.20"
#define TB_PORT       1883
#define TB_TOKEN      "esp32-gates-token"
