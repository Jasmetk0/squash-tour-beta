# Pokračuj přímo v programování Squash Engine — Master v84

Repo: `Jasmetk0/squash-tour-beta`; integrační větev `buuk`.
PR merguje pouze uživatel. Nikdy nemerguj. Programuj přímo dostupnými nástroji
běžného ChatGPT. Nespouštěj placený Codex ani další placené agenty; při chybějících
nástrojích to řekni otevřeně. Nezastavuj se u plánu nebo dalšího promptu.

## 1. Čerstvý stav a souběh

Ověř merge dokumentačního Master v84 PR, aktuální `buuk`, otevřená PR a případnou
již rozpracovanou nativní calendar sporting práci. Auditovaný základ je
`5dce12a07acb980882a5454485681f9eb7e5af79` po #1519, nikoliv trvalý pin.
Nekopíruj paralelně práci jiného chatu; pokračuj v existující větvi/PR, pokud
pokrývá stejný cíl. Nevyžaduj znovu rozhodnutí, která už Master obsahuje.

Načti AGENTS.md, CURRENT_STATE.md, ROADMAP.md, docs/PRE_ALPHA_TEST_POLICY.md,
celý audit docs/PRE_ALPHA_CHECKPOINT_V84_2026_10_17.md a dotčené Master kapitoly
6, 7, 9.8–9.9, 21.3.1, 27.24, 31.37–31.39 a 35.41. Podle změny dočti doménové
kontrakty a zdrojové moduly, nejen souhrny. Celý pre-alpha rozsah zůstává platný.

## 2. První malá, konkrétní oprava — A84-01

Společně spusť test_calendar_official_ranking.py a test_calendar_ranking_source_history.py.
Na auditovaném základu selhává
`test_old_calendar_immutability_and_new_extension_remains_explicit`: požaduje
odmítnutí vyššího horizontu, zatímco #1512 správně povoluje přilehlého následníka
při stejném W/offset/start a striktně prodlouženém horizontu.

Aktualizuj test podle platného kontraktu. Ověř nezměněný původní JSON/hash/clock,
nový previous_fingerprint a odmítnutí zkrácení, změny časové základny a nepřilehlého
týdne. Nevracej správnou implementaci, nemaž test a nezměkčuj ochranu starých dat.
Opravu lze zahrnout do dalšího uceleného PR nebo předat jako malý samostatný fix,
pokud má následný sportovní řez trvat déle. Před dalším navázáním ověř owner merge.

## 3. Hlavní cíl — skutečný nativní sport podle Run kalendáře

Další významný výsledek má být provozní, ne další samostatný read-only wrapper:
Admin na skutečném vlastním W52 Runu připraví podporovaný malý main-only pavouk,
odehraje přes MatchEngine semifinále/finale, získá skutečné Run-owned výsledky
a body z uložené konfigurace, ručně uloží nový immutable stav a po restartu
otevře přesný výsledek/replay. Navazující řez publikuje oficiální ranking při
skutečném Week Transition do Week 2 a potom prokáže hranici Season Week W → 1.

Použij společný RunCalendar, včetně W80 a konfigurovaného startu/offsetu. Nesmíš
odstranit legacy guard a začít předávat W52 data do starých 61-week ordinals.
Vytrasuj skutečnou autoritu od Run/Branch Saved HEAD přes population/lifecycle/
Health, sporting checkpoint, SimulationSlot/Group, frozen match input a rally
výsledky až po canonical tournament result/award, ranking a ruční Save.

Technické schema/migraci navrhni autonomně, verzovaně a s konkrétní kompatibilitou.
Staré FAX typy, JSON, fingerprints a historické revize musí zůstat významově stejné.
Normální nový příkaz přidává novou revizi; žádné re-signování starých revizí.
Částečnou podporu popiš pravdivě a guardy na nemigrovaných operacích ponech.
Neopakuj dalších deset PR, které přidávají jen alternativní kandidátní provenance
vrstvy, aniž se posune normální použití enginu.

### Rozumné rozdělení do dalších PR

