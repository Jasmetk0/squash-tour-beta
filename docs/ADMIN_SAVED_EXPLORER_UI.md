# Saved Explorer UI — Pre-alpha (read-only)

## Ownership and boundaries

Only `SavedTourCalendarPage`, `SavedTourEditionPage`, `SavedTourMatchDetailPage`, `SavedPlayerIdentityPage`, `SavedPlayerMatchesPanel`, `SavedPlayerMatchDetailPage` and their focused tests are modified. Other than this document there are no shared client/API, backend, validator, router, style, global language, or CI edits. Ranking #1646 and native groups #1647 are separate.

This viewer uses read-only GETs; filters, navigation, replay cursor, locale changes and Retry do not issue Save, publish, simulation or other write requests. Health is an existing *separate explicitly editable Admin panel*, not a read-only sporting explorer operation; it is neither modified nor described here as a Saved historic health snapshot.

Tour calendar and Edition use the existing legacy Run Saved Tour `50 seasons × 61 weeks` contract. Tour URL explicitly retains `runId`, `branch`, `revision`, `season`, and local `tour/category/country/view` filters. Edition also retains `tab`; match-detail return retains the same URL params. Only the actual `reachable_saved_revision` DTO can show a historical result. Historical checkpoint selection is **not** equivalent to an authenticated Saved Revision.

Player identity, career history, and player match replay use the **selected Branch Saved HEAD only**. Their API has no arbitrary revision selector; `savedHead` is a query/response identity fence, not an API payload argument. Never infer historical checkpoint support. A query error, stale/cross-revision response or in-flight Retry hides sporting authority until a newly scoped read succeeds. Auxiliary opponent-name queries fall back to verified raw IDs.

No language code is included in data query keys or API parameters. Translating presentation does not alter category/draw/status enums, fingerprint/ID/score data or schedule semantics. The Match Day number is not a date or start time. Unsupported draw/entry/attribute/lifecycle information is left unavailable, not synthesized.

## UI functionality and 24-point checklist

| # | Status | Implemented / verified behaviour |
|---|---|---|
| 1 | Nově + existovalo | CS/EN názvy filtrů, pohledů a stavů kalendáře. |
| 2 | Nově + existovalo | Invalidní kontext, výpadek čtení, Calendar Package missing a prázdná sezona / filtr jsou odlišné; konkrétní HTTP chyby formátuje stávající API helper. |
| 3 | Nově | Ruční Retry kalendáře; při isFetching zakázán, stará autorita skryta. |
| 4 | Nově | Clear filters maže jen tour/category/country; pinne Branch a revizi. |
| 5 | Již existovalo; ověřeno | URLSearchParams a encodeURIComponent uchovávají filtrování, view a přesnou revizi mezi kalendářem a Edition. |
| 6 | Nově + existovalo | Šest Edition záložek CS/EN; překládané běžné hodnoty draw fáze/entry pouze při vykreslení. |
| 7 | Nově + existovalo | aria-current, navigace ArrowLeft/Right/Home/End, focus, přepnutí jazyka nemění tab ani query key. |
| 8 | Již existovalo; ověřeno | Publikace je doložena pouze published_result a příznakem result_published, které kontroluje existující validátor. |
| 9 | Nově + existovalo | Přihlášky, hlavní/kvalifikační los, rozpis a výsledky mají prázdná upozornění; žádné odvozené výsledky. |
| 10 | Již existovalo; ověřeno | Přesná revision, tab a lokální filtry se posílají do match linku a zpět. |
| 11 | Nově | Retry Edition a skrytí dříve načteného modelu během opakovaného čtení / po error. |
| 12 | Nově + existovalo | Historický match detail ve dvou jazycích včetně draw typu. |
| 13 | Nově + existovalo | Archiv available/unavailable z uloženého DTO; chybné ID, page nebo cizí revision odmítá validSavedTourMatchDetail. |
| 14 | Nově + existovalo | Index začíná na nule, page offset floor(index/25)*25, hranice ovládacích tlačítek; vypnuto bez rámce a při fetching. |
| 15 | Nově + existovalo | Replay Retry bez změny scope, key replaye navíc obsahuje časový režim. |
| 16 | Již existovalo; ověřeno | Přehled, atributy, kariéra, zdraví v CS/EN a oddělené zprávy o nepodporovaných a prázdných datech. |
| 17 | Nově + existovalo | Profile vyžaduje skutečný Saved source a necheckpointový present režim; bez historického fallbacku. |
| 18 | Nově + existovalo | Null/missing na žebříčku je '—', skutečná nula zůstává 0; unpublished/unranked/ranked rozlišeno. |
| 19 | Nově | Retry profile a career, úspěšný scoped response vyžadován; staré/cizí výsledky se po chybě nepoužijí. |
| 20 | Nově + existovalo | Season/page state neobsahuje locale; změna Season resetuje page, změna Run/Branch/HEAD/player vynutí nový keyed timeline. |
| 21 | Nově + existovalo | Loading/error/empty season/career a explicitní Retry; Next pouze při has_more, Previous při page>0. |
| 22 | Nově + existovalo | Doplňková jména jen při totožné Saved revision, branch, Run a seznamu ID; jinak raw ID. |
| 23 | Nově + existovalo | Player replay CS/EN, Retry a kontrola offset, limit, total_rallies, has_more; na fetch skryta stará data. |
| 24 | Nově + existovalo | Query keys obsahují celý scope, responses kontrolují identitu a revizi; replay key resetuje cursor při změně Run/Branch/HEAD/player/match/time režimu. Late-response scénáře jsou pouze komponentové, nikoli real HTTP. |

