# Tjedni commitovi u službeni GitLab repozitorij

Službeni repozitorij na GitLabu gradi se **tjedan po tjedan**, prema fazama projekta, tako da povijest
commitova pokazuje put od ideje do gotovog proizvoda. Ova mapa se ne kopira na GitLab.

- [raspored.py](raspored.py) – koji dio repozitorija ulazi u kojem tjednu
- [tjedni_commit.py](tjedni_commit.py) – alat koji pripremi tjedni commit (samo standardni Python ≥ 3.8 i git)

## Raspored

| tjedan | faza | što ulazi |
|---|---|---|
| 1 | ideja, plan, arhitektura | README, `OSTALO`, plan projekta, arhitektura, MQTT ugovor, zahtjevi, plan rada, rizici, odluke, `SOFTWARE/ugovor` |
| 2 | podsustavi I | maketa (`PROJEKT/maketa`, `SOFTWARE/maketa`), senzori, rampe, baza sesija + model podataka |
| 3 | podsustavi II | ALPR, OCR i edge servis, ThingsBoard + snimke dashboarda, mobilna aplikacija |
| 4 | integracija | simulacija cijelog sustava + e2e testovi, postavljanje na edge (`edge/deploy`), `INSTALL.md`, plan integracije, testni plan |
| 5 | testiranje | testni zapisnik, sigurnosni testovi, pragovi senzora, ograničenja i rezultati ALPR-a/OCR-a, izvršne verzije |
| 6 | dokumentacija, obrana | završna dokumentacija, `PREZENTACIJA` |

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
python .gitlab-tjedni/tjedni_commit.py 3 --gitlab ../IoTGarage-gitlab --test
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

Svaka faza ima oznaku (`tjedan-1` … `tjedan-6`), pa se na GitLabu može otvoriti stanje projekta u bilo kojem tjednu.

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
<!-- gitlab:od-tjedna=4 -->
vidljivo ovdje; na GitLabu tek od 4. tjedna
<!-- /gitlab -->

<!-- gitlab:izostavi -->
samo ovdje (npr. GitHub CI), nikad na GitLabu
<!-- /gitlab -->

<!-- gitlab:do-tjedna=3
skriveno ovdje; na GitLabu samo do 3. tjedna (npr. kraći "Brzi start")
-->
```

Osim toga, retci tablica i stavke popisa koji vode na mapu ili datoteku koja još ne postoji se izostave, a
ostale takve poveznice se uklone.
