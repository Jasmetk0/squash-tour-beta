# Historické ATP a Grand Slamy ve Squash Enginu

## Rozhodnutí vlastníka z 27. listopadu 2026

Tento postup platí pro ChatGPT, Claude, Codex i jiné AI pracující na historických balíčcích. Nejprve dokonči rešerši historických podkladů od roku 1990. Potom předkládej převod do enginu **po jedné edici**. Každý konkrétní převod musí výslovně schválit Radim, vlastník projektu. Nové rozhodnutí upravuje pořadí práce ve starších ATP zadáních. Produktový rozsah a herní pravidla vycházejí z [Masteru, zejména §4.12, §9, §31.41 a §36](../SQUASH_ENGINE_MASTER_VISION.md).

Edice je jedna série v jednom zdrojovém roce. Rozsah zahrnuje mužskou dvouhru hlavních úrovní ATP Tour, ATP Finals a Next Gen ATP Finals v příslušných letech a všechny čtyři Grand Slamy. ATP Tour a Grand Slamy mají vlastní zdrojové balíčky. Challenger, nižší okruh ITF, čtyřhra, olympijské a týmové soutěže a samostatný Grand Slam Cup jsou mimo rozsah. Pro zrušené, neúplné a budoucí ročníky eviduj stav doložený zdroji.

## 1. Rešerše původních tenisových dat

