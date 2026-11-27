# Historický registr tenisových turnajů — mužská dvouhra

**Stav k 2026-11-27: 4 ročníky, Wimbledon 2024 a 2025, Australian Open 2024, Roland Garros 2024.** Tento jediný rozšiřitelný dokument je rešeršní registr reálného tenisu. Není autoritativním runtime balíčkem. Neobsahuje převod na squash, Run, simulační týdny, sloty, vlastní bodování ani změny existujících katalogů. Navazujeme vždy jedním ročníkem; další nepřidávat, dokud není předchozí zkontrolován proti povinnému seznamu a jeho zbývající mezery výslovně zařazeny. Rozsah: mužská profesionální dvouhra včetně kvalifikací; další disciplíny pouze jako kontext souhrnných financí či kalendáře.

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
| 2024 | [Roland Garros](#roland-garros-2024) | ✓ | ✓ | ? | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | ROZPRACOVÁNO (H: původní Q2) |

`*` H: doložena okna kol; přesné původní počty zápasů jednotlivých dnů u vícedenních kol se nedokládají odhadem. Z: dobové zdroje jsou dohledatelné, některé pouze indexovaným textem; chybějí nezávisle získané PDF bajty/otisky. Obojí je transparentně zaznamenáno. U 2025 E*: datum uzávěrek odvozeno z dobového předpisu, hodina losu Q neověřena, ale Main los doložen; ATP rankingový předpis 2025 byl následně úspěšně zkontrolován i vizuálně na tištěné str. 264. AO 2024 H*: oficiální říjnový program textově dostupný, obrazové vykreslení selhalo; potvrzen dobovým programem pořadatele a předturnajovým přehledem. R*: dobový Grand Slam předpis v textovém zrcadle a ATP oznámení bodů; přímé PDF rulebooků nebylo dostupné.

**Součet registru:** 4 zpracované ročníky; 3 hotové v nominálním rozsahu; 1 rozpracovaný; ostatní ročníky zatím nejsou v registru, bez ohledu na stav jiných PR.

### Fronta dalších ročníků (pracovní pořadí, nikoli převzaté důkazy)

| Pořadí | Ročník a turnaj | Stav |
|---|---|---|
| 1 | Wimbledon 2024 | HOTOVO (nominální rozsah) |
| 2 | Wimbledon 2025 | HOTOVO (nominální rozsah) |
| 3 | Australian Open 2024 | HOTOVO (nominální rozsah) |
| 4 | Roland Garros 2024 | ROZPRACOVÁNO (původní denní okno Q2) |
| 5 | US Open 2024 | NEZAHÁJENO |
| 6 | Australian Open 2025 | NEZAHÁJENO |
| 7 | Roland Garros 2025 | NEZAHÁJENO |
| 8 | US Open 2025 | NEZAHÁJENO |

Po prvním bloku Grand Slamů 2024–2025 zpracovávat ostatní turnaje ATP 2024 a 2025 chronologicky podle dobového kalendáře, následně další ročníky postupně. Záznamy nikdy nevyplňovat pouze z podobného ročníku. Přesný postup u každého ročníku: (1) identita a dobový detail sheet; (2) plán fází a kol; (3) nominální struktura Main/Q a entry; (4) dobový rulebook, body a odměny; (5) porovnání nezávislého dokladu/losu, aritmetické kontroly, záznam rozporů; (6) aktualizace tabulky pokrytí. Při blokujícím neověřeném povinném údaji jej označit, necertifikovat profil a nejdříve řešit jeho doložení.

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
| [2024](#roland-garros-2024) | Roland Garros | Grand Slam | 2024-05-20–2024-05-24 | 2024-05-26–2024-06-09 | ROZPRACOVÁNO: původní denní plán Q2 |

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

**Stav:** ROZPRACOVÁNO, 8/9 oblastí. Chybí jedno přesné rozlišení původního okna Q2 od pozdějšího denního programu. Nezávislá rešerše 2026-11-27. Referencí zůstává nominální plán, ne historické odklady.

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
| Rozhodčí a individuální diety | NEOVĚŘENO | doplňková metadata |

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
| Q2 | 2024-05-22 doloženo; 23. 5. další zápasy v denním OOP | 32 | RG24-9, RG24-11; původní předturnajové rozložení Q2 mezi 22.–23. 5. NEOVĚŘENO |
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

Q 5 kalendářních dnů; Main 15 dnů; celé okno 21 dnů. Celkově Q 112 + Main 127 = 239 nominálních uzlů. H je zatím otevřeno kvůli nejasnosti Q2: dobový OOP 23. 5. obsahuje Q2 i Q3, avšak neprokazuje sám o sobě, zda bylo Q2 na 23. 5. naplánováno už před turnajem, nebo šlo o přesun. Nevydávat skutečný program za původní plán. U Main kola zůstávají původní okna, navzdory dešti 29.–30. 5. (RG24-13). Předturnajový článek Sky Sports obsahuje posunuté číselné datum u prvních dnů (např. neděle 25. 5., což byl ve skutečnosti sobotní den); jako důkaz těchto dnů používáme konzistentní předturnajový kalendář a datované ATP notes, nikoli chybná čísla Sky. Neodhadovat rozložení všech uzlů rovnoměrně na dny.

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
| H | 7 Main kol a přestávky doloženy; původní Q2 denní okno otevřené, necertifikovat |
| E | nominální kvóty a losovací termíny doloženy, vstupní data odvozena z předpisu; originální mužský detail sheet chybí |
| D | obě strany Main PDF a obě strany archivní kopie Q PDF vizuálně ověřeny; nominální struktura bez rozporu |
| R/B | 2024 rulebook dostupný přes dříve doložený textový zdroj, ATP mužské body přímo v dobovém preview; Q výsledky a struktura potvrzují formát |
| P | Main přímo ATP, Q shoda dostupných nezávislých tabulek, kontrola součtů; původní PDF dotace Q nebylo získáno |
| Z | dobové zdroje doloženy; některé PDF screenshoty 403/500; žádné SHA-256 nepředstíráme |

Další krok: uzavřít H (předturnajový plán Q2; při potvrzení odkladu oddělit původní a pozdější OOP), teprve potom US Open 2024. Do stávajících balíčků ani Grand Slam Draft #1903 se nezasahuje.

### 7. Zdroje (RG24)

- RG24-1: [ATP men's tournament preview 2024](https://www.atptour.com/-/media/5275ccac675646a0bb7f172776df7588.pdf), str. 3 (seeds, WC, Q, LL), str. 5 (body/odměny), text; screenshot 403.
- RG24-2: [WTA dobové informace 22. 5.](https://www.wtatennis.com/news/4025655/roland-garros-2024-draws-dates-prize-money-and-what-you-need-to-know), lokalita, povrch, časové pásmo, míče a termíny; ženské body nepoužívat.
- RG24-3: [FFT časový harmonogram z dubna 2024](https://rg-organisation.fft.fr/sites/default/files/2024-04/RG24%20-%20tableau%20des%20horaires.pdf), text tabulek získán, screenshot 500 (údržba).
- RG24-4: [FFT oznámení mužských a ženských WC 14. 5.](https://www.rolandgarros.com/en-us/article/2024-wildcards-men-women-singles-qualifying-rounds).
- RG24-5: dobový Grand Slam Rule Book 2024 §2/3 a scoring; viz AO24-5 / S16 v témže dokumentu; textové zrcadlo, ne nově vizuálně ověřený originál.
- RG24-6: [ATP entry list 17. 4.](https://www.atptour.com/en/news/roland-garros-2024-entry-list), [pořadatel 16. 4.](https://www.rolandgarros.com/en-us/article/roland-garros-2024-entry-list-men-women-protected-ranking).
- RG24-7: [ATP dobový přehled](https://www.atptour.com/en/news/roland-garros-2024-history-draw-schedule), indexovaný text, přímé 403; [pořadatel Q los 19. 5.](https://www.rolandgarros.com/en-us/article/qualifying-draws-unveiled-roland-garros-2024).
- RG24-8: [kopie originálního Q losu 19. 5. 14:27](https://www.tiebreaktennis.it/wp-content/uploads/2024/05/Roland-Garros-2024-Qualificazioni-maschili.pdf), obě strany vizuálně; [originál aktualizovaný 20. 5.](https://rg-organisation.fft.fr/sites/default/files/2024-05/Mens_Qualifying_20240520220332.pdf), text dostupný, screenshot 500.
- RG24-9: archivované dobové OOP: [20. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240520_OF_1716134216.pdf), [21. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240521_OF_1716224247.pdf), [22. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240522_OF_1716314941.pdf), [23. 5.](https://tennisconnected.com/wp-content/uploads/2024/05/Schedule_EN_20240523_OF_1716404146.pdf), indexované texty denních plánů, ne původní týdenní plán Q2.
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
