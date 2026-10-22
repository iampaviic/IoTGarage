# Osoba 1 – voditelj projekta i sistemski arhitekt

**Zadužen:** Patrik – voditelj projekta; uz to vodi izradu makete ([osoba-2-maketa](../osoba-2-maketa)) i objedinjuje završnu dokumentaciju.

Tvoj posao je da svi znaju **što njihov podsustav prima, što šalje, kojim protokolom i što se događa
kad nešto drugo ne radi** – i da se dijelovi spajaju svaki tjedan, ne tek na kraju.

## Što je već napravljeno

| datoteka | sadržaj |
|---|---|
| [arhitektura.md](arhitektura.md) | blok-dijagram, tokovi ulaska/izlaska, raspored, ponašanje kad podsustav ispadne |
| [komunikacijski-ugovor.md](komunikacijski-ugovor.md) | sve MQTT teme, JSON poruke, pravila (QoS, retained, requestId, UTC) |
| [contract/](contract) | **ugovor kao kod**: Python paket `garage_contract` – teme, JSON sheme, validacija, MQTT klijent, monitor |
| [zahtjevi.md](zahtjevi.md) | funkcionalni i nefunkcionalni zahtjevi s vlasnikom i testom |
| [plan-integracije.md](plan-integracije.md) | 10 koraka integracije s naredbama i kriterijima prolaza, pravila rada u repozitoriju |
| [plan-rada.md](plan-rada.md) | zadaci po osobi i tjednu (za GitHub Projects) |
| [rizici.md](rizici.md) | popis rizika s mjerama |
| [odluke.md](odluke.md) | dnevnik odluka (neke su **prijedlozi** – potvrdite ih) |
| [demo-scenarij.md](demo-scenarij.md) | završna demonstracija korak po korak + kontrolirane greške + kontrolna lista |
| [sastanci/predlozak.md](sastanci/predlozak.md) | predložak zapisnika tjednog sastanka |
| [integracija/](integracija) | **simulacija cijelog sustava** na jednom laptopu + end-to-end testovi |

## Alati koje ćeš najčešće koristiti

```bash
# cijeli sustav bez hardvera: simulatori + ALPR (sintetska kamera) + access control + baza
python integracija/simulacija.py --broker                 # odigra demo scenarij
python integracija/simulacija.py --broker --interactive   # ti upravljaš (upute se ispišu)
python integracija/simulacija.py --broker --tb            # + slanje u ThingsBoard

# što se događa na MQTT-u i krši li netko ugovor
python -m garage_contract.monitor

# end-to-end testovi (isti se vrte u CI-u)
pytest integracija/tests -v
```

Rezultat `simulacija.py` (skraćeno):

```
=== 1. vozilo ZG1234AB ulazi i parkira na P03
    odluka: GRANTED (AUTHORIZED), confidence 0.978
=== 3. nečitljiva pločica -> ručno odobrenje operatera
    odluka: MANUAL_REQUIRED (NO_PLATE)
    ručno: GRANTED (MANUAL_APPROVAL)
=== 4. pokušaj izlaska vozila bez sesije
    odluka: DENIED (NO_ACTIVE_SESSION)
=== 5. ZG1234AB izlazi (demo naplata: 1 min = 1 h)
    trajanje 26 s, cijena 1.50 EUR
=== gotovo; poruke koje krše ugovor: 0
```

## Što još trebaš napraviti ti

1. Proći [odluke.md](odluke.md) s timom i potvrditi prijedloge (posebno D-004 edge računalo, D-007 kamera).
2. Prenijeti [plan-rada.md](plan-rada.md) u GitHub Projects (ili Trello/Planner) i dodijeliti kartice.
3. Dogovoriti termin tjednog integracijskog sastanka; voditi zapisnike u `sastanci/`.
4. Zaštititi `main` granu na GitHubu (Settings → Branches): obavezan PR + zeleni CI.
5. Svaki tjedan: jedan korak iz plana integracije s pravim hardverom.
6. Tjedan 5: organizirati end-to-end test po [demo-scenarij.md](demo-scenarij.md) i snimiti rezervni video.

## Kriterij završetka (iz plana)

Svaki član iz arhitekturnog dokumenta razumije što njegov podsustav prima, što mora poslati, kojim
protokolom komunicira i što se događa ako njegov podsustav nije dostupan → arhitektura.md §7 i
komunikacijski-ugovor.md. Provjeri to tako da svaki član u jednoj rečenici objasni svoj podsustav.
