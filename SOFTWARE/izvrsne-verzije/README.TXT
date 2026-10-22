IZVRSNE VERZIJE
===============
Popunjava se na kraju projekta, kad je rad gotov.

firmware-senzori.bin   pio run -d ../senzori/firmware, zatim kopirati
                       senzori/firmware/.pio/build/esp32dev/firmware.bin
firmware-rampe.bin     isto za ../rampe/firmware
iot-garage-edge.tar    Docker slika edge racunala:
                       docker build -f edge/deploy/Dockerfile -t iot-garage-edge .
                       (iz mape SOFTWARE), zatim
                       docker save iot-garage-edge -o izvrsne-verzije/iot-garage-edge.tar
                       (ako je prevelika za repozitorij, navesti gdje je spremljena)
mobilna aplikacija     APK (Android) ili uputa za instalaciju, kad bude gotova

Upload .bin datoteke na ESP32 bez PlatformIO-a:
    esptool.py --chip esp32 write_flash 0x10000 firmware-senzori.bin
(bootloader i particije vec postoje na ESP32 koji je jednom flashan
PlatformIO-om)
