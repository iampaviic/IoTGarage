# Sigurnosni testovi rampi

Provesti za **obje** rampe, rezultat upisati ovdje i u [testni zapisnik](../osoba-8-baza-testovi/testni-zapisnik.md).
Logika je već pokrivena unit testovima (`firmware/test`, `simulator/test_gate_sim.py`); ovdje se provjerava
stvarni hardver (servo, IR senzor, montaža).

| ID | test | koraci | očekivano | ulaz | izlaz |
|---|---|---|---|---|---|
| TC-R01 | otvaranje na naredbu | `open` preko MQTT-a | `OPENING` s istim `requestId` < 1 s, zatim `OPEN`; zelena LED | | |
| TC-R02 | zatvaranje na naredbu | `close`, ništa ispod rampe | `CLOSING` → `CLOSED`, crvena LED | | |
| TC-R03 | automatsko zatvaranje | otvori, provezi autić | 2 s nakon što IR oslobodi → zatvaranje | | |
| TC-R04 | ne zatvara na vozilo | otvori, autić ostavi ispod rampe 30 s | ostaje `OPEN`; `close` → `VEHICLE_PRESENT` | | |
| TC-R05 | sigurnosno ponovno otvaranje | dok se zatvara, gurni autić pod rampu | odmah `OPENING` (`source: SAFETY`) | | |
| TC-R06 | ručna tipka | kratko pritisni tipku | otvara se i bez Wi-Fi-ja | | |
| TC-R07 | ERROR i reset | 3× zaredom prekini zatvaranje | `ERROR`, rampa gore, LED trepće; tipka 3 s → reset | | |
| TC-R08 | dvostruka naredba | pošalji isti `requestId` dvaput | drugi put `DUPLICATE`, nema dvostrukog pomaka | | |
| TC-R09 | nevaljana naredba | `{"requestId":"x","command":"FLY"}` | `success:false`, `INVALID_COMMAND`, rampa miruje | | |
| TC-R10 | ispad MQTT-a | zaustavi Mosquitto, pritisni tipku, provezi autić | otvaranje/zatvaranje lokalno radi; nakon povratka broker dobiva stanje | | |
| TC-R11 | ispad edge-a | edge ugašen, autić dođe | rampa ostaje zatvorena (nema odluke), tipka radi | | |
| TC-R12 | restart ESP32 | reset tipka na ESP32 | rampa se zatvori/ostane zatvorena, `online:true`, `source: BOOT` < 10 s | | |
| TC-R13 | struja servo | oba servo istovremeno | ESP32 se ne resetira (napajanje odvojeno, kondenzator) | | |
