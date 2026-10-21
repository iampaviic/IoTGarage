# 7. Zaključak i buduća poboljšanja

## 7.1 Što radi
_(šest kriterija uspjeha iz plana – za svaki dokaz: test, mjerenje, slika)_

## 7.2 Poznata ograničenja
- OCR je podešen za naš font pločica (predlošci); druge pločice → niža pouzdanost, više ručnih intervencija
- jedna kamera premješta se između ulaza i izlaza (varijanta B)
- HC-SR04 osjetljiv na kut i jeke; mjesto bez kalibracije može griješiti
- _(dopuniti rezultatima s makete)_

## 7.3 Buduća poboljšanja
- neuronski detektor pločica (YOLO) na Jetson Nano GPU-u, druga kamera
- online plaćanje / rezervacija mjesta, mobilno prilagođen dashboard
- PostgreSQL i sinkronizacija sesija u oblak, više garaža
- TLS na MQTT-u, autentikacija uređaja certifikatima
