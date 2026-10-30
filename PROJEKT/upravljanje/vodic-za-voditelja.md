# Vodič za voditelja

Za Patrika. Sve što je trenutno u repozitoriju na jednom mjestu, objašnjeno bez predznanja, i dva vodiča korak po
korak: kako postaviti cijeli sustav kad je hardver spojen i kako hardver integrirati dio po dio.

- **Prvo pročitaj poglavlja 1–6** (oko 30 min): stanje, kako sustav radi, pojmovi, gdje je što, tim, rokovi.
- **Poglavlje 7** napravi jednom na svom laptopu (oko 1 h): sve radi u simulaciji, bez hardvera.
- **Poglavlja 8–10** su za rad s hardverom: postavljanje, integracija korak po korak, rješavanje problema.

Stanje opisano ovdje provjereno je 30. 10. 2026. Ovaj dokument se ne kopira na GitLab (vidi
[.gitlab-tjedni](../../.gitlab-tjedni/README.md)) jer opisuje i stanje GitHuba.

## Sadržaj

1. [Stanje u jednoj minuti](#1-stanje-u-jednoj-minuti)
2. [Kako sustav radi](#2-kako-sustav-radi)
3. [Rječnik](#3-rječnik)
4. [Gdje je što](#4-gdje-je-što)
5. [Tim i prvi zadaci](#5-tim-i-prvi-zadaci)
6. [Rokovi, odluke i tvoj tjedni ritam](#6-rokovi-odluke-i-tvoj-tjedni-ritam)
7. [Priprema laptopa (jednom)](#7-priprema-laptopa-jednom)
8. [Postavljanje cijelog sustava s hardverom](#8-postavljanje-cijelog-sustava-s-hardverom)
9. [Integracija hardvera korak po korak](#9-integracija-hardvera-korak-po-korak)
10. [Kad nešto ne radi](#10-kad-nešto-ne-radi)
11. [Dan demonstracije](#11-dan-demonstracije)

---

## 1. Stanje u jednoj minuti

| dio | stanje |
|---|---|
| plan projekta (v1.3, gantogram, kontrolne točke) | ✅ [PROJEKT/plan-projekta](../plan-projekta) |
| arhitektura i komunikacijski ugovor (sve MQTT poruke) | ✅ varijanta A je napisana u kodu; varijanta B (sve u ThingsBoardu) je samo opisana |
| softver na edge računalu: ALPR, OCR, kontrola pristupa, baza sesija | ✅ napisan i testiran u simulaciji |
| ThingsBoard: instalacija, uređaji, 2 dashboarda, 7 alarma, bridge | ✅ isproban na ThingsBoard CE 4.2.1 |
| simulacija cijelog sustava na jednom laptopu | ✅ `simulacija.py`, 0 poruka koje krše ugovor |
| automatski testovi | ✅ **145 testova prolazi** (Python) + testovi oba firmwarea u CI-u |
| firmware za oba ESP32 | ✅ preveden, ⬜ **nije isproban na hardveru** |
| ALPR na stvarnim fotografijama makete | ⬜ zasad samo sintetske slike (detekcija 100 % u kontroliranim uvjetima) |
| maketa | ⬜ nacrt 1:1, 3D dijelovi i 3D sklop su gotovi; fizička maketa ne postoji |
| mobilna aplikacija (Leo) | ⬜ nije započeta, postoje samo upute |
| završna dokumentacija | ✅ kostur i 2 poglavlja, ⬜ ostalo |

Ukratko: **sav softver postoji i radi u simulaciji. Posao koji preostaje je hardver, maketa, mjerenja na stvarnim
fotografijama, mobilna aplikacija i dokumentacija.**

### GitHub: dvije verzije repozitorija

Na GitHubu (`iampaviic/iotgarage`) grana **`main` još ima staru strukturu** (mape `osoba-1-voditelj` …
`osoba-8-baza-testovi`). Sve novije – struktura prema uputama nastavnika (`PROJEKT`, `SOFTWARE`, `PREZENTACIJA`,
`OSTALO`), plan projekta, alat za GitLab, 3D sklop, varijanta B – nalazi se na grani **`claude/gitlab-struktura`**.

**Tvoj prvi zadatak:** spoji tu granu u `main`, da cijeli tim radi s istom verzijom.

1. GitHub → *Pull requests* → *New pull request* → base: `main`, compare: `claude/gitlab-struktura` → *Create pull request*.
2. Pričekaj da CI (zelena kvačica) prođe → *Merge pull request*.
3. Javi timu: `git checkout main && git pull`. Tko ima nekomitane promjene u starim `osoba-N` mapama, neka ih prvo
   spremi i prenese u nove mape (tablica u [poglavlju 4](#4-gdje-je-što)).

---

## 2. Kako sustav radi

Priča jednog autića:

1. Autić dođe do ulazne rampe i stane na graničnik. **IR senzor** na crti rampe ga vidi.
2. **ESP32 rampi** javi „vozilo je na ulazu“ preko Wi-Fi-ja (MQTT poruka).
3. Na **edge računalu** (Raspberry Pi uz maketu) servis za kontrolu pristupa traži od **ALPR-a** da pročita
   registraciju. ALPR uzme do 3 slike s **USB kamere**, pronađe pločicu i pročita znakove (OCR).
4. Kontrola pristupa odluči: pouzdanost ≥ 0,85, ima slobodnih mjesta i vozilo već nije unutra → **GRANTED**.
   Otvori **parkirnu sesiju** u bazi (SQLite) i pošalje rampi naredbu „otvori“.
5. ESP32 rampi okrene **servo**, upali zelenu LED, a kad autić prođe, sam zatvori rampu nakon 2 s.
6. Autić parkira na P03. **Ultrazvučni senzor** iznad mjesta to vidi, ESP32 senzora javi „P03 zauzeto“, LED na mjestu
   postane crvena.
7. Pri izlasku isto: kamera na izlazu → pronađena sesija → **trajanje i cijena** → rampa se otvara.
8. Sve poruke idu i u **ThingsBoard** (laptop): dashboard u stvarnom vremenu, povijest, alarmi, gumbi za ručno
   upravljanje. **Mobilna aplikacija** čita analitiku iz ThingsBoarda.

Najvažnije pravilo arhitekture (varijanta A): **odluka se donosi lokalno na edge računalu.** Ulaz i izlaz rade i kad
ThingsBoard ili internet ne rade; ThingsBoard je nadzor i povijest. Detalji:
[arhitektura.md](../sustav/arhitektura.md).

```
 MAKETA                         EDGE RAČUNALO (Raspberry Pi)              LAPTOP
 ESP32 senzora (6 mjesta) ─┐    ┌ MQTT broker (Mosquitto) ┐               ThingsBoard (Docker)
 ESP32 rampi (2 rampe)  ───┼──► │ ALPR + OCR              │ ── bridge ──►  dashboardi, alarmi
 USB kamera ───────────────┘    │ kontrola pristupa       │                     │
                                └ baza sesija (SQLite)    ┘               mobilna aplikacija
```

**Tri vrste računala:** dva ESP32 (mikrokontroleri na maketi), Raspberry Pi (edge računalo, jedan, uz maketu) i
laptop (ThingsBoard, razvoj, dashboard na demonstraciji). Sve je spojeno na **isti Wi-Fi router**.

---

## 3. Rječnik

| pojam | značenje |
|---|---|
| **MQTT** | jednostavan protokol za poruke: uređaj pošalje poruku na *temu*, a svi koji su *pretplaćeni* na tu temu je dobiju |
| **broker** | „poštanski ured“ za MQTT poruke; kod nas Mosquitto na Raspberry Piju, port 1883 |
| **tema** (*topic*) | adresa poruke, npr. `garage/parking/spot/P03/telemetry` |
| **retained** | broker pamti zadnju poruku teme i daje je svakom tko se spoji kasnije (koristimo za stanja) |
| **komunikacijski ugovor** | popis svih tema i oblika poruka ([komunikacijski-ugovor.md](../sustav/komunikacijski-ugovor.md)); monitor ugovora crveno označi svaku poruku koja ga krši |
| **ESP32** | mali mikrokontroler s Wi-Fi-jem; imamo dva: senzori mjesta i rampe |
| **firmware** | program na ESP32 (C++); prevodi se i učitava s **PlatformIO** u VS Codeu |
| **edge računalo** | računalo uz maketu koje donosi odluke (Raspberry Pi; Jetson Nano je rezerva) |
| **ALPR** | automatsko prepoznavanje registracija: *detekcija* (gdje je pločica) + *OCR* (što na njoj piše) |
| **OCR** | čitanje znakova sa slike; imamo dva motora (Tesseract i usporedba s predlošcima) koji glasaju |
| **pouzdanost** (*confidence*) | 0–1, koliko se čitanja slažu. ≥ 0,85 automatska odluka, 0,60–0,85 nova slika, < 0,60 ručno odobrenje |
| **kontrola pristupa** (*access control*) | servis koji odlučuje: `GRANTED`, `DENIED`, `RETRY`, `MANUAL_REQUIRED` |
| **parkirna sesija** | zapis jednog boravka: ulaz, mjesto, izlaz, trajanje, cijena |
| **ThingsBoard** | IoT platforma: dashboardi, alarmi, povijest (*digitalni blizanac* garaže) |
| **bridge** | program koji prosljeđuje poruke s brokera u ThingsBoard i čuva ih dok ThingsBoard ne radi |
| **RPC** | naredba iz ThingsBoarda prema uređaju; tako rade gumbi na dashboardu |
| **simulator** | program koji se na MQTT-u ponaša točno kao hardver; tako svatko radi bez tuđeg hardvera |
| **requestId** | oznaka naredbe; potvrda nosi isti `requestId`, a ponovljena naredba se ne izvršava dvaput |
| **Last Will** / **heartbeat** | poruka „uređaj je offline“ koju broker pošalje kad ESP32 nestane / poruka „živ sam“ svakih 30 s |
| **Docker**, **docker compose** | pokreće programe u kontejnerima, istim naredbama na svakom računalu |
| **venv** | izolirano Python okruženje projekta (mapa `.venv`) |
| **CI** | GitHub nakon svakog pusha sam pokrene sve testove i prevede firmware |
| **grana**, **PR** | grana = odvojena linija rada; *pull request* = prijedlog spajanja grane u `main` |
| **KT** | kontrolna točka iz plana projekta |

---

## 4. Gdje je što

| pitanje | gdje |
|---|---|
| tko radi što | [README.md](../../README.md#tim) i README u svakoj mapi `SOFTWARE/*` (zadaci s kvačicama) |
| plan, rokovi, zadaci po tjednu | [plan-rada.md](plan-rada.md), [plan projekta](../plan-projekta) |
| kako sustav radi | [arhitektura.md](../sustav/arhitektura.md), [zahtjevi.md](../sustav/zahtjevi.md) |
| koje poruke i teme | [komunikacijski-ugovor.md](../sustav/komunikacijski-ugovor.md), kod: [SOFTWARE/ugovor](../../SOFTWARE/ugovor) |
| uređaji i alarmi u ThingsBoardu | [entiteti-i-alarmi.md](../sustav/entiteti-i-alarmi.md) |
| baza i naplata | [model-podataka.md](../sustav/model-podataka.md), [SOFTWARE/baza](../../SOFTWARE/baza) |
| odluke i rizici | [odluke.md](odluke.md), [rizici.md](rizici.md) |
| redoslijed integracije | [plan-integracije.md](plan-integracije.md) (10 koraka) |
| što kupiti | [popis-komponenti.md](../maketa/popis-komponenti.md) (~230 €) |
| kako spojiti žice | [shema-spajanja.md](../maketa/shema-spajanja.md), dijagrami u [SOFTWARE/maketa/elektronika](../../SOFTWARE/maketa/elektronika) |
| napajanje | [proracun-napajanja.md](../maketa/proracun-napajanja.md) (adapter 5 V / 4 A) |
| raspored makete i položaj kamere | [nacrt-makete.md](../maketa/nacrt-makete.md), tlocrt 1:1 u [SOFTWARE/maketa/nacrt](../../SOFTWARE/maketa/nacrt) |
| 3D dijelovi i 3D model cijele makete | [SOFTWARE/maketa/3d](../../SOFTWARE/maketa/3d), [3d/sklop](../../SOFTWARE/maketa/3d/sklop) |
| instalacija svega | [SOFTWARE/INSTALL.md](../../SOFTWARE/INSTALL.md) |
| testovi i rezultati | [testni-plan.md](../testiranje/testni-plan.md), [testni-zapisnik.md](../testiranje/testni-zapisnik.md) |
| upute za operatera dashboarda | [03-korisnicke-upute.md](../dokumentacija/03-korisnicke-upute.md) |
| završna demonstracija | [demo-scenarij.md](../../PREZENTACIJA/demo-scenarij.md) |
| predaja na GitLab tjedan po tjedan | [.gitlab-tjedni/README.md](../../.gitlab-tjedni/README.md) |

Stare mape na `main` → nove mape:

| staro (`main`) | novo |
|---|---|
| `osoba-1-voditelj` | `PROJEKT/sustav`, `PROJEKT/upravljanje`, `SOFTWARE/ugovor`, `SOFTWARE/integracija`, `PREZENTACIJA` |
| `osoba-2-maketa` | `PROJEKT/maketa`, `SOFTWARE/maketa` |
| `osoba-3-senzori` | `SOFTWARE/senzori` |
| `osoba-4-rampe` | `SOFTWARE/rampe` |
| `osoba-5-alpr` | `SOFTWARE/alpr` |
| `osoba-6-ocr-edge` | `SOFTWARE/edge` |
| `osoba-7-thingsboard` | `SOFTWARE/thingsboard`, `SOFTWARE/mobilna-aplikacija` |
| `osoba-8-baza-testovi` | `SOFTWARE/baza`, `PROJEKT/testiranje`, `PROJEKT/dokumentacija` |

---

## 5. Tim i prvi zadaci

Prvi zadaci su iz [plan-rada.md](plan-rada.md) i vode prema **KT2 (10. 11. 2026.)**: jedan senzor, jedan servo,
ThingsBoard i ALPR na stvarnoj fotografiji, plus nacrt makete.

| tko | uloga | već spremno u repozitoriju | prvi zadatak |
|---|---|---|---|
| **Patrik** | voditelj; maketa (s Lovrom) | sve planske datoteke, nacrt makete, 3D dijelovi | spojiti granu (pogl. 1), potvrditi odluke (pogl. 6), naručiti komponente, odabrati mjerilo (preporuka 1:24), **provjeriti minimalni fokus kamere** |
| **Lovro Gale** | baza, testovi, GitHub; pomaže Tomi i Patriku | baza sesija, naplata, testni plan, zapisnik | pročitati testni plan, dogovoriti pravilo naplate, napajanje i ožičenje |
| **Toma Burgund** | senzori mjesta | firmware, filtar, simulator, alati za kalibraciju i test 20× | spojiti **jedan** HC-SR04 s djeliteljem i vidjeti mjerenja (`cal`) |
| **Luka Oslić** | rampe, pravila pristupa | firmware rampi, stroj stanja, simulator, sigurnosni testovi | pokrenuti **jedan** SG90 s ESP32 (`open e`) |
| **Sven Matić** | detekcija pločice | detektor, generator pločica, alati za snimanje i mjerenje | isprintati pločice, snimiti prvih 10 fotografija autića |
| **Lukas Davorija** | OCR, edge računalo | OCR, ALPR servis, kontrola pristupa, Docker za Pi | `python -m edge_service read` na prvim fotografijama; postaviti Raspberry Pi |
| **Anja** | ThingsBoard | docker-compose, provisioning, bridge, dashboardi, alarmi | pokrenuti ThingsBoard na laptopu koji ide na demonstraciju, `provision.py` |
| **Leo Hreljanović** | mobilna aplikacija, analitika | upute u [SOFTWARE/mobilna-aplikacija](../../SOFTWARE/mobilna-aplikacija), analitički dashboard | odabrati tehnologiju (npr. Flutter), dohvatiti prve podatke preko REST API-ja |

Zamjene ako netko ispadne (rizik R-11): 3↔4, 5↔6, 7↔8. Svaki podsustav ima simulator, pa nitko ne čeka tuđi hardver.

---

## 6. Rokovi, odluke i tvoj tjedni ritam

### Kontrolne točke

| | što mora biti gotovo | datum |
|---|---|---|
| KT1 | arhitektura, plan, repozitorij | 28.10. (ostvareno 27.10.) ✅ |
| **KT2** | **dokaz izvedivosti: 1 senzor, 1 servo, ThingsBoard, ALPR na stvarnoj fotografiji; nacrt makete** | **10.11.2026.** |
| KT3 | baza makete izrađena | 23.11.2026. |
| KT4 | podsustavi rade na hardveru (senzori 20/20, sigurnosni testovi rampi, detekcija ≥ 90 %) | 23.12.2026. |
| KT5 | integracija s hardverom završena; MVP mobilne aplikacije | 11.1.2027. |
| KT6 | svi testni scenariji prolaze, rezervni video snimljen | 17.1.2027. |
| KT7 | dokumentacija, prezentacija, predaja na GitLab | **29.1.2027.** |

Faze: 1 definicija (do 1.11.) · 2 podsustavi (2.11.–6.12.) · 3 integracija (7.–20.12.) · blagdanska stanka kao
rezerva (21.12.–3.1.) · 4 testiranje (4.–17.1.) · 5 dokumentacija i predaja (18.–29.1.).
**Integraciju s hardverom završiti prije blagdana** (rizik R-16).

### Odluke koje čekaju tebe i tim

| odluka | prijedlog | gdje |
|---|---|---|
| edge računalo | Raspberry Pi 4, Jetson Nano kao rezerva (D-004) | [odluke.md](odluke.md) |
| jedna ili dvije kamere | počnite s jednom koja se premješta, druga (~20 €) ako budžet dopusti (D-007) | [odluke.md](odluke.md), [nacrt-makete.md](../maketa/nacrt-makete.md) |
| varijanta arhitekture A ili B | **A** – napisana je i testirana; B traži novi posao u ThingsBoardu | [arhitektura.md §9](../sustav/arhitektura.md#9-varijanta-b-sustav-oslonjen-na-thingsboard) |
| tko smije ući | `policy: open` (svaka valjana pločica) ili `allowlist` (samo s popisa) | `SOFTWARE/edge/edge.example.yaml` |
| naplata | 15 min besplatno, 1,50 € po započetom satu, najviše 15 € dnevno; demo: 1 min = 1 h (D-009) | [odluke.md](odluke.md) |
| mjerilo autića | 1:24 (baza 688 × 821 mm) | [nacrt-makete.md](../maketa/nacrt-makete.md) |
| vlastiti Wi-Fi router za maketu | da – fakultetski Wi-Fi često blokira ESP32 (rizik R-07, najveći rizik) | [rizici.md](rizici.md) |

Odluku upiši u [odluke.md](odluke.md) (kontekst → odluka → posljedice) i makni oznaku **[PRIJEDLOG]**.

### Jednom, na početku

- [ ] spojiti `claude/gitlab-struktura` u `main` ([poglavlje 1](#github-dvije-verzije-repozitorija))
- [ ] zaštititi `main`: GitHub → *Settings* → *Branches* → *Add rule* → obavezan pull request i zeleni CI
- [ ] ploča zadataka: GitHub *Projects*, jedna kartica po retku iz [plan-rada.md](plan-rada.md)
- [ ] termin tjednog sastanka (30–45 min)
- [ ] klon službenog GitLab repozitorija za tjedne commitove ([.gitlab-tjedni](../../.gitlab-tjedni/README.md))

### Svaki tjedan

1. **Sastanak** po [predlošku](sastanci/predlozak.md): status po osobi (2 min), demo zadnjeg koraka integracije,
   odluke, rizici, zadaci za idući tjedan. Zapisnik u `sastanci/`.
2. **Jedan korak integracije** s pravim hardverom ([poglavlje 9](#9-integracija-hardvera-korak-po-korak)).
   Rezultat upisuje Lovro u [testni-zapisnik.md](../testiranje/testni-zapisnik.md).
3. **Pregled PR-ova**: svaki PR pregledava barem jedna osoba; CI mora biti zelen.
4. **Tjedni commit na GitLab** (iz ovog repozitorija, nakon spajanja u `main`):

   ```bash
   python .gitlab-tjedni/tjedni_commit.py --gitlab ../IoTGarage-gitlab --test
   # u ../IoTGarage-gitlab dodaj rad tima za taj tjedan (fotografije, kalibracije, zapisnici)
   python .gitlab-tjedni/tjedni_commit.py --gitlab ../IoTGarage-gitlab --commit --poruka "Kratki opis tjedna"
   git -C ../IoTGarage-gitlab push && git -C ../IoTGarage-gitlab push --tags
   ```

   Alat ne dopušta povratak na raniji tjedan. Ako tjedni 1 i 2 još nisu predani, pokreni ih redom
   (`tjedni_commit.py 1 …`, pa `tjedni_commit.py 2 …`).

---

## 7. Priprema laptopa (jednom)

Cilj: na svom laptopu pokreneš cijeli sustav u simulaciji i ThingsBoard. Tada znaš kako sve treba izgledati prije
nego što se spoji hardver.

### 7.1 Instalacije

| program | Windows | Linux (Ubuntu) |
|---|---|---|
| git | [git-scm.com](https://git-scm.com/download/win) | `sudo apt install git` |
| Python 3.11 ili 3.12 | [python.org](https://www.python.org/downloads/); u instalaciji označi **„Add python.exe to PATH“** | `sudo apt install python3 python3-venv` |
| Tesseract OCR | instalacija s [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), zatim `C:\Program Files\Tesseract-OCR` dodaj u PATH | `sudo apt install tesseract-ocr` |
| Mosquitto | [mosquitto.org](https://mosquitto.org/download/), zatim `C:\Program Files\mosquitto` dodaj u PATH | `sudo apt install mosquitto mosquitto-clients` |
| Docker | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (traži WSL 2) | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/ubuntu/) |
| VS Code + PlatformIO | [code.visualstudio.com](https://code.visualstudio.com), u VS Codeu *Extensions* → „PlatformIO IDE“ | isto |

PATH na Windowsu: *Start* → „environment variables“ → *Path* → *New*. Nakon toga otvori **novi** terminal i provjeri:
`git --version`, `python --version`, `tesseract --version`, `docker --version`.

### 7.2 Repozitorij i testovi

```bash
git clone https://github.com/iampaviic/iotgarage.git IoTGarage
cd IoTGarage/SOFTWARE                     # SVE naredbe u ovom vodiču pokreću se iz mape SOFTWARE
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                                    # ~1 min
```

Uspjeh: zadnji redak je `145 passed`. Dok grana nije spojena u `main` (poglavlje 1), nakon kloniranja napravi
`git checkout claude/gitlab-struktura`.

- Repozitorij je privatan → git traži prijavu: korisničko ime s GitHuba i *personal access token* umjesto lozinke
  (GitHub → *Settings* → *Developer settings* → *Personal access tokens*).
- Windows PowerShell odbija `activate` → jednom: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Svaki novi terminal: ponovno `cd IoTGarage/SOFTWARE` i aktiviraj `.venv` (u promptu se vidi `(.venv)`).

### 7.3 Cijeli sustav u simulaciji

```bash
python integracija/simulacija.py --broker
```

Pokrene broker (ako već ne radi), simulator senzora, simulator rampi, ALPR sa sintetskom kamerom, kontrolu pristupa
i bazu, pa odigra demo: ulaz, parkiranje, nečitljivu pločicu s ručnim odobrenjem, izlaz bez sesije i izlaz s cijenom.
Uspjeh: na kraju piše `trajanje … s, cijena 1.50 EUR` i `poruke koje krše ugovor: 0`.

Sam upravljaš s `python integracija/simulacija.py --broker --interactive` (upute se ispišu).
Što se događa na MQTT-u, u drugom terminalu: `python -m garage_contract.monitor` (crveno = poruka krši ugovor).

### 7.4 ThingsBoard

```bash
cd thingsboard
docker compose up -d                      # prvi put ~2–3 min
python provision/provision.py             # uređaji, alarmi, dashboardi (smije se pokrenuti više puta)
cd ..
python integracija/simulacija.py --broker --tb --interactive
```

Otvori <http://localhost:8080>, prijava `tenant@thingsboard.org` / `tenant` → *Dashboards* → **Garaža – nadzor**.
Uspjeh: mjesta mijenjaju boju dok simulacija radi. Prije demonstracije lozinku promijeni (ikona profila →
*Change password*), a `provision.py` od tada pokreći s `--password <nova>`.

---

## 8. Postavljanje cijelog sustava s hardverom

Ovo je postupak kad je hardver **spojen i ožičen** (kako se do toga dolazi dio po dio: [poglavlje 9](#9-integracija-hardvera-korak-po-korak)).

### 8.1 Mreža i adrese

Sve ide na **vlastiti Wi-Fi router** makete. ESP32 radi samo na **2,4 GHz** mreži – na routeru uključi 2,4 GHz
(ili zasebnu 2,4 GHz mrežu) i ne koristi mrežu s prijavom preko web stranice.

U postavkama routera (DHCP → *address reservation*) svakom računalu daj stalnu adresu. Primjer koji je već upisan
u predloške:

| uređaj | adresa | gdje se upisuje |
|---|---|---|
| Raspberry Pi (edge, broker) | `192.168.1.10` | `MQTT_HOST` u `secrets.h` oba ESP32 |
| laptop (ThingsBoard) | `192.168.1.20` | `TB_HOST` u `SOFTWARE/edge/deploy/.env` na Piju |
| ESP32 senzora, ESP32 rampi | bilo koja (DHCP) | – |

Ako router dijeli druge adrese (npr. `192.168.0.x`), koristi njih – bitno je da su iste u svim datotekama.

### 8.2 Raspberry Pi (edge računalo)

1. **Sustav:** u [Raspberry Pi Imageru](https://www.raspberrypi.com/software/) odaberi *Raspberry Pi OS Lite
   (64-bit)*. U *Edit settings* postavi: hostname `garaza-edge`, korisnik `pi` (+ lozinka), Wi-Fi routera makete,
   uključi SSH. Zapiši na microSD, umetni u Pi, uključi.
2. **Spoji se s laptopa:** `ssh pi@garaza-edge.local` (ili `ssh pi@192.168.1.10`).
3. **Docker:**
   ```bash
   sudo apt update && sudo apt full-upgrade -y && sudo apt install -y git
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER          # zatim se odjavi (exit) i ponovno spoji
   docker run --rm hello-world            # mora ispisati "Hello from Docker!"
   ```
4. **Kod i postavke:**
   ```bash
   git clone https://github.com/iampaviic/iotgarage.git ~/IoTGarage
   cd ~/IoTGarage/SOFTWARE
   cp edge/edge.example.yaml edge/edge.yaml            # kamera, pragovi, policy, naplata
   cp edge/deploy/.env.example edge/deploy/.env
   nano edge/deploy/.env                               # TB_HOST = adresa laptopa s ThingsBoardom
   ```
   U `edge.yaml` za početak ništa ne mijenjaj (jedna kamera `"0"`, `policy: open`, demo naplata).
   **`edge.yaml` mora postojati prije pokretanja**, inače Docker umjesto datoteke napravi praznu mapu.
5. **Pokretanje** (prvi put gradi image, 10–30 min):
   ```bash
   cd ~/IoTGarage/SOFTWARE/edge/deploy
   alias dc='docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml'   # kraća naredba (vidi ispod)
   dc up -d --build
   dc ps                                               # mosquitto, edge, tb-bridge: running
   dc logs -f edge                                     # zapisi edge servisa (Ctrl+C za izlaz)
   ```
   `alias` vrijedi do odjave; da bude trajan, isti redak dodaj na kraj `~/.bashrc`. Naredbe `dc …` u ovom vodiču
   pokreću se iz mape `~/IoTGarage/SOFTWARE/edge/deploy`.
   Bez kamere (samo za probu): `docker compose -f docker-compose.edge.yml up -d --build` – tada ALPR koristi
   sintetske slike. Servisi se nakon restarta Pija pokreću sami (`restart: unless-stopped`).
6. **Provjera s laptopa:** `python -m garage_contract.monitor --host 192.168.1.10` – svakih 30 s stižu heartbeat
   poruke servisa na Piju.
7. **Vrijeme bez interneta (opcionalno, D-011):** `sudo apt install -y chrony`, u `/etc/chrony/chrony.conf` dodaj
   redak `allow 192.168.1.0/24`, `sudo systemctl restart chrony`; zatim u `secrets.h` oba ESP32 `NTP_SERVER` =
   adresa Pija.

Nova verzija koda: `cd ~/IoTGarage && git pull && cd SOFTWARE/edge/deploy && dc up -d --build`.
Isključivanje Pija uvijek s `sudo shutdown -h now` (naglo isključivanje može oštetiti microSD).

### 8.3 Laptop: ThingsBoard

Kao u [7.4](#74-thingsboard), na laptopu koji ide na demonstraciju:

```bash
cd SOFTWARE/thingsboard && docker compose up -d && python provision/provision.py
```

- Da tlocrt na dashboardu odgovara maketi: `python provision/provision.py --positions ../maketa/nacrt/spots.json`.
- Bridge na Piju spaja se na laptop na **port 1884**. Ako Windows pita za vatrozid, dopusti Docker na privatnoj mreži.
- Za demonstraciju tajni token: `python provision/provision.py --token <tajna>` i isti `TB_GATEWAY_TOKEN` u `.env`
  na Piju, pa na Piju `dc up -d`.

Uspjeh: na dashboardu **Garaža – nadzor** uređaj *Garage-Edge* je aktivan i stižu podaci.

### 8.4 ESP32 senzora

1. VS Code → *File* → *Open Folder* → `SOFTWARE/senzori/firmware` (PlatformIO sam prepozna projekt).
2. Kopiraj `include/secrets.example.h` u `include/secrets.h` i upiši: `WIFI_SSID`, `WIFI_PASSWORD`,
   `MQTT_HOST` (adresa Pija), `NTP_SERVER`. `secrets.h` se nikad ne komita.
3. Spoji ESP32 USB kabelom koji **prenosi podatke** (ne samo punjenje).
4. *Upload* (strelica → u donjoj traci PlatformIO-a) ili `pio run -t upload`. Ako zapne na `Connecting....___`,
   drži tipku **BOOT** na pločici dok upload ne krene.
5. *Serial Monitor* (ikona utikača) ili `pio device monitor` (115200). Očekuješ:
   ```
   IoT Garage spot sensors 0.1.0, 6 spots
   WiFi: connecting...
   MQTT: connecting to 192.168.1.10:1883
   MQTT: connected
   ```
   Naredba `status` mora javiti `WiFi=1 MQTT=1 time=1`.
6. Na laptopu `python -m garage_contract.monitor --host 192.168.1.10`: zelene poruke
   `garage/parking/spot/P01…P06/telemetry`.

Pinovi i pragovi su u `include/config.h` – nakon kalibracije ([9, korak H3](#h3-svih-6-senzora-kalibracija-i-test-20)) tamo se upišu pragovi.

### 8.5 ESP32 rampi

Isto kao 8.4, u mapi `SOFTWARE/rampe/firmware`. U serijskom monitoru očekuješ `IoT Garage gates 0.1.0` i
`MQTT: connected`. Naredbe: `open e`, `close e`, `reset e`, `status` (`x` umjesto `e` = izlazna rampa).
Kutovi serva (`closedAngle`, `openAngle`) su u `include/config.h`.

### 8.6 Kamera

1. Kamera je na mostu iznad trake, **200 mm iza crte rampe, objektiv ~130 mm iznad poda**, gleda koso prema dolje na
   pločicu autića koji stoji na graničniku ([nacrt-makete.md §3](../maketa/nacrt-makete.md#3-kamera)).
2. Uključi je u USB Raspberry Pija. Provjera na Piju: `ls /dev/video*` → mora postojati `/dev/video0`.
3. Dvije kamere: druga je obično `/dev/video2`. Dodaj je u `docker-compose.camera.yml` (`devices`) i u `edge.yaml`
   za izlaz `camera: "2"` (upute su u komentarima `edge.example.yaml`).
4. Svjetlo: LED traka s difuzorom iznad zone kamere, pločice na **mat** papiru, bez odsjaja.

### 8.7 Svaki put kad pališ sustav

1. Router → 2. Raspberry Pi (servisi se pokrenu sami, ~1 min) → 3. laptop: `docker compose up -d` u
   `SOFTWARE/thingsboard`, otvori dashboard → 4. maketa: sklopka 5 V.
5. Nakon ~30 s: sva mjesta imaju boju, rampe su zatvorene, broj slobodnih mjesta je točan.
6. Proba: autić na ulaz → rampa se otvara → parkiraj → mjesto crveno.

Gašenje obrnutim redom; Pi sa `sudo shutdown -h now`. Upute za operatera dashboarda:
[03-korisnicke-upute.md](../dokumentacija/03-korisnicke-upute.md).

---

## 9. Integracija hardvera korak po korak

**Pravila:**

- **Jedan novi dio odjednom.** Sve što još ne postoji zamjenjuje simulator ili laptop.
- Svaki korak ima **kriterij uspjeha**. Tek kad prođe, ide sljedeći. Rezultat upisuje Lovro u
  [testni-zapisnik.md](../testiranje/testni-zapisnik.md) (datum, tko, prošlo/palo, napomena).
- Dok je uključen bilo koji MQTT dio, u jednom terminalu stalno radi `python -m garage_contract.monitor`.
- **Prije svakog spajanja na ESP32 isključi napajanje.** Žice provjeri dvaput, prema
  [shemi spajanja](../maketa/shema-spajanja.md).
- Koraci prate [plan-integracije.md](plan-integracije.md) (I1–I10 u zagradama).

Dok Raspberry Pi nije spreman, **broker može biti laptop**: ESP32 tada u `MQTT_HOST` ima adresu laptopa. Mosquitto
na laptopu po zadanom prima samo lokalne veze, pa napravi datoteku `lan.conf` s dva retka:

```
listener 1883
allow_anonymous true
```

i pokreni `mosquitto -c lan.conf -v` (na Windowsu prije toga zaustavi servis: terminal kao administrator,
`net stop mosquitto`; vatrozidu dopusti pristup na privatnoj mreži).

| korak | što | tko | rok |
|---|---|---|---|
| H0 | napajanje bez elektronike | Patrik, Lovro | prije prvog spajanja |
| H1 | jedan ultrazvučni senzor | Toma | KT2 |
| H2 | senzori na MQTT-u (I1) | Toma | KT2 |
| H3 | svih 6 senzora, kalibracija i test 20× | Toma, Lovro, Patrik | KT4 |
| H4 | senzori u ThingsBoardu (I2) | Anja | KT2 |
| H5 | jedan servo | Luka | KT2 |
| H6 | obje rampe: IR, LED, tipke, sigurnosni testovi | Luka, Patrik | KT4 |
| H7 | rampe na MQTT-u (I3) | Luka | KT4 |
| H8 | kamera, detekcija i OCR (I4, I5) | Sven, Lukas, Patrik | KT2 (prva fotografija), KT4 (≥ 90 %) |
| H9 | cijeli ulaz na edge računalu (I6–I8) | Lukas, Luka | KT5 |
| H10 | izlaz i ThingsBoard (I9, I10) | svi | KT5 |
| H11 | testovi otpornosti i proba demonstracije | svi | KT6 |

### H0. Napajanje bez elektronike

Treba: adapter 5 V / 4 A, sklopka, WAGO spojnice, kondenzatori 1000 µF, multimetar.

1. Spoji adapter → sklopka → WAGO **+5 V** i WAGO **GND** (vidi [shemu](../maketa/shema-spajanja.md#napajanje-i-masa)).
2. Kondenzator 1000 µF uz napajanje serva i uz LED traku – **duža nožica (+) na +5 V**.
3. Uključi i izmjeri između +5 V i GND.

**Uspjeh:** 4,9–5,2 V. Raspberry Pi ima **svoj** USB-C adapter i ne spaja se na ovaj razvod.

### H1. Jedan ultrazvučni senzor

Treba: ESP32 senzora, jedan HC-SR04, otpornici 1 kΩ i 2 kΩ (ili 2 × 1 kΩ), protoboard.

1. **Djelitelj za ECHO** (obavezan – 5 V na ulazu uništi ESP32): ECHO → 1 kΩ → točka → 2 kΩ → GND; točka ide na
   ESP32 GPIO36 (mjesto P01).
2. **Provjera djelitelja prije ESP32:** ulaz djelitelja spoji na +5 V i izmjeri izlaz: mora biti **3,2–3,4 V**.
3. HC-SR04: VCC na +5 V, GND na GND, TRIG na GPIO23. GND ESP32 spoji na zajednički GND.
4. Učitaj firmware ([8.4](#84-esp32-senzora)), u serijskom monitoru upiši `cal`: stižu redci `CAL,P01,14.2`.
   Ostala mjesta javljaju grešku jer senzora još nema – to je u redu.
5. Stavi autić ispod senzora pa ga makni.

**Uspjeh (TC-S01):** prazno ~14 cm, s autićem ~6–7 cm, razlika veća od 4 cm.

### H2. Senzori na MQTT-u (I1)

1. U `secrets.h` upiši Wi-Fi i `MQTT_HOST` (laptop s `lan.conf` ili Pi), ponovno učitaj firmware.
2. Serijski `status` → `WiFi=1 MQTT=1`.
3. Na laptopu monitor: poruke `garage/parking/spot/P01/telemetry` su **zelene**.
4. Serijski `sim 3 1` (simuliraj zauzeto P03), pa `sim off`.

**Uspjeh:** poruke svih 6 mjesta su zelene, promjena stanja stiže za manje od 1 s.

### H3. Svih 6 senzora, kalibracija i test 20×

1. Na mostu makete (113 mm iznad poda) montiraj 6 nosača i senzora, svaki s djeliteljem; LED traka na mostu.
2. Kalibracija (ESP32 USB-om na laptopu):
   ```bash
   python senzori/tools/kalibracija.py --port COM5          # Linux: /dev/ttyUSB0; port piše u PlatformIO
   ```
   Prati upute (sva mjesta prazna → autić redom na svako mjesto). Alat ispiše redke za `SPOTS[]` u
   `senzori/firmware/include/config.h` i tablicu za [tablica-pragova.md](../testiranje/tablica-pragova.md).
   Ako za neko mjesto piše „PROVJERITI montažu“: senzor nije okomit ili vidi zid.
3. Upiši pragove u `config.h` i ponovno učitaj firmware.
4. Test prihvaćanja (s laptopa, preko MQTT-a):
   ```bash
   python senzori/tools/provjera_20x.py --all --cycles 20 --out testni-zapis-senzori.md
   ```
   Na Windowsu prije toga u PowerShellu `$env:MQTT_HOST="192.168.1.10"` (adresa brokera); na Linuxu
   `MQTT_HOST=192.168.1.10 python …`.

**Uspjeh (TC-S02):** 20/20 ciklusa i točno 40 promjena po mjestu (svaka dodatna promjena = treperenje).

### H4. Senzori u ThingsBoardu (I2)

1. ThingsBoard radi na laptopu ([7.4](#74-thingsboard)).
2. Bridge: na Piju ga pokreće Docker ([8.2](#82-raspberry-pi-edge-računalo)). Dok Pija nema, na laptopu:
   ```bash
   python -m tb_bridge          # MQTT_HOST=localhost, TB_HOST=localhost, TB_MQTT_PORT=1884 su zadane vrijednosti
   ```
3. Stavi i makni autić na jednom mjestu, mjeri štopericom.

**Uspjeh (TC-T01):** tlocrt na dashboardu promijeni boju za manje od 3 s.

### H5. Jedan servo

Treba: ESP32 rampi, jedan SG90, kondenzator 1000 µF.

1. **Servo se napaja s +5 V adaptera, nikad s ESP32.** Smeđa = GND, crvena = +5 V, narančasta (signal) = GPIO13.
   GND adaptera i GND ESP32 moraju biti spojeni.
2. Učitaj firmware rampi ([8.5](#85-esp32-rampi)), serijski `open e`, pa `close e`.
3. Namjesti ruku na stup: zatvorena stoji ravno preko trake, otvorena je okrenuta uz otok. Ako kut ne odgovara,
   promijeni `closedAngle` / `openAngle` u `rampe/firmware/include/config.h` i ponovno učitaj.

**Uspjeh:** ruka se glatko otvara i zatvara, ESP32 se pritom ne resetira.

### H6. Obje rampe: IR, LED, tipke, sigurnosni testovi

1. Drugi servo na GPIO14. IR senzori FC-51 na GPIO34 / GPIO35, **napajani s 3,3 V** (pin 3V3 ESP32, ne 5 V).
   LED-ice preko 220 Ω, tipke između GPIO i GND (pinovi u [shemi](../maketa/shema-spajanja.md#čvor-rampi-esp32-2-esp32-gates)).
2. Postavi IR na crtu rampe s druge strane trake, na visini branika. Serijski `status`: `present=1` samo kad je autić
   na crti – **ruka rampe ga ne smije aktivirati**. Osjetljivost se podešava potenciometrom na FC-51.
3. Tipka: kratko = otvori, drži 3 s = RESET.
4. Provedi [sigurnosne testove rampi](../testiranje/sigurnosni-testovi-rampi.md) (rampa se ne zatvara na autić,
   sama se zatvara, ERROR nakon 3 sigurnosna otvaranja …).

**Uspjeh:** svi sigurnosni testovi prolaze, rezultati u zapisniku.

### H7. Rampe na MQTT-u (I3)

1. `secrets.h` s Wi-Fi-jem i `MQTT_HOST`, ponovno učitaj firmware; monitor: zelene `garage/gate/entrance/state`.
2. Naredba s laptopa (bez edge servisa):
   ```bash
   python -m garage_contract.monitor --pub garage/gate/entrance/command '{"requestId":"t1","command":"OPEN"}'
   ```
   Na Windowsu ovu naredbu pokreni u *Git Bashu* (dolazi s gitom) – PowerShell iz nje miče navodnike.
   S pokrenutim edge servisom isto radi `python -m edge_service manual open --gate entrance`.

**Uspjeh:** stanja `OPENING → OPEN → CLOSING → CLOSED`, potvrda s istim `requestId` za manje od 1 s.

### H8. Kamera, detekcija i OCR (I4, I5)

Prvo na laptopu (vidiš sliku), tek onda na Piju.

1. Isprintaj pločice: `python alpr/tools/generate_plates.py --out tablice` → PDF na **100 %**, mat papir; ravnalom
   provjeri kontrolnu crtu od 50 mm. Zalijepi ih u držače na autićima.
2. **Fokus (prvi tjedan, rizik R-02):** kamera na 20, 25 i 30 cm od pločice; jeftine kamere s fiksnim fokusom su
   mutne ispod ~30 cm. Ako je mutno: veća udaljenost ili kamera s autofokusom.
3. Snimanje treba OpenCV s prozorima (jednom):
   ```bash
   pip uninstall -y opencv-python-headless && pip install -e "alpr[gui]"
   python alpr/tools/capture_dataset.py --out alpr/dataset/real/v1 --plate ZG1234AB --lighting svijetlo --angle 0 --distance blizu
   ```
   RAZMAK = spremi sliku, `q` = izlaz. Snimi prvih 10 slika s kamerom na stvarnom položaju.
4. Detekcija i čitanje:
   ```bash
   python alpr/tools/detect_image.py alpr/dataset/real/v1/<slika>.jpg --out alpr/rezultati/probe
   python -m edge_service read alpr/dataset/real/v1/*.jpg
   ```
5. Kasnije (Sven, Lukas): ≥ 100 slika, `label_tool.py`, `evaluate_detection.py`, `edge/tools/evaluate_ocr.py`.

**Uspjeh:** pločica uokvirena, izrez ravan i čitljiv, registracija točna s pouzdanošću ≥ 0,85.
Za KT4: detekcija ≥ 90 % i **0 pogrešno prihvaćenih** čitanja.

### H9. Cijeli ulaz na edge računalu (I6–I8)

1. Pi pokrenut s kamerom ([8.2](#82-raspberry-pi-edge-računalo)), oba ESP32 spojena na Pi kao broker.
2. Autić dođe na ulaz i stane na graničnik.
3. Prati monitor: `gate/entrance/state` (vozilo prisutno) → `alpr/entrance/event` (registracija, pouzdanost) →
   `access/decision GRANTED` → `gate/entrance/command OPEN` → rampa se otvara.
4. Sesija u bazi:
   ```bash
   dc exec edge parking-sessions --db /data/garage.db list --active
   ```

**Uspjeh (TC-I01):** od zaustavljanja do otvaranja manje od 3 s, sesija `ACTIVE` s vremenom ulaska;
rampa se otvara **samo** nakon `GRANTED`.

### H10. Izlaz i ThingsBoard (I9, I10)

1. Autić s P03 vozi na izlaz. Očekuješ `SESSION_CLOSED` s trajanjem i cijenom, rampa se otvara.
2. Na dashboardima: odluke, sesije i alarmi; na analitičkom dashboardu ulazak i trajanje.
3. Gumbi: „Otvori ulaz“ i „Ručno odobri ulaz“ (prekrij pločicu → `MANUAL_REQUIRED` → gumb → `GRANTED`).

**Uspjeh:** cijeli demo scenarij (koraci 1–13) prolazi bez zastoja.

### H11. Testovi otpornosti i proba demonstracije

Iz [testnog plana](../testiranje/testni-plan.md), na maketi:

| test | kako | očekivano |
|---|---|---|
| TC-I08 ThingsBoard ne radi | na laptopu `docker compose stop thingsboard`, autić uđe, zatim `start` | ulaz radi; događaji se pojave s izvornim vremenom |
| TC-I09 restart ESP32 | tipka EN/RST na oba ESP32 | za manje od 30 s sve radi |
| TC-I10 restart Pija | `sudo reboot` | servisi se sami pokrenu, aktivne sesije ostaju |
| TC-I14 nema Wi-Fi-ja | ugasi router 1 min | tipka na rampi radi; nakon povratka stanja točna |
| TC-S04 senzor ne radi | odspoji ECHO jednog senzora | mjesto `UNKNOWN`, ne broji se kao slobodno, alarm |
| TC-I04 puna garaža | autić na svako mjesto, sedmi na ulaz | `DENIED GARAGE_FULL` |

Zatim dvije generalne probe po [demo-scenariju](../../PREZENTACIJA/demo-scenarij.md) i snimanje rezervnog videa
(do KT6, 17.1.2027.).

---

## 10. Kad nešto ne radi

| simptom | najčešći uzrok | što napraviti |
|---|---|---|
| upload na ESP32 ne uspijeva / nema porta | kabel samo za punjenje, nema drivera | drugi kabel; driver CP210x ili CH340 (piše na čipu do USB-a); drži BOOT tijekom `Connecting...` |
| ESP32 stalno `WiFi: connecting...` | 5 GHz mreža, kriva lozinka, mreža s web prijavom | 2,4 GHz mreža routera makete, provjeri `secrets.h` |
| `MQTT: failed, rc=-2` | kriva adresa brokera, broker ne radi ili prima samo lokalne veze, vatrozid | provjeri `MQTT_HOST`; na laptopu `mosquitto -c lan.conf -v`; dopusti port 1883 |
| `MQTT: failed, rc=5` | broker traži lozinku | `MQTT_USER` / `MQTT_PASSWORD` u `secrets.h` |
| monitor ne prikazuje ništa | monitor gleda drugi broker | `python -m garage_contract.monitor --host <adresa brokera>` |
| crvene poruke u monitoru | netko šalje poruku koja ne odgovara ugovoru | monitor ispiše temu i razlog; ispravlja vlasnik tog dijela |
| ESP32 se resetira kad se servo pomakne | pad napona | servo s adaptera, zajednička masa, kondenzator 1000 µF uz servo |
| senzor uvijek `TIMEOUT` / `UNKNOWN` | ECHO nije spojen kroz djelitelj na pravi pin, senzor bez 5 V | provjeri pin u [shemi](../maketa/shema-spajanja.md), napon djelitelja, serijski `cal` |
| mjesto treperi | senzor vidi zid ili nije okomit, pragovi preblizu | montaža, ponovno `kalibracija.py` |
| IR javlja vozilo bez autića | vidi ruku rampe ili pod, previsoka osjetljivost | potenciometar na FC-51, položaj senzora |
| rampa se ne otvara iako je registracija pročitana | odluka nije `GRANTED` | u monitoru pogledaj `access/decision`: razlog (`GARAGE_FULL`, `ALREADY_INSIDE`, `RETRY`, `MANUAL_REQUIRED`) |
| uvijek `RETRY` / `MANUAL_REQUIRED` | mutna slika, odsjaj, loše svjetlo, pločica nije na 100 % | fokus i udaljenost kamere, mat papir, difuzor, graničnik kotača |
| na Piju `edge` se ruši odmah nakon starta | `edge.yaml` ne postoji (Docker napravi mapu) ili kamera nije `/dev/video0` | `ls ~/IoTGarage/SOFTWARE/edge/edge.yaml`, `ls /dev/video*`; `dc logs edge` |
| ThingsBoard ne dobiva ništa s Pija | kriva `TB_HOST` adresa, vatrozid laptopa, token se ne slaže | `.env` na Piju, port 1884 na laptopu, isti token u `provision.py --token` i `TB_GATEWAY_TOKEN`; `dc logs tb-bridge` |
| gumbi na dashboardu ne rade ništa | bridge ili edge servis ne rade | `dc ps` na Piju |
| `pytest` ili `simulacija.py` ne rade na laptopu | `.venv` nije aktiviran ili ne radiš iz mape `SOFTWARE` | `cd IoTGarage/SOFTWARE`, aktiviraj `.venv` |
| `tesseract` / `mosquitto` „not recognized“ (Windows) | nisu u PATH-u | dodaj mape u PATH, otvori novi terminal |

Ako ništa od toga: pokreni isti korak u simulaciji (simulator umjesto hardvera). Ako u simulaciji radi, problem je u
hardveru ili mreži; ako ne radi ni tamo, problem je u kodu – javi vlasniku tog dijela.

---

## 11. Dan demonstracije

Sve je u [demo-scenarij.md](../../PREZENTACIJA/demo-scenarij.md). Najkraće:

- **Uloge:** ti pričaš, operater upravlja dashboardom, vozač pomiče autiće, tehničar drži terminal s monitorom i plan B.
- **Dan prije:** kontrolna lista iz scenarija; fiktivnu povijest obriši (`python thingsboard/tools/seed_history.py --clear`);
  `PRICING_PROFILE=demo` (u `.env` na Piju) da se vidi cijena.
- **Glavni scenarij:** 13 koraka – ulaz, parkiranje, sesija u bazi, analitika, izlaz s cijenom.
- **Kontrolirana greška:** nečitljiva pločica → ručno odobrenje i/ili ThingsBoard ugašen, a garaža i dalje radi.
- **Plan B:** rezervni video (≤ 4 min) i `python integracija/simulacija.py --broker --tb --interactive`.
- Na kraju pokaži **šest kriterija uspjeha** iz scenarija.
