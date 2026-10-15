# Pre-alpha frontend V1 — approved Admin workflows

Decision dates: 10–15 October 2026. Status: **approved product design; not implementation evidence**.
Authority: Master v82 (calendar/range: §§3.2, 6.1, 6.9–6.12, 31.37) and preserved frontend §§27.6, 27.9, 27.17–27.22, 17.6.1–17.6.2, 9.4–9.7 and 31.30–31.35; newer explicit user decisions prevail.
Older illustrative route trees are not an alternative source of authority.

## Appearance and context

- First pre-alpha Admin has one dark theme; no Light/Dark/System selector.
- No Viewer/Admin selector in the first pre-alpha shell, including global pages.
- Active Run controls are `Run → Branch → Time`. Global pages have none of them.
- Selecting time changes viewing context only. It never advances, rewinds or regenerates simulation.
- Czech/English, readable state labels/icons, global search/Ctrl+K and attention/task access remain part of the product contract.
- Preserve future Viewer code and read-only/public-knowledge contracts without making Viewer part of the first-pre-alpha navigation.

## Global navigation and Home

Sidebar: Home, Runs, Packages, Test Lab. Application settings are separated at the bottom.
The existing collapsible/icon/hover/pin sidebar contract remains.

Startup opens neutral Squash Engine Home with no silently activated/restored Run.
Home contains three useful entries — Runs, Packages, Test Lab — each with a short description and supported factual summary.
A compact recent-Runs list appears below; opening is an explicit user action.
Exact summary fields, graphic layout and entry actions are still to be designed.
The Test Lab hub covers Match, Tournament and Player modules and needs no selected Run.

## Run navigation

After a Run opens, replace global navigation with these seven main categories:
1. Home
2. World
3. Players
4. Tour
5. Rankings & Analytics
6. Simulation
7. History & Branches

Separate **Run Management** at the bottom. It combines the earlier provisional Data and Settings categories without dropping their functions.
The Squash Engine logo returns to global Home and respects the draft/navigation safeguards.

| Category | Approved responsibility |
| --- | --- |
| World | Countries, population, country attributes, Talent Preview and expected-versus-realized intake. |
| Players | Players/prospects, profiles, attributes, development, health, training, creation and generation. |
| Tour | Seasons, calendar, systems/Tours/categories, Series/Editions, entries, draws/groups, matches and results; sporting policy and points tables. |
| Rankings & Analytics | Computed ranking and source breakdown, statistics/H2H, records, rivalries and supported analytical comparisons. |
| Simulation | Execution/controls, ranges, Week/Season Transitions, AI intervention and stop policy. Match stepping is also reachable in its detail. |
| History & Branches | Branch map/timeline, revisions/checkpoints, restoration and Compare States; separate world-event, AI-decision-history and audit subpages. |
| Run Management | Run settings, override overview, applying Packages, import/export, backups, validation and storage. |

Contextual imports also belong near their objects, such as player import in Players and country import in World.
Results/Replay remain reachable from their source matches/tournaments/players.
Task Center, Notification Center and favorites are cross-page utilities; do not conflate their data with history.

## Run Home composition

- Top: Run/branch identity and unsaved-change state.
- Full-width below: two segmented position indicators using the configured season horizon and W Season Weeks of the Run.
- Left: **Next steps / Další postup** — actual upcoming simulation events, active/paused task and link to Simulation.
- Right: **Needs attention / Vyžaduje pozornost** — concrete blockers/warnings and pending interventions, with direct links.
- Below: **World activity / Dění ve světě** — factual results, ranking/health/talent/record changes and access to the latest simulation digest.

Empty sections stay compact and factual; an empty Run is legitimate.
Unavailable/error/unsupported data must not become an invented zero or “no problems”.
Exact metrics, ordering, colors, filters and historical-versus-current progress semantics remain open.
For an initial current-state implementation, expose that boundary explicitly; do not substitute today's values for a historical snapshot.

## Players in Packages

Players are approved as part of pre-alpha Packages (Player Package scope).
This is no longer merely a possible future type.
Exact payload/schema, temporal basis, supported identity mapping/dependencies and Setup composition remain open.
Reuse preview, validation, provenance, built-in read-only protection and independent Run-copy principles.
Approval does not authorize copying fictional career history, silent identity merge or treating an unimplemented editor as complete.

## Runs and Package navigation — approved 11 October 2026

Runs uses wide rows. A simple expandable section lists actual Branch names, their supported season/week positions and Open actions.
Full Branch creation, maps, histories, comparisons and restore belong to Run → History & Branches.
Do not imply one shared simulation week for a multi-Branch Run or promote a Main/Official Branch.
Exact row metrics and the quick-open default are not settled by this simple-expansion approval.

Packages opens as a category hub, not a mandatory combined list.
Clicking a category opens its own list; All packages opens one searchable/filterable inventory.
Use supported types/content categories; do not replace existing World/Category/Series/Calendar/Setup schemas with the illustrative UI labels.
A genuinely multi-content package appears in Hybrid and every category whose data it contains, but only once in All packages.
A dependency/reference does not by itself count as contained data. Navigation classification does not settle Player/hybrid serialization.

