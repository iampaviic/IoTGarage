"""Edge service of the IoT Garage (owner: osoba 6).

- alpr_service:   camera -> plate detection (osoba 5) -> OCR -> garage/alpr/<gate>/event
- access_control: local entry/exit decisions, gate commands, parking sessions
Runs on the Raspberry Pi / Jetson Nano and keeps working without ThingsBoard.
"""
