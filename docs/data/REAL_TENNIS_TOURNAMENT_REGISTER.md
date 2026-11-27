# Historický registr tenisových turnajů — mužská dvouhra

**Stav k 2026-11-27: 10 ročníků, všechny Grand Slamy 2024 a 2025, Brisbane a Hong Kong 2024.** Tento jediný rozšiřitelný dokument je rešeršní registr reálného tenisu. Není autoritativním runtime balíčkem. Neobsahuje převod na squash, Run, simulační týdny, sloty, vlastní bodování ani změny existujících katalogů. Navazujeme vždy jedním ročníkem; další nepřidávat, dokud není předchozí zkontrolován proti povinnému seznamu a jeho zbývající mezery výslovně zařazeny. Rozsah: mužská profesionální dvouhra včetně kvalifikací; další disciplíny pouze jako kontext souhrnných financí či kalendáře.

## Rozhodnutí vlastníka — 2026-11-27: plán je referencí

Vlastník výslovně určil, že pro budoucí squashové balíčky se mají přebírat **nominální parametry a plánovaný program konkrétního ročníku**, nikoli náhodný průběh skutečného turnaje. Tento registr nadále obsahuje výhradně tenisová fakta, bez jakéhokoli převodu nebo implementace enginu.

- Zapisovat plánovaný počet nasazených, účastníků, WC a řádných Q postupů. Například Wimbledon 2024: 32 Q seedů, ne 31; 9 Q WC, ne 6. Historické výjimky zůstávají v odděleném kontextu a nesmí přepsat nominální hodnoty.
- Zapisovat plánovaná data kol a fází. Ojedinělý zápas přeložený kvůli dešti, tmě, zranění apod. nemění standardní termín kola. Rozlišit původní plán a doloženou trvalou změnu formátu/kalendáře ročníku.
- U více dnů uvádět celé plánované okno kola; přesné denní rozdělení pouze pokud je doložené nebo výslovně označené jako odvozené. Nevymýšlet rozdělení 50/50. Den bez mužského kola může být hracím dnem jiné disciplíny.
- Pravidla náhradníků, odstoupení a LL jsou součástí nominálního sportovního předpisu; jejich konkrétní historické realizace jsou volitelný kontext. Není požadován přepis jmen, skóre či hodin všech zápasů ani rekonstrukce každého individuálního odstoupení.
- Zdroje, data a identifikátory zachovávat v reálné podobě. Všechny hodiny jsou místní a časové pásmo se eviduje odděleně. Žádná projekce W52, převod na squash ani změna runtime v tomto PR.

## Evidence pokrytí a postup rešerše

Jednotkou práce je **jeden ročník jedné série**. Kompletní znamená kompletní vůči níže definovanému nominálnímu rozsahu, nikoli kompletní archiv všech skutečných zápasů. Každý ročník dostane stejný checklist a zdroje; stav se aktualizuje po kontrole, ne podle počtu napsaných řádků.

| Kód | Povinná oblast |
|---|---|
| I | Identita, kategorie, rok, lokalita, povrch, místní timezone |
| T | Plánované začátky/konce Main a Q (nebo doložená absence Q) |
| H | Plánovaný den či okno každého kola/fáze, včetně přestávek; ne jednotlivé mimořádně odložené zápasy |
| E | Nominální vstupní kvóty, přihlášky a losování (termíny, jsou-li publikované) |
| D | Kapacita, účastníci, počet nasazených, BYE, kvalifikační struktura, kola a postupy |
| R | Dobová pravidla losování, vstupu, náhradníků, formát zápasů a relevantní bodové výjimky |
| B | Body za každou fázi včetně Q |
| P | Odměny za každou fázi v původní měně; případně doložená absence odměny |
| Z | Konkrétní dohledatelné dobové zdroje; rozpory a nejistoty označeny |

Stavy: **HOTOVO (nominální rozsah)** = všechny povinné oblasti doložené na úrovni ročníku; **ROZPRACOVÁNO** = alespoň jedna povinná oblast chybí; **NEZAHÁJENO** = žádná rešerše v tomto registru. Skutečné hodiny jednotlivých zápasů, jména a výsledky, individuální cutoffs a SHA-256 jsou doplňková metadata, ne podmínka dokončení nominálního profilu. Nepublikované přesné denní počty zůstávají explicitní mezerou, ne smyšleným faktem. U ročníků s nejasností, která mění plánovanou strukturu, zůstává stav ROZPRACOVÁNO.

### Přehled ročníků v tomto PR