Package detail starts on Overview and has:
- Overview: name, description, version, provenance, actual content summary.
- Contents: supported object-type sections, lists and item details.
- Validation: errors, missing dependencies and warnings, linked to affected items.

Supported actions: Apply to Run, Copy and Export; custom sources may be edited.
Built-in source editing normally creates an editable copy and preserves protected originals.

Apply to Run is a separate page with:
1. Target Run and Branch, or entry to create a new Run.
2. Contents and supported selection.
3. Before → after preview, conflicts/warnings and explicit confirmation.

The user can choose only part of the content and supported changes/values.
Recompute the exact diff and validation after selection changes; distinguish selected and excluded changes.
Confirmation is bound to the exact target, source version and reviewed selection; stale inputs require a new preview.
Unselected contents remain unchanged. No silent overwrites/deletion or identity merges.
Preserve existing Working Draft, manual Save, audit/provenance and independent-copy rules.
This approves the UI contract, not unresolved dependency mapping, conflict priorities, Player careers or payload schemas.

## Implementation sequencing and unchanged boundaries

Build the shell and two Home pages first, reusing canonical Product Run context and functioning routes.
This document does not settle every submenu, player/tournament detail, form or package serialization field. Current implementation/review evidence is separately recorded in PRE_ALPHA_FRONTEND_CHECKPOINT_2026_10_11.md.
Full Viewer, Live Ranking, advanced Forecast/Markets, deep training, mobile and court/shot animation retain their earlier deferred status.
Do not add backend sporting decisions, mutate sources or manufacture dashboard values to satisfy this layout.
Preserve creation → packages → players → calendar/entries/draw/match → ranking → Save/reopen/Replay.
CI/browser evidence must identify the actual source and covered scope; mocks are not production integration.

## Players, generation and World — approved v77

## 27.19 Players, generátor a World — schválený frontendový kontrakt v77

**[ROZHODNUTO PRO PRE-ALPHA]** Run → Players používá tabulku: jméno s odkazem na samostatný profil, sportovní země, věk ve zvoleném čase, status, OVR, Potential OVR a Ranking/NR. Nahoře jsou hledání, filtry a `Vytvořit hráče / Generovat / Import`. Další sloupce a uložené pohledy jsou volitelné. Seznam i profil respektují vybranou branch a čas; nedostupná historie se nevyplní současnými daty.

**[ROZHODNUTO PRO PRE-ALPHA]** Profil je samostatná stránka se záložkami `Přehled / Overview`, `Atributy / Attributes`, `Kariéra a výsledky / Career & Results`. Přehled obsahuje základní údaje, ranking, OVR/potenciál, stav a dostupné plánované účasti; Atributy skupiny hodnot a dostupný vývoj; Kariéra zápasy, turnaje, umístění a rankingovou historii se sezonními filtry. Jméno, země, věk a status zůstávají v hlavičce. Základ je čtecí pohled, editace se otevírá explicitně. Akce zahrnují `Upravit` a `Otevřít v Player Test Labu` v podporovaném rozsahu.

**[ROZHODNUTO PRO PRE-ALPHA]** Generátor je jediný postup podle 9.4, nikoliv dvě World/Custom stránky. Obsahuje společné podmínky, volitelné skupiny, vyhledatelné další podmínky, viditelné výjimky, shrnutí a upravitelný náhled s Ponechat/regenerací. Schválené možnosti jsou produktovým cílem; placeholder nebo legacy pool není jejich implementací.

**[ROZHODNUTO PRO PRE-ALPHA]** `World → Talent Preview & Intake` má hlavní tabulku všech zemí včetně nulových skutečných výstupů, hledání a filtry. Časový ročník je sezona dosažení 15 let, ročník narození je také uveden. Sloupce: země, nezávislý očekávaný počet, skutečně zpřístupněný počet k zvolenému weeku, očekávané/skutečné zastoupení potenciálu, průběžný/uzavřený stav. Klik otevře zemi a její skutečně zpřístupněné hráče. Průběžný intake je výslovně neúplný. Volitelná budoucí vrstva podle 9.5 je odlišena od realizace, nikdy není vydávána za již vzniklý intake.

**[ROZHODNUTO PRO PRE-ALPHA]** `World → Countries` je tabulka a samostatný profil. Sloupce: vlajka/název, region, populace ve zvoleném roce, zpřístupnění hráči podle země původu a odděleně podle současné sportovní reprezentace. Šest ratingů lze přidat jako volitelné sloupce. Hledání/filtry, Přidat zemi a Import. Profil má `Přehled`, `Populace`, `Sportovní prostředí`, `Talenty a hráči`. Trvalý ručně zadaný country-strength rating nevzniká.

**[ROZHODNUTO PRO PRE-ALPHA]** Population editor používá graf nad tabulkou roků, výběr intervalu, jednotlivé editace, vložení řádků/import a dávkový před/po diff s dopadem na generování. Chybějící rok a nejbližší použitý populační rok jsou zřetelné; dopočítaná/nahrazená hodnota se nevydává za explicitně zadanou. Existující hráči se zpětně nepřepíší, předpřipravené dotčené profily se označí.

