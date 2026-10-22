# Edge image: ALPR + access control + ThingsBoard bridge (multi-arch: amd64, arm64 = Raspberry Pi 4/5, Jetson Nano).
# Build from the SOFTWARE directory:
#   docker build -f edge/deploy/Dockerfile -t iot-garage-edge .
FROM python:3.11-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ugovor /app/contract
COPY alpr /app/alpr
COPY baza /app/sessions
COPY edge /app/edge
COPY thingsboard/bridge /app/bridge

RUN pip install --no-cache-dir /app/contract "/app/alpr[headless]" /app/sessions /app/edge /app/bridge

ENV PYTHONUNBUFFERED=1 GARAGE_DB=/data/garage.db TB_BUFFER=/data/tb-buffer.db
VOLUME ["/data"]
WORKDIR /data
CMD ["python", "-m", "edge_service", "--config", "/app/edge/edge.example.yaml", "all"]
