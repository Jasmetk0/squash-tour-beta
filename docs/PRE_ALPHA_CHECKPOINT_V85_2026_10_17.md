# Audit a navazující integrace v85 — 17. 10. 2026

Auditovaný `buuk`: `1fe5cb9080cd8cc84bd1002c393f720951020f0f` po merge #1525.
Všechna nová PR #1521–1525 jsou mergnutá; GitHub i lokální fetch souhlasí.
Při inventuře nebylo otevřené PR. Tato větev přidává Master v85 a opravy níže,
nikoliv další hotový Week Transition nebo vydání pre-alpha.

## Kontrola nových PR

Kontrolován byl diff od merge Master v84 `98a3abdd` do aktuálního buuk:
38 souborů, 4 666 přidaných / 19 odstraněných řádků. Audit zahrnul application
services, nový storage/Save/restore kontrakt, repository integraci, HTTP příkazy,
TS validátory/panely a jejich testy i skutečný browser acceptance scénář.
Starší PR #1508–1519 jsou podrobně pokryta v84 auditem a nebyla vydávána za nová.

| PR | Finální HEAD | Skutečný výsledek | Fast CI run | Backend tests |
| --- | --- | --- | --- | ---: |
| #1521 | 572754daad2146d0ff22263d76e640b18bed5e21 | Opraven A84-01: strict horizon extension funguje, staré JSON/hash zůstávají | 39025280194 | 35 passed |
| #1522 | d018791708180625971db006ba272666de89e693 | Skutečná opening-week exhibice, immutable manual Save, replay/restore/restart + CS/EN | 39029091344 | 5 passed |
| #1523 | 2ff21fa3cea4716c08e8cb7e07751b83628f56ea | Skutečná 2 semifinále + winner-fed final, Save a přesný replay pro W52/W80 | 39031128810 | 5 passed |
| #1524 | 82e1fa2fd1359931b09eb7350016513898ef1dda | Reviewed operator point policy + čtyři awards, druhý skutečný Save, restart/restore | 39033229498 | 3 passed |
| #1525 | 2cf16690049cda5aae48b6330a1cb6d04d10ffe4 | Saved-backed hypotetické časové pořadí jednoho turnaje, W-expirace, CS/EN | 39066250497 | 5 passed |

Na finálních HEAD všechna spuštěná workflow success: #1521 1 (Fast CI), #1522 11,
#1523 9, #1524 9, #1525 9. Browser Shell runs: #1522 39029091354,
#1523 39031128850, #1524 39033229559, #1525 39066250503. Zahrnují skutečný W52
1000-player Run a produkční HTTP/SQLite/UI, ne jen mock. Ostatní odpovídající
legacy hybrid/task/restart browser workflow rovněž success. Počty z Fast CI jsou
vybrané moduly, nikoliv plná regrese; nelze je mechanicky sčítat jako unikátní testy.

## Dobře provedené hranice

- Nový sporting state má oddělené verzované schema a neinterpretuje W52/W80 jako
  staré W61 ordinals. MatchEngine reálně hraje a uchovává rally/timeline/stamina.
- Semifinále čerpají stejnou původní populace/input bázi; finále má skutečné
  vítěze. Aktuální frozen inputs finále se ještě nevyvíjejí po semifinále — není
  to tvrzení plné fatigue/Health/57-attribute sporting integrace.
- Positive Save akceptace už používá normální produkční příkazy a nové immutable
  revize. Nález A84-03 o starších re-signed fixtures tedy není hranicí tohoto
  nového pozitivního toku. Historie se neopravuje ručním rehashováním.
- Body se po review/apply ukládají samostatným Save a zachovávají původní pavouk.
  Point policy je otevřeně operator-authored; časové pořadí není vydáváno za
  Official Ranking ani provedený Week Transition. Population-only lifecycle není
  falešně změněn na vstup všech hráčů na Tour.
- Historický předzápasový fork je použitelný. Fork z match-containing revize je
  zatím explicitně blokovaný, nikoliv nekorektně přeznačený pod jinou branch.

## Nalezené chyby a implementace této větve

### A85-01 — prodloužení po Saved native sportu nesprávně blokované

