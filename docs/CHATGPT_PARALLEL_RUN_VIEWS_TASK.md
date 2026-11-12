# Paralelní ChatGPT — druhá série frontendových celků, 12. 11. 2026

Toto zadání nahrazuje první úkol pojmenovaných pohledů. PR #1788/#1791/#1792
jsou po nezávislé kontrole Worka a opravách vlastníkem mergnuté. Ověřený základ
při přípravě této série je `buuk 8c2507bfe20601c5dd7b7fc7a47c48c5190180e9`.
Před úpravami vždy načti aktuální větev. První zadání zůstává v Git historii;
nejde o pokyn implementovat již dokončenou funkci znovu.

## Prompt pro pokračování ve stejném nebo novém ChatGPT chatu

Pokračuj jako samostatný frontendový pomocník na Squash Enginu v repozitáři
`Jasmetk0/squash-tour-beta`, integrační větev `buuk`. Předchozí tři PR už prošla
kontrolou Worka a jsou mergnutá. Nové zadání má tři ucelené části níže.

Work zůstává technický vedoucí a nezávislý reviewer, Radim jediný merguje.
Claude vlastní Turn Pro, kariéry, nativní sezonní souhrny a upozornění. Work
vlastní ATP zdroje, kalendáře a nativní Q/Main integraci. Tvoje úkoly tyto oblasti
nemění. Přečti `AGENTS.md`, aktuální stav, rozdělení práce v
`docs/AI_REVIEW_HANDOFF.md` a příslušné celé části Masteru, zejména 23.8, globální
Home v75 a historickou věrnost/read-only UI. Zadání neuděluje nová sportovní práva.

Ověř aktuální přístup k repozitáři a nástrojům. Můžeš pracovat přes GitHub API,
pokud skutečně umíš zapisovat a připravovat PR. Není nutné předstírat lokální
checkout. Rozliš lokální test, úspěšný hosted CI na přesném commitu a skutečný
browser/API průchod. Pokud máš pouze čtení, vrať patch vůči aktuálně načtenému
kódu a označ nespouštěné kontroly; chybějící obsah si nevymýšlej.

### Celek 1: správa nedávno otevřených Runů na Home

**Proč:** Master 23.8 dovoluje vymazat osobní historii nedávných návštěv. Globální
Home už zobrazuje skutečné nedávné Runy, ale nemá odpovídající uživatelské ovládání.

- Rozšiř existující `web/src/pages/admin/AdminHomePage.tsx` a
  `web/src/navigation/recentProductRuns.ts`; nepřidávej druhý seznam historie.
- Přidej výslovné vymazání pouze historie nedávných Runů v tomto prohlížeči.
  Nesmaž Run, Branch, uložené pohledy, data simulace ani jiné preference.
- Pracuj s aktuálním skutečným inventářem. Přejmenovaný Run ukazuje aktuální
  název; chybějící nebo nedostupná ID nenahrazuj vymyšlenými údaji. Zachovej
  pořadí a omezení stávajícího helperu, nevymýšlej nový produktový limit.
- Po vymazání nebo změně stejného browserového klíče v jiné kartě aktualizuj
  přehled bez automatického otevření Runu či změny kontextu. Poškozené nebo
  nedostupné storage neblokuje Home. Při selhání vymazání nehlásit falešný úspěch.
- Zachovej oddělené stavy načítání, prázdného seznamu a chyby API; CS/EN a
  klávesnicové ovládání. Použij nové překlady lokálně, neměň společný slovník,
  sidebar ani další konzumenty historie bez skutečné potřeby.

**Ověř:** otevři dva Runy, vrať se na Home, vymaž nedávné a obnov stránku. Oba
Runy stále existují a lze je ručně otevřít, uložené pohledy zůstaly. Změna historie
v jiné kartě neotevře Run. Otestuj i odmítnuté `removeItem` a chybný JSON.

**Soubory:** Home, jeho testy, recentProductRuns a jeho testy. Zachovej veřejné
signatury existujících funkcí pro ostatní stránky; případně přidej malý helper.

### Celek 2: sdílené filtry historie odehraných turnajů

**Proč:** `web/src/pages/EventsPage.tsx` už umí filtrovat, ale filtry jsou jen
v dočasném React stavu. Rozšiř tuto existující stránku, nevytvářej druhý prohlížeč.

- Ulož týden, kategorii a textové hledání do jednoznačných URL parametrů stránky.
  Zachovej ostatní parametry a platné deep linky na přesnou událost.
- Reload a Back/Forward obnovují stejnou prezentaci. Psaní textu nezaplňuje
  browser historii každým znakem. Reset odstraní jen vlastní filtry a případný
  již neplatný výběr, nikoliv cizí query parametry.
- Respektuj současné rozlišení `selectedEventSequence` a historického
  `selectedEventId`, včetně opakovaného event ID v různých sezonách. Nevybírej
  jinou událost jen podle shodného názvu nebo pořadí na obrazovce.
