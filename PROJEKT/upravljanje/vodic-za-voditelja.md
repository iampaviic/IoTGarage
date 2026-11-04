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
| arhitektura i komunikacijski ugovor | ✅ varijanta A je napisana u kodu; [varijanta B](../sustav/varijanta-b.md) (sve u ThingsBoardu) je samo opisana |
| softver na edge računalu: ALPR, OCR, kontrola pristupa, baza sesija | ✅ napisan i testiran u simulaciji |
| ThingsBoard: uređaji, 2 dashboarda, 7 alarma, bridge | ✅ isproban na ThingsBoard CE 4.2.1 |
| simulacija cijelog sustava na jednom laptopu | ✅ `simulacija.py`, 0 poruka koje krše ugovor |
| automatski testovi (Python i oba firmwarea, u CI-u) | ✅ prolaze |
| firmware za oba ESP32 | ✅ preveden, ⬜ nije isproban na hardveru |
| ALPR na stvarnim fotografijama makete | ⬜ zasad samo sintetske slike |
| maketa | ⬜ nacrt 1:1, 3D dijelovi i 3D sklop postoje, fizička maketa ne |
| mobilna aplikacija (Leo) | ⬜ nije započeta, postoje samo upute |
| završna dokumentacija | ✅ kostur i 2 poglavlja, ⬜ ostalo |

Sav softver postoji i radi u simulaciji. Preostaju hardver, maketa, mjerenja na stvarnim fotografijama, mobilna
aplikacija i dokumentacija.

