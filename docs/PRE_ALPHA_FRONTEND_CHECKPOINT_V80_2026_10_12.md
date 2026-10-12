# Master v80 frontend / integration checkpoint — 12 October 2026


## 35.37 Integrační a frontendový audit v80 — po #1414 (12. 10. 2026)

**Auditovaný skutečný buuk:** `4a58192cd4f8bb7d4f9d71c76a870ec6ce3baae4`, merge #1414. Předchozí audit po #1404: `5419189c52bfb222c59e40b0ffa05e39d2a7176f`. Všechny nové #1405–1414 jsou merged base=buuk a jejich finální feature HEAD jsou předky auditovaného buuk (compare behind=0). Při vstupní kontrole nebylo otevřené PR. Přečteny popisy, patche, aktuální zdroje/testy, výsledky finálních workflow/jobů a vybrané skutečné browser/CI logy. Lokálně reprodukovány tři čisté frontendové projekce; neproběhl nový plný backend/frontend/browser test ani release gate.

**Předchozí navazující implementace #1385–1404:** na buuk jsou úpravy po Keep, původní Automatic baseline, stale proposal read/revalidation, country+serial names, source sloupce, bulk preview/Undo, chráněné Add Selected před rankingem v pristine Week 1, skutečné append/restart browser testy, Week-2 predecessor/clock opravy, časnější preflight, rozložení/jazyky generátoru, bulk Automatic a Run World/country history/Saved HEAD soupis. Ztracený side-branch #1394 byl obnoven #1396. Tato dostupnost neprokazuje kanonických 57 atributů/OVR, obecné in-season přidání, celý rok ani 50 sezon.

- **#1405:** same-value bulk locking opraven; požadovaných 50 u nezamčeného pole 50 nyní vytvoří zámek. Samostatný číselný/lock diff, no-op jen u stejné hodnoty a zámku; Stage → server preview → Adopt → manual Save zůstávají.
- **#1406:** nové Run World kopie s historii ratingů explicitně volí `country_rating_resolution.linear_v3`. Interpolace, zdrojové roky/hodnoty a neúplná historická evidence jsou rozlišené. Staré neoznačené v2 kopie ponechávají nearest-year a absent-field serialization; authored 1–10 po desetinách a legacy 1–5 nejsou přejmenované. Čtyři místa/half-up jsou verzovaný implementační kontrakt odvozených hodnot, nikoliv nové authorování. Population nearest-year se nemění.
- **#1407:** rozšířen existující skutečný 1 000-player Chromium/API/SQLite průchod o pozitivní copied World, country history a úplnou paginovanou country Saved Players kontrolu před/po restartu, read-only fingerprint a source-directory hash guardy. Browser používá official_fax_world kopii, nikoliv empirický důkaz Earth interpolace.
- **#1408:** přesná reachable Saved Revision World se samostatným source selector a zachovaným vlastníkem sdíleného předka; chybějící komponenty se nenahrazují živými daty. Shell browser doložil starou revizi bez Worldu a historickou kopii bez mutace. Historický soupis hráčů a propojení simulační checkpoint → Saved Revision zatím připojené nejsou.
- **#1409:** Country Tournaments čte skutečnou immutable Saved Calendar kopii, host_country z Edition, skupiny sezon a skutečné plány. Zobrazuje explicitně jen calendar status; live detail je odkazovaný jen pro současnou podporovanou sezonu 2000/2001, historické odkazy jsou vypnuté.
- **#1410:** Country Records tituly/finalisté/pořadatelství ze skutečných publikovaných turnajových výsledků a národních identit v téže reachable revizi.
- **#1411–1412:** kanonické zápasy země, oddělené played/W/O/BYE a derby účtování, serverové filtry sezony/výsledku/outcome před paginací. Souhrnné lifetime počty jsou zřetelně oddělené od filtrované tabulky.
- **#1413:** skutečný browser Country Records/filtry a předvýsledková historická Saved Revision bez dnešních výsledků; zopakováno po SQLite restartu v již existujícím browser jobu.
- **#1414:** all-time statistický přehled hráčů země podle titles/finals/played wins/fewest losses/ID; plná zdrojová sada a reconciliace, 25řádkové stránky. UI ho odlišuje od Official Rankingu. Technické řazení není nový sportovní bodový systém nebo schválená univerzální formule realističnosti.

