# Testni zapisnik

Svaki provedeni test = jedan redak (ne brisati stare – povijest pokazuje napredak).
**Okruženje:** SIM = simulatori na laptopu, HW = maketa, CI = GitHub Actions.

| datum | ID | okruženje | rezultat | mjerenje / bilješka | izveo |
|---|---|---|---|---|---|
| 2026-10-21 | sve automatske | SIM (Python 3.13) | ✅ prolaz | `pytest` iz korijena: **143 passed** (ugovor, baza, detektor, OCR, odluke, access control, bridge, simulator rampe, e2e) | Claude (priprema) |
| 2026-10-21 | TC-C01 | SIM | ✅ | demo scenarij (`simulacija.py`): 0 poruka koje krše ugovor | Claude |
| 2026-10-21 | TC-C02 | SIM | ✅ | 15 primjera = 15 shema | Claude |
| 2026-10-21 | TC-S03 | SIM (g++ + Unity) | ✅ 8/8 | filtar senzora; na PC-u preveden g++-om (PlatformIO registar nije bio dostupan) – ponoviti s `pio test -e native` | Claude |
| 2026-10-21 | TC-R00 | SIM (g++ + Unity, pytest) | ✅ 7/7 + 6/6 | stroj stanja rampe C++ i Python | Claude |
| 2026-10-21 | firmware build | Docker (PlatformIO, ESP32 Arduino core 2.0.6) | ✅ | senzori: RAM 13,8 %, flash 59,1 %; rampe: RAM 14,3 %, flash 60,8 %; **nije još isproban na pločici** | Claude |
| 2026-10-21 | TC-A02 | SIM (sintetski skup) | ✅ | kontrolirani 100 % (150/150), teški 95,3 % (143/150), 0 lažno pozitivnih; **stvarne fotografije tek treba snimiti** | Claude |
| 2026-10-21 | TC-A03 | SIM (x86 laptop) | ✅ | detekcija ~35 ms; detekcija + OCR ~0,7 s po slici (izmjeriti na Raspberry Pi) | Claude |
| 2026-10-21 | TC-O01 / TC-O02 | SIM (sintetski skup) | ✅ | kontrolirani: 91,3 % točno, 68 % prihvaćeno iz prve slike, **0 pogrešno prihvaćenih**; teški: 78,7 % / 39,3 % / 0 | Claude |
| 2026-10-21 | TC-O03 | SIM | ✅ | provjereno na svim kombinacijama statusa, pouzdanosti (0–1, korak 0,01), pokušaja, mjesta | Claude |
| 2026-10-21 | TC-B01 – TC-B08 | SIM | ✅ | 30 testova baze i naplate | Claude |
| 2026-10-21 | TC-I01 | SIM | ✅ | ulaz (pouzdanost 0,98) → P03 → izlaz; sesija `CLOSED` s mjestom, trajanjem i cijenom (demo naplata) | Claude |
| 2026-10-21 | TC-I03, TC-I16 | SIM | ✅ | nečitljiva pločica: 3 pokušaja → `MANUAL_REQUIRED`, rampa zatvorena; ručno odobrenje → `MANUAL_APPROVAL` | Claude |
| 2026-10-21 | TC-I05 | SIM | ✅ | `KA4321ZZ` na izlazu → `DENIED NO_ACTIVE_SESSION` | Claude |
| 2026-10-21 | TC-I07 | SIM | ✅ | kvar senzora P04 → `unknownSpots` 1, ne broji se kao slobodno | Claude |
| 2026-10-21 | TC-I08 / TC-T07 | SIM + ThingsBoard 4.2.1 | ✅ | TB zaustavljen, 12 zapisa u međuspremniku, nakon pokretanja međuspremnik prazan, promjene P06 spremljene s izvornim vremenom | Claude |
| 2026-10-21 | TC-I17 | SIM | ✅ | bez potvrde: ponovljeno s istim `requestId`, zatim alarm `GATE_NO_ACK` | Claude |
| 2026-10-21 | TC-T03 | SIM + ThingsBoard | ✅ djelomično | stvoreni/ugašeni: "ALPR uzastopno ne uspijeva", "Potrebna ručna intervencija", "Uređaj nije dostupan"; ostale izazvati na maketi | Claude |
| 2026-10-21 | TC-T04 | SIM + ThingsBoard | ✅ | RPC `open` na EntranceGate → rampa `OPENING → OPEN`; `approveExit` → `MANUAL_APPROVAL`, sesija zatvorena (pozvano preko REST API-ja, gumb u UI-ju još kliknuti) | Claude |
| 2026-10-21 | TC-T06 | SIM + ThingsBoard | ✅ | nakon restarta kontejnera: dashboardi postoje, 183 točke povijesti `entry` postoje | Claude |
| | TC-S01, S02, S04–S06 | HW | ⬜ | | osoba 3 |
| | TC-R01 – R13 | HW | ⬜ | | osoba 4 |
| | TC-A01, A02 (stvarni skup) | HW | ⬜ | | osoba 5 |
| | TC-O01, O02 (stvarni skup) | HW | ⬜ | | osoba 6 |
| | TC-I01 – I16 na maketi | HW | ⬜ | | osoba 8 + svi |
| | TC-T01, T05 | HW | ⬜ | | osoba 7 |
| | TC-P01 | – | ⬜ | | osoba 8 |