**[ROZHODNUTO PRO PRE-ALPHA]** Dávkový country-rating editor má matici vybraných zemí × šest ratingů a výběr roku/období. Lze měnit jednotlivé buňky nebo použít hodnotu na explicitně vybranou množinu. Ukazuje před/po diff včetně časového/generačního dopadu. Interpolace a jednostranné použití nejbližšího známého ratingu se řídí 5.3/v77, explicitní editace dopočítaného roku vytvoří kotvu. Import/validace zachovávají škálu a historii.

**[AKTUALIZOVÁNO v79]** Konkrétní stručný World přehled je nyní schválen v 27.21. Přesné škály varování, matematika distribucí, numerické defaulty poměrů a algoritmy vývoje se budou kalibrovat na funkčních nástrojích. Doplnění při explicitním celkovém počtu a současné podmínky v téže skupině jsou rozhodnuté v 9.6; další otevřené případy jsou uvedené tam. Player/hybrid Package schema zůstává podle 4.9 otevřené. Nový frontendový souhlas neslouží k domýšlení těchto pravidel.


## 9.4 Jednotné generování a podmínky — schválený pre-alpha kontrakt v77

**[ROZHODNUTO PRO PRE-ALPHA]** Jedno tlačítko `Generovat / Generate` otevírá jeden generátor. Bez zásahů pracuje podle světa; zadávané podmínky postupně omezují jeho výsledek. Neexistují dvě oddělené volby World/Custom. Každé nastavení lze vrátit na `Automaticky podle světa`. Přirozený automatický roční intake pokračuje při simulaci bez nutnosti ručního schvalování každého ročníku; ruční generační náhled je jiný workflow.

**[ROZHODNUTO PRO PRE-ALPHA]** Podmínky jsou závazné. Proveditelné neobvyklé zadání dostane vysvětlené varování realističnosti; nemožné nebo rozporné zadání vrátí konkrétní konflikt. Engine podmínky tiše neignoruje, nenahrazuje jinými hodnotami ani nepředstírá statistický důkaz přirozené distribuce z ručně vynucených výsledků. Ostatní vlastnosti mají dál individuální variabilitu a společně konzistentní vztahy.

**[ROZHODNUTO PRO PRE-ALPHA]** Společné podmínky platí pro celou dávku; volitelné `Přidat skupinu` vytvoří skupinu, která je dědí. Rozpor skupinové a společné podmínky je viditelný; uživatel může vědomě vytvořit explicitní výjimku pro skupinu. V základu jsou počet, země/region, věk nebo ročník narození, potenciál a vývojový typ; `Přidat další podmínku` dovolí vyhledat podporovanou vlastnost a zadat pevnou hodnotu či rozsah, například atribut, výšku, hmotnost nebo rukovost. Podmínka OVR je cíl dosažený konzistentními atributy, nikoliv nezávisle napsaná druhá pravda o hráči.

**[ROZHODNUTO PRO PRE-ALPHA]** Interval má výchozí přirozenou podmíněnou distribuci modelu, nikoliv automaticky rovnoměrnou. U konkrétní podmínky lze výslovně zvolit rovnoměrné rozdělení či vlastní poměry. Vlastní poměry rozlišují `Pravděpodobnost` a `Přesné zastoupení`: 20 % leváků ve 100 hráčích znamená v prvním režimu náhodný výsledek, ve druhém přesně 20. Jednotlivé podmínky mohou tyto volby kombinovat. Pokud přesný poměr nemá celočíselné řešení, například 3 hráči 50:50, engine nabídne proveditelné počty k výslovnému potvrzení; nezaokrouhlí zadání tiše. Matematika společného vzorkování a kalibrace vztahů/distribucí zůstává otevřená.

**[ROZHODNUTO PRO PRE-ALPHA]** Nejprve vznikne náhled; Run se změní až výslovným přidáním/potvrzením, potom se použije běžný ruční Save. V náhledu lze ponechat hráče, přegenerovat vybrané nebo zbytek a jednotlivce upravit. Zachovají se závazné podmínky a počty. Konfliktní úprava vyžaduje opravu hráče nebo podmínky. `Ponechat v náhledu` chrání hráče jen při dalších pokusech této session a není trvalý `Locked Player`.

**[ROZHODNUTO PRO PRE-ALPHA]** Náhled obsahuje hráčskou tabulku a shrnutí podle zemí, věku, OVR/potenciálu a vývojových typů, splnění podmínek a konkrétní vysvětlená varování. Přepíná se celá dávka/jednotlivá skupina; klik na souhrnnou položku filtruje tabulku. Tam, kde model poskytuje nezávislé očekávání, je oddělené od realizace. Vynucené hodnoty jsou označené, nikoliv vydávané za přirozenou frekvenci. Náhled/commit zůstávají navázané na konkrétní Run, branch, čas, vstupy, model a seed s provenance a ochranou proti zastaralému náhledu.