## Test and acceptance evidence

- Focused mocked React Query / MemoryRouter component tests are in the six paired `*.test.tsx` files: response scope, filter/back links, first/last replay boundaries and page 2, explicit Retry, missing Saved source, unranked/zero, raw opponent-ID fallback, CS/EN rerender with unchanged reads, keyboard tab navigation and cursor isolation.
- **Executed evidence (code commit `caec95725ff71d4a077eada1ad3463bb643d455e`, GitHub Fast CI run `40520596889`):** stable critical frontend baseline **14 test files passed**, PR-selected frontend **9 test files passed**, and **TypeScript/Vite build succeeded**. CodeQL was **success** on that same code SHA (Python, JS/TS and Actions analyses). These are actual hosted component/build checks, *not* browser/HTTP/SQLite execution. This documentation-only successor commit must still be verified on its own final HEAD; see PR Checks for that evidence.
- Browser tests for Saved Group Edition, Saved Player Replay and Shell are **skipped while Draft** by the existing policy and cannot be called passed HTTP/SQLite/Chromium acceptance. No manual browser/SQLite acceptance or full pre-alpha release matrix was executed by this change; the owner-controlled Ready/manual gates remain required before merge.
- The 50×61 Saved Tour contract cannot be automatically mapped to native W52/W80; player Saved endpoints cannot read arbitrary historical revisions. The existing lifecycle authority is explicitly `unavailable`; an Edition planned on calendar is not proof of completed tournament. Some display texts remain raw technical IDs/enums by design for audit fidelity.
- **Review status:** keep Draft until focused tests, TS/Vite and CodeQL succeed on final SHA, and applicable real browser/HTTP/SQLite acceptance actually executes successfully. Never merge automatically.

## Manual exploratory follow-up

Open Run → Saved Tour Calendar on a present Branch, set a non-HEAD reachable revision, apply Tour/Category/Country and list view; inspect Edition, change tabs, open a published match then follow Back twice. Force a failed GET and use Retry without Save. In a player profile, inspect a zero-point ranked identity, season-filtered career and 25/26 rally boundary; change language without network activity. Compare an unsupported checkpoint and a foreign-HEAD response: both must fail closed. The automated tests only exercise mocked API responses, not a production backend.
