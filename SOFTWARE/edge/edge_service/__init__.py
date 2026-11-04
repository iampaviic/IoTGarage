"""Edge service of the IoT Garage (owners: Lukas; decision rules and access control: Luka).

- alpr_service:   camera -> plate detection (plate_detector) -> OCR -> garage/alpr/<gate>/event
- access_control: local entry/exit decisions, gate commands, parking sessions
Runs on the Raspberry Pi / Jetson Nano and keeps working without ThingsBoard.
"""
