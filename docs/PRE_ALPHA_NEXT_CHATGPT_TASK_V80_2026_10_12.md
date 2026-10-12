# Next implementation handoff — Master v80 / 12 October 2026

Pokračuj přímo v programování Squash Engine pre-alpha.

Repozitář: Jasmetk0/squash-tour-beta
Integrační větev: buuk
PR merguji já. Ty nikdy nemerguj. Codex není povinný; programuj prostřednictvím dostupných nástrojů.

Před každým PR stručně vysvětli, co implementuješ a co půjde nově dělat. Potom pracuj. Jeden ucelený funkční řez na PR, base=buuk; nerozjížděj duplicitní práci k existujícímu PR. Pošli odkaz až po úspěchu všech požadovaných kontrol na skutečném finálním HEAD. Neptej se na již rozhodnuté chování; skutečné nové produktové konflikty předlož stručně.

VÝCHOZÍ STAV A AUTORITA

Audit 12. 10. 2026 ověřil buuk:
4a58192cd4f8bb7d4f9d71c76a870ec6ce3baae4
Poslední merge #1414. V době rechecku nebylo otevřené implementační PR.
Nový Master v80 konsoliduje návrhy; není tvrzením o naprogramování.

Nejdřív ověř aktuální buuk, otevřená PR a rozpracovanou práci. Načti AGENTS.md, celý pre-alpha rozsah Masteru (zejména 27.21–27.22, 31 a 35.37), constitution, CURRENT_STATE, ROADMAP, docs/PRE_ALPHA_FRONTEND_V1.md, docs/ENGINE_UX_SPEC.md, docs/PRE_ALPHA_TEST_POLICY.md a checkpoint v80. Pokud dokumentační PR v80 ještě není merged, načti jeho konkrétní dokumenty jako novější potvrzené zadání; svou implementační větev odvozuj od skutečného buuk. Nepřebírej naslepo historické candidate/next-step texty.

CO UŽ JE HOTOVÉ — NEOPAKOVAT

#1405–1414 jsou na buuk. Opravené same-value bulk locks; verzovaná ratingová interpolace pro nové Run kopie s ochranou starých v2; skutečný World/country/1000-player/SQLite restart browser; přesná reachable Saved Revision World včetně sdílených předků; Country Tournaments ze Saved Calendar; Country Records z publikovaných turnajových výsledků a skutečných národních identit; played/W/O/BYE/derby zápasové záznamy s filtry před serverovou paginací; skutečný Country Records browser/restart; all-time statistický seznam hráčů s úplnými zdrojovými součty.

Historické country roster/checkpoint vazby, obecné multi-season/historical Edition odkazy, v80 rekordové období/detail, History mapa/Compare UI a v80 rozhodovací odhady tím nejsou hotové. Tituly/finals/wins/losses/ID v #1414 jsou popsané technické řazení přehledu, ne nový Official Ranking ani finální formule sportovní úspěšnosti.

POSTUPUJ PO NÁSLEDUJÍCÍCH ŘEZECH

1. OPRAV POTVRZENÝ IDENTITY BUG A80-01

web/src/pages/runWorldCountryTournaments.ts::projectCountryTournaments hlídá event_id jen uvnitř balíčku. Dvě Calendar kopie s různými package_id/sezonami a stejným event_id same-event vrátí dvě Edition, zatímco kanonický backend resolve_viewer_tournament_history duplicitu event identity napříč balíčky odmítá.

Sjednoť validaci se skutečným kanonickým kontraktem. Nepřidávej vlastní aliasování/rebinding ID ani tichý výběr první Edition. Přidej regresi cross-package/cross-season a zachovej podporu validních různých Edition i z více sezon. UI má jasně odmítnout nejednoznačná data. Zaměřené testy a build; bez změn sporting rules.

2. SPOLEČNÝ RUN CALENDAR A DETAIL EDITION

Přestaň prohlubovat izolovanou country tabulku a propojuj Run → Tour → Calendar → Edition. Nejprve prozkoumej existující skutečné Calendar/Edition API, Six-tab detail a předchozí browser flow; rozšiř je, nevytvářej paralelní autoritu.

Kalendář: výchozí kompaktní 61-week pohled, souběžné turnaje, běžný seznam, podporované Tour/kategorie/země filtry a odkazy. Edition musí být kontextově přesná pro Run, Branch, sezonu a skutečnou Saved Revision; vyřeš současné omezení odkazů jen na sezonu 2000/2001. Nejprve skutečný scoped read kontrakt, pak navazující UI; checkpoint → Saved Revision mapuj jen při doloženém vztahu.

Edition šest záložek: Přehled, Přihlášky a účastníci, Pavouk/skupiny, Program a zápasy, Výsledky, Nastavení. Přepínač kvalifikace/hlavní části POUZE v Pavouk/skupiny; jinde hlavní část první, kvalifikace níže a scroll kotvy. Stav kalendáře není autoritativní lifecycle ani důkaz výsledku. Použij skutečné historicky účinné stavy; chybějící označ. Historické odkazy nesmějí potichu otevřít současný stav. Návrat zachová původní filtry/kontext. Rozděl backend/UI/browser do navazujících soudržných PR podle potřeby.

