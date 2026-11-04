# 3D dijelovi (OpenSCAD)

Svi dijelovi su parametarski – otvori `.scad` u [OpenSCAD](https://openscad.org), promijeni varijable na vrhu
(npr. `lane_width`, `arm_height`) i izvezi STL. Gotovi STL-ovi za zadane mjere su u [stl/](stl).
CI provjerava da se svaki dio može izrenderirati.

| dio | datoteka | kom | opis |
|---|---|---|---|
| ![](slike/rampa_sg90.png) | `rampa_sg90.scad` | 2 | stup za SG90 + ruka rampe s utorom za servo nastavak; `part = "post" / "arm"` |
| ![](slike/nosac_hcsr04.png) | `nosac_hcsr04.scad` | 6 | nosač HC-SR04 stoji na mostu, senzor gleda prema dolje kroz dvije rupe Ø 17 mm u mostu |
| | `nosac_ir.scad` | 2 | FC-51 okomito na crti rampe, LED-ice na visini branika |
| ![](slike/most_kamere.png) | `most_kamere.scad` | 1–2 | most iznad trake (2 noge + prečka s blokom šarnira) + nagibna pločica za kameru (0–40°, M3 vijak kao os) |
| ![](slike/drzac_tablice.png) | `drzac_tablice.scad` | 6 | okvir za tiskanu pločicu 60 × 12,7 mm, lijepi se na autić |
| | `granicnik.scad` | 2 | graničnik kotača = ponovljiv položaj vozila ispred kamere |
| | `kabelski_kanal.scad` | po potrebi | kanal 14 × 9 mm s poklopcem |

Ispis: PLA, sloj 0,2 mm, ispuna 20 %, bez potpornja (dijelovi su položeni ravno).
Servo pričvrstiti vijcima iz kompleta serva; ruku rampe zalijepiti na jednokraki nastavak serva.
Ruku obojiti/oblijepiti crveno-bijelo.

## Sklop cijele makete

Svi dijelovi postavljeni na maketu zajedno sa senzorima, servima, kamerama, ESP32 čvorovima i autićima:
[sklop/](sklop) (slike, STL za pregled u pregledniku, GLB u boji).

![sklop makete](sklop/slike/sklop_pregled.png)
