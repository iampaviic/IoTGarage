# PROJEKT – pisani dio projekta

Tekstovi su pisani u Markdownu (`.md`, originalni format); GitLab ih prikazuje s formatiranjem i dijagramima.
Dijagrami u `.md` datotekama su Mermaid kod unutar samog teksta.

| mapa | sadržaj |
|---|---|
| [plan-projekta/](plan-projekta) | prijedlog i plan projekta (FER predložak): [DOCX](plan-projekta/IoT_Garaza_Plan_projekta.docx) (original), [PDF](plan-projekta/IoT_Garaza_Plan_projekta.pdf); [slike/](plan-projekta/slike) – WBS i gantogram (PNG + Python skripte kojima su nacrtani) |
| [dokumentacija/](dokumentacija) | završna tehnička dokumentacija, jedno poglavlje po datoteci (`01-uvod.md` … `07-zakljucak.md`) – vidi *Sastavljanje rada* dolje |
| [sustav/](sustav) | [arhitektura](sustav/arhitektura.md), [komunikacijski ugovor (MQTT)](sustav/komunikacijski-ugovor.md), [zahtjevi](sustav/zahtjevi.md), [model podataka](sustav/model-podataka.md), [ThingsBoard entiteti i alarmi](sustav/entiteti-i-alarmi.md) |
| [upravljanje/](upravljanje) | [pregled posla voditelja](upravljanje/README.md), [plan rada](upravljanje/plan-rada.md), [plan integracije](upravljanje/plan-integracije.md), [rizici](upravljanje/rizici.md), [odluke](upravljanje/odluke.md), [zapisnici sastanaka](upravljanje/sastanci) |
| [maketa/](maketa) | [nacrt makete](maketa/nacrt-makete.md), [popis komponenti](maketa/popis-komponenti.md) (+ CSV), [shema spajanja](maketa/shema-spajanja.md), [oznake kabela](maketa/oznake-kabela.md), [proračun napajanja](maketa/proracun-napajanja.md), [foto-dnevnik](maketa/foto-dnevnik) |
| [testiranje/](testiranje) | [testni plan](testiranje/testni-plan.md), [testni zapisnik](testiranje/testni-zapisnik.md), [sigurnosni testovi rampi](testiranje/sigurnosni-testovi-rampi.md), [tablica pragova senzora](testiranje/tablica-pragova.md), [ograničenja ALPR-a](testiranje/ogranicenja-alpr.md) |
| [slike/](slike) | snimke zaslona ThingsBoard dashboarda (originali) |

3D modeli, tlocrt i dijagrami ožičenja su izvorni kod i nalaze se u [SOFTWARE/maketa](../SOFTWARE/maketa).
Izvještaje o točnosti ALPR-a i OCR-a generiraju alati u [SOFTWARE/alpr/rezultati](../SOFTWARE/alpr/rezultati) i
[SOFTWARE/edge/rezultati](../SOFTWARE/edge/rezultati).

## Sastavljanje rada

Završna dokumentacija sastoji se od više datoteka. Prije predaje se sastavlja u jednu DOCX i jednu PDF datoteku
alatom [pandoc](https://pandoc.org), iz mape `PROJEKT/dokumentacija`:

```bash
pandoc 0*.md -o IoT-Garaza-dokumentacija.docx
pandoc 0*.md -o IoT-Garaza-dokumentacija.pdf      # treba LaTeX
```

Obje datoteke spremiti u `PROJEKT/dokumentacija/`. Mermaid dijagrame prije toga izvesti u PNG (npr.
[mermaid.live](https://mermaid.live)) i spremiti originale u `PROJEKT/slike/`. Ako se neka `.md` datoteka izvan
`dokumentacija/` prilaže radu, i nju pretvoriti u PDF istom naredbom.