1. **Kalendářově nativní skutečný zápas/turnaj + Save/replay.** Backend authority,
   persistence a potřebné CS/EN ovládání tvoří jeden použitelný řez. Není-li
   bez další migrace možné dokončit celý turnaj, první řez může být skutečný
   samostatný Run-owned zápas dvou uložených hráčů s plným Save/restart/replay;
   ne samotný nový model nebo diagnostické API. Úzký podporovaný formát je v pořádku,
   nesmí však tvrdit obecnou podporu kvalifikace/skupin/abnormal outcomes.
2. **Skutečná bodová publikace + Week/Season Transition.** Zdroj původní Category/
   Edition point policy, její efektivní verze, tournament result a award musí být
   ověřené a svázané v jedné authority linii. Nové rankingové sources musí být
   skutečně součástí Saved capture/restore/fork, nikoliv pouze staging tabulek
   #1513/#1514. Přechod na další týden nesmí přeskočit povinný lifecycle/development/
   recovery ani použít budoucí data. Roční věk/vývoj používá 1/W; týdenní lhůty se
   nepřepočítávají plošně. Nezaváděj finální realistické koeficienty bez testování.
3. **Integrace s řízenou Full Simulation a naplněný průchod.** Až jsou skutečné
   writer/transition cesty migrované, připoj je k existujícím durable tasks,
   zmrazeným cílům a explicitní obnově. Ověř W52, W80, prodloužený W61, rollover,
   Completed → explicitní novou práci, bez oživování terminálních tasků.

Toto je posloupnost funkčních cílů, nikoliv zákaz technických pomocných změn uvnitř
jednoho PR. Kód můžeš průběžně checkpointovat na stejné větvi. Nepokračuj na
nemergnutém překrývajícím se základu bez jasné návaznosti.

## 4. Požadovaný důkaz

- Skutečná SQLite/FastAPI a produkční příkazy; alespoň jeden normální průchod
  přes CS/EN Admin ve stávající Chromium akceptaci. Nevymýšlej novou sadu téměř
  duplicitních workflow. Pozitivní fixture nesmí ručně přepisovat Saved JSON/hash
  nebo vyrábět výsledky místo odehrání; adversarial tamper fixture je jiná věc.
- Deterministický MatchEngine/rally log, stejný pre-slot snapshot pro současné
  zápasy, jediný správný winner-fed final, skutečné publication časy a body.
- Review/confirm/manual Save přesná identita; response-loss retry, stale HEAD,
  cross-Run/Branch, dvojitý příkaz, konflikt a injected partial failure s rollback.
- Cold restart, historické čtení starého i nového Saved stavu, restore/fork tam,
  kde je podporuje nový řez. Nedokončená podpora je konkrétní blocker s důvodem.
- Ověř přímo ovlivněné starší testy společně s novými (viz A84-01). Plnou sadu
  ponech release gate podle politiky; nezaměňuj green PR subset za plný release.
- Samostatný adversarial review průchod zaměřený na časové jednotky, source/HEAD
  provenance, vlastnictví snapshotů, transakční hranice, retry a obnovitelnost.

Před PR stručně řekni, co nově půjde dělat. Aktualizuj stručný CURRENT_STATE,
ROADMAP a relevantní kontrakt, bez hromadění neaktuálních candidate dodatků.
Předej odkaz až když všechny požadované kontroly na finálním HEAD uspějí; napiš
konkrétní otestovaný výsledek, limity a další krok. Sám nikdy nemerguj.

## 5. Co teď nevymýšlet

Nedělej souběžně velké redesigny Records/generátoru, další Earth country research
ani Official Run obsah. Nové v84 dohody jsou canon pro pozdější odpovídající práci,
ne povolení přidávat fiktivní historii či národnostní vrozené bonusy. Initial-rule
inheritance do budoucího intake je výslovně odložená. Numerické odchylky,
retirement/growth realističnost, kompletní katalog rekordů a přesný layout se
kalibrují/testují na funkčním enginu. Žádné nepožadované placené modely.
