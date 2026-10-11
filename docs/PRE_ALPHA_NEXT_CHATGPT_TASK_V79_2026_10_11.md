Pokračuj v programování Squash Engine pre-alpha v repozitáři Jasmetk0/squash-tour-beta. Jsi implementační ChatGPT chat; můžeš použít dostupné nástroje pro GitHub a kód, Codex není povinný. Tento návrhový chat mezitím řeší další UI. Nevymýšlej nové sportovní mechaniky a nepřepisuj produktový Master svými implementačními omezeními.

Nejdřív ověř aktuální buuk, poslední merge a otevřená PR. Výchozí audit je buuk d1090495f3771e97995b94a6f1d119e7218a816b po #1383; pokud je novější, pracuj podle skutečného kódu. Načti nejnovější docs checkpoint v79 po jeho merge, AGENTS.md, CURRENT_STATE.md, ROADMAP.md, relevantní části SQUASH_ENGINE_MASTER_VISION.md (9.4–9.7, 27.19–27.21, 31.34, 35.36), PROJECT_CONSTITUTION_TECHNICAL_PLAN.md, docs/PRE_ALPHA_FRONTEND_V1.md, docs/PRE_ALPHA_FRONTEND_CHECKPOINT_V79_2026_10_11.md a docs/PRE_ALPHA_TEST_POLICY.md. Pokud docs PR v79 ještě není sloučené, přečti jeho skutečný obsah a při implementaci nevydávej návrhy za hotový runtime.

Co už je v buuk: #1376 opravilo integraci Keep, #1377 odděluje Geographic/Travel Region, #1378 ověřuje 1 000 hráčů přes skutečný Chromium/SQLite/Save/ranking/restart, #1379 opakuje autentizované Keep, #1380 edituje devět legacy source polí 1–99, #1381 přesně ukládá návrhy a #1383 vynucuje celodávkové country kvóty s automatickým zbytkem. Tyto funkce nezačínej znovu a nezaměňuj za canonical 57 atributů/OVR 0–200.

Zpracuj následující posloupnost několika samostatných, soudržných PR. Začni prvním řezem a doved ho do zeleného finálního HEAD. Další řezy navazují na skutečně sloučený buuk; uživatel merguje, ty nikdy. Když merge ještě není hotový, připrav další technický návrh bez tvrzení, že nesloučená závislost už je v buuk. Není potřeba čekat na souhlas s běžnými autorizovanými reverzibilními opravami, ale nemerguj.

PR 1 — spojení individuálních editací/zámků s opakovaným Keep a uloženým návrhem.
- Nyní RunInitialWorldSetupPanel dovolí editaci jen když keep_from_seed == null a fieldPreviewAction vyžaduje nulový Keep výběr. Nestačí odblokovat tlačítko: backend při replay předchozího requestu použije dnešní field_locks a změněná pole rozbijí původní fingerprint.
- Navrhni a zdokumentuj verzovanou autentizovanou reprezentaci generační session/operací, která umožní explicitně změnit nebo odemknout podporované pole po Keep a po obnovení návrhu. Původní historické kroky musí zůstat reprodukovatelné; ruční editace je nový ověřený krok, ne tichá změna staré historie.
- Zachovej stabilní identitu, ostatní Keep profily, zámky, tvrdé podmínky, přesné country kvóty a konzistenci současného modelu. Konflikt neřeš odemknutím či změnou jiného vstupu za zády uživatele. Nepřijímej autoritativní hráčské objekty z prohlížeče.
- Staré no-lock/one-pass/multi-pass payloady a uložené fingerprinty musí dál fungovat; nová verze nesmí přepsat uložené Runy/replay.
- Preview nemutuje Run, nepotvrzené editace blokují Adopt, Add/Working Draft/manual Save zůstávají samostatné. Preview locks ani Keep nejsou lifetime locks.
- Testuj edit před/po dvou Keep krocích, změnu výběru, unlock/Automatic, nový seed, uložený/obnovený návrh, tampering, stale World/HEAD, konflikt kvóty a starý hash. Přidej skutečný browser průchod edit → Keep → edit → návrh/reload → Adopt → Save → backend restart; využij existující izolované scénáře.

