# Historický registr tenisových turnajů — mužská dvouhra

**Stav k 2026-11-28: 44 ročníků: všechny Grand Slamy 2024 a 2025, Brisbane, Hong Kong, Adelaide, Montpellier, Córdoba, Dallas, Buenos Aires, Rotterdam, Delray Beach, Rio de Janeiro, Doha, Los Cabos, Acapulco, Dubai, Indian Wells, Miami, Marrakech, Estoril, Houston, Monte-Carlo, Barcelona, Munich, Bucharest, Madrid, Rome, Geneva, Stuttgart, 's-Hertogenbosch, Halle, Queen's, Mallorca, Eastbourne a rozpracované Auckland, Marseille, Santiago a Lyon 2024.** Tento jediný rozšiřitelný dokument je rešeršní registr reálného tenisu. Není autoritativním runtime balíčkem. Neobsahuje převod na squash, Run, simulační týdny, sloty, vlastní bodování ani změny existujících katalogů. Navazujeme vždy jedním ročníkem; další nepřidávat, dokud není předchozí zkontrolován proti povinnému seznamu a jeho zbývající mezery výslovně zařazeny. Rozsah: mužská profesionální dvouhra včetně kvalifikací; další disciplíny pouze jako kontext souhrnných financí či kalendáře.

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
| 2024 | [Acapulco](#acapulco-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Dubai](#dubai-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Santiago](#santiago-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓* | ✓ | ? | ✓* | ROZPRACOVÁNO (8/9; P: rozpor odměn Main) |
| 2024 | [Indian Wells](#indian-wells-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Miami](#miami-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Marrakech](#marrakech-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Estoril](#estoril-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Houston](#houston-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Monte-Carlo](#monte-carlo-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Barcelona](#barcelona-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Munich](#munich-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Bucharest](#bucharest-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓* | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Madrid](#madrid-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Rome](#rome-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Geneva](#geneva-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Lyon](#lyon-2024) | ✓ | ✓ | ✓* | ? | ✓ | ✓* | ✓ | ✓* | ✓* | ROZPRACOVÁNO (8/9; E: nominální Q WC) |
| 2024 | [Stuttgart](#stuttgart-2024) | ✓ | ✓ | ✓* | ✓* | ✓* | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | ['s-Hertogenbosch](#s-hertogenbosch-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Halle](#halle-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Queen's](#queens-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓* | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Mallorca](#mallorca-2024) | ✓ | ✓ | ✓* | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |
| 2024 | [Eastbourne](#eastbourne-2024) | ✓ | ✓ | ✓ | ✓* | ✓ | ✓ | ✓ | ✓ | ✓* | HOTOVO (nominální rozsah) |

`*` H: doložena okna kol; přesné původní počty zápasů jednotlivých dnů u vícedenních kol se nedokládají odhadem. Z: dobové zdroje jsou dohledatelné, některé pouze indexovaným textem; chybějí nezávisle získané PDF bajty/otisky. Obojí je transparentně zaznamenáno. U 2025 E*: datum uzávěrek odvozeno z dobového předpisu, hodina losu Q neověřena, ale Main los doložen; ATP rankingový předpis 2025 byl následně úspěšně zkontrolován i vizuálně na tištěné str. 264. AO 2024 H*: oficiální říjnový program textově dostupný, obrazové vykreslení selhalo; potvrzen dobovým programem pořadatele a předturnajovým přehledem. R*: dobový Grand Slam předpis v textovém zrcadle a ATP oznámení bodů; přímé PDF rulebooků nebylo dostupné.

**Součet registru:** 44 zpracovaných ročníků; 40 hotových v nominálním rozsahu; 4 rozpracované; ostatní ročníky zatím nejsou v registru, bez ohledu na stav jiných PR.

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
| 23 | Acapulco 2024 | HOTOVO (nominální rozsah) |
| 24 | Dubai 2024 | HOTOVO (nominální rozsah) |
| 25 | Santiago 2024 | ROZPRACOVÁNO (P: rozpor odměn Main) |
| 26 | Indian Wells 2024 | HOTOVO (nominální rozsah) |
| 27 | Miami 2024 | HOTOVO (nominální rozsah) |
| 28 | Marrakech 2024 | HOTOVO (nominální rozsah) |
| 29 | Estoril 2024 | HOTOVO (nominální rozsah) |
| 30 | Houston 2024 | HOTOVO (nominální rozsah) |
| 31 | Monte-Carlo 2024 | HOTOVO (nominální rozsah) |
| 32 | Barcelona 2024 | HOTOVO (nominální rozsah) |
| 33 | Munich 2024 | HOTOVO (nominální rozsah) |
| 34 | Bucharest 2024 | HOTOVO (nominální rozsah) |
| 35 | Madrid 2024 | HOTOVO (nominální rozsah) |
| 36 | Rome 2024 | HOTOVO (nominální rozsah) |
| 37 | Geneva 2024 | HOTOVO (nominální rozsah) |
| 38 | Lyon 2024 | ROZPRACOVÁNO (E: nominální Q WC) |
| 39 | Stuttgart 2024 | HOTOVO (nominální rozsah) |
| 40 | 's-Hertogenbosch 2024 | HOTOVO (nominální rozsah) |
| 41 | Halle 2024 | HOTOVO (nominální rozsah) |
| 42 | Queen's 2024 | HOTOVO (nominální rozsah) |
| 43 | Mallorca 2024 | HOTOVO (nominální rozsah) |
| 44 | Eastbourne 2024 | HOTOVO (nominální rozsah) |

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
| [2024](#acapulco-2024) | Abierto Mexicano Telcel presentado por HSBC | ATP 500 | 2024-02-24–2024-02-25 | 2024-02-26–2024-03-02 | HOTOVO v nominálním rozsahu; plánované sobotní finále |
| [2024](#dubai-2024) | Dubai Duty Free Tennis Championships | ATP 500 | 2024-02-24–2024-02-25 | 2024-02-26–2024-03-02 | HOTOVO v nominálním rozsahu; plánované sobotní finále |
| [2024](#santiago-2024) | Movistar Chile Open | ATP 250 | 2024-02-24–2024-02-25 | 2024-02-26–2024-03-03 | ROZPRACOVÁNO; finanční rozpor Main, termíny doloženy |
| [2024](#indian-wells-2024) | BNP Paribas Open | ATP Masters 1000 | 2024-03-04–2024-03-05 | 2024-03-06–2024-03-17 | HOTOVO v nominálním rozsahu; 15.3. bez mužské dvouhry |
| [2024](#miami-2024) | Miami Open presented by Itaú | ATP Masters 1000 | 2024-03-18–2024-03-19 | 2024-03-20–2024-03-31 | HOTOVO v nominálním rozsahu; 30.3. bez mužské dvouhry |
| [2024](#marrakech-2024) | Grand Prix Hassan II | ATP 250 | 2024-03-31–2024-04-01 | 2024-04-01–2024-04-07 | HOTOVO v nominálním rozsahu; plánovaný souběh Q2/R32 1.4. |
| [2024](#estoril-2024) | Millennium Estoril Open | ATP 250 | 2024-03-30–2024-03-31 | 2024-04-01–2024-04-07 | HOTOVO v nominálním rozsahu; dešťové odklady R32 odděleny |
| [2024](#houston-2024) | Fayez Sarofim & Co. U.S. Men's Clay Court Championship | ATP 250 | 2024-03-30–2024-03-31 | 2024-04-01–2024-04-07 | HOTOVO v nominálním rozsahu |
| [2024](#monte-carlo-2024) | Rolex Monte-Carlo Masters | ATP Masters 1000 | 2024-04-06–2024-04-07 | 2024-04-07–2024-04-14 | HOTOVO v nominálním rozsahu; souběh Q2/R64 a R64/R32 |
| [2024](#barcelona-2024) | Barcelona Open Banc Sabadell | ATP 500 | 2024-04-13–2024-04-14 | 2024-04-15–2024-04-21 | HOTOVO v nominálním rozsahu; souběh R64/R32 16.4. |
| [2024](#munich-2024) | BMW Open | ATP 250 | 2024-04-13–2024-04-14 | 2024-04-15–2024-04-21 | HOTOVO v nominálním rozsahu; poslední ročník ATP 250 |
| [2024](#bucharest-2024) | Țiriac Open | ATP 250 | 2024-04-14–2024-04-15 | 2024-04-15–2024-04-21 | HOTOVO v nominálním rozsahu; plánovaný souběh Q2/R32 15.4. |
| [2024](#madrid-2024) | Mutua Madrid Open | ATP Masters 1000 | 2024-04-22–2024-04-23 | 2024-04-24–2024-05-05 | HOTOVO v nominálním rozsahu; 4.5. bez mužské dvouhry |
| [2024](#rome-2024) | Internazionali BNL d'Italia | ATP Masters 1000 | 2024-05-06–2024-05-07 | 2024-05-08–2024-05-19 | HOTOVO v nominálním rozsahu; 18.5. bez mužské dvouhry |
| [2024](#geneva-2024) | Gonet Geneva Open | ATP 250 | 2024-05-18–2024-05-19 | 2024-05-19–2024-05-25 | HOTOVO v nominálním rozsahu; souběh 19.5., sobotní F |
| [2024](#lyon-2024) | Open Parc Auvergne-Rhône-Alpes Lyon | ATP 250 | 2024-05-18–2024-05-19 | 2024-05-19–2024-05-25 | ROZPRACOVÁNO; konflikt Q WC, historická série 7694 |
| [2024](#stuttgart-2024) | BOSS OPEN | ATP 250 | 2024-06-08–2024-06-09 | 2024-06-10–2024-06-16 | HOTOVO v nominálním rozsahu; tráva, Q1 přesuny odděleny |
| [2024](#s-hertogenbosch-2024) | Libéma Open | ATP 250 | 2024-06-08–2024-06-09 | 2024-06-10–2024-06-16 | HOTOVO v nominálním rozsahu; všechny denní počty přímo doloženy |
| [2024](#halle-2024) | Terra Wortmann Open | ATP 500 | 2024-06-15–2024-06-16 | 2024-06-17–2024-06-23 | HOTOVO v nominálním rozsahu; původní denní splity R32/R16 otevřeny |
| [2024](#queens-2024) | cinch Championships | ATP 500 | 2024-06-15–2024-06-16 | 2024-06-17–2024-06-23 | HOTOVO v nominálním rozsahu; R32 5+11 primárně doloženo |
| [2024](#mallorca-2024) | Mallorca Championships presented by waterdrop | ATP 250 | 2024-06-22–2024-06-23 | 2024-06-23–2024-06-29 | HOTOVO v nominálním rozsahu; nedělní souběh Q/Main |
| [2024](#eastbourne-2024) | Rothesay International | ATP 250 | 2024-06-22–2024-06-23 | 2024-06-24–2024-06-29 | HOTOVO v nominálním rozsahu; všech šest Main OOP primárně doloženo |

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


## Acapulco 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/P/Z s omezeními). Rešerše 2026-11-27. Třetí ATP 500 v registru; šestidenní Main bez BYE. Předstartovní originální ATP Main kopie vizuálně ověřena, pořadatelská aktualizace Main a OOP textově. Původní Q PDF nedostupné; Q finanční částky potvrzeny shodou více sekundárních zdrojů, nikoli originálem.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Abierto Mexicano Telcel presentado por HSBC, 31. ročník, mužská dvouhra | ACA24-1/2/3 |
| Kategorie / ATP ID | ATP 500 / 807 | ACA24-1/4 |
| Dějiště obou fází | Arena GNP Seguros, Acapulco, Guerrero, Mexiko | ACA24-3/4/5 |
| Povrch | venkovní tvrdý, Solflex | ACA24-1/2 |
| Časové pásmo | America/Mexico_City, UTC−06:00 v únoru a březnu 2024 | lokalita a datum |
| Ředitel | Álvaro Falla | ACA24-6 |
| Supervisor | Ali Nili / Cristina Romero; OOP 28.2. navíc Jaime Chavez | ACA24-1/6 |
| Referee / tour manager | Ricardo Reis / Arnau Brugues | ACA24-6 |
| Měna | USD | ACA24-1/2 |

Nezaměňovat s Los Cabos, které bylo v roce 2024 přesunuto z července na předcházející týden. Pořadatel v prosinci 2023 potvrdil zachování dějiště a plán 24.2.–2.3.2024 po hurikánu Otis (ACA24-7); nejde o mimořádně přesunutý turnaj. Model míčů a originální detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | neověřeno originální listinou; pravidlový referenční den 2024-01-29 | §7.03 |
| Q rank date | neověřeno originální listinou; pravidlový referenční den 2024-02-05 | §7.03 |
| Nominální Main deadline | 2024-01-29 11:00 (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-02-05 11:00 (12:00 US Eastern) | odvozeno §7.03 |
| Podmíněná A+ WC deadline | 2024-02-23 09:00 (10:00 US Eastern) | odvozeno §7.12 A.2 |
| Main los | 2024-02-24; hodina 15:00 uvedena v rozporném ATP preview, skutečná hodina neověřena | ACA24-8/9 |
| Q los | nejpozději 2024-02-24 před Q1, přesná hodina neověřena | ACA24-10/11 |
| Q | 2024-02-24–25 | ACA24-5/10/12 |
| Main | 2024-02-26–2024-03-02 | ACA24-1/2/5/13 |
| Finále | 2024-03-02 21:00 místně, plán | ACA24-5 |

ATP preview ACA24-8 uvádí neslučitelnou kombinaci soboty a 25.2.; v roce 2024 je 25.2. neděle. Pořadatel ve zprávě s datací 24.2. a dobová publikace téhož dne potvrzují los 24.2.; hodinu z chybně datovaného preview nepovažujeme za jistou. Předstartovní originální Main los uvádí Taro Daniel 62 jako last DA při deadline i při losu, zatímco dobový přepis původní listiny 31.1. končí u McDonalda 48 (ACA24-14). Jsou to různé stavy, bez originální acceptance listiny nelze jejich rozdíl přesně administrativně vysvětlit. Q cutoff ani původní rank dates nezískány. Uzávěrky odvozené, ne prokázané skutečným timestampem.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-24 | 8 |
| Q2 | 2024-02-25 | 4 |
| R32 | 2024-02-26–27 | 16 (8+8) |
| R16 | 2024-02-28 | 8 |
| QF | 2024-02-29 | 4 |
| SF | 2024-03-01 | 2 |
| F | 2024-03-02 | 1 |

Oficiální návštěvnický program ACA24-5 výslovně uvádí oba Q dny (17:00 a 18:00), R32 ve dvou dnech od 18:00, R16 28.2. od 18:00, QF 29.2. od 18:00, SF 1.3. od 19:00 a singlové finále 2.3. od 21:00 po doubles finále. Pořadatel před Q1 publikoval 8 singlových zápasů; Q2 25.2. čtyři postupující. Pořadatelská zpráva 25.2. (ACA24-12) plánuje na pondělí osm singlů a dva doubles. Zpráva o druhé Main hrací době (ACA24-15) uvádí osm singlů a šest doubles; v úvodní větě chybně označuje den jako pondělí, titulek, jmenované dvojice a výsledky potvrzují úterý 27.2. Originální OOP 28.2. vydán 28.2. 00:12, osm R16 na třech kurtech, žádné plánované R32. Výsledkový archiv ACA24-16 nezávisle kontroluje počty, zahraniční datum přes půlnoc nepřepisuje místní plán. Celé nominální okno osm dní, 2 Q + 6 Main bez překryvu fází, 43 zápasů. ATP kalendář označuje sobotní finále; ITF datum do 3.3. je širší metadata, nikoli nominální den finále.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 |
| Základní DA při všech rezervách | 23 | 13 |
| SE rezerva | 1 | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 23 DA + 1 SE + 3 WC + 1 A+ WC + 4 Q = 32, přímo doloženo ročníkovým přepisem listiny z 31.1. (ACA24-14) a standardem §7.08 B/E, §7.10 B, §7.12 A.2; 0–1 SE, 3–4 WC, 23–25 DA dle využití rezerv. Nevyužité rezervy se vracejí do DA. Originální předstartovní Main ACA24-1 vizuálně potvrzuje všechny 32 pozice, 8 seedů, Q placeholdery 6/14/29/31 a WC 4/11/19; žádné BYE. Pořadatelská aktualizace 26.2. ACA24-2 dokládá čtyři Q a jednoho LL Nishioku po odstoupení Norrieho. Historické přerozdělení slotů (např. LL v pozici 6, Q v pozici 27) nemění čtyři nominální Q postupy; neoznačovat pět vstupů z kvalifikačního pole za pět řádných postupů.

Q 13 DA + 3 WC = 16 dle standardu ATP 500; dobový přepis Q losu a OOP 24.2. ACA24-11 označuje tři WC (Svajda, Mejia, Rubio Fierros), jedno Alt, všech osm seedů a čtyři sekce. Pořadatel potvrzuje osm dvojic a čtyři postupy ACA24-10/12, výsledkový pavouk ACA24-17 potvrzuje geometrii a štítky. Původní Q PDF a acceptance list nedostupné, neodvozovat neoznačené jednotlivce jako jistě DA. Main 16+8+4+2+1=31, Q 8+4=12. Historická skreč nebo LL nemění nominální počet.

### 5. Dobová pravidla

ATP 500 §7.08 B/E, §7.10 B, §7.12 A.2, §7.13/7.15–16: jedna SE rezerva (pro SE z ATP 250 platí stejný ATP region), podmíněná A+ WC do páteční uzávěrky, osm seedů Main/Q, čtyři Q vítězové, náhradníci a LL podle §7.09/7.16, BO3 s tiebreakem podle ATP singles předpisu. Oproti ATP 250 žádná LE rezerva; žádná bodová výjimka při prohře po BYE, neboť pavouk nemá BYE. Pro tento ročník již platí únorové změny sign-in a pravidel náhradníků z 16.2. (LCB24-19); nepřenášet starší verzi beze změny. Q body 25/13/0 dle dobového předpisu ROT24-16 a příslušného řádku 32 hráčů ATP 500.

Týden Acapulco/Dubai/Santiago: samotná přítomnost mladých hráčů nebo WC není důkaz Next Gen programového vstupu. Přesné přidělení případných kvalifikačních příležitostí neověřeno; další audit při zpracování Santiago, ATP 250 téhož týdne. Nevytvářet dodatečné místo v žádném pavouku.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 412555 |
| Finalista | 1 | 330 | 221975 |
| SF | 2 | 200 | 118300 |
| QF | 4 | 100 | 60440 |
| R16 | 8 | 50 | 32265 |
| R32 | 16 | 0 | 17210 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 8820 |
| Q1 prohra | 8 | 0 | 4945 |

Main primární ATP los ACA24-1 vizuálně, ACA24-2 textově. Q sekundární shoda ACA24-17/18/19 (vzájemná nezávislost neprokázána); TennisTemple nesprávně nazývá postup třetím Q kolem, geometrie a pořadatel potvrzují dvě kola. Canal Tenis uvádí chybně 112625 USD za SF (částka Rio), proto pro Main výlučně primární ATP částka 118300 USD; jeho Q řádky souhlasí s dalšími tabulkami. P* zůstává do získání Q originálu. Nominální Main 1646370 USD, Q 74840 USD, celkem 1721210 USD; total financial commitment 2377565 USD (originální ATP los) a ITF celková dotace 2206080 USD (ACA24-20) jsou jiné veličiny. Q postupující dostávají Main odměnu podle výsledku, Q body se přičítají dle dobového předpisu.

### 7. Kontrola a mezery

I/T/H/D/R/B doloženy. E* pravidlové uzávěrky odvozené; originální acceptance listy/DS, přesné časy losů a Q cutoff neověřeny. P* Q odměny sekundární shoda. Z* archiv předstartovního originálu Main (1 strana) vizuálně; pořadatelský originální Main 26.2. a OOP 28.2. textově, screenshoty 404; originální Q PDF nedostupné. Nevymýšlet SHA-256. Kontrola kvót, seedů, zápasů, peněz a nominálních oken prošla. Další Dubai 2024, následně Santiago. Bez runtime změn.

### 8. Zdroje (ACA24)

- ACA24-1: [archiv předstartovního originálního ATP Main](https://www.raquetc.com/wp-content/uploads/2024/02/ATP-500-Acapulco-2024-quadro-principal-singulares.pdf), str. 1 vizuálně, kvóty, povrch, body/ceny.
- ACA24-2: [pořadatelský originál ATP Main 26.2.](https://abiertomexicanodetenis.com/wp-content/uploads/2024/02/mds_26feb.pdf), text, screenshot 404, LL a čtyři Q, ceny.
- ACA24-3: [pořadatelské zprávy 26.2.](https://abiertomexicanodetenis.com/tag/prensa_26feb_2024/), 31. ročník, dějiště.
- ACA24-4: [ATP série 807](https://www.atptour.com/es/tournaments/acapulco/807/overview), identita a tvrdý povrch od 2014; ne zdroj specifických ročníkových cen.
- ACA24-5: [oficiální návštěvnický plán s daty 2024](https://abiertomexicanodetenis.com/planea-tu-visita/), tabulka HORARIOS; při budoucí aktualizaci URL kontrolovat ročník.
- ACA24-6: [originální OOP 28.2.](https://abiertomexicanodetenis.com/wp-content/uploads/2024/02/OP_28feb_acapulco.pdf), text, screenshot 404; 8 R16 a funkcionáři.
- ACA24-7: [pořadatel 14.12.2023](https://abiertomexicanodetenis.com/2023/12/14/mextenis-refrenda-su-compromiso-con-acapulco-y-mantiene-en-el-puerto-el-abierto-mexicano-telcel-presentado-por-hsbc-del-2024/), potvrzení celého okna.
- ACA24-8: [ATP preview 23.2.2024](https://www.atptour.com/en/news/acapulco-2024-history-draw-schedule), indexovaný text, přímý přístup 403; chyba datum/den Main losu.
- ACA24-9: [pořadatelský archiv zprávy o losu](https://abiertomexicanodetenis.com/tag/imagen_ok/page/6/), datace 24.2.; [dobová sekundární zpráva 24.2.](https://tennisuptodate.com/atp/atp-draw-2024-mexican-open-acapulco-abierto-mexicano-telcel-including-alexander-zverev-holger-rune-taylor-fritz), nezávislé potvrzení data.
- ACA24-10: [pořadatel Q1 24.2.](https://abiertomexicanodetenis.com/en/2024/02/24/the-abierto-mexicano-telcel-presented-by-hsbc-2024-kicks-off-with-the-qualy-round/), 8 dvojic, čtyři postupy.
- ACA24-11: [dobový Q los a program 24.2.](https://www.livetennis.it/post/407412/atp-500-acapulco-e-atp-250-santiago-il-tabellone-di-qualificazione-con-il-programma-completo-cinque-azzurri-al-via/), osm seedů, tři WC, lokální start.
- ACA24-12: [pořadatelský archiv zpráv 25.2.](https://abiertomexicanodetenis.com/en/amt-news/page/11/), indexované zprávy o čtyřech postupech a osmi pondělních singlech, přímé otevření 404; [španělský archiv](https://abiertomexicanodetenis.com/category/noticias/page/13/).
- ACA24-13: [ATP kalendář 8.2.2024](https://www.atptour.com/-/media/files/calendar-pdfs/2024/2024-atp-challenger-calendar-as-of-8-february-2024.pdf), indexovaný řádek 32/16 a Saturday final; [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024).
- ACA24-14: [dobový přepis Main entry listu 31.1.](https://canaltenis.com/entry-list-atp-acapulco-2024/), 23 DA a explicitní 3 WC + A+ WC + SE + 4 Q; v úvodu generické koncové datum 3.3., přednost ATP a pořadateli.
- ACA24-15: [pořadatel druhý den Main](https://abiertomexicanodetenis.com/2024/02/27/zverev-rune-tsitsipas-ruud-y-tiafoe-entran-en-accion-en-la-segunda-jornada-del-amt-2024/), osm singlů, chyba weekday v úvodu.
- ACA24-16: [dobový denní přehled výsledků](https://canaltenis.com/resultados-atp-acapulco-2024/), pouze kontrola kol/počtů; [Tennis Abstract](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024Acapulco).
- ACA24-17: [TennisTemple Q pavouk a odměny](https://en.tennistemple.com/competitions/acapulco/2024/draw-qualifications), 8820/4945, 25/13/0.
- ACA24-18: [TennisCompanion historický sloupec 2024 USD](https://tenniscompanion.org/prize-money/acapulco/), Q shoda.
- ACA24-19: [Canal Tenis, ročníkový oddíl 2024](https://canaltenis.com/el-prize-money-del-atp-acapulco/), Q shoda, nesprávná SF částka; nepoužívat pro Main.
- ACA24-20: [ITF ročník](https://www.itftennis.com/en/tournament/acapulco/mex/2024/m-500-mex-2024-001/draws-and-results/), celková dotace, širší datum do 3.3. není nominální finále.
- Pravidla ROT24-15/16, LCB24-19; [originální Q PDF](https://www.protennislive.com/posting/2024/807/qs.pdf) nedostupné, DS nezískán.


## Dubai 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/P/Z s omezeními). Rešerše 2026-11-27. Čtvrtý ATP 500 v registru. Tři verze originálního ATP Main losu a tři pořadatelské denní rozpisy vizuálně ověřeny. Originální Q pavouk nezískán, Q geometrie a finanční odměny doloženy sekundárními zdroji a originálním OOP Q2.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Dubai Duty Free Tennis Championships, 32. mužský ročník, dvouhra | DXB24-1/5 |
| Kategorie / ATP ID | ATP 500 / 495 | DXB24-1/2 |
| Dějiště | Dubai Duty Free Tennis Stadium, Aviation Club Tennis Centre, Dubai, Spojené arabské emiráty | DXB24-5/6/13 |
| Povrch | venkovní tvrdý, Decoturf II | DXB24-1/2/3/6 |
| Časové pásmo | Asia/Dubai, GST UTC+04:00 | lokalita a datum |
| Ředitel | Salah Tahlak | DXB24-7/8/10 |
| Supervisor | Ahmed Abdel-Azim; výsledkový Main a pozdější OOP také Roland Herfel | DXB24-1/2/10 |
| Referee / tour manager | Hany El-Khafief / Diego Pedraza | DXB24-7/8/10 |
| Měna | USD | DXB24-1/2 |

Nezaměňovat s předcházející ženskou akcí WTA 1000 (18.–24.2.2024); její losy a peníze nejsou součástí mužského profilu. Míče a detail sheet neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | neověřeno originální listinou; pravidlový referenční den 2024-01-29 | §7.03 |
| Q rank date | neověřeno originální listinou; pravidlový referenční den 2024-02-05 | §7.03 |
| Nominální Main deadline | 2024-01-29 21:00 GST (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-02-05 21:00 GST (12:00 US Eastern) | §7.03, odvozeno |
| Podmíněná A+ WC deadline | 2024-02-23 19:00 GST (10:00 US Eastern) | §7.12 A.2, odvozeno |
| Main los | 2024-02-24 13:00 GST, plán ATP | DXB24-6; datum potvrzuje pořadatel DXB24-5 |
| Q los | před 2024-02-24, přesný čas a den neověřeny | DXB24-11/12 |
| Q | 2024-02-24–25 od 11:00 GST | DXB24-6/7/11/12 |
| Main | 2024-02-26–2024-03-02 | DXB24-1/2/5/6 |
| Main LL sign-in 26.2. | 13:30 GST | DXB24-8 |
| Finále | 2024-03-02 19:00 GST, plán ATP | DXB24-6 |

Pořadatel potvrzuje skutečné konání losovací ceremonie 24.2.; 13:00 je publikovaný plán, nikoli nezávisle ověřený čas zahájení ceremonie. Všechny tři verze ATP Main losu uvádějí O'Connell 64 jako last DA při deadline i v losu. Dobový sekundární přepis 31.1. (DXB24-14) slouží jako kontrola raného seznamu hráčů, nikoli původního acceptance listu, který nebyl získán. Q cutoff neověřen. Rank date, deadline a čas zveřejnění nejsou zaměnitelné.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-24 | 8 |
| Q2 | 2024-02-25 | 4 |
| R32 | 2024-02-26–27 | 16 (7+9) |
| R16 | 2024-02-28 | 8 |
| QF | 2024-02-29 | 4 |
| SF | 2024-03-01 | 2 |
| F | 2024-03-02 | 1 |

ATP preview DXB24-6 stanoví Q 24.–25.2. od 11:00 a sobotní singlové finále 2.3. v 19:00. Dobové výsledky DXB24-11 potvrzují osm Q1; originální pořadatelský OOP Q2 (DXB24-7), vydaný 24.2. v 16:32, vizuálně potvrzuje čtyři singlová finále kvalifikace na dvou kurtech (další kvalifikační utkání v programu je čtyřhra). Pořadatelský OOP 26.2., vydaný 25.2. v 15:55, uvádí čtyři singlové zápasy na centru a tři na kurtu 1, tj. 7 R32. ATP Day 2 DXB24-9 přímo potvrzuje zbývajících devět R32 dne 27.2. OOP QF z 28.2. 16:23 (DXB24-10) plánuje čtyři QF na centru 29.2., ještě s neurčenými soupeři z R16. Kompletní denní výsledky DXB24-15 potvrzují všech osm R16 ve středu, čtyři QF ve čtvrtek, dvě SF v pátek a finále v sobotu. Nejde o odhad 8+8 R32 ani o kopii jiného ATP 500. Původní samostatný středeční OOP nezískán; okno R16 potvrzují výsledky a předem zveřejněný čtvrteční program. Metadata ITF s koncem 3.3. jsou širší než plán singlové soutěže a nemění nominální finále. 2 Q + 6 Main = 8 dní, bez plánovaného překryvu, 43 zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 |
| Základní DA při všech rezervách | 23 | 13 |
| SE rezerva | 1 | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main standard podle dříve doložených §7.08 B/E, §7.10 B a §7.12 A.2: 23 DA + 1 SE + 3 WC + 1 A+ WC + 4 Q = 32. Nevyužité rezervy přecházejí na způsobilé DA, tedy 23–25 DA podle využití. Originální předstartovní ATP Main DXB24-3 vizuálně: Q placeholdery 11/18/22/30, tři WC 3/15/20, SE 5 (Menšík), PR 13 (Shapovalov), osm seedů, žádné BYE. Aktualizace po Q 25.2. (DXB24-2) přiřazuje čtyři Q na stejné pozice. Zbývá 24 DA včetně PR, což je slučitelné s uvolněním podmíněné A+ rezervy; přesné administrativní potvrzení o nevyužití A+ nezískáno. Výsledkový ATP los DXB24-1 má navíc LL na pozici 23 místo odstoupivšího Popyrina. LL není pátý nominální postupující z Q. Main 16+8+4+2+1=31.

Q standard 13 DA + 3 WC; ročníkový sekundární pavouk DXB24-16 přímo označuje všechny tři WC (Dougaz, Erel, Pospisil) a osm nasazených, 16 hráčů ve čtyřech sekcích po čtyřech. Dobové výsledky Sky DXB24-11/12 a pořadatelský Q2 OOP potvrzují 8+4 zápasy a čtyři řádné postupy. Originální Q draw ani acceptance list nedostupné; pozor na odlišný ženský Q pavouk. Skreče a diskvalifikace v historických zápasech nemění počet nominálních uzlů.

### 5. Dobová pravidla a návaznost Doha

ATP 500 §7.08 B/E, §7.10 B, §7.12 A.2, §7.13/7.15–16: jedna SE rezerva, tři běžné WC a jedna podmíněná A+ WC, bez ATP 250 LE rezervy; nepoužité rezervy se vracejí do DA. Pravidla náhradníků včetně LL podle §7.09/7.16. Čtyři Q sekce, osm seedů v Main i Q, BO3 tiebreak sety. Únorové změny sign-in a náhradníků z 16.2. již platí (LCB24-19). Q body 25/13/0 podle ročníkového ATP rankingového předpisu ROT24-16; výjimka za prohru po BYE zde není relevantní.

Menšík má v originálním Main explicitní SE. ATP Day 2 DXB24-9 a předturnajové podklady potvrzují jeho účast po finále v Doha. Jde o konkrétní návaznost SE mezi ATP 250 a ATP 500 v témže regionu podle §7.10 B; v Doha byl předtím NG (DOH24), ale v Dubaji SE, tedy jiný vstupní mechanismus. Nepřenášet automaticky označení z předcházejícího turnaje ani přidávat místo. Týden Dubai/Acapulco/Santiago: přesná alokace Next Gen kvalifikačních příležitostí nezjištěna; ověřit při zpracování Santiago. Nominalní kapacita žádného pavouka tím není zvětšena.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 550140 |
| Finalista | 1 | 330 | 296000 |
| SF | 2 | 200 | 157755 |
| QF | 4 | 100 | 80600 |
| R16 | 8 | 50 | 43025 |
| R32 | 16 | 0 | 22945 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 11760 |
| Q1 prohra | 8 | 0 | 6595 |

Main částky a body potvrzeny ve všech třech vizuálně ověřených verzích ATP losu DXB24-1/2/3. Q částky shodné v ročníkových tabulkách DXB24-16/17; nezávislost jejich původu není prokázána. TennisTemple označuje postup jako Q3, ale jde o dvě hraná kola a postup po Q2, doložený pořadatelským OOP. Body odpovídají ATP předpisu ROT24-16. P* = primární Q finanční tabulka zatím chybí. Nominální Main 2195370 USD, Q 99800 USD, celkem 2295170 USD. Total financial commitment 3113270 USD (ATP originály); sekundární celková turnajová dotace 2941785 USD, ITF uvádí jako prize money 3113270 USD, což odpovídá financial commitment. Tyto veličiny nemíchat s odměnami mužské dvouhry. Q postupující pobírají Main odměnu podle výsledku.

### 7. Kontrola a mezery

I/T/H/D/R/B doloženy. E*: uzávěrky odvozené, původní acceptance lists/DS, Q cutoff a čas losu nedohledány. P*: Q finanční tabulka sekundární shoda; Z*: tři originální Main verze a OOP Q2, 26.2., QF (vždy jedna strana) vizuálně ověřeny; ATP Day 2 text dostupný, screenshot 403; původní Q PDF nedostupné. Úplný původní OOP Q1 a R16 nezískán. Žádné PDF hashe netvrdíme. Kontrola kvót, 8/8 seedů, 31/12 zápasů, denního součtu a finanční aritmetiky prošla. Další Santiago 2024. Bez runtime změn.

### 8. Zdroje (DXB24)

- DXB24-1: [ATP výsledkový Main los](https://www.protennislive.com/posting/2024/495/mds.pdf), str. 1 vizuálně.
- DXB24-2: [pořadatel, Main po kvalifikaci](https://dubaidutyfreetennischampionships.com/wp-content/uploads/2024/02/MDS-feb25400pm.pdf), str. 1 vizuálně.
- DXB24-3: [archiv předstartovního ATP Main](https://www.fantatennis.net/_downloads/53fc2e21f282eeebd629d74b99bc74a2), str. 1 vizuálně.
- DXB24-5: [pořadatel 24.2., Main los](https://dubaidutyfreetennischampionships.com/atp-500-draw-adds-excitement-and-intrigue-to-2024-dubai-duty-free-tennis-championships/), datum a identita 32. ročníku.
- DXB24-6: [ATP předturnajový přehled 2024](https://www.atptour.com/en/news/dubai-2024-history-draw-schedule), indexovaný text, přímé otevření 403; datum/hodina plánovaného losu, Q, Main a finále.
- DXB24-7: [pořadatelský OOP Q2 25.2.](https://dubaidutyfreetennischampionships.com/wp-content/uploads/2024/02/ORDER-OF-PLAY-SUNDAY-25-FEBRUARY-2024.pdf), vydán 24.2. 16:32, str. 1 vizuálně.
- DXB24-8: [pořadatelský OOP 26.2.](https://dubaidutyfreetennischampionships.com/wp-content/uploads/2024/02/OP-ATP-24feb24-4pm.pdf), skutečná hlavička vydání 25.2. 15:55, 7 R32, str. 1 vizuálně.
- DXB24-9: [ATP Day 2, 27.2.2024](https://www.atptour.com/-/media/1e1203b2b36c46f68b369d07416f8eed.pdf), text str. 1 a 4, screenshot 403; 9 R32, SE, LL.
- DXB24-10: [pořadatelský OOP QF 29.2.](https://dubaidutyfreetennischampionships.com/wp-content/uploads/2024/02/OP-ATP-Feb29.pdf), vydán 28.2. 16:23, str. 1 vizuálně.
- DXB24-11: [Sky 24.2.2024](https://www.skysports.com/tennis/scores-schedule/24-02-2024), Q1 mužské dvouhry; nepočítat čtyřhru.
- DXB24-12: [Sky 25.2.2024](https://www.skysports.com/tennis/scores-schedule/25-02-2024), Q2; [pořadatel 25.2.](https://dubaidutyfreetennischampionships.com/french-qualifier-arthur-cazaux-reaches-main-draw-of-2024-dubai-duty-free-tennis-championships/).
- DXB24-13: [ročníkový přehled ATP/WTA odděleně](https://en.wikipedia.org/wiki/2024_Dubai_Tennis_Championships), sekundární místo, dotace, vstupy; [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024).
- DXB24-14: [dobový přepis Main listu 31.1.2024](https://tennisuptodate.com/atp/atp-entry-list-2024-dubai-duty-free-tennis-championships-including-daniil-medvedev-andrey-rublev-hubert-hurkacz), časný seznam, nikoli původní ATP acceptance list.
- DXB24-15: [dobový úplný denní archiv](https://www.championat.ru/tennis/_atp/tournament/80026/calendar/), kola a počty, nikoli místní hodiny; [Tennis Explorer](https://www.tennisexplorer.com/dubai/2024/atp-men/) nezávislá kontrola.
- DXB24-16: [TennisTemple Q 2024](https://en.tennistemple.com/competitions/dubai/2024/draw-qualifications), všechny seedy, WC, sekce, ceny a body.
- DXB24-17: [sekundární ročníkový finanční rozpis](https://en.wikipedia.org/wiki/2024_Dubai_Tennis_Championships#Prize_money), mužský řádek, Q 11760/6595; nezaměňovat s ženskými řádky.
- DXB24-18: [ITF ročník](https://www.world.tennis/en/tournament/dubai/uae/2024/m-500-uae-2024-001/draws-and-results/), širší metadata termínu a financial commitment, přednost originálu ATP.
- Pravidla ROT24-15/16, LCB24-19; [původní Q PDF](https://www.protennislive.com/posting/2024/495/qs.pdf) nedostupné. Detail sheet nezískán.


## Santiago 2024

**Stav:** ROZPRACOVÁNO (8/9; P blokuje HOTOVO). Rešerše 2026-11-27. Dobový oficiální ATP Preview a více ročníkových finančních přehledů se liší o 5 USD u vítěze i finalisty; původní Main/Q PDF nedostupné. Nominální geometrie, plán kol, vstupní kvóty a body doloženy nezávisle na tomto rozporu.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Movistar Chile Open, mužská dvouhra | SCL24-1/2 |
| Kategorie / ATP ID | ATP 250 / 8996 | SCL24-1/2 |
| Ročník | pátý od obnovení roku 2020 dle ATP; 26. celkový dle sekundární chronologie | SCL24-1/3 |
| Dějiště | Club Deportivo Universidad Católica, San Carlos de Apoquindo, Court Central Jaime Fillol, Santiago, Chile | SCL24-1/4/5 |
| Povrch | venkovní antuka | SCL24-3/6/7 |
| Časové pásmo | America/Santiago, CLST UTC−03:00 | SCL24-8/9 |
| Ředitelka | Catalina Fillol | SCL24-10 |
| Měna | USD | SCL24-1/11/12 |

Rozdílné počítání ročníků není rozpor identity: ATP počítá aktuální řadu od 2020, sekundární přehled zahrnuje předcházející chilské akce. Historické série Santiago/Viña del Mar nepřepisovat současným názvem ani místem. Konkrétní typ antuky, míče, supervisor, referee a detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | referenční datum 2024-01-29, odvozené | §7.03; SCL24-7 |
| Q rank date | referenční datum 2024-02-05, odvozené | §7.03 |
| Nominální Main deadline | 2024-01-29 14:00 CLST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-02-05 14:00 CLST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální LE deadline | 2024-02-22 12:00 CLST (10:00 US Eastern) | odvozeno §7.04 |
| Q los | nejpozději 2024-02-23; čas neověřen | SCL24-8 |
| Main los | 2024-02-24 odpoledne; přesná hodina neověřena | SCL24-9/13 |
| Q | 2024-02-24–25, plán od 12:00 | SCL24-4/5/8 |
| Main | 2024-02-26–2024-03-03 | SCL24-1/2/4/5 |
| Singlové finále | 2024-03-03 19:00 CLST, plán | SCL24-1/4/5 |

Přepis Main entry listu SCL24-7 (31.1., aktualizace 2.2.) uvádí posledního z 18 vyjmenovaných DA Coriu s rankingem 103. Nejde o důkaz konečného cutoff nebo přesné hodiny původní akceptace. Q cutoff, originální acceptance lists, DS a přesné časy losování nedostupné. Datum Q losu nejpozději 23.2. vychází z večerní dobové zprávy se zveřejněnými dvojicemi, nikoli z odvozené kalendářní zvyklosti.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-02-24 | 8 |
| Q2 | 2024-02-25 | 4 |
| R32 | 2024-02-26–27 | 12 (4+8) |
| R16 | 2024-02-28–29 | 8 (4+4 pozorováno) |
| QF | 2024-03-01 | 4 |
| SF | 2024-03-02 | 2 |
| F | 2024-03-03 | 1 |

Dobový plán zveřejněný 22.2. v SCL24-4 a shodný přehled SCL24-5 (pravděpodobný společný zdroj) stanoví dvoudenní Q, R32 pondělí/úterý, R16 středa/čtvrtek, páteční QF, sobotní SF a nedělní finále. Uvádí 6/11/8/7/6 denních zápasů po–pá včetně čtyřhry, nikoli počty mužských singlů; např. pondělní dobový program SCL24-14 explicitně má 4 singles a 2 doubles. Z 12 R32 tedy 4+8, potvrzeno celým výsledkovým denním soupisem SCL24-15. R16 4+4 podle skutečného soupisu; kompletní prvotní předturnajový singlový OOP středy a čtvrtka nebyl získán, takže přesné denní rozdělení R16 není nezávisle potvrzené jako původní plán. Okna kol jsou doložena. Q1 osm plánovaných dvojic a tři kurty v dobovém přepisu SCL24-16; Q2 čtyři postupy potvrzuje ATP SCL24-17. Pátek od 14:00, sobota singlové SF od 18:00 po doubles finále, neděle 19:00 pouze singlové finále. Nominál 2+7 dní bez plánovaného překryvu, 39 zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA (včetně případné NG rezervy) | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28 přímo v dobovém přepisu SCL24-7 a pravidlech ATP 16.2. SCL24-18. Nevyužité rezervy se vracejí do DA. Původní nominální tři WC včetně tehdy oznámeného Čiliće nebyly konečná jména: ATP Preview výslovně označuje Darderiho, Fonsecu a Passara jako WC. ATP Preview dále uvádí čtyři kvalifikanty, dva LL a jedno SE Navoneho; jeho současnou evidenci v předstartovním soupisu nelze vydávat za potvrzení skutečně odehraného utkání (viz oddíl 5). Výsledkový pavouk SCL24-19/20 potvrzuje osm seedů a čtyři BYE na pozicích 2/10/23/31, 28 účastníků a 27 utkání. 12+8+4+2+1=27.

Q 14 DA + 2 WC podle §7.08 E.1 a předstartovního přepisu celého Q losu SCL24-16: všech osm seedů včetně Huga Delliena [4], WC Buse a Soto, Bagnis [6/Alt] a další Alt. Výsledkový soupis SCL24-19/21 má sedm označených seedů (Hugo Dellien v Main, Q místo obsadil Murkel Dellien). Tuto výjimku nelze převést na sedm nominálních seedů. Buse a Soto potvrzeni jako WC v dobovém přepisu; Tennis Abstract u Buse status neuvádí. Čtyři sekce po čtyřech, 8+4=12 zápasů, čtyři vítězové. Dva následní Main LL nejsou pátý a šestý řádný kvalifikant. Originální Q PDF není dostupné, geometrie doložena soudobým úplným přepisem a výsledky.

### 5. Dobová pravidla a návaznosti

ATP §7.03/7.04/7.08/7.09/7.10/7.14–18/7.20, verze kapitoly VII z 16.2.2024 SCL24-18, tištěné strany 129–150 a 164–165 pro vstupy, složení a nasazení; BO3 tiebreak sety. ATP Preview SCL24-1 přímo potvrzuje nulové body při první prohře po BYE v R16, nikoli zrušení R16 odměny. Q body podle ROT24-16 a opravy 16.2. z LCB24-19. V uvedeném rulebooku §7.08 C.3 výslovně náleží do challengerové sekce; předchozí zmínku o změně tohoto ustanovení v LCB24 nepovažovat automaticky za pravidlo ATP Tour. Pro ATP Tour používat §7.03, §7.04 a §7.08 E.1 a další příslušné články samostatně. Únorové novely a ES podle data účinnosti, ne retroaktivně.

ATP zpráva 25.2. SCL24-13 výslovně potvrzuje plánovaný SE vstup Mariana Navoneho po Rio; očekávaný první zápas s Varillasem. Ve skutečném pavouku SCL24-19 se místo něj objevuje LL Comesaña; Navone neodehrál Main zápas. ATP Day 1 stále uvádí SE Navoneho spolu s LL Comesañou a Bagnisem; soupis národností na stejné straně již Navoneho nezahrnuje. Oddělit původní SE a konečnou účast, neodvozovat extra místo.

**Next Gen:** v týdnu Acapulco/Dubai/Santiago byly tři ATP akce, pouze Santiago ATP 250. §7.04 (tištěná str. 137) a §7.08 B.1.c (str. 147) verze 16.2. výslovně upravují NG rezervy pro týdny se třemi akcemi, způsobilost hráčů narozených 2004 a později a rankingové hranice, nevyužité místo se vrací na dalšího podle rankingu. Jedno Main a dvě Q příležitosti pro způsobilé hráče Top 250 není důkaz, že právě v Santiago byly využity. Fonseca je v oficiálních ATP notes pořadatelská WC, nikoli doložený NG vstup. Q Buse je WC v předturnajovém přepisu. Originální listina s NG označením ani doklad o propadu rezervy nebyly získány; nominální počet zůstává 28 a 16, individuální alokace R* otevřená. Znovu prověřit při získání původní acceptance listiny.

### 6. Body a odměny (USD) — rozpor P

| Výsledek | Nominální příjemci | ATP body | ATP Preview SCL24-1 | Ročníkové přehledy SCL24-11/12/20/22 |
|---|---:|---:|---:|---:|
| Vítěz | 1 | 250 | 100635 | 100640 |
| Finalista | 1 | 165 | 58700 | 58705 |
| SF | 2 | 100 | 34510 | 34510 |
| QF | 4 | 50 | 19995 | 19995 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 11610 | 11610 |
| R32 | 12 | 0 | 7095 | 7095 |
| Q postupující | 4 | 13 | v notes není Q tabulka | 0 samostatně |
| Q2 prohra | 4 | 7 | v notes není Q tabulka | 3550 |
| Q1 prohra | 8 | 0 | v notes není Q tabulka | 1935 |

Main ATP Preview (str. 1) 100635/58700 USD. Dobové nezávisle publikované zprávy před i po turnaji SCL24-11/22, historické rozpisy SCL24-12 a výsledkový archiv SCL24-20 uvádějí 100640/58705. Nelze rozhodnout, zda ATP Preview obsahuje překlep či pozdější úpravu nebo sekundární zdroje používají jiný zaokrouhlený rozpis. Rozdíl je 5 USD u každé z prvních dvou cen, 10 USD celkem. ATP Preview je silný primární doklad původně publikovaného plánu, ale bez originálního losu/DS a při rozsáhlé ročníkové shodě proti němu nepovyšujeme P na HOTOVO. Nezaměňovat s Delray, které má originální Main 100635/58700, ani s Aucklandem, kde je jiný nevyřešený Q rozpor.

Q 3550/1935 USD shodně v SCL24-12/20/22; Q body v dobovém předpisu. Q postupující nemají samostatnou nominální Q odměnu; LL může dostat Q odměnu navíc k Main (skutečný součet 10645 USD pro LL v SCL24-20), nepromítat historický dodatečný payout do nominálního modelu. Nominální Main varianta A 486355 USD, varianta B 486365 USD; Q kandidát 29680 USD; singlový součet A 516035 USD / B 516045 USD. Ani jeden celek dosud není certifikován. Turnajová dotace 661585 USD a total financial commitment 742350 USD jsou samostatné veličiny, ne singlový součet.

### 7. Kontrola a mezery

I/T/H/E*/D/R*/B/Z* doloženy; P zůstává blokující rozpor. H: všechny termíny kol doloženy, R16 denní split pouze výsledkový. E*: odvozené termíny uzávěrek, chybějí originální acceptance lists/DS a časy losování. R*: NG alokace nedoložena, předpis ano. Z*: ATP Preview a rulebook 16.2. textově ověřeny, screenshoty 403; žádný Main/Q originál nebyl získán ani vizuálně zkontrolován. Neuvádět neexistující SHA-256. Kontrola kvót, 8/8 seedů, 27/12 zápasů, denních součtů a obou finančních variant prošla. Opakovaná rešerše: přímé ATP PDF, dobové odkazy SuperTennis, ATP notes, více dobových a archivních finančních zdrojů, hledání alternativních Main PDF kopií bez získání ročníkového originálu. Vyžaduje další primární doklad; poté pokračovat Indian Wells 2024, první ATP Masters 1000 v registru. Bez runtime změn.

### 8. Zdroje (SCL24)

- SCL24-1: [ATP Preview & Day 1, 26.2.2024](https://www.atptour.com/-/media/0d8c7cea020848e1b5007515dbef1ab5.pdf), str. 1, text, screenshot 403; Main ceny/body, nedělní finále, WC/Q/LL/SE.
- SCL24-2: [ATP série 8996](https://www.atptour.com/tournaments/santiago/8996/overview), [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), ročníková identita/termíny; aktuální název nepřenášet zpět.
- SCL24-3: [ročníkový sekundární přehled](https://en.wikipedia.org/wiki/2024_Chile_Open), 26. historický ročník, venkovní antuka, dotace.
- SCL24-4: [Mall Sport, předturnajový program 22.2.](https://www.mallsport.cl/noticias/se-viene-el-movistar-chile-open-2024-con-la-presencia-de-los-mejores-tenistas-del-mundo/), okna všech kol; součty včetně doubles.
- SCL24-5: [Portal Metropolitano, předturnajový program](https://portalmetropolitano.cl/en-que-horarios-se-disputara-el-movistar-chile-open-2024/), stejné okno a session, pravděpodobně stejný původ jako SCL24-4.
- SCL24-6: [TNT Sports 23.2.](https://tntsports.cl/institucional/Chile-Open-por-TNT-Sports--Se-inicia-la-accion-del-ATP-250-de-Santiago-20240223-0020.html), Q a Main, místo; [SuperTennis 24.2.](https://www.supertennis.tv/News/Atp/santiago-atp-qualificazionimain-draw-tabellone), povrch, financial commitment, odkazy na originální losy.
- SCL24-7: [dobový Main entry list 31.1.](https://canaltenis.com/entry-list-chile-open-2024/), 18 DA, 3 WC, 2 SE, 1 LE, 4 Q.
- SCL24-8: [ADN Radio 23.2., Q los](https://www.adnradio.cl/2024/02/23/este-sabado-comienza-la-qualy-del-chile-open-2024/), 16 hráčů a 4 postupy, CLST.
- SCL24-9: [ADN Radio 24.2., Main los odpoledne](https://www.adnradio.cl/2024/02/24/con-todos-los-nacionales-en-el-mismo-lado-del-cuadro-asi-quedo-el-main-draw-del-chile-open-2024/).
- SCL24-10: [La Tercera 2024, ředitelka Catalina Fillol](https://www.latercera.com/el-deportivo/noticia/la-particular-defensa-de-catalina-fillol-a-las-canchas-del-open-santiago-es-una-superficie-mas-desafiante-hace-que-los-partidos-sean-mas-entretenidos/6Q356BAHFNF77FF5KKKDTEA2EA/?outputType=base-amp-type).
- SCL24-11: [T13 po finále](https://www.t13.cl/noticia/deportes13/el-millonario-premio-que-gano-alejandro-tabilo-tras-su-caida-en-la-final-del-chile-open-2024), obě rozdílné ceny; [24horas před turnajem 23.2.](https://www.24horas.cl/amp/deportes/tenis/el-millonario-premio-economico-que-entregara-el-chile-open), 100640.
- SCL24-12: [Canal Tenis ročníkový rozpis](https://canaltenis.com/el-prize-money-del-chile-open/), [TennisCompanion 2024 USD sloupec](https://tenniscompanion.org/prize-money/chile/), Main alternativa, Q shoda.
- SCL24-13: [ATP 25.2., Main los a Navone SE](https://www.atptour.com/es/news/santiago-2024-jarry-previa-cuadro).
- SCL24-14: [ADN Radio 26.2., pondělní program](https://www.adnradio.cl/2024/02/26/este-lunes-comienza-el-chile-open-2024-quienes-juegan-a-que-hora-y-donde-ver-los-partidos-en-vivo/), 4 singles + 2 doubles.
- SCL24-15: [dobový denní výsledkový soupis](https://canaltenis.com/resultados-atp-santiago-2024/), počty obou fází a dny; [ATP Day 6, 2.3.](https://www.atptour.com/-/media/561f52fa5131402e9829760e394c0866.pdf), text, screenshot 403.
- SCL24-16: [dobový úplný Q los a program 24.2.](https://www.livetennis.it/post/407412/atp-500-acapulco-e-atp-250-santiago-il-tabellone-di-qualificazione-con-il-programma-completo-cinque-azzurri-al-via/), všech 8 seedů, 2 WC, Q1 tři kurty.
- SCL24-17: [ATP 25.2., Q výsledky](https://www.atptour.com/es/news/santiago-2024-domingo-previa-burruchaga).
- SCL24-18: [ATP Rulebook VII, revize 16.2.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_16feb.pdf), text, screenshoty 403; §7.03, §7.04, §7.08 B/E, §7.14–16 a NG, tištěné str. 137/147/149–150/165.
- SCL24-19: [Tennis Abstract Main/Q 2024](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024Santiago), skutečný výsledkový stav a Alt/LL; [ročníkový pavouk](https://en.wikipedia.org/wiki/2024_Chile_Open_%E2%80%93_Singles).
- SCL24-20: [Open Era Rankings, ročník 2024, Main a Q](https://openerarankings.com/Draws?DrawType=MS&Highlight=M00000085&Round=1&tID=24873), ceny, BYE a LL; sekundární.
- SCL24-21: [Tennis Explorer Q](https://www.tennisexplorer.com/santiago/2024/atp-men/?phase=qualification), 7 skutečných označených seedů, oba WC, čtyři sekce, 12 utkání.
- SCL24-22: [Tennis Infinity dobový finanční přehled](https://tennis-infinity.com/atp/2024-chile-open-santiago-atp-prize-money-points-overview), [TennisUpToDate dobový finanční přehled](https://tennisuptodate.com/atp/atp-prize-money-and-points-breakdown-2024-chile-open-santiago-with-661585-on-offer), alternativa Main; [český sekundární rozpis](https://web.kurzy.cz/wiki/Chile_Open_2024), indexovaný text 3550/1935 Q, otevření timeout.
- [Původní Main PDF](https://www.protennislive.com/posting/2024/8996/mds.pdf) a [Q PDF](https://www.protennislive.com/posting/2024/8996/qs.pdf) nedostupné; DS nezískán.


## Indian Wells 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/P/Z s omezeními). Rešerše 2026-11-27. První Masters 1000 v registru, 96 účastníků v pavouku o 128 pozicích. Předstartovní a výsledkový originální ATP Main vizuálně ověřeny, každý na dvou stránkách; původní Q los nedostupný, Q finanční odměny ze shodných sekundárních zdrojů.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | BNP Paribas Open, mužská dvouhra | IW24-1/2/3 |
| Kategorie / ATP ID | ATP Masters 1000 / 404 | IW24-1/3/18 |
| Ročník | 47. dle ATP preview, 50. dle sekundárního historického přehledu | IW24-3/17 |
| Dějiště | Indian Wells Tennis Garden, Indian Wells, Kalifornie, USA | IW24-3/4 |
| Povrch | venkovní tvrdý, Plexipave | IW24-1/2/3 |
| Časové pásmo | America/Los_Angeles; PST UTC−08:00 do 10.3. 02:00, poté PDT UTC−07:00 | lokalita a americké DST 2024 |
| Ředitel | Tommy Haas | IW24-5/6 |
| ATP supervisor | Carlos Sanches; Main OOP navíc Zsolt Beda, Cedric Mourier, Ali Nili | IW24-1/5/6 |
| Referee / tour manager | Gerry Armstrong / Thomas Schrader, Denis Zivkovic (Q OOP) | IW24-5/6 |
| Měna | USD | IW24-1/2 |

Odlišné počítání ročníků zachovat zdrojově, bez vynucení jedné historické genealogie. Turnaj zahrnuje WTA a další disciplíny, ty nejsou mužskou dvouhrou. Míče a detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-02-05 | IW24-7 |
| Q rank date | 2024-02-12 | IW24-7 |
| Nominální Main deadline | 2024-02-05 09:00 PST (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-02-12 09:00 PST (12:00 US Eastern) | §7.03, odvozeno |
| Main los | 2024-03-04 15:00 PST, plán ATP | IW24-3 |
| Q los | nejpozději 2024-03-03 18:41 PST, vydání OOP; skutečný čas losu neověřen | IW24-5 |
| Q1 Alt sign-in deadline | 2024-03-04 09:30 PST | IW24-5 |
| Q | 2024-03-04–05, od 10:00 PST | IW24-3/5/8 |
| Main | 2024-03-06–17 | IW24-1/2/3/4 |
| Main LL sign-in 6.3. | 10:30 PST | IW24-6 |
| Singlové finále | 2024-03-17 ne před 14:00 PDT | IW24-3/4 |

Dobový přepis listiny IW24-7 uvádí původní cutoffs 76 Main / 140 Q. Obě originální Main verze uvádějí Zapata Miralles 79 při deadline i v losu. Alternativní přepis IW24-9 uvádí Main cutoff 75. Rozdíl údajů o výchozím cutu nepřepisovat bez původní acceptance listiny, nejde o rozpor nominální kapacity. Q konečný cutoff nezískán. Uzávěrky odvozené z §7.03, nikoli nezávislé timestampy. Kalifornský čas se v průběhu turnaje mění, neukládat jediný fixní offset pro všechny dny.

### 3. Nominální harmonogram

| Kolo / den | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-03-04 | 24 |
| Q2 | 2024-03-05 | 12 |
| R128 | 2024-03-06–07 | 32 (16+16) |
| R64 | 2024-03-08–09 | 32 |
| R32 | 2024-03-10–11 | 16 |
| R16 | 2024-03-12–13 | 8 |
| QF | 2024-03-14 | 4 |
| bez mužské dvouhry | 2024-03-15 | 0 |
| SF | 2024-03-16 | 2 |
| F | 2024-03-17 | 1 |

ATP plán Q 4.–5.3., nikoli 3.–5.3. (rozšíření společné akce na neděli se týká WTA Q; IW24-3/4). Originální OOP Q1 vydaný 3.3. 18:41 (IW24-5) má 24 ATP zápasů, odděleně osm WTA zápasů; počítat jen mužské. Pořadatel 5.3. výslovně potvrzuje 12 Q2 zápasů a 12 postupujících (IW24-8). Originální Main OOP 6.3., vydaný 5.3. 14:02 (IW24-6), obsahuje 16 ATP R128 včetně placeholderů dosud nepřiřazených Q, druhá polovina tedy nominálně 16 následující den. ATP dobová zpráva o dešti potvrzuje pouze devět dokončených ATP zápasů první den; zbytek se přesunul nebo dohrával, nepřepisovat původní 16+16. Plánovaná okna R64, R32, R16 doložena dobovým přehledem IW24-10; přesné denní rozdělení těchto vícedenních kol necertifikováno bez původních OOP obou dnů. Záměr 2024 nově shromáždit všech osm ATP/WTA QF do čtvrtka 14.3. výslovně potvrzuje pořadatel, pátek 15.3. je vyhrazen mužské čtyřhře a ženským SF; žádné mužské singlové kolo, nikoli přestávka celého turnaje. Mužské SF v sobotu, F v neděli. Nominál Q 2 dny + Main 12 kalendářních dní (11 hracích pro mužskou dvouhru) = 14 dní, bez plánovaného překryvu; 95+36=131 zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 128 / 96 | 48 / 48 (12 sekcí po 4) |
| Základní DA při rezervovaném SE | 78 | 43 |
| SE rezerva | 1 (0 použitých dle listiny) | 0 |
| WC | 5 | 5 |
| Řádné Q postupy | 12 | 12 |
| Nasazení | 32 | 24 |
| BYE | 32, všichni nasazení | 0 |
| Kola / zápasy | 7 / 95 | 2 / 36 |
| Formát | BO3 setů | BO3 setů |

ATP §7.08 B.1.a a §7.10 B (IW24-11): 78 DA + 1 SE + 5 WC + 12 Q = 96; při nevyužitém SE 79 DA. Dobový přepis entry listu IW24-7 přesně 79 DA, 5 WC, 12 Q, 0 SE; nejde o obecně zrušenou SE rezervu. Bez ATP 250 LE a bez ATP 500 A+ WC. Předstartovní Main IW24-2 obě strany vizuálně: 32 seedů a 32 BYE, 12 Q placeholderů (3/13/19/20/45/68/77/84/107/115/123/124), WC 5/14/53/70/83. ATP předem oznámila právě pět Main WC a pět Q WC (IW24-12). Menšík má tentokrát v Main WC, nikoli NG nebo SE jako v Doha/Dubai. PR v DA není samostatná dodatečná kvóta. Výsledkový originál IW24-1 uvádí tři LL (Nardi, Nagal, Rodionov), včetně změny původní seed pozice po odstoupení Etcheverryho; nominální 32 seedů/12 Q/32 BYE tím neměníme. Main 32+32+16+8+4+2+1=95. R128 neznamená 128 přijatých hráčů.

Q 43 DA + 5 WC, 48 hráčů, 24 seedů dle §7.08 E.1 a §7.15, dvanáct sekcí po čtyřech, dva seedy v každé podle §7.08 a pravidel nasazování Q. Q1 OOP všech 24 dvojic a 5 WC; pořadatelské oznámení Q2 potvrzuje 12 postupů. Sekundární úplný Q pavouk IW24-13 kontroluje 48 pozic a 36 výsledkových uzlů. Původní Q los nedostupný; žádný důkaz výjimky z nominálního nasazení. Q 24+12=36. Q není jeden 64pozicový pavouk s 16 BYE, ale 12 samostatných čtyřhráčových sekcí.

### 5. Dobová pravidla a rankingové výjimky

ATP §7.03, §7.08 B.1.a/E.1, §7.10, §7.15–18, §7.20–21, verze VII 16.2.2024 IW24-11. Pro SE do Masters 1000 musí předchozí kvalifikovaná soutěž být ATP 500, ATP Masters 1000 nebo Grand Slam; samotná účast v předcházejícím ATP 250 není standardním kvalifikačním důvodem pro SE do Masters. Jedna nevyužitá rezerva se vrací do DA. Všichni 32 seedy mají BYE, Q 24 seedů, 12 Q vítězů; výměny hráčů po začátku Q dle pravidel LL. BO3 tiebreak sety, nepřebírat GS BO5. Předpis §7.08 C.3 z LCB24-19 se týká Challengeru, nikoli této ATP Tour akce.

Rankingová kapitola IX ve verzi 16.2.2024 (IW24-14, §9.03 G.2–5, tištěné str. 253–254) přímo potvrzuje:
- 96členný Masters má vlastní řádek bodů; 48/56členný Masters má jiné Q body a nesmí používat automaticky stejnou tabulku.
- Při prohře v prvním hraném kole po BYE přidělit body prvního kola (10, nikoli standardních 30 za R64); finanční odměna se neztotožňuje s bodovým ziskem.
- WC hráč v Masters 1000 získává body od druhého kola; při prohře v R128 tedy 0, běžný DA získá 10.
- Q postup 20 bodů navíc k Main výsledku, prohra v Q2 10, v Q1 nula. Nezaměňovat s WTA ani s 16/8 ze sekundární tabulky TennisTemple (IW24-15). Závazný je dobový ATP rankingový předpis.
- Masters 1000 povinné turnaje a způsob započtení do 52týdenního rankingu jsou samostatná pravidla §9.03 A/B, nikoli změna počtu bodů za jednotlivé kolo. Žádná implementace v tomto registru.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 1000 | 1100000 |
| Finalista | 1 | 650 | 585000 |
| SF | 2 | 400 | 325000 |
| QF | 4 | 200 | 185000 |
| R16 | 8 | 100 | 101000 |
| R32 | 16 | 50 | 59100 |
| R64 | 32 | 30 (10 při prohře po BYE) | 42000 |
| R128 | 32 | 10 (WC 0) | 30050 |
| Q postupující | 12 | 20 | 0 samostatně |
| Q2 prohra | 12 | 10 | 14400 |
| Q1 prohra | 24 | 0 | 7800 |

Main oba původní ATP losy IW24-1/2 vizuálně, Q body primární IW24-14 a předsezonní ATP update; Q ceny 14400/7800 USD shodně IW24-15/16/17, nezávislost vzniku tabulek neprokázána. P* do získání originální Q finanční tabulky. Pozor na chybný údaj TennisTemple 16/8 bodů a A$ u Stevegtennis: částky ano, body/měna mají přednost z ATP a USD turnajového kontextu. Nominální Main 7134200 USD, Q 360000 USD, celkem 7494200 USD; 96 Main příjemců, 36 nepostupujících Q příjemců. Q postupující odměna dle Main výsledku, nikoli další nominální Q odměna. Skutečné LL payout či odstoupení vyžadují samostatný předpis a nejsou zahrnuty. Financial commitment 12418990 USD v originále ATP; pořadatelské oznámení 19M USD zahrnuje společnou akci a jiné složky; nezaměňovat se singlovým součtem.

### 7. Kontrola a mezery

I/T/D/R/B doloženy. H* všechna okna, Q1/Q2 a R128 16+16 doloženy; původní denní dělení R64/R32/R16 neověřeno. E* referenční data listiny doložena, uzávěrky odvozeny, přesný čas Q losu, konečný cutoff, původní acceptance lists/DS chybí. P* Main originál, Q sekundární shoda. Z* obě strany původního ATP Main z federálního archivu RFET a předstartovní kopie Raquetc vizuálně, OOP Q1 a Main 6.3. vizuálně; alternativní Main archiv datocms textově, screenshot 404, kapitoly VII/IX textově, screenshot VII 403 a IX nepodporován. Původní ATP Q nedostupný; nevymýšlet SHA-256. Kontrola 96/48, 32/24 seedů, 32/0 BYE, 12 Q, 95/36 zápasů, kvót a finanční aritmetiky prošla. Další Miami 2024; bez runtime změn.

### 8. Zdroje (IW24)

- IW24-1: [výsledkový originální ATP Main v RFET archivu](https://www.rfet.es/descargar/file-noticias-adjuntos/4906_Documento/cuadro-individual-atp-1000-indian-wells-usa.pdf), obě stránky vizuálně.
- IW24-2: [předstartovní originální ATP Main](https://www.raquetc.com/wp-content/uploads/2024/03/ATP-Masters-1000-Indian-Wells-2024-quadro-principal.pdf), obě stránky vizuálně; [alternativní datocms kopie](https://www.datocms-assets.com/110926/1709600551-msd.pdf), text, screenshot 404.
- IW24-3: [ATP předturnajový přehled 26.2.2024](https://www.atptour.com/en/news/indian-wells-2024-atp-masters-1000-history-draw-schedule), indexovaný text, otevření 403, termíny a plán losu.
- IW24-4: [pořadatel, předsezonní oznámení změn programu a prize money](https://bnpparibasopen.com/news/2024-bnp-paribas-open-prize-money-competition-schedule-changes), QF 14.3., pátek bez mužských singlů, SF 16.3., F 17.3. ne před 14:00.
- IW24-5: [originální OOP Q1 4.3.](https://www.datocms-assets.com/110926/1709527753-op-20240304.pdf), str. 1 vizuálně; vydán 3.3. 18:41, 24 ATP Q1.
- IW24-6: [originální OOP Main 6.3.](https://www.datocms-assets.com/110926/1709691958-op-20240306.pdf), str. 1 vizuálně; vydán 5.3. 14:02, 16 R128.
- IW24-7: [dobový přepis entry listů 28.2.](https://www.tennisteen.it/entry-list/atp/24130-atp-entry-list-4-17-marzo-2024.html), Main/Q řádky 80–234.
- IW24-8: [pořadatel 5.3., všech 12 Q postupů](https://bnpparibasopen.com/news/2024-indian-wells-qualifiers-ethan-quinn-leads-the-way).
- IW24-9: [dobová aktualizace Main/Q listů 3.3.](https://www.livetennis.it/post/406065/masters-1000-indian-wells-la-situazione-aggiornata-md-e-qualificazioni-gaio-entra-nelle-quali-di-indian-wells/), rank dates a odlišný Main cutoff.
- IW24-10: [dobový kompletní plán kol](https://www.etonline.com/how-to-watch-indian-wells-2024-online-schedule-channel-and-bnp-paribas-open-livestream-221127), [ATP 7.3. dešťové odklady](https://www.atptour.com/en/news/rain-indian-wells-2024-day-1-wednesday), [dobový denní výsledkový soupis](https://canaltenis.com/resultados-atp-indian-wells-2024/).
- IW24-11: [ATP Competition VII 16.2.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_16feb.pdf), §7.08, §7.10, §7.15–18, text, screenshot 403.
- IW24-12: [ATP oznámení pěti Main i pěti Q WC](https://www.atptour.com/en/news/mensik-indian-wells-2024-wild-cards), indexovaný text, přímé otevření 403.
- IW24-13: [dobový Q pavouk](https://canaltenis.com/cuadro-atp-indian-wells-2024/), [Tennis Explorer Q](https://www.tenisportal.cz/indian-wells/2024/atp-muzi/?phase=qualification).
- IW24-14: [ATP Ranking IX 16.2.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-9_pepperstone-atp-rankings_16feb.pdf), §9.03 G.2–5 str. 253–254, text; screenshot nepodporován. [ATP předsezonní ranking update](https://www.atptour.com/en/news/2024-rankings-points-update).
- IW24-15: [TennisTemple Q 2024](https://da.tennistemple.com/competitions/indian-wells/2024/draw-qualifications), správné Q částky 14400/7800, chybné 16/8 body; [Stevegtennis](https://www.stevegtennis.com/draw-results/atp/BNP%20Paribas%20Open%20-%20Indian%20Wells/2024), chybné A$.
- IW24-16: [dobový Sporting News](https://www.sportingnews.com/uk/tennis/news/watch-indian-wells-tennis-2024-schedule-channel-prize-money/497790a441808e99d83234c1), [dobový Tennis365](https://www.tennis365.com/tennis-features/2024-indian-wells-open-novak-djokovic-carlos-alcaraz-rafael-nadal-play-dates-draw-prize-money), shoda Q.
- IW24-17: [ročníkový přehled 2024](https://en.wikipedia.org/wiki/2024_BNP_Paribas_Open), Q ceny a body, sekundární chronologie; souhrnné částky v záhlaví a těle nejsou totožné, nepoužívat jako singlový součet.
- IW24-18: [ročníková identita 2024-404](https://goatstats.tennis/tournament/2024-404), [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024); přímý [ATP Main](https://www.protennislive.com/posting/2024/404/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/404/qs.pdf) nedostupné, Main originály dostupné v IW24-1/2.


## Miami 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/Z s doplňkovými omezeními). Rešerše 2026-11-27. Druhý Masters 1000 v registru. Obě stránky předstartovního i výsledkového ATP Main losu a originální ATP Q los vizuálně ověřeny, včetně všech bodů a peněžních odměn. Odlišná finanční a časová struktura oproti Indian Wells, přestože počet účastníků je stejný.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Miami Open presented by Itaú, 39. ročník, mužská dvouhra | MIA24-1/2/3/4 |
| Kategorie / ATP ID | ATP Masters 1000 / 403 | MIA24-1/3 |
| Dějiště | Hard Rock Stadium, Miami Gardens, Florida, USA | MIA24-4/6 |
| Povrch | venkovní tvrdý, Laykold | MIA24-1/2/3 |
| Časové pásmo | America/New_York, EDT UTC−04:00 | lokalita a datum |
| Ředitel | James Blake | MIA24-7/8/9 |
| ATP supervisors | Gerry Armstrong, Cedric Mourier, Hans-Juergen Ochs, Zsolt Beda | MIA24-1/3/7 |
| Referee / tour managers | Jorge Mandl / Konstantin Haerle, Nicolas Rakitin | MIA24-7/8/9 |
| Měna | USD | MIA24-1/2/3 |

ATP Day 1 počítá ročníky 1985–2019 a od 2021. Širší termíny společné akce zahrnují WTA, čtyřhru a další disciplíny; nepřenášet je na mužskou dvouhru. Míče a detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-02-19 | MIA24-5 |
| Q rank date | 2024-02-26 | MIA24-5 |
| Nominální Main deadline | 2024-02-19 12:00 EST (UTC−05:00) | §7.03, odvozeno |
| Nominální Q deadline | 2024-02-26 12:00 EST (UTC−05:00) | §7.03, odvozeno |
| Main los | 2024-03-18 13:00 EDT, plán ATP | MIA24-4 |
| Q los | před Q1 2024-03-18, přesná hodina a datum neověřeny | MIA24-3/10 |
| Q | 2024-03-18–19, ATP plán od 11:00 EDT | MIA24-4/6/10 |
| Main | 2024-03-20–31 | MIA24-1/2/4 |
| Main LL sign-in 21.3. | 10:30 EDT | MIA24-7 |
| Singlové finále | 2024-03-31 ne před 15:00 EDT (ATP plán) | MIA24-4/11 |

Rank dates a čas uzávěrek odlišit od doloženého času podání přihlášky. V únoru platí EST, v březnovém turnaji EDT. Dobový přepis MIA24-5 uvádí původní Main cutoff 76 a Q 134. Předstartovní i výsledkový Main originál mají Soonwoo Kwon s PR 80 jako last DA při deadline i v losu; Q originál Elias Ymer 158. Jde o odlišné publikované údaje/stavy, ne sjednocený cutoff. Originální acceptance listiny nebyly získány. Dřívější únorový návštěvnický program MIA24-6 uvádí start Q 10:00 a zahájení finálové session 12:30; pro nominální čas mužského finále má přednost explicitní ATP Day 1 (15:00 nejdříve), nikoli zahájení společné session.

### 3. Nominální harmonogram

| Kolo / den | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-03-18 | 24 |
| Q2 | 2024-03-19 | 12 |
| R128 | 2024-03-20–21 | 32 (16+16) |
| R64 | 2024-03-22–23 | 32 |
| R32 | 2024-03-24–25 | 16 |
| R16 | 2024-03-26 | 8 |
| QF | 2024-03-27–28 | 4 (2+2) |
| SF | 2024-03-29 | 2 |
| bez mužské dvouhry | 2024-03-30 | 0 |
| F | 2024-03-31 | 1 |

Předturnajový plán z 6.2. MIA24-6 potvrzuje dvě Q data, všechna okna prvních čtyř Main kol, čtvrteční QF, páteční SF, sobotu vyhrazenou jiným disciplínám a nedělní finále. Originální Q los MIA24-3 a dobový denní soupis MIA24-10/12 potvrzují dvě hraná kola 24+12. OOP 21.3. vydaný 20.3. v 15:49 (MIA24-7, vizuálně) obsahuje 16 mužských R128 (2 Stadium, 3 Grandstand, 3 Butch Buchholz, 2 Court 1, 2 Court 7, 2 Court 5, 2 Court 3); z celkových 32 tedy 16+16 při plánovaném dvoudenním R128. První den samostatný originální OOP nezískán. ATP 22.–23.3. dokládá významné dešťové odklady R64, skutečné pozdější dokončení se nepromítá do nominálního okna. Přesné původní denní dělení R64/R32 bez těchto odkladů není certifikováno. Všech osm R16 v úterý 26.3. potvrzeno plánem a dobovým soupisem MIA24-13. Oba originální OOP QF (vydány 26.3. 18:53 a 27.3. 18:14; MIA24-8/9) potvrzují dvě singlová čtvrtfinále v každý den na Stadium, neplést s ATP doubles. Dobový OOP SF v MIA24-14 potvrzuje páteční dvě SF. Sobota 30.3. nemá mužský singlový zápas; ATP Day 1 potvrzuje samostatné mužské finále v neděli ne před 15:00. Celkem 2 Q + 12 Main kalendářních dní, 11 hracích dní Main mužské dvouhry a 131 nominálních zápasů. Nejde o stejný harmonogram jako Indian Wells: Miami má R16 v jediném dni, QF ve dvou dnech a den bez mužských singlů až po SF.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 128 / 96 | 48 / 48 (12 sekcí po 4) |
| Základní DA při rezervovaném SE | 78 | 43 |
| SE rezerva | 1 (0 použitých podle listiny) | 0 |
| WC | 5 | 5 |
| Řádné Q postupy | 12 | 12 |
| Nasazení | 32 | 24 |
| BYE | 32, všichni nasazení | 0 |
| Kola / zápasy | 7 / 95 | 2 / 36 |
| Formát | BO3 setů | BO3 setů |

Dobový ATP §7.08 B.1.a/E.1 a §7.10 B (IW24-11): 78 DA + 1 SE + 5 WC + 12 Q = 96; nevyužité SE přechází do DA. Dobový přepis MIA24-5 explicitně 79 DA, 5 WC, 12 Q a 0 SE, Q 43 DA + 5 WC = 48. Předstartovní Main MIA24-2 vizuálně: 32 seedů, 32 BYE, 12 Q placeholderů 12/20/27/28/36/46/54/61/91/118/124/126, WC 13/44/70/100/115. Výsledkový Main MIA24-1 potvrzuje pět WC a 12 Q; po odstoupení seed 32 Corice se do původní seed pozice 8 přesunul Thompson [33], jeho původní pozice 77 připadla kvalifikantovi a na původní Q pozici 91 je LL Nishioka. ATP Day 1 MIA24-11 vysvětluje jeho LL vstup a uvádí 12 řádných Q a tři PR. Nejde o 33 nominálně nasazených ani o 13 řádných Q postupů. PR není nová kvóta. R128 má 32 skutečných hracích uzlů a 32 BYE; 32+32+16+8+4+2+1=95.

Originální Q los MIA24-3 na jedné straně: 48 pozic, 12 čtyřhráčových sekcí, 5 WC na pozicích 18/22/30/42/43, 24 nominálních seedů, seed 15 Lestienne vyškrtnut po odstoupení a Alt Kukushkin v pozici 40. Zachovat 24 nasazených v nominálu, ne 23 skutečně označených; 24+12=36 zápasů a 12 postupů. Pět Q WC nezaměňovat s pěti Main WC ani nezvyšovat kapacitu.

### 5. Dobová pravidla

Pro 96členný Masters platí pravidla doložená IW24-11/14: jedna SE rezerva, bez ATP 250 LE a bez ATP 500 A+ WC, Q dvanáct sekcí po čtyřech, dva nominální seedy v sekci, BO3 tiebreak sety, pravidla náhradníků a LL podle §7.09/7.16; rank dates a termíny podle §7.03. V únorové verzi §9.03 G jsou Q body 20/10/0; Main první prohra po BYE 10 místo 30 a držitel Main WC při prohře R128 0 bodů. ATP Preview str. 2 MIA24-11 má bodové výjimky označeny, Q los MIA24-3 přímo potvrzuje 20/10/0. Finanční odměna není ztotožněna s body. Předešlé označení hráče NG/SE nebo mediální označení #NextGenATP nezakládá automatickou NG rezervu v Miami: Shang je zde explicitně běžná Main WC, Coleman Wong Q WC a následně řádný Q, Menšík Q seed 4. Žádná další kapacita. Ostatní disciplíny a žebříčkové povinnosti Masters se evidují odděleně od singlového pavouka.

### 6. Body a odměny (USD)

| Výsledek | Nominální příjemci | ATP body | USD |
|---|---:|---:|---:|
| Vítěz | 1 | 1000 | 1100000 |
| Finalista | 1 | 650 | 585000 |
| SF | 2 | 400 | 325000 |
| QF | 4 | 200 | 185000 |
| R16 | 8 | 100 | 101000 |
| R32 | 16 | 50 | 59100 |
| R64 | 32 | 30 (10 při první prohře po BYE) | 34500 |
| R128 | 32 | 10 (WC 0) | 23250 |
| Q postupující | 12 | 20 | 0 samostatně |
| Q2 prohra | 12 | 10 | 13500 |
| Q1 prohra | 24 | 0 | 7000 |

Main tabulka přímo v obou vizuálně ověřených verzích MIA24-1/2, shoda s ATP Day 1 MIA24-11. Q tabulka přímo v originálním Q losu MIA24-3, vizuálně. P bez hvězdičky. Nominální Main 6676600 USD, Q 330000 USD, celkem 7006600 USD; 96 Main příjemců a 36 nepostupujících Q příjemců. Financial commitment 10404205 USD ve všech originálech a celková turnajová dotace 8995555 USD dle ATP preview nejsou singlový součet; částka 8770480 USD v některých společných OOP bez jasně určené disciplíny není dokladem mužské singlové dotace. Oproti Indian Wells stejné body, ale Main R64 o 7500 USD a R128 o 6800 USD méně na hráče, Q2 o 900 a Q1 o 800 méně (IW24 Q údaje stále sekundární). Historické dodatečné LL payout nepatří do nominálního součtu.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy; H*: všechna okna doložena, denní dělení R128 a QF ověřeno, kompletní první OOP a původní R64/R32 denní splity před deštěm nezískány. E*: původní acceptance listy/DS a hodina Q losu chybí, uzávěrky odvozené; Z*: vizuálně ověřeny obě stránky výsledkového Main, obě stránky předstartovního Main, Q los a OOP 21./27./28.3.; ATP Day 1 str. 1/2 textově, screenshoty 403; přímé ATP preview otevření 403, indexovaný text. Žádné neověřené SHA-256. Kontrola 96/48, 32/24 seedů, 32/0 BYE, 12 Q postupů, 95/36 zápasů, nominálních vstupních kvót a peněz prošla. Další pracovní fronta Marrakech, Estoril a Houston 2024, před zahájením ověřit dobový kalendář. Bez runtime změn.

### 8. Zdroje (MIA24)

- MIA24-1: [ATP výsledkový Main los](https://www.protennislive.com/posting/2024/403/mds.pdf), obě stránky vizuálně ověřeny.
- MIA24-2: [předstartovní originální ATP Main v archivu Raquetc](https://www.raquetc.com/wp-content/uploads/2024/03/mds-4.pdf), obě stránky vizuálně.
- MIA24-3: [originální ATP Q los v pořadatelském CDN](https://s42493.pcdn.co/wp-content/uploads/2024/03/mQS.pdf), str. 1 vizuálně, úplný pavouk, seed 15 vyškrtnut, body a odměny.
- MIA24-4: [ATP předturnajový přehled 2024](https://www.atptour.com/en/news/miami-2024-atp-masters-1000-history-draw-schedule), indexovaný text, přímé otevření 403; [alternativní ATP URL](https://www.atptour.com/en/news/miami-2024-atp), [španělská verze](https://www.atptour.com/es/news/miami-2024-atp).
- MIA24-5: [dobový přepis listin 10.3.2024](https://www.tennisteen.it/entry-list/atp/24134-atp-entry-list-18-31-marzo-2024.html), řádky 66–215, rank dates, kvóty, původní cutoffs.
- MIA24-6: [předturnajový program 6.2.2024](https://www.miamilivingmagazine.com/post/miami-open-tennis-schedule-2024), program jednotlivých dnů, společné session neztotožňovat s konkrétním singlovým startem.
- MIA24-7: [originální OOP 21.3.](https://s42493.pcdn.co/wp-content/uploads/2024/03/OP.21.24.pdf), vydán 20.3. 15:49, str. 1 vizuálně.
- MIA24-8: [originální OOP 27.3.](https://s42493.pcdn.co/wp-content/uploads/2024/03/OP.27.24.pdf), vydán 26.3. 18:53, str. 1 vizuálně.
- MIA24-9: [originální OOP 28.3.](https://s42493.pcdn.co/wp-content/uploads/2024/03/OP.28.24.pdf), vydán 27.3. 18:14, str. 1 vizuálně.
- MIA24-10: [Sky denní Q1 výsledky](https://www.skysports.com/tennis/scores-schedule/18-03-2024), [dobový Q1 denní soupis TennisTemple](https://en.tennistemple.com/competitions/miami/2024/orderofplay/2024-03-18).
- MIA24-11: [ATP Preview & Day 1, 20.3.2024](https://www.atptour.com/-/media/120e601796a34590a4c3376656a71880.pdf), str. 1–2 text, oba screenshoty 403, finále, kvóty, LL, body/odměny.
- MIA24-12: [dobový denní soupis](https://canaltenis.com/resultados-atp-miami-2024/), výsledková kontrola; [ATP odklady 22.3.](https://www.atptour.com/en/news/sinner-vavassori-miami-2024-friday), [ATP odklady 23.3.](https://www.atptour.com/en/news/miami-2024-rain-update-sinner-medvedev-alcaraz).
- MIA24-13: [dobový OOP 26.3. v mediálním přepisu](https://www.lafamiliadebroward.com/2024-miami-open-presented-by-itau-march-25-tournament-updates/), [Sky denní R16](https://www.skysports.com/tennis/scores-schedule/26-03-2024), [pořadatel 27.3., potvrzení všech čtvrtfinalistů](https://www.miamiopen.com/latest-news/terrific-tuesday-sets-mens-quarters-azarenka-and-rybakina-into-semifinals/).
- MIA24-14: [dobový OOP SF 29.3. v mediálním přepisu](https://www.miamilivingmagazine.com/post/dimitrov-stuns-alcaraz-2024-miami-open-presented-by-ita%C3%BA-tournament-update), [ATP potvrzení nedělního finále](https://www.atptour.com/en/news/sinner-dimitrov-miami-2024-final).
- Dobový předpis ATP VII/IX viz IW24-11/14, nikoli novější ročníková pravidla.


## Marrakech 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/P/Z s doplňkovými omezeními). Rešerše 2026-11-27. Předstartovní i výsledkový originální ATP Main vizuálně ověřeny. Originální pořadatelský magazín potvrzuje Q kvóty, Main velikost a odměny. Q finanční tabulka sekundární shoda po rozlišení ročníků; původní Q PDF nedostupné. Q2 a Main R32 plánovaně ve stejný den, nikoli mimořádný odklad.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Grand Prix Hassan II, mužská dvouhra | RAK24-1/2/3/4 |
| Kategorie / ATP ID | ATP 250 / 360 | RAK24-1/15 |
| Ročník | 38. podle pořadatele; 32. podle ATP Media Notes | RAK24-3/4 |
| Dějiště | Royal Tennis Club de Marrakech, Marrakech, Maroko | RAK24-1/3/4 |
| Povrch | venkovní červená antuka | RAK24-1/2/3 |
| Časové pásmo | Africa/Casablanca, UTC+00:00 během turnaje (ramadán) | RAK24-5 |
| Ředitel | Hicham Arazi | RAK24-3 |
| ATP supervisor / referee | Roland Herfel / Ashraf Hamouda | RAK24-1/3 |
| Měna | EUR | RAK24-1/2/3 |

Rozdílné počty ročníků zachovat jako zdrojové údaje. ATP notes uvádějí historii ATP akce od roku 1990, pořadatel používá širší počítání; textová extrakce losů mylně uvádí 30ème, obraz obou originálů jednoznačně 38ème. Logo sponzora Dunlop na titulní straně magazínu samo neurčuje přesný model zápasových míčů. Detail sheet a tour manager neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-04 | RAK24-6 |
| Q rank date | 2024-03-11 | RAK24-6 |
| Nominální Main deadline | 2024-03-04 18:00 (12:00 US Eastern, UTC−05; Maroko UTC+01) | odvozeno §7.03 |
| Nominální Q deadline | 2024-03-11 16:00 (12:00 US Eastern, UTC−04; Maroko UTC+00) | odvozeno §7.03 |
| Nominální LE deadline | 2024-03-28 14:00 (10:00 US Eastern) | odvozeno §7.04 |
| Q los | nejpozději před Q1 dne 2024-03-31, přesný okamžik neověřen | RAK24-7/8 |
| Main los | před dokončením Q2, nejpozději před Main startem 2024-04-01, přesný okamžik neověřen | RAK24-2/4 |
| Q | 2024-03-31–2024-04-01 | RAK24-3/4/6/7 |
| Main | 2024-04-01–07 | RAK24-1/2/4 |
| Singlové finále | 2024-04-07 14:00 místně, plán ATP | RAK24-4 |

Dobový přepis entry listu 27.3. uvádí původní cutoff 75 Main a 128 Q; oba originální Main losy uvádějí Moutet 105 při deadline i v losu. Neztotožňovat různé publikované stavy bez originální acceptance listiny; Q konečný cutoff neověřen. Přesné termíny uzávěrek jsou odvozené z dobového předpisu, nikoli prokázané časové značky. Časový režim se mezi Main a Q uzávěrkou změnil na obou stranách Atlantiku; nezaměňovat dubnový marocký čas UTC+00 s obvyklým UTC+01.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-03-31 | 8 |
| Q2 | 2024-04-01 | 4 |
| R32 | 2024-04-01–02 | 12 (3+9) |
| R16 | 2024-04-03–04 | 8 (4+4 pozorováno) |
| QF | 2024-04-05 | 4 |
| SF | 2024-04-06 | 2 |
| F | 2024-04-07 | 1 |

Pořadatelský magazín uvádí celé okno 31.3.–7.4., dobový přepis listiny výslovně začátek Q v neděli 31.3. a ATP Preview & Day 1 1.4. předem uvádí čtyři kvalifikanty, kteří budou určeni až v pondělí. Pondělní souběh není dešťový posun: dobová zpráva RAK24-9 výslovně avizuje tři první Main zápasy v pondělí; denní přehled RAK24-7 potvrzuje současně čtyři Q2 a tři R32, dalších devět R32 v úterý. Osm R16 rozděleno 4+4 podle výsledků, původní samostatné OOP obou dnů nezískány. QF/SF/F potvrzeny denním přehledem, finále plánováno v ATP notes na neděli 14:00. Plánovaná okna kol podporuje dobový průběh; bez kompletního předturnajového OOP neprohlašovat všechny denní počty za nezávisle potvrzený původní plán. Q dva dny, Main sedm dní, překryv jeden den, celé okno osm kalendářních dní a 39 zápasů. Předchozí Miami má finále ve stejný civilní den jako Q1 Marrakech; nejde o chybu kalendáře. 

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA (včetně případné NG rezervy) | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

ATP 250 podle dobového §7.08 B/E: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28. RAK24-6 uvádí 18 DA, 0 SE/LE, 3 WC a 4 Q (mezistav 25, ne konečný počet). Pořadatelský magazín RAK24-3 uvádí 21 přímých vstupů, 4 Q, 3 WC a samostatně Q 14 DA + 2 WC; souhrnných 21 odpovídá uvolnění rezerv, nikoli absenci nominálních rezerv. Oba originální Main losy potvrzují BYE 2/10/23/31, WC 6/7/26, Q pozice 3/11/13/15, PR na pozici 18 a osm seedů. Žádný LL nebo SE ve výsledkovém Main. PR náleží mezi přímé vstupy. Sekundární zpráva RAK24-8 uvádí 32 hráčů v Main, ale směšuje kapacitu s účastí; přednost oficiálnímu magazínu a originálnímu pavouku s 28 hráči. 12+8+4+2+1=27.

Q 16 hráčů, 14 DA a 2 WC výslovně potvrzují pořadatel i přepis listiny. Výsledkový pavouk RAK24-10 uvádí Karmoussiho a Bennaniho jako WC, jednoho Alt Miedlera a sedm označených seedů (1–6 a 8). Osm nominálních seedů podle §7.15, případný původní seed 7 a jeho konkrétní nahrazení neověřeny; neodvozovat jeho jméno pouze z pozice Alt. Q 4 sekce po čtyřech, 8+4=12 utkání, čtyři postupující potvrzeni výsledky a Main originálem. Nominální počet zachovat navzdory skutečným změnám.

### 5. Dobová pravidla

ATP §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 v únorové verzi (SCL24-18), včetně účinných změn LCB24-19 a upřesnění rozsahu challengerového §7.08 C.3 v SCL24. Dvě SE a jedna LE rezerva v Main ATP 250, nevyužitá místa přecházejí na DA, čtyři BYE top čtyř seedů, čtyři Q sekce, osm Q seedů, BO3 s tiebreakem. ATP notes RAK24-4 potvrzují 0 bodů za první prohru po BYE, finanční R16 nominál zůstává. Q body 13/7/0 podle dobového ATP předpisu, nikoli zastaralé 12/6/0 v RAK24-10.

Týden 1.–7.4. tři ATP 250 (Marrakech, Estoril, Houston), viz RAK24-6 a RAK24-16. ATP notes označují Van Assche #NextGenATP, ale přepis původní Main listiny jej uvádí mezi běžnými náhradníky s rankingem 86, originální Main bez zvláštní značky. Nelze prohlásit programovou alokaci NG jen z jeho věku nebo mediálního označení. Konkrétní využití či propad NG rezerv v tomto týdnu zůstává otevřené; žádná místa nad nominální kapacitu.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main ceny a body shodně oba vizuálně ověřené ATP losy, ATP notes a oficiální magazín. Q 3105/1695 EUR shodně ročníkový sloupec 2024 TennisCompanion a explicitní oddíl 2024 Canal Tenis (RAK24-11/12). TennisTemple uvádí 3020/1645 a 12/6 bodů; obě částky přesně odpovídají oddílům 2023 v obou srovnávacích zdrojích a body staršímu předpisu, proto jde o silně doložené podezření na převzetí starší tabulky, ne rovnocenný ročníkový protidoklad. Na rozdíl od Santiago zde lze konkrétní zdroj nesrovnalosti vysvětlit přesným shodným předchozím ročníkem. P* sekundární shoda, ne primární Q potvrzení; nezávislost vzniku obou tabulek neprokázána. Alternativa ze staršího rozpisu by dala Q 25240 EUR, nepoužívá se. Nominální Main 425905 EUR, Q 25980 EUR, celkem 451885 EUR. Financial commitment 651865 EUR z originálu a turnajová dotace 579320 EUR z magazínu jsou jiné veličiny; neodvozovat Q ceny z rozdílu celkových částek. Q postupující získávají Main peníze podle výsledku.

### 7. Kontrola a mezery

I/T/D/B doloženy. H* okna a souběh potvrzeny, úplný původní denní OOP nezískán. E* uzávěrky odvozené, acceptance listy/DS, Q konečný cutoff a hodiny losů chybějí. R* NG alokace otevřena; P* Q ceny sekundární shoda po kontrole odlišného ročníku. Z* oba originální Main (po jedné straně) vizuálně; oficiální magazín titulní strana vizuálně, pasáže o kvótách a odměnách textově; ATP notes str. 2 screenshot 403, text dostupný; Q PDF nedostupný. Nevymýšlet hash. Kontroly 28/16 účastníků, 8/8 seedů, 4/0 BYE, 27/12 zápasů, 3+9 a 4+4 dělení, finanční součty a všech devět oblastí prošly v nominálním rozsahu s hvězdičkami. Následující Estoril, poté Houston. Žádný převod ani runtime změna.

### 8. Zdroje (RAK24)

- RAK24-1: [výsledkový originální ATP Main v RFET](https://www.rfet.es/descargar/file-noticias-adjuntos/4915_Documento/cuadro-atp-marrakech.pdf), str. 1 vizuálně.
- RAK24-2: [předstartovní originální ATP Main](https://www.fantatennis.net/_downloads/2af70157f3988736b3cb652f47eaaefe), str. 1 vizuálně.
- RAK24-3: [oficiální Magazine GPH2 38e](https://grandprixhassan2.com/wp-content/uploads/2024/04/Magazine-GPH2-38e-web_compressed.pdf), titul vizuálně, COMITÉ D'ORGANISATION, PRÉSENTATION DES TABLEAUX, BREAKDOWN textově.
- RAK24-4: [ATP Preview & Day 1, 1.4.2024](https://www.atptour.com/-/media/13627bca79a044779d36c8fa90f6105e.pdf), str. 1–2 text, screenshot 403.
- RAK24-5: [časové změny Marrakech 2024](https://www.timeanddate.com/time/change/morocco/marrakech?year=2024), [dobová zpráva o ramadánu](https://www.moroccoworldnews.com/2024/03/22340/ramadan-2024-morocco-back-to-gmt-on-march-10/).
- RAK24-6: [dobový přepis listiny 27.3.](https://www.tennisteen.it/entry-list/atp/24142-atp-entry-list-1-7-aprile-2024.html), řádky 182–244, obě fáze a kvóty.
- RAK24-7: [dobový denní přehled obou fází](https://canaltenis.com/resultados-atp-marrakech-2024/), místní data a počty; [Sky 1.4.](https://www.skysports.com/tennis/scores-schedule/01-04-2024) nezávislá kontrola souběhu.
- RAK24-8: [SNRT News 31.3. o Q startu](https://snrtnews.com/fr/article/38e-grand-prix-hassan-ii-de-tennis-coup-denvoi-des-qualifications-au-tableau-final-94375), Main kapacitu nelze zaměnit za počet hráčů.
- RAK24-9: [TennisActu 1.4. o třech pondělních Main zápasech](https://www.tennisactu.net/news-atp-marrakech-luca-van-assche-cale-d-entree-face-a-jaume-munar-au-maroc-108684.html), [ATP 1.4.](https://www.atptour.com/en/news/munar-van-assche-marrakech-2024-monday).
- RAK24-10: [TennisTemple Q 2024](https://en.tennistemple.com/competitions/marrakech/2024/draw-qualifications), geometrie a vstupy, zastaralá bodová/finanční tabulka.
- RAK24-11: [TennisCompanion ročníkové sloupce EUR](https://tenniscompanion.org/prize-money/marrakech/), 2024 a 2023 porovnány.
- RAK24-12: [Canal Tenis ročníkové oddíly 2024 a 2023](https://canaltenis.com/prize-money-atp-marrakech/), Q 3105/1695 vs 3020/1645.
- RAK24-13: [Sportface dobové Main ceny 8.4.](https://news.sportface.it/tennis/atp-marrakech-2024-montepremi-e-prize-money/2500487), souhlas s originály; celková částka v článku je commitment.
- RAK24-14: [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), Main termíny.
- RAK24-15: [ročníkový identifikátor ATP 360](https://www.ultimatetennisstatistics.com/tournamentEvent?extId=360&name=Marrakech&season=2024&tab=results), 32/28; [ATP Q PDF](https://www.protennislive.com/posting/2024/360/qs.pdf) nedostupné.
- RAK24-16: [ATP kalendář 11.3.2024](https://www.atptour.com/-/media/files/calendar-pdfs/2024/2024-atp-challenger-calendar-as-of-11-march-2024.pdf), indexovaný text, týden tří ATP 250; viz také RAK24-6. Dobový předpis viz SCL24-18, LCB24-19, ROT24-16.


## Estoril 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/Z s omezeními). Rešerše 2026-11-27. Originální ATP Q předstartovní los, Main po doplnění kvalifikantů před prvními zápasy a výsledkový Main vizuálně ověřeny. Původní OOP 1. a 2.4. jednoznačně potvrzují původní R32 4+8, navzdory zrušení celé úterní hrací doby.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Millennium Estoril Open, mužská dvouhra, 9. ročník | EST24-1/2/4/5 |
| Kategorie / ATP ID | ATP 250 / 7290 | EST24-1/3/14 |
| Dějiště | Clube de Ténis do Estoril, Estoril, Portugalsko | EST24-4/5/15 |
| Povrch | venkovní červená antuka | EST24-1/2/3 |
| Časové pásmo | Europe/Lisbon; WET UTC+00 do 31.3. 01:00, poté WEST UTC+01 | místní kalendář DST |
| Ředitel | João Zilhão | EST24-7/8 |
| ATP supervisor | Anne Lasserre, později Carlos Sanches | EST24-1/2/7/9 |
| Tour manager / referee | Arnau Brugues / Rogério Santos | EST24-7/8/9 |
| Měna | EUR | EST24-1/2/3 |

Model míčů podle indexované dobové Raquetc zprávy EST24-16: Dunlop ATP Millennium Estoril Open Special Select; přímé otevření zprávy 503, nepovažovat za ověřený detail sheet. Nezaměňovat s jinou historickou portugalskou sérií ani s Challenger ročníkem 2025.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-04 | EST24-6 |
| Q rank date | 2024-03-11 | EST24-6 |
| Nominální Main deadline | 2024-03-04 17:00 WET (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-03-11 16:00 WET (12:00 US Eastern) | §7.03, odvozeno |
| Nominální LE deadline | 2024-03-28 14:00 WET (10:00 US Eastern) | §7.04, odvozeno |
| Q los | zveřejněn 2024-03-29; přesný čas neověřen | EST24-10 |
| Main los | zveřejněn 2024-03-30; přesný čas neověřen | EST24-11 |
| Q | 2024-03-30–31 | EST24-5/6/12 |
| Main | 2024-04-01–07 | EST24-1/2/4 |
| LL sign-in 1.4. / 2.4. | 11:30 / 11:00 WEST | EST24-7/8 |
| Singlové finále | 2024-04-07 15:30 WEST, plán ATP | EST24-4/13 |

Dobový přepis EST24-6 uvádí původní cutoffs 91 Main / 140 Q. Main dokument před začátkem Main EST24-2 uvádí Lestienne 100 při deadline i v losu; výsledkový los ponechává pole prázdná. Q originál uvádí Vanshelboim 358 jako last DA. Odlišná data neztotožňovat bez originální acceptance listiny. Změna US DST 10.3. a portugalského DST 31.3. znamená různé offsety v průběhu procesu, včetně samotné Q. Uzávěrky odvozené, nikoli nezávislé timestampy.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-03-30 | 8 |
| Q2 | 2024-03-31 | 4 |
| R32 | 2024-04-01–02 | 12 (4+8) |
| R16 | 2024-04-03–04 (rekonstrukce původního okna) | 8 |
| QF | 2024-04-05 | 4 |
| SF | 2024-04-06 | 2 |
| F | 2024-04-07 | 1 |

Pořadatel 28.2. oznámil celé okno 30.3.–7.4. a závěrečný víkend SF/F 6.–7.4. (EST24-5). Dobové Q výsledky EST24-12 potvrzují 8+4, Q byla ukončena v neděli 31.3. před Main startem. OOP 1.4., vydaný 31.3. v 16:08, obsahuje čtyři R32 na centrálním kurtu a dva doubles na vedlejším. OOP 2.4., vydaný 1.4. v 16:28, obsahuje osm zbývajících R32 (4+2+2 na třech kurtech), bez pondělních dohrávek. Revidovaný originál 19:45 mění Lestienne na LL Jorda Sanchis, nikoli počet plánovaných utkání. ATP výslovně potvrzuje zrušení celé úterní hrací doby deštěm (EST24-17). Revidovaný středeční OOP má devět singlových R32 (osm zbývajících úterních a pondělní dohrávku); ve čtvrtečním OOP všech osm R16. Tyto dva krizové programy nejsou původní nominální plán. Okno R16 3.–4.4. je rekonstrukce mezi původním koncem R32 a QF 5.4., podpořená předem publikovanými denními/nočními session 3.–5.4. (EST24-15) a skutečným čtvrtečním R16; původní přesné denní rozdělení R16 neznámé, nepřebírat 4+4 z jiných akcí. QF čtyři v pátek, SF dvě v sobotu a nedělní F potvrzeny dobovými výsledky EST24-18 a plánem pořadatele. Finále od 15:30 podle ATP Day 1 i posledního OOP v mediálním přepisu. Q 2 dny + Main 7 dní = 9 kalendářních dní bez překryvu; 39 zápasů. Na rozdíl od Marrakech začíná Q v sobotu, ne v neděli a nekryje se s Main.

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

ATP §7.08 B/E: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28; nevyužité SE/LE rezervy přecházejí do DA. Dobový přepis EST24-6 potvrzuje 18 základních DA, 0 SE a 0 LE v mezistavu, 3 WC, 4 Q; nejde o konečný 25členný pavouk. Main originál před zápasy EST24-2 potvrzuje 21 ostatních vstupů, tři WC 7/18/30, čtyři Q 21/26/27/29, osm seedů, BYE 2/10/23/31. Výsledkový Main EST24-1 uvádí LL Gasqueta na pozici 9 po odstoupení seed 4 a LL Jorda Sanchise na pozici 28 po odstoupení Lestienneho. Gasquet tak historicky získal BYE po náhradě původního seedu; neznamená to jiné plánované pravidlo nasazování či šest řádných kvalifikantů. Main 12+8+4+2+1=27.

Originální Q EST24-3 potvrzuje osm seedů, 16 pozic, dva WC na pozicích 2/3 (Vale a Francisco Rocha), Alt na 10 po odstoupení Nardiho. Nominál 14 DA+2 WC, čtyři sekce po čtyřech, 8+4=12 zápasů, čtyři řádní vítězové potvrzeni pořadatelem a Main originálem. Výsledkový Q originál nebyl získán, ale předstartovní originál a dobové výsledky potvrzují geometrii nezávisle.

### 5. Dobová pravidla

ATP §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 v únorové verzi (SCL24-18), se změnami LCB24-19 a upřesněním challengerového §7.08 C.3 v SCL24. Dvě SE a jedna LE rezerva, čtyři Q sekce, osm seedů, BO3 tiebreak, první čtyři Main seedy BYE. ATP Preview přímo potvrzuje nulu bodů za první prohru po BYE; Q originál 13/7/0. Historický LL na původní seed pozici s BYE evidovat jako výjimku při změně obsazení, ne jako páté BYE ani vlastní nasazení LL. Jeho konkrétní individuální bodový či peněžní payout necertifikován.

Next Gen týden Marrakech/Estoril/Houston: ATP notes uvádějí Fils, Fonseca a Henrique Rocha jako #NextGenATP; Fonseca a Rocha jsou doložené běžné WC a Fils řádný DA v listině. Mediální označení není doklad programové rezervy. Q originál oba WC a jednoho Alt označuje; individuální NG alokace či propad není potvrzen. Nevytvářet dodatečné místo.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main obě originální verze vizuálně shodné, Q originál EST24-3 vizuálně včetně 13/7/0 a 0/3105/1695 EUR. P bez hvězdičky. Main 425905 EUR, Q 25980 EUR, nominální součet 451885 EUR. Financial commitment 651865 EUR a turnajová dotace 579320 EUR (EST24-19) jsou jiné veličiny. Shoda všech jednotlivých částek s Marrakech 2024 podporuje jeho sekundární Q kandidát, ale není ročníkovým originálem Marrakech; P* u Marrakech zachovat.

### 7. Kontrola a mezery

I/T/D/B/P doloženy. H* původní R32 4+8 vizuálně ověřeno, R16 okno rekonstruováno a denní split před deštěm neznámý; E* originální acceptance lists/DS a přesné časy losů chybějí, uzávěrky odvozené. R* NG přidělení neověřeno. Z* tři ATP pavouky a pět originálních OOP (1.4., dvě verze 2.4., 3.4., 4.4.) po jedné straně vizuálně; ATP Preview str. 2 textově, screenshot 403; žádný tvrzený SHA-256. Kontrola kvót, 8/8 seedů, 4/0 BYE, 27/12 utkání, denního součtu a obou primárních finančních tabulek prošla. Další Houston 2024. Žádný převod ani změna runtime.

### 8. Zdroje (EST24)

- EST24-1: [výsledkový originální ATP Main, RFET](https://www.rfet.es/descargar/file-noticias-adjuntos/4914_Documento/cuadro-atp-250-estoril-por.pdf), str. 1 vizuálně.
- EST24-2: [originální ATP Main před zápasy, po doplnění Q](https://www.raquetc.com/wp-content/uploads/2024/03/MDS.pdf), str. 1 vizuálně.
- EST24-3: [originální ATP Q před zápasy](https://www.raquetc.com/wp-content/uploads/2024/03/QS.pdf), str. 1 vizuálně, osm seedů, 2 WC, finanční tabulka.
- EST24-4: [ATP Preview & Day 1, 1.4.2024](https://www.atptour.com/-/media/73f6e75ef1d744888e375556c0e2e0ba.pdf), str. 1–2 text, str. 2 screenshot 403; 9. ročník, plán finále, WC/Q/LL, BYE.
- EST24-5: [pořadatel 28.2., devátý ročník a program](https://www.millenniumestorilopen.com/news/65df1d0987adfe001c9b22fa), celé okno, SF/F víkend.
- EST24-6: [dobový přepis obou acceptance listů 27.3.](https://www.tennisteen.it/entry-list/atp/24142-atp-entry-list-1-7-aprile-2024.html), řádky 66–125, kvóty a rank dates.
- EST24-7: [originální OOP 1.4.](https://www.raquetc.com/wp-content/uploads/2024/03/OP-2.pdf), vydání 31.3. 16:08, 4 R32, vizuálně.
- EST24-8: [originální OOP 2.4.](https://www.raquetc.com/wp-content/uploads/2024/04/OP.pdf), vydání 1.4. 16:28, 8 R32, vizuálně; [revidovaný pořadatelský originál](https://estoril-open-media.s3.amazonaws.com/images/660b01eb4e9144001cc1eb9c-OP.pdf), 19:45, vizuálně.
- EST24-9: [OOP 3.4.](https://www.raquetc.com/wp-content/uploads/2024/04/OP-3.pdf), [OOP 4.4.](https://www.raquetc.com/wp-content/uploads/2024/04/OP-4.pdf), oba vizuálně, program po dešti, nikoli původní.
- EST24-10: [A Bola 29.3., oznámení Q losu](https://www.abola.pt/noticias/estoril-open-sorteado-qualifying-com-seis-portugueses-2024032919574947993).
- EST24-11: [A Bola 30.3., Main los](https://www.abola.pt/noticias/estoril-open-sorteio-conhecido-portugueses-com-adversarios-duros-2024033015240029312).
- EST24-12: [RTÉ Q denní soupis](https://www.rte.ie/sport/results/tennis/estoril-open-qualification-men/888919/results/), [pořadatel 31.3., dokončení Q](https://www.millenniumestorilopen.com/news/6609a0cf8e7a92001c0a7acb).
- EST24-13: [Raquetc, program finále publikovaný 6.4.](https://www.raquetc.com/2024/04/06/millennium-estoril-open-ordem-de-jogos-de-7-de-abril-domingo/), potvrzení 15:30.
- EST24-14: [Tennis Europe, identita 7290 a odkaz na původní ATP los](https://www.tenniseurope.org/calendarevent/73808/Millenium-Estoril-Open).
- EST24-15: [dobové návštěvnické informace a session](https://cartazculturallisboa.pt/evento/millennium-estoril-open-2024/), dny 3.–5.4., nikoli přesné počty kol.
- EST24-16: [Raquetc, přehled 30.3.](https://www.raquetc.com/2024/03/30/millennium-estoril-open-2024-tudo-o-que-precisa-de-saber-sobre-o-maior-torneio-em-portugal/), indexovaný model míčů, otevření 503.
- EST24-17: [ATP 2.4., zrušení úterního programu deštěm](https://www.atptour.com/en/news/estoril-2024-tuesday-rain), [Raquetc 2.4., revidovaný středeční program](https://www.raquetc.com/2024/04/02/millennium-estoril-open-ordem-de-jogos-de-3-de-abril-quarta-feira/).
- EST24-18: [Tennis Explorer 2024](https://www.tennisexplorer.com/estoril/2024/atp-men/), [RTÉ Main denní výsledky](https://www.rte.ie/sport/results/tennis/estoril-open-men/888923/results/), kontrola QF/SF/F.
- EST24-19: [ročníkový přehled dotace](https://web.kurzy.cz/wiki/Estoril_Open_2024); pravidla viz SCL24-18, LCB24-19, ROT24-16.


## Houston 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/P/Z s omezeními). Rešerše 2026-11-27. Pořadatelský Media Guide vizuálně ověřen na straně Quick Facts; indexovaný předstartovní ATP Main los a ATP Day 1 textově. Q los a jeho plán prvního dne doloženy úplným dobovým přepisem, originální Q finanční tabulka zatím nezískána.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Fayez Sarofim & Co. U.S. Men's Clay Court Championship | HOU24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 717 | HOU24-1/4 |
| Dějiště | River Oaks Country Club, Houston, Texas, USA | HOU24-1/2 |
| Povrch | venkovní červená antuka, Lee Fast-Dry | HOU24-1/3 |
| Míče | Dunlop ATP Regular Duty | HOU24-1 |
| Časové pásmo | America/Chicago, CDT UTC−05:00 v průběhu soutěží | lokalita a DST |
| Ředitelka | Bronwyn Greer | HOU24-1 |
| Supervisor / referee | Hans-Jurgen Ochs / Zsolt Beda | HOU24-1/3 |
| Tour manager | Denis Zvitkovic (pravopis podle pořadatelského dokumentu) | HOU24-1 |
| Měna | USD | HOU24-2/3 |

Pořadatel rozlišuje historii U.S. Clay od 1910, samostatnou tradici River Oaks od 1931 a 88. turnaj na River Oaks; nezaměňovat tyto počty za jediný pořadový ročník současné ATP série. Originální detail sheet nezískán. Historický povrch a míče převzaty z konkrétního ročníku, nikoli z aktuálního webu.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-04 | HOU24-5 |
| Q rank date | 2024-03-11 | HOU24-5 |
| Nominální Main deadline | 2024-03-04 11:00 CST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-03-11 11:00 CDT (12:00 US Eastern) | odvozeno §7.03 |
| Nominální LE deadline | 2024-03-28 09:00 CDT (10:00 US Eastern) | odvozeno §7.04 |
| Main a Q losy | zveřejněny nejpozději 2024-03-30 před Q1 | HOU24-6 |
| Q | 2024-03-30–31 | HOU24-1/5/6/7 |
| Main | 2024-04-01–07 | HOU24-2/3/4 |
| Singlové finále | 2024-04-07, přesný původní čas neověřen | HOU24-4/7/8 |

Přepis HOU24-5 uvádí původní cutoffs 92 Main / 211 Q; předstartovní ATP Main HOU24-3 má Bergs 122 v obou cutoff polích. Jde o různé publikované údaje/stavy. Q konečný cutoff, přesné okamžiky losování a originální acceptance lists neověřeny. Údaj 30.3. je mez zveřejnění přepisu, nikoli nutně den konání losovací ceremonie. Uzávěrky jsou pravidlová odvození. Změna amerického času 10.3. mezi uzávěrkami nemění hodinový rozdíl Houston–US Eastern.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-03-30 | 8 |
| Q2 | 2024-03-31 | 4 |
| R32 | 2024-04-01–02 | 12 (4+8) |
| R16 | 2024-04-03–04 | 8 (4+4) |
| QF | 2024-04-05 | 4 |
| SF | 2024-04-06 | 2 |
| F | 2024-04-07 | 1 |

Pořadatelský Media Guide potvrzuje celé okno 30.3.–7.4. a dvě Q kola. Dobový Q1 OOP v úplném přepisu HOU24-6 uvádí osm dvojic na kurtech 3 a 7, start obou v 11:00 místně. Denní přehled HOU24-7 potvrzuje 8+4 Q zápasů, dokončení Q v neděli před Main. Main R32 4+8 podle denního soupisu; úterní plán osmi singlů potvrzuje předem publikovaný článek z 1.4. (HOU24-9). R16 4+4 podle dobového rozpisu/výsledků; u Thompson–Kovacevic zůstává v HOU24-7 na 4.4. uveden plán 20:00 místo výsledku, jiné databáze řadí výsledek pod 5.4. Bez originálního OOP a doložené příčiny nelze určit skutečný okamžik dokončení. Nominální R16 okno nepřepisovat zahraničním datem. QF/SF/F potvrzeny denním přehledem a ATP zprávou o finále. H*: okna a denní počty rekonstruovány z ročníkových dokladů; úplný původní Main OOP nezískán. Q 2 + Main 7 dní, celkem 9 kalendářních dní bez překryvu, 39 nominálních zápasů.

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

Dobový §7.08 B/E a přepis listiny HOU24-5: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28. Listina 18 DA, 0 SE/LE, 3 WC, 4 Q je mezistav; při uvolnění rezerv jde o 21 běžných vstupů. Pořadatel potvrzuje 28 hráčů a čtyři BYE. ATP předstartovní Main text a dobový úplný přepis potvrzují BYE 2/10/23/31, Q placeholdery 3/18/21/27 a WC 13/26/30 (Mmoh, Shapovalov, Kudla), osm seedů. Konečná jména kvalifikantů doložena výsledkovým přehledem HOU24-7 a HOU24-10. Main 12+8+4+2+1=27.

Q 14 DA + 2 WC dle listiny i dobového pravidla, 16 účastníků a čtyři postupující dle pořadatele. Úplný předstartovní přepis HOU24-6 potvrzuje všech osm seedů (Diallo, Kypson, Vacherot, Yevseyev, Ritschard, Brouwer, Tabur, Damm), WC Pannu a Wu, dva Alt Rybakov a Kozlov. Čtyři sekce po čtyřech, 8+4=12 zápasů; čtyři vítězové Q Brouwer, Ritschard, Kypson, Wu. Skreč v Q2 nemění plánovanou geometrii. Originální Q PDF nezískáno.

### 5. Dobová pravidla

ATP §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 v únorové verzi (SCL24-18), se změnami LCB24-19 a upřesněním rozsahu challengerového §7.08 C.3 v SCL24. Dvě SE a jedna LE rezerva, čtyři Q sekce, osm seedů, BO3 tiebreak, první čtyři Main seedy BYE. ATP Preview HOU24-2 přímo potvrzuje nula bodů při první prohře po BYE; Q 13/7/0 dle dobového předpisu, nikoli odvození z výše peněz.

Týden Marrakech/Estoril/Houston: HOU24-5 obsahuje Michelsena v běžné Main DA listině, Damma v běžné Q listině; přítomnost mladých hráčů není sama o sobě dokladem Next Gen programové rezervy. Ani ve všech třech zpracovaných ročnících nebyl získán původní administrativní doklad o skutečném přidělení/propadu týdenních NG příležitostí. Zůstává společná otevřená položka R*, nominální kapacity 28/16 se nemění.

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

Main ceny a body v ATP Day 1 a indexovaném předstartovním originálním ATP Main (HOU24-2/3) souhlasí; obrazové vykreslení těchto PDF se nezdařilo. Q 3550/1935 USD souhlasí v ročníkovém sloupci TennisCompanion a explicitním oddílu 2024 Canal Tenis (HOU24-11/12). Stevegtennis uvádí shodné částky, ale nesprávnou značku A$; měnu nepřebírat. P* Q sekundární shoda, originální Q tabulka nezískána. Nominální Main 486355 USD, Q 29680 USD, celkem 516035 USD. Financial commitment 742350 USD z ATP losu a celková dotace 661585 USD z ročníkových přehledů jsou jiné veličiny; nevydávat je za singlový součet. Houston Main tabulka je stejná jako v ATP notes Santiago; sama o sobě neřeší ročníkový rozpor Santiago. Q postupující pobírají Main odměnu podle výsledku, bez samostatné nominální Q odměny.

### 7. Kontrola a mezery

I/T/D/B doloženy. H* úplný původní Main OOP a hodina finále chybí; E* původní acceptance listy/DS, časy losování a Q cutoff neověřeny, uzávěrky odvozené. R* individuální týdenní NG alokace neověřena. P* Main primární text, Q sekundární shoda. Z*: Media Guide str. 2 vizuálně; ATP notes screenshot 403, indexovaný ATP Main screenshot 404; verze stejné URL bez www již odpovídá 2025, proto ji nelze zaměnit za historický dokument. Přímé ATP Main/Q PDF 2024 nedostupné. Žádný tvrzený PDF hash. Kontrola kvót, 28/16, 8/8 seedů, 4/0 BYE, 27/12 utkání, denních součtů a nominálních finančních částek prošla. Další Monte-Carlo 2024, před zahájením ověřit odlišnou velikost losu a nedělní start. Bez runtime změn.

### 8. Zdroje (HOU24)

- HOU24-1: [oficiální 2024 US Clay Media Guide](https://mensclaycourt.com/web/DATA/2024%20US%20Clay%20Media%20Guide.pdf), str. 2 (Quick Facts) vizuálně, historie textově; povrch, míče, velikosti losů a organizace.
- HOU24-2: [ATP Preview & Day 1, 1.4.2024](https://www.atptour.com/-/media/5dc15d0d4b0d41f7863596d871d7a31a.pdf), Main body a ceny, text, screenshot 403.
- HOU24-3: [indexovaný předstartovní ATP Main 2024](https://www.mensclaycourt.com/web/files/6968/MDS.pdf), text s datem 1.–7.4.2024, screenshot 404; URL bez www indexována už s ročníkem 2025, neověřené bajty a nestabilní URL.
- HOU24-4: [ATP Tennis TV 717_2024](https://www.tennistv.com/tournaments/717_2024/houston), [ATP archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024).
- HOU24-5: [dobový přepis entry listů](https://www.tennisteen.it/entry-list/atp/24142-atp-entry-list-1-7-aprile-2024.html), řádky 125–181, kvóty a rank dates.
- HOU24-6: [dobový úplný přepis Main/Q losů a Q1 programu 30.3.2024](https://www.livetennis.it/post/410028/atp-250-houston-il-tabellone-principale-e-di-qualificazione-presenza-di-luciano-darderi-nel-md/), datum publikace, všechny seedy, WC a Q1 start.
- HOU24-7: [dobový denní přehled obou fází](https://canaltenis.com/resultados-atp-houston-2024/), dny a kola; jeden R16 řádek obsahuje plán namísto výsledku.
- HOU24-8: [ATP finále 7.4.2024](https://www.atptour.com/en/news/shelton-tiafoe-houston-2024-final), datum výsledku.
- HOU24-9: [dobový úterní preview publikovaný 1.4.](https://lastwordonsports.com/tennis/2024/04/01/atp-houston-day-2-predictions-shapovalov-giron/), osm plánovaných singlů; [ATP pondělní zpráva](https://www.atptour.com/en/news/eubanks-hijikata-nakashima-houston-2024-monday).
- HOU24-10: [Tennis Abstract Main/Q](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024-0717%2FHouston), [TennisPortal Q](https://www.tenisportal.cz/houston/2024/atp-muzi/?phase=qualification), nezávislá výsledková kontrola.
- HOU24-11: [TennisCompanion USD ročníkový sloupec 2024](https://tenniscompanion.org/prize-money/houston/), Q 3550/1935.
- HOU24-12: [Canal Tenis explicitní oddíl 2024](https://canaltenis.com/prize-money-atp-houston/), Main a Q shoda; [Stevegtennis 2024](https://www.stevegtennis.com/draw-results/atp/US%20Men%27s%20Clay%20Court%20Championship%20-%20Houston/2024), shoda čísel, chybná měna.
- [Původní ATP Main](https://www.protennislive.com/posting/2024/717/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/717/qs.pdf) nedostupné. Dobová pravidla viz SCL24-18, LCB24-19, ROT24-16; další Monte-Carlo podle dobového ATP kalendáře.


## Monte-Carlo 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/Z s doplňkovými omezeními). Rešerše 2026-11-27. První 56členný Masters v registru. Originální výsledkové ATP Main a Q losy, průběžný ATP Main a všech devět denních OOP vizuálně ověřeny. Obě finanční a bodové tabulky primárně doloženy.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Rolex Monte-Carlo Masters, mužská dvouhra, 117. ročník | MTC24-1/2/6 |
| Kategorie / ATP ID | ATP Masters 1000, nepovinný / 410 | MTC24-1/2/10/11 |
| Dějiště | Monte-Carlo Country Club, Roquebrune-Cap-Martin, Francie; oficiální ATP označení Monte-Carlo, Monaco | MTC24-1/5/10 |
| Povrch | venkovní červená antuka | MTC24-1/2/5 |
| Časové pásmo | Europe/Paris (Europe/Monaco stejný offset), CEST UTC+02:00 během soutěže | lokalita a datum |
| Ředitel | David Massey | MTC24-4/6 |
| ATP supervisors | Cedric Mourier / Carlos Sanches / R. Azemar | MTC24-1/2/4 |
| Referee / tour managers | Stephane Apostolou / Konstantin Haerle, Nicolas Rakitin | MTC24-4 |
| Měna | EUR | MTC24-1/2 |

Pořadatelský press kit uvádí 127 let historie od 1897, nikoli 127. uskutečněný ročník. Klub je na francouzské straně hranice; zachovat ATP obchodní označení samostatně od fyzické lokality. Press kit uvádí dodavatele Dunlop, přesný model míčů a detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-11 | MTC24-7 |
| Q rank date | 2024-03-18 | MTC24-7 |
| Nominální Main deadline | 2024-03-11 17:00 CET (12:00 US Eastern) | §7.03, odvozeno |
| Nominální Q deadline | 2024-03-18 17:00 CET (12:00 US Eastern) | §7.03, odvozeno |
| Main los | 2024-04-05 17:00 CEST, plán pořadatele | MTC24-6/8 |
| Q los | nejpozději 2024-04-05 21:42 CEST (vydání OOP); skutečný čas neověřen | MTC24-4 str. 1 |
| Q1 Alt sign-in deadline | 2024-04-06 10:30 CEST | MTC24-4 str. 1 |
| Q | 2024-04-06–07, od 11:00 | MTC24-4/5/9 |
| Main | 2024-04-07–14 | MTC24-1/3/4/9 |
| Main LL sign-in 8.–10.4. | 10:30 CEST | MTC24-4 str. 3–5 |
| Singlové finále | 2024-04-14 ne před 15:00 CEST | MTC24-4 str. 9 |

Referenční pondělí turnajového týdne 8.4.; nedělní start nemění rank dates. Dobový přepis listiny MTC24-7 uvádí cutoffs 47 Main a 77 Q; oba Main originály mají 50 při deadline i v losu, Q originál Sumit Nagal 97. Odlišné publikované stavy, nikoli sjednocený cutoff. Uzávěrky odvozené, originální acceptance lists neověřeny. Pořadatel zveřejnil seznam účastníků 12.3. a čtyři Main WC 4.4.; ATP potvrzuje den losu 5.4. Hodina 17:00 je plán ceremonie, Q čas vydání OOP není čas losu.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-04-06 | 14 |
| Q2 | 2024-04-07 | 7 |
| R64 | 2024-04-07–09 | 24 (4+12+8) |
| R32 | 2024-04-09–10 | 16 (4+12) |
| R16 | 2024-04-11 | 8 |
| QF | 2024-04-12 | 4 |
| SF | 2024-04-13 | 2 |
| F | 2024-04-14 | 1 |

Pořadatelský archiv MTC24-4 obsahuje devět originálních OOP, všechny strany vizuálně: sobota 6.4. 14 Q1, vydáno 5.4. 21:42; neděle 7.4. 7 Q2 + 4 R64, vydáno 6.4. 19:46; pondělí 8.4. 12 R64, vydáno 7.4. 17:18; úterý 9.4. 8 R64 + 4 R32, vydáno 8.4. 20:26; středa 10.4. 12 R32, vydáno 9.4. 21:44. Ve středu déšť přerušil dva R32 (Rune–Nagal, Kecmanovic–Dimitrov), ATP MTC24-12; čtvrteční OOP explicitně označuje dvě pokračování TBF a všech osm R16. Dohrávky nejsou devátý/desátý R16 ani nominální prodloužení R32. Pátek čtyři QF (OOP má anomální čas vydání 12.4. 20:46 v den zápasů, nepovažovat za předchozí večer); sobota dvě SF od 13:30/15:30 nejdříve, nedělní F od 15:00 nejdříve. Q 2 dny + Main 8 dní − jeden překryv = 9 kalendářních dní, 76 nominálních zápasů. Předchozí tři ATP 250 ještě hrály během Q Monte-Carlo. Nedělní i úterní souběh je doložen OOP před příslušnými dny, nejde o náhodný posun.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 64 / 56 | 28 / 28 (7 sekcí po 4) |
| DA | 45 v ročníkové listině; obecně 44–45 podle SE | 24 |
| SE | 0 v ročníkové listině; obecný předpis 0–1 | 0 |
| WC | 4 | 4 |
| Řádné Q postupy | 7 | 7 |
| Nasazení | 16 | 14 |
| BYE | 8, top 8 seedů | 0 |
| Kola / zápasy | 6 / 55 | 2 / 21 |
| Formát | BO3 setů | BO3 setů |

§7.08 B.1.a obecně 44–45 DA, 7 Q, 4 WC, 0–1 SE. Ročníkový přepis MTC24-7 uvádí 45 DA, 4 WC, 7 Q, 0 SE; MTC24-13 uvádí SE 0/0. Předcházející týden byly pouze ATP 250, nikoli standardně způsobilé předcházející soutěže pro SE do Masters dle §7.10 B. Ročníkový nominál 45+4+7=56, ne univerzální absence SE. Press kit potvrzuje 56, 7 Q, 4 WC a Q28. Průběžný Main MTC24-3 potvrzuje 16 seedů, BYE 2/15/18/31/34/47/50/63, Q 4/14/20/23/27/30/52, WC 10/45/54/55; již má tři dokončené R64 a dva LL, není předstartovní originál. Výsledkový Main MTC24-1 má čtyři LL, Sonego převzal pozici odstoupivšího seedu 3 včetně BYE; zachovat 16 nominálních seedů, nikoli 15 skutečně označených. LL nejsou další řádné Q postupy. Main 24+16+8+4+2+1=55.

Q 24 DA+4 WC, 28 účastníků, 14 nominálních seedů, 7 sekcí po čtyřech. Originál MTC24-2 má WC 10/15/19/23, čtyři Alt a seed 12 Cazaux vyškrtnutý v tabulce 14 seedů; sobotní původní OOP obsahuje jeho utkání. Zachovat 14, ne 13 skutečně označených. 14+7=21 zápasů, sedm řádných Q vítězů. Skreč nemění geometrii.

### 5. Dobová pravidla

§7.03/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle IW24-11/14 a SCL24-18; obecná 56členná Masters kvóta také v ročníkovém textovém zrcadle MTC24-11, tištěná str. 146. Dvě Q kola, 14 seedů, Main 16 seedů a osm BYE, BO3 tiebreak, bez ATP 250 LE a ATP 500 A+ WC. ATP Preview explicitně potvrzuje bodovou výjimku R32 po BYE: 10 místo 50, a Main WC při prohře R64 0 místo 10. Q originál přímo 30/16/0; u 96členných Masters 20/10/0, nepřenášet. Q body se přičítají k dosaženému Main výsledku.

**Nepovinný Masters:** Monte-Carlo se pro commitment povinnosti a rankingovou kategorii započítává do ATP 500 minima, ale přiděluje body Masters 1000. Dobový §1.07 D/H a §9.03 (MTC24-11/10) rozlišují také bonus pool: body Monte-Carlo se nezapočítávají do bonusového pořadí ATP 500. Sportovní kategorie, ranking/commitment a bonus pool jsou samostatné veličiny; žádná implementace.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 1000 | 919075 |
| Finalista | 1 | 650 | 501880 |
| SF | 2 | 400 | 274425 |
| QF | 4 | 200 | 149685 |
| R16 | 8 | 100 | 80065 |
| R32 | 16 | 50 (10 při první prohře po BYE) | 42935 |
| R64 | 24 | 10 (WC 0) | 23785 |
| Q postupující | 7 | 30 | 0 samostatně |
| Q2 prohra | 7 | 16 | 12185 |
| Q1 prohra | 14 | 0 | 6380 |

Obě tabulky přímo z vizuálně ověřených originálů MTC24-1/2, Main shoda s MTC24-3 a ATP Preview str. 3. P bez hvězdičky. Nominální Main 4466865 EUR, Q 174615 EUR, celkem 4641480 EUR; 56 Main příjemců a 21 nepostupujících Q příjemců. Q vítězové 0 EUR samostatně. Financial commitment 6642938 EUR a celková dotace 5950575 EUR nejsou singlový součet. Historické LL/withdrawal payout nezahrnuty.

### 7. Kontrola a mezery

I/T/H/D/R/B/P doloženy. E* chybí původní acceptance lists/DS, přesná hodina Q losu, deadline odvozené. Z* vizuálně oba výsledkové originály, průběžný Main, všech devět OOP a str. 2 press kitu; ATP Preview text (str. 3 screenshot 403), dobový předpis ve stávajících odkázaných verzích a ročníkovém textovém zrcadle (přímé otevření únorových kapitol nyní 403). Bez neověřených hashů. Kontrola kvót, 56/28, 16/14 seedů, 8/0 BYE, 55/21 zápasů, denních součtů i primárních finančních tabulek prošla. Kontrolní očekávaný Main součet při prvním pokusu chybný, přepočítán nezávisle po jednotlivých řádcích před zápisem. Další Barcelona, Munich, Bucharest 2024, před zahájením ověřit kalendář. Bez runtime změn.

### 8. Zdroje (MTC24)

- MTC24-1: [ATP výsledkový Main](https://www.protennislive.com/posting/2024/410/mds.pdf), str. 1 vizuálně.
- MTC24-2: [ATP výsledkový Q](https://www.protennislive.com/posting/2024/410/qs.pdf), str. 1 vizuálně.
- MTC24-3: [průběžný ATP Main archiv Fanpage](https://static.fanpage.it/wp-content/uploads/sites/27/2024/04/Tabellone-atp-montecarlo-2024.pdf), str. 1 vizuálně.
- MTC24-4: [pořadatelský archiv OOP 6.–14.4.](https://montecarlotennismasters.com/wp-content/uploads/2024/06/Programmation-2024.pdf), všech 9 stran vizuálně.
- MTC24-5: [pořadatelský press kit březen 2024](https://montecarlotennismasters.com/wp-content/uploads/2024/03/RMCM24_DossierPresse_A4_UK_WEB.pdf), str. 2 vizuálně, kvóty textově.
- MTC24-6: [pořadatel 4.4. Main WC a ceremonie](https://montecarlotennismasters.com/en/wild-cards-complete-the-2024-edition/), [pořadatel 12.3. roster](https://montecarlotennismasters.com/en/press-conference-paris-3/).
- MTC24-7: [dobový přepis listin 3.4.](https://www.tennisteen.it/entry-list/atp/24146-atp-entry-list-8-14-aprile-2024.html), rank dates, kvóty a cutoffs.
- MTC24-8: [ATP los 5.4.2024](https://www.atptour.com/en/news/monte-carlo-2024-draw), indexovaný text.
- MTC24-9: [ATP předturnajový přehled](https://www.atptour.com/en/news/monte-carlo-2024-atp-masters-1000-history-draw-schedule), indexovaný text, otevření 403; [ATP Preview & Day 1 7.4.](https://www.atptour.com/-/media/32a56d8005e34a80bc33f69d238c3162.pdf), str. 3 text, screenshot 403.
- MTC24-10: [ročníkový přehled 2024](https://en.wikipedia.org/wiki/2024_Monte-Carlo_Masters), fyzické místo, 117. ročník, nepovinný Masters, body a dotace; [Tennis Europe ATP 410](https://www.tenniseurope.org/calendarevent/73809/Rolex-MonteCarlo-Masters).
- MTC24-11: [ročníkové textové zrcadlo ATP Rulebook 2024](https://www.scribd.com/document/787665242/2024-rulebook-atp), §1.07 D/H, §7.08 B.1.a, §7.10, §9.03; doplňkově IW24-11/14 a SCL24-18.
- MTC24-12: [ATP 10.4., dvě deštěm přerušené R32](https://www.atptour.com/en/news/monte-carlo-2024-wednesday-rain-delay), [ATP 11.4., dohrávky a R16](https://www.atptour.com/en/news/rune-dimitrov-monte-carlo-2024-thursday).
- MTC24-13: [dobový přepis listin a seedů](https://www.livetennis.it/post/410245/masters-1000-monte-carlo-ecco-le-teste-di-serie-sorteggio-del-tabellone-principale-venerdi-pomeriggio-si-parte-sabato-con-le-qualificazioni-e-gia-domenica-con-il-main-draw/), SE 0/0, nedělní start.


## Barcelona 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/Z s označenými mezerami). Rešerše 2026-11-27. První 48členný ATP 500 v registru. Výsledkové originály Main/Q přímo ATP a stejné kopie RFET vizuálně ověřeny, stejně jako poslední OOP. Hlavní los má chybný měnový symbol $, korigovaný explicitními EUR údaji ATP Media Notes a předturnajového přehledu. Originální předstartovní OOP všech dnů nezískány.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Barcelona Open Banc Sabadell / Trofeu Comte de Godó, 71. ročník celkově | BCN24-2/5/9 |
| Kategorie / ATP ID | ATP 500 / 425 | BCN24-1/2 |
| Dějiště | Real Club de Tenis Barcelona 1899, Barcelona, Španělsko | BCN24-4/5 |
| Povrch | venkovní červená antuka | BCN24-1/2 |
| Časové pásmo | Europe/Madrid, CEST UTC+02:00 během turnaje | lokalita a datum |
| Ředitel | David Ferrer | BCN24-3 |
| ATP supervisors | Cedric Mourier / Carlos Sanches | BCN24-1/2/3 |
| Tour manager / referee | Arnau Brugues / Javier Moreno | BCN24-3 |
| Měna | EUR (chybný $ v Main originálu) | BCN24-2/4/5 |

ATP Media Notes počítají 56. ročník otevřené éry (1968–2019, od 2021), nikoli všechny ročníky od založení. 71. ročník označuje logo Q originálu a sekundární historie. Míče a detail sheet nezískány. Nepřenášet 32členný formát Barcelona 2025 zpět do roku 2024.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-18 | BCN24-6 |
| Q rank date | 2024-03-25, pravidlový referenční den | odvozeno §7.03, originální Q listina chybí |
| Nominální Main deadline | 2024-03-18 17:00 CET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-03-25 17:00 CET (12:00 US Eastern) | odvozeno §7.03 |
| Podmíněná A+ WC deadline | 2024-04-12 16:00 CEST (10:00 US Eastern) | odvozeno §7.12 A.2 |
| Main los | 2024-04-13, plán ATP, hodina nezískána | BCN24-5 |
| Q los | nejpozději před Q1 2024-04-13, čas neověřen | BCN24-2/7 |
| Q | 2024-04-13–14 od 10:00 CEST podle ATP | BCN24-5/7 |
| Main | 2024-04-15–21 | BCN24-1/4/5 |
| Singlové finále | 2024-04-21 ne před 16:00 CEST | BCN24-3/4 |

Dobový přepis Main listiny 11.4. uvádí cutoff 72, výsledkový Main originál 92 v obou cutoff polích, Q originál Sanchez Izquierdo 285. Odlišné publikované stavy nesjednocovat. Přesné uzávěrky odvozené, nikoli nezávislé timestampy. Po změně amerického času 10.3. a před evropskou změnou 31.3. je rozdíl pěti hodin, v dubnu šesti. Původní acceptance lists a konkrétní hodiny obou losů nezískány.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-04-13 | 12 |
| Q2 | 2024-04-14 | 6 |
| R64 | 2024-04-15–16 | 16 (9+7 v dobových denních soupisech) |
| R32 | 2024-04-16–17 | 16 (5+11 uzlů v dobových soupisech) |
| R16 | 2024-04-18 | 8 |
| QF | 2024-04-19 | 4 |
| SF | 2024-04-20 | 2 |
| F | 2024-04-21 | 1 |

ATP Preview potvrzuje Q 13.–14.4. a Main 15.–21.4. Dvě kvalifikační kola 12+6 potvrzují Q originál a dobové denní archivy. Dobový mediální přepis programu BCN24-8 uvádí pondělí 9 R64, úterý 7 R64 a 5 R32, středu 11 R32 uzlů (včetně walkover Davidovich Fokina–Machac). Ve čtvrtek všech osm R16, poté 4/2/1. Výsledkový denní soupis BCN24-10 nezávisle kontroluje okna. Přesný počet skutečně rozehraných zápasů se může lišit od nominálního počtu uzlů; walkover nesnižuje plánovaný počet. Původní samostatné OOP prvních dnů nezískány, H* denní split a překryv R64/R32 rekonstruovány z dobového programu/výsledků; nepovažovat všechny údaje za primárně potvrzený původní plán. Originální OOP finále vydaný 20.4. v 20:17 přímo stanoví nedělní singlové finále ne před 16:00, po doubles. Q 2 + Main 7 dní bez překryvu, 9 kalendářních dní, 47+18=65 nominálních zápasů. Q probíhá během závěrečného víkendu Monte-Carlo.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 64 / 48 | 24 / 24 (6 sekcí po 4) |
| Základní DA při všech rezervách | 36 | 20 |
| SE rezerva | 1 | 0 |
| WC | 4 běžné + 1 podmíněná A+ | 4 |
| Řádné Q postupy | 6 | 6 |
| Nasazení | 16 | 12 |
| BYE | 16, všichni původní seedy | 0 |
| Kola / zápasy | 6 / 47 | 2 / 18 |
| Formát | BO3 setů | BO3 setů |

Dobový §7.08 B.1.b pro ATP 500/48 hráčů výslovně 36–38 DA, 6 Q, 4–5 WC, 0–1 SE; při využití všech rezerv 36+1+4+1+6=48. Pátá WC pouze pro způsobilého A+ hráče z regionu dle §7.12 A.2. Přepis listiny BCN24-6 uvádí 36 DA, 4 WC, 6 Q, 0 SE: 46 obsazených míst v mezistavu, nikoli plánovaný 46členný pavouk. Uvolněná rezervovaná místa přecházejí na další způsobilé vstupy. ATP Day 1 uvádí čtyři WC, šest řádných Q, jeden LL a jednoho PR, nikoli využitou A+ WC. Konečný Main originál má WC 6/46/52/60, Q 28/29/37/38/53/59, LL 11/49, 16 BYE. Po odstoupení seed 1 Alcaraze přemístěn Marozsan [17] na pozici 1 a LL Grenier obsadil jeho původní místo; po odstoupení seed 7 Khachanova LL Vavassori zdědil pozici 49 včetně BYE. Původní seed list 1–16 se zachovává v patičce, dva vyškrtnuté; označení 17 ani LL s BYE nemění nominálních 16 seedů a 16 BYE. PR Nadal náleží mezi DA. Main 16+16+8+4+2+1=47, 48 účastníků.

Q §7.08 E.1: 20 DA+4 WC=24; Q originál vizuálně potvrzuje všech 12 seedů, WC 3/6/11/14, Alt 18. Šest sekcí po čtyřech, dvě nasazené pozice v každé, šest vítězů. 12+6=18 zápasů. Dva následní LL nepřidávají řádná Q postupová místa. Obě kopie Q jsou výsledkové, nikoli nezávislé předstartovní losy.

### 5. Dobová pravidla

§7.03/7.08 B/E/7.09/7.10/7.12/7.15–18/7.20, verze VII z 16.2.2024 (BCN24-11). 48členný Main na 64 pozicích, 16 seedů a 16 BYE; 24členná kvalifikace má šest samostatných sekcí. Jedna SE rezerva, čtyři WC a podmíněná A+ WC; žádná ATP 250 LE. BO3 tiebreak sety. Bodová tabulka pro ATP 500 s 48 hráči se liší od ATP 500 s 32: Q postup 16, Q2 prohra 8, Q1 0 (BCN24-2/12), Main R32 25 a R64 0. ATP Media Notes potvrzují výjimku první prohry po BYE v R32: 0 bodů místo 25, peněžní odměna tím není změněna. Q body přičítat k Main dle předpisu. #NextGenATP jména v Media Notes nejsou dokladem speciálního vstupu: Landaluce WC, Shang řádný Q, Fils běžný DA; přesná individuální alokace případných týdenních NG rezerv Munich/Bucharest otevřena, neodvozovat další slot v Barceloně.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 488390 |
| Finalista | 1 | 330 | 260475 |
| SF | 2 | 200 | 135125 |
| QF | 4 | 100 | 70550 |
| R16 | 8 | 50 | 37175 |
| R32 | 16 | 25 (0 při první prohře po BYE) | 20350 |
| R64 | 16 | 0 | 10855 |
| Q postupující | 6 | 16 | 0 samostatně |
| Q2 prohra | 6 | 8 | 5700 |
| Q1 prohra | 12 | 0 | 3255 |

Main originál (ATP i RFET kopie) má v tabulce a financial commitment chybný symbol $, nikoli jiná čísla. ATP Media Notes 15.4. přímo označují jednotlivé částky EUR a předturnajový ATP přehled potvrzuje totéž, včetně celkové dotace 2782960 EUR a commitment 2938695 EUR. Q originál používá EUR. P bez hvězdičky, měnový rozpor vyřešen primárními dokumenty. Nominální Main 2097995 EUR, Q 73260 EUR, celkem 2171255 EUR; 48 Main příjemců a 18 nepostupujících Q příjemců. Celková turnajová dotace a commitment nejsou singlový součet. Historické LL payout nezahrnuty.

### 7. Kontrola a mezery

I/T/D/B/P doloženy. H* původní denní rozpisy mimo finále nedohledány; okna a denní rozdělení z dobového programu a výsledků, walkover oddělen. E* chybí originální acceptance lists/DS, časy losů a ročníkový doklad Q rank date; uzávěrky odvozené. R* týdenní NG alokace otevřena. Z* ATP Main/Q, obě RFET kopie a poslední OOP (vše po jedné straně) vizuálně ověřeny; ATP notes str. 2 a únorový rulebook textově, screenshoty 403. Nevymýšlet SHA-256. Kontroly 48/24, 16/12 seedů, 16/0 BYE, 6 řádných Q, 47/18 utkání, kvót a finančních součtů prošly. Další Munich, Bucharest 2024. Bez runtime změn.

### 8. Zdroje (BCN24)

- BCN24-1: [ATP výsledkový Main](https://www.protennislive.com/posting/2024/425/mds.pdf), [RFET kopie](https://www.rfet.es/descargar/file-competicion-cuadros/19750_Cuadro/2024-barcelona-open-banc-sabadell-individual.pdf), obě vizuálně, chybné $.
- BCN24-2: [ATP výsledkový Q](https://www.protennislive.com/posting/2024/425/qs.pdf), [RFET kopie](https://www.rfet.es/descargar/file-competicion-cuadros/19744_Cuadro/2024-barcelona-open-banc-sabadell-previa.pdf), obě vizuálně; 12 seedů, 4 WC, EUR a 16/8/0.
- BCN24-3: [ATP OOP finále](https://www.protennislive.com/posting/2024/425/op.pdf), vizuálně, vydání 20.4. 20:17, neděle 16:00 nejdříve.
- BCN24-4: [ATP Preview & Day 1 15.4.](https://www.atptour.com/-/media/02b75ee196ac47bab051b508841d7ac6.pdf), str. 2 text, screenshot 403; EUR, body a BYE výjimka, vstupy.
- BCN24-5: [ATP termíny a prize money](https://www.atptour.com/en/news/barcelona-2024-atp-500-history-draw-schedule), indexovaný text, přímé otevření 403.
- BCN24-6: [dobový přepis Main listiny 11.4.](https://www.tennisteen.it/entry-list/atp/24150-atp-entry-list-15-21-aprile-2024.html), rank date, cutoff a kvóty.
- BCN24-7: [Q1 13.4.](https://en.tennistemple.com/competitions/barcelona/2024/orderofplay/2024-04-13), [Q2 14.4.](https://en.tennistemple.com/competitions/barcelona/2024/orderofplay/2024-04-14), výsledkové dny.
- BCN24-8: [dobový denní program a výsledky](https://tennisuptodate.com/atp/2024-barcelona-open-atp-tournament-centre-results-schedules-tv-guide-and-prize-money-breakdown-for-rafael-nadals-return), 9+7 R64, 5+11 R32, rozpis R16; obsahuje následné výsledkové aktualizace, nikoli kompletní původní OOP.
- BCN24-9: [ročníkový přehled 2024](https://en.wikipedia.org/wiki/2024_Barcelona_Open_Banc_Sabadell), 71. ročník, místo a celková dotace.
- BCN24-10: [dobový denní soupis](https://canaltenis.com/resultados-atp-barcelona-2024/), [Tennis Abstract](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024-0425%2FBarcelona), kontrola výsledků, nikoli originální OOP.
- BCN24-11: [ATP Competition VII 16.2.2024](https://www.atptour.com/-/media/files/rulebook/2024/2024-rulebook-chapter-7_the-competition_16feb.pdf), §7.08 B/E, §7.09, tištěné str. 146/149–150, text, screenshot 403.
- BCN24-12: [ATP ranking update 2024](https://www.atptour.com/en/news/2024-rankings-points-update), zvláštní řádek ATP 500 48 Draw, shoda s Q originálem.


## Munich 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/P/Z s doplňkovými omezeními). Rešerše 2026-11-27. Poslední ročník ATP 250 před povýšením na ATP 500 v roce 2025. Main odměny z dobových oficiálních ATP Media Notes, Q ze shodných ročníkových sekundárních tabulek. Originální historické Main/Q PDF se nepodařilo otevřít; finálový ATP OOP vizuálně ověřen. Dobová listina obsahuje plánovanou NG akceptaci a využití LE rezervy.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | BMW Open (v kalendáři též BMW Open by American Express) | MUC24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 308 | MUC24-1/2/3 |
| Ročník | 55. podle ATP Media Notes (otevřená éra), 108. podle širší historické chronologie | MUC24-1/4 |
| Dějiště | MTTC Iphitos, Mnichov, Německo | MUC24-1/5 |
| Povrch | venkovní antuka | MUC24-5/6 |
| Časové pásmo | Europe/Berlin, CEST UTC+02:00 během soutěže | lokalita a datum |
| Ředitel | Patrik Kühnen | MUC24-2/7 |
| ATP supervisor / referee | Roland Herfel / Norbert Peick | MUC24-2 |
| Tour manager | Nicolas Rakitin | MUC24-2 |
| Měna | EUR | MUC24-1 |

Pořadatel 12.4. výslovně označuje ročník jako poslední ATP 250. Nepřenášet kategorii ATP 500 ani její pozdější kapacitu a odměny do 2024. Přesný výrobek povrchu, míče a detail sheet nezískány. Pořadatel navíc oznámil věcnou výhru pro vítěze, BMW i5 M60; oddělit od peněžních odměn a nepřičítat odhadovanou hodnotu automobilu k prize money.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-18 | MUC24-8 |
| Q rank date | 2024-03-25, odvozený referenční den | §7.03, originální Q listina nezískána |
| Nominální Main deadline | 2024-03-18 17:00 CET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-03-25 17:00 CET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální LE deadline | 2024-04-11 16:00 CEST (10:00 US Eastern) | odvozeno §7.04 |
| Main los | 2024-04-13, hodina neověřena | MUC24-9/10 |
| Q los | nejpozději před Q1 2024-04-13, čas a den losu neověřeny | MUC24-11/12 |
| Q | 2024-04-13–14 | MUC24-5/11/12 |
| Main | 2024-04-15–21 | MUC24-1/2/3/5 |
| Singlové finále | 2024-04-21 13:30 CEST | MUC24-1/2/7 |

Přepis listiny 11.4. uvádí původní Main cutoff 84, 18 DA, 3 WC, 4 Q, SE 0 a LE 1; konečný cutoff Main/Q neověřen. Rank date není nezávislý doklad okamžiku uzávěrky; časy odvozeny z pravidla, s ohledem na odlišné datum přechodu na letní čas v USA a Evropě. Pořadatel 14.4. retrospektivně potvrzuje sobotní losování Main, nikoli jeho hodinu. Finálový čas potvrzuje dobové oznámení z 12.4., ATP Preview z 15.4. i poslední OOP z 20.4. Rozpis čtyřhry se mezitím změnil (ATP Preview uvádí 11:00, finálový OOP až po singlu), což nemění plán mužského singlového finále.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-04-13 | 8 |
| Q2 | 2024-04-14 | 4 |
| R32 | 2024-04-15–16 | 12 (4+8 rekonstruováno) |
| R16 | 2024-04-17–18 | 8 |
| QF | 2024-04-19 | 4 |
| SF | 2024-04-20 | 2 |
| F | 2024-04-21 | 1 |

Dobový přehled kol MUC24-5 uvádí všechna okna v tabulce. Q 8+4 doloženo výsledkovým přehledem MUC24-11/12. Zpráva z 15.4. MUC24-13 jmenuje čtyři pondělní R32 zápasy, které byly naplánovány a nakonec dokončeny i po dlouhé dešťové pauze; osm dalších R32 tedy připadá na plánované úterý, úplný původní OOP obou dnů nezískán. R16 nominální okno 17.–18.4. doloženo, přesné původní denní dělení před deštěm nezjištěno. Výsledkové zdroje a ATP potvrzují opakované dešťové a kroupové pauzy. Páteční QF Struff–Auger-Aliassime byl přerušen počasím a tmou, dohrán v sobotu před SF (MUC24-5/14); nominálně zůstává v pátek, nepřidávat sobotní QF. Poslední originální OOP vydán 20.4. 18:33, neděle 21.4. 13:30 singlové finále, později doubles; finále samostatné Rudi Berger Cup na vedlejším kurtu není zápas ATP Main. Q 2 dny + Main 7 dní bez plánovaného překryvu, 9 kalendářních dní, 39 nominálních singlových zápasů. Kvalifikace se koná během závěrečného víkendu Monte-Carlo.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 |
| Základní DA (včetně NG) | 18 | 14 |
| SE rezervy | 2 | 0 |
| LE rezerva | 1 | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4, top 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

§7.08 B/E pro ATP 250: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28. Dobový přepis Main listiny MUC24-8 obsahuje 18 DA (17 běžných a Prižmić NG), 3 WC, 4 Q, SE 0, LE 1; dvě neobsazené SE rezervy nejsou zmenšení pavouku. Konečný Main podle ATP Media Notes a sekundárního výsledkového pavouku má osm seedů, čtyři BYE, tři WC Molleker, Rehberg a Topo, čtyři řádné Q Gakhov, Hüsler, Moro Cañas a Passaro. Main 12+8+4+2+1=27. Původní příslib WC Thiemovi a Berrettinimu v březnové listině nepřebírat jako konečný WC stav; dobová ORF zpráva potvrzuje, že Thiem nakonec vstoupil bez WC.

Q 14 DA+2 WC dle dobového §7.08 E.1, osm nominálních seedů. Sekundární ročníkový pavouk MUC24-12/15 označuje seed 2 Molleker jako přesunutého do Main WC, skutečný Q pavouk má sedm označených seedů a Alt Naw a Masur; zachovat osm nominálně nasazených, nikoli sedm. Dva WC Kelm a Haupt v úplném Q výsledkovém pavouku. Čtyři sekce po čtyřech, 8+4=12 utkání, čtyři postupující. Originální Q PDF ani předstartovní Q acceptance list nedostupné, nejde o vizuální ověření originálu.

### 5. Dobová pravidla a vstupní návaznosti

§7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 v únorové verzi (SCL24-18), změny LCB24-19 v příslušném rozsahu. Dvě SE a jedna LE rezerva; nevyužitá místa přecházejí do DA. BO3 tiebreak, osm seedů, čtyři Main BYE, čtyři Q sekce. Main první prohra po BYE v R16 znamená nula bodů, ATP Media Notes MUC24-1; Q 13/7/0 podle dobového ATP rankingového předpisu. Q body se přičtou k Main výsledku.

**LE a NG v konkrétním ročníku:** MUC24-8 explicitně uvádí LE 1 a Prižmiće na 18. DA pozici s NG označením; nezávislý dobový přepis MUC24-16 má rovněž Prižmić NG. Pořadatel 28.3. oznámil jeho účast, v konečném pavouku není; sekundární ročníkový přehled uvádí náhradu Ugo Carabellim. Jde o důkaz plánované NG Main akceptace, nikoli skutečně odehraného zápasu ani detailního administrativního propadu rezervy. Pořadatel 12.4. oznámil dodatečné potvrzení Fritze; ročníková listina uvádí LE 1, retrospektivní článek z dubna 2025 (MUC24-17) výslovně potvrzuje, že Fritz využil v roce 2024 Late Entry místo. Silná kombinace dokladů, nikoli originální LE formulář nebo potvrzený individuální timestamp. NG je uvnitř DA kapacity, LE má vlastní rezervu, žádné místo nad 28. Q NG alokace pro týden Barcelona/Munich/Bucharest zůstává neověřena; Michelsenova běžná DA účast je potvrzena pořadatelem, samotné označení #NextGenATP v ATP notes není jiný vstupní mechanismus.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main tabulka oficiální ATP Media Notes (MUC24-1, text, screenshot 403), Q ceny shodně v ročníkovém sloupci 2024 TennisCompanion a tabulce ATP München (MUC24-18/19), sekundární shoda, nezávislost jejich vzniku neprokázána. P*; dobové Q body z rankingového předpisu. Nominální Main 425905 EUR, Q 25980 EUR, celkem 451885 EUR. Turnajová dotace 579320 EUR z dobového SuperTennis a commitment 651865 EUR z kalendáře nejsou singlový součet. Věcný automobilový bonus evidován odděleně, bez přičtení k finanční tabulce. Q postupující získávají Main odměnu podle výsledku, skutečné LL payout nezahrnuty.

### 7. Kontrola a mezery

I/T/D/B doloženy. H* úplný původní OOP mimo finále a předdešťový denní R16 split nezískány. E* originální acceptance listy/DS, Q rank date, cutoffs, hodiny losů a individuální LE administrativní doklad chybí, termíny odvozené. R* Q NG alokace otevřena; plánovaná Main NG akceptace Prižmiće a Fritzův LE doloženy výše. P* Q sekundární shoda; Z* poslední ATP OOP str. 1 vizuálně, ATP Preview str. 1 textově (screenshot 403); přímé historické Main/Q originály nedostupné. V indexovaném vyhledávání nalezen Main soubor jiného ročníku s Altmaierem WC, proto nepoužit jako 2024. Bez neověřených hashů. Aritmetická kontrola kvót, 28/16 účastníků, 8/8 seedů, 4/0 BYE, 27/12 utkání, počtu příjemců a odměn prošla. Další Bucharest 2024. Bez runtime změn.

### 8. Zdroje (MUC24)

- MUC24-1: [ATP Preview & Day 1 15.4.2024](https://www.atptour.com/-/media/a6851118613048b89893756911626a7b.pdf), str. 1 text, screenshot 403, Main ceny/body, WC/Q, 55. ročník, singlové finále.
- MUC24-2: [originální ATP OOP finále 21.4.](https://www.protennislive.com/posting/2024/308/op.pdf), str. 1 vizuálně, vydání 20.4. 18:33.
- MUC24-3: [Tennis Europe BMW Open by American Express 2024](https://www.tenniseurope.org/calendarevent/73812/BMW-Open-by-American-Express), identita ATP 308; [dobový ATP kalendář 8.3.](https://www.atptour.com/-/media/files/calendar-pdfs/2024/2024-atp-challenger-calendar-as-of-8-march-2024.pdf), indexovaný řádek 28/ATP 250.
- MUC24-4: [ročníkový přehled 2024](https://en.wikipedia.org/wiki/2024_BMW_Open), 108. ročník a místo.
- MUC24-5: [tennis MAGAZIN, dobový program všech dnů](https://www.tennismagazin.de/news/bmw-open-2024-spielplan-nicht-verpassen/), okna kol, průběžné aktualizace a dešťová QF dohrávka.
- MUC24-6: [SuperTennis Q1 13.4.](https://www.supertennis.tv/News/Atp/Monaco-di-Baviera-risultati-primo-turno-qualificazioni-italiani), červená antuka a 579320 EUR.
- MUC24-7: [pořadatel 12.4.2024, Fritz, poslední ATP250, věcná výhra a finálový čas](https://www.bmwopen.de/2024/04/12/bmw-open-2024-taylor-fritz-gibt-zusage-bmw-siegerfahrzeug-enthuellt-erstmalig-alle-neun-tage-ausverkauft/).
- MUC24-8: [dobový přepis Main listiny 11.4.](https://www.tennisteen.it/entry-list/atp/24150-atp-entry-list-15-21-aprile-2024.html), řádky 127–159, kvóty, rank date, LE a NG.
- MUC24-9: [pořadatel 14.4., sobotní los a Q dokončení](https://www.bmwopen.de/2024/04/14/alles-bereit-fuer-das-hauptfeld/).
- MUC24-10: [dobová publikace Main losu 13.4.](https://tennisuptodate.com/atp/2024-bmw-open-munich-atp-draw-featuring-alexander-zverev-holger-rune-and-taylor-fritz-as-top-seeds), [ORF 13.4., Thiem bez WC](https://sport.orf.at/stories/3124409/).
- MUC24-11: [Tennis Explorer Q 2024](https://www.tennisexplorer.com/munich/2024/atp-men/?phase=qualification), 8+4 utkání, výsledkové dny.
- MUC24-12: [TennisTemple Q 2024](https://fr.tennistemple.com/competitions/munich/2024/draw-qualifications), sedm skutečně označených seedů, 2 WC, 2 Alt.
- MUC24-13: [tz 15.–16.4., pondělní plán a výsledky](https://www.tz.de/muenchen/stadt/bmw-open-muenchen-regenpause-match-atp-tennis-turnier-regen-sandplatz-wetter-93011779.html), čtyři R32.
- MUC24-14: [Tennis Explorer Main 2024](https://www.tennisexplorer.com/munich/2024/atp-men/), sobotní QF dokončení; [ATP 17.4. o kroupách](https://www.atptour.com/en/news/zverev-draper-munich-2024-wednesday).
- MUC24-15: [ročníkový Main/Q pavouk](https://en.wikipedia.org/wiki/2024_BMW_Open_%E2%80%93_Singles), seed 2 Q přesunut do Main, [německý Q přehled](https://de.wikipedia.org/wiki/BMW_Open_2024/Qualifikation).
- MUC24-16: [dobový přepis vstupů s NG označením](https://tennisuptodate.com/atp/atp-entry-list-2024-bmw-open-munich-headlined-by-alexander-zverev-holger-rune-and-jan-lennard-struff), [pořadatel 28.3.](https://www.bmwopen.de/2024/03/28/grose-namen-bei-den-bmw-open-2024/).
- MUC24-17: [tz retrospektiva LE Fritze 2024 v článku 2025](https://www.tz.de/sport/zwei-heisse-wildcard-eisen-fuer-die-bmw-open-in-muenchen-zr-93667223.html), doplňuje dobové MUC24-7/8.
- MUC24-18: [TennisCompanion, historické EUR sloupce](https://tenniscompanion.org/prize-money/munich/), 2024 Q 3105/1695.
- MUC24-19: [ATP München, ročníková finanční tabulka](https://de.wikipedia.org/wiki/ATP_M%C3%BCnchen), 2024 shoda Q.
- [Původní ATP Main](https://www.protennislive.com/posting/2024/308/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/308/qs.pdf) při kontrole nedostupné. Dobová pravidla viz SCL24-18, LCB24-19, ROT24-16.


## Bucharest 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/R/P/Z s označenými mezerami). Rešerše 2026-11-27. Návrat ATP do Bukurešti po osmi letech. Předstartovní Main originál vizuálně ověřen ve dvou archivních kopiích, výsledkový Main v primárním textu. Nedělní Q1 a pondělní Q2/Main souběh potvrzeny programem před zahájením Main. Q finanční tabulka sekundární shoda tří ročníkových přehledů; konfliktní zastaralá tabulka zdokumentována.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Țiriac Open | BUC24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 4462 | BUC24-1/14 |
| Ročník | 25. dle ATP (1993–2016, 2024), 22. podle místního počítání 1996–2016 a 2024 | BUC24-3/4/5 |
| Dějiště | Baza Sportivă Năstase–Marica, Bukurešť, Rumunsko; ATP notes Tiriac Stadium | BUC24-3/4/5 |
| Povrch | venkovní červená antuka | BUC24-1/2/4 |
| Časové pásmo | Europe/Bucharest, EEST UTC+03:00 během soutěže | lokalita a datum |
| Ředitel | Cosmin Hodor (sekundární ročníkový přehled) | BUC24-14 |
| ATP supervisor | Zsolt Beda | BUC24-1/2 |
| Měna | EUR | BUC24-1/2 |

Nepřenášet dějiště 2025 National Tennis Center ani předchozí Arenele BNR do roku 2024; pořadatel potvrzuje nové dějiště 2025 (BUC24-15). Míče, detail sheet, referee a tour manager neověřeny. Rozdílné historické počítání ročníků zachovat.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-18 | BUC24-6 |
| Q rank date | 2024-03-25, odvozený referenční den | §7.03 |
| Nominální Main deadline | 2024-03-18 18:00 EET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-03-25 18:00 EET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální LE deadline | 2024-04-11 17:00 EEST (10:00 US Eastern) | odvozeno §7.04 |
| Main los | 2024-04-13 13:00 EEST, oznámený plán | BUC24-7 |
| Q los | nejpozději před Q1 dne 2024-04-14, čas neověřen | BUC24-5/8 |
| Q | 2024-04-14–15 | BUC24-4/5/8 |
| Main | 2024-04-15–21 | BUC24-1/2/3 |
| Singlové finále | 2024-04-21 ne před 15:00 EEST | BUC24-3/4 |

Místní rozhlas 11.4. oznámil los na sobotu 13.4. ve 13:00, zprávy 13.4. potvrzují den konání, nikoli nezávisle přesný okamžik. Přepis Main entry listu 11.4. má původní cutoff 88; obě originální Main verze uvádějí Moutet 107 v deadline i draw polích. Odlišné publikované stavy nesjednocovat. Uzávěrky odvozené z dobového předpisu; Q rank date/cutoff, originální acceptance lists a DS nezískány. V březnu se americký letní čas změnil dříve než rumunský.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-04-14 | 8 |
| Q2 | 2024-04-15 | 4 |
| R32 | 2024-04-15–16 | 12 (4+8) |
| R16 | 2024-04-17–18 | 8 |
| QF | 2024-04-19 | 4 |
| SF | 2024-04-20 | 2 |
| F | 2024-04-21 | 1 |

Předturnajový program vstupenek publikovaný 12.4. (BUC24-4) potvrzuje nedělní kvalifikační start, pondělní kombinaci kvalifikace a R32, úterní R32 a R16 ve středu/čtvrtek. Páteční a sobotní popis v této zprávě opakuje čtvrtfinále a doubles SF pro oba dny, proto z něj neodvozovat nominální QF dělení. Nedělní zpráva GSP 14.4. (BUC24-5) uvádí všech osm Q1 výsledků, a především úplný předem publikovaný pondělní program: čtyři Main R32 na centru, čtyři Q2 na kurtech 1/2 a dvě doubles utkání. Nominální pondělní souběh 4 Q2 + 4 R32 tedy není důsledkem deště; zbývá osm R32 pro úterý. Jeden R32 Barrere–Kokkinakis se skutečně dokončil ve středu 17.4. a pouze Tabilo–Rinderknech z R16 se stihl celý před deštěm. ATP zpráva a místní GSP dokládají zrušení zbytku středečního programu (BUC24-9). Čtyři R16 dokončeny až v pátek; přesné původní denní rozdělení R16 neověřeno. Páteční QF Cerundolo–Navone přerušen tmou bez umělého osvětlení, dohrán v sobotu před SF (BUC24-10). Nominální páteční QF a sobotní SF rekonstruovány z průběhu a dokladu pátečního přerušení, nikoli z úplného předturnajového OOP. Nedělní singlové finále plánované na 15:00 bylo skutečně dokončeno v neděli 21.4. (BUC24-11), žádný pondělní přesun singlového finále. Q 2 + Main 7 dní − 1 plánovaný překryv = 8 kalendářních dní, 39 nominálních zápasů. Q1 se překrývá s finále předchozího Monte-Carlo.

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

Dobový §7.08 B/E: 18 DA + 2 SE + 1 LE + 3 WC + 4 Q = 28. Přepis BUC24-6 obsahuje 18 DA, 3 WC, 4 Q, SE 0, LE 0 (mezistav 25). Předstartovní originál BUC24-1 potvrzuje 21 běžných vstupů, WC Gasquet, Fonseca, Shapovalov na 3/18/28, Q placeholdery 11/15/19/29, osm seedů a BYE 2/10/23/31. Nevyužité rezervy doplněny do DA. Výsledkový Main BUC24-2 a ATP Media Notes potvrzují LL Bonzi na pozici 3 po odstoupení WC Gasqueta pro nemoc. Tato náhrada není pátý řádný Q postup ani nominální snížení WC kvóty. Čtyři řádní Q Albot, Barrere, Taberner, Vacherot. Main 12+8+4+2+1=27.

Q 14 DA+2 WC podle §7.08 E.1; úplný výsledkový pavouk BUC24-8 potvrzuje osm seedů Dzumhur, Barrere, Albot, Vacherot, Zeppieri, Droguet, Misolic, Bonzi, dvě WC Pouille a Copil, čtyři označené Alt Taberner, Cretu, Jianu, Pavel. Čtyři sekce po čtyřech, 8+4=12 zápasů; skreč v Q1 nemění nominální uzly. Původní Q PDF a acceptance list nedostupné, struktura doložena dobovým přepisem a výsledky.

### 5. Dobová pravidla

§7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 v únorové verzi (SCL24-18), s příslušnými účinnými změnami LCB24-19. Dvě SE, jedna LE rezerva, čtyři Main BYE, osm seedů v každé fázi, čtyři Q sekce, BO3 tiebreak. ATP notes BUC24-3 přímo potvrzují výjimku nula bodů při první prohře po BYE. Q 13/7/0 podle dobového ATP předpisu, body se přičítají k Main výsledku. WC po odstoupení před zápasem nahrazena LL; další individuální peněžní nároky necertifikovat pouze podle sekundárních payoutů.

Týden Barcelona/Munich/Bucharest: ATP Media Notes výslovně uvádějí Fonsecu jako #NextGenATP a WC. Jeho skutečný Main vstup je běžná WC, nikoli doklad využití zvláštní NG rezervy. Dobový Main přepis neobsahuje v Bukurešti NG označení; plánovaná NG Main akceptace Prižmiće v Mnichově je již zdokumentována (MUC24). Přesná týdenní alokace Q NG příležitostí nadále neověřena. Nezvyšovat nominální kapacity.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main originál vizuálně v BUC24-1 a výsledkový text BUC24-2 potvrzují EUR a všech šest částek i body. ATP notes BUC24-3 chybně uvádějí symbol $ v názvu sloupce; originální losy a ročníková dotace jsou EUR. Dobové rumunské mediální zprávy BUC24-7 uvádějí 150 bodů finalistovi, ale přednost mají originální ATP 165. Q 3105/1695 EUR ve třech shodných ročníkových tabulkách BUC24-12/13/14; sekundární nezávislost jejich vzniku neprokázána. TennisTemple BUC24-8 uvádí 3020/1645 a zastaralé body 12/6. Tyto hodnoty odpovídají staršímu obecnému rozpisu 2023 zdokumentovanému v RAK24, nikoli předchozímu ročníku Bukurešti, který v roce 2023 neexistoval. Proto nepovažovat za rovnocenný 2024 protidoklad. Další nepřímá kontrola: BUC24-16 uvádí Bonziho kombinovaný payout 9320 EUR = 6215+3105; současně u Kordy po BYE uvádí odlišnou částku, kterou bez primárního vyúčtování nelze vydávat za nominální tabulku. P* Q sekundární shoda, originální Q finanční tabulka stále chybí. Nominální Main 425905 EUR, Q 25980 EUR, celkem 451885 EUR. Nominální částky podle kola z losu, nikoli skutečně vyplacený součet včetně LL a individuálních výjimek. Turnajová dotace 579320 EUR a financial commitment 651865 EUR samostatné veličiny.

### 7. Kontrola a mezery

I/T/D/B doloženy. H* plánovaný pondělní souběh a R32 4+8 potvrzeny, původní R16 denní split a úplný OOP nezískány; QF/SF rekonstrukce s dobovou dokumentací dohrávky. E* originální acceptance lists/DS, Q rank date/cutoff a čas losu chybějí. R* týdenní Q NG alokace otevřena. P* Main originál, Q sekundární shoda s popsaným konfliktem. Z* dvě archivní kopie stejného předstartovního Main originálu vizuálně, výsledkový ATP Main text (screenshot DisabledError), ATP Media Notes str. 1/2 text (screenshoty 403), přímý Q PDF nedostupný. Bez neověřených hashů. Kontroly kvót, 8/8 seedů, 4/0 BYE, 27/12 utkání, denních součtů a peněz prošly. Další Madrid 2024, ATP předturnajový přehled BUC24-17 potvrzuje Q 22.–23.4. a Main 24.4.–5.5. Bez runtime změn.

### 8. Zdroje (BUC24)

- BUC24-1: [předstartovní originální Main Raquetc](https://www.raquetc.com/wp-content/uploads/2024/04/ATP-250-Bucareste-2024-quadro-principal.pdf), [archivní kopie Fantatennis](https://www.fantatennis.net/_downloads/03a408fea3c351219c08354041e87fbb), obě str. 1 vizuálně.
- BUC24-2: [ATP výsledkový Main](https://www.protennislive.com/posting/2024/4462/mds.pdf), text, screenshot DisabledError; [Q PDF](https://www.protennislive.com/posting/2024/4462/qs.pdf) nedostupné.
- BUC24-3: [ATP Preview & Day 1 15.4.2024](https://www.atptour.com/-/media/1584a0f6b38242dab78db712e1b02b35.pdf), str. 1–2 text, oba screenshoty 403, 25. ročník, Main odměny, body, LL a finále.
- BUC24-4: [TVR 12.4., předturnajový program](https://tvrinfo.ro/incepe-turneul-international-de-tenis-atp-250-tiriac-open-premii-de-600-000-de-euro/), Q/Main okna, předprodej, finále ne před 15:00; závěrečný víkend v textu nepřesně popsán.
- BUC24-5: [GSP 14.4., všech osm Q1 a předem zveřejněný pondělní program](https://www.gsp.ro/sporturi/tenis/tiriac-open-bucuresti-dupa-8-ani-primul-antrenament-stan-wawrinka-738386.html).
- BUC24-6: [dobový Main entry list 11.4.](https://www.tennisteen.it/entry-list/atp/24150-atp-entry-list-15-21-aprile-2024.html), ř. 160–190.
- BUC24-7: [Radio București 11.4., plán losu](https://www.bucurestifm.ro/2024/04/11/tragerea-la-sorti-a-turneului-atp-250-tiriac-open-are-loc-pe-13-aprilie/), [Mediafax 13.4., los](https://www.mediafax.ro/sport/s-au-tras-la-sorti-meciurile-de-pe-tabloul-principal-al-tiriac-open-de-la-bucuresti-22337275), 150 bodů finalisty v médiích je v rozporu s ATP.
- BUC24-8: [TennisTemple Q pavouk](https://de.tennistemple.com/competitions/bucharest/2024/draw-qualifications), geometrie a vstupy, zastaralé body/ceny; [Sky Q1 14.4.](https://www.skysports.com/tennis/scores-schedule/14-04-2024), [Sky Q2 15.4.](https://www.skysports.com/tennis/scores-schedule/15-04-2024).
- BUC24-9: [pořadatel/ATP 17.4., déšť](https://tiriacopen.ro/en/media/news/fonseca-bucharest-2024-rain), [GSP 17.4. výsledky a revidovaný čtvrteční program](https://www.gsp.ro/sporturi/tenis/tiriac-open-ploaie-persistenta-si-doar-trei-meciuri-incheiate-programul-zilei-a-cincea-738786.html).
- BUC24-10: [Tennis Explorer Main](https://www.tennisexplorer.com/bucharest/2024/atp-men/), [Radio România 20.4. přesuny](https://www.romania-actualitati.ro/stiri/sport/tiriac-open-primii-semifinalisti-id191992.html), [TyC Sports 19.4., QF přerušení tmou](https://www.tycsports.com/tenis/indignacion-por-insolito-motivo-que-freno-duelo-argentino-atp-250-bucarest-id579071.html).
- BUC24-11: [ATP finále 21.4.](https://www.atptour.com/en/news/fucsovics-navone-bucharest-2024-final), [Radio România 21.4.](https://www.romania-actualitati.ro/stiri/sport/marton-fucsovics-campion-la-tiriac-open-2024-id192036.html), skutečný nedělní konec.
- BUC24-12: [TennisCompanion EUR ročníkový sloupec 2024](https://tenniscompanion.org/prize-money/bucharest/), Q 3105/1695.
- BUC24-13: [Canal Tenis ročníkový oddíl 2024](https://canaltenis.com/prize-money-atp-bucarest/), Q shoda.
- BUC24-14: [ročníkový přehled 2024](https://de.wikipedia.org/wiki/%C8%9Airiac_Open_2024), identita 4462, ředitel, Q ceny/body a dotace.
- BUC24-15: [pořadatel 17.2.2025, nové dějiště National Tennis Center](https://www.tiriacopen.ro/en/media/news/comunicat-tiriac-open).
- BUC24-16: [Open Era Rankings 2024](https://openerarankings.com/Draws?DrawType=QS&tID=25310), nepřímý LL payout, nikoli primární nominální rozpis.
- BUC24-17: [ATP předturnajový přehled Madrid 2024](https://www.atptour.com/en/news/madrid-2024-atp-masters-1000-history-draw-schedule), následující ročník. Dobová pravidla viz SCL24-18, LCB24-19, ROT24-16.


## Madrid 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/Z s doplňkovými omezeními). Rešerše 2026-11-27. Originální ATP Main (obě strany), Q a poslední OOP vizuálně ověřeny. Únorový i dubnový plán pořadatele vizuálně ověřeny na první straně. Primární ročníkové ceny, odlišné od amerických Masters, a konkrétní chyby sekundárních zdrojů zdokumentovány.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Mutua Madrid Open, mužská dvouhra, 22. ročník | MAD24-1/8 |
| Kategorie / ATP ID | ATP Masters 1000 / 1536 | MAD24-1/2/8 |
| Dějiště | Caja Mágica, Madrid, Španělsko | MAD24-4/6 |
| Povrch | červená antuka, venkovní s možností zastřešení | MAD24-1/2/8 |
| Časové pásmo | Europe/Madrid, CEST UTC+02:00 během soutěže | lokalita a datum |
| Ředitel | Feliciano López | MAD24-3 |
| ATP supervisors | HJ Ochs, J. Mandl, C. Mourier, A. Egli | MAD24-1/2/3 |
| ATP tour managers / referees | T. Schrader, D. Pedraza / I. Martinez, R. De Haro | MAD24-3 |
| Měna | EUR | MAD24-1/2 |

Míče a detail sheet nezískány. Nezaměňovat s WTA 1000 (ID 1038) nebo Madrid Challenger. Rok 2024 již druhý rozšířený 96členný ročník po změně v roce 2023, potvrzeno pořadatelem 26.3. (MAD24-6).

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-03-25 | MAD24-5/6 |
| Q rank date | 2024-04-01 | MAD24-5 |
| Nominální Main deadline | 2024-03-25 17:00 CET (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-04-01 18:00 CEST (12:00 US Eastern) | odvozeno §7.03 |
| Main los | 2024-04-22, hodina neověřena | MAD24-4/9 |
| Q los | nejpozději před Q1 2024-04-22, přesný čas a den neověřeny | MAD24-2/10 |
| Q | 2024-04-22–23; start session 10:00/11:00 CEST podle pozdějšího plánu | MAD24-4/7/10 |
| Main | 2024-04-24–2024-05-05 | MAD24-1/4/7 |
| Singlové finále | 2024-05-05 ne před 18:30 CEST | MAD24-3/7 |

Pořadatel zveřejnil 26.3. 79 přijatých hráčů, původní Main cutoff Darderi 75. Dobový přepis MAD24-5 potvrzuje cutoff 75, Q 127 a obě rank dates. Výsledkový Main má Galan 84 v obou cutoff polích, Q originál Droguet 149. Jde o odlišné publikované údaje, nesjednocovat bez originálních acceptance lists. Přesné uzávěrky jsou pravidlová odvození. Evropská změna času 31.3. mění místní převod mezi oběma uzávěrkami. Únorový plán uvádí pro 23.4. společnou session od 10:00, dubnový 11:00; zachovat později publikovaný plán. Přesný čas Main/Q losu a nezávislé administrativní doklady chybějí.

### 3. Nominální harmonogram

| Kolo / den | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-04-22 | 24 |
| Q2 | 2024-04-23 | 12 |
| R128 | 2024-04-24–25 | 32 |
| R64 | 2024-04-26–27 | 32 |
| R32 | 2024-04-28–29 | 16 |
| R16 | 2024-04-30 | 8 |
| QF | 2024-05-01–02 | 4 (2+2) |
| SF | 2024-05-03 | 2 |
| bez mužské dvouhry | 2024-05-04 | 0 |
| F | 2024-05-05 | 1 |

Pořadatelský plán MAD24-7 v únorové a dubnové verzi potvrzuje všechna okna, QF dvě denně, SF 3.5., sobotu 4.5. bez ATP singlu a nedělní F ne před 18:30. První strany obou verzí ověřeny vizuálně; anglický extrahovaný text omylem uvádí Q2 už v pondělí, obraz a španělský plán potvrzují Q1. Extrakce dubnové anglické verze na 25.4. uvádí ATP 2nd Round na centru, ale obraz má ATP 1st Round; nejde o skutečný plánovaný překryv R128/R64. Součty 48/34/38/37 atd. jsou souhrn ATP a WTA, později i dalších disciplín, nikoli počty mužské dvouhry. Denní splity R128/R64/R32 nelze z tohoto smíšeného programu samostatně vyvodit. Q1/Q2 počty potvrzeny geometrií a dobovými výsledky. Všech osm R16 na jediný den potvrzuje dobový OOP v přepisu MAD24-11. Poslední originální OOP vydán 4.5. 17:33, WTA doubles od 15:30, ATP finále ne před 18:30. Rozlišit začátek session od mužského finále. Walkover Sinner–Auger-Aliassime v QF a skreče SF/QF neodstraňují plánované hrací uzly, ani nemění denní kvóty. Q 2 + Main 12 dní bez překryvu, Main 11 singlových hracích dní, celkem 14 kalendářních dní a 131 nominálních zápasů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 128 / 96 | 48 / 48 (12 sekcí po 4) |
| DA | 79 ročníkově; 78–79 podle SE | 43 |
| SE | 0 ročníkově; obecně 0–1 | 0 |
| WC | 5 | 5 |
| Řádné Q postupy | 12 | 12 |
| Nasazení | 32 | 24 |
| BYE | 32, všichni seedy | 0 |
| Kola / zápasy | 7 / 95 | 2 / 36 |
| Formát | BO3 setů | BO3 setů |

§7.08 B.1.a/E.1 a §7.10 B, viz IW24-11: obecně 78–79 DA, 0–1 SE, 5 WC a 12 Q. Ročníkový přepis MAD24-5 uvádí 79 DA, 5 WC, 12 Q, 0 SE; pořadatel nezávisle potvrzuje 79 přijatých. Obě strany výsledkového Main potvrzují 32 seedů a 32 BYE, WC na pozicích 28/51/70/76/102, 12 Q na 3/5/59/60/62/67/83/84/94/99/100/101; navíc LL Bautista Agut na 14 po odstoupení Evanse. Pět WC Fonseca, Blanch, Landaluce, Bergs, Shang; žádné další místo pro mediální Next Gen označení. PR Nadal a Shapovalov součástí DA. LL není třináctý řádný postup. Main 32+32+16+8+4+2+1=95.

Q 43 DA+5 WC potvrzeno dobovým přepisem i vizuálně z originálu. Q WC na 3/10/14/19/27 (Pouille, Omarakhanov, Bennani, Martin Tiffon, Shelbayh). 24 nominálních seedů; v patičce vyškrtnuti Lestienne (6), Fognini (9) a Garin (15), Ajdukovic je označen jako náhradní seed 25. Neodvozovat nominálních 25 seedů ani snižovat kapacitu po odstoupeních. Tři Alt Hassan, Llamas Ruiz, Napolitano. Dvanáct sekcí po čtyřech, 24+12=36 zápasů, 12 postupujících. Q originál datuje záhlaví společně s Main, skutečná data Q doložena samostatně MAD24-4/7/10.

### 5. Dobová pravidla

§7.03/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle IW24-11/14 a SCL24-18. Pro 96členný Masters 32 seedů a 32 BYE, 24 Q seedů a 12 sekcí; jedna obecná SE rezerva, v Madridu listina 0 SE, bez ATP250 LE nebo ATP500 A+ WC. BO3 tiebreak sety. R64 první prohra po BYE 10 bodů místo 30; držitel WC při prohře R128 nula místo 10 (dobové pravidlo §9.03 G, viz IW24). Q 20/10/0 přímo originál, odlišně od 56členného Monte-Carlo 30/16/0. Q body navíc k Main výsledku. Peněžní nominály dle originálního losu, nikoli podle bodových výjimek. Povinnosti Masters ranking/commitment samostatně, nepřenášet nepovinnou výjimku Monte-Carlo.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 1000 | 963225 |
| Finalista | 1 | 650 | 512260 |
| SF | 2 | 400 | 284590 |
| QF | 4 | 200 | 161995 |
| R16 | 8 | 100 | 88440 |
| R32 | 16 | 50 | 51665 |
| R64 | 32 | 30 (10 při první prohře po BYE) | 30225 |
| R128 | 32 | 10 (WC 0) | 20360 |
| Q postupující | 12 | 20 | 0 samostatně |
| Q2 prohra | 12 | 10 | 11820 |
| Q1 prohra | 24 | 0 | 6130 |

Obě tabulky z vizuálně ověřených ATP originálů MAD24-1/2. Sporting News MAD24-12 uvádí R64 30255 EUR, originál obou stran jednoznačně 30225 EUR, shoda s MAD24-13. Použít 30225; rozdíl 30 na hráče, 960 při 32 příjemcích. P bez hvězdičky. Nominální Main 5845525 EUR, Q 288960 EUR, celkem 6134485 EUR; 96 Main příjemců, 36 nepostupujících Q příjemců. Q vítězové 0 EUR samostatně. Originální losy uvádějí financial commitment 9249713 EUR, ATP předturnajový přehled 9017445 EUR a prize money 7877020 EUR. Rozdíl celkové commitment evidovat jako konflikt publikovaných souhrnů, neovlivňuje primární singlovou tabulku; přesná příčina nezjištěna. Nesčítat ATP a WTA ani nevydávat celkovou dotaci za mužský singlový součet. Historické LL a odstoupení nezahrnuty.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy. H* přesné původní denní splity R128/R64/R32 chybějí, okna a QF 2+2 primárně doloženy. E* původní acceptance lists/DS a hodiny losování nezískány, rank dates z ročníkového přepisu, termíny odvozené. Z* obě Main strany, Q, finálový OOP a první strany únorového/dubnového plánu vizuálně; předturnajový ATP přehled indexovaný, přímé otevření 403. Žádné neověřené hashe. Kontrola kvót, 96/48, 32/24 seedů, 32/0 BYE, 12 Q, 95/36 uzlů, příjemců a obou finančních součtů prošla. Další Rome 2024 po ověření kalendáře. Bez runtime změn.

### 8. Zdroje (MAD24)

- MAD24-1: [ATP výsledkový Main](https://www.protennislive.com/posting/2024/1536/mds.pdf), obě strany vizuálně; [pořadatelský archiv 2024](https://mutuamadridopen.com/palmares/palmares-2024/) odkazuje na Main kopii a ATP Q.
- MAD24-2: [ATP výsledkový Q](https://www.protennislive.com/posting/2024/1536/qs.pdf), str. 1 vizuálně, 20/10/0 a 11820/6130 EUR.
- MAD24-3: [ATP OOP finále](https://www.protennislive.com/posting/2024/1536/op.pdf), str. 1 vizuálně, vydání 4.5. 17:33, finále 18:30 nejdříve.
- MAD24-4: [ATP předturnajový přehled 16.4.](https://www.atptour.com/en/news/madrid-2024-atp-masters-1000-history-draw-schedule), indexovaný text, přímé otevření 403; [španělská verze 19.4.](https://www.atptour.com/es/news/madrid-2024-atp-masters-1000-history-draw-schedule).
- MAD24-5: [dobový přepis acceptance lists 17.4.](https://www.tennisteen.it/entry-list/atp/24154-atp-entry-list-22-aprile-5-maggio-2024.html), rank dates, cutoffs, DA/WC/Q/SE.
- MAD24-6: [pořadatel 26.3., 79 přijatých, cutoff 75 a velikost 96](https://mutuamadridopen.com/en/nadal-sabalenka-alcaraz-swiatek-djokovic-and-gauff-among-the-stars-at-the-mutua-madrid-open/).
- MAD24-7: [únorový plán pořadatele](https://desarrollo.mutuamadridopen.com/wp-content/uploads/2024/02/Programacion-Partidos-ATP-WTA-_MMO2024_2.pdf), [dubnový plán](https://mutuamadridopen.com/wp-content/uploads/2024/04/ING_Programacion_Partidos_ATP_WTA__MMO2024.pdf), první strany vizuálně, odlišné session a společné denní součty, nikoli jen ATP.
- MAD24-8: [ročníkový přehled](https://en.wikipedia.org/wiki/2024_Mutua_Madrid_Open), 22. mužský ročník a místo; [ITF 2024](https://www.itftennis.com/en/tournament/madrid/esp/2024/m-1000-esp-2024-001/draws-and-results/).
- MAD24-9: [Reuters 22.4., zveřejnění Main losu](https://www.reuters.com/sports/tennis/djokovic-skip-madrid-open-2024-04-22/).
- MAD24-10: [dobový Q výsledkový soupis](https://www.rte.ie/sport/results/tennis/madrid-open-qualification-men/888932/results/), [Sky 22.4.](https://www.skysports.com/tennis/scores-schedule/22-04-2024).
- MAD24-11: [dobový OOP 30.4.](https://elportal24.com/2024/04/orden-de-juego-partidos-y-horarios-de-hoy-martes-30-de-abril-en-el-mutua-madrid-open-2024/), [TennisTemple denní přehled](https://en.tennistemple.com/competitions/madrid/2024/orderofplay).
- MAD24-12: [Sporting News dobový program a ceny](https://www.sportingnews.com/uk/tennis/news/watch-madrid-open-2024-schedule-channel-stream-prize-money/6fc48773e50b2528826a3afd), chybných 30255 EUR R64, přednost originálu.
- MAD24-13: [TenisPortal ročníkový přehled](https://www.tenisportal.cz/madrid/2024/atp-muzi/), shoda 30225 EUR. Dobový předpis viz IW24-11/14 a SCL24-18.


## Rome 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/P/Z s označenými mezerami). Rešerše 2026-11-27. Předstartovní a výsledkový originální ATP Main (obě strany každého), první strana originální ATP Main acceptance list a tři původní OOP vizuálně ověřeny. Originální Q finanční tabulka nezískána, Q ceny sekundárně doloženy. Samostatná pořadatelská předkvalifikace přiděluje dvě z pěti WC do ATP Q.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Internazionali BNL d'Italia, mužská dvouhra | ROM24-1/2/4 |
| Kategorie / ATP ID | ATP Masters 1000 / 416 | ROM24-2/12 |
| Ročník | 81. ročník společné akce v dobovém přehledu | ROM24-12/13 |
| Dějiště | Foro Italico, Řím, Itálie | ROM24-4/12 |
| Povrch | venkovní červená antuka | ROM24-1/2 |
| Časové pásmo | Europe/Rome, CEST UTC+02:00 během soutěže | lokalita a datum |
| Ředitel | Paolo Lorenzi | ROM24-5/6/7 |
| ATP supervisors | Carlos Sanches, Roland Herfel, Andrei Kornilov, Carmelo Di Dio | ROM24-1/2/5 |
| Tour managers / referee | Konstantin Haerle, Denis Zivkovic / Riccardo Ragazzini | ROM24-5/6 |
| Měna | EUR | ROM24-1/2 |

Míče a detail sheet nezískány. Nezaměňovat s WTA nebo s Rome Challenger. Záhlaví společných OOP obsahující EUR 4791105 patří ženské dotaci, nikoli ATP singlovým cenám.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-04-08 | ROM24-3, originál |
| Q rank date | 2024-04-15, pravidlový referenční den | odvozeno §7.03 |
| Nominální Main deadline | 2024-04-08 18:00 CEST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-04-15 18:00 CEST (12:00 US Eastern) | odvozeno §7.03 |
| Main los | 2024-05-06, přesný čas neověřen | ROM24-8 |
| Q los | nejpozději 2024-05-05 19:38 CEST (vydání OOP), hodina losu neověřena | ROM24-5 |
| Q1 Alt sign-in deadline | 2024-05-06 09:30 CEST | ROM24-5 |
| Q | 2024-05-06–07 od 10:00 CEST | ROM24-4/5/6 |
| Main | 2024-05-08–19 | ROM24-4/7/9 |
| Main LL sign-in 8.5. | 10:30 CEST | ROM24-7 |
| Singlové finále | 2024-05-19 17:00 CEST, dobový plán | ROM24-9 |

Získán skutečný **Official Player Acceptance List**, označený Original, ze dne 8.4.2024, str. 1/3, timestamp 12:23:51 bez uvedeného časového pásma (ROM24-3). První strana vizuálně, zbylé strany alternates textově; Main 79 DA, 5 WC, 12 Q, 0 SE, původní cutoff 77 a rankings date 8.4. Konečný Main originál uvádí Daniel Galan 85 v obou cutoff polích. Oba údaje uchovat odděleně: původní acceptance cutoff a údaj v pozdějším losu nejsou totéž. Dobový přepis Q listu ROM24-10 uvádí cutoff 127 a datum listiny 16.4.; datum listiny není rank date. Q originální acceptance list a konečný cutoff chybějí. Uzávěrky odvozené, neztotožňovat s časem exportu listiny. Původní OOP před zahájením Q je vydán v neděli večer, neprokazuje přesný čas losování.

### 3. Nominální harmonogram

| Kolo / den | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-05-06 | 24 |
| Q2 | 2024-05-07 | 12 |
| R128 | 2024-05-08–09 | 32 (16+16) |
| R64 | 2024-05-10–11 | 32 |
| R32 | 2024-05-12–13 | 16 |
| R16 | 2024-05-14 | 8 |
| QF | 2024-05-15–16 | 4 (2+2 pozorováno) |
| SF | 2024-05-17 | 2 |
| bez mužské dvouhry | 2024-05-18 | 0 |
| F | 2024-05-19 | 1 |

ATP předturnajový přehled ROM24-4 a dobový program Sky 5.5. ROM24-9 potvrzují všechna okna Main a kvalifikaci 6.–7.5. Originální společný OOP 6.5. vydaný 5.5. 19:38 obsahuje 24 mužských Q1 (počítány pouze ATP buňky), OOP 7.5. vydaný 6.5. 21:40 obsahuje 12 mužských Q2, z nich dvě s dosud neurčenými účastníky po neuzavřeném Q1; to není důvod zvýšit počet Q kol. Přesný důvod a okamžik dokončení těchto Q1 uzlů neověřen. Originální OOP 8.5. vydaný 7.5. 19:46 obsahuje 16 R128 (2+2+3+3+2+4 na šesti kurtech), zbývajících 16 nominálně 9.5. Přesné původní denní splity R64/R32 bez dalších OOP neověřeny. R16 14.5., QF 15.–16.5. po dvou (dobový plán oken, výsledková kontrola ROM24-11), SF 17.5., sobota bez mužské dvouhry, F v neděli 19.5. v 17:00 podle předturnajového programu. Původní OOP závěrečných kol nezískány. Q 2 + Main 12 dní bez překryvu, 11 singlových hracích dní Main, 14 kalendářních dní celkem, 95+36=131 nominálních zápasů. OOP jsou kombinované s WTA; nepočítat ženské zápasy ani jiné disciplíny.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 128 / 96 | 48 / 48 (12 sekcí po 4) |
| DA | 79 ročníkově; 78–79 podle SE | 43 |
| SE | 0 ročníkově; obecně 0–1 | 0 |
| WC | 5 | 5 |
| Řádné Q postupy | 12 | 12 |
| Nasazení | 32 | 24 |
| BYE | 32, všichni nominální seedy | 0 |
| Kola / zápasy | 7 / 95 | 2 / 36 |
| Formát | BO3 setů | BO3 setů |

Ročníkový originální acceptance list ROM24-3 explicitně 79+5+12+0=96, obecný §7.08 B/E a §7.10 B viz IW24-11. Obě strany předstartovního Main ROM24-1 potvrzují 32 seedů a BYE, pět WC Gigante, Zeppieri, Fognini, Napolitano, Vavassori (11/12/52/83/118), 12 Q placeholderů (3/27/30/35/44/53/60/76/91/99/102/124). PR Nadal a Shapovalov jsou součástí DA. Výsledkový originál ROM24-2 eviduje čtyři LL: Moutet na původním Q místě 3, Shang na původní seed pozici 81 po odstoupení Humberta s BYE, Wolf a Mayot po dalších odstoupeních. Počet skutečně označených Q/seedů ve výsledkovém pavouku není plánovaný počet. Main 32+32+16+8+4+2+1=95.

Q 43 DA+5 WC, 24 seedů, 12 čtyřčlenných sekcí. Dobový úplný Q přehled ROM24-14 potvrzuje všechny seedy 1–24, WC Passaro, Maestrelli, Vincent Ruggeri, Picchione, Oradini a dva Alt Fatic/Mpetshi Perricard. Původní OOP Q1 nezávisle obsahuje těchto pět WC a 24 mužských utkání. Q 24+12=36 uzlů a 12 vítězů; LL přechody nezvyšují nominální počet Q postupových míst.

**Předkvalifikace pořadatele:** dobové zdroje ROM24-15 potvrzují finální národní předkvalifikační soutěž 30.4.–3.5. a dvě mužské WC do ATP Q. Picchione a Oradini získali WC touto cestou, další tři WC byly přímo oznámené pořadatelem (Maestrelli, Passaro, Vincent Ruggeri). Jde o způsob rozdělení pěti existujících WC, nikoli třetí kolo ATP Q, další dvě WC nebo ATP rankingový turnaj. Předkvalifikační lokální série není zahrnuta do 131 uzlů; úplná samostatná geometrie této série není předmětem této edice ATP Main/Q.

### 5. Dobová pravidla

§7.03/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle IW24-11/14 a SCL24-18. Obecně 78–79 DA a 0–1 SE; konkrétní originální Main listina Říma potvrzuje 79 DA a 0 SE. Main 32 seedů a 32 BYE, Q 24 seedů, BO3 tiebreak. Bez ATP 250 LE a ATP 500 A+ WC. Main první prohra po BYE 10 bodů místo 30, držitel WC při prohře R128 0 místo 10, Q 20/10/0 podle dobového předpisu, Q body navíc k Main výsledku. Bodové výjimky nejsou změnou nominální finanční tabulky. Předkvalifikační WC výše jsou pořadatelský mechanismus uvnitř běžné WC kapacity.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 1000 | 963225 |
| Finalista | 1 | 650 | 512260 |
| SF | 2 | 400 | 284590 |
| QF | 4 | 200 | 161995 |
| R16 | 8 | 100 | 88440 |
| R32 | 16 | 50 | 51665 |
| R64 | 32 | 30 (10 při první prohře po BYE) | 30255 |
| R128 | 32 | 10 (WC 0) | 20360 |
| Q postupující | 12 | 20 | 0 samostatně |
| Q2 prohra | 12 | 10 | 11820 |
| Q1 prohra | 24 | 0 | 6130 |

Main ceny včetně R64 **30255 EUR** přímo vizuálně v předstartovním i výsledkovém originálu (vždy obě strany). V registru Madrid 2024 je doloženo 30225 EUR, tedy nepřebírat částku pouze ze stejné kategorie či celkové dotace. Q 11820/6130 EUR souhlasí v dobové Borsa&Finanza a ročníkových tabulkách ROM24-16/17; původní Q finanční tabulka nedostupná, P*. Nezávislost vzniku sekundárních tabulek neprokázána. Nominální Main 5846485 EUR, Q 288960 EUR, celkem 6135445 EUR; 96 Main příjemců a 36 nepostupujících Q příjemců. Financial commitment 9094379 EUR a prize money 7877020 EUR dle ATP nejsou mužský singlový součet. Q vítězové nemají samostatnou nominální Q odměnu, historické LL/withdrawal payout nezahrnuty.

### 7. Kontrola a mezery

I/T/D/R/B doloženy. H* Q1/Q2, první den Main a okna kol potvrzeny, původní R64/R32 a QF denní OOP nezískány; QF 2+2 výsledkově. E* originální Main listina získána, ale Q acceptance list, detail sheet, přesné časy losů a konečný Q cutoff chybějí; uzávěrky odvozené. P* Main primární, Q sekundární shoda. Z* oba Main originály v archivních kopiích po dvou stranách, Main acceptance list první strana a OOP 6./7./8.5. po jedné straně vizuálně; přímé ATP Main/Q PDF nedostupné, ATP preview indexovaný text, otevření 403. Nevymýšlet SHA-256. Aritmetická kontrola kvót, 96/48, 32/24 seedů, 32/0 BYE, 12 postupů, 95/36 zápasů a peněz prošla. Další pracovní fronta Geneva a Lyon 2024, pořadí a data ještě ověřit v dobovém kalendáři. Bez runtime změn.

### 8. Zdroje (ROM24)

- ROM24-1: [předstartovní ATP Main archiv Fantatennis](https://www.fantatennis.net/_downloads/b47e0a21292755a5a02c06292eb01310), obě strany vizuálně; [FITP kopie](https://www.fitp.it/media/ibi_repository/2024/20240506_MDSatp.pdf) textově.
- ROM24-2: [výsledkový ATP Main archiv tenislosalcazares](https://tenislosalcazares.com/cuadros/masters/roma24.pdf), obě strany vizuálně. [Přímý ATP Main](https://www.protennislive.com/posting/2024/416/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/416/qs.pdf) nedostupné.
- ROM24-3: [originální ATP Official Player Acceptance List 8.4.](https://www.supertennis.tv/media/REDAZIONE_APRILE_2024/20240408_Rome_1000_MDS.pdf), str. 1 vizuálně, všechny 3 textově; původní cutoff 77 a rank date 8.4.
- ROM24-4: [ATP předturnajový přehled 2024](https://www.atptour.com/en/news/rome-2024-atp-masters-1000-history-draw-schedule), indexovaný text, otevření 403.
- ROM24-5: [FITP originální OOP Q1 6.5.](https://www.fitp.it/media/ibi_repository/2024/20240505_OP.pdf), vizuálně, 24 ATP Q1.
- ROM24-6: [FITP originální OOP Q2 7.5.](https://www.fitp.it/media/ibi_repository/2024/20240506_OP.pdf), vizuálně, 12 ATP Q2.
- ROM24-7: [FITP originální OOP Main 8.5.](https://www.fitp.it/media/ibi_repository/2024/20240507_OPmercoled__.pdf), vizuálně, 16 ATP R128.
- ROM24-8: [Sky Sport 6.5., Main los](https://sport.sky.it/tennis/2024/05/06/atp-roma-2024-tabellone).
- ROM24-9: [Sky předturnajový kalendář 5.5.](https://sport.sky.it/tennis/2024/05/05/atp-roma-2024-calendario-guida), okna kol a finále 17:00.
- ROM24-10: [LiveTennis aktualizace listin 5.5.](https://www.livetennis.it/post/411508/masters-1000-roma-la-situazione-aggiornata-md-e-qualificazioni-entra-matteo-berrettini-nel-md-wild-card-md-a-stefano-napolitano/), Q cutoff 127, datum listiny 16.4.; [OA Sport Q listina 18.4.](https://www.oasport.it/2024/04/atp-roma-annunciata-lentry-list-delle-qualificazioni-al-via-un-solo-azzurro-in-attesa-delle-wild-card/amp/).
- ROM24-11: [RTÉ denní výsledky](https://www.rte.ie/sport/results/tennis/internazionali-bnl-ditalia-men/888935/results/), [Stat Pick 2024](https://www.statpick.ai/tournaments/tennis/rome-atp/2024), QF 2+2.
- ROM24-12: [ročníkový přehled](https://en.wikipedia.org/wiki/2024_Italian_Open_(tennis)), [německá ročníková identita ATP 416](https://de.wikipedia.org/wiki/Internazionali_BNL_d%E2%80%99Italia_2024/Herren).
- ROM24-13: [dobový přehled 81. ročníku](https://reteoro.tv/blog-detail?post=274124&slug=internazionali-bnl-ditalia-a-roma-fino-al-19-maggio).
- ROM24-14: [TennisTemple úplný Q pavouk](https://en.tennistemple.com/competitions/rome/2024/draw-qualifications), [Sportface dobový Q přehled](https://news.sportface.it/tennis/tabellone-qualificazioni-maschili-internazionali-ditalia-roma-2024-risultati-e-accoppiamenti/2539472).
- ROM24-15: [ANSA 23.4. oznámení WC](https://www.ansa.it/sito/notizie/sport/tennis/2024/04/23/internazionali-wild-card-per-fognini-e-berrettini_94d5d959-cadb-4f60-aa54-86a2671ac998.html), [dobový rozsah předkvalifikace](https://www.livetennis.it/post/412459/pre-quali-roma-2024-i-risultati-completi-della-prima-giornata-prima-sorpresa-dalla-valle-n-1-del-seeding-si-ritira-alla-fine-del-primo-set-avanza-raul-brancaccio/), [OA Sport výsledné WC po změnách](https://www.oasport.it/2024/05/atp-roma-caos-ritiri-cosa-e-cambiato-per-le-wild-card-agli-italiani-tra-tabellone-principale-e-qualificazioni/).
- ROM24-16: [Borsa&Finanza dobový kompletní rozpis cen a bodů](https://borsaefinanza.it/internazionali-roma-2024-quanto-guadagna-chi-vince/), Q 11820/6130, vložený nulový řádek Q3 není důkaz třetího kola.
- ROM24-17: [ročníková finanční tabulka](https://en.wikipedia.org/wiki/2024_Italian_Open_(tennis)), [IA Tennis Academy 2024](https://iatennis.net/the-2024-italian-open-results/), shoda Q. Dobový ATP předpis viz IW24-11/14 a SCL24-18.

## Geneva 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/Z s označenými mezerami). Rešerše 2026-11-27. Obě původní ATP finanční tabulky (Main i Q) dostupné jako indexovaný text z archivu pořadatele. Obrazové vykreslení selhalo; nezávislé dobové zdroje potvrzují strukturu a časový plán. Nedělní souběh Q2 a Main a sobotní finále jsou ročníkový plán, nikoli následky deště.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Gonet Geneva Open | GVA24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 322 | GVA24-4/5 |
| Ročník | 2024, devátý od obnovení v roce 2015 | GVA24-4/12 |
| Dějiště | Tennis Club de Genève, Parc des Eaux-Vives, Ženeva, Švýcarsko | GVA24-6/7 |
| Povrch | venkovní červená antuka | GVA24-1/2/3/7 |
| Časové pásmo | Europe/Zurich, CEST UTC+02:00 | lokalita a datum |
| Ředitel | Thierry Grin | GVA24-9/10 |
| ATP supervisors | Carlos Sanches / Ahmed Abdel-Azim | GVA24-9/10 |
| Tour manager / referee | Nicolas Rakitin / Stephane Apostolou | GVA24-9/10 |
| Měna | EUR | GVA24-1/2/3 |

Míče a původní detail sheet nezískány. ATP kalendář z března 2023 již uvádí nedělní start Geneva i Lyon 19.5. (GVA24-5); sobotní konec potvrzuje konkrétní dobový program a losy. ITF datum od 20.5. je odlišný evidenční týden, nikoli důkaz změny nedělního Main startu.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-04-22 | GVA24-8 |
| Nominální Main deadline | 2024-04-22 18:00 CEST (12:00 US Eastern) | odvozeno z §7.03 |
| Q referenční rank date | 2024-04-29, odvozeno; původní listina chybí | §7.03 |
| Nominální Q deadline | 2024-04-29 18:00 CEST (12:00 US Eastern), odvozeno | §7.03 |
| Nominální LE deadline | 2024-05-16 16:00 CEST (10:00 US Eastern) | odvozeno §7.04 |
| Main los | 2024-05-17, přesná hodina neověřena | GVA24-11 |
| Q los | před zahájením Q1 2024-05-18, přesná hodina neověřena | GVA24-3/7 |
| Q | 2024-05-18–19, program od 11:00 CEST | GVA24-7/13 |
| Main | 2024-05-19–25 | GVA24-1/2/7 |
| Singlové finále | 2024-05-25 15:00 CEST, nejdříve | GVA24-7/10 |

Oznámení pořadatele 23.4. (GVA24-6) uvádí 18 DA, původní cutoff 51, tři rezervovaná místa souhrnně popsaná jako special exemptions, tři WC a čtyři Q. Dobový přepis entry listu (GVA24-8, 15.5.) uvádí 18 DA, SE 0 a LE 0; to není důkaz absence rezerv. Dobový obecný předpis je rozlišuje na dvě SE a jednu LE. Přesné znění originální listiny/DS nedostupné. Předstartovní Main los v obou cutoff polích uvádí Coria 83 (GVA24-1); odlišit od původního 51. Q originál uvádí Gakhov 272 jako poslední DA, původní Q cutoff a skutečná uzávěrka nejsou samostatně doloženy.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-05-18 | 8 |
| Q2 | 2024-05-19 | 4 |
| R32 | 2024-05-19–21 | 12 (2+6+4, rekonstruováno) |
| R16 | 2024-05-21–22 | 8 (2+6 uzlů, rekonstruováno) |
| QF | 2024-05-23 | 4 |
| SF | 2024-05-24 | 2 |
| F | 2024-05-25 | 1 |

Dobový program GVA24-7 plánuje Q1 sobota, Q2 a první Main kolo neděle, první kolo pondělí, druhé kolo úterý/středa, QF čtvrtek, SF pátek a F sobota. Přesnější dobový přehled GVA24-14 uvádí v úterý R32 i R16. Nedělní úplný výsledkový program GVA24-13 zachycuje čtyři Q2 a dva Main R32, pondělní předem zveřejněný program GVA24-15 a ATP Day 2 potvrzují šest R32. Zbývající čtyři R32 patří do úterního plánu; úterní historický program vykazuje navíc dva R32 přenesené z pondělí. Dva R16 uzly jsou evidované v úterý, jeden jako walkover; zbývajících šest připadá na středu. Jde o rekonstrukci uzlů, nikoli nezávisle získaný původní úterní OOP. Originální revidovaný čtvrteční OOP GVA24-9 (vydán 22.5. ve 22:47) dokládá čtyři QF a pokračování jednoho nedokončeného R16. Revidovaný sobotní OOP GVA24-10 (24.5. 21:15) obsahuje odložené SF Cobolli–Ruud od 10:30 a F nejdříve v 15:00; nominální SF zůstává pátek. Q dva dny + Main sedm dní, jeden společný den 19.5., osm kalendářních dní celkem; 12+27=39 nominálních uzlů. Déšť a walkover nemění kapacitu, plán kol ani datum nominálního finále.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 při nevyužití rezerv | 14 |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28. Předstartovní Main GVA24-1 uvádí všech osm seedů, čtyři BYE, tři WC (Djokovic, Murray, Shapovalov), čtyři Q placeholdery a 21 zbývajících účastníků bez zvláštního označení; nevyvozovat individuální PR/LE pouze z absence značky. Q GVA24-3 uvádí všech osm seedů, dva WC (Jebens, Paul), tři náhradníky Alt a čtyři čtyřčlenné sekce. Alt obsazují existující kapacitu 14 míst mimo WC, nikoli další místa. Main 12+8+4+2+1=27 a Q 8+4=12. Výsledkový Main GVA24-2 obsahuje walkover v R16 a čtyři řádné kvalifikanty; plánované počty zůstávají stejné.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03, verze viz MPL24-5/6 a IW24-11/14. Obvyklé dvě SE rezervy a jedna LE rezerva se při nevyužití vracejí DA; souhrnný pojem tři special exemptions v oznámení pořadatele neprokazuje tři samostatné SE podle předpisu. Q 14 DA/2 WC, osm seedů, čtyři kvalifikanti, žádná třetí Q fáze. Main osm seedů a čtyři BYE. První prohra po BYE přináší 0 ATP bodů; Q postup 13, Q2 prohra 7, Q1 prohra 0. Body za kvalifikaci přistupují k bodům z Main. Walkover není odehraný zápas. Bez přenosu pravidel Grand Slamu, ATP 500 A+ WC nebo týdenní alokace tří souběžných ATP akcí (zde dobový kalendář uvádí Geneva a Lyon).

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main částky přímo v GVA24-1/2, Q v GVA24-3, nikoli převzaté z jiného turnaje. Nominální Main 425905 EUR, Q 25980 EUR, celkem 451885 EUR. Výpočet zahrnuje 28 Main příjemců a 12 nepostupujících Q příjemců. Financial commitment 651865 EUR v originálech není mužský singlový součet. Sekundární souhrnné dotace 562815/579320 EUR nejsou touto singlovou tabulkou; rozdíl souhrnů zde neřešen a nemění doložené jednotlivé částky.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy. H* okna a nominální dny Q/QF/SF/F ověřeny, R32 2+6+4 a R16 2+6 uzlů transparentně rekonstruovány, plný předdešťový OOP chybí. E* rank date Main a původní cutoff z dobové listiny a oznámení, původní acceptance lists/DS, Q cutoff v původní listině a přesné časy losů nezískány. Z* primární pořadatelské Main/Q PDF, oznámení a oba revidované OOP dostupné textově; pokusy o obrazovou kontrolu skončily 502/timeout, ATP Day 2 403 a přímé ATP draw PDF nedostupné. Nevymýšlet PDF SHA-256. Kontrola kvót, 28/16, 8/8 seedů, čtyř Main BYE, čtyř postupujících, 27/12 uzlů a finančních součtů prošla. Další Lyon 2024, stejný nedělní start v dobovém kalendáři. Bez runtime změn.

### 8. Zdroje (GVA24)

- GVA24-1: [originální ATP předstartovní Main u pořadatele](https://gonetgenevaopen.com/wp-content/uploads/2024/05/MDS.pdf), str. 1 indexovaný text.
- GVA24-2: [originální ATP výsledkový Main u pořadatele](https://gonetgenevaopen.com/wp-content/uploads/2024/05/MDS-6.pdf), str. 1 text.
- GVA24-3: [originální ATP předstartovní Q u pořadatele](https://gonetgenevaopen.com/wp-content/uploads/2024/05/QS.pdf), str. 1 text, Q ceny a body.
- GVA24-4: [Tennis Europe ročníkový záznam](https://www.tenniseurope.org/calendarevent/73816/Gonet-Geneva-Open), ATP 322 a Main data; [ATP identita](https://www.atptour.com/en/tournaments/Geneva/322/overview), nikoli aktuální finanční údaje.
- GVA24-5: [ATP kalendář verze březen 2023](https://www.atptour.com/-/media/files/updated-2024-atp-tour-calendar-march-2023.pdf), indexovaný záznam Geneva/Lyon 19.5.; konkrétní sobotní finále potvrzeno GVA24-7/10.
- GVA24-6: [oznámení pořadatele 23.4.2024](https://www.gonet.ch/uploads/2024-4-23-9-42-9-980-4U1nDfN09pNtfcI7spUh.pdf), str. 1 text, DA/rezervy/cutoff.
- GVA24-7: [Flash Léman dobový program](https://flashleman.ch/le-tournoi-de-tennis-gonet-geneva-open-dans-le-magnifique-cadre-du-parc-des-eaux-vives/), Q a Main souběh, pátek SF, sobota F 15:00.
- GVA24-8: [TennisTeen 15.5.2024, přepis acceptance listu](https://www.tennisteen.it/entry-list/atp/24168-atp-entry-list-20-26-maggio-2024.html).
- GVA24-9: [originální revidovaný OOP 23.5.](https://gonetgenevaopen.com/wp-content/uploads/2024/05/OP-8.pdf), str. 1 text.
- GVA24-10: [originální revidovaný OOP 25.5.](https://gonetgenevaopen.com/wp-content/uploads/2024/05/OP-11.pdf), str. 1 text.
- GVA24-11: [ATP zpráva o losu 17.5.](https://www.atptour.com/en/news/djokovic-geneva-2024-draw).
- GVA24-12: [ročníková identita](https://en.wikipedia.org/wiki/2024_Geneva_Open), historie a devátý novodobý ročník; [ITF ročníkový záznam](https://www.world.tennis/en/tournament/geneva/sui/2024/m-250-sui-2024-001/draws-and-results/).
- GVA24-13: TennisTemple ročníkové denní programy [Q1 18.5.](https://en.tennistemple.com/competitions/geneva-2024/31553/orderofplay/2024-05-18), [19.5.](https://en.tennistemple.com/competitions/geneva-2024/31553/orderofplay/2024-05-19), [20.5.](https://en.tennistemple.com/competitions/geneva-2024/31553/orderofplay/2024-05-20), [21.5.](https://en.tennistemple.com/competitions/geneva-2024/31553/orderofplay/2024-05-21); skutečné výsledky odděleně od nominálního plánu.
- GVA24-14: [dobový přehled rozpisu](https://gotennisracquets.com/geneva-open-2024/), indexovaný text, úterý R32/R16; nepoužívat pro nominální kapacitu či odměny.
- GVA24-15: [nedělní předem zveřejněný pondělní program](https://tennisuptodate.com/atp/2024-geneva-open-monday-schedule-including-return-of-andy-murray-with-novak-djokovic-tie-in-his-sights), šest R32; [ATP Day 2 Media Notes](https://www.atptour.com/-/media/f11ca67985b94a4dbd96c4a3b7546ebf.pdf), text str. 1–3.

## Lyon 2024

**Stav:** ROZPRACOVÁNO (8/9; E: konflikt nominálních Q WC; H/P/Z s dílčími mezerami). Rešerše 2026-11-27. Sedmý a poslední Open Parc původní antukové série ATP 7694. Dobový press kit, ATP Day 1 a původní OOP získány textově, revidovaný OOP 21.5. také vizuálně. Rozpor Q kvót nesmí být skryt převzetím standardní tabulky.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Open Parc Auvergne-Rhône-Alpes Lyon | LYO24-1/2 |
| Kategorie / ATP ID | ATP 250 / 7694 | LYO24-1/3 |
| Ročník | 7. a poslední (2017–2019, 2021–2024) | LYO24-1/2 |
| Dějiště | Parc de la Tête d'Or, Vélodrome Georges-Préveral, Lyon, Francie | LYO24-1/4 |
| Povrch | venkovní antuka | LYO24-1 |
| Časové pásmo | Europe/Paris, CEST UTC+02:00 | lokalita a datum |
| Ředitel / ATP supervisor | Thierry Ascione / Roland Herfel | LYO24-5/6/7 |
| Tour manager / referee | Thomas Schrader / Carlos Ramos | LYO24-5/6/7 |
| Měna | EUR | LYO24-1/4/8 |

Pořadatel výslovně označuje 2024 za poslední ročník. Neztotožňovat s ATP 496 (Marseille do 2025, přemístění licence do Lyonu od 2026), historickým halovým Lyonem ani s Lyon Challengerem. Míče a detail sheet nezískány. ITF uvádí evidenční týden od 20.5.; ATP ročníková stránka a pořadatel potvrzují Main od neděle 19.5.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-04-22 | LYO24-9 |
| Nominální Main deadline | 2024-04-22 18:00 CEST | odvozeno §7.03 (12:00 US Eastern) |
| Q referenční rank date | 2024-04-29, odvozeno | §7.03 |
| Nominální Q deadline | 2024-04-29 18:00 CEST | odvozeno §7.03 |
| Nominální LE deadline | 2024-05-16 16:00 CEST | odvozeno §7.04 |
| Main los | 2024-05-17 od 19:30 CEST, oznámený čas | LYO24-10 |
| Q los | před Q1 18.5., čas neověřen | LYO24-11 |
| Q | 2024-05-18–19 od 10:30 | LYO24-1/12 |
| Main | 2024-05-19–25 | LYO24-1/2/3 |
| Main LL sign-in 20.–22.5. | 10:30 CEST | LYO24-5/6/7 |
| Singlové finále | 2024-05-25 14:30 CEST, předběžný plán | LYO24-1 |

Původní Main cutoff 63 potvrzen shodně pořadatelem a přepisem listiny 15.5.; ten uvádí 18 DA, 3 WC, 4 Q, SE 0 a LE 1. Nejde o úplnou konečnou kvótu ani důkaz identity příjemce LE. Uzávěrky odvozené z dobového předpisu; originální acceptance lists, Q cutoff a časy losování Q nezískány. Main draw čas podle dobového TennisActu, ne auditovaný okamžik uskutečnění.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-05-18 | 8 |
| Q2 | 2024-05-19 | 4 |
| R32 | 2024-05-19–21 | 12 |
| R16 | 2024-05-21–22 | 8 |
| QF | 2024-05-23 | 4 |
| SF | 2024-05-24 | 2 |
| F | 2024-05-25 | 1 |

Press kit LYO24-1 označuje program jako předběžný, neděli Q2 + R32, úterý R32 + R16, středu R16, další kola po jednom dni. Oficiální magazine LYO24-13 uvádí neděli 12:30 zahájení Main po Q; rozdílné vyznačení úterních kol (magazine pouze R32, press kit i R16) je zachováno, úterní R16 potvrzuje revidovaný OOP. Předběžný nedělní součet 8 zápasů implikuje 4 Q2 + 4 R32, protože doubles nejsou uvedeny; pozdější webový program uvádí 7, výsledkový archiv 4 Q2 + 2 R32. Nepovažovat 4/3/2 za jediný jistý původní split. Pondělní revidovaný OOP vydaný 20.5. 13:18 obsahuje 6 R32 a 2 doubles. Úterní revidovaný OOP 21.5. 12:21 (vizuálně) obsahuje 4 nové R32, 2 pokračující R32 (TBF Gaston–Galan a Munar–Tiafoe) a 2 R16. Středeční OOP vydaný 21.5. 19:31 obsahuje dalších 6 R16. Kombinací denních uzlů vychází pozorovaný start R32 2+6+4, R16 2+6, nikoli jistý původní plán. Původní denní rozpisy před změnami chybějí; příčinu dvou nedokončených pondělních zápasů zde neurčovat bez dobového dokladu. Čtvrteční QF walkover Rinderknech–Darderi evidován odděleně. Sobota F v předběžném plánu 14:30; přesný konečný OOP čas neověřen. Q 2 + Main 7 dní s jednodenním překryvem, osm kalendářních dní, 39 nominálních uzlů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 při nevyužití rezerv | 14 podle ATP / 12 podle press kitu – NEVYŘEŠENO |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 podle ATP / 4 podle press kitu – NEVYŘEŠENO |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28; press kit souhrnně označuje tři rezervy jako special exempts, dobový ATP předpis a entry list rozlišují SE a LE. Výsledkový Main přepis potvrzuje osm seedů, čtyři BYE, 3 WC (Gasquet, Müller, Mpetshi Perricard), 4 Q a další LL obsazující původní místa. Q přepis LYO24-11 má všech osm seedů, 16 hráčů a čtyři postupující. Maxime Chazal získal Q WC v předturnaji 80 účastníků na All In Country Club; nejde o třetí ATP Q kolo. TennisActu 16.5. označuje Harolda Mayota jako druhou Q WC; výsledkový přepis Mayota uvádí jako seed bez WC značky. To podporuje existenci dvou oznámených WC, neprokazuje maximální nominální kvótu ani jejich konečné využití.

**Blokující rozpor E:** oficiální press kit LYO24-1 explicitně uvádí 12 DA a 4 WC pro 16členné Q; běžný dobový §7.08 E stanoví 14 DA a 2 WC. Dobové oznámení druhé WC a skutečný pavouk jsou důkaz ve prospěch standardní kvóty, ale originální Q acceptance list/DS ani schválená výjimka nebyly nalezeny. Stejný typ rozporu jako Marseille 2024, nelze přenést závěr z jiné edice. Obě varianty součtem dávají 16, nemění 8+4 Q uzlů, ale mění vstupní mechaniku; E zůstává otevřeno.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle MPL24-5/6, IW24-11/14. Main rezervy SE/LE, nevyužité rezervy se vracejí do DA; čtyři top seedy s BYE a při první prohře v R16 nula bodů, což ATP Day 1 výslovně potvrzuje. Q dva BO3 tiebreak zápasy k postupu, 13/7/0 ATP bodů, bez třetího kola. LL doplňuje existující Main místo. Pořadatelská předkvalifikační WC je způsob výběru uvnitř Q kapacity, nikoli další postupové místo. Q kvóta zůstává sporná; žádná domyšlená výjimka z ATP pravidel.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 88125 |
| Finalista | 1 | 165 | 51400 |
| SF | 2 | 100 | 30220 |
| QF | 4 | 50 | 17510 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 10165 |
| R32 | 12 | 0 | 6215 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3105 |
| Q1 prohra | 8 | 0 | 1695 |

Main částky a body z ATP Day 1 LYO24-2; záhlaví jeho tabulky uvádí $, avšak dobový český přehled LYO24-4, TenisPortal a CanalTenis výslovně EUR se shodnými čísly, pořadatel EUR dotaci. Q 3105/1695 EUR shodně LYO24-8/14, originální Q finanční tabulka nedostupná, P*. TennisCompanion chybně prezentuje stejná nominální čísla v USD a přepočítává je na EUR (2910/1588 pro Q); nejde o nezávislou shodu měny. TennisTemple Q uvádí neslučitelná 3 kola a 12/6 bodů, 4200/2105/1055 EUR; jeho vlastní Q pavouk má pouze dvě kola. Tuto tabulku nepoužívat. Nominální Main 425905 EUR, Q 25980 EUR, celkem 451885 EUR. Pořadatelská prize money 579320 EUR a financial commitment 651865 EUR nejsou singlové součty; alternativní 562815 EUR v ročníkovém přehledu odpovídá 2023 dotaci podle LYO24-8/15.

### 7. Kontrola a mezery

I/T/D/R/B/P/Z doloženy s výhradami, H* plán kol a rekonstruované denní uzly; E zůstává otevřeno kvůli konfliktu nominálních Q WC. P* Q sekundární shoda, Main primární text a korekce měny. Z* vizuálně ověřen revidovaný úterní OOP, screenshoty press kitu, pondělního/středečního OOP a ATP Day 1 selhaly 502/403. Přímé ATP Main/Q losy nedostupné, pořadatelská tabulková stránka při otevření 502. Originální acceptance/DS, Q rank date/cutoff, Q los a přesný finálový OOP zůstávají otevřené; nevymýšlet PDF hash. Aritmetika 28/16, 8/8 seedů, 4 BYE, 4 postupů, 27+12 uzlů, obou kandidátů Q kvót a cen prošla. Další krok cílená kontrola Q kvóty Lyon a Marseille; poté chronologicky Stuttgart a 's-Hertogenbosch 2024 (nejprve ověřit kalendář, Roland Garros již zpracován). Bez změn runtime.

### 8. Zdroje (LYO24)

- LYO24-1: [originální pořadatelský press kit 2024](https://openparc.com/site/wp-content/uploads/2024/05/DOSSIER-DE-PRESSE-OP24.pdf), text: identita, 12+4 Q, 18+3+4+3 Main, předběžný program; screenshot 502.
- LYO24-2: [ATP Preview & Day 1, 19.5.2024](https://www.atptour.com/-/media/da1f071142f949e2b55f985d66f820e9.pdf), str. 1–3 text, Main finanční/point table a historie, screenshot 403.
- LYO24-3: [ATP 7694 historická stránka](https://www.atptour.com/en/tournaments/lyon/7694/overview), 19–25.5.2024; [ITF evidenční týden](https://www.itftennis.com/en/tournament/lyon/fra/2024/m-250-fra-2024-003/draws-and-results/); [pořadatel poslední edice](https://openparc.com/tournoi/tableau-de-bord/).
- LYO24-4: [Tenis-živě, ročníkový přehled 22.5.2024](https://www.tenis-zive.cz/rubriky/atp/atp-lyon-open-muzi-program-vysledky-pavouk_2331.html), dějiště, EUR a Main přehled.
- LYO24-5: [originální pondělní OOP 20.5.](https://openparc.com/site/wp-content/uploads/2024/05/200524OP.pdf), text, 6 R32.
- LYO24-6: [originální revidovaný úterní OOP 21.5.](https://openparc.com/site/wp-content/uploads/2024/05/OP_2105-1.pdf), str. 1 vizuálně; dva TBF R32 a 2 R16.
- LYO24-7: [originální středeční OOP 22.5.](https://openparc.com/site/wp-content/uploads/2024/05/OP_2205-1.pdf), text, 6 R16.
- LYO24-8: [CanalTenis ročníková tabulka 2024](https://canaltenis.com/prize-money-atp-lyon/), Main/Q EUR; odděleně tabulky 2023/2026.
- LYO24-9: [TennisTeen přepis Main entry listu 15.5.](https://www.tennisteen.it/entry-list/atp/24168-atp-entry-list-20-26-maggio-2024.html), cutoff 63, rank date 22.4., LE 1.
- LYO24-10: [TennisActu Main los 17.5.](https://www.tennisactu.net/news-atp-lyon-humbert-gasquet-muller-mpetshi-sonego-le-tirage-de-l-open-parc-109569.html), 19:30.
- LYO24-11: [TennisTemple Q pavouk](https://en.tennistemple.com/competitions/lyon-2024/46943/draw-qualifications), [Main pavouk](https://en.tennistemple.com/competitions/lyon-2024/46943/draw), [TenisPortal Q](https://www.tenisportal.cz/lyon/2024/atp-muzi/?phase=qualification); geometrie, nikoli vadná Q prize tabulka TennisTemple. [TennisActu první WC](https://www.tennisactu.net/news-atp-lyon-gasquet-muller-et-mayot-invites-rinderknech-rentre-109521.html) a [předturnaj Chazal 11.5.](https://www.tennisactu.net/news-atp-lyon-q-maxime-chazal-remporte-le-pre-tournoi-et-une-wild-card-qualif-109430.html).
- LYO24-12: [pořadatel denní program](https://openparc.com/tournoi/programme-des-matchs/), odkazy na OOP; [nedělní archiv výsledků](https://en.tennistemple.com/competitions/lyon-2024/46943/orderofplay/2024-05-19). [Nedělní originální OOP](https://openparc.com/site/wp-content/uploads/2024/05/OP_1905.pdf), [sobotní finálový OOP](https://openparc.com/site/wp-content/uploads/2024/05/OP_2505.pdf) nalezené odkazy, obrazově 502.
- LYO24-13: [originální pořadatelský magazine](https://openparc.com/site/wp-content/uploads/2024/05/MAGAZINE-OFFICIEL-OP24.pdf), indexovaný text rozpisu.
- LYO24-14: [ročníková finanční tabulka](https://en.wikipedia.org/wiki/2024_ATP_Lyon_Open), Q 3105/1695 EUR; [TenisPortal Main](https://www.tenisportal.cz/lyon/2024/atp-muzi/), měna; [TennisAbstract 2024](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024Lyon), Main WC.
- LYO24-15: [TennisCompanion historické tabulky a identita sérií](https://tenniscompanion.org/prize-money/lyon/), nesprávně převedené singlové částky, nepoužít jako primární finanční doklad.
- Přímé [ATP Main](https://www.protennislive.com/posting/2024/7694/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/7694/qs.pdf) nedostupné. [Pořadatelská stránka losů](https://openparc.com/tableaux/) 502. Dobové ATP předpisy viz MPL24-5/6 a IW24-11/14.

## Stuttgart 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/D/P/Z s označenými mezerami). Rešerše 2026-11-28. První travnatá edice v tomto registru po antukové části sezony (Wimbledon již evidován samostatně). Předturnajový program pořadatele, dobové přepisy Main/Q listin, ATP Media Notes a úplné sekundární pavouky. Déšť v Q1 nezměnil nominální okna.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | BOSS OPEN | STU24-1/2 |
| Kategorie / ATP ID | ATP 250 / 321 | STU24-2/3 |
| Ročník | 46. dle ročníkového přehledu | STU24-4 |
| Dějiště | Tennisclub Weissenhof, Stuttgart, Německo | STU24-1/2/4 |
| Povrch | venkovní tráva | STU24-2/4 |
| Časové pásmo | Europe/Berlin, CEST UTC+02:00 | lokalita a datum |
| Ředitel | Edwin Weindorfer | STU24-5 |
| Měna | EUR | STU24-2/6 |

Nezaměňovat s dubnovým WTA Porsche Tennis Grand Prix na antuce ani se starší antukovou érou ATP Stuttgart (ATP notes potvrzují trávu od 2015). Míče, detail sheet, supervisor/referee v originálních dokumentech neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-13 | STU24-7 |
| Q rank date | 2024-05-20 | STU24-7 |
| Nominální Main deadline | 2024-05-13 18:00 CEST | odvozeno §7.03 |
| Nominální Q deadline | 2024-05-20 18:00 CEST | odvozeno §7.03 |
| Nominální LE deadline | 2024-06-06 16:00 CEST | odvozeno §7.04 |
| Main los | 2024-06-08, hodina neověřena | STU24-1/8 |
| Q los | nejpozději 2024-06-07, hodina neověřena | STU24-9 |
| Q | 2024-06-08–09 od 11:00 | STU24-1/9 |
| Main | 2024-06-10–16 | STU24-1/2 |
| F | 2024-06-16 nejdříve 13:00 CEST | STU24-1 |

Dobový přepis listin z 5.6. uvádí původní Main cutoff 52, Q cutoff 124; Main 18 DA, 3 WC, 4 Q, SE 0, LE 1; Q 14 DA/2 WC. STU24-10 nezávisle uvádí Main cutoff 52, datum listiny 14.5. (nikoli rank date), stav k 7.6. Originální ATP listiny/DS a konečné cutoffy nezískány. Uzávěrky jsou odvozené z dobových pravidel, nikoli doložené exportní časy. Pořadatel předem oznámil Main los na sobotu a 8.6. jeho provedení potvrdil. Párování Q bylo zveřejněno 7.6., neznamená přesný okamžik losování.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-08 | 8 |
| Q2 | 2024-06-09 | 4 |
| R32 | 2024-06-10–11 | 12 (4+8 rekonstruováno) |
| R16 | 2024-06-12–13 | 8 (4+4 plán) |
| QF | 2024-06-14 | 4 |
| SF | 2024-06-15 | 2 |
| F | 2024-06-16 | 1 |

Pořadatel 9.4. (STU24-1) vypsal osm sobotních Q1 a čtyři nedělní Q2; Main od pondělí, čtyři singlové zápasy ve středu, čtvrtek R16, pátek QF, sobota SF od 12:00 a nedělní F nejdříve 13:00. Oznámení 15.5. (STU24-5) potvrzuje R32 první dva Main dny a R16 od středy. Zpráva pořadatele z pondělí 10.6. (STU24-11) explicitně naplánovala osm úterních singlů, všechny R32; zbývající čtyři R32 nominálně pondělí. Denní split je rekonstrukce z těchto zpráv, ne originální pondělní OOP. Déšť 8.6. způsobil přeložení jednoho nezahájeného Q1 (Rehberg–Hassan) a dokončení dalšího (Mpetshi Perricard–Ursu) 9.6. (STU24-12). Q2 zůstalo plánováno na 9.6.; žádné třetí kolo ani změna délky Q. Výsledkový Main obsahuje jeden QF walkover, není to snížení plánované geometrie. Q 2 + Main 7 dní bez překryvu, 9 kalendářních dní a 39 nominálních uzlů.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 při nevyužití rezerv | 14 |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28, Q 14+2=16; ročníkový přepis výslovně potvrzuje obě kapacity a Q kvótu (STU24-7). Pořadatel 8.6. výslovně potvrzuje čtyři BYE pro seedy 1–4. Výsledkový Main STU24-13 má LL Gasquet na původním místě seedu 1 s BYE, tři WC Squire/Medjedovic/Shapovalov, čtyři Q a Berrettini PR; historické nahrazení seedu nemění nominální nasazení. Q pavouk má 16 účastníků, dva WC Rehberg/Nadal, čtyři vítěze sekcí a sedm viditelně označených seedů (chybí 5). Původní Q1 program STU24-9 uvádí Medjedovice proti Cressymu, konečný Q pavouk místo něj Alt Gavrielides a Main WC Medjedovice. Původní seed č. 5 bez originálu nepotvrzen; nominálně osm seedů podle pravidel. Main 12+8+4+2+1=27, Q 8+4=12.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle MPL24-5/6 a IW24-11/14. Main dvě SE a jedna LE rezervy, při nevyužití přecházejí do DA; stav SE 0 a LE 1 v přepisu není důkaz absence SE rezerv. Q dva BO3 zápasy k postupu, 13/7/0 ATP bodů, žádné třetí kolo. Main první prohra po BYE 0 bodů výslovně v ATP Media Notes. LL, Alt a PR neznamenají další kapacitu. V týdnu Stuttgart/'s-Hertogenbosch pouze dvě ATP Tour akce, nepřebírat alokaci NG pro tři souběžné ATP turnaje.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 111785 |
| Finalista | 1 | 165 | 65205 |
| SF | 2 | 100 | 38335 |
| QF | 4 | 50 | 22215 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 12900 |
| R32 | 12 | 0 | 7880 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3940 |
| Q1 prohra | 8 | 0 | 2150 |

Main primární ATP Notes str. 1–2, výslovně EUR, shoda s dobovým Tennis Infinity 17.5. (STU24-6). Q 3940/2150 EUR shodně ročníkové tabulky TennisCompanion a CanalTenis (STU24-14/15), původní Q finanční tabulka nedostupná, P*. Nezávislost vzniku sekundárních tabulek neprokázána. TennisTemple uvádí neslučitelný tříkolový Q rozpis a chybné Main ceny (vítěz 72150 EUR), přestože jeho pavouk má dvě Q kola; použít pouze pro strukturu, nikoli finanční tabulku. Nominální Main 540280 EUR, Q 32960 EUR, celkem 573240 EUR. 28 Main + 12 nepostupujících Q příjemců. Celková prize money 734915 EUR (včetně doubles) není mužský singlový součet.

### 7. Kontrola a mezery

I/T/E/D/R/B/P/Z doloženy s výhradami, H* plán kol a denní Main splity z předturnajových a dobových oznámení. P* Q sekundární shoda; Z* ATP Notes textově, screenshot 403, přímé Main/Q PDF nedostupné; odkazy z původních zpráv pořadatele nyní vedou na stránky 2025, nezaměňovat je za originální 2024 OOP/los. Originální acceptance lists/DS, časy losů, model míčů, konečné cutoffy, původní denní OOP a obrazový originál obou losů nezískány. Aritmetická kontrola kapacit, nominálních seedů, BYE, Q postupů, 27+12 uzlů a cen prošla. Další 's-Hertogenbosch 2024, stejný týden a Q data 8.–9.6. podle STU24-7/10. Bez runtime změn.

### 8. Zdroje (STU24)

- STU24-1: [pořadatelský předturnajový program 9.4.](https://bossopen.com/de/news/volles-programm-bei-den-boss-open), Q dny a počty, Main okna, plán F.
- STU24-2: [ATP Preview & Day 1, 10.6.2024](https://www.atptour.com/-/media/793a5f3d4a6d416bb959444a9b850730.pdf), str. 1–2 text, screenshot 403; Main ceny a body.
- STU24-3: [Tennis Europe ročníkový záznam](https://www.tenniseurope.org/calendarevent/73819/BOSS-Open), ATP 321; [Main originál](https://www.protennislive.com/posting/2024/321/mds.pdf) a [Q originál](https://www.protennislive.com/posting/2024/321/qs.pdf) nedostupné.
- STU24-4: [ročníková identita](https://en.wikipedia.org/wiki/2024_BOSS_Open), [ITF ročníkový záznam](https://www.itftennis.com/en/tournament/stuttgart/ger/2024/m-250-ger-2024-002/draws-and-results/).
- STU24-5: [pořadatel 15.5.](https://bossopen.com/en/news/fans-can-look-forward-to-an-amazing-program), BYE, R32 a začátek R16.
- STU24-6: [Tennis Infinity 17.5.2024](https://tennis-infinity.com/atp/2024-stuttgart-open-atp-prize-money-points-overview), Main odměny.
- STU24-7: [TennisTeen 5.6.2024 přepis Main/Q entry lists](https://www.tennisteen.it/entry-list/atp/24176-atp-entry-list-10-16-giugno-2024.html), oba rank dates, cutoffy, Q 14+2.
- STU24-8: [pořadatel 8.6. Main los](https://bossopen.com/en/news/draw-of-the-boss-open-2024-carried-out).
- STU24-9: [pořadatel 7.6. Q1 program](https://bossopen.com/en/news/boss-open-starten-mit-erster-quali-runde), 8 Q1, WC Nadal, předstartovní párování.
- STU24-10: [LiveTennis aktualizace Main/Q 7.6.](https://www.livetennis.it/post/413572/atp-250-stoccarda-e-s-hertogenbosch-entry-list-md-musetti-e-arnaldi-a-stoccarda-berrettini-punta-a-giocare-in-germania/).
- STU24-11: [pořadatel 10.6. úterní plán](https://bossopen.com/en/news/full-schedule-on-tuesday), osm R32.
- STU24-12: [pořadatel 8.6. nedělní program po dešti](https://bossopen.com/en/news/rain-makes-for-a-full-schedule-on-sunday), dva přesunuté Q1.
- STU24-13: [TennisTemple Main pavouk](https://en.tennistemple.com/competitions/stuttgart/2024/draw), [Q pavouk](https://en.tennistemple.com/competitions/stuttgart/2024/draw-qualifications), pouze struktura; [dobový Main přepis CanalTenis](https://canaltenis.com/cuadro-atp-stuttgart-2024/).
- STU24-14: [TennisCompanion historická tabulka 2024](https://tenniscompanion.org/prize-money/stuttgart/), Q 3940/2150 EUR.
- STU24-15: [CanalTenis tabulka 2024](https://canaltenis.com/prize-money-atp-stuttgart/), Q 3940/2150 EUR; dobové ATP předpisy viz MPL24-5/6 a IW24-11/14.

## 's-Hertogenbosch 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/Z s dílčími mezerami). Rešerše 2026-11-28. Předturnajový program pořadatele z 21.5. obsahuje přesné denní počty mužských singlů. Předstartovní Main a oba výsledkové originály ATP vizuálně ověřeny, včetně Main/Q finančních tabulek. Skutečné dešťové přesuny odděleny.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Libéma Open (Rosmalen Grass Court Championships) | HER24-1/2/4 |
| Kategorie / ATP ID | ATP 250 / 440 | HER24-1/2 |
| Ročník | 33. (1990–2019, 2022–2024) | HER24-4 |
| Dějiště | Autotron Rosmalen, 's-Hertogenbosch, Nizozemsko | HER24-4/5 |
| Povrch | venkovní tráva | HER24-1/2/5 |
| Časové pásmo | Europe/Amsterdam, CEST UTC+02:00 | lokalita a datum |
| ATP supervisors | Carlos Sanches / Andrey Kornilov | HER24-1/2/3 |
| Měna | EUR | HER24-1/2/4 |

Společný ATP/WTA turnaj; oddělená ženská soutěž má jiné losy, počty i finanční tabulky. Model míčů, DS, ředitel/referee/tour manager neověřeny.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-13 | HER24-7 |
| Q rank date | 2024-05-20 | HER24-7 |
| Nominální Main deadline | 2024-05-13 18:00 CEST | odvozeno §7.03 |
| Nominální Q deadline | 2024-05-20 18:00 CEST | odvozeno §7.03 |
| Nominální LE deadline | 2024-06-06 16:00 CEST | odvozeno §7.04 |
| Main los | 2024-06-08, hodina neověřena | HER24-8 |
| Q los | před zahájením Q1 8.6., hodina neověřena | HER24-2/5 |
| Q | 2024-06-08–09 od 11:00 | HER24-5 |
| Main | 2024-06-10–16 | HER24-1/4/5 |
| F | 2024-06-16 12:00 CEST, plán | HER24-5/6/15 |

Dobový přepis 5.6. obsahuje Main původní cutoff 66, Q 125; 18 DA, 3 WC, 4 Q, SE 0, LE 1 v Main; Q 14 DA/2 WC. Oznámení pořadatele 14.5. uvádí 18 původně přijatých hráčů (včetně PR Raonice) a čtyři Q, tři rezervy popsané společně jako SE; v dobovém předpisu 2 SE + 1 LE. Závěrečné i předstartovní ATP losy uvádějí Main last direct acceptance at deadline Purcell 84 a at draw Bautista Agut 85, Q last direct acceptance Brouwer 244. Odlišná pole a časové stavy od původního cutoffu 66/125 nezaměňovat. Uzávěrky odvozeny, nikoli auditované timestampy originálních listin. Přesný čas obou losů, originální acceptance listy a DS nezískány.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-08 | 8 |
| Q2 | 2024-06-09 | 4 |
| R32 | 2024-06-10–11 | 12 (4+8) |
| R16 | 2024-06-12–13 | 8 (4+4) |
| QF | 2024-06-14 | 4 |
| SF | 2024-06-15 | 2 |
| F | 2024-06-16 | 1 |

Předturnajový HER24-5 z 21.5. je výslovně předběžný program, ale odděleně vyčísluje mužské ATP singlové zápasy pro každý den (nikoli součty WTA a doubles). Potvrzuje 8/4 Q a 4/8/4/4/4/2/1 Main. První čtyři R32 v pondělním denním bulletinu HER24-9; kvůli dešti se začalo až v 15:30 (HER24-16), jeden z nich dokončen, jeden přerušen a dva přesunuty bez zahájení. Úterní HER24-10 uvádí těchto 11 zbývajících R32, tedy osm nominálních plus tři přenesené uzly. Středeční HER24-11 má čtyři R16, čtvrteční HER24-12 čtyři nové R16 plus pokračování Vukic–Khachanov. Páteční HER24-13 plánuje čtyři QF; jeden QF Humbert–Brouwer dokončen až v sobotu z důvodu počasí, viz HER24-14. Obě SF byly dokončeny v sobotu (HER24-17). Nedělní HER24-15 potvrzuje plán F ve 12:00 i po změnách programu jiných disciplín. V ročníku pořadatel prohodil pořadí mužského a ženského finále, mužské bylo plánováno dříve; jde o původní ročníkový plán, nikoli dešťový přesun. Q 2 + Main 7 dní, bez překryvu, 9 kalendářních dní, 39 nominálních uzlů. Nezaměňovat přesuny konkrétních utkání s plánem kol.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 při nevyužití rezerv | 14 |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28; Q 14+2=16 potvrzeno dobovou listinou HER24-7. Předstartovní Main originál HER24-3 obsahuje osm seedů, čtyři BYE (2/10/23/31), tři WC (Van Rijthoven, Van de Zandschulp, Goffin) a čtyři Q placeholdery (4/6/15/26). Výsledkový Main HER24-1 dokládá čtyři řádné Q (Brouwer, Huesler, Napolitano, Schoolkate) a LL Bergs: po odstoupení Carballese Baeny se řádný kvalifikant Brouwer objevil na jiné pozici a LL na původním Q placeholderu 4. Nevyvozovat z toho další kvalifikační místo; přesné administrativní pořadí změn neověřeno. Q originál HER24-2 potvrzuje 16 míst, 2 WC (Haase, Bergs), 4 sekce a osm původně nasazených v tabulce. Seed 1 Bautista Agut přesunut do Main, jeho místo obsadil Alt Koolhof, proto jen sedm označených seedů v konečném Q pavouku. Bergs je současně seed a WC (překryv vlastností). Main 12+8+4+2+1=27, Q 8+4=12.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle MPL24-5/6 a IW24-11/14. Nevyužité SE/LE rezervy se vracejí k DA, aktuální stav přepisu SE 0 není důkaz absence rezerv. ATP Media Notes HER24-4 výslovně potvrzují 0 bodů za první prohru po BYE. Q body 13/7/0 a 0 samostatné finanční odměny za postup přímo v originálu HER24-2; Q body navíc k Main výsledku. WC i PR mohou být nasazené, pokud splňují dobové pravidlo rankingu pro nasazení; Q seed 3 WC doložen zde. LL a Alt nevytvářejí nová místa. Pouze dvě souběžné ATP Tour akce v tomto týdnu (Stuttgart a 's-Hertogenbosch); žádná extrapolace NG pravidla tří akcí.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 104985 |
| Finalista | 1 | 165 | 61235 |
| SF | 2 | 100 | 36000 |
| QF | 4 | 50 | 20860 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 12110 |
| R32 | 12 | 0 | 7400 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3700 |
| Q1 prohra | 8 | 0 | 2020 |

Všechny částky primárně v obou výsledkových ATP originálech HER24-1/2 a Main též v předstartovním HER24-3 a ATP notes. Nominální Main 507340 EUR, Q 30960 EUR, celkem 538300 EUR; 28 Main příjemců a 12 nepostupujících Q příjemců. Financial commitment 767455 EUR z originálů není mužský singlový součet. Nezaměňovat se Stuttgart, jiná dotace i jednotlivé ceny při stejné geometrii.

### 7. Kontrola a mezery

I/T/H/D/R/B/P doloženy přímo ročníkovými zdroji. H bez hvězdičky: přesné plánované počty všech devíti dní doloženy předturnajovým programem, denní bulletiny nezávisle potvrzují jeho použití a pozdější změny. E* původní cutoffy a rank dates z dobového přepisu, původní acceptance listy/DS a přesné hodiny losů chybějí, uzávěrky odvozené. Z* vizuálně ověřeny 3 ATP losy po jedné straně a první strany denních bulletinů 10., 11., 13., 14., 16.6.; obrazové vykreslení bulletinů 12./15.6. selhalo 500, jejich programy textově dostupné, ATP notes screenshot 403. Bez získaných celých PDF bajtů neuvádět SHA-256. Kontrola kvót, 28/16, 8/8 nominálních seedů, 4 BYE, 4 postupů, denních součtů, 27+12 uzlů i odměn prošla. Další Halle a Queen's 2024, oba Main 17.–23.6. dle ATP archivu. Bez runtime změn.

### 8. Zdroje (HER24)

- HER24-1: [originální ATP výsledkový Main](https://www.protennislive.com/posting/2024/440/mds.pdf), str. 1 vizuálně.
- HER24-2: [originální ATP výsledkový Q](https://www.protennislive.com/posting/2024/440/qs.pdf), str. 1 vizuálně.
- HER24-3: [archiv původního předstartovního Main](https://www.fantatennis.net/_downloads/abc95d70d2729542c94dcfd3710a295c), str. 1 vizuálně.
- HER24-4: [ATP Preview & Day 1 10.6.](https://www.atptour.com/-/media/23c154abd77448d6aea231d5d3c958fc.pdf), text str. 1–2, screenshot 403, historie, odměny a BYE bodová výjimka.
- HER24-5: [pořadatel 21.5. předběžný program](https://libema-open.nl/2024/05/21/agenda-libema-open-2024/), přesné denní počty ATP singles.
- HER24-6: [pořadatel 14.5. entry announcement](https://libema-open.nl/en/2024/05/14/as-many-as-six-atp-top20-players-open-grass-season-at-libema-open/), 18 jmen a rezervy, změna pořadí finále.
- HER24-7: [TennisTeen přepis Main/Q listin 5.6.](https://www.tennisteen.it/entry-list/atp/24176-atp-entry-list-10-16-giugno-2024.html), 66/125 cutoff, obě rank dates, 14+2 Q.
- HER24-8: [pořadatel Main los 8.6.](https://libema-open.nl/en/2024/06/08/title-holder-griekspoor-close-to-van-de-zandschulp-after-draw/).
- HER24-9: [pořadatelský bulletin 10.6.](https://libema-open.nl/dagjournaals/2024/10062024_dagjournaal_maandag.pdf), str. 1 vizuálně.
- HER24-10: [pořadatelský bulletin 11.6.](https://libema-open.nl/dagjournaals/2024/11062024_dagjournaal_dinsdag.pdf), str. 1 vizuálně.
- HER24-11: [pořadatelský bulletin 12.6.](https://libema-open.nl/dagjournaals/2024/12062024_dagjournaal_woensdag.pdf), str. 1 text.
- HER24-12: [pořadatelský bulletin 13.6.](https://libema-open.nl/dagjournaals/2024/13062024_dagjournaal_donderdag.pdf), str. 1 vizuálně.
- HER24-13: [pořadatelský bulletin 14.6.](https://libema-open.nl/dagjournaals/2024/14062024_dagjournaal_vrijdag.pdf), str. 1 vizuálně.
- HER24-14: [pořadatelský bulletin 15.6.](https://libema-open.nl/dagjournaals/2024/15062024_dagjournaal_zaterdag.pdf), str. 1 text, pokračující QF.
- HER24-15: [pořadatelský bulletin 16.6.](https://libema-open.nl/dagjournaals/2024/16062024_dagjournaal_zondag.pdf), str. 1 vizuálně.
- HER24-16: [ATP report 10.6.](https://www.atptour.com/en/news/nardi-goffin-s-hertogenbosch-2024-monday), dešťový posun začátku.
- HER24-17: [ATP report 15.6.](https://www.atptour.com/en/news/korda-griekspoor-de-minaur-humbert-s-hertogenbosch-2024-saturday), obě SF sobota; [ATP výsledkový archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), další Halle/Queen's. Dobový rulebook viz MPL24-5/6 a IW24-11/14.

## Halle 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/P/Z s dílčími mezerami). Rešerše 2026-11-28. Oba originální ATP Main losy vizuálně ověřeny, Q struktura z dobové listiny a úplného sekundárního pavouku, Q odměny ze shodných ročníkových tabulek. Neodvozovat přesný původní denní split R32 z pozdějších výsledků.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Terra Wortmann Open | HAL24-1/2 |
| Kategorie / ATP ID | ATP 500 / 500 | HAL24-1/3 |
| Ročník | 31. (logo originálního losu) | HAL24-1/2 |
| Dějiště | OWL Arena, Halle (Westfalen), Německo | HAL24-4/5 |
| Povrch | venkovní tráva | HAL24-1/2/4 |
| Časové pásmo | Europe/Berlin, CEST UTC+02:00 | lokalita a datum |
| ATP supervisors | Hans-Juergen Ochs / Roland Herfel | HAL24-1 |
| Měna | EUR | HAL24-1/2 |

Předstartovní los uvádí pouze Herfela, výsledkový oba supervisory. Model míčů, detail sheet, tour manager a referee nezískány. Nezaměňovat Halle ve Vestfálsku s Halle (Saale). Sekundární zdroj HAL24-10 nesprávně uvádí 30. edici, originální logo výslovně 31.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-20 | HAL24-6 |
| Q rank date | 2024-05-27 | HAL24-6 |
| Nominální Main deadline | 2024-05-20 18:00 CEST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-05-27 18:00 CEST (12:00 US Eastern) | odvozeno §7.03 |
| Deadline podmíněné A+ WC | 2024-06-14 16:00 CEST (10:00 US Eastern) | odvozeno §7.12 A.2 |
| Main los | 2024-06-15, čas nepotvrzen | HAL24-4 |
| Q los | před zahájením Q1 15.6., hodina neověřena | HAL24-7/8 |
| Q | 2024-06-15–16 od 11:00 | HAL24-4/5 |
| Main | 2024-06-17–23 | HAL24-1/2/4/5 |
| F | 2024-06-23 14:00 CEST, dobový program | HAL24-5 |

Dobový přepis listiny 11.6. uvádí Main původní cutoff 50, Q 96, Main 23 DA/3 WC/4 Q/1 SE (31 míst v mezistavu bez explicitní A+ rezervy), Q13 DA/3 WC. Oba původní Main losy uvádějí v obou cutoff polích Cobolli 56. Odlišné časové stavy a pole uchovat odděleně. Uzávěrky odvozené, nikoli skutečné exportní časy. Originální acceptance listy, DS, Q konečný cutoff a hodiny losování nezískány.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-15 | 8 |
| Q2 | 2024-06-16 | 4 |
| R32 | 2024-06-17–18, pracovní nominální okno | 16 |
| R16 | 2024-06-19–20 | 8 |
| QF | 2024-06-21 | 4 |
| SF | 2024-06-22 | 2 |
| F | 2024-06-23 | 1 |

HAL24-10 (článek původně 11.6., aktualizován 23.6.) uvádí R32 pondělí/úterý a R16 středa/čtvrtek. Dobový tennis MAGAZIN aktualizovaný 22.6. zahrnuje R32 i R16 ve středu a čtvrtek, tedy rozšířená okna, a potvrzuje závěrečná kola pátek/sobota/neděle. Původní oficiální předdenní programy nezískány; není jisté, zda úterní R32 spillover byl plán nebo pozdější posun, proto H*. Výsledkový archiv 19.6. potvrzuje dva R32 (Struff–Darderi, Berrettini–Michelsen) a čtyři R16. Skutečný středeční R32 nepřepisuje pracovní nominální okno bez lepšího předturnajového dokladu; z přesných denních splitů nečinit jistotu. ATP předturnajový článek 11.6. potvrzuje Q dva dny od 11:00, Main pondělí–pátek od 12:00, Main los v sobotu a víkendová závěrečná kola. Q 2 + Main 7 dní bez překryvu, 9 kalendářních dní, 43 nominálních uzlů. Exhibice 16.6. nepatří do ATP Q.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 (4 sekce po 4) |
| DA | 23 základních, až 25 | 13 |
| SE | 1 rezerva | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

ATP 500 standard 23+1 SE+3 běžné WC+1 A+ WC+4 Q=32, při nevyužití rezerv přecházejí místa do DA. Předstartovní Main vizuálně: 8 seedů, 4 Q placeholdery 15/20/22/31, tři WC Squire/Fonseca/Koepfer, jeden SE Berrettini. Výsledkový Main má čtyři Q (Purcell/Duckworth/Michelsen/Otte), 24 neoznačených DA, 3 WC a 1 SE. A+ WC skutečně nebyla označena jako čtvrtá WC; 24 DA odpovídá uvolnění rezervy, administrativní přidělení jednotlivci neověřeno. Q pavouk všech 16 hráčů a seedů 1–8, WC Rehberg/Otte/Wessels, čtyři sekce a čtyři postupující; nezávisle listina Q potvrzuje 13+3. Main 16+8+4+2+1=31, Q 8+4=12. Skreč Auger-Aliassime v R32 po zahájení není walkover.

### 5. Dobová pravidla

ATP §7.03/7.08 B/E/7.09/7.10/7.12 A.2/7.13/7.15–18 a §9.03, viz ROT24-15/16 a IW24-11/14. ATP500 Main jedna SE rezerva, případná čtvrtá WC pro způsobilého A+ hráče, nevyužité místo DA. ATP250 LE se nepřenáší. Q 13 DA/3 WC, dva BO3 zápasy k postupu; Q body 25/13/0 podle dobové tabulky pro 32 Main (ne 16/8/0 pro 48 Main). Body Q navíc k Main výsledku. Bez BYE, takže výjimka první prohry po BYE zde není relevantní. Pouze dvě souběžné ATP Tour akce v tomto týdnu, Halle a Queen's; nepřidávat NextGen rezervy pro tři turnaje.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 421790 |
| Finalista | 1 | 330 | 226945 |
| SF | 2 | 200 | 120960 |
| QF | 4 | 100 | 61800 |
| R16 | 8 | 50 | 32990 |
| R32 | 16 | 0 | 17595 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 9015 |
| Q1 prohra | 8 | 0 | 5060 |

Main vizuálně v obou ATP originálech a shodně v ATP Media Notes. Q 9015/5060 EUR v HAL24-11/12, sekundární shoda, nikoli originální Q finanční tabulka; nezávislost vzniku tabulek neprokázána. Nominální Main 1683295 EUR, Q 76540 EUR, celkem 1759835 EUR; 32 Main příjemců a 12 nepostupujících Q příjemců. Financial commitment 2411390 EUR a prize money 2255655 EUR nejsou mužské singlové součty. Q body z dobového předpisu.

### 7. Kontrola a mezery

I/T/D/R/B doloženy. H* okna R32/R16 pracovní dle dobových programů; jejich přesné původní splity a důvod středečního R32 nedoloženy. E* rank dates a původní cutoffy z dobového přepisu, oba Main cutoffy z originálů; originální acceptance/DS, Q cutoff v losu a hodiny losů chybějí. P* Q sekundární shoda. Z* oba Main originály po jedné straně vizuálně ověřeny, přímý Q PDF nedostupný, ATP preview indexovaný text (otevření 403). Bez získání celých bajtů neuvádět SHA-256. Aritmetika 32/16, 8/8 seedů, bez BYE, 4 postupující, 31+12 uzlů, kvóty a peníze prošla. Další Queen's 2024. Bez runtime změn.

### 8. Zdroje (HAL24)

- HAL24-1: [originální výsledkový Main u pořadatele](https://www.terrawortmann-open.de/fileadmin/Gerry_Weber_Open/Turnier/2024/Hauptfeld_Einzel.pdf), str. 1 vizuálně.
- HAL24-2: [archiv originálního předstartovního Main Raquetc](https://www.raquetc.com/wp-content/uploads/2024/06/ATP-500-Halle-2024-quadro-principal-singulares.pdf), str. 1 vizuálně.
- HAL24-3: [Tennis Europe ročníkový záznam](https://www.tenniseurope.org/calendarevent/73821/Terra-Wortmann-Open), ATP ID 500; [přímý Q PDF](https://www.protennislive.com/posting/2024/500/qs.pdf) nedostupný.
- HAL24-4: [ATP předturnajový přehled 11.6.](https://www.atptour.com/en/news/halle-2024-atp-500-history-draw-schedule), indexovaný text, otevření 403.
- HAL24-5: [tennis MAGAZIN 22.6.](https://www.tennismagazin.de/news/atp-halle-alle-infos-zu-spieler-preisgeld-tickets-tv-terra-wortmann-punkte-absagen-spielplan/), dobový rozpis a F 14:00.
- HAL24-6: [TennisTeen 11.6., Main/Q přepis](https://www.tennisteen.it/entry-list/atp/24180-atp-entry-list-17-23-giugno-2024.html), rank dates, cutoffy, Q13+3.
- HAL24-7: [LiveTennis aktualizace 15.6.](https://www.livetennis.it/post/414007/atp-500-halle-e-queens-entry-list-md-e-qualificazioni-uscite-anche-le-quali-berrettini-nelle-quali-del-queens-con-il-ranking-protetto/).
- HAL24-8: [TennisTemple úplný Q pavouk](https://cs.tennistemple.com/competitions/halle/2024/draw-qualifications), 8 seedů, 3 WC, 4 sekce.
- HAL24-9: [TennisTemple denní výsledky 19.6.](https://en.tennistemple.com/competitions/halle/2024/orderofplay/2024-06-19), 2 R32 a 4 R16, ne původní plán.
- HAL24-10: [dobový program, původně 11.6.](https://gotennisracquets.com/halle-open-2024/), aktualizován 23.6.; R32 17.–18.6., R16 19.–20.6.; chybný počet edic nepoužit.
- HAL24-11: [CanalTenis ročníková finanční tabulka 2024](https://canaltenis.com/prize-money-atp-halle/), Q 9015/5060.
- HAL24-12: [ročníková finanční tabulka](https://en.wikipedia.org/wiki/2024_Halle_Open), Q shoda; [ATP Media Notes 17.6.](https://www.atptour.com/-/media/740e3e3c2dec43929e5791b1ba7454cd.pdf), indexovaná Main tabulka, ne vizuálně ověřený PDF originál.
- HAL24-13: [pořadatel 13.6. o exhibici](https://www.terrawortmann-open.de/news/artikel/showmatch-am-qualifikationswochenende-wird-als-herren-doppel-gespieltjunioren-max-schoenhaus-und-patrick-valentin-moise-unterstuetzen-dustin-brown-und-mischa-zverev/), odděleně od ATP Q. Dobový rulebook viz ROT24-15/16.

## Queen's 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/P/Z s označenými mezerami). Rešerše 2026-11-28. Oba původní ATP Main losy, lednové oznámení pořadatele a šest denních OOP vizuálně ověřeny. Přesný Main split 5+11, nikoli symetrický 8+8. Q odměny sekundární shoda, Q nominální kvóty doloženy dobovým přepisem listiny.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | cinch Championships | QUE24-1/2 |
| Kategorie / ATP ID | ATP 500 / 311 | QUE24-1/3 |
| Ročník | 121. podle ročníkového přehledu | QUE24-4 |
| Dějiště | The Queen's Club, West Kensington, Londýn, Velká Británie | QUE24-1/5 |
| Povrch | venkovní tráva | QUE24-1/2/4 |
| Časové pásmo | Europe/London, BST UTC+01:00 | lokalita a datum |
| Ředitel / tour manager | Jamie Murray / Diego Pedraza | QUE24-6/7 |
| Referee / ATP supervisors | Denise Parnell / Gerry Armstrong a Cedric Mourier | QUE24-1/6/7 |
| Měna | EUR, nikoli GBP | QUE24-1/2 |

V roce 2024 jde o mužský ATP turnaj, nikoli o pozdější kombinovanou ATP/WTA akci. Model míčů a originální detail sheet nezískány. Adresa National Tennis Centre v lednovém dopisu je adresa kanceláře, nikoli dějiště.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-20 | QUE24-8 |
| Q rank date | 2024-05-27 | QUE24-8 |
| Nominální Main deadline | 2024-05-20 17:00 BST (12:00 US Eastern) | odvozeno §7.03 |
| Nominální Q deadline | 2024-05-27 17:00 BST (12:00 US Eastern) | odvozeno §7.03 |
| Deadline A+ WC | 2024-06-14 15:00 BST (10:00 US Eastern) | odvozeno §7.12 A.2 |
| Main los | 2024-06-15, přesná hodina neověřena | QUE24-9 |
| Q los | před Q1 15.6., přesná hodina neověřena | QUE24-5/10 |
| Q1 / Q2 | 2024-06-15 od 11:00 / 2024-06-16 od 12:00 BST | QUE24-5/10 |
| Main | 2024-06-17–23 | QUE24-1/2/5 |
| Main LL sign-in 17.–18.6. | 11:30 BST | QUE24-7/11 |
| F | 2024-06-23 14:00 BST | QUE24-14 |

Dobový přepis 11.6. uvádí původní Main cutoff 35, Q 77; rank dates a 23 DA/3 WC/4 Q/1 SE (31 míst v mezistavu bez explicitní A+ rezervy), Q 13 DA/3 WC. Oba originální Main losy uvádějí J. Thompson 37 v obou cutoff polích. Odlišné stavy nemíchat. Originální acceptance listy a DS nezískány; uzávěrky odvozeny. Sky 15.6. potvrzuje den zveřejnění Main losu, ne přesný okamžik losování. Q cutoff v konečném originálu nedostupný.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-15 | 8 |
| Q2 | 2024-06-16 | 4 |
| R32 | 2024-06-17–18 | 16 (5+11) |
| R16 | 2024-06-19–20 | 8 (4+4; druhý den odvozen) |
| QF | 2024-06-21 | 4 |
| SF | 2024-06-22 | 2 |
| F | 2024-06-23 | 1 |

Lednový dopis pořadatele explicitně stanoví Q 15.–16.6. a Main 17.–23.6.; ATP předturnajový přehled 11.6. potvrzuje začátky Q 11:00/12:00, Main od poledne. Revidovaný nedělní Q OOP vydaný 16.6. 10:19 obsahuje tři nedokončené Q1 (TBF Popyrin–Virtanen, Mpetshi Perricard–Vukic, Choinski–Bergs) a Q2 Rinderknech–Hijikata, poté dvě další Q2 po odpočinku. Čtvrtý Q2 Daniel–Kokkinakis skončil walkoverem (QUE24-15). Tyto výjimky nemění nominální 8+4 Q uzlů ani dvoudenní kvalifikaci. Přesnou příčinu všech Q1 přerušení neprohlašovat bez dalšího dokladu.

Pondělní OOP vydaný 16.6. 18:36 má 4 R32 na centru a 1 na kurtu 1. Úterní OOP vydaný 17.6. 13:58 má 4+4+3 R32 na třech kurtech. Dohromady všech 16 uzlů; nejde o odhad 8+8. Středeční OOP vydaný 18.6. 18:45 má čtyři R16 na centru, zbývající čtyři odvozeny pro čtvrtek. Původní čtvrteční OOP nezískán. Páteční OOP vydaný 20.6. 17:02 má čtyři QF, v jednom ještě alternativního účastníka, protože R16 v době vydání neskončil. Sobotní dvě SF doloženy dobovým reportem pořadatele. Finálový OOP vydaný 22.6. 17:32 plánuje singlové F v neděli 14:00, před doubles. Q 2 + Main 7 dní bez překryvu, 9 kalendářních dní, 43 nominálních uzlů. Wheelchair a learning disability exhibice 21.–23.6. odděleny, nejde o další ATP singles uzly.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 32 | 16 / 16 (4 sekce po 4) |
| DA | 23 základních, až 25 při uvolnění rezerv | 13 |
| SE | 1 rezerva | 0 |
| WC | 3 běžné + 1 podmíněná A+ | 3 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 0 | 0 |
| Kola / zápasy | 5 / 31 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 23+1 SE+3 běžné WC+1 A+ WC+4 Q=32, Q13+3=16. Oba originální Main losy vizuálně potvrzují osm seedů, čtyři Q místa (13/20/23/26), tři WC Murray/Harris/Evans, jeden SE Nakashima a PR Raonic. Zbývajících 24 míst mimo Q/WC/SE odpovídá uvolnění A+ rezervy do DA; administrativní přidělení konkrétnímu hráči neověřeno. Q přepis listiny potvrzuje 13+3. Úplný sekundární Q pavouk (QUE24-16) má 16 hráčů, seedy 1–8, WC Jubb/Choinski/Searle a čtyři Q postupující. Bergs označen jako seed 8 v sekundárním pavouku, avšak Alt v originálním nedělním OOP; nevylučuje se převzetí seed pozice náhradníkem, skutečný administrativní status bez Q originálu neuzavřen. Nominálně 8 seedů. Main 16+8+4+2+1=31, Q 8+4=12, Q walkover Daniel–Kokkinakis je postupový uzel, nikoli odehraný zápas.

### 5. Dobová pravidla

ATP §7.03/7.08 B/E/7.09/7.10/7.12 A.2/7.13/7.15–18 a §9.03 viz ROT24-15/16 a IW24-11/14. ATP500 Main jedna SE rezerva a podmíněná čtvrtá A+ WC, nevyužité rezervy přecházejí do DA. ATP250 LE se nepřenáší. Q 13 DA/3 WC, dva BO3 zápasy k postupu, Q body 25/13/0 dle tabulky pro ATP500 s 32 Main; přičítají se k Main výsledku. Bez BYE. Pouze dvě ATP Tour akce v daném týdnu (Halle, Queen's), žádná extrapolace NG pravidla tří akcí. PR, Alt, LL a nasazení nejsou dodatečné kapacity.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 500 | 421790 |
| Finalista | 1 | 330 | 226945 |
| SF | 2 | 200 | 120960 |
| QF | 4 | 100 | 61800 |
| R16 | 8 | 50 | 32990 |
| R32 | 16 | 0 | 17595 |
| Q postupující | 4 | 25 | 0 samostatně |
| Q2 prohra | 4 | 13 | 9015 |
| Q1 prohra | 8 | 0 | 5060 |

Main ceny přímo vizuálně v obou ročníkových ATP originálech QUE24-1/2 (EUR), neodvozeny z Halle, byť stejné. Q 9015/5060 EUR shodně QUE24-17/18, původní Q finanční tabulka nedostupná, P*. Nezávislost vzniku sekundárních tabulek není prokázána. TennisTemple Q finanční tabulka uvádí 8530/4785, 20/10 bodů a třetí Q kolo, což odporuje vlastnímu dvoukolovému pavouku a dobovému ATP bodovému předpisu; nepoužívat pro ceny/body. Nominální Main 1683295 EUR, Q 76540 EUR, celkem 1759835 EUR. 32 Main a 12 nepostupujících Q příjemců. Financial commitment 2411390 EUR a celková prize money 2255655 EUR nejsou singlový součet. Skutečná individuální finanční úprava při walkoveru není nominální tabulka.

### 7. Kontrola a mezery

I/T/H/D/R/B doloženy v nominálním rozsahu. E* původní rank dates a cutoffy z dobového přepisu, Main cutoffy v originálech, Q acceptance list/DS, konečný Q cutoff a časy losů chybějí. P* Q sekundární shoda. Z* oba Main originály a OOP 16./17./18./19./21./23.6. plus lednový dopis vizuálně zkontrolovány; přímé Q PDF nedostupné, čtvrteční OOP a původní sobotní Q1 OOP nezískány, přesná Q administrativní označení otevřená. Nevymýšlet PDF SHA-256. Kontrola kvót, seedů, 32/16, 4 postupů, 31+12 uzlů, denních počtů a odměn prošla. Další Mallorca 2024 (Main 23.–29.6.), Eastbourne 2024 (24.–29.6.) podle ATP archivu. Bez runtime změn.

### 8. Zdroje (QUE24)

- QUE24-1: [originální výsledkový ATP Main u LTA](https://www.lta.org.uk/49e71a/siteassets/events/cinch/media/completed-2024-queens-draw.pdf), str. 1 vizuálně.
- QUE24-2: [originální předstartovní ATP Main u LTA](https://www.lta.org.uk/49d628/siteassets/events/cinch/media/2024-queens-club-draw.pdf), str. 1 vizuálně.
- QUE24-3: [Tennis Abstract ročníkový záznam ATP 311](https://www.tennisabstract.com/cgi-bin/tourney.cgi?t=2024-0311%2FQueen%27s-Club); [přímý Q PDF](https://www.protennislive.com/posting/2024/311/qs.pdf) nedostupný.
- QUE24-4: [ročníková identita](https://en.wikipedia.org/wiki/2024_Queen%27s_Club_Championships); [ITF ročníkový záznam](https://www.itftennis.com/en/tournament/queens/gbr/2024/m-500-gbr-2024-001/draws-and-results/).
- QUE24-5: [LTA oznámení 31.1.2024](https://www.lta.org.uk/49124a/siteassets/events/cinch/residents-letter-jan-2024.pdf), str. 1 vizuálně, původní Q/Main termíny.
- QUE24-6: [LTA revidovaný OOP Q 16.6.](https://www.lta.org.uk/49d7c6/siteassets/news/2024/june/cinch-championships-oop-sunday-16-june.pdf), str. 1 vizuálně, TBF a Q2.
- QUE24-7: [LTA OOP 17.6.](https://www.lta.org.uk/49d5f8/siteassets/events/cinch/media/queens-order-of-play---june-17-2024.pdf), str. 1 vizuálně, 5 R32.
- QUE24-8: [TennisTeen přepis Main/Q 11.6.](https://www.tennisteen.it/entry-list/atp/24180-atp-entry-list-17-23-giugno-2024.html), rank dates, cutoffy 35/77, Q13+3.
- QUE24-9: [Sky dobová zpráva 15.6. o Main losu](https://www.skysports.com/tennis/news/13153658/queens-club-draw-carlos-alcaraz-could-face-brit-jack-draper-early-on-in-title-defence).
- QUE24-10: [ATP předturnajový přehled 11.6.](https://www.atptour.com/en/news/queens-2024-atp-500-history-draw-schedule), indexovaný text, otevření 403.
- QUE24-11: [LTA OOP 18.6.](https://www.lta.org.uk/49db62/siteassets/events/cinch/media/queens-order-of-play-tuesday-18-june-2024.pdf), str. 1 vizuálně, 11 R32.
- QUE24-12: [LTA OOP 19.6.](https://www.lta.org.uk/49df02/siteassets/events/cinch/media/order-of-play---wednesday-june-19.pdf), str. 1 vizuálně, 4 R16.
- QUE24-13: [LTA původní OOP 21.6.](https://www.lta.org.uk/49df51/siteassets/events/cinch/media/cinch-order-of-play-friday-21-june.pdf), str. 1 vizuálně, 4 QF.
- QUE24-14: [LTA OOP 23.6.](https://www.lta.org.uk/49e735/siteassets/events/cinch/media/cinch-championships-order-of-play---june-23-2024.pdf), str. 1 vizuálně, F 14:00; [LTA report 22.6.](https://www.lta.org.uk/fan-zone/international/hsbc-championships/news/2024/fifth-seed-tommy-paul-to-take-on-lorenzo-musetti-in-final-clash-at-the-queens-club/), dvě SF.
- QUE24-15: [Tennis Australia 17.6.](https://www.tennis.com.au/fan-zone/news/2024/06/17/hijikata-popyrin-qualify-in-singles-at-prestigious-queens-club-tournament), Q1 pokračování a Q2 walkover.
- QUE24-16: [TennisTemple úplný Q pavouk](https://en.tennistemple.com/competitions/queens/2024/draw-qualifications), struktura, nikoli vadná finanční tabulka.
- QUE24-17: [TennisCompanion historické ceny 2024](https://tenniscompanion.org/prize-money/queens-club/).
- QUE24-18: [CanalTenis ročníková finanční tabulka 2024](https://canaltenis.com/prize-money-atp-queens/), Q 9015/5060.
- QUE24-19: [LTA oznámení samostatných exhibic](https://www.lta.org.uk/fan-zone/cinch-championships/news/2024-wheelchair-and-learning-disability-exhibitions-set-to-shine-spotlight-on-disability-tennis/).
- QUE24-20: [ATP výsledkový archiv 2024](https://www.atptour.com/en/scores/results-archive?year=2024), Mallorca 23.–29.6., Eastbourne 24.–29.6. Dobový rulebook viz ROT24-15/16.

## Mallorca 2024

**Stav:** HOTOVO (nominální rozsah 9/9; H/E/Z s označenými mezerami). Rešerše 2026-11-28. Originální výsledkový ATP Q los z archivu RFET, páteční OOP a předturnajový program z 21.6. vizuálně ověřeny. Main ceny z dobových ATP Media Notes; sekundární chybné R32 nepřevzato.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Mallorca Championships presented by waterdrop | MAL24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 8994 | MAL24-4 |
| Ročník | 4. (od 2021) | MAL24-2/5 |
| Dějiště | Mallorca Country Club, Santa Ponça, Calvià, Španělsko | MAL24-5/6 |
| Povrch | venkovní tráva | MAL24-1/4/6 |
| Časové pásmo | Europe/Madrid, CEST UTC+02:00 | lokalita a datum |
| Ředitel / ATP supervisor | Tony (Toni) Nadal / Roland Herfel | MAL24-1/3 |
| Tour manager / referee | Arnau Brugues / Javier Moreno | MAL24-3 |
| Měna | EUR | MAL24-1/2 |

Nezaměňovat s Mallorca Challenger v Manacoru, WTA Mallorca Open ani s pozdějšími názvy sponzorů. Model míčů a původní detail sheet nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-27 | MAL24-7 |
| Q rank date | 2024-06-03 | MAL24-7 |
| Nominální Main deadline | 2024-05-27 18:00 CEST | odvozeno §7.03 |
| Nominální Q deadline | 2024-06-03 18:00 CEST | odvozeno §7.03 |
| Nominální LE deadline | 2024-06-20 16:00 CEST | odvozeno §7.04 |
| Main los | 2024-06-22, přesná hodina neověřena | MAL24-8 |
| Q los | před zahájením Q1 22.6., přesná hodina neověřena | MAL24-1/9 |
| Q | 2024-06-22–23, Q1 od 11:00 | MAL24-9 |
| Main | 2024-06-23–29 | MAL24-2/4/8 |
| F | 2024-06-29 nejdříve 15:00 CEST | MAL24-2/9 |

Dobový přepis 20.6. uvádí původní Main cutoff 64, Q 233; Main18 DA/3 WC/4 Q, SE 0 a LE 0; Q14 DA/2 WC. Oznámení španělské federace 18.6. nezávisle vyjmenovává 18 Main a 14 Q hráčů před dalšími změnami (MAL24-6). Q výsledkový originál uvádí last direct acceptance Ramanathan 329, ne původní cutoff 233. Main konečný cutoff z originálu nedostupný (sekundární přehled uvádí Hanfmann 85; datum stavu nejasné, nepovyšovat na originální pole). Uzávěrky odvozené z pravidel pro turnajový týden; originální acceptance lists/DS a hodiny losů chybějí.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-22 | 8 |
| Q2 | 2024-06-23 | 4 |
| R32 | 2024-06-23–25 | 12 (pozorováno 3+6+3) |
| R16 | 2024-06-25–26 | 8 (pozorováno 4+4) |
| QF | 2024-06-27 | 4 |
| SF | 2024-06-28 | 2 |
| F | 2024-06-29 | 1 |

Tištěný předturnajový program 21.6., str. 6 (MAL24-9) výslovně uvádí sobotní Q, nedělní Q/Main, Main do čtvrtka, páteční SF a sobotní F. Rozpis podle kurtů zahrnuje i doubles a některé řádky nejsou specifikovány; nepoužívat celkový počet rezervovaných slotů jako počet mužských singlů. Dobový ATP Day 1 potvrzuje čtyři postupující z nedělní Q a F nejdříve 15:00. ATP Day 2/3 potvrzují pondělní R32 a úterní R16, včetně souběhu s dokončováním prvního kola podle výsledkových zdrojů. Úplný výsledkový denní archiv (MAL24-12) vykazuje Q1 osm, Q2 čtyři, neděle tři R32, pondělí šest R32, úterý tři R32 a čtyři R16, středa čtyři R16. Označení kvalifikačních fází R2/R3 v tomto sekundárním archivu je posunuté; skutečný originál Q dokládá právě dvě kola. Denní počty jsou pozorované a představují kandidát nominálního rozložení, nikoli nezávisle potvrzený původní OOP. Okna R32/R16 potvrzují i ročníkové rozpisy AS a ATP poznámky; přesný předem publikovaný split prvních kol nezískán. Čtvrtek QF potvrzen ATP Day 5 a výsledky. Originální OOP 28.6. vydaný 27.6. 21:39 potvrzuje dvě SF na centru nejdříve v 15:30 a 18:00, před nimi doubles. Sobota F nejdříve 15:00, doubles F ve 12:00 podle předturnajového programu. Q 2 + Main 7 dní s překryvem 23.6., osm kalendářních dní, 39 nominálních uzlů. Nedělní souběh není mimořádný posun.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 | 14 |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28; Q14+2=16. Dobový přepis listiny i RFET oznámení potvrzují počáteční DA počty, ATP Day 1 uvádí osm seedů, tři WC Carreño Busta/Fognini/Thiem a čtyři Q. Úplný výsledkový Main přepis MAL24-13 potvrzuje čtyři BYE, čtyři řádné Q a LL Brouwer; sedm viditelných seedů po odstoupení seedu 7 Thompson (historická výjimka). Q originál vizuálně potvrzuje všech osm seedů, 16 hráčů, dva WC Joan Nadal a Paul Jubb (současně seed 7), jednoho Alt Casanova a čtyři čtyřčlenné sekce. Čtyři postupující Jubb/Marterer/Lestienne/Walton; další LL Brouwer není páté řádné Q místo. Main 12+8+4+2+1=27, Q8+4=12.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle MPL24-5/6 a IW24-11/14. Main dvě SE a jedna LE rezervy; nevyužité rezervy přecházejí do DA, mezistav SE 0/LE 0 není důkaz nulové rezervy. Q dva BO3 zápasy k postupu. Q body 13/7/0 přímo v originálu, přičítají se k Main bodům. ATP Day 1 explicitně uvádí 0 bodů při první prohře po BYE. WC může být zároveň seed (Jubb v Q), nejde o dodatečné místo. Pouze dvě ATP Tour akce ve stejném týdnu (Mallorca a Eastbourne); označení #NextGenATP v Media Notes neprokazuje využití NG vstupní rezervy.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 141795 |
| Finalista | 1 | 165 | 82715 |
| SF | 2 | 100 | 48620 |
| QF | 4 | 50 | 28175 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 16360 |
| R32 | 12 | 0 | 9995 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 5000 |
| Q1 prohra | 8 | 0 | 2725 |

Main primární ATP Day 1, tabulka výslovně EUR, potvrzena dobovým Tennis Infinity. Q přímo vizuálně v originálu MAL24-1. CanalTenis ročníkový přehled má nesprávně R32 7880 EUR (odlišné od primárních 9995), jeho Q částky naopak odpovídají originálu. Nominální Main 685270 EUR, Q 41800 EUR, celkem 727070 EUR. 28 Main příjemců + 12 nepostupujících Q příjemců. Financial commitment 1005340 EUR v Q originálu ani celková prize money 932135 EUR nejsou mužský singlový součet.

### 7. Kontrola a mezery

I/T/D/R/B/P doloženy, H* okna kol a pozorované denní počty odděleny od původního OOP, E* rank dates/cutoffy z přepisu, Q konečný cutoff z originálu. Z* Q originál a páteční OOP po jedné straně a předturnajový program str. 6 vizuálně ověřeny. Main originál nedostupný, ATP Notes textově (obrazové pokusy 403); Main geometrie doložena ATP a úplným sekundárním pavoukem. Originální acceptance lists/DS, hodiny obou losů, původní denní OOP časných kol, Main konečný cutoff a model míčů neověřeny; žádné smyšlené SHA-256. Kontrola kvót, 28/16, osmi nominálních seedů obou fází, čtyř BYE, čtyř postupujících, 27+12 uzlů a odměn prošla. Další Eastbourne 2024. Bez runtime změn.

### 8. Zdroje (MAL24)

- MAL24-1: [originální ATP Q los v archivu RFET](https://www.rfet.es/descargar/file-competicion-cuadros/20365_Cuadro/2024-mallorca-championships-previa.pdf), str. 1 vizuálně, Q ceny/body, seedy, WC, cutoff 329.
- MAL24-2: [ATP Preview & Day 1 23.6.2024](https://www.atptour.com/-/media/a470d8ddcaf1400896b4f88d1908a641.pdf), str. 1 text, Main odměny/body, osm seedů a tři WC; screenshot 403.
- MAL24-3: [originální OOP 28.6. v RFET](https://www.rfet.es/descargar/file-competicion-cuadros/20362_Cuadro/2024-mallorca-championships-orden-de-juego.pdf), str. 1 vizuálně.
- MAL24-4: [Tennis Europe ročníkový záznam](https://www.tenniseurope.org/calendarevent/73822/Mallorca-Championships-presented-by-Waterdrop), ATP 8994, Main 23.–29.6.; přímý ATP [Main](https://www.protennislive.com/posting/2024/8994/mds.pdf) a [Q](https://www.protennislive.com/posting/2024/8994/qs.pdf) nedostupné.
- MAL24-5: [RFET 30.6., závěrečná zpráva](https://www.rfet.es/es/noticia.html?Id=13688), čtvrtý ročník a místo.
- MAL24-6: [RFET 18.6. oznámení účastníků](https://www.rfet.es/es/noticia/el-mallorca-championships-by-waterdrop-contara-con-cinco-jugadores-en-el-top-25), 18+14 jmen a termíny.
- MAL24-7: [TennisTeen přepis Main/Q listin 20.6.](https://www.tennisteen.it/entry-list/atp/24186-atp-entry-list-24-30-giugno-2024.html), rank dates, cutoffy 64/233, Q14+2.
- MAL24-8: [ATP oznámení losu 22.6.](https://www.atptour.com/es/news/mallorca-2024-sabado-sorteo-cuadro-thiem-monfils).
- MAL24-9: [Majorca Daily Bulletin special supplement 21.6.2024](https://www.majorcadailybulletin.com/archivo/specials/2024-06-21.pdf), str. 6 vizuálně, předturnajový program a Q WC Joan Nadal.
- MAL24-10: [ATP Day 2 24.6.](https://www.atptour.com/-/media/f79f6de4aaea4d0cb7b1df5ff6f6936c.pdf), text, screenshot 403.
- MAL24-11: [ATP Day 3 25.6.](https://www.atptour.com/-/media/e1fbc323b40f419f98ed2c66555c1fca.pdf), text, screenshot 403; [ATP QF Day 5](https://www.atptour.com/-/media/f217b74104f849ee95f4ec0ea8cdf655.pdf), indexovaný text.
- MAL24-12: [Stat Pick denní výsledky 2024](https://www.statpick.ai/tournaments/tennis/mallorca/2024), pozorované denní počty; [AS první kolo](https://en.as.com/resultados/tenis/atp_mallorca/2024/calendario/primera_ronda_a/), okno 23.–25.6.
- MAL24-13: [CanalTenis Main pavouk 2024](https://canaltenis.com/cuadro-atp-mallorca-2024/), [ročníkový Main/Q přehled](https://en.wikipedia.org/wiki/2024_Mallorca_Championships_%E2%80%93_Singles), kapacita/seed/LL.
- MAL24-14: [Tennis Infinity dobový Main rozpis cen](https://tennis-infinity.com/atp/2024-mallorca-open-atp-prize-money-points-overview), [CanalTenis 2024 finanční přehled](https://canaltenis.com/prize-money-atp-mallorca/), chybné R32 7880 odmítnuto; [německý ročníkový přehled](https://de.wikipedia.org/wiki/Mallorca_Championships_2024), obě ceny Q a Main R32 souhlasí, sekundární cutoff. Dobový rulebook viz MPL24-5/6 a IW24-11/14.

## Eastbourne 2024

**Stav:** HOTOVO (nominální rozsah 9/9; E/Z s dílčími mezerami). Rešerše 2026-11-28. Oba konečné ATP losy, průběžný Main, str. 2 ATP Media Notes a všech šest Main denních programů pořadatele vizuálně ověřeny. Přesný denní Main split 5+7+8+4+2+1, Q termíny z dobové listiny a výsledkového přehledu. Main i Q finanční tabulky přímo z originálů.

### 1. Identita a místo

| Pole | Hodnota | Důkaz |
|---|---|---|
| Název | Rothesay International | EAS24-1/2/3 |
| Kategorie / ATP ID | ATP 250 / 741 | EAS24-1/2 |
| Ročník | 29. ročník mužské série podle ATP (včetně Nottinghamu) | EAS24-4 |
| Dějiště | Devonshire Park, Eastbourne, Velká Británie | EAS24-4/6 |
| Povrch | venkovní tráva | EAS24-1/2 |
| Časové pásmo | Europe/London, BST UTC+01:00 | lokalita a datum |
| Ředitel / ATP supervisor | Rebecca James / Gerry Armstrong | EAS24-7/8 |
| Tour manager / referee | Diego Pedraza / Tom Kinloch | EAS24-7/8 |
| Měna | EUR, nikoli GBP | EAS24-1/2/4 |

ATP Media Notes počítají historickou mužskou sérii Nottingham 1995–2008 a 2015–16, Eastbourne 2009–14, 2017–19 a od 2021. Nepřebírat počet ročníků ženské WTA 500 nebo výroční logo společného turnaje jako počet mužských ATP edic. Model míčů a DS nezískány.

### 2. Vstup a losování

| Událost | Datum / místní čas | Důkaz |
|---|---|---|
| Main rank date | 2024-05-27 | EAS24-5 |
| Q rank date | 2024-06-03 | EAS24-5 |
| Nominální Main deadline | 2024-05-27 17:00 BST | odvozeno §7.03 |
| Nominální Q deadline | 2024-06-03 17:00 BST | odvozeno §7.03 |
| Nominální LE deadline | 2024-06-20 15:00 BST | odvozeno §7.04 |
| Main los | nejpozději 2024-06-23 18:21 (vydání pondělního OOP), čas losu neověřen | EAS24-7 |
| Q los | před Q1 22.6., čas neověřen | EAS24-2/6 |
| Q | 2024-06-22–23 | EAS24-5/6 |
| Main | 2024-06-24–29 | EAS24-1/3/4 |
| Main LL sign-in 24.–26.6. | 10:30 BST | EAS24-7/8/9 |
| F | 2024-06-29 nejdříve 14:30 BST | EAS24-4/12 |

Dobový přepis 20.6. uvádí Main původní cutoff 53, Q 78, Main 18 DA/3 WC/4 Q/SE 0/LE 1 a Q 14 DA/2 WC. Páteční a konečný originál Main shodně uvádějí last direct acceptance Rinderknech 69, Q originál Broom 283. Jde o rozdílné časové stavy, nikoli rozporné hodnoty stejného pole. Přesné hodiny losů a originální acceptance lists/DS nezískány; uzávěrky odvozeny z pravidel, nikoli exportních časů.

### 3. Nominální harmonogram

| Kolo | Lokální okno | Nominální zápasy |
|---|---|---:|
| Q1 | 2024-06-22 | 8 |
| Q2 | 2024-06-23 | 4 |
| R32 | 2024-06-24–25 | 12 (5+7) |
| R16 | 2024-06-26 | 8 |
| QF | 2024-06-27 | 4 |
| SF | 2024-06-28 | 2 |
| F | 2024-06-29 | 1 |

Pondělní OOP vydán 23.6. 18:21, ATP singly 2 na centru + 2 kurt 1 + 1 kurt 2. Úterní OOP vydán 24.6. 18:17, ATP singly 2 na centru + 2 kurt 1 + 1 kurt 2 + 2 kurt 5. První kolo tedy 5+7, nikoli obvyklý předpoklad 4+8. Středeční OOP vydán 25.6. 18:33 a obsahuje všech osm R16 (2+2+1+3 na kurtech centre/1/2/5). Čtvrteční OOP vydán 26.6. 20:46 a obsahuje všechny čtyři QF, páteční vydán 27.6. 19:12 a obsahuje dvě SF na centru, první nejdříve 14:00. Finálový OOP vydán 28.6. 18:32: mužská F po ženské, nejdříve 14:30 BST. ATP Day 1 již potvrzuje sobotní singlové F 14:30, mužské doubles F v pátek, tedy oddělené termíny. Q1 a Q2 po 8 a 4 uzlech dle originální Q geometrie, dat listiny a ročníkového denního výsledkového archivu; původní Q OOP chybí. Denní výsledkový archiv nezávisle potvrzuje všech osm denních počtů 8/4/5/7/8/4/2/1. Q 2 + Main 6 dní bez překryvu, osm kalendářních dní a 39 nominálních uzlů. Nezapočítávat WTA, doubles ani paralelní wheelchair soutěž.

### 4. Nominální struktura

| Parametr | Main | Q |
|---|---:|---:|
| Kapacita / účastníci | 32 / 28 | 16 / 16 (4 sekce po 4) |
| DA | 18 základních, až 21 při nevyužití rezerv | 14 |
| SE | 2 rezervy | 0 |
| LE | 1 rezerva | 0 |
| WC | 3 | 2 |
| Řádné Q postupy | 4 | 4 |
| Nasazení | 8 | 8 |
| BYE | 4 (seedy 1–4) | 0 |
| Kola / zápasy | 5 / 27 | 2 / 12 |
| Formát | BO3 setů | BO3 setů |

Main 18+2+1+3+4=28, Q 14+2=16. Originální Main seed table má 8 položek, Paul (2) a Davidovich Fokina (8) jsou ve výsledkové verzi přeškrtnuti; nominálně osm seedů a čtyři BYE na 2/10/23/31. Broom jako LL převzal místo 32 po seedu 2 a tím i již existující BYE. Main čtyři Q McCabe/Shang/Nishioka/Purcell, tři WC Broady/Harris/Fearnley a čtyři LL Vukic/Searle/Hussey/Broom, které nahrazují odstoupení, nejsou čtyři nové kvalifikační kvóty. Původní úterní OOP ještě uvádí Nishikori PR a Davidoviche, výsledková verze jejich náhradníky. Q originál: všech osm seedů, dvě WC Searle a Hussey, tři Alt McCabe/Bellier/Otte, čtyři sekce po čtyřech, čtyři řádní vítězové. Main 12+8+4+2+1=27, Q 8+4=12. Skutečné obsazení po odstoupeních nepřepisuje nominální geometrii.

### 5. Dobová pravidla

ATP 2024 §7.03/7.04/7.08 B/E/7.09/7.10/7.15–18/7.20 a §9.03 dle MPL24-5/6 a IW24-11/14. Main dvě SE a jedna LE rezervy, nevyužité se vracejí DA, stav SE 0 a LE 1 v dobovém přepisu není důkaz nulové SE rezervy ani identity příjemce LE. Q dva BO3 zápasy k postupu. Q 13/7/0 přímo v originálu, přičítá se k Main bodům. ATP Media Notes str. 2 výslovně potvrzují 0 bodů za první prohru po BYE, relevantní i pro skutečného LL na BYE místě. LL/Alt nepřidávají kapacitu. Pouze dvě souběžné ATP Tour akce týdne (Mallorca, Eastbourne); označení #NextGenATP v notes není důkaz zvláštního vstupu NG.

### 6. Body a odměny (EUR)

| Výsledek | Nominální příjemci | ATP body | EUR |
|---|---:|---:|---:|
| Vítěz | 1 | 250 | 112555 |
| Finalista | 1 | 165 | 65660 |
| SF | 2 | 100 | 38610 |
| QF | 4 | 50 | 22370 |
| R16 | 8 | 25 (0 při první prohře po BYE) | 12990 |
| R32 | 12 | 0 | 7940 |
| Q postupující | 4 | 13 | 0 samostatně |
| Q2 prohra | 4 | 7 | 3970 |
| Q1 prohra | 8 | 0 | 2165 |

Main a Q tabulky vizuálně přímo v konečných originálech EAS24-1/2, Main nezávisle v průběžném originálu EAS24-3 a ATP notes str. 2. Q potvrzena i dvěma ročníkovými sekundárními tabulkami EAS24-14. Nominální Main 544115 EUR, Q 33200 EUR, celkem 577315 EUR. 28 Main příjemců + 12 nepostupujících Q příjemců. Celkových 740160 EUR v originálních záhlavích zahrnuje jiné složky než mužské singlové ceny. Skutečné individuální finanční zacházení s odstoupením a LL nepovažovat za nominální prize schedule.

### 7. Kontrola a mezery

I/T/H/D/R/B/P doloženy. H: přesné Main denní počty přímo v šesti původních předdenních OOP, Q data/listina a výsledkové potvrzení. E* originální acceptance lists/DS a hodiny losování chybějí, cutoffy z dobového přepisu a konečných originálů. Z* vizuálně zkontrolovány tři ATP losy, šest Main OOP a str. 2 ATP notes; původní předstartovní Main/Q losy, Q OOP a model míčů nezískány. SHA-256 neuvádět bez celých bajtů. Kontrola nominálních kvót, 28/16, 8/8 seedů, čtyř BYE, čtyř Q postupů, 27+12 uzlů, denních součtů a odměn prošla. Wimbledon 2024 již evidován; další řádné ATP turnaje po Wimbledonu ověřit podle dobového kalendáře. Bez runtime změn.

### 8. Zdroje (EAS24)

- EAS24-1: [originální konečný ATP Main](https://www.protennislive.com/posting/2024/741/mds.pdf), str. 1 vizuálně, vydán 29.6. 16:30:57.
- EAS24-2: [originální konečný ATP Q](https://www.protennislive.com/posting/2024/741/qs.pdf), str. 1 vizuálně, vydán 29.6. 16:30:57.
- EAS24-3: [LTA průběžný Main](https://www.lta.org.uk/49f0b5/siteassets/events/eastbourne/media/updated-atp-draw---friday.pdf), str. 1 vizuálně, vydán 27.6. 19:12:28.
- EAS24-4: [ATP Preview & Day 1 24.6. u LTA](https://www.lta.org.uk/49e95f/siteassets/events/eastbourne/media/atp-notes---eastbourne-day-1.pdf), str. 1 text (identita, 29. edice, F) a str. 2 vizuálně (ceny/body/BYE výjimka).
- EAS24-5: [TennisTeen 20.6., dobový přepis Main/Q listin](https://www.tennisteen.it/entry-list/atp/24186-atp-entry-list-24-30-giugno-2024.html), rank dates, 53/78, Q14+2, Main LE1.
- EAS24-6: [CanalTenis denní výsledky 2024](https://canaltenis.com/resultados-atp-eastbourne-2024/), Q1 22.6. osm a Q2 23.6. čtyři, Main kontrola všech dnů, Devonshire Park.
- EAS24-7: [LTA OOP 24.6.](https://www.lta.org.uk/49e467/siteassets/events/eastbourne/media/eastbourne-order-of-play--monday.pdf), str. 1 vizuálně.
- EAS24-8: [LTA OOP 25.6.](https://www.lta.org.uk/49e945/siteassets/events/eastbourne/media/eastbourne-order-of-play---tuesday.pdf), str. 1 vizuálně.
- EAS24-9: [LTA OOP 26.6.](https://www.lta.org.uk/49eb20/siteassets/events/eastbourne/media/eastbourne-order-of-play---wednesday.pdf), str. 1 vizuálně.
- EAS24-10: [LTA OOP 27.6.](https://www.lta.org.uk/49eacd/siteassets/events/eastbourne/media/reastbourne-order-of-play---thursday.pdf), str. 1 vizuálně.
- EAS24-11: [LTA OOP 28.6.](https://www.lta.org.uk/49f055/siteassets/events/eastbourne/media/eastbourne-order-of-play---friday.pdf), str. 1 vizuálně.
- EAS24-12: [LTA OOP 29.6.](https://www.lta.org.uk/49ef9a/siteassets/events/eastbourne/media/eastbourne-order-of-play---saturday.pdf), str. 1 vizuálně, F nejdříve 14:30.
- EAS24-13: [LiveTennis aktualizace 21.6.](https://www.livetennis.it/post/415176/atp-250-eastbourne-e-maiorca-entry-list-md-e-qualificazioni/), potvrzení sobotního F, 28 Main/16 Q, cutoff 53.
- EAS24-14: [TennisCompanion historické ceny](https://tenniscompanion.org/prize-money/eastbourne/), sloupec 2024 EUR; [německý ročníkový přehled](https://de.wikipedia.org/wiki/Rothesay_International_Eastbourne_2024/Herren), sekundární kontrola Q 3970/2165. Dobové ATP předpisy viz MPL24-5/6 a IW24-11/14.

## Otevřené položky k opakované kontrole

**Cílená opakovaná kontrola Lyon/Marseille 2024 (2026-11-28):** [TennisTeen 15.5.](https://www.tennisteen.it/entry-list/atp/24168-atp-entry-list-20-26-maggio-2024.html) pro Lyon obsahuje pouze Main, nikoli Q listinu. [Marseille originální listina 9.1.](https://www.open13.fr/wp-content/uploads/2024/01/Singles-Acceptance-List-open1324.pdf) je pouze Main (text dostupný, screenshot 502), potvrzuje 18 DA a tři souhrnné rezervy, neřeší Q kvótu. [TennisTeen 5.–11.2.](https://www.tennisteen.it/entry-list/atp/24110-atp-entry-list-5-11-febbraio-2024.html) je již známý typ přepisu. Výsledkové pavouky a oznámení WC neprokazují nominální výjimku. Nový rozhodný ročníkový Q doklad nezískán, oba E stavy zůstávají otevřené. U Stuttgart a 's-Hertogenbosch dobový přepis výslovně potvrzuje standardní 14+2 (STU24-7); není důkaz pro jinou edici.

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
| Acapulco 2024 | E*/P*/Z* | originální acceptance list/DS, čas losu, Q cutoff a primární Q finanční tabulka (sekundární shoda 8820/4945 USD); screenshot pořadatelských PDF nedostupný |
| Dubai 2024 | E*/P*/Z* | originální Q PDF a jeho finanční tabulka (sekundární shoda 11760/6595 USD), acceptance list/DS, Q cutoff a čas losu; původní OOP Q1/R16 nezískán |
| Santiago 2024 | P – Main prize money, blokuje HOTOVO | ATP Preview 100635/58700 vs více ročníkových zdrojů 100640/58705 USD; opakovaná kontrola 27.11. (https://www.encancha.cl/polideportivo/tenis/2024/02/26/los-millones-del-atp-de-santiago-cuanto-dinero-reparte-en-premios-el-chile-open/ a https://www.tennisexplorer.com/santiago/2024/atp-men/ potvrzují 100640, https://dewiki.de/Lexikon/Movistar_Chile_Open_2024 uvádí 100635) další primární los nepřinesla; zůstává otevřeno, Q shoda 3550/1935 USD, NG a časy losu neověřeny |
| Indian Wells 2024 | H*/E*/P*/Z* | původní denní R64/R32/R16 OOP, originální Q/DS a acceptance listy, Q čas losu a cutoff, Q odměny 14400/7800 USD sekundární shoda; body Q 20/10/0 primárně ověřeny |
| Miami 2024 | H*/E*/Z* | původní acceptance listy/DS a čas Q losu, kompletní první OOP a denní R64/R32 splity před deštěm; obě finanční tabulky primárně vizuálně ověřeny |
| Marrakech 2024 | H*/E*/R*/P*/Z* | originální Q/DS a acceptance listy, časy losů, původní OOP, skutečná alokace NG v týdnu Marrakech/Estoril/Houston; Q 3105/1695 EUR sekundární shoda 2024, 3020/1645 přesně odpovídá roku 2023, nikoli rovnocenný ročníkový doklad |
| Estoril 2024 | H*/E*/R*/Z* | původní R16 OOP před deštěm, acceptance listy/DS, časy losování a NG alokace; Main i Q finanční tabulky primárně vizuálně ověřeny |
| Houston 2024 | H*/E*/R*/P*/Z* | originální Q PDF/DS a acceptance listy, přesné časy losů a finále, úplný Main OOP a vizuální kontrola Main, NG alokace týdne Marrakech/Estoril/Houston; Q 3550/1935 USD sekundární shoda |
| Monte-Carlo 2024 | E*/Z* | originální acceptance lists/DS, přesný čas Q losu a model míčů; Main/Q finanční tabulky a všech 9 OOP primárně vizuálně ověřeny |
| Barcelona 2024 | H*/E*/R*/Z* | originální denní OOP mimo finále, acceptance lists/DS, Q rank date a časy losů, týdenní NG alokace; Main/Q ceny primárně ověřeny, chybný $ v Main vyřešen explicitním ATP EUR rozpisem |
| Munich 2024 | H*/E*/R*/P*/Z* | původní Main/Q PDF, Q finanční originál (3105/1695 EUR sekundární shoda), acceptance lists/DS, Q rank date a cutoff, hodiny losů, předdešťové OOP a týdenní Q NG alokace; plánovaný Main NG Prižmić a využití LE Fritzem doloženy |
| Bucharest 2024 | H*/E*/R*/P*/Z* | originální Q/DS a acceptance lists, Q rank date/cutoff a čas losu, původní R16 split/OOP, týdenní Q NG alokace; Main EUR ověřeno primárně, Q 3105/1695 EUR ze tří ročníkových přehledů, TennisTemple zastaralá tabulka |
| Madrid 2024 | H*/E*/Z* | původní denní splity R128/R64/R32, acceptance lists/DS, časy losů a model míčů; Main/Q ceny primární, konflikt souhrnného commitment 9249713/9017445 EUR bez vlivu na singlové ceny |
| Rome 2024 | H*/E*/P*/Z* | originální Q los/finanční tabulka (11820/6130 EUR sekundární shoda), Q acceptance list/DS, Q rank date/cutoff, časy losů, původní denní R64/R32/QF OOP; originální Main acceptance list a oba Main losy vizuálně ověřeny |
| Geneva 2024 | H*/E*/Z* | původní pre-rain OOP, originální acceptance lists/DS, Q rank date/cutoff a hodiny losů, vizuální ověření originálů; Main/Q finanční tabulky primárně textově doloženy |
| Lyon 2024 | E – nominální Q WC, blokuje HOTOVO | press kit 12 DA+4 WC proti ATP §7.08 E 14+2; dobová oznámení dvou WC a výsledkový Q přepis neprokazují nominální výjimku. Získat originální Q acceptance list/DS nebo schválení výjimky; podobný rozpor Marseille. H*/P*/Z*: původní denní OOP, Q finanční tabulka (3105/1695 EUR sekundární shoda), časy losů, originální Main/Q PDF |
| Stuttgart 2024 | H*/E*/D*/P*/Z* | originální Main/Q PDF a acceptance/DS, časy losů, konečné cutoffy, původní OOP a Q finanční originál (3940/2150 EUR sekundární shoda); 7 skutečně označených Q seedů vs 8 nominálních |
| 's-Hertogenbosch 2024 | E*/Z* | originální acceptance lists/DS, hodiny losů, model míčů, původní předstartovní Q los, vizuální kontrola bulletinů 12./15.6.; plán všech dnů a Main/Q finanční tabulky primárně doloženy |
| Halle 2024 | H*/E*/P*/Z* | původní denní OOP a důvod středečního R32, acceptance lists/DS, hodiny losů, originální Q PDF a finanční tabulka (9015/5060 EUR sekundární shoda), Q konečný cutoff; oba Main losy vizuálně ověřeny |
| Queen's 2024 | E*/P*/Z* | originální Q los/finanční tabulka (9015/5060 EUR sekundární shoda), acceptance lists/DS, Q konečný cutoff a hodiny losů, původní Q1 a čtvrteční OOP; oba Main losy a šest OOP vizuálně ověřeny |
| Mallorca 2024 | H*/E*/Z* | původní denní OOP prvních kol, acceptance lists/DS, hodiny losů, originální Main PDF a jeho cutoff, model míčů; Q originál a finanční tabulka vizuálně ověřeny, Main ceny z primárních ATP Notes |
| Eastbourne 2024 | E*/Z* | originální acceptance lists/DS, hodiny losů, původní předstartovní Main/Q a Q denní OOP, model míčů; Main/Q konečné finanční tabulky a šest Main OOP primárně vizuálně ověřeny |
