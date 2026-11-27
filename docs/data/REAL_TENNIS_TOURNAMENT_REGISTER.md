# Historický registr tenisových turnajů — mužská dvouhra

**Stav k 2026-11-27: 2 ročníky, Wimbledon 2024 a 2025.** Tento jediný rozšiřitelný dokument je rešeršní registr reálného tenisu. Není autoritativním runtime balíčkem. Neobsahuje převod na squash, Run, simulační týdny, sloty, vlastní bodování ani změny existujících katalogů. Navazujeme vždy jedním ročníkem; další nepřidávat, dokud není předchozí zkontrolován proti povinnému seznamu a jeho zbývající mezery výslovně zařazeny. Rozsah: mužská profesionální dvouhra včetně kvalifikací; další disciplíny pouze jako kontext souhrnných financí či kalendáře.

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
| 2025 | [Wimbledon](#wimbledon-2025) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |

`*` H: doložena okna kol; přesné původní počty zápasů jednotlivých dnů u vícedenních kol se nedokládají odhadem. Z: dobové zdroje jsou dohledatelné, některé pouze indexovaným textem; chybějí nezávisle získané PDF bajty/otisky. Obojí je transparentně zaznamenáno. U 2025 E*: datum uzávěrek odvozeno z dobového předpisu, hodina losu Q neověřena, ale Main los doložen; R*: ATP rankingový PDF dostupný indexovaným textem, ne novým vizuálním přístupem.

**Součet registru:** 2 zpracované ročníky; 2 hotové v nominálním rozsahu; 0 rozpracovaných; ostatní ročníky zatím nejsou v registru, bez ohledu na stav jiných PR.

### Fronta dalších ročníků (pracovní pořadí, nikoli převzaté důkazy)

| Pořadí | Ročník a turnaj | Stav |
|---|---|---|
| 1 | Wimbledon 2024 | HOTOVO (nominální rozsah) |
| 2 | Wimbledon 2025 | HOTOVO (nominální rozsah) |
| 3 | Australian Open 2024 | NEZAHÁJENO |
| 4 | Roland Garros 2024 | NEZAHÁJENO |
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
| Ředitel | Jamie Baker | W25-1 |
| Měna | GBP | W25-5 |

Míče, jméno rozhodčího a adresní detail konkrétní edice nebyly samostatně ověřeny: nevyplňujeme z 2024. Nejde o povinná data I.

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
- Dle ATP Ranking Rulebook 2025 (W25-15, indexovaný text, přímé PDF 403): body za kvalifikaci se přičítají k dosaženému Main výsledku; divoká karta při prohře v prvním kole Main nezíská standardních 10 bodů. Individuální výpočet LL a ostatních výjimek není zde řešen.
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
| R | Grand Slam předpis 2025 vizuálně ověřen na str. 7,24–32, ATP rankingová pravidla dohledána indexovaným textem (PDF 403); individuální historické výjimky mimo povinný rozsah |
| Z | dohledatelné dobové zdroje; některé indexované, SHA-256 všech originálů zatím nezískány |
| Další doplňky | jména rozhodčího/míče, přesné hodiny jednotlivých zápasů, vývoj všech náhrad nejsou ověřeny; nejsou podmínkou nominálního rozsahu |

Vizuální podklady potvrzují stejnou plánovanou geometrii jako 2024. Nominální kvóty a body se shodují také s dříve uloženými zdrojovými údaji Grand Slam Draft #1903; zde jde o samostatně ověřený záznam, nikoli nový runtime profil. Další ročník v pořadí Australian Open 2024.

### 7. Zdroje (W25)

- W25-1: [ATP 2025 Wimbledon preview](https://www.atptour.com/en/news/wimbledon-2025-history-draw-schedule), dobový indexovaný text: identita, plán Q/Main, los Main.
- W25-2: [originální Main los 2025](https://www.wimbledon.com/en_GB/scores/draws/2025_MS_draw.pdf), obě strany vizuálně ověřeny, aktualizace 13. 7. 2025.
- W25-3: [originální Q los 2025](https://www.wimbledon.com/en_GB/scores/draws/2025_QS_draw.pdf), obě strany vizuálně ověřeny, aktualizace 3. 7. 2025.
- W25-4: [Grand Slam Rule Book 2025](https://www.wimbledon.com/pdf/Grand_Slam_Rulebook_2025.pdf), tištěné str. 7 a 24–32 (PDF indexy 12,29–37), vizuálně ověřeny.
- W25-5: [Wimbledon Prize Money 2025](https://www.wimbledon.com/pdf/Wimbledon_Prize_Money_2025.pdf), první strana vizuálně ověřena; [ATP prize money](https://www.atptour.com/en/news/wimbledon-2025-prize-money).
- W25-6: oficiální Q OOP: [a 23. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF1.pdf), [b 25. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF3.pdf), [c 26. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF4.pdf), [d 24. 6.](https://www.wimbledon.com/en_GB/scores/2025/schedule/pdf/schedulePDF2.pdf) (u d viz další kontrolu; neověřený přesný počet zápasů); a/b/c první strany vizuálně ověřeny.
- W25-7: [dobový plán vysílání ESPN](https://espnpressroom.com/press-release/espn-presents-first-ball-to-last-ball-of-the-championships-wimbledon-2025-june-30-july-13-2025/) a [předturnajový rozpis](https://www.business-standard.com/sports/other-sports-news/wimbledon-2025-schedule-live-timings-ist-live-streaming-telecast-125062900210_1.html).
- W25-8: [oficiální Wimbledon Debenture Handbook 2025](https://www.wimbledon.com/pdf/2025_Debenture_Handbook.pdf), oddíl New for 2025, indexovaný text; změna finále a ELC.
- W25-9: [BBC dobový přehled](https://bbc.com.im/sport/tennis/articles/c056ly89q6go), termíny a Roehampton (indexovaný text).
- W25-10: [GOV.UK BST](https://www.gov.uk/when-do-the-clocks-change).
- W25-11: [Radio Times denní harmonogram](https://www.radiotimes.com/tv/sport/tennis/wimbledon-2025-order-of-play/), 13. 7. 2025, všechna okna kol a plán finále.
- W25-12: [Tennis365 předturnajový přehled](https://www.tennis365.com/tennis-features/wimbledon-2025-dates-when-is-draw-prize-money-emma-raducanu-seeded), dobový běžný časový program.
- W25-13: [ATP poslední přímé akceptace 24. 6.](https://www.atptour.com/en/news/wimbledon-2025-last-direct-entries), 16 Q postupových míst.
- W25-14: [BBC kvalifikační finále 26. 6.](https://www.bbc.co.uk/sport/tennis/articles/ckgj184pdrno), pětisetový formát.
- W25-15: [ATP Ranking Rulebook 2025 §IX.G](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf), tištěná str. 264, indexovaný text (403 při přímém načtení); [ATP turnaj 540](https://www.atptour.com/en/tournaments/wimbledon/540/overview). [ATP Detail Sheet 2025](https://www.protennislive.com/posting/2025/540/ds.pdf) nedostupný při přímém načtení; neoznačovat za ověřený.

