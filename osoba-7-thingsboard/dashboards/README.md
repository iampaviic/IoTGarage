# Dashboardi

| datoteka | dashboard |
|---|---|
| `glavni.json` | **Garaža – nadzor**: tlocrt (HTML kartica), slobodna mjesta, popunjenost, vozila u garaži, stanje rampi, gumbi (otvori ulaz/izlaz, ručno odobri, odbij), odluke pristupa, alarmi |
| `analitika.json` | **Garaža – analitika**: zauzetost kroz vrijeme, ulasci/izlasci po satu, popunjenost po satu, prosječno trajanje po danu, prihod po danu, tablica završenih sesija |

Uvoz: `python ../provision/provision.py` (ili u UI: *Dashboards → + → Import dashboard*).
Aliasi koriste **tipove i imena** uređaja, ne ID-jeve, pa JSON radi na svakoj instanci gdje je pokrenut `provision.py`.

Promjene: uredi u UI-ju pa *Export* preko ove datoteke, **ili** promijeni `build_dashboards.py`
(treba pokrenut ThingsBoard zbog zadanih postavki widgeta) i pokreni ga.
