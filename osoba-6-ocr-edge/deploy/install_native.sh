#!/usr/bin/env bash
# Native install on the edge computer (Raspberry Pi OS Bookworm / Ubuntu 20.04+ / Jetson with Python >= 3.8).
#   git clone <repo> ~/IoTGarage && cd ~/IoTGarage && bash osoba-6-ocr-edge/deploy/install_native.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$(pwd)
PY=${PYTHON:-python3}

sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients tesseract-ocr python3-venv
sudo cp osoba-1-voditelj/integracija/mosquitto.conf /etc/mosquitto/conf.d/garage.conf
sudo sed -i 's#/mosquitto/data/#/var/lib/mosquitto/#' /etc/mosquitto/conf.d/garage.conf
sudo systemctl restart mosquitto

$PY -m venv .venv
.venv/bin/pip install --upgrade pip
OPENCV_EXTRA="[headless]"
if $PY -c "import cv2" 2>/dev/null; then OPENCV_EXTRA=""; echo "using the system OpenCV"; fi
.venv/bin/pip install -e osoba-1-voditelj/contract -e "osoba-5-alpr${OPENCV_EXTRA}" -e osoba-8-baza-testovi/sessions \
    -e osoba-6-ocr-edge -e osoba-7-thingsboard/bridge
mkdir -p runtime
[ -f osoba-6-ocr-edge/edge.yaml ] || cp osoba-6-ocr-edge/edge.example.yaml osoba-6-ocr-edge/edge.yaml

echo
echo "Installed. Next steps:"
echo "  1. edit osoba-6-ocr-edge/edge.yaml (camera, thresholds) and the TB_HOST in the .service files"
echo "  2. test:  .venv/bin/python -m edge_service --config osoba-6-ocr-edge/edge.yaml all"
echo "  3. autostart: sudo cp osoba-6-ocr-edge/deploy/*.service /etc/systemd/system/ && \\"
echo "     sudo systemctl daemon-reload && sudo systemctl enable --now garage-edge garage-tb-bridge"
