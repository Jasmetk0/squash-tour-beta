# Historický registr tenisových turnajů — mužská dvouhra

**Stav k 2026-11-27: 22 ročníků: všechny Grand Slamy 2024 a 2025, Brisbane, Hong Kong, Adelaide, Montpellier, Córdoba, Dallas, Buenos Aires, Rotterdam, Delray Beach, Rio de Janeiro, Doha, Los Cabos a rozpracované Auckland a Marseille 2024.** Tento jediný rozšiřitelný dokument je rešeršní registr reálného tenisu. Není autoritativním runtime balíčkem. Neobsahuje převod na squash, Run, simulační týdny, sloty, vlastní bodování ani změny existujících katalogů. Navazujeme vždy jedním ročníkem; další nepřidávat, dokud není předchozí zkontrolován proti povinnému seznamu a jeho zbývající mezery výslovně zařazeny. Rozsah: mužská profesionální dvouhra včetně kvalifikací; další disciplíny pouze jako kontext souhrnných financí či kalendáře.

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
| 2024 | [Adelaide](#adelaide-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Auckland](#auckland-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ? | ✓* | ROZPRACOVÁNO (8/9; P: Q odměny) |
| 2024 | [Montpellier](#montpellier-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Córdoba](#córdoba-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Dallas](#dallas-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Marseille](#marseille-2024) | ✓ | ✓ | ✓ | ? | ✓ | ✓* | ✓ | ✓ | ✓* | ROZPRACOVÁNO (8/9; E: nominální Q WC) |
| 2024 | [Buenos Aires](#buenos-aires-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Rotterdam](#rotterdam-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Delray Beach](#delray-beach-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Rio de Janeiro](#rio-de-janeiro-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Doha](#doha-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Los Cabos](#los-cabos-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |

`*` H: doložena okna kol; přesné původní počty zápasů jednotlivých dnů u vícedenních kol se nedokládají odhadem. Z: dobové zdroje jsou dohledatelné, některé pouze indexovaným textem; chybějí nezávisle získané PDF bajty/otisky. Obojí je transparentně zaznamenáno. U 2025 E*: datum uzávěrek odvozeno z dobového předpisu, hodina losu Q neověřena, ale Main los doložen; ATP rankingový předpis 2025 byl následně úspěšně zkontrolován i vizuálně na tištěné str. 264. AO 2024 H*: oficiální říjnový program textově dostupný, obrazové vykreslení selhalo; potvrzen dobovým programem pořadatele a předturnajovým přehledem. R*: dobový Grand Slam předpis v textovém zrcadle a ATP oznámení bodů; přímé PDF rulebooků nebylo dostupné.

**Součet registru:** 22 zpracovaných ročníků; 20 hotových v nominálním rozsahu; 2 rozpracované; ostatní ročníky zatím nejsou v registru, bez ohledu na stav jiných PR.

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
| 11 | Adelaide 2024 | HOTOVO (nominální rozsah) |
| 12 | Auckland 2024 | ROZPRACOVÁNO (P: rozpor odměn Q) |
| 13 | Montpellier 2024 | HOTOVO (nominální rozsah) |
| 14 | Córdoba 2024 | HOTOVO (nominální rozsah) |
| 15 | Dallas 2024 | HOTOVO (nominální rozsah) |
| 16 | Marseille 2024 | ROZPRACOVÁNO (E: nominální Q WC) |
| 17 | Buenos Aires 2024 | HOTOVO (nominální rozsah) |
| 18 | Rotterdam 2024 | HOTOVO (nominální rozsah) |
| 19 | Delray Beach 2024 | HOTOVO (nominální rozsah) |
| 20 | Rio de Janeiro 2024 | HOTOVO (nominální rozsah) |
| 21 | Doha 2024 | HOTOVO (nominální rozsah) |
| 22 | Los Cabos 2024 | HOTOVO (nominální rozsah) |
| 23 | Acapulco 2024 | NEZAHÁJENO |
| 24 | Dubai 2024 | NEZAHÁJENO |
| 25 | Santiago 2024 | NEZAHÁJENO |

Po prvním bloku Grand Slamů 2024–2025 zpracovávat ostatní turnaje ATP 2024 a 2025 chronologicky podle dobového kalendáře, následně další ročníky postupně. Startovní inventura: `buuk` commit `29784d51d01d9d747705be8abae30f0c82706c1e`, soubor `config/reference_packages/atp_tour_1990_2026/calendar_dates_v1.json` obsahuje 62 datovaných záznamů roku 2024, prvně Brisbane, Hong Kong, Adelaide, Auckland. Jde o pracovní seznam, ne potvrzený celkový počet historických akcí; ověřovat identitu jednotlivých položek a samostatně doplnit týmové/speciální soutěže mimo tento soubor (United Cup aj.). Neoznačovat celý rok hotový pouze podle těchto 62 položek. Záznamy nikdy nevyplňovat pouze z podobného ročníku. Přesný postup u každého ročníku: (1) identita a dobový detail sheet; (2) plán fází a kol; (3) nominální struktura Main/Q a entry; (4) dobový rulebook, body a odměny; (5) porovnání nezávislého dokladu/losu, aritmetické kontroly, záznam rozporů; (6) aktualizace tabulky pokrytí. Při blokujícím neověřeném povinném údaji jej označit, necertifikovat profil a nejdříve řešit jeho doložení. Po opakované a zdokumentované neúspěšné rešerši lze konkrétní mezeru odložit do otevřeného seznamu a pokračovat dalším ročníkem; nedochází k povýšení stavu a položka se znovu kontroluje při získání lepšího zdroje.

## Metodika evidence

- **Late Entry (LE), nově doloženo pro Montpellier 2024:** ATP Rulebook, verze 22.1.2024, §7.04 a §7.08 B.1.c, stanoví jedno rezervované LE místo v ATP 250; pro 28 hráčů 18 základních DA + 2 rezervy SE + 1 LE + 4 Q + 3 WC. Nevyužité LE místo přechází na dalšího způsobilého hráče entry listu. Způsobilost se posuzuje podle rankingu 28 dní před pondělím turnaje a původního cut-off; deadline LE je čtvrtek 10:00 US Eastern před turnajem. Rozlišovat verze pravidel: konkrétní doklad pro Montpellier existuje již v listině zveřejněné 4.1.2024, nepovažovat však datum verze rulebooku za přesné datum účinnosti ani mechanicky nepřepisovat starší turnaje. Viz MPL24-5/6/7.

- **Special Exempt (SE), doplněno při rešerši Adelaide 2024:** ATP §7.08/7.10 (verze 21.12.2023) pro ATP 250 uvádí dvě rezervy SE, podle potřeby 0–2 skutečně přidělených míst a doplnění nevyužitých míst přímými akceptacemi. Pro 28 hráčů standardně 19 základních DA + 2 rezervy SE + 4 Q + 3 WC. Rozlišovat rezervy, skutečné využití a konečnou kvótu přímých vstupů. Starší formulace Brisbane/Hong Kong „SE 0 v listině“ znamená stav přepisu listiny, nikoli důkaz nulové rezervované kapacity. Případné odlišné turnajové výjimky musejí mít vlastní důkaz. Viz ADL24-8/9. Nepřebírat SE mechanicky do Grand Slamů ani do engine.

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
| [2024](#adelaide-2024) | Adelaide International | ATP 250 | 2024-01-07–2024-01-08 | 2024-01-08–2024-01-13 | HOTOVO v nominálním rozsahu; Q/Main překryv |
| [2024](#auckland-2024) | ASB Classic | ATP 250 | 2024-01-06–2024-01-07 | 2024-01-08–2024-01-13 | ROZPRACOVÁNO: Q odměny |
| [2024](#montpellier-2024) | Open Sud de France | ATP 250 | 2024-01-28–2024-01-29 | 2024-01-29–2024-02-04 | HOTOVO v nominálním rozsahu; Q/Main překryv |
| [2024](#córdoba-2024) | Córdoba Open | ATP 250 | 2024-02-03–2024-02-04 | 2024-02-05–2024-02-11 | HOTOVO v nominálním rozsahu; bez překryvu Q/Main |
| [2024](#dallas-2024) | Dallas Open | ATP 250 | 2024-02-04–2024-02-05 | 2024-02-05–2024-02-11 | HOTOVO v nominálním rozsahu; Q/Main překryv |
| [2024](#marseille-2024) | Open 13 Provence | ATP 250 | 2024-02-04–2024-02-05 | 2024-02-05–2024-02-11 | ROZPRACOVÁNO: nominální Q WC |
| [2024](#buenos-aires-2024) | IEB+ Argentina Open | ATP 250 | 2024-02-10–2024-02-11 | 2024-02-12–2024-02-18 | HOTOVO v nominálním rozsahu; bez překryvu Q/Main |
| [2024](#rotterdam-2024) | ABN AMRO Open | ATP 500 | 2024-02-10–2024-02-11 | 2024-02-12–2024-02-18 | HOTOVO v nominálním rozsahu; bez překryvu Q/Main |
| [2024](#delray-beach-2024) | Delray Beach Open | ATP 250 | 2024-02-10–2024-02-11 (plán) | 2024-02-12–2024-02-18 (plán) | HOTOVO v nominálním rozsahu; finále přeloženo na 19.2. |
| [2024](#rio-de-janeiro-2024) | Rio Open presented by Claro | ATP 500 | 2024-02-17–2024-02-18 | 2024-02-19–2024-02-25 | HOTOVO v nominálním rozsahu; odklady deštěm odděleně |
| [2024](#doha-2024) | Qatar ExxonMobil Open | ATP 250 | 2024-02-17–2024-02-18 | 2024-02-19–2024-02-24 | HOTOVO v nominálním rozsahu; plánované sobotní finále |
| [2024](#los-cabos-2024) | Mifel Tennis Open by Telcel Oppo | ATP 250 | 2024-02-17–2024-02-18 | 2024-02-19–2024-02-24 | HOTOVO v nominálním rozsahu; plánované sobotní finále |

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


## Adelaide 2024

**Stav:** HOTOVO v nominálním rozsahu (I/T/H/E/D/R/B/P/Z), s označenými omezeními E/R/Z. Rešerše 2026-11-27. Oba originální ATP losy vizuálně ověřeny; místní mužský Q program je 7.–8. ledna, nikoli 6.–7. ledna (ženská Q / časové pásmo agregátorů).

### 1. Identita

| Pole | Hodnota | Zdroj |
|---|---|---|
| Název / disciplína | Adelaide International 2024, mužská dvouhra | ADL24-1/2 |
| Kategorie / ATP ID | ATP 250 / 8998 | ADL24-1/2 |
| Dějiště obou fází | The Drive (Memorial Drive Tennis Centre), Adelaide, South Australia, Austrálie | ADL24-3/4 |
| Povrch | venkovní tvrdý, GreenSet Cushion | ADL24-1/2/3 |
| Časové pásmo | Australia/Adelaide, ACDT UTC+10:30 v lednu | identita místa; místní OOP |
| Ředitelka | Alicia Molik | ADL24-5/6 |
| ATP supervisor | Hans-Juergen Ochs (Main), Nacho Forcadell (Q) | ADL24-1/2 zápatí |
| Měna | USD (nikoli AUD) | ADL24-1/2 |
| Míče / individuální diety | NEOVĚŘENO | doplňková metadata |

### 2. Přihlášky a termíny

| Událost | Datum / čas | Důkaz |
|---|---|---|
| Main rank date | 2023-12-11 | dobový přepis listiny ADL24-7 |
| Nominální Main deadline | 2023-12-11 12:00 US Eastern, tj. 2023-12-12 03:30 ACDT | odvozeno dle §7.03 A.1, 28 dnů před pondělím 8.1.; ne originální detail sheet |
| Nominální Q deadline | 2023-12-18 12:00 US Eastern, tj. 2023-12-19 03:30 ACDT | odvozeno dle §7.03 A.2, 21 dnů před 8.1.; mužský Q rank date samostatně NEOVĚŘEN |
| Main los | zveřejněn nejpozději 2024-01-06 | ADL24-3/9; přesný čas ceremonie NEOVĚŘEN |
| Q los | zveřejněn nejpozději 2024-01-06 19:20 (vydání OOP) | ADL24-5; okamžik losování neověřen |
| Q1 | 2024-01-07 10:00, ALT sign-in 09:30 | ADL24-5, OOP z 6.1. |
| Q2 | 2024-01-08 11:00 | ADL24-6, OOP z 7.1. |
| Main | 2024-01-08–13 | ADL24-1/3/4 |
| Finále | 2024-01-13 16:00 (publikovaný program) | ADL24-4 |

Místní termíny jsou odděleny od data/času americké uzávěrky. Historický Main cutoff 48 v prosincovém seznamu vs Fucsovics 59 při deadline a Draper 61 v konečném losu podle zápatí ATP; tyto údaje zachovat jen jako kontext různých verzí, nikoli jako pevný parametr. Pozor: oficiální hlavička Q pavouka uvádí hlavní turnajové okno 8.–13.1., nikoliv skutečné datum Q. Pro fáze použít původní denní programy.

### 3. Nominální harmonogram

| Kolo | Lokální datum | Nominální zápasy | Důkaz |
|---|---|---:|---|
| Q1 | 2024-01-07 | 8 | ADL24-5 (všech osm dvojic předem zveřejněno) |
| Q2 | 2024-01-08 | 4 | ADL24-6 (všechny čtyři kvalifikační finálové dvojice) |
| R32 | 2024-01-08–09 | 12 | ADL24-6/10, čtyři zápasy 8.1. a osm 9.1. |
| R16 | 2024-01-10 | 8 | ADL24-11/4 |
| QF | 2024-01-11 | 4 | ADL24-12 |
| SF | 2024-01-12 | 2 | ADL24-13 |
| F | 2024-01-13 | 1 | ADL24-4 |

Q 2 dny, Main 6 dní, celé okno 7 dní, protože Q2 a R32 souběžně 8.1. Předem vydané OOP 7.1. (6.1. 19:20, pozdější verze 22:07) obsahuje všech osm mužských Q1 dvojic. OOP 8.1. (7.1. 18:39) obsahuje čtyři Q2 a čtyři mužské singlové R32; OOP 9.1. vydán 8.1. 20:15 obsahuje osm zbývajících mužských singlových R32. Mužská čtyřhra v OOP rovněž označená ATP R32 se do počtu nezapočítává. 10.1. R16, 11.1. QF, 12.1. SF potvrzeny příslušnými OOP. Zdroj ADL24-4 potvrzuje celý Main harmonogram. Změny hráčů po losování nejsou změny programu. V tomto ročníku lze evidovat i konkrétní plánované počty Main R32 4+8, nikoli odhad 6+6.

### 4. Nominální struktura a SE

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Plánovaný počet účastníků | 28 | 16 |
| Základní přímé akceptace | 19 | 14 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 vítězové sekcí |
| SE rezervy | 2, nevyužité se mění na DA | nevztahuje se |
| Přímé akceptace při nulovém SE | 21 | 14 |
| Nasazení | 8 | 8 |
| BYE | 4 (první čtyři seedy) | 0 |
| Kola / nominální hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

19+2+3+4=28; při nulovém SE 21+3+4=28. Dobový přepis ADL24-7 uvádí 19 DA, 3 WC, 4 Q, SE 0, což samo o sobě dává 26; **nejde o kompletní nominální kvótu**. Dobový ATP předpis §7.08/7.10 (ADL24-8) explicitně stanoví 19–21 DA, 0–2 SE a dvě rezervy. Předstartovní los ADL24-9 má pět viditelných Q/SE placeholderů (pozice 3,4,7,12,15); §7.10 D.4 popisuje přesně tento postup pro čtyři Q a jednu dosud nevyřešenou SE možnost. Nevydáváme počet placeholderů za počet plánovaných kvalifikantů. Konečný Main los nemá SE označení. Z této skutečnosti nelze odvodit nulovou plánovanou rezervu.

Q nominálně 14+2=16, 4 sekce po 4, dva seedy na sekci. Oba originální losy ADL24-1/2 vizuálně zkontrolovány. Main: BYE 2,10,23,31; Q 3,12,20,26; WC 13,19,28; LL 4,15,30; všech osm seedů. Q: WC 3,11; Alt 1,7,10,14; 7 viditelných seedů (č.1 Draper přešel do Main, výslovně v zápatí Q); 16 míst a 8 nominálních seedů. Žádný Q BYE. 12+8+4+2+1=27 Main zápasů, 8+4=12 Q zápasů, celkem 39. BYE není hraný zápas. Skuteční 3 LL ani 7 viditelných Q seedů nemění nominální strukturu.

### 5. Dobová pravidla

ATP 2024 §7.03/7.08/7.10/7.12/7.15–16/7.20 (ADL24-8 a BRI24-15): Main vstupní rank, 8 seedů a 4 BYE nejvýše nasazeným; Q 8 seedů ve čtyřech sekcích. Předpis Q/SE při neuzavřeném SE výslovně stanoví společné losování Q/SE zástupných pozic a následné přiřazení SE nebo další přímé akceptace. Nevyužité SE rezervy před zahájením Q obsadí další přímé akceptace, hráč může přejít z Q do Main a být nahrazen alternatem. Po skončení Q los kvalifikantů do dostupných pozic. LL přednost poraženým posledního Q kola, poté dřívější kola, při volných místech na konci Q los skupiny nejvýše postavených (1 místo = 2, více míst = počet+1), poté ranking; nejsou-li volná místa při konci Q, pořadí dle rankingu pro Q seeding. Pravidla náhrad před/po OOP dle §7.20. V případě prohry prvního hraného zápasu po BYE body za první kolo, nikoli běžné R16 body (BRI24-17 / HK24-2). Q body přičítat k Main výsledku podle předpisu; jednotlivé historické LL platby a body zde nepřepisujeme.

### 6. Body a prize money (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 100665 |
| Finalista | 1 | 165 | 58720 |
| SF | 2 | 100 | 34510 |
| QF | 4 | 50 | 19995 |
| R16 | 8 | 25 (0 po BYE při první prohře) | 11610 |
| R32 | 12 | 0 | 7095 |
| Q postupující | 4 | 13 | 0 (výslovně v Q PDF, prize z Main samostatně) |
| Q2 prohra | 4 | 7 | 3550 |
| Q1 prohra | 8 | 0 | 1935 |

Všechny hodnoty přímo v tabulkách zápatí obou originálních ATP losů ADL24-1/2, vizuálně ověřeny. Nominální součet Main 486405 USD, Q 29680 USD = 516085 USD. Total financial commitment 739945 USD je jiná veličina; údaj 922573 z kombinovaného OOP není mužská singlová dotace. Q2 3550/Q1 1935 se shoduje se sekundárně doloženým Hongkongem 2024, ale samo o sobě nedokazuje jeho odměny (jiný ročník/turnaj, nutný vlastní doklad).

### 7. Kontrola a mezery

I/T/H/D/B/P doloženy, E*: mužský Main rank date z dobového přepisu, deadline odvozen, skutečný Q rank date a čas losování nezískány; R*: ročníkový ATP rulebook §7.08/7.10 dostupný v indexovaném textu, screenshot 403. Z*: originální Main/Q ATP PDF vizuálně ověřeny, OOP textově dostupné, vizuální pokusy 403; DS nedostupný, PDF SHA-256 nezískány. Kalendář na `buuk` již správně uvádí Main 8.–13.1., sportovní profil Adelaide 2024 v prověřeném katalogu není. Žádný engine převod. Další Auckland 2024.

### 8. Zdroje (ADL24)

- ADL24-1: [ATP originální Main los](https://www.protennislive.com/posting/2024/8998/mds.pdf), str. 1 vizuálně.
- ADL24-2: [ATP originální Q los](https://www.protennislive.com/posting/2024/8998/qs.pdf), str. 1 vizuálně.
- ADL24-3: [Tennis Australia, Main draw 6.1.2024](https://www.tennis.com.au/fan-zone/news/2024/01/06/aussies-handed-tough-draws-at-adelaide-international-2024), [Q1 7.1.](https://www.tennis.com.au/fan-zone/news/2024/01/07/aussie-contenders-score-big-upsets-at-adelaide-international), [Q2 8.1.](https://www.tennis.com.au/fan-zone/news/2024/01/08/walton-records-back-to-back-top-100-wins-to-qualify-at-adelaide-international).
- ADL24-4: [Sporting News, denní program a výsledky](https://www.sportingnews.com/ca/tennis/news/adelaide-international-results-scores-draw-schedule-2024/eb0bd6623d46dbe562586228), pozor na duplicitní řádek Arnaldi/Zapata v historickém seznamu; počty podle OOP.
- ADL24-5: [OOP 7.1. vydán 6.1. 19:20](https://www.adelaideinternational.com.au/documents/2024-01-06-op/), [revize 22:07](https://www.adelaideinternational.com.au/documents/2024-01-07-op/), text, screenshot 403.
- ADL24-6: [OOP 8.1.](https://www.adelaideinternational.com.au/wp-content/uploads/2024/01/OP-Adelaide-MON-8-JAN-2024.pdf), text, screenshot 403.
- ADL24-7: [dobový přepis acceptance listu, 25.12.2023](https://www.tennisteen.it/entry-list/atp/24098-atp-entry-list-8-14-gennaio-2024.html), nesoučet kvót vysvětlen dobovým předpisem, ne automatické převzetí.
- ADL24-8: [ATP 2024 Competition, verze 21.12.2023](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_21dec.pdf), §7.03, §7.08 c), §7.10 A–D, indexovaný text, screenshot 403.
- ADL24-9: [dobový přepis předstartovního losu s Q/SE](https://www.oasport.it/2024/01/atp-adelaide-2024-il-tabellone-di-arnaldi-e-sonego/), konfrontovat s originálním konečným losem.
- ADL24-10: [OOP 9.1. vydán 8.1. 20:15](https://www.adelaideinternational.com.au/documents/2024-01-08-op-2/), text, screenshot 403.
- ADL24-11: [OOP 10.1.](https://www.adelaideinternational.com.au/wp-content/uploads/2024/01/OP-Adelaide-WED-10-JAN-2024.pdf), text, screenshot 403.
- ADL24-12: [OOP 11.1.](https://www.adelaideinternational.com.au/documents/3462-2/), text, screenshot 403.
- ADL24-13: [OOP 12.1. vydán 11.1. 19:32](https://www.adelaideinternational.com.au/wp-content/uploads/2024/01/OP-3.pdf), text, screenshot 403.
- ADL24-14: [ATP detail sheet 2024](https://www.protennislive.com/posting/2024/8998/ds.pdf), nedostupný, nepovažovat za ověřený.

## Auckland 2024

**Stav:** ROZPRACOVÁNO (8/9). P: Main odměny jednoznačně doloženy; přesná Q odměna v ročníkových zdrojích rozporná. Kandidáta uchovat, necertifikovat jako fakt, dokud není získán lepší doklad. Rešerše 2026-11-27. Žádný převod na engine.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / disciplína | ASB Classic 2024, mužská dvouhra | AKL24-1/2 |
| Kategorie / ATP ID | ATP 250 / 301 | AKL24-1/12 |
| Místo | ASB Tennis Arena, Auckland, Nový Zéland | AKL24-3 |
| Povrch | tvrdý, Greenset, venkovní turnaj | AKL24-1/13 |
| Časové pásmo | Pacific/Auckland, NZDT UTC+13:00 v lednu | lokální datum; identita místa |
| Ředitel / ATP supervisor / rozhodčí | Nicolas Lamperin / Gerry Armstrong / Ricardo Reis | AKL24-4, podpisy OOP |
| Měna | USD | ATP finanční předpis §3.10, AKL24-1/14 |
| Míče, individuální diety | NEOVĚŘENO | doplňková metadata |

Mužský a ženský ASB Classic mají odlišné termíny. WTA losy 1049 neslouží jako doklad mužské kvalifikace ani mužských odměn.

### 2. Přihlášky, plán, losování

| Pole | Údaj | Důkaz / význam |
|---|---|---|
| Main rank date | 2023-12-11 | AKL24-5, dobový přepis acceptance listu |
| Nominální Main entry deadline | 2023-12-11 12:00 US Eastern, tj. 2023-12-12 06:00 NZDT | odvozeno z ATP §7.03 A.1, 28 dnů před pondělím 8.1.; nezískán originální detail sheet |
| Nominální Q entry deadline | 2023-12-18 12:00 US Eastern, tj. 2023-12-19 06:00 NZDT | odvozeno z §7.03 A.2, 21 dnů; mužský Q rank date nezávisle NEOVĚŘEN |
| Q los | před Q1, datum a hodina NEOVĚŘENY | úplný archiv AKL24-6/7 |
| Main los | archivovány dvě verze před/po přiřazení Q, přesný čas losování NEOVĚŘEN | AKL24-1/2 |
| Q | 2024-01-06–07 | AKL24-6/7/8 |
| Main | 2024-01-08–13 | AKL24-1/2/3 |
| Main první den | 2024-01-08 12:00, LL sign-in 11:30 | AKL24-4, OOP vydán 7.1. 15:50 |
| Finále | 2024-01-13, přesný plánovaný čas NEOVĚŘEN | AKL24-1/11 |

Rank date 11.12. a cutoff 66 z prosincového přepisu nejsou automaticky konečný stav; obě předstartovní kopie Main losu uvádějí v zápatí Taro Daniel 75 (cutoff při deadline i v losu). Nezaměňovat historický rank s počtem DA. Časy amerických uzávěrek jsou odvozené, nikoli původní místní přihlašovací termíny z detail sheet.

### 3. Nominální harmonogram

| Kolo | Lokální datum | Nominální zápasy | Evidence |
|---|---|---:|---|
| Q1 | 2024-01-06 | 8 | AKL24-7/8; skutečné výsledky a struktura, původní OOP nezískán |
| Q2 | 2024-01-07 | 4 | AKL24-7/8; skutečné výsledky, původní OOP nezískán |
| R32 | 2024-01-08–09 | 12 | AKL24-4/9; 8 na první den, 4 na druhý odvozeno z úplného losu a potvrzeno denními notes |
| R16 | 2024-01-10 | 8 | AKL24-9 |
| QF | 2024-01-11 | 4 | AKL24-9/10 |
| SF | 2024-01-12 | 2 | AKL24-10 |
| F | 2024-01-13 | 1 | AKL24-11 |

Q 2 kalendářní dny, Main 6 dnů, celkem 8 dnů bez překryvu; 12+27=39 nominálně hraných zápasů. Dobový ATP OOP 8.1. (vydán 7.1. 15:50) uvádí čtyři mužské singly na Centre Court a čtyři na Grandstand. Čtyřhra se nepočítá. Všechny 4 Q vítěze již přiřazeny. ATP Media Notes 9.1. označují zbylé zápasy jako R32, 10.1. R16, 11.1. QF. Jeden QF walkover 11.1. je skutečná odchylka, nikoli změna plánovaného počtu 4 QF. Q dny jsou doloženy retrospektivním denním výsledkovým archivem, ne nově získaným předturnajovým OOP; H* označuje tento rozdíl.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Cíloví účastníci | 28 | 16 |
| Základní DA | 19 | 14 |
| SE rezervy podle dobového standardu | 2, nevyužité uvolněny pro DA | nevztahuje se |
| DA při nulovém SE | 21 | 14 |
| WC | 3 | 2 |
| Q postupy | 4 | 4 vítězové sekcí |
| Nasazení | 8 | 8 |
| BYE | 4, nejvýše nasazení | 0 |
| Kola / nominální hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 | BO3 |

Main: 19+2+3+4=28, 21+3+4=28 po uvolnění rezerv. Dobový přepis AKL24-5 uvádí 19 DA, 3 WC, 4 Q, SE 0; aritmeticky není úplný, proto se rezervy dle ročníkového standardu evidují odděleně (ADL24-8, dřívější kontrola §7.08/7.10). Výslovná turnajová výjimka SE nebyla nalezena. Q 14+2=16, 4 sekce po 4, dva nominální seedy na sekci. Obě Main kopie vizuálně: BYE 2,10,23,31; WC 7,15,18; Q placeholders/později Q 11,19,28,30; osm seedů, žádné označené LL/SE v těchto předstartovních verzích. Tyto dvě kopie nejsou konečný výsledkový los. Q úplný archiv AKL24-6/7: 16 hráčů, 2 WC, 5 alternates, 1 PR a 5 viditelných seedů (#3,5,6,7,8). Původní seznam #1,2 přešli do Main a #4 odstoupil (AKL24-7, sekundární); neměnit nominálních 8. BO3 v obou fázích potvrzeno úplnými výsledky. Q 8+4=12; Main 12+8+4+2+1=27. BYE není hraný zápas.

### 5. Pravidla

Dobový ATP rulebook 2024 §7.03/7.08/7.10/7.12/7.15–16/7.20 (viz ADL24-8 a BRI24-15): Main top 4 BYE, 8 seedů, Q 8 seedů a 4 sekce; kvalifikanti přiřazováni do volných Main pozic po skončení Q, což ročník přímo dokládá dvojicí před/po kopií Main losu. SE pravidla dle ročníkového standardu, nevyužité místo se vrací DA. ATP LL pravidla, pořadí a případné losování podle §7.20 (odlišné od Grand Slam). Přesný LL sign-in pro první den je v originálním OOP 11:30. Bodování po BYE: prohra prvního skutečně hraného zápasu R16 = 0, přímo ATP Media Notes (AKL24-3). Prize money se od bodování liší: dobový ATP §3.08 C.4 (AKL24-14, tištěná str. 47) uvádí, že běžný hráč s BYE a prohrou R16 má odměnu druhého kola; speciální případy náhrad a withdrawal compensation mají odlišná pravidla. Neodvozovat odměnu z počtu přiznaných bodů. Q body přičítány k Main; 13/7/0 dle BRI24-17, též AKL24-6.

### 6. Body a odměny (USD)

| Výsledek | Příjemci | ATP body | USD | Stav |
|---|---:|---:|---:|---|
| Vítěz | 1 | 250 | 100640 | primární |
| Finalista | 1 | 165 | 58705 | primární |
| SF | 2 | 100 | 34510 | primární |
| QF | 4 | 50 | 19995 | primární |
| R16 | 8 | 25 (0 při první prohře po BYE) | 11610 | primární |
| R32 | 12 | 0 | 7095 | primární |
| Q postupující | 4 | 13 | 0 samostatně (sekundární) | kandidát |
| Q2 prohra | 4 | 7 | 3550 | kandidát, neověřeno primárně |
| Q1 prohra | 8 | 0 | 1935 | kandidát, neověřeno primárně |

Main šest hodnot a body shodně v obou vizuálně zkontrolovaných kopiích originálního ATP Main losu (AKL24-1/2), dobové ATP Preview (AKL24-3, text) a TennisExplorer (AKL24-15). Main nominální součet 486365 USD. Q částky 3550/1935 uvádí TennisTemple AKL24-6; další tabulky se rozcházejí: německý přehled AKL24-16 uvádí 3650/2050, ale i Main částky 100000/57845/34000/20000/11600/7200, v přímém rozporu s primárními doklady. CanalTenis AKL24-17 uvádí 3600/2000 a Main částky odpovídající Brisbane 2024, nikoli Aucklandu. Oba jsou pro Main prokazatelně chybné; to však samo o sobě nedokazuje přesnou Q odměnu. Kandidát Q 29680 USD, hypotetický součet Main+Q 516045 USD; alternativní Q součty 31000 nebo 30400 USD. Dokud není přímý Q PDF nebo jiná spolehlivá ročníková tabulka získána, P zůstává otevřeno. Celková mužská dotace 661585 USD podle AKL24-18 a total financial commitment 739945 USD z Main losu jsou odlišné veličiny a neslouží k dopočtení Q bez doložení všech položek. Stejné odměny jiného turnaje (Adelaide) nejsou důkaz Aucklandu.

### 7. Evidence / další krok

I/T/D/B pokryty, H*: Q data rekonstruována z denních výsledků, Main plán doložen ATP OOP a notes; E*: deadline odvozeny, losovací časy a Q rank date neznámé; R*: společný dobový předpis a konkrétní Main BYE poznámka, ATP PDF screenshoty 403; Z*: dvě originální Main kopie vizuálně, Q los pouze nezávislé archivy, ATP originální Main/Q/DS URL nedostupné. P je otevřeno; neoznačovat za hotový profil ani za definitivní odměny. Doplnit přímé kvalifikační PDF, ročníkovou tabulku nebo spolehlivý finanční předpis s konkrétním rozpisem; potom znovu posoudit. Katalog `buuk` již uvádí Main 8.–13.1., v prověřeném sportovním katalogu není Auckland 2024. Žádný engine převod. Po opakované rešerši P zůstává otevřeno, viz doplňkový audit AKL24-19–24; Montpellier zpracován samostatně, žádná změna stavu Aucklandu.

### 8. Zdroje (AKL24)

- AKL24-1: [archivovaná ATP Main kopie před přiřazením Q](https://www.raquetc.com/wp-content/uploads/2024/01/mds-4.pdf), str. 1 vizuálně ověřena.
- AKL24-2: [archivovaná ATP Main kopie po přiřazení Q](https://www.raquetc.com/wp-content/uploads/2024/01/mds-6.pdf), str. 1 vizuálně ověřena.
- AKL24-3: [ATP Media Notes preview a Day 1](https://www.atptour.com/-/media/5f690343219a4f2badc7861097ef19e3.pdf), textová tabulka a BYE poznámka, pokus o screenshot str. 2 skončil 403.
- AKL24-4: [originální OOP 8.1. kopie Britwatchsports](https://britwatchsports.com/wp-content/uploads/2021/11/ATP-Auckland-OOP-20240107.pdf), text včetně osmi dvojic a zápatí; screenshot 403.
- AKL24-5: [dobový přepis acceptance listu](https://www.tennisteen.it/entry-list/atp/24098-atp-entry-list-8-14-gennaio-2024.html).
- AKL24-6: [TennisTemple úplný Q pavouk](https://en.tennistemple.com/competitions/auckland/2024/draw-qualifications), zdroj kandidátních Q odměn.
- AKL24-7: [historický Q archiv](https://de.wikipedia.org/wiki/ASB_Classic_2024/Herren/Qualifikation), [TennisExplorer Q](https://www.tennisexplorer.com/auckland/2024/atp-men/?phase=qualification); druhý zdroj zobrazuje Main odměny i na Q stránce, nepoužívat jako potvrzení Q peněz.
- AKL24-8: [Sky Sports 6.1.](https://www.skysports.com/tennis/scores-schedule/06-01-2024), [7.1.](https://www.skysports.com/tennis/scores-schedule/07-01-2024), [dobový Q2 výsledek 7.1.](https://tennistonic.com/stat-tournaments/atp/19354/92985-92056/jack-loutit-vs-alex-michelsen/).
- AKL24-9: ATP Media Notes [9.1.](https://www.atptour.com/-/media/e2e02b2a95954c1a8b246707af0b0d5a.pdf), [10.1.](https://www.atptour.com/-/media/340de989774544309b58475320aebfa6.pdf), [11.1.](https://www.atptour.com/-/media/0d7a39ad3e1b4b93882f23c7468ae180.pdf), text, pokusy screenshotů 403; [ATP R16 zpráva 10.1.](https://www.atptour.com/en/news/shelton-marozsan-auckland-2024-wednesday).
- AKL24-10: [AP QF 11.1.](https://www.tennis.com/news/articles/cameron-norrie-withdraws-from-auckland-classic-with-wrist-injury-shelton-through-to-semifinals), [AP SF 12.1.](https://www.tennis.com/news/articles/taro-daniel-alejandro-tabilo-upset-shelton-fils-reach-auckland-final-asb-classic).
- AKL24-11: [historický výsledkový přehled Main](https://en.wikipedia.org/wiki/2024_ASB_Classic_%E2%80%93_Men%27s_singles), [TennisExplorer Main](https://www.tennisexplorer.com/auckland/2024/atp-men/).
- AKL24-12: [ATP identita v TennisAbstract, ID 0301](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024-0301%2FAuckland), [ATP originální Main](https://www.protennislive.com/posting/2024/301/mds.pdf), [Q](https://www.protennislive.com/posting/2024/301/qs.pdf), [DS](https://www.protennislive.com/posting/2024/301/ds.pdf), všechny tři originální URL nedostupné při této rešerši.
- AKL24-13: [dobový přehled entry listu a venkovního povrchu](https://news.sportface.it/ultimi-articoli/entry-list-atp-auckland-2024-partecipanti-ed-italiani-presenti/2392923).
- AKL24-14: [ATP 2024 Financial, 5.1.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-3_financial_05jan.pdf), text §3.08/3.09/3.10, vizuální pokus 403.
- AKL24-15: [TennisExplorer Main odměny](https://www.tennisexplorer.com/auckland/2024/atp-men/).
- AKL24-16: [německá tabulka s konfliktem](https://de.wikipedia.org/wiki/ASB_Classic_2024/Herren), nepoužívat místo primární Main tabulky.
- AKL24-17: [CanalTenis historická tabulka s konfliktem](https://canaltenis.com/el-prize-money-del-atp-auckland/), odstavec 2024.
- AKL24-18: [TennisCompanion celková dotace](https://tenniscompanion.org/prize-money/auckland/), historický součet 2024; dostupná tabulka po kolech v této verzi neslouží jako mužský důkaz Q odměn.


### 9. Auckland – doplňkový audit otevřené položky P (2026-11-27)

Třetí kopie originálního ATP Main losu (AKL24-19, vizuálně str. 1) a dobový článek AKL24-20 nezávisle potvrzují všech šest Main částek, žádný Q rozpis. Dobový rozpis AKL24-21 potvrzuje Q/Main hranici a Main odměny; jeho sekundární tabulka čtyřhry dává 129 000 USD (1×35 000 + 1×18 800 + 2×11 000 + 4×6 100 + 8×3 600). Rozdíl 661 585 − 486 365 − 129 000 = 46 220 USD není doložená Q dotace: chybí primární rozpis všech složek. ATP Rulebook 10.7.2024, Exhibit J, odkazuje na schválenou distribuci v turnajovém Detail Sheet (AKL24-22), nikoli univerzální výpočet ze zveřejněné celkové dotace. Ani stejný financial commitment jako u Adelaide není důkaz stejného Q prize money. AKL24-23 potvrzuje data kvalifikačních kol, nikoli peníze. Další databáze a varianty ATP cest neodblokovaly Q tabulku (AKL24-24). Kandidát 3550/1935 USD se nemění; P zůstává otevřeno, bez povýšení stavu. Při novém dokladu nejprve porovnat přesný ročník, měnu, druh soutěže a kompletní tabulku.
- AKL24-19: [třetí archivovaná ATP Main kopie](https://www.fantatennis.net/_downloads/e0f41f3209d87bb2a703d4d51a25b5d8), str. 1 vizuálně.
- AKL24-20: [dobový Tennis Infinity, 7.1.2024](https://tennis-infinity.com/atp/2024-asb-classic-auckland-atp-prize-money-points-overview).
- AKL24-21: [dobový Sportskeeda program a Main/čtyřhra](https://hindi3.sportskeeda.com/tennis/news-auckland-2024-men-s-draw-schedule-players-prize-money-breakdown-ranking-points-asb-classic), bez Q částek.
- AKL24-22: [ATP Rulebook 2024, 10.7.](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_10jul.pdf), Exhibit J, tištěná str. 326, indexovaný text, pokus o screenshot 403; pozdější verze se zde používá pouze jako vysvětlení, proč nedopočítávat neověřený rozpis.
- AKL24-23: [MyKhel mužský denní archiv](https://www.mykhel.com/tennis/asb-classic-2024-mens-singles-scores-c10460/), potvrzení 8 Q1 a 4 Q2; zobrazené časy nejsou místní.
- AKL24-24: původní /2024/301/qs.pdf, /2024/0301/qs.pdf, /2024/301/ds.pdf a /2024/301/mdd.pdf opakovaně nedostupné; zkoušeny též Matchstat a Stevegtennis (bez použitelného Q rozpisu). TennisCompanion aktuálně nezávisle nepotvrzuje mužskou Q tabulku, záměna s ženskými hodnotami možná.

## Montpellier 2024

**Stav:** HOTOVO v nominálním rozsahu 9/9 s omezeními E/R/P/Z. Rešerše 2026-11-27. Oproti předchozím ATP 250 doložena rezervace Late Entry. Bez převodu na engine.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / kategorie | Open Sud de France 2024, ATP 250, mužská dvouhra | MPL24-1/2 |
| ATP ID | 375 | MPL24-2/11 |
| Dějiště | Sud de France Arena, Pérols, Montpellier, Francie | MPL24-1/3/10 |
| Povrch | tvrdý, krytý | MPL24-2/3 |
| Časové pásmo | Europe/Paris, CET UTC+01:00 v celém okně | lokalita, datum |
| Měna | EUR | MPL24-1, primární tabulka výslovně € |
| Míče / diety / přesný model povrchu | NEOVĚŘENO | doplňková metadata |

### 2. Přihlášky, plán a losování

| Pole | Údaj | Důkaz / význam |
|---|---|---|
| Main rank date | 2024-01-01 | MPL24-6, dobový přepis entry listu |
| Q rank date | 2024-01-08 | MPL24-6 |
| Nominální Main deadline | 2024-01-01 12:00 US Eastern = 18:00 CET | §7.03, 28 dní před 29.1., odvozeno |
| Nominální Q deadline | 2024-01-08 12:00 US Eastern = 18:00 CET | §7.03, 21 dní před 29.1., odvozeno |
| Nominální LE deadline | 2024-01-25 10:00 US Eastern = 16:00 CET | §7.04, čtvrtek před 29.1., odvozeno |
| Q los | před 28.1., přesný čas NEOVĚŘEN | MPL24-8 |
| Main los | zveřejněn nejpozději 27.1.; přesný okamžik NEOVĚŘEN | MPL24-9 |
| Q | 2024-01-28–29 | MPL24-4/8 |
| Main | 2024-01-29–02-04 | MPL24-1/2/4 |
| Finále | 2024-02-04, plán 15:00 CET | MPL24-4; čtyřhra 12:30 odděleně |

Přihlašovací listiny uvádějí historické rank cutoffs; nejsou pevnou vstupní hranicí pro jiný ročník. Uzávěrky jsou nominálně odvozeny, originální Detail Sheet se nepodařilo získat.

### 3. Nominální harmonogram

| Kolo | Lokální datum | Nominální zápasy | Důkaz |
|---|---|---:|---|
| Q1 | 2024-01-28 | 8 | MPL24-4/8, plán dne od 10:30 |
| Q2 | 2024-01-29 | 4 | MPL24-4/8, program dne od 12:00 |
| R32 | 2024-01-29–31 | 12 | MPL24-4 |
| R16 | 2024-01-31–02-01 | 8 | MPL24-4 |
| QF | 2024-02-02 | 4 | MPL24-4 |
| SF | 2024-02-03 | 2 | MPL24-4 |
| F | 2024-02-04 | 1 | MPL24-4 |

Dobový program zveřejněný 23.1. před turnajem výslovně rozlišuje kola a plánované denní časy. Q 2 dny, Main 7 dní, celé okno 8 dní; Q2/R32 překryv 29.1., R32/R16 překryv 31.1. Přesné počty jednotlivých vícedenních Main kol v každém dni nepublikované, neodhadovat rovnoměrně. Q 12 a Main 27 nominálně hraných zápasů, celkem 39. Čas začátku celého denního programu neznamená začátek každé mužské singlové dvojice.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Účastníci | 28 | 16 |
| Základní DA | 18 | 14 |
| SE rezervy | 2 | nevztahuje se |
| LE rezerva | 1 | nevztahuje se |
| DA při nulovém SE/LE | 21 | 14 |
| WC | 3 | 2 |
| Q postupy | 4 | 4 vítězové sekcí |
| Nasazení | 8 | 8 |
| BYE | 4 (první 4 seedy) | 0 |
| Kola / nominální hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 | BO3 |

18+2+1+3+4=28; při nevyužití rezerv 21+3+4=28; Q 14+2=16, čtyři sekce po čtyřech. Přihlašovací listina zveřejněná 4.1. explicitně eviduje 18 DA a placeholdery 3 WC, 2 SE, 1 LE, 4 Q (MPL24-5). Aktualizovaná listina 11.1. uvádí 18 DA, 1 LE, 3 WC, 4 Q, SE 0; nevyužité rezervy nejsou nulová nominální kapacita (MPL24-6). Úplné sekundární pavouky potvrzují 4 BYE, 8 Main seedů, 4 Q, 16 Q hráčů, 2 Q WC, jeden alternate a 7 viditelných Q seedů (chybí #2); nominální Q seeding zůstává 8. ATP Media Notes uvádí WC Holger Rune, Harold Mayot a Lucas Pouille; některý sekundární pavouk WC u Rune neznačí, nemění to nominální kvótu. Výsledkový BO3 formát potvrzen v obou fázích. Nepřepisujeme historické nahrazení do plánu.

### 5. Dobová pravidla

ATP Rulebook verze 22.1.2024 §7.04, §7.08 B.1.c (MPL24-7): jedno LE místo v ATP 250, způsobilost hráče podle rankingu použitého pro původní vstup (28 dní před turnajem) a nad původním cut-off; LE do čtvrtka 10:00 US Eastern, nevyužité místo vráceno entry listu. Dvě SE rezervy; nevyužité SE se uvolní do DA. Pravidla přihlašování, nasazení, Q/SE placeholderů, náhradníků a LL viz ADL24-8, BRI24-15 a odpovídající verze §7.10/7.20. 4 top seedy BYE, 8 Q seedů, čtyři kvalifikační sekce, vítězové Q přiřazeni do volných Main míst po Q. Specifický NextGen slot pro týdny se třemi ATP turnaji nepřenášet na Montpellier (v tomto týdnu jediný běžný ATP Tour turnaj podle MPL24-2). BYE a prohra prvního skutečně hraného kola = 0 bodů, explicitně ATP Media Notes MPL24-1; odměna přitom odpovídá dosaženému kolu podle finančních pravidel. Q body přičíst podle ATP pravidel; žádné převody na squash.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR | Doklad |
|---|---:|---:|---:|---|
| Vítěz | 1 | 250 | 88125 | ATP |
| Finalista | 1 | 165 | 51400 | ATP |
| SF | 2 | 100 | 30220 | ATP |
| QF | 4 | 50 | 17510 | ATP |
| R16 | 8 | 25 (0 po BYE při první prohře) | 10165 | ATP |
| R32 | 12 | 0 | 6215 | ATP |
| Q postupující | 4 | 13 | bez samostatné Q odměny, Main samostatně | ročníkový standard |
| Q2 prohra | 4 | 7 | 3105 | sekundární shoda |
| Q1 prohra | 8 | 0 | 1695 | sekundární shoda |

Main body, částky a výjimka po BYE v originálním ATP Preview & Day 1 (MPL24-1, indexovaný text, screenshot 403). Dobový MPL24-12 shodný Main rozpis. Q body z dobového ATP rulebooku (BRI24-17); Q částky shodně TennisCompanion EUR historický řádek 2024, německý ročníkový přehled a TennisTemple Q (MPL24-8/10/13). Není prokázána úplná vzájemná nezávislost sekundárních zdrojů. TennisTemple označuje částky jako $, Stevegtennis používá A$ i záporný sentinel; originální ATP výslovně EUR a dvě sekundární tabulky v EUR potvrzují správnou měnu. Nezaměňovat měnu převodů s původní denominací. Originální Q PDF nebyl získán, P* nikoli primární ověření. Main nominální součet 425905 EUR, Q 25980 EUR, dohromady 451885 EUR. Celková dotace se v sekundárních zdrojích liší (579320 vs 564835 EUR); nevyvozovat z ní singlovou tabulku ani skutečné individuální platby. Total financial commitment je jiná veličina.

### 7. Kontrola a omezení

I/T/H/D/B doloženy dobovým ATP, předem zveřejněným rozpisem a úplnými archivy; E*: rank dates/listiny doloženy, nominální deadlines odvozeny, přesné časy losů a DS chybí; R*: dobový rulebook textově, screenshot 403, LE potvrzen konkrétní listinou; P*: Main primární text, Q sekundární shoda tří zdrojů, při získání originálního Q PDF znovu ověřit; Z*: původní Main/Q PDF přímé odkazy nefungují, žádný hash nezískán. V katalogu `buuk` je Main 29.1.–4.2.2024, v prověřených sportovních profilech tento ročník není. Další Córdoba 2024; u následujícího týdne pracovní katalog uvádí položku Lyon s datem Marseille, ověřit správnou identitu proti původnímu ATP kalendáři, neprovádět zde zásah do enginu.

### 8. Zdroje (MPL24)

- MPL24-1: [ATP Preview & Day 1, 29.1.2024](https://www.atptour.com/-/media/a6fa4add53c54a5182670d5e0f6c230f.pdf), tabulka Main body/EUR a BYE poznámka, indexovaný text; screenshot 403. [Day 2, 30.1.](https://www.atptour.com/-/media/bcd637ed58c04b75a820c14443a57b45.pdf), text, screenshot 403.
- MPL24-2: [oficiální ATP kalendář 2024](https://www.atptour.com/-/media/files/final-2024-atp-calendar.pdf), text; screenshot neproveditelný kvůli chybě vykreslení.
- MPL24-3: [Tennis Europe kalendář ročníku](https://www.tenniseurope.org/calendarevent/73310/Open-Sud-De-France), kategorie, indoor hard, Main data.
- MPL24-4: [dobový program publikovaný 23.1.](https://www.leguidemontpellier.fr/tennis-programme-open-sud-de-france-montpellier/4792/), plán před zahájením.
- MPL24-5: [entry list zveřejněná 4.1.2024](https://tennisuptodate.com/atp/entry-list-2024-open-sud-de-france-montpellier-headlined-by-musetti-auger-aliassime-and-murray), explicitně LE a 2 SE.
- MPL24-6: [dobový přepis Main/Q listin 11.1.](https://www.tennisteen.it/entry-list/atp/24106-atp-entry-list-29-gennaio-4-febbraio-2024.html).
- MPL24-7: [ATP Rulebook 22.1.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_22jan.pdf), §7.04, §7.08 B.1.c, text; pokus screenshotu 403.
- MPL24-8: [TennisTemple Q](https://en.tennistemple.com/competitions/montpellier-2024/12268/draw-qualifications), [Main](https://en.tennistemple.com/competitions/montpellier-2024/12268/draw); úplné sekundární pavouky, peněžní měna chybně označena.
- MPL24-9: [dobová zpráva o losu 27.1.](https://tennisuptodate.com/atp/draw-2024-open-sud-de-france-montpellier-featuring-holger-rune-alexander-bublik-andy-murray-and-felix-auger-aliassime).
- MPL24-10: [ročníkový přehled](https://de.wikipedia.org/wiki/Open_Sud_de_France_2024), sekundární Main/Q rozpis v EUR.
- MPL24-11: [ATP původní Main](https://www.protennislive.com/posting/2024/375/mds.pdf), [Q](https://www.protennislive.com/posting/2024/375/qs.pdf); nedostupné, nepovažovat za vizuálně ověřené.
- MPL24-12: [dobový Tennis Infinity prize/points](https://tennis-infinity.com/atp/2024-montpellier-open-atp-prize-money-points-overview).
- MPL24-13: [TennisCompanion historická tabulka v EUR](https://tenniscompanion.org/prize-money/montpellier/), řádek 2024 Main a Q; odlišné celkové prize money nepoužívat jako autoritu.
- MPL24-14: [Stevegtennis Main/Q archiv](https://www.stevegtennis.com/draw-results/atp/Open%20Sud%20de%20France%20-%20Montpellier/2024), potvrzuje sportovní strukturu, nikoli měnu či záporné sentinel hodnoty.


## Córdoba 2024

**Stav:** HOTOVO v nominálním rozsahu I/T/H/E/D/R/B/P/Z, s vyznačenými omezeními H/E/R/Z. Rešerše 2026-11-27. Primární ročníkové Main i Q finanční tabulky doloženy textem původních ATP losů zveřejněných pořadatelem; předstartovní Main kopie vizuálně. Pouze reálný tenis.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / disciplína | Córdoba Open 2024, mužská dvouhra | COR24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 9158 | COR24-2/4 |
| Areál | Polo Deportivo Kempes, Córdoba, Argentina | COR24-3/5 |
| Povrch | venkovní červená antuka | COR24-1/2/3 |
| Časové pásmo | America/Argentina/Cordoba, ART UTC−03:00 | lokalita, místní civilní datum |
| Organizace | Torneos a Octagon s vládou provincie Córdoba | COR24-3 |
| ATP supervisor | Carlos Sanches | COR24-1/2/6 |
| Měna | USD; nikoli ARS, měna vstupenek není měna prize money | COR24-1/2/7 |
| Míče, rozhodčí, individuální diety | NEOVĚŘENO | doplňkové údaje |

### 2. Přihlášky a termíny

| Pole | Hodnota | Důkaz / význam |
|---|---|---|
| Main rank date | 2024-01-08 | dobový přepis acceptance listu 20.1. COR24-8 |
| Q rank date dle přepisu | 2024-01-08 | COR24-8; rozpor s obecným pravidlem cca 21 dní před pondělím (15.1.); neměnit záznam zdroje na odvozený údaj |
| Nominální Main deadline | 2024-01-08 12:00 US Eastern = 14:00 ART | odvozeno z §7.03, 28 dní před 5.2. |
| Nominální Q deadline | 2024-01-15 12:00 US Eastern = 14:00 ART | odvozeno z §7.03, 21 dní před 5.2.; skutečný ročníkový deadline neověřen |
| Nominální LE deadline | 2024-02-01 10:00 US Eastern = 12:00 ART | §7.04, odvozeno |
| Q los | zveřejněn nejpozději 2024-02-03 | COR24-9; přesný čas neověřen |
| Main los | 2024-02-03, sobota | výslovně pořadatel COR24-3, hodina nepublikována |
| Q | 2024-02-03–04 | COR24-3/5/10 |
| Main | 2024-02-05–11 | COR24-1/2/3/4 |
| Finále singlu | 2024-02-11 19:00 ART | pořadatel COR24-5; čtyřhra 16:00 odděleně |

Detail Sheet nezískán. Původní Main cutoff 93 a Q 180 z COR24-8 jsou historické ranky, nikoli kvóty; konečný los uvádí Main 111 a Q 253, odlišné okamžiky a záznamy. Nepřebírat z přepisu Q rank date jako potvrzenou uzávěrku. Turnajové datum 5.–11.2. v záhlaví Q losu není datum samotné Q; kvalifikace 3.–4.2. přímo podle pořadatele.

### 3. Nominální harmonogram

| Kolo | Lokální datum / okno | Nominální zápasy | Důkaz |
|---|---|---:|---|
| Q1 | 2024-02-03 | 8 | COR24-5/9, plán od 11:00 |
| Q2 | 2024-02-04 | 4 | COR24-5/10, plán od 14:00 |
| R32 | 2024-02-05–06 (konkrétní mužský program); veřejný plán označuje R1 i 7.2. | 12 | COR24-7/11/12/13 |
| R16 | 2024-02-07–08 | 8 | COR24-12/13/14 |
| QF | 2024-02-09 | 4 | COR24-5 |
| SF | 2024-02-10 | 2 | COR24-5, od 15:30; poslední SF ne před 18:00 |
| F | 2024-02-11 | 1 | COR24-5, 19:00 |

Q 2 dny, Main 7 dní, celé okno 9 dní bez překryvu fází. Pozor na dvojí úroveň programu: veřejný harmonogram pořadatele COR24-5 uvádí obecně první kolo 5.–7.2. a osmifinále 8.2.; konkrétní denní ATP notes 5./6.2. jsou R32, notes vydané pro 7.2. výslovně označují čtyři mužské singlové dvojice jako R16. Pořadatel 8.2. potvrzuje zahájení R16 ve středu 7.2. a současně první kolo čtyřhry. Proto zachováváme obě zdrojové vrstvy: obecný předturnajový plán a upřesněné mužské okno dle denního programu. Nominálně R16 čtyři zápasy 7.2. a čtyři 8.2., nikoli 7.–9.2. (déšť). ATP 8./9.2. potvrzuje odložení tří zbývajících R16 na 9.2.; jeden R16 se 8.2. dohrál. Tato mimořádnost nemění plán QF 9.2. Denní počet R32 5./6.2. se neodhaduje. H* kvůli rozdílu veřejné a specifické vrstvy, nikoli chybějící fázi.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Účastníci | 28 | 16 |
| Základní přímé akceptace | 18 | 14 |
| SE rezervy | 2 | nevztahuje se |
| LE rezerva | 1 | nevztahuje se |
| DA při nulovém SE/LE | 21 | 14 |
| WC | 3 | 2 |
| Q postupy | 4 | 4 vítězové sekcí |
| Nasazení | 8 | 8 |
| BYE | 4 (top 4) | 0 |
| Kola / nominální hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 | BO3 |

18+2+1+3+4=28; 14+2=16. Dobový přepis COR24-8 uvádí 18 DA, 3 WC, 4 Q, SE/LE nula; součet je neúplný bez uvolnitelných rezerv. Ročníkový standard §7.04/7.08 (MPL24-7) vysvětluje 2 SE a 1 LE. Předstartovní Main los (COR24-6, vizuálně) má 32 pozic, BYE 2/10/23/31, Q placeholders 5/19/21/28, WC 6/7/26, všech 8 seedů. Q originální textový los (COR24-1) má 16 účastníků, všechny 8 seedů, WC 2 a 14, Alt 10 a 11, PR 15; čtyři sekce po čtyřech, bez BYE. Konečný Main textový los označuje LL na místě původního seedu č. 6, který odstoupil; neznamená to plánovaný devátý typ vstupu ani změnu nominálních 8 seedů. Extrakce konečného Main pavouka vykazuje místy posunuté štítky/jména a výsledkové cesty, proto pro geometrii a nominální kvóty má přednost vizuálně zkontrolovaný předstartovní los a přímá zpráva pořadatele. Nepřepisujeme výsledky z vadného textového výtahu. BO3 potvrzují Q výsledky a nezávislý singlový archiv. 12+8+4+2+1=27 Main, Q 8+4=12; celkem 39 zápasů.

### 5. Dobová pravidla

ATP §7.03/7.04/7.08/7.10/7.12/7.15–16/7.20, lednová verze 2024 (MPL24-7, COR24-15): 8 Main seedů, 4 BYE pro top 4, 8 Q seedů, 4 sekce. LE pozice pro způsobilého hráče nad původním cut-off, nevyužité místo vráceno entry listu; nevyužité SE rezervy doplněny DA. Q vítězové losem do volných Main míst, LL postup podle ATP §7.20, nikoli Grand Slam. BO3 v obou fázích. Prohra prvního hraného zápasu po BYE = nula bodů (COR24-7, výslovná poznámka), odměna za dosažené kolo podle finančního předpisu. Body Q přičteny k Main dle dobového předpisu. Nový kontext: v týdnu 5.2. jsou tři ATP Tour turnaje Córdoba, Dallas a Marseille (COR24-8/16). ATP oznámení z 20.12.2023 a ročníkový §7.04 zavádějí Next Gen příležitosti pro způsobilé U20 v top 250 v takových týdnech (COR24-17): jedna Main a dvě Q příležitosti, nevyužité rezervy uvolněné dalším hráčům. Konkrétní distribuce/využití mezi turnaji tohoto týdne není z dostupných ročníkových listin doložena; evidovat jako programové pravidlo týdne, **ne přidat automaticky jedno Main a dvě Q místa každému turnaji navíc**. Nominální kapacita 28/16 zůstává pevná. Přesné přiřazení těchto rezerv k jednotlivým akcím otevřeno pro společný audit týdne.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 85535 |
| Finalista | 1 | 165 | 49900 |
| SF | 2 | 100 | 29335 |
| QF | 4 | 50 | 16995 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 9870 |
| R32 | 12 | 0 | 6030 |
| Q postupující | 4 | 13 | 0 (výslovně v Q tabulce) |
| Q2 prohra | 4 | 7 | 3015 |
| Q1 prohra | 8 | 0 | 1645 |

Main všech šest částek a body přímo ATP předstartovní los COR24-6 (vizuálně), originální konečný los COR24-2 (text) a ATP Media Notes COR24-7 (text). Q všechny tři hodnoty a body přímo originální ATP Q los na webu pořadatele COR24-1 (text; screenshot timeout), nezávislá sekundární tabulka COR24-18 potvrzuje částky. Stevegtennis nesprávně označuje měnu A$, originální dokument a ATP poznámka USD mají přednost. Nominální Main 413405 USD, Q 25220 USD, celkem 438625 USD. Záhlaví originálních losů uvádí total financial commitment 640705 USD; některé sekundární přehledy nesprávně nazývají tento údaj prize money nebo uvádějí jiný součet. Nezaměňovat s nominálním součtem singlových odměn.

### 7. Kontrola a mezery

I/T/D/B/P doloženy, H* obecný veřejný plán vs konkrétní mužské OOP/notes a dešťové odklady odděleny; E* přepis Q rank date v rozporu s očekávaným datem, deadline pouze odvozen, Q/LE/SE skutečné administrativní časové záznamy a DS chybí; R* dobová pravidla textově a týdenní Next Gen pravidlo doloženo, konkrétní rezervace mezi třemi akcemi otevřena; Z* původní Main/Q los pořadatele textově, screenshoty timeout, předstartovní Main kopie vizuálně, ATP Media Notes textově, screenshoty 403. Žádné SHA-256 originálních PDF nezískány. Žádný runtime převod. Další Dallas 2024 a následně Marseille 2024; společně ověřit týdenní Next Gen rozdělení.

### 8. Zdroje (COR24)

- COR24-1: [pořadatel, originální ATP Q los](https://www.cordobaopen.com/media/d/91/2b/912b749624c08459144dbca08e4263a8658f7bfe.pdf), text zápatí a všech 16 míst; screenshot timeout.
- COR24-2: [pořadatel, originální ATP konečný Main los](https://www.cordobaopen.com/media/d/da/49/da49108eac6b3776beb8191cfddeab0cacd9ca78.pdf), text zápatí, pozor na nekonzistentní extrakci výsledkových cest; screenshot timeout.
- COR24-3: [pořadatel, Main los 3.2.](https://www.cordobaopen.com/articulo/1051/32835/cachin-y-ramos-viniolas-se-enfrentaran-en-la-primera-ronda-del-cordoba-open), datum losu, Q fáze, všechny nominální pozice a organizace.
- COR24-4: [ATP ročník 9158](https://www.atptour.com/es/tournaments/cordoba/9158/overview).
- COR24-5: [pořadatel, Horarios 2024](https://www.cordobaopen.com/horarios), úplný indexovaný text veřejného programu, přímý přístup 502.
- COR24-6: [archiv předstartovního ATP Main losu](https://www.fantatennis.net/_downloads/087503cf1f010607413b89db9befce60), str. 1 vizuálně zkontrolována.
- COR24-7: [ATP Preview & Day 1 5.2.](https://www.atptour.com/-/media/59fd914f0b9c4f049bbebe248ccf09d6.pdf), text tabulky bodů/odměn a BYE poznámky; screenshot 403.
- COR24-8: [dobový přepis acceptance listů 20.1.](https://www.tennisteen.it/entry-list/atp/24110-atp-entry-list-5-11-febbraio-2024.html), odděleně Córdoba Main/Q.
- COR24-9: [pořadatel, Q los 3.2.](https://www.cordobaopen.com/articulo/1051/32834/bagnis-%E2%80%93-rodriguez-taverna-partido-destacado-en-la-primera-ronda-de-la-qualy), indexovaný text; [Sky Q1 3.2.](https://videos.sport.sky.de/tennis/spielplan-ergebnisse/03-02-2024).
- COR24-10: [ATP Q postupy před Main 5.2.](https://www.atptour.com/es/news/cordoba-2024-previa-bagnis-gomez-burruchaga), [dobová Q entry zpráva 16.1.](https://www.cba24n.com.ar/deportes/las-promesas-argentinas-sobresalen-la-lista-de-la-clasificacion-del-cordoba-open-2024_a65a5b1172541f95bcbf5f486).
- COR24-11: [ATP Day 2 6.2.](https://www.atptour.com/-/media/28dc2cb03db94d56938a2f34e9e10657.pdf), text; [pořadatel první den](https://www.cordobaopen.com/articulo/1051/32837/bagnis-y-diaz-acostan-avanzan-en-cordoba), [druhý den](https://www.cordobaopen.com/articulo/1051/32838/roman-burruchaga-vivio-un-debut-soniado-en-el-cordoba-open).
- COR24-12: [ATP Day 3 7.2., druhé kolo](https://www.atptour.com/-/media/3903551e6b6c4f30931710401653d4fa.pdf), indexovaný text, screenshot 403.
- COR24-13: [pořadatel 8.2., středeční R16](https://www.cordobaopen.com/articulo/1051/32840/etcheverry-debuto-con-solvencia-en-el-atp-250-cordoba-open), čtyři R16 a první kolo čtyřhry výslovně oddělené.
- COR24-14: [ATP déšť 8.2.](https://www.atptour.com/en/news/darderi-ofner-cordoba-2024-thursday), [ATP dohánění R16/QF 9.2.](https://www.atptour.com/en/news/baez-dellien-cordoba-2024-friday).
- COR24-15: [ATP Competition 22.1.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_22jan.pdf), indexovaný text; viz též MPL24-7. [ATP Competition 2.8.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_02aug.pdf) potvrzuje obecné 28/21denní lhůty, nikoli skutečný Q deadline ročníku.
- COR24-16: [ATP results archive 2024](https://www.atptour.com/en/scores/results-archive?year=2024), týdenní inventura.
- COR24-17: [ATP Next Gen oznámení 20.12.2023](https://www.atptour.com/en/news/next-gen-atp-brand-expansion-2024), [ročníkový ATP Competition 2.7.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_02jul.pdf), indexovaný text pravidla účinného od 1.1.2024; konkrétní rozdělení akcím nedoloženo.
- COR24-18: [historická finanční tabulka](https://tenniscompanion.org/prize-money/cordoba/), [sekundární Q přehled](https://de.wikipedia.org/wiki/C%C3%B3rdoba_Open_2024), [TennisTemple Q pavouk](https://en.tennistemple.com/competition/cordoba-2024/62848/draw-qualifications). Originální ATP URL [Q](https://www.protennislive.com/posting/2024/9158/qs.pdf) nedostupná; alternativní primární pořadatelská kopie COR24-1 dostupná textově.


## Dallas 2024

**Stav:** HOTOVO v nominálním rozsahu 9/9 s vyznačenými omezeními H/E/R/P/Z. Rešerše 2026-11-27. Kategorie ATP 250 v roce 2024, nikoli ATP 500 z roku 2025. Žádná konverze do enginu.

### 1. Identita

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název / disciplína | Dallas Open 2024, mužská dvouhra | DAL24-1/2 |
| Kategorie / ATP ID | ATP 250 / 424 | DAL24-1/3 |
| Dějiště | Styslinger/Altec Tennis Complex, Southern Methodist University, Dallas, Texas, USA | DAL24-1/2/4 |
| Povrch | krytý tvrdý, Laykold | DAL24-5/6 |
| Časové pásmo | America/Chicago, CST UTC−06:00 v únoru | lokalita a datum |
| Ředitel | Peter Lebedevs | DAL24-2 |
| Měna | USD | DAL24-1 |
| Míče, referee, supervisor, diety | NEOVĚŘENO pro mužskou dvouhru | doplňková metadata |

Třetí ročník v Dallasu, historická série má delší historii v jiných městech (DAL24-1). Nepřebírat Ford Center ve Frisco z ročníku 2025 ani jeho novou ATP 500 kategorii (DAL24-7).

### 2. Vstup, termíny a losování

| Událost | Údaj | Zdroj / význam |
|---|---|---|
| Main rank date | 2024-01-08 | DAL24-8, dobový přepis |
| Q rank date v přepisu | 2024-01-08 | DAL24-8; nepovažovat za uzávěrku, rozpor s obecným výpočtem 15.1. |
| Nominální Main deadline | 2024-01-08 12:00 US Eastern = 11:00 CST | §7.03, 28 dní před 5.2., odvozeno |
| Nominální Q deadline | 2024-01-15 12:00 US Eastern = 11:00 CST | §7.03, 21 dní před 5.2., odvozeno |
| Nominální LE deadline | 2024-02-01 10:00 US Eastern = 09:00 CST | §7.04, odvozeno |
| Q los | zveřejněn nejpozději 3.2. | hostitel SMU předem uvedl konkrétní dvojice, DAL24-4; přesný čas neověřen |
| Main los | zveřejněn nejpozději 3.2. | DAL24-4/9; přesný okamžik losu neověřen |
| Q1 | 2024-02-04, oznámený start 11:00 CST | DAL24-4, předturnajový článek 3.2. |
| Q2 | 2024-02-05 | DAL24-1/10; čtyři postupující určeni v pondělí |
| Main | 2024-02-05–11 | DAL24-1/3 |
| Finále | 2024-02-11 13:00 CST | DAL24-1 str. 1, oznámený program |

Celé pořadatelské okno 3.–11.2. (DAL24-2) zahrnuje 3.2. v 19:00 Women's Tennis Classic, nikoli mužskou Q (DAL24-11). Některý sekundární web uvádí Q 3.–4.2. (DAL24-12); v rozporu s dobovým oznámením SMU a pondělními ATP notes. Mužské Q 4.–5.2. mají přednost. Historický cutoff Main 92 a Q 164 z přepisu DAL24-8 nejsou nominální kvóty. Detail Sheet nedostupný, přesné ročníkové uzávěrky samostatně neověřeny.

### 3. Nominální harmonogram

| Kolo | Místní datum / okno | Nominální zápasy | Důkaz |
|---|---|---:|---|
| Q1 | 2024-02-04 | 8 | DAL24-4/10 |
| Q2 | 2024-02-05 | 4 | DAL24-1/10 |
| R32 | 2024-02-05–06 | 12 | DAL24-13 |
| R16 | 2024-02-07–08 | 8 | DAL24-14 |
| QF | 2024-02-09 | 4 | DAL24-15 |
| SF | 2024-02-10 | 2 | DAL24-15 |
| F | 2024-02-11 | 1 | DAL24-1/15 |

Q 2 kalendářní dny, Main 7 dní, celé sportovní okno 8 dní. Q2 a R32 souběžně 5.2. Dobové denní ATP Media Notes a zprávy pořadatele potvrzují okna Main; kompletní původní předturnajový rozpis všech dnů nezískán. Q1 oznámena předem hostitelem a Q2 přímo ATP Preview jako pondělní určení čtyř postupujících. Denní rozdělení 12/8 zápasů vícedenních kol se neodhaduje; některé agregátory zobrazují následující den kvůli jinému pásmu (např. QF 10.2.), místní ATP notes mají přednost. 27 Main + 12 Q = 39 nominálně hraných zápasů. Historický R16 walkover nenahrazuje standardní program.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Účastníci | 28 | 16 |
| Základní DA dle standardní tabulky | 18 | 14 |
| SE rezervy | 2 | nevztahuje se |
| LE rezerva | 1 | nevztahuje se |
| WC | 3 | 2 |
| Q postupy | 4 | 4 vítězové sekcí |
| DA při nevyužití SE/LE | 21 (bez zvláštní NextGen alokace) | 14 (bez zvláštní NextGen alokace) |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / nominálně hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 | BO3 |

18+2+1+3+4=28 a 14+2=16; standardní rámec dle §7.08 a přepisu DAL24-8 (18 DA, 3 WC, 4 Q, pozdější rezervy zatím neobsazené). Přesná ročníková alokace NextGen zůstává otevřená a může měnit složení uvnitř kapacity, nikoliv celkový počet. Původní ATP kalendář potvrzuje 28/16 (DAL24-6). Main konečný sekundární archiv DAL24-16 potvrzuje osm seedů, čtyři BYE, čtyři Q, tři WC, dva LL během průběhu turnaje; první LL očekáván v pondělních ATP notes, druhý až při pozdějším odstoupení. Nejde o plánovanou kvótu. Q úplný archiv DAL24-17: 16 účastníků, všech osm seedů, dva označení WC (Trevor Svajda/Jerry Barton, potvrzeno přímo SMU), dvě označení Alt, čtyři sekce po čtyřech, bez BYE. U neoznačených hráčů nelze bez vstupní listiny určit přesný typ akceptace. BO3 potvrzen výsledky obou pavouků. Nezaměňovat tři původně oznámené WC z 9.1. (Opelka, Neff, Quinn) s konečným stavem (Krueger, Neff, Quinn) v ATP Preview.

### 5. Dobová pravidla a Next Gen

ATP §7.03/7.04/7.08/7.10/7.12/7.15–16/7.20 (MPL24-7, ADL24-8, DAL24-18): 8 Main seedů, BYE pro 4 nejvyšší; Q 8 seedů ve 4 sekcích, Q vítězové přiřazeni po kvalifikaci do volných míst losem. SE/LE rezervy a jejich uvolnění dle předpisu, LL pořadí dle ATP (ne Grand Slam). První prohra po BYE = 0 bodů, výslovně v DAL24-1 str. 2. Odměny a body se posuzují odděleně podle finančního předpisu AKL24-14.

**Upřesnění Next Gen:** ATP oznámení 20.12.2023 uvádí pro způsobilé hráče (20 let a méně, top 250) jednu Main a dvě Q příležitosti na úrovni ATP 250; to není automaticky počet míst v každém pavouku ani nárok využít všechny v jednom týdnu. §7.08 dobového 2024 Rulebooku hostovaného ITF (DAL24-18, tištěná str. 147) výslovně uvádí jedno rezervované NextGen Program místo pro ATP 250 v týdnech se třemi ATP Tour turnaji. Znění ověřeno textově, screenshot nedostupný; samotná konkrétní alokace Main/Q pro Dallas a ostatní dvě akce z dostupných listin nezjištěna. Alex Michelsen, kterého pořadatel označuje jako NextGen, byl již v původní Main listině jako DA na ranku 92 (DAL24-8), samotná marketingová značka tedy není důkaz využití rezervy. Nezvyšovat 28/16. Otevřený společný audit týdne zůstává v seznamu.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD | Doklad |
|---|---:|---:|---:|---|
| Vítěz | 1 | 250 | 114970 | ATP |
| Finalista | 1 | 165 | 67070 | ATP |
| SF | 2 | 100 | 39435 | ATP |
| QF | 4 | 50 | 22850 | ATP |
| R16 | 8 | 25 (0 při první prohře po BYE) | 13270 | ATP |
| R32 | 12 | 0 | 8110 | ATP |
| Q postupující | 4 | 13 | 0 samostatně | sekundární |
| Q2 prohra | 4 | 7 | 4055 | sekundární shoda |
| Q1 prohra | 8 | 0 | 2210 | sekundární shoda |

Main tabulka přímo ATP Preview str. 2 (DAL24-1, text, screenshot 403), nezávisle shoda s TennisCompanion a TennisTemple. Q peníze shodně ve třech sekundárních tabulkách DAL24-17/19/20; jejich vzájemná nezávislost není prokázána. Původní Q PDF nedostupné. TennisTemple uvádí chybně 8 bodů Q2 a označuje postup jako Q3; dobový ATP rankingový předpis a předsezonní oznámení (DAL24-21) potvrzují 7 bodů a Q má pouze dvě kola. Italský přehled uvádí R32 8100 USD, ale primární ATP uvádí 8110; německé archivní zrcadlo také vykazuje chybné Q řádky, proto primární Main a shoda ročníkových Q tabulek mají přednost. Stevegtennis označuje měnu A$; originální ATP tabulka v USD je autorita pro denominaci. Main nominální součet 555790 USD, Q 33900 USD, celkem 589690 USD; ne celkový prize pool. ITF uvádí celoturnajové prize money 756020 USD (DAL24-22), původní ATP doubles draw financial commitment 841590 USD (DAL24-5). Neodvozovat z rozdílu neznámé odměny. Q body se přičítají dle ATP předpisu; P* značí, že původní Q finanční tabulku je třeba opětovně ověřit, nikoli primární jistotu.

### 7. Kontrola a omezení

I/T/D/B doloženy dobovými ATP/SMU materiály a úplnými sekundárními pavouky. H*: denní okna z dobových notes a zpráv, ne kompletní původní předturnajový rozpis; E*: Main/Q rank dates z přepisu, skutečné uzávěrky a okamžik losu neověřeny; R*: dobový rulebook textově, NextGen přesná turnajová alokace otevřena; P*: Main primární, Q sekundární shoda (odlišný chybný bodový údaj odmítnut); Z*: ATP původní Main/Q/DS nedostupné, screenshoty ATP notes a ITF hostovaného rulebooku 403/500; žádné nové vizuální ověření singlových losů ani SHA-256 se nepředstírá. Existující ročník v `buuk` kalendáři má Main 5.–11.2.; Dallas 2025 je jiná kategorie a nesmí se zaměnit. Další Marseille 2024, ověřit mapování identity a pokračovat ve společném auditu NextGen.

### 8. Zdroje (DAL24)

- DAL24-1: [ATP Preview & Day 1 5.2.2024](https://www.atptour.com/-/media/038f94d7dade47f4958a0f418d9a46ff.pdf), str. 1 (Q/LL, finále), str. 2 (body, odměny, BYE), indexovaný text, screenshot 403.
- DAL24-2: [pořadatel entry field 9.1.2024](https://www.dallasopen.com/en/media/news/2024playerfieldreleased), místo, ředitel, celé okno akce, původní WC.
- DAL24-3: [ATP identita série 424](https://www.atptour.com/en/tournaments/nexo-dallas-open/424/overview), [TennisTV ročník 424_2024](https://www.tennistv.com/tournaments/424_2024/dallas).
- DAL24-4: [SMU 3.2.2024 – Q WC a nedělní start](https://smumustangs.com/news/2024/2/4/mens-tennis-mustangs-set-to-compete-in-2024-dallas-open), datum v záhlaví 3.2., URL 4.2.; předem uvedeny konkrétní dvojice a start 11:00.
- DAL24-5: [archivní původní ATP doubles los](https://www.raquetc.com/wp-content/uploads/2024/02/mdd.pdf), pouze hlavička povrchu/dotace, text; screenshot nebylo možné vyřešit. Nejde o singlový los.
- DAL24-6: [ATP/Challenger Calendar 8.2.2024](https://www.atptour.com/-/media/files/calendar-pdfs/2024/2024-atp-challenger-calendar-as-of-8-february-2024.pdf), indexovaný řádek IH/28/16.
- DAL24-7: [ATP Dallas 2025 preview – první ATP 500](https://www.atptour.com/en/news/dallas-2025-history-draw-schedule).
- DAL24-8: [dobový přepis Main/Q entry listů 20.1.](https://www.tennisteen.it/entry-list/atp/24110-atp-entry-list-5-11-febbraio-2024.html), Dallas řádky 120–181.
- DAL24-9: [dobová zpráva o zveřejnění Main losu](https://tennis-infinity.com/atp/2024-dallas-open-atp-draw-with-shelton-tiafoe-paul-more).
- DAL24-10: [Sky Q1 4.2.](https://www.skysports.com/tennis/scores-schedule/04-02-2024), [Q2 5.2.](https://www.skysports.com/tennis/scores-schedule/05-02-2024), používat s místními daty DAL24-1/4.
- DAL24-11: [pořadatel oznámení exhibice 3.2.2024](https://www.dallasopen.com/en/media/news/womens-tennis-classic), nikoli mužské Q.
- DAL24-12: [sekundární přehled s chybným Q datem](https://gotennisracquets.com/dallas-open/), odmítnuto vůči DAL24-1/4.
- DAL24-13: [ATP Day 2, 6.2.](https://www.atptour.com/-/media/edab2f947f2f40d1b779dc205a04b8b0.pdf), text/screenshot 403; [pořadatel pondělí](https://www.dallasopen.com/en/media/news/purcell-krueger-dallas-2024-monday), [úterý](https://www.dallasopen.com/en/media/news/eubanks-michelsen-dallas-2024-tuesday).
- DAL24-14: [ATP Day 3, 7.2.](https://www.atptour.com/-/media/39282fbd554e4a5ba16f9255f708974c.pdf), [Day 4, 8.2.](https://www.atptour.com/-/media/88b39511783e440e8c09c8b03a00b099.pdf), text/screenshoty 403; [pořadatel čtvrteční R16](https://www.dallasopen.com/en/media/news/tiafoe-michelsen-dallas-2024-thursday).
- DAL24-15: ATP notes [QF 9.2.](https://www.atptour.com/-/media/a02a0a52cedb4c16939e5935ada58e62.pdf), [SF 10.2.](https://www.atptour.com/-/media/0f74ca2013c24da29b6089b4781c682a.pdf) indexované názvy fází; [F 11.2.](https://www.atptour.com/-/media/dbe73f4ce72f40938fcd7ce99509cc94.pdf), text/screenshot 403; [pořadatel QF](https://www.dallasopen.com/en/media/news/paul-koepfer-dallas-2024-friday).
- DAL24-16: [úplný Main archiv TennisTemple](https://en.tennistemple.com/competitions/dallas/2024/draw), místy špatný nadpis Long Island, identita potvrzena datem a hráči; [nezávislá Main kontrola](https://en.wikipedia.org/wiki/2024_Dallas_Open_%E2%80%93_Singles).
- DAL24-17: [úplný Q archiv TennisTemple](https://fr.tennistemple.com/competitions/dallas/2024/draw-qualifications), Q peníze, chybné body Q2 8 a štítek Q3; [nezávislá kontrola Q](https://de.wikipedia.org/wiki/Dallas_Open_2024/Qualifikation).
- DAL24-18: [2024 ATP Rulebook hostovaný ITF](https://www.itftennis.com/media/11845/2024-rulebook-atp-update.pdf?embed=true), §7.08 tištěná str. 146–147, text, screenshot 500/redirect; [ATP Next Gen oznámení 20.12.2023](https://www.atptour.com/en/news/next-gen-atp-brand-expansion-2024), [ATP lednová verze](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_22jan.pdf) viz MPL24-7.
- DAL24-19: [TennisCompanion ročníkový USD rozpis](https://tenniscompanion.org/prize-money/dallas/), sloupec 2024; nebrat jeho aktuální formát jako historický.
- DAL24-20: [Stevegtennis ročník 2024](https://www.stevegtennis.com/draw-results/atp/Dallas%20Open%20-%20Dallas/2024), Q částky souhlasí, chybné A$ označení; [italský přehled](https://it.wikipedia.org/wiki/Dallas_Open_2024) shoda Q, nesouhlas R32, [německý archiv](https://wiki.postl.cc/content/wikipedia_de_all_maxi_2024-03/A/Dallas_Open_2024) nesouhlas některých řádků.
- DAL24-21: [ATP předsezonní aktualizace 2024](https://www.atptour.com/en/news/2024-rankings-points-update), tabulka ATP250, 13/7; další ročníkový rankingový předpis viz BRI24-17.
- DAL24-22: [ITF Dallas 2024](https://www.world.tennis/en/tournament/dallas/usa/2024/m-250-usa-2024-001/draws-and-results/), celková dotace. Originální ATP [Main](https://www.protennislive.com/posting/2024/424/mds.pdf), [Q](https://www.protennislive.com/posting/2024/424/qs.pdf), [DS](https://www.protennislive.com/posting/2024/424/ds.pdf) v tomto průchodu nedostupné.


## Marseille 2024

**Stav:** ROZPRACOVÁNO (8/9). E: rozpor konkrétní nominální kvalifikační WC kvóty mezi pořadatelským press kitem a dobovým přepisem ATP acceptance listu. Ostatní oblasti pokryty, včetně primárních Q odměn a historické identity série. Rešerše 2026-11-27.

### 1. Identita a mapování série

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Open 13 Provence, mužská dvouhra 2024 | MRS24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 496 | MRS24-3/4 |
| Dějiště obou fází | Palais des Sports, Marseille, Francie | MRS24-3 |
| Povrch | krytý tvrdý, acrylic on wood | MRS24-1/2/3 |
| Časové pásmo | Europe/Paris, CET UTC+01:00 v únoru | lokalita a datum |
| Ředitel | Jean-François Caujolle | MRS24-3/5 |
| Míče | Babolat | MRS24-3, značka, přesný model neověřen |
| Video review | Foxtenn | MRS24-3 |
| ATP supervisor / referee | Stéphane Cretois / Pascal Maria v OOP 5.2.; Main verze 6.2. uvádí Cédric Mourier jako supervisora | MRS24-5/1; zachovat rozdíl verzí |
| Měna | EUR | MRS24-1/2/3/6 |

**Identita série vs místo ročníku:** `calendar_dates_v1.json` na `buuk` uvádí `lyon` 5.–11.2.2024 a `lyon_old` 19.–25.5.2024. ATP oficiální archiv MRS24-7 rozlišuje Marseille v únoru a Lyon v květnu; originální mužská acceptance list MRS24-4 má ID 2024-496. ATP oznámení MRS24-8 potvrzuje relokaci série 496 z Marseille do Lyon-Décines od 2026; samostatný květnový Lyon měl ID 7694 (MRS24-9). Označení `lyon` v katalogu může být stabilní identita přejmenované série, nikoli chybné datum. Historický název/místo pro 2024 zůstává Marseille; žádná změna identifikátorů ani runtime. Přesné ověření interní definice série nebylo dokončeno (pokus o cestu k series souboru 404); nepotvrzujeme správnost celého katalogu.

### 2. Vstup a losování

| Událost | Datum / čas | Zdroj |
|---|---|---|
| Main rank date | 2024-01-08 | originální ATP acceptance list MRS24-4 |
| Q rank date v přepisu | 2024-01-08 | MRS24-10; není dokladem uzávěrky |
| Nominální Main deadline | 2024-01-08 12:00 US Eastern = 18:00 CET | odvozeno dle §7.03 |
| Nominální Q deadline | 2024-01-15 12:00 US Eastern = 18:00 CET | odvozeno dle §7.03; skutečný Q deadline neověřen |
| Nominální LE deadline | 2024-02-01 10:00 US Eastern = 16:00 CET | odvozeno dle §7.04 |
| Q/Main losy | před příslušným prvním kolem; přesné časy neověřeny | MRS24-5/11 |
| Q | 2024-02-04–05 | MRS24-3/5/12 |
| Main | 2024-02-05–11 | MRS24-1/3/6/7 |
| Finále | 2024-02-11 15:30 CET dle pořadatelského press kitu | MRS24-3; sekundární předběžný program MRS24-13 uvádí 14:00, přednost pořadatelskému plánu |

Originální Main acceptance list 9.1. má cutoff 73 a rank date 8.1.; pozdější Main los uvádí cutoff 87 při deadline a 97 v losu. Jde o různé okamžiky, nikoli pevné parametry. Originální Q acceptance list a detail sheet nezískány. Údaj rank date se nezaměňuje s časem uzávěrky.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-04 | 8 |
| Q2 | 2024-02-05 | 4 |
| R32 | 2024-02-05–07 | 12 |
| R16 | 2024-02-07–08 | 8 |
| QF | 2024-02-09 | 4 |
| SF | 2024-02-10 | 2 |
| F | 2024-02-11 | 1 |

Předem vydaný pořadatelský press kit MRS24-3, oddíl Programme prévisionnel, výslovně uvádí překryv Q/Main 5.2. a R32/R16 7.2.; Q 4.2. od 11:00, 5.2. od 12:00, 6.–8.2. od 11:30, 9.2. od 12:30, 10.2. od 14:00, finále 11.2. v 15:30. Jeho denní počty Main zahrnují čtyřhru; nepoužívat je jako singlové počty. OOP 5.2. vydán 4.2. 12:58 (MRS24-5) přímo potvrzuje 4 Q2 a 3 R32, od 16:00 Main; přesné počty jiných vícedenních kol neodhadovat. Q 2 dny, Main 7 dní, celé okno 8 dní, 27+12=39 nominálních zápasů. Sekundární předběžný časový plán MRS24-13 se liší v některých hodinách; data kol souhlasí a pořadatelský press kit má přednost.

### 4. Nominální struktura a rozpor vstupních kvót

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Účastníci | 28 | 16 |
| Základní DA | 18 dle originální ATP listiny | 14 dle přepisu ATP listiny / 12 dle press kitu |
| Rezervy | 3 souhrnně v originální listině; standard ATP 2 SE + 1 LE | nevztahuje se |
| WC | 3 | 2 dle přepisu / 4 dle press kitu – otevřeno |
| Řádné Q postupy | 4 | 4 vítězové sekcí |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / hrané zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Originální ATP Main acceptance list (MRS24-4, vydání 9.1. 03:19) výslovně uvádí 18 DA, 3 WC, 4 Q a 3 možné SE (součet 28). Standard §7.08 lednové verze rozlišuje 2 SE a 1 LE; dobový přepis z 20.1. uvádí 18 DA, 1 LE, 1 SE, 3 WC a 4 Q, tj. mezistav bez úplného součtu. Neprohlašovat 3 souhrnné rezervy ve starší listině za tři definitivní SE podle pozdějšího členění. Press kit uvádí 19 DA + 2 SE + 4 Q + 3 WC, což je jiné členění a pravděpodobně obecný starší popis; nemáme doklad, že tento popis byl skutečně závazný pro ročník. Main základní standard 18+2+1+3+4=28 s otevřenou specifickou NextGen alokací uvnitř pevné kapacity.

**Blokující E:** Q press kit uvádí 12 DA + 4 WC (MRS24-3); ročníkový přepis acceptance listu uvádí 14 DA + 2 WC (MRS24-10), což odpovídá standardu ATP 250. Originální výsledkový Q los (MRS24-2) viditelně označuje pouze jednu WC, pět Alt a osm seedů; nevyužití WC neřeší otázku původní nominální kvóty. Obě nominální varianty mají 16 míst. Nelze bez původního Q acceptance listu, DS nebo výslovného vyjádření ATP určit, zda byla ročníková výjimka 4 WC, či je press kit zastaralý. Preferovaný kandidát 14+2, nikoli certifikovaná hodnota. E zůstává otevřeno.

Vizuálně ověřená předstartovní Main kopie MRS24-11: BYE 2/10/23/31, Q placeholdery 11/26/27/30, WC 3/12/18, Alt 7/28 a osm seedů. Originální verze 6.2. potvrzuje čtyři Q, jeden LL (Zeppieri na místě 20), dva Alt a tři WC. Q text originálu má všech 16 hráčů a osm seedů, čtyři sekce po čtyřech, 8+4 zápasů. Main 12+8+4+2+1=27; BYE není zápas. Skutečné výměny nepromítat do nominálního plánu.

### 5. Dobová pravidla

BO3 včetně tiebreaku ve všech setech výslovně pořadatel MRS24-3. Standard ATP §§7.03/7.04/7.08/7.10/7.15–16/7.20 (MPL24-7/ADL24-8): 8 Main seedů, top 4 BYE, Q 8 seedů ve 4 sekcích; Q vítězové losováni do volných Main pozic, SE/LE uvolnění nevyužitých míst, LL dle ATP. Prohra prvního hraného kola po BYE = nula bodů, potvrzeno ATP Media Notes MRS24-6. Finanční odměny odděleně dle ATP finančního předpisu.

Next Gen: ATP §7.04 v ročníkové verzi z 10.7.2024 (MRS24-14) výslovně popisuje způsobilost narozených 2004 a později, top 250, jednu Main a dvě Q příležitosti v týdnu se třemi ATP akcemi a uvolnění nevyužitých pozic. Jde o příležitosti programu, ne automatické navýšení kapacity. ATP 26.2.2024 výslovně potvrdila využití rezervy Jakubem Menšíkem v Doha (MRS24-15); to nedokládá konkrétní únorovou alokaci v Marseille, Dallasu či Córdobě. Pozdější ročník pravidel nepřenášet zpět bez kontroly. Přesné turnajové vyhrazení v týdnu 5.2. zůstává v otevřené evidenci.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 110115 |
| Finalista | 1 | 165 | 64240 |
| SF | 2 | 100 | 37765 |
| QF | 4 | 50 | 21885 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 12705 |
| R32 | 12 | 0 | 7765 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3885 |
| Q1 prohra | 8 | 0 | 2120 |

Main přímo originální Main los MRS24-1 (text), vizuálně zkontrolovaná předstartovní kopie MRS24-11 a dobové ATP Media Notes MRS24-6. Q hodnoty v originálním ATP Q losu zveřejněném pořadatelem MRS24-2 (text v zápatí, screenshot 502). Q body dle stejné tabulky 13/7/0, přičtení dle ročníkových pravidel. Nominální součet Main 532245 EUR, Q 32500 EUR, celkem 564745 EUR. Prize pool dle pořadatelského press kitu 724015 EUR; total financial commitment 801335 EUR z losů je odlišný. Nezaměňovat s nominálním singlovým součtem.

### 7. Kontrola a mezery

I/T/H/D/B/P doloženy. E otevřeno kvůli rozporu 12+4 versus 14+2 Q; nominální Main administrativní rezervy odděleny od historické realizace. R* dobové ATP pravidlo doloženo textem, NextGen přesná alokace otevřena. Z* Main předstartovní originální kopie vizuálně; pořadatelský originál Q/Main, press kit, OOP a Main acceptance list textově, screenshoty 502; ATP notes screenshot 403, žádné vymyšlené hashe. Další krok dohledat originální Q acceptance list/DS či písemný ročníkový Q WC předpis. Poté Buenos Aires 2024 (při přetrvávajícím bloku po dokumentované opakované rešerši pokračovat bez povýšení stavu). Runtime beze změny.

### 8. Zdroje (MRS24)

- MRS24-1: [pořadatel ATP Main los 6.2.](https://www.open13.fr/wp-content/uploads/2024/02/MDS_060224.pdf), text, screenshot 502.
- MRS24-2: [pořadatel ATP Q los 5.2.](https://www.open13.fr/wp-content/uploads/2024/02/QS_050224.pdf), text, screenshot 502.
- MRS24-3: [pořadatelský press kit ročníku](https://www.open13.fr/wp-content/uploads/2024/02/DOSSIER-DE-PRESSE-V2.pdf), oddíly Tableau de bord, Déroulement de la compétition, Programme prévisionnel; text, screenshot 502.
- MRS24-4: [originální mužský ATP acceptance list 9.1.](https://www.open13.fr/wp-content/uploads/2024/01/Singles-Acceptance-List-open1324.pdf), text, screenshot 502, footer ID 2024-496.
- MRS24-5: [originální OOP 5.2., vydán 4.2. 12:58](https://www.open13.fr/wp-content/uploads/2024/02/OP_4224.pdf), text, screenshot 502.
- MRS24-6: [ATP Preview & Day 1](https://www.atptour.com/-/media/24ce339c3bba4717b70cc06ecb77539c.pdf), str. 2, text, screenshot 403.
- MRS24-7: [ATP výsledkový archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), Marseille 5.–11.2., Lyon 19.–25.5.; [Tennis Europe 2024](https://www.tenniseurope.org/calendar/82/European-Tennis-Calendar?egid=42&year=2024) nezávisle potvrzuje.
- MRS24-8: [ATP relokace série do Lyonu od 2026](https://www.atptour.com/en/news/marseille-lyon-relocation), [ATP ID 496](https://www.atptour.com/en/tournaments/marseille/496/overview).
- MRS24-9: [ATP původní Lyon ID 7694](https://www.atptour.com/en/tournaments/lyon/7694/overview).
- MRS24-10: [dobový přepis Main/Q acceptance listu 20.1.](https://www.tennisteen.it/entry-list/atp/24110-atp-entry-list-5-11-febbraio-2024.html), Marseille, explicitně 14 DA/2 WC pro Q.
- MRS24-11: [archiv původního předstartovního ATP Main losu](https://www.fantatennis.net/_downloads/e73fef15c93cc78e7dc67fbca63180c9), str. 1 vizuálně ověřena.
- MRS24-12: [Sky Q1 4.2.](https://www.skysports.com/tennis/scores-schedule/04-02-2024).
- MRS24-13: [sekundární předběžný program](https://the-place-to-be.fr/evenement/open-13-provence-marseille/), odlišné některé hodiny, shoda okna kol.
- MRS24-14: [ATP Rulebook 2024, 10.7., §7.04](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_10jul.pdf), text programu účinného od 1.1.2024; viz dřívější pokusy o screenshot AKL24-22; [ATP oznámení 20.12.2023](https://www.atptour.com/en/news/next-gen-atp-brand-expansion-2024).
- MRS24-15: [ATP potvrzení Menšíkovy rezervy Doha 26.2.2024](https://www.atptour.com/en/news/mensik-michelsen-fonseca-next-gen-review-26-february-2024), nevztahovat na Marseille.


### 9. Opakovaná kontrola E — 2026-11-27

- MRS24-16: [ATP Rulebook, kapitola VII, 21.12.2023](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_21dec.pdf), §7.08 E.1, tištěné str. 149–150: řádek pro ATP 250 rozlišuje 16 míst, 14 DA a 2 WC; stejný předpis v [lednové verzi 22.1.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_22jan.pdf). Prosincová kapitola textově dostupná; screenshot 403. Lednová verze indexovaný text, přímý přístup 403.
- MRS24-17: [press kit pořadatele 2025](https://www.open13.fr/wp-content/uploads/2025/02/DOSSIER-DE-PRESSE-202590.pdf), oddíl průběhu soutěže opakuje 12 DA + 4 WC a Main 19 DA + 2 SE + 4 Q + 3 WC; jde o jiný ročník, nikoli důkaz hodnoty pro 2024. Text dostupný, screenshot 502. Opakování zvyšuje podezření na šablonový popis, ale neprokazuje absenci schválené ročníkové výjimky.
- Nová kontrola tedy zesiluje kandidáta 14+2 (dobový předpis i ročníkový přepis MRS24-10). Původní ročníkový Q acceptance list/DS ani výslovnou výjimku jsme nezískali. Rozpor nezamlčujeme, E zůstává otevřeno; po dokumentovaném opakování pokračujeme dalším ročníkem bez povýšení Marseille.

## Buenos Aires 2024

**Stav:** HOTOVO (nominální rozsah, 9/9; E/R/P/Z s označenými omezeními). Rešerše 2026-11-27. Plán a skutečný průběh odděleny; žádný převod do Squash Enginu.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | IEB+ Argentina Open, mužská dvouhra | BUE24-1/2 |
| Kategorie / ATP ID | ATP 250 / 506 | BUE24-1/3 |
| Dějiště | Buenos Aires Lawn Tennis Club, Buenos Aires, Argentina | BUE24-2/4 |
| Povrch | venkovní červená antuka | BUE24-1/4/5 |
| Časové pásmo | America/Argentina/Buenos_Aires, ART UTC−03:00 | lokalita a datum |
| Ředitel | Martín Jaite | BUE24-6 |
| ATP supervisor / referee | Carlos Sanches a Jorge Mandl / Damian Steiner | BUE24-1/6 |
| Tour manager | Thomas Schrader | BUE24-6 |
| Měna | USD | BUE24-1/2 |

Nezaměňovat s lednovým a dalšími Challenger turnaji v Buenos Aires ani listopadovou WTA 125. ATP ročníkový identifikátor 506_2024 je potvrzen TennisTV. Míče a původní ATP detail sheet nedohledány.

### 2. Vstup a losování

| Událost | Datum / čas | Zdroj |
|---|---|---|
| Main rank date | 2024-01-15 | BUE24-7 |
| Q rank date | 2024-01-22 | BUE24-7 |
| Nominální Main deadline | 2024-01-15 12:00 US Eastern = 14:00 ART | odvozeno dle §7.03 |
| Nominální Q deadline | 2024-01-22 12:00 US Eastern = 14:00 ART | odvozeno dle §7.03 |
| Nominální LE deadline | 2024-02-08 10:00 US Eastern = 12:00 ART | odvozeno dle §7.04, lednová verze |
| Q alternate sign-in v den Q1 | 2024-02-10 11:30 ART | originální OOP BUE24-6 |
| Q/Main losování | před příslušnou fází; přesné datum a čas neověřeny | BUE24-1/6 |
| Q | 2024-02-10–11 | BUE24-6/8/9 |
| Main | 2024-02-12–18 | BUE24-1/2/3/4 |
| Finále | 2024-02-18 ne před 16:00 ART | BUE24-9/10, denní program, ne skutečný čas prvního servisu |

Přepis acceptance listu uvádí Main původní cutoff 78, Q 128. Předstartovní originální Main pavouk uvádí poslední přímou akceptaci při deadline i při losu Varillas 81. Jde o rozdílné zdrojové okamžiky/údaje; nelze je zaměnit ani vydávat za shodné bez originální acceptance listiny. Časy uzávěrek jsou pravidlové odvození, nikoli doložené publikované časy konkrétního ročníku.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-10 | 8 |
| Q2 | 2024-02-11 | 4 |
| R32 | 2024-02-12–13 | 12 |
| R16 | 2024-02-14–15 | 8 |
| QF | 2024-02-16 | 4 |
| SF | 2024-02-17 | 2 |
| F | 2024-02-18 | 1 |

Předturnajový program BUE24-8 uvádí přesně tato okna. Originální Q1 OOP vydaný 9.2. ve 21:26 (BUE24-6) plánuje osm zápasů na dvou kurtech od 12:00; Q2 čtyři zápasy 11.2. potvrzeny místním rozpisem BUE24-9. BUE24-9/11 potvrzují denní Main rozdělení R32 4+8 a R16 4+4, QF/SF/F 4/2/1. Jde o dobové denní rozpisy, nikoli rekonstrukci prvního předturnajového plánu po jednotlivých zápasech. R32 se místně hraje 12.–13.2.; archiv BUE24-12 uvádí R32 až 14.2. bez jasného časového pásma, což nemění doložené místní okno. Ve skutečných výsledcích Q1 se Vavassoriho soupeř změnil z Martíneze uvedeného v předem vydaném OOP na Pellegrina (BUE24-9/13); nominální počty ani harmonogram se nemění. Q 2 dny, Main 7 dní, celé okno 9 dní, bez překryvu. 39 nominálních zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita pavouka | 32 | 16 |
| Účastníci | 28 | 16 |
| Základní DA | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 (standard, nevyužita v doloženém losu) | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28, dle dobového lednového §7.08. Ročníkový přepis (BUE24-7) vykazuje 18 DA, 2 SE, 0 LE, 3 WC, 4 Q, tedy mezistav 27 míst. Předstartovní původní ATP Main los BUE24-1 vizuálně ověřen: BYE 2/10/23/31; Q placeholdery 4/5/14/28; WC 7/13/21; SE 27/30; osm nasazených. Zbývá 19 neoznačených míst, což souhlasí s uvolněním nevyužité LE rezervy, ale konkrétní administrativní důvod každého vstupu neodvozujeme jen ze štítku. Obě SE skutečně využity; nejsou dodatečnými místy mimo kapacitu.

Q: 14 DA + 2 WC = 16 dle BUE24-7 a dobového §7.08 E.1. Oficiální Q1 OOP má dvě WC a dva Alt; výsledkový sekundární pavouk BUE24-13 má 16 hráčů, dvě WC, 4 sekce a 12 zápasů. Označeno jen sedm různých seedů (1,2,3,5,6,7,8), důvod chybějícího čtvrtého seedu bez původního Q losu neověřen. Nominál osm seedů zůstává, jak stanoví §7.15. Main 12+8+4+2+1=27, Q 8+4=12; BYE nejsou hrané zápasy.

### 5. Dobová pravidla

ATP §§7.03/7.04/7.08/7.09/7.10/7.15–18/7.20: pravidlové termíny, uvolnění nevyužitých SE/LE míst, pravidla vstupu náhradníků, losování čtyř kvalifikantů a lucky losers; osm nasazených v obou fázích; Q čtyři sekce po čtyřech, dva seedy v sekci; top čtyři Main BYE. Formát BO3 s tiebreakem podle ATP singles pravidel, také potvrzen dobovými výsledky. První prohra po BYE v R16 znamená 0 bodů, avšak odměnu za R16; ATP preview BUE24-2 a §7.18. Q body se přičítají dle dobového rankingového předpisu BUE24-15.

Týden 12.2. má Rotterdam ATP 500, Buenos Aires a Delray Beach ATP 250. Dobový program NextGen pro týden tří akcí se uplatňuje v rámci pevné kapacity (viz MRS24-14/15, BUE24-7/14); konkrétní alokaci této rezervy mezi Buenos Aires a Delray Beach nemáme doloženou. Nepřidávat automaticky další místo. Jde o otevřený detail pravidel, nikoli důkaz jiné draw geometry.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 97745 |
| Finalista | 1 | 165 | 57015 |
| SF | 2 | 100 | 33520 |
| QF | 4 | 50 | 19425 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 11280 |
| R32 | 12 | 0 | 6890 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3445 |
| Q1 prohra | 8 | 0 | 1880 |

Main primární původní ATP los BUE24-1 a ATP preview BUE24-2 se shodují ve všech řádcích. Q hodnoty z ročníkového archivu TennisTemple a Canal Tenis BUE24-16/17; další sekundární shoda BUE24-18, vzájemná nezávislost neprokázána. TennisTemple označuje postup jako Q3, geometrie má však pouze dvě kola. Q body 13/7/0 odpovídají ATP 2024 předpisu. Main součet 472420 USD, Q 28820 USD, nominální singlový součet 501240 USD. Originální Main draw financial commitment 728185 USD a ITF prize pool 642615 USD (BUE24-5) jsou jiné veličiny než singlový součet. P* = originální Q finanční tabulka dosud chybí, sekundární shoda je výslovně označena.

### 7. Kontrola a mezery

I/T/H/D/B doloženy; H denní okna a počty ověřeny dobovým místním rozpisem, původní kompletní Main OOP soubor nezískán. E*: ročníkový přepis listin a vizuální originální Main pavouk, nikoli originální acceptance listy, přesné časy losů neznámé. R*: NextGen alokace otevřena; P*: sekundární shoda Q odměn. Z*: vizuální kontrola celé strany originálního ATP Main draw v archivní kopii, ATP preview, Day 2 a pořadatelský Q1 OOP textově; jejich screenshoty 403/500. Původní Q draw/DS nedostupné, neuvádět hash. Nominální kontrola 28/16 hráčů, 4 BYE, 8/8 seedů, 4 postupující, 27/12 zápasů a finanční součty prošly aritmetickou kontrolou. Další ročník Rotterdam 2024, následně Delray Beach 2024. Žádný zásah do runtime.

### 8. Zdroje (BUE24)

- BUE24-1: [archiv originálního předstartovního ATP Main losu 2024](https://www.fantatennis.net/_downloads/2a1457afb7e7d6422cfe3810cb45f477), str. 1 vizuálně ověřena včetně zápatí; pozor na odlišný PDF ročníku 2025.
- BUE24-2: [ATP Preview & Day 1, 12.2.2024](https://www.atptour.com/-/media/60a7ac1ed2b64f379fc58718445638b0.pdf), str. 1–2, body, USD ceny a BYE výjimka, text, screenshot 403.
- BUE24-3: [ATP ID 506](https://www.atptour.com/en/tournaments/buenos-aires/506/overview?detailtab=pastresults), [TennisTV ročník 506_2024](https://www.tennistv.com/tournaments/506_2024/buenos-aires), [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024).
- BUE24-4: [dobový přehled losu a povrchu](https://canaltenis.com/cuadro-argentina-open-2024/); [nezávislá kontrola Main pavouka](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024Buenos_Aires).
- BUE24-5: [ITF Buenos Aires 2024](https://www.itftennis.com/en/tournament/buenos-aires/arg/2024/m-250-arg-2024-002/draws-and-results/), prize pool a termíny.
- BUE24-6: [originální pořadatelský OOP Q1](https://argentinaopentennis.com/wp-content/uploads/2024/02/OP-1.pdf), vydán 9.2. 21:26, sign-in a osm zápasů, text, screenshot 500 po redirectu.
- BUE24-7: [dobový přepis ATP entry listů týdne 12.–18.2.](https://www.tennisteen.it/entry-list/atp/24114-atp-entry-list-12-18-febbraio-2024.html), Buenos Aires Main/Q a týdenní sestava turnajů.
- BUE24-8: [předturnajový program a vstupenky Canal Tenis](https://canaltenis.com/todo-lo-que-debes-saber-del-argentina-open/), Q 10.–11., kola Main 12.–18.2.
- BUE24-9: [dobové místní termíny a rozpis všech dnů](https://www.sportingnews.com/es/tenis/news/argentina-open-2024-partidos-horarios-resultados-hoy-buenos-aires/c01a4570fb9aa72aafc83f91), místní hodiny, Q1 změna soupeře, Main 4+8 a 4+4.
- BUE24-10: [dobová zpráva o čase finále](https://www.pagina12.com.ar/713611-argentina-open-2024-a-que-hora-es-la-final-este-domingo-y-co/), 16:00 ART.
- BUE24-11: [ATP Day 2, 13.2.](https://www.atptour.com/-/media/b609c861894647bf9ebe0f1cb23318c4.pdf), text/screenshot 403; nezávislá kontrola denních Main rozpisů [12.2.](https://en.tennistemple.com/competitions/buenos-aires/2024/orderofplay/2024-02-12), [13.2.](https://en.tennistemple.com/competitions/buenos-aires/2024/orderofplay/2024-02-13), [14.2.](https://en.tennistemple.com/competitions/buenos-aires/2024/orderofplay/2024-02-14), [15.2.](https://en.tennistemple.com/competitions/buenos-aires/2024/orderofplay/2024-02-15).
- BUE24-12: [Tennis Majors archiv Main](https://www.tennismajors.com/competitions/ieb-argentina-open-2024-mens-singles), odlišné koncové datum R32 bez určení časového pásma, nepřebírat jako lokální plán.
- BUE24-13: [Tennis Explorer úplná Q struktura](https://www.tennisexplorer.com/buenos-aires/2024/atp-men/?phase=qualification), seed značky a čtyři postupy; časy nejsou prokázány jako místní.
- BUE24-14: [ATP 2024 Rulebook, 22.1.](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook_22jan.pdf), indexovaný text, přímý přístup 403; prosincová kapitola VII MRS24-16, zejména §7.08, 7.15, 7.18; NextGen viz MRS24-14/15.
- BUE24-15: [ATP předsezonní aktualizace rankingových bodů 2024](https://www.atptour.com/en/news/2024-rankings-points-update), ATP 250.
- BUE24-16: [TennisTemple Q pavouk a prize table 2024](https://en.tennistemple.com/competitions/buenos-aires/2024/draw-qualifications), 3445/1880, 13/7/0.
- BUE24-17: [Canal Tenis finanční rozpis 2024](https://canaltenis.com/el-prize-money-del-argentina-open/), oddíl výslovně 2024, nikoli aktuální ročník.
- BUE24-18: [GoTennisRacquets ročníková tabulka](https://gotennisracquets.com/argentina-open/), indexovaná shoda Q, přímý přístup selhal. [TennisCompanion](https://tenniscompanion.org/prize-money/buenos-aires/) indexovaná shoda Q2, přímý přístup 403.
- Originální ATP [Main](https://www.protennislive.com/posting/2024/506/mds.pdf), [Q](https://www.protennislive.com/posting/2024/506/qs.pdf) v tomto průchodu přímo nedostupné. Původní Main kopie BUE24-1 je vizuálně ověřená.


## Rotterdam 2024

**Stav:** HOTOVO (nominální rozsah, 9/9; H/E/Z s omezeními). První ATP 500 v registru, rešerše 2026-11-27. Vizuálně ověřeny oba originální ATP losy a předstartovní Main kopie; žádný squashový převod.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | ABN AMRO Open, 51. ročník, mužská dvouhra | ROT24-1/2/3/4 |
| Kategorie / ATP ID | ATP 500 / 407 | ROT24-1/2 |
| Dějiště | Rotterdam Ahoy, Rotterdam, Nizozemsko | ROT24-4/5 |
| Povrch | krytý tvrdý, Proflex | ROT24-1/2/3/4 |
| Časové pásmo | Europe/Amsterdam, CET UTC+01:00 | lokalita a datum |
| Ředitel | Richard Krajicek | ROT24-6 |
| ATP supervisor | Zsolt Beda / Roland Herfel | ROT24-1/2; předstartovní Main pouze Herfel |
| Referee / tour manager | Gerry Armstrong / Nicolas Rakitin | ROT24-6 |
| Měna | EUR | ROT24-1/2/3 |

Pouze ATP mužská dvouhra, nikoli wheelchair či čtyřhra. Přesný model míčů a originální detail sheet neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-01-15 | ROT24-7 |
| Q rank date | 2024-01-22 | ROT24-7 |
| Nominální Main deadline | 2024-01-15 18:00 CET (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-01-22 18:00 CET (12:00 US Eastern) | §7.03, odvozeno |
| Deadline zvláštní čtvrté Main WC | 2024-02-09 16:00 CET (10:00 US Eastern) | §7.12 A.2, odvozeno |
| Main los | 2024-02-09 19:00 CET plán; páteční večerní konání potvrzeno | ROT24-4/8 |
| Q los | před 2024-02-10; OOP zveřejněn 9.2., čas losu neznámý | ROT24-9 |
| Q | 2024-02-10–11 | ROT24-4/9/11 |
| Main | 2024-02-12–18 | ROT24-1/4 |
| Finále | 2024-02-18 15:30 CET plán | ROT24-4/12 |
| Main LL sign-in 12.2. | 12:30 CET | ROT24-6 |

Dobový přepis entry listu uvádí původní Main cutoff 54, Q 114; Main předstartovní i výsledkový ATP los uvádí poslední DA při deadline i v losu Marozsan 67, Q výsledkový los Zeppieri 133. Odlišné zdrojové hodnoty neztotožňovat bez původní acceptance listiny. Rank date není důkaz hodiny uzávěrky, která je zde pravidlovým odvozením.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-10 | 8 |
| Q2 | 2024-02-11 | 4 |
| R32 | 2024-02-12–14 | 16 |
| R16 | 2024-02-14–15 | 8 |
| QF | 2024-02-16 | 4 |
| SF | 2024-02-17 | 2 |
| F | 2024-02-18 | 1 |

Oficiální předem zveřejněný Q1 program z 9.2. má osm zápasů na dvou kurtech od 11:00 (ROT24-9). Q2 čtyři zápasy doloženy ROT24-2/11. Originální pondělní OOP vydaný 11.2. 13:42 má čtyři R32, první od 13:00. Středeční OOP vydaný 13.2. 16:34 dokládá pět R32 a tři R16; čtvrteční OOP pět R16 (ROT24-13). Tím je potvrzen plánovaný souběh kol 14.2., nikoli nahodilý odklad. Denní rozdělení R32 4+7+5 a R16 3+5 rekonstruováno z dobových OOP a výsledků ROT24-11/13. ATP středeční článek ROT24-14 uvádí nepřesný úplný součet R16 (jeden místo tří), pro denní rozpis má přednost úplný OOP a výsledkový přehled. První kompletní předturnajový denní plán nezískán. Q 2 dny, Main 7 dní, celkem 9 dní bez překryvu fází; 31+12=43 nominálních zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 |
| Základní DA při všech rezervách | 23 | 13 |
| SE rezervy | 1 | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Dobový ATP §7.08 B/E, §7.10 B a §7.12 A.2 (ROT24-15): Main 23–25 DA, 3–4 WC, 0–1 SE, 4 Q. Maximální rezervy 23+1+3+1+4=32, nevyužité SE a A+ WC přecházejí mezi DA. Entry list uvádí 23 DA, 3 WC, 4 Q, 1 SE (31 míst, mezistav, A+ rezervu neoznačuje). V předstartovním Main losu Q placeholdery 3/28/29/31, WC 4/6/27, PR 5, osm seedů, bez SE a BYE. Výsledkový originál má stejné pozice a žádnou LL. 25 DA včetně PR odpovídá uvolnění rezerv, ale konkrétní administrativní mechanismus každého hráče neodvozujeme pouze ze štítků. PR není samostatná kvóta.

Q 13 DA + 3 WC potvrzeno entry listem, předem zveřejněným programem a výslovným oznámením pořadatele 6.2. (ROT24-10). Osm seedů v předem vydaném OOP; výsledkový originál má sedm aktivních označených seedů, seed 2 Fucsovics přešel do Main a nahradil jej Llamas Ruiz [Alt]. To nemění nominální osm. Čtyři sekce po čtyřech, dvě kola, čtyři postupující, 8+4=12; Main 16+8+4+2+1=31. Skreč v QF je historická výjimka, ne změna nominálního počtu.

### 5. Dobová pravidla

ATP 500: jedna SE rezerva, dodatečná Main WC jen pro A+ hráče určeného regionem, do pátku 10:00 US Eastern, jinak místo získá další způsobilý hráč z entry listu (§7.12 A.2). SE z ATP 250 vyžaduje stejný ATP region (§7.10). Q polovina Main, u 16 Q 13 DA/3 WC; čtyři kvalifikanti dle §7.08 E, §7.13/7.15–16. Náhradníci a LL podle §7.09/7.16. BO3 s tiebreakem dle dobového ATP singles předpisu. ATP 250 LE rezerva se nepřenáší do ATP 500. Bodová výjimka pro prohru po BYE zde není relevantní. Q body se přičítají dle dobového ATP rankingového předpisu. Týden tří akcí nezvyšuje kapacitu.

Doplňková stopa pro audit NextGen: entry list ROT24-7 výslovně označuje Shang Junchenga (NG) v Main Delray Beach. Jde o doklad stavu listiny jiné akce stejného týdne, nikoli o definitivní využití ani Q alokaci. Prověřit při rešerši Delray Beach; nepřepisovat Buenos Aires ani Rotterdam jen na základě této stopy.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 399215 |
| Finalista | 1 | 330 | 214795 |
| SF | 2 | 200 | 114490 |
| QF | 4 | 100 | 58495 |
| R16 | 8 | 50 | 31225 |
| R32 | 16 | 0 | 16655 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 8535 |
| Q1 prohra | 8 | 0 | 4790 |

Všechny částky a body přímo ve spodních tabulkách originálních Main/Q losů ROT24-1/2, vizuálně ověřeny; Main shodný i v předstartovní kopii a ATP Preview ROT24-3/17. Q body 25/13/0 souhlasí s dobovým předpisem ROT24-16. Main 1593250 EUR, Q 72460 EUR, celkem 1665710 EUR nominální singlové odměny. Celkový financial commitment 2290720 EUR v originálním záhlaví a prize pool 2134985 EUR v sekundárním ročníkovém přehledu jsou jiné veličiny. Q postupující nemají samostatnou Q odměnu.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy. H*: doložena okna a dobové denní rozpisy, nikoli celý první předturnajový plán. E*: uzávěrky odvozené, Q čas losování a originální acceptance list chybí. Z*: originální výsledkové ATP Main/Q i předstartovní Main kopie vizuálně zkontrolovány (každá jedna strana); OOP, ATP Media Notes a rulebook textově, screenshot 403. DS nedostupný, SHA-256 neuvádíme. P bez hvězdičky: primární vizuální ověření obou tabulek. Aritmetika kvót, zápasů a peněz zkontrolována. Další Delray Beach 2024; runtime beze změny.

### 8. Zdroje (ROT24)

- ROT24-1: [originální ATP Main](https://www.protennislive.com/posting/2024/407/mds.pdf), str. 1 vizuálně ověřena.
- ROT24-2: [originální ATP Q](https://www.protennislive.com/posting/2024/407/qs.pdf), str. 1 vizuálně ověřena.
- ROT24-3: [archiv předstartovního ATP Main](https://www.fantatennis.net/_downloads/de657ca99fc3df1b432361c803b1361a), str. 1 vizuálně ověřena.
- ROT24-4: [ATP 2024 přehled a plán](https://www.atptour.com/en/news/rotterdam-2024-history-draw-schedule), indexovaný text, přímý přístup 403.
- ROT24-5: [ABN AMRO, 51. ročník](https://www.abnamro.com/en/news/abn-amro-open-2024-edition), celý turnaj 10.–18.2.
- ROT24-6: [originální OOP 12.2., vydán 11.2. 13:42](https://britwatchsports.com/wp-content/uploads/2021/11/ATP-Rotterdam-OOP-20240211.pdf), text, screenshot 403.
- ROT24-7: [dobový přepis acceptance listů](https://www.tennisteen.it/entry-list/atp/24114-atp-entry-list-12-18-febbraio-2024.html), Rotterdam Main/Q a NG stopa Delray.
- ROT24-8: [ATP zpráva o Main losu 9.2.](https://www.atptour.com/en/news/rotterdam-2024-draw).
- ROT24-9: [pořadatel Q1 program 9.2.](https://www.abnamro-open.nl/en/news/headlines/51th-edition/qualifying-schedule-full-of-stars), osm seedů, osm zápasů.
- ROT24-10: [pořadatel Q WC 6.2.](https://www.abnamro-open.nl/en/news/headlines/51th-edition/wildcard-qualifiers-for-brouwer-den-ouden-and-boogaard).
- ROT24-11: [Canal Tenis úplný denní přehled](https://canaltenis.com/resultados-atp-rotterdam-2024/), pouze kola a počty; [Tennis Explorer](https://www.tennisexplorer.com/rotterdam/2024/atp-men/) nezávislá kontrola.
- ROT24-12: [NOS 17.2., plán finále](https://nos.nl/artikel/2509301-griekspoor-buigt-net-als-vorig-jaar-voor-sinner-in-halve-finales-abn-amro-open).
- ROT24-13: [dobový OOP 14.2.](https://www.livetennis.it/post/406559/atp-500-rotterdam-il-programma-completo-di-mercoledi-14-febbraio-2024-in-campo-jannik-sinner-e-lorenzo-sonego/), [OOP 15.2.](https://www.livetennis.it/post/406641/atp-500-rotterdam-il-programma-completo-di-giovedi-15-febbraio-2025-in-campo-jannik-sinner-in-singolare-e-lorenzo-musetti-in-doppio/) (URL 2025, titulek i datum publikace 14.2.2024).
- ROT24-14: [ATP středeční zpráva](https://www.atptour.com/en/news/rune-safiullin-rotterdam-2024-wednesday), potvrzuje souběh, ne úplný počet.
- ROT24-15: [ATP Rulebook VII 21.12.2023](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_21dec.pdf), §7.03/7.08/7.10/7.12/7.13; text, screenshot 403. Formát BO3 viz ročníkový rulebook MPL24-7.
- ROT24-16: [ATP aktualizace bodů 2024](https://www.atptour.com/en/news/2024-rankings-points-update), ATP 500–32.
- ROT24-17: [ATP Preview & Day 1](https://www.atptour.com/-/media/2841d9bdded5444cb752004800f36cbd.pdf), str. 2 Main body/ceny, text, screenshot 403.
- ROT24-18: [sekundární ročníkový kontext a prize pool](https://en.wikipedia.org/wiki/2024_ABN_AMRO_Open); originální [DS](https://www.protennislive.com/posting/2024/407/ds.pdf) nedostupný.


## Delray Beach 2024

**Stav:** HOTOVO (nominální rozsah, 9/9; H/E/R/Z s omezeními). První doložené využití Next Gen vstupu v týdnu 12.2. v tomto registru. Rešerše 2026-11-27. Předturnajový Main los vizuálně, originální Q los v archivní kopii textově (screenshot 403). Plánované termíny nemění mimořádné přesuny zápasů.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Delray Beach Open, 32. ročník, mužská dvouhra | DLB24-1/3/4 |
| Kategorie / ATP ID | ATP 250 / 499 | DLB24-1/2/3/5 |
| Dějiště | Delray Beach Stadium & Tennis Center, 201 West Atlantic Avenue, Florida, USA | DLB24-4/6 |
| Povrch | venkovní tvrdý, Plexipave | DLB24-1/2/4 |
| Časové pásmo | America/New_York, EST UTC−05:00 | lokalita a datum |
| ATP supervisor | Nacho Forcadell | DLB24-1/2 |
| Měna | USD | DLB24-1/2/3 |

Celá pořadatelská akce 9.–18.2. zahrnovala také Legends a ženskou exhibici; pátek 9.2. není první den mužské kvalifikace ATP. Série probíhala v Coral Springs 1993–98, v Delray Beach od 1999 dle ATP notes; historické názvy/místa nepřepisovat současnou identitou. Přesný typ míčů, DS a další funkcionáři nezjištěni.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-01-15 | DLB24-7 |
| Q rank date | 2024-01-22 | DLB24-7 |
| Nominální Main deadline | 2024-01-15 12:00 EST | §7.03, odvozeno |
| Nominální Q deadline | 2024-01-22 12:00 EST | §7.03, odvozeno |
| Nominální LE deadline | 2024-02-08 10:00 EST | §7.04, odvozeno |
| Main/Q losy | před příslušnou fází; přesné časy neověřeny | DLB24-1/2 |
| Q | 2024-02-10–11, plán | DLB24-8/9 |
| Main | 2024-02-12–18, plán | DLB24-1/3/4 |
| Finále | 2024-02-18 15:00 EST, plán | DLB24-3 |
| Přeložené finále | 2024-02-19 ne před 12:30 EST | DLB24-10, historická změna |

Dobový přepis listiny DLB24-7: původní cutoff Main 71, Q 143; Main předstartovní originál uvádí Broady 98 při deadline a Lestienne 104 v losu; Q originální kopie uvádí Moreno de Alboran 147 jako last DA. Hodnoty zachovat s jejich zdrojovým označením, nejsou totožnými okamžiky. Přímý čas uzávěrek ani losovací ceremonie nepotvrzeny původní listinou.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-10 | 8 |
| Q2 | 2024-02-11 | 4 |
| R32 | 2024-02-12–13 | 12 |
| R16 | 2024-02-14–15 | 8 |
| QF | 2024-02-16 | 4 |
| SF | 2024-02-17 | 2 |
| F | 2024-02-18 | 1 |

Pořadatel 10.1. publikoval sobotní začátek Q od 10:00 EST, Q v sobotu a neděli; 23.1. znovu explicitně dvě kola 10.–11.2. a čtyři postupující. Prosincový předběžný program umístil první hrané kolo Fritz a Paul na 14./15.2.; lednová aktualizace mění Paulův čas z večera na denní session, při zachování data, a potvrzuje Tiafoeho na 15.2. (DLB24-4/8/9). ATP Preview 12.2. a dobové denní přehledy DLB24-3/11 potvrzují R32 4+8, R16 4+4, QF/SF 4/2. Jde o rekonstrukci denních počtů podle dobových rozpisů a výsledků, nikoli celý první předturnajový OOP. Jeden Q2 zápas Kokkinakis–Mochizuki je v dobových sekundárních archivech veden 12.2., ostatní tři 11.2.; důvod ani přesný lokální čas změny neověřen primárně. Nominál Q2 zůstává 11.2., nepřidávat třetí standardní Q den. Nedělní finále výslovně odloženo deštěm na pondělí 19.2. (DLB24-10), nominál neděle 18.2. se nemění. Plán 2+7 dní bez překryvu fází; 27+12=39 zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA včetně NG | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main dle dobového §7.08: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28. DLB24-7 výslovně počítá 18 DA, z toho 17 běžných podle pořadí a jeden Shang (NG); NG je zahrnutý v DA kvótě, nikoli 29. hráč. Zobrazený mezistav listiny 18+1 LE+3 WC+4 Q+0 SE=26 není konečný los; nevyužité SE rezervy se vracejí do DA. Originální předstartovní Main DLB24-1, str. 1 vizuálně: BYE 2/10/23/31, Q placeholdery 20/22/26/29, WC 12/15/19, 8 seedů. Shang na místě 30 bez zvláštního štítku; pořadatel v lednovém oznámení DLB24-12 a DLB24-9 explicitně potvrzuje NG vstup, ATP notes potvrzují účast, dobové výsledky DLB24-11 potvrzují, že nastoupil. U Tiafoeho sekundární ročníkový přehled DLB24-13 výslovně uvádí LE a pořadatel oznámil jeho dodatečný vstup již 23.1., nikoli až po Dallasu, jak naznačuje sekundární článek; přesná administrativní realizace LE doložena slaběji než NG. Neoznačovat ho jako WC (v losu bez WC štítku). V pozdějším skutečném losu se objevují LL Diallo a Cobolli, nepřičítat jako další plánované Q postupy.

Q 14 DA + 2 WC = 16 dle listiny a dobového pravidla. Originální Q kopie DLB24-2 (text) obsahuje osm seedů, dvě WC, šest Alt a čtyři sekce po čtyřech. Nominální počty nezměněny historickými náhradami. Q 8+4=12 a Main 12+8+4+2+1=27; BYE není zápas.

### 5. Dobová pravidla a Next Gen

ATP §§7.03/7.04/7.08/7.09/7.10/7.15–18/7.20 (MPL24-7, MRS24-16 a DLB24-14): termíny, SE a LE, pravidla pro náhradníky/LL, čtyři Q sekce, osm seedů v obou fázích, top čtyři Main BYE, BO3 tiebreak sety. ATP Media Notes DLB24-3 výslovně potvrzují nula bodů při prohře prvního hraného kola po BYE. Body Q dle 2024 pravidel, přičítají se k Main výsledku.

Next Gen (2024, ne novější model): ve třítur­najovém týdnu Rotterdam/Buenos Aires/Delray Beach je Main rezervace v Delray doložena pořadatelem, acceptance přepisem a skutečnou účastí Shanga; Q nominálně 14+2 a žádný další slot. Michelsen byl v počáteční Q listině na základě rankingu 91, poté v Main losu; označení mladého hráče v ATP notes není samo důkaz využití programové rezervy. Konkrétní dvě Q příležitosti, jejich výběr a případné přidělení/propad v týdnu zůstávají otevřené; nemáme důkaz, že Buenos Aires použil vlastní Main NG místo. Obecné pravidlo jednoho vyhrazeného místa pro ATP 250 ve třítur­najových týdnech neinterpretovat jako automatické přidávání míst nebo univerzální alokaci každému turnaji; DLB24-14/15. Tím je předchozí otevřená stopa ROT24-7 pro Main Delray vyřešena, nikoli celý týdenní mechanismus.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 100635 |
| Finalista | 1 | 165 | 58700 |
| SF | 2 | 100 | 34510 |
| QF | 4 | 50 | 19995 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 11610 |
| R32 | 12 | 0 | 7095 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3550 |
| Q1 prohra | 8 | 0 | 1935 |

Main primární předstartovní ATP los vizuálně a ATP notes textově (DLB24-1/3), Q primární kopie ATP losu DLB24-2 textově, nikoli pouze sekundární tabulka; screenshot Q 403. Body potvrzeny ATP ročníkovým oznámením DAL24-21. Nominální singlové součty: Main 486355 USD, Q 29680 USD, celkem 516035 USD. Financial commitment 742350 USD v originálních losech není singlová dotace. Q postupující nemají zvláštní Q peněžní odměnu. Shoda Q částek s Adelaide a dalšími ročníky není sama důkaz odměn Aucklandu; ten zůstává otevřený.

### 7. Kontrola a mezery

I/T/D/B/P doloženy; H* denní rozdělení rekonstruováno, kompletní předturnajový OOP a přesný důvod jednotlivého Q posunu neověřeny; E* uzávěrky odvozené, originální acceptance list a časy losování nezískány; R* Next Gen Main doložen, Q alokace stále otevřena; Z* Main původní předstartovní kopie vizuálně ověřena, Q a ATP notes textově (403 při screenshotu), přímé originály/DS nedostupné. Nevymýšlet PDF hash. Kontrola kvót, slotů, zápasů a odměn prošla. Další pořadí Rio de Janeiro, Doha, Los Cabos 2024 podle ATP archivu DLB24-16; žádný zásah do engine.

### 8. Zdroje (DLB24)

- DLB24-1: [archiv původního ATP předstartovního Main losu](https://www.raquetc.com/wp-content/uploads/2024/02/ATP-250-Delray-Beach-2024-quadro-singulares.pdf), str. 1 vizuálně zkontrolována.
- DLB24-2: [archiv původního ATP Q losu](https://britwatchsports.com/wp-content/uploads/2021/11/ATP-Delray-Beach-QS-20240211.pdf), text (16 pozic, 8 seedů, odměny 3550/1935); screenshot 403. Datum v názvu souboru není důkaz doby dokončení všech zápasů.
- DLB24-3: [ATP Preview & Day 1, 12.2.2024](https://www.atptour.com/-/media/ce938d7699d5422cad4894f597885392.pdf), tištěná str. 2, text; screenshot 403.
- DLB24-4: [pořadatel 21.12.2023](https://www.delraybeachopen.com/en/tournament/news/schedule-released-for-top-players), předběžný Main a původní session plán, venkovní tvrdý povrch.
- DLB24-5: [oficiální archiv losů pořadatele](https://www.delraybeachopen.com/en/tournament/past-draws), řádek 2024; originální [Main](https://www.protennislive.com/posting/2024/499/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/499/qs.pdf) přímým otevřením nedostupné.
- DLB24-6: [město Delray Beach, místo a termíny 2024](https://www.delraybeachfl.gov/Home/Components/News/News/743/395).
- DLB24-7: [dobový přepis ATP acceptance listů](https://www.tennisteen.it/entry-list/atp/24114-atp-entry-list-12-18-febbraio-2024.html), řádky 164–214, Main/Q, 17 běžných DA + Shang NG pod hlavičkou 18.
- DLB24-8: [pořadatel 10.1.2024, opening weekend](https://www.delraybeachopen.com/en/tournament/news/fritz-and-paul-rankings-race), sobota 10:00 a neděle Q.
- DLB24-9: [pořadatel 23.1.2024, Q field a Tiafoe](https://www.delraybeachopen.com/en/tournament/news/tiafoe-player-announcement), explicitní Q 10.–11.2., čtyři postupy, NG Shang, posun Paulovy session.
- DLB24-10: [pořadatel 18.2., odklad finále deštěm](https://www.delraybeachopen.com/en/tournament/news/delray-beach-2024-final-postponed), pondělí 19.2. ne před 12:30.
- DLB24-11: [Canal Tenis dobový denní přehled](https://canaltenis.com/resultados-atp-delray-beach-2024/), počty a kalendář; [TennisTemple 12.2.](https://it.tennistemple.com/competitions/delray-beach/2024/orderofplay/2024-02-12), [15.2.](https://en.tennistemple.com/competitions/delray-beach/2024/orderofplay/2024-02-15) nezávislá kontrola; [Tennis Abstract Main](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024Delray_Beach). U přesahů do dalšího dne nekopírovat neoznačené timezone; sekundární [Q přehled](https://www.livefootball365.com/Tennis/USA/Delray-Beach-Open-Qualification/65250) podporuje datum Q2 posunu, ne důvod.
- DLB24-12: [pořadatel původní Main list](https://www.delraybeachopen.com/en/tournament/news/player-field-announcement), výslovně Shang Next Gen vstup, [USTA nezávislé zrcadlo](https://www.usta.com/en/home/stay-current/florida/2024-delray-beach-open-early-entry-list-revealed.html).
- DLB24-13: [dobový sekundární Main přehled](https://canaltenis.com/cuadro-atp-delray-beach-2024/), Tiafoe LE, nepřebírat jeho časové vysvětlení v rozporu s pořadatelem; [ročníkový soupis](https://en.wikipedia.org/wiki/2024_Delray_Beach_Open).
- DLB24-14: [ATP Rulebook VII 2.7.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_02jul.pdf), §7.08 B, str. 147, text, screenshot 403; lednová verze MPL24-7 / MRS24-16 pro dobový základ, nikoli automatická retroaktivita pozdější revize.
- DLB24-15: [ATP oznámení Next Gen programu 20.12.2023](https://www.atptour.com/en/news/next-gen-atp-brand-expansion-2024), příležitosti od roku 2024.
- DLB24-16: [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), další Rio, Doha, Los Cabos.


## Rio de Janeiro 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/Z s omezeními). Druhý ATP 500 v registru; první ATP 500 na antuce. Rešerše 2026-11-27. Oba originální ATP losy i předstartovní Main kopie vizuálně zkontrolovány. Oficiální program pořadatele má přednost před deštěm změněnými skutečnými výsledky.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Rio Open presented by Claro, 10. ročník, mužská dvouhra | RIO24-1/2/4/5 |
| Kategorie / ATP ID | ATP 500 / 6932 | RIO24-1/2/4 |
| Dějiště Main i Q | Jockey Club Brasileiro, Rio de Janeiro, Brazílie | RIO24-4/5/6 |
| Povrch | venkovní červená antuka | RIO24-1/2/4 |
| Časové pásmo | America/Sao_Paulo, BRT UTC−03:00 v únoru 2024 | lokalita a datum |
| Ředitel | Luiz Procopio Carvalho | RIO24-4 |
| ATP supervisors | Carlos Sanches / Jorge Mandl | RIO24-1/2/3 |
| Měna | USD | RIO24-1/2/4 |

Míče, původní ATP detail sheet a referee neověřeny. Čtyřhra jen kontext, nikoli součást singlového součtu.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-01-22 | RIO24-7 |
| Q rank date | 2024-01-29 | RIO24-7 |
| Nominální Main deadline | 2024-01-22 14:00 BRT (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-01-29 14:00 BRT (12:00 US Eastern) | §7.03, odvozeno |
| Podmíněná A+ WC deadline | 2024-02-16 12:00 BRT (10:00 US Eastern) | §7.12 A.2, odvozeno |
| Main los | 2024-02-17 14:30 BRT (publikovaný plán) | RIO24-4 |
| Q los | nejpozději 2024-02-16, kdy pořadatel zveřejnil páry; přesný čas neověřen | RIO24-8 |
| Q | 2024-02-17–18 od 16:00 | RIO24-4/6/8/9 |
| Main | 2024-02-19–25 | RIO24-1/4/9 |
| Finále | 2024-02-25 17:30 BRT (plán) | RIO24-4/9 |

Dobový přepis listin RIO24-7 uvádí původní cutoffs 85 Main / 145 Q. Předstartovní Main los RIO24-3 uvádí Diaz Acosta 90 při deadline a Dellien 105 v losu; výsledkový Main RIO24-1 nechává obě pole prázdná. Originální Q los uvádí Pellegrino 163 jako last DA. Zachovat rozdílné zdrojové údaje bez ztotožnění a bez dopočítávání chybějících polí. Uzávěrky jsou pravidlovým odvozením; originální acceptance list PDF ani hodina Q losu nedohledány.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-17 | 8 |
| Q2 | 2024-02-18 | 4 |
| R32 | 2024-02-19–20 | 16 |
| R16 | 2024-02-21–22 | 8 |
| QF | 2024-02-23 | 4 |
| SF | 2024-02-24 | 2 |
| F | 2024-02-25 | 1 |

Oficiální pořadatelská Revista Rio Open 2024 (RIO24-9, PROGRAMAÇÃO) výslovně stanoví uvedená okna. Q na všech kurtech od 16:00, po–čt první session 16:30 a večer od 19:00; QF jeden na kurtu 1 od 16:00 a tři na centru od 16:30; SF od 17:00, F 17:30. Po–čt nelze odvodit celkové počty pouze z centrálního kurtu. Q1 předstartovní seznam obsahuje všech osm dvojic a všech osm seedů (RIO24-8). Oficiální OOP 19.2. vydaný 18.2. má sedm R32 (3+2+2 na třech kurtech); OOP 20.2. vydaný 19.2. má devět R32 (3+2+2+2 na čtyřech kurtech); součet 16. Denní plán R32 tedy doložen 7+9, nikoli odhad 8+8. Pořadatelský OOP 21.2. již po úterním dešti zahrnoval jeden přesunutý R32 a čtyři R16. Původní denní rozdělení osmi R16 bez vlivu deště není nezávisle doloženo, zachovat okno 21.–22.2., neprohlašovat 4+4 za původní přesný plán. Dne 21.2. další déšť způsobil přesun tří singlových R16 (jedno rozehrané) a jednoho doubles utkání na 22.2.; počty a okna nominálu se nemění. Q 2 dny, Main 7 dní, celkem 9 dní bez plánovaného překryvu fází ani Main kol. 31+12=43 zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 |
| Základní DA při všech rezervách | 23 | 13 |
| SE rezervy | 1 | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Na rozdíl od pouhého obecného odvození z pravidel ATP je zde i přímý ročníkový důkaz všech Main kvót: pořadatel 5.2. výslovně popisuje 23 DA + 3 WC + 1 A+ WC + 4 Q + 1 SE a převod nepoužitých A+/SE na DA (RIO24-5). Dobový přepis RIO24-7 uvádí 23 DA, 3 WC, 4 Q, 0 SE, což je neúplný stav listiny, nikoli konečná kapacita. Předstartovní originál RIO24-3: Q placeholdery 3/7/10/22; WC 2/18/29; osm seedů, žádné BYE. Finální originál potvrzuje stejné čtyři Q pozice a tři WC, bez LL nebo SE značek. 25 ostatních míst odpovídá uvolnění rezerv, individuální administrativní cestu nezjišťujeme pouze ze štítku. Cilic měl v počáteční listině PR, ne extra kapacitu, v předstartovním losu již nebyl.

Q 13 DA + 3 WC dle RIO24-7, standardu ATP 500 a předem vydaného Q programu RIO24-8. Výsledkový originál RIO24-2 vizuálně potvrzuje tři WC na pozicích 6/14/15, dvě Alt a sedm aktivních seedů; seed 6 Barrios Vera a Dellien přešli do Main, jejich místa obsadili náhradníci. Osm nominálních seedů zachovat podle původního Q programu. Dřívější mediální oznámení WC RIO24-14 zahrnovalo i Meligeniho, který ve finálním Q originálu WC štítek nemá; původní oznámení není konečný vstupní status. Čtyři Q sekce po čtyřech, každý vítěz postoupí dvěma zápasy; Q 8+4=12, Main 16+8+4+2+1=31. Skreče nemění nominální počet.

### 5. Dobová pravidla

ATP 500 §7.08 B/E, §7.10 B a §7.12 A.2: jedna SE rezerva, tři běžné WC, podmíněná A+ WC s páteční uzávěrkou; nevyužité rezervy se vracejí do DA. SE z ATP 250 pro ATP 500 omezen stejným ATP regionem. §7.13/7.15–16: osm seedů v Main i Q, čtyři kvalifikanti; pravidla Alt a LL podle §7.09/7.16. BO3 s tiebreakem dle dobového ATP singles předpisu (MPL24-7, ROT24-15). Bodové pravidlo pro prohru po BYE není relevantní, protože pavouk nemá BYE. Q body dle ATP 2024 rankingové aktualizace ROT24-16.

Týden 19.2. zahrnuje také ATP 250 Doha a Los Cabos. Pořadatelský Main seznam označuje Fonsecu jako WC a Filse jako řádnou přímou akceptaci, byť je oba mediálně možné označit jako mladé hráče; nejde o doklad programového NG vstupu. Dobový týdenní přepis RIO24-7 již uvádí Menšíka jako NG v rámci 18 DA Doha (17 ostatních); spolu s MRS24-15 je to silná stopa pro příští ročník, nikoli nové místo v Rio nebo potvrzení konkrétních Q rezerv.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 392775 |
| Finalista | 1 | 330 | 211330 |
| SF | 2 | 200 | 112625 |
| QF | 4 | 100 | 57540 |
| R16 | 8 | 50 | 30715 |
| R32 | 16 | 0 | 16380 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 8395 |
| Q1 prohra | 8 | 0 | 4710 |

Main i Q primární vizuálně ověřené tabulky RIO24-1/2, Main shoda s předstartovním losem RIO24-3 a ATP preview u pořadatele RIO24-4. Nominální Main 1567315 USD, Q 71260 USD, součet 1638575 USD. Celková turnajová dotace 2100230 USD a total financial commitment 2271715 USD jsou jiné veličiny (RIO24-4); neztotožňovat se singlovým součtem. Q postupující obdrží 25 bodů a samostatně 0 USD, peníze podle Main výsledku.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy včetně explicitních ročníkových Main rezerv a tří Q WC. H*: předturnajový plán kol oficiálně, R32 7+9 ověřeno v předem vydaných OOP; původní R16 denní dělení neověřeno, dešťové přesuny nepromítnuty do nominálu. E*: Main čas losu doložen plánem, Q čas neznámý, uzávěrky odvozené; originální acceptance list/DS nezískány. Z*: originální Main/Q i předstartovní Main kopie vizuálně zkontrolovány, Revista program textově, screenshot odmítnut kvůli velikosti 18,6 MB. PDF hashe neověřeny. Aritmetická kontrola kvót, zápasů, peněz a součtu R32 prošla. Následující Doha 2024; Los Cabos poté. Žádný zásah do runtime.

### 8. Zdroje (RIO24)

- RIO24-1: [originální ATP Main los](https://www.protennislive.com/posting/2024/6932/mds.pdf), str. 1 vizuálně ověřena.
- RIO24-2: [originální ATP Q los](https://www.protennislive.com/posting/2024/6932/qs.pdf), str. 1 vizuálně ověřena včetně bodů a peněz.
- RIO24-3: [archiv předstartovního ATP Main losu](https://www.fantatennis.net/_downloads/05df4c56adf4a0efda3077262cebdb08), str. 1 vizuálně ověřena, cutoffs a Q placeholdery.
- RIO24-4: [ATP předturnajový přehled 15.2.](https://www.atptour.com/en/news/rio-de-janeiro-2024-history-draw-schedule), [stejný článek u pořadatele](https://www.rioopen.com/en/noticias/news/rio-de-janeiro-2024-history-draw-schedule), termíny, Main los, session, body/peníze, ředitel; nejde o dva nezávislé zdroje.
- RIO24-5: [pořadatelský Main entry list 5.2.](https://www.rioopen.com/en/noticias/news/rio-open-2024-entry-list-features-alcaraz-norrie-fils-wawrinka-and-cilic), explicitní 23 DA + 3 WC + A+ WC + 4 Q + SE.
- RIO24-6: [pořadatel Q entry list 30.1.](https://www.rioopen.com/pt-br/noticias/news/quali-2024), Q dny a dva zápasy na postup.
- RIO24-7: [dobový přepis entry listů týdne 19.–25.2.](https://www.tennisteen.it/entry-list/atp/24123-atp-entry-list-19-25-febbraio-2024.html), Rio Main/Q, Doha NG stopa, Los Cabos.
- RIO24-8: [pořadatel Q los a Q1 program 16.2.](https://www.rioopen.com/en/noticias/news/qualifying-gets-underway-in-rio), všech osm předstartovních seedů a tři WC.
- RIO24-9: [oficiální Revista Rio Open 2024](https://www.rioopen.com/-/media/sites/tournaments/rio/revista-programa/revista_rio_open_fev2024_site.pdf), oddíl PROGRAMAÇÃO, celý nominální rozpis kol, text, screenshot neúspěšný (příliš velký soubor).
- RIO24-10: [pořadatel OOP 19.2. vydaný 18.2.](https://www.rioopen.com/en/noticias/news/norrie-begins-his-tittle-defense-this-monday), 7 R32.
- RIO24-11: [pořadatel OOP 20.2. vydaný 19.2.](https://www.rioopen.com/en/noticias/news/alcaraz-wawrinka-and-fils-in-action-this-tuesday), 9 R32.
- RIO24-12: [pořadatel úterní déšť](https://www.rioopen.com/en/noticias/news/diaz-acosta-wawrinka-rio-de-janeiro-2024-tuesday), [středeční aktualizovaný OOP](https://www.rioopen.com/en/noticias/news/norrie-back-in-action-at-jockey-this-wednesday), [odklad středečních zápasů](https://www.rioopen.com/en/noticias/news/rain-cancels-four-matches-on-wednesday-night).
- RIO24-13: [Ge dobový program](https://ge.globo.com/tenis/rio-open/noticia/2024/02/19/rio-open-2024-onde-assistir-ao-vivo-e-programacao.ghtml), nezávislé potvrzení plánovaných oken; [dobový denní archiv](https://canaltenis.com/resultados-atp-rio-open-2024/) pouze jako výsledková kontrola, chybná závěrečná data v úvodu nepřebírat.
- RIO24-14: [Ge 14.2., oznámení WC](https://ge.globo.com/tenis/rio-open/noticia/2024/02/14/rio-open-distribui-convites-para-mais-quatro-tenistas-brasileiros.ghtml), historické oznámení před definitivním losem.
- Pravidla viz ROT24-15/16 a MPL24-7; originální DS a acceptance list PDF nedohledány.


## Doha 2024

**Stav:** HOTOVO (nominální rozsah, 9/9; H/E/R/Z s označenými omezeními). Rešerše 2026-11-27. Oba výsledkové ATP losy vizuálně zkontrolovány v kopii turnajového moderátora, rovněž předstartovní Main los. Šestidenní Main se sobotním finále je plánovaná vlastnost ročníku, nikoli výjimka způsobená počasím.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Qatar ExxonMobil Open, 32. ročník, mužská dvouhra | DOH24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 451 | DOH24-1/4 |
| Dějiště | Khalifa International Tennis and Squash Complex, Doha, Katar | DOH24-3/5/6 |
| Povrch | venkovní tvrdý, Plexicushion Prestige | DOH24-1/2/4 |
| Časové pásmo | Asia/Qatar, UTC+03:00 | lokalita a datum |
| Ředitel | Karim Alami | DOH24-7 |
| Supervisor / referee / tour manager | Roland Herfel / Ashraf Hamouda / Diego Pedraza | DOH24-7 |
| Měna | USD | DOH24-1/2/3 |

Pořadatel oznámil 28.1.2024 zvýšení kategorie až od 2025 (DOH24-8). Ročník 2024 zůstává ATP 250, nezaměňovat s paralelní WTA akcí 11.–17.2. ani současnou kategorií. Míče a detail sheet neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-01-22 | DOH24-9 |
| Q rank date | 2024-01-29 | DOH24-9 |
| Nominální Main deadline | 2024-01-22 20:00 (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-01-29 20:00 (12:00 US Eastern) | §7.03, odvozeno |
| Nominální LE deadline | 2024-02-15 18:00 (10:00 US Eastern) | §7.04 dle lednové verze, odvozeno |
| Main los | 2024-02-17, přesná hodina neověřena | DOH24-10 |
| Q los | nejpozději 2024-02-17 před Q1, čas neověřen | DOH24-2/5 |
| Q | 2024-02-17–18 | DOH24-2/5 |
| Main | 2024-02-19–24 | DOH24-1/3/6/11 |
| Finále | 2024-02-24 18:00 místně, plán | DOH24-3, str. 1 |

Dobový přepis acceptance listů uvádí původní cutoff 54 Main / 114 Q. Předstartovní i výsledkový Main originál uvádí Fucsovics 70 při deadline i v losu; výsledkový Q originál Zhukayev 189 jako last DA. Hodnoty se liší, původní listiny neobdrženy; rank date a pravidlově odvozená uzávěrka nejsou totéž co potvrzený okamžik přijetí. Zpráva QNA o Main losu 17.2. dostupná pouze v indexu, otevření 500.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-17 | 8 |
| Q2 | 2024-02-18 | 4 |
| R32 | 2024-02-19–20 | 12 |
| R16 | 2024-02-21 | 8 |
| QF | 2024-02-22 | 4 |
| SF | 2024-02-23 | 2 |
| F | 2024-02-24 | 1 |

Dobový kalendář ATP 18.12.2023 výslovně značí Doha poznámkou 8 = Saturday final (DOH24-11). Turnajový moderátor ve svém přehledu DOH24-5 uvádí dvoudenní Q, R32 pondělí/úterý, všech osm R16 ve středu a po jednom kole až do soboty. Ve stejném přehledu je chybný popis finále čtyřhry v pátek; ATP notes uvádějí sobotu, což se však netýká mužské dvouhry. Výsledkový denní soupis DOH24-2, str. 1/3, vizuálně potvrzuje R32 5+7, všech osm R16 v jediný den, QF/SF/F 4/2/1 a Q1/Q2 8/4. Denní R32 dělení je pozorovaná rekonstrukce, nikoli získaný původní kompletní předturnajový OOP. OOP 23.2. (DOH24-7, text) potvrzuje SF; ATP Day 1 plánuje finále 18:00. Sekundární ITF metadata do 25.2. nepoužívat jako závazný plán proti ATP kalendáři, originálním losům a předturnajovým notes. Q 2 dny, Main 6 dní, celé okno 8 dní bez překryvu; 27+12=39 nominálních zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA včetně NG | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Standard §7.08 B: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28 (DOH24-12). Přepis DOH24-9 zahrnuje 17 běžných DA a Menšíka NG pod hlavičkou 18 DA, dále 3 WC, 4 Q, 0 SE, 0 LE a 1 emergency substitution (mezistav 26). Nouzová náhrada není další místo navíc. Předstartovní Main DOH24-1: BYE 2/10/23/31, Q placeholdery 5/18/27/30, WC 4/13/20, osm seedů, Menšík bez WC značky na pozici 7. Výsledkový originál v DOH24-2 str. 2: Griekspoor na 17 nahrazen Martererem LL před prvním zápasem; tím nevzniká pátý plánovaný kvalifikant. Main 12+8+4+2+1=27. Skreč v QF nemění geometrii.

Q 14 DA + 2 WC potvrzují listina a dobový předpis, dvě WC na pozicích 11/15 přímo výsledkový ATP Q los DOH24-2 str. 4. Los označuje Fogniniho současně seed 4 a Alt; skutečná náhrada, nikoli změna nominálního počtu seedů. Osm seedů, čtyři sekce po čtyřech, 8+4=12 zápasů, čtyři postupující. BO3 dle ATP singles pravidel, potvrzeno také formátem výsledkových pavouků.

### 5. Dobová pravidla, NG a nouzová náhrada

Dobový rulebook §7.03/7.04/7.08/7.09/7.10/7.15–18/7.20 (MPL24-7, DOH24-12) pro ATP 250: SE/LE nevyužité rezervy přejdou do běžných vstupů, čtyři Q sekce, pravidla Alt a LL, top čtyři Main BYE. ATP Preview přímo potvrzuje nulové body při první prohře po BYE v R16, nikoli zrušení R16 peněžní odměny. Q body 13/7/0 se přičítají dle rankingového předpisu.

**Next Gen:** přepis listiny DOH24-9 přímo identifikuje Menšíka v 18 DA. ATP dobové zprávy DOH24-13 výslovně potvrzují využití programu Next Gen Accelerator a postup do finále. ATP v publicistickém textu používá i označení programová WC, ale los nemá WC značku a tři běžné WC jsou obsazené jinými hráči; programový vstup tedy nepočítat jako čtvrtou pořadatelskou WC ani jako 29. místo. Rozlišovat programové pojmenování a skutečnou účetní kapacitu listiny. Dvě Q příležitosti v týdnu Rio/Doha/Los Cabos a jejich přidělení dosud neprokázány.

**Emergency substitution (ES, nikoli SE):** přepis DOH24-9 uvádí jedno ES a Bautistu Aguta s označením ES na seznamu náhradníků. Dobový §7.03 A.7 v ročníkovém ATP předpisu (DOH24-12, tištěné str. 134–135) stanoví podmíněnou jednu substituci v ATP 250 při odstoupení dvou z původních top 4, z toho alespoň jednoho z prvních dvou; kvalifikační kritéria náhradníka zahrnují např. bývalého vítěze turnaje či top 20 za posledních pět let a aktuální top 500. Časové okno je týden před akcí od pondělí do páteční 10:00 US Eastern, se zvláštním prodloužením při druhém odstoupení v poslední hodině. Předpis řeší i odměnu vytlačeného způsobilého DA v určitých případech. Nemění se počet hráčů ani tři pořadatelské WC. Původní listina měla v top 4 Medveděva a Nadala, oba odstoupili v týdnu před akcí (DOH24-2/9); Bautista Agut je bývalý vítěz a nastoupil, v Main losu bez zvláštní značky. Jde o silnou ročníkovou shodu s mechanismem, nikoli získaný originální administrativní doklad schválení ES či kompenzace vytlačenému hráči. Sekundární listina 16.2. uvádí pole ES bez jména (DOH24-14); nepřidávat hypotetickou kompenzaci k nominálním singlovým odměnám. R* označuje tuto evidenční mez, ne jinou kapacitu.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 212300 |
| Finalista | 1 | 165 | 123840 |
| SF | 2 | 100 | 72810 |
| QF | 4 | 50 | 42190 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 24500 |
| R32 | 12 | 0 | 14970 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 7485 |
| Q1 prohra | 8 | 0 | 4085 |

Main předstartovní a výsledkový ATP los vizuálně shodné (DOH24-1/2), Q finanční tabulka vizuálně na str. 4 DOH24-2. ATP Preview (DOH24-3) nezávisle potvrzuje Main a BYE výjimku; sekundární dobová Main tabulka DOH24-15 souhlasí. Main 1026160 USD, Q 62620 USD, celkem 1088780 USD nominální singlové odměny. Financial commitment 1493465 USD přímo v originálních losech; sekundární celková turnajová dotace 1395875 USD (DOH24-15), obojí odlišné od singlového součtu. P bez hvězdičky, oba primární losy vizuálně ověřeny.

### 7. Kontrola a mezery

I/T/D/B/P doloženy, H* přesné R32 denní rozdělení pouze výsledkově, nikoli kompletním předturnajovým OOP; E* uzávěrky odvozené, Main datum losu indexovanou zprávou, přesné hodiny a originální acceptance list/DS chybí; R* ES administrativní doklad/kompenzace a Q NextGen otevřeny; Z* předstartovní Main a všechny čtyři stránky archivu DOH24-2 vizuálně zkontrolovány, rovněž ATP notes str. 2 (str. 1 screenshot 403, text dostupný). OOP screenshot 404, rulebook ITF zrcadlo screenshot 500, kalendář ATP screenshot 403. Žádné nové PDF hashe. Kontrola 28/16, 8/8 seedů, 27/12 zápasů, kvót, součtů a finančních tabulek. Další Los Cabos 2024; následně Acapulco, Dubai, Santiago (DOH24-11). Bez runtime změn.

### 8. Zdroje (DOH24)

- DOH24-1: [archiv původního předstartovního ATP Main losu](https://www.fantatennis.net/_downloads/96f505ce4fc6c31efb2ecec73dfc0103), str. 1 vizuálně.
- DOH24-2: [turnajový moderátor Andy Taylor, Complete Singles Results](https://andytayloronline.com/wp-content/uploads/2024/02/Announcer-Andy-Taylor.-2024-Qatar-ExxonMobil-Open.-Complete-Singles-Results.pdf), str. 1 denní Main, str. 2 původní výsledkový ATP Main, str. 3 denní Q, str. 4 původní výsledkový ATP Q; všechny čtyři stránky vizuálně. Datum v indexu neztotožňovat s datem vzniku originálních losů.
- DOH24-3: [ATP Preview & Day 1, 19.2.2024](https://www.atptour.com/-/media/138c37515f254bd3a2233a4c82a896c1.pdf), str. 1 singlové finále, WC, body/ceny a BYE; str. 2 vizuálně, str. 1 text/screenshot 403.
- DOH24-4: [ATP identita série 451](https://www.atptour.com/en/tournaments/doha/451/overview), [TennisTV ročník 451_2024](https://www.tennistv.com/tournaments/451_2024/doha).
- DOH24-5: [turnajový moderátor, ročníkový přehled](https://andytayloronline.com/announcer-services/doha/2024-qatar-exxonmobil-open/), struktura a singlová okna; [Q denní PDF](https://andytayloronline.com/wp-content/uploads/2024/02/Announcer-Andy-Taylor.-2024-Qatar-ExxonMobil-Open.-Qualifying-Results.pdf) vizuálně, stejný autor jako DOH24-2.
- DOH24-6: [Qatar Olympic Committee předturnajový článek](https://www.olympic.qa/media-center/five-past-champions-challenging-quest-qatar-exxonmobil-open-title), místo a sobotní finále.
- DOH24-7: [archiv originálního OOP SF, vydán 22.2. 21:21](https://assets-eu-01.kc-usercontent.com/0d576561-b074-01c9-c2d3-ad66a4d46ec6/a477319e-7813-4fce-bf9d-1e1820d6753a/OP.pdf), text, screenshot 404.
- DOH24-8: [pořadatel oznámení ATP 500 od 2025, 28.1.2024](https://www.qatartennis.org/articles/qatar-exxonmobil-open-from-atp250-to-atp500).
- DOH24-9: [dobový přepis entry listů](https://www.tennisteen.it/entry-list/atp/24123-atp-entry-list-19-25-febbraio-2024.html), řádky 181–238.
- DOH24-10: [Qatar News Agency, los 17.2.](https://qna.org.qa/en/news/news-details?date=17%2F02%2F2024&id=0029-qatar-exxonmobil-open-2024-draw-held), indexovaný text, otevření 500.
- DOH24-11: [ATP kalendář 18.12.2023](https://www.atptour.com/-/media/files/calendar-pdfs/2024/2024-atp-challenger-calendar-as-of-18-december-2023.pdf), únorový řádek a poznámka 8, text/screenshot 403; [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024). [ITF metadata](https://www.itftennis.com/en/tournament/doha/qat/2024/m-250-qat-2024-001/draws-and-results/) uvádějí konec 25.2., přednost ATP.
- DOH24-12: [ATP Rulebook 2024, ITF zrcadlo](https://www.itftennis.com/media/11845/2024-rulebook-atp-update.pdf?embed=true), §7.03 A.7 str. 134–135, §7.08 B/E str. 146–150, §7.04 a NG; text, screenshot 500; dobová lednová verze MPL24-7, prosincová kapitola MRS24-16 nedostupná přímo 403. Změny ročníkové revize nepřenášet mechanicky zpět.
- DOH24-13: [ATP 20.2.2024, NG vstup](https://www.atptour.com/en/news/mensik-davidovich-fokina-doha-2024-tuesday), [ATP 22.2., NG Accelerator](https://www.atptour.com/en/news/mensik-rublev-doha-2024-thursday), [ATP retrospektiva 2025](https://www.atptour.com/en/news/next-gen-accelerator-pathway-expansion-february-2025); indexované texty, článek 22.2. přímé otevření 403.
- DOH24-14: [dobová aktualizace listiny 16.2.](https://tennisuptodate.com/atp/atp-entry-list-2024-qatar-open-including-andrey-rublev-karen-khachanov-and-ugo-humbert-update-16-02), pole ES, odstoupení, v úvodu chybně 25.2. konec; nepřebírat.
- DOH24-15: [dobový Main finanční rozpis](https://tennis-infinity.com/atp/2024-qatar-open-doha-atp-prize-money-points-overview), shoda Main, celková dotace; [SteveGtennis](https://www.stevegtennis.com/draw-results/atp/Qatar%20ExxonMobil%20Open%20-%20Doha/2024) shoda Q částek, chybné A$ označení, původní USD los má přednost.
- Přímé originální ATP [Main](https://www.protennislive.com/posting/2024/451/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/451/qs.pdf) nedostupné; dochované kopie DOH24-1/2 zkontrolovány.


## Los Cabos 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/R/P/Z s označenými omezeními). Rešerše 2026-11-27. Tři verze původního ATP Main losu a dva originální OOP vizuálně ověřeny. Kvalifikační finanční tabulka má pouze sekundární shodu, nikoli získaný originál.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Mifel Tennis Open by Telcel Oppo, 8. ročník, mužská dvouhra | LCB24-1/4/5 |
| Kategorie / ATP ID | ATP 250 / 7480 | LCB24-1/4/15 |
| Dějiště | Cabo Sports Complex, turistický koridor San José del Cabo–Cabo San Lucas, Baja California Sur, Mexiko | LCB24-4/6/13 |
| Povrch | venkovní tvrdý, Solflex | LCB24-1/2/3/13 |
| Časové pásmo | America/Mazatlan, UTC−07:00 v únoru | LCB24-16 |
| Ředitel | José Antonio Fernández (Geoffrey) | LCB24-7/8 |
| Supervisor / referee / tour manager | Jaime Chavez / Ricardo Reis / Arnau Brugues | LCB24-7/8 |
| Měna | USD | LCB24-1/4 |

ATP oznámila změnu z červencového termínu na únor už v kalendáři 2024 (LCB24-14). Ročník je plánovanou změnou, nikoli odloženým letním turnajem. Následuje týden před Acapulcem, nikoli souběžně s ním. Přesný model míčů a detail sheet neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Zdroj |
|---|---|---|
| Main rank date | 2024-01-22 | LCB24-9 |
| Q rank date | 2024-01-29 | LCB24-9 |
| Nominální Main deadline | 2024-01-22 10:00 (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-01-29 10:00 (12:00 US Eastern) | §7.03, odvozeno |
| Nominální LE deadline | 2024-02-15 08:00 (10:00 US Eastern) | §7.04, odvozeno |
| Main los | 2024-02-17, hodina neověřena | LCB24-5 |
| Q los | nejpozději 2024-02-17 před Q1, hodina neověřena | LCB24-10 |
| Q | 2024-02-17–18, od 16:00 | LCB24-5/6/10/11 |
| Main | 2024-02-19–24 | LCB24-1/4/5/6 |
| Main LL sign-in 20.2. | 15:30 místně | LCB24-7 |
| Finále | 2024-02-24 20:00 místně | LCB24-6/8 |

Rank date a pravidlově odvozený deadline nejsou nezávislým potvrzením hodiny uzávěrky. Přepis listiny LCB24-9 uvádí původní cutoffs 62 Main a 132 Q. Pořadatelský předstartovní Main PDF má obě cutoff pole prázdná, archivní kopie stejného pavouka uvádí Koepfer 62 při deadline a Kokkinakis 80 v losu. Verze před finále 24.2. má Koepfer 62 a Lestienne 99. Jde o různé verze; Q cutoff v konečném losu neověřen.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-17 | 8 |
| Q2 | 2024-02-18 | 4 |
| R32 | 2024-02-19–20 | 12 |
| R16 | 2024-02-21 | 8 |
| QF | 2024-02-22 | 4 |
| SF | 2024-02-23 | 2 |
| F | 2024-02-24 | 1 |

Pořadatelský program LCB24-6 uvádí R32 ve dvou dnech od 16:00, R16 ve středu od 16:00, QF čtvrtek od 15:00, SF pátek od 19:00 a singlové finále od 20:00. Dvě chyby v kalendářním textu (druhá kvalifikační neděle označená 25.2., finálový 24.2. označený nedělí) jsou opraveny podle dobových datovaných oznámení pořadatele LCB24-5/10/11 a originálního sobotního OOP LCB24-8; 24.2.2024 je sobota. Q1/Q2 potvrzeny pořadatelem 8/4. Originální OOP 20.2. vydaný 19.2. 18:12 vizuálně potvrzuje sedm R32; výsledkový přehled LCB24-13 potvrzuje pět R32 19.2. a sedm 20.2., osm R16 21.2., 4/2/1 v dalších kolech. Pondělní původní OOP nedostupný, jeho pět R32 je doloženo výsledkově, nikoli samostatným předstartovním OOP. Časy sekundárních zahraničních archivů mohou přesahovat do následujícího civilního dne; např. LCB24-13 uvádí finále pod 25.2., ale místní sobotní plán 24.2. 20:00 je přímo potvrzen. Původní singlové okno 8 dní, Q 2 + Main 6, žádný plánovaný překryv; 39 zápasů. Čtyřhrové změny programu nemění singlový nominál.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Standard ATP 250 dle dříve doložené lednové verze §7.08: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28; entry list LCB24-9 explicitně uvádí 18 DA, 3 WC, 4 Q, 0 SE a 0 LE, tedy mezistav 25. Nepoužité rezervy se vracejí do DA, nejde o menší plánovaný pavouk. Předstartovní ATP Main (LCB24-1/2) vizuálně ověřen: BYE 2/10/23/31, čtyři Q placeholdery 3/14/27/28, WC 13/15/30, Alt 11/12 a osm seedů. Originál 24.2. (LCB24-3) má čtyři přiřazené Q, stejné WC/BYE, odstraněné Alt značky; nejde o změnu kapacity. Main 12+8+4+2+1=27. Q 14 DA + 2 WC dle dobové listiny, 16 účastníků a osm Q1 utkání dle pořadatele, čtyři sekce a všech osm seedů potvrzeny nezávislým výsledkovým archivem LCB24-12. Sekundární Q pavouk LCB24-17 označuje WC Rubio Fierros a Mejía, Alt Holt a Mayo; pořadatel potvrzuje všech 16 jmen, nikoli všechny vstupní štítky. 8+4=12, čtyři řádní postupující. Nominální počet Q WC doložen dobovým přepisem a pravidlem; původní Q PDF chybí.

### 5. Dobová pravidla

§7.03/7.04/7.08/7.09/7.10/7.15–18/7.20, dříve doložená lednová verze, včetně SE/LE, čtyř sekcí, osmi seedů, čtyř Main BYE a pravidel náhradníků. ATP Preview LCB24-4 potvrzuje nulové body za první prohru po BYE; Q body dle LCB24-18. Next Gen v týdnu Rio/Doha/Los Cabos: Main Menšík v Doha doložen, žádný NG vstup není označen v Los Cabos listině LCB24-9; Michelsen je v Main předstartovním losu Alt. Věk ani samotná účast nedokazují NG rezervu. Přesná alokace Q příležitostí zůstává otevřená.

**Důležitá časová revize pravidel:** oficiální ATP change log LCB24-19 výslovně datuje na 16.2.2024 změny §7.04 D (sign-in přes SMS nebo e-mail s potvrzením před deadline) a §7.08 C.3 (uchování způsobilosti na acceptance listu, kontakt před 18:00 místně den před Q; po zahájení Q přednost LL před dalšími Alt). Tentýž den oprava §9.03 G.4 potvrzuje pro ATP 250 s Main do 32 hráčů Q2 7 bodů, Q1 0. Tato revize již platí pro Q 17.2. v Los Cabos, Doha a Rio; nepřenášet automaticky na starší ročníky. Dále change log datuje změnu §7.03 A.7 (ES) na 20.2.2024, vypouští předchozí formulaci začátku časového okna v pondělí před event week; páteční uzávěrka a podmínky zůstávají. Pro vstupy před zahájením Doha 19.2. zachovat dřívější časový předpis, nikoli zpětně novelizovaný. Evidence změny je textová; screenshot zdroje 403.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 139190 |
| Finalista | 1 | 165 | 81195 |
| SF | 2 | 100 | 47740 |
| QF | 4 | 50 | 26665 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 16065 |
| R32 | 12 | 0 | 9815 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 4910 |
| Q1 prohra | 8 | 0 | 2675 |

Main přímo ze tří vizuálně ověřených originálních ATP kopií a ATP notes. Q ceny 4910/2675 shodně ve čtyřech sekundárních přehledech (LCB24-20/21/22/23), bez prokázané vzájemné nezávislosti; Stevegtennis chybně označuje měnu A$, jeho Main čísla však souhlasí s primárním USD losem. Q body primární předpis LCB24-18/19. Q částky nejsou primárně ověřené; P* zůstává do získání originálního Q losu/DS. Nominální Main 668825 USD, Q 41040 USD, celkem 709865 USD. ITF celková dotace 915245 USD a financial commitment v Main 1005620 USD nejsou singlovým součtem.

### 7. Kontrola a mezery

I/T/H/D/B doloženy; E* původní acceptance list a časy losů nedohledány, uzávěrky odvozené; R* dobové změny doloženy textem, Q NG alokace otevřena; P* Q ceny sekundární shoda; Z* vizuálně ověřeny pořadatelský Main 17.2., archivní Main kopie, Main 24.2. před finále a OOP 20./24.2. (vše po jedné straně). ATP notes str. 2 a ATP change log textově, pokusy o screenshot 403; přímý Q originál a DS nedostupné. Žádné PDF hashe. Kontrola kvót, počtů zápasů a finančních součtů prošla. Další Acapulco, Dubai a Santiago 2024. Bez runtime změn.

### 8. Zdroje (LCB24)

- LCB24-1: [pořadatelský ATP Main los 17.2.](https://www.loscabostennisopen.com/wp-content/uploads/2024/02/MDS_17feb.pdf), str. 1 vizuálně.
- LCB24-2: [archiv původního předstartovního Main losu](https://www.raquetc.com/wp-content/uploads/2024/02/ATP-250-Los-Cabos-2024-quadro-principal-de-singulares.pdf), str. 1 vizuálně, vyplněné cutoffs.
- LCB24-3: [pořadatelský ATP Main los 24.2. před finále](https://www.loscabostennisopen.com/wp-content/uploads/prensa-2024/febrero_24/documentos/mds_24feb.pdf), str. 1 vizuálně.
- LCB24-4: [ATP Preview & Day 1](https://www.atptour.com/-/media/b8477901154743c9a3d363d6c88a8814.pdf), 19.2., str. 2 Main body/odměny/BYE, text, screenshot 403.
- LCB24-5: [pořadatel 17.2. Main los](https://loscabostennisopen.com/en/2024/02/17/mifel-tennis-open-2024-main-draw-is-ready/), termín Main a Q, změna harmonogramu.
- LCB24-6: [pořadatelský program označený 2024](https://loscabostennisopen.com/en/tournament-schedules/), tabulka SCHEDULES, dvě chyby v datu/dni opraveny podle dobových dokumentů.
- LCB24-7: [originální OOP 20.2.](https://www.loscabostennisopen.com/wp-content/uploads/prensa-2024/febrero_20/documentos/OP_20feb.pdf), vydán 19.2. 18:12, str. 1 vizuálně, 7 R32.
- LCB24-8: [originální OOP 24.2.](https://www.loscabostennisopen.com/wp-content/uploads/prensa-2024/febrero_24/documentos/OP_24feb.pdf), vydán 24.2. 01:46, str. 1 vizuálně, finále 20:00.
- LCB24-9: [dobový přepis entry listů](https://www.tennisteen.it/entry-list/atp/24123-atp-entry-list-19-25-febbraio-2024.html), Los Cabos řádky 121–180.
- LCB24-10: [pořadatel Q1 17.2.](https://loscabostennisopen.com/en/2024/02/17/mifel-tennis-open-by-telcel-oppo-2024-opens-with-qualifiers/), osm dvojic, 16 hráčů.
- LCB24-11: [pořadatel Q2 18.2.](https://loscabostennisopen.com/en/2024/02/18/cobolli-nava-holt-y-kovacevic-advance-to-the-main-draw/), čtyři postupující.
- LCB24-12: [Tennis Explorer Q](https://www.tennisexplorer.com/los-cabos/2024/atp-men/?phase=qualification), úplná výsledková struktura a seedy, ne místní data.
- LCB24-13: [Canal Tenis dobové výsledky](https://canaltenis.com/resultados-atp-los-cabos-2024/), Main denní rozdělení, finále datum nekopírovat jako místní; [pořadatel R16](https://loscabostennisopen.com/en/2024/02/21/zverev-tsitsipas-and-ruud-advance-to-quarterfinals/).
- LCB24-14: [ATP oznámení kalendáře 2024](https://www.atptour.com/en/news/2024-atp-tour-calendar), přesun z července do února.
- LCB24-15: [Ultimate Tennis Statistics ročník s extId 7480](https://www.ultimatetennisstatistics.com/tournamentEvent?extId=7480&name=Los+Cabos&season=2024&tab=results); [ITF ročník a celková dotace](https://www.itftennis.com/en/tournament/los-cabos/mex/2024/m-250-mex-2024-001/draws-and-results/).
- LCB24-16: [historie času San José del Cabo](https://www.timeanddate.com/time/zone/mexico/san-jose-del-cabo), UTC−7 od 2023; [IANA timezone](https://time.is/Los_Cabos).
- LCB24-17: [sekundární Q pavouk](https://en.wikipedia.org/wiki/2024_Los_Cabos_Open_%E2%80%93_Singles), WC/Alt a osm seedů; původní [ATP Q PDF](https://www.protennislive.com/posting/2024/7480/qs.pdf) nedostupný.
- LCB24-18: [ATP předsezonní aktualizace rankingových bodů 2024](https://www.atptour.com/en/news/2024-rankings-points-update), ATP 250 32 draw.
- LCB24-19: [ATP změny rulebooku, revize 30.4.2024](https://www.atptour.com/-/media/files/rulebook/2024/24-rulebook-changes_apr2024.pdf), explicitně účinnost 16.2. (§7.04 D, §7.08 C.3, §9.03 G.4) a 20.2. (§7.03 A.7); text, screenshot 403.
- LCB24-20: [TennisCompanion historický sloupec 2024](https://tenniscompanion.org/prize-money/los-cabos/), Q 4910/2675.
- LCB24-21: [Canal Tenis ročníkový oddíl 2024](https://canaltenis.com/prize-money-atp-los-cabos/), Q shoda.
- LCB24-22: [dobový The SportsRush finanční rozpis 2024](https://thesportsrush.com/tennis-news-los-cabos-open-2024-prize-money-breakdown-who-is-playing-in-it-points-on-offer-where-to-watch-in-usa-and-uk/), Q shoda.
- LCB24-23: [Stevegtennis ročník 2024](https://www.stevegtennis.com/draw-results/atp/Mifel%20Tennis%20Open%20-%20Los%20Cabos/2024), indexovaná shoda částek, chybné A$; přímý přístup timeout.

## Otevřené položky k opakované kontrole

| Ročník | Oblast | Priorita / další požadovaný doklad |
|---|---|---|
| Auckland 2024 | P – Q prize money, blokuje HOTOVO | originální ATP Q draw/Detail Sheet nebo ročníková spolehlivá tabulka potvrzující konkrétní hodnoty; kandidát 3550/1935 USD není certifikovaný |
| Hong Kong 2024 | P* – sekundární Q prize money | originální Q tabulka; kandidát 3550/1935 USD doložen sekundární shodou |
| Montpellier 2024 | P* – sekundární Q prize money | originální Q tabulka, kandidát 3105/1695 EUR doložen sekundární shodou |
| Marseille 2024 | inventura – historická identita doložena, interní series metadata neověřena | ATP 496 se přesunul do Lyonu 2026; samostatný Lyon 7694; historické místo Marseille, neměnit runtime; MRS24-4/7/8/9 |
| Marseille 2024 | E – nominální Q WC, blokuje HOTOVO | 12+4 press kit vs 14+2 dobový ATP předpis a přepis listiny; opakovaná kontrola MRS24-16/17 nezískala originální Q listinu/DS ani výjimku; kandidát 14+2, stále otevřeno |
| Córdoba/Dallas/Marseille 2024 | R* – Next Gen rezervy v týdnu tří ATP akcí | ověřit přesnou alokaci mezi akcemi a případné individuální využití, nepřidávat mimo pevnou kapacitu; COR24-17 |
| Dallas 2024 | P* – sekundární Q prize money | původní ATP Q PDF nebo Detail Sheet; 4055/2210 USD shoda sekundárních zdrojů, DAL24-17/19/20 |
| Buenos Aires 2024 | P* – sekundární Q prize money | originální Q draw/DS; sekundární shoda 3445/1880 USD (BUE24-16/17/18) |
| Buenos Aires/Delray Beach 2024 | R* – NextGen rezervy | Main Delray Shang doložen pořadatelem a listinou DLB24-7/9/12; Q příležitosti a případné využití/propad v týdnu stále otevřeny; žádné navýšení kapacity |
| Rotterdam 2024 | E*/Z* – doplňkové podklady | originální acceptance list/DS, Q losovací čas; Main/Q ceny přímo v originálech, bez blokující mezery |
| Delray Beach 2024 | E*/H*/Z* – doplňkové podklady | původní acceptance list, detail sheet, úplné OOP, vizuální kontrola Q originálu a přesný důvod Q2 posunu; nominální Q odměny již z primárního textu |
| Rio de Janeiro 2024 | H*/E*/Z* – doplňkové podklady | původní rozdělení R16 před deštěm, originální acceptance list/DS, čas Q losu, obrazová kontrola velké Revista; primární Main/Q finanční tabulky ověřeny |
| Doha 2024 | R*/E*/H*/Z* – doplňkové podklady | originální schválení ES a případná kompenzace, Q NextGen alokace v týdnu Rio/Doha/Los Cabos, originální acceptance list/DS, časy losů a kompletní původní OOP; Main/Q ceny vizuálně z ATP kopií |
| Los Cabos 2024 | P* / E* / Z* | originální Q finanční tabulka (sekundární shoda 4910/2675 USD), acceptance list/DS, časy losování a pondělní OOP; Q NG alokace stále otevřená |
