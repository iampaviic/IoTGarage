# Simulator rampi

- `gate_sim.py` – Python verzija stroja stanja iz `firmware/lib/GateLogic` (ista pravila, isti testovi)
- `gate_simulator_tb.py` – obje rampe kao gateway `esp32-gates` u ThingsBoardu (varijanta B), vozilo s tipkovnice
- `gate_simulator.py` – varijanta A: obje rampe na Mosquittu, prisutnost vozila s tipkovnice ili `garage/sim/gate/<gate>/presence`
- `test_gate_sim.py` – `pytest rampe/simulator` (iz mape SOFTWARE)