**[ROZHODNUTO PRO PRE-ALPHA]** Volitelné jednoduché pojmenované předvolby uchovávají společné/skupinové podmínky, explicitní hodnoty a volby Automatic. Automatické hodnoty se vyhodnotí v cílovém světě a čase, takže stejné zadání lze porovnat mezi FAX/FIFA/ATP. Přesné zopakování výsledku vyžaduje uložené konkrétní vstupy, seed a verzi modelu; předvolba sama není totožný světový snapshot. Toto rozhodnutí neuzavírá Player Package schema.

**[ROZHODNUTO PRO PRE-ALPHA]** Staršímu generovanému hráči engine dopočítá zjednodušený vývoj do požadovaného věku: nejprve talentové předpoklady, vývojový typ a individuální vlastnosti, potom zjednodušenou aplikaci stejného vývojového modelu jako v normální simulaci. Zachová manuální podmínky a označí nepravděpodobné kombinace. Jde o označenou generační předhistorii, nikoliv důkaz odehraných zápasů, titulů, rankingové pozice nebo celých minulých sezon. Předstartovní výsledkový podklad vzniká pouze ve výslovně zvolené odpovídající variantě 9.1; plná rekurzivní simulace minulosti není povinná. Přesné křivky, startovní stavy a kalibrace zůstávají otevřené.

**[AKTUALIZOVÁNO v78]** Automatické doplnění při explicitním celkovém počtu a současné podmínky pro část téže skupiny jsou nyní rozhodnuté v 9.6. Otevřené zůstávají Automatic total s částečnými přesnými kvótami a obecné vnořené/překrývající se populační skupiny nad tento schválený případ.

## 9.5 Budoucí profily — výslovná opt-in vrstva Adminu v77

**[ROZHODNUTO PRO PRE-ALPHA; NOVĚJŠÍ VÝJIMKA Z v70]** Běžný seznam Players nadále výchozí zobrazuje pouze časově zpřístupněné hráče. Admin může zapnout `Zobrazit budoucí hráče` a uvidí všechny již skutečně vygenerované budoucí profily v dané branchi, i před 15. narozeninami nebo před narozením. Není tím povinné předgenerování všech sezon Runu ani generování dosud neexistujících dat při pouhém čtení.

**[ROZHODNUTO PRO PRE-ALPHA]** Rozlišují se `Budoucí profil — ještě nenarozen`, `Budoucí prospect — ještě nezpřístupněn` a běžný Prospect/Tour stav po zpřístupnění. Profil ukáže datum/rok-week narození, plánované zpřístupnění, původ a skutečně dostupná generační data. Nenarozený hráč nedostane smyšlený současný OVR, únavu, výsledky ani jistou budoucí kariéru. Předpřipravené hodnoty pro 15 let jsou výslovně označené svým budoucím časem. Aktivace do světa zůstává na otevření týdne 15. narozenin před prvními sloty; opt-in viditelnost toto datum neposouvá.

**[ROZHODNUTO PRO PRE-ALPHA]** Viewer, hráčská AI a veřejné projekce nesmí před zpřístupněním znát budoucí profily. Připravená budoucí vrstva nesmí být započítaná jako skutečný průběžný intake, dnešní populace hráčů nebo historie. Změna světa či generační konfigurace označí dotčené předpřipravené profily a nabídne explicitní regeneraci; neproběhne tichá retroaktivní změna existujících hráčů ani skryté vynucení nekompatibilní budoucnosti.


Country rating history contract:

**[ROZHODNUTO PRO PRE-ALPHA v77]** Chybějící rok každého ze šesti country ratingů se uvnitř dvou nejbližších známých časových bodů dopočítá lineární interpolací. Pro roky `y0 < y < y1` platí `v(y) = v0 + (v1 − v0) × (y − y0)/(y1 − y0)`. Například `1990: 4,0` a `2000: 6,0` dávají `1995: 5,0`. Mimo známý interval se použije nejbližší známá hodnota, bez extrapolovaného trendu. UI a provenance odliší explicitní vstup, interpolaci i jednostranný fallback a uvedou zdrojové roky/hodnoty. Ruční zadání v dopočítaném roce vytvoří nový explicitní kotvící bod. Rozhodnutí platí pro ratingy, nikoliv populační historii: populace nadále používá nejbližší dostupný rok podle 5.1. Autorské ratingy zůstávají `1–10` s nejvýše jedním desetinným místem; konkrétní numerická reprezentace a zaokrouhlení odvozeného mezivýsledku vyžadují explicitní verzovaný technický kontrakt, nikoliv tiché zaokrouhlení vstupu. Staré uložené snapshoty a replay se nepřepisují.

## Generation refinements — approved v78

## 9.6 Doplňky jednotného generátoru — rozhodnutí v78

