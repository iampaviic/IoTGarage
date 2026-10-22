----------------------------------------------------------------
Projekt: IoT Garaza, ak. god. 2026/27
Puni naziv projekta:   Pametna parkirna garaza s automatskim prepoznavanjem
                       registarskih oznaka (ALPR), lokalnim (edge) upravljanjem
                       ulaskom i izlaskom te digitalnim blizancem u platformi
                       ThingsBoard
Datum prezentacije:  <upisati datum prezentacije>

Sadrzaj repozitorija:
- PROJEKT/       pisani dio projekta: prijedlog i plan projekta (DOCX + PDF),
                 zavrsna dokumentacija po poglavljima, arhitektura sustava,
                 komunikacijski ugovor (MQTT), zahtjevi, rizici, odluke,
                 plan rada i integracije, nacrt makete i elektronike,
                 testni plan i zapisnik, slike.
                 Opis: PROJEKT/README.TXT
- SOFTWARE/      sav izvorni kod: firmware za dva ESP32 cvora (PlatformIO),
                 edge servis (ALPR, OCR, lokalna kontrola pristupa), baza
                 parkirnih sesija, ThingsBoard (Docker, provisioning, bridge,
                 dashboardi), simulacija cijelog sustava i automatski testovi,
                 3D dijelovi i sheme ozicenja makete, mobilna aplikacija.
                 Opis: SOFTWARE/README.TXT
                 Instalacija: SOFTWARE/INSTALL.TXT
- PREZENTACIJA/  zavrsna prezentacija i scenarij demonstracije.
                 Opis: PREZENTACIJA/README.TXT
- OSTALO/        literatura i poveznice, upute nastavnika.
                 Opis: OSTALO/README.TXT
- README.md      isti pregled s poveznicama i brzim startom (prikazuje se
                 na naslovnoj stranici repozitorija)

Svaka mapa ima README.TXT s opisom sto je sto; podmape u SOFTWARE/ imaju
i README.md s detaljnim uputama za taj dio sustava.

Tim: Patrik (voditelj), Anja, Toma Burgund, Luka Oslic, Sven Matic,
     Lukas Davorija, Leo Hreljanovic, Lovro Gale
----------------------------------------------------------------