| Ročník | Turnaj | I | T | H | E | D | R | B | P | Z | Stav |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | [Wimbledon](#wimbledon-2024) | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2025 | [Wimbledon](#wimbledon-2025) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Australian Open](#australian-open-2024) | ✓ | ✓ | ✓* | ✓ | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Roland Garros](#roland-garros-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [US Open](#us-open-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2025 | [Australian Open](#australian-open-2025) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2025 | [Roland Garros](#roland-garros-2025) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2025 | [US Open](#us-open-2025) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Brisbane](#brisbane-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Hong Kong](#hong-kong-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |

`*` H: doložena okna kol; přesné původní počty zápasů jednotlivých dnů u vícedenních kol se nedokládají odhadem. Z: dobové zdroje jsou dohledatelné, některé pouze indexovaným textem; chybějí nezávisle získané PDF bajty/otisky. Obojí je transparentně zaznamenáno. U 2025 E*: datum uzávěrek odvozeno z dobového předpisu, hodina losu Q neověřena, ale Main los doložen; ATP rankingový předpis 2025 byl následně úspěšně zkontrolován i vizuálně na tištěné str. 264. AO 2024 H*: oficiální říjnový program textově dostupný, obrazové vykreslení selhalo; potvrzen dobovým programem pořadatele a předturnajovým přehledem. R*: dobový Grand Slam předpis v textovém zrcadle a ATP oznámení bodů; přímé PDF rulebooků nebylo dostupné.

**Součet registru:** 10 zpracovaných ročníků; 10 hotových v nominálním rozsahu; 0 rozpracovaných; ostatní ročníky zatím nejsou v registru, bez ohledu na stav jiných PR.

### Fronta dalších ročníků (pracovní pořadí, nikoli převzaté důkazy)

| Pořadí | Ročník a turnaj | Stav |
|---|---|---|
| 1 | Wimbledon 2024 | HOTOVO (nominální rozsah) |
| 2 | Wimbledon 2025 | HOTOVO (nominální rozsah) |
| 3 | Australian Open 2024 | HOTOVO (nominální rozsah) |
| 4 | Roland Garros 2024 | HOTOVO (nominální rozsah) |
| 5 | US Open 2024 | HOTOVO (nominální rozsah) |
| 6 | Australian Open 2025 | HOTOVO (nominální rozsah) |
| 7 | Roland Garros 2025 | HOTOVO (nominální rozsah) |
| 8 | US Open 2025 | HOTOVO (nominální rozsah) |
| 9 | Brisbane 2024 | HOTOVO (nominální rozsah) |
| 10 | Hong Kong 2024 | HOTOVO (nominální rozsah) |
| 11 | Adelaide 2024 | NEZAHÁJENO |
| 12 | Auckland 2024 | NEZAHÁJENO |

Po prvním bloku Grand Slamů 2024–2025 zpracovávat ostatní turnaje ATP 2024 a 2025 chronologicky podle dobového kalendáře, následně další ročníky postupně. Startovní inventura: `buuk` commit `29784d51d01d9d747705be8abae30f0c82706c1e`, soubor `config/reference_packages/atp_tour_1990_2026/calendar_dates_v1.json` obsahuje 62 datovaných záznamů roku 2024, prvně Brisbane, Hong Kong, Adelaide, Auckland. Jde o pracovní seznam, ne potvrzený celkový počet historických akcí; ověřovat identitu jednotlivých položek a samostatně doplnit týmové/speciální soutěže mimo tento soubor (United Cup aj.). Neoznačovat celý rok hotový pouze podle těchto 62 položek. Záznamy nikdy nevyplňovat pouze z podobného ročníku. Přesný postup u každého ročníku: (1) identita a dobový detail sheet; (2) plán fází a kol; (3) nominální struktura Main/Q a entry; (4) dobový rulebook, body a odměny; (5) porovnání nezávislého dokladu/losu, aritmetické kontroly, záznam rozporů; (6) aktualizace tabulky pokrytí. Při blokujícím neověřeném povinném údaji jej označit, necertifikovat profil a nejdříve řešit jeho doložení.

## Metodika evidence

- Jeden blok = jeden konkrétní historický ročník. Uvádět původní název, ročník, kategorii, stabilní identifikátor zdroje, pořadatele, místo, povrch, fáze, termíny, uzávěrky, losování, strukturu, nasazení, vstupní kvóty, body, odměny, relevantní pravidla a odchylky. Identifikátor série není náhradou za historické místo.
- Data YYYY-MM-DD a čas HH:MM jsou **místní civilní údaje** dějiště; IANA timezone evidujeme odděleně, případně doložený tehdejší offset. Datum bez času zůstává datem; nevymýšlet půlnoc a nepřepočítávat na jiný den. Rozlišit program/odhad/skutečný začátek/dokončení a případná přerušení přes půlnoc. Neznámé hodnoty zapisovat jako NEOVĚŘENO, ne jako nulu.
- Rozlišovat nominální kapacitu, nominální kvóty a skutečné obsazení konečného losu. Nasazení je překryvná vlastnost, ne další způsob vstupu. Neoznačený hráč není bez dalšího důkazu běžná přímá akceptace; může využívat chráněný ranking. Náhradník v kvalifikaci není lucky loser hlavní soutěže. Rozlišovat postupové uzly, zahájené zápasy, skreč po zahájení a walkover bez zahájení.
- Stav **doloženo** = konkrétní hodnota podložená uvedeným zdrojem; **odvozeno** = transparentní výpočet z doložených hodnot; **neověřeno** = konkrétní mezera; **rozpor** = zachovat obě zdrojové hodnoty a vysvětlení. Program kola neznamená skutečné datum každého zápasu. Zdrojové PDF odkazovat s číslem strany, datum verze a případný hash uvést pouze po získání celých bajtů.
- Existující ATP/Grand Slam balíčky a jejich samostatné PR (#1886, #1888, #1891, #1898, #1903) zůstávají beze změny. Tento registr nezakládá žádnou paralelní importní autoritu. Výsledky lze později porovnat s těmito balíčky, až vlastník rozhodne o dalším kroku.

| Ročník | Soutěž | Kategorie | Kvalifikace (místně) | Main (místně) | Stav |
|---|---|---|---|---|---|
| [2024](#wimbledon-2024) | Wimbledon | Grand Slam | 2024-06-24–2024-06-27 | 2024-07-01–2024-07-14 | HOTOVO v nominálním rozsahu; doplňková metadata otevřená |
| [2025](#wimbledon-2025) | Wimbledon | Grand Slam | 2025-06-23–2025-06-26 | 2025-06-30–2025-07-13 | HOTOVO v nominálním rozsahu; doplňková metadata otevřená |
| [2024](#australian-open-2024) | Australian Open | Grand Slam | 2024-01-08–2024-01-11 (plán) | 2024-01-14–2024-01-28 | HOTOVO v nominálním rozsahu; skutečné Q 9.–12. 1. odděleně |
| [2024](#roland-garros-2024) | Roland Garros | Grand Slam | 2024-05-20–2024-05-24 | 2024-05-26–2024-06-09 | HOTOVO v nominálním rozsahu; denní Q2 ověřeno |
| [2024](#us-open-2024) | US Open | Grand Slam | 2024-08-19–2024-08-22 | 2024-08-26–2024-09-08 | HOTOVO v nominálním rozsahu |
| [2025](#australian-open-2025) | Australian Open | Grand Slam | 2025-01-06–2025-01-09 | 2025-01-12–2025-01-26 | HOTOVO v nominálním rozsahu |
| [2025](#roland-garros-2025) | Roland Garros | Grand Slam | 2025-05-19–2025-05-23 | 2025-05-25–2025-06-08 | HOTOVO v nominálním rozsahu |
| [2025](#us-open-2025) | US Open | Grand Slam | 2025-08-18–2025-08-21 (plán) | 2025-08-24–2025-09-07 | HOTOVO v nominálním rozsahu; skutečné Q do 22. 8. |
| [2024](#brisbane-2024) | Brisbane International | ATP 250 | 2023-12-30–2023-12-31 | 2023-12-31–2024-01-07 | HOTOVO v nominálním rozsahu; Q/Main překryv |
| [2024](#hong-kong-2024) | Bank of China Hong Kong Tennis Open | ATP 250 | 2023-12-31–2024-01-01 | 2024-01-01–2024-01-07 | HOTOVO v nominálním rozsahu; Q/Main překryv |

## Wimbledon 2024

### 1. Identita a místo

| Pole | Historická hodnota | Důkaz |
|---|---|---|
| Název | The Championships, Wimbledon | S1, S2 |
| Rok / disciplína | 2024 / mužská dvouhra | S2 |
| Kategorie | Grand Slam, třetí major sezony | S5 |
| ATP tournament ID | 540 | S1 |
| Stav | Odehráno, vítěz Carlos Alcaraz | S2, S9 |
| Země / město | Spojené království, Londýn | S1 |
| Hlavní areál | All England Lawn Tennis and Croquet Club, Church Road, London SW19 5AG | S1 |
| Kvalifikační areál | Community Sport Centre Roehampton | S10 |
| Povrch | Venkovní tráva (kvalifikace i Main) | S1, S16 §3.a |
| Míče | Slazenger | S1 |
| Ředitel / rozhodčí | Jamie Baker / Denise Parnell | S1 |
| Časové pásmo | Europe/London, v uvedených červnových a červencových dnech BST (UTC+01:00) | S11, zeměpisná identifikace |
| Měna odměn | GBP | S1, S4 |

### 2. Historické termíny a program

Všechny hodiny níže jsou londýnské místní časy, nikoli UTC. Uzávěrky bez doložené hodiny nemají doplněný čas.

| Událost | Datum / čas | Povaha údaje | Důkaz |
|---|---|---|---|
| Uzávěrka hlavní dvouhry | 2024-05-20 | oznámená, automatické přihlášení | S1 str. 2 |
| Uzávěrka kvalifikace | 2024-06-03 | oznámená | S1 str. 2 |
| Trénink Q v Roehamptonu od | 2024-06-21 | oznámený | S1 str. 1 |
| Los kvalifikace | 2024-06-23 14:00 | oznámený čas | S1 str. 1 |
| Konec sign-in náhradníků Q | 2024-06-24, 30 min před plánovaným prvním zápasem (při programu 11:00 tedy 10:30) | oznámená podmínka; 10:30 odvozeno | S1 str. 2 |
| Q začátek / konec | 2024-06-24 / 2024-06-27 | program i doložené krajní dny | S1, S6, S7 |
| Los hlavní dvouhry | 2024-06-28 10:00 | oznámený čas | S1 str. 1 |
| Main začátek / konec | 2024-07-01 / 2024-07-14 | program i doložené krajní dny | S1, S8, S9 |
| Běžný start venkovních kurtů | 11:00 | oznámený program, ne start každého zápasu | S1 |
| Centre Court | 13:30; poslední dva dny 14:00 | oznámený program | S1, S9 |
| No. 1 Court | 13:00; závěrečný víkend 11:00 | oznámený program | S1 |
| Finále mužů | 2024-07-14 | skutečné datum, Centre Court | S2, S9 |
| Čas finále — starší verze | ne před 15:00 | oznámení v detail sheet 2024-06-14 | S1 |
| Čas finále — denní program | 14:00, první zápas | pozdější oficiální pořadí hry; první odpálený míč NEOVĚŘENO | S9 |

**Nominální rozpis kol — referenční fakta pro tento ročník.** Počty jsou uzly celého kola, nikoli počet zápasů odehraných v konkrétním dni. Ověřeno proti dobovému programu S13/S21 a kvalifikačním denním rozpisům S6/S7/S12. Původní kvalifikační program jednotlivých dnů před zahájením nebyl samostatně archivně získán; Q1/Q2/Q3 jsou doložené programy a výsledky příslušných dnů, nikoli odhad z jiného ročníku.

| Kolo | Plánované okno, místní datum | Nominální počet zápasových uzlů | Zdroj |
|---|---|---:|---|
| Q1 | 2024-06-24 | 64 | S1, S6; datum doloženo výsledky |
| Q2 | 2024-06-26 | 32 | S7a |
| Q3 | 2024-06-27 | 16 | S7b |
| R128 | 2024-07-01–2024-07-02 | 64 | S13, S21 |
| R64 | 2024-07-03–2024-07-04 | 32 | S13, S21 |
| R32 | 2024-07-05–2024-07-06 | 16 | S13, S21 |
| R16 | 2024-07-07–2024-07-08 | 8 | S13, S21 |
| QF | 2024-07-09–2024-07-10 | 4 | S13, S21 |
| SF | 2024-07-12 | 2 | S13, S21 |
| F | 2024-07-14 | 1 | S1, S13, S21 |

Kontrola: Q = 64+32+16 = 112; Main = 64+32+16+8+4+2+1 = 127; celkem 239 nominálních uzlů. Plánovaná struktura zůstává 239, ne 237 (skutečně zahájených). Přihlášky: 104+16+8=128, Q:119+9=128. Main odměny součtem počtů poražených v kole a vítěze = 17 942 000 GBP; Q odměny 64×15 000 + 32×25 000 + 16×40 000 = 2 400 000 GBP. Výjimky nemění tyto plánované parametry.

**Denní pohled a historický kontext:**

| Místní den | Fáze | Druh evidence |
|---|---|---|
| Po 24. 6. | Q1 | doložené zahájení a výsledky S6 |
| Út 25. 6. | druhý den společného kvalifikačního programu; ženské Q1 | S12; samostatné mužské zápasy nedoloženy, neoznačovat automaticky za další mužské kolo |
| St 26. 6. | Q2 | oficiální denní výsledky S7a |
| Čt 27. 6. | Q3, postup do Main | oficiální denní výsledky S7b |
| Pá 28. 6. | los Main | program S1 |
| So 29. 6. | mezi fázemi | není součástí publikovaného hracího okna mužské dvouhry |
| Ne 30. 6. | mezi fázemi | totéž |
| Po 1. 7. | R128 | plán S13, skutečné výsledky S8 |
| Út 2. 7. | R128 | plán S13 |
| St 3. 7. | R64 | plán S13; déšť S14 |
| Čt 4. 7. | R64 | plán S13 |
| Pá 5. 7. | R32 | plán S13; déšť S15 |
| So 6. 7. | R32 | plán S13 |
| Ne 7. 7. | R16 | plán S13 |
| Po 8. 7. | R16 | plán S13 |
| Út 9. 7. | QF | plán S13 |
| St 10. 7. | QF | plán S13; v losu evidován jeden walkover |
| Čt 11. 7. | bez plánované mužské dvouhry | plán S13 |
| Pá 12. 7. | SF | plán S13 |
| So 13. 7. | bez plánované mužské dvouhry | plán S13 |
| Ne 14. 7. | F | výsledek S9 |

Odvozeno: kvalifikační okno 4 kalendářní dny včetně dne 25. 6.; Main 14 kalendářních dnů; celé okno od 24. 6. do 14. 7. včetně 21 dnů. Nejde o počet skutečných hracích dnů mužů. Déšť a přerušené zápasy jsou skutečné odchylky: například zápas Bellucci–Shelton je v denním protokolu 1. 7. označen jako nedokončený (S8), konečný los už uvádí výsledek (S2). Přesná denní alokace všech zápasů není povinná; okna kol jsou v nominální tabulce.

### 3. Struktura obou soutěží — plán versus konečný los

| Parametr | Hlavní soutěž | Kvalifikace | Zdroj |
|---|---:|---:|---|
| Kapacita pavouka | 128 | 128 | S1 |
| Obsazené pozice v konečném losu | 128 | 128 | S2, S3 |
| Formát | vyřazovací | vyřazovací, 16 sekcí | S2, S3, S16 |
| Kol | 7 | 3 | S2, S3 |
| Plánované přímé akceptace | 104 | 119 | S1 str. 2 |
| Plánovaná řádná postupová místa Q do Main | 16 | 16 vítězů sekcí | S1, S3 |
| Plánovaná kvóta WC | 8 | 9 | S1 |
| WC viditelné v konečném losu | 8 | 6 | S2, S3 |
| Lucky losers viditelní v Main | 5 | nevztahuje se | S2 |
| Alternates označené v Q | nevztahuje se | 2 | S3 |
| Neoznačené pozice (bez W/Q/L v Main; bez W/A v Q) | 99 | 120 | odvozeno z S2, S3 |
| Nominální nasazení | 32 | 32 (2 na sekci) | S2, S16 |
| Skutečně viditelné nasazení | 32 | 31 (chybí číslo 11) | S2, S3, S17 |
| BYE | 0 | 0 | S2, S3 |
| Uzly zápasů celkem | 127 | 112 | odvozeno z S2, S3 |
| Walkovery v konečném losu | 2 | 0 | vizuální kontrola S2, S3 |
| Zahájené zápasy včetně skrečí | 125 | 112 | odvozeno z uzlů minus walkovery |

Kvalifikace má 16 nezávislých osmičlenných sekcí, každá se 4+2+1 zápasovými uzly; vítěz každé sekce postupuje do Main. Plánované 119+9 v Q nelze zaměnit za skutečné 120+6+2 značení. Důvod každé neobsazené nominální WC kvóty ještě není jednotlivě doložen. Hlavní soutěž má 99 neoznačených pozic + 16 Q + 8 WC + 5 LL = 128. Neoznačené pozice nejsou důkazem přesného způsobu přijetí všech 99 hráčů.

**Kontrolní pozice v originálním losu (1–128, stránky 1–2):**

| Značka | Pozice |
|---|---|
| Main WC (W) | 12, 22, 46, 70, 93, 110, 115, 125 |
| Main Q | 13, 15, 19, 26, 30, 34, 38, 51, 53, 63, 90, 98, 107, 117, 126, 127 |
| Main LL (L) | 7, 61, 74, 101, 111 |
| Q WC (W) | 7, 36, 45, 51, 86, 92 |
| Q alternate (A) | 42, 81 |

Q nasazený č. 11 Valentin Vacherot se na poslední chvíli odhlásil; na pozici 81 nastoupil alternate Alex Bolt, který kvalifikaci vyhrál. Doloženo australským tenisovým svazem (S17) a konečným Q losem. Je to historická výjimka, nikoli důvod změnit nominální počet nasazených na 31 pro jiné ročníky.

Pět Main LL v konečném losu: Daniel Elahi Galan, Luca Van Assche, Giovanni Mpetshi Perricard, David Goffin, James Duckworth. Všichni jsou v Q losu mezi poraženými ve třetím kole. Přesná chronologie všech pěti změn a totožnost všech původně nahrazených hráčů nejsou zatím doloženy.

### 4. Kola, body a odměny

Hodnoty bodů vycházejí z dobového ATP detail sheet a ATP Rulebook 2024 §IX.G (S1, S18); odměny z oficiálního přehledu pořadatele (S4). Jde o částky za dosaženou fázi na osobu, nikoli součet částek za každé vyhrané kolo. Výjimky bodování viz níže.

| Výsledek | Účastníků na začátku kola | Uzly kola | ATP body | GBP |
|---|---:|---:|---:|---:|
| Main vítěz | — | — | 2000 | 2700000 |
| Main poražený finalista | 2 | 1 | 1300 | 1400000 |
| Main poražený semifinalista | 4 | 2 | 800 | 715000 |
| Main poražený čtvrtfinalista | 8 | 4 | 400 | 375000 |
| Main poražený v R16 | 16 | 8 | 200 | 226000 |
| Main poražený v R32 | 32 | 16 | 100 | 143000 |
| Main poražený v R64 | 64 | 32 | 50 | 93000 |
| Main poražený v R128 | 128 | 64 | 10 | 60000 |
| Q postupující | — | — | 30 | samostatná odměna není uvedena |
| Q3 poražený | 32 | 16 | 16 | 40000 |
| Q2 poražený | 64 | 32 | 8 | 25000 |
| Q1 poražený | 128 | 64 | 0 | 15000 |

- První kolo Main: držitel divoké karty při prohře bez dalšího postupu nezískává běžných 10 bodů (S18 str. 253–254). Řádnému kvalifikantovi se 30 Q bodů přičítá k výsledku Main dle §IX.G. Individuální body lucky loserů, chráněného rankingu a walkoverů nejsou v tomto registru vypočteny.
- Hlavní mužská dvouhra: 17 942 000 GBP; mužská kvalifikace: 2 400 000 GBP; součet obou vypsaných položek 20 342 000 GBP (bez čtyřhry a diet). Úplná mužská soutěž včetně čtyřhry: 23 232 000 GBP dle S1; celý turnaj všechny disciplíny včetně odhadovaných diet: 50 000 000 GBP dle S4. Nezaměňovat tyto čtyři odlišné součty.
- Dobový detail sheet (S1 str. 3) uvádí diety 300 GBP/den od plánovaného prvního zápasu příslušné soutěže po poslední zápas včetně tří dnů navíc. Nejsou součástí individuální tabulky prize money.

### 5. Dobová pravidla tenisu a výsledkové kontrolní body

| Pole | Hodnota | Zdroj |
|---|---|---|
| Main mužská dvouhra | best of 5 setů | S16 §L, S2 |
| Q1 a Q2 | best of 3 setů | S3 výsledky |
| Q3 | best of 5 setů | S3, S7, S19 (např. pětisetový rozhodující zápas) |
| Rozhodující set Main při 6:6 | tiebreak na 10, rozdíl alespoň 2 body | S20 |
| Přijetí Main dle žebříčku | standardně ranking asi 42 dnů před turnajem; WC a Q samostatné | S16 §2.a–e |
| Nasazení Main | standardně ranking asi 7 dnů před turnajem, 32 skutečných seedů | S16 §2.f, S2 |
| Q nasazení | dva seedy na sekci; prvních 16 seedů na horních pozicích jednotlivých sekcí, dalších 16 losováno na dolní pozice. Před zveřejněním Order of Play se odstoupený seed nahradí dalším způsobilým seedem, po zveřejnění přímo alternatem. | S16 §3.g–h, tištěné str. 30–31; S17 |
| Zařazení vítězů Q | losování do volných kvalifikačních pozic po Q; žádné předem pevné spojení sekce s pozicí Main | S16 §3.j |
| Lucky loser | přednost poražených Q3; při nedostatku i dřívější kola. Los mezi čtyřmi nejvýše postavenými podle rankingu pro Q nasazení, ostatní podle rankingu; pokud při skončení Q více než dvě odhlášení z Main, velikost losované skupiny = počet odhlášení + 2. Náhrada před prvním bodem prvního zápasu odstoupivšího; sign-in 30 min před prvním zápasem dne. | S16 §2.h, tištěné str. 28–29 |
| Vítěz / finalista | Carlos Alcaraz / Novak Djokovic | S2, S9 |
| Výsledek finále | 6:2, 6:2, 7:6(4) | S2, S9 |
| Walkovery Main | de Minaur proti Pouille (R32); Djokovic proti de Minaur (QF) | S2 str. 2 |
| Historická změna / omezení | déšť posouval zahájení a dokončování zápasů | S8, S14, S15 |

Úplný jmenný los, výsledky jednotlivých zápasů a jejich skóre jsou zachovány v odkazech S2/S3, nikoli přepsány jako další kopie. Pro kontrolu tvaru jsme vizuálně zkontrolovali obě stránky každého z obou losů.

### 6. Stav kontroly a otevřené otázky

| Oblast | Stav | Co zbývá |
|---|---|---|
| Identita, dějiště, data fází, velikost, kvóty, body, odměny | Doloženo | kontrola revizí původních zdrojů při případné opravě |
| Konečné značení Q/W/L/A, nasazení, nulové BYE, uzly | Doloženo / odvozeno | individuální rekonstrukce přijetí a odhlášení |
| Přihlášky a losování | Doložený oznámený plán | skutečné okamžiky losování nejsou ověřeny |
| Denní harmonogram | Nominální okna všech kol doložena | přesné denní počty vícedenních kol a samostatný původní program Q před zahájením nejsou získány; nepovinný detail, neodhadovat |
| Časové pásmo | Lokální pásmo a letní offset | konkrétní skutečné starty zápasů dosud nepřepsány |
| Body a prize money všech jednotlivých hráčů | Tabulky a pravidlo Q doloženy | konkrétní výjimky a rankingové výpisy (včetně LL a WC) |
| Ochranné pořadí, přihlášky, cutoffs 2024, všechna odstoupení | Neověřeno | původní a konečné entry lists, pozor: detail sheet obsahuje cutoffs 2023, nepoužívat pro 2024 |
| Originální bajty a SHA-256 PDF | Neověřeno | vizuální/textové zobrazení není stažení souboru; žádný hash nevymyšlen |
| Přepis celých losů / všech 239 uzlů výsledků | Mimo požadovaný rozsah | originály dostupné S2/S3; jednotlivé výsledky nepřepisovat |

Závěr: Wimbledon 2024 je uzavřen v definovaném nominálním rozsahu (I/T/H/E/D/R/B/P/Z), s výše uvedenými omezeními zdrojů a detailnosti. Není to tvrzení o kompletním přepisu všech zápasů ani o 100% historické certifikaci. Historické výjimky nepřepisují plánované údaje. Žádné převody do simulačního kalendáře.

### 7. Zdroje

- S1: [ATP — Wimbledon 2024 Detail Sheet](https://www.protennislive.com/posting/2024/540/ds.pdf), aktualizace 2024-06-14, str. 1–3 (vizuálně ověřeny). Dobový program, identity, uzávěrky, kvóty, body, peníze.
- S2: [Wimbledon — Gentlemen's Singles 2024](https://www.wimbledon.com/en_GB/scores/draws/2024_MS_draw.pdf), 2 strany, aktualizace 2024-07-14 16:49; obě strany vizuálně ověřeny.
- S3: [Wimbledon — Gentlemen's Qualifying Singles 2024](https://www.wimbledon.com/en_GB/scores/draws/2024_QS_draw.pdf), 2 strany, aktualizace 2024-06-27 16:10; obě strany vizuálně ověřeny.
- S4: [Wimbledon — Prize Money 2024](https://www.wimbledon.com/pdf/Wimbledon_Prize_Money_2024.pdf?os=vbKn42TQHo), str. 1, vizuálně ověřeno.
- S5: [ATP — Wimbledon 2024 preview](https://www.atptour.com/en/news/wimbledon-2024-history-draw-schedule), indexovaný text; přímé otevření v rešerši 403.
- S6: [ATP — kvalifikace, 24. 6.](https://www.atptour.com/en/news/wimbledon-2024-qualifying-monday), [Sky Sports — výsledky 24. 6.](https://www.skysports.com/tennis/scores-schedule/24-06-2024).
- S7: S7a [oficiální denní protokol 26. 6.](https://www.wimbledon.com/en_GB/scores/2024/schedule/pdf/schedulePDF3.pdf), S7b [27. 6.](https://www.wimbledon.com/en_GB/scores/2024/schedule/pdf/schedulePDF4.pdf), vizuálně ověřeny první strany.
- S8: [Wimbledon — denní protokol 1. 7.](https://www.wimbledon.com/en_GB/scores/2024/schedule/pdf/schedulePDF8.pdf), první strana vizuálně ověřena.
- S9: [Wimbledon — denní protokol 14. 7.](https://www.wimbledon.com/en_GB/scores/2024/schedule/pdf/schedulePDF21.pdf), první strana vizuálně ověřena.
- S10: [Wimbledon — místo kvalifikace](https://help.wimbledon.com/hc/en-gb/articles/14269853761948-Where-does-the-Qualifying-Competition-take-place), publikováno 2024-06-02.
- S11: [GOV.UK — British Summer Time](https://www.gov.uk/when-do-the-clocks-change), obecné pravidlo; červnové/červencové termíny leží v BST.
- S12: [Wimbledon — denní protokol 25. 6.](https://www.wimbledon.com/en_GB/scores/2024/schedule/pdf/schedulePDF2.pdf), první strana vizuálně ověřena; [Sky Sports 25. 6.](https://www.skysports.com/tennis/scores-schedule/25-06-2024).
- S13: [ESPN — dobový vysílací rozpis](https://espnpressroom.com/press-release/espn-presents-first-ball-to-last-ball-of-the-championships-wimbledon-2024/) a [Tennis Connected — denní program](https://tennisconnected.com/2024-wimbledon-tournament-schedule/); plán, nikoli autorita o skutečných dokončeních.
- S14: [ATP — déšť 3. 7.](https://www.atptour.com/en/news/wimbledon-2024-day-3-rain-delay).
- S15: [ATP — déšť 5. 7.](https://www.atptour.com/en/news/wimbledon-2024-rain-friday).
- S16: [ITF — Official Grand Slam Rule Book 2024](https://www.itftennis.com/media/5986/grand-slam-rule-book-2024-f3.pdf), §L, §2, §3; indexovaný text, vykreslení stran při rešerši selhalo.
- S17: [Tennis Australia — náhrada Vacherota Boltem, 25. 6. 2024](https://www.tennis.com.au/fan-zone/news/2024/06/25/bolt-makes-the-most-of-late-call-up-into-wimbledon-2024-qualifying-draw).
- S18: [ATP Rulebook 2024, Chapter IX — Rankings](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-9_pif-atp-rankings_27feb.pdf), §G, tištěné str. 253–254; vizuálně ověřeny.
- S19: [ATP — kvalifikace, 27. 6.](https://www.atptour.com/en/news/wimbledon-qualifying-2024-thursday).
- S20: [ITF — Wimbledon 2024 men's tournament preview](https://www.itftennis.com/media/12685/2024-wimbledon-mens-tournament-preview.pdf) a [Grand Slam Board — společná změna rozhodujícího tiebreaku 2022](https://ausopen.com/articles/news/grand-slams-jointly-adopt-10-point-final-set-tiebreak).

- S21: [The Standard — předturnajový rozpis mužské dvouhry Wimbledon 2024](https://www.standard.co.uk/sport/tennis/wimbledon-2024-tennis-dates-schedule-ticket-information-b1160804.html); potvrzuje okna všech sedmi kol; [Sky Sports — 26. 6. 2024](https://www.skysports.com/tennis/scores-schedule/26-06-2024), [27. 6. 2024](https://www.skysports.com/tennis/scores-schedule/27-06-2024) nezávislá kontrola označení kol Q2/Q3. Opětovná kontrola 2026-11-27: S1 str. 1–2 vizuálně; S7a/b první strany vizuálně; S16 text dohledán, screenshot vrací 404.

## Wimbledon 2025

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z, s výslovnými omezeními níže. Rešerše 2026-11-27. Nejde o převod do squashového enginu.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Oficiální název | The Championships, Wimbledon | W25-1, W25-2 |
| Rok / disciplína | 2025 / mužská dvouhra | W25-2, W25-3 |
| Kategorie / ATP ID | Grand Slam / 540 (identita turnaje) | W25-1, W25-15 |
| Místo Main | All England Lawn Tennis Club, Londýn, UK | W25-1 |
| Místo Q | Community Sport Centre, Roehampton, Londýn | W25-9 |
| Povrch Main a Q | venkovní tráva | W25-1, W25-4 str. 30 |
| Časové pásmo | Europe/London; po dobu Q a Main BST, UTC+01:00 | W25-10 |
| Ředitel / rozhodčí | Jamie Baker / Denise Parnell | W25-1, W25-6d str. 3 |
| Měna | GBP | W25-5 |

Míče a adresní detail konkrétní edice nebyly samostatně ověřeny: nevyplňujeme z 2024. Nejde o povinná data I.

### 2. Termíny, vstupní uzávěrky a nominální harmonogram

| Událost | Lokální údaj | Povaha / zdroj |
|---|---|---|
| Uzávěrka Main | 2025-05-19 | odvozeno z 42 dnů před prvním pondělím Main (30. 6.); W25-4 str. 24 |
| Uzávěrka Q | 2025-06-02 | odvozeno z 28 dnů před prvním pondělím Main; W25-4 str. 24 |
| Los Q | přesné datum a hodina NEOVĚŘENY | existoval před Q1 23. 6.; neodvozovat datum/hodinu z 2024 |
| Q | 2025-06-23 až 2025-06-26, od 11:00 | W25-1, W25-6 |
| Main los | 2025-06-27 10:00 | plán W25-1 |
| Main | 2025-06-30 až 2025-07-13 | W25-1, W25-2, W25-7 |
| Plánované finále | 2025-07-13, 16:00 | pořadatel W25-8; nezávisle W25-7/W25-11 |
| Začátky běžných dnů | venkovní kurty 11:00, No.1 13:00, Centre 13:30 | dobový přehled W25-12; nejsou to skutečné starty všech zápasů |

**Nominální rozložení všech kol mužské dvouhry.**

| Fáze | Místní data | Nominální uzly | Zdroj |
|---|---|---:|---|
| Q1 | 2025-06-23 | 64 | W25-6a |
| Q bez plánovaného mužského kola | 2025-06-24 | 0 | ženské Q1, W25-6d; ne tvrzení o žádném zápase areálu |
| Q2 | 2025-06-25 | 32 | W25-6b |
| Q3 | 2025-06-26 | 16 | W25-6c |
| Přestávka mezi Q a Main | 2025-06-27–2025-06-29 | 0 | W25-1 |
| R128 | 2025-06-30–2025-07-01 | 64 | W25-7, W25-11 |
| R64 | 2025-07-02–2025-07-03 | 32 | W25-7, W25-11 |
| R32 | 2025-07-04–2025-07-05 | 16 | W25-7, W25-11 |
| R16 | 2025-07-06–2025-07-07 | 8 | W25-7, W25-11 |
| QF | 2025-07-08–2025-07-09 | 4 | W25-7, W25-11 |
| Bez plánovaného kola mužské dvouhry | 2025-07-10 | 0 | W25-7, W25-11 |
| SF | 2025-07-11 | 2 | W25-7, W25-11 |
| Bez plánovaného kola mužské dvouhry | 2025-07-12 | 0 | W25-7, W25-11 |
| F | 2025-07-13 | 1 | W25-8, W25-11 |

Q1/Q2/Q3 doloženy dobovými denními programy; celkový Q plán potvrzuje ATP. U vícedenních Main kol není doloženo plánované rozdělení počtu uzlů mezi dny a není doplněno předpokladem 50/50. 4 kalendářní dny Q, 14 kalendářních dnů Main, 21 dnů celého okna včetně mezery. Počty uzlů jsou aritmetika nominálního pavouka, ne statistika přerušení.

### 3. Struktura turnaje

| Nominální parametr | Main | Q | Důkaz |
|---|---:|---:|---|
| Kapacita | 128 | 128 | W25-2, W25-3, W25-4 |
| Počet účastníků | 128 | 128 | W25-2, W25-3 |
| Přímé akceptace | 104 | 119 | W25-4 str. 26,31 |
| WC | 8 | 9 | W25-4 str. 26,31 |
| Postupující z Q | 16 | 16 vítězů sekcí | W25-4 str. 26,31; W25-13 |
| Nasazených | 32 | 32 | W25-2, W25-3, W25-4 str. 28,31–32 |
| BYE | 0 | 0 | W25-2, W25-3 |
| Sekce | jeden vyřazovací pavouk | 16 skupin po 8 (vyřazovací sekce) | W25-2, W25-3 |
| Počet kol | 7 | 3 | W25-2, W25-3 |
| Nominální uzly | 127 | 112 | odvozeno |

Aritmetika: 104+16+8=128; 119+9=128; 127+112=239 uzlů. Není to tvrzení o počtu unikátních hráčů v obou fázích dohromady.

**Oddělený kontrolní kontext konečného losu:** vizuálně přečteny všechny čtyři stránky W25-2/3. Main: 8 W (6,15,44,61,62,74,92,108), 16 Q (18,29,31,37,42,51,54,85,86,94,98,117,119,124,125,126), 3 L (22,84,93), 101 neoznačených. Q: 9 W (19,30,34,53,63,78,91,106,125), 1 A (126), 118 neoznačených. Main i Q všech 32 seedů a žádný BYE. Označení nejsou rekonstrukce individuální přímé akceptace. Tři LL, kteří reálně nastoupili v Main, nejsou nominální kvóta a nemění 16 Q postupů. Nepřepisujeme jména ani výsledky všech zápasů.

### 4. Dobová pravidla

- Grand Slam Rule Book 2025, tištěné str. 24–32 (W25-4, vizuálně ověřeno): vstupní termíny 42/28 dnů, automatické přihlášení způsobilých hráčů, hlavní přímé akceptace podle rankingu přibližně 42 dnů před turnajem, nasazení podle rankingu přibližně sedm dnů před turnajem; seed 1/2 na krajích, ostatní v příslušných skupinách losované podle tabulky pro 128/32. Q nasazení podle nejnovějšího dostupného rankingu, prvních 16 seedů na začátcích sekcí, druhá skupina 16 náhodně na konce sekcí. Před vydáním OOP se uvolněné Q seed místo obsadí dalším seedem, po vydání OOP alternatem.
- Q vítězové se losují do Main po ukončení Q; žádná předem pevná vazba mezi sekcí Q a konkrétní pozicí Main. LL přednostně z poražených Q3, případně nižších kol. Los pořadí čtyř nejvýše postavených podle rankingu pro Q seeding; pokud při skončení Q více než dvě odhlášení z Main, velikost skupiny je počet odhlášení + 2. Další v pořadí podle rankingu. Náhrada do prvního bodu prvního zápasu odstoupivšího, LL sign-in půl hodiny před začátkem prvního zápasu dne.
- Main best of 5 setů, Q1/Q2 best of 3, Q3 best of 5 (W25-4 str. 7, W25-3, W25-6, W25-14). Rozhodující set při 6:6 tiebreak na 10 s rozdílem 2. Pro Q3 pěti-setový formát nezávisle potvrzen dobovým výsledkem 26. 6.
- Dle ATP Ranking Rulebook 2025 (W25-15, vizuálně ověřena tištěná str. 264 po opětovném dohledání PDF): body za kvalifikaci se přičítají k dosaženému Main výsledku; divoká karta při prohře v prvním kole Main nezíská standardních 10 bodů. Individuální výpočet LL a ostatních výjimek není zde řešen.
- Novinka pořadatele 2025: elektronické hlášení čar na všech kurtech včetně Q a plánované přesunutí obou singlových finále na 16:00 (W25-8); jde o změnu plánovaných pravidel/programu, nikoli náhodnou historickou odchylku.

### 5. Bodování a prize money

Body za dosaženou fázi podle W25-15 (stejné jako v 2024, ověřeno proti dobovému předpisu), odměny za dosaženou fázi v GBP podle W25-5 (originální tabulka vizuálně ověřena).

| Výsledek | Počet příjemců | Body | GBP 2025 | GBP 2024 pro srovnání |
|---|---:|---:|---:|---:|
| Vítěz | 1 | 2000 | 3000000 | 2700000 |
| Finalista | 1 | 1300 | 1520000 | 1400000 |
| SF | 2 | 800 | 775000 | 715000 |
| QF | 4 | 400 | 400000 | 375000 |
| R16 | 8 | 200 | 240000 | 226000 |
| R32 | 16 | 100 | 152000 | 143000 |
| R64 | 32 | 50 | 99000 | 93000 |
| R128 | 64 | 10 | 66000 | 60000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 41500 | 40000 |
| Q2 prohra | 32 | 8 | 26000 | 25000 |
| Q1 prohra | 64 | 0 | 15500 | 15000 |

Kontrola součtů: Main 19414000 GBP, Q 2488000 GBP, obě fáze mužské dvouhry 21902000 GBP. Oficiální celkové odměny za všechny soutěže 52 000 000 GBP, odhad diet 1 500 000 GBP, celkem 53 500 000 GBP (W25-5; nepoužít některé mediální součty 53,55 mil.). Diety na osobu nebyly ověřeny. Prize money vítězů Q není samostatnou další položkou; nevyplňovat nulou jako doloženou platbu. Všechny částky se oproti roku 2024 zvýšily.

### 6. Kontrola pokrytí a zbývající mezery

| Oblast | Stav / podmínky |
|---|---|
| I/T/D/B/P | doloženy plánované údaje, kvóty a tabulky; čtyři stránky originálních losů a oficiální tabulka peněz zkontrolovány |
| H | doložena všechna okna kol, Q denní programy; nerozdělovat vícedenní kola odhadem |
| E | uzávěrky odvozeny z výslovné lhůty, Main los doložen; přesné datum a hodina Q losu, případné výjimky lhůt, individuální cutoffs a původní ATP Detail Sheet nedostupné/NEOVĚŘENY |
| R | Grand Slam předpis 2025 vizuálně ověřen na str. 7,24–32, ATP rankingová pravidla vizuálně ověřena na tištěné str. 264; individuální historické výjimky mimo povinný rozsah |
| Z | dohledatelné dobové zdroje; některé indexované, SHA-256 všech originálů zatím nezískány |
| Další doplňky | míče, přesné hodiny jednotlivých zápasů, vývoj všech náhrad nejsou ověřeny; nejsou podmínkou nominálního rozsahu |

Vizuální podklady potvrzují stejnou plánovanou geometrii jako 2024. Nominální kvóty a body se shodují také s dříve uloženými zdrojovými údaji Grand Slam Draft #1903; zde jde o samostatně ověřený záznam, nikoli nový runtime profil. Další ročník v pořadí Australian Open 2024.

### 7. Zdroje (W25)

- W25-1: [ATP 2025 Wimbledon preview](https://www.atptour.com/en/news/wimbledon-2025-history-draw-schedule), dobový indexovaný text: identita, plán Q/Main, los Main.
- W25-2: [originální Main los 2025](https://www.wimbledon.com/en_GB/scores/draws/2025_MS_draw.pdf), obě strany vizuálně ověřeny, aktualizace 13. 7. 2025.
- W25-3: [originální Q los 2025](https://www.wimbledon.com/en_GB/scores/draws/2025_QS_draw.pdf), obě strany vizuálně ověřeny, aktualizace 3. 7. 2025.
- W25-4: [Grand Slam Rule Book 2025](https://www.wimbledon.com/pdf/Grand_Slam_Rulebook_2025.pdf), tištěné str. 7 a 24–32 (PDF indexy 12,29–37), vizuálně ověřeny.
- W25-5: [Wimbledon Prize Money 2025](https://www.wimbledon.com/pdf/Wimbledon_Prize_Money_2025.pdf), první strana vizuálně ověřena; [ATP prize money](https://www.atptour.com/en/news/wimbledon-2025-prize-money).
- W25-6: oficiální Q OOP: [a 23. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF1.pdf), [b 25. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF3.pdf), [c 26. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF4.pdf), [d 24. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF2.pdf) ; a/b/c první strany a d všechny tři strany vizuálně ověřeny; d obsahuje výhradně ženské Q1.
- W25-7: [dobový plán vysílání ESPN](https://espnpressroom.com/press-release/espn-presents-first-ball-to-last-ball-of-the-championships-wimbledon-2025-june-30-july-13-2025/) a [předturnajový rozpis](https://www.business-standard.com/sports/other-sports-news/wimbledon-2025-schedule-live-timings-ist-live-streaming-telecast-125062900210_1.html).
- W25-8: [oficiální Wimbledon Debenture Handbook 2025](https://www.wimbledon.com/pdf/2025_Debenture_Handbook.pdf), str. 12, oddíl New for 2025, vizuálně ověřena; změna finále a ELC.
- W25-9: [BBC dobový přehled](https://bbc.com.im/sport/tennis/articles/c056ly89q6go), termíny a Roehampton (indexovaný text).
- W25-10: [GOV.UK BST](https://www.gov.uk/when-do-the-clocks-change).
- W25-11: [Radio Times denní harmonogram](https://www.radiotimes.com/tv/sport/tennis/wimbledon-2025-order-of-play/), 13. 7. 2025, všechna okna kol a plán finále.
- W25-12: [Tennis365 předturnajový přehled](https://www.tennis365.com/tennis-features/wimbledon-2025-dates-when-is-draw-prize-money-emma-raducanu-seeded), dobový běžný časový program.
- W25-13: [ATP poslední přímé akceptace 24. 6.](https://www.atptour.com/en/news/wimbledon-2025-last-direct-entries), 16 Q postupových míst.
- W25-14: [BBC kvalifikační finále 26. 6.](https://www.bbc.co.uk/sport/tennis/articles/ckgj184pdrno), pětisetový formát.
- W25-15: [ATP Ranking Rulebook 2025 §IX.G](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf), tištěná str. 264, vizuálně ověřena (po počátečním 403); [ATP turnaj 540](https://www.atptour.com/en/tournaments/wimbledon/540/overview). [ATP Detail Sheet 2025](https://www.protennislive.com/posting/2025/540/ds.pdf) nedostupný při přímém načtení; neoznačovat za ověřený.


## Australian Open 2024

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z. Nezávislá rešerše 2026-11-27. Důležité: plánované Q 8.–11. ledna není skutečně odehrané Q 9.–12. ledna. Obě hodnoty mají odlišný význam; historický posun není náhradou za plán.

### 1. Identita a místo

| Pole | Historická hodnota | Důkaz |
|---|---|---|
| Název | Australian Open | AO24-1 |
| Rok / disciplína / kategorie | 2024 / mužská dvouhra / Grand Slam | AO24-1, AO24-4 |
| ATP tournament ID | 580 | AO24-13 (identita série) |
| Místo Main i Q | Melbourne Park, Batman Avenue, Melbourne VIC 3000, Austrálie | AO24-1, AO24-7 |
| Povrch | tvrdý, GreenSet Cushion | AO24-1 |
| Míče | Dunlop Australian Open | AO24-1 |
| Ředitel / rozhodčí | Craig Tiley / Wayne McKewen | AO24-1 |
| Elektronické rozhodování | ELC Live na všech zápasových kurtech dle fact sheet | AO24-1 |
| Časové pásmo | Australia/Melbourne, v lednu AEDT (UTC+11) | AO24-12 |
| Měna | AUD | AO24-1, AO24-3 |

### 2. Přihlášky, losování a plánované termíny

Primární dobový dokument je AO24 Player Fact Sheet (publikace uvádí 17. 10. 2023), str. 1–2 vizuálně zkontrolovány. U vstupních uzávěrek dokument označuje časové pásmo „EST“, ale hodinu vůbec nepublikuje; zachováváme přesné uvedené datum bez převodu či domyšlené hodiny. Hodiny losování jsou místní program Melbourne.

| Událost | Datum / čas | Důkaz |
|---|---|---|
| Main přihlášky | 2023-12-04, automatické přes ATP/WTA | AO24-1 |
| Žádosti o WC | 2023-12-08 | AO24-1 |
| Q přihlášky | 2023-12-18, Playerzone | AO24-1 |
| Q los mužů | 2024-01-07 15:00 | AO24-1; oznámený plán |
| Q začátek–konec | 2024-01-08–2024-01-11 | AO24-1, AO24-2, AO24-7 |
| Main los | 2024-01-11 13:00 AEDT | AO24-8; fact sheet původně čas TBA |
| Main začátek–konec | 2024-01-14–2024-01-28 | AO24-1, AO24-2, AO24-9 |
| Běžné denní / večerní sessions | 11:00 / 19:00 | AO24-9; nikoli čas každého zápasu |
| Mužské finále | 2024-01-28 večer, Rod Laver Arena | AO24-2; BBC předturnajový čas 19:30, AO24-14; přesný první bod není vyžadován |

Skutečné Q se kvůli dešti uskutečnilo 9.–12. ledna (AO24-10, AO24-15). V Draftu Grand Slam #1903 je uložené skutečné Q 9.–12. 1. a původní 8.–11. 1. v doplňkovém poli; registr podle rozhodnutí vlastníka vybere **původní plán**. Žádný soubor #1903 se zde nemění.

### 3. Nominální harmonogram

| Kolo/fáze | Plánované lokální datum | Uzly | Důkaz |
|---|---|---:|---|
| Q1 | 2024-01-08–09 | 64 | AO24-2 |
| Q2 | 2024-01-10 | 32 | AO24-2 |
| Q3 | 2024-01-11 | 16 | AO24-2 |
| Mezi fázemi, bez mužského kola dle plánu | 2024-01-12–13 | 0 | AO24-1, AO24-2 |
| R128 | 2024-01-14–16 | 64 | AO24-2, AO24-11 |
| R64 | 2024-01-17–18 | 32 | AO24-2, AO24-11 |
| R32 | 2024-01-19–20 | 16 | AO24-2, AO24-11 |
| R16 | 2024-01-21–22 | 8 | AO24-2, AO24-11 |
| QF | 2024-01-23–24 | 4 | AO24-2, AO24-11 |
| Bez plánovaného mužského kola | 2024-01-25 | 0 | AO24-2 |
| SF | 2024-01-26 | 2 | AO24-2, AO24-11 |
| Bez plánovaného mužského kola | 2024-01-27 | 0 | AO24-2 |
| F | 2024-01-28 | 1 | AO24-2, AO24-11 |

Kontrola Q 64+32+16=112, Main 64+32+16+8+4+2+1=127, dohromady 239. Q 4 dny, Main 15 dnů, celkově 21 kalendářních dnů. Třídenní R128 je vědomá novinka ročníku, nikoli důsledek odložených zápasů: pořadatel výslovně oznámil první nedělní zahájení 14. 1. (AO24-2). Přesná plánovaná distribuce zápasů po dnech vícedenních kol není doložena, proto se nedělí rovnoměrně odhadem. Širší označení Opening Week / Qualifying 8.–13. 1. v grafice AO24-2 zahrnuje i rezervní a jiné programové dny, ale konkrétní mužská Q3 je plánována 11. 1.; není důvod měnit konec sportovní fáze na 13. 1.

Pozor na jinou publikaci Tennis Australia „What's new for AO24“: automatický textový výtah její grafiky posouvá některé Main sloupce o den, což odporuje explicitním datům článku pořadatele a původnímu kalendáři. Bez vizuálního ověření ji nepoužíváme jako alternativní autoritu.

### 4. Nominální struktura a dobová pravidla

| Parametr | Main | Q | Důkaz |
|---|---:|---:|---|
| Kapacita a cílový počet hráčů | 128 | 128 | AO24-1 |
| Přímé akceptace | 104 | 119 | AO24-5; součet |
| WC | 8 | 9 | AO24-5, AO24-4 str. 18, AO24-7 |
| Q postupová místa | 16 | 16 vítězů sekcí | AO24-5, AO24-7 |
| Nasazení | 32 | 32 | AO24-5, AO24-6, AO24-16 |
| BYE | 0 | 0 | AO24-6, plné pavouky |
| Formát | vyřazovací | 16 vyřazovacích sekcí po 8 | AO24-5, AO24-6 |
| Kol | 7 | 3 | AO24-5, AO24-6 |
| Zápasových uzlů | 127 | 112 | odvozeno |
| Formát zápasů | best of 5 setů | best of 3 setů ve všech třech kolech | AO24-1 |

Nominální počty: 104+16+8=128, 119+9=128. Všech devět Q divokých karet potvrzuje přímo dobový seznam pořadatele. Main 8 WC zahrnovalo i reciproční přidělení Francii a USA (AO24-4 str. 18). Pravidla Grand Slam 2024 §2/3 (AO24-5): Main nasazení podle rankingu přibližně 7 dnů před akcí, seed 1/2 na protilehlých koncích, ostatní skupiny dle tabulky 128/32; Q dva nasazení na sekci, prvních 16 na horní okraje, druhých 16 losováno na spodní okraje. Před zveřejněním prvního Q OOP se uvolněná pozice seedu obsadí dalším způsobilým seedem, po zveřejnění alternatem. Přímé akceptace dle žebříčku při vstupní uzávěrce. Po skončení Q se vítězové losují do volných Main pozic; sekce nemá předem určené místo. LL přednostně poražení Q3, při nedostatku i dřívější kola; los mezi čtyřmi nejvýše postavenými způsobilými hráči, při více než dvou Main odhlášeních při skončení Q počet odhlášení + 2, poté ranking. Sign-in a okamžik náhrady podle dobového předpisu. Rozhodující set tiebreak na 10 s náskokem 2 při 6:6 (AO24-17).

**Podstatný rozdíl proti Wimbledonu:** Q3 je v Austrálii BO3, nikoli BO5. To není adaptace, jde o skutečný dobový tenisový formát.

Kontrolní historický kontext: dostupné neoficiální vykreslené losy AO24-6 str. 2 a 4 (PDF indexy 1 a 3) mají 128 pozic v obou fázích, Main 8 WC/16 Q/3 LL, Q 9 WC, alternate na pozici 1 místo nasazeného č. 1, tedy 31 označených seedů. Nominální Q seeding zůstává 32; žádná jména ani výsledky se nepřepisují. ITF potvrzuje tři nahrazené Main hráče a osm WC. Přímý oficiální Main/Q PDF se nepodařilo nově získat; dřívější #1903 má Main zdroj, Q marker audit byl neúplný. Neoficiální los slouží jako kontrola geometrie, ne jako jediný důkaz plánovaných pravidel.

### 5. Body a odměny

| Výsledek | Počet příjemců | ATP body | AUD |
|---|---:|---:|---:|
| Vítěz | 1 | 2000 | 3150000 |
| Finalista | 1 | 1300 | 1725000 |
| SF | 2 | 800 | 990000 |
| QF | 4 | 400 | 600000 |
| R16 | 8 | 200 | 375000 |
| R32 | 16 | 100 | 255000 |
| R64 | 32 | 50 | 180000 |
| R128 | 64 | 10 | 120000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 65000 |
| Q2 prohra | 32 | 8 | 44100 |
| Q1 prohra | 64 | 0 | 31250 |

Body: AO24-4 str. 1 (vizuálně), AO24-18 dobové ATP oznámení a předpis. Základní tabulka Main souhlasí s ITF. Q body se přičítají k výsledku Main; výjimka WC při prohře v prvním kole Main 0 bodů, nikoli 10. Individuální historické body LL a náhrad se zde nerekonstruují. Odměny AO24-3, potvrzené ITF pro Main. Aritmetika Main 29775000 AUD (přesná shoda s ITF), Q 4451200 AUD, celkem 34226200 AUD mužská dvouhra včetně Q. Celý turnaj všechny soutěže 86 500 000 AUD. Diety 330 AUD/den od prvního dne příslušné fáze do vyřazení plus 3 dny (AO24-1 str. 2), mimo tabulku odměn.

### 6. Kontrola pokrytí a mezery

| Oblast | Výsledek |
|---|---|
| I, T, E | dobový fact sheet vizuálně ověřen; pořadatel potvrzuje čas Main losu; plán vs skutečnost Q oddělen |
| H | všechna okna kol z původního programu textově; vizualizace velkého PDF selhala, články potvrzují plán; denní počty u vícedenních kol nedopočítávány |
| D | dobový předpis + fact sheet + skutečné losy z nezávislého archivního zobrazení, počet WC potvrzen pořadatelem a ITF |
| R | dobový předpis dostupný v textovém zrcadle, přímé ITF PDF 404, ATP PDF 403; formát AO přímo fact sheet |
| B, P | ITF hlavní tabulka vizuálně ověřena, Q body dobové ATP oznámení, odměny Q přímo pořadatel, kontrolní součty bez rozporu |
| Z | zdroje dohledatelné, přímý originální ATP detail/draw PDF nedostupný; žádné SHA-256 nedoloženy |
| Mimo nominální rozsah | individuální cutoffs, výsledky, přesné časy skutečných zápasů a kompletní změny obsazení |

Závěr: nominální profil pokrývá všech 9 oblastí s vyznačenými omezeními důkazů. Nejde o stoprocentní historickou certifikaci. Rozdíl plán/skutečnost proti #1903 je věcně zdůvodněn, nikoli chyba skutečného data v #1903. Další ročník Roland Garros 2024.

### 7. Zdroje (AO24)

- AO24-1: [Tennis Australia — AO24 Player Fact Sheet](https://www.tennis.com.au/wp-content/uploads/2023/11/AO24-Player-Fact-Sheet.pdf), 17. 10. 2023, str. 1–2 vizuálně ověřeny.
- AO24-2: [oficiální původní kalendář PDF](https://ausopen.com/sites/default/files/2023-10/ao24-provisional-schedule.pdf) (textový výtah, screenshot selhal kvůli velikosti); [článek pořadatele 9. 11. 2023](https://ausopen.com/articles/news/australian-open-2024-provisional-schedule-unveiled). Kontrola alternativy: [What's new for AO24](https://www.tennis.com.au/wp-content/uploads/2023/12/Whats-new-for-AO24-2912-1.pdf), neověřený grafický výtah neautoritativní.
- AO24-3: [pořadatel — prize money](https://ausopen.com/articles/news/australian-open-prize-money-hits-record-high-10-million-increase-2024).
- AO24-4: [ITF — Men's Tournament Preview 2024](https://www.world.tennis/media/11625/2024-australian-open-mens-tournament-preview-third-edition.pdf), str. 1 a 18 vizuálně.
- AO24-5: [Grand Slam Rule Book 2024](https://www.itftennis.com/media/5986/grand-slam-rule-book-2024-f3.pdf) (přímé PDF 404); [textové zrcadlo dobového předpisu](https://www.scribd.com/document/807392104/grand-slam-rulebook-2024), tištěné str. 24–30. Důkaz z doplňkového zrcadla explicitně označen.
- AO24-6: [nezávislý archiv losů](https://donald.au/tennis/2024/2024-australian-open-singles.pdf), str. 2 a 4 vizuálně; nejde o originální pořadatelský soubor. [Sky Sports Main draw](https://www.skysports.com/tennis/news/13046191/australian-open-mens-singles-draw-as-novak-djokovic-looks-to-win-11th-title-in-melbourne). [Dřívější oficiální Main odkaz #1903](https://ausopen.com/sites/default/files/2026-11/draw_ms_2024-01-28_2336.pdf) při této rešerši nedostupný; protennislive /posting/2024/580/{ds,mds,qs}.pdf rovněž nedostupné.
- AO24-7: [pořadatel — Q wildcards](https://ausopen.com/articles/news/australian-open-qualifying-wildcards-announced), devět mužských WC, plán Q; [Q entry list](https://ausopen.com/articles/news/australian-open-2024-qualifying-events-set-thrill-fans).
- AO24-8: [pořadatel — Main draw ceremony 11. 1.](https://ausopen.com/articles/news/where-watch-australian-open-2024-draw), 13:00 AEDT.
- AO24-9: [ATP preview 2024](https://www.atptour.com/en/news/australian-open-2024-history-draw-schedule), indexovaný text, přímý přístup 403.
- AO24-10: [pořadatel — začátek Q 9. 1.](https://ausopen.com/articles/news/goffin-leads-mens-winners-ao-2024-qualifying-begins); [konec Q 12. 1.](https://ausopen.com/articles/news/aussies-open-jasika-sweeny-hunter-complete-dream-qualifying-runs).
- AO24-11: [Nine, předturnajový program 11. 1.](https://www.nine.com.au/sport/tennis/australian-open-2024-schedule-dates-players-draw-odds-prize-money-tickets-everything-need-to-know-ultimate-guide-20240111-p5j8yt.html).
- AO24-12: [Victoria — daylight saving](https://business.vic.gov.au/business-information/daylight-saving), [Tourism Australia time zones](https://www.australia.com/en/facts-and-planning/about-australia/time-zones.html).
- AO24-13: [ATP series 580](https://www.atptour.com/en/tournaments/australian-open/580/overview); identity series, not evidence of year-specific dates.
- AO24-14: [BBC — předturnajový program](https://www.bbc.co.uk/sport/tennis/67863460).
- AO24-15: [historický přehled Q, posun kvůli dešti](https://en.wikipedia.org/wiki/2024_Australian_Open_%E2%80%93_Men%27s_singles_qualifying), doplňkový zdroj potvrzených krajních dnů, ne primární plán.
- AO24-16: [pořadatel — seed list 10. 1.](https://ausopen.com/articles/news/seed-list-confirmed-australian-open-2024).
- AO24-17: [Grand Slam Board — rozhodující tiebreak](https://ausopen.com/articles/news/grand-slams-jointly-adopt-10-point-final-set-tiebreak).
- AO24-18: [ATP oznámení bodů pro 2024](https://www.atptour.com/en/news/2024-rankings-points-update); [ATP Rulebook IX 19. 3. 2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-9_pif-atp-rankings_19mar.pdf) (indexovaný text); [dobový přehled pravidel](https://openerarankings.com/RankingRules2024).


## Roland Garros 2024

**Stav:** HOTOVO v nominálním rozsahu, 9/9 oblastí. Denní Q2 byl ověřen samostatnou kontrolou všech identifikátorů oficiálního OOP. Nezávislá rešerše 2026-11-27. Referencí zůstává nominální plán, ne historické odklady.

### 1. Identita a místo

| Pole | Historická hodnota | Důkaz |
|---|---|---|
| Název | Roland-Garros / French Open | RG24-1, RG24-2 |
| Rok / disciplína / kategorie | 2024 / mužská dvouhra / Grand Slam | RG24-1 |
| ATP tournament ID | 520 | RG24-16 |
| Dějiště Main a Q | Stade Roland-Garros, Paříž, Francie | RG24-2, RG24-3 |
| Povrch | venkovní antuka | RG24-1, RG24-2 |
| Časové pásmo | Europe/Paris; CEST UTC+02:00 v květnu a červnu | RG24-2, RG24-3 |
| Míče | Wilson Roland Garros | RG24-2 |
| Pořadatel | Fédération Française de Tennis (FFT) | RG24-4 |
| Ředitelka | Amélie Mauresmo | RG24-4 |
| Měna | EUR | RG24-1 |
| Rozhodčí | Rémy Azémar | RG24-9, podpis v programu 22. 5. |
| Individuální diety | NEOVĚŘENO | doplňková metadata |

### 2. Termíny, přihlášky a losování

| Událost | Plánované datum/čas, místní (není-li uvedeno jinak) | Důkaz |
|---|---|---|
| Main vstupní datum žebříčku / uzávěrka | 2024-04-15 | odvozeno z 42 dnů před pondělím 27. 5.; mužská entry list zveřejněna 16.–17. 4. a přehled WTA potvrzuje toto datum pro stejný turnaj. Přesnou hodinu ani výjimku neověřujeme. RG24-5, RG24-6, RG24-14 |
| Q vstupní datum žebříčku / uzávěrka | 2024-04-29 | odvozeno z 28 dnů před pondělím 27. 5.; WTA přehled téhož turnaje jako podpůrný doklad, nikoli mužský originál. RG24-5, RG24-14 |
| Oznámení WC | 2024-05-14 | RG24-4 |
| Los Q | 2024-05-19, ne před 14:00 | RG24-7; archivní kopie losu označena 19. 5. 14:27, RG24-8 |
| Q alternate sign-in první den | 2024-05-20 09:30 | dobový OOP RG24-9 |
| Q | 2024-05-20–2024-05-24 | RG24-3, RG24-4, RG24-7 |
| Main los | 2024-05-23 14:00 | pořadatel RG24-10 |
| Main | 2024-05-26–2024-06-09 | RG24-1, RG24-2, RG24-4, RG24-7 |
| Mužské finále | 2024-06-09 15:00 oznámený čas; 15:10 plán první výměny | dubnový časový plán RG24-3; ne tvrzení o skutečném prvním bodu |

Časový plán RG24-3 explicitně označuje všechny časy jako pařížské GMT+2. První tři Q dny mají veřejný začátek 10:00, 23.–24. 5. venkovní kurty 11:00, Suzanne-Lenglen 13:00; veřejný čas pro diváky může být dřívější než příchod hráčů. Běžné hlavní dny 26.–28. 5. na Philippe-Chatrier denní program 12:00, noční veřejný čas 20:15 / plánovaný první míč 20:30; jiné kurty zpravidla 11:00. Toto jsou časy programu, nikoli začátky každého zápasu.

### 3. Nominální harmonogram

| Kolo / fáze | Místní datum | Nominální uzly | Důkaz |
|---|---|---:|---|
| Q1 | 2024-05-20–21 | 64 | RG24-9, RG24-11 |
| Q2 | 2024-05-22 | 32 | RG24-9, oficiální OOP vydaný 21. 5. 18:09: všech 32 identifikátorů QM032–QM063 |
| Q3 | 2024-05-23–24 | 16 | RG24-3, RG24-7, RG24-9, RG24-11; denní program a konec Q |
| Mezera mezi Q/Main | 2024-05-25 | 0 | RG24-4 |
| R128 | 2024-05-26–28 | 64 | RG24-12, RG24-13 |
| R64 | 2024-05-29–30 | 32 | RG24-12, RG24-13 |
| R32 | 2024-05-31–06-01 | 16 | RG24-12 |
| R16 | 2024-06-02–03 | 8 | RG24-12 |
| QF | 2024-06-04–05 | 4 | RG24-12 |
| Bez mužské dvouhry | 2024-06-06 | 0 | RG24-12 |
| SF | 2024-06-07 | 2 | RG24-12 |
| Bez mužské dvouhry | 2024-06-08 | 0 | RG24-12 |
| F | 2024-06-09 | 1 | RG24-3, RG24-12 |

Q 5 kalendářních dnů; Main 15 dnů; celé okno 21 dnů. Celkově Q 112 + Main 127 = 239 nominálních uzlů. Kontrola H: OOP vydaný 21. 5. v 18:09 obsahuje na třech stranách právě všech 32 různých identifikátorů QM032–QM063 (seřazeno, bez mezer), tedy kompletní Q2 plán 22. 5.; program 23. 5. vydaný 22. 5. v 18:55 obsahuje výhradně osm mužských Q3 identifikátorů QM018, QM024–QM030. Předběžná domněnka o Q2 23. 5. byla vyvrácena identifikací kola, nikoli odhadem podle výsledků. Q3 23.–24. 5. je doložené okno; osm plánovaných zápasů 23. 5. je potvrzeno, původní předturnajový detail 24. 5. samostatně nezískán. U Main kola zůstávají původní okna, navzdory dešti 29.–30. 5. (RG24-13). Předturnajový článek Sky Sports obsahuje posunuté číselné datum u prvních dnů (např. neděle 25. 5., což byl ve skutečnosti sobotní den); jako důkaz těchto dnů používáme konzistentní předturnajový kalendář a datované ATP notes, nikoli chybná čísla Sky. Neodhadovat rozložení všech uzlů rovnoměrně na dny.

### 4. Nominální struktura a pravidla

| Parametr | Main | Q | Důkaz |
|---|---:|---:|---|
| Kapacita / cíloví účastníci | 128 | 128 | RG24-8, RG24-15 |
| Přímé akceptace | 104 | 119 | dobový Grand Slam předpis RG24-5 a kontrola součtu |
| WC | 8 | 9 | přímo mužské oznámení pořadatele RG24-4 |
| Q postupová místa | 16 | 16 vítězů sekcí | RG24-1, RG24-8 |
| Nasazených | 32 | 32 | RG24-1, RG24-8, RG24-15 |
| BYE | 0 | 0 | obě strany obou losů RG24-8, RG24-15 |
| Kola | 7 | 3 | RG24-8, RG24-15 |
| Struktura | vyřazovací pavouk | 16 vyřazovacích sekcí po 8 | RG24-8 |
| Uzly | 127 | 112 | odvozeno |
| Formát | BO5 setů | BO3 setů ve všech kolech | RG24-5, RG24-11 |

Kontrolní součty Main 104+8+16=128 a Q 119+9=128. Dobový Grand Slam předpis 2024 (RG24-5): Main seed 1 a 2 na protilehlých krajích a ostatní ve skupinách podle tabulky 128/32, Q seedy 1–16 na horní a 17–32 losované na spodní pozice sekcí. Přímá akceptace podle příslušného rankingu při uzávěrce, Main nasazení zpravidla podle žebříčku 7 dnů před turnajem. Před zveřejněním prvního Q OOP uvolněný seed nahradí další způsobilý seed, poté alternate. Q vítězové se losují do volných Main míst po skončení Q. LL přednostně z poražených Q3 (poté podle potřeby dřívější kola), losování mezi čtyřmi nejvýše postavenými způsobilými hráči, při více než dvou Main odhlášeních při skončení Q velikost losované skupiny = odhlášení + 2. Další dle rankingu. Sign-in půl hodiny před prvním zápasem dne a náhrada před prvním bodem prvního zápasu odstoupivšího. Rozhodující set tiebreak na 10 s rozdílem 2 při 6:6 (RG24-5, RG24-17).

Původní Q los 19. 5. 14:27 (kopie RG24-8, obě strany vizuálně): 128 pozic, 32 seedů, devět označených WC; pořadatelem oznámený seznam 14. 5. má rovněž 9 WC, ale jedno jméno se před losem změnilo. Počet se nemění. Main los aktualizovaný 4. 6. (RG24-15, obě strany vizuálně): 128 míst, 32 seedů, 8 WC, 16 Q, 3 LL, nulové BYE. ATP předturnajový přehled uváděl dva LL, pozdější los tři; jde o rozdíl okamžiku zveřejnění, nikoli strukturální rozpor. Původní los i pozdější stav mají svou hodnotu jako zdroj, nic z toho nepřepisuje nominální kvóty.

### 5. Body a odměny

| Výsledek | Příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 2000 | 2400000 |
| Finalista | 1 | 1300 | 1200000 |
| SF | 2 | 800 | 650000 |
| QF | 4 | 400 | 415000 |
| R16 | 8 | 200 | 250000 |
| R32 | 16 | 100 | 158000 |
| R64 | 32 | 50 | 110000 |
| R128 | 64 | 10 | 73000 |
| Q postupující | 16 | 30 | samostatná částka neuvedena |
| Q3 prohra | 16 | 16 | 41000 |
| Q2 prohra | 32 | 8 | 28000 |
| Q1 prohra | 64 | 0 | 20000 |

Main částky/body přímo dobový ATP přehled RG24-1 str. 5 (indexovaný text; screenshot 403). Q odměny z nezávislých přehledů RG24-18, Q3 potvrzuje dobový ATP článek RG24-19 a WTA článek uvádí rozdíl 32 000 mezi Q3 prohrou a Main R128. Q body dle mužského ATP předpisu RG24-20. Nezaměňovat odlišné ženské body ve WTA článcích. Řádné Q body přičteny k Main; WC prohra R128 bez bodů dle dobového ATP předpisu. Individuální LL bodové výjimky zde nepočítáme.

Nominální aritmetické součty Main 19280000 EUR, Q 2832000 EUR, celkem 22112000 EUR (mužská dvouhra, nikoli celková dotace všech disciplín). Celoturnajová dotace 53 478 000 EUR podle dobových zpráv. Pozor: údaj 24 961 000 EUR v ATP preview není prostým součtem těchto dvou singlových tabulek; nerozšiřujeme jej bez doložení jeho rozsahu.

### 6. Evidence a mezery

| Oblast | Stav |
|---|---|
| I/T | ověřeno více dobovými zdroji včetně pořadatele |
| H | všechna okna kol doložena; Q2 32/32 unikátních identifikátorů ve třech stranách předem vydaného OOP, Q3 23. 5. osm identifikátorů; časové a denní odchylky nezaměňovat za plán |
| E | nominální kvóty a losovací termíny doloženy, vstupní data odvozena z předpisu; originální mužský detail sheet chybí |
| D | obě strany Main PDF a obě strany archivní kopie Q PDF vizuálně ověřeny; nominální struktura bez rozporu |
| R/B | 2024 rulebook dostupný přes dříve doložený textový zdroj, ATP mužské body přímo v dobovém preview; Q výsledky a struktura potvrzují formát |
| P | Main přímo ATP, Q shoda dostupných nezávislých tabulek, kontrola součtů; původní PDF dotace Q nebylo získáno |
| Z | dobové zdroje doloženy; některé PDF screenshoty 403/500; žádné SHA-256 nepředstíráme |

Nominální rozsah je uzavřen, s výše uvedenými omezeními zdrojů; další ročník US Open 2024. Do stávajících balíčků ani Grand Slam Draft #1903 se nezasahuje.

### 7. Zdroje (RG24)

- RG24-1: [ATP men's tournament preview 2024](https://www.atptour.com/-/media/5275ccac675646a0bb7f172776df7588.pdf), str. 3 (seeds, WC, Q, LL), str. 5 (body/odměny), text; screenshot 403.
- RG24-2: [WTA dobové informace 22. 5.](https://www.wtatennis.com/news/4025655/roland-garros-2024-draws-dates-prize-money-and-what-you-need-to-know), lokalita, povrch, časové pásmo, míče a termíny; ženské body nepoužívat.
- RG24-3: [FFT časový harmonogram z dubna 2024](https://rg-organisation.fft.fr/sites/default/files/2024-04/RG24%20-%20tableau%20des%20horaires.pdf), text tabulek získán, screenshot 500 (údržba).
- RG24-4: [FFT oznámení mužských a ženských WC 14. 5.](https://www.rolandgarros.com/en-us/article/2024-wildcards-men-women-singles-qualifying-rounds).
- RG24-5: dobový Grand Slam Rule Book 2024 §2/3 a scoring; viz AO24-5 / S16 v témže dokumentu; textové zrcadlo, ne nově vizuálně ověřený originál.
- RG24-6: [ATP entry list 17. 4.](https://www.atptour.com/en/news/roland-garros-2024-entry-list), [pořadatel 16. 4.](https://www.rolandgarros.com/en-us/article/roland-garros-2024-entry-list-men-women-protected-ranking).
- RG24-7: [ATP dobový přehled](https://www.atptour.com/en/news/roland-garros-2024-history-draw-schedule), indexovaný text, přímé 403; [pořadatel Q los 19. 5.](https://www.rolandgarros.com/en-us/article/qualifying-draws-unveiled-roland-garros-2024).
- RG24-8: [kopie originálního Q losu 19. 5. 14:27](https://www.tiebreaktennis.it/wp-content/uploads/2024/05/Roland-Garros-2024-Qualificazioni-maschili.pdf), obě strany vizuálně; [originál aktualizovaný 20. 5.](https://rg-organisation.fft.fr/sites/default/files/2024-05/Mens_Qualifying_20240520220332.pdf), text dostupný, screenshot 500.
- RG24-9: archivované dobové OOP: [20. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240520_OF_1716134216.pdf), [21. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240521_OF_1716224247.pdf), [22. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240522_OF_1716314941.pdf), [23. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240523_OF_1716404146.pdf), OOP 22. 5. (vydán 21. 5. 18:09) všechny tři strany a OOP 23. 5. (vydán 22. 5. 18:55) celá strana vizuálně ověřeny, včetně identifikátorů a rozhodčího; 20./21. 5. indexovaný text.
- RG24-10: [pořadatel — los Main 23. 5. 14:00](https://www.rolandgarros.com/en-us/article/rg2024-watch-the-roland-garros-2024-draw-ceremony-live).
- RG24-11: [pořadatel — Q výsledky 22. 5.](https://www.rolandgarros.com/en-us/order-of-play?annexeCourt=all&competition=all&country=all&date=2024-05-22&favoriteFilter=false&principalCourt=all&year=2024), [23. 5. Q3](https://www.rolandgarros.com/en-us/article/rg2024-qualifying-and-draw-day---thursday-may-23-live), [24. 5.](https://www.rolandgarros.com/en-us/order-of-play?annexeCourt=all&competition=all&country=ITA&date=2024-05-24&favoriteFilter=false&principalCourt=all&year=2024).
- RG24-12: [předturnajový rozpis 2024](https://uk.sports.yahoo.com/news/french-open-2024-full-schedule-164350297.html), [provisional schedule kopie](https://static1.squarespace.com/static/5f1d6e50195f36727ee1723e/t/65e3375b69e1e96311a4b24d/1709389660028/French%2BOpen%2BTennis%2B2024.pdf) (indexovaný text); [Sky dobový program](https://www.skysports.com/tennis/news/13141712/french-open-2024-draw-schedule-for-men-s-women-s-singles-featuring-andy-murray-rafael-nadal-novak-djokovic-coco-gauff) použít jen konzistentní data druhého týdne.
- RG24-13: [ATP den 1](https://www.atptour.com/-/media/039f1c8495c94cf29ab43a44b16341f3.pdf), [den 2](https://www.atptour.com/-/media/9e71a713ef744adabbb9aabc139d412a.pdf), [den 3](https://www.atptour.com/-/media/6cbd8d0cc0e84330b8f22f11c4d781b4.pdf), [déšť 29. 5.](https://www.atptour.com/en/news/rain-roland-garros-2024-wednesday), indexované texty.
- RG24-14: [FFT/WTA Q acceptance list](https://rg-organisation.fft.fr/sites/default/files/2024-05/RolandGarrosQLF2024Update%20V2.pdf), podporuje data 15./29. 4., ale není mužský dokument; screenshot 500.
- RG24-15: [FFT Main los aktualizovaný 4. 6. 22:54](https://rg-organisation.fft.fr/sites/default/files/2024-06/Mens_Singles_20240604225512.pdf), obě strany vizuálně ověřeny.
- RG24-16: [ATP série 520](https://www.atptour.com/en/tournaments/roland-garros/520/overview) identifikátor.
- RG24-17: Grand Slam Board změna rozhodujícího tiebreaku, viz AO24-17.
- RG24-18: [nezávislá tabulka odměn](https://salarysport.com/tennis/roland-garros/2024/prize-money/), [přehled 2024](https://en.wikipedia.org/wiki/2024_French_Open), [dobové Reuters](https://www.reuters.com/sports/tennis/french-open-2024-prize-money-how-much-do-winners-mens-womens-doubles-finals-get-2024-05-21/).
- RG24-19: [ATP odměny 2024](https://www.atptour.com/en/news/roland-garros-2024-prize-money) indexovaný text, 403; [WTA vysvětlení odměny Q3 vs Main](https://www.wtatennis.com/news/4027889/qualifying-at-roland-garros-the-grueling-journey-that-can-change-careers).
- RG24-20: mužský ATP Rulebook IX a oznámení 2024 viz AO24-18 / S18.

## US Open 2024

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z. Kontrola 2026-11-27. Žádný převod na squash.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / ročník | US Open 2024, mužská dvouhra | US24-1, US24-2 |
| Kategorie / ATP ID | Grand Slam / 560 | US24-1, US24-13 |
| Místo Main a Q | USTA Billie Jean King National Tennis Center, Flushing Meadows, Queens, New York, USA | US24-1, US24-3, US24-4 |
| Povrch | venkovní tvrdý | US24-1 |
| Časové pásmo | America/New_York; EDT UTC−04:00 v uvedeném období | místní ET v US24-4/5/6, letní offset |
| Pořadatel / měna | USTA / USD | US24-4, US24-9 |
| Míče, rozhodčí, diety | NEOVĚŘENO | doplňková metadata; nepřebírat z jiného ročníku |

### 2. Přihlášky a plánované termíny

| Událost | Místní údaj | Evidence |
|---|---|---|
| Main entry deadline | 2024-07-15 | 42 dnů před pondělím 26. 8.; oficiální mužská entry list označena 15. 7. (US24-7), hodina nedoložena |
| Q entry deadline | 2024-07-29 | 28 dnů před 26. 8.; oficiální mužská entry list označena 29. 7. (US24-8), hodina nedoložena |
| Oznámení WC | 2024-08-14 | US24-10 |
| Q los | zveřejněn nejpozději 2024-08-18 | US24-11; přesná hodina a okamžik losování neověřeny |
| Q | 2024-08-19–22, denní start 11:00 | US24-1, US24-4, US24-5 |
| Main los | 2024-08-22 12:00 | US24-1 |
| Main | 2024-08-26–09-08 | US24-1, US24-6 |
| Mužské finále | 2024-09-08 14:00, oznámený program | US24-6, US24-12 |

Entry listy nejsou konečné losy. Datum doloženo jejich zápatím a odvozením z 42/28denního pravidla; původní ATP Detail Sheet nebyl v této rešerši získán. Čas není uměle doplněn. Program běžného dne od 11:00 ET (US24-1/6); přesné začátky jednotlivých zápasů mimo rozsah.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální uzly | Důkaz |
|---|---|---:|---|
| Q1 | 2024-08-19–20 | 64 | US24-5 |
| Q2 | 2024-08-21 | 32 | US24-5 |
| Q3 | 2024-08-22 | 16 | US24-5 |
| Mezi fázemi | 2024-08-23–25 | 0 | US24-1 |
| R128 | 2024-08-26–27 | 64 | US24-6 |
| R64 | 2024-08-28–29 | 32 | US24-6 |
| R32 | 2024-08-30–31 | 16 | US24-6 |
| R16 | 2024-09-01–02 | 8 | US24-6 |
| QF | 2024-09-03–04 | 4 | US24-6 |
| Bez plánované mužské dvouhry | 2024-09-05 | 0 | US24-6 |
| SF | 2024-09-06 | 2 | US24-6 |
| Bez plánované mužské dvouhry | 2024-09-07 | 0 | US24-6 |
| F | 2024-09-08 | 1 | US24-6, US24-12 |

Q 4 dny, Main 14 dnů, celé okno 21 dnů. Součty 112 Q a 127 Main = 239 nominálních uzlů. Denní rozdělení vícedenních kol není mechanicky 50/50. Předturnajový vysílací rozpis Q výslovně uvádí kola a ATP/ESPN potvrzují čtyřdenní plán; odklady jednotlivých zápasů nepřepisují nominální data.

### 4. Nominální struktura a pravidla

| Pole | Main | Q |
|---|---:|---:|
| Kapacita a účastníci | 128 | 128 |
| Přímé akceptace | 104 | 119 |
| WC | 8 | 9 |
| Nasazení | 32 | 32 |
| Q postupová místa | 16 | 16 |
| BYE | 0 | 0 |
| Kola | 7 | 3 |
| Uzly | 127 | 112 |
| Formát | BO5 setů | BO3 setů ve všech kolech |

Dobový rulebook 2024 (S16/AO24-5) a originální losy US24-2/3; kvóty WC také přímo pořadatel US24-10. 104+16+8=128, 119+9=128. Q 16 vyřazovacích sekcí po osmi, dva seedy na sekci (prvních 16 horní pozice, dalších 16 los na spodní); Main 32 seedů dle dobové skupinové tabulky. Přímý vstup dle rankingu při uzávěrce včetně případného protected ranking; Main seeding dle příslušného rankingu přibližně týden před turnajem. Náhrada odstoupeného Q seedu před prvním OOP dalším seedem, potom alternatem; Q vítězové losováni na volné Main pozice po Q. LL přednostně poražení Q3, při nedostatku i dřívější kola, los nejvýše postavených čtyř (při více než dvou odstoupeních při skončení Q počet +2), dále ranking; náhrada před prvním bodem prvního zápasu odstoupivšího; sign-in 30 minut před prvním zápasem. Tiebreak na 10 při 6:6 rozhodujícího setu (S20). Q BO3 potvrzeno výsledky všech tří kol v originálním losu, ne extrapolací z Wimbledonu.

**Kontrola označení původních losů:** vizuálně obě strany Main i Q. Main 7 viditelných W (6,10,21,58,59,93,99), 16 Q (3,5,12,30,34,51,52,63,66,68,69,101,102,111,124,127), 1 L (95). Na pozici 114 chybí W, ale pořadatel přímo potvrdil, že Dominic Thiem měl WC (US24-10/14). Rekonciliace: 8 WC + 16 Q + 1 LL + 103 ostatních = 128; samotné PDF 104 neoznačených pozic. Q devět W (27,34,38,59,71,90,94,98,124), žádná A značka; 119 neoznačených. Oba losy 32 seedů bez BYE. Jedna LL není plánovaná kvóta. Shoda s dřívějším Draft #1903, bez změny jeho souborů.

### 5. Body a prize money

| Výsledek | Počet příjemců | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 2000 | 3600000 |
| Finalista | 1 | 1300 | 1800000 |
| SF | 2 | 800 | 1000000 |
| QF | 4 | 400 | 530000 |
| R16 | 8 | 200 | 325000 |
| R32 | 16 | 100 | 215000 |
| R64 | 32 | 50 | 140000 |
| R128 | 64 | 10 | 100000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 52000 |
| Q2 prohra | 32 | 8 | 38000 |
| Q1 prohra | 64 | 0 | 25000 |

Odměny přímo pořadatel 7. 8. 2024, US24-9; body dobový ATP preview US24-1 a dříve doložený 2024 rankingový předpis S18. Q body přičíst k dosaženému Main výsledku; WC prohra v prvním kole Main 0, nikoli 10. Individuální body historických LL se nepočítají. Nominální součet Main 26440000 USD, Q 3648000 USD, celkem 30088000 USD; celoturnajová kompenzace 75 000 000 USD zahrnuje jiné soutěže a další položky, nikoli pouze mužskou dvouhru.

### 6. Kontrola a mezery

I/T/H/D/B/P pokryty dobovými zdroji. E: ověřeny první strany obou originálních entry listů a text zápatí, přesný čas Q losu neověřen. R: dobový předpis 2024 zdroj S16/AO24-5 (dřívější textové zrcadlo), nikoli nově získané originální bajty; výsledky Q potvrzují formát. Z: čtyři strany originálních losů vizuálně ověřeny, ATP preview indexovaný text (403), žádný hash není prohlašován za získaný. Všechna povinná nominální pole doložena; doplňková metadata otevřena. Další Australian Open 2025.

### 7. Zdroje (US24)

- US24-1: [ATP dobový preview](https://www.atptour.com/en/news/us-open-2024-history-draw-schedule), indexovaný text, přímé 403.
- US24-2: [USTA originální Main los](https://www.usopen.org/en_US/scores/draws/2024_MS_draw.pdf), obě strany vizuálně ověřeny.
- US24-3: [USTA originální Q los](https://www.usopen.org/en_US/scores/draws/2024_MQ_draw.pdf), obě strany vizuálně ověřeny.
- US24-4: [ESPN čtyřdenní Q plán](https://espnpressroom.com/press-release/all-four-days-of-the-2024-us-open-qualifying-tournament-live-and-exclusively-on-espn-platforms-starts-monday-august-19/).
- US24-5: [dobový plán Q jednotlivých kol](https://www.sportingnews.com/us/tennis/news/us-open-qualifying-schedule-2024-dates-channels-live-streams-tennis/95e7e59f1c1e9e4109a42b71).
- US24-6: [TNT předturnajový plán všech Main kol](https://www.tntsports.co.uk/tennis/us-open/2024/when-start-draw-schedule-who-is-playing-prize-money-preview_sto20030307/story.shtml), [ESPN dobový vysílací plán](https://espnpressroom.com/press-release/espns-exclusive-first-ball-to-last-ball-coverage-of-the-2024-us-open-august-26-september-8/). TNT má nesouhlasný čas finále v úvodní větě, správný 19:00 UK v tabulce = 14:00 EDT; přímá potvrzení US24-12.
- US24-7: [USTA Main entry list 15. 7.](https://www.usopen.org/pdf/2024_USO_men_MD_entry_list.pdf), str. 1 vizuálně, zápatí textově.
- US24-8: [USTA Q entry list 29. 7.](https://www.usopen.org/pdf/mens-qualifying-2024-USO-entry-list.pdf), str. 1 vizuálně, zápatí textově.
- US24-9: [USTA oficiální odměny 7. 8.](https://www.usopen.org/amp/en_US/news/articles/2024-08-07/2024_us_open_prize_money_will_be_largest_purse_in_tennis_history.html).
- US24-10: [USTA oznámení Main a Q WC 14. 8.](https://www.usopen.org/en_US/news/articles/2024-08-14/former_mens_champions_thiem_wawrinka_among_2024_us_open_wild_cards.html).
- US24-11: [USTA kvalifikační preview 18. 8.](https://www.usopen.org/en_US/news/articles/2024-08-18/can_the_next_generation_of_us_women_make_noise_in_2024_us_open_qualifying.html), odkazuje již na mužský los; přesný čas losování neznámý.
- US24-12: [USTA finálový program 5. 9.](https://www.usopen.org/en_US/news/articles/2024-09-05/mickey_guyton_ruben_studdard_to_perform_during_2024_us_open_finals_weekend.html), 14:00 ET.
- US24-13: [ATP série 560](https://www.atptour.com/en/tournaments/us-open/560/overview), identifikátor série.
- US24-14: [USTA potvrzení Thiemovy WC 26. 8.](https://www.usopen.org/en_US/news/articles/2024-08-26/ben_shelton_defeats_former_us_open_champion_dominic_thiem_at_austrians_last_slam.html).


## Australian Open 2025

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z, s označenými doplňkovými mezerami. Rešerše 2026-11-27. Zachován reálný tenis bez převodu.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / ročník / disciplína | Australian Open 2025, mužská dvouhra | AO25-1/2 |
| Kategorie / ATP ID | Grand Slam / 580 | AO25-2, AO24-13 (identita série) |
| Dějiště Main a Q | Melbourne Park, Melbourne, Victoria, Austrálie | AO25-1/2 |
| Povrch | tvrdý | AO25-2 |
| Časové pásmo | Australia/Melbourne, AEDT UTC+11 během obou fází | AO25-3 (AEDT), AO24-12 (pravidlo letního času ve Victorii) |
| Pořadatel / měna | Tennis Australia / AUD | AO25-4/5/6 |
| Míče, konkrétní typ povrchu a rozhodčí | NEOVĚŘENO pro ročník 2025 | doplňková metadata; nepřebírat z AO24 |

### 2. Přihlášky, losování a termíny

| Událost | Datum / čas | Důkaz |
|---|---|---|
| Main uzávěrka | 2024-12-02 | výslovně v zápatí originálního mužského entry listu AO25-4 |
| Q uzávěrka | 2024-12-16 | výslovně v zápatí originálního mužského Q entry listu AO25-5 |
| Q los | již existoval 2025-01-05; přesný okamžik NEOVĚŘEN | AO25-10; dobový přehled Tennis Australia již uvádí konkrétní soupeře |
| Q | 2025-01-06–09 | AO25-1/2/7 |
| Q běžný start | 6.–8. 1. 10:00, 9. 1. 11:00 | AO25-2, oznámený program |
| Main los | 2025-01-09 14:30 AEDT | přímo pořadatel AO25-3 |
| Main | 2025-01-12–26 | AO25-1/2 |
| Finále | 2025-01-26 | AO25-1/9 |

Obě uzávěrky odpovídají též 42/28 dnům před prvním pondělím Main 13. 1.; žádná hodina nebyla domyšlena. Entry listy jsou aktualizované k 29. 12. 2024, nikoli aktuální ranking k tomuto dni: jejich rankovací datum je výslovně datum uzávěrky. Main los plánován ještě v průběhu finálového kola Q. Pořadatel přímo vysvětluje, že volná Q místa jsou nejdříve označena zástupným textem a konkrétní kvalifikanti se přiřazují po skončení Q (AO25-3).

### 3. Nominální harmonogram

| Kolo | Lokální datum / okno | Nominální uzly | Důkaz |
|---|---|---:|---|
| Q1 | 2025-01-06–07 | 64 | AO25-1/8 |
| Q2 | 2025-01-08 | 32 | AO25-8/11 |
| Q3 | 2025-01-09 | 16 | AO25-7/8 |
| Mezi fázemi | 2025-01-10–11 | 0 | AO25-1 |
| R128 | 2025-01-12–14 | 64 | AO25-1/9 |
| R64 | 2025-01-15–16 | 32 | AO25-1/9 |
| R32 | 2025-01-17–18 | 16 | AO25-9 |
| R16 | 2025-01-19–20 | 8 | AO25-9 |
| QF | 2025-01-21–22 | 4 | AO25-9 |
| Bez plánovaného mužského kola | 2025-01-23 | 0 | AO25-9 |
| SF | 2025-01-24 | 2 | AO25-9 |
| Bez plánovaného mužského kola | 2025-01-25 | 0 | AO25-9 |
| F | 2025-01-26 | 1 | AO25-1/9 |

Q 4 kalendářní dny, Main 15 dnů, celé okno 21 dnů. Součty Q 112 + Main 127 = 239 uzlů. Oficiální předturnajový článek (25. 11. 2024) potvrzuje čtyřdenní Q, nedělní začátek Main a třídenní R128. Přesná okna Q1/Q2 potvrzuje dobové shrnutí výsledků a články Tennis Australia; samostatný předstartovní denní Q program nebyl získán. Main všechna kola potvrzují dva dobové předturnajové rozpisy. Denní počty vícedenních kol neodhadovat. Skutečné přerušení nebo posun jednotlivého zápasu není změna nominálního okna.

### 4. Struktura, pravidla a kontrola losu

| Nominální parametr | Main | Q |
|---|---:|---:|
| Kapacita / cíloví účastníci | 128 | 128 |
| Přímé akceptace | 104 | 119 |
| WC | 8 | 9 |
| Nasazených | 32 | 32 |
| Q postupová místa | 16 | 16 |
| BYE | 0 | 0 |
| Kola | 7 | 3 |
| Uzly | 127 | 112 |
| Formát | BO5 setů | BO3 setů ve všech kolech |

Důkazy AO25-3/4/5/12/13/14: pořadatel výslovně potvrzuje 104/16/8 Main, 119/9 Q, 32 Main seedů a tři vítězství pro postup; 2025 předpis str. 7, 24, 26, 30–31 vizuálně ověřen, Q seeding a geometrie potvrzeny nezávislým vykreslením obou mužských pavouků. 104+16+8=128, 119+9=128. AO25-13 výslovně potvrzuje BO3 ve všech Q kolech a BO5 v Main; nejde o přepis pravidel Wimbledonu.

Dobový rulebook 2025 (W25-4) stanovuje nasazení Main přibližně podle rankingu týden před turnajem, Q podle nejnovějšího rankingu, v 16 sekcích po osmi dva seedy (1–16 horní pozice, 17–32 losované na spodní). Q seed se před zveřejněním prvního OOP nahrazuje dalším způsobilým seedem, později alternatem. Výherci Q přiřazeni losem po Q. LL přednostně z poražených Q3, při nedostatku i dřívější kola, los mezi nejvýše postavenými čtyřmi způsobilými hráči, při více než dvou odhlášeních na konci Q velikost losované skupiny počet odhlášení + 2, další podle rankingu. LL sign-in před začátkem denního programu, náhrada před prvním bodem odstoupivšího hráče. Rozhodující set tiebreak na 10 s rozdílem alespoň 2 při 6:6. Použít ročníkový předpis a jeho výjimky, nikoli dnešní rankingovou tabulku.

**Oddělený historický kontext:** originální mužské entry listy z 29. 12. obsahují 8 Main WC a 9 Q WC. Organizátor uvádí 6 protected-ranking vstupů v původní Main listině, takže počáteční cutoff byl 98, nikoli 104; dvě náhrady po odhlášení posunuly vstup na 99 a 100 (AO25-3/4). Tato historická čísla nejsou nominální pravidlo pro budoucí simulaci. Nezávislý archiv losů (AO25-12, str. 2 a 4 vizuálně) potvrzuje 128/128 pozic, 32/32 seedů, bez BYE, Q devět W (6,10,12,31,37,44,70,109,125). Main obsahuje jednu LL; stejný historický počet uvádí předchozí #1903. Originální PDF Main a Q nebyly v tomto průchodu nově staženy, nezávislé zobrazení nenahrazuje původní bajty. Individuální výsledky a jména nepřepisujeme.

### 5. Body a odměny

| Výsledek | Nominální příjemci | ATP body | AUD 2025 | AUD 2024 |
|---|---:|---:|---:|---:|
| Vítěz | 1 | 2000 | 3500000 | 3150000 |
| Finalista | 1 | 1300 | 1900000 | 1725000 |
| SF | 2 | 800 | 1100000 | 990000 |
| QF | 4 | 400 | 665000 | 600000 |
| R16 | 8 | 200 | 420000 | 375000 |
| R32 | 16 | 100 | 290000 | 255000 |
| R64 | 32 | 50 | 200000 | 180000 |
| R128 | 64 | 10 | 132000 | 120000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 72000 | 65000 |
| Q2 prohra | 32 | 8 | 49000 | 44100 |
| Q1 prohra | 64 | 0 | 35000 | 31250 |

Body z dobového ATP 2025 rulebooku (W25-15, str. 264 dříve vizuálně zkontrolována) a preview AO25-2. Q body přičítány k Main, WC prohra prvního kola bez 10 bodů; individuální LL body mimo nominální rozsah. Všechny peněžní hodnoty z originálního AO25-6 (první strana vizuálně), který uvádí vedle sebe i 2024. Main 33108000 AUD, Q 4960000 AUD = 38068000 AUD mužská dvouhra s Q; kontrolní součty přesně shodné s publikovanými dílčími součty pořadatele. AO24 součty 29 775 000 a 4 451 200 AUD rovněž potvrzeny nezávisle. Celoturnajová dotace všech soutěží 96 500 000 AUD; nezaměňovat se singlovým součtem.

Oficiální AO25 Key Player Information (AO25-15, str. 1 vizuálně) uvádí 350 AUD/noc od prvního dne dané soutěže do vyřazení plus 3 dny, stravné 250 AUD/den pro hráče a maximálně tři členy doprovodu (100 hráč + 50 za každého člena, podle uvedených podmínek), pro top 8 přihlášených LL zvláštní lhůta do konce R128. Nejde o prize money.

### 6. Kontrola a mezery

I/T/D/R/B/P pokryto. H: Q denní okna potvrzena dobovými zprávami, ale samostatný předturnajový Q OOP nebyl získán; Main předturnajově doložen. E: originální obě mužské listiny a výslovné datum uzávěrek vizuálně potvrzeno, přesný okamžik Q losu neověřen. Z: originální prize sheet, entry listy, Grand Slam rulebook vybrané strany a nezávislé vykreslení losů vizuálně ověřeny. Hash originálních draw PDF nezískán; žádný nevymýšlíme. Povinná nominální data jsou doložena, nikoli úplná historie každého zápasu. Další ročník Roland Garros 2025.

### 7. Zdroje (AO25)

- AO25-1: [pořadatel — plán 25. 11. 2024](https://ausopen.com/articles/news/australian-open-2025-provisional-schedule-plan-your-three-weeks-melbourne-park).
- AO25-2: [ATP dobové preview](https://www.atptour.com/en/news/australian-open-2025-history-draw-schedule), indexovaný text.
- AO25-3: [pořadatel — jak vzniká los, AO25](https://ausopen.com/articles/news/how-grand-slam-tournament-draws-are-made), kvóty, čas Main losu, protected ranking, mechanismus Q/LL.
- AO25-4: [Tennis Australia — mužský Main entry list 29. 12.](https://www.tennis.com.au/wp-content/uploads/2024/12/AO25_mens-singles_main-draw_241229.pdf), str. 1 vizuálně včetně zápatí.
- AO25-5: [Tennis Australia — mužský Q entry list 29. 12.](https://www.tennis.com.au/wp-content/uploads/2024/12/AO25_mens-singles_qualifying_241229.pdf), str. 1 vizuálně včetně zápatí.
- AO25-6: [originální AO25 prize money](https://www.tennis.com.au/wp-content/uploads/2025/01/AO25-Prize-Money.pdf), str. 1 vizuálně; [oznámení pořadatele](https://ausopen.com/articles/news/australian-open-prize-money-increases-more-11-cent-2025).
- AO25-7: [pořadatel Q entry list a termíny](https://ausopen.com/articles/news/australian-open-2025-qualifying-entry-lists-released).
- AO25-8: [dobové shrnutí Q rozpisu](https://www.sportingnews.com/uk/tennis/news/australian-open-qualifying-2025-results-scores-draw/cd276136defda498342adf4b).
- AO25-9: [dobový Main plán TNT](https://www.tntsports.co.uk/tennis/australian-open/2025/start-schedule-uk-time-who-is-playing-novak-djokovic-nick-kyrgios-andy-murray-jannik-sinner-carlos-alcaraz-aryna-sabalenka-iga-swiatek-coco-gauff_sto20057807/story.shtml); [Sports Mole plán](https://www.sportsmole.co.uk/tennis/australian-open/feature/is-raducanu-playing-how-to-watch-a-complete-guide-to-the-2025-australian-open_562174.html).
- AO25-10: [Tennis Australia — 5. 1. již zveřejněné Q páry](https://www.tennis.com.au/fan-zone/news/2025/01/05/aussies-set-to-begin-australian-open-2025-qualifying-campaigns).
- AO25-11: [Tennis Australia Q1 7. 1.](https://www.tennis.com.au/fan-zone/news/2025/01/07/birrell-fronts-successful-day-for-aussies-at-ao-2025-qualifying), [Q2 8. 1.](https://www.tennis.com.au/fan-zone/news/2025/01/08/australian-quartet-one-win-from-australian-open-qualification).
- AO25-12: [nezávislé vykreslení losů](https://donald.au/tennis/2025/2025-australian-open-singles.pdf), mužský Main str. 2 a Q str. 4 vizuálně; není originální pořadatelský PDF. #1903 eviduje originál Main https://ausopen.com/sites/default/files/2026-11/draw_ms_2025-01-26_2235.pdf, zde nepředstíráme nové ověření.
- AO25-13: [pořadatel — formát zápasů AO25](https://ausopen.com/articles/news/guide-scoring-tennis).
- AO25-14: [Grand Slam Rule Book 2025](https://www.wimbledon.com/pdf/Grand_Slam_Rulebook_2025.pdf), opět vizuálně tištěné str. 7,24,26,30,31, zbytek relevantního §2/3 viz W25-4; ATP body W25-15.
- AO25-15: [Tennis Australia — AO25 Key Player Information](https://www.tennis.com.au/wp-content/uploads/2024/11/AO25-Key-Player-Information.pdf), str. 1 vizuálně.


## Roland Garros 2025

**Stav:** HOTOVO v nominálním rozsahu (9/9), s níže uvedenými omezeními H/E/Z. Rešerše 2026-11-27. Pouze tenisová fakta.

### 1. Identita

| Pole | Hodnota | Zdroj |
|---|---|---|
| Název / disciplína | Roland-Garros 2025, mužská dvouhra | RG25-1/2 |
| Kategorie / ATP ID | Grand Slam / 520 (identita série) | RG25-1, RG24-16 |
| Dějiště obou fází | Stade Roland-Garros, Paříž, Francie | RG25-1/2 |
| Povrch | venkovní antuka | RG25-2 |
| Časové pásmo | Europe/Paris, CEST UTC+02:00 | místní civilní datum, RG25-1 |
| Pořadatel / měna | FFT / EUR | RG25-3/4 |
| Ředitelka | Amélie Mauresmo | RG25-3 |
| Míče, rozhodčí, individuální diety | neověřeno pro tento ročník | doplňková metadata |

### 2. Přihlášky a plán

| Pole | Místní údaj | Zdroj / význam |
|---|---|---|
| Main datum rankingu pro vstup | 2025-04-14 | mužský ATP Acceptance List RG25-5, rank date výslovně; 42 dní před prvním pondělím 26. 5. |
| Q datum rankingu pro vstup | 2025-04-21 | mužský ATP Q Acceptance List RG25-6, rank date výslovně |
| Obecná Q uzávěrka podle předpisu | 2025-04-28 | výpočet 28 dní před pondělím Main; nejde o doloženou mužskou uzávěrku tohoto ročníku. Q rank date 21. 4. nelze zaměnit s touto hodnotou. Konkrétní uzávěrka/hodina nezískána. |
| Oznámení WC | 2025-05-13, aktualizace 18. 5. | RG25-3 |
| Q los | zveřejněn 2025-05-18 | RG25-7, okamžik losování neověřen |
| Q | 2025-05-19–23 | RG25-1 |
| Main los | 2025-05-22 14:00 | RG25-1 |
| Main | 2025-05-25–06-08 | RG25-1 |
| Mužské SF | 2025-06-06, ne před 14:30 a 19:00 | RG25-1 |
| Mužské finále | 2025-06-08, ne před 15:00 | RG25-1 |

Pozor: mužský Q Acceptance List nese Date 19 May a Rank Date 21 Apr; Main Acceptance List Date 26 May a Rank Date 14 Apr. Date 26 May v administrativní listině nepřepisuje nedělní zahájení soutěže 25. 5. Ženský acceptance PDF RG25-8 uvádí jiné Q datum 28. 4.; pro muže se nesmí použít. Předpis RG25-9 str. 24 určuje obecné lhůty a možnost výjimek. Stejnou opatrnost uplatňovat u starších ročníků: RG24 dříve evidované Q datum 29. 4. je pouze obecný výpočet s podpůrným ženským dokladem, nikoli ověřený mužský rank date.

### 3. Plánované fáze a kola

| Kolo | Lokální okno | Nominální uzly | Evidence |
|---|---|---:|---|
| Q1 | 2025-05-19–20 | 64 | RG25-10/11 |
| Q2 | 2025-05-21 | 32 | RG25-11/12; odklad části programu 22. 5. kvůli dešti |
| Q3 | 2025-05-22–23 | 16 | RG25-1/12/13, denní pořadatelské zprávy |
| Mezi fázemi | 2025-05-24 | 0 | RG25-1, charitativní Yannick Noah Day |
| R128 | 2025-05-25–27 | 64 | RG25-1 |
| R64 | 2025-05-28–29 | 32 | RG25-1 |
| R32 | 2025-05-30–31 | 16 | RG25-1 |
| R16 | 2025-06-01–02 | 8 | RG25-1 |
| QF | 2025-06-03–04 | 4 | RG25-1 |
| Bez mužského singlového kola | 2025-06-05 | 0 | RG25-1 |
| SF | 2025-06-06 | 2 | RG25-1 |
| Bez mužského singlového kola | 2025-06-07 | 0 | RG25-1 |
| F | 2025-06-08 | 1 | RG25-1 |

Q 5 dní, Main 15 dní, 21 dní celé okno. Pořadatel v úterý 20. 5. avizoval Q2 na středu. Dne 21. 5. déšť způsobil odklad venkovních zápasů, 22. 5. se hrálo Q2 i Q3. Nominální Q2 ponecháváme 21. 5. jako odvozený plán kola podpořený dobovou zprávou o odkladu; kompletní předdešťový OOP s 32 mužskými identifikátory, jako u RG24, zatím nezískán. Q3 okno potvrzeno pořadatelskými články, nikoli přesným původním rozdělením denních počtů. Main okna všech kol přímo v oficiálním plánu. Start Q 19.–21. 5. od 10:00, 22.–23. 5. od 11:00; Main obvykle od 11:00. Nejde o individuální starty.

### 4. Struktura a pravidla

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / nominální hráči | 128 | 128 |
| Přímé akceptace | 104 | 119 |
| WC | 8 | 9 |
| Nasazení | 32 | 32 |
| Q postupová místa | 16 | 16 vítězů sekcí |
| BYE | 0 | 0 |
| Kola / nominální uzly | 7 / 127 | 3 / 112 |
| Formát | BO5 setů | BO3 setů ve všech kolech |

RG25-5/6 přímo mužské ATP listiny uvádějí kvóty; RG25-3 aktualizované WC; RG25-14 obě strany Main vizuálně, RG25-15 horní Q strana vizuálně a druhá textově, RG25-7/13 Q výsledky. 104+16+8=128; 119+9=128; 239 uzlů celkem. Main kontrolní konečný los 8 WC, 16 Q, 6 LL, 32 seedů, žádný BYE; šest skutečných LL není nominální kvóta. Q 16 sekcí po osmi, 2 seedy v každé sekci. Nepřebírat výjimku Wimbledonu BO5 Q3. Dobová pravidla RG25-9: Main seeding podle rankingu přibližně týden před turnajem, skupiny 128/32, krajní seedy 1/2; Q seedy 1–16 horní pozice, 17–32 losované na spodní pozice. Před zveřejněním prvního OOP odstoupeného seedu nahradí další způsobilý seed, po zveřejnění alternate. Q vítězové přiřazeni do Main losem po skončení Q. LL z posledního kola Q přednostně, další kola jen v případě potřeby; losování čtyř nejvýše postavených způsobilých, při více než dvou odstoupeních při konci Q počet odstoupení + 2; poté ranking. Náhrada před prvním bodem prvního zápasu odstoupivšího; sign-in 30 min před prvním zápasem dne. Rozhodující tiebreak na 10 s rozdílem 2 při 6:6. Main a Q BO doloženo 2025 předpisem a výsledky Q3 RG25-13. Historické první cutoff ranky 100 Main, 218 Q z RG25-5/6 jsou jen kontext.

### 5. Body a odměny

| Výsledek | Příjemci | ATP body | EUR 2025 |
|---|---:|---:|---:|
| Vítěz | 1 | 2000 | 2550000 |
| Finalista | 1 | 1300 | 1275000 |
| SF | 2 | 800 | 690000 |
| QF | 4 | 400 | 440000 |
| R16 | 8 | 200 | 265000 |
| R32 | 16 | 100 | 168000 |
| R64 | 32 | 50 | 117000 |
| R128 | 64 | 10 | 78000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 43000 |
| Q2 prohra | 32 | 8 | 29500 |
| Q1 prohra | 64 | 0 | 21000 |

Main přímo ATP mužský preview RG25-16 (text, screenshot 403) + WTA preview vizuálně pouze pro stejné odměny, nikoli ženské body. Q tabulka z více zdrojů RG25-17; originální press kit je odkázán, ale přímý přístup překročil velikostní limit, takže nelze tvrdit jeho vizuální kontrolu. Eurosport tabulka v době rešerše obsahuje chybné/nesouhlasné částky 2 555 000, 88 737, 48 919; pro Main přednost ATP a WTA, pro Q shoda zdrojů s původním release. ATP body Q dle W25-15, 30 Q body přičítány k Main, WC prohra R128 bez bodů. Nominální součty Main 20509000 EUR, Q 2976000 EUR = 23485000 EUR. Celoturnajová dotace 56 352 000 EUR zahrnuje ostatní soutěže. Nepřepisovat skutečné platby jednotlivcům.

### 6. Pokrytí

I/T/D/R/B/P doloženo, H* Q2 plán odvozen z dobového programu/odkladu, kompletní předdešťové OOP nezískáno; E* mužské rank dates přímo doloženy, skutečná Q entry uzávěrka a hodiny losu neověřeny (neztotožňovat rank date a deadline); Z* druhá Q strana a ATP preview vizuálně nedostupné, Q prize press kit překročil limit. Nominální struktura doložena mužskými listinami a dobovým předpisem. SHA-256 nebyly získány. Další US Open 2025.

### 7. Zdroje (RG25)

- RG25-1: [FFT oficiální program všech kol](https://www.rolandgarros.com/en-us/article/2025-full-schedule-calendar-qualifications-main-draw-singles-doubles-wheelchair-tennis).
- RG25-2: [WTA dobový přehled](https://www.wtatennis.com/news/4271092/____french-open-2025-draws-dates-prize-money-and-what-you-need-to-know) (identita/povrch, ne ženské body).
- RG25-3: [FFT WC 13. 5., update 18. 5.](https://www.rolandgarros.com/en-us/article/2025-wildcards-men-women-singles-qualifying-rounds).
- RG25-4: [ATP prize money](https://www.atptour.com/en/news/roland-garros-2025-prize-money) indexovaný text.
- RG25-5: [mužský Main ATP Acceptance List](https://rg-organisation.fft.fr/sites/default/files/2025-04/RG%20MD%20Men%202025.pdf), str. 1 vizuálně.
- RG25-6: [mužský Q ATP Acceptance List](https://rg-organisation.fft.fr/sites/default/files/2025-04/RG%20Q%20Men%202025.pdf), str. 1 vizuálně.
- RG25-7: [ATP Q draw 18. 5.](https://www.atptour.com/en/news/roland-garros-2025-qualifying-draw), [FFT Q preview](https://www.rolandgarros.com/en-us/article/rg2025-qualifying-the-only-way-is-up).
- RG25-8: [ženský WTA acceptance PDF](https://rg-organisation.fft.fr/sites/default/files/2025-05/RolandGarrosMD2025Update.pdf), indexovaný text, pouze kontrast, ne mužské datum.
- RG25-9: [ITF Grand Slam Rulebook 2025](https://www.itftennis.com/media/5986/grand-slam-rulebook-2025-f.pdf), tištěná str. 24 vizuálně; §2/3 viz W25-4, AO25-14.
- RG25-10: [FFT Opening Week](https://www.rolandgarros.com/en-us/article/2025-roland-garros-gears-up-for-opening-week).
- RG25-11: [FFT 20. 5., představení středečního Q2](https://www.rolandgarros.com/en-us/article/rg2025-roland-garros-wrap-tuesday-may-20).
- RG25-12: [FFT 21. 5., odklady](https://www.fft.fr/actualites/qualifications-roland-garros-mercredi-droguet-ferro-monnet-gea-mpetshi-programmation-courts-tableaux), [L'Équipe 21. 5.](https://www.lequipe.fr/Tennis/Actualites/Les-matches-de-qualifications-sur-les-courts-annexes-reportes-a-jeudi-en-raison-de-la-pluie/1563683), [FFT 22. 5.](https://www.rolandgarros.com/en-us/article/rg2025-roland-garros-wrap-thurs-may-22).
- RG25-13: [ATP Q3 výsledky 23. 5.](https://www.atptour.com/en/news/roland-garros-2025-qualifying-results), [FFT poslední den](https://www.fft.fr/actualites/vendredi-23-mai-direct-commente-roland-garros).
- RG25-14: [originální Main draw kopie RFET, aktualizace 8. 6. 20:58](https://www.rfet.es/descargar/file-noticias-adjuntos/5247_Documento/cuadro-individual-roland-garros-2025.pdf), obě strany vizuálně.
- RG25-15: [FFT Q draw 19. 5. 21:05](https://rg-organisation.fft.fr/sites/default/files/2025-05/Mens_Qualifying_20250519210617.pdf), str. 1 vizuálně; str. 2 screenshot 500, indexovaný text.
- RG25-16: [ATP Men's Tournament Preview 2025](https://www.atptour.com/-/media/8b317e663bf34fbba0bbb6fa013a76fa.pdf), tabulka bodů a Main prize textově, screenshot 403; [WTA preview](https://wtafiles.wtatennis.com/pdf/matchnotes/2025/903_preview.pdf), str. 1 vizuálně, pouze stejné peněžní částky.
- RG25-17: [press kit FFT](https://fft-rg-commun-news.cdn.prismic.io/fft-rg-commun-news/aAEIrOvxEdbNPMke_DPROLANDGARROS2025UKVF1.pdf), přístup selhal kvůli velikosti 13 MB; [tabulka s odkazem na press kit](https://tennisprizemoney.com/french-open-prize-money/2025/), [dobový TennisTemple Q tabulka](https://en.tennistemple.com/actu/roland-garros-announces-prize-money-increase-for/F2du), [Reuters 6. 5. 2025](https://www.reuters.com/sports/tennis/french-open-2025-prize-money-how-much-do-winners-earn-2025-05-06/).

## US Open 2025

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z. Rešerše 2026-11-27. Nedělní začátek Main a původní čtyřdenní Q potvrzeny samostatně; déšť nemění nominální údaje.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / disciplína | US Open 2025, mužská dvouhra | US25-1/2 |
| Kategorie / ATP ID | Grand Slam / 560 | US25-1, US24-13 |
| Dějiště Main i Q | USTA Billie Jean King National Tennis Center, Flushing Meadows, Queens, New York, USA | US25-2/3 |
| Povrch | venkovní tvrdý | US25-1/4 |
| Časové pásmo | America/New_York, EDT UTC−04:00 | US25-3/5 místní ET |
| Pořadatel / měna | USTA / USD | US25-2/6 |
| Míče a rozhodčí | NEOVĚŘENO | doplňkové, nevyplňovat z jiných ročníků |

### 2. Přihlášky, losování a termíny

| Událost | Místní údaj | Důkaz |
|---|---|---|
| Main vstupní ranking | 2025-07-14 | výslovně USTA US25-2; zveřejnění 15. 7. |
| Main nominální uzávěrka | 2025-07-14 | 42 dnů před pondělím 25. 8.; souhlas s doloženým rank date, hodina neověřena |
| Q nominální uzávěrka | 2025-07-28 | odvozeno z 28denního předpisu, ne nezávisle potvrzené mužské Q rank date ani skutečný deadline |
| Oznámení WC | 2025-08-13 | USTA US25-7 |
| Q los | před začátkem Q, přesný datum/čas NEOVĚŘEN | originální konečný los US25-9 neprokazuje okamžik losování |
| Q | 2025-08-18–21, start 11:00 | US25-1/3 |
| Main los | 2025-08-21 12:00 | US25-1/5 |
| Main | 2025-08-24–09-07 | US25-1/2/4 |
| Mužské SF | 2025-09-05, plán od 15:00 | US25-5 |
| Mužské finále | 2025-09-07 14:00 | US25-5 |

Mužský Main entry list z 14. 8. (US25-8, str. 1 vizuálně, text druhé strany) potvrzuje strukturu 104 přímých pozic a aktualizaci po odhlášeních. Pořadatel v červenci uváděl původní mužský cutoff 101 a ranking 14. 7. Nepovažovat pořadí posledního hráče za nominální kvótu. Originální Q acceptance list nezískán, takže 28. 7. pouze obecná lhůta, viz i poučení z RG25.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální uzly | Zdroj |
|---|---|---:|---|
| Q1 | 2025-08-18–19 | 64 | US25-3 |
| Q2 | 2025-08-20 | 32 | US25-3 |
| Q3 | 2025-08-21 | 16 | US25-3 |
| Mezi fázemi | 2025-08-22–23 | 0 | US25-1/3 |
| R128 | 2025-08-24–26 | 64 | US25-4/5 |
| R64 | 2025-08-27–28 | 32 | US25-5 |
| R32 | 2025-08-29–30 | 16 | US25-5 |
| R16 | 2025-08-31–09-01 | 8 | US25-5 |
| QF | 2025-09-02–03 | 4 | US25-5 |
| Bez plánovaného mužského kola | 2025-09-04 | 0 | US25-5 |
| SF | 2025-09-05 | 2 | US25-5 |
| Bez plánovaného mužského kola | 2025-09-06 | 0 | US25-5 |
| F | 2025-09-07 | 1 | US25-5 |

Q 4 dny, Main 15 dnů, celé okno 21 dnů, 239 nominálních uzlů. Oproti 2024 se Main rozšířil na 15 dní s třídenním R128, což USTA oznámila již 29. 1. 2025 (US25-4). Další Main kola pořadatel neměnil. ESPN předturnajový plán 13. 8. rozlišuje všechny čtyři Q dny přímo. Skutečný průběh: 20. 8. déšť zrušil většinu programu, Q2 se přesunulo na 21. 8. a Q skončilo 22. 8. (US25-10). V referenčním plánu proto zůstává Q3 21. 8., nikoli 22. 8. Přesný denní počet vícedenních Main kol neodhadovat. Mixed doubles nově ve Fan Week, mimo rozsah mužské dvouhry.

### 4. Nominální struktura a pravidla

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / plánovaný počet hráčů | 128 | 128 |
| Přímé akceptace | 104 | 119 |
| WC | 8 | 9 |
| Nasazení | 32 | 32 |
| Q postupová místa | 16 | 16 vítězů sekcí |
| BYE | 0 | 0 |
| Kola / uzly | 7 / 127 | 3 / 112 |
| Formát | BO5 setů | BO3 setů ve všech kolech |

Pořadatel potvrzuje 8 Main a 9 Q WC, 16 Q postupů; obě stránky originálního Main/Q losu vizuálně (US25-9). 104+16+8=128, 119+9=128; 16 vyřazovacích Q sekcí po osmi. BO3 Q všech kol kontrolováno na původním losu, BO5 Main podle dobového předpisu. Main seed 1/2 na krajích, ostatní skupiny podle tabulky 128/32, Q seedy 1–16 na horních a 17–32 losované na spodní pozice sekcí. Pravidla 2025 (RG25-9, W25-4) upravují náhradu seedu před/po prvním OOP, losování kvalifikantů do Main po skončení Q, přednost LL poražených Q3, los mezi čtyřmi nejvýše postavenými způsobilými (více než dvě odhlášení na konci Q: počet +2), další dle rankingu, sign-in 30 min před začátkem dne; náhrada před prvním bodem prvního zápasu odstoupivšího. Rozhodující set tiebreak na 10 při 6:6 s rozdílem 2.

**Historický kontext oddělený od nominálního plánu:** Main 8 W (5,12,46,50,76,95,123,124), 16 Q (23,31,44,47,53,62,67,68,75,77,83,90,91,94,98,100), 4 LL (28,39,45,109), 100 bez W/Q/L; 32 seedů, nula BYE. Q 9 W (4,19,29,39,66,71,85,93,101), 1 alternate (16), 118 bez W/A, **31 viditelných seedů (č. 25 chybí)**, nula BYE. Konečný Q los ukazuje nahrazenou seed pozici, ne důvod ani okamžik výměny. Dřívější #1903 uvádí v poli seeds 32 bez rozlišení; nominální 32 je správně, skutečných 31 se zapíše pouze jako kontext. Main jedna pozdější WO (Bergs/Draper); žádný důvod měnit 127 nominálních uzlů.

### 5. Body a prize money

| Výsledek | Příjemci | ATP body | USD 2025 |
|---|---:|---:|---:|
| Vítěz | 1 | 2000 | 5000000 |
| Finalista | 1 | 1300 | 2500000 |
| SF | 2 | 800 | 1260000 |
| QF | 4 | 400 | 660000 |
| R16 | 8 | 200 | 400000 |
| R32 | 16 | 100 | 237000 |
| R64 | 32 | 50 | 154000 |
| R128 | 64 | 10 | 110000 |
| Q postupující | 16 | 30 | samostatná odměna neuvedena |
| Q3 prohra | 16 | 16 | 57200 |
| Q2 prohra | 32 | 8 | 41800 |
| Q1 prohra | 64 | 0 | 27500 |

Peněžní částky přímo USTA US25-6 (6. 8.), body dobový ATP rulebook US25-11 a specifický ATP mužský preview US25-12. **Rozpor:** obecný webový ATP preview US25-1 uvádí staré body (např. F 1200 a R16 180), ale dobový mužský turnajový PDF a ročníkový předpis potvrzují F 1300/R16 200. Předpis má přednost. Q body se přičítají k Main, WC prohra R128 bez 10 bodů; individuální LL historie mimo požadavek. Součty Main 31620000 USD, Q 4012800 USD, celkem 35632800 USD. Dvě Q soutěže nominálně 2×4012800 USD = 8 025 600 USD, pořadatel zaokrouhluje na 8 mil.; celková kompenzace 90 mil. USD zahrnuje další disciplíny i hotel a diety. USTA navíc oznámila cestovní příspěvek 1000 USD a dvě hotelové místnosti (alternativa 600 USD/den při jiném ubytování), ne součást singlového prize money.

### 6. Evidence

I/T/H/D/R/B/P pokryto; E*: Main rank date potvrzen přímo pořadatelem, Q deadline obecný výpočet, Q acceptance list a okamžik losu chybí; Z*: oba originální losy a Main list str. 1 vizuálně, ATP rulebook z předchozí rešerše a text z dobového dokumentu; SHA-256 nezískány. Historické odklady odděleny. Všech osm Grand Slamů 2024–2025 je nyní pokryto v nominálním rozsahu; další běžné ATP ročníky z dobového kalendáře, nejdříve první turnaj ATP 2024 (včetně týmových/formátově odlišných soutěží, pokud jsou v katalogu; neposuzovat je automaticky jako singlové vyřazovací pavouky).

### 7. Zdroje (US25)

- US25-1: [ATP US Open 2025 preview](https://www.atptour.com/en/news/us-open-2025-history-draw-schedule), indexovaný text, chybné staré body explicitně odmítnuty.
- US25-2: [USTA Main entry announcement 15. 7.](https://www.usopen.org/amp/en_US/news/articles/2025-07-15/who_is_playing_in_the_2025_us_open_sabalenka_sinner_gauff_alcaraz_and_more.html).
- US25-3: [ESPN předturnajový Q plán 13. 8.](https://espnpressroom.com/press-release/espn-begins-three-weeks-of-us-open-coverage-on-august-18/), jednotlivá kola a 128/16.
- US25-4: [USTA oznámení nedělního startu 29. 1.](https://www.usopen.org/en_US/news/articles/2025-01-29/us_open_main_draw_expanding_to_sunday_start_in_2025.html), indexovaný text; [WTA preview](https://www.wtatennis.com/news/4345509/us-open-2025-draws-dates-stats-prize-money-and-what-you-need-to-know).
- US25-5: [Sports Mole 20. 8., všechna Main kola a Main los](https://www.sportsmole.co.uk/tennis/us-open/feature/when-is-the-draw-how-can-i-watch-a-complete-guide-to-the-2025-us-open_579661.html), [ESPN Main plán 20. 8.](https://espnpressroom.com/press-release/all-of-the-2025-us-open-all-in-one-place/).
- US25-6: [USTA oficiální prize money 6. 8.](https://www.usopen.org/amp/en_US/news/articles/2025-08-06/2025_us_open_prize_money_sets_record_for_largest_purse_in_tennis_history.html).
- US25-7: [USTA oznámení WC 13. 8.](https://www.usopen.org/en_US/news/articles/2025-08-13/holt_nava_among_american_men_awarded_2025_us_open_wild_cards.html).
- US25-8: [USTA mužský Main entry list 14. 8.](https://www.usopen.org/pdf/mens-2025-us-open-main-draw-entry-list.pdf), str. 1 vizuálně, další textově.
- US25-9: [Main](https://www.usopen.org/en_US/scores/draws/2025_MS_draw.pdf), [Q](https://www.usopen.org/en_US/scores/draws/2025_MQ_draw.pdf), všechny čtyři stránky vizuálně.
- US25-10: [ATP zrušení programu 20. 8.](https://www.atptour.com/en/news/us-open-2025-wednesday-qualifying-cancelled), [Tennis.com přesun Q2](https://www.tennis.com/news/articles/2025-us-open-qualifying-postponed-due-to-wednesday-rain), [USTA Q2 21. 8.](https://www.usopen.org/en_US/news/articles/2025-08-21/day_4_of_mens_and_womens_qualifying_at_the_2025_us_open.html), [USTA konec Q 22. 8.](https://www.usopen.org/en_US/news/articles/2025-08-22/day_5_of_mens_and_womens_qualifying_at_the_2025_us_open.html).
- US25-11: [ATP Rulebook IX 2025](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf), indexovaný text / dříve vizuálně W25-15; [ITF hostovaný ATP 2025 ranking info](https://www.itftennis.com/media/13761/atp-2025-rankings-info.pdf), indexovaná bodová tabulka.
- US25-12: [ATP mužský turnajový preview PDF](https://www.atptour.com/-/media/bbcfbd0dcbf94821998f4339a53cf8ab.pdf), indexovaný text odlišný od chybného webového článku.

## Brisbane 2024

**Stav:** HOTOVO v nominálním rozsahu, H/E/R/Z s označenými omezeními. Rešerše 2026-11-27. První běžný ATP turnaj v registru. Zásadní výjimka proti obecnému pravidlu ATP 250: Q24, šest postupů, nikoli Q16/4.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Brisbane International presented by Evie | BRI24-1 |
| Ročník / disciplína | sezona 2024 / mužská dvouhra | BRI24-1/2 |
| Kategorie / ATP ID | ATP 250 / 339 | BRI24-1 |
| Dějiště Q a Main | Queensland Tennis Centre, Tennyson, Brisbane, Queensland, Austrálie | BRI24-2/3 |
| Povrch | venkovní tvrdý, Greenset Cushion | BRI24-1/2 |
| Časové pásmo | Australia/Brisbane, AEST UTC+10 (Queensland nemá letní čas) | místní civilní data, identita lokality |
| Ředitel / ATP supervisor | Cameron Pearson / Hans-Jürgen Ochs | BRI24-1/4 |
| Měna | USD, nikoli AUD | BRI24-1/8 |
| Míče, individuální diety | NEOVĚŘENO | doplňková metadata |

Ročník patří do sezony 2024, přestože dvě první lokální data leží v roce 2023. Dvojí datum 31. 12. nelze deduplikovat: Q2 a R32 jsou odlišné fáze.

### 2. Přihlášky, plán a losování

| Pole | Údaj | Důkaz / význam |
|---|---|---|
| Main entry rank date | 2023-12-04 | dobový přepis mužského acceptance listu BRI24-5 |
| Q entry rank date | 2023-12-11 | BRI24-5 |
| Nominální Main uzávěrka | 2023-12-04 12:00 US Eastern (2023-12-05 03:00 AEST) | §7.03 A.1, 28 dnů před pondělím 2024-01-01; odvozeno, nikoli samostatný původní detail sheet |
| Nominální Q uzávěrka | 2023-12-11 12:00 US Eastern (2023-12-12 03:00 AEST) | §7.03 A.2, 21 dnů před pondělím; odvozeno |
| Q los | nejpozději před Q1 30. 12.; přesný okamžik NEOVĚŘEN | BRI24-4 |
| Q | 2023-12-30–31 | pořadatelské OOP BRI24-4/6, dobové ATP zprávy BRI24-7 |
| Main los | 2023-12-30 dopoledne, Queensland Tennis Centre | pořadatel BRI24-3; hodina nepublikována |
| Main | 2023-12-31–2024-01-07 | originální Main los BRI24-1 a předturnajové oznámení BRI24-2 |
| Běžný program | 11:00 AEST (některé kurty později) | BRI24-4/6 |
| Finále | 2024-01-07 | BRI24-1/9; přesný plánovaný čas mužského finále neověřen |

Rulebook §7.12 obsahuje starší formulaci 42 dní pro Main ranking list; pro tento ročník rozhoduje konkrétní dobový acceptance list (4. 12.) a výslovná entry deadline §7.03 (28 dní). Nepoužívat 42/28denní Grand Slam lhůtu. Původní ATP detail sheet nedostupný. Datum US Eastern není lokálním australským datem; obě data zachována s pásmem, nikoli W52 převod.

### 3. Nominální harmonogram

| Kolo | Místní okno | Nominální uzly | Důkaz |
|---|---|---:|---|
| Q1 | 2023-12-30 | 12 | BRI24-4/7 |
| Q2 | 2023-12-31 | 6 | BRI24-6, šest kvalifikačních dvojic v programu |
| R32 | 2023-12-31–2024-01-02 | 16 | BRI24-6/9/10, rekonstruovaný plán |
| R16 | 2024-01-03–04 | 8 | BRI24-9/11 |
| QF | 2024-01-05 | 4 | BRI24-12, všechny čtyři mužské singlové dvojice v OOP |
| SF | 2024-01-06 | 2 | BRI24-9/13 |
| F | 2024-01-07 | 1 | BRI24-1/9 |

Q 2 dny, Main 8 dní, celkem 9 kalendářních dnů, protože Q2 se hraje stejný den jako začátek Main. R32 31. 12.–2. 1. je rekonstrukce z denních plánů a doloženého odkladu posledního R32 (Humbert/Michelsen původně 2. 1., odehráno 3. 1. kvůli dešti, BRI24-10). Proto nominální konec není 3. 1. R16 3.–4. 1. potvrzen dobovými zprávami a programy. Kompletní předturnajový detailní mužský rozpis se nepodařilo získat; H* značí rekonstruované plánované okno, ne tvrzení o jeho přímém přepisu. Přesné počty R32 na jednotlivé dny neodhadovat.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Cílový počet účastníků | 32 | 24 |
| Přímé akceptace | 23 | 20 |
| WC | 3 | 4 |
| Řádné Q postupy | 6 | 6 vítězů sekcí |
| SE rezervace v publikovaném acceptance listu | 0 | nevztahuje se |
| Nasazení | 8 | 12 |
| BYE | 0 | 0 |
| Struktura | vyřazovací pavouk 32 | 6 nezávislých vyřazovacích sekcí po 4 |
| Kola / nominální uzly | 5 / 31 | 2 / 18 |
| Formát | BO3 setů | BO3 setů |

Main 23+3+6=32, Q 20+4=24; Q 12+6=18, Main 16+8+4+2+1=31; celkem 49 uzlů. Main originál vizuálně: 6 Q (6,15,19,23,26,29), 3 WC (18,20,28), všech 8 seedů, žádný BYE ani LL; jeden pozdější walkover a skreč nepřepisují plán. Q kompletní textový pavouk BRI24-14 obsahuje 24 účastníků, všech 12 seedů, čtyři WC, šest sekcí po 4, bez BYE. Main i Q strukturu nezávisle potvrzuje dobová acceptance list BRI24-5; pozor na obecnou §7.08 šablonu 16 Q/4 postupů pro ATP 250. Pro Brisbane má přednost skutečná nominální ročníková dokumentace. Nominální SE 0 zde dle listiny, nikoli plošný zákaz SE.

### 5. Dobová pravidla ATP (nikoli Grand Slam)

- 2024 ATP §7.03/7.08/7.10/7.12/7.15–16 (BRI24-15): vstup podle rankingu a příslušných pravidel entry protection; Main 8 seedů, #1 na řádku 1 a #2 na řádku 32, skupiny 3–4 na 9/24, skupina 5–8 na 8/16/17/25 losem. Pro Q24 je 12 seedů; 6 sekcí po 4, dva seedy na sekci. Kvalifikanti jsou po ukončení Q přiřazeni do volných Main pozic losem, nikoli předem pevnou vazbou.
- ATP §7.20 A: LL prioritně z poražených posledního Q kola, teprve poté z dřívějších kol; pokud při skončení Q nejsou volná místa, pořadí dle rankingu pro Q seeding (bez protected ranking). Při jednom volném místě los mezi dvěma nejvýše postavenými; při nejméně dvou odhlášeních počet +1; následně ranking. Denní sign-in 30 min před prvním zápasem. To je jiný postup než Grand Slam 4 / počet+2.
- Předpis §7.20 rozlišuje obsazení volných míst před Q a po začátku Q, náhradu seedu před prvním OOP a další případy. Nenahrazovat obecnými pravidly Grand Slam. BO3 v obou fázích potvrzeno losy BRI24-1/14.

### 6. Body a prize money (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 95340 |
| Finalista | 1 | 165 | 55665 |
| SF | 2 | 100 | 32800 |
| QF | 4 | 50 | 18700 |
| R16 | 8 | 25 | 11000 |
| R32 | 16 | 0 | 6640 |
| Q postupující | 6 | 13 | samostatná odměna neuvedena |
| Q2 prohra | 6 | 7 | 3600 |
| Q1 prohra | 12 | 0 | 2000 |

Main peníze i body vizuálně z originálního ATP losu (BRI24-1); Q peníze z dobové tabulky BRI24-8 a historického přehledu BRI24-16, Q body dle dobového ATP 2024 §9.03 G singles table a aktualizace 16. 2. (BRI24-17), odpovídají i Q archivu BRI24-14. Původní znění bodového §9.03 G.4 v ITF hostovaném PDF uvádí starých 6 bodů v textu, ale jeho nová tabulka 7 a opravený únorový předpis výslovně 7; používat 7. Q body přičítají k Main výsledku. Prohra R32 Main 0 bodů. Nominální součet Main 485645 USD, Q 45600 USD = 531245 USD. Celková mužská prize money 661 585 USD dle ITF, zahrnuje i čtyřhru; total financial commitment 739 945 USD z ATP losu není synonymum prize money. Částka 1 736 763 v kombinovaných OOP je ženská dotace, nikoli mužská. Nominální součet neslouží k rekonstrukci skutečných individuálních plateb.

### 7. Kontrola a mezery

I/T/D/B/P doloženy. H*: rekonstruované okno R32/R16 z původních denních programů a výslovně doloženého odkladu, nikoli nově získaný kompletní předturnajový program. E*: konkrétní rank dates a kvóty z dobového přepisu acceptance listu, lhůty odvozené podle §7.03, Q draw time neznámý. R*: ATP pravidla indexovaný text, vizuální vykreslení PDF selhalo. Z*: originální Main PDF vizuálně ověřeno, původní Q PDF a detail sheet nedostupné, Q struktura nezávisle potvrzena textovým úplným losem a dobovým acceptance listem. OOP získány textově, screenshoty selhaly. Žádný hash se nepředstírá. Srovnání s `buuk`: kalendář Brisbane 2024 již má správné Main datum 31.12.2023–7.1.2024; sportovní profil pro tento ročník v katalogu `squash_sporting_profiles_v1.json` není. Žádná změna runtime. Další Hong Kong 2024.

### 8. Zdroje (BRI24)

- BRI24-1: [originální ATP Main los](https://www.protennislive.com/posting/2024/339/mds.pdf), str. 1 vizuálně ověřena (datum, povrch, 32 míst, 6Q/3WC, body, prize, supervisor).
- BRI24-2: [Tennis Australia oznámení návratu 2024](https://www.tennis.com.au/brisbane-international/news/2023/09/brisbane-international-returns-in-2024); [dobový mužský entry preview](https://tennis-infinity.com/atp/2024-brisbane-international-atp-entry-list-nadal-rune-shelton-more) potvrzuje venkovní tvrdý povrch a 32 Main.
- BRI24-3: [pořadatel — los 30.12.](https://www.tennis.com.au/brisbane-international/news/2023/12/draws-set-for-brisbane-international-2024); [Tennis Australia mužský los](https://www.tennis.com.au/fan-zone/news/2023/12/30/aussies-contenders-handed-brutal-draws-at-brisbane-international-2024).
- BRI24-4: [pořadatel OOP 30.12.](https://www.brisbaneinternational.com.au/documents/bi-2024-order-of-play/), text dostupný, screenshot timeout.
- BRI24-5: [dobový přepis acceptance listů 13.12.2023](https://www.tennisteen.it/entry-list/atp/24092-atp-entry-list-1-7-gennaio-2024.html), Brisbane Main/Q odděleně.
- BRI24-6: [pořadatel OOP 31.12.](https://www.brisbaneinternational.com.au/documents/bi-2024-order-of-play-day-one-revised/), text, screenshot timeout; 6 Q2 a současně Main.
- BRI24-7: [ATP Q1 30.12.](https://www.atptour.com/en/news/thiem-mccabe-brisbane-2024-saturday-qualifying).
- BRI24-8: [dobová tabulka odměn USD](https://firstsportz.com/tennis-prize-money-for-the-2024-brisbane-international); [ITF ročník](https://www.itftennis.com/en/tournament/brisbane/aus/2024/m-250-aus-2024-002/draws-and-results/) potvrzuje mužskou dotaci, ale jeho týdenní datum 1.–7.1. není přesné Main okno.
- BRI24-9: [dobový rozpis a výsledky](https://www.sportingnews.com/au/tennis/news/brisbane-international-schedule-scores-results-2024-tennis/d718f35dac0afe7d42f20934), [Khel Now 5.1.](https://khelnow.com/tennis/2024-01-brisbane-international-2024-fixtures-schedule-timings-results-telecast-live-streaming), používat jen ověřené rozlišení kola, ne jeho chybné označení R32 jako R16 u jednoho zápasu.
- BRI24-10: [pořadatel OOP 3.1.](https://www.brisbaneinternational.com.au/wp-content/uploads/2024/01/ORDER-OF-PLAY-WEDNESDAY-3-JANUARY-2024-l.pdf), indexovaný text; [TennisActu 3.1. výslovně potvrzuje úterní odklad Humbert/Michelsen](https://www.tennisactu.net/news-atp-brisbane-malade-humbert-s-en-est-sorti-rune-a-dejoue-un-piege-106988.html).
- BRI24-11: [Tennis Australia 3.1.](https://www.tennis.com.au/brisbane-international/news/2024/01/quarterfinal-spots-secured-in-dramatic-mens-singles-encounters), [4.1.](https://www.tennis.com.au/fan-zone/news/2024/01/04/hijikata-joins-thompson-and-duckworth-in-brisbane-international-quarterfinals).
- BRI24-12: [pořadatel QF OOP 5.1.](https://www.brisbaneinternational.com.au/wp-content/uploads/2024/01/ORDER-OF-PLAY-FRIDAY-5-JANUARY-2024.pdf), text, screenshot přesměroval.
- BRI24-13: [pořadatel SF OOP 6.1.](https://www.brisbaneinternational.com.au/documents/2024-brisbane-international-order-of-play-day-seven-6-january-2024/), indexovaný text.
- BRI24-14: [úplný nezávislý Q pavouk](https://en.tennistemple.com/competitions/brisbane/2024/draw-qualifications), text; [originál ATP Q](https://www.protennislive.com/posting/2024/339/qs.pdf) přístup selhal; [detail sheet](https://www.protennislive.com/posting/2024/339/ds.pdf) nedostupný.
- BRI24-15: [ATP Rulebook 2024, Competition, verze 21.12.](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_21dec.pdf), §7.03,7.08,7.10,7.12,7.15,7.16,7.20, indexovaný text, screenshot 403.
- BRI24-16: [historická tabulka odměn](https://tenniscompanion.org/prize-money/brisbane/), řádek 2024, nezávislá kontrola.
- BRI24-17: [ATP dobové oznámení bodů](https://www.atptour.com/en/news/2024-rankings-points-update), [ITF hostovaná bodová tabulka 2024](https://www.world.tennis/media/11555/2024-atp-rankings-section.pdf), [oprava 16.2.](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-9_pepperstone-atp-rankings_16feb.pdf), text ověřen, screenshot nedostupný.


## Hong Kong 2024

**Stav:** HOTOVO v nominálním rozsahu, H/E/R/P/Z s omezeními důkazů popsanými níže. Kontrola 2026-11-27. Nominální Q odměny podpořené dvěma shodnými sekundárními tabulkami, nikoli originálním Q PDF; při získání primárního důkazu znovu ověřit.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Bank of China Hong Kong Tennis Open | HK24-1/2 |
| Ročník / disciplína / kategorie | sezona 2024 / mužská dvouhra / ATP 250 | HK24-1/2 |
| ATP ID | 336 | HK24-12 |
| Dějiště | Victoria Park Tennis Stadium, Causeway Bay, Hong Kong, Čína | HK24-3/4 |
| Povrch | venkovní tvrdý, Greenset | HK24-1/3 |
| Časové pásmo | Asia/Hong_Kong, HKT UTC+08:00, bez sezónní změny | místní lokalita |
| ATP supervisor | Roland Herfel | HK24-1, vizuální kontrola zápatí |
| Měna | USD (ne HKD; vstupenky v HKD nejsou prize money) | HK24-1/2/3 |
| Míče, ředitel, individuální diety | NEOVĚŘENO | doplňková metadata |

ATP oznámila přesun licence z Pune do Hongkongu v červnu 2023. Jde o ročník 2024, nikoli 2023, i když kvalifikace začala 31. prosince. Oficiální ATP kalendář rozlišuje Main 1.–7. ledna od celého pořadatelského okna 31. prosince–7. ledna.

### 2. Přihlášky a losování

| Pole | Údaj | Zdroj / význam |
|---|---|---|
| Main rank date | 2023-12-04 | HK24-5, dobový přepis mužské acceptance list |
| Q rank date | 2023-12-11 | HK24-5 |
| Nominální Main deadline | 2023-12-04 12:00 US Eastern = 2023-12-05 01:00 HKT | odvozeno z ATP §7.03, 28 dní před pondělím 1.1.; bez originálního detail sheet |
| Nominální Q deadline | 2023-12-11 12:00 US Eastern = 2023-12-12 01:00 HKT | odvozeno z §7.03, 21 dní před pondělím; ne samostatně potvrzená uzávěrka |
| Q los | před 2023-12-31; přesné datum/hodina NEOVĚŘENY | HK24-6 |
| Main los | kopie původního losu se zástupnými Q pozicemi, přesný okamžik NEOVĚŘEN | HK24-1 |
| Q | 2023-12-31–2024-01-01 | HK24-4/6/7 |
| Main | 2024-01-01–07 | HK24-1/2/3 |
| Otevírací ceremoniál | 2024-01-01 13:20 HKT, před prvními Main zápasy na Centre Court | HK24-13, plán |
| Finále | 2024-01-07 | HK24-2/8; přesná hodina neověřena |

Rank date není nutně deadline. Pro Main HK24-5 uvádí cutoff 70 k 13.12., zatímco předstartovní los má v zápatí Bonzi 73; oba údaje jsou historický kontext, ne nominální pravidlo. Main i Q se dne 1.1. překrývají. Není důvod předpokládat, že kvalifikace musí skončit o den dříve než Main.

### 3. Nominální harmonogram

| Kolo | Lokální datum/okno | Nominální zápasy | Důkaz |
|---|---|---:|---|
| Q1 | 2023-12-31 | 8 | HK24-4/6/7 |
| Q2 | 2024-01-01 | 4 | HK24-4/6/7 |
| R32 | 2024-01-01–02 | 12 | HK24-4, předem publikované vstupenky pro první kolo |
| R16 | 2024-01-03–04 | 8 | HK24-9, indexovaný pořadatelský booklet, podpůrný denní archiv HK24-8 |
| QF | 2024-01-05 | 4 | HK24-9/8 |
| SF | 2024-01-06 | 2 | HK24-8 |
| F | 2024-01-07 | 1 | HK24-2/8 |

Q 2 kalendářní dny, Main 7 dní, celý turnaj 8 dní. Q 8+4=12, Main 12+8+4+2+1=27. Pořadatel 14.12.2023 výslovně avizoval 12 Q a 27 Main singlových zápasů (HK24-10). BYE čtyři nejsou zápasy: kapacita 32 má 31 potenciálních uzlů, ale 27 nominálně hraných. R16 okno 3.–4.1. a QF 5.1. potvrzuje indexovaný booklet, jeho přímé PDF načtení skončilo 502; nelze tvrdit vizuální kontrolu. SF/F potvrzeny dobovým denním archivem, finále také ATP. Původní kompletní předturnajový OOP všech dnů nezískán; denní počty vícedenních kol neodhadovat.

### 4. Struktura a pravidla

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Plánovaní účastníci | 28 | 16 |
| Přímé akceptace | 21 | 14 |
| WC | 3 | 2 |
| Q postupy | 4 | 4 vítězové sekcí |
| SE rezervace | 0 v dobovém seznamu | nevztahuje se |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola | 5 | 2 |
| Nominálně hrané zápasy | 27 | 12 |
| Formát | BO3 setů | BO3 setů |

HK24-5 přímo uvádí nominální kvóty. 21+3+4=28 a 14+2=16. Předstartovní ATP los HK24-1 vizuálně potvrzuje BYE na pozicích 2,10,23,31, Q placeholders 3,5,6,12; WC 13,15,26, 8 seedů. Pozice jsou skutečný konkrétní los, nikoli předem pevné budoucí rozmístění kvalifikantů. Konečný Main archiv HK24-11 a Q archiv HK24-6 potvrzují 4 řádné Q vítěze, 2 Q WC, 8 Q seedů, žádný Q BYE, čtyři čtyřčlenné sekce a 8+4 zápasů. BO3 potvrzují výsledky obou fází. Nominální počet SE 0 pouze pro tuto listinu.

Použít dobová ATP pravidla §7.03/7.08/7.10/7.12/7.15–16/7.20 (BRI24-15), nikoli Grand Slam pravidla. Top 4 seeds dostávají BYE, další 4 hrají první kolo. Q dva seedy v každé sekci; vítězové Q se losují do volných Main pozic po Q. LL přednostně poražení posledního Q kola, teprve při nedostatku dřívější kola; při volném místě na konci Q los mezi nejvýše postavenými dvěma, při více místech počet +1, potom ranking; pokud nejsou na konci Q volná místa, pořadí podle rankingu pro Q seeding. Pravidla náhrad před/po OOP dle ATP předpisu. Hlavní singlová výjimka v bodování: hráč s BYE, který prohraje svůj první hraný zápas (R16), má 0 bodů, nikoli 25; přímo poznámka ATP HK24-2.

### 5. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 100000 |
| Finalista | 1 | 165 | 57845 |
| SF | 2 | 100 | 34000 |
| QF | 4 | 50 | 20000 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 11600 |
| R32 | 12 | 0 | 7200 |
| Q postupující | 4 | 13 | samostatná odměna neuvedena |
| Q2 prohra | 4 | 7 | 3550 |
| Q1 prohra | 8 | 0 | 1935 |

Main tabulka vizuálně z kopie originálního ATP losu HK24-1, nezávisle totožné hodnoty dobový ATP Preview & Day 1, str. 2 (HK24-2, text; screenshot 403). Q body z dobového ATP rulebooku BRI24-17 a Q archivu HK24-6. Q prize 3550/1935 shodně TennisTemple a TennisCompanion historický řádek 2024 (HK24-6/14); originální Q PDF není dostupné. **Rozpor zdrojů:** CanalTenis tabulka HK24-15 uvádí pro 2024 přesně částky Brisbane, které odporují oběma primárním Main dokladům Hongkongu. SportsLite uvádí odměny odpovídající jiným ročníkům a chybně 13 bodů za Main R32 prohru; nepoužívat. Tato tabulka Q 3550/1935 je sekundárně doložený nejlepší kandidát, nikoli primárně ověřená hodnota. Pokud bude originální Q PDF získáno, znovu ověřit a případně opravit. Bodování po BYE má zvláštní pravidlo uvedené výše, Q body se přičítají dle ATP. Nominální součet Main 485045 USD; Q 29680 USD podle sekundárních částek; celkem 514725 USD (ne celoturnajová dotace). Total financial commitment 739945 USD dle Main losu, nelze zaměnit za prize pool.

### 6. Evidence a porovnání s katalogem

I/T/D/B pokryty. H*: booklet pouze indexovaný text a denní archivy, ne kompletní původní OOP; E*: nominální data uzávěrky odvozena, rank dates z dobového přepisu, losovací časy neznámé. R*: ATP rulebook doložen textově v BRI24-15/17, vizuální dostupnost omezená. P*: Main primárně potvrzen, Q sekundární shoda, konflikt zdrojů explicitně označen. Z*: Main kopie vizuálně, originál ATP Q/DS nedostupný a žádné PDF SHA-256 nezískány. V `buuk` (`29784d51d01d9d747705be8abae30f0c82706c1e`) již Main datum 1.–7.1.2024, ale tento ročník není ve sportovních profilech. Žádný převod nebo změna runtime. Další Adelaide 2024.

### 7. Zdroje (HK24)

- HK24-1: [kopie předstartovního originálního ATP Main losu](https://www.raquetc.com/wp-content/uploads/2023/12/ATP-250-Hong-Kong-2023-quadro-principal.pdf), str. 1 vizuálně ověřena; jméno souboru 2023 nemění datum 1.–7.1.2024 v hlavičce.
- HK24-2: [ATP Preview & Day 1, 1.1.2024](https://www.atptour.com/-/media/85aa0b241ef349c6ad1c6e44f129e06b.pdf), str. 2 textově, screenshot 403.
- HK24-3: [ATP oznámení návratu 12.6.2023](https://www.atptour.com/en/news/hong-kong-atp-250-2024), [HKCTA oznámení 22.8.2023](https://www.tennishk.org/en/press-release/bochk-named-title-sponsor-of-atp-mens-professional-tennis-tour-event-in-2024/).
- HK24-4: [dobový prodejní program 2024](https://www.klook.com/event-detail/101022105-2024-bochk-tennis-open/), Q 31.12. a 1.1., Main R32 1.–2.1.
- HK24-5: [dobový přepis Main/Q acceptance list 13.12.2023](https://www.tennisteen.it/entry-list/atp/24092-atp-entry-list-1-7-gennaio-2024.html).
- HK24-6: [úplný Q pavouk a sekundární body/peníze](https://en.tennistemple.com/competitions/hong-kong-2024/37822/draw-qualifications), text.
- HK24-7: [Sky výsledky Q1 31.12.2023](https://www.skysports.com/tennis/scores-schedule/31-12-2023); Q2 termín též předem HK24-4.
- HK24-8: [dobový/archivní rozpis TNT](https://www.tntsports.co.uk/tennis/atp-hong-kong/2024/calendar-results.shtml), [ATP finále 7.1.](https://www.atptour.com/en/news/rublev-ruusuvuori-hong-kong-2024-final).
- HK24-9: [pořadatelský booklet](https://livescores.hkmenstennisopen.com/livescores/uploaded/Booklet-web.pdf), indexovaný text s 3.–4.1. R16 a 5.1. QF; přímý přístup 502, obrazová kontrola nemožná.
- HK24-10: [pořadatel 14.12.2023](https://www.hkmenstennisopen.com/en/news/news_v1i9gstbzelcqdrsp3g5jn1c9zkpfvpu/), indexovaný text 12 Q + 27 Main; aktuální JS stránka text historického článku nevykreslí.
- HK24-11: [konečný Main pavouk](https://en.tennistemple.com/competitions/hong-kong-2024/37822/draw), text.
- HK24-12: [TennisTV ročník 336_2024](https://www.tennistv.com/tournaments/336_2024/hong-kong), [ATP identita 336](https://www.atptour.com/en/tournaments/hong-kong/336/overview).
- HK24-13: [SCMP předturnajový partnerský článek](https://www.scmp.com/presented/sport/topics/bank-china-tennis-open/article/3246462/top-10-things-do-bank-china-hong-kong-tennis-open-2024).
- HK24-14: [TennisCompanion historické odměny](https://tenniscompanion.org/prize-money/hong-kong/), indexovaný řádek 2024, přímý přístup 403.
- HK24-15: [CanalTenis tabulka s rozporem](https://canaltenis.com/el-prize-money-del-atp-hong-kong/), [SportsLite 31.12.2023 s rozporem](https://thesportslite.com/latest-sports-news/hong-kong-open-2024-prize-money-and-breakdown/); nepoužívat jako autoritu. [Originální ATP Main](https://www.protennislive.com/posting/2024/336/mds.pdf), [Q](https://www.protennislive.com/posting/2024/336/qs.pdf), [DS](https://www.protennislive.com/posting/2024/336/ds.pdf) v tomto průchodu nedostupné.

