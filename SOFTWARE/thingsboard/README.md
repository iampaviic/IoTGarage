# ThingsBoard: digitalni blizanac i dashboardi

Zaduženi: Anja (vlasnica: instalacija, provisioning, rule chain, nadzorni dashboard, alarmi i obavijesti) i Leo
Hreljanović (analitički dashboard i pristup podacima za [mobilnu aplikaciju](../mobilna-aplikacija), koja podatke
čita preko ThingsBoard REST API-ja).

U [varijanti B](../../PROJEKT/sustav/varijanta-b.md) ThingsBoard je središte sustava: uređaji se spajaju izravno na
njega, a rule chain donosi odluke o ulasku i izlasku, vodi parkirne sesije i naplatu te diže alarme.

## Što je već napravljeno (isprobano na ThingsBoard CE 4.2.1)

| | sadržaj |
|---|---|
| [docker-compose.yml](docker-compose.yml) | ThingsBoard CE i PostgreSQL u jednom kontejneru, podaci u imenovanim volumenima (preživljavaju restart) |
| [rulechain/](rulechain) | rule chain „Garaža (varijanta B)“: TBEL skripte (`scripts/`), generator `build_rule_chain.py` i generirani `garaza.json` |
| [provision/provision.py](provision/provision.py) | jednom naredbom napravi sve: profile uređaja s pravilima alarma, uređaje, gateway uređaje s *access tokenima*, asset "Garage" s postavkama, root rule chain, dashboarde; smije se pokretati više puta i ne briše sesije |
| [bridge/](bridge) | varijanta A (rezerva): most Mosquitto → ThingsBoard s lokalnim međuspremnikom |
| [dashboards/](dashboards) | 2 dashboarda (JSON) i generator `build_dashboards.py` |
| [tools/seed_history.py](tools/seed_history.py) | fiktivna povijest asseta Garage za razvoj analitike (`--clear` prije prave demonstracije!) |
| [entiteti-i-alarmi.md](../../PROJEKT/sustav/entiteti-i-alarmi.md) | popis uređaja, telemetrijskih ključeva i pravila alarma |
| [tests/](tests) | rule chain (`garaza.json` odgovara skriptama, svi čvorovi povezani); most varijante A |

Svaki čvor (oba ESP32 i ALPR servis) je *gateway* uređaj s jednom MQTT vezom za svoje uređaje
([odluka D-012](../../PROJEKT/upravljanje/odluke.md)), jer ThingsBoard CE nema generičku MQTT integraciju.

## Rule chain

Uređuje se u kodu, ne u web sučelju (promjene u sučelju `provision.py` prepiše):

```bash
# promijeni rulechain/scripts/*.tbel ili rulechain/build_rule_chain.py, zatim
python rulechain/build_rule_chain.py          # garaza.json (komitaj ga zajedno sa skriptama)
python provision/provision.py                 # uveze ga kao root rule chain
TB_LIVE_TEST=1 pytest ../integracija/tests/test_varijanta_b.py   # cijeli scenarij na tvom ThingsBoardu
```

Pojedinu skriptu možeš isprobati u ThingsBoardu: otvori rule chain, čvor → *Test script function*. Što koji dio radi
i sekvencijski dijagrami: [varijanta-b.md](../../PROJEKT/sustav/varijanta-b.md#rule-chain).

### Glavni dashboard "Garaža – nadzor"
![nadzor](../../PROJEKT/slike/dashboard-nadzor.jpg)

### Analitički dashboard "Garaža – analitika" (ovdje s fiktivnom poviješću)
![analitika](../../PROJEKT/slike/dashboard-analitika.jpg)

## Pokretanje

Instalacija i provisioning su u [INSTALL.md §3](../INSTALL.md#3-thingsboard-laptop-ili-server-s--4-gb-ram).
Uređaji se spajaju na MQTT port 1883. Za demonstraciju promijeni lozinku tenanta i postavi tajne *access tokene*
(`TB_TOKEN_SPOTS`, `TB_TOKEN_GATES`, `TB_TOKEN_ALPR` pri pokretanju `provision.py`); iste upiši u `secrets.h` oba ESP32
i u `edge.yaml`. Postavke naplate i odluke su atributi asseta Garage (`provision.py --demo-pricing` za demo).

## Alarmi i obavijesti

Alarme dižu pravila u profilima uređaja (stvara ih `provision.py`) i rule chain (popis je u
[entiteti-i-alarmi.md](../../PROJEKT/sustav/entiteti-i-alarmi.md)). Alarmi se propagiraju na asset Garage i vide se
u tablici na dashboardu.

ThingsBoard CE već ima uključeno pravilo *New alarm*, koje šalje obavijest u aplikaciji (zvonce). Za ostale kanale:

- e-mail: *Settings → Mail server* (npr. Gmail SMTP s app-lozinkom), zatim u *Notification center → Rules → New alarm*
  dodaj dostavnu metodu Email;
- webhook (Slack, Discord, vlastiti servis): u `build_rule_chain.py` nakon čvora „Pravila alarma profila“ (izlaz
  *Alarm Created*) dodaj čvor REST API Call s URL-om webhooka, pa ponovno izgradi i uvezi rule chain.

## Zadaci

- ✅ ThingsBoard instanca (compose), uređaji i asseti (`provision.py`), dva dashboarda, 7 pravila alarma
- ✅ varijanta B: rule chain (odluke, sesije, naplata, alarmi), gateway uređaji s tokenima, dashboardi na assetu
  Garage, gumbi „Ručno odobri“ / „Odbij“ i polje za registraciju; isprobano scenarijem `simulacija_b.py`
- ⬜ proći rule chain s timom (Luka: pravila, Lovro: naplata) i dogovoriti `policy`, naplatu, `exitFuzzyMatch`
- ⬜ pokrenuti ThingsBoard i `provision.py` na laptopu koji ide na demonstraciju; tajni tokeni i lozinka
- ⬜ nove snimke zaslona dashboarda (`PROJEKT/slike`) kad radi s maketom
- ⬜ prilagoditi dashboarde (boje, raspored, mobilni prikaz) i izvesti promjene (*Export dashboard*) u `dashboards/*.json`
- ⬜ obavijest e-mailom ili webhookom (opcionalno)
- ⬜ provjera: promjena mjesta vidljiva za manje od 3 s, a nakon `docker compose restart` ništa ne nestaje (TC-T06)
- ⬜ prije demonstracije `python tools/seed_history.py --clear`