PR 2 — přesné čtecí otevření zastaralého návrhu a explicitní revalidace.
- read_run_generation_proposal dnes odmítá samotné Open po změně HEAD/draft/World nebo po vytvoření InitialWorld.
- Odděl autorizované čtení neměnného uloženého návrhu od jeho současné použitelnosti. V původním vlastnickém Run/Branch scope dovol zobrazit přesně uložené hráče/podmínky/provenance, jasně označ neaktuální kontext a konkrétní důvod.
- Open nesmí volat generátor, měnit původní návrh, Working Draft, Viewer Branch či Saved Revision. Zachovej checksum/model validation a ochranu cizího scope.
- Explicitní nová validace ověří současné podmínky. Nezměněné konkrétní hráče neprohlašuj za čerstvý RNG výsledek nového světa. Pokud současný adopt kontrakt neumí bezpečné přidání původního návrhu, vrať konkrétní konflikt a vysvětlenou dostupnou cestu; nevytvářej backend bypass nebo automatickou regeneraci.
- Úspěšná revalidace/nový návrh musí mít vlastní konkrétní aktuální potvrzení, původní návrh zůstává neměnný. Žádné automatické Adopt ani Save.
- Ověř nezměněné Open bez RNG, unrelated HEAD změnu, změněný World/draft, již existující InitialWorld, corruption/cizí scope, explicitní potvrzení a SQLite restart.

PR 3 — schválené dočasné názvy nově generovaných hráčů.
- Zatím název země + pořadové číslo generování; nevytvářej/rešeršuj osobní jmenné databáze.
- Dokumentuj deterministický scope čítače v současném first-cohort workflow, vazbu na country identitu, retry/seed/Keep/branch chování a budoucí append návaznost. Název není player_id.
- Preserve původní jména importovaných/existujících/Keep hráčů a staré snapshoty/hashes. Změna vyžaduje verzovaný kontrakt; nesmí nekompatibilně přejmenovat při ověřování starého saved proposal/replay.
- Nelži, že first-cohort jména řeší obecné přidávání dalších dávek, dokud append neexistuje. Testuj úplnou dávku, Keep, proposal restore, retry a Save/restart.

PR 4 — dokončení samostatné generační stránky a sloupců.
- Jedna stránka: vlevo sbalitelné podmínky/skupiny/předvolby v podporovaném rozsahu, vpravo shrnutí/varování/tabulka, player side editor zachovávající filtr, stránku a scroll.
- Hlavní akce Generate / Save proposal / Add to Run a samostatný manual Run Save; žádné nové World/Custom rozdělení.
- Přidej Columns a zapamatování volby. Cílové OVR/potential/development/physical sloupce zobraz jen ze skutečného canonical modelu; nynější source schopnosti 1–99 označ poctivě. Nepřidávej fiktivní výšku/57 atributů.
- Viditelný rozpis upravených/zamčených polí, jasné počty stránka/odpovídající filtr/celá dávka a použitelnost 1 000 profilů. Filtr nesmí změnit Adopt ani Keep.
- Bulk edit/Undo a subset Add jsou schválený další cíl, ale nepředstírej je tímto UI PR. Subset Add později potřebuje bezpečný generický append kontrakt, explicitní úpravu závazných kvót, zachování zbytku návrhu a ochranu duplicit; nikdy částečné nahrazení autoritativního InitialWorld.
- Ověř oba jazyky, zachování kontextu, columns persistence, hotové server flows a browser reload.

Další schválené stránky v79 jsou backlog po stabilizaci těchto základů: stručný World přehled, šest country tabs včetně Records/Tournaments, 61-week kalendář/list, šest Edition tabs, match/replay, Simulation a Official Ranking/Finals Race s klikacími body. Qualification/Main přepínač je POUZE v Draw/Groups; jinde obě části, hlavní první a kvalifikace níže, tlačítka jen scrollují. Nevyráběj budoucí výsledky nebo současný stav místo chybějící historické projekce.

Disciplína pro každé PR:
- běžný base=buuk, jeden soudržný vertical slice, aktuální skutečný kód a předchozí merge ověř znovu;
- relevantní deterministické backendové a UI/API/SQLite testy a skutečný browser tam, kde měníš end-to-end flow; mock test nevydávej za integraci;
- odlišná adversarial kontrola fingerprint/scope/identity/pending change/no mutation hranic;
- focused test policy běžných PR, celý release gate až při skutečném release; netvrď celou pre-alpha ani realistickou simulaci ze smoke CI;
- aktualizuj CURRENT_STATE, dotčený technický kontrakt a evidence, historické limity jasně označ; nenahrazuj Master vlastním canonem;
- uživateli dej merge link až po dokončení všech příslušných required checks na posledním feature HEAD. Uveď HEAD, testy, skutečně pokrytý browser scénář a zbývající omezení. Žádný merge za uživatele.

Začni kontrolou buuk a implementací PR 1. Neskonči pouhým plánem.
