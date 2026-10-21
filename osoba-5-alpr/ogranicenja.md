# Kada detekcija pločice ne radi (ograničenja)

Početna verzija iz mjerenja na sintetskim scenama (`rezultati/detekcija_synthetic_hard.md`) i iz poznatih
svojstava metode. **Dopuniti stvarnim primjerima** iz `rezultati/debug/` nakon snimanja makete.

| situacija | što se događa | zašto | mjera |
|---|---|---|---|
| jak bočni kut (> 35–40°) | pločica nije pronađena ili je izrez kriv | omjer stranica izlazi iz raspona 2,3–7,5; znakovi preuski | kamera u osi trake, graničnik kotača |
| vrlo mala pločica (< 6 % širine slike) | ignorira se | donja granica u `DetectorConfig.min_plate_width_frac` | kamera bliže / veća pločica (kalkulator) |
| mrak / jako presvijetlo | slab kontrast, bjelina pločice ne prolazi ocjenu | ocjena traži svijetlu, nezasićenu pozadinu i tamne znakove | difuzna LED rasvjeta iznad zone kamere |
| zamućenje (pokret, fokus) | znakovi se stapaju, broj "znakova" pogrešan | ocjena broji povezane komponente | autić stoji na graničniku; provjera fokusa |
| odsjaj na sjajnoj pločici | bijela mrlja preko znakova | prezasićeni pikseli | mat papir, svjetlo ne u osi kamere |
| bijeli natpis/znak bez plave trake sličnih proporcija | moguća lažna detekcija (conf 0,55–0,75) | izgleda kao pločica bez EU trake | OCR + format registracije ga odbija |
| pločica bez plave EU trake (crno-bijeli ispis) | niža pouzdanost (najviše ~0,85) | plava traka je 15 % ocjene | ispis u boji |
| dvije pločice u kadru | uzima se ona s najboljom ocjenom | jedna detekcija po slici | ROI po rampi (`edge.yaml`) |
| pločica djelomično izvan kadra / zaklonjena rukom rampe | nema detekcije | kutovi nisu vidljivi | geometrija iz `kamera_kalkulator.py` |

Promašaji sintetskog "teškog" skupa (7/150) spremaju se kao slike u `rezultati/debug/` (zeleno = oznaka,
crveno = detekcija) nakon `python tools/evaluate_detection.py dataset/synthetic/hard` – pregledaj ih i
usporedi sa stvarnim promašajima.
