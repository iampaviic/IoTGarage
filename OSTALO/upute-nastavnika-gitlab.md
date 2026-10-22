# Upute za arhiviranje projekta

> Upute nastavnika (izvorno dobivene kao `.txt`, ovdje prepisane u Markdown bez promjene sadržaja).

Prije prezentacije projekta (najkasnije dan prije), studenti) trebaju mentoru(ima) predati arhivirane rezultate na
GitLabu.

U repozitoriju treba bit struktura datoteka ovakva:

```
+---README.TXT <ascii file>
+---PROJEKT    <direktorij>
+---SOFTWARE   <direktorij>
+---PREZENTACIJA	<direktorij>
+---OSTALO     <direktorij>
```

Pojedini dijelovi trebaju biti uredjeni ovako:

## 1. README.md

```
----------------------------------------------------------------
Projekt: [kratki naziv projekta], ak. god. 2021/22
Puni naziv projekta:   [puni naslov]
Datum prezentacije:  [datum]

Sadržaj repozitorija:
- kratki opis sto je sve u repozitoriju i kako je organizirano, po potrebi
reference na README fileove u pojedinim direktorijima

----------------------------------------------------------------
```

## 2. PROJEKT

&lt;direktorij, s pod-direktorijima po potrebi&gt;

- README.TXT s opisom sto je sto
- ako je rad (osim slika) u jednoj datoteci:
  1. konacna datoteka u formatu word processora koristenog za obradu teksta (npr. MS Word, LaTeX, ...)
  2. konacna datoteka u PDF formatu
  3. za slike ili grafove, koji su napravljeni pomocu nekog drugog alata (npr. snapshoti, crtezi u Visiu i sl.),
     pod-direktorij s datotekama u originalnom formatu
- ako je rad (osim slika) organiziran u vise datoteka:
  1. sve tekstualne datoteke po gornjem postupku (original; PS ili PDF)
  2. sve slike i grafovi u originalnom formatu u posebni direktorij, vidi upute gore
  3. detaljne upute kako sastaviti rad u README.TXT

## 3. SOFTWARE – napravljeni izvorni programski kod (projekt iz IDE-a)

&lt;direktorij, s pod-direktorijima po potrebi - npr. Android aplikacija, iOS aplikacija, waspmote, webapp, sql baze, ...&gt;

- README.TXT – s opisom sto je sto
- INSTALL.TXT – upute za instalaciju i evt. postavljanje varijabli; ako postoje upute u diplomskom radu (a trebale
  bi!), dovoljna je referenca na brojeve stranica gdje se nalaze
- direktorij(i) s kodom
  1. ako se koristi C, C++, Java ili neki drugi programski jezik, posebno staviti izvorne (source) datoteke,
     makefile/gradle/maven datoteke, eventualne upute za kompajliranje ako se ne koriste uobicajene naredbe
  2. U poseban direktorij staviti izvrsne verzije (ovo staviti na kraju kada je rad gotov)

**FAQ: Sto sve staviti u repozitorij?**

U repozitoriju treba biti sve sto bi vam trebalo da relativno brzo (cca par sati) instalirate, konfigurirate i
pokrenete svoj softver kada bi se npr. nenadano pobrisao disk na racunalu na kojem radite (ili dobijete drugo
racunalo za rad).

## 4. OBRANA

&lt;direktorij, s pod-direktorijima po potrebi&gt;

- README.TXT – s opisom sto je sto
- datoteka s prezentacijom (originalni format)
- slike i grafovi ako su napravljeni u nekom drugom alatu (originali koji se mogu mijenjati)

## 5. OSTALO

&lt;direktorij, s pod-direktorijima po potrebi&gt;

- README.TXT s opisom sto je sto
- tu ide sve sto ne spada pod PROJEKT ili SOFTWARE, npr.:
  - Web stranice na koje se pozivate u poglavlju Literatura
  - Web siteovi, bookmark (HTML) file
  - literatura, clanci, specifikacije i sl. skinuto s mreze ili sto ste dobili u elektronickom obliku od nastavnika