**[ROZHODNUTO PRO PRE-ALPHA]** `Přidat podmínku pro část hráčů` může zadat více současně platných podmínek uvnitř stejné dávky/skupiny. Jeden hráč může splňovat více z nich a do celkového počtu hráčů se započítá jednou. Příklad: 20 českých hráčů, přesně 2 s potenciálem S a přesně 5 leváků; některý z těchto dvou může být zároveň jedním z pěti leváků. Nejde automaticky o 27 hráčů ani o disjunktní podskupiny. Náhled ukazuje, kteří hráči plní kterou podmínku; nemožná společná kombinace vrátí konkrétní konflikt. Toto rozhodnutí neuzavírá libovolně hluboký strom vnořených skupin ani sémantiku několika nezávisle zadaných překrývajících se populačních skupin.

**[ROZHODNUTO PRO PRE-ALPHA]** Je-li celkový počet výslovně zadaný a podmínky určují jen část dávky, engine automaticky doplní zbývající hráče podle cílového světa a platných společných podmínek. Příklad: celkem 100, přesně 20 CZE a přesně 10 SVK v celé dávce → 70 zbývajících hráčů z ostatních způsobilých zemí. Doplnění nesmí přidat další CZE/SVK a porušit přesné celkové kvóty. UI ukazuje `100 celkem · 30 výslovně určených · 70 automaticky`. U překrývajících se podmínek se nesčítají jejich počty bez znalosti společných členů. Pokud zbývající způsobilá populace neexistuje nebo jsou kvóty rozporné, vznikne konflikt, nikoliv tichá změna zadání.

**[OTEVŘENO]** Odvození celkového počtu při kombinaci částečných přesných kvót a celkového počtu ponechaného na Automatic nebylo tímto potvrzením rozhodnuto. Konkrétní společný solver, algoritmus podmíněné distribuce a numerická kalibrace zůstávají implementačním/kalibračním úkolem v mezích schváleného chování. UI nemá předstírat podporu dosud nepodporovaných podmínek.

**[ROZHODNUTO — DOČASNÝ DEFAULT PRO VÝVOJ PRE-ALPHA]** Nově generovaní hráči se zatím pojmenovávají názvem země a pořadovým číslem generování, například `Česko 1`, `Česko 2`, `Slovensko 1`. Číslování je nezávislé na řazení tabulky a navazuje při další dávce; Ponechat nezmění jméno již ponechaného hráče. Jde o dočasnou konvenci, která se může změnit ještě před vydáním pre-alpha. Nyní se nevyvíjejí ani nerešeršují realistické osobní jmenné databáze. Zobrazované jméno nenahrazuje stabilní `player_id`. Technická serializace do existujících jmenných polí, scope čítače, kolize a deterministické větvení se musí explicitně dokumentovat a ověřit; tento souhlas nepředepisuje nový globální identitní registr ani nepřepisuje importovaná/existující jména.

**[ROZHODNUTO PRO PRE-ALPHA]** V generačním náhledu lze u konkrétního hráče zamknout jednotlivé vlastnosti a atributy, například ručně zadanou výšku 185 cm, a regenerovat zbytek jeho profilu. Zamčená pole jsou viditelně označena a lze je jednotlivě odemknout/vrátit na Automatic. Zůstávají zachovány závazné podmínky, konzistence profilu i přesné počty. Konflikt se zobrazí a vyžaduje výslovnou opravu; engine pole tiše neodemkne ani nepřepíše. Odlišují se (a) zamčené pole náhledu, (b) Ponechat celý hráčský profil v session a (c) trvalý Locked Player. První dvě volby chrání generační návrh, nikoliv atributy po zbytek kariéry v běžné simulaci.

**[ROZHODNUTO PRO PRE-ALPHA]** Nedokončený generační návrh lze uložit a později otevřít se stejnými konkrétními hráči, podmínkami, seedem, celými ponechanými profily i jednotlivými zamčenými poli, včetně provenance cílového Runu/branche, času, vstupů a modelu. Otevření uloženého návrhu samo znovu negeneruje hráče. Uložit návrh nepřidává hráče do Runu; explicitní `Přidat do Runu` a běžný ruční Save jsou samostatné kroky. Změněný cílový svět/branch/HEAD vyvolá upozornění a novou validaci před přidáním, nikoliv tichou regeneraci. Návrh s konkrétními výsledky je odlišný od pojmenované předvolby, která uchovává zadání. Technické úložiště může využít kompatibilní existující draft/session mechanismus; tímto není schváleno Player/Hybrid Package schema.

## 27.20 Stránka generování — schválené rozložení v78

**[ROZHODNUTO PRO PRE-ALPHA]** Generátor je samostatná stránka. Vlevo má sbalitelný panel společných podmínek, skupin a předvoleb, vpravo shrnutí, konkrétní varování a hráčskou tabulku. Sbalení podmínek rozšíří prostor tabulky. Klik na hráče otevře postranní editor se zachováním pozice a kontextu seznamu; podporované individuální hodnoty a zámky se řídí 9.6. Hlavní akce jsou `Generovat`, `Uložit návrh` a `Přidat do Runu`, se zřetelným rozlišením následného ručního Save. Nezavádí se World/Custom rozdělení ani modální průvodce. Rozložení musí být použitelné i pro velkou dávku; současný počáteční limit 128 není produktový limit.

## Approved generator selection and downstream Admin pages — v79

## 9.7 Práce s celou dávkou a výběrem — rozhodnutí v79

