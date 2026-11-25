# Zadání pro ChatGPT: ATP Tour W52 od sezóny 1990

## Rozhodnutí vlastníka

Radim zvolil variantu A pro první pre-alphu. ATP Earth a skutečný historický kalendář tvoří prostředí Runu. Hráče generuje Squash Engine a přihlášky, losy, zápasy, body, žebříčky a kariéry vznikají v simulaci. Data turnajů se promítají do pevných 52 týdnů každého ročníku tak, aby kalendář odpovídal přibližnému času skutečného konání. Používej aktuální pravidla Masteru §§3.2, 9 a 31.41. Toto zadání upřesňuje pořadí práce a rozsah ATP dat.

Rozsah určuje existující [historická reference ATP Tour](ATP_TOUR_1990_2026_REFERENCE_PACKAGES.md). Zahrnuje mužskou dvouhru hlavních úrovní ATP Tour s dobovými názvy kategorií a samostatně ATP Finals a Next Gen ATP Finals tam, kde do ročníku skutečně patří. Grand Slamy, Challenger, ITF, čtyřhra, olympijské a týmové soutěže mají vlastní rozsahy. Zachovej je mimo tento balíček. Sezónu 2026 zpracuj podle přesného stavu zdrojů. Předběžný kalendář a doložené odehrání mají odlišný stav.

## Zahájení a rozsah práce

1. Ověř aktuální větev `buuk`, přečti kořenový [AGENTS.md](../AGENTS.md), [Master](../SQUASH_ENGINE_MASTER_VISION.md), [stav projektu](../CURRENT_STATE.md), [mapování na W52](ATP_EARTH_WEEK_MAPPING_V1.md) a [sportovní profily](ATP_SQUASH_SPORTING_PROFILES_V1.md). Před změnou souboru porovnej aktivní ATP PR a skutečné blob verze. #1881 už dodal Dallas 2025. #1886 a #1888 jsou při zadání rozpracované moderní profily. #1877 vlastní průvodce importem. Tyto PR přebírej jako kontext a chraň jejich změny.
2. Odvoď frontu z ročních seznamů, kanonického kalendáře a skutečně uložených sportovních profilů. Zdrojové soubory jsou v [config/reference_packages/atp_tour_1990_2026](../config/reference_packages/atp_tour_1990_2026). V současném katalogu je 2 407 datovaných výskytů. První ročník 1990 má 75 datovaných výskytů v rozsahu balíčku, z toho 74 v hlavních dobových úrovních a ATP Finals. Ověř aktuální přepočet před vykázáním počtu. Roční členství, datum konání a hratelnost sleduj odděleně.
3. Začni rokem **1990**. Uspořádej výskyty podle původního termínu a stabilního identifikátoru. Projdi každý výskyt v pořadí. Začni prvními lednovými položkami v kanonickém kalendáři, včetně identit `brisbane` a `wellington_1992`. Současný název ID nepoužívej jako důkaz dobového názvu, města ani roku konání. První dávka má obsahovat audit celého ročníku s přesnou frontou a první skutečné implementované historické položky, jakmile jsou doložené a kompatibilní.
4. Udržuj jediný aktivní Draft pro aktuální datovou dávku. Pracuj v kontrolovatelných dávkách, orientačně tři až osm turnajů, případně menší dávka u složitého formátu. Přidávej commity do stejného Draftu, dokud dává smysl kontrolovat změny spolu. Po review a owner mergi založ další dávku z čerstvého `buuk`. Pokud jiný autor upravuje společný katalog, pracuj mezitím na konkrétních historických podkladech ve vlastních ročníkových souborech a připrav verzi katalogu, až se integrace uvolní. S touto koordinací může výzkum pokračovat i v čekání na CI.
5. Zdokumentuj chybějící podklad nebo nepodporovaný formát s konkrétním důvodem a pokračuj na další výskyt. Blokované položky udržuj ve frontě. Do dalšího ročníku postup jako do další dávky po prvním průchodu celým aktuálním ročníkem, s jasně předaným seznamem neuzavřených výskytů. Ročník uzavři podle stavu každé položky, včetně konkrétního důvodu, proč případně ještě nemůže být hratelná. Po 1990 následují 1991, 1992 a dál po ročnících.

## Co doplnit ke každému turnaji

