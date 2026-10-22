# Završna tehnička dokumentacija (kostur)

Poglavlja su zasebne Markdown datoteke – svatko piše svoj dio, Patrik (voditelj) objedinjuje.
Izvoz u jedan PDF/DOCX (treba [pandoc](https://pandoc.org)):

```bash
cd PROJEKT/dokumentacija
pandoc 0*.md -o IoT-Garaza-dokumentacija.docx           # ili .pdf (treba LaTeX) / .html
```

| poglavlje | piše | izvori |
|---|---|---|
| [01-uvod.md](01-uvod.md) | 1, 8 | zadatak, plan |
| [02-arhitektura.md](02-arhitektura.md) | 1 | `PROJEKT/sustav/arhitektura.md`, ugovor |
| [03-korisnicke-upute.md](03-korisnicke-upute.md) | 8 | ✅ prva verzija napisana |
| [04-tehnicka-dokumentacija.md](04-tehnicka-dokumentacija.md) | 2–7 (svaki svoj odjeljak) | README-ovi foldera |
| [05-testiranje.md](05-testiranje.md) | 8 | testni plan, zapisnik, izvještaji |
| [06-privatnost-i-sigurnost.md](06-privatnost-i-sigurnost.md) | 8 | ✅ prva verzija napisana |
| [07-zakljucak.md](07-zakljucak.md) | svi | ograničenja, poboljšanja |

Slike: dashboardi (`PROJEKT/slike`), tlocrt (`SOFTWARE/maketa/nacrt/tlocrt.png`), sheme
(`SOFTWARE/maketa/elektronika/wireviz/*.svg`), 3D dijelovi, fotografije iz foto-dnevnika.
