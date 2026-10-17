# Audit v84 — PR #1508–1519, 17. 10. 2026

Auditovaný `buuk`: `5dce12a07acb980882a5454485681f9eb7e5af79` po merge #1519.
Git fetch a GitHub API souhlasí. Všech 12 PR níže je mergnutých; při inventuře
nebylo otevřené PR. Před novou prací stav znovu ověřit. Dokumentační v84 je
samostatný kandidát nad tímto základem, nikoliv implementace nových produktových
pravidel a nikoliv vydaná pre-alpha.

## Co bylo skutečně zkontrolováno

Zdrojový diff od `181ef0df01f7f87411122bcb3c4afcd21b83d333` (po #1507):
55 souborů, 8 608 přidaných a 87 odstraněných řádků. Kontrola zahrnovala nové
application/domain/storage moduly, změny repository/fork/restore/health,
HTTP hranice, TS validátory, Home a extension UI, testy i browser acceptance.
Samostatný průchod hledal rozpor starého/nového horizontu, záměnu stagingu za
Save, chybějící provenance, netransakční čtení a slabší pozitivní testové důkazy.
Nejde o nový security scan ani audit všech historických PR v repozitáři.

## Inventura a finální HEAD CI

Všechny uvedené Fast CI byly dokončené success na konkrétním finálním HEAD.
Počet backendových testů je z logu jobu, nikoliv počet celé sady.

| PR | Finální HEAD (prefix) | Výsledek / hranice | Fast CI run | Backend passed |
| --- | --- | --- | --- | ---: |
| #1508 | 71a8c53cbc53 | Skutečný reviewed all-Branch horizon Save, audit/receipt, kompatibilní historický fork/restore, CS/EN | 38960478348 | 10 |
| #1509 | a585058e683f | Read-only Saved-backed Home readiness s odkazy a explicitní sporting hranicí | 38963928107 | 5 |
| #1510 | 2b7839c0d3a4 | W52/61/80 neautoritativní RankingRace point report; legacy výstup zachován | 39013621833 | 23 |
| #1511 | e357f5126950 | W-aware Official Ranking kandidát: Best N, zeros, expirace, předchůdce, Saved clock | 39014522054 | 25 |
| #1512 | 58ab3ac88761 | Datované korekce/zeros a hashová historie; přechod kandidáta přes prodloužení horizontu | 39015415844 | 19 |
| #1513 | 9fba6181dd27 | Dvě SQLite staging tabulky; rollback/restart, přesná identita HEAD; není Saved komponenta | 39017217342 | 9 |
| #1514 | 6b3c5092bf64 | Hashově ověřovaný interní staging bundle, empty-destination import a retry | 39018447625 | 8 |
| #1515 | 64626c94261c | Čtení canonical Saved Owned result/award + live parity, pouze referenční FAX | 39019505409 | 9 |
| #1516 | ba60d2e67573 | Kompletní main-only knockout evidence → atomická staging dávka; vstupy dodává caller | 39020646526 | 18 |
| #1517 | d368febecc7c | Skutečné MatchEngine-shaped rally/result witnesses; samy neprokazují Run ownership | 39021741585 | 7 |
| #1518 | f1e196e53d2e | Saved Simulation Slot/group + live parity pro původ zápasů; pouze FAX | 39022718034 | 10 |
| #1519 | 60b94cec73f5 | Spojení Saved match witness a canonical Saved point awards; stále read-only FAX kandidát | 39023724718 | 8 |

#1508: všech 10 spuštěných workflow success, včetně Shell a obou typů restart/task
akceptací. #1509: všech 9 spuštěných workflow success, včetně Shell, Saved Player
Replay a hybridních/restart scénářů. #1513: 3 workflow success (Fast CI, Boundary
Targets a Server Tasks browser). #1510–1512 a #1514–1519: pouze Fast CI; netvrdit,
že tyto PR mají vlastní úspěšnou browser akceptaci nebo že proběhla plná regrese.
Frontend joby #1508/#1509 uspěly; u čistě backendových PR jsou přeskočené.

## Dobře provedené části

- Extension používá `BEGIN IMMEDIATE`, znovu ověří celý cohort, HEAD/draft,
  transient blockers, pending commands i task/lease stavy. Před výměnou prvního
  HEAD zmrazí všechny původní branch states. Nové revize/audit/receipt jsou jeden
  commit; staré payloady a hashe nepřepisuje. Idempotentní receipt řeší response loss.
- `run_calendar_content_origin` je úzce validovaný historický základ populace,
  nikoliv globální vypnutí porovnání kalendáře. W/offset/start zůstávají stejné,
  povolené je pouze prodloužení. Fork/restore vytváří nový current-clock stav.
- Home čte Saved komponenty v jedné fyzické SQLite read transakci. Nezaměňuje
  kandidátní ranking za publikovaný a neprohlašuje podporu W52 sportu. UI kontroluje
  Run/Branch/HEAD/draft/clock a extension ignoruje zastaralé odpovědi.
- Nové rankingové typy a historie jsou verzované odděleně od starých FAX dat.
  W-expirace, Best N a zeros mají čisté výpočty a fail-closed validaci. Žádné nové
  oprávnění neplyne z toho, že caller předá sám vypočtený fingerprint.
