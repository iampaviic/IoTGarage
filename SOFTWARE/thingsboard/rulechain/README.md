# Rule chain „Garaža (varijanta B)“

Odluke o ulasku i izlasku, parkirne sesije, naplata i alarmi ([varijanta-b.md](../../../PROJEKT/sustav/varijanta-b.md#rule-chain)).

| datoteka | sadržaj |
|---|---|
| [scripts/decide.tbel](scripts/decide.tbel) | odluka, sesija, cijena (isto pravilo kao `SOFTWARE/baza`) |
| [scripts/](scripts) | ostale TBEL skripte: zahtjev ALPR-u, sažetak garaže, naredba rampi, veza uređaja |
| [build_rule_chain.py](build_rule_chain.py) | čvorovi i veze; iz skripti piše `garaza.json` |
| [garaza.json](garaza.json) | generirano – ne uređivati ručno; uvozi ga `provision.py` (ili *Rule chains → Import*) |

```bash
python build_rule_chain.py                       # nakon svake promjene skripte, komitaj i garaza.json
python ../provision/provision.py                 # uvoz kao root rule chain
TB_LIVE_TEST=1 pytest ../../integracija/tests/test_varijanta_b.py   # scenarij i provjere decide.tbel
```

`pytest thingsboard/tests` (i CI) javlja ako `garaza.json` ne odgovara skriptama.
