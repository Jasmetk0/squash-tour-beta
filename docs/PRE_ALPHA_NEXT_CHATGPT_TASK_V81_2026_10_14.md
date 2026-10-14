# Další ChatGPT / Codex úkol po checkpointu v81 — 14. 10. 2026

Pokračuj v programování Squash Engine pre-alpha.

Repozitář: Jasmetk0/squash-tour-beta
Integrační větev: buuk
PR merguji já. Ty nikdy nemerguj.

Můžeš programovat přímo dostupnými nástroji nebo využít Codex. Před každým PR:
1. Stručně vysvětli, co nově půjde dělat a proč je to nyní nejlepší krok.
2. Uveď doporučený model Codexu a reasoning režim.
3. Vždy napiš úplný kopírovatelný prompt pro tento konkrétní řez, i když ho následně provedeš sám.
4. Potom pracuj; nezůstávej jen u plánu. Nepředstírej spuštění Codexu bez skutečně dostupného nástroje a neduplikuj tutéž implementaci ve dvou prostředích.
Po PR napiš, co bude následovat. Jeden ucelený funkční řez na PR, base=buuk. Odkaz jako merge akci pošli až po všech požadovaných zelených kontrolách na finálním HEAD. Na skutečně otevřené produktové otázky se ptej; technické volby řeš samostatně.

## Model
Výchozí doporučení pro běžnou implementaci: GPT-6.1 Sol / Medium, je-li dostupný v daném Codex klientu. Pro obtížnou historickou/transactional integraci přepni na High; Astra použij cíleně při složité architektuře nebo přetrvávající regresi, nikoli automaticky na každou úpravu textu. Doporučení vždy přizpůsob konkrétnímu řezu a ověř skutečnou dostupnost, nevymýšlej názvy modelů. Max/Ultra nejsou povinný default.

## Nejdřív ověř skutečný stav
Auditovaný buuk: bf928bfcd3e9848c15762ac66860039b53bedaef, merge #1453.
PR #1442–1453 jsou začleněná, jejich finální feature HEADy v historii a dostupné finální PR CI úspěšné; při auditu nebylo otevřené implementační PR. Novější stav ověř, nepřepisuj cizí rozpracovanou práci. Přečti AGENTS.md, celý relevantní rozsah SQUASH_ENGINE_MASTER_VISION.md v81, constitution, CURRENT_STATE.md, ROADMAP.md, docs/PRE_ALPHA_TEST_POLICY.md a docs/PRE_ALPHA_FRONTEND_CHECKPOINT_V81_2026_10_14.md. Pokud dokumentační PR v81 ještě není mergnuté, přečti ho jako novější explicitní rozhodnutí a neduplikuj jeho soubory.

## Co už je hotové — nedělej znovu
Country → historická Saved Edition a návrat, intervalové Country Records v doloženém rozsahu, branch mapa/tabulka historie, samostatné read-only A/B dvou reachable revizí jedné branche, Edition a publikované match evidence.
Reálný hybrid: dvě skupiny po dvou → dva skutečné skupinové zápasy → frozen standings → postupující → finále → explicitní policy → canonical ranking source → Saved Edition/restart.
Body 10/100/60 jsou pouze vstupy testu, nikoli obecný default.
Cyklická shoda #1449 je reálné browser/HTTP/SQLite rozhodování nad autentickými MatchEngine výsledky, ale s testovým adaptérem vstupních receipts. Není to běžný Run-native Match Day ani Save tohoto cyklického případu.

## První PR: sjednoť použitelné CS/EN History/Compare a pravdivé hybridní popisy
Oprav zdrojově potvrzené A81-01 až A81-03:
- SavedBranchMap.tsx, SavedRevisionHistoryPanel.tsx, SavedStatesComparePage.tsx, SavedEditionCompareSection.tsx, SavedMatchComparePanel.tsx: všechny viditelné nadpisy, akce, stavy, prázdné/error stavy a accessibility názvy dle skutečně vybraného jazyka. Používej existující LanguageContext/překladovou infrastrukturu; směs EN+CS v jednom textu není lokalizace.
- V pre-alpha mapě nezobrazuj Official ani Viewer role/badges. Branche jsou rovnocenné. Zachovej legacy persistence/schema a interní Viewer selection invarianty; odstraňuješ zavádějící UI, ne historická data.
- GroupFormatSetupPanel.tsx: český úvod a help musí správně odpovídat pure groups vs groups_knockout. V hybridním formuláři nesmí tvrdit “Pouze skupiny” nebo že hybrid potřebuje jiné neexistující ovládání. Přelož relevantní validace/stages v navazujícím hybridním toku bez změny sportovních pravidel.
- Ponech čitelné technické ID/fingerprinty v rozbalitelném důkazu tam, kde pomáhají; není potřeba plošný redesign.
- Zachovej přesnou Saved Revision, original owner, reachable lineage, A/B filtry a čistě read-only chování.
Ověření: cílené jazykové/component testy v obou jazycích, frontend build, existující vhodný browser smoke. Neopakuj kompletní sportovní suite pro čistě jazykový řez.