- #1518/#1519 opravdu kontrolují Saved payload hash, úplnou sadu zápasů a live
  shodu. #1519 porovnává i účastníky, eliminaci, bodové hodnoty a publikační čas.

## Nálezy a další blokery

### A84-01 — reprodukovaná rozporná regrese testů (opravit jako první)

`tests/domain/test_calendar_official_ranking.py:254–263`, test
`test_old_calendar_immutability_and_new_extension_remains_explicit`, stále
vyžaduje chybu při větším horizontu stejné časové základny. #1512 nově a správně
umožňuje navázat další kandidát při striktním prodloužení; své pozitivní testy má
v `test_calendar_ranking_source_history.py`. Starý test z #1511 nebyl aktualizován.

Reprodukce na auditovaném `buuk`:

```sh
PYTHONPATH=src python -m pytest -o addopts='' -q \
  tests/domain/test_calendar_official_ranking.py::test_old_calendar_immutability_and_new_extension_remains_explicit \
  tests/domain/test_calendar_ranking_source_history.py::test_immutable_ranking_predecessor_can_cross_a_strict_horizon_extension
```

Výsledek **1 failed, 3 passed**. Nejde o důvod zakázat rozhodnuté prodlužování.
Opravit očekávání: nové navázání funguje, starý JSON/hash/clock zůstává beze změny;
zkrácení, změna W/offset/start a nepřilehlý týden se stále odmítají. Spustit obě
dotčené sady společně. Fast CI vybírá změněné testové moduly, a proto tuto starší
regresi v #1512 nezachytila. Není nutné kvůli tomu zapnout plnou sadu pro každý PR;
stačí odpovědně vybrat i přímo ovlivněné existující testy.

### A84-02 — hlavní nedokončená integrace (ne nová runtime chyba)

W52/W80 mají výpočty/kandidáty/staging, ale nemají dokončený kalendářově nativní
Run-owned sporting writer, oficiální publication, Saved ownership všech nových
zdrojů, restore/fork a skutečný Week/Season Transition. Staging je svázaný s přesným
Saved HEAD; po změně HEAD nemá podporovaný rebase a nesmí se automaticky povýšit
na oficiální výsledky. W61 po prodloužení mimo 50 sezon je také nadále za legacy
guardem. Completed status extension zachová; skutečné pokračování je dosud
blokované nedokončenými sporting writers. Rozšíření rozsahu není restart tasku.

### A84-03 — pozitivní důkaz #1518/#1519 má užší hranici než produktový Save

Zápasy v testech skutečně hraje produkční `execute_supported_four_player_tournament`.
Pozitivní fixture však pomocí `_resign_saved` ručně přepisuje testovou existující
Saved Revision a přepočítává její hash; #1519 ručně sestavuje canonical result/
point authority a ukládá ji přes produkční capture adapter. To je užitečný test
readeru a tamper kontrol, **není to** důkaz běžného uživatelského toku
Edit → Review → nový immutable Save → restart → replay. Produkční nové moduly
samotné historické revize nepřepisují. Nesmí se z fixture dovozovat, že je hotová
nativní W52 tournament konfigurace, původní Category/Event policy nebo publication.
Příští integrační akceptace musí vzniknout normálními produkčními commandy bez
ručního rehashování pozitivní historie a bez přímého nasazení smyšlených výsledků.

### A84-04 — provozní dokumentace zaostala za mergi (opravuje dokumentační v84)

Původní úvod CURRENT_STATE/ROADMAP stále tvrdil, že extension writer chybí,
a pak následovalo mnoho zastaralých candidate dodatků. V84 nahrazuje aktivní
souhrny stručnou aktuální mapou; stará evidence je zachovaná v Git historii a
Master 35.40. Rovněž sjednocuje dřívější slabý status historie držitelů rekordů
s již schváleným v71 a konkrétním v84 kontraktem. Žádný runtime soubor není touto
dokumentační aktualizací změněn.

## Lokální ověření tohoto auditu

- Python 3.12, společné spuštění všech 16 nových/změněných backendových modulů
  z #1508–1519: **147 testů, 146 prošlo, 1 selhal (A84-01)**. Python 3.11 CI
  výše je samostatný důkaz. Toto není plná historická regrese.
- Samostatná reprodukce A84-01: **1 failed / 3 passed**.
- Frontend: RunCalendarExtensionInspection, RunHomeReadinessPanel, RunPage:
  **21 passed**; TypeScript + production build úspěšný (jen stávající bundle warnings).
- Dalších šest přímo dotčených původních authority/transition/fork/restore modulů:
  **39 passed** (220,52 s).
- V tomto auditu nebyl nově spuštěn Chromium browser; browser důkaz výše pochází
  z ověřených CI konkrétních PR. Nebyl proveden 50-season release ani nový realism audit.

## Doporučené pokračování

Nejprve A84-01, potom jeden skutečně použitelný calendar-native sportovní řez
s produkčním Save/replay/restart místo další řady samotných provenance wrapperů.
Kompletní zadání: [PRE_ALPHA_NEXT_CHATGPT_TASK_V84_2026_10_17.md](PRE_ALPHA_NEXT_CHATGPT_TASK_V84_2026_10_17.md).
Kanonické nové produktové cíle 9.9/21.3.1/27.24 nejsou této implementační prioritě
podřízené, ale jejich existence neznamená, že už je hotové generování nebo rekordy.