**[ROZHODNUTO PRO PRE-ALPHA]** Hráčská tabulka generačního náhledu nabízí volbu sloupců a pamatuje uživatelovu volbu. Cílový základ je jméno, země, věk, OVR, Potential OVR, vývojový typ a session Ponechat; další dostupné sloupce zahrnují rukovost, výšku a konkrétní atributy. Ručně upravené/zamčené hodnoty mají rozpoznatelný indikátor s rozpisem po kliknutí. Jde o hodnoty skutečného modelu: legacy schopnost 1–99 se nesmí přeznačit na kanonický OVR 0–200 a chybějící vlastnosti se nevymýšlejí. Klik na hráče otevře existující postranní editor a zachová filtry, stránku a pozici seznamu. Počet na stránce, počet odpovídající filtrům a celková dávka jsou odlišeny.

**[ROZHODNUTO PRO PRE-ALPHA]** Hromadná úprava náhledu pracuje s explicitním výběrem hráčů. `Vybrat zobrazené` a `Vybrat všechny odpovídající filtru` jsou odlišné akce s počty; filtrace není sama výběrem. Pro podporovaná pole lze hromadně nastavit hodnotu, vrátit ji na Automatic a zamknout/odemknout. Před potvrzením je viditelná množina zasažených hráčů, před/po a dostupné odvozené dopady. Zachovají se závazné podmínky, přesné kvóty a konzistence profilů; konflikt vyžaduje výslovnou opravu. Celá potvrzená hromadná operace je jeden krok Undo v generační session. Nejde o rollback již uloženého Runu ani přepis historie.

**[ROZHODNUTO PRO PRE-ALPHA]** Přidání nabízí explicitní `Přidat celou dávku` a `Přidat vybrané hráče`, vždy s přesným počtem a konkrétní množinou v potvrzení. Pouhá stránka/filtr neurčuje přidávané hráče. Nevybraný zbytek zůstává v návrhu. Pokud výběr neplní závazné počty/podmínky původní dávky, uživatel musí před přidáním výslovně upravit zadání tohoto dílčího přidání a znovu je validovat; původní kvóty se nesmějí tiše ignorovat. Přidání zachovává stabilní identity a ochranu proti duplicitnímu přidání; náhled ani výběr sám Run nemění. Výslovné přidání vytvoří Working Draft změnu, běžný ruční Save následuje samostatně. Dílčí přidání není automatickým potvrzením připravenosti celého počátečního světa ke všem simulačním operacím.

**[IMPLEMENTAČNÍ HRANICE]** Schválený cíl je obecný. Současná první-cohort implementace přidává pouze celý InitialWorld a není tímto zápisem změněna na obecný append ani na částečné nahrazení autoritativního světa. Rozšiřující transakční kontrakt musí být verzovaný, zdokumentovaný a ověřený; nerozhoduje nové sportovní mechaniky.

## 27.21 Navazující Admin stránky — schválený frontendový kontrakt v79

**[ROZHODNUTO PRO PRE-ALPHA — GENERÁTOR]** Volitelné sloupce, indikace ručních zásahů, explicitní vícenásobný výběr, hromadný před/po diff a Undo i přidání celé dávky/vybraných profilů se řídí 9.7. Session Ponechat, výběr pro hromadnou akci a výběr pro přidání mají odlišný význam. Nevzniká druhý World/Custom generátor.

**[ROZHODNUTO PRO PRE-ALPHA — WORLD]** Hlavní stránka World začne stručným přehledem: identita světa, zvolený rok, původní balíček a Runové úpravy; tři kompaktní souhrny počtu zemí, světové populace a zemí s neúplnými daty. Pod nimi je vyhledatelná tabulka zemí s dostupnými populačními/ratingovými údaji pro zvolený rok a odkazem do detailu. Talent Preview zůstává samostatnou stránkou/záložkou. Neúplný populační součet musí být označen jako neúplný, nikoliv vydáván za úplnou světovou populaci. Počet zemí s mezerami je informativní a nenahrazuje operation-scoped validaci. Toto rozhodnutí nahrazuje staré OPEN pouze pro tento konkrétní přehled, nikoliv pro nevyřešené matematické ukazatele síly světa.

**[ROZHODNUTO PRO PRE-ALPHA — COUNTRY DETAIL]** Samostatný profil země rozšiřuje 27.19 na šest záložek: `Přehled / Overview`, `Populace / Population`, `Atributy země / Country Attributes`, `Hráči a talenty / Players & Talent`, `Rekordy / Records`, `Turnaje / Tournaments`. Hlavička zachová zemi a zvolený rok. Přehled ukazuje skutečné základní údaje včetně odlišných Region, Travel Region a Timezone Area; populační a ratingové grafy/tabulky/editory zachovají provenance explicitní/interpolované/fallback hodnoty a pravidla 5.1/5.3. Hráči a talenty odliší skutečné hráče, očekávání, intake a případnou opt-in budoucí vrstvu. Návrat do seznamu zachová jeho filtry a pozici.