3. COUNTRY RECORDS PODLE v80

Nad již existujícími kanonickými výsledky/zápasy doplň konzistentní Whole history / Season / Custom period (od/do sezona+week) s cutoff právě prohlíženého stavu. Filtruj úplná ověřená data před paginací/agregací; interval musí platit pro všechny odpovídající souhrny a detaily. World data year není sportovní čas. Zachovej historické reprezentace, BYE/W/O/derby a source revision.

Tematické stručné řádky + postranní detail se zdroji a všemi shodnými držiteli; list filtry/scroll zůstanou. Nevymýšlej nové record formula, ranking historii nebo body. Začni doložitelnými již dostupnými metrikami; nedostupné poctivě označ. ID může stabilně řadit shodné hráče, nesmí předstírat vítěze sportovní shody. Pozitivní a historické browser/restart kontroly rozšiř v existujícím vhodném workflow, nepřidávej zbytečně další dlouhý job.

4. HISTORY & BRANCHES A COMPARE

Mapa actual branchí nad tabulkou reachable Saved Revisions; inspekce branchí nemění aktivní Admin Branch. Detail revize v postranním panelu se skutečným diffem/časem uložení/simulačním bodem a oddělenými akcemi Inspect / Create Branch / Compare / potvrzený Restore.

Compare je samostatná read-only A/B stránka s Differences only / All a dostupnými rozdíly/detailními podklady. Použij existující uložené stavy a Compare authority. Nevytvářej privilegiovanou Main branch, nový restore kontrakt, falešné simulované body ani odložené comparison levels. Zachovej draft/navigation guards.

5. SIMULATION — AŽ NAD FUNKČNÍMI AUTORITAMI

Propoj existující konzoli a rozhodovací služby se schváleným postranním nastavením více individuálních stop rules (OR mezi pravidly, jedna pauza + všechny shodné důvody), původní AI volbou a Apply+continue / Apply+remain paused. Pokračuj k původnímu cíli/next pause, bez implicitního Run Save.

Diagnostické procentuální odhady nesmí být mock ani LLM domněnka: musí opakovaně vyhodnocovat skutečnou interní AI nad zmrazeným kontextem s izolovaným diagnostickým RNG, bez změny původní autoritativní volby/sportovního RNG/Runu. Nejprve změř malou skutečnou dávku, determinismus, neovlivnění výsledků, bezpečný cancel a relevantní přesnost; potom automatický background průběh, uncertainty/barevná kvalita, detail a pravdivá historie včetně nepovinné nesimulační admin poznámky. Samotná neměnná zaokrouhlená procenta nejsou test přesnosti. Miliony pokusů nejsou povinné. Přesné matematické/numerické koeficienty a kalibrace jsou k testování, nevkládej je do produktu jako definitivní sportovní canon.

Pokud podporovaný rozhodovací kernel/context dosud chybí, implementuj potřebnou konkrétní autoritu jako samostatný řez; neprezentuj procenta bez podkladů. Otázka o seznamu více čekajících rozhodnutí byla PŘESKOČENÁ, není schválená. Události stejného slotu čtou společný pre-slot snapshot a UI click order nesmí změnit jejich vstupy.

PRŮŘEZOVÉ PODMÍNKY A OVĚŘENÍ

Admin-only dark, CS/EN; autorita a snapshot/hash/replay zpětná kompatibilita. Built-in FAX/Earth origins read-only, Run kopie nezávislé. Preview/Working Draft/manual Save oddělené. Čtení neposouvá simulaci, nepřidává výsledky a nenahrazuje historická data dnešními; prepared-future vrstva explicitně opt-in. Legacy 1–5 / authored 1–10 tenths / derived linear_v3 zůstanou verzovaně rozlišené; country model nevytváří innate national potential bonus.

Devět 1–99 source polí není kanonických 57 atributů/OVR 0–200. Nedomýšlej mentální taxonomii, Player/Hybrid schema ani sportovní kalibraci.

Testuj podle dopadu: relevantní pure/backend/SQLite/API, frontend contract/build, skutečný Chromium user flow pro propojené stránky; nevydávej mocks za end-to-end. U state/history změn zvlášť adversarial identity, stale/context leak, shared ancestry, restart, immutability a simultaneity review. Instalace/lockfile bez zbytečných změn. Neopakuj celý historický suite na každé kosmetice; full gate je před skutečným releasem. Žádný automatický merge.

Průběžně aktualizuj krátký aktivní CURRENT_STATE/ROADMAP. Po PR napiš co nově jde dělat, finální HEAD, skutečně provedené testy, omezení a konkrétní další řez. Cílem je použitelná pre-alpha s propojenými stránkami a následným empirickým laděním, nikoliv další nekonečné lokální statistiky.
