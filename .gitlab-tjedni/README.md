# Tjedni commitovi u službeni GitLab repozitorij

Službeni repozitorij na GitLabu gradi se **tjedan po tjedan**, prema fazama projekta, tako da povijest
commitova pokazuje put od ideje do gotovog proizvoda. Ova mapa se ne kopira na GitLab.

- [raspored.py](raspored.py) – koji dio repozitorija ulazi u kojem tjednu
- [tjedni_commit.py](tjedni_commit.py) – alat koji pripremi tjedni commit (samo standardni Python ≥ 3.8 i git)

## Raspored

Projekt traje od 19.10.2026. do roka za predaju **29.1.2027.** (15 tjedana). Svaki dio ulazi u tjednu kad se na
njemu radi prema gantogramu iz plana projekta:

| tjedan | datumi | faza | što ulazi |
|---|---|---|---|
| 1 | 19.10. – 25.10. | 1 – definicija | README, `OSTALO`, plan projekta, arhitektura, MQTT ugovor, zahtjevi, plan rada, rizici, odluke, `SOFTWARE/ugovor` |
| 2 | 26.10. – 1.11. | 1 – definicija | maketa: `PROJEKT/maketa` (nacrt, komponente, sheme), `SOFTWARE/maketa` (tlocrt, 3D dijelovi, ožičenje) |
| 3 | 2.11. – 8.11. | 2 – podsustavi | `SOFTWARE/senzori`, `SOFTWARE/rampe` |
| 4 | 9.11. – 15.11. | 2 – podsustavi | `SOFTWARE/baza` + model podataka, `SOFTWARE/thingsboard` + entiteti i alarmi |
| 5 | 16.11. – 22.11. | 2 – podsustavi | `SOFTWARE/alpr` |
| 6 | 23.11. – 29.11. | 2 – podsustavi | `SOFTWARE/edge` (OCR, kontrola pristupa) |
| 7 | 30.11. – 6.12. | 2 – podsustavi | `SOFTWARE/mobilna-aplikacija`, snimke dashboarda |
| 8 | 7.12. – 13.12. | 3 – integracija | `SOFTWARE/integracija` (simulacija + e2e testovi), plan integracije, testni plan |
| 9 | 14.12. – 20.12. | 3 – integracija | `SOFTWARE/edge/deploy`, `SOFTWARE/INSTALL.md` |
| 10–11 | 21.12. – 3.1. | blagdanska stanka | ništa novo iz rasporeda – samo ono što tim napravi |
| 12 | 4.1. – 10.1. | 4 – testiranje | testni zapisnik, sigurnosni testovi rampi, pragovi senzora, ograničenja ALPR-a |
| 13 | 11.1. – 17.1. | 4 – testiranje | rezultati mjerenja ALPR-a i OCR-a |
| 14 | 18.1. – 24.1. | 5 – dokumentacija | `PROJEKT/dokumentacija` |
| 15 | 25.1. – 29.1. | 5 – predaja | `PREZENTACIJA`, izvršne verzije; predaja do 29.1.2027. |

Pregledne datoteke (`README.md`, `PROJEKT/README.md`, `SOFTWARE/README.md`, `requirements-dev.txt`, `pytest.ini`)
alat svaki tjedan ponovno sastavi tako da spominju samo ono što već postoji – svaka tjedna verzija se može
pokrenuti i testovi prolaze.

## Jednom, na početku

```bash
git clone <url-gitlab-repozitorija> ../IoTGarage-gitlab        # pored ovog repozitorija
```

Ako u GitLab repozitoriju već postoje datoteke nastavnika (npr. predložak `README.md`), alat ih ne dira i
ispiše ih; ako ih treba zamijeniti našima, pokreni tjedan 1 s `--prisili`.

## Svaki tjedan

Iz ovog repozitorija (najnovija verzija grane `main`):

```bash
python .gitlab-tjedni/tjedni_commit.py --gitlab ../IoTGarage-gitlab --test      # tekući tjedan prema datumu
python .gitlab-tjedni/tjedni_commit.py 3 --gitlab ../IoTGarage-gitlab --test    # ili zadani tjedan
```

1. Alat kopira dio za taj tjedan (i sve iz prethodnih tjedana što još nedostaje), osvježi pregledne datoteke,
   pokrene testove (`--test`: napravi `SOFTWARE/.venv` u GitLab klonu) i sve pripremi za commit.
2. U `../IoTGarage-gitlab` dodajte **svoj rad za taj tjedan** – kalibracije, fotografije, zapise u testnom
   zapisniku, foto-dnevnik, ispravke, zapisnike sastanaka.
3. Commit, oznaka i objava:

   ```bash
   python .gitlab-tjedni/tjedni_commit.py 3 --gitlab ../IoTGarage-gitlab --commit --poruka "Kalibrirani senzori P01-P06; sastanak 4.11."
   git -C ../IoTGarage-gitlab push && git -C ../IoTGarage-gitlab push --tags
   ```

   `--commit` napravi commit s porukom „Tjedan N: …“ (+ popis promjena + vaša `--poruka`) i oznaku `tjedan-N`.
   Pushanje uvijek radite sami. Može i ručno: `git commit`, `git tag tjedan-3`, `git push --follow-tags`.

Svaki tjedan ima oznaku (`tjedan-1` … `tjedan-15`), pa se na GitLabu može otvoriti stanje projekta u bilo kojem tjednu.

## Izmjene tima i izmjene u ovom repozitoriju

- Što tim promijeni u GitLab klonu, **ostaje**. Ako se ista datoteka u međuvremenu promijeni i ovdje (npr.
  ispravak u `main`), alat ih spoji (`git merge-file`).
- Ako su obje strane mijenjale **isti redak**, alat javi **KONFLIKT** i datoteku ostavi kako ju je tim ostavio.
  Riješi ručno pa pokreni ponovno s `--zadrzi PUTANJA` (ostaje verzija tima) ili `--prisili` (verzija odavde).
- Datoteku koju je tim obrisao u GitLabu alat ne vraća. Datoteku obrisanu ovdje alat obriše i u GitLabu ako je
  tim nije mijenjao.
- Nova datoteka koja ne odgovara nijednom pravilu u `raspored.py` se samo prijavi – dodaj joj pravilo.
- Stanje alata je u `../IoTGarage-gitlab/.git/tjedni-stanje-v2.json` (ne komita se).

## Oznake u preglednim README datotekama

Nevidljive HTML oznake određuju što se u kojem tjednu pojavljuje (na GitHubu se ne vide):

```markdown
<!-- gitlab:od-tjedna=8 -->
vidljivo ovdje; na GitLabu tek od 8. tjedna
<!-- /gitlab -->

<!-- gitlab:izostavi -->
samo ovdje (npr. GitHub CI), nikad na GitLabu
<!-- /gitlab -->

<!-- gitlab:do-tjedna=7
skriveno ovdje; na GitLabu samo do 7. tjedna (npr. kraći "Brzi start")
-->
```

Osim toga, retci tablica i stavke popisa koji vode na mapu ili datoteku koja još ne postoji se izostave, a
ostale takve poveznice se uklone.