## Další PR: skutečný hybridní zdroj → první oprávněný Official Ranking týden
Ověř aktuální ranking/Week Transition služby a existující UI, pak dokonči jeden skutečný uživatelský tok:
- normální odehraný hybrid, explicitně schválené bodování a canonical closure;
- první časově oprávněná ranking publikace podle uložené policy a source boundary; předčasná publikace musí být odmítnuta;
- přesné hráčské body, jediný souhrnný turnajový zdroj, žádný double count group+knockout, správné Best N;
- preview, výslovné potvrzení/publikace/Save, historický detail zdroje a restart se stejnými výsledky;
- použij autentickou autoritu původního turnaje, nikoli ručně vložený ranking fixture.
Zkontroluj ordinal 0 / první týden a sezonní hranice dotčené #1453. Otevřenou W/O politiku nesmíš vyřešit vymyšlenou konstantou. Pokud je tento řez mezitím hotový, ověř jeho důkaz a pokračuj následujícím.

## Potom: více knockout kol
Nejmenší skutečný hybrid se semifinále a finále, postup přes winner feeders, jedno odehrání každého zápasu, správné výsledky/awards a explicitní Saved history + restart. Rozšiř existující průchod; novou infrastrukturu jen pokud je nutná. Nehonit další seed-only PR místo propojené funkčnosti.

## Potom: schválené v81 ovládání simulace
Postupuj po soudržných řezech nad existujícím engine:
- serverová identita úlohy a bezpečné pause/resume/change target/stop; jeden běžící autoritativní Run, idempotentní příkazy, žádná duplikace při reconnect;
- konzole + globální panel, čtení konzistentního dokončeného stavu při navigaci, změny vstupů až po bezpečném pozastavení;
- časové/relativní/událostní cíle, původní cíl po pauze, ruční Save, souhrn;
- zavřená karta nepřeruší živý backend; po restartu procesu žádný automatický restart simulace a poctivý Recovery Draft;
- Runové sledování objektů/pravidel, branchové stop rules, předvolby; propojené ovládání není druhý nezávislý systém pravidel.
Nevydávej frontendový interval/loop za durable background engine. Zachovej simultánní pre-slot snapshot a původní RNG při pause/retry. Technickou granularitu odvoď od existujících bezpečných commit hranic.

## Další potvrzený rozsah, který nesmí zmizet
§27.23: boční detail zápasu + celá stránka, porovnání původního předzápasového stavu obou hráčů bez current fallback, poznámky mimo herní AI, explicitní podklady pro prověření zápasu/AI volby v Labu nebo vývojovou AI.
Samostatný nový A/B Lab layout Původní/Experimentální nebyl potvrzen. Přeskočený seznam čekajících rozhodnutí stále otevřený. Prahy významnosti, přesnosti a realističnosti i úrovně porovnání se kalibrují až na fungujícím enginu.

## Invarianty, evidence a dokumentace
- Dark Admin a funkční CS/EN, Viewer není pre-alpha produktový tok.
- Immutable reachable Saved Revisions, historický original owner, žádné read mutations/current fallback, žádný automatický Save.
- Chráněné vestavěné balíčky a Official zdroje testovat na kopiích; Run zásahy jen v autorizovaném rozsahu.
- Přesný historický informační snapshot pro hráčskou AI, diagnostika bez sportovního RNG/Run mutací.
- Cílené testy podle dopadu. Rozliš mock/component, real HTTP/SQLite a skutečný browser UI. Ověř poslední HEAD, ne starší green run.
- CURRENT_STATE/ROADMAP mají na začátku skutečný současný stav; staré kandidátní zápisy označ jako historické, nepřidávej další zavádějící aktivní “NOT MERGED” po mergi.
- Žádná proklamace celé pre-alpha nebo realismu z jednoho malého scénáře. Cross-Branch Compare, full season/rollover/50-season a release suites mají vlastní důkazní mezery.
- Po dokončení: PR odkaz, nová schopnost, finální SHA a kontroly, zbývající omezení, konkrétní následující PR + prompt/model.

Začni kontrolou aktuálního stavu a prvním výše uvedeným funkčním řezem. 
