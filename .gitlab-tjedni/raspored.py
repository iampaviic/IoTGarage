"""Raspored: koji dio repozitorija ulazi u GitLab u kojem tjednu.

Svaka datoteka pripada tjednu najduljeg prefiksa koji joj odgovara. Nova datoteka koja ne odgovara nijednom
pravilu se prijavi kao "nije raspoređena" – dodaj pravilo ovdje.
"""

# tjedan: (faza, naslov commita)
TJEDNI = {
    1: ("Ideja, plan i arhitektura", "Tjedan 1: plan projekta, arhitektura i MQTT ugovor"),
    2: ("Samostalni podsustavi I", "Tjedan 2: maketa, senzori mjesta, rampe i baza sesija"),
    3: ("Samostalni podsustavi II", "Tjedan 3: ALPR detekcija, OCR i edge servis, ThingsBoard"),
    4: ("Integracija", "Tjedan 4: integracija cijelog sustava i postavljanje na edge računalo"),
    5: ("Stabilizacija i testiranje", "Tjedan 5: testiranje i rezultati mjerenja"),
    6: ("Dokumentacija i prezentacija", "Tjedan 6: završna dokumentacija i prezentacija"),
}

# (prefiks putanje, tjedan); prefiks koji završava s "/" je mapa
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
    # tjedan 2 – maketa, senzori, rampe, baza
    ("PROJEKT/maketa/", 2),
    ("PROJEKT/sustav/model-podataka.md", 2),
    ("SOFTWARE/maketa/", 2),
    ("SOFTWARE/senzori/", 2),
    ("SOFTWARE/rampe/", 2),
    ("SOFTWARE/baza/", 2),
    # tjedan 3 – ALPR, OCR i edge servis, ThingsBoard, početak mobilne aplikacije
    ("SOFTWARE/alpr/", 3),
    ("SOFTWARE/edge/", 3),
    ("SOFTWARE/thingsboard/", 3),
    ("SOFTWARE/mobilna-aplikacija/", 3),
    ("PROJEKT/sustav/entiteti-i-alarmi.md", 3),
    ("PROJEKT/slike/", 3),
    # tjedan 4 – integracija i postavljanje na edge računalo
    ("SOFTWARE/integracija/", 4),
    ("SOFTWARE/edge/deploy/", 4),
    ("SOFTWARE/INSTALL.md", 4),
    ("PROJEKT/upravljanje/plan-integracije.md", 4),
    ("PROJEKT/testiranje/testni-plan.md", 4),
    # tjedan 5 – testiranje i rezultati
    ("PROJEKT/testiranje/", 5),
    ("SOFTWARE/alpr/rezultati/", 5),
    ("SOFTWARE/edge/rezultati/", 5),
    ("SOFTWARE/izvrsne-verzije/", 5),
    # tjedan 6 – dokumentacija i prezentacija
    ("PROJEKT/dokumentacija/", 6),
    ("PREZENTACIJA/", 6),
]

# nikad u GitLab: alati za GitHub i ovaj alat
IZOSTAVI = [".github/", ".gitlab-tjedni/"]

# pregledne datoteke koje se svaki tjedan ponovno sastave tako da opisuju samo ono što već postoji
UPRAVLJANE = [
    "README.md",
    "PROJEKT/README.md",
    "SOFTWARE/README.md",
    "SOFTWARE/requirements-dev.txt",
    "SOFTWARE/pytest.ini",
]
