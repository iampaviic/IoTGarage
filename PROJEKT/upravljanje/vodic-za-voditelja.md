# Vodič za voditelja

Za Patrika: stanje projekta, kako sustav radi, pojmovi i postavljanje cijelog sustava kad je hardver spojen.
Poglavlja 1–4 pročitaj prvo, poglavlje 5 napravi jednom na svom laptopu, a 6–8 su za rad s hardverom.
Dokument se ne kopira na GitLab ([.gitlab-tjedni](../../.gitlab-tjedni/README.md)) jer opisuje i stanje GitHuba.

## Sadržaj

1. [Stanje u jednoj minuti](#1-stanje-u-jednoj-minuti)
2. [Kako sustav radi](#2-kako-sustav-radi)
3. [Rječnik](#3-rječnik)
4. [Tim, rokovi i odluke](#4-tim-rokovi-i-odluke)
5. [Priprema laptopa](#5-priprema-laptopa)
6. [Postavljanje cijelog sustava s hardverom](#6-postavljanje-cijelog-sustava-s-hardverom)
7. [Integracija hardvera](#7-integracija-hardvera)
8. [Kad nešto ne radi](#8-kad-nešto-ne-radi)

## 1. Stanje u jednoj minuti

| dio | stanje |
|---|---|
| plan projekta (gantogram, kontrolne točke) | ✅ [PROJEKT/plan-projekta](../plan-projekta) |
| arhitektura i komunikacijski ugovor | ✅ odabrana je [varijanta B](../sustav/varijanta-b.md) (sve u ThingsBoardu, D-012), sa sekvencijskim dijagramima; varijanta A ostaje kao rezerva |
| ThingsBoard: rule chain (odluke, sesije, naplata, alarmi), uređaji, 2 dashboarda | ✅ isproban na ThingsBoard CE 4.2.1 |
| ALPR i OCR kao uređaj ThingsBoarda | ✅ napisan, isproban sa sintetskim slikama |
| simulacija cijelog sustava s ThingsBoardom | ✅ `simulacija_b.py`, scenarij od 8 koraka prolazi |
| automatski testovi (Python i oba firmwarea, u CI-u) | ✅ prolaze |
| firmware za oba ESP32 (ThingsBoard API) | ✅ preveden, ⬜ nije isproban na hardveru |
| ALPR na stvarnim fotografijama makete | ⬜ zasad samo sintetske slike |
| maketa | ⬜ nacrt 1:1, 3D dijelovi i 3D sklop postoje, fizička maketa ne |
| mobilna aplikacija (Leo) | ⬜ nije započeta, postoje samo upute |
| završna dokumentacija | ✅ kostur i 2 poglavlja, ⬜ ostalo |

Sav softver postoji i radi u simulaciji s pravim ThingsBoardom. Preostaju hardver, maketa, mjerenja na stvarnim fotografijama, mobilna
aplikacija i dokumentacija.

Na GitHubu (`iampaviic/iotgarage`) grana `main` još ima staru strukturu s mapama `osoba-1-voditelj` …
`osoba-8-baza-testovi`. Sve opisano ovdje je na grani `claude/gitlab-struktura`, pa je tvoj prvi zadatak spojiti
je u `main`: GitHub → *Pull requests* → *New pull request*, base `main`, compare `claude/gitlab-struktura`; kad CI
prođe, *Merge pull request*. Zatim svi rade `git checkout main && git pull`. Tko ima nekomitane promjene u starim
`osoba-N` mapama, prenosi ih u nove mape iz tablice [Tim](../../README.md#tim).

## 2. Kako sustav radi

Priča jednog autića:

1. Autić dođe do ulazne rampe i stane na graničnik. IR senzor na crti rampe ga vidi.
2. ESP32 rampi javi ThingsBoardu "vozilo je na ulazu" preko Wi-Fi-ja (MQTT poruka `vehicleArrived`).
3. Rule chain ThingsBoarda traži od ALPR servisa (laptop ili Raspberry Pi uz kameru) da pročita registraciju.
   ALPR uzme do 3 slike s USB kamere, pronađe pločicu i pročita znakove (OCR).
4. Ako je pouzdanost dovoljna, ima slobodnih mjesta i vozilo već nije unutra, rule chain zapiše `GRANTED`,
   otvori parkirnu sesiju (atribut asseta Garage) i pošalje rampi naredbu "otvori" (RPC).
5. ESP32 rampi okrene servo i upali zelenu LED. Kad autić prođe, sam zatvori rampu nakon 2 s.
6. Autić parkira na P03. Ultrazvučni senzor iznad mjesta to vidi, ESP32 senzora javi "P03 zauzeto" i LED na mjestu
   postane crvena.
7. Izlaz ide isto: kamera na izlazu, pronađena sesija, trajanje i cijena, rampa se otvara.
8. Dashboard u stvarnom vremenu pokazuje mjesta, rampe, odluke i alarme, a gumbi služe za ručno upravljanje.
   Mobilna aplikacija čita analitiku iz ThingsBoarda.

Glavno pravilo arhitekture (varijanta B, odluka D-012) je da sve odluke donosi ThingsBoard. Bez ThingsBoarda ili
mreže rampe se otvaraju samo tipkom (i dalje se same zatvaraju i ne spuštaju se na vozilo). Detalji i sekvencijski
dijagrami su u [varijanta-b.md](../sustav/varijanta-b.md).

```
 MAKETA                                   LAPTOP
 ESP32 senzora (6 mjesta) ──MQTT──┐       ┌ ThingsBoard (Docker) ──────────────────┐
 ESP32 rampi (2 rampe)  ───MQTT───┼─────► │ rule chain: odluke, sesije, alarmi     │ ── REST ──► mobilna aplikacija
 USB kamera ── ALPR + OCR ─MQTT───┘       └ dashboardi                             ┘
              (laptop ili Pi)
```

U sustavu su dva ESP32 (mikrokontroleri na maketi) i laptop (ThingsBoard, ALPR, dashboard na demonstraciji);
ALPR po potrebi radi na Raspberry Piju uz kameru. Svi su spojeni na isti Wi-Fi router.

## 3. Rječnik

| pojam | značenje |
|---|---|
| MQTT | jednostavan protokol za poruke: uređaj pošalje poruku na *temu*, a dobiju je svi koji su *pretplaćeni* na tu temu |
| broker | "poštanski ured" za MQTT poruke; kod nas je to ugrađeni MQTT ThingsBoarda, port 1883 |
| tema (*topic*) | adresa poruke, npr. `v1/gateway/telemetry` |
| *access token* | "lozinka" uređaja u ThingsBoardu; ESP32 ga šalje kao MQTT korisničko ime |
| gateway uređaj | uređaj koji jednom vezom šalje podatke za više uređaja (ESP32 senzora za 6 mjesta) |
| rule chain | lanac pravila u ThingsBoardu koji obrađuje svaku poruku; kod nas donosi odluke, vodi sesije i alarme |
| TBEL | jezik skripti u rule chainu (sličan JavaScriptu); naše skripte su u `SOFTWARE/thingsboard/rulechain/scripts` |
| komunikacijski ugovor | popis tema, uređaja, ključeva i RPC metoda ([komunikacijski-ugovor.md](../sustav/komunikacijski-ugovor.md)) |
| ESP32 | mali mikrokontroler s Wi-Fi-jem; imamo dva, za senzore mjesta i za rampe |
| firmware | program na ESP32 (C++); prevodi se i učitava s PlatformIO u VS Codeu |
| edge računalo | računalo uz kameru na kojem radi ALPR (laptop ili Raspberry Pi; Jetson Nano je rezerva) |
| ALPR | automatsko prepoznavanje registracija: *detekcija* (gdje je pločica) i *OCR* (što na njoj piše) |
| OCR | čitanje znakova sa slike; imamo dva motora (Tesseract i usporedba s predlošcima) koji glasaju |
| pouzdanost (*confidence*) | broj 0–1 koji kaže koliko se čitanja slažu; pragovi za odluku su u [ugovoru](../sustav/komunikacijski-ugovor.md#pravila-odlučivanja) |
| odluka | `GRANTED`, `DENIED` ili `MANUAL_REQUIRED` (operater odlučuje), s razlogom |
| parkirna sesija | zapis jednog boravka: ulaz, izlaz, trajanje, cijena |
| ThingsBoard | IoT platforma s dashboardima, alarmima i poviješću (*digitalni blizanac* garaže); kod nas i "mozak" sustava |
| asset Garage | entitet u ThingsBoardu za cijelu garažu: postavke, sesije, sažetak, odluke |
| RPC | naredba iz ThingsBoarda prema uređaju s odgovorom; tako rade gumbi na dashboardu i naredbe rampi |
| simulator | program koji se prema ThingsBoardu ponaša kao hardver, pa nitko ne čeka tuđi hardver |
| heartbeat, Disconnect | poruka "živ sam" svakih 30 s; kad ESP32 nestane, ThingsBoard to vidi (Disconnect Event) i digne alarm |
| Docker, docker compose | pokreće programe u kontejnerima, istim naredbama na svakom računalu |
| venv | izolirano Python okruženje projekta (mapa `.venv`) |
| CI | GitHub nakon svakog pusha sam pokrene sve testove i prevede firmware |
| grana, PR | grana je odvojena linija rada; *pull request* je prijedlog spajanja grane u `main` |
| KT | kontrolna točka iz plana projekta |

## 4. Tim, rokovi i odluke

Tko radi što piše u tablici [Tim](../../README.md#tim), a zadaci po osobi i kontrolne točke u
[plan-rada.md](plan-rada.md). Sljedeća kontrolna točka je KT2 (10.11.2026.): jedan senzor, jedan servo, ThingsBoard
i ALPR na stvarnoj fotografiji te nacrt makete. Od 23.11. do 4.12. su međuispiti, a integraciju s hardverom treba
završiti prije blagdana (rizik R-16). Ako netko ispadne, mijenjaju se Toma i Lovro, Luka i Lukas, Sven i Lukas te Anja i
Leo (rizik R-11).

### Odluke koje čekaju tebe i tim

| odluka | prijedlog | gdje |
|---|---|---|
| gdje radi ALPR | na laptopu s ThingsBoardom (najjednostavnije) ili na Raspberry Piju uz kameru (D-004) | [odluke.md](odluke.md) |
| jedna ili dvije kamere | počnite s jednom koja se premješta, druga (~20 €) ako budžet dopusti (D-007) | [odluke.md](odluke.md), [nacrt-makete.md](../maketa/nacrt-makete.md#3-kamera) |
| ~~varijanta arhitekture A ili B~~ | ✅ odlučeno: B (D-012) | [varijanta-b.md](../sustav/varijanta-b.md) |
| tko smije ući | `policy: open` (svaka valjana pločica) ili `allowlist` (samo s popisa) | atributi `policy`, `allowlist` asseta Garage |
| naplata | prijedlog D-009 | [model-podataka.md](../sustav/model-podataka.md#pravilo-naplate) |
| mjerilo autića | 1:24 (baza 688 × 821 mm) | [nacrt-makete.md](../maketa/nacrt-makete.md) |
| vlastiti Wi-Fi router za maketu | da, jer fakultetski Wi-Fi često blokira ESP32 (R-07, najveći rizik) | [rizici.md](rizici.md) |

Odluku upiši u [odluke.md](odluke.md) (kontekst → odluka → posljedice) i makni oznaku [PRIJEDLOG].

### Jednom, na početku

- [ ] spojiti `claude/gitlab-struktura` u `main` ([poglavlje 1](#1-stanje-u-jednoj-minuti))
- [ ] zaštititi `main`: GitHub → *Settings* → *Branches* → *Add rule*, obavezan pull request i zeleni CI
- [ ] ploča zadataka u GitHub *Projects*, jedna kartica po zadatku iz [plan-rada.md](plan-rada.md)
- [ ] termin tjednog sastanka
- [ ] klon službenog GitLab repozitorija za tjedne commitove ([.gitlab-tjedni](../../.gitlab-tjedni/README.md))

### Svaki tjedan

1. Sastanak po [predlošku](sastanci/predlozak.md): status po osobi, demo zadnjeg koraka integracije, odluke,
   rizici, zadaci za idući tjedan. Zapisnik ide u `sastanci/`.
2. Jedan korak iz [plana integracije](plan-integracije.md) s pravim hardverom. Rezultat upisuje Lovro u
   [testni zapisnik](../testiranje/testni-zapisnik.md).
3. Pregled PR-ova: svaki PR pregledava barem jedna osoba, a CI mora biti zelen.
4. Tjedni commit na GitLab prema [.gitlab-tjedni](../../.gitlab-tjedni/README.md#svaki-tjedan), iz grane `main`.
   Alat ne dopušta povratak na raniji tjedan, pa ako tjedni 1 i 2 još nisu predani, pokreni ih redom.

## 5. Priprema laptopa

Prije hardvera na svom laptopu pokreni cijeli sustav u simulaciji i ThingsBoard, da znaš kako sve treba izgledati.
Koraci su u [INSTALL.md](../../SOFTWARE/INSTALL.md), poglavlja 1–4 (Python, ThingsBoard, simulacija). Za GitHub
još vrijedi:

- Repozitorij je privatan, pa git traži prijavu: korisničko ime s GitHuba i *personal access token* umjesto lozinke
  (GitHub → *Settings* → *Developer settings* → *Personal access tokens*).
- Dok grana nije spojena u `main`, nakon kloniranja napravi `git checkout claude/gitlab-struktura`.

Uspjeh: `pytest` završi s `passed` bez grešaka, `simulacija_b.py` na kraju ispiše `scenarij prošao`, a na
dashboardu "Garaža – nadzor" mjesta mijenjaju boju i pojavljuju se odluke dok simulacija radi.

## 6. Postavljanje cijelog sustava s hardverom

Ovo je postupak kad je hardver spojen i ožičen. Kako se do toga dolazi dio po dio, piše u
[planu integracije](plan-integracije.md).

### 6.1 Mreža i adrese

Sve ide na vlastiti Wi-Fi router makete. ESP32 radi samo na 2,4 GHz, pa na routeru uključi 2,4 GHz mrežu i ne
koristi mrežu s prijavom preko web stranice.

U postavkama routera (DHCP → *address reservation*) laptopu daj stalnu adresu. Adresa iz primjera je već upisana u
predloške:

| uređaj | adresa | gdje se upisuje |
|---|---|---|
| laptop (ThingsBoard, ALPR) | `192.168.1.20` | `TB_HOST` u `secrets.h` oba ESP32 (i `thingsboard.host` u `edge.yaml` ako ALPR radi na Piju) |
| Raspberry Pi (samo ako ALPR radi na njemu) | `192.168.1.10` | |
| ESP32 senzora, ESP32 rampi | bilo koja (DHCP) | |

Ako router dijeli druge adrese (npr. `192.168.0.x`), koristi njih, ali iste u svim datotekama.

### 6.2 Laptop: ThingsBoard

Na laptopu koji ide na demonstraciju pokreni ThingsBoard kao u
[INSTALL.md §3](../../SOFTWARE/INSTALL.md#3-thingsboard-laptop-ili-server-s--4-gb-ram), a zatim:

- da tlocrt na dashboardu odgovara maketi: `python thingsboard/provision/provision.py --demo-pricing --positions maketa/nacrt/spots.json`;
- za demonstraciju promijeni lozinku tenanta i postavi tajne tokene:
  `TB_TOKEN_SPOTS=… TB_TOKEN_GATES=… TB_TOKEN_ALPR=… python thingsboard/provision/provision.py --password <nova>`;
  iste tokene upiši u `secrets.h` oba ESP32 i u `edge/edge.yaml`;
- ESP32 se spajaju na laptop na port 1883; ako Windows pita za vatrozid, dopusti Docker na privatnoj mreži.

Uspjeh: rule chain „Garaža (varijanta B)“ je *root*, a dashboard „Garaža – nadzor“ se otvara.

### 6.3 ALPR servis

Najjednostavnije na istom laptopu, s kamerom na USB-u laptopa:

```bash
cp edge/edge.example.yaml edge/edge.yaml      # kamera "0", sekcija thingsboard: host localhost, token alpr-service
python -m edge_service --config edge/edge.yaml tb-alpr
```

Ako kamera mora biti uz maketu daleko od laptopa, ALPR radi na Raspberry Piju:

1. U [Raspberry Pi Imageru](https://www.raspberrypi.com/software/) odaberi *Raspberry Pi OS Lite (64-bit)*, u
   *Edit settings* hostname `garaza-edge`, korisnika `pi`, Wi-Fi routera makete i SSH. S laptopa
   `ssh pi@garaza-edge.local`.
2. Docker: `curl -fsSL https://get.docker.com | sh`, `sudo usermod -aG docker $USER`, odjava i ponovna prijava.
3. Kod i postavke:
   ```bash
   git clone https://github.com/iampaviic/iotgarage.git ~/IoTGarage && cd ~/IoTGarage/SOFTWARE
   cp edge/edge.example.yaml edge/edge.yaml && cp edge/deploy/.env.example edge/deploy/.env
   nano edge/deploy/.env                     # TB_HOST = adresa laptopa, TB_TOKEN_ALPR = token alpr-service
   cd edge/deploy
   docker compose -f docker-compose.alpr.yml -f docker-compose.alpr-camera.yml up -d --build   # prvi put 10–30 min
   docker compose -f docker-compose.alpr.yml logs -f alpr
   ```
   `edge.yaml` mora postojati prije pokretanja, inače Docker umjesto nje napravi praznu mapu. Pi gasi sa
   `sudo shutdown -h now`.

Uspjeh: u ThingsBoardu je `alpr-service` *Active*, a u zapisima `connected to ThingsBoard`.

### 6.4 ESP32 senzora

1. VS Code → *File* → *Open Folder* → `SOFTWARE/senzori/firmware`. PlatformIO sam prepozna projekt.
2. Kopiraj `include/secrets.example.h` u `include/secrets.h` i upiši `WIFI_SSID`, `WIFI_PASSWORD`, `TB_HOST`
   (adresa laptopa) i `TB_TOKEN` (token `esp32-spots`). `secrets.h` se nikad ne komita.
3. Spoji ESP32 USB kabelom koji prenosi podatke, ne samo kabelom za punjenje.
4. *Upload* (strelica → u donjoj traci PlatformIO-a) ili `pio run -t upload`. Ako zapne na `Connecting....___`,
   drži tipku BOOT na pločici dok upload ne krene.
5. *Serial Monitor* (ikona utikača) ili `pio device monitor` (115200). Očekuješ:
   ```
   IoT Garage spot sensors 0.2.0, 6 spots
   WiFi: connecting...
   ThingsBoard: connecting to 192.168.1.20:1883
   ThingsBoard: connected
   ```
   Naredba `status` mora javiti `WiFi=1 ThingsBoard=1`.
6. U ThingsBoardu `esp32-spots` je *Active*, a `ParkingSpot-01…06` imaju telemetriju; na dashboardu mjesta imaju boju.

Pinovi i pragovi su u `include/config.h`. Pragovi se ondje upišu nakon kalibracije (korak H3 plana integracije).
Što čvor šalje i kada: sekvencijski dijagrami u [varijanta-b.md](../sustav/varijanta-b.md#čvor-senzora-mjesta-esp32).

### 6.5 ESP32 rampi

Isto kao 6.4, u mapi `SOFTWARE/rampe/firmware`, s tokenom `esp32-gates`. U serijskom monitoru očekuješ
`IoT Garage gates 0.2.0` i `ThingsBoard: connected`. Naredbe su `open e`, `close e`, `reset e` i `status` (`x` umjesto
`e` je izlazna rampa). Kutovi serva (`closedAngle`, `openAngle`) su u `include/config.h`.

### 6.6 Kamera

1. Kamera je na mostu iznad trake, 200 mm iza crte rampe, s objektivom ~130 mm iznad poda. Gleda koso prema dolje na
   pločicu autića koji stoji na graničniku ([nacrt-makete.md](../maketa/nacrt-makete.md#3-kamera)).
2. Na Linuxu `ls /dev/video*` mora pokazati `/dev/video0`; na Windowsu je prva kamera `"0"` u `edge.yaml`.
3. Druga kamera je obično `"1"` (Windows) ili `/dev/video2` (Linux). U `edge.yaml` za izlaz postavi `camera`, a na
   Piju je dodaj i u `docker-compose.alpr-camera.yml` (`devices`).
4. Svjetlo: LED traka s difuzorom iznad zone kamere i pločice na mat papiru, bez odsjaja.

### 6.7 Svaki put kad pališ sustav

1. Upali router i laptop, pokreni `docker compose -f thingsboard/docker-compose.yml up -d` (iz mape `SOFTWARE`) i
   otvori dashboard.
2. Pokreni ALPR (`tb-alpr` na laptopu; na Piju se pokreće sam).
3. Uključi maketu sklopkom 5 V.
4. Nakon ~30 s sva mjesta imaju boju, rampe su zatvorene, a broj slobodnih mjesta je točan.
5. Proba: autić na ulaz, rampa se otvara, parkiraj, mjesto postane crveno.

Gasi se obrnutim redom. Upute za operatera dashboarda su u
[03-korisnicke-upute.md](../dokumentacija/03-korisnicke-upute.md), a za dan demonstracije u
[demo-scenarij.md](../../PREZENTACIJA/demo-scenarij.md).

## 7. Integracija hardvera

Koraci H0–H11, od napajanja bez elektronike do probe demonstracije, s naredbama, kriterijima uspjeha, odgovornima i
rokovima su u [plan-integracije.md](plan-integracije.md). Svaki tjedan s timom napravi bar jedan korak.

## 8. Kad nešto ne radi

| simptom | najčešći uzrok | što napraviti |
|---|---|---|
| upload na ESP32 ne uspijeva / nema porta | kabel samo za punjenje, nema drivera | drugi kabel; driver CP210x ili CH340 (piše na čipu do USB-a); drži BOOT tijekom `Connecting...` |
| ESP32 stalno `WiFi: connecting...` | 5 GHz mreža, kriva lozinka, mreža s web prijavom | 2,4 GHz mreža routera makete, provjeri `secrets.h` |
| `ThingsBoard: failed, rc=-2` | kriva adresa laptopa, ThingsBoard ne radi, vatrozid | provjeri `TB_HOST`; `docker compose ps`; dopusti port 1883 |
| `ThingsBoard: failed, rc=4` ili `rc=5` | pogrešan *access token* | `TB_TOKEN` u `secrets.h` = token koji je ispisao `provision.py` |
| uređaj je *Active*, a nema telemetrije | poruka nije u očekivanom obliku ili ide na krivi uređaj | *Latest telemetry* uređaja i gatewaya; *Debug* na prvom čvoru rule chaina, kartica *Events* |
| ESP32 se resetira kad se servo pomakne | pad napona | servo s adaptera, zajednička masa, kondenzator 1000 µF uz servo |
| senzor uvijek `TIMEOUT` / `UNKNOWN` | ECHO nije spojen kroz djelitelj na pravi pin, senzor bez 5 V | provjeri pin u [shemi](../maketa/shema-spajanja.md), napon djelitelja, serijski `cal` |
| mjesto treperi | senzor vidi zid ili nije okomit, pragovi preblizu | montaža, ponovno `kalibracija.py` |
| IR javlja vozilo bez autića | vidi ruku rampe ili pod, previsoka osjetljivost | potenciometar na FC-51, položaj senzora |
| rampa se ne otvara iako je registracija pročitana | odluka nije `GRANTED` | asset Garage, *Latest telemetry*: `decision`, `decisionReason` (`GARAGE_FULL`, `ALREADY_INSIDE`, `LOW_CONFIDENCE`, `TIMEOUT` …) |
| uvijek `MANUAL_REQUIRED` s razlogom `TIMEOUT` | ALPR servis ne radi ili nije spojen | `alpr-service` mora biti *Active*; zapisi `tb-alpr` |
| uvijek `MANUAL_REQUIRED` s `LOW_CONFIDENCE` / `NO_PLATE` | mutna slika, odsjaj, loše svjetlo, pločica nije ispisana na 100 % | fokus i udaljenost kamere, mat papir, difuzor, graničnik kotača |
| ništa se ne događa kad autić stane na rampu | nema `vehicleArrived` (IR) ili rule chain nije *root* | `EntranceGate` telemetrija; ponovno `provision.py` |
| na Piju se `alpr` ruši odmah nakon starta | `edge.yaml` ne postoji (Docker napravi mapu) ili kamera nije `/dev/video0` | `ls ~/IoTGarage/SOFTWARE/edge/edge.yaml`, `ls /dev/video*`, `docker compose -f docker-compose.alpr.yml logs alpr` |
| gumbi na dashboardu javljaju grešku | rampa nije spojena ili ne odgovara u 5 s | `esp32-gates` *Active*; alarm „Rampa ne potvrđuje naredbe“ |
| `pytest` ili `simulacija_b.py` ne rade na laptopu | `.venv` nije aktiviran, ne radiš iz mape `SOFTWARE` ili ThingsBoard nije pripremljen | `cd IoTGarage/SOFTWARE`, aktiviraj `.venv`, `provision.py` |
| `tesseract` "not recognized" (Windows) | nije u PATH-u | dodaj mapu u PATH, otvori novi terminal |

Ako ništa od toga ne pomogne, pokreni isti korak sa simulatorom umjesto hardvera. Ako sa simulatorom radi, problem
je u hardveru ili mreži. Ako ne radi ni tamo, problem je u kodu i javi se vlasniku tog dijela.