- Ověř aktuální `buuk`, [AGENTS.md](../AGENTS.md), [stav projektu](../CURRENT_STATE.md), [historickou referenci ATP Tour](ATP_TOUR_1990_2026_REFERENCE_PACKAGES.md) a skutečné commity a soubory aktivních PR. Odvoď inventuru z ročních seznamů, stabilních identit Category/Series a kalendářních výskytů. Současný název stabilního ID sám nedokládá dobový název ani místo.
- Hlavní chronologická řada začíná sezonou 1990. Dílčí rešerše mohou probíhat souběžně v různých ročnících. Používej [historický registr reálného tenisu](https://github.com/Jasmetk0/squash-tour-beta/pull/1919) jako společný přehled pokrytí a před novou rešerší dohledávej existující zdroje i rozpracované edice. PR mohou mít rozdílné dílčí výstupy pro stejný rok. Před převodem slaď zdrojová tvrzení podle stejného stabilního výskytu a eviduj rozpory.
- Pro každou edici hledej dobové ATP/ATP Tour podklady, oficiální dokumenty pořadatele, Grand Slamu či ITF a příslušná pravidla. Zaznamenej konkrétní zdroj, vydání nebo stránku, co dokládá, a mezery. Sekundární podklady označ podle jejich skutečné úrovně. Když úplný originál potřebný pro platný produkční profil chybí, zapiš překážku. SHA-256 může pocházet pouze z úplných bajtů dokumentu.

| Oblast | Záznam pro každou edici |
| --- | --- |
| Identita | Dobová kategorie, série a název, ročník, místo, povrch a místní časové pásmo |
| Termíny | Plánovaný začátek a konec kvalifikace a hlavní soutěže, den nebo interval každého kola, plánované překryvy a přestávky |
| Vstup a los | Kapacita a nominální kvóty hlavní soutěže i kvalifikace, nasazení, WC, přímé vstupy, postupová místa, BYE, skupiny a pravidla náhrad; zveřejněné termíny přihlášek a losování |
| Pravidla | Dobový formát zápasů, body a odměny po fázích včetně kvalifikace a relevantní výjimky |
| Provenience | Odkazy, datum/verze, podložené hodnoty, rozpory, nepublikované údaje a zbývající překážky |

**Pro budoucí převod je referencí plán konkrétní edice.** Kapacita 32 zůstává 32, i když se nakonec dostavilo 31 hráčů. Počet přidělených WC se odlišuje od počtu využitých WC. Dva zápasy přesunuté kvůli dešti nemění plánovaný den kola. Pokud původní program rozložil kolo na dva dny, uchovej celé plánované okno. Přesný počet zápasů na jednotlivé dny zapisuj, když jej dokládá zdroj. Skutečné mimořádné změny uchovej odděleně jako kontext. Jména, skóre ani skuteční vítězové nejsou součástí simulovaných edic.

Pokrytí znamená doložený nominální rozsah podle tabulky, s výslovným stavem nekonaných, neaplikovatelných a veřejně nedoložitelných údajů. Doložený interval kola může být dostatečným podkladem i při nepublikovaných časech jednotlivých zápasů. Otevřený údaj, který mění formát nebo plán edice, se vede jako mezera. Přepočítej pokrytí z aktuálních souborů. Kalendářní položka sama uzavírá jen identitu a kalendář, který skutečně dokládá.

## 2. Návrh převodu jedné edice

Po dokončení zdrojové etapy vezmi jednu edici, počínaje od roku 1990. Rutinní převod a datovou práci dělej v běžných ChatGPT chatech bez čerpání Codex kreditů. Složité společné formáty a změny enginu koordinuje Work podle Masteru §36.

Předlož vlastníkovi jeden kontrolovatelný návrh se stabilním ID edice a konkrétními verzemi zdrojů. U každého převáděného údaje ukaž **dobový plán → hodnotu pro engine → odůvodnění volby**. Rozepiš Category/Series/Edition, kvalifikaci a hlavní soutěž, W52 týdny a dny kol, počty hráčů, WC, nasazení, BYE, postupy, bodování a všechny squashové adaptace. Použij [stávající W52 pravidla](ATP_EARTH_WEEK_MAPPING_V1.md) a [kontrakt sportovních profilů](ATP_SQUASH_SPORTING_PROFILES_V1.md). Zdrojový rok a datum ponech vedle výsledné Run Season/Week. Výslovně ukaž nejasnosti kolem překryvů, hranic sezon, ISO W53 a formátů, které engine neumí vyjádřit. Zkušební projekce ve výzkumných souborech je diagnostika. Produkční sloty a adaptace získají platnost schválením podle další části.

## 3. Výslovné schválení vlastníkem

Před zapsáním edice do produkčního katalogu nebo balíčku musí Radim výslovně potvrdit její konkrétní návrh, i když se všechny hodnoty převezmou beze změny. Zaznamenej edici, odkaz na potvrzený návrh nebo jeho revizi, datum a kde rozhodnutí padlo. Příkaz k pokračování ve výzkumu, zelené CI, testovací fixture nebo souhlas s jinou edicí schválení nenahrazují. Změna schváleného formátu, slotů nebo bodů vyžaduje nové potvrzení změny.

Dosavadní výzkumné návrhy a testovací profily zůstávají podklady. Při práci s verzemi už publikovaných balíčků zachovej historické payloady, identity, fingerprinty a Saved replay. Společné technické testy nad nimi lze dál používat jako regresi.

## 4. Implementace a ověření

Po potvrzení edice uplatni schválený návrh ve stávajícím verzovaném modelu Category/Series/Calendar/Setup. Pracuj v kontrolovatelných Draft dávkách a před úpravou sdíleného katalogu zkontroluj ostatní otevřené PR. Více předem schválených edic smí být v jedné datové dávce. Každý souhlas zůstává dohledatelný k jednotlivé edici. Work vlastní koordinaci sdíleného runtime a integrační ověření. Radim rozhoduje o merge.

Ověř stabilní identitu, vazbu profilu na skutečný výskyt, správný W52 kalendář včetně podporovaného posunu, Preview, Confirm, explicitní Save a plánování z připnutého Saved zdroje po restartu. Pro stav **odehráno a obnoveno** musí skutečný HTTP/SQLite Run projít Entry, kvalifikací podle formátu, hlavní soutěží, publikací bodů, Save a opětovným otevřením. Testovací kandidáty a produkční ověření vykazuj podle jejich skutečného rozsahu. Používej cílené testy a příslušné existující audity.

```bash
PYTHONPATH=src python -m scripts.audit_atp_calendar_full_roster --check
PYTHONPATH=src python -m scripts.audit_atp_earth_week_mapping_v1 --check
```

V přehledu a PR dolož zvlášť **inventarizováno**, **zdrojový nominální rozsah doložen**, **převod navržen**, **převod schválen**, **profil importován**, **plán ověřen** a **odehráno a obnoveno**. Uveď přesný commit, běhy kontrol a konkrétní překážky. Zrušenou edici eviduj jako nekonanou. Pokud runtime nepodporuje doložený formát, předej Workovi nejmenší konkrétní případ, zdroj a očekávaný kontrakt.

## Návaznost na historický Run

Cílový integrační scénář je souvislý ATP Earth W52 Run od roku 1990. Začíná uložením připnutých balíčků a vznikem vygenerované počáteční populace. Postupně navazuje odehrání podporovaných edic, celý ročník 1990, Save/restart, sezona 1991 a otevření W01 1992 s rankingem, historií a další generací hráčů. K úplné akceptaci §31.41 patří všech osm Grand Slamů obou sezon. První technické průchody a průběžná měření atributů, populace a síly zemí mají vlastní evidenci pokrytí a výsledků. Historické seznamy ani nouzové testovací profily se nevykazují jako plně odehraná sezona.
