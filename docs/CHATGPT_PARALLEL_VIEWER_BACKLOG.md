# Soustavná práce ChatGPT na Vieweru

Zadání od Radima z 22. listopadu 2026. Integrační větev je `buuk`. První audit vychází z `71f03fb9242427d3dbc46d9106d58d21442df98c`. Aktuální stav ověřuj při každém pokračování.

## Komu patří která část

Radim rozhoduje o produktu a jediný merguje. Work koordinuje a nezávisle kontroluje. ChatGPT implementuje pouze samostatné čtecí funkce Vieweru a jejich cílené frontendové testy. Viewer zůstává vedlejším proudem práce mimo hlavní průchody první pre-alphy podle Masteru §31.41.

Před změnou přečti [AGENTS.md](../AGENTS.md), [CURRENT_STATE.md](../CURRENT_STATE.md), [ROADMAP.md](../ROADMAP.md), [AI handoff](AI_REVIEW_HANDOFF.md), [testovací pravidla](PRE_ALPHA_TEST_POLICY.md) a celé relevantní části [Masteru](../SQUASH_ENGINE_MASTER_VISION.md). Starší úkoly z [původního frontendového zadání](CHATGPT_PARALLEL_RUN_VIEWS_TASK.md) ověř proti současnému kódu, ať je neděláš znovu.

## Zásobník v pořadí práce

1. **Odeslání dotazu ve Viewer Search (§23.1).** `web/src/pages/viewer/explore/ViewerSearchPage.tsx` přijímá URL `q` a načítá výsledky podle něj, ale vlastní pole mění jen lokální stav a nemá cestu k odeslání. Propoj existující pole a formulář s URL. Ověř Enter, tlačítko, prázdný dotaz, reload, Back/Forward a zachování cizích parametrů. Zachovej existující čtecí zdroje, prázdný stav bez Runu a přesné hranice současného pokrytí. Načtení musí respektovat právě vybraný Run a současné ochrany veřejné historie. Pokud zdroj neposkytuje historický kontext, nesmí se současná data prezentovat jako data tehdejší. Rozsah tohoto PR je stránka Search, její lokální texty a izolované testy.
2. **Sdílitelný pohled na historii Official Rankingu (§27.16 a §31.41).** `web/src/pages/viewer/rankings/ViewerOfficialRankingHistoryPage.tsx` drží sezonu, Best N, hledání a pořadí v lokálním stavu. Přenes stávající filtry do URL tak, aby přímý odkaz a Back/Forward obnovily prezentaci. Zachovej přesné odkazy podle publication ordinal, reset při změně Runu/branche podle stávajícího kontraktu a ignorování opožděných odpovědí starého kontextu. Testy pokryjí také neplatný filtr a nesouvisející query parametry.
3. **Přímý odkaz na dříve publikovaný Finals Race (§27.16).** `web/src/pages/viewer/rankings/ViewerRacePage.tsx` drží výběr publikované sezony v React stavu. Umožni vrátit se ke stejné historické publikaci přes URL a Back/Forward. Testuj chybějící publikaci, změnu Runu/branche a rozlišení skutečné nuly od chybějících dat. Použij stávající publikace. Výpočet Race, sportovní pravidla a výběr účastníků jsou mimo zadání.
4. **Klávesová zkratka k existujícímu Viewer vyhledávání (§23.1).** Až funguje první celek, ověř umístění skutečného Viewer vyhledávání v jeho navigaci. Pokud lze bezpečně upravit komponentu používanou výhradně Viewerem, přidej `Ctrl+K` jako aktivaci téhož pole a ověř fokus i navigaci klávesnicí. Pokud by šlo o společnou Admin/Viewer lištu, přesuň požadavek do seznamu závislostí a pokračuj jiným celkem.
5. **Veřejné výsledky, historické názvy a dostupný uložený Replay (§23.1 a §23.9).** Každou z těchto věcí dělej jako samostatnou úpravu pouze při doloženém existujícím veřejném GET, který vrací potřebný stabilní identifikátor, historii a správný časový kontext. Využij skutečné odkazy a existující read-only obrazovku. Nepřimíchávej Admin data ani dnešní název, budoucí výsledek nebo vyrobený Replay do minulosti. Chybějící backendovou schopnost zaznamenej s konkrétním souborem a pokračuj podloženou mezerou.
6. **Další procházení Masteru.** Hledej další konkrétní rozdíl mezi rozhodnutými požadavky na čtecí Viewer a současným kódem ve stejných hranicích. Například skutečně dostupný údaj nebo přístupný ovládací prvek, který v rozhraní chybí (§27.1 a §27.3). V každém PR cituj rozhodnutý požadavek a dolož konkrétní mezeru. Odložený nebo otevřený produktový návrh eviduj, nerealizuj jej na základě odhadu.

## Mimo rozsah

- `src/beta_engine/**`, API routy a kontrakty, databáze a migrace, Saved v1/v2, ověřování historie, explicitní Save, Restore, cold reopen, hashe, replay kernel, cache a výkon. Existující GET lze použít z již funkčního klienta. Změny sdíleného `web/src/api/**` předává Work.
- ATP a FAX zdroje, Packages, kalendář a sloty, Q/Main, zápasy a rally, ranking writer, seedy, turnajová pravidla, hráčská AI, Turn Pro a simulační běhy. Správu nativních kariér, sezonních přehledů a upozornění ponech příslušnému vlastníkovi.
- Admin obrazovky a sdílená navigace nebo router včetně `App.tsx`, ochrany Working Draftu, globální jazykové nebo designové přepínače, CI, workflow, produkční timeouty a konfigurace. Nerozbíhej dlouhé benchmarky. Zachovej existující bezpečnostní a zdrojové testy.
- `buuk`, Master a cizí větve. PR #1840–#1843 zůstávají mimo tuto práci. Nepoužívej force-push, auto-merge, přímý zápis do cílové větve ani uzavírání PR. Scope svévolně nerozšiřuj.

## Jak pokračovat

- Na začátku zkontroluj čerstvé `buuk`, stav přiděleného PR a soubory aktivních PR. Pokud se vlastnictví souboru překrývá nebo existuje současná práce, přejdi k dalšímu nezávislému celku. Před zápisem znovu ověř HEAD. Nepřepisuj změny Radima, Worka ani Claudea.
- První celek implementuj v Draft PR založeném s tímto zadáním, na větvi `feat/chatgpt-viewer-search-20261122`. Po něm vždy jeden samostatný celek v jednom Draft PR větve `feat/chatgpt-viewer-*` vycházející z čerstvého `buuk`. Na nezávislém dalším celku můžeš pracovat, zatímco předchozí čeká na kontrolu. Stav hotových a blokovaných částí zapisuj do přehledu v PR a odkazuj zpět na toto zadání. Červené CI nejprve prověř na správném commitu a skutečně oprav.
- Testuj cílené Vitest testy a build podle `web/package.json` a testovací politiky. Zachovej CS/EN, klávesnici a kontext Runu, branche a historického času. Test s mockovaným API výslovně odliš od browser/API průchodu. Stav i důkazy navazuj na přesný HEAD. Radim schvaluje každý merge.
- [x] Založené zadání, první mezera ověřená v kódu
- [ ] 1. Odeslání hledání
- [ ] 2. Odkaz na Ranking History
- [ ] 3. Historický Finals Race
- [ ] 4. Ctrl+K
- [ ] 5. Podložené veřejné výsledky, názvy a Replay
- [ ] 6. Další konkrétní mezera v rozhodnutém Viewer scope