**CI důkazy:** applicable finální HEAD workflow všech deseti PR jsou success; nepříslušné skipped joby nejsou testovým důkazem. #1405 frontend: 155 baseline + 35 changed testů/build; #1406 backend: 23 passed (+17 subtests), frontend 155+10/build. #1407 large browser run `38286410915`, job `114935743257`: `1000-PLAYER BROWSER/SQLITE ACCEPTANCE PASSED`. #1408 shell run `38288127205`, job `114941296619`: `PREALPHA_SHELL_BROWSER_PASSED`, historický World bez fallback/mutace. #1413 saved browser run `38298666483`, job `114975898948` a #1414 run `38300437067`, job `114981776249`: `SAVED PLAYER REPLAY BROWSER ACCEPTANCE PASSED`; skript má skutečné country výsledkové/filtrační/historické kontroly před/po restartu. #1414 backend job `114981831085`: 4 passed, frontend `114981831329`: 155 baseline + 83 changed testů/build. Audit četl důkazy; žádný nový dlouhý CI workflow nebyl ručně spuštěn.

**Nový reprodukovaný nález A80-01:** `web/src/pages/runWorldCountryTournaments.ts::projectCountryTournaments` hlídá event_id pouze uvnitř jednoho Calendar balíčku. Dvě verze Calendar pro 2000/2001 a 2001/2002 se stejným event_id `same-event` vrátí dva řádky místo odmítnutí; skutečný backend `resolve_viewer_tournament_history` globální duplicitní event_id odmítá. Jde o nesoulad identity/corruption guardu, ne prokázanou havárii běžného validního kalendáře. Oprava má použít stejný kanonický identity kontrakt a regresi napříč balíčky/sezonami.

**Aktivní mezery:** A80-01; country rekordové intervaly/vlastní období, tematický seznam, postranní detail a shody z v80; společná multi-season/historical Edition navigace místo odkazu jen v sezoně 0 a authoritative lifecycle; historická country roster/checkpoint vazba; mapový History/Compare frontend; v80 stop rules/diagnostické odhady jsou cíl, nikoliv hotový engine. World/country editory, intake/skupiny, kanonické atributy, obecné přidání, sezonní/50-season akceptace a empirická realističnost nadále vyžadují práci. CURRENT_STATE/ROADMAP nové aktivní záhlaví odděluje tuto evidenci od zachovaných starých candidate textů.

| PR | Final feature HEAD | Integrated | Applicable final-HEAD CI |
| --- | --- | --- | --- |
| [#1405](https://github.com/Jasmetk0/squash-tour-beta/pull/1405) | `b055ef7862fd20f2a58865c6be6df1066e6ad057` | buuk; compare behind=0 | success |
| [#1406](https://github.com/Jasmetk0/squash-tour-beta/pull/1406) | `5c2c64c7174b2cefba61c02bada787087479417f` | buuk; compare behind=0 | success |
| [#1407](https://github.com/Jasmetk0/squash-tour-beta/pull/1407) | `e7fe805c48ff0e5f809e5485315a8f0a61aaad75` | buuk; compare behind=0 | success |
| [#1408](https://github.com/Jasmetk0/squash-tour-beta/pull/1408) | `eb46562fece7e41b563db63a6a9cd828073b787c` | buuk; compare behind=0 | success |
| [#1409](https://github.com/Jasmetk0/squash-tour-beta/pull/1409) | `40c5aeb1a9ee334613606d550585f2a59539a569` | buuk; compare behind=0 | success |
| [#1410](https://github.com/Jasmetk0/squash-tour-beta/pull/1410) | `20c2a2768c2f3b31ee38b7fd0f8ae11fbf798870` | buuk; compare behind=0 | success |
| [#1411](https://github.com/Jasmetk0/squash-tour-beta/pull/1411) | `9a6aaa7a09b4018afb16512e8dcb94852dd1adf1` | buuk; compare behind=0 | success |
| [#1412](https://github.com/Jasmetk0/squash-tour-beta/pull/1412) | `dc1066b1d48ee43d1e0e6b9900baa345c69b3895` | buuk; compare behind=0 | success |
| [#1413](https://github.com/Jasmetk0/squash-tour-beta/pull/1413) | `e08931884e5f64e8bf49164a01cbc6d393ef3cd3` | buuk; compare behind=0 | success |
| [#1414](https://github.com/Jasmetk0/squash-tour-beta/pull/1414) | `42902345194742280bd97e48158629bedf9e80f9` | buuk; compare behind=0 | success |

## Approved target additions

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


## Reproduction method

Read-only Node V8 TypeScript stripping ran the actual pinned pure projections, using the repository World fixture. Legacy rating 1995 returned 4, tagged linear_v3 returned 5/interpolated/incomplete=true; same-value field 50 produced one new lock. Two Calendar copies with different seasons and the same event_id returned both IDs (A80-01). Bulk lock helper was injected only for ordering; it does not affect the new-lock identity finding. No repository implementation code was edited and no new full CI/browser suite was dispatched by this audit. The earlier #1397–1404 audit remains dated evidence; new final-head source review here covers #1405–1414.