- Neznámou kategorii/týden vysvětli a nepřepni tiše na Vše. Chybějící čas není
  doslovná hodnota `null` nebo `undefined`; zachovej ochrany identity a zdrojů.
- Filtry neprovádějí další simulaci, zápis ani automatické přepnutí Runu.
  Zachovej současné lazy čtení detailu a neduplikuj API požadavky při výběru.

**Ověř:** otevření konkrétní události filtrovaným odkazem, reload, Back, reset
s cizím parametrem, opakované event ID, neznámý filtr a chybějící metadata.

**Soubory:** `EventsPage.tsx` a nový izolovaný
`EventsPage.filters.test.tsx`. Existující `HistoryViews.test.tsx` a
`RunHistoryLocale.test.tsx` spusť; jejich ochranná očekávání neměň kvůli zelené CI.
Stránka je legacy read-only historie, nikoliv nová autorita Product Run Saved.

### Celek 3: sdílené filtry rankingových a Race snapshotů

**Proč:** `web/src/pages/SnapshotsPage.tsx` má existující filtry týdne, kategorie
a zdrojové události. Doplň stejný použitelný URL návrat bez přepisování rankingu.

- URL zachová filtry a přesný platný `selectedSequence`. Při změně filtrů
  neukazuj detail ze starého neodpovídajícího výběru. Chraň rozlišení Ranking/Race
  i změnu Runu; číslo snapshotu samo není identitou napříč různými kontexty.
- Zachovej reload, Back/Forward, textový replace a reset pouze vlastních klíčů.
  Nepřenášej nekompatibilní výběr do druhého režimu. Vycházej ze skutečných
  tehdejších zdrojů; nepřidávej fallback na dnešní ranking nebo jinou Branch.
- Číselné URL hodnoty ověřuj striktně: `3abc`, `null` ani `undefined` nejsou
  platný týden/sequence a nenahrazují chybějící metadata. Volný textový filtr
  zdrojového ID však zbytečně nezakazuj podle jeho obsahu.
- Zachovej současné ochrany cizího Runu, nejednoznačného zdrojového event ID,
  částečných dat a chyby API. Přidáním filtrů neobcházej žádnou z těchto podmínek.
- Stránka zůstává legacy read-only diagnostika. Není to Claudův nativní sezonní
  souhrn ani implementace Official Ranking writeru. Zachovej CS/EN a současné
  vysvětlení pokrytí historie.

**Ověř:** oba režimy nad různými snapshoty, přímý odkaz na detail, reload,
Back/Forward, reset s nesouvisejícími parametry, chybnou sequence a zdroj bez týdne.

**Soubory:** `SnapshotsPage.tsx` a nový izolovaný
`SnapshotsPage.filters.test.tsx`. Stávající společné testy mají zůstat zachované.
Nepřepisuj `ViewerRunSnapshotsPage` ani nativní sezonní/kariérní komponenty.

### Společné hranice a postup

1. Před každým celkem načti čerstvý buuk a zkontroluj otevřená PR i jejich soubory.
   Přeskoč skutečně dokončenou práci s důkazem; nedělej znovu #1788/#1791/#1792.
2. Jeden dokončený celek = jeden přehledný Draft PR. Po odevzdání pokračuj dalším
   nezávislým celkem z aktuálního buuk, i když Work ještě kontroluje první.
   Neskládej tři změny do skrytého kumulativního řetězce. Já merguji, ne ty.
3. Rozsah je výše uvedené UI a jeho izolované helpery/testy. Neměň backend,
   API kontrakty nebo `web/src/api/client.ts`, konfiguraci, Master, závislosti,
   obecnou navigaci, kalendář, sport, Save/restore/fork, oblíbené/watchlisty,
   Claudovy kariéry/souhrny ani Workovy ATP soubory.
4. Používej existující styl, překlady a komponenty; případné nové texty drž
   lokálně. Nedělej plošný refaktor ani nový globální filtr-framework.
5. Pro každý celek spusť cílené nové i dotčené existující testy a `npm run build`
   z `web`, nebo ověř jejich skutečný finální hosted CI, pokud lokální běh nemáš.
   Browser zkus, máš-li jej dostupný. Po selhání popiš konkrétní limit; netvrď pass.
6. Chyba testu se opravuje podle skutečné příčiny, ne odstraněním aserce,
   přepsáním fixture na úspěch, potlačením Sonaru nebo vypnutím ochrany zdroje.
   Pamatuj na opravu z #1791: text `null` nesmí přes String(null) vybrat chybějící čas.
7. Vracej přesný head, změněné soubory, praktický příklad, provedené kontroly a
   omezení. Nezaměňuj RTL s mockovanou API hranicí za skutečnou HTTP/browser akceptaci.
8. Technické detaily řeš samostatně. Na novou nevyřešenou produktovou otázku se
   zeptej s možnostmi a příkladem, ale nezastavuj nezávislou schválenou práci.
   Po třech celcích předej souhrn Workovi; bez přidělení nepřebírej jiné části enginu.
