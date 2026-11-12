#!/usr/bin/env bash
# Native install of the ALPR service (Raspberry Pi OS Bookworm / Ubuntu 20.04+ / Jetson with Python >= 3.8).
#   git clone <repo> ~/IoTGarage && cd ~/IoTGarage && bash SOFTWARE/edge/deploy/install_native.sh
# Varijanta B (default) needs no Mosquitto; VARIJANTA=a also installs Mosquitto for the old edge setup.
set -euo pipefail
cd "$(dirname "$0")/../.."   # the SOFTWARE directory
ROOT=$(pwd)
PY=${PYTHON:-python3}

sudo apt-get update
sudo apt-get install -y tesseract-ocr python3-venv
if [ "${VARIJANTA:-b}" = "a" ]; then
    sudo apt-get install -y mosquitto mosquitto-clients
    sudo cp integracija/mosquitto.conf /etc/mosquitto/conf.d/garage.conf
    sudo sed -i 's#/mosquitto/data/#/var/lib/mosquitto/#' /etc/mosquitto/conf.d/garage.conf
    sudo systemctl restart mosquitto
fi

$PY -m venv .venv
.venv/bin/pip install --upgrade pip
OPENCV_EXTRA="[headless]"
if $PY -c "import cv2" 2>/dev/null; then OPENCV_EXTRA=""; echo "using the system OpenCV"; fi
.venv/bin/pip install -e ugovor -e "alpr${OPENCV_EXTRA}" -e baza \
    -e edge -e thingsboard/bridge
mkdir -p runtime
[ -f edge/edge.yaml ] || cp edge/edge.example.yaml edge/edge.yaml

echo
echo "Installed in $ROOT (.venv, runtime). Next steps, from that directory:"
echo "  1. edit edge/edge.yaml: camera, and in the section thingsboard the host and the token of alpr-service"
echo "  2. test:  .venv/bin/python -m edge_service --config edge/edge.yaml tb-alpr"
echo "  3. autostart: sudo cp edge/deploy/garage-alpr.service /etc/systemd/system/ && \\"
echo "     sudo systemctl daemon-reload && sudo systemctl enable --now garage-alpr"
echo "  (varijanta A: edge_service all + garage-edge.service and garage-tb-bridge.service)"