`run_calendar_extension_commit._capture_live_content` nevolal nově přidaný
`capture_saved_calendar_match`. Saved sporting komponenta se proto při kontrole
považovala za chybějící/odlišnou i tehdy, když se live row přesně shodoval.
Skutečná reprodukce: W52 Run → produkční populace → 3 MatchEngine zápasy →
Save → review bodů → apply → druhý Save → extension review vrátí
`unsaved_live_state_differs_from_saved_head` a `can_save=false`.

Oprava doplňuje tentýž produkční capture adapter jako normální Save. Neoslabuje
porovnání obsahu, nevynechává klíče a nemění původní revize. Integrační test
ověřuje W52/W80, více branchí, receipt retry, cold restart, přesný replay,
hypotetickou expiraci, historický backward/forward restore a další extension.
Unsaved body nebo ztracený live row stále blokují bez částečného Save.

### A85-02 — přesný původní command retry ztracený po bodování

Po povýšení live row na scored schema přestal `simulate` rozpoznávat původní
odehraný příkaz, přestože jej scored evidence obsahuje celý a beze změny.
Nyní přesný retry porovná původní command/request fingerprint a vrátí původní
played receipt/fingerprint, včetně situace po Save, extension a restartu.
Neodehraje nic znovu, nevrátí novější scoring fingerprint a nesmaže připravené body.
Změněný příkaz se nadále odmítá. Jde o idempotenci, ne druhý turnaj na stejné branchi.

### A85-03 — consent/pozdní odpovědi bodového panelu přes změnu HEAD

Panel kontroloval jen rovnost textového targetu, ne přechod pryč a zpět; starý
review/consent navíc zůstával ve state při změně props. Server chránil Save,
ale UI mohlo znovu nabídnout zastaralý review. Oprava váže viditelný review na
konkrétní target a request epoch, resetuje souhlas/příkaz při změně zdroje,
ignoruje staré úspěchy/chyby i návrat A → B → A a unmount. Nové component testy
ověřují nemožnost apply bez nové kontroly a nového souhlasu.

### A85-04 — Home přehlížel skutečnou Saved native historii

`phase` odvozoval historii pouze z legacy transition events. Nový Saved zápas/
pavouk proto stále vypadal jako pouhá příprava. Home nyní načte validovanou Saved
native komponentu a označí `sporting_history`. Počet transitions a publikovaných
rankingů zůstává skutečný (v těchto testech 0); legacy sporting guard se neodemyká.

### A85-05 — chybějící browser workflow path coverage

Změny nového knockout browser helperu, panelů a native backend služeb samy
nespouštěly existující Shell workflow. Přidány relevantní cesty do stejného
workflow, nevzniká nová duplicitní CI sada. Shell je rozšířen o review/consent/
all-Branch extension po reálném obodovaném turnaji a reload/replay/expiraci.

## Ověření

- Auditní společný běh všech šesti relevantních #1521–1525 backend modulů:
  **53 passed**, 261,22 s. A84-01 už se nereprodukuje.
- Nový produkční HTTP/SQLite sporting-horizon modul: **4 passed**, 117,89 s,
  včetně skutečně odehraných zápasů a popsaných negativních případů.
- Frontend nové source-change regrese + Home panel: **6 passed**, build TypeScript
  a Vite success. Component testy mockují pouze HTTP boundary a nejsou označené
  za integrační browser důkaz.
- Další přímo dotčené původní extension/Home/knockout regrese: **20 passed**,
  46,89 s. Finální PR CI je samostatná přesná evidence.
- Nová rozšířená Chromium akceptace musí projít na finálním HEAD před předáním
  PR k mergi; lokální prostředí pro tento audit nemá Playwright. Neprohlašuje se
  plná regrese, release, 50 sezon ani empirická realističnost.

## Co stále chybí

Calendar-native canonical sporting/Health checkpoint a skutečné následné efekty,
plná atributová projekce místo sedmipolového compatibility vstupu, historicky
účinná Category/Edition point policy, actual Tour entry, Official publication,
Week/Season transitions a durable Full Simulation na nových kalendářích.
Match-containing cross-Branch fork nemá proven remap. Příští práce má dokončovat
skutečnou sporting authority cestu; tyto opravy neprohlašují další týden za odehraný.
Nové milníky/souhrny v Master v85 jsou produktové cíle, ne hotový backend/frontend.