**[ROZHODNUTO PRO PRE-ALPHA — COUNTRY RECORDS]** Rekordy čerpají ze skutečné historie a odkazují na hráče, hodnotu a čas/výsledek, kde je to dostupné. Nejlepší dosažený ranking, tituly nebo výhry jsou příklady zobrazení, nikoliv tímto stanovený úplný katalog nebo nové výpočtové formule. Sportovní rekord země respektuje historickou reprezentaci při daném výsledku a již platná pravidla 10.3 a 21.3; původ hráče a dnešní reprezentace se nezaměňují. Nedostupná historie není smyšlený rekord.

**[ROZHODNUTO PRO PRE-ALPHA — COUNTRY TOURNAMENTS]** Turnaje země výchozí zobrazí aktuální sezonu. Sezonní oddíly dovolí scroll do minulosti a v Adminu i do již skutečně naplánované budoucnosti; `Aktuální sezona` vrátí na dnešní sezonu. Budoucí plán není budoucí výsledek a prohlížení neposouvá simulaci. Umístění země se čte z konkrétní Edition, protože místo série se může mezi ročníky měnit. Klik vede do společného detailu turnajové Edition.

**[ROZHODNUTO PRO PRE-ALPHA — RUN CALENDAR]** Kalendář výchozí používá kompaktní weekový přehled W Season Weeks podle Runu s turnajovými termíny/stavy, souběžné turnaje vedle sebe. Lze přepnout na běžný vyhledatelný/řaditelný seznam. Filtry zahrnují Tour, kategorii a zemi; klik otevírá Edition. Čtení kalendáře nemění globální simulační osu ani nevytváří výsledky.

**[ROZHODNUTO PRO PRE-ALPHA — TOURNAMENT EDITION]** Samostatná stránka má hlavičku s názvem, sezonou, místem a stavem; záložky `Přehled / Overview`, `Přihlášky a účastníci / Entries & Participants`, `Pavouk/skupiny / Draw & Groups`, `Program a zápasy / Schedule & Matches`, `Výsledky / Results`, `Nastavení / Settings`. Přehled ukáže skutečný stav a další požadovaný krok; účastníci přihlášky, kvalifikanty, WC, rezervy a dostupná zdůvodnění; formátový pohled pavouk/skupiny; program odehrané i plánované zápasy; výsledky skutečné umístění/body; nastavení pravidla, velikosti a organizační okna. Návrat zachová pozici kalendáře.

**[ROZHODNUTO PRO PRE-ALPHA — QUALIFICATION / MAIN]** Přepínač `Hlavní soutěž / Kvalifikace` patří **pouze do Pavouk/skupiny**. Ve všech ostatních relevantních záložkách jsou obě části na jedné stránce: hlavní soutěž první a výraznější, kvalifikace níže. Tlačítka `Hlavní soutěž` a `Kvalifikace` jsou odkazy pro posun na daný oddíl a zůstávají při scrollování dostupná; nejsou filtrem ani druhými záložkami. Společné informace o Edition se neduplikují, odlišná nastavení jsou ve svých oddílech. Bez kvalifikace se nepotřebné ovládání nezobrazuje. Jde o jednu Edition se společnou historií a skutečnými kvalifikačními postupy, nikoliv dva nesouvisející turnaje.

**[ROZHODNUTO PRO PRE-ALPHA — MATCH DETAIL]** Klik na zápas otevře samostatnou stránku `Přehled / Overview`, `Statistiky / Statistics`, `Průběh a Replay / Course & Replay`. Přehled ukáže hráče, skóre, dostupný předzápasový stav a důvod případného nestandardního ukončení. Statistiky a průběh čerpají ze skutečně uložených dat. Návrat zachová kontext původního turnaje/seznamu.

**[ROZHODNUTO PRO PRE-ALPHA — REPLAY]** Nahoře jsou hráči, skóre při aktuálním kurzoru, game a dostupný čas; vlevo chronologický seznam rally/událostí s kliknutím pro posun, vpravo vedle sebe dostupné historické stavy obou hráčů. Fyzické/mentální ukazatele čtou skutečné zaznamenané dimenze a nerozhodují dosud otevřenou mechaniku či počet mentálních barů. Ovládání zahrnuje předchozí/další rally, skok na game, přehrát/pozastavit a rychlost; detail rally je rozbalitelný. Replay pouze čte uloženou historii, nedopočítává novou simulaci ani chybějící stavy podle dnešního modelu. Animace kurtu/úderů zůstává pozdější verzí.

**[ROZHODNUTO PRO PRE-ALPHA — SIMULATION]** Hlavní konzole má ovládání dalšího zápasu, dalšího slotu, dokončení weeku a simulace do vybraného dostupného časového bodu; režimy automaticky/se zásahy a tlačítko nastavení zastavování. Chronologicky ukáže další zápasy/organizační přechody, průběh a poslední dokončené události s odkazy. Při rozhodovací pauze zobrazí důvod, možnosti a dostupné doporučení enginu. Cílové rychlé akce zachovávají nejbližší nevyřešený slot, souběžnost, explicitní Week/Season Transition a všechny skutečné blokátory podle kapitol 6 a 31.27. Změna přehrávacího UI není sportovní autorita.

