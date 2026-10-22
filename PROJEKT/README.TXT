PROJEKT - pisani dio projekta
=============================

Tekstovi su pisani u Markdownu (.md, originalni format; GitLab ih prikazuje
s formatiranjem i dijagramima). Dijagrami u .md datotekama su Mermaid kod
i nalaze se unutar samog teksta.

plan-projekta/
    Prijedlog i plan projekta (FER predlozak).
    IoT_Garaza_Plan_projekta.docx  - original (MS Word)
    IoT_Garaza_Plan_projekta.pdf   - PDF verzija
    slike/                         - WBS i gantogram: PNG + Python skripte
                                     kojima su nacrtani (originali)

dokumentacija/
    Zavrsna tehnicka dokumentacija, jedno poglavlje po datoteci
    (01-uvod.md ... 07-zakljucak.md). Vidi "Sastavljanje rada" dolje.

sustav/
    arhitektura.md            - blok-dijagram, tokovi ulaska/izlaska,
                                raspored, rad kad neki dio ispadne
    komunikacijski-ugovor.md  - sve MQTT teme i JSON poruke
    zahtjevi.md               - funkcionalni i nefunkcionalni zahtjevi
    model-podataka.md         - baza parkirnih sesija, pravilo naplate
    entiteti-i-alarmi.md      - ThingsBoard uredjaji, telemetrija, alarmi

upravljanje/
    README.md                 - pregled posla voditelja
    plan-rada.md              - zadaci po tjednima i osobama
    plan-integracije.md       - 10 koraka integracije s kriterijima
    rizici.md                 - popis rizika i mjera
    odluke.md                 - dnevnik odluka
    sastanci/                 - zapisnici sastanaka (predlozak)

maketa/
    nacrt-makete.md, popis-komponenti.md (+ .csv), shema-spajanja.md,
    oznake-kabela.md, proracun-napajanja.md, foto-dnevnik/
    (3D modeli, tlocrt i dijagrami ozicenja su izvorni kod i nalaze se
    u SOFTWARE/maketa/)

testiranje/
    testni-plan.md, testni-zapisnik.md, sigurnosni-testovi-rampi.md,
    tablica-pragova.md (kalibracija senzora), ogranicenja-alpr.md
    (izvjestaji o tocnosti ALPR-a i OCR-a generiraju alati u
    SOFTWARE/alpr/rezultati/ i SOFTWARE/edge/rezultati/)

slike/
    snimke zaslona ThingsBoard dashboarda (originali)


Sastavljanje rada
-----------------
Zavrsna dokumentacija sastoji se od vise datoteka. Prije predaje se
sastavlja u jednu DOCX i jednu PDF datoteku alatom pandoc
(https://pandoc.org), iz mape PROJEKT/dokumentacija:

    pandoc 0*.md -o IoT-Garaza-dokumentacija.docx
    pandoc 0*.md -o IoT-Garaza-dokumentacija.pdf      (treba LaTeX)

Obje datoteke spremiti u PROJEKT/dokumentacija/. Mermaid dijagrame prije
toga izvesti u PNG (npr. https://mermaid.live) i spremiti originale u
PROJEKT/slike/. Ako se neka .md datoteka izvan dokumentacija/ prilaze
radu, i nju pretvoriti u PDF istom naredbom.