Na GitHubu (`iampaviic/iotgarage`) grana `main` još ima staru strukturu s mapama `osoba-1-voditelj` …
`osoba-8-baza-testovi`. Sve opisano ovdje je na grani `claude/gitlab-struktura`, pa je tvoj prvi zadatak spojiti
je u `main`: GitHub → *Pull requests* → *New pull request*, base `main`, compare `claude/gitlab-struktura`; kad CI
prođe, *Merge pull request*. Zatim svi rade `git checkout main && git pull`. Tko ima nekomitane promjene u starim
`osoba-N` mapama, prenosi ih u nove mape iz tablice [Tim](../../README.md#tim).

## 2. Kako sustav radi

Priča jednog autića:

1. Autić dođe do ulazne rampe i stane na graničnik. IR senzor na crti rampe ga vidi.
2. ESP32 rampi javi "vozilo je na ulazu" preko Wi-Fi-ja (MQTT poruka).
3. Na edge računalu (Raspberry Pi uz maketu) servis za kontrolu pristupa traži od ALPR-a da pročita registraciju.
   ALPR uzme do 3 slike s USB kamere, pronađe pločicu i pročita znakove (OCR).
4. Ako je pouzdanost dovoljna, ima slobodnih mjesta i vozilo već nije unutra, kontrola pristupa javi `GRANTED`,
   otvori parkirnu sesiju u bazi (SQLite) i pošalje rampi naredbu "otvori".
5. ESP32 rampi okrene servo i upali zelenu LED. Kad autić prođe, sam zatvori rampu nakon 2 s.
6. Autić parkira na P03. Ultrazvučni senzor iznad mjesta to vidi, ESP32 senzora javi "P03 zauzeto" i LED na mjestu
   postane crvena.
7. Izlaz ide isto: kamera na izlazu, pronađena sesija, trajanje i cijena, rampa se otvara.
8. Sve poruke idu i u ThingsBoard na laptopu: dashboard u stvarnom vremenu, povijest, alarmi i gumbi za ručno
   upravljanje. Mobilna aplikacija čita analitiku iz ThingsBoarda.

Glavno pravilo arhitekture (varijanta A) je da se odluka donosi lokalno na edge računalu. Ulaz i izlaz rade i kad
ThingsBoard ili internet ne rade, a ThingsBoard služi za nadzor i povijest. Detalji su u
[arhitektura.md](../sustav/arhitektura.md).

```
 MAKETA                         EDGE RAČUNALO (Raspberry Pi)              LAPTOP
 ESP32 senzora (6 mjesta) ─┐    ┌ MQTT broker (Mosquitto) ┐               ThingsBoard (Docker)
 ESP32 rampi (2 rampe)  ───┼──► │ ALPR + OCR              │ ── bridge ──►  dashboardi, alarmi
 USB kamera ───────────────┘    │ kontrola pristupa       │                     │
                                └ baza sesija (SQLite)    ┘               mobilna aplikacija
```

U sustavu su tri vrste računala: dva ESP32 (mikrokontroleri na maketi), jedan Raspberry Pi (edge računalo uz
maketu) i laptop (ThingsBoard, razvoj, dashboard na demonstraciji). Svi su spojeni na isti Wi-Fi router.

## 3. Rječnik

| pojam | značenje |
|---|---|
| MQTT | jednostavan protokol za poruke: uređaj pošalje poruku na *temu*, a dobiju je svi koji su *pretplaćeni* na tu temu |
| broker | "poštanski ured" za MQTT poruke; kod nas Mosquitto na Raspberry Piju, port 1883 |
| tema (*topic*) | adresa poruke, npr. `garage/parking/spot/P03/telemetry` |
| retained | broker pamti zadnju poruku teme i daje je svakom tko se spoji kasnije (koristimo za stanja) |
| komunikacijski ugovor | popis svih tema i oblika poruka ([komunikacijski-ugovor.md](../sustav/komunikacijski-ugovor.md)); monitor ugovora crveno označi svaku poruku koja ga krši |
| ESP32 | mali mikrokontroler s Wi-Fi-jem; imamo dva, za senzore mjesta i za rampe |
| firmware | program na ESP32 (C++); prevodi se i učitava s PlatformIO u VS Codeu |
| edge računalo | računalo uz maketu koje donosi odluke (Raspberry Pi; Jetson Nano je rezerva) |
| ALPR | automatsko prepoznavanje registracija: *detekcija* (gdje je pločica) i *OCR* (što na njoj piše) |
| OCR | čitanje znakova sa slike; imamo dva motora (Tesseract i usporedba s predlošcima) koji glasaju |
| pouzdanost (*confidence*) | broj 0–1 koji kaže koliko se čitanja slažu; pragovi za odluku su u [ugovoru](../sustav/komunikacijski-ugovor.md#pravila-odlučivanja) |
| kontrola pristupa (*access control*) | servis koji odlučuje: `GRANTED`, `DENIED`, `RETRY`, `MANUAL_REQUIRED` |
| parkirna sesija | zapis jednog boravka: ulaz, mjesto, izlaz, trajanje, cijena |
| ThingsBoard | IoT platforma s dashboardima, alarmima i poviješću (*digitalni blizanac* garaže) |
| bridge | program koji prosljeđuje poruke s brokera u ThingsBoard i čuva ih dok ThingsBoard ne radi |
| RPC | naredba iz ThingsBoarda prema uređaju; tako rade gumbi na dashboardu |
| simulator | program koji se na MQTT-u ponaša kao hardver, pa nitko ne čeka tuđi hardver |
| requestId | oznaka naredbe; potvrda nosi isti `requestId`, a ponovljena naredba se ne izvršava dvaput |
| Last Will, heartbeat | poruka "uređaj je offline" koju broker pošalje kad ESP32 nestane; poruka "živ sam" svakih 30 s |
| Docker, docker compose | pokreće programe u kontejnerima, istim naredbama na svakom računalu |
| venv | izolirano Python okruženje projekta (mapa `.venv`) |
| CI | GitHub nakon svakog pusha sam pokrene sve testove i prevede firmware |
| grana, PR | grana je odvojena linija rada; *pull request* je prijedlog spajanja grane u `main` |
| KT | kontrolna točka iz plana projekta |

## 4. Tim, rokovi i odluke

Tko radi što piše u tablici [Tim](../../README.md#tim), a zadaci po osobi i kontrolne točke u
[plan-rada.md](plan-rada.md). Sljedeća kontrolna točka je KT2 (10.11.2026.): jedan senzor, jedan servo, ThingsBoard
i ALPR na stvarnoj fotografiji te nacrt makete. Od 23.11. do 4.12. su međuispiti, a integraciju s hardverom treba
završiti prije blagdana (rizik R-16). Ako netko ispadne, mijenjaju se Toma i Luka, Sven i Lukas te Anja i Lovro
(rizik R-11).

### Odluke koje čekaju tebe i tim

| odluka | prijedlog | gdje |
|---|---|---|
| edge računalo | Raspberry Pi 4, Jetson Nano kao rezerva (D-004) | [odluke.md](odluke.md) |
| jedna ili dvije kamere | počnite s jednom koja se premješta, druga (~20 €) ako budžet dopusti (D-007) | [odluke.md](odluke.md), [nacrt-makete.md](../maketa/nacrt-makete.md#3-kamera) |
| varijanta arhitekture A ili B | A, jer je napisana i testirana; B traži novi posao u ThingsBoardu | [varijanta-b.md](../sustav/varijanta-b.md) |
| tko smije ući | `policy: open` (svaka valjana pločica) ili `allowlist` (samo s popisa) | `SOFTWARE/edge/edge.example.yaml` |
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
Koraci su u [INSTALL.md](../../SOFTWARE/INSTALL.md), poglavlja 1–4. Za GitHub još vrijedi:

- Repozitorij je privatan, pa git traži prijavu: korisničko ime s GitHuba i *personal access token* umjesto lozinke
  (GitHub → *Settings* → *Developer settings* → *Personal access tokens*).
- Dok grana nije spojena u `main`, nakon kloniranja napravi `git checkout claude/gitlab-struktura`.

Uspjeh: `pytest` završi s `passed` bez grešaka, `simulacija.py --broker` na kraju ispiše cijenu i
`poruke koje krše ugovor: 0`, a na dashboardu "Garaža – nadzor" mjesta mijenjaju boju dok simulacija radi.

## 6. Postavljanje cijelog sustava s hardverom

Ovo je postupak kad je hardver spojen i ožičen. Kako se do toga dolazi dio po dio, piše u
[planu integracije](plan-integracije.md).

### 6.1 Mreža i adrese

Sve ide na vlastiti Wi-Fi router makete. ESP32 radi samo na 2,4 GHz, pa na routeru uključi 2,4 GHz mrežu i ne
koristi mrežu s prijavom preko web stranice.

U postavkama routera (DHCP → *address reservation*) svakom računalu daj stalnu adresu. Adrese iz primjera su već
upisane u predloške:

| uređaj | adresa | gdje se upisuje |
|---|---|---|
| Raspberry Pi (edge, broker) | `192.168.1.10` | `MQTT_HOST` u `secrets.h` oba ESP32 |
| laptop (ThingsBoard) | `192.168.1.20` | `TB_HOST` u `SOFTWARE/edge/deploy/.env` na Piju |
| ESP32 senzora, ESP32 rampi | bilo koja (DHCP) | |

Ako router dijeli druge adrese (npr. `192.168.0.x`), koristi njih, ali iste u svim datotekama.

### 6.2 Raspberry Pi (edge računalo)

1. Sustav: u [Raspberry Pi Imageru](https://www.raspberrypi.com/software/) odaberi *Raspberry Pi OS Lite (64-bit)*.
   U *Edit settings* postavi hostname `garaza-edge`, korisnika `pi` s lozinkom, Wi-Fi routera makete i uključi SSH.
   Zapiši sustav na microSD, umetni ga u Pi i uključi.
2. S laptopa se spoji: `ssh pi@garaza-edge.local` (ili `ssh pi@192.168.1.10`).
3. Docker:
   ```bash
   sudo apt update && sudo apt full-upgrade -y && sudo apt install -y git
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER          # zatim se odjavi (exit) i ponovno spoji
   docker run --rm hello-world            # mora ispisati "Hello from Docker!"
   ```
4. Kod i postavke:
   ```bash
   git clone https://github.com/iampaviic/iotgarage.git ~/IoTGarage
   cd ~/IoTGarage/SOFTWARE
   cp edge/edge.example.yaml edge/edge.yaml            # kamera, pragovi, policy, naplata
   cp edge/deploy/.env.example edge/deploy/.env
   nano edge/deploy/.env                               # TB_HOST = adresa laptopa s ThingsBoardom
   ```
   U `edge.yaml` za početak ništa ne mijenjaj (jedna kamera `"0"`, `policy: open`, demo naplata). Datoteka mora
   postojati prije pokretanja, inače Docker umjesto nje napravi praznu mapu.
5. Pokretanje (prvi put gradi image, 10–30 min):
   ```bash
   cd ~/IoTGarage/SOFTWARE/edge/deploy
   alias dc='docker compose -f docker-compose.edge.yml -f docker-compose.camera.yml'
   dc up -d --build
   dc ps                                               # mosquitto, edge, tb-bridge: running
   dc logs -f edge                                     # zapisi edge servisa (Ctrl+C za izlaz)
   ```
   `alias` vrijedi do odjave. Da bude trajan, isti redak dodaj na kraj `~/.bashrc`. Naredbe `dc …` u ovom vodiču
   pokreću se iz mape `~/IoTGarage/SOFTWARE/edge/deploy`. Bez kamere, samo za probu, pokreni
   `docker compose -f docker-compose.edge.yml up -d --build` i ALPR će koristiti sintetske slike. Nakon restarta
   Pija servisi se pokreću sami (`restart: unless-stopped`).
6. Provjera s laptopa: `python -m garage_contract.monitor --host 192.168.1.10`. Svakih 30 s stižu heartbeat poruke
   servisa na Piju.
7. Vrijeme bez interneta (opcionalno, D-011): `sudo apt install -y chrony`, u `/etc/chrony/chrony.conf` dodaj redak
   `allow 192.168.1.0/24` i pokreni `sudo systemctl restart chrony`. Zatim u `secrets.h` oba ESP32 postavi
   `NTP_SERVER` na adresu Pija.

Nova verzija koda: `cd ~/IoTGarage && git pull && cd SOFTWARE/edge/deploy && dc up -d --build`.
Pi uvijek gasi sa `sudo shutdown -h now`, jer naglo isključivanje može oštetiti microSD.

### 6.3 Laptop: ThingsBoard

Na laptopu koji ide na demonstraciju pokreni ThingsBoard kao u
[INSTALL.md §4](../../SOFTWARE/INSTALL.md#4-thingsboard-laptop-ili-server-s--4-gb-ram), a zatim:

- da tlocrt na dashboardu odgovara maketi: `python provision/provision.py --positions ../maketa/nacrt/spots.json`;
- bridge s Pija spaja se na laptop na port 1884; ako Windows pita za vatrozid, dopusti Docker na privatnoj mreži;
- za demonstraciju tajni token: `python provision/provision.py --token <tajna>`, isti `TB_GATEWAY_TOKEN` upiši u
  `.env` na Piju i ondje pokreni `dc up -d`.

Uspjeh: na dashboardu "Garaža – nadzor" uređaj *Garage-Edge* je aktivan i stižu podaci.

### 6.4 ESP32 senzora

1. VS Code → *File* → *Open Folder* → `SOFTWARE/senzori/firmware`. PlatformIO sam prepozna projekt.
2. Kopiraj `include/secrets.example.h` u `include/secrets.h` i upiši `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_HOST`
   (adresa Pija) i `NTP_SERVER`. `secrets.h` se nikad ne komita.
3. Spoji ESP32 USB kabelom koji prenosi podatke, ne samo kabelom za punjenje.
4. *Upload* (strelica → u donjoj traci PlatformIO-a) ili `pio run -t upload`. Ako zapne na `Connecting....___`,
   drži tipku BOOT na pločici dok upload ne krene.
5. *Serial Monitor* (ikona utikača) ili `pio device monitor` (115200). Očekuješ:
   ```
   IoT Garage spot sensors 0.1.0, 6 spots
   WiFi: connecting...
   MQTT: connecting to 192.168.1.10:1883
   MQTT: connected
   ```
   Naredba `status` mora javiti `WiFi=1 MQTT=1 time=1`.
6. Na laptopu `python -m garage_contract.monitor --host 192.168.1.10` prikazuje zelene poruke
   `garage/parking/spot/P01…P06/telemetry`.

Pinovi i pragovi su u `include/config.h`. Pragovi se ondje upišu nakon kalibracije (korak H3 plana integracije).

### 6.5 ESP32 rampi

Isto kao 6.4, u mapi `SOFTWARE/rampe/firmware`. U serijskom monitoru očekuješ `IoT Garage gates 0.1.0` i
`MQTT: connected`. Naredbe su `open e`, `close e`, `reset e` i `status` (`x` umjesto `e` je izlazna rampa).
Kutovi serva (`closedAngle`, `openAngle`) su u `include/config.h`.

### 6.6 Kamera

1. Kamera je na mostu iznad trake, 200 mm iza crte rampe, s objektivom ~130 mm iznad poda. Gleda koso prema dolje na
   pločicu autića koji stoji na graničniku ([nacrt-makete.md](../maketa/nacrt-makete.md#3-kamera)).
2. Uključi je u USB Raspberry Pija i provjeri: `ls /dev/video*` mora pokazati `/dev/video0`.
3. Druga kamera je obično `/dev/video2`. Dodaj je u `docker-compose.camera.yml` (`devices`) i u `edge.yaml` za izlaz
   postavi `camera: "2"` (upute su u komentarima `edge.example.yaml`).
4. Svjetlo: LED traka s difuzorom iznad zone kamere i pločice na mat papiru, bez odsjaja.

### 6.7 Svaki put kad pališ sustav

1. Upali router, zatim Raspberry Pi (servisi se pokrenu sami za ~1 min).
2. Na laptopu pokreni `docker compose up -d` u `SOFTWARE/thingsboard` i otvori dashboard.
3. Uključi maketu sklopkom 5 V.
4. Nakon ~30 s sva mjesta imaju boju, rampe su zatvorene, a broj slobodnih mjesta je točan.
5. Proba: autić na ulaz, rampa se otvara, parkiraj, mjesto postane crveno.

Gasi se obrnutim redom, Pi sa `sudo shutdown -h now`. Upute za operatera dashboarda su u
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
| `MQTT: failed, rc=-2` | kriva adresa brokera, broker ne radi ili prima samo lokalne veze, vatrozid | provjeri `MQTT_HOST`; na laptopu `mosquitto -c lan.conf -v`; dopusti port 1883 |
| `MQTT: failed, rc=5` | broker traži lozinku | `MQTT_USER` / `MQTT_PASSWORD` u `secrets.h` |
| monitor ne prikazuje ništa | monitor gleda drugi broker | `python -m garage_contract.monitor --host <adresa brokera>` |
| crvene poruke u monitoru | netko šalje poruku koja ne odgovara ugovoru | monitor ispiše temu i razlog; ispravlja vlasnik tog dijela |
| ESP32 se resetira kad se servo pomakne | pad napona | servo s adaptera, zajednička masa, kondenzator 1000 µF uz servo |
| senzor uvijek `TIMEOUT` / `UNKNOWN` | ECHO nije spojen kroz djelitelj na pravi pin, senzor bez 5 V | provjeri pin u [shemi](../maketa/shema-spajanja.md), napon djelitelja, serijski `cal` |
| mjesto treperi | senzor vidi zid ili nije okomit, pragovi preblizu | montaža, ponovno `kalibracija.py` |
| IR javlja vozilo bez autića | vidi ruku rampe ili pod, previsoka osjetljivost | potenciometar na FC-51, položaj senzora |
| rampa se ne otvara iako je registracija pročitana | odluka nije `GRANTED` | u monitoru pogledaj razlog u `access/decision` (`GARAGE_FULL`, `ALREADY_INSIDE`, `RETRY`, `MANUAL_REQUIRED`) |
| uvijek `RETRY` / `MANUAL_REQUIRED` | mutna slika, odsjaj, loše svjetlo, pločica nije ispisana na 100 % | fokus i udaljenost kamere, mat papir, difuzor, graničnik kotača |
| na Piju se `edge` ruši odmah nakon starta | `edge.yaml` ne postoji (Docker napravi mapu) ili kamera nije `/dev/video0` | `ls ~/IoTGarage/SOFTWARE/edge/edge.yaml`, `ls /dev/video*`, `dc logs edge` |
| ThingsBoard ne dobiva ništa s Pija | kriva `TB_HOST` adresa, vatrozid laptopa, token se ne slaže | `.env` na Piju, port 1884 na laptopu, isti token u `provision.py --token` i `TB_GATEWAY_TOKEN`; `dc logs tb-bridge` |
| gumbi na dashboardu ne rade ništa | bridge ili edge servis ne rade | `dc ps` na Piju |
| `pytest` ili `simulacija.py` ne rade na laptopu | `.venv` nije aktiviran ili ne radiš iz mape `SOFTWARE` | `cd IoTGarage/SOFTWARE`, aktiviraj `.venv` |
| `tesseract` / `mosquitto` "not recognized" (Windows) | nisu u PATH-u | dodaj mape u PATH, otvori novi terminal |

Ako ništa od toga ne pomogne, pokreni isti korak sa simulatorom umjesto hardvera. Ako sa simulatorom radi, problem
je u hardveru ili mreži. Ako ne radi ni tamo, problem je u kodu i javi se vlasniku tog dijela.