**[ROZHODNUTO PRO PRE-ALPHA — RANKINGS]** Stránka má `Official Ranking` a `Finals Race`, každou s vlastními historicky platnými pravidly. Zobrazuje pořadí, posun oproti skutečnému předchozímu snapshotu, jméno, zemi a body; sezonu a rankingový week lze zvolit v dostupné uložené historii. Jméno otevře profil, **klik na body otevře postranní rozpis** započtených/nezapočtených výsledků, důvodů vyřazení a příslušné expirace, pokud ji daná pravidla mají. Neexistující předchozí snapshot neznamená nulový posun a budoucí nepřidělené body nejsou historie. Nevzniká nový bodový systém ani Live Ranking; ten zůstává mimo první pre-alpha.

**[HRANICE CÍLE A IMPLEMENTACE]** Tato konkrétní UI rozhodnutí jsou závazným cílem pro pre-alpha. Neprohlašují současné produkční služby za úplné, nedomýšlejí Player/Hybrid Package schema, numerickou kalibraci, nové historické výsledky ani zbývající obecné submenu. Nepodporované hodnoty/operace mají být zřetelně nedostupné s důvodem.

## Selected frontend decisions — Master v80 (12 October 2026)

Master §§27.22 and 31.35 add approved pre-alpha target behavior; §35.37 and the v80 checkpoint contain implementation evidence, not a release certificate.

- Country Records: thematic groups, brief rows, side detail with actual value/time/source links and all tied holders. Whole history / Season / Custom period (season+week bounds), default through the viewed simulation time; show scope in list/detail and preserve filters/scroll. World data year is a different axis. Record examples do not finalize the catalog/formulas.
- History & Branches: map above the selected branch's actual Saved Revision table. Inspection does not activate an Admin Branch. Saved Revision side detail separates inspect / create branch / compare / confirmed restore. Compare is a separate read-only A/B page with Differences only / All and actual supported difference details; deferred comparison levels remain deferred.
- Simulation stop settings: side panel with master intervention switch and several individually editable/enabled rules, matching any active rule (OR across rules). Multiple matching rules for one decision point yield one pause with every matching reason.
- Decision choice: manual choice or original authoritative AI choice, followed by Apply and continue to original target/next pause, or Apply and remain paused to inspect. This is not automatic Run Save and does not reroll the AI choice.
- Diagnostic AI-choice percentages should appear automatically where supported, measured for performance and allowed to update in the background while the panel remains usable. Show progress, percentages beside choices and an expandable estimate detail (sample count, duration, uncertainty). Repeated evaluation uses the exact frozen decision inputs and information legitimately known to that internal AI, isolated diagnostic RNG and model provenance; it cannot advance/mutate the Run or consume/reseed sporting RNG. Deterministic choices may honestly be 100%.
- Red/orange/green estimate-quality labels reflect sampling precision, not empirical realism or blocking validation. Convergence of unrounded estimates, uncertainty and independent verification govern stopping; time/sample limits, user stop and applying the decision also terminate. A missed precision target stays visibly incomplete. Refine estimate may continue over the same context.
- Exact statistical methodology, adaptive-stopping coverage, counts/minima/thresholds and performance calibration remain for implementation/tests; 10/20 million were examples, not mandatory limits. Unsupported estimates remain honestly unavailable or existing relative scores, not invented percentages.
- Decision history stores the then-available estimate/status and actual AI/Admin choice without retroactive replacement. An optional admin note is separate from AI reasons and has no simulation effect.
- The user skipped the question about a list of multiple waiting decisions: do not turn it into approved behavior. Preserve all existing pre-slot snapshot/simultaneity semantics; presenting decisions sequentially must not make same-slot inputs order-dependent.

## Run calendar and horizon — approved v82 target (15 October 2026)

Optional creation/settings fields: fixed W weeks per year/season, Season Week 1 → Year Week offset, start year, and either last season or season count (synchronized). Preview exact first/last season and year/week endpoints. Earth defaults to 52, FAX to 61 with offset 37; 50 FAX seasons can remain a preset. Name-only empty creation remains possible with defaults.

After the first week starts, structural calendar/time basis is locked. Only horizon extension is supported, including after completion, shared by all Branches without moving any timeline or changing/starting existing tasks. The operator can always choose a shorter simulation goal. Before-start edits validate already prepared dependencies; never silently reinterpret them.

Primary Admin time: season + Season Week; secondary: year + Year Week. Example Earth W=52, offset=35: Season 2000/2001 Week 19 = Year 2001 Week 1. Avoid identical duplicate labels when season equals year; preserve existing Viewer preferences separately. Calendar/planning can switch yearly/seasonal views of the same point.

Import preview lists incompatible term/dependency changes with source → target values. The operator corrects or excludes affected tournaments; independent compatible selections can proceed. A FAX Week 58 is invalid in a 52-week target, never silently clamped/wrapped/rescaled. Existing Runs and historical views retain their versioned semantics. These are product targets; the current 61-week UI is not yet proof of v82 implementation.
