"""Raspored: koji dio repozitorija ulazi u GitLab u kojem tjednu.

Svaka datoteka pripada tjednu najduljeg prefiksa koji joj odgovara. Nova datoteka koja ne odgovara nijednom
pravilu se prijavi kao "nije raspoređena" – dodaj pravilo ovdje.
"""

import datetime

POCETAK = datetime.date(2026, 10, 19)   # ponedjeljak 1. tjedna
ROK = datetime.date(2027, 1, 29)        # rok za predaju projekta (petak 15. tjedna)

# tjedan: (faza, naslov commita)
TJEDNI = {
    1: ("Faza 1 – definicija i dokaz izvedivosti", "Tjedan 1: plan projekta, arhitektura i MQTT ugovor"),
    2: ("Faza 1 – definicija i dokaz izvedivosti", "Tjedan 2: nacrt makete, popis komponenti i 3D dijelovi"),
    3: ("Faza 2 – samostalni podsustavi", "Tjedan 3: firmware senzora mjesta i rampi"),
    4: ("Faza 2 – samostalni podsustavi", "Tjedan 4: baza parkirnih sesija i ThingsBoard"),
    5: ("Faza 2 – samostalni podsustavi", "Tjedan 5: ALPR – detekcija registarske pločice"),
    6: ("Faza 2 – samostalni podsustavi", "Tjedan 6: OCR i lokalna kontrola pristupa (edge servis)"),
    7: ("Faza 2 – samostalni podsustavi", "Tjedan 7: mobilna aplikacija i dashboardi s pravim podacima"),
    8: ("Faza 3 – integracija", "Tjedan 8: integracija cijelog sustava"),
    9: ("Faza 3 – integracija", "Tjedan 9: postavljanje na edge računalo i upute za instalaciju"),
    10: ("Blagdanska stanka (rezerva)", "Tjedan 10: rad tijekom blagdana"),
    11: ("Blagdanska stanka (rezerva)", "Tjedan 11: rad tijekom blagdana"),
    12: ("Faza 4 – stabilizacija i testiranje", "Tjedan 12: testiranje na maketi"),
    13: ("Faza 4 – stabilizacija i testiranje", "Tjedan 13: rezultati mjerenja ALPR-a i OCR-a"),
    14: ("Faza 5 – dokumentacija, prezentacija i predaja", "Tjedan 14: završna dokumentacija"),
    15: ("Faza 5 – dokumentacija, prezentacija i predaja", "Tjedan 15: prezentacija, izvršne verzije i predaja"),
}

# (prefiks putanje, tjedan); prefiks koji završava s "/" je mapa. Tjedni 10 i 11 (blagdani) nemaju novih dijelova.
PRAVILA = [
    # tjedan 1 – ideja, plan, arhitektura, komunikacijski ugovor
    (".gitignore", 1),
    ("README.md", 1),
    ("OSTALO/", 1),
    ("PROJEKT/README.md", 1),
    ("PROJEKT/plan-projekta/", 1),
    ("PROJEKT/sustav/", 1),
    ("PROJEKT/upravljanje/", 1),
    ("SOFTWARE/README.md", 1),
    ("SOFTWARE/requirements-dev.txt", 1),
    ("SOFTWARE/pytest.ini", 1),
    ("SOFTWARE/ugovor/", 1),
    # tjedan 2 – maketa: nacrt, komponente, 3D dijelovi, ožičenje
    ("PROJEKT/maketa/", 2),
    ("SOFTWARE/maketa/", 2),
    # tjedan 3 – firmware senzora i rampi
    ("SOFTWARE/senzori/", 3),
    ("SOFTWARE/rampe/", 3),
    # tjedan 4 – baza sesija i ThingsBoard
    ("SOFTWARE/baza/", 4),
    ("PROJEKT/sustav/model-podataka.md", 4),
    ("SOFTWARE/thingsboard/", 4),
    ("PROJEKT/sustav/entiteti-i-alarmi.md", 4),
    # tjedan 5 – ALPR
    ("SOFTWARE/alpr/", 5),
    # tjedan 6 – OCR i edge servis
    ("SOFTWARE/edge/", 6),
    # tjedan 7 – mobilna aplikacija, dashboardi s pravim podacima
    ("SOFTWARE/mobilna-aplikacija/", 7),
    ("PROJEKT/slike/", 7),
    # tjedan 8 – integracija
    ("SOFTWARE/integracija/", 8),
    ("PROJEKT/upravljanje/plan-integracije.md", 8),
    ("PROJEKT/testiranje/testni-plan.md", 8),
    # tjedan 9 – postavljanje na edge računalo
    ("SOFTWARE/edge/deploy/", 9),
    ("SOFTWARE/INSTALL.md", 9),
    # tjedan 12 – testiranje na maketi
    ("PROJEKT/testiranje/", 12),
    # tjedan 13 – rezultati mjerenja
    ("SOFTWARE/alpr/rezultati/", 13),
    ("SOFTWARE/edge/rezultati/", 13),
    # tjedan 14 – završna dokumentacija
    ("PROJEKT/dokumentacija/", 14),
    # tjedan 15 – prezentacija, izvršne verzije, predaja
    ("PREZENTACIJA/", 15),
    ("SOFTWARE/izvrsne-verzije/", 15),
]

# nikad u GitLab: alati za GitHub i ovaj alat
IZOSTAVI = [".github/", ".gitlab-tjedni/", "PROJEKT/upravljanje/vodic-za-voditelja.md"]  # vodič opisuje i GitHub

# pregledne datoteke koje se svaki tjedan ponovno sastave tako da opisuju samo ono što već postoji
UPRAVLJANE = [
    "README.md",
    "PROJEKT/README.md",
    "SOFTWARE/README.md",
    "SOFTWARE/requirements-dev.txt",
    "SOFTWARE/pytest.ini",
]
