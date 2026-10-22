// Copy this file to secrets.h (secrets.h is git-ignored) and fill in your values.
#pragma once

#define WIFI_SSID     "IoTGarage"
#define WIFI_PASSWORD "change-me"

// MQTT broker = the edge computer (Raspberry Pi / Jetson Nano) running Mosquitto
#define MQTT_HOST     "192.168.1.10"
#define MQTT_PORT     1883
#define MQTT_USER     ""          // empty = anonymous
#define MQTT_PASSWORD ""

// time source for ISO 8601 timestamps; the edge computer can run an NTP server (chrony)
#define NTP_SERVER    "pool.ntp.org"