| Vrstva | Ověř a implementuj v existujícím modelu |
| --- | --- |
| Category | Dobovou kategorii v konkrétním ročníku, dobu účinnosti a bodovou tabulku pro danou sezónu. Rozliš kvalifikační a hlavní body a doložená pravidla pro BYE, skupiny nebo finálový formát. Pokud starou tabulku nevystihuje stávající typ, zapiš přesný příklad pro Work. |
| Series | Existující stabilní identitu turnaje, dobový název, hostitele a rok změny kategorie nebo lokality. Spojení dvou sérií opři o důkaz kontinuity. Nejdřív hledej existující ID a vztahy v katalogu. |
| Výskyt a Edition | Ověř konání nebo zrušení, původní data a mapování do W52. Pro doloženou a kompatibilní položku doplň verzovaný profil a jeho vazbu na přesný kalendářní výskyt. Hratelnou Edition smí vytvořit odpovídající průchod v konkrétním Runu s existujícím review a explicitním Save. |
| Sportovní formát | Dolož kapacitu hlavního losu, kvalifikaci, počet postupujících, nasazených a divokých karet, BYE, skupiny a fáze, pokud se vztahují k položce. Historický los nebo tableau použij jako zdroj geometrie a pravidel. Výběr hráčů a výsledek patří simulaci. |
| Provenance | Ulož odkazy na konkrétní doklady, datum/verzi zdroje a pro použité původní PDF SHA-256 podle existujícího vzoru. Roční přehled podporuje inventuru, detailní formát a body vyžadují odpovídající doklad. Záznam rozlišuje přesná data, doložený squashový převod a chybějící údaje. |

### Kalendář W52

- Reálné dny uchovej jako zdrojová data. Použij existující deterministické mapování krátkých akcí a vícetýdenních termínů. Když doložená kvalifikace a hlavní soutěž patří do různých týdnů, zachovej pořadí a jejich vlastní W52 týdny. Případy rovnosti, ISO W53, překryvu a neřešitelného formátu označ podle stávajících pravidel a předej s původními daty k rozhodnutí.
- Mapování ověř na kalendářní i posunuté W52 sezóně. Zdrojový ročník ATP a Run Season/Week jsou samostatné údaje. Zachovej původní datum a očekávaný týden pro konkrétní předvolbu.
- Podporovaný sportovní profil může být v datové dávce i tehdy, kdy native Q/Main ještě čeká na společnou implementaci. V auditu bude taková položka vedena jako ověřený profil s čekajícím hraním.

### Evidence po dávkách

Každá kontrolovaná položka musí mít v ročníkovém přehledu stabilní Series/výskyt, Category, původní fáze/daty a W52 týdny v dostupném rozsahu, hlavní odkazy, stav a případný zbývající krok. Rozliš nejméně:

- **Kalendář ověřen** — potvrzená položka a její zdrojové přiřazení.
- **Profil ověřen** — podložený formát a body, pravidla lze přečíst z nové uložené verze.
- **Plán ověřen** — existující schedule/draw preview prošlo se správným Saved zdrojem.
- **Odehráno a obnoveno** — skutečný veřejný HTTP/SQLite Run prošel Entry, relevantními fázemi, body, Save a znovuotevřením.
- **Zrušeno / chybí zdroj / blokováno formátem či runtime** — výslovný stav a odkaz nebo konkrétní omezení. Ve vykázaných počtech zachovej rozsah každého stavu.

Na každé dávce použij stávající verze Category/Series/Calendar/Setup a audit nástrojů. Při změně publikované verze vydej novou verzi podle pravidel adaptéru a zachovej staré uložené payloady a fingerprinty. Ověř duplicitní identitu, přesnou vazbu ročníku a profilů, odmítnutí posunutých fází a stabilitu po restartu z aktuálního skutečně uloženého Runu. Přidej cílené testy a spusť relevantní existující kontroly, například:

```bash
python scripts/audit_atp_calendar_full_roster.py --check
python scripts/audit_atp_earth_week_mapping_v1.py --check
```

V popisu Draftu uveď rozmezí zpracovaných ročníků a výskytů, počty podle stavu, odkazy, přesný head, skutečně vykonané testy a první otevřenou položku pro další chat. Předání má fungovat i po restartu chatu. Běžná kontrola stavu má pokračovat prací na dalším otevřeném výskytu.

## Hranice mezi ChatGPT a Workem

ChatGPT vlastní obsah ATP balíčků, historické zdroje, inventuru, pokrytí, nezbytné verzování zdrojových dokumentů a cílené testy importu a plánování. Work vlastní nativní průchod ATP turnajem přes Entry, Q/Main, MatchEngine, body, Save a restart. Claude samostatně pracuje na žebříčcích. Když rozhraní blokuje doložený formát, předej Workovi nejmenší reprodukovatelný výskyt, očekávaný sportovní kontrakt a existující chybovou zprávu. Použij standardní ochrany seedu, Run/branch izolace, Saved historie, sportovních pravidel a explicitního Save. Produkční engine, Saved v1/v2, FAX, CI pokrytí, timeouty a cizí rozpracované větve mají vlastní autoritu. Žádný merge, auto-merge, force-push, přímý zápis do `buuk` ani spuštění obřích běhů. Work kontroluje kandidáta, Radim rozhoduje o mergi.

## Cíl programu

Chronologicky inventarizovaný a doložený ATP Tour v letech 1990–2026, s jednoznačným stavem každého výskytu, přesným Category/Series profilem a přibližně věrným W52 termínem. Hratelnost se eviduje po skutečně provedeném ověření. Produktová brána první pre-alphy v §31.41 zůstává dvě celé ATP sezóny s explicitním Save, restartem a otevřením třetí sezóny. Dlouhodobá inventura všech ročníků se vede samostatně od této brány.
