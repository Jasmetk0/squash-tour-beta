# Squash Engine / FAX Squash / MSA World Tour

## Kompletní průběžná specifikace a registr rozhodnutí

**Verze dokumentu:** 65
**Aktualizováno:** 12. 9. 2026 (UTC) – synchronizační audit po merge #720; canonical repo Master, nový Development Operating Model a integrační cesta k pre-alpha
**Účel dokumentu:** jediný průběžný zdroj pravdy pro to, co má Squash Engine být, co už je rozhodnuté, jakým směrem se projekt ubírá, co se musí teprve dořešit a – v oddělené evidenční vrstvě – co je prokazatelně naprogramované a sloučené.

Tento dokument primárně popisuje zamýšlený produkt. Samotná přítomnost produktového pravidla neznamená, že už je naprogramované. Ověřený stav kódu se od verze 51 zapisuje výhradně do samostatné kapitoly 35; implementace sama nikdy nevytváří ani nemění produktový canon.

**Rychlá orientace ve v65:** sportovní registry zůstávají **411 pevných / 88 prozatímních / 69 širokých otevřených bodů** a brána **48 vyřešených / 109 otevřených ze 157 PAQ**. Toto vydání neuzavírá žádnou PAQ implementací. Ověřený `buuk` je `08a29074250675a61434ba58fb42a185474648d5` po merge PR #720. #689 včetně #690 už je v `buuk`; staré označení „otevřeno“ níže je evidence k vydání v64. Nový aktuální stav je v **35.29–35.31**, pracovní model v **kapitole 36**. Ranking preparation je rozvinutá, ale publikace a skutečný end-to-end svět nejsou dokončené.

**Canonical cesta:** `SQUASH_ENGINE_MASTER_VISION.md` v kořeni repozitáře `Jasmetk0/squash-tour-beta`. Číslo vydání se mění uvnitř; přiložená/exportovaná verze je přenosná kopie téhož obsahu. Git historie uchovává další změny bez dalšího souběžného „nejnovějšího“ Masteru. `CURRENT_STATE.md` je krátký commitově ukotvený index implementace a aktuálního zadání; `ROADMAP.md` určuje technické pořadí. Ani jeden nemění tento produktový canon.

**Rozsah konsolidace v65:** zachován úplný převzatý produktový obsah v64 a historická evidence; doplněna viditelná konverzace a explicitní pracovní protokol z 12. 9. 2026. Zkontrolována merge historie #689–720, současné rankingové, Run/revision a legacy simulační hranice, aktivní autoritativní odkazy a cílené testy. Nejde o nový doslovný audit všech starých chatů ani o potvrzení plné testové sady. Sdílený odkaz `https://chatgpt.com/share/6aa5a8f2-f200-83ed-9278-aee649114353` se nepodařilo načíst; žádná neviděná rozhodnutí z něj nejsou doplněna. Předchozí nedostupný share ve v64: `https://chatgpt.com/share/6aa058ed-2104-83eb-8ec8-66b80074c50a`.

**Auditované zdroje:** úplný doslovný archiv hlavního chatu `squash_chat_archive(2).md`, 1 055 textových zpráv: 486 uživatelských a 569 odpovědí ChatGPT; jeho veřejný share snapshot obsahuje prvních 1 048 zpráv a archiv správně doplňuje dalších sedm zpráv. Na něj chronologicky navazuje úplný doslovný archiv `SQUASH_ENGINE_CHAT_2_FULL_ARCHIVE_2026-07-29_TO_2026-08-10.md`, 910 viditelných zpráv: 903 zpráv veřejného snapshotu a sedm následných handoff zpráv. Audit verze 41 přečetl oba archivy celé v tomto pořadí a následně celý Master v40. Proběhl ve třech samostatných průchodech: chronologická evidence rozhodnutí, úplné porovnání s Masterem a samostatná kontrola rozporů, statusů, opomenutí, původu, pozdějších změn a technické integrity. Verze 42 navíc načetla do konce veřejný sdílený chat `https://chatgpt.com/share/6a79d23e-25ec-83eb-85f4-acfeb5ca48d1`, zrekonstruovala jeho navazující viditelnou chronologii po verzi 41 a celý nový blok znovu porovnala s detailními kapitolami, souhrnnými registry a technickou strukturou Masteru. Verze 43 stejným způsobem načetla do konce sdílené chaty `https://chatgpt.com/share/6a7af046-bfdc-83eb-b6f8-70e51dbf0b2f` a `https://chatgpt.com/share/6a7af055-ef5c-83eb-8321-617e26e600f8`, oddělila v nich skutečná uživatelská potvrzení od návrhů a implementačních kroků jiného chatu a po výslovném potvrzení v tomto chatu zapsala také význam a logiku šesti country atributů. Verze 44 načetla do konce veřejný sdílený chat `https://chatgpt.com/share/6a7b2b60-1100-83eb-9ddb-a20e2f22c825` se 319 viditelnými zprávami, chronologicky auditovala nový blok po verzi 43 ve zprávách 238–319 a znovu jej porovnala se souvisejícími kapitolami, registry i souhrny. Návrhy o dvou turnajích v témže weeku podle nepřekrývajících se hracích období a o odděleném novějším snapshotu pro nasazení nebyly převzaty: první byl nahrazen potvrzeným Week Tournament Lockem první verze a druhý odporoval již dříve rozhodnutému jedinému Tournament Ranking Snapshotu. Verze 45 samostatně auditovala navazující rozhodování po v44 a porovnala je se všemi dotčenými detailními kapitolami, pevnými, prozatímními a otevřenými registry i auditními souhrny. Verze 46 podle výslovného zadání konsoliduje pouze potvrzená rozhodnutí navazující po v45; starší archivy znovu neaudituje. Verze 47 stejným způsobem konsoliduje potvrzenou viditelnou chronologii po v46, celý nový blok znovu porovnává se souvisejícími kapitolami, registry a auditními souhrny a opravuje dřívější povinnost zvolit World a Category Package při založení Runu. Poskytnutý share odkaz `https://chatgpt.com/share/6a7d7172-4b78-83ed-bf7c-01aa527e4153` byl při auditu již smazaný; nebyl proto použit jako důkaz ničeho nad rámec úplné navazující chronologie viditelné přímo v tomto chatu. Verze 48 načetla veřejný sdílený chat `https://chatgpt.com/share/6a8471f7-0408-83ed-b496-1a6187ad7785` celý až k poslední viditelné zprávě, chronologicky oddělila rozhodnutí po v47 od návrhů, směrů a poslední nezodpovězené otázky a nový blok znovu porovnala se všemi dotčenými detailními kapitolami, třemi registry a auditními souhrny. GitHubové implementační detaily, migrace a stav cizího PR nejsou produktovým canonem tohoto dokumentu.

Verze 27 navíc zahrnuje navazující rozhodování vedené do 5. 8. 2026. Tento blok prošel stejnými třemi průchody: kontrolou úplnosti, kontrolou statusů a rozporů a závěrečnou strukturální validací dokumentu. Verze 28, 29, 30 a 31 stejným způsobem zahrnují další navazující rozhodování vedené do 6. 8. 2026; verze 32, 33 a 34 navazují návrhem Run Admin navigace, prvních jejích stránek, predikčního systému a Future Locks vedeným do 7. 8. 2026. Verze 35 stejným způsobem zahrnuje navazující návrh reprodukovatelných Forecast Sessions, adaptivních vizualizací, podmíněného samplingu, práce s jednotlivými scénáři a counterfactual analýzy vedený do 8. 8. 2026. Verze 36 stejnými třemi průchody uzavírá navazující návrh historie světových událostí, technického auditu, upozornění, watchlistů, jednotné závažnosti a jejich Admin/Viewer hranice. Verze 37 stejným způsobem audituje navazující blok o vyloučených podpůrných entitách, zjednodušené geografii a cestování, rekordech, rivalitách a prestiži turnajů. Otázka dalšího rozpracování kariér byla na konci výslovně přeskočena, proto verze 37 nemění již platná kariérní pravidla kapitoly 12.

Nálezy auditu byly následně jednotlivě projednány v navazujícím chatu. Verze 21 zachycuje výsledná rozhodnutí a u odpovědí obsahujících „asi“, „zatím“ nebo obdobnou nejistotu zachovává pouze prozatímní status.

Verze 22 doplňuje jako prozatímní silný směr model „historická pravda + aktuální profil“ pro změnu reprezentované země hráče. Vychází z následné diskuse a studia reálného squashe a dalších individuálních sportů; nejde zatím o definitivně uzavřené pravidlo.

Verze 23 prozatímně zpřesňuje přechod mezi reprezentovanými zeměmi: standardní čekací lhůtu nastavuje na dva fiktivní roky, rozlišuje běžnou účast na MSA Tour od skutečné státní reprezentace, vyžaduje výslovné schválení světovou organizací FAX a určuje, že náhodnost má ovlivňovat především vznik hráčovy úvahy a žádosti, nikoliv dělat ze schválení FAX bezdůvodnou loterii.

Verze 24 souhrnně zachycuje navazující blok rozhodování. Uzavírá jedinečnost názvů Runů, kopírování World a Category Packages do nezávislého Run snapshotu, formální okamžik vstupu prospecta na MSA Tour, možnost úplných historických změn kategoriálního systému a několik pravidel Team World Championship. Dále rozšiřuje prozatímní model změny reprezentované země o základ eligibility, současnou abstraktní úroveň simulace, jedinou běžnou dobrovolnou změnu a možnost předběžného schválení FAX. Význam a vzorec Country Rankingu je výslovně odložen do doby, kdy bude fungovat základ simulace. Zkrácení 122weekové lhůty FAX a pořadí šesti reprezentačních zápasů zůstávají otevřené.

Verze 25 souhrnně zachycuje další ucelený blok navazujícího rozhodování. Doplňuje konfigurovatelnou kapacitu a lock reprezentační soupisky, pevný rankingový snapshot, mimořádné náhrady, neúplnou sestavu a technické W/O v Team World Championship. Uzavírá jedinečné pořadí i tie-break shodných bodů v Official MSA Rankingu, ukládání délky zápasu, povinný budoucí vstup každého generovaného prospecta na Tour a základ vrstev hráčského stavu. Potvrzuje potenciálovou škálu `L+` až `F−`, individuálně vážené OVR, oddělení skutečného stavu od hráčova odhadu soupeře, možnost kariérní i zápasové adaptace stylu a základní zdravotní rozhodování. Přesná matematika všech těchto systémů zůstává záměrně otevřená a bude se zpřesňovat s dalšími verzemi enginu.

Verze 26 ruší dřívější představu povinné blokující setup fáze: Run lze budovat postupně a simulovat každou právě validní dílčí operaci už od prvních vytvořených hráčů, zápasů a turnajů. Doplňuje pevný směr vestavěného read-only Match Test Labu s oddělenými testovacími sessions a historickými snapshoty hráčů z jiných Runů. Upřesňuje, že únava se průběžně přenáší mezi zápasy, turnaji i weeky, skutečný zdravotní stav zná Admin, ale Viewer pouze veřejně známou nebo odhadovanou informaci, a `Inactive` vzniká skutečným rozhodnutím, nikoliv automatickým časovým limitem bez zápasu. Uzavírá recovery draft po pádu a vymezuje Undo/Redo na pracovní relaci, zatímco dlouhodobé návraty používají verze a checkpointy. Budoucí Viewer analytika a FIFA-style FAX hodnocení jsou zachovány jen jako pozdější směr. Přesný determinismus celého Match Enginu byl výslovně přeskočen a zůstává otevřený.

Verze 27 uzavírá další blok Admin workflow a přenositelnosti. CSV/XLSX import probíhá ve staging preview, umí přesně vysvětlit chybu i její opravu a dovolí bezpečný částečný import pouze nezávislých platných řádků. Kopie Runu výslovně volí zdroj při neuložených změnách a nabízí úplný nebo pokročilý rozsah. Lifecycle Runu je uzavřen jako neblokující `Working / Completed / Archived` s oddělenými osami původu, editovatelnosti a validity. Každý uložený platný bod historie lze obnovit nebo použít pro branch; checkpoint je pouze pojmenovaná či technicky připravená záložka. Admin získá interaktivní mapu branchí propojenou s detailní časovou osou a rozdílné simulované historie se nikdy automaticky neslučují. Export má úplný archiv, vlastní výběr a kompaktní snapshot; import mezi verzemi používá bezpečnou migraci bez tiché ztráty dat. Workflow konfliktu stejného `run_id`, dva režimy Compare States pro odlišné weeky a přesné pořadí konfigurační dědičnosti jsou zapsány pouze jako silné směry. Přesné Viewer reveal režimy byly výslovně přeskočeny a zůstávají otevřené.

Verze 28 uzavírá další část každodenní práce s dlouhými Runy. Běžné `Uložit` ukládá vše a pokročilé uložení umí bezpečně vybrat celé logické balíčky změn; každé úspěšné uložení vytváří obnovitelnou verzi. Historie se ukládá rozdílově, deduplikuje a bezztrátově komprimuje bez umělých kvót a bez tichého mazání; Admin ukazuje fyzickou velikost Runů, branchí a datových oblastí, varuje při vysoké spotřebě a blokuje jen operaci, pro kterou skutečně není dost místa. Dlouhá simulace může po zavření okna pokračovat přes Windows tray, lze ji okamžitě pozastavit, bezpečně zastavit po současném zápase nebo jí nastavit libovolný podporovaný budoucí cílový bod. Automatické checkpointy vznikají pouze před rizikovými operacemi, protože každý Save už má vlastní verzi a návrat není na checkpoint vázaný. World a Category Package jsou obsahově nezávislé. Branche téhož Runu mohou mít po odvětvení jiné kalendáře, hráčské atributy i pravidla a společnou minulost ukládají jen jednou. V uživatelském modelu se ruší dojem důležitější Main či Official Branch: právě jednu branch pouze zobrazuje Viewer, a proto se nazývá `Viewer Branch`. Přesný okamžik jejího přepnutí a konečná pravidla souběžných branchových zámků zůstávají otevřená.

Verze 29 zahajuje návrh jednotlivých stránek a globálního aplikačního rámce úplně od začátku, bez přebírání současné struktury naprogramované bety jako cílového návrhu. Pro současnou verzi potvrzuje jedno hlavní okno aplikace a ruší samostatný landing rozcestník Viewer/Admin: běžným vstupem je stránka `Všechny Runy`. Viewer/Admin se přepíná trvale dostupným ovladačem vpravo nahoře. Vedle něj jsou na každé stránce globální volby Runu a prohlížené sezony/weeku; Admin navíc vybírá aktivní branch. Kompaktní volič ukazuje nejvýše pět současných, oblíbených či nedávných Runů nebo branchí a vždy nabízí přechod na úplný přehled. Přepnutí času pouze mění prohlížený kontext a nikdy samo neposouvá ani nevrací simulaci. Volitelný samostatný Viewer v druhém okně zůstává pouze možnou budoucí funkcí.

Verze 30 dokončuje další vrstvu tohoto rámce. `Všechny Runy` je neutrální globální stránka mimo Viewer i Admin a Runy zobrazuje v řádcích; přesný obsah řádků zůstává pouze silným směrem. Kliknutí na Run nabízí otevření jeho `Viewer Branch` na hlavní stránce Adminu, otevření úplné správy branchí nebo otevření Runu ve Vieweru. Admin používá skrývací levý sidebar, zatímco Viewer má stálý vodorovný navbar právě otevřeného veřejného webu. Viewer už není definován pouze jako MSA stránka, ale jako read-only prostředí více samostatných fiktivních webů nad stejným Runem a časem; ikona domečku vede na jejich společný rozcestník a současným hlavním předmětem návrhu je oficiální web MSA. Jeho homepage je živý historický snapshot vybraného season/weeku. Přepínač Viewer/Admin přenáší Run, čas, objekt a pokud možno i stejnou stránku; Viewer vždy mapuje do současné `Viewer Branch` a bezpečný fallback otevře nejbližší smysluplný protějšek s viditelným vysvětlením.

Verze 31 mění kořen aplikace: po spuštění se už neotevřou přímo `Všechny Runy`, ale neutrální `Squash Engine Home`, odkud se vstupuje do globálních oblastí `Runs` a `Packages`. Globální Admin stránky nemají aktivní Run, branch ani week; Viewer na nich nelze otevřít a jeho neaktivní ovladač vysvětlí, že je nejprve nutné vybrat Run. Runový Admin si ponechává celý kontext a používá vlastní hlavní stránku Runu. Sidebar mění obsah podle globálního nebo Runového scope. V Adminu vede logo Squash Engine na globální kořen a obecná Run ikona s názvem na hlavní stránku současného Runu; ve Vieweru vede Viewer logo na rozcestník veřejných webů a logo konkrétního webu na jeho homepage. Ovladač času doplňují stavy `PRESENT / PAST` ve Vieweru a `PRESENT / PAST / FUTURE` v Adminu s rychlým návratem do současnosti. Zdrojové World a Category Packages dostávají vlastní globální Admin stránky, zatímco myšlenka dalších typů, například Player Packages, a jejich pracovní dělení na základní a importní Packages zůstává výslovně pouze silným směrem.

Verze 32 nahrazuje pracovní pojetí Runového Dashboardu stránkou `Home`. Ta je hlavní souhrnnou Admin stránkou konkrétního Runu, zatímco vlastní simulování a hluboké nástroje zůstávají na specializovaných stránkách. Home dostává dva pevné segmentované ukazatele: pozici v 50sezonním rozsahu a pozici v 61weekové sezoně; ostatní obsah se doplní později. Základní skrývací sidebar se při najetí dočasně vysune přes obsah, kategorie rozbalí své podstránky svisle dolů a uživatel jej může připnout. Celý současný seznam kategorií `Home / World / Players / Tour / Rankings & Analytics / Simulation / History / Data / Settings`, jejich pořadí, přesné názvy i podstránky jsou výslovně pouze silným směrem. Stejný status má návrh `World Overview / Countries / Population & Demography / Talent Preview` i pracovní rozdělení rankingových pravidel, výsledných rankingů, Elo, kurzů a statistik.

Verze 33 rozšiřuje dosavadní pracovní `Absolute Prediction` a `Viewer Prediction` do obecného Forecast systému. Nezávazný Forecast nemění Run, branch, seed budoucí reality ani čas a na rozdíl od Candidate Branches vytváří statistický report, nikoliv pokračovatelnou historii. Může začít z podporovaného uloženého bodu, sahat až do velmi vzdálené budoucnosti, používat uživatelem zvolený počet simulací nebo cílovou přesnost a porovnávat hypotetické vstupy. Simulační detail automaticky dědí z časově platného modelu Runu; samostatně lze měnit rozsah reportu, nikoliv potají zjednodušit `Absolute Forecast`. Dlouhodobým silným směrem jsou persistentní Forecast Markets, například světová jednička na konci zvoleného kalendářního roku nebo vítěz příštího Team World Championship, jejichž pravděpodobnosti a kurzy lze ukládat po jednotlivých historických bodech a ve Vieweru skládat do časových grafů. Stejný prozatímní status má univerzální index odchylky na škále `−1 až +1` nebo `0 až 1`; přesný střed, znaménko, vzorec a agregace zůstávají otevřené.

Verze 34 rozšiřuje Forecast o povinné budoucí podmínky `Future Locks`. Forecast slouží jako jejich nezávazná testovací laboratoř a stejnou ověřenou konfiguraci lze následně použít v současné nebo nové skutečné branchi. Lock může mířit do minulosti, přítomnosti i budoucnosti, určit jen jeden údaj nebo velmi podrobný výsledek a pracovat s přesnou hodnotou, rozsahem, minimem, maximem či počtem výskytů. Proveditelnost se odděluje od přirozené absolutní pravděpodobnosti: jakmile ranking, nasazení a pevná pravidla požadovaný stav dovolují, lock může vynutit náhodný los a nutné postupy, aniž by se čekalo na jejich přirozeně vzácnou shodu. Více locků se vyhodnocuje jako pořadím nezávislý celek s individuální i společnou pravděpodobností a identifikací hlavního bottlenecku. Viewer locky nevidí, zatímco Admin uchovává jejich provenance a splněný lock zůstává v historii jako `Fulfilled`. Úsporný Forecast dlouhodobě neukládá jednotlivé virtuální světy, nýbrž pouze agregáty a metadata potřebná pro audit či další zpřesnění. Návrh dvojice dočasných conflict branches a samostatný nenucený `Scenario Direction` jsou výslovně pouze běžnými směry; životní cyklus pozdější úpravy nebo odstranění splněného locku byl na konci dialogu přeskočen.

Verze 35 rozšiřuje tento silný směr o celý pracovní životní cyklus Forecast Session. Jednotlivé vzorky se odvozují z automaticky vytvořeného nebo ručně zadaného 256bitového master seedu a stabilního čísla pokusu; běžně se ukládá jen seed, rozsahy vzorků, vstupní fingerprinty a agregáty, nikoliv miliardy samostatných seedů nebo celých světů. Forecast dostává adaptivní vizualizace, `Highlight` a podmíněný `Focus`, průběžnou kontrolu konvergence, přirozený sampling a oddělený vážený `Rare Event Accelerator`. Konkrétní vzorek lze na vyžádání zrekonstruovat, prohlédnout, připnout, porovnat a explicitně zhmotnit jako branch; samotný Forecast tím nadále žádnou branch automaticky nemění. Nový `Scenario Inspector` doplňuje odhad faktorů odchylky, rychlé i statistické párové counterfactual testy a pravidlo, že minulost před zásahem zůstane stejná, zatímco všechny kauzálně navazující důsledky se znovu nasimulují. Celý tento blok je výslovně pouze prozatímní silný směr; konkrétní názvy, vzorce, samplingové algoritmy, prahy, layouty a implementační pořadí zůstávají otevřené.

Verze 36 odděluje čtyři dosud částečně překrývané vrstvy: World Event Log jako historii faktů fiktivního světa, Audit Log jako historii změn dat a jejich původu, Task Center jako správu běžících a dokončených operací a Notification Center jako vrstvu věcí vyžadujících pozornost. Uzavírá automatická systémová upozornění i uživatelské watchlisty, seskupování opakování, Admin zvonek a filtry podle branche, Runu a globálního scope. V celém enginu nyní platí jednotná závažnost: modrá informační ikona nic neblokuje, oranžový vykřičník varuje bez blokování a červený vykřičník zastaví nebo zablokuje pouze dotčenou operaci či branch. Viewer technická upozornění nevidí; jeho případné veřejné zprávy vycházejí jen z veřejně známých světových událostí.

Verze 37 rozhodnutě vylučuje z modelu trenéry, podpůrné týmy, agenty a tréninková centra jako samostatné entity. V principu zavádí vzájemně nezávislé `Travel Regions` a kruhově uspořádané `Timezone Areas`; první verze používá pouze hrubé přechody mezi oblastmi a časový odstup jako náhradu za aklimatizaci, zatímco přesné vzdálenosti, pobyt hráče a matematika zůstávají odložené. Jako směry přidává individuální `Jet Lag Resistance` a `Travel Resilience`, vícečlenné a překrývající se rivality, ruční doplnění rivality z nesimulované juniorské historie a transparentní použití Scenario Direction bez záměny za Forced Lock. Potvrzuje velké množství rekordů napříč Viewerem a Adminem; jednotná služba a úplná posloupnost držitelů jsou jen slabým směrem. Turnajová prestiž je běžným směrem: Tournament Series může mít vlastní proměnlivé `Prestige Score`, kategorie dodává typickou výchozí hodnotu, změna kategorie prestiž neresetuje a Admin ji může upravit či zamknout. Individuální `Tournament Appeal` je pouze slabý směr a přesné podmínky kurtu patří až do pozdější verze.

Verze 38 audituje navazující rozhodování vedené do 9. 8. 2026. Potvrzuje, že každý hráč používá vlastní individuální AI, jejíž přesné chování se bude kalibrovat až nad funkční první verzí, a doplňuje běžný směr faktorového dobrovolného retirementu a slabý směr porovnávání možností `Active / Inactive / retired`. Automatické veřejné zprávy odvozené z autoritativních World Events nově rozhodnutě patří na historickou MSA homepage; samostatná stránka `News` zůstává otevřená, soukromý Admin digest je jen směr a `News Importance Score` pouze slabý směr. Pro první verzi se zavádí samostatný `Week Transition`, týdenní development používající stav a historii známé nejpozději do konce právě skončeného weeku a globální proměnlivá posloupnost `Simulation Slots` se současnými událostmi nad společným vstupním snapshotem. Současně uzavírá základ akcí `Simulate Next Slot` a děleného `Simulate Next Match`. Vztah slotů k dříve odloženým procesním oknům, jejich přesný počet a jakékoli minimum sedmi oken zůstávají výslovně nerozhodnuté.

Verze 39 audituje další navazující rozhodování vedené do 9. 8. 2026. Pro první verzi uzavírá `Season Transition` jako speciální rozšíření Week Transitionu při přechodu ze Season Weeku 61 do Weeku 1, atomickou aktivaci nových sezonních pravidel, scoped resety a lehký `Season Closure Marker`. Budoucích všech 50 sezon lze plánovat pomocí úsporných `Inherited Plans`; samostatný Draft a nové Tournament Editions vznikají až při editaci, hromadném potvrzení nebo potřebě simulace, přičemž individuální overrides zůstávají chráněné. Tournament Edition dostává odvozený lifecycle, detailní komponentní stavy a z nich vypočtený veřejný `Public Stage`. Každá Edition má historicky platný `announcement_week`; Viewer i hráčská AI smějí turnaj znát až od veřejného World Eventu, běžné oznámení musí předcházet první provozní události alespoň o jeden week a pozdější veřejné změny používají samostatný Tournament Update s mimořádnou emergency výjimkou. Entry rozhodnutí jednoho slotu se vyhodnocují ze společného snapshotu, zapisují transakčně a neúspěšný retry nesmí bezdůvodně přehodit nesouvisející výsledky. Přihláška je samostatný historický objekt. Společné portfolio více turnajů a formální mimořádné ukončení rozběhnuté Edition zůstávají pouze běžnými směry; konkrétní Admin lifecycle akce jsou jen silným směrem.

Verze 40 stejnými třemi průchody audituje navazující rozhodování vedené do 10. 8. 2026 a uzavírá základ Match Enginu pro první verzi. Každý zápas se simuluje rally po rally, nikoliv shot-by-shot; rally prochází skrytým vícefázovým procesem s pěti stavy kontroly a tlaku, individuální fyzickou zátěží a odděleným sportovním i oficiálním vyhodnocením. Pevně zavádí tři samostatně trénovatelné stamina systémy, jejich kapacitu, aktuální stav a recovery, průběžné přepočítání po každé rally, omezené vnímání hráčskou AI a změny úsilí i během rally. Rally log první verze ukládá kompaktní sportovní příčinu, oficiální rozhodnutí, délku, odhad počtu úderů a stav všech tří stamina systémů obou hráčů. Podání je zohledněno jako slabší úvodní vliv odpovídající squashi a interference používají správné zjednodušené `No Let / Yes Let / Stroke`; chyby rozhodčích, detailní review a úmyslné zdržování jsou vědomě přesunuty do pokročilejší verze. Přesné vzorce, číselné škály, kalibrace a detailní okrajové situace zůstávají otevřené.

Verze 41 nemění žádné produktové pravidlo vlastním rozhodnutím. Po úplném tříprůchodovém auditu obou archivů proti Masteru v40 opravuje především záměnu rally za bod u autoritativního rally logu, neprokázaný přesný tříweekový cut-off jet lagu, neprokázané univerzální minimum `roster_capacity`, neprokázaný způsob generování běžné mezery mezi rally a nepřesné zahrnutí pre-Tour prospectů do filtru MSA rankingu. Doplňuje opomenutý potvrzený princip existence hráčských rivalit, takže souvislý pevný registr nyní obsahuje 227 bodů; dále odděluje prozatímní detaily od pevného souhrnu a sjednocuje zápis statusových značek. Následný porovnávací i konfliktní audit výsledné verze nenašel nevysvětlenou kolizi.

Verze 42 audituje navazující rozhodování vedené 10. 8. 2026. Zpřesňuje sezonní `Best N`: první sezona Official Runu začíná s Best 15 a každá další jako svůj výchozí návrh převezme efektivní hodnotu předchozí sezony, přičemž zůstává samostatně konfigurovatelná. Uzavírá první kontrakt jediné aktuální Form, její aktualizace po každém odehraném zápase, návratu k individuálnímu normálu, zvláštních výsledkových statusů a omezeného odhadu hráčskou AI. Doplňuje zjednodušenou zdravotní přestávku, Official Run defaulty tří minut pro ni a dvou minut mezi gamy, obnovu bez resetů a autoritativní časové události v logu. Pro první verzi rozhodnutě zavádí `Match Reconstruction`: ručně zadaná fakta tvoří constraints, Admin si volí počet kandidátů, prohlíží jejich kompaktní přehled a úplný read-only detail a pouze výslovně vybraný kandidát se stane historií. Výchozích deset kandidátů, zapamatování posledního počtu, přesná statistická/probability architektura, retence session a obsah kompaktní karty zachovávají nižší statusy podle skutečných formulací uživatele. Souvislé registry po auditu obsahují 239 pevných, 77 prozatímních a 68 otevřených bodů; následná kontrola nenašla nevysvětlený rozpor.

Verze 43 audituje navazující rozhodování vedené 10.–11. 8. 2026 a návrhy z výslovně předloženého druhého chatu. Pro první verzi zavádí šest ručně zadávaných country ratingů a jejich přesné významové hranice, přičemž země ovlivňuje sampling, objevení, rozvoj, soutěžní zkušenost a přechod k profesionálům, nikoliv vrozený talent nebo národní herní DNA. Opravuje starší formulaci tří stamina systémů: `Explosive Stamina`, `Rally Stamina` a `Match Stamina` jsou dynamické fyzické bary odvozené z podkladových atributů a stavu, ne tři samostatně authorované dlouhodobé schopnosti s již rozhodnutým tréninkovým workflow. Přidává dva dynamické mentální bary, kontextové vážení jednotlivých atributů, krokové simulační akce, dočasnou pracovní časovou osu, Auto Play, read-only Match Replay, základní Viewer Scores a rozšířený kandidátní workflow Match Reconstruction. Přesná atributová taxonomie, trénink, matematika country pipeline, barů, indexů, vynuceného hledání a UI zůstávají v odpovídajících prozatímních, otevřených nebo odložených statusech. Závěrečný strukturální audit potvrdil souvislé registry 250 pevných, 80 prozatímních a 69 otevřených bodů a nenašel žádnou nevysvětlenou obsahovou kolizi.

Verze 44 audituje navazující rozhodování vedené 11. 8. 2026. Pro první verzi uzavírá společné přehodnocení všech dostupných turnajů hráčskou AI v každém entry decision slotu, zveřejnění předběžného entry listu až po dokončení slotu, neomezený počet předběžných přihlášek a stavově závislé řešení jejich konfliktů. Doplňuje rankingový odečet a časově omezenou, samostatně se skládající disciplinární nulu, univerzální ruční Admin override s technickou integritou, jednorázový či uzamčený zásah do přihlášky a zdravotní výjimku ze sankce. Zavádí Week Tournament Lock pro všechny oficiální soutěže, podmíněný stav `Still Competing`, Final Commitment, zjednodušenou proveditelnost přesunu, tříúrovňový Travel Load a automaticky generovaný editovatelný Round Schedule nad Simulation Slots. Přesná AI, číselné sankce a jejich délky, umístění deadlines, travel prahy, detailní logistika a budoucí výjimky z jednoho turnaje na week zůstávají otevřené nebo odložené. Dříve rozhodnutý jediný Tournament Ranking Snapshot zůstává beze změny a platí pro celý entry i draw proces. Závěrečný strukturální audit potvrdil souvislé registry 260 pevných, 80 prozatímních a 69 otevřených bodů a nenašel žádnou nevysvětlenou obsahovou kolizi.

Verze 45 audituje navazující rozhodování vedené 11. 8. 2026 od Masteru v44. Pro Qualification i Main Draw samostatně uzavírá tři fáze oprav losu: úplné přelosování před `Redraw Cutoff`, seed cascade do `Draw Freeze` a následné doplňování konkrétních fyzických slotů. Zpřesňuje atomické zpracování souběžných změn, zachování seed čísel, hráčský replacement cutoff, WC rezervy a identitu LL. Uzavírá rankingový BYE unlock, aditivní kvalifikační a Main Draw složku jednoho turnajového výsledku, `Ranked / Unranked` Tournament Editions a publikační podmínku úplné bodové tabulky u Ranked Edition. První verze má prize money nepovinné; pokud jsou nakonfigurované, používá úplnou výplatní, historickou a souhrnnou logiku včetně kvalifikace, Main Draw a neúplných tabulek. Bodová tabulka Edition se přebírá z konfigurace její kategorie pro danou sezonu a nová sezonní tabulka kategorie se předvyplní z bezprostředně předchozí sezony. Závěrečný audit odstranil jednu duplicitní Markdown odrážku, potvrdil souvislé registry 276 pevných, 80 prozatímních a 69 otevřených bodů a nenašel nevysvětlenou obsahovou kolizi.

Verze 46 konsoliduje pouze navazující potvrzené rozhodování po Masteru v45. Upřesňuje výchozí a přednastavený původ `Ranked / Unranked`, povolené změny statusu před a po oznámení, mimořádné odebrání Ranked statusu bez přepisování už známé historie a plné sportovní následky Unranked zápasů. Uzavírá základ `Cancelled`, `Postponed`, `Suspended` a `Abandoned`, včetně zachování identity Edition, dvou režimů odkladu, uvolnění hráčů a Week Tournament Locků, bodů a nakonfigurovaných výplat při nedokončení a rozlišení zahájeného `ABN` zápasu od neodehraného slotu. Pro první verzi také zavádí vnější nezaviněné přerušení živé rally jako `Yes Let` bez bodu se zopakováním rally ze stejného skóre. Hranice, kdy se krátké přerušení mění na `Suspended`, byla výslovně přeskočena a zůstává otevřená; neprojednaný vztah Protected Rankingu k nasazení ani LL se nemění. Závěrečná kontrola potvrdila souvislé registry 292 pevných, 79 prozatímních a 69 otevřených bodů bez nevysvětlené obsahové kolize.

Verze 47 konsoliduje navazující rozhodování vedené do 13. 8. 2026. Opravuje starší povinnost vybrat při založení právě jeden World a Category Package: Run nyní rozhodnutě může vzniknout úplně prázdný a Packages jsou volitelné jednorázové zdroje bez živého propojení. Uzavírá pět typů World/Category/Series/Calendar/Setup, měkké závislosti, zachování unresolved referencí, neúplné Setupy, hierarchii Competition System / volitelný Tour / Category, stabilní číselná ID, rozsah a merge Calendar Packages i export ručně vytvořeného obsahu Runu. Tournament plánování doplňuje `Edition Plan` oddělený od Edition a denní Match Schedule první verze s uloženým pořadím, fair-rest a feeder pravidly. Přesná hranice Series versus Calendar polí a více Editions jedné Series v sezoně zůstávají silnými směry; merge konflikty, mapování a detailní scheduler matematika zůstávají otevřené. Poskytnutý share odkaz byl již smazaný, proto audit vycházel z úplné navazující chronologie viditelné přímo v tomto chatu. Závěrečná kontrola potvrdila souvislé registry 308 pevných, 81 prozatímních a 69 otevřených bodů bez nevysvětlené obsahové kolize.

Verze 48 konsoliduje navazující rozhodování vedené do 18. 8. 2026 a celý poskytnutý veřejný share načítá až k poslední viditelné zprávě. Uzavírá source identity a Run-local ID Package entit, verzování a lifecycle Packages, bezpečný opakovaný i selektivní import, exact-scope export, Setup version snapshot, sezonní kategoriální hierarchii a tier hranice, pevné rozdělení Series/Calendar, materializaci Edition Plans, více Editions jedné Series, jejich číslování a rozdíl mezi odstraněním neveřejného Draftu a změnou veřejně známé historie. Ruční kanonický merge a divergentní historie stejného Package zůstávají silnými směry, shodný `tier_rank` je odložený a poslední nezodpovězený návrh neměnných Draw Versions zůstává otevřený. Pokročilé očekávání pravidelných turnajů hráčskou AI patří až do pozdějších verzí; první verze používá pouze veřejně potvrzené informace. Závěrečný audit potvrdil souvislé registry 335 pevných, 84 prozatímních a 69 otevřených otázek bez nevysvětlené obsahové kolize.

Verze 48a nemění žádné sportovní ani produktové pravidlo. Nad úplným obsahem v48 zavádí stabilní označení širokých otevřených okruhů `OQ-001–OQ-069` a samostatnou pre-alpha rozhodovací mapu. Ta rozpadá dosavadní široké body a nově odhalené mezery na atomické otázky `PAQ-001–PAQ-150`, rozlišuje jejich prioritu `PA0 / PA1` a vlastníka `PRODUCT / TECH / CALIBRATION / CONTENT` a u každé uvádí konkrétní příklad. Jde výhradně o backlog: jeho zápis nic neuzavírá, nezvyšuje status žádného směru a nevrací do první verze výslovně odložené funkce. Pevný, prozatímní a široký otevřený registr proto zůstávají na 335 / 84 / 69 bodech.

Verze 49 konsoliduje navazující viditelnou chronologii po v48a vedenou do 19. 8. 2026. Uzavírá jediný povinný uživatelský údaj pro vznik Runu, aktivní pre-alpha katalog 57 samostatných atributů na škále `0–200`, rozsah a význam OVR, pevný celoživotní typ načasování vývoje, dvousložkovou Experience, samostatný `Match Sharpness` a zjednodušenou `Match Preparation` ze studia soupeře a cíleného tréninku na kurtu. Potenciál dostává jeden skrytý měkký `Potential OVR`; jeho číselná mapa, distribuce vývojových typů a věkové středy jsou kvůli uživatelským formulacím „orientačně“ a „zatím“ pouze prozatímními defaulty. Přesné vzorce, kalibrace, hluboký trénink a jemné rally projevy určené pro verzi 3+ se neuzavírají. Verze také opravuje chybnou formulaci `PAQ-046`, která ve v48a směšovala atributovou škálu s oddělenými potenciálovými labely. Poskytnutý share odkaz `https://chatgpt.com/share/6a85e73c-65a0-83eb-a268-369e1d64d482` nebyl v tomto prostředí načitatelný; audit proto nepřisuzuje odkazu žádný obsah nad úplnou navazující chronologii viditelnou přímo v tomto chatu.

Verze 50 načetla veřejný sdílený chat `https://chatgpt.com/share/6a8c8e23-7580-83eb-af7b-e1fef59c12e0` celý až k jeho poslední viditelné zprávě, chronologicky oddělila nový blok po v49 od staršího obsahu a následně jej porovnala se všemi dotčenými detailními kapitolami, registry `ROZHODNUTO / PROZATÍMNÍ / OTEVŘENO`, pre-alpha bránou a auditními souhrny. Poslední viditelnou zprávou snapshotu byla otázka na minimální vstupy `Rally Setupu`; bezprostředně navazující uživatelské „ano“ a výslovný pokyn aktualizovat Master jsou součástí tohoto auditu jako přímé pokračování. Verze uzavírá dva povinné akceptační průchody pre-alpha, pracovní hranici Draft/Save/Viewer, přesné pořadí Week a Season Transitionu, Season Closing Ranking, skupinovou atomickou hranici uvnitř Simulation Slotu, tři pre-alpha režimy historického dopočtu vývoje, zdravotní minimum, experimentální `Financial Level 0–10` a úplný minimální seznam `Rally Setupu`. Samostatné osy rozsahu a míry zachování regenerace byly výslovně odloženy; ligový squash se v první verzi vůbec nemodeluje a přesná matematika nových systémů zůstává kalibrací. GitHub ani implementace nebyly při této obsahové aktualizaci měněny.

Verze 51 načetla veřejný sdílený chat `https://chatgpt.com/share/6a905d6e-ceb8-83eb-843b-8e62623a8024` celý až k jeho poslední viditelné zprávě a chronologicky oddělila blok po v50 od staršího obsahu. Potvrzuje, že `Run` je kořen celého samostatného stromu historie, nikoliv jedna sezona, a že samotné úspěšné založení Runu se automaticky počítá jako jeho první uložená verze. Současně zavádí oddělenou evidenci ověřené implementace: proti aktuálnímu `buuk` byly zkontrolovány sloučené PR [#670](https://github.com/Jasmetk0/squash-tour-beta/pull/670) a [#671](https://github.com/Jasmetk0/squash-tour-beta/pull/671), jejich přesné Git stromy, integrační hranice, testy a známá omezení. Technické volby z kódu nebyly automaticky povýšeny na produktová rozhodnutí. Poslední návrh automatických názvů dalších branchí `Timeline 2 / Timeline 3` zůstal bez uživatelské odpovědi, a proto je ve v51 pouze otevřenou otázkou. Registry nyní obsahují 381 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 17 vyřešených. GitHub ani implementace nebyly při této dokumentační aktualizaci měněny.

Verze 52 navazuje úplnou viditelnou chronologií po v51. Uživatelská volba `možnost 1` uzavírá `PAQ-157`: počáteční branch se automaticky jmenuje `Timeline 1`, každá další běžná branch dostane návrh prvního nepoužitého `Timeline N` a uživatel jej může před vytvořením nahradit vlastním jedinečným názvem. Po následné implementaci byl proti aktuálnímu `buuk` samostatně zkontrolován sloučený [PR #672 – Create Run branches from Saved Revisions](https://github.com/Jasmetk0/squash-tour-beta/pull/672), jeho přesný Git strom, veřejné API, atomická persistence, migrace, testy a známé hranice. Implementační záznam `IMP-003` nevydává obecný Save, přenos rozpracovaného Working Draftu, frontend ani branch merge za hotové. Registry nyní obsahují 382 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 18 vyřešených. GitHub ani implementace nebyly při této dokumentační aktualizaci měněny.

Verze 53 načetla veřejný sdílený chat `https://chatgpt.com/share/6a913db5-e77c-83eb-8261-ddcf2772a6f5` až k jeho poslednímu dostupnému stavu a dokončila dokumentační handoff, který byl v předchozí relaci přerušen těsně před bezpečným uložením a výběrem dalšího řezu. Porovnání s dodanou v52 potvrdilo, že už obsahuje všechna věcná uživatelská rozhodnutí a výslovné hranice z tohoto bloku: šest organizačních kategorií a 57 atributů jako výrazně rozšiřitelný pre-alpha základ, uzavřené pojmenování branchí `Timeline N`, ověřený rozsah sloučeného PR #672 i odlišení branche z čisté Saved Revision od akce `Nová branch z Working Draftu`. Nechyběl žádný nový produktový bod ani implementační údaj, proto verze 53 nemění statusy ani počty registrů. Doplňuje pouze auditní uzavření a závaznou pokračovací hranici: pro další návrh a implementaci je tento Master soběstačným zdrojem pravdy a starý chat slouží už jen jako historická provenance, nikoliv jako povinný podklad.

Verze 54 nemění produktový canon ani stav žádné `PAQ`. Proti cílové branchi `buuk` samostatně ověřuje sloučený [PR #673 – Save Viewer Branch changes through Working Drafts](https://github.com/Jasmetk0/squash-tour-beta/pull/673), jeho merge a feature commit, totožný otestovaný Git strom, veřejné API, atomickou persistence hranici, migraci, testy a známá omezení. `IMP-004` eviduje pouze první konkrétní draftový typ `set_viewer_branch`; nevydává obecné ukládání všech budoucích změn, historii revizí ve veřejném API, restore, recovery ani frontend za hotové. Registry proto zůstávají 382 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 18 vyřešených. Dalším technickým řezem je bezpečný read-only přístup k úplné dosažitelné Saved Revision historii zvolené branche, aby existující branch-from-historical-revision workflow nepotřebovalo znát revision ID z interní persistence.

Verze 55 nemění produktový canon ani stav žádné `PAQ`. Proti cílové branchi `buuk` samostatně ověřuje sloučený [PR #674 – Expose validated Saved Revision history](https://github.com/Jasmetk0/squash-tour-beta/pull/674), jeho merge a feature commit, totožný lokálně otestovaný Git strom, obě read-only API, fail-closed validační hranici, testy a známá omezení. `IMP-005` eviduje pouze čtení úplné dosažitelné lineage a scopeovaného revision detailu; nevydává stránkování, restore současné branche, porovnávací UI, veřejné čtení Audit Eventů, recovery, nové draftové typy ani frontend za hotové. Registry proto zůstávají 382 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 18 vyřešených. Bezprostřední pokračování se přesouvá od dalšího kódového řezu k postupnému uzavírání dosud otevřených `[PA0][PRODUCT]` otázek; až se implementace znovu otevře, prvním kandidátem je bezpečné obnovení současné branche z vybrané Saved Revision podle již rozhodnutých pravidel historie a předobnovovacího checkpointu.

Verze 56 konsoliduje první navazující blok pěti výslovně potvrzených `[PA0][PRODUCT]` odpovědí. `PAQ-023` zavádí nedestruktivní partial-scope kontrakt pro všech pět současných Package typů. `PAQ-024` uzavírá minimální bezpečný workflow chybějící či nekompatibilní závislosti včetně `Unresolved`, oranžového upozornění a červeného blokování teprve dotčené operace. `PAQ-027` pro pre-alpha odmítá automatický i ruční kanonický merge divergentních historií stejného `package_id` a dovoluje příchozí větev zachovat jen jako výslovně vytvořený samostatný Package s novou identitou a provenance. `PAQ-029` určuje, že neúplný Setup aplikuje pouze obsažená validní data, nic si nedomýšlí a chybějící části neblokují nesouvisející práci. `PAQ-030` uzavírá sedmifázové procesní pořadí Simulation Slotu jako testovatelný kontrakt první pre-alpha verze s možností pozdější vědomé revize. Registry se tím mění na 387 pevných, 87 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 23 vyřešených a 134 otevřených. Ověřená implementační hranice zůstává beze změny po PR #674.

Verze 57 konsoliduje další čtyři výslovně potvrzené `[PA0][PRODUCT]` odpovědi. `PAQ-034` uzavírá hierarchickou prerequisite matici podporovaných simulačních akcí a potvrzuje, že červená chyba blokuje jen zvolený rozsah a jeho skutečné závislosti. `PAQ-036` zavádí jedinou autoritativní globální osu Simulation Slots, na kterou se procesní okna a turnajové Match Day Slots pouze mapují. `PAQ-042` přesně určuje první `NR` období nového Tour Playera, jeho zahrnutí až do následujícího Official Ranking snapshotu a zákaz jakéhokoli zvláštního přidělení bodů před rankingem. `PAQ-043` uzavírá povinné jádro hráčského profilu, definitivní rozlišení shodných jmen a historickou `Sporting Representation` tří typů `Country / World / FAX Neutral`; World je dobrovolná globální identita, zatímco FAX Neutral je oddělený regulační status. Registry se tím mění na 391 pevných, 86 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 27 vyřešených a 130 otevřených. Ověřená implementační hranice zůstává beze změny po PR #674.

Verze 58 konsoliduje pět dalších výslovně potvrzených produktových odpovědí `PAQ-051 / 053 / 066 / 067 / 115`. Pre-alpha dostává agregovaný `General Training Load` se čtyřmi úrovněmi a omezenou AI volbou, čtyřosý aktivní model stylu a gameplanu, kontextové skládání atributů `Primary / Supporting / Constraint` a vrstvený Rally Resolution Record založený na skutečných squashových pravidlech. Terminální událost, pravidlový kontext, finální verdikt, změny skóre, analytické připsání a vedlejší incidenty se již nesmějí slévat do jednoho enumu. Minimální `ball hit / turning / further attempt` se přesouvá do pre-alpha jako sada pravidlových flagů; shot-by-shot trajektorie, chyby rozhodčích a detailní video review zůstávají pozdější. Registry se tím mění na 395 pevných, 86 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 32 vyřešených a 125 otevřených. Ověřená implementační hranice zůstává beze změny po PR #674.

Verze 59 konsoliduje potvrzené `PAQ-064 / 065 / 068 / 069 / 070` a završuje první funkční kostru skrytého průběhu rally. Pět stavů kontroly používá lokální setrvačné přechody bez umělého střídání; rally má 0–24 abstraktních segmentů, takže může skončit už podáním či prvním returnem a současně nemůže uváznout v nekonečné smyčce. Engine nejprve vytvoří sportovní pravdu a verzovaný rules resolver z ní v pre-alpha bez náhodné chyby rozhodčího odvodí správný bod, `No Let`, `Yes Let` či `Stroke`. Podání nemá obecný server bonus ani skrytý trvalý modifier a ovlivňuje pouze opening ve společném souboji Serve Execution × Return Execution. Délka, počet úderů, tempo a zátěž vznikají kauzálně z téhož průběhu a používají verzovaný `RallyCalibrationProfile`. Starší studie publikovaná roku 2016 zůstává pouze historickou kontrolou; současný mužský pre-alpha benchmark vychází hlavně z větší PSA analytiky a novější práce nad zápasy 2018–2020, přičemž číselné koridory jsou výslovně prozatímní. Registry se mění na 400 pevných, 87 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 37 vyřešených a 120 otevřených. Ověřená implementační hranice zůstává beze změny po PR #674.

Verze 60 uzavírá `PAQ-071` a přesouvá do pre-alpha také rozdílné hráčské tempo mezi rally a jeho vědomé taktické použití. Každý hráč může mít jinou přirozenou tendenci na podání a returnu a v konkrétní situaci zvolit zrychlení, přirozené tempo nebo zpomalení podle únavy, skóre, momenta, gameplanu a odhadu soupeře. Skutečný další servis vznikne až ze společné připravenosti servera, receivera, rozhodčího a kurtu; uplynulý čas se započítá oběma hráčům právě jednou a taktika nemá magický přímý bonus. Přehnané bezdůvodné zdržování vstupuje do zjednodušeného deterministického rules/conduct resolveru, zatímco individuální chyby a profily rozhodčích zůstávají pozdější. Registry se mění na 401 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 38 vyřešených a 119 otevřených. Ověřená implementační hranice zůstává beze změny po PR #674.

Verze 61 nemění produktový canon ani stav žádné `PAQ`. Proti cílové branchi `buuk` samostatně ověřuje sloučený [PR #675 – Add guarded Saved Revision restore workflow](https://github.com/Jasmetk0/squash-tour-beta/pull/675), jeho merge a feature commit, totožný Git strom, atomickou persistence hranici, pre-restore checkpoint, optimistické concurrency podmínky, první frontend historie revizí a relevantní testy. `IMP-006` eviduje pouze podporovaný současný pre-alpha rozsah: prázdný kanonický Run bez sporting či legacy stavu. Nevydává obnovu kompletního simulovaného světa, obecný checkpoint browser, úplný Audit Log, Compare States, recovery draft ani stránkování za hotové. Registry proto zůstávají 401 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 38 vyřešených a 119 otevřených. Dalším úzkým technickým kandidátem je validované read-only zpřístupnění pre-restore checkpointů a souvisejících revision Audit Eventů, aby byla nově vytvořená safety vrstva v Adminu skutečně dohledatelná a prakticky použitelná přes již existující preview a restore workflow.

Verze 62 načítá do konce veřejný sdílený chat `https://chatgpt.com/share/6a94633b-6a44-83eb-aef3-73bc8b3e7b2e`, odděluje skutečná uživatelská potvrzení od návrhů a konsoliduje deset odpovědí `PAQ-072–081`. Uzavírá oficiální Match Format fallback, rally snapshot/replay kontrakt, minimální turnajové entity, úplné pořadí povolené dědičnosti, materializaci virtuálních plánů, číslování více Editions, třívrstvý lifecycle, historicky verzované veřejné změny, hranici `Postponed / Cancelled / Suspended / Abandoned` a deterministické fair-rest priority scheduleru. Orientační odhad rychlosti generování a velikosti zápasu se na výslovné přání nezapisuje jako produktové rozhodnutí a nezodpovězená `PAQ-082` zůstává otevřená. Registry se mění na 411 pevných, 88 prozatímních a 69 širokých otevřených bodů; z 157 atomických `PAQ` je 48 vyřešených a 109 otevřených. Samostatná evidence `IMP-007` ověřuje sloučený PR #676 pouze v jeho úzkém read-only recovery-activity rozsahu.

---

Verze 63 načetla celý dostupný veřejný snapshot `https://chatgpt.com/share/6a9f3f69-657c-83eb-b675-47e339d5528d` až po závěrečné předání PR #686. Snapshot obsahoval 6 069 uzlů časové osy; část nástrojových výstupů byla výslovně skrytá a nebyla použita jako důkaz obsahu kódu. Navazující věcný blok po předání v62 byl porovnán s Masterem, PR #677–686 a současnými zápasovými kontrakty. GitHub při aktualizaci potvrdil všech deset merge do `buuk`, včetně #686 dne 7. 9. 2026 v 22:48:54 UTC. Po v62 už uživatel nezavřel další produktovou otázku: zadával pokračování programování a sloučení. Verze 63 proto nepovyšuje návrhy, implementační proxy ani kalibrační koeficienty na nové rozhodnutí. Doplňuje IMP-008–017, schémata, kompatibilitu, známé testové mezery a pokračovací hranici. PAQ-082 zůstává přeskočená a otevřená; orientační rychlost generování a velikost jednoho zápasu se na přání uživatele nadále nezapisují. Obsah potřebný k navázání je přímo v kapitole 35; odkaz na chat zůstává pouze provenance tohoto konsolidovaného bloku.

## Jak číst stav jednotlivých bodů

- **[ROZHODNUTO]** – současné platné pravidlo v rozsahu uvedeném u daného bodu. Neznamená automaticky, že musí být stejné ve všech Runech. Stále je lze někdy v budoucnu vědomě změnit, ale do té doby se podle něj navrhuje a programuje.
- **[PROZATÍMNÍ]** – pracovní pravidlo nebo silný směr, který lze používat při návrhu, ale před definitivním uzavřením se k němu ještě vrátíme.
- **[CÍLOVÁ FUNKCE]** – požadovaná schopnost výsledného enginu; její přesná pravidla nebo rozhraní ještě nemusí být hotová.
- **[OTEVŘENO]** – otázka zatím nemá odpověď.
- **[ODLOŽENO]** – záměrně se vyřeší později, protože je složitý nebo teď není prioritní.
- **[POZDĚJI]** – funkce plánovaná až pro některou budoucí verzi, ne pro současný rozsah.
- **[STARŠÍ NÁVRH]** – zachovaná myšlenka z dřívější dokumentace; bez nového potvrzení není canonem.

Kapitola 35 používá druhou, zcela nezávislou osu pro stav kódu:

- **[IMPLEMENTOVÁNO A OVĚŘENO]** – uvedený přesný rozsah je ve jmenovaném commitu nebo PR sloučený do evidované cílové branche a jeho relevantní chování bylo ověřeno kontrolou kódu a testy.
- **[ČÁSTEČNĚ IMPLEMENTOVÁNO]** – naprogramovaná je pouze výslovně vyjmenovaná část širšího pravidla; zbytek se nesmí domýšlet.
- **[IMPLEMENTAČNĚ OTEVŘENO]** – navazující schopnost v evidovaném řezu chybí, nebyla ověřena nebo čeká na další rozhodnutí.

Tyto značky nikdy nenahrazují `[ROZHODNUTO / PROZATÍMNÍ / OTEVŘENO]`. Kód může realizovat rozhodnutí, ale nemůže je zpětně vytvořit. Naopak nepřítomnost bodu v implementačním registru neprokazuje, že v celém repozitáři nic podobného neexistuje; znamená pouze, že pro tuto verzi Masteru nebyl jeho přesný stav auditován.

Pre-alpha backlog navíc používá dvě samostatné pracovní osy, které **nejsou stavem rozhodnutí**:

- **[PA0]** – před uzavřením behaviorální specifikace pre-alpha musí existovat jednoznačná odpověď nebo výslovně schválený minimální default; jinak může stejný vstup vést k neurčitému výsledku.
- **[PA1]** – pro použitelnou end-to-end pre-alpha musí existovat minimální funkční chování, bezpečný dočasný default nebo vědomý stub; přesná kalibrace může pokračovat nad fungujícím enginem.
- **[PRODUCT]** – viditelné produktové nebo sportovní pravidlo, které nesmí implementace sama domyslet.
- **[TECH]** – implementační kontrakt, který lze zvolit autonomně, pokud zachová všechny rozhodnuté invarianty a uživatelsky viditelné chování.
- **[CALIBRATION]** – číselný model, který potřebuje testování; před pre-alpha musí mít reprodukovatelný výchozí profil, nikoliv nutně finální realistické hodnoty.
- **[CONTENT]** – konkrétní obsah Official Runu. Engine musí umět jeho datový tvar, ale jednotlivé názvy, tabulky či kalendáře nejsou automaticky Engine invariantem.

Například otázka `PAQ-072 [PA0][PRODUCT]` zůstává nezodpovězená produktová otázka o dědění match formátu; označení `PA0` z ní samo nedělá rozhodnutí.

Přívlastky jako **„v principu“** nebo **„pro současnou verzi“** pouze zpřesňují rozsah rozhodnutí: základ funkce je potvrzený, ale její detail nebo vzdálená budoucnost může zůstat otevřená.

### Dvě nezávislé osy: stav rozhodnutí a rozsah pravidla

Stav `[ROZHODNUTO]`, `[PROZATÍMNÍ]`, `[OTEVŘENO]` atd. říká, **jak jisté rozhodnutí je**. Samostatně se musí určit, **kde pravidlo platí**:

- **[ENGINE INVARIANT]** – technická schopnost nebo kontrakt platný pro všechny Runy současné verze.
- **[RUN CONFIG]** – hodnota či pravidlo uložené v konkrétním Runu, balíčku, sezoně, kategorii, Tournament Edition nebo jiné konfigurační vrstvě.
- **[OFFICIAL RUN DEFAULT]** – canon a současné výchozí nastavení pro Official Run. Jiné Runy je smějí změnit; při tvorbě nebo editaci se tato hodnota může nabízet předvyplněná.
- **[OVERRIDE]** – vědomá výjimka na užší úrovni, například jeden turnaj nebo jedno kolo.

Rozhodnutí tedy může být současně například:

- **pevně rozhodnuté jako schopnost enginu**, že každá sezona má upravitelnou Ranking Policy;
- **pevně rozhodnuté jako Official Run default**, že první sezona používá Best 15 a každá další výchozím způsobem převezme efektivní Best N předchozí sezony;
- **prozatímní jako Official Run default**, že hodnota PR používá průměr prvních 15 snapshotů.

**[ROZHODNUTO][ENGINE INVARIANT]** Konfigurovatelná sportovní pravidla se historicky ukládají společně se stavem, ve kterém platila. Změna budoucí sezony nesmí přepsat pravidla starých sezon, turnajů, zápasů, rankingových snapshotů ani již uzamčených policy cases.

**[ROZHODNUTO][ENGINE INVARIANT]** Pokud se pravidlo může mezi Runy nebo sezonami smysluplně lišit, nesmí být bezdůvodně natvrdo zakódované jako globální konstanta. Engine musí umět načíst hodnotu z odpovídající konfigurace. Official Run default může být současně výchozí hodnotou formuláře.

Následující mapa určuje rozsah i tam, kde se značka neopakuje u každé jednotlivé věty:

| Oblast | Univerzální funkčnost enginu | Co může být jiné v jiném Runu |
|---|---|---|
| Run a čas | Runy, branche, historie, checkpointy a současný pevný kontrakt 50 sezon × 61 weeků | obsah jednotlivých sezon a jejich pravidla |
| Produkt | Viewer/Admin, read-only Viewer, ukládání, audit, import/export a volitelný Package mechanismus | ručně vytvořený či z Packages zkopírovaný obsah Runu a jeho konkrétní skladba |
| Hráči | identity, profily, historická data a lifecycle mechanismus | generační věk, vstup na Tour, retirement věk, comeback a další Player Lifecycle Policy |
| Turnaje | Tournament Series/Edition, kalendářový a losovací mechanismus | kalendář, kategorie, kapacity, seedy, BYE, qualification, entry a draw policy |
| Zápasy | schopnost simulovat a ukládat zápas, výsledkové statusy a historii | BO formát, bodování setu a povolené formáty podle soutěže či kola |
| Rankingy | snapshoty, historické zobrazení, Live/Official mechanismus a konfigurovatelné policy | Best N, platnost bodů, povinné výsledky, PR a ostatní rankingová pravidla |
| Soutěže | schopnost vytvářet individuální a týmové soutěže | jejich existence, cyklus, formát, kvalifikace, soupisky a bodování |
| Ekonomika a chování | mechanismy prize money, disciplíny, zranění a AI | částky, pravděpodobnosti, sankce a konkrétní sportovní chování |

**Výkladové pravidlo pro celý dokument:** číselné hodnoty, seznamy soutěží a sportovní policy uvedené pro svět MSA/FAX se považují za **Official Run defaulty**, pokud daný bod výslovně neříká, že jde o Engine invariant. Jiné Runy je mohou mít jiné, pokud engine danou variabilitu podporuje. Přesné technické umístění každé konfigurace v Runu, Category Package, Season Policy nebo Tournament Edition se ještě může zpřesnit.

### Pravidlo přednosti

Při rozporu platí toto pořadí:

1. **výslovná rozhodnutí učiněná v tomto konkrétním chatu,**
2. tento master dokument jako průběžný zápis rozhodnutí z tohoto konkrétního chatu,
3. prozatímní pravidla a směry dohodnuté v tomto konkrétním chatu,
4. obsah z jiných chatů, starších dokumentů, handoffů nebo kódu pouze jako návrh či inspirace.

**Absolutní pravidlo:** pokud se tento dokument nebo jakýkoliv jiný podklad liší od toho, co bylo řečeno v tomto konkrétním chatu, platí tento konkrétní chat. Nic převzatého z jiného chatu se nepovažuje za rozhodnuté, dokud to uživatel výslovně nepotvrdí také zde.

Slova jako „asi“, „zatím“, „možná“ a „ještě upřesníme“ se nesmějí převádět na pevné rozhodnutí.

---

# 1. Hlavní vize a rozsah produktu

## 1.1 Co má Squash Engine být

**[CÍLOVÁ FUNKCE]** Squash Engine je dlouhodobý simulátor a správce profesionálního squashového světa FAX. Má spojovat:

- generování zemí, populace a hráčských generací,
- vývoj celých hráčských kariér,
- turnajové kalendáře, přihlášky, losy a kvalifikace,
- simulaci zápasů, kol, turnajů, týdnů, sezon i celé padesátileté historie,
- rankingy, statistiky, rekordy, H2H a ocenění,
- alternativní časové linie přes Runy, branche a checkpointy,
- administrační pracovní prostředí,
- historicky věrný read-only Viewer jako prostředí více fiktivních veřejných webů nad stejnými daty, jehož hlavním oficiálním webem je MSA.

Nejde jen o generátor jednoho výsledku. Match engine je jedna část celého simulačního světa.

## 1.2 Současný sportovní rozsah

**Rozsah kapitoly:** mužský squash a dvouhra jsou současným globálním produktovým rozsahem enginu. Konkrétní týmové a kontinentální soutěže a jejich formáty jsou naproti tomu **Official Run konfigurací**.

**[ROZHODNUTO]** Engine je zaměřen pouze na mužský squash.

**[ROZHODNUTO]** Ženský squash a WSA nejsou součástí současného enginu. Starší dokumentace, která s WSA počítá, není v tomto bodě aktuální.

**[ROZHODNUTO]** Jednotlivé zápasy jsou pouze dvouhra. Čtyřhra se dělat nebude.

**[ROZHODNUTO]** Official Run obsahuje také mužské týmové soutěže složené ze samostatných dvouher: Team World Championship a týmová mistrovství jednotlivých kontinentů.

**[ROZHODNUTO PRO TEAM WORLD CHAMPIONSHIP]** Jeden mezistátní duel se skládá přesně ze šesti individuálních dvouher. Každá z nich se hraje standardním formátem BO5 do 11 bodů o dva body.

**[ROZHODNUTO PRO TEAM WORLD CHAMPIONSHIP]** Při stavu individuálních zápasů `3:3` rozhodne nejprve souhrnný rozdíl setů ze všech šesti dvouher, potom souhrnný rozdíl míčů a při úplné shodě vítěz dvouhry hráčů na pozici číslo 1. Podrobnosti soupisek a sestav jsou v kapitole 26.3.

**[OTEVŘENO]** Formát celého týmového turnaje, field, kvalifikace, kalendář a přesné pořadí šesti dvouher se dořeší zvlášť.

## 1.3 Produkt pro jednoho uživatele

**[ROZHODNUTO]** Současný engine je pro jednoho uživatele.

**[ROZHODNUTO]** V současném rozsahu nejsou uživatelské účty, role ani přihlašování.

## 1.4 Co nyní není součástí enginu

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Nyní nebudou:

- ženy a WSA,
- čtyřhra,
- trenéři, podpůrné týmy, agenti a tréninková centra jako samostatné entity, bonusy nebo simulované vztahy,
- osobní sponzoři a smlouvy se značkami,
- platy hráčů,
- odečítání cestovních, ubytovacích nebo turnajových nákladů,
- přesný osobní peněžní účet, měny, rozpočet, pravidelné příjmy a položkové výdaje hráče,
- hráčské fotografie nebo AI avatary,
- simulovaná návštěvnost turnajů,
- samostatný juniorský ranking,
- detailní rozdělení každého týdne na dny jako potvrzená součást modelu.

Trenéři, podpůrné týmy, agenti a tréninková centra jsou výslovně ignorované rozhodnutí, nikoliv pouze chybějící detail první verze. Abstraktní development, tréninkový vliv nebo hráčská příprava tím nejsou zakázané; pouze se kvůli nim nyní nevytvářejí vlastní osoby, organizace, vztahy ani infrastruktura.

Toto vyloučení přesného účetnictví není v rozporu s experimentálním `Financial Level 0–10` z kapitoly 19.2. Financial Level je pouze hrubý odhad dostupného zázemí a zdrojů, nikoliv částka peněz, účet ani simulovaný cash-flow.

Některé ostatní vyjmenované funkce mohou přijít ve velmi vzdálené verzi, ale nesmějí komplikovat současný základ.

---

# 2. Viewer a Admin mód

## 2.1 Dvě části jednoho produktu

**[ROZHODNUTO]** Engine má dvě jasně oddělené části nad stejnými daty:

1. **Viewer mód** – veřejně působící read-only prostředí několika samostatných fiktivních webů; hlavním současným webem je oficiální MSA Squash.
2. **Admin mód** – generování, simulace, editace a správa celého světa.

Mohou mít oddělené route prostory, například `/viewer/...` a `/admin/...`. Nemá jít jen o jednu stránku, na které se schovají editační tlačítka.

## 2.2 Viewer mód

**[ROZHODNUTO]** Viewer je vždy pouze ke čtení.

Ve Vieweru nelze:

- editovat data,
- spouštět simulace,
- importovat nebo regenerovat obsah,
- měnit Run, branch nebo historii jinak než běžným přepnutím zobrazovaného kontextu,
- provádět administrační mutace.

**[ROZHODNUTO]** Viewer nesmí vymýšlet chybějící data. Pokud nejsou výsledky, ranking, H2H, rekord nebo predikce skutečně dostupné, zobrazí se prázdný či nedostupný stav.

## 2.3 Admin mód

**[CÍLOVÁ FUNKCE]** Admin slouží zejména pro:

- správu Runů, branchí a checkpointů,
- správu lokálních World, Category, Series, Calendar a Setup Packages,
- generování, editaci, zamykání a regenerování hráčů,
- přípravu sezon a kalendářů,
- správu turnajů, kategorií, přihlášek, kvalifikací a losů,
- simulaci v různých rozsazích,
- ruční opravy a přepsání budoucnosti,
- import, export, diagnostiku a audit.

**[ROZHODNUTO][ENGINE INVARIANT]** Admin může ručně zasáhnout do každého produktově modelovaného pravidla, stavu, rozhodnutí hráčské AI a autoritativního údaje enginu. Takový zásah musí respektovat zvolený Run, branch a časový bod, nést původ `Manual` nebo `Manual Override` a být dohledatelný v Audit Logu. U jednotlivých dalších systémů se proto znovu nerozhoduje, zda jejich podporovanou hodnotu Admin vůbec smí přepsat; otevřený může zůstat jen konkrétní workflow a UI.

**[ROZHODNUTO][ENGINE INVARIANT]** Admin smí vědomě vytvořit výjimku z běžného sportovního nebo sezonního pravidla, pokud je výjimka zřetelně označená a potvrzená. Nesmí však uložit vnitřně nemožný či poškozený technický stav, například dva autoritativní vítěze téhož zápasu nebo odkaz na neexistujícího hráče. Pokud změna vyžaduje úpravu souvisejících údajů, engine ukáže potřebný rozsah a celý `Manual Override` zapíše atomicky.

**[ROZHODNUTO]** Hlavní stránka Runového Adminu se nazývá `Home`, nikoliv `Dashboard`. Je to nejvyšší souhrnná Admin stránka právě zvoleného Runu a branche a běžný vstup do jeho obsahu; není to další globální landing ani náhrada specializovaných stránek. Má poskytovat přehled o Runu a postupně také náhledy jeho hlavních oblastí. Vlastní řízení simulací patří primárně do sekce `Simulation`; úplná skladba ostatních bloků Home se doplní později.

## 2.4 Kontextové přepínání Viewer ↔ Admin

**[ROZHODNUTO V PRINCIPU]** Přepnutí režimu musí co nejpřesněji zachovat kontext.

**[ROZHODNUTO]** Přepínač `Viewer / Admin` je aktivní na všech stránkách, které mají vybraný Run. Produkt pro současnou verzi používá jedno hlavní okno aplikace; změna módu proto standardně probíhá uvnitř téhož okna, nikoliv povinným otevřením samostatného Vieweru nebo Adminu.

**[ROZHODNUTO]** Globální Admin stránky bez aktivního Runu nemají platný Viewer protějšek. Volba Vieweru na nich zůstává viditelná, ale neaktivní a vysvětluje `Nejdříve otevři Run`. Nesmí potichu použít naposledy otevřený Run. Do Vieweru se z globálního scope vstupuje přes `Runs → vybraný Run → Otevřít ve Vieweru`.

Příklad: jestli je uživatel ve Vieweru v konkrétním Runu, branchi, sezoně, turnaji, kole a zápasu, přepnutí do Adminu ho otevře na administrační stránce stejného Runu a stejného konkrétního objektu. Totéž platí opačným směrem.

Nestačí přejít pouze na obecný Players nebo Tournament hub, pokud přesný protějšek existuje.

**[ROZHODNUTO]** Běžný přepínač Admin → Viewer nikdy automaticky nezmění `Viewer Branch`. Z jiné aktivní Admin branche se pokusí otevřít odpovídající objekt a week současné `Viewer Branch`; pokud přesný protějšek neexistuje, použije již rozhodnutý vysvětlený fallback. Výslovná Admin akce pro změnu toho, kterou branch Viewer zobrazuje, zůstává samostatným workflow.

**[POZDĚJI]** Možnost otevřít Viewer také v samostatném druhém okně může být užitečná například při simulaci v Adminu a současném sledování posledního uloženého Viewer stavu. Pro současnou verzi není součástí základního workflow a její přesná synchronizace ani ovládání nejsou rozhodnuté.

## 2.5 Zobrazování skrytých informací

**[ROZHODNUTO]** Výchozí Viewer režim skrývá interní informace, například skutečný potenciál, OVR a detailní schopnosti.

**[CÍLOVÁ FUNKCE]** V navbaru nebo jiném globálním ovladači bude možné přepínat úroveň odhalení dat. Pracovní příklad:

- **Public** – vše interní skryté; vždy výchozí,
- **Ratings** – může ukázat OVR a atributy,
- **Full Reveal** – může ukázat i skutečný potenciál a další interní hodnoty.

**[OTEVŘENO]** Přesné názvy režimů a přesný obsah každé úrovně.

Tato otázka byla v navazujícím rozhodování dne 5. 8. 2026 výslovně přeskočena. Výše uvedené názvy zůstávají pouze pracovním příkladem a nesmějí být považovány za nově potvrzené režimy.

**[ROZHODNUTO PRO ZDRAVÍ]** Ani Viewer reveal režim nesmí bez jasného oddělení vydávat skutečný interní zdravotní stav za veřejně známou informaci. Viewer pracuje s veřejnou či odhadovanou zdravotní vrstvou; autoritativní pravda patří do Adminu. Přesný debug/reveal UX se může dořešit, ale obě vrstvy musí zůstat významově rozlišené.

---

# 3. Run model

## 3.1 Co je Run

**[ROZHODNUTO][ENGINE INVARIANT]** Run je kořen celé samostatné historie squashového světa a všech jejích alternativních časových linií. Není jednou sezonou ani jednou branchí: sezona je pouze časový úsek konkrétní branche uvnitř Runu a branch je jedna konkrétní časová linie téhož Runu.

Runový kontejner nese vlastní strukturální kořen a v průběhu práce může obsahovat:

- vlastní interní ID,
- název,
- volitelný popis,
- vlastní nezávislý obsah a konfiguraci, které mohou vzniknout ručně, z balíčků nebo kombinací obojího,
- provenance všech případně použitých Packages a zachované nevyřešené reference,
- pevný padesátisezonní časový rámec,
- branche a jejich historii,
- hráče, turnaje, zápasy a rankingy,
- checkpointy a metadata,
- nastavení a simulační stav.

## 3.2 Pevný rozsah Runu

**[ROZHODNUTO][ENGINE INVARIANT PRO SOUČASNOU VERZI]** Rozsah 50 sezon `2000/01–2049/50` a přesně 61 Season Weeks v každé sezoně platí pro každý Run, nikoliv pouze pro Official Run.

**[ROZHODNUTO]** Každý Run vždy obsahuje přesně 50 sezon:

- první sezona `2000/01`,
- poslední sezona `2049/50`.

**[ROZHODNUTO]** Po sezoně `2049/50` Run v současné verzi definitivně končí. Nelze pokračovat do `2050/51`.

Toto pravidlo může být někdy v budoucnu vědomě změněno, ale nyní je platné.

**[ROZHODNUTO]** Každá sezona obsahuje přesně 61 Season Weeks, číslovaných 1–61.

**[ROZHODNUTO]** Mohou existovat týdny bez jediného turnaje.

**[ROZHODNUTO]** Turnaj může trvat více než jeden týden.

## 3.3 Vytvoření a zahájení Runu

**[ROZHODNUTO][ENGINE INVARIANT]** Run lze vytvořit úplně prázdný, bez World Package, Category Package, Series Package, Calendar Package i Setup Package. Samotná nepřítomnost těchto dat je platným stavem rozpracovaného `Working` Runu, nikoliv chybou.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Jediným povinným údajem, který při založení Runu zadává uživatel, je jeho jedinečný zobrazovaný název. Engine automaticky přidělí `run_id` a vytvoří prázdný časový rámec Runu; popis, Packages, hráči, kalendář, pravidla i ostatní obsah lze doplnit až později. Příklad: po zadání názvu `Test Run` může Run okamžitě existovat jako platný prázdný `Working` stav, i když v něm zatím nelze spustit žádnou sportovní simulaci.

**[ROZHODNUTO][ENGINE INVARIANT]** Samotné úspěšné založení Runu je současně jeho první úspěšné uložení. V jedné atomické bootstrap operaci vznikne identita Runu, jeho počáteční `Viewer Branch`, neměnná první `Saved Revision` bez rodičovské revize a čistý `Working Draft` založený právě na ní. Pokud selže kterákoliv část, nesmí zůstat částečně vytvořený Run, branch, revize ani draft.

První `Saved Revision` zachycuje platný prázdný stav celé historie. Není samostatným simulačním stavem ani automatickým checkpointem a nevytváří neexistující Packages, hráče, kalendář nebo sezonní obsah. Počáteční branch se automaticky jmenuje `Timeline 1`; úplné pojmenovací pravidlo pokračování řady a vlastní název určuje kapitola 7.1.

**[ROZHODNUTO]** Uživatel může obsah prázdného Runu vytvářet ručně, importovat do něj jednotlivé Packages až později nebo použít volitelný Setup Package. Žádný Setup Package není podmínkou vzniku ani otevření Runu.

**[ROZHODNUTO][ENGINE INVARIANT]** Nový Run nemá povinnou globální blokující fázi `Setup/Draft → Start Run`. Uživatel jej může budovat postupně a simulovat už od prvních vytvořených hráčů, zápasů a turnajů; nemusí předem dokončit celý svět, první sezonu ani všechny budoucí systémové části.

**[ROZHODNUTO][ENGINE INVARIANT]** Spustitelnost se posuzuje podle právě požadované operace, nikoliv jedním globálním testem „je hotový celý Run“. Například platně sestavený samostatný zápas lze simulovat, i když zbytek kalendáře ještě neexistuje. Simulace celého kola, turnaje, weeku, sezony nebo Full Simulation vyžaduje postupně širší množinu vstupů potřebných právě pro daný rozsah.

**[ROZHODNUTO]** Chybějící nebo nevalidní data mimo zvolený rozsah nesmějí bezdůvodně blokovat jinou nezávislou validní operaci. Admin musí před spuštěním přesně ukázat, které povinné vstupy chybějí právě požadované operaci.

**[ODLOŽENO]** Přesná matice prerequisites jednotlivých rozsahů simulace, UX průběžného zakládání Runu a případné neblokující onboarding/checklist obrazovky.

## 3.4 Počet Runů a názvy

**[ROZHODNUTO]** Počet Runů není omezen.

**[ROZHODNUTO]** Každý Run má jedinečný zobrazovaný název napříč aktivními i archivovanými Runy. Archivovaný Run si svůj název rezervuje, aby jej bylo možné obnovit bez nového konfliktu. Skutečnou technickou identitu vždy určuje stabilní `run_id`.

**[ROZHODNUTO]** Popis Runu je volitelný.

**[ROZHODNUTO]** Kopie nebo import Runu s obsazeným názvem automaticky navrhne nový jedinečný pracovní název, například `Copy of X` nebo `X (2)`. Uživatel jej může před dokončením upravit, ale nelze uložit název, který je stále v konfliktu.

## 3.5 Lokální a vestavěné Runy

**[ROZHODNUTO]** Běžný uživatelský Run je uložen lokálně na počítači uživatele.

**[CÍLOVÁ FUNKCE]** Některé Runy mohou být zabudované v projektu/GitHubu.

Vestavěný Run:

- je viditelný ve Vieweru,
- je viditelný také v Adminu,
- nelze přímo editovat v enginu,
- upravuje se zdrojovým kódem nebo daty v GitHubu,
- Admin má vysvětlit dostupný postup, například zkopírování/export a následnou úpravu mimo vestavěný originál.

Přesný UX tohoto postupu se ještě dořeší.

### Vestavěný Match Test Lab

**[ROZHODNUTO V PRINCIPU][CÍLOVÁ FUNKCE]** Projekt bude obsahovat také vestavěný GitHub Run určený k rychlému testování jednotlivých zápasů a Match Enginu. Jeho zdrojový baseline je stejně jako jiné vestavěné GitHub položky read-only.

**[ROZHODNUTO V PRINCIPU]** Akce typu `New Test Session` vytvoří oddělenou editovatelnou testovací session/kopii, kterou lze upravovat a vrátit k baseline. Testovací změny ani výsledky nesmějí měnit vestavěný zdroj.

**[ROZHODNUTO V PRINCIPU]** Do Test Labu lze převzít hráče z jiného Runu v historickém stavu zvoleného Runu, branche a weeku. Vzniká oddělený snapshot s dohledatelnou provenance, nikoliv živé propojení. Pozdější úpravy nebo testovací zápasy nemění zdrojového hráče, jeho ranking, H2H, statistiky ani původní Run. Tentýž zdrojový hráč proto může v Test Labu existovat vícekrát jako různé historické verze.

**[ODLOŽENO]** Přesné obrazovky, importní volby, rozsah kopírovaného hráčského stavu, nástroje pro úpravy, ukládání a životní cyklus testovacích sessions. Zatím je pevný pouze směr Test Labu a nezávislých historických snapshotů.

## 3.6 Kopírování Runu

**[ROZHODNUTO]** Kopie Runu je jednorázový nezávislý snapshot zvoleného stavu. Vždy dostane nové `run_id`; pozdější změny originálu se do kopie automaticky nepřenášejí a naopak.

**[ROZHODNUTO]** Pokud má zdrojový Run neuložené změny, engine nikdy potichu nezvolí, co kopíruje. Dialog nabídne:

1. zkopírovat poslední uložený stav,
2. nejdříve změny uložit a potom Run zkopírovat,
3. vytvořit nový Run přímo ze současného pracovního draftu, aniž by se draft uložil do originálu,
4. akci zrušit.

**[ROZHODNUTO]** Samotné kopírování nabízí dva režimy:

- `Úplná kopie` – výchozí jednoduchá volba se všemi daty, nastavením, branchemi, historií a checkpointy zvoleného zdrojového stavu,
- `Pokročilá kopie` – výběr podporovaných branchí, hloubky historie, checkpointů, nastavení a dalších bezpečně oddělitelných datových oblastí.

**[ROZHODNUTO]** Engine automaticky přidá všechny povinné závislosti, nedovolí nevalidní kombinaci a před potvrzením ukáže přesný obsah, vynechané části a odhad velikosti kopie.

**[ODLOŽENO]** Úplný konečný seznam volitelných datových skupin a nejjemnější podporovaná granularita pokročilé kopie.

## 3.7 Archivace a odstranění Runu

**[ROZHODNUTO]** Aktivní Run se nejdříve archivuje. Archivovaný Run lze kdykoliv znovu obnovit mezi aktivní Runy.

**[PROZATÍMNÍ]** Archivovaný Run je ve Vieweru skrytý, dokud není obnovený.

**[ROZHODNUTO]** Teprve z archivu lze lokální Run trvale smazat. Trvalé smazání musí být výslovně potvrzené. Lokální soubor lze také odstranit ručně mimo engine.

**[PROZATÍMNÍ]** Vestavěné GitHub Runy a balíčky zatím nepůjde skrývat ani archivovat, protože k tomu nebyl nalezen důvod.

## 3.8 Dokončený Run

**[ROZHODNUTO]** Po dokončení Weeku 61 sezony 2049/50 Run dál nepokračuje, ale zůstává normálně aktivní a dostupný ve Vieweru. Dokončení Run automaticky nearchivuje.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Poslední sezonní uzávěrka vytvoří `Season Closing Ranking`, sezonní souhrn a `Season Closure Marker` a potom označí Run jako `Completed`. Nevytváří neexistující Week 1 sezony 2050/51 ani nový Official Ranking této neexistující sezony.

**[ROZHODNUTO]** Z dokončeného Runu lze stále vytvářet nové branche z dřívějších uložených bodů a znovu simulovat alternativní historii.

**[ROZHODNUTO]** Lifecycle Runu používá tři neblokující stavy:

- `Working` – Run je od založení průběžně vytvářený nebo simulovaný a smí být obsahově neúplný,
- `Completed` – dosáhl konce Weeku 61 sezony 2049/50, zůstává dostupný a lze z jeho historie vytvářet další branche,
- `Archived` – byl výslovně odložen mimo běžné aktivní nabídky a lze jej obnovit.

Samostatný blokující lifecycle přechod `Setup → Active` neexistuje. Trvalé smazání není stav Runu, ale potvrzená operace dostupná až nad archivovaným lokálním Runem.

**[ROZHODNUTO]** `Built-in / Local`, `Read-only / Editable` a `Valid / Warnings / Errors` jsou nezávislé vlastnosti či osy Runu, nikoliv další lifecycle stavy.

## 3.9 Výchozí Run a globální přepínání

**[ROZHODNUTO]** Výchozí úvodní stránkou po běžném spuštění celé aplikace je neutrální `Squash Engine Home`. V současném návrhu nabízí vstup do globálních oblastí `Runs` a `Packages`; může se později rozšířit o další skutečně globální oblasti. Nejde o dříve odmítnutý rozcestník `Viewer / Admin` a automaticky se neotevírá žádný Run.

**[ROZHODNUTO]** `Runs` otevře stránku `Všechny Runy`. Ta zůstává neutrální globální stránkou mimo Viewer i Runový Admin: její obsah, filtrování ani základní layout se nemění podle naposledy aktivního módu.

**[ROZHODNUTO]** Viewer a Runový Admin mají na svých Run-scoped stránkách vpravo nahoře stále dostupný globální Run switcher. Zobrazuje Runy dostupné v daném módu a dovoluje mezi nimi přepínat. Na `Squash Engine Home`, globálních Package stránkách a dalších stránkách bez aktivního Runu se Run switcher, branch selector ani season/week ovladač nezobrazují.

**[ROZHODNUTO V PRINCIPU]** Rychlý Run switcher je kompaktní: ukáže nejvýše pět Runů včetně právě vybraného. Aktuální Run je jednoznačně označený, přednost mají Runy označené hvězdičkou a zbývající místa doplní naposledy otevřené Runy. Tlačítko `Všechny Runy` otevře úplnou globální Runs stránku; vytváření, import, mazání a složitá správa se neprovádějí v malém rychlém panelu.

**[ROZHODNUTO]** Úplná stránka `Všechny Runy` používá široké řádky pod sebou, nikoliv mřížku velkých dlaždic. Kliknutí na řádek Runu nabídne tři odlišné vstupy:

- `Otevřít v Adminu` – nastaví zvolený Run, vybere jeho současnou `Viewer Branch` a otevře `Home` tohoto Runu; nevkládá se před ni žádný další mezilehlý rozcestník,
- `Otevřít branche` – otevře úplnou Admin stránku branchí a jejich mapu pro daný Run,
- `Otevřít ve Vieweru` – otevře tento Run ve Vieweru nad jeho `Viewer Branch`.

Přesná grafická podoba této nabídky se může doladit; nesmí však dojít k neoznámenému automatickému výběru jedné z těchto tří odlišných akcí.

**[ROZHODNUTO]** Ve Vieweru se vždy zobrazí `Viewer Branch` vybraného Runu. Jinou branch lze jako `Viewer Branch` zvolit pouze v Adminu.

**[ROZHODNUTO]** Přepnutí Viewer ↔ Admin se nejprve pokusí otevřít protějšek právě zobrazené stránky nebo objektu v druhém módu. Přenáší Run, sezonu/week, vybraný objekt a pokud možno také konkrétní podstránku či záložku. Typickými vazbami jsou stejný hráč, turnaj, zápas, země nebo rankingový pohled.

**[ROZHODNUTO]** Při přepnutí Admin → Viewer se nikdy automaticky nemění `Viewer Branch`. Pokud byl Admin v jiné branchi, Viewer použije současnou `Viewer Branch` daného Runu a pokusí se v ní nalézt tentýž objekt a odpovídající časový kontext.

**[ROZHODNUTO]** Pokud přesný protějšek v cílovém módu neexistuje nebo není v daném weeku veřejně dostupný, otevře se nejbližší smysluplná nadřazená či související stránka a aplikace jasně vysvětlí, co nešlo přenést. Teprve bez jakéhokoliv smysluplného protějšku se použije hlavní stránka MSA nebo Adminu; nesmí dojít k tichému zobrazení neodpovídajících dat.

**[ROZHODNUTO V PRINCIPU]** Při přepnutí mezi Runy se engine pokusí zachovat stejný typ stránky i zvolenou sezonu/week, pokud jsou v cílovém Runu dostupné a v daném módu povolené. Pokud odpovídající objekt nebo časový bod neexistuje, otevře nejbližší logický přehled či dostupný bod a změnu kontextu viditelně vysvětlí; nesmí tiše ukázat neodpovídající data.

## 3.10 Konfigurace Runu a Official Run defaulty

**[ROZHODNUTO][ENGINE INVARIANT]** Každý Run si nese vlastní stav všech podporovaných sportovních policy a konfigurovatelných hodnot. Proto mohou mít dva Runy nad stejným enginem například jiný retirement věk, Best N, platnost bodů, kategorie, kalendář, formát zápasu nebo Protected Ranking Policy.

**[ROZHODNUTO][ENGINE INVARIANT]** Hodnoty označené v tomto dokumentu jako `Official Run default` se mohou při tvorbě Runu, sezony, kategorie, turnaje nebo jiné konfigurace nabídnout jako předvyplněná výchozí volba. Nejsou však univerzálním omezením jiného Runu a Admin je může v podporovaném rozsahu změnit.

**[ROZHODNUTO][ENGINE INVARIANT]** Uložený Run musí obsahovat skutečně použité hodnoty a jejich historické verze; nesmí se při načtení skrytě dopočítávat z nejnovějšího Official defaultu.

**[ROZHODNUTO][ENGINE INVARIANT]** Po odvětvení je časově platná sportovní konfigurace součástí stavu konkrétní branche. Změna pravidla, kalendáře nebo hodnoty v jedné branchi od zvoleného weeku nesmí automaticky přepsat jinou branch. Výslovné použití stejné změny ve více branchích je samostatná validovaná operace.

**[ROZHODNUTO][ENGINE INVARIANT]** Každá podporovaná konfigurovatelná hodnota má dva režimy:

- `Inherited` – efektivní hodnota se přebírá z nadřazené konfigurační úrovně,
- `Override` – pro konkrétní objekt je hodnota výslovně nastavena ručně.

Admin vždy ukáže efektivní hodnotu, její režim a přesný zdroj, ze kterého se zdědila.

**[ROZHODNUTO]** Změna nadřazené hodnoty automaticky aktualizuje pouze závislé `Inherited` hodnoty. Výslovné overrides zůstávají beze změny.

**[ROZHODNUTO]** Override zůstává overridem i tehdy, když se jeho hodnota právě shoduje se zděděnou hodnotou. Na dědění se vrátí pouze výslovnou akcí `Obnovit dědění`.

Před obnovením dědění se zobrazí rychlé preview:

- současná hodnota → nově zděděná hodnota,
- zdroj nové hodnoty,
- případné navazující dopady.

**[ROZHODNUTO]** Také změna nadřazeného nastavení před uložením ukáže dopad na všechny zděděné objekty a výslovně označí overrides, kterých se změna nedotkne.

**[ROZHODNUTO]** Admin obsahuje centrální přehled všech aktivních overrides v daném Runu. Lze je filtrovat například podle sezony, kategorie, Tournament Series a Tournament Edition; kliknutí otevře přesně příslušné nastavení.

**[ROZHODNUTO]** Každý override je viditelně označený, ale samotná existence platného override není varováním. Oranžový nebo červený vykřičník se používá pouze pro neobvyklou, rizikovou nebo neplatnou hodnotu a zachovává jednotný význam z kapitoly 25.6.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE CONTRACT]** Obecné pořadí konfigurační dědičnosti je:

`Official engine default → relevantní hodnota Package → Run → sezona → Competition System → volitelný Tour → Category → Tournament Series → Edition Plan → Tournament Edition → fáze → kolo → konkrétní zápas`

Na každém poli vítězí nejbližší **povolený** explicitní override. Ne každé nastavení je dostupné na každé úrovni: engine udržuje field-specific scope registry, který určuje, kde lze danou hodnotu zadat, dědit, uzamknout nebo pouze číst. Úplný katalog polí se může implementačně doplňovat, ale nesmí měnit výše uvedené pořadí ani si vytvořit skrytou úroveň.

Příklady povoleného scope:

- sezonní bodová tabulka vychází z `Category × season` a výjimka může patřit Tournament Edition, nikoliv jednotlivému zápasu,
- dlouhodobý název či typické místo může vycházet z Tournament Series a změnit se v Edition Planu nebo Tournament Edition,
- Match Format používá užší samostatný kontrakt kapitoly 16.1: v první pre-alpha se neprotahuje celou touto obecnou hierarchií,
- čistě uživatelské nastavení rychlosti zobrazení není sportovní konfigurace a do této hierarchie vůbec nevstupuje.

Admin vždy ukáže efektivní hodnotu, `Inherited / Override`, přesný zdroj a dopad `Obnovit dědění`. Výslovný override zůstává overridem i při shodné hodnotě. Zděděná hodnota sleduje časově platný zdroj jen do svého příslušného provozního locku; již uzamčený nebo odehraný historický stav se změnou rodiče zpětně nepřepisuje.

---

# 4. Packages a jejich skládání

**Rozsah kapitoly:** mechanismus vytváření, editace, skládání, kopírování a importu/exportu balíčků je funkčnost enginu. `Official FAX World`, `Official FAX Category Package` a další oficiální balíčky jsou **Official Run defaulty**, nikoliv povinný obsah jiných Runů.

## 4.1 Princip

**[ROZHODNUTO][ENGINE INVARIANT]** Packages jsou volitelné přenositelné zdroje obsahu. Run může vzniknout bez nich, může být celý vytvořen ručně a může přijmout jeden či více balíčků až později.

**[ROZHODNUTO][ENGINE INVARIANT]** Použití nebo import Package zkopíruje jeho vybraný obsah do nezávislého stavu Runu. Run uloží identitu a verzi zdroje jako provenance, ale mezi globálním balíčkem a Runem potom neexistuje živé datové propojení.

**[ROZHODNUTO][ENGINE INVARIANT]** Úprava zdrojového balíčku sama nezmění žádný existující Run. Úprava zkopírovaného obsahu uvnitř editovatelného Runu naopak nemění zdrojový Package ani jiné Runy. Pozdější převzetí novější verze zdroje musí být výslovná operace s preview, validací a řešením konfliktů.

**[ROZHODNUTO][ENGINE INVARIANT]** Jakmile se historie Runu rozdělí do branchí, změna časově platného importovaného či ručně vytvořeného obsahu je součástí právě upravované branche. Ostatní branche automaticky nemění; použití stejné změny ve více branchích je samostatná kontrolovaná operace.

**[ROZHODNUTO]** Absence Package ani neúplná skladba balíčků sama o sobě není globální hard error. Blokuje se pouze operace, která chybějící data skutečně potřebuje.

**[OTEVŘENO]** Přesná pravidla současného použití více balíčků stejného typu, jejich priority, merge/replacement konflikty a nejjemnější podporovaný rozsah importu. Nic z toho se nesmí řešit tichým přepsáním.

## 4.2 Potvrzené typy, vestavěné a lokální balíčky

**[ROZHODNUTO]** Systém nyní zná pět samostatných typů: `World Package`, `Category Package`, `Series Package`, `Calendar Package` a `Setup Package`.

**[ROZHODNUTO]** Vestavěné Packages uložené v projektu/GitHubu jsou jako zdrojové šablony v enginu read-only.

**[ROZHODNUTO]** Vestavěnou zdrojovou šablonu lze měnit pouze mimo engine přímo ve zdrojových datech nebo kódu.

**[ROZHODNUTO]** Lokální/custom Packages jsou v enginu editovatelné.

**[ROZHODNUTO]** Vestavěný read-only Package lze v enginu upravovat pouze nepřímo akcí `Duplikovat`, která vytvoří nový nezávislý lokální Package s novým `package_id` a vlastní verzí 1. Vestavěný zdroj zůstane beze změny.

**[ROZHODNUTO]** Snapshot vytvořený z vestavěného balíčku uvnitř běžného editovatelného lokálního Runu lze upravovat pouze pro tento Run. Samotný vestavěný zdroj ani jiné Runy se tím nezmění. Pokud je read-only celý vestavěný GitHub Run, zůstává read-only také jeho vložený obsah.

**[ROZHODNUTO V PRINCIPU]** Každý potvrzený typ Package lze samostatně exportovat a importovat. Přesný souborový formát se dořeší.

**[ROZHODNUTO]** Zdrojové Packages mají vlastní správu v globálním Adminu mimo Run. Editor vždy jednoznačně rozlišuje globální zdroj od nezávislého obsahu konkrétního Runu.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Architektura zůstává rozšiřitelná o další budoucí typy, například `Player Package`. Jejich konkrétní katalog a schémata zatím rozhodnuté nejsou.

## 4.3 Obsah World Package

World Package má určovat minimálně:

- země a území,
- jejich vnitřní oblasti používané podporovanou geografickou abstrakcí,
- `Travel Regions`, `Timezone Areas` a jejich přiřazení,
- jejich kódy a názvy,
- populační historii,
- faktická country data podle podporovaného modelu, například rozlohu, Region a případný počet kurtů,
- šest ručně authorovaných squashových ratingů Country Modelu V1,
- parametry a verzovanou logiku produkční pipeline hráčů,
- případná world-specific pravidla,
- stabilní zdrojovou identitu.

## 4.4 Official FAX World

**[ROZHODNUTO]** `Official FAX World` je nabízený Official Run default a vestavěný read-only balíček. Run jej nemusí použít.

Má postupně obsahovat celý fiktivní svět FAX, například Germanicu, Bogemii, Hungaricu, Polandii, Anglicu, Francicu, Maghiru, Amerigu, New Anglicu, New Francicu, Californicu a další státy či regiony.

Starší známé populační návrhy pro rok 2020, které je nutné před canonizací znovu ověřit:

| Země | Populace | Rozloha km² |
|---|---:|---:|
| Germanica | 169 702 055 | 870 516 |
| Bogemia | 48 566 934 | 237 528 |
| Hungarica | 32 407 718 | 368 441 |
| Polandia | 31 584 129 | 296 910 |

## 4.5 Real World

**[STARŠÍ SILNĚ ROZPRACOVANÝ ZÁKLAD]** Existuje záměr druhého vestavěného read-only balíčku `Real World` se všemi současnými zeměmi a územími, ISO-3 kódy a populací 1955–2050.

Tento bod se v aktuálním dialogu znovu nepotvrzoval, proto se jeho přesný rozsah nesmí rozšiřovat bez ověření.

## 4.6 Category Package

**[ROZHODNUTO V PRINCIPU]** Vedle World Package existuje samostatný `Category Package`, který funguje stejným základním stylem.

**[ROZHODNUTO]** Zdrojový lokální Category Package lze upravovat. Vestavěný GitHub Category Package je jako zdrojová šablona zamčený a v enginu read-only. Jeho snapshot uvnitř editovatelného lokálního Runu však lze upravovat pouze pro tento Run podle obecného snapshotového pravidla z kapitoly 4.1.

**[ROZHODNUTO]** Nabízeným Official Run defaultem je vestavěný `Official FAX Category Package`; Run jej však nemusí při založení ani později použít.

**[ROZHODNUTO]** Vestavěný balíček lze zkopírovat nebo duplikovat do nové nezávislé lokální editovatelné kopie.

**[ROZHODNUTO]** Category Package lze samostatně exportovat a importovat.

**[ROZHODNUTO][ENGINE INVARIANT]** Základní sportovní taxonomie Category Package je obsahově nezávislá na World Package. Samotné kategorie nesmějí vyžadovat konkrétní země či regiony. Případné reference navazujících Series nebo Calendar dat na objekty světa se řeší jako měkké závislosti podle kapitoly 4.8.

**[ROZHODNUTO V PRINCIPU]** Vnitřní hierarchie je:

`Category Package → Competition System → volitelný Tour → Category`

Kategorie tedy může patřit pod Tour, ale také přímo pod Competition System. Tour není povinná mezivrstva.

**[ROZHODNUTO]** V jedné konkrétní sezoně patří každá Category právě do jednoho Competition Systemu a nejvýše do jedné Tour. Mezi sezonami se může přesunout pod jinou Tour nebo do jinak uspořádaného Competition Systemu při zachování stejného `category_id` a celé předchozí historie.

**[ROZHODNUTO V PRINCIPU]** `Competition System`, `Tour` a `Category` jsou historické entity se stabilními číselnými ID v rámci příslušného Category Package. Pracovní názvy polí jsou `competition_system_id`, `tour_id` a `category_id`. ID se znovu nepoužívají a nevyjadřují sportovní pořadí ani pozici v UI.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][MINIMUM ENTITY CONTRACT]** Všechny uložené doménové entity používají stabilní číselné Run-local ID, které se nikdy znovu nepoužije, a společný technický envelope se schema verzí a provenance. Minimální věcná pole turnajové hierarchie jsou:

| Entita | Povinné minimum |
|---|---|
| `Competition System` | `competition_system_id`, časově platný název, období platnosti/aktivita a `display_order` |
| `Tour` | `tour_id`, rodičovské `competition_system_id`, časově platný název, období platnosti/aktivita a `display_order` |
| `Category` | `category_id`, `competition_system_id`, volitelné `tour_id`, časově platný název, sezonní platnost, `display_order` a volitelné `tier_rank` |
| `Tournament Series` | `series_id`, současný a historické názvy, dlouhodobé defaulty a aktivita; neobsahuje konkrétní sezonu, week ani výsledek |
| `Edition Plan` | vazba na Series, cílová sezona, occurrence/order key, plánovaný week či rozsah a explicitní overrides; virtuální plán je před materializací adresovaný deterministickým klíčem `Series + season + occurrence` a vlastní uložené ID ještě nemá |
| `Tournament Edition` | `edition_id`, `series_id`, plan provenance, sezona, skutečné weeky, efektivní Category a místo, lifecycle/public state a efektivní sportovní konfigurace; entries, draw a výsledky jsou povinné až od lifecycle fáze, která je skutečně vyžaduje |

Povinná reference je buď platně vyřešená, nebo výslovně `Unresolved`; nesmí se ztratit jako nejednoznačné `null`. Skutečně volitelná reference smí být `null`. Neúplný Draft lze uložit a pole se stávají povinnými postupně podle operation-scoped prerequisites. Finance, marketing, budovy, kurty a detailní venue nejsou součástí tohoto minimálního entity kontraktu; tím se neruší samostatná volitelná prize-money konfigurace ani pozdější rozšíření.

**[ROZHODNUTO]** Pro pořadí slouží oddělené volitelné hodnoty: `display_order` pro zobrazení a `tier_rank` pro sportovní hierarchii síly. Obě hodnoty jsou časově platné pro konkrétní sezonu, standardně se dědí do následující sezony a při reorganizaci se mohou změnit bez přepsání starší historie.

**[ROZHODNUTO]** Engine rozlišuje srovnatelné tierové entity a speciální nesrovnatelné entity:

- běžná srovnatelná Tour nebo Category může mít `tier_rank`,
- Finals, olympijská, týmová, šampionátová nebo jiná speciální struktura může mít `tier_rank = null`,
- význam speciální soutěže se vyjadřuje odděleně zejména bodováním, prestiží, typem titulu, periodicitou a kvalifikačními pravidly.

Konkrétní zařazení jednotlivých soutěží je obsah Runu. `tier_rank` se porovnává pouze mezi sourozenci pod stejným rodičem, nikdy globálně mezi nesouvisejícími Tours nebo Categories.

**[ROZHODNUTO]** Zobrazovaný název musí být v jedné sezoně unikátní pouze mezi sourozenci pod stejným nadřazeným objektem. Stejný název může existovat pod jinou Tour nebo Competition Systemem. Přejmenování zachovává ID i historii.

**[ROZHODNUTO V PRINCIPU]** Tour může pod stejným `tour_id` měnit název a další časově platné údaje, být deaktivována a později znovu aktivována. Skutečně nová Tour dostane nové ID. Hráč se nadále nepřiřazuje k Tour jako člen; Tour organizuje soutěže a kategorie.

**[ROZHODNUTO V PRINCIPU]** Category konfigurace uvnitř Run snapshotu musí podporovat sezonní bodové tabulky a další časově platné parametry kategorií; Ranked Tournament Edition používá tabulku své kategorie a sezony podle kapitoly 14.1.

**[PROZATÍMNÍ]** Přesné rozdělení authoringu těchto sezonních tabulek mezi zdrojový Category Package, jeho Run snapshot a pozdější Runové změny zůstává součástí dosud nepotvrzené technické konfigurační hierarchie.

**[ROZHODNUTO V PRINCIPU]** Category Package a jeho Run snapshot musí umět historicky popsat vznik, změnu, deaktivaci a případné nahrazení kategorií i celého kategoriálního systému. Běžné změny platí od začátku nové sezony; podrobnosti jsou v kapitole 14.1.

**[OTEVŘENO]** Přesný datový formát sezonních pravidel, slučování při výslovném přenosu novějšího zdrojového balíčku a úplné UX Run-specific overrides.

**[ODLOŽENO]** Přesné diagnostické UX individuální nekompatibility balíčku s příliš starou nebo novou verzí enginu a migrace jeho samostatného schématu. Nejde o kompatibilitu World Package vůči Category Package.

**[ODLOŽENO DO DALŠÍCH VERZÍ]** Zda a jak mohou dvě srovnatelné sesterské entity sdílet stejný `tier_rank`. Toto téma nebylo pro první verzi uzavřeno; nesmí se z výše rozhodnutého lokálního významu `tier_rank` odvodit povinná unikátnost ani povinné remízy.

## 4.7 Series Package a Calendar Package

**[ROZHODNUTO]** `Series Package` a `Calendar Package` jsou samostatné importovatelné a exportovatelné typy. Calendar Package může odkazovat na Series a Series Package může odkazovat na Category nebo World objekty, ale chybějící reference nebrání samotnému importu.

**[ROZHODNUTO]** Hranice obsahu je:

- `Series Package` nese stabilní Tournament Series a jejich dlouhodobé výchozí vlastnosti,
- `Calendar Package` nese sezonní/weekové plánování a konkrétní Edition Plans.

Konkrétní sezonní weeky a explicitní overrides tedy patří do Calendar Package, nikoliv do dlouhodobé identity Series. Jemný katalog jednotlivých polí a jejich souborové schéma se může technicky dopracovat, aniž by se tato významová hranice znovu otevírala.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Všech pět současných typů `World / Category / Series / Calendar / Setup Package` může vedle úplného obsahu deklarovat výslovně vybraný dílčí scope. Každý partial-scope import je ve výchozím stavu nedestruktivní: upraví pouze výslovně obsažené entity a neuvedený objekt sám o sobě nic nemaže ani nenahrazuje. Úplné nahrazení nebo odstranění musí být samostatná operace pro přesně označený scope, s preview dopadu a výslovným potvrzením. Příklad: Category Package obsahující jedinou Tour nepřímo nesmaže ostatní Tours ani neuvedené kategorie téže Tour.

**[ROZHODNUTO]** Calendar Package může pokrýt právě jednu sezonu, libovolný výběr více sezon nebo všech 50 sezon. Smí pokrývat také jen vymezenou část sezony, například olympijské hry, jednu Tour nebo jednu Tournament Series.

**[ROZHODNUTO][ENGINE INVARIANT]** Sezona nebo věcný scope, který Calendar Package vůbec nezmiňuje, je `mimo rozsah balíčku`. Neznamená prázdný kalendář ani příkaz ke smazání existujících dat.

**[ROZHODNUTO]** Výchozí import Calendar Package slučuje jeho vymezený obsah s existujícím kalendářem přes preview. Úplné nahrazení je možné pouze jako výslovně zvolená operace pro přesně označený scope; nic mimo něj se nesmí tiše odstranit.

## 4.8 Měkké závislosti a neúplné skladby

**[ROZHODNUTO][ENGINE INVARIANT]** Závislosti mezi Packages jsou měkké importní vazby, nikoliv globální blokátory. Category, Series nebo Calendar Package lze importovat i tehdy, když v Runu chybí World, Category, Series nebo jiný odkazovaný objekt.

**[ROZHODNUTO][ENGINE INVARIANT]** Chybějící cíl reference se nesmí potichu změnit na obyčejné `null`. Engine zachová očekávanou původní identitu a označí vazbu jako `Unresolved`, aby ji bylo možné později automaticky či ručně namapovat.

**[ROZHODNUTO V PRINCIPU]** Validace rozlišuje alespoň tři odlišné významy:

- `Not included` – objekt nebo oblast nebyly součástí daného Package či Setupu,
- `Unresolved` – balíček zachoval referenci, jejíž cíl zatím v Runu chybí nebo není namapovaný,
- `Invalid` – přítomná data porušují podporované pravidlo nebo schéma.

Neúplná skladba používá informační nebo oranžové upozornění. Červený problém vzniká pouze u operace, která bez dané závislosti nemůže korektně proběhnout.

**[ROZHODNUTO]** Pozdější import chybějícího Package nebo ruční mapování může `Unresolved` vazbu vyřešit se zachováním provenance.

**[ROZHODNUTO][ENGINE INVARIANT]** Pokud později dorazí přesně hledaná dvojice `source_package_id + source_entity_id`, importní preview oznámí očekávané propojení a po potvrzení importu se vazba automaticky vyřeší. Pouhá shoda názvu nikdy k automatickému mapování nestačí. Ostatní heuristický matching, konfliktní priority a podoba pozdějšího ručního mapovacího UI zůstávají otevřené.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Importní preview používá pro chybějící nebo nekompatibilní závislost jedno bezpečné minimum:

- přesnou známou source identitu připojí pouze při shodě `source_package_id + source_entity_id` a ověřené typové i schématické kompatibilitě; navržené propojení je před potvrzením viditelné,
- bezpečně uložitelná data s chybějícím cílem lze importovat se zachovanou referencí `Unresolved`; objekt dostane oranžové upozornění a zbytek Runu může dál fungovat,
- nekompatibilní či nevalidní závislý logický balíček nelze vynutit: musí se z vybraného importu vynechat, nebo se import zruší; nezávislé validní balíčky mohou pokračovat,
- červený blok vznikne teprve při operaci, která danou závislost skutečně potřebuje, a musí obsahovat příčinu, dopad i přímou cestu k opravě.

Libovolné mapování pouze podle názvu ani neomezené ruční připojení k jiné entitě nepatří do základního pre-alpha importního preview. Bezpečný pozdější ruční mapping zůstává samostatným workflow, které nesmí obcházet kompatibilitu ani provenance.

## 4.9 Setup Package

**[ROZHODNUTO]** `Setup Package` je volitelný kompoziční balíček, který může spojit vybrané World, Category, Series a Calendar Packages, jejich payloady, mapování, validaci a provenance do jednoho přenositelného celku.

**[ROZHODNUTO][ENGINE INVARIANT]** Setup Package sám nepřidává nový druh sportovních pravidel. Pouze skládá obsah a vazby jiných Packages.

**[ROZHODNUTO]** Setup Package může být neúplný: může v něm chybět World, Category, Series, Calendar nebo libovolná jejich část. Smí také zachovat očekávanou, ale unresolved závislost.

**[ROZHODNUTO]** Přenositelný export Setup Package obsahuje skutečné payloady balíčků, které do něj uživatel zahrnul, nikoliv pouze lokální odkazy na zdroje v jednom počítači.

**[ROZHODNUTO][ENGINE INVARIANT]** Každá verze Setup Package je přesný reprodukovatelný snapshot konkrétních verzí zahrnutých Packages. Novější verze některé součásti sama existující Setup nezmění; vědomě změněné složení vytvoří novou verzi stejného Setup Package a starší verze zůstane dostupná.

**[ROZHODNUTO]** Dostupná novější verze zahrnutého Package se označí modrou informací. Oranžové varování vznikne až při skutečném problému s kompatibilitou nebo závislostmi a červený stav pouze tehdy, když kvůli němu nelze provést konkrétní operaci.

**[ROZHODNUTO]** Run nemusí Setup Package použít. Může vzniknout prázdný, být sestaven ručně nebo importovat jednotlivé Packages samostatně.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Aplikace neúplného Setup Package do prázdného nebo rozpracovaného Runu pracuje výhradně s obsahem, který Setup skutečně nese. Preview rozliší přidávané či aktualizované validní komponenty, zcela nezahrnuté části, `Unresolved` vazby a nevalidní logické balíčky. Vybraná validní data se nedestruktivně připraví do Working Draftu; chybějící Packages, prázdný kalendář ani jiné placeholdery se nevytvářejí a nic mimo scope se nemaže. Nezahrnutá nebo unresolved část nezablokuje vznik Runu ani nesouvisející práci, ale operace, která ji skutečně potřebuje, zobrazí přesný červený prerequisite problém. Příklad: Setup obsahující World a Category bez Series a Calendar vytvoří použitelný dílčí stav, ale simulace turnaje zůstane zablokovaná, dokud potřebné závislosti nevzniknou nebo se bezpečně nevyřeší.

## 4.10 Vytvoření balíčku z Runu

**[ROZHODNUTO]** World, kategoriální systém, Tournament Series i kalendář vytvořené ručně uvnitř Runu lze později vyexportovat jako nové nezávislé Packages odpovídajících typů.

**[ROZHODNUTO][ENGINE INVARIANT]** Nový Package si uchová provenance svého vzniku, ale po exportu není živě propojen s Runem. Pozdější změny Package nemění zdrojový Run a změny Runu nemění Package bez další výslovné exportní/importní operace.

**[ROZHODNUTO][ENGINE INVARIANT]** Entita vyexportovaná z Runu do nového Package dostane vlastní stabilní ID v rámci tohoto Package. Původní Runové ID zůstane pouze v provenance; nestane se zdrojovým ID nového balíčku.

**[ROZHODNUTO][ENGINE INVARIANT]** Package exportní soubor obsahuje přesně ten rozsah a ty komponenty, které uživatel výslovně vybral. Engine v preview označí vynechané závislosti a zachová příslušné externí či unresolved reference, ale žádný další objekt, Package ani payload do souboru nepřidá potichu.

## 4.11 Identity, verze a bezpečné aktualizace Packages

**[ROZHODNUTO][ENGINE INVARIANT]** Identitu Package určuje stabilní `package_id`. Běžné uložení editovatelného Package vytvoří novou verzi pod stejným `package_id`; akce `Duplikovat` vytvoří nový Package s novým `package_id` a vlastní verzí 1.

**[ROZHODNUTO]** Všechny předchozí verze Package zůstávají read-only dostupné k prohlížení, porovnání a importu. Výchozím zdrojem je nejnovější verze. Obnovení obsahu starší verze ji nepřepíše ani nevymaže mezilehlou historii: vytvoří novou nejnovější verzi téhož Package.

**[ROZHODNUTO]** Lokální Package se nejprve archivuje a lze jej obnovit. Trvalé smazání je dostupné až z archivu po výslovném potvrzení. Existující Runy se tím nezmění, protože již obsahují vlastní nezávislé kopie importovaného payloadu.

**[ROZHODNUTO][ENGINE INVARIANT]** Export a import téhož Package mezi počítači zachovává jeho `package_id` i číslo konkrétní verze. Novou identitu vytváří pouze výslovná duplikace, nikoliv samotný přenos souboru.

**[ROZHODNUTO][ENGINE INVARIANT]** Zdrojovou identitu entity určuje dvojice `source_package_id + source_entity_id`:

- stejná dvojice označuje tutéž zdrojovou entitu napříč verzemi Package,
- stejné číselné `source_entity_id` v různých Packages označuje ve výchozím stavu různé entity,
- Admin může dvě skutečně totožné entity výslovně ručně namapovat, ale engine je nesmí spojit pouze podle názvu.

Po importu dostane entita vlastní stabilní číselné ID uvnitř Runu a zdrojová dvojice zůstane uložená jako provenance.

**[ODLOŽENO MIMO PRE-ALPHA][PROZATÍMNÍ, SILNÝ SMĚR PRO POZDĚJI]** Pokud už v Runu vznikly dvě skutečně totožné entity, má je jít ručně sloučit pod jedno kanonické Run ID, druhé ID zachovat jako historický alias, bezpečně převést všechny vazby a ponechat provenance všech zdrojů. Přesný merge workflow ještě není pevně rozhodnutý a automatické sloučení jen podle názvu je vyloučené.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Dvě rozdílně pokračující historie se stejným `package_id` engine rozpozná podle verzové ancestry a obsahových identifikátorů a nikdy jednu automaticky ani ručně nepřepíše druhou. Příchozí divergentní historie se odmítne jako aktualizace stávajícího Package. Chce-li ji Admin zachovat, jediným bezpečným pre-alpha workflow je výslovný import jako samostatný nový Package s novým `package_id`, odlišeným názvem a uloženou provenance původní identity a bodu divergence. Stávající Package i všechny jeho Runové kopie zůstanou beze změny.

**[ODLOŽENO MIMO PRE-ALPHA][PROZATÍMNÍ SMĚR]** Pokročilé porovnání a vědomé slučování divergentních Package historií může vzniknout později až s úplným převodem referencí, aliasů, konfliktů a auditní provenance. Pre-alpha raději bezpečně zachová dvě identity, než aby vytvořila zdánlivě sloučený, ale vnitřně poškozený stav.

**[ROZHODNUTO][ENGINE INVARIANT]** Žádný Package konflikt se nevyřeší tichým přepsáním nebo skrytým výběrem. Engine ukáže všechny právě proveditelné logické a datově bezpečné možnosti; jejich konkrétní sada se odvodí z typu konfliktu. Přesné názvy akcí, layout a jemné field-level workflow zůstávají otevřené.

**[ROZHODNUTO]** Opakovaný import přesně stejného Package a verze nikdy nevytvoří duplicity:

- nezměněný obsah se označí `Already imported` a operace je no-op,
- obsah mezitím změněný v Runu se zobrazí v diffu a Admin zvolí některou z datově bezpečných možností, například ponechat Runovou hodnotu, obnovit zdrojovou hodnotu nebo provést podporované výběrové sloučení.

**[ROZHODNUTO]** Při převzetí novější Package verze lze přijmout pouze bezpečně vybranou část změn. Engine znovu ověří všechny její závislosti. Potřebuje-li vybraná změna nevybraná data, preview ukáže vazbu a všechny proveditelné možnosti, například doplnit závislý objekt, ponechat platné `Unresolved`, zachovat starou vazbu nebo operaci zrušit. Nic se nesmí přidat ani změnit potichu.

---

# 5. Země, populace a generování talentu

**Rozsah kapitoly:** datový a generační mechanismus je funkčnost enginu. Konkrétní populační řady, období 1955–2050, šest country ratingů, faktická country data a jejich hodnoty patří k World Package a pro Official FAX World jsou **Official Run defaultem**.

## 5.1 Populační historie

**[ROZHODNUTO]** Každá země má populační historii pro každý rok 1955–2050.

**[ROZHODNUTO]** Při generování hráče se používá populace jeho země v roce jeho narození, nikoliv populace v aktuálním roce simulace.

**[ROZHODNUTO]** Každá země má vlastní vlajku. Vlajka se používá u země a u souvisejících hráčských či soutěžních zobrazení ve Vieweru i Adminu. Přesný grafický styl a zacházení s historickými změnami vlajek se ještě mohou dořešit.

## 5.2 Změny populačních dat

**[ROZHODNUTO]** Když admin upraví populaci nebo generační parametry, už existující vygenerovaní hráči se zpětně nemění.

Změna ovlivní pouze budoucí generování.

**[ROZHODNUTO V PRINCIPU]** Engine na nesoulad po takové změně výrazně upozorní. Přesné typy varování, jejich počet a možnost přepočtu se ještě doladí.

## 5.3 Country Model V1: sampling a conversion

**[ROZHODNUTO PRO PRVNÍ VERZI][RUN CONFIG]** Každá země má šest vzájemně významově odlišených ručně authorovaných ratingů na společné škále `1–5`:

1. `Squash Popularity` — pravděpodobnost či tendence, že člověk v dané zemi začne squash aktivně hrát; nejde o fanouškovskou sledovanost.
2. `Squash Access` — praktická možnost hrát pravidelně: dostupnost kurtů, geografická a cenová dostupnost, kluby a možnost trénovat.
3. `Development Quality` — jak efektivně země hráče rozpozná a rozvíjí: coaching, metodika, talent identification, junior pathway, tréninková centra, sport science a základní fungování federace.
4. `Competition Quality` — kvalita a dostupnost přiměřených soutěží a zápasových příležitostí, včetně možnosti potkávat kvalitní soupeře a získat mezinárodní zkušenost.
5. `Elite Support` — jak dobře země umožní elitnímu juniorovi přejít k profesionálnímu sportu: finance, cestování, zahraniční turnaje, fyzio, kondiční příprava, sportovní medicína a případná stipendia.
6. `Squash Tradition` — dlouhodobá kultura, know-how a kontinuita: bývalí hráči a trenéři, role models, historické kluby a generačně předávaná znalost cesty sportem.

`Squash Tradition` může ostatní části pipeline mírně podporovat, ale v první verzi nesmí fungovat jako silný přímý bonus k hráčovým schopnostem nebo OVR. Přesné relativní váhy všech šesti ratingů zůstávají otevřené.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Competition Quality` není totéž co `Competitive Depth`. První je authorovaný popis soutěžních příležitostí země. Druhá musí být odvozena z hráčů a konkurence, kteří v daném čase skutečně existují v konkrétní branchi Runu; Egypt ani jiná země proto nedostane hloubku pouze ručně zadaným labelem.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Vedle ratingů zůstávají oddělená faktická data, nikoliv další ratingy: `Population Timeline`, `Area`, `Region`, `Travel Region`, `Timezone Area` a případně `Court Count`. `Travel Region` a `Timezone Area` se řídí geografickým modelem kapitoly 5.5. Konkrétní počet kurtů může být užitečným vstupem nebo validačním údajem, ale sám nenahrazuje rating `Squash Access`.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Engine z autoritativního stavu dopočítává hodnoty, které se nemají ručně ukládat jako další pevné country ratingy: minimálně `Effective Squash Pool`, `Competitive Depth`, `Talent Discovery Rate`, `Professional Conversion Rate` a `Current Country Strength`. Každá odvozená hodnota musí respektovat čas, branch a použitou verzi modelu.

**[ROZHODNUTO V PRINCIPU]** Země přímo neurčuje vrozenou distribuci talentu, potenciálový strop, technický či mentální bias ani národní `style_dna`. Vrozený talent je na úrovni jednotlivce globálně možný: i malá nebo systémově slabší země má nenulovou šanci na generační `L+` talent. Země ovlivňuje především sampling a conversion — kolik lidí začne hrát, zda jsou objeveni, jak se rozvinou, jakou získají soutěžní zkušenost a zda dostanou možnost přejít k profesionálům. Silná squashová země proto opakovaně vytváří více kvalitních hráčů díky hlubší pipeline, nikoliv genetickou nebo národní předurčeností.

Základní logická posloupnost první verze je:

`Population → Squash Popularity → Squash Access → Effective Squash Pool → náhodné vrozené talenty → Talent Discovery → Development Quality → Competition Quality → Elite Support → Professional Players`

`Squash Tradition` tuto pipeline pouze mírně moduluje. Velká populace sama o sobě nesmí automaticky vytvořit nejlepší hráče a velký aktivní pool zvyšuje počet příležitostí mimořádný talent nalézt, nikoliv talent každého jednotlivce.

**[ODLOŽENO]** Přesné váhy, vzorce, konverzní poměry, význam hranic `1/2/3/4/5`, roční velikost světového poolu, kalibrace jednotlivých zemí, dynamické změny ratingů v průběhu historie a jejich zpětné vazby. Národní `style_dna` se nebude zavádět, dokud nebudou dostatečně zralé individuální atributy, styly a jejich simulační logika; případný budoucí návrh nesmí porušit výše rozhodnutou hranici vrozeného talentu.

## 5.4 CSV/XLSX import zemí a populace

**[ROZHODNUTO]** Hromadný import zemí a populačních dat přes CSV/XLSX je možný pouze u editovatelných lokálních Runů/balíčků.

**[ROZHODNUTO]** Import nelze použít k přímé změně vestavěných GitHub Runů nebo read-only World Packages.

**[ROZHODNUTO]** Každý import nejdříve zobrazí preview:

- plánované změny,
- nalezené chyby,
- varování a problematické řádky.

Data se skutečně zapíší až po výslovném potvrzení uživatele.

**[ROZHODNUTO]** Import se nejprve zpracuje v oddělené staging vrstvě a před potvrzením nesmí změnit Run ani balíček. Preview rozdělí řádky minimálně na platné, platné s varováním a chybné.

**[ROZHODNUTO]** Každá chyba ukáže:

- přesný řádek a sloupec,
- zadanou problematickou hodnotu,
- proč je neplatná,
- očekávaný formát, rozsah nebo vazbu,
- příklad správného zápisu,
- doporučený způsob opravy.

Hodnotu lze opravit přímo v preview a znovu validovat bez povinného nového nahrání souboru.

**[ROZHODNUTO]** Jednoznačné technické opravy může Admin nabídnout jednotlivě nebo hromadně. Oprava, která může změnit význam dat, se nikdy neprovede tiše a vyžaduje výslovné potvrzení.

**[ROZHODNUTO]** Hard errors standardní import blokují. Uživatel však může výslovně zvolit `Importovat pouze platné řádky`, pokud engine ověří, že přeskočení chybných řádků neporuší referenční vazby ani konzistenci výsledku. V opačném případě je částečný import zakázán a preview přesně vysvětlí proč.

**[ROZHODNUTO]** Potvrzený zápis je atomický: buď se zapíše celý schválený výsledek, nebo nic. Jedna potvrzená importní dávka tvoří jeden auditní záznam a jeden krok v Undo; odmítnuté či přeskočené řádky zůstávají v přehledu chyb.

**[ODLOŽENO]** Přesné mapování libovolně pojmenovaných sloupců, úplná sada doménových validačních pravidel a konkrétní vzhled importního editoru.

## 5.5 Zjednodušená geografie, cestování a časová pásma

**[ROZHODNUTO V PRINCIPU]** World Package může přiřadit země a jejich podporované vnitřní oblasti současně do dvou nezávislých geografických vrstev:

- `Travel Region` představuje hrubou fyzickou cestovní vzdálenost nebo náročnost přesunu,
- `Timezone Area` představuje posun biologického času a vstup pro jet lag.

Stejná dvojice míst proto může být fyzicky vzdálená bez velkého časového posunu nebo naopak překročit více Timezone Areas při odlišné cestovní topologii. Turnaj přebírá obě hodnoty z konkrétní hostitelské oblasti či venue, nikoliv nutně pouze ze země.

**[ROZHODNUTO PRO PRVNÍ ZJEDNODUŠENOU VERZI]** Fyzická vzdálenost se nepočítá v kilometrech. Pracuje se jen s hrubým počtem podporovaných přechodů mezi Travel Regions a Timezone Areas. Počet těchto oblastí není globální neměnná konstanta a může jej určit World Package.

**[ROZHODNUTO V PRINCIPU]** Timezone Areas tvoří kruh: první a poslední oblast spolu sousedí. Engine používá nejkratší podporovaný posun po kruhu a uchovává také směr cesty. Směr na východ a na západ nejsou biologicky totožné; v základním modelu může cesta na východ vytvářet vyšší jet-lag zátěž než stejně velký posun na západ.

**[ROZHODNUTO PRO PRVNÍ ZJEDNODUŠENOU VERZI]** Dokud se nesimuluje přesný pobyt a okamžik příjezdu hráče, jet lag se odvozuje z poslední známé turnajové či zápasové Timezone Area a časového odstupu do dalšího zápasu. Čím více weeků oba zápasy odděluje, tím menší je účinek a po dostatečně dlouhé mezeře se neuplatní. Pokud předchozí použitelná poloha není známá, hráč se považuje za aklimatizovaného. Přesný počet weeků, při kterém účinek zeslábne nebo zanikne, není rozhodnutý.

**[ROZHODNUTO PRO PRVNÍ ZJEDNODUŠENOU VERZI]** Každý proveditelný přesun mezi dvěma navazujícími turnajovými závazky automaticky dostane krátkodobou úroveň `Low / Medium / High Travel Load`. Určí ji hrubá vzdálenost podle podporovaných Travel Regions a abstraktní čas dostupný mezi posledním relevantním slotem předchozí akce a prvním slotem následující akce. Nejde o nový hráčský atribut ani o čtvrtý fyzický bar a první verze nesimuluje jednotlivé lety.

`Travel Load` dočasně:

- přidává obecnou `Fatigue`,
- omezuje recovery,
- snižuje počáteční naplnění tří fyzických stamina barů v následujícím zápase,
- postupně odeznívá odpočinkem,
- nikdy sám nemění trvalé hráčské atributy.

Fyzický `Travel Load` a biologický jet lag z Timezone Areas zůstávají významově oddělené vrstvy téhož přesunu. Přesné hodnoty, hranice úrovní, rychlost odeznívání a síla dopadu se musí kalibrovat později.

**[PROZATÍMNÍ]** Už první verze může každému hráči generovat dvě oddělené individuální predispozice:

- `Jet Lag Resistance` – odolnost vůči změně časových pásem a rychlost aklimatizace,
- `Travel Resilience` – odolnost vůči fyzické cestovní zátěži.

Nejde o jednu společnou vlastnost a vysoká hodnota nemá zaručit bezchybnou reakci při každém přesunu. Přesná veřejnost hodnot, náhodnost a vztah k formě, únavě a recovery se rozhodnou později.

**[ODLOŽENO]** Přesné vzorce a prahy `Travel Load`, křivky odeznívání, směrové koeficienty, síť a sousednost Travel Regions, přesná síla vlivu na Fatigue, recovery a počáteční stamina i případný detailní model letů, tras, příjezdů, víz a postupné aklimatizace.

**[VÝSLOVNĚ PŘESKOČENO]** Hráčův `Origin Area`, `Home Base`, přesné současné místo pobytu, návraty domů, více základen a rozhodovací AI pobytu se nyní nezavádějí. Případný pozdější model nesmí být zpětně vydáván za již rozhodnutou součást první verze.

**[PROZATÍMNÍ]** Dokud neexistuje spolehlivý model bydliště, tréninkové základny, místa utkání a publika, první verze nemá přidávat automatický domácí bonus pouze podle shody národnosti hráče a hostitelské země. Pozdější domácí efekt může podle konkrétního hráče pomáhat i škodit, ale nyní nebyl rozhodnut.

---

# 6. Čas, sezony a aktuální bod historie

**Rozsah kapitoly:** časový model, historický Viewer a pořadí událostí jsou funkčnost enginu. Rozsah 50 sezon × 61 weeků je výslovně současný Engine invariant pro všechny Runy; naplánovaný obsah weeků a případná interní procesní okna jsou stavem či konfigurací konkrétního Runu.

## 6.1 Časová identita

**[ROZHODNUTO][ENGINE INVARIANT PRO SOUČASNOU VERZI]** Fiktivní svět FAX používá kalendářní rok o přesně 61 weecích. Přesná kalendářní data ani jednotlivé dny v datovém modelu neexistují; čas se zapisuje pouze pomocí roku a weeku.

**[ROZHODNUTO]** Engine rozlišuje dvě souběžná číslování:

- `Year Week` – pořadí weeku v kalendářním roce, vždy 1–61,
- `Season Week` – pořadí weeku v sezoně, vždy 1–61.

**[ROZHODNUTO]** Každý nový kalendářní rok začíná současně jako `Year Week 1` a `Season Week 26`. Z toho plyne například pro sezonu `2000/01`:

- `Season Week 1` = `Year 2000, Year Week 37`,
- `Season Week 25` = `Year 2000, Year Week 61`,
- `Season Week 26` = `Year 2001, Year Week 1`,
- `Season Week 61` = `Year 2001, Year Week 36`.

**[ROZHODNUTO]** Narození hráče se ukládá jako `birth_year` a `birth_year_week`. Odpovídající sezona a `Season Week` se z těchto údajů jednoznačně dopočítají. Přesné kalendářní datum narození neexistuje.

## 6.2 Dokončený týden

**[ROZHODNUTO]** Historický Viewer stav lze zvolit pro kterýkoliv dokončený a vygenerovaný week.

**[ROZHODNUTO]** Viewer však zároveň ukazuje i právě probíhající aktuální week. V něm zobrazí všechny dokončené a uložené zápasy, kola, turnaje a další již platná data. Nedokončené části jsou označené jako probíhající nebo čekající.

**[ROZHODNUTO]** Budoucí dosud nezahájený week nelze otevřít jako Viewer stav.

**[ROZHODNUTO]** Stav týdne se zobrazuje po jeho dokončení a před začátkem dalšího týdne. Zahrnuje všechny výsledky, rankingy, statistiky a záznamy vzniklé do konce tohoto týdne včetně.

**[ROZHODNUTO]** I week bez jediného naplánovaného turnaje nebo zápasu se musí normálně zpracovat a dokončit. Proběhne zejména stárnutí podle `birth_year_week`, příchod nových patnáctiletých prospectů, vývoj hráčů a vytvoření dalšího oficiálního rankingového snapshotu, i když se jeho pořadí a body nezmění.

## 6.3 Viewer time machine

**[ROZHODNUTO]** Ve Vieweru se lze přepnout na libovolný dokončený a vygenerovaný week.

Celý Viewer se potom chová, jako by právě nastal konec vybraného týdne:

- ukáže pouze výsledky a informace známé do tohoto bodu,
- ranking, statistiky, H2H a profily odpovídají tomuto bodu,
- pozdější výsledky se nezobrazí,
- ani data již vygenerovaná několik let dopředu nesmějí uniknout do staršího pohledu.

**[ROZHODNUTO]** Budoucí výsledky vůči vybranému weeku nejsou ve Vieweru viditelné.

**[ROZHODNUTO]** Při běžném otevření Vieweru se automaticky zobrazí nejnovější uložený bod `Viewer Branch` vybraného Runu. Historický week se volí ručně.

**[ROZHODNUTO V PRINCIPU]** Viewer smí v historickém weeku zobrazit pouze tehdy už veřejně oznámené budoucí Tournament Editions a jejich poslední veřejně známé údaje podle kapitoly 13.9. Interní plán, neoznámené změny, budoucí výsledky ani data odvozená z pozdějšího stavu se nesmějí prozradit. **[ODLOŽENO]** Přesný layout a rozsah veřejných detailů budoucího turnaje.

## 6.4 Zobrazení současného časového bodu

**[ROZHODNUTO]** Vedle globální volby Runu a přepínače Viewer/Admin je na každé stránce s aktivním Runem jeden společný ovladač pro výběr prohlížené sezony a weeku. Nejde o dvě nesouvisející globální volby. Jeho kompaktní popisek respektuje níže zvolený roční, sezonní nebo kombinovaný formát zobrazení. Globální stránky bez Runu tento ovladač nemají.

**[ROZHODNUTO]** Změna globální sezony/weeku pouze mění prohlížený časový kontext. Sama nikdy neposune, nevrátí, nepřepočítá ani jinak nezmění skutečný stav simulace.

**[ROZHODNUTO V PRINCIPU]** Po otevření ovladač nabídne výběr sezony a Weeků 1–61, označí skutečný aktuální bod simulace a významové stavy dostupných weeků. Viewer dovolí pouze časové body, které smí podle kapitol 6.2 a 6.3 skutečně zobrazit; Admin může stejným ovladačem přejít také do podporovaného budoucího weeku kvůli plánování, aniž by jej vydával za již simulovanou současnost. Přesný grafický layout panelu se ještě může změnit.

**[ROZHODNUTO]** Pod kompaktním season/week ovladačem je přímo viditelný stav jeho vztahu k současnému bodu:

- Viewer používá `PRESENT` pro nejnovější dostupný stav `Viewer Branch` a `PAST` pro starší zvolený week,
- Admin používá `PRESENT` pro současný bod aktivní branche, `PAST` pro její starší stav a `FUTURE` pro podporovaný budoucí plánovací week.

Kliknutí na `PAST` ve Vieweru nebo na `PAST` či `FUTURE` v Adminu okamžitě vrátí pouze prohlížený kontext do `PRESENT`. Samo nikdy neposune, nevrátí ani jinak nezmění simulaci.

**[ROZHODNUTO]** Globální Viewer ovladač současnosti umožňuje přepínat tři způsoby zobrazení téhož časového bodu:

- `Roční` – například `Year 2001 · Week 1`,
- `Sezonní` – například `Season 2000/01 · Week 26`,
- `Obojí` – současně zobrazí Year Week i Season Week.

Přepnutí režimu nijak nemění vybraný historický bod ani data; mění pouze jeho formát zobrazení.

**[ROZHODNUTO]** Výchozí režim je `Roční`. Uživatelova zvolená varianta se ukládá jako globální zobrazovací preference.

## 6.5 Week Transition

**[ROZHODNUTO PRO PRVNÍ VERZI]** Přechod z právě dokončeného weeku do následujícího weeku tvoří samostatný automatický `Week Transition`. Nejde o běžný interní Simulation Slot a nezapočítává se do jejich počtu.

**[ROZHODNUTO PRO PRVNÍ VERZI][ENGINE INVARIANT]** Celý Week Transition je atomický: nejprve vznikne staging výsledek všech kroků, potom proběhne validace a teprve úspěšný celek se jedním commitem stane stavem nového weeku. Chyba v pozdějším kroku nesmí ponechat napůl zapsaný development, recovery, narozeniny, body ani ranking.

Při přechodu například `Week 20 → Week 21` platí toto úplné hlavní pořadí:

1. `Preflight & Staging` ověří uzavření Weeku 20, prerequisites a připraví izolovaný kandidátní stav.
2. `Weekly Player Development Update` zpracuje celý dokončený Week 20 podle policy platné pro Week 20. Použije jeho konečnou Form ještě před týdenním návratem k normálu.
3. `Between-Week State Update` podle policy dokončeného Weeku provede zejména návrat Form, případný decay Match Sharpness, recovery Fatigue a průběžné hojení zdravotních stavů; nic z toho se neresetuje.
4. Aktivují se konfigurace a policy účinné od Weeku 21.
5. Proběhnou narozeniny, vznik nových patnáctiletých prospectů a ostatní podporované lifecycle změny při otevření Weeku 21.
6. Atomicky se vyhodnotí expirace starých výsledků, aktivace nově splatných výsledků, účinné disciplinární zásahy a pozdější korekční události.
7. Z autoritativních vstupů se právě jednou přepočítá `Official MSA Ranking – Week 21` podle rankingové policy účinné ve Weeku 21.
8. Vzniknou veřejné události a počáteční veřejný stav Weeku 21.
9. Celý staging stav projde závěrečnou validací a buď se atomicky commitne, nebo se nezapíše nic.

Veřejné události z kroku 8 se publikují až spolu s úspěšným commitem kroku 9; neúspěšný transition nesmí do Vieweru ani World Event Logu propustit kandidátní nový-week stav.

Do Week Transitionu patří také jediné týdenní vyhodnocení Financial Levelu. Jeho přesné umístění mezi kompatibilními podkroky ještě není rozhodnuté; nesmí však porušit výše uzavřené kauzální pořadí ani způsobit více nezávislých přepočtů v jednom weeku.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Weekly Player Development Update vyhodnotí u všech evidovaných hráčů podporované měnitelné sportovní hodnoty. Vyhodnocení neznamená povinnou číselnou změnu každého atributu: schopnost se může zlepšit, zhoršit nebo zůstat stejná. Model může zohlednit zejména věk, potenciál, predispozice, abstraktní trénink a přípravu, zápasové vytížení, zdraví, dosavadní vývoj a náhodnost.

**[ROZHODNUTO PRO PRVNÍ VERZI][ENGINE INVARIANT]** Transition `Week 20 → Week 21` smí development vypočítat pouze z informací a událostí známých nejpozději do konce Weeku 20. Nové hodnoty začnou platit otevřením Weeku 21 a všechny jeho první současné události je čtou ze stejného počátečního stavu. Budoucí naplánované události Weeku 21 nesmějí zpětně ovlivnit tento výpočet.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Nová development policy účinná od Weeku 21 neovlivní vývoj za Week 20; poprvé řídí development událostí Weeku 21, jehož výsledek se projeví při otevření Weeku 22. Naproti tomu nová rankingová policy účinná od Weeku 21 se použije už pro Official Ranking Weeku 21. Dříve získaný turnajový výsledek si zachovává bodovou hodnotu podle pravidel svého vzniku, dokud výslovné pravidlo neříká jinak.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Před vytvořením každého Official Rankingu se ranking povinně znovu vypočítá z autoritativních výsledků, jejich platnosti, disciplinárních a korekčních událostí a právě účinné Ranking Policy. Rozpor mezi takto vypočteným výsledkem a kandidátním snapshotem je červená chyba a zablokuje celý atomický Week Transition; rankingový snapshot ani vypočtené body nelze ručně přepsat jako primární data.

Aktuální forma, únava, zdraví a další krátkodobé stavy se mohou měnit také uvnitř weeku podle zápasů a jiných událostí. Week Transition je automaticky nevynuluje; pouze na ně aplikuje podporovaný týdenní recovery či další časový vývoj. **[ODLOŽENO]** Development a recovery matematika, přesné pořadí navzájem nezávislých podkroků uvnitř výše uzavřených vrstev a úplný katalog dalších týdenních změn. Hlavní devítikrokové pořadí už otevřené není.

## 6.6 Globální časová osa a Simulation Slots

**[ROZHODNUTO PRO PRVNÍ VERZI]** Week není jeden nedělitelný okamžik. Uvnitř obsahuje chronologicky uspořádanou, pro celý svět a aktivní branch společnou časovou osu `Simulation Slots`. Počet slotů není pevný; vznikne jich tolik, kolik daný week potřebuje podle svého skutečného obsahu a návazností.

`Simulation Slot` je časová jednotka a nesmí se plést s fyzickým slotem hráče v turnajovém pavouku, Q slotem ani idealizovaným seed slotem z kapitoly 15.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Jeden slot může obsahovat více logicky současných událostí z různých turnajů a částí světa. Všechny současné události vycházejí ze stejného zmrazeného vstupního snapshotu na začátku slotu. Výsledek jedné proto nesmí změnit vstupy jiné události téhož slotu a technické pořadí jejich výpočtu nesmí nikoho zvýhodnit.

Jednotlivé události mají návaznosti a prerequisites. Los musí předcházet svým zápasům, feeder zápasy příslušnému dalšímu kolu, kvalifikace potřebné části Main Draw a dokončení turnaje jeho navazujícím operacím. Engine podle těchto vazeb sestaví platné pořadí; přesný scheduler a katalog všech typů závislostí zůstávají otevřené.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Do následujícího slotu nelze postoupit, dokud nejsou všechny povinné události současného slotu vyřešené. Vyřešení nemusí znamenat odehrání: příslušná událost může mít také platný konečný stav typu W/O, zrušení nebo přesunutí. Nesmí však zůstat bez výsledného technického stavu.

**[ROZHODNUTO PRO PRVNÍ VERZI][ENGINE INVARIANT]** Atomickou jednotkou uvnitř slotu není automaticky celý slot, ale jedna nezávislá událost nebo jedna kauzálně či konfliktně propojená skupina událostí. Nezávislou dokončenou skupinu lze platně uložit a po uložení zobrazit ve Vieweru, aniž by technická chyba jiné skupiny její výsledek zrušila. Nevyřešené skupiny téhož slotu však stále používají původní společný `slot-start snapshot`; dříve uložený souběžný výsledek nesmí potichu změnit jejich vstupy.

Každá taková skupina používá stejnou šestivrstvou procesní kostru: načíst zmrazené slotové vstupy → vypočítat kandidátní výsledky do stagingu bez autoritativního zápisu → uvnitř skupiny společně vyřešit konflikty → zvalidovat celý její batch → atomicky jej commitnout → zveřejnit pouze výstupy, které už smějí z tohoto commitu vzniknout. Pozdější rozdělení atomické hranice na skupiny tedy neruší dříve potvrzenou procesní kostru; pouze ji nevztahuje bezdůvodně na celý globální slot.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Celý globální Simulation Slot používá toto jednotné hlavní pořadí:

1. `Slot-Start Activation` aktivuje pouze změny, které už mají být účinné na začátku slotu; událost, jejíž výsledek má ovlivnit jiné rozhodnutí, musí být účinná před jeho snapshotem nebo ležet v předchozím slotu.
2. `Freeze Slot-Start Snapshot` ověří prerequisites, sestaví množinu právě splatných událostí a zmrazí jejich společný autoritativní vstup.
3. `Calculate to Staging` vypočítá všechny události a kandidátní změny bez přímého zápisu do autoritativní historie.
4. `Resolve Conflicts` společně vyřeší každou kauzálně či konfliktně propojenou skupinu; nezávislé skupiny se navzájem neovlivní.
5. `Validate and Commit` zvaliduje celý batch každé skupiny a atomicky jej uloží, nebo z něj neuloží nic; hotové nezávislé skupiny se kvůli chybě jiné skupiny nevracejí.
6. `Publish Committed Outputs` zveřejní pouze data odvozená z úspěšného commitu, například výsledek zápasu, H2H, entry list nebo World Event; kandidátní staging data se nikdy nezveřejní.
7. `Close Slot` dovolí vytvořit snapshot následujícího slotu až poté, co všechny povinné události současného slotu mají platný terminální stav.

Toto pořadí je testovatelný kontrakt první pre-alpha verze, nikoliv zákaz jeho pozdějšího vědomého zlepšení podle výsledků skutečné simulace. Neurčuje pevný katalog obsahu každého slotu: scheduler stále volí splatné události podle jejich času a závislostí. Příklad: všichni hráči nejprve ze společného snapshotu provedou entry rozhodnutí, celý konfliktní entry batch se vyřeší a uloží a teprve potom se zveřejní nový entry list. Los, který tento list používá jako vstup, patří až do navazujícího slotu.

Události sdílející rozhodný zdroj nebo vzájemný konflikt tvoří jeden atomický batch. Příklad: všechna současná entry rozhodnutí měnící tentýž field se zvalidují a publikují společně, zatímco deset navzájem nezávislých zápasů může být dokončeno a uloženo po jednotlivých zápasech.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Po dokončení skupiny se mohou ihned aktualizovat pouze výstupy závislé výhradně na ní, například výsledek zápasu a H2H. Agregát vyžadující úplný relevantní batch čeká na jeho uzavření. Známý feeder se do navazujícího zápasu doplní okamžitě; neznámá strana zůstane placeholderem. Navazující zápas se nesmí spustit, dokud nemá všechny prerequisites a není uzavřen předchozí globální slot.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Retry neúspěšné skupiny se stejnými vstupy a stejnou verzí modelu zachová její seed i kandidátní výsledek. Nový náhodný průběh smí vzniknout až po relevantní změně vstupu nebo výslovné akci `Resimulate`; dokončené nezávislé skupiny se při retry znovu nehází.

Globální model první verze nepředstírá přesné hodiny. `Simulation Slot` je jediná autoritativní časová osa celé aktivní branche. Procesní okna ani turnajové `Match Day Slots` nejsou dalšími hodinami: pouze popisují význam nebo seskupení konkrétních globálních slotů.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Procesní okno nabývá účinnosti na hranici konkrétního globálního slotu. Například `Draw Freeze` nezačne neurčitě „během weeku“, ale od určeného `Simulation Slotu`; všechny následující operace už čtou zmrazený stav.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Turnajový `Match Day Slot` z kapitoly 13.4 představuje hrací den bez přesných hodin a mapuje se na jeden nebo více po sobě jdoucích globálních Simulation Slots. Uložené pořadí zápasů jednoho dne vytváří chronologické závislosti. Pozdější zápas stejného hráče musí být v pozdějším globálním slotu, aby četl únavu, zdraví a ostatní následky dřívějšího zápasu. Následující Match Day Slot smí začít teprve po terminálním vyřešení všech předchozích zápasů, které jeho obsah skutečně potřebuje.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Scheduler skládá společnou globální osu topologicky podle časových a kauzálních závislostí. Nezávislé události z různých turnajů mohou sdílet jeden Simulation Slot; závislá událost musí ležet později. Příklad: globální slot `14` aktivuje Draw Freeze, sloty `15–17` mohou nést postupné pondělní zápasy turnajů A a B a slot `18` otevře jejich úterní Match Day Slot, pokud jsou jeho prerequisites splněné. Přesný optimalizační algoritmus scheduleru zůstává technickým detailem, ale jedna globální osa a dependency pravidla už otevřené nejsou.

## 6.7 Vnitřní procesní okna weeku

**[ROZHODNUTO PRO PRVNÍ VERZI]** Některé Simulation Slots nebo jejich skupiny mohou plnit roli interních procesních oken, aniž by se celý engine musel standardně dělit na jednotlivé kalendářní dny. V jednotlivých oknech mohou například nastávat přihlášení, odhlášení a další změny dostupnosti hráčů. Pro každý Qualification a Main Draw samostatně platí:

- dřívější okna před `Redraw Cutoff` dovolují úplné přelosování dotčeného losu,
- předposlední okno začíná `Redraw Cutoff` a používá případný seed cascade,
- poslední okno začíná `Draw Freeze` a dovoluje už jen přímé doplnění konkrétního fyzického slotu.

`Main Entry Window` a `Qualification Entry Window` z kapitoly 15 jsou vícerozsažné přihlašovací fáze měřené ve weecích. Nejsou totožné s jedním interním procesním oknem; uvnitř každého jejich weeku může proběhnout několik menších příležitostí k rozhodnutím hráčů.

**[ROZHODNUTO PRO PRVNÍ VERZI]** V každém skutečně nakonfigurovaném entry decision slotu smí hráčská AI znovu vyhodnotit a změnit své dosavadní přihlášky podle kapitoly 15.1. Toto rozhoduje chování existujícího slotu, nikoliv jejich pevný počet. Každé procesní okno se mapuje na hranici konkrétního globálního Simulation Slotu podle kapitoly 6.6.

**[ODLOŽENO]** Celkový počet, přesné názvy a délka časných procesních oken, pravděpodobnosti jejich událostí, výchozí rozložení a optimalizační detaily jejich skládání s více souběžnými turnaji. Dřívější dialog žádný pevný počet neuzavřel; zejména minimum sedmi oken není rozhodnuté pravidlo. Funkce předposledního a posledního okna i jejich vztah k jediné globální slotové ose již otevřené nejsou.

## 6.8 Season Transition

**[ROZHODNUTO PRO PRVNÍ VERZI]** Přechod ze `Season Weeku 61` do `Season Weeku 1` následující sezony používá `Season Transition`. Nejde o druhé nezávislé hodiny ani o běžný Simulation Slot, ale o speciální sezonní rozšíření standardního Week Transitionu. Provede všechny běžné týdenní operace a navíc kontrolovaně uzavře starou a otevře novou sezonu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Season Transition lze dokončit pouze tehdy, když všechny povinné události uzavírané sezony a jejich závislosti mají platný konečný stav. Nevyřešené finále, chybějící technické ukončení nebo jiný skutečný prerequisite vyvolá červený operation-scoped problém, který přesně označí blokující objekt a zastaví pouze přechod do nové sezony. Turnaj ani jinou povinnou událost nelze jen přeskočit.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Jedna Tournament Edition nesmí překročit hranici `Season Week 61 → Season Week 1`. Plán, který by ji překračoval, je okamžitě červeně neplatný a nelze jej potvrdit ani uložit. Pokročilejší podpora přeshraničních Editions je mimo první verzi.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Při otevření nové sezony se atomicky aktivují všechny časově verzované policy, kategorie, formáty a další změny naplánované s účinností od této sezony. Dokončená sezona zůstává navždy vyhodnocená podle tehdy platných pravidel; pozdější aktivace ji potichu nepřepočítá. Zpětná vědomá změna používá obecný history/branch workflow z kapitoly 7.

**[ROZHODNUTO]** Součástí přípravy nové sezony je předvyplnění bodové tabulky každé pokračující kategorie efektivní tabulkou bezprostředně předchozí sezony. Jde o upravitelný výchozí stav nové sezony, nikoliv zpětnou změnu staré tabulky; podrobnosti jsou v kapitole 14.1.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Na sezonní hranici neexistuje univerzální reset světa nebo hráčů. Vynulují či znovu inicializují se pouze hodnoty výslovně definované jako season-scoped, například příslušná sezonní Race nebo sezonní čítače. Rankingové výsledky a jejich platnost, atributy, forma, únava, zdraví, lifecycle hráčů, rivality a ostatní kontinuální stavy se přenesou dál a případně se změní pouze svými běžnými časovými pravidly.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Konečné season-scoped statistiky se před resetem zmrazí do sezonního souhrnu; kariérní statistiky pokračují bez resetu. Stejně tak disciplinární postih trvající ještě `X` weeků pokračuje přes sezonní hranici podle zbývající doby a nezačíná znovu ani nezaniká pouze změnou sezony.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Úspěšné uzavření vytvoří lehký `Season Closure Marker`, nikoliv další úplnou kopii světa. Marker označí dokončenou sezonu, branch a její konečný uložený bod, přímo odkazuje na samostatný `Season Closing Ranking` z kapitoly 18.5.1 a uchovává verze pravidel použité při uzavření. Výsledky, statistiky, hráčské stavy a ostatní obsah se nadále čtou z již existující autoritativní historie.

**[ROZHODNUTO PRO PRVNÍ VERZI][ENGINE INVARIANT]** Season Transition je jeden atomický staging proces v tomto hlavním pořadí:

1. ověřit úplnost Season Weeku 61 a zákaz Edition překračující sezonní hranici,
2. podle odcházejících pravidel vytvořit `Season Closing Ranking` zahrnující i výsledky dokončené ve Weeku 61,
3. zmrazit season-scoped statistiky do sezonního souhrnu a vytvořit `Season Closure Marker`,
4. provést development za dokončený Week 61 a navazující Between-Week State Update podle odcházejících pravidel,
5. aktivovat pravidla nové sezony a vynulovat nebo znovu inicializovat pouze výslovně season-scoped hodnoty,
6. provést narozeniny, lifecycle a vznik prospectů při otevření Weeku 1,
7. vytvořit `Official MSA Ranking – Week 1` podle nové Ranking Policy,
8. vytvořit veřejné události a počáteční stav nové sezony,
9. celý kandidátní stav zvalidovat a atomicky commitnout; při chybě se nezapíše žádná jeho část.

U poslední sezony 2049/50 se po kroku 3 Run uzavře jako `Completed`: kroky 4–8 určené k otevření dalšího weeku se neprovedou a nevytváří se další sezona, její Week 1 ani nový Official Ranking. Krok 9 pouze zvaliduje a atomicky uloží toto konečné uzavření.

Season Transition nevyžaduje kompletně ručně připravený kalendář všech budoucích sezon. Validuje uzavíranou sezonu a právě otevíraný rozsah podle skutečných operation-scoped prerequisites; neúplná vzdálená budoucnost nesmí bezdůvodně blokovat přechod. Materializaci plánů a Tournament Editions nové sezony popisuje kapitola 13.3.

**[ODLOŽENO]** Datové schéma Closure Markeru, podrobný katalog season-scoped hodnot, přesné pořadí navzájem nezávislých podkroků uvnitř výše uzavřených vrstev a konečný Season Transition UX. Hlavní devítikrokové pořadí už otevřené není.

---

# 7. Branch a checkpoint model

## 7.1 Branch

**[ROZHODNUTO]** Branch je samostatná časová linie uvnitř Runu.

**[ROZHODNUTO][ENGINE INVARIANT]** Od bodu odvětvení může mít každá branch vlastní časově platný stav prakticky všech simulovaných dat: kalendář a Tournament Editions, účastníky a losy, výsledky, rankingy a statistiky, stav hráčů včetně atributů, formy, únavy a zdraví i pozdější změny pravidel a konfigurace. Kvůli alternativnímu kalendáři, atributům hráče nebo jinému vývoji světa není nutné zakládat nový Run.

**[ROZHODNUTO][ENGINE INVARIANT]** Branche téhož Runu sdílejí `run_id`, ale každá má vlastní `branch_id`. Společná minulost před bodem odvětvení se fyzicky ukládá pouze jednou a branch uchovává vlastní rozdíly od společného základu. Tentýž hráč si napříč branchemi zachovává `player_id`, zatímco jeho časově proměnlivý stav je verzovaný podle branche a weeku.

**[ROZHODNUTO]** Všechny běžné branche jsou z hlediska historie a další simulace rovnocenné. Označení, kterou z nich ukazuje Viewer, neznamená vyšší sportovní, simulační ani technickou důležitost.

**[PROZATÍMNÍ]** Počet branchí pravděpodobně nebude omezen.

**[ROZHODNUTO]** Názvy branchí musí být v rámci jednoho Runu jedinečné.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Počáteční branch se automaticky pojmenuje `Timeline 1`. Při vytvoření každé další běžné branche engine předvyplní první právě nepoužitý název řady `Timeline N` v daném Runu. Uživatel může tento návrh před vytvořením nahradit vlastním jedinečným názvem; pokud jej nenahradí, uloží se nabídnutý název. Přesná pravidla porovnávání velikosti písmen a pozdější UX přejmenování nejsou tímto rozhodnutím určena.

**[ROZHODNUTO]** Popis branche je volitelný.

## 7.2 Viewer Branch

**[ROZHODNUTO]** Každý Run musí mít neustále právě jednu `Viewer Branch`.

Při atomickém založení Runu se jeho jediná počáteční branch rovnou nastaví jako `Viewer Branch` a ukazuje na první `Saved Revision` podle kapitoly 3.3. Pozdější změna tohoto označení se řídí běžným Draft/Save workflow níže.

**[ROZHODNUTO]** `Viewer Branch` pouze určuje, kterou uloženou časovou linii daného Runu zobrazuje read-only Viewer. Není to `Official Branch`, vítězná větev ani větev s vyšší prioritou. Porovnávání, pokračování, archivní historie a ostatní Admin operace zůstávají dostupné pro všechny branche nezávisle na tomto označení.

**[ROZHODNUTO]** `Viewer Branch` nelze archivovat, dokud se pro Viewer nezvolí jiná aktivní branch. Technický ukazatel se označuje `viewer_branch_id`, nikoliv `official_branch_id`.

**[ROZHODNUTO]** Změna označení `Viewer Branch` je běžná neuložená Admin změna. Viewer se na novou branch přepne až po potvrzeném `Uložit` a vždy zobrazí pouze její poslední skutečně uložený a pro zobrazení platný stav; samotné rozpracované označení ani ostatní Working Draft data se do Vieweru nepropíší.

## 7.3 Vytvoření branche

**[ROZHODNUTO]** Branch lze vytvořit z kteréhokoliv uloženého bodu historie.

**[ROZHODNUTO][ENGINE INVARIANT]** Nová běžná branch vytvořená přímo z uložené `Saved Revision` sdílí neměnnou minulost až po tento zvolený bod, používá jej jako svůj počáteční uložený head a dostane vlastní čistý `Working Draft` založený právě na něm. Tento způsob vytvoření branche neduplikuje společnou minulost, nevytváří nový checkpoint ani automaticky nemění dosavadní `Viewer Branch`. Odlišná akce `Nová branch z Working Draftu` zachovává své rozpracované změny podle pravidla níže.

**[ROZHODNUTO]** Může vzniknout i uprostřed turnaje, například po konkrétním zápase.

**[ROZHODNUTO]** Checkpoint je pojmenovaná uživatelská záložka nebo automaticky technicky připravený bod obnovy. Není podmínkou pro návrat ani vytvoření branche: každý uložený platný bod historie lze otevřít, obnovit nebo použít jako počátek nové branche.

Mezi platné body patří podporované hranice uložených událostí, například stav před či po zápase, kole, turnaji, weeku, sezoně, importu nebo ruční změně. Engine může potřebný technický checkpoint vytvořit či stav z autoritativní historie zrekonstruovat na vyžádání. Návrat doprostřed právě počítané a neuložené události je možný pouze tehdy, pokud příslušná úroveň detailu její mezistav skutečně ukládá.

**[ROZHODNUTO]** Ruční pojmenovaný checkpoint lze vytvořit kdykoliv v podporovaném uloženém bodě. Automatické checkpointy nevznikají periodicky po každém zápase, weeku či sezoně jen kvůli kalendáři; každý úspěšný Save už vytváří obnovitelnou verzi.

**[ROZHODNUTO]** Automatický bezpečnostní checkpoint vznikne před rizikovou operací, která může nahradit nebo odstranit uloženou budoucnost či současný stav, například před obnovením starší verze, přegenerováním minulosti, tvrdým přelosováním nebo obnovením importované verze existujícího Runu.

**[ROZHODNUTO]** Akce `Nová branch z Working Draftu` převede právě rozpracované neuložené změny do nové branche. Původní branch zůstane na své poslední Saved Revision; nová branch začne ze stejného uloženého základu a ponese oddělený Working Draft, který se stane její historií až potvrzeným uložením.

**[ODLOŽENO]** Úplný konečný katalog operací vyžadujících automatický checkpoint a technický formát fork-safe bodů. Základní pravidlo „pouze před rizikovou operací, nikoliv periodicky“ je rozhodnuté.

## 7.4 Změna minulosti

**[ROZHODNUTO V PRINCIPU]** Při zásahu do už odehrané minulosti se před provedením zobrazí potvrzení s možnostmi:

1. vytvořit z daného bodu novou branch a zachovat původní budoucnost,
2. smazat budoucnost současné branche od tohoto bodu a přegenerovat ji,
3. akci zrušit.

Budoucnost se nesmí potichu tvářit jako stále platná.

**[ROZHODNUTO PRO TVRDÉ RUČNÍ ÚPRAVY LOSU]** Při ruční změně hráče v již odehraném zápase Admin nabídne dvě varianty:

1. vynulovat dotčené zápasy a odstranit nebo přegenerovat navazující budoucnost,
2. vědomě zachovat existující skóre, výhry, prohry a postup a převést je na nového hráče.

Při druhé variantě se změna hráče automaticky propíše do všech jeho následujících zápasů v daném turnaji a přepočítají se H2H, statistiky, rankingové dopady, prize money a další odvozená data.

Jde o mimořádný tvrdý Admin override. Dokud Admin vědomě nezvolí dovolený způsob řešení, zobrazí se červený kritický stav, seznam všech dopadů a silné doporučení přegenerovat budoucnost od změněného bodu. Vytvoření nové branche se vždy nabídne, ale není povinné; po výslovném potvrzení podporované strategie a úspěšné validaci výsledku lze dotčenou operaci dokončit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Při velké ruční změně atributu nabídne Admin vedle okamžité změny s odpovídajícím oranžovým varováním také `Dopočítat historický vývoj`. Engine vytvoří novou branch nebo přegeneruje současnou branch od zvoleného dřívějšího bodu a rozloží změnu do uvěřitelné vývojové cesty, která v cílovém weeku dosáhne požadované hodnoty.

Pre-alpha nabízí tři významové režimy:

1. `Přirozeně přegenerovat` – kauzálně navazující výsledky a historie se mohou změnit,
2. `Zachovat přesné výsledky` – celý potřebný soutěžní skelet a oficiální výsledková fakta zůstávají uzamčené,
3. `Zachovat podobnou historii` – engine chrání zvolená základní fakta a minimalizuje odchylky v povolených měkkých cílech.

V přesném režimu jsou tvrdými fakty minimálně přihlášky, účast a odhlášení, los a soupeři, vítěz, `RET / W/O / ABN`, celkové skóre, přesná skóre gamů, postup turnajem, body a z nich odvozené rankingy. Délka zápasu, odhad rally a úderů, Form, tři stamina bary, Fatigue, Health a další navazující stavy jsou cíle podobnosti: oficiální fakta mají absolutní prioritu, engine minimalizuje jejich souhrnnou odchylku a každou skutečnou odchylku vypíše.

Engine nabídne více kandidátních vývojových cest s různým počátečním weekem a průběhem, seřadí je podle realističnosti a zachování historie a dovolí Adminovi zadat pevný počáteční week nebo rozsah. Před potvrzením zobrazí proveditelnost, odhad realističnosti včetně dostupného `p / α`, počet vzorků či nejistotu a nejproblematičtější zápasy. Přesné vzorce a kalibrace zůstávají otevřené.

**[ROZHODNUTO][ENGINE INVARIANT]** Solver nesmí bez sportovní příčiny účelově kličkovat s atributy mezi zápasy. Přirozený růst, pokles nebo plateau jsou možné podle věku, tréninku, vytížení, zdraví a náhodnosti. Stejná vývojová ochrana platí pro běžnou simulaci i rekonstrukci: oranžová označí extrémně rychlý, ale ještě možný vývoj; červená znamená překročení absolutního limitu development modelu a změnu zablokuje i proti ručnímu vynucení. Přesná čísla jsou kalibrací.

**[ODLOŽENO DO DALŠÍCH VERZÍ]** Samostatné nastavitelné osy `rozsah regenerace × míra zachování`, jejich úplný katalog a výchozí kombinace. Toto odložení neruší výše rozhodnuté tři pre-alpha režimy.

## 7.5 Archivace branche

**[ROZHODNUTO]** Branch lze archivovat se zachováním její historie a checkpointů.

**[ROZHODNUTO]** Cokoliv archivované lze znovu obnovit do aktivního stavu.

**[ROZHODNUTO]** Aktivní důležitý objekt se nejdříve archivuje. Teprve z archivu jej lze trvale smazat po výslovném potvrzení.

## 7.6 Více alternativních simulací

**[ROZHODNUTO]** Z libovolného uloženého platného bodu historie lze spustit více alternativních simulací stejného výchozího stavu. Engine podle potřeby připraví technický checkpoint automaticky; uživatel jej nemusí mít předem pojmenovaný. Každá simulace používá jiný náhodný seed a vzniká jako samostatná `Candidate Branch` uvnitř téhož Runu; zdrojová branch zůstává beze změny.

**[ROZHODNUTO]** Uživatel zvolí počet kandidátů a engine před spuštěním odhadne čas a potřebné úložiště.

**[ROZHODNUTO]** Po dokončení se žádný kandidát automaticky nevybere ani nesmaže. U každého lze:

- zachovat jej jako běžnou branch,
- nastavit jej jako `Viewer Branch`,
- pokračovat v jeho simulaci,
- archivovat jej,
- odstranit jej.

**[ROZHODNUTO]** Dokončené Candidate Branches se nejdříve uchovávají v dočasném obnovitelném stavu odolném proti běžnému pádu nebo zavření aplikace. Nejsou tím automaticky publikované do Vieweru ani uložené jako běžná kanonická změna Runu. Běžnou branchí se stanou až po výslovném zachování a uložení.

Tato technická recovery vrstva je úzkou výjimkou z pravidla ručního ukládání: chrání výsledek náročného výpočtu, ale sama nenahrazuje uživatelské `Uložit`.

## 7.7 Obnovitelné verze po uložení

**[ROZHODNUTO]** Každé úspěšné stisknutí `Uložit` automaticky vytvoří obnovitelnou verzi dotčeného Runu a branchového stavu, i když šlo pouze o malou úpravu.

**[ROZHODNUTO]** Engine k verzi automaticky vytvoří stručný souhrn uložených změn. Uživatel může nepovinně přidat vlastní název nebo poznámku; jejich nevyplnění uložení neblokuje.

**[ROZHODNUTO]** Výběr starší uložené verze ji nejprve otevře pouze v read-only preview. Admin potom nabídne:

1. pouze ji prohlédnout,
2. vytvořit z ní novou branch,
3. po výrazném potvrzení jí obnovit současnou branch.

Samotné otevření verze nikdy nic nepřepíše.

**[ROZHODNUTO]** Před obnovením současné branche starší verzí engine automaticky vytvoří samostatný obnovitelný checkpoint jejího aktuálního stavu. Návrat ke starší verzi proto definitivně nezničí stav existující těsně před obnovením.

**[ROZHODNUTO V PRINCIPU]** Obnovitelné verze nemají vznikat jako úplné fyzické kopie celého Runu. Používají sdílenou minulost, rozdílové ukládání, deduplikaci a bezztrátovou kompresi podle kapitoly 25.3. Přesný datový algoritmus se zvolí a bude kalibrovat až podle skutečné velikosti a rychlosti fungujícího enginu.

## 7.8 Compare States

**[ROZHODNUTO V PRINCIPU]** Admin obsahuje nástroj `Compare States`, který dokáže porovnat libovolné dvě podporované branche, uložené verze nebo checkpointy a zobrazit pouze jejich rozdíly.

Porovnání může zahrnout zejména hráče, výsledky, rankingy, turnaje, nastavení a další změněné objekty.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Při porovnání stavů z různých weeků má Compare States nabídnout dva režimy:

- `Stejný week` – výchozí doporučené porovnání obou historií ve společném vybraném weeku,
- `Přesně vybrané body` – porovnání každého snapshotu v jeho skutečném weeku s výrazným označením časového rozdílu a oddělením změn způsobených pouhým uplynutím času od skutečné divergence branchí.

Tento dvourežimový model je silný směr, ale není ještě pevně rozhodnutý.

**[ODLOŽENO]** Přesné filtry, agregace, pravidla rozlišení časového vývoje od divergence a detailní podoba obrazovky.

## 7.9 Mapa branchí a Historie Runu

**[ROZHODNUTO V PRINCIPU][CÍLOVÁ FUNKCE]** Admin obsahuje centrální interaktivní obrazovku `Historie Runu`, která propojuje:

- mapu všech branchí se zobrazenými body jejich vzniku a označením právě zvolené `Viewer Branch`,
- detailní časovou osu právě vybrané branche.

Mapa ukazuje minimálně název branche, její vztah k ostatním větvím, bod odvětvení, aktuální dosažený week a relevantní stav. `Viewer Branch` dostane jasný Viewer badge, ale mapa ji nesmí vydávat za hodnotnější nebo sportovně významnější větev; topologie vychází ze skutečného původu a bodů divergence.

**[ROZHODNUTO]** Detail vybrané branche umožní procházet sezony, weeky, turnaje, kola, zápasy, simulace, importy, ruční změny a checkpointy. Kliknutí na uložený bod otevře jeho read-only náhled a podle kontextu nabídne porovnání, vytvoření nové branche nebo bezpečné obnovení současné branche.

**[ROZHODNUTO]** Celková mapa nesmí zobrazit všechny zápasy naráz. Používá úrovně přiblížení, sbalení a detail vybrané branche, aby zůstala čitelná i u dlouhého Runu s mnoha větvemi.

**[ODLOŽENO]** Přesný layout grafu, orientace, zoom, seskupování technických bodů, filtry, barevný systém a výkon u extrémně velkého počtu branchí.

## 7.10 Bez slučování rozdílných simulovaných historií

**[ROZHODNUTO][ENGINE INVARIANT]** Dvě branche, které po společném bodu vytvořily rozdílné simulované historie, nelze automaticky sloučit zpět do jedné historie. Výsledky, rankingy, stav hráčů, únava, zdraví a navazující události tvoří kauzálně odlišné časové linie a engine je nesmí smíchat.

Uživatel může branche porovnat, jednu zvolit jako `Viewer Branch` nebo z ní pokračovat. Vybrané kompatibilní nastavení či jednotlivou ruční změnu lze v principu přenést jako novou výslovnou operaci s preview a validací; nikdy tím však nevznikne automatický merge odehraných zápasů, statistik nebo simulované budoucnosti.

---

# 8. Ukládání a ochrana neuložené práce

## 8.1 Ruční ukládání

**[ROZHODNUTO]** Engine používá ruční tlačítko `Uložit`.

**[ROZHODNUTO][ENGINE INVARIANT]** Jedinou bootstrap výjimkou je vznik nového Runu podle kapitoly 3.3: jeho úspěšné vytvoření samo atomicky založí první `Saved Revision` a čistý `Working Draft`. Nejde o automatické ukládání pozdější práce; každá následná změna, editace nebo simulace zůstává v draftu až do výslovného `Uložit`.

**[ROZHODNUTO]** Ani dokončená simulace se automaticky neuloží. Výsledky simulace zůstávají neuloženými změnami, dokud uživatel nestiskne `Uložit`.

**[ROZHODNUTO]** Viewer vždy čte pouze poslední uložený stav. Neuložené změny ani neuložené výsledky simulace se ve Vieweru neprojeví.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Validní simulace smí vycházet také z neuloženého `Working Draftu` aktivní branche. Její výsledky zůstanou součástí téhož draftu a Viewer dál ukazuje poslední Saved Revision. Zahození draftu proto zahodí i všechny simulované následky, které z jeho neuložených vstupů vznikly.

**[ROZHODNUTO]** Uložení právě zvolené `Viewer Branch` automaticky aktualizuje Viewer bez samostatného tlačítka `Publikovat`. Také změna, která jinou branch označí jako `Viewer Branch`, začne pro Viewer platit až po potvrzeném Save podle kapitoly 7.2.

**[ROZHODNUTO V PRINCIPU]** Admin má trvale dostupné tlačítko `SAVE`. Bez změn je neaktivní; při existenci změn se aktivuje a zvýrazní. Kliknutí nejprve ukáže krátký srozumitelný diff, po potvrzení vytvoří Saved Revision a auditní událost. Přesný vizuální styl, umístění a frontendová animace se navrhnou později.

**[ROZHODNUTO]** Hlavní akce `Uložit` výchozím způsobem uloží všechny neuložené změny aktuální pracovní relace, které lze společně bezpečně zapsat.

**[ROZHODNUTO]** Pokročilá akce `Uložit vybrané změny` dovolí vybrat celé srozumitelné logické balíčky změn, nikoliv jednotlivé interní databázové řádky. Engine předem ukáže jejich obsah a dopad.

**[ROZHODNUTO]** Pokud vybraný balíček závisí na jiné neuložené změně, engine povinnou závislost automaticky přidá, nebo přesně vysvětlí, proč nelze skupiny bezpečně oddělit. Nevalidní částečné uložení nepovolí. Nevybrané změny zůstanou dál jako neuložený pracovní draft.

**[ROZHODNUTO][ENGINE INVARIANT]** Běžné `Uložit` je při jakékoliv červené validační chybě v zamýšleném ukládaném celku zablokované. `Uložit vybrané změny` však smí potvrdit nezávislé validní logické balíčky; nevalidní balíček a vše, co na něm závisí, zůstane neuložené. Červená chyba proto nesmí být obcházena, ale ani bezdůvodně zadržet prokazatelně nezávislou validní práci.

**[ROZHODNUTO]** Každé potvrzené úplné i částečné uložení je atomické, vytvoří jednu obnovitelnou verzi a odpovídající auditní událost pro skutečně uložený rozsah.

## 8.2 Varování při odchodu

**[ROZHODNUTO]** Pokud existují neuložené změny a uživatel se pokusí odejít, přepnout Run, změnit kontext nebo zavřít stránku, engine ho upozorní a nabídne například:

- uložit změny a pokračovat,
- odejít bez uložení,
- zůstat na stránce.

**[ROZHODNUTO]** Při pádu nebo nechtěném zavření aplikace se neuložené změny automaticky zachovají v odděleném dočasném `Recovery Draftu`. Recovery Draft není skutečné uložení Runu, nepřepisuje poslední uložený stav a nikdy se sám nepublikuje do Vieweru.

**[ROZHODNUTO]** Při dalším spuštění engine nabídne:

1. obnovit rozpracovanou práci jako neuložené změny,
2. nejprve ji otevřít v read-only náhledu,
3. recovery draft vědomě zahodit.

Samotná existence recovery dat nesmí změnit kanonický stav Runu. Viewer dál čte poslední skutečně uložený stav.

**[ODLOŽENO]** Přesná retence recovery draftů, jejich velikost, chování při více pádech nebo novější pracovní relaci a technické slučování s dočasnými Candidate Branches.

## 8.3 Undo potvrzených neuložených změn

**[ROZHODNUTO]** Potvrzená hromadná operace zůstává až do uložení jedním společným krokem v `Undo`. Například hromadnou úpravu několika Tournament Editions lze vrátit jedinou akcí; není nutné vracet každou dílčí změnu zvlášť.

**[ROZHODNUTO]** Admin podporuje běžnou více-krokovou historii `Undo/Redo` během aktuální pracovní relace. Slouží k vracení editací a operací v rozpracovaném stavu, nikoliv jako trvalá historie celého Runu.

**[ROZHODNUTO]** Po ukončení pracovní relace nebo po návratu ke staršímu uloženému stavu se negarantuje „nekonečné Ctrl+Z“. Dlouhodobé návraty, prohlížení starší historie a obnova používají uložené verze a checkpointy podle kapitoly 7.

**[ODLOŽENO]** Přesný počet a retence kroků v jedné relaci, klávesové zkratky, slučování rychlých editací a chování Undo/Redo při případném částečném uložení.

---

# 9. Generování hráčů

**Rozsah kapitoly:** engine musí umět hráče generovat, zveřejňovat v určeném weeku, zamykat, ručně vytvářet a regenerovat. Konkrétní věkové hranice, velikosti generací a pravidla vstupu na Tour jsou konfigurovatelná `Player Generation/Lifecycle Policy`; zde uvedené hodnoty jsou **Official Run defaulty**, pokud nejsou označeny jako čisté UI či datové chování.

## 9.1 Počáteční hráčský pool

**[ROZHODNUTO]** Před první sezonou musí vzniknout počáteční aktivní hráčský pool.

**[ROZHODNUTO]** Počáteční aktivní hráči mohou mít 15–45 let.

Při startu v roce 2000 to přibližně odpovídá ročníkům narození 1955–1985; tím se také vysvětluje začátek populačních dat v roce 1955.

**[ROZHODNUTO]** Není potřeba vytvářet již retired historické hráče z doby před rokem 2000.

**[ODLOŽENO]** Přesný způsob vytvoření počátečního rankingu, počátečních schopností, kariérní minulosti a rozložení hráčů je složitý a vyřeší se později.

## 9.2 Pravidelný příchod nových hráčů

**[ROZHODNUTO]** Každý nový hráč se objeví přesně v týdnu svých 15. narozenin.

**[ROZHODNUTO]** Nejprve existuje jako junior/prospect.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Prospect se formálně zaregistruje na MSA Tour a získá kariérní status `Tour Player` okamžikem prvního platného podání přihlášky do kteréhokoliv turnaje MSA Tour. Přijetí do Main Draw nebo kvalifikace není podmínkou: i když je hráč pod cutem nebo je přihláška později odmítnuta z kapacitního důvodu, status Tour Player mu zůstane.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** U wild card nastane vstup na Tour až definitivním přidělením platné WC do fieldu. Samostatná akce výslovného přijetí se nepoužívá: finální přidělení se považuje za implicitně přijaté, dokud hráč neodstoupí. Pouhá předběžná nabídka nebo vedení mezi WC rezervami vstup nespouští. Účast na juniorském mistrovství světa sama o sobě vstupem na MSA Tour není.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][OFFICIAL RUN DEFAULT]** Nový Tour Player vstupuje s nulou rankingových bodů a zpětně se nevkládá do již publikovaného současného Official MSA Ranking snapshotu. Do vytvoření následujícího Official snapshotu se zobrazuje jako `NR`. V následujícím snapshotu se objeví stejně jako všichni ostatní Tour Players, i kdyby stále měl 0 bodů.

Dokončený Ranked turnajový výsledek se stane autoritativním vstupem pro další rankingový výpočet. Hráči se však nevytváří žádný zvláštní mezikrok, ve kterém by „dostal body před rankingem“: jeho započitatelné body a pozice se materializují až v následujícím Official Ranking snapshotu, přesně stejně jako u všech ostatních hráčů.

Pokud Tournament Ranking Snapshot předchází jeho vstupu na Tour, je pro danou přihlášku `NR` a stojí pod všemi hráči, kteří v tomto snapshotu pozici mají. Více takových `NR` uchazečů se seřadí nejprve podle dřívějšího entry decision slotu a při vstupu ve stejném slotu stabilním reprodukovatelným tie-break tokenem uloženým pro daný turnaj; technické pořadí zpracování nesmí rozhodnout. Neúspěch pod cutem status Tour Playera neruší.

**[ROZHODNUTO]** Vstup může nastat v kterémkoliv weeku od 15 let. Kariérní status `Tour Player` nevylučuje, že je hráč podle věku současně stále juniorem.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Každý automaticky vygenerovaný prospect je zamýšlený budoucí hráč MSA Tour a dříve či později na Tour skutečně vstoupí. Nesmí zůstat po celou kariéru pouze nevyužitým vygenerovaným profilem. Toto pravidlo se vztahuje na automaticky generované prospecty; zvláštní ručně vytvořený hráč může mít Adminem zadanou odlišnou historii nebo stav.

**[ROZHODNUTO]** Pro první vstup na Tour neexistuje další pevná maximální věková hranice typu 25 let. Od 15. narozenin může nastat v kterémkoliv weeku; konkrétní okamžik určí hráčské rozhodování a okolnosti.

**[PROZATÍMNÍ SMĚR]** Hráčská AI má okamžik první přihlášky nebo získání wild card odvozovat zejména z aktuálních schopností, věku, osobnosti, ambicí, dostupných příležitostí, očekávané šance na přidělení a předchozího odkládání. S postupem času se má kumulativně zvyšovat tlak na vstup, aby vznikaly přirozené rozdíly mezi hráči, ale nikdo neodkládal vstup absurdně dlouho. První verze může použít jednoduchý model; pravděpodobnosti a inteligence se budou po rozběhnutí aplikace postupně zpřesňovat.

**[OTEVŘENO]** Přesný vzorec hráčské AI, váhy faktorů, minimální a typické věky, způsob kalibrace a volba prvního konkrétního turnaje. Formální trigger vstupu i pravidlo, že každý automaticky vygenerovaný prospect nakonec vstoupí, jsou již rozhodnuté a samostatná hráčská licence se nezavádí.

**[PROZATÍMNÍ]** Na začátku sezony se mohou technicky předgenerovat všichni hráči, kteří v ní dosáhnou 15 let, ale do aktivního světa vstoupí až ve svém `birth_year_week`. Definitivní implementace se ještě dohodne.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Samotné zpřístupnění hráče v jeho `birth_year_week` proběhne při otevření tohoto weeku v samostatném Week Transitionu podle kapitoly 6.5, ještě před jeho prvním Simulation Slotem. Případné technické předgenerování nesmí hráče prozradit ve starším Viewer čase.

**[ROZHODNUTO]** V Adminu je prospect viditelný od týdne svých 15. narozenin.

**[ROZHODNUTO]** Ve Vieweru je před vstupem na Tour viditelný v samostatné juniorské/prospect sekci, má vlastní omezený profil a lze ho najít globálním vyhledáváním.

**[ROZHODNUTO]** Do běžného seznamu profesionálních hráčů a Tour se dostane až při připojení k Tour. Po vstupu pokračuje stejný profil a nevytváří se nový hráčský profil.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Běžná juniorská zápasová historie se nesimuluje.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Juniorské mistrovství světa je součástí enginu a představuje výjimku z absence běžné juniorské zápasové historie.

**[PROZATÍMNÍ]** Juniorské mistrovství světa bude pravděpodobně jediným simulovaným juniorským turnajem. Celý juniorský okruh ani běžná juniorská kariéra se simulovat nebudou.

## 9.3 Ruční hráči, lock a regenerace

**[ROZHODNUTO]** Engine obsahuje `Locked Players`.

**[ROZHODNUTO]** Ručně vytvořený hráč je automaticky locked.

**[ROZHODNUTO]** Locked hráče lze ručně odemknout.

**[ROZHODNUTO]** Regenerace bude dostupná v mnoha rozsazích, například:

- jeden hráč,
- ročník narození,
- země,
- region,
- sezona/generace,
- celý odemčený hráčský pool.

**[CÍLOVÁ FUNKCE]** Před regenerací má existovat bezpečný preview/edit/lock workflow. Přesné UX se dořeší.

**[ROZHODNUTO V PRINCIPU]** Admin může kdykoliv během Runu ručně vytvořit hráče ve věku 15–45 let. Jeho minulost, ranking a přesný okamžik vstupu na Tour se dořeší později.

---

# 10. Hráčský profil a identita

**Rozsah kapitoly:** stabilní identita hráče, jedinečné ID, historicky správný profil a schopnost ukládat časově proměnlivé údaje jsou funkčnost enginu. Povinná či volitelná profilová pole, fyzické rozsahy, národnostní pravidla a jiné sportovní hodnoty mohou patřit k Player Policy konkrétního Runu; zde uvedený obsah popisuje současný Official Run základ, pokud není výslovně označen jako Engine invariant.

## 10.1 Identita

**[ROZHODNUTO]** Dva hráči mohou mít stejné jméno.

**[ROZHODNUTO]** Rozlišuje je jedinečné interní ID.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Simulačně validní hráčské jádro obsahuje:

- neměnné systémové `player_id`,
- `given_name` a `family_name`, ze kterých vzniká zobrazované jméno,
- `birth_year` a existující přesnost `birth_year_week`,
- stabilní `origin_country_id` jako původ hráčské populační pipeline, oddělený od sportovní reprezentace,
- neprázdnou časově verzovanou `Sporting Representation`,
- handedness,
- časově platnou výšku a hmotnost,
- lifecycle status a jeho effective week,
- původ vytvoření `Generated / Manual / Imported`,
- stabilní rankingový tie-break token,
- všech 57 aktivních atributů, Potential OVR, development type a všechny současné sportovní stavy, které potřebuje požadovaná simulace.

Přezdívka, fotografie a další mediální či profilové údaje povinné nejsou. Hometown zůstává v současné verzi výslovně vyloučené. Neúplného hráče lze uložit jako `Draft`; červeně zablokuje pouze operaci, která některý chybějící údaj skutečně potřebuje.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Běžně se zobrazuje jen jméno, například `Jan Novák`. Pokud v daném seznamu existuje stejné zobrazované jméno, oba profily se rozliší v tomto stabilním pořadí:

1. `Jan Novák · CZE · 2005`, tedy Sporting Representation a rok narození,
2. při shodě také `Jan Novák · CZE · 2005/W17`,
3. při další shodě krátkým stabilním veřejným diskriminátorem odvozeným z `player_id`.

Globální vyhledávání vždy ukáže Sporting Representation a rok narození. Admin může zobrazit celé `player_id`; Viewer jej běžně nepotřebuje. Profil, odkazy a trvalá URL vždy používají `player_id`, takže změna jména ani reprezentace nevytvoří nového hráče.

**[ROZHODNUTO]** Hráči mohou dostávat přezdívky.

**[ODLOŽENO]** Pravidla generování přezdívek a jejich zobrazování.

## 10.2 Základní fyzické údaje

**[ROZHODNUTO]** U hráče se ukládá handedness:

- pravák,
- levák,
- obouruký/ambidextrous.

**[ROZHODNUTO]** Hráč bude mít výšku a hmotnost.

**[ROZHODNUTO]** Výška i hmotnost jsou časově proměnlivé. Výška se mění především během juniorského růstu a dospívání; hmotnost se může měnit během celé kariéry.

**[OTEVŘENO]** Přesné růstové a hmotnostní křivky, intervaly změn, rozsahy a vazba na věk, vývoj, zdraví a trénink.

**[PROZATÍMNÍ]** Výška i hmotnost budou ovlivňovat schopnosti, herní styl a gameplan hráče, například dosah, sílu, stabilitu, pohyb, výdrž nebo únavu. Vyšší ani těžší hráč nemá být automaticky lepší; přesné výhody, nevýhody a matematické vazby se rozhodnou později.

**[ROZHODNUTO]** Viewer musí vždy ukázat fyzické údaje platné k právě vybranému týdnu, ne dnešní nebo budoucí hodnotu.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Hráč nebude mít uložené rodné město/hometown. Později se to může změnit.

**[ROZHODNUTO]** Viewer nabízí tři globální režimy zobrazení věku hráče:

- pouze celé roky, například `17 let`,
- roky a weeky od posledních narozenin, například `17 let, 28 weeků`,
- desetinný věk, například `17,459 let`.

Výchozí režim je pouze celý věk. Zvolený režim se ukládá jako globální zobrazovací preference a používá se konzistentně všude, kde Viewer věk zobrazuje.

**[ROZHODNUTO]** Desetinný věk se počítá jako celé roky plus počet weeků od posledních narozenin dělený 61. Zobrazuje pouze tolik desetinných míst, kolik je potřeba, nejvýše však tři; zbytečné koncové nuly se nezobrazují a hodnota se zaokrouhluje na nejbližší tisícinu.

## 10.3 Původ, Sporting Representation a zařazení do Tour

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Biografický či generační původ hráče a jeho veřejná sportovní reprezentace jsou dvě oddělené veličiny. `origin_country_id` zůstává stabilní provenance populační pipeline. `Sporting Representation` je neprázdná, časově verzovaná sportovní identita platná od konkrétního effective weeku a má právě jeden z těchto typů:

| Typ | Kód a zobrazení | Význam |
|---|---|---|
| `Country` | kód a vlajka skutečné země, například `CZE` | standardní reprezentace existující Country entity |
| `World` | `WRL` a symbol zeměkoule | dobrovolná globální sportovní identita bez reprezentace konkrétní země |
| `FAX Neutral` | `NTL` a neutrální znak FAX | dočasný regulátorem uložený nebo schválený neutrální status |

`World` není země a nesmí získat populaci, území, Country Model, národní federaci ani `country_id`. `FAX Neutral` rovněž není země. Chybějící nebo `Unknown` hodnota není ani World, ani Neutral a u simulačně potřebného hráče zůstává validační chybou.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][OFFICIAL RUN DEFAULT]** `World` je dobrovolná identita hráče, který se sportovně hlásí k celému světu, nikoliv vynucená neutralita. Uložený důvod používá nejméně taxonomii `Personal Global Identity / No National Affiliation / Stateless or Displaced / No Recognised Federation`. Ručně vytvořený hráč může s World začít. Hráčská AI o něj může velmi vzácně požádat; přesná pravděpodobnost a kalibrace zůstávají otevřené. Zahájení vždy schválí FAX a určí effective week.

Pokud hráč nikdy nenastoupil v závazné oficiální národní reprezentaci, může World začít ve schváleném effective weeku. Pokud už za zemi závazně nastoupil, musí před účinností uplynout zbývající část standardní 122weekové lhůty od posledního takového startu. Přechod `Country ↔ World` se počítá jako jedna běžná dobrovolná změna Sporting Representation a neslouží k obcházení limitu změn.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][OFFICIAL RUN DEFAULT]** `FAX Neutral` používá FAX při suspendaci národní federace, sankčním či integritním opatření nebo jiné výslovně odůvodněné regulační situaci. Není osobní volbou, nesmí se zaměňovat s World a nespotřebuje hráčovu běžnou dobrovolnou změnu. Po ukončení statusu se obnoví předchozí stále platná Country či World reprezentace, není-li současně schválena jiná účinná změna.

Hráči s World i FAX Neutral mohou normálně nastupovat na individuální MSA Tour a mají stejné rankingy, body, prize money, tituly a osobní rekordy jako ostatní. Nemohou být nominováni do národního týmu a nevzniká z nich automatický světový tým. Případný budoucí `World Select` by byl pouze samostatná exhibice, nikoliv země nebo účastník Team World Championship.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Každý start a výsledek uloží snapshot Sporting Representation platný v daném okamžiku. Pozdější změna nikdy nepřepíše staré vlajky, symboly, výsledky ani statistiky. Výsledky pod World se nezapočtou žádné zemi a mohou se agregovat pod World; původová analytika je může současně přiřadit k `origin_country_id`. Hráč tedy může například pocházet z anglické pipeline, ale sportovně reprezentovat World.

**[ROZHODNUTO][ENGINE INVARIANT]** Engine umožňuje, aby hráč v průběhu kariéry změnil reprezentovanou zemi a aby se tato změna ukládala historicky.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Změna reprezentované země je velmi výjimečná událost.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Zbývající detaily dobrovolné změny `Country ↔ Country` používají model „historická pravda + aktuální profil“:

- změna nabývá účinnosti od konkrétního weeku dopředu a hráč si po celou kariéru zachovává stejné `player_id`,
- každý turnajový start a výsledek uchovává Sporting Representation platnou v daném weeku; staré výsledky, losy a jejich vlajky či symboly se po pozdější změně zpětně nepřepisují,
- Viewer v historicky vybraném weeku ukazuje Sporting Representation platnou právě tehdy; v nejnovějším bodu profilu ukazuje současnou reprezentaci a profil zpřístupní její historii,
- individuální zápasy, tituly, rekordy a ostatní kariérní statistiky zůstávají součástí jedné souvislé kariéry hráče; mohou se zobrazit celkem i rozděleně podle Sporting Representation platné v době jejich získání,
- platné rankingové body se při změně země nevynulují a pokračují se stejným hráčem; historické rankingové snapshoty se zpětně nemění,
- reprezentační starty, tituly a medaile zůstávají připsané zemi, za kterou byly skutečně získány,
- pokud se vytváří historická statistika individuálních výsledků podle zemí, započítá se pouze tehdejší reprezentace typu Country; World se vede odděleně a FAX Neutral se nesmí připsat dnešní ani původové zemi hráče.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Pro běžnou dobrovolnou změnu musí mít hráč občanství nové země a současně splnit alespoň jednu skutečnou vazbu: narodil se v ní, narodil se v ní alespoň jeden z jeho rodičů, nebo v ní hráč reálně žil nejméně pět let. Samotná lepší šance dostat se do reprezentace nové země nestačí. Mimořádná nesportovní situace, například uprchlictví nebo zánik státu, může založit zvláštní eligibility posouzenou FAX; sama o sobě ale neznamená automatické prominutí čekací lhůty.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Hráč smí během kariéry provést jednu běžnou dobrovolnou změnu reprezentované země. Druhá změna je možná pouze jako mimořádné individuální rozhodnutí FAX nebo vědomý ruční Admin override.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Engine nyní nebude do hloubky simulovat stěhování, rodiče, pobytovou historii ani pasové řízení. Velmi vzácně vytvoří abstraktní událost získání eligibility či občanství a uloží minimálně její důvod a week. Bohatší model migrace a životní historie lze doplnit v budoucnu.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Standardní čekací lhůta pro změnu reprezentované země je dva fiktivní roky, tedy přesně `122 weeků`. Počítá se od posledního weeku, ve kterém hráč skutečně nastoupil za starou zemi v závazné oficiální reprezentační soutěži nebo mezistátním utkání. Pouhá vlajka u jména v běžném individuálním turnaji MSA Tour se za takovou reprezentaci nepovažuje.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Během čekací lhůty:

- hráč nemusí přijmout nominaci ani nastupovat za starou zemi,
- může normálně pokračovat ve všech individuálních turnajích MSA Tour a až do účinnosti změny se u něj používá dosavadní reprezentovaná země a její vlajka,
- za novou zemi ještě nesmí nastoupit v závazné oficiální reprezentační soutěži,
- pokud znovu nastoupí za starou zemi v závazné oficiální reprezentaci, rozhodný poslední reprezentační week se posune na tento start a celá lhůta `122 weeků` začne znovu od něj.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Změna nenabude účinnosti automaticky. U každého konkrétního hráče ji musí výslovně schválit hlavní světová squashová organizace FAX. I po splnění časové lhůty zůstává do schválení a stanoveného effective weeku platná stará reprezentovaná země.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Hráč může podat žádost kdykoliv poté, co získá eligibility, tedy i během běžící 122weekové lhůty. FAX ji může podmíněně schválit předem a určit budoucí effective week. Čekací lhůta se vždy počítá od poslední závazné reprezentace, nikoliv od podání žádosti. Pokud už při schválení uplynula celá lhůta, může změna s výslovným souhlasem FAX nabýt účinnosti okamžitě.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Simulace má změnu země vytvářet jako extrémně výjimečný vícestupňový jev. Velmi nízké pravděpodobnosti mají především určit, zda oprávněný hráč vůbec začne o změně uvažovat a zda podá žádost. Rozhodnutí FAX se má opírat o splnění pravidel a konkrétní důvody; nemá jít o náhodný hod, který bez vysvětlení schválí nebo zamítne jinak totožný případ.

**[OTEVŘENO]** Přesné doklady a ověřování Country eligibility, číselné pravděpodobnosti a jejich kalibrace včetně extrémně vzácné AI žádosti o World, případné juniorské výjimky, přesná taxonomie dalších mimořádných nesportovních případů, úplný automatický a ruční workflow, důvody zamítnutí, podmínky případné druhé dobrovolné změny a detailní Admin UX. U změny `Country ↔ Country` výslovně zůstává otevřeno, zda a za jakých okolností smí FAX zkrátit nebo prominout standardní 122weekovou lhůtu.

**[ROZHODNUTO]** `MSA Tour` je společný zastřešující profesionální okruh. World Tour, Elite Tour, Challenger Tour a Development Tour jsou jeho součásti, nikoliv vzájemně se vylučující kariérní kategorie hráčů. Hráč není trvale přiřazen k jedné Tour a může nastupovat napříč nimi podle pravidel konkrétních turnajů.

## 10.4 Fotografie a média

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Hráči nemají fotografie ani AI avatary.

Mohou přijít později, až bude AI umět dlouhodobě vytvářet opravdu konzistentní podobu stejného hráče.

---

# 11. Schopnosti, potenciál, vývoj a hráčská AI

**Rozsah kapitoly:** engine musí podporovat skryté schopnosti, vývoj, formu, únavu, zdravotní stav, styl, gameplan a hráčské rozhodování. Jednotlivé vrstvy nesmějí být sloučeny do jediného OVR. Pro pre-alpha je rozhodnutý aktivní katalog 57 atributů a jejich škála `0–200`; konkrétní váhy, vzorce, rychlost vývoje, pravděpodobnosti, AI chování a budoucí změny taxonomie zůstávají verzovanou simulační politikou. První verze může být jednoduchá, dlouhodobým cílem je extrémně podrobný model.

**[ROZHODNUTO V PRINCIPU]** Každý hráč funguje jako individuální AI a může se ve stejné vnější situaci rozhodovat jinak podle vlastních charakteristik, stavu, informací a historie. Neexistuje jedna všem hráčům společná mechanická osobnost. První funkční verze může používat podstatně jednodušší rozdíly; konkrétní inteligence, chování a pravděpodobnosti se budou systematicky kalibrovat až nad fungující simulací.

## 11.1 Interní schopnosti a skutečný stav

**[ROZHODNUTO]** Každý hráč má v každém časovém bodě své aktuální schopnosti. Match Engine používá skutečné aktuální hodnoty, nikoliv pouze jméno, ranking nebo jedno souhrnné číslo.

**[ROZHODNUTO]** Aktuální schopnosti, aktuální forma, únava a zdravotní stav jsou odlišné vrstvy. Postupně se k nim mohou přidávat další krátkodobé i dlouhodobé stavy. Jedna vrstva nesmí skrytě přepisovat význam jiné.

**[ROZHODNUTO][ENGINE INVARIANT]** Tentýž hráč může mít od bodu divergence v různých branchích rozdílné atributy a další časově proměnlivé stavy, aniž by se změnila jeho trvalá identita `player_id`. Ruční změna v jedné branchi nesmí automaticky změnit stejný week v jiné branchi.

**[ROZHODNUTO]** Admin nabízí pro ruční zásah do podporovaného atributu dvě významově odlišné akce:

- `Nastavit od tohoto weeku` – od zvoleného bodu nastaví novou hodnotu, ze které potom dál pokračuje běžný development a ostatní simulované vlivy,
- `Uzamknout hodnotu` – drží konkrétní atribut na výslovně nastavené hodnotě, dokud uživatel tento field-level lock znovu neodemkne.

Změna přepočítá všechny odvozené hodnoty včetně OVR podle právě platného modelu, nese původ `Manual` a při zásahu do již simulované minulosti používá obecný branch/regeneration workflow. Field-level zámek atributu je odlišný od celkového statusu `Locked Player` z kapitoly 9.3.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Každý aktivní atribut používá interní číselnou škálu `0–200`. Jde o škálu jednotlivých schopností, nikoliv o převod na potenciálové labely `L+–F−`.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Aktivní atributový katalog používá šest organizačních kategorií a celkem 57 jednotlivých atributů:

- `Technical` — Forehand, Backhand, Volley, Drop Shot, Lob, Boast, Precision, Variability, Power, Control,
- `Move` — Footwork, Range, Positioning, Efficiency, Balance, Explosiveness, Hustle, Court Dominance, Blocking,
- `Tactics` — Anticipation, Shot Selection, Pace, Adaptability, Analysis, Offense, Defense, Listening, Vision,
- `Mental` — Focus, Composure, Consistency, Patience, Aggressiveness, Confidence, Self Control, Discipline, Motivation, Toughness,
- `Physical` — Speed, Stamina, Endurance, Strength, Flexibility, Reflexes, Coordination, Agility, Durability,
- `Creativity` — Improvisation, Risk Taking, Unpredictability, Flair, Winner, Deception, Trick shots, Racket skill, Spin, Touch.

Každý z těchto 57 atributů je samostatně uložená aktuální hodnota hráče. Match Engine z nich v konkrétní situaci používá pouze relevantní podmnožinu; například `Drop Shot` nevytváří konstantní bonus v rally, ve které pro něj nevznikla odpovídající sportovní situace.

Tento katalog je rozhodnutým funkčním základem pre-alpha, ale není definitivní taxonomií budoucího enginu. V dalších verzích se má výrazně testovat, rozšiřovat, slučovat nebo zpřesňovat společně se styly a gameplany.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Kategorie jsou pouze organizační skupiny pro obrazovku a práci s daty. Samy nevytvářejí další souhrnný atribut ani jednotný vstup Match Enginu; simulace používá jednotlivé relevantní atributy a samostatné aktuální stavy.

**[ROZHODNUTO][ENGINE INVARIANT]** Každý historický zápas musí zachovat identitu a verzi atributového i simulačního modelu, který jej vytvořil. Pozdější vylepšení katalogu nebo vah nesmí potichu přepsat jeho uložený průběh či význam tehdejších hodnot.

**[OTEVŘENO]** Konečný katalog po pre-alpha, případné budoucí změny škály, definitivní názvy a seskupení, vzájemné vazby, přesné kontextové váhy, frekvence jednotlivých aktualizací a migrace mezi budoucími verzemi katalogu. Tyto otevřené detaily nemění rozhodnutý pre-alpha základ `57 samostatných hodnot na škále 0–200`.

## 11.2 Potenciál

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Zobrazovaná škála skutečného potenciálu používá v sestupném pořadí základní třídy:

`L, S, A, B, C, D, E, F`

Každá třída má vždy tři varianty `+`, bez znaménka a `−`. Úplné pořadí tedy začíná `L+`, `L`, `L−`, pokračuje `S+`, `S`, `S−` a stejným způsobem končí `F+`, `F`, `F−`.

**[ROZHODNUTO]** Skutečný potenciál je ve výchozím Viewer režimu skrytý.

**[ROZHODNUTO V PRINCIPU]** Potenciál není záruka jediného předem určeného vrcholu ani přesného budoucího OVR. Vymezuje talentové předpoklady a možnosti vývoje, které se mohou naplnit různě podle kariéry, zdraví, příležitostí, tréninku, osobnosti a dalších budoucích vlivů.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Skutečný potenciál se hráči přidělí při jeho vytvoření a běžná simulace jej během kariéry nemění. Příležitosti, zdraví, trénink a průběh kariéry určují, nakolik se potenciál naplní, nikoliv zpětně to, jaký talent hráč při vzniku dostal. Vědomý ruční Admin zásah do minulosti zůstává možný přes obecný branch/regeneration workflow.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Každý hráč má jeden skrytý celkový `Potential OVR`. První verze nepoužívá samostatné pevné potenciálové stropy pro každý atribut. `Potential OVR` je měkký dlouhodobý orientační strop vývoje, nikoliv očekávaný ani zaručený vrchol.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT PRO PRVNÍ VERZI]** Orientační převod potenciálového labelu na skrytý `Potential OVR` je:

| Potenciál | Potential OVR | Potenciál | Potential OVR | Potenciál | Potential OVR |
|---|---:|---|---:|---|---:|
| `L+` | 194 | `L` | 193 | `L−` | 192 |
| `S+` | 191 | `S` | 190 | `S−` | 189 |
| `A+` | 188 | `A` | 187 | `A−` | 186 |
| `B+` | 185 | `B` | 184 | `B−` | 183 |
| `C+` | 182 | `C` | 181 | `C−` | 180 |
| `D+` | 179 | `D` | 178 | `D−` | 177 |
| `E+` | 176 | `E` | 175 | `E−` | 174 |
| `F+` | 173 | `F` | 172 | `F−` | 171 |

Tato číselná mapa je prozatímní, protože byla potvrzena jako orientační první odhad. Labely `L+–F−`, existence jednoho celkového měkkého Potential OVR a jeho význam jsou naproti tomu rozhodnuté.

**[ROZHODNUTO V PRINCIPU]** Hráč může svůj `Potential OVR` překročit, ale pouze velmi výjimečně a se strmě klesající pravděpodobností dalšího růstu nad něj. Vedle toho nevzniká samostatný tvrdý limit typu `potential + 2`; jediným absolutním stropem současné OVR škály je `200`.

**[CÍLOVÁ FUNKCE]** Reveal režimy mohou ukázat OVR, atributy a skutečný potenciál podle zvolené úrovně zobrazení.

**[ODLOŽENO]** Přesná matematická křivka růstu v okolí a nad `Potential OVR`, četnost výjimečného překročení, distribuce labelů, skrytá granularita uvnitř stejného labelu a pokročilý vliv potenciálu na jednotlivé atributy. První verze bude jednodušší; pozdější verze mohou systém výrazně prohloubit bez změny základního pořadí labelů.

## 11.3 OVR

**[ROZHODNUTO]** OVR je odvozené celkové přepočítání hráčových aktuálních schopností. Není samostatnou schopností a není přímým vstupem, který by sám určoval vítěze zápasu.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** OVR používá rozsah `0–200` a vzniká jako normalizovaný vážený průměr právě platných atributů. Do samotného Match Enginu nadále vstupují relevantní atributy a aktuální stavy, nikoliv výsledné OVR.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** První funkční výpočet může používat jeden společný verzovaný profil vah pro všechny hráče. Dlouhodobým rozhodnutým cílem jsou individuální váhové profily podle predispozic, herního stylu a role jednotlivých schopností v hráčově hře; dva hráči se stejnými atributy potom nemusí mít naprosto stejné OVR, pokud jejich hra stojí na jiných přednostech.

**[ROZHODNUTO][ENGINE INVARIANT]** U historicky uloženého OVR musí být dohledatelné, z jakého stavu a jaké verze hodnoticího modelu vzniklo. Pozdější vylepšení OVR algoritmu nesmí potichu přepsat dříve zobrazenou historickou hodnotu; vědomý zpětný přepočet používá workflow změny minulosti.

**[ODLOŽENO]** Konkrétní první váhy, přesný normalizační vzorec, pozdější rozsah individualizace, zobrazované zaokrouhlení a vztah OVR k různým rolím a stylům. Model se bude zpřesňovat v dalších verzích enginu.

## 11.4 Vývoj během kariéry a historický stav

**[ROZHODNUTO PRO PRVNÍ VERZI]** Schopnosti hráčů se vyhodnotí a případně změní jednou za week v `Weekly Player Development Update` během Week Transitionu podle kapitoly 6.5. Výpočet smí použít hráčův stav a historii známé nejpozději do konce právě skončeného weeku, nikdy však informace z nově otevíraného nebo budoucího weeku. Nové hodnoty platí od otevření následujícího weeku. Každý atribut se nemusí při každém vyhodnocení skutečně změnit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Development za dokončený week používá konečnou Form tohoto weeku ještě před jejím meziweekovým návratem k normálu. Teprve po developmentu proběhne `Between-Week State Update` s Form regression, případným Match Sharpness decay, Fatigue recovery a hojením; přesné pořadí je v kapitole 6.5.

**[ROZHODNUTO]** Engine neukládá jeden povinný pevný `peak_week`, ke kterému by se celá kariéra mechanicky blížila. Kariéra může mít více lokálních vrcholů, plateau, návrat po poklesu i nevyužitý potenciál; skutečný průběh vzniká dynamicky.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Každý hráč při vytvoření dostane právě jeden typ načasování vývoje: `Early Bloomer`, `Standard` nebo `Late Bloomer`. Typ je nezávislý na potenciálu, určuje především časování růstu a poklesu a běžná simulace jej během kariéry nemění. Early Bloomer proto nemusí mít vyšší potenciál než Late Bloomer; pouze typicky rozvíjí a ztrácí schopnosti dříve.

**[ROZHODNUTO PRO ZJEDNODUŠENOU PRVNÍ VERZI]** Všechny tři typy vycházejí ze společné základní věkové křivky, kterou Early Bloomer posune přibližně o tři roky dříve a Late Bloomer přibližně o tři roky později. Nejde o pevný skutečný week osobního maxima ani rankingového vrcholu.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT PRO PRVNÍ VERZI]** První odhad generování a věkového středu je:

| Typ | Pravděpodobnost při vytvoření | Orientační střed věkového peaku | Orientační prime pásmo |
|---|---:|---:|---:|
| `Early Bloomer` | 16 % | 26 let | 24–28 let |
| `Standard` | 68 % | 29 let | 27–31 let |
| `Late Bloomer` | 16 % | 32 let | 30–34 let |

Tyto hodnoty jsou kalibračním prvním odhadem, nikoliv definitivní distribucí. Globální konkurence ve FAX světě může ovlivnit kariérní příležitosti a ranking, ale sama mechanicky neposouvá biologickou věkovou křivku každého hráče.

**[ROZHODNUTO V PRINCIPU]** Věk nepůsobí na všechny schopnosti stejně. Fyzické schopnosti mohou začít klesat dříve, zatímco technické, taktické a mentální schopnosti se mohou ještě později zlepšovat nebo držet. Přesné přiřazení atributů a samostatné křivky zůstávají kalibrací dalších verzí.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Experience` není atribut, OVR ani omezený bar. Je to z kariérní historie odvozený profil se dvěma složkami:

- `General Experience` vzniká ze všech skutečně odehraných soutěžních zápasů,
- `High-Pressure Experience` vzniká zejména z významných kol, finále, rozhodujících stavů a dalších tlakových situací.

Obě složky jsou celoživotně kumulativní, nemají pevné maximum a běžnou simulací neklesají; jejich další přínos však používá klesající mezní efekt. Hráč se stovkami menších zápasů proto může mít vyšší General Experience, ale nižší High-Pressure Experience než hráč s menším počtem zápasů a mnoha světovými finále.

**[ROZHODNUTO][ENGINE INVARIANT]** Časově proměnlivé hráčské hodnoty se ukládají historicky. Při otevření starého weeku Viewer i Admin pracují se stavem platným tehdy — včetně schopností, formy, únavy, zdraví, výšky, hmotnosti, stylu a dalších podporovaných vrstev — nikoliv s dnešní hodnotou ani s tichým přepočtem podle nejnovějšího modelu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Velkou ruční změnu atributu lze vedle okamžité změny od zvoleného weeku převést na historicky dopočítanou vývojovou cestu podle kapitoly 7.4. Běžný development i tento solver sdílejí stejnou oranžovou hranici extrémního, ale možného vývoje a červený nepřekročitelný absolutní limit; solver nesmí vytvářet nevysvětlené účelové oscilace jen kvůli zachování výsledků.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Explosive Stamina`, `Rally Stamina` a `Match Stamina` nejsou tři samostatně authorované dlouhodobé schopnosti vedle hráčových atributů. Jsou to dynamické zápasové fyzické rozměry odvozené z podkladových atributů a aktuálního stavu podle kapitoly 11.5. Tímto novější rozhodnutí nahrazuje starší formulaci o jejich samostatné trénovatelnosti.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Minimální obecný týdenní trénink používá jedinou agregovanou volbu `General Training Load` se čtyřmi úrovněmi `Recovery / Light / Normal / Heavy`. General Training, `Opponent Study` a `Match-specific Court Training` čerpají ze společné omezené týdenní kapacity; Opponent Study z ní spotřebovává hlavně čas a soustředění, zatímco oba fyzické druhy tréninku vytvářejí zátěž. Vyšší obecný load může zvýšit development, ale zhoršit recovery a zvýšit Fatigue i riziko přetížení či zranění. Hráčská AI volí load podle vlastního nedokonalého odhadu zdraví a únavy, zápasového vytížení, kalendáře a důležitosti nejbližších soutěží; Admin jej může pro konkrétní week vědomě přepsat. Stejný minimální choice uzavírá `PAQ-051` i `PAQ-115`.

**[ODLOŽENO]** Detailní tréninkový systém se vyřeší až tehdy, kdy bude naprogramovaná podstatně větší část enginu. Úplný denní či jednotkový plán, detailní rozdělení focusu mezi atributy, pokročilá automatická periodizace, burnout a hluboký Admin editor se nyní nepovažují za uzavřený kontrakt první verze. Přesné číselné development, fatigue, recovery a injury účinky čtyř úrovní zůstávají kalibrací.

**[OTEVŘENO]** Přesný development model, růst, plateau, pokles, návraty, výchozí křivky jednotlivých skupin atributů, vliv potenciálu, Experience, tréninku, zápasového vytížení, zdraví, osobnosti a náhody. Otevřené zůstávají také přesné váhy a klasifikace high-pressure událostí, matematika klesajícího přínosu Experience a její konkrétní účinky. Trénink má rozvíjet podkladové atributy; přesné mapování jejich změn do tří fyzických barů, krátkodobé zátěže a recovery i to, zda bude některý bar mít samostatný tréninkový cíl, rozhodnuté není.

## 11.5 Forma, Match Sharpness, únava, zdraví a rozhodnutí nastoupit

**[ROZHODNUTO]** Aktuální forma existuje odděleně od dlouhodobých schopností. Stejně tak okamžitý stav stamina, dlouhodobá fatigue/únava a zdraví nejsou pouhou součástí OVR; Match Engine je vyhodnocuje jako samostatné aktuální vstupy.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každý hráč má jednu společnou aktuální `Form`, nikoliv samostatnou formu podle Tour, kategorie, soutěže nebo soupeře. Kontext konkrétního zápasu zohledňují matchup, tlak, gameplan a ostatní samostatné systémy.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Form` se aktualizuje po každém skutečně odehraném zápase a nový stav ovlivní už případný další zápas ve stejném turnaji. Změnu určuje kvalita skutečného výkonu vzhledem k soupeři a očekávání, nikoliv pouze výhra či prohra: výborná těsná prohra může formu zlepšit a slabá výhra nad výrazně horším soupeřem ji může zhoršit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Při každém Week Transitionu se forma postupně vrací k hráčovu individuálnímu dlouhodobému normálu, pokud ji další výkony nepotvrzují. Nikdy se skokově neresetuje; přesný normál, rychlost návratu a výpočet výkonu zůstávají otevřené.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Forma ovlivňuje krátkodobé využití existujících schopností, například přesnost, načasování, provedení a konzistenci. Nepřepisuje dlouhodobé atributy ani z nich odvozenou fyzickou kapacitu. První verze zároveň nepoužívá samostatný atribut nebo bonus `Match Momentum`; zdánlivé momentum vzniká ze skóre, tlaku, stamina, formy, gameplanu a průběžné adaptace.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Match Engine zná skutečnou aktuální formu. Hráčská AI svou vlastní formu pouze odhaduje z posledních výkonů a soupeřovu formu odhaduje ještě méně přesně z výsledků, pozorování a dalších oprávněně dostupných informací; nemá přístup ke skrytému přesnému číslu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Zvláštní výsledkové statusy mění formu takto:

- `W/O` nebo `DQ` před začátkem neposkytuje žádný zápasový výkon a formu nemění,
- u `RET` nebo `DQ` po začátku se hodnotí pouze skutečně odehraný výkon; samotné odstoupení ani disciplinární důvod nepřidávají automatický sportovní postih do formy,
- síla změny u nedokončeného zápasu odpovídá množství skutečně odehraných dat,
- u dočasně `Suspended` zápasu se přepočet odloží do obnovení nebo definitivního ukončení; po dohrání či terminálním `ABN / No Contest` se skutečně odehraný výkon započítá právě jednou s vahou podle množství dat.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Match Sharpness` je samostatný dynamický bar `0–100 %`, který vyjadřuje obecnou soutěžní rozehranost. Není součástí atributů ani OVR a nesmí se zaměnit za Form, Fatigue nebo Health. Příklad: zdravý a plně odpočatý hráč po osmitýdenní pauze může mít dobrou dlouhodobou kvalitu, ale nízký Match Sharpness.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Match Sharpness se po každém skutečně odehraném soutěžním zápase zvýší podle jeho délky a intenzity a za každý week bez soutěžního zápasu postupně klesá. Nikdy se automaticky neresetuje. Dlouhý zápas `3:2` proto může rozehranost zvýšit více než velmi krátký zápas `3:0`, zatímco delší absence ji postupně snižuje.

**[ROZHODNUTO]** Vyšší Match Sharpness je vždy výhodnější než nižší. Negativní důsledky přetížení se nezdvojují obrácením Sharpness křivky, ale řeší je Fatigue, tři stamina systémy, recovery a Health/Injury State. Hráč proto může být současně velmi rozehraný a příliš unavený.

**[POZDĚJI, POTVRZENÝ SMĚR PRO VERZI 3+]** Nízká rozehranost se má nejsilněji projevit na začátku zápasu a její bezprostřední vliv se může v průběhu odehraných gamů částečně zmenšovat. Uložený kariérní Match Sharpness se přesto autoritativně přepočítá až po zápase. Přesný intra-match průběh a konkrétní ovlivněné výkonnostní složky nejsou požadavkem první pre-alpha.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Zápas používá dva dynamické mentální bary `Current Focus` a `Current Confidence`. Oba se aktualizují po každé rally, ale `Current Focus` reaguje rychleji rally od rally, zatímco `Current Confidence` se mění pomaleji podle průběhu gamu a zápasu.

Na začátku každého zápasu se oba mentální bary nově odvodí z tehdy aktuálního hráčova stavu a podkladových atributů. Jejich konečné číselné hodnoty z předchozího zápasu se přímo nepřenášejí; historické zkušenosti nebo události je mohou ovlivnit pouze prostřednictvím podporovaných dlouhodobějších stavů. `Current Focus` a `Current Confidence` se nesmějí zaměnit za dlouhodobé atributy `Focus` a `Confidence` z pracovního katalogu kapitoly 11.1.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Před zápasem může existovat skrytá `Match-Day Baseline`, která vyjadřuje lepší či horší den hráče. Výsledná `Match Performance` by přesto vznikala až z konkrétních rally, soupeře, atributů, formy, fyzického a zdravotního stavu a rozhodování. Tento vstup není rozhodnutou podmínkou první verze.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Fyzický stav zápasu zobrazují tři navzájem odlišné dynamické bary:

- `Explosive Stamina` – krátké explozivní pohyby, první krok, dosažení míče a opakování intenzivních výpadů,
- `Rally Stamina` – udržení vysoké intenzity a kvality během náročné rally,
- `Match Stamina` – aerobní základ, dlouhodobá výdrž, recovery mezi rally a kumulativní odolnost v průběhu zápasu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Kapacita, aktuální naplnění a recovery každého baru se odvozují z individuální kombinace podkladových atributů — například Stamina, Endurance a Explosiveness — a z právě platného fyzického stavu. Bary zůstávají oddělené, mají vlastní průběh čerpání a recovery a nesmějí se nahradit jedinou průměrnou energií. Recovery není čtvrtou stamina; je to proces závislý zejména na Match Stamina, vlastnostech daného systému, skutečném čase odpočinku a ostatním fyzickém stavu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Fatigue` je dlouhodobější stav mezi zápasy, který ovlivňuje dostupné výchozí hodnoty tří fyzických barů. Není čtvrtým barem uvnitř zápasu. `Health / Injury State` je další samostatná zdravotní vrstva a rovněž není stamina.

**[ROZHODNUTO][ENGINE INVARIANT]** Aktuální fyzická energie i dlouhodobá únava jsou kontinuální časové stavy. Přenášejí se mezi zápasy téhož turnaje, mezi různými turnaji i přes hranice weeků a nesmějí se automaticky vynulovat začátkem nového zápasu, turnaje nebo weeku. Při nástupu se tři bary znovu vyjádří podle právě platných atributů, nesené fyzické rezervy, fatigue, zdraví, předchozích zápasů, recovery času a cestování; toto odvození není reset.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Stavy všech tří stamina systémů se přepočítají po každé rally, nikoliv až po skončení setu. Krátká recovery používá skutečně uplynulý čas mezi rally; během klidnější části živé rally může Explosive Stamina nepatrně obnovovat rezervu, zatímco Match Stamina se během aktivní hry prakticky neobnovuje. Přesný model vzniku a délky běžné mezery mezi rally zůstává otevřený.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Fyzická zátěž je individuální a asymetrická. Krátká explozivní rally může jednoho hráče zatížit více než delší klidná rally a hráč pod tlakem může vydat výrazně více energie než soupeř kontrolující T. Match Engine proto počítá zatížení každého hráče odděleně v každém abstraktním úseku rally.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Dopad vyčerpání je spojitý a nelineární, nikoliv sada tvrdých prahů. Vysoká rezerva způsobuje malý nebo žádný postih, střední stav postupné zhoršování a nízký stav prudší propad; nulová hodnota sama o sobě neznamená automatickou prohru. Nízká Explosive Stamina zhoršuje zejména start, dosah a návrat na T, nízká Rally Stamina udržení intenzity a přesnosti a nízká Match Stamina recovery a kumulativní pokles.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Minimální zdravotní model rozlišuje dva základní typy záznamu:

- `Injury` – zranění s konkrétně zasaženou oblastí a profilem omezení,
- `Illness` – nemoc s celkovým nebo jinak typově odvozeným profilem dopadu.

Podrobná taxonomie diagnóz se přidá později. Jeden hráč může mít současně více samostatných zdravotních záznamů; každý se vyvíjí a léčí odděleně a nesmí být sloučen do jediného univerzálního Health baru.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Každý zdravotní záznam má `Severity 0–100`, kde `0` znamená vyléčený stav a `100` krajní závažnost, a samostatný typově odvozený profil omezení. Stejná Severity proto nesnižuje všechny schopnosti stejně: například kotník může zasáhnout hlavně movement a energetickou náročnost, zatímco nemoc zejména stamina, recovery a Focus.

Souběžné účinky se kombinují podle zasažených domén s klesajícím dodatečným dopadem a bezpečným maximem, nikoliv prostým součtem procent. Přesný skládací vzorec zůstává kalibrací.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Zdravotní záznam používá lifecycle `At Risk → Active → Recovering → Recovered`:

- `At Risk` je latentní přetížení, varovný signál nebo raný příznak, nikoliv ještě aktivní Injury/Illness,
- `Active` právě trvá nebo se může zhoršovat,
- `Recovering` se postupně léčí, ale může stále omezovat,
- `Recovered` má nulovou Severity a bez dalšího účinku zůstává v historii.

Pokud se včas odhalený signál po omezení zátěže upraví dříve, než vznikne aktivní problém, je povolen také přímý přechod `At Risk → Recovered`; engine kvůli tomu nevymýšlí mezilehlou aktivní Injury/Illness. Opakování nebo návrat problému se historicky zaznamená a původní zdravotní stopa se nemaže.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Doba zotavení je nejisté odhadované rozmezí, nikoliv garantované budoucí datum. Skutečný průběh Severity se simuluje postupně a podle odpočinku, zátěže, léčby a náhody může skončit dříve, později nebo se zhoršit. Hráčská AI ani Viewer proto neznají jistý budoucí termín uzdravení.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Hráči mají oddělené individuální predispozice k Injury a Illness, případnou náchylnost ke konkrétním typům nebo oblastem a vlastní rychlosti zotavení z obou druhů stavů. Tyto vrozené či dlouhodobé predispozice jsou samostatné od malého finančního modifikátoru z kapitoly 19.2.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Jeden kontextový `Health Check` vyhodnocuje vznik, aktivaci a zhoršení zdravotních stavů podle skutečného kontextu a uplynulé zátěže:

- na hranici Simulation Slotu zachytí běžné události mezi soutěžními událostmi,
- při abstraktním týdenním tréninku zohlední jeho load,
- během rally zachytí akutní zápasové zranění nebo zhoršení.

Základní riziko se škáluje podle uplynulého času a skutečné zátěže, aby se jedna náchylnost nezapočítala jako tři nezávislé plné pravděpodobnosti. Injury může vzniknout v zápase, při týdenním tréninku i mezi sloty; Illness může mezi sloty vzniknout nebo se zhoršit. Přesné pravděpodobnosti zůstávají kalibrací.

**[ROZHODNUTO V PRINCIPU]** Hráč může nastoupit s lehčím nebo zvládnutelným zraněním či nemocí. Stav ovlivní výkon, gameplan, výdrž, riziko zhoršení a možnost pozdějšího `RET`; rozhodnutí nastoupit může záviset na důležitosti zápasu, osobnosti hráče a dalších okolnostech.

**[ROZHODNUTO]** Pokud je hráč před zápasem objektivně neschopen nastoupit, vznikne `W/O`. FAX, turnajový lékař nebo jiná oprávněná autorita může v krajním případě start zdravotně nezpůsobilého hráče nepovolit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Rally-context Health Check se provede po každé rally a zjištěný stav se projeví před další rally. Nejde o další nezávislé plné riziko, ale o zápasový kontext jednotného systému výše.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Zdravotní vyhodnocení během rozehraného zápasu podporuje tři základní výsledky: `pokračovat / zdravotní přestávka / RET`. Po zdravotní přestávce se zdravotní stav a účinek ošetření znovu vyhodnotí a teprve potom hráčská AI rozhodne mezi pokračováním a `RET`.

**[PROZATÍMNÍ, SILNÝ SMĚR]** První verze používá jednu obecnou zdravotní přestávku bez detailního rozlišení původu a zavinění zranění. Stejný základ `pokračovat / zdravotní přestávka / RET` se pracovně použije také při náhlém zhoršení nemoci během zápasu.

**[ROZHODNUTO PRO PRVNÍ VERZI][OFFICIAL RUN DEFAULT]** Maximální délka zdravotní přestávky je ve výchozím Official Runu tři minuty a jde o konfigurovatelnou hodnotu pravidel soutěže, nikoliv globální konstantu enginu. Po skutečně uplynulou dobu získávají oba hráči svou běžnou individuální stamina recovery. Ošetřovaný hráč nedostává automatický bonus ke stamina recovery; ošetření působí na samostatný `Injury State`. Přesný zdravotní účinek ošetření zůstává otevřený a dlouhodobé zranění se přestávkou automaticky nevyléčí.

**[ROZHODNUTO PRO PRVNÍ VERZI][OFFICIAL RUN DEFAULT]** Nominální přestávka mezi gamy/sety je ve výchozím Official Runu dvě minuty a je konfigurovatelným pravidlem zápasu. Všechny tři stamina se po skutečně uplynulou dobu pouze průběžně obnovují podle individuální recovery a nikdy se neresetují; stejně tak se automaticky neresetuje zranění ani dlouhodobá fatigue.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Skutečná přestávka mezi gamy nemusí vždy trvat přesně nominálních 120 sekund, protože se může odvíjet od reálné připravenosti a objektivních událostí. Taktické tempo mezi běžnými rally už patří do pre-alpha podle kapitoly 17.8.3; otevřené zde zůstává konkrétní chování při vypršení nominální mezihrové přestávky a detailní pravidlové vynucování zdržování mezi gamy.

**[ROZHODNUTO PRO SOUČASNÝ ROZSAH]** Za samotné rozhodnutí nastoupit zraněný či nemocný se v enginu neřeší žádný automatický disciplinární postih, ani když se stav později zveřejní. Simulují se sportovní a zdravotní následky. Podvod, úmyslné nevynaložení nejlepšího úsilí, porušení bezpečnostního protokolu nebo sázková manipulace patří do případného budoucího disciplinárního systému, nikoliv do základního zdravotního modelu.

**[ROZHODNUTO]** Admin pracuje se skutečným interním zdravotním stavem hráče. Viewer smí zobrazit pouze zdravotní informaci, která je k vybranému historickému weeku veřejně známá, oficiálně oznámená nebo oprávněně odhadovaná z veřejných signálů. Skryté lehčí zranění či nemoc se proto ve Vieweru nemusí objevit vůbec; veřejný odhad nesmí být vydáván za interní jistotu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Ani hráčská AI nemá přímý přístup k interní zdravotní pravdě enginu. Rozhoduje podle vlastního nedokonalého vnímání typu, Severity a rizika; může stav přehlédnout nebo jej podcenit. Abstraktní hráčovo zázemí může stav `At Risk` odhalit, ale odhalení není garantované a vyšší Financial Level pouze mírně zvyšuje jeho pravděpodobnost a přesnost odhadu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Odhalený `At Risk` automaticky nevynutí odpočinek. AI zvažuje vnímanou závažnost, osobnost, význam nadcházející soutěže a kalendář a může snížit trénink, změnit přípravu nebo vědomě riskovat. Preventivní snížení loadu zmenšuje riziko aktivace problému a podporuje recovery, ale současně snižuje týdenní development a Match Preparation. „Tým“ zde zůstává pouze abstraktní součástí hráčova zázemí, nikoliv samostatnou entitou.

**[POZDĚJŠÍ POKROČILÁ VERZE]** Detailní squashové kategorie zdravotních přestávek, rozlišení původu či zavinění zranění, počty přestávek, podrobná léčba a další okrajová zdravotní pravidla. První verze zachovává pouze výše uvedený zjednodušený základ.

**[ODLOŽENO]** Podrobná taxonomie diagnóz, přesné profily omezení, pravděpodobnosti a křivky Health Checku, skládání více stavů, detekce, léčba, healing a rozhodovací prahy pro start/RET/W/O; nakažlivost; číselné vzorce tří fyzických i dvou mentálních barů, mapování atributů, čerpání a recovery; dlouhodobá fatigue; vstupy a kalibrace počátečního odvození; a podrobný travel model nad základem kapitoly 5.5. Rozhodnuté typy Injury/Illness, škála Severity, lifecycle, souběh, nejisté rozmezí zotavení, individuální predispozice, jednotný kontextový Health Check a hranice interní pravdy už otevřené nejsou. U formy zůstávají otevřené číselná škála, individuální dlouhodobý normál, očekávací model, váha množství odehraných dat a rychlost návratu při Week Transitionu. U Match Sharpness zůstávají otevřené inicializace, konkrétní přírůstky podle zápasu, týdenní decay, vliv match-specific tréninku a přesná výkonnostní křivka.

## 11.6 Herní styl, gameplan, znalost soupeře a Match Preparation

**[ROZHODNUTO]** Herní styl hráče se může během kariéry vyvíjet. Není navždy uzamčený při generování hráče.

**[ROZHODNUTO]** Hráč a jeho AI mohou měnit gameplan také během konkrétního zápasu. Pokus o adaptaci nemusí být správný ani úspěšný; závisí na schopnostech, inteligenci, dostupných informacích, fyzickém stavu a průběhu zápasu.

**[ROZHODNUTO]** Match Engine zná skutečný interní stav obou hráčů. Samotný hráč ani jeho rozhodovací AI však soupeřův skutečný stav automaticky neznají. Vytvářejí si odhad ze scoutingu, veřejných výsledků, H2H, předchozích pozorování, aktuálně dostupných signálů a dalších oprávněných informací.

**[ROZHODNUTO]** Odhad soupeře obsahuje nejistotu a může být chybný. Gameplan proto vychází z toho, co si hráč rozumně myslí, nikoliv z vševědoucího přístupu ke skrytým atributům Match Enginu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Hráčská AI vnímá vlastní únavu poměrně dobře, ale ne jako přesné interní číslo. Soupeřovu únavu pouze odhaduje z pohybu, chyb, průběhu rally, známých predispozic a ostatních dostupných signálů; tento odhad může být opožděný nebo chybný.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Před každou rally AI volí základní míru úsilí, pracovně `conserve / normal / increased / maximum`, a během skrytých změn kontroly a tlaku ji může změnit. Může šetřit síly, zvýšit úsilí při šanci získat převahu, stabilizovat se, riskovat rychlé ukončení, přestat plýtvat energií na téměř nedosažitelný míč nebo reagovat na domnělou únavu soupeře. Rozhodnutí může být nesprávné a ani správné rozhodnutí se nemusí fyzicky podařit provést.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Aktivní herní styl a gameplan používají čtyři souběžné osy `Risk / Tempo / Court Positioning / Variation`. Každý hráč má dlouhodobě se vyvíjející `Natural Style Profile` a pro různé kombinace stylu vlastní odlišnou `Style Familiarity`; ne každý tedy umí stejně dobře provést každý přípustný plán. Skutečná `Style Execution` v rally vzniká z právě relevantních atributů z katalogu 57 schopností, Style Familiarity, Adaptability, Match Preparation a aktuálních fyzických i mentálních stavů. AI se může podle nedokonalého odhadu soupeře pokoušet jeho hru counterovat, ale counter není povinný: může vědomě zůstat u vlastní silné hry, zachovat plán s očekávaným pozdějším efektem nebo u nefunkčního plánu setrvat kvůli nízké adaptabilitě, chybné interpretaci či tvrdohlavosti. Gameplan proto uchovává zamýšlený mechanismus, časový horizont, confidence a reassessment threshold a během zápasu se může po dosažení prahu přehodnotit; krátkodobě špatný výsledek sám o sobě automaticky neznamená změnu.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Match Preparation` je samostatný dočasný stav navázaný na konkrétní plánovaný zápas nebo přípravu na nejbližší zápas. Zobrazuje se jedním výsledným barem `0–100 %`, ale engine odděleně uchovává, kolik přípravy vzniklo ze dvou zdrojů:

- `Opponent Study` – sledování zápasů, statistik, návyků a dostupných informací o soupeři,
- `Match-specific Court Training` – praktický nácvik konkrétní taktiky, situací a provedení na kurtu.

**[ROZHODNUTO]** Oba zdroje používají jiné náklady. Opponent Study spotřebovává čas a soustředění, ale vytváří jen zanedbatelnou přímou fyzickou únavu. Match-specific Court Training spotřebovává část běžné tréninkové kapacity, vytváří fyzickou zátěž a může přidat malé riziko přetížení či zranění. Match Preparation proto není bezplatný bonus nad běžný týden.

**[ROZHODNUTO]** Stejná doba přípravy nemá u všech hráčů stejný efekt. Přínos závisí na relevantních schopnostech, například `Analysis`, `Focus`, `Adaptability`, `Shot Selection` nebo schopnosti prakticky provést připravený plán. Výborné studium může odhalit správnou taktiku, ale hráči automaticky nedá elitní úder, který neumí.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Není-li soupeř známý, hráč může zvolit obecnou přípravu na nadcházející zápas, nebo cílit na jednoho pravděpodobného soupeře a přijmout riziko, že postoupí někdo jiný. První verze nepotřebuje současnou optimalizaci samostatných příprav na mnoho možných soupeřů.

**[ROZHODNUTO]** Aktuální Match Preparation se po cílovém zápase uzavře. Předchozí vzájemné zápasy, studium a získaná zkušenost však zůstávají v autoritativní historii a mohou zjednodušeně usnadnit budoucí přípravu na stejného soupeře; nevzniká tím navždy platný bonus původního baru.

**[ROZHODNUTO]** Příprava má dva významově oddělené následky:

- okamžitě zlepšuje kontextové využití existujících schopností a gameplanu v cílovém zápase,
- vytváří malý dlouhodobý rozvojový příspěvek pro relevantní atributy, který se zpracuje běžným Weekly Player Development Update.

Nevzniká okamžitý dočasný skok základního atributu. Příklad: dvě hodiny studia mohou okamžitě zvýšit připravenost proti konkrétnímu soupeři a opakovaně v čase přispět k růstu `Analysis`, ale nezmění před jedním zápasem atribut skokově ze 112 na 120.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Hráčská AI nemá přístup k Admin `Absolute Forecastu`, k miliardám virtuálních budoucností ani k jejich skutečným pravděpodobnostem. Vlastní rozhodnutí musí odhadovat z omezených informací, scoutingu, osobnosti, inteligence, zkušeností a vnímaného rizika. Forecast může později sloužit Adminovi k nezávislé analýze kvality rozhodnutí AI, nikdy však jako její skrytá vševědoucí pomůcka.

**[ODLOŽENO]** Přesný scouting model, dostupnost a kvalita záznamů, paměť hráčů, váhy obou zdrojů Match Preparation, její inicializace a decay, přesné náklady, vztah k Match Sharpness, výpočet usnadnění opakované přípravy, abstraktní analytika, číselná tvorba a změna gameplanu, rozhodovací matematika míry úsilí, rychlost adaptace a pravděpodobnost správného odhadu. Samostatné entity trenérů a podpůrných týmů jsou rozhodnutě vyloučené v kapitole 1.4. Pre-alpha už musí používat výše rozhodnuté čtyři stylové osy, familiarity, counterování a možnost vědomého či chybného setrvání; jemnější taktické projevy, podrobné shot patterns a jejich kalibrace patří do dalších verzí.

---

# 12. Věk, stárnutí a retirement

**Rozsah kapitoly:** stárnutí, stavy `Inactive`/`retired`, automatický i dobrovolný retirement a comeback jsou schopnosti enginu. Konkrétní věková hranice 46 let, návratová pravidla a jejich pravděpodobnosti jsou **Official Run defaulty** v `Player Lifecycle Policy`; jiný Run je může nastavit jinak.

## 12.1 Stárnutí

**[ROZHODNUTO]** Hráč zestárne ve svém `birth_year_week`, nikoliv hromadně na konci sezony.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Změna věku se provede při Week Transitionu, který daný `birth_year_week` otevře, a nový věk proto platí už pro všechny jeho první sloty.

## 12.2 Automatický retirement

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Jakmile hráč v `birth_year_week` dosáhne věku 46 let, automaticky ukončí kariéru.

To znamená, že maximální běžný aktivní věk je 45 let. Takový případ má být velmi vzácný.

Pravidlo lze někdy později změnit, ale nyní je platné.

## 12.3 Návrat z retirementu

**[ROZHODNUTO]** Hráč, který skončil dříve než ve 46 letech, se může vrátit.

**[ROZHODNUTO]** Takový návrat může výjimečně vytvořit samotná simulace a zároveň jej může Admin provést ručně.

**[ROZHODNUTO]** Po automatickém retirementu ve 46 letech už návrat není možný.

**[ROZHODNUTO]** Dobrovolně retired hráč v aktuálním oficiálním rankingu není, ale jeho jednotlivé turnajové výsledky se nemažou. Během retirementu dál normálně stárnou a propadají podle své původní platnosti.

**[ROZHODNUTO]** Při comebacku se do skutečného rankingu znovu započítají všechny jeho výsledky, které jsou v daném weeku stále platné a vejdou se do aktuálního Best N. Výsledky, jejichž platnost už skončila, se nikdy neobnovují.

**[ODLOŽENO]** Přesné načasování comebacku uvnitř weeku, jeho vztah k již otevřeným přihláškám a jeho AI pravděpodobnost.

## 12.4 Inactive stav a dobrovolný retirement

**[ROZHODNUTO]** `Inactive` a `retired` jsou dva odlišné stavy. Hráč může dočasně opustit Tour a později se vrátit bez ukončení kariéry.

**[ROZHODNUTO]** Hráč, který už vstoupil na Tour, zůstává v MSA rankingu i jako `Inactive` a po poklesu na 0 bodů, dokud oficiálně neukončí kariéru.

**[ROZHODNUTO]** `Inactive` nevzniká automaticky jen proto, že hráč určitý počet weeků neodehrál zápas nebo turnaj. Musí jít o skutečné rozhodnutí hráče/jeho AI dočasně Tour opustit, případně o výslovnou ruční změnu v Adminu.

**[ROZHODNUTO]** Dlouhá doba bez zápasu je pouze historický údaj a může být ve Vieweru či Adminu vizuálně zvýrazněna. Sama o sobě nemění lifecycle status hráče.

**[ROZHODNUTO]** `Inactive` hráč se stává znovu `Active` okamžikem první platné přihlášky do turnaje MSA Tour nebo definitivního přidělení platné wild card do fieldu. Samostatné výslovné přijetí WC se nevyžaduje. U běžné přihlášky není podmínkou, aby se následně vešel přes cut do Main Draw či kvalifikace; rozhodující je platný návrat do entry procesu.

**[ROZHODNUTO V PRINCIPU]** Hráč může dobrovolně ukončit kariéru v kterémkoliv weeku; nejčastěji to pravděpodobně bude po sezoně.

**[PROZATÍMNÍ SMĚR]** Dobrovolný retirement nemá vznikat pouze jedním věkovým procentem nebo izolovaným náhodným hodem. Hráčská AI má průběžně vytvářet individuální ochotu pokračovat podle kombinace věku a zdraví, současné výkonnosti a trendu, rozdílu mezi ambicemi a výsledky, motivace a osobnosti, očekávané budoucnosti, dlouhé neaktivity, zranění, významných neúspěchů, úspěchů, návratu formy a blízkosti důležitého cíle. Rozhodnutí zůstává částečně pravděpodobnostní a při stejném výchozím stavu může v různých branchích dopadnout jinak. Hlavní vyhodnocení se očekává zejména po sezoně, mimořádná událost jej však může vyvolat v libovolném weeku.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Při kariérní krizi může AI porovnat pokračování jako `Active`, dočasný přechod do `Inactive` a dobrovolný retirement. `Inactive` by měl být přirozenější při dočasném zranění, vyhoření, osobní pauze nebo přechodné ztrátě motivace; retirement při dlouhodobém přesvědčení, že pokračování nebo dosažení podstatných cílů nedává smysl. Jde pouze o slabý směr, nikoliv uzavřený rozhodovací algoritmus.

**[ODLOŽENO]** Přesné AI chování hráčů, důvody neaktivity, retirementu a comebacku, jejich pravděpodobnosti, kalibrace a konkrétní přechody mezi stavy. Tyto detaily se mají dolaďovat až nad alespoň první funkční verzí enginu.

## 12.5 Bez hráčských licencí

**[ROZHODNUTO]** Squash Engine nebude obsahovat systém hráčských licencí. Způsobilost hráče pro Tour, turnaje a ranking se určuje přímo podle jeho lifecycle stavu, vstupu na Tour, věku, případných trestů a dalších konkrétních pravidel. Při comebacku se žádná licence nezískává ani neobnovuje.

---

# 13. Turnaje, identity a kalendář

**Rozsah kapitoly:** `Tournament Series`, `Tournament Edition`, historická identita, kalendářový editor a víceweekové fáze jsou funkčnost enginu. Konkrétní kalendář, týdny, fáze a soutěže každého Runu jsou jeho konfigurací.

## 13.1 Trvalá identita turnaje

**[ROZHODNUTO]** Opakující se turnaj si mezi sezonami zachovává stejnou interní identitu a společnou historii prostřednictvím objektu `Tournament Series` a jeho trvalého `series_id`.

**[ROZHODNUTO]** Turnaj může změnit název a přesto zůstat stejným historickým turnajem.

**[ROZHODNUTO]** Turnaj může změnit kategorii a přesto zůstat stejným historickým turnajem.

**[ROZHODNUTO]** Změna názvu, kategorie, hostitelského města či země, weeku, formátu nebo jiného sezonního parametru sama o sobě nevytváří nový historický turnaj. O pokračování společné historie rozhoduje přiřazení ke stejnému `series_id`, nikoliv shoda názvu nebo ostatních vlastností.

**[ROZHODNUTO][ENGINE INVARIANT]** Tournament Series nemá vlastní přímou vazbu na Tour. Každá Edition používá kategorii platnou pro svůj konkrétní sezonní výskyt a z ní se odvodí tehdejší Tour a Competition System. Series si proto zachová identitu i tehdy, když mezi sezonami změní kategorii, Tour nebo se celý Competition System reorganizuje; starší Editions zůstávají pod tehdy platnou hierarchií.

**[ROZHODNUTO]** Každý konkrétně uložený plánovaný výskyt Tournament Series používá objekt `Edition Plan` se stabilním `edition_plan_id`. Před materializací jej může nahrazovat virtuální Inherited Plan adresovaný deterministickým klíčem `series_id + season_id + occurrence_key`; ten vlastní uložené ID ještě nemá. Plán lze před vznikem Edition měnit, přesunout nebo zrušit; sám ještě není odehranou Tournament Edition.

**[ROZHODNUTO]** Zhmotněná Tournament Edition dostane vlastní odlišné `edition_id` a zachová odkaz na původní `edition_plan_id` jako provenance. `edition_plan_id` a `edition_id` tedy nejsou dvě jména stejného identifikátoru.

**[ROZHODNUTO][ENGINE INVARIANT]** Z jednoho Edition Planu může vzniknout nejvýše jedna Tournament Edition. Má-li tatáž Series ve stejné sezoně více uskutečnění, každé používá vlastní `edition_plan_id` a vlastní `edition_id`. Postponement pouze mění termín téhož plánu a Edition; nevytváří druhé uskutečnění.

**[ROZHODNUTO]** Každé konkrétní uskutečnění turnaje v kalendáři je samostatná `Tournament Edition`. Uživatel ji běžně vnímá pouze jako daný ročník turnaje; technicky obsahuje zejména:

- jedinečné `edition_id`,
- odkaz na zdrojový `edition_plan_id`, pokud Edition vznikla z plánu,
- odkaz na `series_id`,
- přiřazenou sezonu přes `season_id`,
- Qualification Weeks a Main Draw Weeks,
- provisional pořadí před startem a od první skutečné rally uzamčené oficiální `edition_number`,
- rankingový status `Ranked / Unranked`, původ jeho výchozího nastavení či override a u Ranked Edition provenance efektivní bodové tabulky její kategorie a sezony,
- případnou úplnou, částečnou nebo chybějící prize-money konfiguraci,
- všechny parametry platné pouze pro tento konkrétní ročník.

Rok ani označení sezony není nutné zadávat podruhé ručně, protože je Edition získá ze svého umístění v sezonním kalendáři.

**[ROZHODNUTO]** `edition_number` říká, kolikátý ročník dané Tournament Series se skutečně uskutečnil. Engine jej generuje automaticky. Před startem smí UI ukazovat jen zřetelně `provisional edition number`; oficiální číslo se přidělí a uzamkne teprve při zahájení prvního skutečně odehraného zápasu celé Edition, podle reálného pořadí startu. Plánovaný termín ani dřívější announcement sám číslo nezamyká.

**[ROZHODNUTO]** Má-li jedna Series více Editions v téže sezoně, každá používá vlastní `edition_plan_id` a `edition_id` a aktivní termíny se v první pre-alpha nesmějí překrývat. Zrušení, W/O, DQ před zápasem ani technický postup bez skutečně zahájeného zápasu číslo nespotřebují. Jakmile však první rally skutečně začne, číslo zůstane navždy uzamčené i při pozdějším `RET`, `DQ`, `Suspended` nebo `Abandoned`.

**[ROZHODNUTO]** Předstartovní odklad může způsobit, že jiná Edition stejné Series začne dříve a získá nižší číslo; odložená Edition zachová identitu, ale její provisional pořadí se smí změnit. Po startu už odklad pokračování používá `Suspended` a uzamčené číslo se nemění. Admin může historické číslo opravit pouze výslovnou auditovanou akcí; výsledná hodnota musí být kladná a unikátní mezi započítanými Editions Series. Pozdní import historických dat vytvoří viditelný konflikt k ručnímu vyřešení, nikdy tiché automatické přečíslování.

**[ROZHODNUTO]** Každá Tournament Edition zobrazuje a uchovává název, který turnaj skutečně používal v dané sezoně. Souhrnná stránka Tournament Series může pracovat se současným názvem, ale její historické ročníky se zpětně nepřejmenovávají.

**[ROZHODNUTO]** Globální vyhledávání umí Tournament Series najít podle současného i historických názvů. Vždy však otevře tutéž společnou historii identifikovanou přes `series_id`.

## 13.2 Přerušení, návrat a zrušení

**[ROZHODNUTO]** Turnaj může jednu nebo více sezon vynechat a později se vrátit se stejnou identitou.

**[ROZHODNUTO]** Naplánovaný turnaj může být ve fiktivním světě zrušen například kvůli válce, epidemii, katastrofě, bezpečnosti, financím nebo rozhodnutí pořadatelů.

**[ROZHODNUTO]** Zrušení zůstane v historii spolu s důvodem.

**[ROZHODNUTO]** Vynechaná sezona ani zrušený turnaj, ve kterém nezačal žádný zápas, nezvýší `edition_number`.

**[ROZHODNUTO]** Jakmile začne alespoň jeden zápas turnaje, daná Tournament Edition se už započítá do pořadí ročníků. To platí i tehdy, když je turnaj následně nedokončen nebo formálně `Abandoned`; v historii zůstane například jako `75. ročník – nedokončeno`.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Hlavní mimořádný stav se určí jednoduchou maticí podle toho, zda už skutečně začal alespoň jeden zápas a zda má Edition později pokračovat:

| Skutečný stav | Má pokračovat | Definitivně nepokračuje |
|---|---|---|
| žádný zápas nezačal | `Postponed` | `Cancelled` |
| alespoň jeden zápas začal | `Suspended` | `Abandoned` |

Terminální `Completed / Cancelled / Abandoned` se v současné historii znovu neotevírají; oprava minulosti používá branch/historical workflow.

### Cancelled před zahájením

**[ROZHODNUTO PRO PRVNÍ VERZI]** Je-li Tournament Edition definitivně zrušena před prvním skutečně zahájeným zápasem kvalifikace nebo Main Draw, získá historický stav `Cancelled` a důvod zůstane uložený. Nevzniknou žádné rankingové body, prize money ani titul.

Všechny její přihlášky, závazky a Week Tournament Locky se uvolní bez disciplinární sankce. Tato nově vzniklá dostupnost však neobchází deadline, freeze ani replacement pravidla jiného turnaje: hráč do něj smí vstoupit jen tehdy, pokud jej jeho normální entry nebo replacement workflow ještě dovoluje.

### Postponed

**[ROZHODNUTO PRO PRVNÍ VERZI]** Odložený turnaj zůstává toutéž Tournament Edition se stejným `edition_id` a společnou historií. Pokud už má podle pravidel výše uzamčené oficiální `edition_number`, zachová je; před prvním skutečným zápasem má jen provisional číslo, které se může změnit podle pozdějšího reálného pořadí zahájení. Změna weeků a schedule se uloží jako časově verzovaná změna a nevytváří nový ročník.

Dosavadní přihlášky se automaticky nemažou, ale kvůli novému termínu a možným konfliktům smí všichni hráči své rozhodnutí znovu přehodnotit nebo bez sankce odstoupit.

FAX/Admin při odkladu výslovně zvolí jeden ze dvou režimů a před potvrzením uvidí dopad:

1. `Preserve Field & Draw` — pro kratší či jinak stabilní odklad se zachová původní field, los a Tournament Ranking Snapshot; odhlášení se řeší běžným replacement workflow.
2. `Reopen Entry Process` — při zásadní změně se zruší ještě neodehraná budoucí podoba losu, nastaví nové entry deadlines, vytvoří nový Tournament Ranking Snapshot a turnaj se znovu vylosuje; identita Edition zůstává stejná.

**[ROZHODNUTO]** Mezi těmito režimy není pevná hranice počtu weeků. Jde o výslovné rozhodnutí FAX/Admina podle konkrétní situace, nikoliv automatický přechod po univerzálním časovém prahu.

### Suspended

**[ROZHODNUTO PRO PRVNÍ VERZI]** Již zahájený turnaj, u kterého je reálné pozdější pokračování, může přejít do dočasného stavu `Suspended` místo terminálního `Abandoned`. Dosavadní výsledky i přesný stav právě rozpracovaných zápasů se zachovají a další turnajová simulace se zastaví do formálního obnovení.

Při obnovení pokračuje rozpracovaný zápas ze stejného skóre a zachovaného match/rally logu. Aktuální stamina, focus, fatigue a health se před pokračováním znovu odvodí podle skutečné délky přerušení a průběžných událostí; nic se automaticky neresetuje.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Dlouhé `Suspended` období nezamkne hráčům automaticky všechny mezilehlé weeky. Mohou v nich při splnění běžných pravidel hrát jiné turnaje; Week Tournament Lock původní Edition se znovu uplatní v jejím skutečném resume weeku.

Pokud konkrétní hráč při obnovení nemůže pokračovat kvůli zdraví, jeho zápas skončí `RET`. Neodůvodněné odmítnutí nebo nenastoupení se řeší jako `Default`, nikoliv `ABN`; `ABN` je vyhrazen pro vnější příčinu bez zavinění hráčů.

### Abandoned po zahájení

**[ROZHODNUTO PRO PRVNÍ VERZI]** Jestli už zahájenou Tournament Edition nelze dokončit a FAX ji formálně ukončí jako `Abandoned`, všechny dokončené zápasy zůstávají oficiální ve statistikách i H2H. Bez platně dokončeného finále nevznikne automatický šampion ani titul; pouze FAX může výslovným mimořádným rozhodnutím přiznat jiný konečný výsledek nebo titul.

Každý hráč získá nejvyšší rankingovou hodnotu, kterou do okamžiku ukončení skutečně odemkl podle běžného win/BYE/W/O kontraktu. Bez platného finále nikdo automaticky nedostane champion points. Jsou-li prize money nakonfigurované, aktivní hráči dostanou loser payout nejvyššího fyzického stage, kterého skutečně dosáhli; winner payout se bez platného vítěze nevyplatí.

Zahájený zápas, který už nebude obnoven ani dohrán, se uzavře jako `ABN`: zachová částečné skóre, skutečný čas, rally log a vzniklé fyzické následky, ale nemá vítěze, poraženého ani H2H výsledek. Ještě nezahájené zápasy nebo prázdné budoucí sloty nejsou `ABN` zápasovými výsledky; zůstávají pouze neodehrané či zrušené.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Hranici krátkého vnějšího přerušení určuje produktová časová abstrakce, nikoliv reálný počet minut. Přerušení, po němž hra pokračuje ve stejném `Match Day Slotu`, zůstává součástí `In Progress` zápasu a podle situace použije `External Interruption → Yes Let / replay`. Pokračování přesunuté do pozdějšího Match Day Slotu nebo weeku vyžaduje `Suspended`.

**[OTEVŘENO]** Detailní Admin UI, další mimořádné kompenzace a složité přesuny přes hranici sezony. Potvrzené přechody a důsledky `Cancelled / Postponed / Suspended / Abandoned` se tím znovu neotevírají.

## 13.3 Sezonní kalendář

**[ROZHODNUTO]** Sezonní kalendář lze vytvořit více způsoby:

- ručně,
- ze šablony,
- zkopírováním jiné sezony.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Uživatel může plánovat všech 50 sezon Runu, i když je nasimulovaný teprve Season 1 Week 1. Vzdálená budoucnost však nemusí být předem uložena jako desítky plných kopií stejného kalendáře.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Opakující se Tournament Series se do budoucích sezon promítají jako úsporné virtuální `Inherited Plans`. Kalendářový pohled je může zobrazit ve stejných weecích jako předchozí aktivní ročník pomocí průhledného návrhu s odlišným, například přerušovaným, okrajem. Inherited Plan ještě není samostatnou fyzicky uloženou Tournament Edition, nemá vlastní stabilní `edition_plan_id` a nedědí výsledky, přihlášky, los ani odehrané zápasy.

Konkrétní Edition Plan se stabilním `edition_plan_id` z virtuálního návrhu zhmotní teprve při první operaci, která potřebuje vlastní trvalý stav:

- individuální editace či override,
- výslovné samostatné nebo hromadné potvrzení,
- import,
- announcement/publication nebo jiná první operace vyžadující trvalou veřejnou identitu,
- vstup do entries, rozhodování hráčské AI, jiná trvalá reference, simulace nebo Season Transition.

Pouhé prohlížení, filtrování, vyhledávání či preview vzdálené budoucnosti žádný objekt ani ID nevytváří. Bezprostředně před materializací engine znovu vyřeší aktuální dědičnost a validaci. Jedna materializace je atomická: vznikne buď celý platný Edition Plan, nebo nic; chyba nespotřebuje ID ani číslo ročníku a přesně vysvětlí opravu. Následná Tournament Edition se materializuje podle vlastních lifecycle prerequisites a používá odlišné `edition_id`.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Hromadná materializace nejprve provede preflight a oddělí platné návrhy od konfliktů. Po výslovném potvrzení se nezávislé platné návrhy materializují atomicky každý za sebe; konfliktní zůstanou virtuální a viditelně se vypíšou, nic se tiše nepřeskočí. Změní-li se zdroj dědičnosti mezi preview a commitem, engine efektivní hodnoty znovu spočítá, ukáže rozdíl a vyžádá nové potvrzení.

**[ROZHODNUTO][ENGINE INVARIANT]** Samotná materializace nezamyká všechny zděděné sportovní hodnoty. Každé pole sleduje dědičnost až do svého vlastního provozního locku; přesné historické snapshoty se vytvoří v okamžicích určených příslušným kontraktem.

**[ROZHODNUTO]** Konkrétní `Edition Plan` ukládá cílovou sezonu, plánovaný week nebo rozsah weeků a pouze výslovné overrides. Nezměněné hodnoty se dědí; plán nemusí duplikovat celý efektivní objekt předchozího ročníku.

**[ROZHODNUTO]** Běžný plán další sezony vychází z posledního existujícího efektivního ročníku či plánu stejné Series. Pokud Series jednu nebo více sezon vynechala, návrat dědí z posledního skutečně existujícího ročníku, nikoliv z prázdné mezery.

**[ROZHODNUTO]** Pravidla vázaná na cílovou sezonu, zejména bodová tabulka, se vždy vyřeší z `Category × target season`. Nekopírují se slepě z minulé Edition ani z Calendar Package pro jinou sezonu.

Zhmotněná Edition:

- převezme příslušné konfigurační parametry předchozího ročníku nebo časově platné šablony,
- bodovou tabulku Ranked Edition však vždy čte z konfigurace přiřazené kategorie pro cílovou sezonu podle kapitoly 14.1, nikoliv slepě z předchozí Edition,
- dostane sezonu a rok odpovídající cílové sezoně,
- pokračuje pod stejným `series_id`, ale má nové vlastní `edition_id`,
- nezačne se starými přihláškami, losy ani výsledky.

**[ROZHODNUTO]** Jedna Tournament Series může mít v téže sezoně více samostatných Edition Plans a Editions. Každý plán a každá Edition mají vlastní identity podle kapitoly 13.1; přesné validační edge cases a typické použití se mohou dále dopracovat.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Season Transition nepotřebuje ručně připravenou kopii celého budoucího kalendáře. Pokud konkrétní potřebná Edition ještě není zhmotněná, vytvoří ji z tehdy platného Inherited Planu aktivní opakující se Tournament Series. Jednorázové, ukončené nebo pro danou sezonu neaktivní Series se automaticky nevytvářejí.

Admin může u jednoho návrhu zvolit například:

1. `Vytvořit beze změn`,
2. `Upravit a vytvořit`,
3. `Přesunout do jiného weeku`,
4. `Tuto sezonu nepořádat`,
5. `Rozhodnout později`.

**[ROZHODNUTO]** Season Builder nabídne také bezpečné hromadné `Vytvořit všechny nezměněné návrhy`. Před potvrzením ukáže společné preview a případné konflikty.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Změna budoucího kalendáře má dva výslovné scopes:

1. `Only this Edition` – změna platí pouze pro konkrétní ročník,
2. `From this season onward` – změna upraví děděný plán od zvolené sezony dál.

Změna `From this season onward` přepíše pouze dosud děděné budoucí hodnoty. Již existující individuální override konkrétní Edition se tiše neztratí. Impact preview ukáže, které sezony se změní, které explicitní overrides zůstanou zachované a kde vzniká konflikt vyžadující rozhodnutí Admina.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Budoucí část aktivní sezony zůstává editovatelná. Změny již nasimulované minulosti používají obecný branchový a historický workflow z kapitoly 7; nevzniká kvůli nim druhý zvláštní systém.

**[ODLOŽENO]** Zbývající přesné workflow Season Builderu, verzování šablon, detailní texty konfliktních hlášení, UI vzdálených Inherited Plans a opravy už vytvořeného kalendáře. Spouštěče, atomicita a conflict behavior materializace jsou již rozhodnuté výše.

### 13.3.1 Hromadná práce s Tournament Series

**[ROZHODNUTO]** Běžná úprava právě otevřeného turnaje výchozím způsobem mění pouze konkrétní `Tournament Edition`. Změna se automaticky nepropíše do ostatních ročníků stejné Tournament Series.

**[ROZHODNUTO]** Tournament Series lze v Adminu rozbalit do přehledu jejích Editions. V tomto přehledu lze:

- vybrat a hromadně upravit více ročníků,
- kopírovat zvolené vlastnosti z jedné Edition do jiných,
- vybrat přesné cílové Editions i přesné přenášené vlastnosti.

**[ROZHODNUTO]** Každá taková operace nejprve vytvoří editovatelný preview. V něm lze ještě změnit jednotlivé hodnoty, některé cíle vyřadit nebo upravit samostatně a znovu přepočítat validaci. Skutečná data se změní až finálním potvrzením.

**[ROZHODNUTO]** Kopírování vlastností mezi Editions je jednorázový snapshot aktuálních hodnot, nikoliv trvalé propojení. Pozdější změna zdrojové Edition již cílové Editions nezmění.

## 13.4 Délka a fáze turnaje

**[ROZHODNUTO]** Turnaj může přesahovat do více týdnů.

**[ROZHODNUTO]** Každý turnaj má samostatně přiřazené:

- jeden nebo více `Qualification Weeks`,
- jeden nebo více `Main Draw Weeks`.

Main Draw má běžně jeden nebo dva weeky; výjimečně může mít více, například u Team World Championship.

**[ROZHODNUTO]** Turnaj ani Main Draw nemají pevnou maximální délku. Pokud `Main Draw` trvá více než dva weeky, Admin zobrazí neblokující varování s oranžovým vykřičníkem; nejde však o chybu a uložení ani simulace se nezablokují. Qualification Weeks se do tohoto dvouweekového upozornění nepočítají.

**[ROZHODNUTO]** Kvalifikace musí být vždy dokončena před začátkem Main Draw. Qualification Weeks a Main Draw Weeks se však smějí překrývat. Pokud se překrývají, uvnitř společného weeku se nejprve dokončí kvalifikace, určí kvalifikanti a LL a teprve potom začne Main Draw.

Platná je tedy například konfigurace:

- kvalifikace: weeky `10–11`,
- Main Draw: weeky `11–12`.

V překrývajícím se weeku 11 proběhne nejprve zbývající kvalifikace a následně Main Draw.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Kvůli překryvu není nutné rozdělit celý světový engine na přesné hodiny. Turnajový `Match Schedule` však používá zjednodušené denní sloty: jeden `Match Day Slot` představuje jeden hrací den bez konkrétních časů začátku. Pevný počet sedmi slotů pro každý week nebyl rozhodnutý.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá Tournament Edition má `Round Schedule` a navazující `Match Schedule`:

- každé kvalifikační i Main Draw kolo dostane jeden denní slot nebo souvislý rozsah denních slotů,
- jedno kolo smí podle velikosti fieldu zabírat více dnů,
- konkrétní zápasy se přiřadí do hracích dnů a uvnitř každého dne dostanou pevné zveřejněné pořadí,
- schedule musí zachovat feeder návaznosti, dokončení potřebné kvalifikace před Main Draw, minimální potřebný odpočinek a ostatní technické prerequisites,
- výchozí schedule engine vytvoří automaticky podle velikosti pavouku, počtu kol, Qualification/Main Draw Weeks a plánované délky turnaje,
- Admin může celý návrh ručně upravit; nevalidní pořadí nelze potvrdit, dokud je neopraví nebo výslovným konzistentním Manual Overridem neupraví všechny dotčené vazby.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Zápasy jednoho dne se simulují postupně ve svém uloženém pořadí. Pozdější zápas proto používá aktuální fatigue, stamina, health a další následky po dřívějších zápasech daného hráče; nejde o množinu současných zápasů se společným slot-start snapshotem.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Automatický scheduler hledá logicky platné a co nejférovější rozložení. Prioritně respektuje feeder vazby, potřebný odpočinek a srovnatelnou recovery obou soupeřů. Bere v úvahu také carryover z předchozího weeku: hráči, který v minulém weeku došel například do finále a hned v dalším weeku začíná jiný turnaj, přidělí první zápas co nejpozději, pokud tím neporuší důležitější vazby. Náhodnost slouží pouze jako tie-break mezi stejně vhodnými platnými variantami.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][SCHEDULER CONTRACT]** Tvrdé podmínky jsou, v tomto významu, nepřekročitelné:

1. feedery a potřebné výsledky musí být známé; před rozuzlením lze plánovat placeholder, ale skutečný zápas nelze spustit bez obou hráčů,
2. hráč smí standardně odehrát nejvýše jeden zápas v jednom Match Day Slotu,
3. jeho další zápas může začít nejdříve v následujícím Match Day Slotu,
4. kvalifikace musí být dokončená před startem Main Draw,
5. všechna kola se musí vejít do nakonfigurovaných weeků a Round Schedule.

Je-li konfigurace neproveditelná, scheduler nesmí potají vytvořit nespravedlivé pořadí ani porušit tvrdé pravidlo. Vrátí konkrétní chybu a návrh opravy, například prodloužit kolo nebo přidat slot; Admin může změnit konfiguraci, ale ne potvrdit skryté porušení.

Mezi platnými variantami používá scheduler lexikografické fair-rest priority v tomto přesném pořadí:

1. maximalizovat odpočinek hráče, který ho má méně,
2. minimalizovat rozdíl recovery obou soupeřů,
3. zohlednit, kdo odehrál předchozí zápas později,
4. dát kvalifikantovi nebo LL maximální rozumný odpočinek před Main Draw,
5. dát hráči po pozdním kole či finále předchozího weeku co nejpozdější rozumný první zápas,
6. zachovat již publikovaný schedule a měnit nejmenší nutný rozsah,
7. použít uloženou deterministickou náhodnost jen jako tie-break mezi jinak stejně vhodnými platnými variantami.

Ranking, seed, národnost ani popularita nesmějí samy vytvářet odpočinkovou výhodu.

**[ROZHODNUTO]** Vygenerované pořadí se uloží při potvrzení schedule a při spuštění simulace se znovu náhodně nehází. Viewer ukazuje pevné pořadí zápasů uvnitř dne bez slibovaných přesných časů.

**[ROZHODNUTO]** Schedule se zveřejní po potvrzení. Pozdější změny se viditelně označí a engine při odhlášení, náhradě nebo jiné změně zachová co největší část již publikovaného pořadí; přepočítá pouze nejmenší nutný dotčený rozsah.

**[ROZHODNUTO]** Budoucí zápasy lze plánovat pomocí feeder placeholderů, například `vítěz zápasu 12` proti `vítězi zápasu 13`. Takový zápas je do určení hráčů provisional; po jejich určení se potvrdí, nebo se minimálně přesune, pokud to vyžaduje odpočinek či jiná platná vazba.

`Match Day Slot` je turnajová plánovací jednotka a není totožný s globálním `Simulation Slot` z kapitoly 6.6 ani s interním procesním oknem entries či losu z kapitoly 6.7.

**[ODLOŽENO]** Přesné hodiny, číselná délka či kapacita slotů, složité odklady a přeložení, venue logistika, paralelní kurty, mimořádné změny schedule a číselné kvalifikační bodové tabulky. Tvrdé podmínky a pořadí fair-rest priorit jsou již rozhodnuté; základ jedné Q stage hodnoty a jejího přičtení k Main Draw složce je rozhodnutý v kapitole 18.1.

## 13.5 Kurty a venues

**[POZDĚJI]** První verze nebude rozlišovat herní podmínky kurtů ani jejich vliv na stylový matchup. Rychlost či pomalost prostředí, odskok, glass/classic court, arenas, kapacity a další venue charakteristiky mohou přijít v některé pokročilejší verzi enginu.

## 13.6 Paralelní turnaje

**[ROZHODNUTO]** V jednom weeku může současně probíhat více turnajů.

**[ROZHODNUTO]** Počet souběžných turnajů nemá pevný maximální limit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Jeden hráč smí během jednoho weeku aktivně soutěžit nejvýše v jednom oficiálním turnaji. Pouhý fakt, že Tournament Edition zasahuje do více weeků, hráče neblokuje po celou její nominální délku; používá se `Week Tournament Lock`:

- jakmile hráči v daném weeku začne jeho kvalifikace nebo Main Draw, původní turnaj mu obsadí celý tento week,
- ani po vyřazení už v témže weeku nesmí začít druhý turnaj,
- do dalšího weeku se lock přenese pouze tehdy, pokud hráč v původním turnaji stále pokračuje a Edition není pro tento week formálně `Suspended`; během dlouhého přerušení se lock uvolní a znovu se aktivuje v resume weeku podle kapitoly 13.2,
- po vyřazení ve Weeku 20 je hráč od Weeku 21 volný; po vyřazení ve Weeku 21 je volný od Weeku 22,
- přímo přijatý hráč do Main Draw smí v dřívějším qualification-only weeku téže Edition hrát jiný turnaj, protože jeho vlastní fáze ještě nezačala.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Week Tournament Lock platí pro všechny oficiální soutěže podporované enginem, zejména MSA Tour, olympijské hry, juniorské mistrovství světa a jejich kvalifikace. Předběžné a podmíněné přihlášky do více akcí zůstávají povolené podle kapitoly 15.1, ale nikdy z nich nevznikne právo skutečně hrát dva turnaje v jednom weeku.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Pro následující week může entry objekt používat podmíněný stav `Still Competing`. Pokud hráčův předchozí turnaj do dalšího weeku skutečně pokračuje, engine jej z podmíněné následující akce omluveně stáhne a dovolí jeho nahrazení. Správně označený a včas vyřešený stav `Still Competing` není disciplinárním proviněním.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Kombinace turnajů v po sobě jdoucích weecích je platná pouze tehdy, když zjednodušená kontrola podle míst a dostupných Simulation Slots vyhodnotí přesun jako proveditelný. Stejná země sama proveditelnost nezaručuje a jiná země ji sama nevylučuje. Detailní lety, trasy a víza se nesimulují; proveditelný přesun následně vytváří Travel Load podle kapitoly 5.5.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Turnaj kvůli individuálnímu programu hráče automaticky nepřesouvá zápasy ani kola. Admin/FAX může udělit výslovnou výjimku, ale zásah musí být konzistentní a zaznamenaný v Audit Logu.

**[POZDĚJŠÍ POKROČILÁ VERZE]** Přesnější pravidla podle nepřekrývajících se hracích období, možnost dvou krátkých turnajů v témže weeku, clash lift, detailní doprava, víza a další výjimky. Pro první verzi je nahrazuje výše uvedený jednodušší Week Tournament Lock.

## 13.7 Prestiž turnaje

**[PROZATÍMNÍ]** Každá Tournament Series může mít vlastní časově proměnlivé `Prestige Score`, které vyjadřuje dlouhodobou reputaci turnaje odděleně od jeho formální kategorie, rankingových bodů, prize money a momentální síly startovního pole. Dva turnaje stejné kategorie, například dva Silvery, tak mohou mít rozdílnou prestiž a rozdílnou schopnost přilákat hráče.

**[PROZATÍMNÍ]** Category Package může pro každou kategorii dodat typickou výchozí hodnotu. Pokud Admin při založení Tournament Series vlastní prestiž nezadá, použije se tato hodnota jako počáteční default; nejde o trvalé živé propojení ani o povinně stejnou prestiž všech turnajů kategorie.

**[PROZATÍMNÍ]** Prestiž se má v čase měnit postupně podle historie a významu turnaje. Admin ji může ručně upravit nebo zamknout. Změna kategorie Tournament Series prestiž okamžitě neresetuje: povýšení ani sestup nemažou vybudovanou reputaci a nová kategorie ji může ovlivňovat pouze postupně.

**[PROZATÍMNÍ]** Konkrétní Tournament Edition může vedle dlouhodobé prestiže Series získat dočasný kontextový bonus nebo postih, aniž by se jednorázová mimořádná Edition automaticky stala novou trvalou reputací celé Series.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Vedle obecného Prestige Score může později vzniknout individuální `Tournament Appeal`, který pro konkrétního hráče skládá prestiž, body, prize money, kalendář, únavu, cestování, domácí prostředí a další osobní priority. Tento název, existence jedné souhrnné hodnoty i její matematika zatím nejsou pevně rozhodnuté.

**[PROZATÍMNÍ]** Admin má pracovně vidět přesnou interní hodnotu prestiže. Viewer ji má spíše vyjadřovat slovní úrovní, pořadím turnajů a historickým vývojem než vydávat interní číslo za oficiální veřejnou veličinu.

**[ODLOŽENO]** Číselná škála, defaulty kategorií, vstupní faktory, tempo růstu a poklesu, ochrana před samoposilující smyčkou silné pole → prestiž → silné pole, pravidla Edition modifieru, dopad na entry AI a přesný Admin/Viewer layout.

## 13.8 Lifecycle Tournament Edition

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][LIFECYCLE CONTRACT]** Stav Tournament Edition se odvozuje z její skutečné historie a dokončených událostí; není to libovolný štítek. Edition má současně tři autoritativně provázané vrstvy.

1. **Hlavní lifecycle:** `Draft → Scheduled → In Progress → Completed` s výjimečnými větvemi. Nepoužitý soukromý Draft lze odstranit; soukromý nepoužitý `Scheduled` se smí vrátit do Draftu, pokud ztratí prerequisites. `Scheduled → Postponed / Cancelled`, `Postponed → Scheduled / Cancelled`, `In Progress → Suspended / Abandoned` a `Suspended → In Progress / Abandoned`. `Completed / Cancelled / Abandoned` jsou terminální. Veřejná nebo datově použitá Edition se nesmí vrátit do Draftu; změna terminální minulosti vyžaduje branch/historical workflow.
2. **Komponentní stavy:** Entries používají přesně `Not Open → Main Entry Window Open → Qualification Entry Window Open → All Entries Closed → Finalized`; Entry List `Not Published → Published`; Draw `Not Created → Draft → Published → Locked`; Qualification `Not Applicable / Not Started → In Progress → Completed`; Main Draw `Not Started → In Progress → Completed`. Fáze, kola a zápasy mají vlastní stav. Auditované `Reopen Entry Process` po Postponed smí znovu otevřít entry workflow v nové veřejné verzi.
3. **Public Stage:** `Hidden → Announced → Entries Open → Entries Closed → Entry List Published → Draw Published → Qualification → Main Draw → Completed`; nepoužitelné kroky se přeskočí. Výjimečně se zobrazí `Postponed / Suspended / Cancelled / Abandoned`.

Ve fázi Qualification Entry Window Viewer ukazuje srozumitelné `Entries Open` a doplněk `Qualification entries only`; Admin vidí přesný komponentní stav. Viewer vždy vidí jen veřejný stav platný v prohlíženém historickém bodě. Admin navíc vidí deadlines, freezes, závislosti, chybějící prerequisites a varování. Stav se mění výslovnou doménovou akcí, například `Publish Draw`, `Postpone`, `Cancel` nebo `Resume`, která provede odpovídající data a audit; ne prostým raw dropdownem. Přesné délky obou entry oken tím nejsou rozhodnuté a zůstávají v `PAQ-083`.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Neúplný Draft lze uložit. Chybějící údaje jsou zřetelně označené, ale neblokují nesouvisející práci. Přechod do `Scheduled`, otevření přihlášek, vytvoření losu nebo simulace se povolí teprve tehdy, když jsou platné všechny prerequisites relevantní pro právě prováděnou operaci. Chyba používá červený operation-scoped vykřičník, přesně vysvětlí, co chybí a jak to opravit, a neblokuje jiné nezávislé části Runu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Čistě interní nepoužitý Edition Plan nebo Draft lze odstranit z aktivního kalendáře. Samotná potvrzená změna zůstane dohledatelná v Audit Logu a historii verzí. Jakmile však byla Edition veřejně oznámena nebo už má přihlášky, los či zápasy, nesmí z aktuální historie beze stopy zmizet; musí se vyřešit odpovídající lifecycle akcí, například `Cancelled`, `Postponed`, `Suspended` nebo `Abandoned` podle skutečného stavu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá Tournament Edition je výslovně `Ranked` nebo `Unranked`. Běžná nová Edition má výchozí status `Ranked`; Admin ji musí výslovně označit jako `Unranked`. Bodová kategorie sama tento status neurčuje. Category/World Package však může určit konkrétní typ soutěže jako předem `Unranked Only`; takovou Edition nelze v žádném ročníku změnit na Ranked. Všechny ostatní typy používají běžný Ranked default a jejich konkrétní Edition může mít povolený override podle následujících pravidel.

`Ranked` Edition musí mít před oznámením, zveřejněním hráčům, otevřením entry rozhodování a simulací kompletní bodovou tabulku všech relevantních kvalifikačních a Main Draw výsledků. Neúplná Ranked Edition může existovat pouze jako interní Admin Draft; Viewer ani hráčská AI ji nesmějí vidět nebo použít při volbě turnaje. Prize money v první verzi povinným prerequisite nejsou.

**[ROZHODNUTO PRO PRVNÍ VERZI]** U běžné neveřejné Draft Edition lze status před announcementem opravit oběma směry. Jakmile byla Edition veřejně oznámena jako Unranked, nesmí být změněna na Ranked. Oznámenou Ranked Edition lze před prvním zápasem změnit na Unranked pouze výslovným veřejným `Tournament Update` nebo rozhodnutím FAX/Admina s impact preview a přepočtem všech relevantních dopadů.

Od prvního skutečně zahájeného zápasu včetně kvalifikace je normální změna statusu uzamčená. Povoleno je už jen mimořádné odebrání statusu `Ranked → Unranked` rozhodnutím FAX; vyžaduje důvod, veřejný update, Audit Log a přepočet bodových dopadů. Opačná změna `Unranked → Ranked` je po zahájení zakázaná.

Pokud FAX odebere Ranked status až po skončení turnaje, dřívější historické rankingové snapshoty, losy, rozhodnutí hráčů a odehrané události zůstávají tak, jak byly v daném čase skutečně známé. Od účinného bodu rozhodnutí se turnajové body odstraní z nových rankingových výpočtů; minulá simulovaná historie se zpětně nepřepisuje.

**[ROZHODNUTO]** `Unranked` Edition bodovou tabulku nepotřebuje a její výsledek nevstupuje do MSA rankingu ani Best N. Všechny ostatní sportovní následky jsou plnohodnotné: zápasy ovlivní stamina, fatigue, health/injuries, formu a development a zapisují se do statistik, titulů, rekordů, H2H a historie.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Admin mění lifecycle pouze explicitní doménovou akcí, například `Cancel`, `Postpone`, `Resume`, `Publish Draw`, `Edit Result` nebo `Force Resolve`. Akce ověří povolený přechod, u výjimek vyžádá důvod, ukáže dopad a zapíše Audit Log; raw dropdown nesmí obcházet stavový kontrakt.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Rozběhnutý turnaj nelze jednoduše přeskočit a pokračovat, jako by neexistoval. Musí být buď dočasně `Suspended` a později obnoven, nebo formálně ukončen jako `Abandoned`; předstartovní zrušení používá `Cancelled` a přesun termínu `Postponed`. Odehrané výsledky, nedokončené zápasy, body, prize money, tituly, hráčské locky a historie se vyřeší podle kapitoly 13.2 a změna vytvoří odpovídající World Event i Audit Log.

## 13.9 Veřejná znalost turnaje a announcement

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá Tournament Edition má uložený přesný efektivní `announcement_week`, tedy historický bod, od kterého je její existence veřejně známá současně Vieweru i hráčské AI. Admin může interní Draft vidět a upravovat dříve, ale Viewer ani AI hráčů před zveřejněním nesmějí využít skrytou Admin informaci.

V první verzi používají Viewer i všichni hráči stejné veřejné datum. Případné budoucí oddělení soukromého oznámení hráčům od veřejného announcementu je až pozdější rozšíření.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Prvotní oznámení se zveřejní při Week Transitionu, který otevře určený week. Vznikne autoritativní veřejný World Event a teprve od tohoto bodu může Viewer Edition zobrazit a hráčská AI s ní počítat.

Přesný `announcement_week` se předvyplní v tomto pořadí:

1. explicitní override konkrétní Tournament Edition,
2. výchozí announcement week nebo lead time její Tournament Series,
3. typický fallback příslušné kategorie.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Announcement musí být nejméně jeden celý week před nejčasnější skutečnou provozní událostí dané Edition. Počítá se zejména otevření kteréhokoli Entry Window, nabídka wildcard, veřejná deadline nebo publikace entry listu, los a první zápas. Samotné interní vytvoření či editace Admin Draftu se za provozní událost nepočítá. Neplatná kombinace používá červený operation-scoped problém a vysvětlí nejbližší povolený week.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][PUBLIC VERSION CONTRACT]** Každá pozdější veřejně podstatná editace dostane vlastní public timing:

- `Before Announcement` znamená, že změna je součástí prvního zveřejněného stavu a veřejnost nikdy neuvidí předchozí interní hodnotu,
- konkrétní publication week znamená, že od začátku tohoto weeku vznikne nová veřejná verze a `Tournament Update`; do té doby Viewer i hráčská AI znají pouze poslední zveřejněnou verzi.

Naplánované budoucí změny vidí před účinností pouze Admin. Více veřejných změn se stejným publication weekem lze sloučit do jednoho srozumitelného Tournament Update, ale jednotlivé editace zůstávají oddělené v Audit Logu. Čistě interní technická oprava bez veřejného dopadu potřebuje audit, nikoliv Tournament Update.

**[ROZHODNUTO][ENGINE INVARIANT]** Po skutečném announcementu už nelze v současné historii zvolit `Before Announcement`; taková alternativa vyžaduje návrat před veřejnou událost a branch/regeneraci. Změna přiřazená do již běžícího weeku po jeho začátku se stává `Emergency Update`, účinným na nejbližší bezpečné hranici simulace, a vyžaduje důvod. Nikdy zpětně nepřepočítá dřívější rozhodnutí ani historii; hráčská AI reaguje až od okamžiku veřejné znalosti.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Historický Viewer vždy čte právě tu veřejnou verzi Edition, která byla v daném weeku skutečně známá. Admin současně umí dohledat interní pending verze, public timing, World Event a jednotlivé auditované změny.

**[ROZHODNUTO][ENGINE INVARIANT]** Chce-li Admin po první veřejné události vytvořit alternativní historii, ve které turnaj nikdy nevznikl, nejde o obyčejné smazání. Engine použije obecný branch/historical workflow: vrátí se do bodu před první veřejnou událostí, odstraní plán v této časové linii a znovu nasimuluje všechny kauzálně navazující následky. Původní branch zůstane zachovaná nebo jinak bezpečně obnovitelná. V současné historii se bez takového návratu používá pravdivý stav `Cancelled` nebo jiný odpovídající lifecycle výsledek.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Hráčská AI plánuje pouze podle turnajů a změn, které už byly v jejím historickém bodě skutečně veřejně potvrzené. Nesmí číst skryté Edition Plans ani budoucí announcement nastavený pouze v Adminu.

**[POZDĚJŠÍ VERZE, SMĚR]** Pokročilejší hráčská AI může z veřejné historie, pravidelnosti, stability termínu a významu Tournament Series vytvářet vlastní pravděpodobné očekávání, že se turnaj uskuteční v podobném období i další sezonu. Větší tradiční akce mohou být očekávány silněji a pravidelné menší akce s menší jistotou. Nejde o potvrzenou znalost ani přístup ke skrytému plánu; přesná inteligence, matematika a dopad na program se budou rozvíjet až v dalších verzích.

---

# 14. Turnajové kategorie a sezonní pravidla

**Rozsah kapitoly:** schopnost definovat tour, kategorie a sezonní parametry je funkčnost enginu. Veškeré konkrétní názvy, hierarchie a hodnoty v této kapitole jsou pouze **Official Run default/test configuration** a mohou se mezi Runy i sezonami změnit.

## 14.1 Kategorie řízené balíčkem

**[ROZHODNUTO V PRINCIPU]** Seznam a identity Competition Systems, volitelných Tours a kategorií může do Runu dodat Category Package nebo je může Admin vytvořit ručně. Jejich hierarchie a stabilní číselné identity se řídí kapitolou 4.6.

**[ROZHODNUTO][ENGINE INVARIANT]** Kategorie mohou v průběhu historie vznikat, měnit se, být deaktivovány nebo nahrazeny. Od určité sezony se může změnit i celý kategoriální systém. Kategorie, která už byla použita, se nesmí tvrdě smazat ani odstranit z historie.

**[ROZHODNUTO][ENGINE INVARIANT]** Každá kategorie má stabilní `category_id`. Pokud se po přestávce vrátí skutečně tatáž historická kategorie, může se znovu aktivovat pod stejným ID; pokud jde o novou kategorii pouze se stejným nebo podobným názvem, dostane nové ID.

**[ROZHODNUTO]** Sezonní stav kategorie určuje právě jeden Competition System, nejvýše jednu Tour, `display_order` a případný `tier_rank`. Tyto hodnoty se do další sezony standardně dědí, ale reorganizace je smí změnit bez přepsání minulosti. Tier se porovnává jen mezi sourozenci; speciální nesrovnatelná kategorie může používat `tier_rank = null`. Podrobnosti a odložená otázka shodných tierů jsou v kapitole 4.6.

**[ROZHODNUTO]** Běžná změna kategorií nebo celého systému nabývá účinnosti od začátku nové sezony. Simulace smí takovou systémovou změnu provést pouze mezi sezonami.

**[ROZHODNUTO][ENGINE INVARIANT]** Admin může výjimečně vynutit změnu od konkrétního weeku uprostřed sezony. Operace musí mít silné varování, preview dopadů, zachovat již vzniklou historii a řídit se obecnými pravidly pro změnu minulosti a regeneraci dotčené budoucnosti.

**[ROZHODNUTO V PRINCIPU]** Pravidla konkrétní kategorie se mohou mezi sezonami měnit.

Měnit se mohou zejména:

- bodové tabulky,
- prize money,
- velikost hlavního pavouku,
- velikost a formát kvalifikace,
- další sezonní parametry.

**[ROZHODNUTO]** Bodová tabulka kategorie je vždy konfigurací konkrétní kategorie v konkrétní sezoně, nikoliv jednou bezčasou hodnotou kategorie. Ranked Tournament Edition přiřazená této kategorii převezme tabulku platnou pro svou sezonu.

**[ROZHODNUTO]** Při vytvoření nové sezony se sezonní bodová tabulka každé pokračující kategorie předvyplní efektivní tabulkou bezprostředně předchozí sezony. Admin ji může pro novou sezonu samostatně změnit; změna nesmí zpětně přepsat tabulku, výsledky ani rankingové snapshoty starší sezony.

**[ROZHODNUTO]** Jsou-li prize money v daném Runu nakonfigurované, jejich tabulky se mohou a v Official Runu budou během let měnit.

**[ROZHODNUTO]** Velikost hlavního pavouku nebo kvalifikace se může mezi sezonami výjimečně změnit.

**[PROZATÍMNÍ]** Kategorie mohou mít vlastní barvy, badges nebo stickery. Vizuální systém se ještě potvrdí.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Turnajová loga nejsou potřeba; mohou přijít později.

**[OTEVŘENO]** Přesná datová reprezentace deaktivace a reaktivace, Admin UX, validace kompatibility a hranice toho, kdy je návrat ještě tatáž kategorie a kdy už nová identita.

## 14.2 Současný oficiální testovací katalog tour a kategorií

**[ROZHODNUTO PRO SOUČASNOU PRACOVNÍ VERZI]** Official Run a jeho výchozí Official FAX Category Package nyní používají tuto strukturu:

### World Tour

1. World Championship,
2. World Tour Finals,
3. Diamond,
4. Emerald,
5. Platinum,
6. Gold,
7. Silver,
8. Bronze.

### Elite Tour

1. Copper,
2. Cobalt,
3. Iron,
4. Nickel,
5. Tin,
6. Zinc.

### Challenger Tour

1. MSA Challenger 100,
2. MSA Challenger 90,
3. MSA Challenger 85,
4. MSA Challenger 80,
5. MSA Challenger 70,
6. MSA Challenger 65,
7. MSA Challenger 60,
8. MSA Challenger 55,
9. MSA Challenger 50,
10. MSA Challenger 45,
11. MSA Challenger 40.

### Development Tour

1. ISD Future 25,
2. ISD Future 20,
3. ISD Future 15,
4. ISD Future 10,
5. ISD Future 5.

**[PROZATÍMNÍ CHARAKTER KATALOGU]** Toto je pevně zvolený základ pro současné testování a vývoj, ale nikoliv slib, že stejný katalog zůstane navždy. Výsledky simulací mohou vést k přejmenování, přesunutí, přidání nebo odebrání kategorií, změně jejich posloupnosti, případně k úplnému překopání celé struktury tour.

**[OTEVŘENO]** Přesná hierarchie, bodování, prize money, formáty, velikosti pavouků, kvalifikace a další pravidla jednotlivých kategorií se budou pomocí simulací postupně ladit.

## 14.3 Rozsah detailní simulace tour

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Jednotlivé zápasy a celé turnaje se detailně simulují pouze na World Tour a Elite Tour.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Challenger Tour a Development Tour se nyní nebudou simulovat zápas po zápase ani jako kompletní turnajové pavouky.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Mimo běžnou MSA Tour jsou současnými plně simulovanými veřejnými výjimkami juniorské mistrovství světa a olympijské hry. Tím se nemění výše uvedená hranice, že uvnitř pravidelné MSA Tour se detailně simulují pouze World Tour a Elite Tour.

**[ODLOŽENO]** Jak budou Challenger a Development Tour abstraktně reprezentovat výsledky, body, postup hráčů, účast a další dopady na společný svět.

---

# 15. Přihlášky, kvalifikace a losy

**Rozsah kapitoly:** entry, qualification a draw engine, stabilní sloty, validace, preview a audit jsou funkčnost enginu. Konkrétní timing, kapacity, počty seedů, rozmístění, BYE, qualification formáty a automatické replacement policy jsou **Official Run defaulty**, které lze podle podporované konfigurace změnit v Category/Season/Tournament nastavení. Bezpečnostní a historické invarianty Adminu zůstávají globální.

## 15.1 Entry systém

**[CÍLOVÁ FUNKCE]** Turnaje mají vlastní entry pravidla, uzávěrky, priority listy, kvalifikace, main draw a případné náhrady.

**[ROZHODNUTO]** Turnaj používá dvě navazující přihlašovací fáze:

1. `Main Entry Window` – hlavní přihlašovací okno, do něhož se hlásí naprostá většina hráčů; přihláška platí pro turnaj jako celek,
2. `Qualification Entry Window` – následné kvalifikační přihlašovací okno, v němž se mohou přihlásit další hráči a již zařazení hráči se mohou odhlásit.

Hráč z hlavního okna, který se nevejde přímo do Main Draw, automaticky zůstává v kvalifikačním seznamu nebo pod jeho čarou. Nemusí kvalifikaci znovu potvrzovat; pokud ji nechce hrát, musí se odhlásit.

**[ROZHODNUTO]** Po uzavření Qualification Entry Window tvoří všichni přihlášení jeden souvislý prioritní seznam seřazený podle Tournament Ranking Snapshotu:

1. přímí účastníci Main Draw,
2. účastníci kvalifikace,
3. hráči pod kvalifikační čarou.

Horní část kvalifikačního seznamu zároveň funguje jako pořadí pro případný posun do Main Draw. Pokud se před příslušným cut-offem uvolní místo, postupuje nejvýše postavený oprávněný hráč kvalifikačního seznamu.

**[ROZHODNUTO]** Hráč přihlášený až v Qualification Entry Window může být podle svého rankingu zařazen na libovolné odpovídající místo kvalifikačního seznamu. Pokud je například světová desítka nejvýše postaveným hráčem kvalifikace a následně se uvolní Main Draw místo, má přednost před hráčem číslo 70. Hlavní uzávěrka mu nezaručila původní Direct Acceptance, ale pozdní kvalifikační přihláška mu neodebírá rankingovou prioritu pro pozdější posun.

**[ROZHODNUTO]** Každý turnaj má právě jeden `Tournament Ranking Snapshot`, který platí pro celý jeho entry a draw proces, zejména pro:

- rozdělení Main Draw / Qualification / Reserves,
- pořadí všech přihlášených včetně hráčů z Qualification Entry Window,
- posouvání náhradníků,
- nasazení Main Draw i kvalifikace,
- rankingová kritéria LL.

Novější ranking vydaný během procesu tento snapshot automaticky nenahrazuje. Výslovný postpone režim `Reopen Entry Process` původní proces uzavře a vytvoří pro celý nový entry/draw proces jeden nový efektivní snapshot; starý se zachová pouze v historii a oba se nikdy současně nepoužívají pro tutéž aktivní verzi fieldu či losu.

**[ROZHODNUTO]** Výchozím Tournament Ranking Snapshotem je oficiální ranking po dokončení weeku bezprostředně před weekem, ve kterém končí Main Entry Window, tedy `Main Entry Closing Week − 1`. V Adminu lze pro konkrétní turnaj nastavit jiný existující rankingový snapshot.

**[PROZATÍMNÍ VÝCHOZÍ TIMING]**

- Main Entry Window trvá dva weeky,
- bezprostředně následuje jeden week dlouhý Qualification Entry Window,
- potom zbývá několik weeků na stabilizaci seznamů, odhlášení, WC a přípravu losu,
- konkrétní weeky a délky obou oken lze změnit u jednotlivého turnaje.

Příklad při první kvalifikaci ve weeku 20:

- weeky `13–14`: Main Entry Window,
- konec weeku 14: hlavní uzávěrka; výchozí snapshot je ranking po weeku 13,
- week 15: Qualification Entry Window,
- weeky `16–18`: stabilizace seznamů,
- začátek weeku 19: vytvoření losů,
- week 20: první kvalifikační zápasy.

**[ROZHODNUTO PRO NÁHRADNÍKY]** Po vyčerpání všech lucky loserů se oslovují dostupní hráči, kteří byli do turnaje přihlášení, ale nevešli se ani do kvalifikace. Jejich pořadí určuje stejný rankingový snapshot jako vstup a nasazení turnaje. Nedostupný hráč nebo hráč odmítající účast se přeskočí.

**[ROZHODNUTO V PRINCIPU]** Hráč, který splňuje přímý vstup podle rankingu, není vedený jako wildcard. Nepotřebovaná WC se může přidělit jinému hráči nebo zůstat nevyužitá.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Uvolněné nebo nově nepotřebné místo vyhrazené pro WC se nejprve přidělí příslušné dostupné `Reserve Wild Card` (`RWC`) podle uloženého pořadí rezerv. Rezerva zůstává ve stavu `Available`, dokud ji skutečně nevyužije, neodstoupí nebo neztratí eligibility; nejde o jednorázovou nabídku, jejíž nepoužití by ji automaticky vyřadilo. Teprve po vyčerpání dostupných WC rezerv se slot řeší běžným zdrojem náhrady platným pro danou fázi.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Dostane-li se původní držitel WC do fieldu přímo podle Tournament Ranking Snapshotu, WC se mu automaticky odebere a může přejít na další dostupnou WC rezervu. Aktivní draw badge už ukazuje jeho skutečný přímý status, ale historický entry objekt trvale uchová, že mu byla WC dříve přidělena. Samostatná akce výslovného přijetí WC ani RWC se nepoužívá; definitivní přidělení do fieldu je implicitním přijetím a hráč může následně použít běžné odstoupení.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Více změn WC, RWC, přímých přijetí a navazujících posunů vzniklých v jednom procesním okně se přepočítá atomicky ze společného stavu před oknem. Technické pořadí jednotlivých záznamů nesmí změnit, kdo získá přímé místo, WC nebo rezervní prioritu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá přihláška je samostatný historický objekt `Tournament Entry/Application`; nepřepisuje se pouze aktuální buňka na hráči ani se starý záznam nemaže. Objekt uchovává identitu hráče a Edition, čas vzniku, původ rozhodnutí a historii změn stavu, pracovně například `Submitted → Main Draw / Qualification / Reserve / Outside Cut → Withdrawn`. Přesný konečný katalog názvů se ještě dořeší.

Viewer v každém historickém weeku vidí pouze tehdy veřejné stavy přihlášek a entry listů. Admin navíc vidí interní stav, celý status history a Audit Log.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Po úspěšném dokončení každého entry decision slotu se aktuální předběžný entry list zveřejní hráčským AI i Vieweru. Kandidátní rozhodnutí vznikající uvnitř právě běžícího slotu zůstávají skrytá až do společného dokončení; nikdo nesmí reagovat na částečný technický mezistav. Zveřejnění seznamu nemění předběžnou přihlášku na neodvolatelný závazek a Viewer musí její stav označit pravdivě.

**[ROZHODNUTO PRO PRVNÍ VERZI]** V jednom entry decision slotu vyhodnotí všechny hráčské AI své rozhodnutí nad stejným zmrazeným snapshotem ze začátku slotu. Později technicky zpracovaný hráč proto nevidí přihlášky dříve zpracovaných hráčů z téhož slotu. Kandidátní rozhodnutí se použijí společně až na konci slotu; až následující slot může reagovat na nový veřejný či interně dostupný stav entry listu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** V každém nakonfigurovaném entry decision slotu hráčská AI společně přehodnotí všechny tehdy veřejně známé možnosti příslušných weeků. Může ponechat, přidat nebo odebrat předběžnou přihlášku a změnit priority; jednotlivé turnaje nesmí být rozhodovány izolovaně v náhodném technickém pořadí. První verze smí používat jednoduchou rozumnou AI a její přesné faktory, váhy, náhodnost i celková chytrost se budou v dalších verzích kalibrovat a zlepšovat.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Hráčská AI při tomto porovnávání neopomíjí Unranked turnaje. Jejich bodový přínos je přesně nula, ale mohou být atraktivní prestiží, prize money, možností získat titul, reprezentovat zemi nebo jinou hráčovou motivací. Přesné váhy těchto důvodů a individuální chování AI zůstávají otevřené pro pozdější kalibraci.

**[ROZHODNUTO]** Engine nemá pevný početní limit souběžných předběžných nebo podmíněných přihlášek jednoho hráče. AI je omezuje jejich smysluplností, eligibility a konflikty; všechny skutečné závazky však musí včas zúžit tak, aby hráč splnil Week Tournament Lock a ostatní pravidla.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Více kolidujících přihlášek lze během otevřeného procesu dočasně ponechat. Okamžik, od kterého je nevyřešený konflikt sankcionovaný, se řídí skutečným stavem hráče v obou fieldech:

- pokud je přijatý do Main Draw obou akcí téhož weeku, nevyřešený konflikt je po uzavření Main Entry Window už pozdní a sankce může s dalším prodlením růst,
- pokud není přijatý do Main Draw ani jedné akce, může konfliktní volbu dál řešit v navazujícím Qualification Entry Window,
- pokud je v Main Draw jedné akce a mimo Main Draw druhé, může během Qualification Entry Window opustit tu, do jejíhož Main Draw se nedostal,
- po příslušné uzávěrce roste závažnost podle délky prodlení a škody způsobené dotčeným turnajům.

Tato tolerance není oprávněním hrát dva turnaje. Rozhodující je, kam hráč skutečně odjede a nastoupí: může odehrát jednu akci, nebo nenastoupit ani na jednu a vytvořit více porušení; engine mu automaticky nezachraňuje předem určený „prioritnější“ turnaj. Přesné číselné sankce jsou policy a zůstávají otevřené podle kapitoly 20.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Před `Final Commitment Deadline` může hráč svůj zvolený turnajový závazek pro daný week změnit v rámci ostatních entry pravidel. Po tomto deadline každý odpovídající potvrzený závazek zamkne příslušný week i tehdy, když hráč později odstoupí; nevyřešená vícenásobná přihláška tím nezískává právo hrát více akcí. Skutečné zranění či nemoc odstraní disciplinární sankci, nikoliv Week Tournament Lock. Lock může uvolnit zrušení akce, odklad na nový termín s právem všech hráčů znovu se rozhodnout, formální dlouhé Suspended období pro mezilehlé weeky, chyba organizátora nebo výslovné rozhodnutí FAX/Admina; podmíněný stav `Still Competing` pro následující week zůstává samostatnou omluvenou cestou podle kapitoly 13.6.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Ruční Admin změna přihlášky má dvě varianty:

- `Jednorázová změna` – v následujícím entry decision slotu ji hráčská AI smí znovu přehodnotit,
- `Uzamknout rozhodnutí` – AI ji nesmí změnit do ručního odemčení nebo do předem nastaveného konce platnosti zámku.

Obě varianty nesou Manual provenance, správný historický čas a Audit Log.

**[ODLOŽENO]** Přesná eligibility, povinné turnaje, konečné umístění `Final Commitment Deadline` vůči entry closing, losu a freezes, číselné sankční prahy, detailní AI optimalizace, konečný obecný cut-off pro některé posuny a přesný způsob sestavení a seřazení WC rezerv. Priorita dostupné RWC, její trvající dostupnost, automatické odebrání WC při přímém vstupu, uchování historie a atomický přepočet jsou již rozhodnuté.

## 15.2 Kapacita pavouku a počet nasazených

**[ROZHODNUTO]** Každý klasický eliminační pavouk má kapacitu rovnou mocnině dvou: `2, 4, 8, 16, 32, 64, 128…`.

**[ROZHODNUTO]** Kapacita je předem nastavenou vlastností turnaje. Odhlášení nebo nenaplnění field nevede k automatickému zmenšení pavouku; neobsazená místa jsou datově vedena jako BYE.

**[ROZHODNUTO]** Automatická nejbližší mocnina dvou může sloužit jako návrh při vytváření nového turnaje bez zadané kapacity, nikoliv jako průběžný přepočet již existujícího losu.

**[ROZHODNUTO]** Počet nasazených v klasickém pavouku se vypočítá:

> `seed_count = min(počet skutečných hráčů, max(1, kapacita pavouku ÷ 4))`

Příklady:

| Kapacita pavouku | Počet nasazených před omezením počtem hráčů |
|---:|---:|
| 2 | 1 |
| 4 | 1 |
| 8 | 2 |
| 16 | 4 |
| 32 | 8 |
| 64 | 16 |
| 128 | 32 |

## 15.3 Idealizované sloty a rozmístění hráčů

**[ROZHODNUTO]** Každá fyzická pozice v pavouku má také idealizované číslo slotu. To popisuje její místo v dokonale vyváženém nasazovacím systému, nikoliv automaticky skutečný seed hráče.

Pro osm slotů je pořadí shora dolů:

```text
1
8
5
4
3
6
7
2
```

Stejný rekurzivní princip pokračuje pro kapacity 16, 32, 64, 128 a další.

**[ROZHODNUTO]**

- seed 1 má pevný horní slot,
- seed 2 má pevný protilehlý slot, pokud turnaj skutečně má alespoň dva nasazené,
- skuteční hráči skupiny `3–4` se náhodně rozdělí mezi dva idealizované sloty této skupiny,
- skupina `5–8` se náhodně rozdělí mezi své čtyři sloty,
- skupina `9–16` a další vrstvy pokračují stejným zdvojovacím principem.

**[ROZHODNUTO]** Nenasazení hráči se losují náhodně mezi všechny zbývající nenasazené sloty.

**[ROZHODNUTO]** Standardní los nepoužívá ochranu podle země, klubu, předchozího H2H ani rivality. Případná výjimka pro konkrétní budoucí soutěž musí být rozhodnuta samostatně.

## 15.4 BYE

**[ROZHODNUTO]** Při prvotním vytvoření losu obsazují BYE idealizované sloty s nejvyššími čísly. Tím dostávají volné první kolo nejvýše postavené idealizované seed pozice.

Příklad pro 28 hráčů v pavouku pro 32:

- osm nasazených,
- čtyři BYE,
- BYE obsadí idealizované sloty `29–32`,
- volné první kolo tím dostanou skuteční seedy 1–4.

**[ROZHODNUTO]** BYE vzniklé dodatečně po odhlášení a vyčerpání všech povolených náhrad zůstane přesně v uvolněném fyzickém slotu. Již existující los se kvůli němu nepřeskupuje.

**[ROZHODNUTO]** Viewer i Admin nabídnou dva způsoby zobrazení:

1. úplný/technický pohled se všemi BYE sloty,
2. kompaktní pohled, který prázdné zápasy skryje a hráče s BYE vizuálně ukáže až v následujícím kole.

Přesný vzhled a ovládání se dopracují později.

**[ROZHODNUTO]** Samotný BYE ani pozdní vložení náhradníka přímo do vyššího kola nejsou skutečnou zápasovou výhrou a neodemknou vyšší rankingovou hodnotu kola. Prohraje-li hráč svůj první skutečně zahájený zápas, získá v dané draw složce body pouze za první kolo, i kdyby kvůli jednomu či více BYE nebo pozdnímu LL/replacement placementu začínal až ve druhém či pozdějším kole. Jakmile první skutečný zápas vyhraje, vyšší bodová hodnota se dále řídí jeho konečným výsledkem. Pravidlo platí pro všechny entry statusy v Main Draw i kvalifikaci; RET po zahájení prvního skutečného zápasu se pro tento účel počítá jako prohra. Samostatný W/O postup se řídí výslovnou výjimkou kapitoly 16.3.

**[ROZHODNUTO]** Prize money se u startu po BYE nebo přímém pozdním placementu řídí skutečně dosaženým finishing stage, nikoliv výše popsaným rankingovým unlockem. Hráč, který začne až ve druhém kole a svůj první skutečný zápas prohraje nebo ukončí RET, proto dostane bodovou hodnotu prvního kola, ale prize money druhého kola, pokud jsou pro Edition nakonfigurované.

## 15.5 Q sloty v hlavním pavouku

**[ROZHODNUTO]** Hlavní pavouk lze vylosovat před dokončením kvalifikace. Budoucí kvalifikanti jsou dočasně reprezentováni objekty `Q1`, `Q2`, `Q3` atd.

**[ROZHODNUTO]** Každý Q slot je trvale propojený s jednou konkrétní kvalifikační větví nebo skupinou. Přesun slotu `Q3` v Adminu přesune celý objekt včetně propojení s kvalifikací Q3.

**[ROZHODNUTO]** Q sloty se náhodně losují pouze mezi sloty určené pro nenasazené hráče. Dva Q sloty mohou být v prvním kole proti sobě.

**[ROZHODNUTO]** Počet Q slotů v hlavním pavouku se rovná počtu kvalifikačních pavouků nebo skupin. Každá kvalifikace vytváří právě jednoho postupujícího do svého Q slotu.

## 15.6 Pavoukové kvalifikace

**[ROZHODNUTO]** Pavouková kvalifikace je výchozí a primárně nabízený kvalifikační formát.

**[ROZHODNUTO]** Turnaj nastavuje počet kvalifikačních pavouků a jejich společnou kapacitu. Všechny kvalifikační pavouky jednoho turnaje jsou stejně velké a každý vede k jednomu konkrétnímu Q slotu.

**[ROZHODNUTO]** Počet nasazených uvnitř každého Q pavouku používá stejný vzorec jako hlavní pavouk.

Při `m` souběžných kvalifikačních pavoucích:

- první globální seed vrstva obsahuje seedy `1–m`, pevně po jednom do Q1 až Qm,
- každá další seed vrstva o velikosti `m` se náhodně rozdělí po jednom mezi příslušné sloty všech Q pavouků,
- všichni nenasazení se náhodně losují napříč všemi kvalifikačními pavouky.

Příklad tří Q pavouků pro osm hráčů:

- seed 1 je pevně v Q1, seed 2 v Q2 a seed 3 v Q3,
- seedy 4–6 se náhodně rozdělí jako druhé nasazení po jednom do všech tří Q,
- ostatních 18 hráčů se náhodně rozdělí napříč Q1–Q3.

**[ROZHODNUTO]** BYE se při několika Q pavoucích přidělují po idealizovaných vrstvách:

1. nejprve nejvyšší idealizovaný slot ve všech kvalifikacích,
2. potom další nejvyšší vrstva,
3. neúplná vrstva se mezi Q pavouky rozdělí náhodně.

## 15.7 Skupinové kvalifikace

**[ROZHODNUTO PRO PRVNÍ VERZI]** První verze podporuje dva kvalifikační formáty: pavouk a skupiny. Další formáty mohou případně vzniknout ve vzdálené budoucnosti, ale nejsou součástí současného plánu.

**[ROZHODNUTO]**

- skupinový formát lze zvolit v nastavení turnaje,
- všechny skupiny jednoho turnaje musí být stejně velké,
- minimální velikost skupiny jsou tři hráči,
- z každé skupiny postupuje právě jeden hráč do jednoho odpovídajícího Q slotu,
- ve skupině hraje každý s každým právě jednou.

**[ROZHODNUTO]** První seed vrstva se pevně rozdělí po jednom do jednotlivých skupin. Každá další seed vrstva se mezi skupiny rozdělí náhodně; nepoužívá se snake systém. Nenasazení hráči se poté náhodně rozdělí mezi všechna volná místa.

**[ROZHODNUTO]** Počet seed vrstev je nastavitelný, ale v každé skupině musí zůstat alespoň dva nenasazení hráči:

> `seed_layers ≤ velikost skupiny − 2`

**[ODLOŽENO]** Kompletní určování pořadí uvnitř skupiny, tie-breaky, odstoupení během skupiny a zacházení s nekompletní skupinou.

## 15.8 Lucky loseři

**[ROZHODNUTO]** Dokud kvalifikace nezačala, neexistuje skutečný lucky loser, protože ještě nikdo neprohrál.

**[ROZHODNUTO]** Když se po začátku kvalifikace uvolní místo v hlavním pavouku, vytvoří se anonymní slot `LL1`; další místa vytvářejí `LL2`, `LL3` atd. Číslo určuje pořadí vzniku volných míst, nikoliv jejich pozici shora dolů.

**[ROZHODNUTO]** Po dokončení kvalifikace se LL sloty automaticky zaplní podle LL pořadí. Pokud kvalifikace skončila už před vznikem volného místa, slot přesto dostane další LL číslo a může se okamžitě zaplnit konkrétním hráčem.

**[ROZHODNUTO PRO PAVOUKOVOU KVALIFIKACI]** LL pořadí určuje:

1. nejdříve dosažené kolo – finalisté kvalifikace, potom semifinalisté, čtvrtfinalisté a další,
2. mezi hráči vyřazenými ve stejném kole rozhoduje rankingový snapshot použitý pro turnaj.

**[ROZHODNUTO V PRINCIPU PRO SKUPINY]** Nejdříve se porovnávají hráči na nejvyšším nepostupovém místě ze všech skupin, potom další nepostupové místo atd. Přesné pořadí hráčů se stejným umístěním z různých skupin se rozhodne později.

**[ROZHODNUTO]** Po vyčerpání všech LL následují dostupné externí rezervy podle pravidla v kapitole 15.1. Pokud už není nikdo dostupný:

- před začátkem hlavního turnaje vznikne BYE,
- po uzavření možnosti náhrad postupuje soupeř přes W/O.

**[ROZHODNUTO]** Když se odhlásí vítěz například Q3, jeho fyzický slot se nepřelosuje. Změní se na další LL slot podle pořadí vzniku, například `Q3 → LL2`; ostatní Q sloty zůstávají beze změny.

**[ROZHODNUTO]** Lucky loser vložený do slotu odhlášeného nasazeného hráče nepřebírá jeho seed číslo ani seed status. V aktivním losu zůstává označený svým vlastním `[LLx]`; historie zároveň uchová, který původní seed slot nahradil. Stejně se zachová jeho vlastní kvalifikační původ a rankingový i prize-money výsledek se určí podle kapitol 18 a 19, nikoliv podle statusu původního držitele slotu.

## 15.9 Odhlášení a náhrady – již rozhodnuté části

**[ROZHODNUTO]** Pokud se před vytvořením losů někdo odhlásí, pouze se aktualizují seznamy. Všichni dotčení hráči se automaticky posunou podle Tournament Ranking Snapshotu: nejlepší oprávněný hráč kvalifikačního seznamu může postoupit do Main Draw a nejlepší hráč pod kvalifikační čarou do kvalifikace. Protože los ještě neexistuje, nic se nepřelosovává.

**[ROZHODNUTO]** Pokud se v hlavním pavouku uvolní místo před začátkem kvalifikace a stále je povolený přesun z kvalifikace, postoupí do něj nejvýše postavený oprávněný účastník kvalifikace podle Tournament Ranking Snapshotu.

Pokud už existuje kvalifikační los:

- před `Qualification Redraw Cutoff` se po přesunu kompletně přelosují všechny dotčené Q pavouky; propojení Q1, Q2 atd. s Main Draw zůstává,
- od `Qualification Redraw Cutoff` do `Qualification Draw Freeze` se použije tier-aware seed cascade pouze tehdy, pokud přesun skutečně zasáhl seed strukturu; jinak se doplní konkrétní fyzický slot,
- od `Qualification Draw Freeze` se Q los už nepřelosuje ani necascaduje a konkrétní fyzický slot přesunutého hráče zaplní nejlepší dostupný hráč pod kvalifikační čarou podle Tournament Ranking Snapshotu.

**[ROZHODNUTO]** Při běžném odhlášení nenasazeného hráče po vytvoření losu se pouze zaplní jeho fyzický slot náhradníkem povoleným aktuální fází. To platí i v prostřední cascade fázi: odchod obyčejného nenasazeného hráče sám o sobě nespouští seed cascade ani úplné přelosování.

**[ROZHODNUTO]** Cut-off náhrady se posuzuje zvlášť pro každého hráče. Jeho fyzický slot lze obsadit náhradníkem až do okamžiku zahájení jeho prvního skutečného zápasu; jeden nebo více předchozích BYE tento okamžik neposouvá do minulosti. Jakmile jeho první skutečný zápas začne, při běžném pozdějším odstoupení jej už nemůže nahradit LL, WC rezerva ani jiná rezerva a jeho následující soupeř postoupí přes W/O.

**[ROZHODNUTO]** Původní hráč, který před svým prvním skutečným zápasem odstoupí a je ve slotu skutečně nahrazen, nezíská z dané Tournament Edition žádné rankingové body ani prize money. Historie odstoupení a nahrazení se přesto zachová.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Všechny odchody, posuny, WC/RWC změny, LL sloty a náhrady vzniklé v témže procesním okně se vypočítají atomicky ze společného pre-window stavu. Výsledek nesmí záviset na technickém pořadí, v jakém engine jednotlivé změny zpracoval.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Prokázané skutečné zranění nebo nemoc může omluvit pozdní odhlášení či nenastoupení a odstranit disciplinární sankci. Pokud však odhlášení nastalo až po Final Commitment Deadline, samo zdravotní omluvení neuvolní hráčův Week Tournament Lock pro jinou akci téhož weeku. Zrušení turnaje, chyba organizátora nebo výslovné uvolnění FAX/Adminem se řeší samostatně podle kapitoly 15.1.

**[ODLOŽENO]** Konečný katalog všech mimořádných edge cases, detailní UI atomického preview a pravidla vědomého ručního porušení automatického repair workflow. Základ tří fází, seed cascade, přímé doplnění nenasazeného slotu a hráčský replacement cut-off jsou již rozhodnuté.

## 15.10 Qualification/Main Draw Freeze a procesní okna

**[ROZHODNUTO]** Všechny losy jednoho turnaje se výchozím způsobem vytvoří naráz:

- Main Draw,
- všechny kvalifikační pavouky nebo skupiny,
- objekty a propojení Q1, Q2 atd. mezi kvalifikacemi a Main Draw.

**[ROZHODNUTO]** Výchozí `Draw Week` je week bezprostředně před prvním Qualification Weekem. Pokud turnaj kvalifikaci nemá, je to week bezprostředně před prvním Main Draw Weekem.

**[ROZHODNUTO]** Losy se vytvoří na začátku Draw Weeku, takže jsou hráčům i Vieweru dostupné přibližně jeden týden před prvním zápasem. Konkrétní Draw Week lze u turnaje v Adminu změnit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Qualification a Main Draw mají každá vlastní dvojici hranic a vlastní tři repair fáze. Jejich hranice se neposuzují společně jen proto, že se oba losy výchozím způsobem vytvořily ve stejném okamžiku:

1. `Redraw Cutoff` nastane na začátku předposledního nakonfigurovaného procesního okna příslušného losu.
2. `Draw Freeze` nastane na začátku posledního nakonfigurovaného procesního okna příslušného losu.

Celkový počet a rozmístění dřívějších procesních oken zůstávají konfigurovatelné a jejich výchozí katalog se ještě dořeší; role posledních dvou oken je však pevná.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Před `Redraw Cutoff` se při změně oprávněného fieldu po vytvoření losu znovu kompletně vylosuje celý dotčený Qualification nebo Main Draw. Použije se stále tentýž Tournament Ranking Snapshot a nový draw seed/verze se uloží do historie.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Od `Redraw Cutoff` včetně do `Draw Freeze` se úplné automatické přelosování nepoužije. Odchod nasazeného hráče opraví tier-aware `seed cascade`, která zachová vyváženost povolených seed sektorů:

- seed 2 se po odchodu seedu 1 nepřejmenuje na seed 1,
- již nasazení hráči si při přesunu ponechají původní seed čísla,
- cascade přesouvá jen hráče a seed vrstvy skutečně potřebné k opravě vzniklé mezery,
- na jejím konci se nejvýše postavený oprávněný nenasazený hráč podle Tournament Ranking Snapshotu povýší do uvolněné seed struktury a běžný náhradník zaplní jeho původní fyzický slot,
- běžný odchod nenasazeného hráče seed cascade nespouští a řeší se přímým doplněním jeho slotu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Od `Draw Freeze` se automaticky nemění seed struktura, sektory ani jiné sloty. Náhradník vstoupí přímo do konkrétního uvolněného fyzického slotu a přebírá pouze tuto pozici v pavouku, nikoliv seed číslo nebo entry status původního hráče. Je-li podle fáze zdrojem lucky loser, může se nejprve vytvořit nový `[LLx]` slot. Draw Freeze sama náhrady nezakazuje; poslední hranicí konkrétního hráče je zahájení jeho prvního skutečného zápasu podle kapitoly 15.9.

**[ROZHODNUTO]** Před začátkem kvalifikace má nejlepší oprávněný hráč kvalifikačního seznamu stále přednost při posunu do uvolněného Main Draw místa i po vytvoření losů. Následná oprava Qualification Draw se řídí právě platnou z jeho tří fází. Po začátku kvalifikace už pro nově uvolněná Main Draw místa platí lucky loser workflow.

**[ODLOŽENO]** Přesný výchozí počet časných procesních oken, detailní vizualizace jednotlivých draw verzí a okrajové kombinace ručního override. Umístění `Redraw Cutoff` a `Draw Freeze`, tři repair fáze a jejich samostatné použití pro Qualification i Main Draw již otevřené nejsou.

## 15.11 Ruční úpravy a regenerace losu

**[ROZHODNUTO]** Admin může regenerovat celý los nebo mnoho přednastavených či vlastních částí, například:

- pouze nenasazené hráče,
- horní nebo dolní polovinu,
- konkrétní čtvrtinu,
- jednu seed skupinu,
- vlastní výběr hráčů, slotů nebo oblastí.

Vše mimo vybraný rozsah se automaticky zamkne. Uvnitř rozsahu lze dodatečně zamknout konkrétní hráče, sloty nebo menší oblasti.

**[ROZHODNUTO]** Každá regenerace nejprve vytvoří samostatný náhled. V něm lze:

- změnu potvrdit nebo zrušit,
- znovu náhodně generovat,
- ručně prohazovat povolené hráče,
- měnit zamčené prvky.

Aktivní los se změní až po výslovném potvrzení.

**[ROZHODNUTO]** Neplatný stav může během práce dočasně existovat pouze v náhledu. Okamžitě dostane červený vykřičník a konkrétní chybu; nelze jej potvrdit, aktivovat ani uložit, dokud jej Admin neopraví nebo nevrátí.

Mezi tvrdé strukturální invarianty patří zejména:

- seed 1/2 a seed skupiny pouze v povolených sektorech,
- zachování propojení Q slotu,
- žádný hráč ve dvou slotech téhož turnaje,
- konzistentní návaznosti kol a odehraných výsledků.

**[ROZHODNUTO]** Dva hráče, kteří ještě neodehráli svůj první zápas, lze po začátku turnaje ručně prohodit, pokud zůstane los validní. Zobrazí se oranžové varování, preview dopadů a potvrzení.

**[ROZHODNUTO]** Po prvním odehraném zápase hlavního turnaje nesmí engine automaticky kompletně přelosovat hlavní pavouk. Admin to může ručně vynutit pouze po vyřešení červeného kritického stavu, výslovném potvrzení a bezpečné práci s historií.

## 15.12 Simulate a Manual

**[ROZHODNUTO]** `Simulate` a `Manual / Step-by-step` jsou kombinovatelné způsoby práce, nikoliv dva neslučitelné globální módy.

- Simulate automaticky provádí potřebné kroky do zvoleného rozsahu.
- Manual umožňuje postupovat po krocích, ručně vytvářet či upravovat los a zadávat nebo spouštět výsledky.
- Admin mezi nimi může plynule přecházet a automatika vždy naváže na aktuální potvrzený validní stav.

## 15.13 Konfigurace a označení hráčů

**[ROZHODNUTO]** Kategorie a sezonní pravidla poskytují výchozí konfiguraci losu. Při přiřazení kategorie se turnaji automaticky předvyplní například:

- kapacita hlavního pavouku,
- počet a velikost kvalifikací,
- pavoukový nebo skupinový formát,
- počet seed vrstev ve skupinách,
- počet Q slotů.

Admin může tyto hodnoty pro konkrétní turnaj upravit. Přesná pravidla override vůči Category Package se dořeší později.

**[ROZHODNUTO]** Ve Vieweru i Adminu se za jménem vždy zobrazí relevantní označení postavení hráče v losu. Přímý nenasazený účastník nemá označení.

Existují dva styly:

1. **individuální – výchozí:** `[11]`, `[Q6]`, `[LL2]`, `[WC]`,
2. **skupinový:** `[9/16]`, `[Q]`, `[LL]`, `[WC]`.

Označení jednotlivých typů se samostatně neskrývají; mění se pouze úroveň podrobnosti. Seed má přednost před speciálním entry označením, protože hráč splňující přímý vstup podle rankingu nepotřebuje WC.

Přesný grafický styl badge a umístění přepínače se doladí později.

---

# 16. Formát a výsledek zápasu

**Rozsah kapitoly:** schopnost definovat formát podle soutěže a kola je Engine invariant. BO5 do 11 o dva body je **Official Run default**, nikoliv povinný formát všech Runů. Individuální zápas bez remízy a význam uložených výsledkových statusů tvoří současný kontrakt Match Enginu.

## 16.1 Výchozí formát

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][MATCH FORMAT CONTRACT]** Oficiální fallback individuálního zápasu je celý atomický formát `BO5 / game do 11 / win by 2`. Není-li pro Tournament Edition nebo její fázi či kolo nastavený povolený override, použije se přímo tento fallback. Pre-alpha pro Match Format nepoužívá skryté mezistupně přes Competition System, Tour, Category, Series ani sezonu.

Formát lze přepsat jako celek pro konkrétní Tournament Edition a její fázi nebo kolo; nejbližší povolený override vítězí. Engine nedědí jednotlivé podčásti odděleně, aby nevznikla nechtěná směs například `BO3` s body či ukončením z jiného formátu. Admin vždy ukáže efektivní formát a jeho přesný zdroj.

**[ROZHODNUTO][ENGINE INVARIANT]** Při materializaci konkrétního zápasu se uloží přesný `Effective Match Format Snapshot` včetně provenance. Do začátku první rally jej lze výslovně opravit s důvodem a Audit Logem. Od první rally je uzamčený; pozdější změna rodičovského nastavení ani běžná editace nesmí přepsat rozehraný nebo historický zápas. Jiná historická varianta vyžaduje branch/regeneraci.

## 16.2 Žádná remíza

**[ROZHODNUTO]** Individuální squashový zápas nikdy nesmí skončit remízou.

Musí mít vítěze nebo skončit některým nenormálním výsledkovým statusem, například:

- retirement/RET během rozehraného zápasu,
- walkover/W/O,
- default,
- diskvalifikace/DQ,
- abandoned/ABN nebo No Contest bez vítěze.

Ani tyto statusy se nepovažují za remízu.

## 16.3 Nenormální výsledky

Základní hranicí je zahájení zápasu, tedy odehrání prvního míčku.

### RET – retirement po zahájení

**[ROZHODNUTO]** `RET` po zahájení zápasu je oficiální odehraný zápas:

- soupeř získá výhru a odstoupivší hráč prohru,
- výsledek se započítá do H2H a zápasové bilance,
- uloží se pouze skutečně odehrané skóre a označení `RET`,
- do setových a míčkových statistik vstoupí pouze skutečně odehrané sety a míčky,
- neodehraný zbytek zápasu se nikdy uměle nedoplňuje.

### W/O – walkover před zahájením

**[ROZHODNUTO]** `W/O` znamená, že zápas vůbec nezačal:

- oprávněný soupeř postoupí v turnaji,
- nevznikne odehraný zápas,
- nikomu se nezapíše zápasová výhra ani prohra,
- nevznikne nový H2H výsledek,
- dosažené kolo, rankingové body a prize money se vyhodnotí odděleně od zápasové bilance podle turnajového postupu.

**[ROZHODNUTO]** Jakmile hráč odehraje první zápas turnaje a potom před dalším zápasem odstoupí, nesmí jej nahradit LL ani rezerva. Jeho následující soupeř postupuje přes W/O.

**[ROZHODNUTO]** W/O je pro turnajový postup plnohodnotné dosažení dalšího kola: postupující hráč získá rankingovou hodnotu a případné prize money podle svého následného skutečně dosaženého finishing stage, přestože samotný W/O nevytvoří zápasovou výhru, prohru ani H2H. Jde o výslovnou výjimku z pravidla, že samotný BYE vyšší rankingovou hodnotu neodemkne.

### DQ – diskvalifikace

**[ROZHODNUTO]** `DQ` po zahájení zápasu je oficiální výhra/prohra a započítá se do H2H i zápasové bilance.

Sportovní výsledek, postup a běžně dosažené body či prize money se nejprve vyhodnotí podle výsledku v pavouku. Samostatná disciplinární policy může diskvalifikovanému hráči body, prize money nebo obojí dodatečně odebrat; přesný katalog a sazby tohoto forfeitu zůstávají odložené.

**[ROZHODNUTO]** `DQ` před zahájením zápasu se pro soupeře a zápasové statistiky chová jako W/O: soupeř postoupí, ale nevznikne odehraný zápas, výhra, prohra ani H2H. Diskvalifikovaný hráč dostane z dané Tournament Edition nula rankingových bodů a nula prize money.

### ABN / No Contest

**[ROZHODNUTO]** Pro skutečně zahájený zápas, který je kvůli vnější příčině bez zavinění hráčů definitivně ukončen bez výsledku, existuje stav `ABN` nebo `No Contest`, například při technické závadě, nebezpečných podmínkách či jiné mimořádné události.

- nemá vítěze ani poraženého a nezapočítá se do H2H ani bilance výher a proher,
- uchová přesné částečné skóre, skutečně odehraný čas, rally log a všechny fyzické následky vzniklé před ukončením,
- dočasně přerušený zápas, který má pokračovat, se vede jako `Suspended`; `ABN` vznikne až po formálním rozhodnutí, že už obnoven nebude,
- ještě nezahájený budoucí zápas nebo prázdný slot zrušeného zbytku turnaje není ABN zápasovým výsledkem a nevstupuje do H2H ani statistik.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Jestli při obnovení suspendovaného zápasu nemůže pokračovat konkrétní hráč kvůli zdraví, použije se `RET`. Neodůvodněné odmítnutí nebo no-show se řeší jako `Default`; ani jedna z těchto hráčských příčin se nesmí vydávat za externí `ABN`.

### Důvody a jejich zadávání

**[ROZHODNUTO]** Každý `RET`, `W/O`, `DQ` a `ABN` má povinnou kategorii důvodu a volitelnou podrobnější poznámku.

Při ručním zadávání v Adminu se kategorie vybírá z kontextové nabídky podle typu výsledku:

- `RET`: zranění, nemoc, fyzická nezpůsobilost, jiné,
- `W/O`: zranění, nemoc, osobní důvod, cestovní nebo vízový problém, nedostavení se, nezpůsobilost ke startu, jiné,
- `DQ`: nesportovní chování, porušení pravidel, manipulace nebo podvod, jiné,
- `ABN`: technická závada, problém kurtu nebo venue, bezpečnostní situace, zásah vyšší moci, jiné.

Základní kódy jsou pevné kvůli konzistentním statistikám. Volba `Jiné` umožní doplnit vlastní textový důvod.

**[ROZHODNUTO]** Viewer standardně ukáže kategorii důvodu. Admin může zobrazit také celou interní poznámku.

**[ROZHODNUTO]** Všechny čtyři stavy může vytvářet automatická simulace i Admin ručně. `RET` a `W/O` mohou nastávat běžněji, zatímco automatické `DQ` a `ABN` budou extrémně vzácné. Jejich pravděpodobnosti budou nastavitelné.

**[ODLOŽENO]** Přesné pravděpodobnosti, jejich vazba na atributy, zdraví a chování hráčů, konkrétní disciplinární forfeity po DQ zahájeného zápasu a přesný vztah technického statusu `default` k DQ. Nulový bodový i finanční výsledek DQ před startem je již rozhodnutý.

## 16.4 Ukládaný detail

**[ROZHODNUTO]** Ukládá se přesné skóre jednotlivých setů.

**[ROZHODNUTO]** Každý skutečně zahájený zápas ukládá celkovou dobu trvání. Autoritativní interní hodnota se ukládá v sekundách; Viewer a Admin ji mohou zobrazit čitelně v minutách, případně v hodinách a minutách.

**[ROZHODNUTO]** U `W/O` je délka zápasu `null`, protože žádný zápas nezačal. `RET`, `DQ` nebo `ABN` po zahájení uchovají pouze skutečně odehraný čas do okamžiku ukončení. Technické týmové W/O se pro individuální délku zápasu chová stejně jako ostatní W/O.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][MATCH LOG CONTRACT]** Před první rally vznikne neměnný `Match Input Snapshot`: oba hráči, jejich autoritativní vstupní stavy, Effective Match Format Snapshot, aktivní gameplany, potřebné sportovní konfigurace a verze modelu i seedů. Každá dokončená rally pak atomicky přidá neměnný `Rally Event`, který obsahuje nejméně:

- výsledek a autoritativní příčinu/řešení rally,
- skóre před a po rally a podávajícího hráče,
- skutečný elapsed time a vzniklé stavové změny,
- rally seed či ekvivalentní reprodukční provenance,
- kompaktní úplný `Post-Rally State Snapshot` potřebný k přesnému obnovení dalšího kroku.

Snapshot vzniká po každé rally. Commit je atomický po rally: pád během výpočtu nedokončené rally ji zahodí a zápas pokračuje z posledního úplného snapshotu, nikdy z napůl zapsaného výsledku.

**[ROZHODNUTO][ENGINE INVARIANT]** Rally Events tvoří ověřitelný hash chain a dokončený zápas ukládá finální `match_log_hash`. `RET`, zahájené `DQ` a `ABN` zachovají všechny skutečně dokončené rally; `W/O` má prázdný rally log. Step Back/Forward i Replay čtou uložené snapshoty a eventy, nikdy kvůli rekonstrukci znovu nespouštějí RNG ani současný simulační model.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá skutečně odehraná rally vytváří kompaktní autoritativní rally záznam. Udržuje odděleně:

- primární terminální trigger — fyzickou nebo pravidlovou událost, která hru ukončila či zastavila,
- pravidlový kontext — pouze fakta potřebná k rozhodnutí daného typu situace,
- oficiální vyřešení — původní a finální call, pokud se liší,
- dopad na skóre — autoritativní seřazené změny skóre nebo replay,
- analytické připsání — `Clean Winner / Forced Error / Unforced Error / Official Award / Neutral Replay`,
- vedlejší incidenty a jejich následky — zejména zdraví, conduct, čas a stav pokračování zápasu.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Přesný minimální katalog primárního terminálního triggeru je `GOOD_RETURN_UNANSWERED`, `SERVE_FAULT`, `RETURN_DOWN`, `RETURN_OUT`, `RETURN_NOT_UP`, `INTERFERENCE_STOP`, `BALL_HIT_PLAYER`, `PROCEDURAL_OR_OFFICIAL_STOP`, `BALL_COURT_OR_EXTERNAL_STOP`, `HEALTH_STOP` a `CONDUCT_STOP`. Konkrétní podtyp uchová například tin uvnitř `RETURN_DOWN`, foot fault uvnitř `SERVE_FAULT`, prasklý míč či mokrý kurt uvnitř `BALL_COURT_OR_EXTERNAL_STOP` nebo druh zdravotního zastavení. `Illegal strike` není souběžný obecný terminální typ: nesprávně zasažený return patří podle pravidel do `RETURN_NOT_UP` a neplatné podání do `SERVE_FAULT`.

Clean winner, forced error a unforced error jsou analytická připsání, nikoliv fyzické mechanismy ani verdikty rozhodčího. Stejný `RETURN_DOWN`, `RETURN_OUT` či `RETURN_NOT_UP` může být vynucený i nevynucený podle obtížnosti reakce, tlaku a předchozího úderu; `GOOD_RETURN_UNANSWERED` může být Clean Winner. `No Let`, `Yes Let` a `Stroke` jsou oficiální vyřešení situace, nikoliv příčina jejího vzniku.

**[ROZHODNUTO][ENGINE INVARIANT]** Rally smí mít jeden primární terminální trigger a současně více vedlejších incidentů. Zranění zjištěné po normálním konci rally neruší již vzniklý sportovní výsledek a conduct udělený po rally může vytvořit další samostatnou změnu skóre. Dopad na skóre se proto neukládá jako jediný vzájemně výlučný enum, ale jako seřazený autoritativní seznam `score_mutations`; běžná rally obsahuje jednu, replay žádnou bodovou a pravidlově dovolený následný Conduct Stroke může přidat další.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Rally záznam dále uchová její délku, odhadovaný počet úderů a aktuální stav všech tří stamina systémů obou hráčů po rally. To umožní pozdější grafy průběhu stamina bez nutnosti ukládat každý úder nebo celý interní mikrostav rally.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Autoritativní časová osa dále ukládá skutečně uplynulou dobu od konce předchozí rally ke kontaktu následujícího podání. Záznam běžné mezery uchová nejméně výslednou délku, role hráčů, zvolené restart intents, dominantní důvod případného prodloužení a jakýkoli prompt či conduct následek. Interní readiness složky lze uchovat pro Replay a diagnostiku, ale délka zápasu používá právě jeden výsledný elapsed interval, nikoliv jejich součet. Každá přestávka mezi gamy je samostatná časová událost se skutečnou délkou; zdravotní událost navíc uchová zdravotní přestávku, její skutečnou délku a následné rozhodnutí `pokračovat / RET`.

Nezaviněné vnější přerušení živé rally ukládá typ `External Interruption`, konkrétní důvod, skutečně uplynulý čas a oficiální vyřešení `Yes Let / replay`; skóre před opakovanou rally zůstává stejné.

**[POZDĚJI]** Nad autoritativním rally logem lze přidávat podrobnější veřejné i Admin statistiky, aniž by první verze musela ukládat shot-by-shot trajektorii.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Délka zápasu vzniká součtem délek rally a všech skutečně uplynulých časových událostí mezi nimi, včetně běžných mezer, přestávek mezi gamy a zdravotních přestávek. Délka a odhad počtu úderů jednotlivé rally vycházejí z jejího skrytého průběhu, nikoliv z dodatečně náhodně připojeného čísla nezávislého na sportovní události.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Délka, odhad úderů a zátěž rally vznikají společně z openingu, 0–24 abstraktních segmentů a terminální fáze podle verzovaného kalibračního profilu; nejsou to nezávislé dodatečné hody. Přesný mechanismus, datové zdroje a současné prozatímní mužské benchmarky vymezuje kapitola 17.8.1.

**[ODLOŽENO]** Přesné finální distribuční křivky, pravděpodobnosti a parametry tempa jednotlivých typů segmentů, finální číselný fit běžných pauz, přesné conduct prahy, matematika objektivních přerušení a jejich číselné vazby na styl, únavu, zranění, formát a ostatní vstupy. Kauzální readiness model běžné mezery, hráčská individualita, taktické zrychlení či zpomalení a zákaz dvojího započtení času jsou již rozhodnuté.

---

# 17. Simulační model a rozsahy simulace

**Rozsah kapitoly:** rozsahy simulace, preview, průběh, přerušení a determinismus jsou schopnosti enginu. Simulace vždy používá právě ty sportovní policy a hodnoty, které jsou uložené v daném Runu a platné v simulovaném bodě historie.

## 17.1 Rozsahy

**[ROZHODNUTO V PRINCIPU]** Admin nabídne mnoho rozsahů simulace, například:

- Simulate Next Match,
- Simulate Next Slot,
- Simulate Next Round,
- Simulate Next Tournament,
- Simulate Next Week,
- Simulate Next Season,
- Full Simulation,
- další předvolby,
- vlastní custom rozsah.

Přesný seznam tlačítek a parametry custom rozsahu se ještě dopracují.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Simulate Next Slot` vyřeší všechny dosud nevyřešené události v nejbližším neuzavřeném slotu. Pokud už uživatel jednotlivě vypočítal některé jeho zápasy, akce dokončí pouze zbývající události a po jejich platném výsledném stavu slot uzavře.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Simulate Next Match` je dělená akce. Běžné kliknutí vypočítá první dosud nevyřešený zápas aktuálního slotu podle stabilního technického pořadí. Vedlejší rozbalovací část ukáže ostatní nevyřešené zápasy stejného globálního slotu bez nesplněné schedule dependency a dovolí zvolit konkrétní zápas. Uživatelské pořadí výběru nesmí změnit vstupy ani pravděpodobnosti ostatních skutečně současných zápasů podle kapitoly 6.6; pozdější zápas v uloženém pořadí jednoho Match Day Slotu nelze přeskočit, pokud potřebuje následky dřívějšího. **[ODLOŽENO]** Přesné stabilní pořadí, názvy ovládacích prvků a jejich detailní layout.

**[ROZHODNUTO]** Tyto rozsahy nejsou podmíněny jedním globálním `Start Run`. Engine dovolí spustit každý rozsah, jehož vlastní vstupy jsou právě validní: od samostatného zápasu prvních vytvořených hráčů až po pozdější rozsáhlé simulace. Čím širší je požadovaný rozsah, tím širší jsou jeho operation-scoped prerequisites.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE CONTRACT]** Prerequisites tvoří hierarchickou matici podle cíle operace. Každá akce ověřuje pouze svůj cílový objekt a jeho skutečné kauzální závislosti; širší akce zdědí prerequisites všech obsažených užších akcí. Známý červený problém uvnitř zvoleného rozsahu zablokuje tuto hromadnou akci, ale nesmí zablokovat užší nezávislou akci, jejíž vlastní vstupy jsou validní.

| Simulační akce | Povinné minimum pro spuštění |
|---|---|
| `Next Rally / Simulate Game / Rest of Match` | rozehraný zápas, přiřazení oba účastníci, platný formát a skóre, současné hráčské a zápasové stavy a uložený model/random state |
| `Next Match` | oba účastníci nebo platně vyřešené feedery, formát, umístění v losu či plánu, současné stavy a všechny schedule dependencies tohoto zápasu |
| `Next Slot` | slot-start prerequisites všech povinných dosud nevyřešených událostí nejbližšího otevřeného globálního slotu |
| `Next Round` | platný field a los, účastníci či feedery, formáty a schedule a všechny povinné zápasy kola |
| `Next Tournament` | platná Tournament Edition, entry/field/draw, schedule, u Ranked Edition úplná potřebná bodová konfigurace a prerequisites všech obsažených zápasů |
| `Next Week` | všechny povinné události současného weeku a celý kontrakt navazujícího Week Transitionu |
| `Next Season / Full Simulation` | progresivní validace: engine ověří právě přicházející horizont a další závislosti až při jejich přiblížení; úplná vzdálená budoucnost nemusí být vyplněná už při startu |
| `Custom` | sjednocení prerequisites všech výslovně vybraných objektů a časového rozsahu |

Příklad: chybějící bodová tabulka budoucího Ranked turnaje zablokuje `Next Tournament`, pokud je součástí cíle, ale nezablokuje ruční simulaci zcela nezávislého platného zápasu. Jde o praktický výchozí kontrakt první pre-alpha verze; po end-to-end testování jej lze vědomě zpřesnit bez návratu ke globální Setup bráně.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Při práci s jedním rozehraným zápasem nabízí Admin tři navazující rozsahy:

- `Simulate Next Rally` vypočítá právě jednu celou rally,
- `Simulate Game` dokončí právě rozehraný game/set,
- `Simulate Rest of Match` dokončí celý zbytek utkání.

Všechny tři navazují na přesný současný stav zápasu a krokový režim je dostupný v běžném Runu i ve vestavěném `Match Test Labu`. Ani při krokovém zobrazení se zápas nesimuluje po jednotlivých úderech.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Před každým `Simulate Game` a `Simulate Rest of Match` vznikne automatický dočasný návratový bod. Pracovní zápas uchovává všechny takové body v lokální časové ose, nikoliv pouze poslední. Admin se může vrátit a nasimulovat jiný průběh; původní cesta zůstane po dobu práce dočasně dostupná pro návrat a porovnání. Přesná retence těchto pracovních alternativ po opuštění nebo potvrzení zápasu zůstává otevřená.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Po každém kroku `Simulate Next Rally` Admin uvidí dostupné interní informace celé rally: vývoj kontroly a tlaku, změny úsilí, terminální incident, oficiální vyřešení, délku, odhad úderů a změny tří stamina barů. Nejde o povinně veřejný Viewer detail.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Auto Play` používá tutéž simulační logiku a mění pouze rychlost zobrazení či automatického postupu, nikdy sportovní pravděpodobnosti ani uložený výsledek. Umí postup rally po rally, rychlé přehrávání a přeskočení k nejbližšímu konci gamu nebo zápasu. Lze jej kdykoliv pozastavit; při běžném rally-by-rally režimu se automaticky zastaví na konci gamu a při zdravotní či jiné mimořádné události. `Step Back / Step Forward` jsou čistě read-only pohyb po uložených Post-Rally State Snapshotech.

**[OTEVŘENO]** Zda a v jakém rozsahu smí Admin před další rally ručně přepsat rozhodnutí hráčské AI, například míru úsilí, a jak se takový zásah liší mezi běžným Runem a Match Test Labem.

## 17.2 Simulace turnaje

**[PROZATÍMNÍ]** Jednotlivé zápasy turnaje se pravděpodobně vypočítají až ve chvíli, kdy na ně přijde řada, nikoliv celý turnaj dopředu.

**[OTEVŘENO]** Přesná hranice předgenerování losu, match packages a výsledků.

## 17.3 Potvrzení a průběh

**[PROZATÍMNÍ]** Před větší simulací se zobrazí rozsah a potvrzení.

**[ROZHODNUTO V PRINCIPU]** Delší simulace probíhá postupně a průběžně načítá svůj stav.

**[ROZHODNUTO]** Dlouhou simulaci lze bezpečně zastavit. Engine nejprve dokončí právě zpracovávaný individuální zápas, potom úlohu ukončí a dosažený stav ponechá jako neuložené změny k prohlédnutí.

**[ROZHODNUTO]** `Pozastavit okamžitě` je odlišná akce od bezpečného zastavení. Výpočet se zmrazí prakticky ihned v nejbližším technicky přerušitelném okamžiku, klidně uprostřed interního výpočtu zápasu, aniž by čekal na jeho dokončení. Částečný zápas se nestane výsledkem ani se nezobrazí ve Vieweru; jeho interní výpočetní stav se uchová pro přesné `Pokračovat`.

**[ROZHODNUTO]** Po dobu okamžitého pozastavení zůstává dotčená simulační branch uzamčená, protože obsahuje nedokončený výpočet. Pokud uživatel z pozastaveného stavu zvolí `Bezpečně zastavit`, engine výpočet obnoví pouze natolik, aby dokončil právě rozpracovaný zápas, a potom úlohu ukončí.

**[ROZHODNUTO]** Admin ukáže živý postup:

- aktuální sezonu a week,
- právě zpracovávaný turnaj, kolo nebo zápas,
- celkový průběh,
- rychlost simulace,
- odhad zbývajícího času,
- průběžný feed důležitých momentů.

Průběžný feed je pohled na právě relevantní momenty simulace, nikoliv náhrada trvalého World Event Logu ani Notification Centeru z kapitoly 25.6.

**[ROZHODNUTO]** Dlouhá simulace má obecnou akci `Naplánovat zastavení`, nikoliv pouze pevnou volbu zastavit po současné sezoně. Uživatel může zvolit podporovaný budoucí bod, například po konkrétním zápase, kole, turnaji, weeku, sezoně nebo jiném konzistentním bodě historie.

**[ROZHODNUTO]** Naplánovaný bod lze před jeho dosažením změnit nebo zrušit. Volba `Bez předčasného zastavení` nechá úlohu doběhnout až do původně zvoleného cíle simulace. Task Center stále ukazuje původní rozsah, případný naplánovaný bod zastavení a právě zpracovávanou část.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Přechod po Season Weeku 61 používá rozhodnutý `Season Transition` z kapitoly 6.8. Simulace pokračuje do Weeku 1 další sezony pouze tehdy, pokud její zvolený rozsah sahá dál a všechny prerequisites přechodu jsou platně uzavřené.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každá operace nebo kauzálně či konfliktně propojená skupina, která společně mění více záznamů, používá vlastní transakční hranici. Engine nejprve vypočítá kandidátní výsledky do staging vrstvy, zvaliduje celý batch a teprve potom jej použije jako celek. Pokud například chyba vznikne až u hráče 431 jednoho společného entry batchu, nesmí z něj v autoritativním stavu zůstat potichu zapsaní hráči 1–430. Nezávislé skupiny téhož Simulation Slotu však podle kapitoly 6.6 smějí commitnout odděleně; chyba jedné již platný nezávislý commit nevrací.

**[PROZATÍMNÍ]** Po simulaci se zobrazí souhrn výsledků. Detail souhrnu se přizpůsobí velikosti simulovaného rozsahu.

**[ROZHODNUTO V PRINCIPU]** Po dokončení je dostupný souhrn důležitých událostí celé simulace.

**[PROZATÍMNÍ SMĚR]** Po dokončení většího rozsahu, například weeku nebo sezony, Admin nabídne neblokující soukromý digest nejdůležitějších výsledků, změn, rekordů, překvapení, oranžových a červených stavů a splněných či ohrožených Future Locks s odkazy na podrobnosti. Digest lze zavřít, později znovu otevřít a bez povinného potvrzení okamžitě pokračovat v další simulaci. Nejde o veřejný Viewer článek.

**[ODLOŽENO]** Přesná definice důležitého momentu, míra podrobnosti feedu a pravidla odhadu času.

**[ODLOŽENO]** Přesný technický formát okamžitě pozastaveného mid-match stavu, latence pozastavení a podporovaná nejjemnější granularita plánovaného zastavení. Funkční rozdíl mezi okamžitým pozastavením, bezpečným zastavením a budoucím plánovaným bodem je rozhodnutý.

## 17.4 Determinismus

**[OTEVŘENO]** Zatím není definitivně rozhodnuto, zda musí stejný seed a totožný stav vždy vyrobit naprosto stejné výsledky.

Tato otázka byla v navazujícím rozhodování dne 5. 8. 2026 výslovně přeskočena. Nesmí se proto považovat za nově uzavřenou ani odvozovat ze souhlasu s determinismem losu nebo Candidate Branch plánování.

Starší dokumentace označovala plný determinismus jako pevné pravidlo. Toto označení se ruší, dokud nebude otázka znovu výslovně rozhodnutá.

Novější prozatímní silný směr v kapitole 22 zavádí užší reprodukovatelnost jednoho konkrétního Forecast vzorku pomocí master seedu, čísla pokusu, totožného vstupního snapshotu a kompatibilní verze modelu. Tím se neuzavírá plný determinismus všech běžných simulací, různých verzí enginu, platforem ani hardwaru. Stejný seed po změně simulačně relevantních dat nebo algoritmu proto sám o sobě negarantuje stejnou historii.

To není v rozporu s užším rozhodnutým kontraktem Candidate Branches: v rámci jedné konkrétní hromadné úlohy, stejné verze enginu a stejných vstupů nesmí pouhá změna pořadí plánování změnit výsledek jednotlivého kandidáta. Širší determinismus napříč verzemi enginu a všemi typy simulace zůstává otevřený.

**[ROZHODNUTO PRO PRVNÍ VERZI – ÚZKÝ RETRY CONTRACT]** Opakování téže neúspěšné operace se stejnými vstupy musí vytvořit stejné kandidátní výsledky. Oprava lokální chyby nesmí bez kauzálního důvodu znovu vylosovat rozhodnutí, která na ni nezávisela; přepočítají se pouze dotčený výsledek a jeho skutečné závislosti. Tento kontrakt chrání opravitelnost batchů a audit, ale sám o sobě stále nerozhoduje plný seed a determinismus všech simulací v celém enginu.

**[ROZHODNUTO PRO LOSOVÁNÍ]** Každá automaticky vytvořená nebo přegenerovaná verze losu má technický `draw_seed`. Stejný draw seed spolu se stejným seznamem účastníků, rankingem, nasazením, typy míst, nastavením turnaje a verzí losovacího algoritmu musí vytvořit totožný los.

Draw seed nemusí být běžně viditelný. Je oddělený od náhodnosti Match Enginu a používá se pro reprodukci, testování a diagnostiku.

## 17.5 Task Center a práce na pozadí

**[ROZHODNUTO]** Dlouhé simulace, importy, exporty a validace se zobrazují v centrálním `Task Centeru` se stavem, průběhem a výsledkem operace.

**[ROZHODNUTO]** Během dlouhé simulace může uživatel:

- používat Viewer,
- prohlížet simulovanou branch v Adminu pouze pro čtení,
- normálně upravovat jiné Runy.

**[ROZHODNUTO]** Po dobu simulace se nesmí měnit její zdrojová branch ani společná data, která právě běžící úloha používá. Viewer tohoto Runu nadále ukazuje poslední uložený stav `Viewer Branch`; rozpracovaná simulace se do něj průběžně nepublikuje.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Bezpečný cílový model používá jemnější zámky: simulovaná branch a skutečně sdílená Runová data jsou zamčená, zatímco jinou nezávislou branch téhož Runu lze prohlížet a upravovat. Dřívější absolutní zámek celého Runu je pouze bezpečný implementační fallback, nikoliv konečný požadovaný UX. Přesná matice branch-local a Run-global mutací ještě není rozhodnutá.

**[ROZHODNUTO V PRINCIPU]** Pokus o konfliktní změnu, například přesun turnaje v právě simulované historii, nikdy nezmění vstupy běžící úlohy. Admin nabídne nejméně vytvoření nové branche z vhodného uloženého bodu před změnou, bezpečné zastavení původní simulace nebo zrušení akce. Nová branch může mít vlastní kalendář a změnu provést bez zásahu do původní simulační historie.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Další pohodlnou možností je uložit konfliktní editaci pouze jako čekající návrh pro provedení po skončení úlohy. Před skutečným použitím se znovu zvaliduje proti novému stavu. Přesné řazení fronty, souběh operací v různých branchích a zacházení se změnou, jejíž vhodný bod už simulace minula, zůstávají otevřené.

**[ROZHODNUTO]** Po dokončení se uvolní zámky zdrojové branche a použitých společných dat a výsledek simulace se v této branchi otevře jako neuložené změny k revizi a případnému ručnímu uložení.

**[ROZHODNUTO]** Pokud uživatel zavírá hlavní okno během dlouhé simulace, zobrazí se tři přesné možnosti:

1. `Pokračovat na pozadí` – okno se zavře, ale lokální engine a úloha pokračují,
2. `Bezpečně zastavit a zavřít` – dokončí se právě zpracovávaný zápas, výsledek se zachová jako Recovery Draft a potom se okno zavře,
3. `Nezavírat` – návrat do aplikace bez změny úlohy.

**[ROZHODNUTO]** Při pokračování na pozadí zůstane engine dostupný přes ikonu v oznamovací oblasti Windows. Ikona ukazuje stav a průběh, dovolí znovu otevřít Task Center a po dokončení zobrazí systémové upozornění. `Ukončit engine` je samostatná akce a při běžící úloze znovu nabídne bezpečné možnosti; zavření hlavního okna samo neznamená ukončení enginu.

**[ROZHODNUTO V PRINCIPU]** Po znovuotevření aplikace se Task Center napojí na stále běžící úlohu nebo ukáže její bezpečně zastavený výsledek. Pád či vypnutí počítače nemůže předstírat pokračování na pozadí: po dalším spuštění se použije poslední bezpečně zachovaný stav a obecný Recovery Draft workflow. Přesná podpora automatického pokračování jednotlivých typů úloh po restartu zůstává odložená.

## 17.6 Plánování Candidate Branches

**[ROZHODNUTO]** Více kandidátních simulací lze spouštět těmito způsoby:

- `Auto` – výchozí režim, engine volí vhodný plán podle hardwaru,
- `Sequential` – vždy se dokončí celý jeden kandidát a potom další,
- `Lockstep by Week` – kandidáti postupují společně po weecích,
- `Lockstep by Season` – kandidáti postupují společně po sezonách.

**[ROZHODNUTO]** Lze zvolit souběžnost `1`, `2`, `4` nebo `Auto`. Kandidáti nad aktuální kapacitu čekají ve frontě.

**[ROZHODNUTO]** Způsob plánování smí měnit pouze pořadí práce, čas a spotřebu prostředků. Při stejném výchozím stavu a stejných seedech musí každý kandidát dát stejný výsledek bez ohledu na zvolený plán.

## 17.7 Podrobnost a výkon simulace

**[ROZHODNUTO V PRINCIPU]** První funkční verze simulace může být výrazně jednodušší. Dlouhodobým cílem je postupně rozšířit Match Engine, vývoj, hráčskou AI a ostatní simulaci do extrémní podrobnosti.

**[ROZHODNUTO][ENGINE INVARIANT]** Každý Run má verzované nastavení úrovně podrobnosti simulace. Zvolená úroveň určuje, které podporované modely a výpočty se v daném Runu skutečně používají; Run si musí uchovat použitý profil i verzi modelu kvůli historii a reprodukovatelnosti.

**[PROZATÍMNÍ SMĚR]** Engine má umožnit snížit podrobnost náročné hromadné simulace a odložit výpočet nepotřebných analytických dat, například některých pravděpodobností, aby dlouhé rozsahy netrvaly zbytečně dlouho.

**[ODLOŽENO]** Přesné profily podrobnosti, jejich názvy, úplná konfigurační hierarchie, hranice povinných a volitelných výpočtů, možnost zpětného dopočtu pravděpodobností, potřebné historické snapshoty modelu a cache. Výslovně zatím není rozhodnuto, zda půjde detail přepisovat také podle Tour, kategorie, Tournament Edition nebo užší úrovně.

## 17.8 Základní kontrakt Match Enginu

**[ROZHODNUTO]** Match Engine simuluje každý konkrétní zápas z relevantních skutečných vstupů obou hráčů. Nevybere vítěze pouhým porovnáním OVR ani rankingu.

**[ROZHODNUTO V PRINCIPU]** Mezi vstupy budou postupně patřit zejména aktuální atributy, forma, únava, zdraví, styl, zvolený gameplan, matchup obou stylů, odhad soupeře, průběžná adaptace a náhoda. První verze může používat menší podmnožinu, ale architektura nesmí předpokládat, že OVR je jedinou sportovní pravdou.

**[ROZHODNUTO]** Výsledek rozhodování hráčské AI a výsledek samotného fyzického zápasu jsou dvě navazující, ale odlišné vrstvy: AI volí podle svého omezeného odhadu, zatímco Match Engine vyhodnocuje skutečný stav a reálné provedení. Správně zvolený gameplan se nemusí podařit provést a špatný odhad může vést k nevhodné taktice.

### 17.8.1 Granularita a průběh rally

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každý zápas se simuluje rally po rally. První verze nesimuluje jednotlivé údery a souřadnice míče, ale jedna rally zároveň není jediný statický náhodný hod.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Interní rally pipeline má čtyři navazující vrstvy:

1. `Rally Setup` — server, strana podání, jednoduchá volba podání, return a počáteční stav,
2. `Control / Pressure Development` — jedna nebo více skrytých změn kontroly, tlaku, úsilí a individuální zátěže,
3. `Terminal Incident` — fyzická událost ukončující nebo přerušující rally,
4. `Official Resolution & Consequences` — oficiální rozhodnutí, dopad na skóre, čas a následný fyzický stav.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Skrytý model kontroly a tlaku používá pět stavů: `strong control A`, `slight control A`, `neutral`, `slight control B` a `strong control B`. Během jedné rally může mezi stavy přejít vícekrát podle schopností, stylů, gameplanů, fyzického stavu, zvoleného úsilí a náhody.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Přechod používá lokální setrvačnost. V běžném segmentu kontrola zůstane ve stejném stavu nebo se posune o jeden stupeň; dvoustupňový posun vyžaduje významný sportovní zlom a přímý obrat `strong control A ↔ strong control B` je pouze vzácná prudká reversal situace. Relevantní atributy, styl, gameplan, únava, fyzické a mentální stavy ovlivňují získání i udržení kontroly, malá náhodnost zachovává variabilitu a žádné pravidlo nevynucuje střídání hráčů. Přesná transition matrix zůstává kalibrací.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Rally má `control_segment_count` v rozsahu `0–24`. Může skončit přímo v Rally Setupu podáním nebo prvním returnem; tehdy má nula control segmentů, ale jeden nebo dva odhadované údery. Pokud opening pokračuje, začínají control segmenty. Běžná rally má převážně `1–10` segmentů, po desátém postupně roste closure pressure a 24. segment je tvrdý technický strop. Na stropu vznikne kontextově vážený terminální incident podle skutečné kontroly, atributů a stavů, nikoliv mechanický hod 50:50. Segment je sportovní fáze s možnou změnou kontroly, ne jeden úder.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Minimální `Rally Setup` zachytí:

- aktuální skóre, servera, service box a právě platná pravidla zápasu,
- skutečně uplynulý čas a recovery od předchozí rally,
- relevantní jednotlivé atributy, Form a Match Sharpness,
- Fatigue, aktivní zdravotní omezení, všechny tři fyzické bary a oba mentální bary,
- styl, matchup, současný gameplan, zvolenou míru úsilí a volbu podání/returnu,
- tlak vyplývající z aktuálního stavu gamu a zápasu,
- identitu/verzi modelu a náhodný stav potřebný pro přesný Replay v rámci podporovaného kontraktu.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Rally Setup` a každý následný abstraktní kontext určují vlastní váženou podmnožinu relevantních jednotlivých atributů ve třech rolích: `Primary` přímo řídí hlavní sportovní úkol, `Supporting` upravuje kvalitu či stabilitu provedení a `Constraint` omezuje dosažitelný výsledek při zjevné slabině. Engine proto v každé rally nepoužívá jeden stejný průměr ani souhrn všech atributů: například připravený útočný drop, obranné vybírání v protažení a dlouhá trpělivá rally aktivují jiné kombinace technických, pohybových, taktických, mentálních, fyzických a kreativních schopností. Aktuální fyzické a mentální stavy se aplikují až na provedení relevantního úkolu. Jeden kauzální vstup ani jeho materializovaný následek se v témže výpočtu nesmí započítat dvakrát. Jde stále o abstraktní rally model, nikoliv shot-by-shot simulaci.

**[ROZHODNUTO][ENGINE INVARIANT]** OVR, ranking, Travel Load ani Financial Level nesmějí do téže rally vstoupit znovu jako obecný přímý bonus, pokud se jejich relevantní vliv už materializoval v konkrétních atributech, Fatigue, Health, přípravě, recovery nebo dynamických barech. Tím se brání dvojímu započítání; výslovně povolený malý Financial Level modifier delší přestávky se aplikuje pouze v recovery procesu podle kapitoly 19.2, ne v samotném sportovním výpočtu každé rally.

**[ROZHODNUTO][ENGINE INVARIANT]** Stav kontroly a tlaku je interní mechanismus rally. Není automaticky veřejnou statistikou, OVR ani `Surprise Score` a nesmí se s těmito vrstvami významově zaměnit.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Každý abstraktní úsek skrytého průběhu vypočítá sportovní vývoj a fyzickou zátěž zvlášť pro každého hráče. Z tohoto společného průběhu potom konzistentně vznikne terminální incident, délka rally, odhad počtu úderů a stav stamina.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `estimated_shot_count`, `active_rally_duration` a individuální workload se nikdy negenerují jako tři nezávislé kosmetické hodnoty. Přímý konec v openingu přidá jeden nebo dva údery; každý další segment společně přidává kontextově vzorkovaný počet úderů, vlastní `Phase Pace`, čas a asymetrickou zátěž a terminální fáze přidá pouze sportovně odpovídající závěr. Rychlá útočná sekvence, trpělivá hloubka, obranné získávání pozice a vyčerpaná pozdní fáze proto mohou mít při stejném počtu úderů jiný čas i workload. Dřívější pracovní představa „obvykle 2–5 úderů na segment“ je pouze implementační aproximace k následnému fitu, nikoliv vědecká konstanta.

**[ROZHODNUTO][ENGINE CONTRACT]** Číselná vrstva používá historicky verzovaný `RallyCalibrationProfile`, nejméně podle podporovaného soutěžního/cohortového profilu a verze modelu. Profil určuje opening-end rate, distribuci úderů a tempa segmentů, closure pressure, koridory mediánu a vyšších percentilů, korelaci úderů s časem a dlouhý pravý ocas. Styl, schopnost zakončení a retrievalu, gameplan, matchup, skóre, únava a ostatní Rally Setup vstupy profil kontextově posouvají; nesmějí však vytvořit druhý nezávislý přepočet po hotové rally.

**[PROZATÍMNÍ KALIBRACE PRE-ALPHA – MUŽSKÝ ELITNÍ PROFIL]** Prvním acceptance koridorem je medián přibližně `11–13` úderů a 75. percentil přibližně `19–23` úderů napříč dostatečně velkým reprezentativním vzorkem. Nejde o cíl každého hráče ani zápasu: [Cross Court Analytics review na konci roku 2023](https://crosscourtanalytics.com/blog/cxvpu622gug21qvzab2v1r1hpsny1a) ukazuje matchupové hráčské průměry zhruba od `13,5` u rychle zakončujících profilů po `20` u nejvytrvalejších profilů. [Novější akademická kontrola publikovaná roku 2023](https://efsupit.ro/images/stories/aprilie2023/Art%20126.pdf) nad 14 mužskými PSA zápasy z let 2018–2020 uvádí průměr `18,6` úderu, `25,1 s` na rally a přibližně `1,34 s` mezi kontakty; kvůli convenience sample a rozdílu průměr versus medián se tato čísla nekopírují jako jedna povinná distribuce.

**[KALIBRAČNÍ PROVENANCE A OMEZENÍ]** [Práce Murray et al. publikovaná roku 2016](https://pubmed.ncbi.nlm.nih.gov/27494689/) s mediánem `13` úderů, 75. percentilem `25`, 95. percentilem `42` a maximem `157` se uchovává jen jako historický benchmark a kontrola dlouhého ocasu, nikoliv jako současný default. [Větší veřejná PSA analytika přibližně 13 000 rally a 200 000 úderů](https://crosscourtanalytics.com/blog/how-long-is-a-typical-squash-rally) podporuje současný medián mužů `11–13` a 75. percentil `19–23`, ale sama upozorňuje na převahu pozdějších turnajových kol. Ve veřejných zdrojích není k v59 úplný oficiální PSA dataset sezony 2025/26 se všemi percentily; 95. percentil proto pre-alpha nezamyká falešně přesným moderním číslem. Extrémy přes 100 úderů zůstávají možné, ale velmi vzácné. Nová kvalitnější data smějí změnit kalibrační profil a jeho verzi, nikoliv historické již odehrané rally.

### 17.8.2 Podání a začátek rally

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Rally Setup` ukládá servera a levou či pravou service box. Hráčská AI volí `safe / normal / aggressive`: safe snižuje fault a opening pressure, aggressive zvyšuje šanci slabého returnu či výjimečného přímého bodu, ale také faultu nebo attackable serve; normal leží mezi nimi. Přesné pravděpodobnosti se kalibrují.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Neexistuje automatický obecný server bonus. `Serve Execution × Return Execution` společně určí opening state; běžně jej posunou nejvýše o jeden stupeň od neutral a silná počáteční kontrola či přímý konec jsou výjimečné. Podání působí jen při openingu. Jakmile vznikne první control segment, nepokračuje žádný skrytý persistentní serve modifier; kauzálně získaná kontrola však může přirozeně přetrvat podle běžné transition logiky. Váha podání tak odpovídá squashi, nikoliv tenisu. Vliv může být větší na slabší úrovni nebo proti mimořádně slabému returnu; přesné trajektorie a podrobné typy podání do pre-alpha nepatří.

### 17.8.3 Terminální příčina a oficiální vyřešení

**[ROZHODNUTO PRO PRVNÍ VERZI]** Konec rally odděluje fyzický terminální mechanismus od vysvětlení, proč nastal. Clean winner, forced error a unforced error jsou kontexty, nikoliv náhrada za mechanismus typu tin/down, out, not up nebo nevrácený platný míč. Oficiální rozhodnutí a dopad na skóre tvoří další samostatné vrstvy podle kapitoly 16.4.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `Terminal Incident` používá katalog a vrstvený Rally Resolution Record z kapitoly 16.4. Běžné míčové konce rozlišují neodpovězený good return, fault podání a return `down / out / not up`; pravidlová zastavení zvlášť rozlišují interference, zásah hráče míčem, procedurální či oficiální stop, míč/kurt/vnější prostředí, zdraví a conduct. Terminální záznam dále nese actor, podporovaný subtype, dostupná fakta o poslední rozhodující situaci a případný terminální shot metadata, aniž by engine ukládal celou shot-by-shot trajektorii. Pravidlovým výchozím podkladem tohoto kontraktu jsou `World Squash Rules of Singles Squash 2025 V1.2.2`, účinné od 1. 9. 2025; rules resolver i použitá ruleset verze jsou historicky verzované, aby budoucí změna pravidel nepřepsala staré zápasy.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Interference se simulují zjednodušeně podle tlaku, pohybu a clearingu a rozhodnutí rozhodčího se považuje za správné:

- `No Let` — nevznikla skutečná interference, míč nebyl hratelný nebo si hráč vytvořil špatnou cestu sám,
- `Yes Let` — vznikla skutečná interference, dobrý return byl možný a soupeř se přiměřeně pokusil uvolnit prostor,
- `Stroke` — soupeř prostor neuvolnil, zablokoval švih nebo zabránil pravděpodobnému vítěznému úderu.

Minimální pravidlový kontext interference umí rozlišit omezení výhledu, přístupu k míči, prostoru pro rozumný švih a svobody hrát na přední stěnu; možnost `good return / winning return`, clearing effort, striker effort a path, minimal interference, pokračování po interferenci, excessive swing, turning a first/further attempt. Nejde o souřadnicovou simulaci: tyto hodnoty jsou diskrétní interní fakta vytvořená z abstraktní situace a finální verdikt z nich určí verzovaný rules resolver.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI][ENGINE INVARIANT]** Engine nejprve vytvoří pravdivá situační fakta nezávislá na verdiktu a potom z jejich kombinace a historicky platné verze pravidel deterministicky odvodí správný bod, `No Let`, `Yes Let` nebo `Stroke`. Pre-alpha nepřidává náhodnou chybu rozhodčího, takže `initial_official_call = final_official_call`; pole zůstávají oddělená kvůli budoucímu rozšíření. Pozdější model smí mezi ground truth a finální call vložit referee perception, omylný initial call, review a corrected final call, ale nesmí zpětně změnit samotnou sportovní pravdu situace.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** `BALL_HIT_PLAYER` se neodkládá celý do pokročilé verze. Minimální rules resolver zná, koho a v jaké fázi míč zasáhl, zda by return byl good či winning, zda mířil přímo na přední stěnu nebo nejprve na jinou stěnu, zda šlo o first/further attempt, turning a případné úmyslné zachycení. Tato malá sada flagů stačí k výběru podporovaného bodu, Letu nebo Stroke bez modelování přesné trajektorie.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Nezaviněný vnější incident, který zasáhne právě probíhající rally, se vyřeší jako `External Interruption → Yes Let`: nikdo nezíská bod, rally se ze stejného skóre zopakuje a autoritativní log uloží důvod přerušení. Pokud incident nastane až po řádném skončení rally, již získaný bod zůstává. Událost způsobená hráčem se neposuzuje automaticky jako vnější přerušení, ale podle příslušných pravidel hráče, interference nebo conduct.

**[OTEVŘENO, VÝSLOVNĚ PŘESKOČENO]** Přesná hranice, po které vnější incident přestane být pouze krátkým přerušením s Yes Let a vytvoří stav `Suspended`, včetně časového prahu a navazujícího workflow. Základ Yes Let, nulový bod a replay rally se tím znovu neotevírají.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Běžná mezera se měří od konce předchozí rally po kontakt následujícího podání. Engine nejprve vytvoří čtyři kauzální časy připravenosti a další rally může začít až v jejich maximu:

`next_serve_contact = max(server_ready, receiver_ready, official_ready, court_ready)`

`server_ready` a `receiver_ready` zohledňují délku a individuální workload předchozí rally, aktuální fyzický a zdravotní stav, mentální reset, přesun do service boxu nebo return position, přirozenou hráčskou tendenci, aktuální taktický záměr a malou reprodukovatelnou variabilitu. `official_ready` a `court_ready` zachycují pouze skutečné procedurální či objektivní překážky. Složky se nesčítají: skutečný elapsed čas je jejich překryté maximum a stejnou dobu získají oba hráči jako svou individuálně účinnou recovery právě jednou.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Každý hráč má odvozený `Between-Rally Restart Profile` se zvláštní tendencí při podání a při returnu. Nejde o 58. schopnostní atribut ani o trvalý výkonový bonus: je to stabilnější behaviorální preference odvozená z hráčovy individuality, relevantních mentálních a taktických atributů, Natural Style Profile a reprodukovatelného individuálního variation seedu. Vnitřní `Tempo` během rally zůstává jinou osou. Rychlý hráč může chodit podávat téměř okamžitě, pomalejší hráč si přirozeně bere více času a tentýž hráč se může jako server chovat jinak než jako receiver.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Před každou další rally hráčská AI volí role-specific `restart_intent = accelerate / natural / delay`. Může zrychlit, aby soupeři omezila recovery a mentální reset, udržela vlastní momentum nebo zatlačila na hráče, který nemá rád rychlé navázání. Může zpomalit kvůli vlastní recovery, uklidnění, změně rytmu, přerušení soupeřova momenta nebo jako součást gameplanu. Volba vychází z nedokonalého odhadu vlastní i soupeřovy únavy, jejich restartových preferencí, předchozí rally, skóre a důležitosti bodu, mentálního stavu, dosavadního vzorce, gameplanu a již obdržených promptů či postihů. Může být dobrá, špatná nebo se nepodařit; soupeř ze stejné delší pauzy také odpočívá a rychlý restart může unavenému iniciátorovi uškodit.

**[ROZHODNUTO][ENGINE INVARIANT]** Restart intent nevytváří magický přímý bonus k příští rally. Jeho účinek vede pouze přes skutečně uplynulou recovery, připravenost, nedokonalé provedení a malý krátkodobý `restart pressure / rhythm disruption` kontext. Ten závisí na rozdílu mezi skutečným tempem a očekáváním soupeře, jeho adaptabilitě, Focus, Composure, Self Control a opakování vzorce; není garantovaný, časem slábne a nesmí podruhé započítat tutéž recovery nebo tentýž atribut.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** Přirozeně delší zotavení po mimořádně dramatické či fyzicky náročné rally se odlišuje od bezdůvodného taktického zdržování. Zjednodušený verzovaný tempo/conduct resolver vyhodnotí pozorovatelnou přiměřenost doby, objektivní důvody a dosavadní zásahy; nečte hráči tajně myšlenky. Minimální eskalace podporuje `bez zásahu → prompt k pokračování → Conduct Warning → při pokračujícím či opakovaném porušení Conduct Stroke` přes již existující conduct a `score_mutations` rámec. Pre-alpha nadále nemá náhodné chyby ani individuální profily rozhodčích; jemná subjektivita, rozdílná přísnost a úplná vyšší conduct eskalace patří do pozdější verze.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Review, vysoušení či čištění kurtu, problém s míčem, zdravotní přestávka a delší procedurální vysvětlování jsou samostatné autoritativní časové události. Jejich skutečný čas již hráčům poskytuje recovery a readiness; po jejich skončení se automaticky nepřipočte celá nová běžná mezera. Hráči mají být připraveni navázat bez zbytečného dalšího zdržení.

**[PROZATÍMNÍ KALIBRACE PRE-ALPHA – MUŽSKÝ ELITNÍ PROFIL]** Napříč reprezentativním vzorkem mají běžné mezery bez samostatné dlouhé události ležet převážně přibližně v `8–18 s` s průměrem kolem `13 s`. Velmi rychlé navázání po krátké rally a zrychlujícím intentu může být přibližně `5–9 s`; přirozený reset po mimořádně náročné rally přibližně `15–25 s`. Interval přes `30 s` obvykle vyžaduje konkrétní objektivní událost nebo vyvolá posouzení možného time-wastingu, nejde však o globální tvrdý fyzikální cap. Jde o verzovaný acceptance profil určený k rekalibraci nad většími současnými daty, nikoliv o povinných třináct sekund po každé rally.

**[KALIBRAČNÍ PROVENANCE A OMEZENÍ]** Veřejná observační analýza 20 gamů, 7 mužských profesionálních zápasů a 392 intervalů uvádí průměr běžného inter-rally intervalu přibližně `13 s`; intervaly delší než 30 sekund kvůli review či čištění kurtu ze vzorku vyloučila, takže nedokládá celý pravý ocas ani univerzální limit. Současná `PSA Squash Tour – WSO Directive 2025/26` neukládá jeden pevný počet sekund pro každou rally: vyžaduje prompt readiness, výslovně rozlišuje přirozený čas po dramatické rally od taktického zdržování a mezi příklady time-wastingu uvádí opožděné podání, pomalou chůzi, nadměrné odrážení míčku či zbytečné diskuse. Čísla výše jsou proto pracovní kalibrací, zatímco kauzální a pravidlová struktura je závazný pre-alpha kontrakt.

**[POZDĚJŠÍ POKROČILÁ VERZE]** Chyby rozhodčích, individuální referee profily a jejich rozdílná přísnost či konzistence, detailní video review, sporné video verdikty, úplná vyšší conduct eskalace, přesné trajektorie a jemnější úsudek o úmyslu, nebezpečnosti či clearingu nad minimálními pre-alpha flagy.

**[ODLOŽENO]** Přesná transition matrix, číselné vazby atributů, stylů, gameplanů a stamina na skryté stavy, podoba růstu closure pressure po desátém segmentu, pravděpodobnosti jednotlivých terminálních triggerů a jejich subtypů, per-segment sampling, finální parametry RallyCalibrationProfile, restartových distribucí a conduct thresholds, analytické připsání i interference. Rally-by-rally granularita, čtyřvrstvá pipeline, pět setrvačných stavů kontroly, rozsah `0–24` segmentů, kontextové role atributů, pouze úvodní účinek podání, kauzální a taktické tempo mezi rally, deterministický rules resolver, terminální katalog a oddělení výsledkových vrstev jsou již rozhodnuté.

### 17.8.4 Zdravotní a časové události

**[ROZHODNUTO PRO PRVNÍ VERZI]** Match Engine mezi rally zpracuje také podporované zdravotní přestávky a přestávky mezi gamy. Stamina recovery vždy vychází ze skutečně uplynulého času a nikdy neprovádí reset. Zdravotní rozhodování a jeho statusy popisuje kapitola 11.5; autoritativní časové a zdravotní záznamy kapitola 16.4.

## 17.9 Match Reconstruction ručně zadaného výsledku

**[ROZHODNUTO PRO PRVNÍ VERZI]** Ručně zadávaný zápas používá `Match Reconstruction`. Adminem zadaná fakta, například vítěz, výsledek nebo přesné skóre gamů, se stanou závaznými constraints. Engine nad nimi vytvoří více úplných validních průběhů zápasu místo jediného hrubého dopočtu pouze z výsledku.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Počet kandidátů není pevný a Admin jej nastaví pro každou rekonstrukci. Všechny kandidáty musí splnit uzamčená fakta, ale mohou se lišit délkou, průběhem rally, kvalitou výkonu obou hráčů, stamina a dalšími neuzamčenými podporovanými událostmi.

**[ROZHODNUTO][ENGINE INVARIANT]** Nevybrané kandidáty jsou pouze preview a nesmějí změnit formu, stamina, zdraví, statistiky ani historii. Teprve výslovná akce `Vybrat tuto rekonstrukci` zapíše jediný zvolený kandidát jako autoritativní zápasový průběh a všechny následky se odvodí právě z něj.

**[ROZHODNUTO PRO PRVNÍ VERZI]** `Constraint Builder` dovoluje kombinovat velké množství podporovaných podmínek jako přesné hodnoty, rozsahy, minima a maxima. Vedle vítěze, výsledku a skóre lze omezovat například celkovou délku zápasu nebo rozsah formy či výkonu hráče. Přesný úplný katalog proměnných zůstává otevřený.

**[ROZHODNUTO PRO PRVNÍ VERZI]** U formy Builder významově odděluje vstupní `Pre-match Form`, dosažený `Match Performance` a odvozenou `Post-match Form`. První dvě vrstvy lze omezovat samostatně; `Post-match Form` se standardně dopočítá až z vybrané rekonstrukce podle kapitoly 11.5.

**[ROZHODNUTO]** Constraint Builder před generováním společně zvaliduje všechny podmínky a používá globální systém závažnosti z kapitoly 25.6: podle závažnosti zobrazí oranžový nebo červený vykřičník a vysvětlí příčinu, dopad a možnosti opravy; červený stav zablokuje pouze dotčenou operaci. Přesné prahy a zařazení extrémně nepravděpodobných či výpočetně náročných zadání nejsou pevně rozhodnuté.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Všech X kandidátů se nejprve zobrazí společně v kompaktním přehledu. Každý lze rozkliknout do úplného read-only Admin detailu se všemi dostupnými interními údaji, zejména rally logem, časovou osou, stamina, formou, zdravotními událostmi a rozhodnutími; otevření detailu samo nic necommitne.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Seznam kandidátů lze řadit. Výchozí pořadí je pořadí jejich nalezení; podporované alternativy mohou zahrnout odhadovanou pravděpodobnost, `α`, délku nebo výkon hráčů. Úplný katalog řadicích polí a dostupnost statistických řazení podle množství provedených pokusů zůstávají otevřené.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Simulačně významná ruční změna kandidáta nesmí potichu přepsat jeho již vygenerovaný průběh. Změněná hodnota se stane novou constraint a nový konzistentní kandidát se vygeneruje až po výslovném spuštění tlačítkem, nikoliv automaticky po každém úhozu. Původní kandidáti zůstanou v dočasné historii pro porovnání a návrat až do potvrzení zápasu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Po potvrzení zápasu se jako autoritativní historie zachová pouze vybraný kandidát. Ostatní kandidáti se zahodí, pokud je Admin předtím výslovně neuložil podporovanou samostatnou akcí; samotné preview nikdy nevytváří následky.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Hledání může pokračovat, dokud nenajde požadovaných X kandidátů. Pokud trvá příliš dlouho nebo se nedaří množinu naplnit, zobrazí průběžný stav a odpovídající vykřičníky a Admin si vybere mezi třemi cestami: cíleně vynutit vyhovující průběh, hledat nejbližší kandidáty s viditelnými odchylkami nebo změnit constraints. Existence vynucujícího režimu je rozhodnutá, ale jeho přesný princip, omezení, provenance a vztah k přirozené pravděpodobnosti zůstávají otevřené. Stejně otevřené zůstává případné rozlišení povinných a preferovaných constraints.

**[ROZHODNUTO V PRINCIPU]** Pravděpodobnostní výstupy významově oddělují:

- `p` — přirozenou pravděpodobnost či četnost události,
- `δ` na škále `−1 až +1` — směr a vzdálenost výsledku vůči nejpravděpodobnější nebo typické oblasti distribuce,
- `α` na škále `0 až 1` — velikost této vzdálenosti bez směru, v současném konceptu protějšek velikosti `δ`, nikoliv jiné jméno pro `p`.

Referenční distribuce vzniká ze simulací a nesmí být uměle nucena do Gaussovy křivky. Přesný výpočet, normalizace a kalibrace `δ` a `α`, jejich vztah ve více rozměrech a chování u více stejně typických vrcholů zůstávají otevřené a budou se rozsáhle testovat.

**[PROZATÍMNÍ]** Při prvním použití je pracovním výchozím počtem deset kandidátů. Hodnota deset není pevné produktové pravidlo a po testování se může změnit.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Po prvním použití si engine pamatuje poslední zvolený počet kandidátů jako uživatelskou výchozí hodnotu; před každou rekonstrukcí jej lze znovu změnit.

**[SMĚR]** Nad stejným `Constraint Setem` se pracovně oddělují akce `Validate Constraints`, `Calculate Probability` a `Generate Matching Scenarios`. Pravděpodobnost může ukazovat výskyty `k/N`, odhad 0–1, nejistotu a případně samostatnou vzácnost; nulový nález nemá být vydáván za důkaz nulové pravděpodobnosti. Počet simulací ani hranice jedné miliardy nejsou pevné a extrémně vzácné případy mohou později využít transparentně označený `Rare Event Accelerator`. Celá tato statistická architektura, včetně přesných hranic oranžové a červené, je pouze běžným směrem.

**[SMĚR]** Bezpečné předčasné ukončení pokusu, který už nevratně porušil constraint, může šetřit výpočet a přitom se neúspěšný pokus stále započítat do jmenovatele přirozené pravděpodobnosti. Úplné dokončování všech nevyhovujících zápasů může zůstat diagnostickým nebo distribučním režimem. Konkrétní architektura probability, candidate a landscape passů nebyla výslovně uzavřena.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Trvalá `Reconstruction Session` uchovávající rozpracované generování a kandidáty po zavření okna není požadavkem první verze. Má smysl pouze tehdy, pokud půjde potřebné kandidáty nebo jejich reprodukční data uchovat úsporně bez významné datové režie.

**[SMĚR]** Přesný obsah kompaktní karty kandidáta se rozhodne později. Pracovní souhrn může ukazovat výsledek a skóre gamů, délku, `Match Performance` obou hráčů, počet rally, konečnou stamina a nejdůležitější mimořádnou událost; tento seznam není pevný.

**[OTEVŘENO]** Úplný katalog constraints, jejich kombinace, hard/preferred statusy a validace, algoritmus hledání, vynucování, nearest-distance a rozmanitosti kandidátů, výkonové rozpočty a warning prahy, přesný probability model, naturalness/provenance, standardní hodnoty, batch workflow, retence preview a pracovních alternativ a konečné Admin UI. Rozhodnutý je základ rekonstrukce, nastavitelný počet, významové oddělení formy, řaditelný kompaktní přehled, úplný read-only detail, nový kandidát po významové editaci, tři řešení neúspěšného hledání a commit pouze vybraného kandidáta.

---

# 18. Rankingy

**Rozsah kapitoly:** engine poskytuje Official/Live Ranking, historické snapshoty a konfigurovatelné sezonní rankingové policy. Best N je samostatnou hodnotou každé sezony: první sezona Official Runu začíná s Best 15 a další sezona výchozím způsobem převezme efektivní hodnotu předchozí sezony. Platnost 61 weeků, PR hodnoty a další konkrétní sportovní parametry jsou rovněž **Official Run defaulty**, nikoliv globální konstanty všech Runů.

## 18.1 MSA Official Ranking

**[ROZHODNUTO]** MSA ranking se aktualizuje každý týden.

**[ROZHODNUTO]** Po každém dokončeném weeku vznikne při Week Transitionu nový oficiální rankingový snapshot označený následujícím weekem, i když se pořadí ani body vůbec nezměnily.

**[ROZHODNUTO]** Bodová hodnota turnajového výsledku se stane autoritativním rankingovým vstupem až po dokončení celého turnaje nebo po jeho formálním terminálním uzavření jako `Abandoned`. Pouhé dočasné `Suspended` ji neaktivuje.

Do oficiálních bodů a pořadí se tento vstup materializuje až v následujícím weeku po dokončení nebo terminálním uzavření turnaje. Pokud například turnaj skončí ve Weeku 20, jeho body se poprvé objeví v Official Ranking snapshotu Weeku 21; neexistuje samostatný mezilehlý rankingový stav s již připsanými body.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Technicky se tato změna provede při samostatném `Week Transition 20 → 21`: aktivují se nově splatné turnajové výsledky a vznikne Official Ranking označený jako Week 21 ještě před prvním interním slotem tohoto weeku. Nejde o událost vloženou do některého zápasového či přihlašovacího slotu.

**[ROZHODNUTO][ENGINE INVARIANT]** Vypočtené rankingové body, pořadí a již existující Official Ranking snapshoty jsou přímo read-only. Admin může jako přímý rankingový vstup zadat disciplinární událost; jiné opravy musí změnit autoritativní zdrojové výsledky, jejich status, bodovou policy nebo jinou skutečnou příčinu a potom ranking znovu vypočítat.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Pozdě zadaná korekční či disciplinární událost potichu nepřepíše dříve publikovaný Official Ranking. Projeví se v nejbližším novém snapshotu podle svého effective weeku. Má-li historie vypadat, jako by chyba nikdy nevznikla, musí Admin použít branch nebo regeneraci od bodu před chybným snapshotem.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Tournament Edition má rankingový status `Ranked` nebo `Unranked`:

- `Ranked` Edition používá úplnou předem zveřejněnou bodovou tabulku a její výsledek může vstoupit do Official MSA Rankingu a Best N,
- `Unranked` Edition nepřidělí žádné MSA rankingové body a do Best N nevstoupí, ale její zápasy a všechny ostatní sportovní následky zůstávají plnohodnotné,
- běžná Edition vzniká jako Ranked a Admin ji musí výslovně označit Unranked; bodová kategorie status neurčuje,
- konkrétní typ soutěže může být v Package přednastaven jako `Unranked Only` a potom jej žádná Edition nesmí změnit na Ranked; ostatní typy používají běžný Ranked default a Edition-level změny podle kapitoly 13.8.

**[ROZHODNUTO]** Unranked zápas nadále ovlivní stamina, fatigue, health/injuries, formu a development a zapíše se do titulů, historie, statistik, rekordů a H2H. Hráčská AI u něj počítá s nulovým bodovým přínosem, ale může jej zvolit kvůli prestiži, prize money, titulu, reprezentaci nebo jiné motivaci.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Mimořádné odebrání Ranked statusu po dokončení turnaje nepřepisuje historické rankingové snapshoty ani tehdejší rozhodování. Od účinného bodu rozhodnutí se jeho body nepoužijí v nových Official Ranking výpočtech a nový snapshot transparentně zachytí jejich odstranění.

**[ROZHODNUTO PRO PRVNÍ VERZI]** U formálně `Abandoned` Ranked Edition získá každý hráč pouze nejvyšší bodovou hodnotu, kterou před ukončením skutečně odemkl podle běžného win/BYE/W/O kontraktu. Bez platně dokončeného finále nikdo automaticky nezíská champion points, a to ani tehdy, pokud FAX samostatně přizná mimořádný titul.

**[ROZHODNUTO]** Kvalifikace a Main Draw jedné Ranked Edition tvoří jeden společný turnajový výsledek a zabírají právě jedno místo v limitu Best N. Výsledek může obsahovat dvě aditivní složky:

1. jednu kvalifikační bodovou hodnotu podle konečného dosaženého kvalifikačního výsledku,
2. jednu Main Draw bodovou hodnotu podle konečného dosaženého Main Draw výsledku.

Body se nepřičítají za každou jednotlivou výhru nebo kolo. Uvnitř každé složky se použije právě jedna hodnota nejvzdálenějšího platně dosaženého stage; teprve Q a Main Draw složka se mezi sebou sečtou.

**[ROZHODNUTO]** Úspěšný kvalifikant i lucky loser si k Main Draw složce přičtou svou skutečně získanou kvalifikační složku. Hodnota `Qualified` musí být vyšší než kvalifikační hodnota hráče, který kvalifikaci prohrál a následně vstoupil jako LL. Hráč vyřazený v kvalifikaci má pouze jednu Q složku bez Main Draw složky.

**[ROZHODNUTO]** BYE ani pozdní vložení náhradníka přímo do vyššího kola samy vyšší bodovou hodnotu v Qualification nebo Main Draw neodemknou. Prohra nebo RET v prvním skutečně zahájeném zápase proto znamená hodnotu prvního kola příslušné draw složky bez ohledu na to, v kterém fyzickém kole hráč začal. Výhra prvního skutečného zápasu odemkne další hodnoty podle konečného výsledku. W/O postup je samostatnou rozhodnutou výjimkou kapitoly 16.3.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Zveřejněnou bodovou tabulku Ranked Edition používá hráčská AI při porovnávání turnajových možností. Chybějící nebo neúplná tabulka proto drží Edition pouze jako neveřejný Admin Draft; prize money tuto rankingovou publikační podmínku v první verzi nenahrazují ani neblokují.

**[ODLOŽENO]** Přesné číselné bodové tabulky jednotlivých kategorií, sezon, kvalifikačních stages a Main Draw kol. Aditivní struktura, jedna hodnota za každou draw složku, vyšší hodnota úspěšného kvalifikanta než LL a BYE unlock jsou již rozhodnuté.

## 18.2 Platnost a počet výsledků

**[ROZHODNUTO]** Každý turnaj má výchozí platnost bodů 61 weeků, tedy jeden squashový rok. Platnost se počítá od prvního weeku, ve kterém se body objeví v oficiálním rankingu.

Admin může tuto hodnotu u konkrétního turnaje ručně změnit. Jde o výjimečný override očekávaný přibližně u 0,1 % turnajů; engine na odchylku od 61 weeků výrazně upozorní, ale dovolí ji uložit.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** První sezona Official Runu má výchozí `Best 15`: do rankingu se započítá nejvýše 15 nejlepších aktuálně platných turnajových výsledků hráče. Nejde o pevnou globální hodnotu enginu ani o hodnotu vnucenou všem sezonám.

**[ROZHODNUTO]** Každá další sezona jako svůj počáteční výchozí návrh převezme efektivní Best N bezprostředně předchozí sezony. Admin může Best N nové sezony samostatně změnit a historické rankingové snapshoty si uchovávají skutečně použitou časově platnou Ranking Policy.

**[ROZHODNUTO]** Žádný turnaj se nezapočítává povinně. Vždy se vyberou platné výsledky s nejvyšším počtem bodů.

**[ROZHODNUTO]** Výjimkou z běžného výběru turnajových výsledků je `Disciplinary Zero`: povinná dočasná nulová rankingová položka, která po dobu `X` weeků zabírá právě jedno místo v Best N. `X` určuje závažnost provinění a Admin může výslednou délku ručně změnit. Po uplynutí vlastní doby nula automaticky zmizí a není navázaná na 61weekovou platnost výsledku konkrétního turnaje.

**[ROZHODNUTO]** Více Disciplinary Zeros se skládá nezávisle. Každá zabírá vlastní místo v Best N, má vlastní effective/expiry dobu a opakované provinění se proto neztratí uvnitř jediné již aktivní nuly. Přesný okamžik účinnosti, délky podle provinění a vztah k samostatnému odečtu bodů jsou otevřenou disciplinární policy.

**[ROZHODNUTO]** Každá sezona má vlastní upravitelná pravidla výpočtu rankingu, včetně hodnoty Best N. Pravidlo lze změnit také během probíhající sezony, ale Admin zobrazí varování a dopady změny.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Změna Best N v sezoně se pracovně propíše do všech ještě budoucích sezon, které tuto hodnotu pouze dědí; výslovné sezonní overrides zůstanou chráněné. Přesný okamžik materializace, impact preview a chování již připravených budoucích plánů ještě nejsou pevně rozhodnuté.

Při takové změně jsou možné dvě varianty:

1. **Od zvoleného weeku dál** – starší oficiální snapshoty zůstanou zachované a nové pravidlo se použije od určeného bodu.
2. **Zpětně od začátku sezony nebo jiného minulého bodu** – engine určí první dotčený stav a ukáže dopady na rankingové snapshoty, přihlášky, nasazení, losy, turnaje, statistiky a další navazující data.

Zpětná změna používá obecný workflow změny minulosti z kapitoly 7.4: nabídne vytvoření nové branche nebo odstranění a přegenerování budoucnosti současné branche od prvního dotčeného bodu. Nová branch je doporučená, nikoliv povinná.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Official MSA Ranking nepoužívá sdílené pořadí. I hráči se stejným součtem bodů mají vždy jedinečnou oficiální pozici; stejný počet bodů se normálně zobrazí, ale pořadí rozhodne tie-break.

Výchozí tie-break se použije postupně v tomto pořadí:

1. porovnají se bodové hodnoty všech započítávaných výsledků v aktuálním Best N, seřazené od nejvyšší k nejnižší; rozhodne první rozdílná hodnota,
2. pokud je celá skladba započítávaných bodových výsledků totožná, porovná se jejich profil stáří a přednost má hráč s novější rozhodnou skladbou výsledků,
3. pokud shoda trvá, přednost má lepší pozice v bezprostředně předchozím Official MSA Ranking snapshotu,
4. pokud neexistuje ani předchozí rozhodující pořadí nebo je stále shoda, rozhodne stabilní uložený reprodukovatelný tie-break token; nejde o nový náhodný hod při každém zobrazení.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** U hráčů s nulou bodů se třetí vrstva vykládá doslovně: dříve klasifikovaný nulový hráč stojí před prvním novým Tour Playerem bez předchozí pozice. Pokud žádný ze shodných nových hráčů předchozí pozici nemá, rozhodne jejich již uložený stabilní rankingový tie-break token. Samotné technické pořadí vložení do databáze pořadí nikdy neurčuje.

**[ROZHODNUTO][ENGINE INVARIANT]** Rankingový tie-break je součástí verzované sezonní Ranking Policy. Každý snapshot uchová výsledné jedinečné pořadí i informaci o použité policy; pozdější změna tie-breaku nesmí potichu přepsat historii.

**[CÍLOVÁ FUNKCE]** Viewer nebo Admin může u shodných bodů vysvětlit rozhodující tie-break vrstvu, aby bylo pořadí auditovatelné.

## 18.3 Zobrazení hráčů

**[ROZHODNUTO]** V oficiálním rankingu jsou všichni hráči, kteří už vstoupili na Tour a nejsou `retired`, včetně aktivních či `Inactive` hráčů s 0 body.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Samostatný juniorský ranking nyní nebude. Může být přidán až v některé vzdálené budoucí verzi.

**[ROZHODNUTO]** V MSA rankingu lze podle běžných MSA bodů filtrovat hráče juniorského věku, kteří už vstoupili na Tour. Pre-Tour prospecti se zobrazují v samostatné juniorské/prospect sekci a toto pravidlo je do MSA rankingu nevkládá.

**[ROZHODNUTO]** Retired hráč už v aktuálním oficiálním MSA rankingu není. Historická rankingová data a profil mu zůstávají.

**[ROZHODNUTO V PRINCIPU]** Hráč, jehož poslední turnaj je starý alespoň 30 weeků, bude v rankingových seznamech vizuálně odlišený, například jinou barvou jména, ikonou nebo tooltipem. Přesný vzhled se rozhodne až s celkovým designem.

Toto zvýraznění je pouze informace o době od posledního turnaje. Automaticky nepřiděluje status `Inactive`; ten se řídí skutečným lifecycle rozhodnutím podle kapitoly 12.4.

**[ROZHODNUTO V PRINCIPU]** Má-li hráč aktivní Protected Ranking, lze jej zobrazit vedle skutečného pořadí v závorce, například `180. Linus Becker (PR 14)`. Samotné pořadí `180.` zůstává jeho jediným skutečným Official Rankingem.

## 18.4 Protected Ranking

Protected Ranking (`PR`) je oddělená dočasná vstupní hodnota. Nepřidává hráči body, nepřepisuje jeho skutečné pořadí a nevkládá jej na falešné místo do Official Rankingu.

### 18.4.1 Nárok a započítávání absence

**[ROZHODNUTO V PRINCIPU]** Nárok může vzniknout pouze z důvodu, při kterém hráč reálně neměl rozumnou možnost soutěžit. Patří sem zejména zranění, doložená nemoc, válka, povinná státní či vojenská služba nebo jiná schválená závažná nedobrovolná překážka.

Dobrovolná neaktivita, dobrovolný retirement, taktická pauza ani disciplinární či dopingová suspendace nárok nevytvářejí.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Výchozí minimum pro získání PR je 30 započitatelných weeků nedobrovolné absence. Jde o hodnotu v sezonní `Protected Ranking Policy`, nikoliv o globální konstantu enginu.

**[ROZHODNUTO]** Do minima se počítají pouze weeky, ve kterých hráč kvůli uznané překážce skutečně nemohl hrát.

**[ROZHODNUTO]** Absence nemusí být naprosto souvislá. Výjimečný neúspěšný pokus o návrat může ochranný případ přerušit, aniž by smazal dříve nasbírané weeky. Weeky, ve kterých hráč pokus o návrat absolvoval, se do absence nezapočítají. Toto pravidlo je určeno pro skutečné pokračování nebo bezprostřední návrat stejné překážky, nikoliv pro běžné střídání hraní a dobrovolných pauz.

**[ODLOŽENO]** Přesná taxonomie a dokazování způsobilých důvodů, maximální počet neúspěšných návratů a nejdelší povolená mezera mezi částmi téhož případu.

### 18.4.2 Sezonní Protected Ranking Policy a PR Case

**[ROZHODNUTO][ENGINE INVARIANT]** Každá sezona má vlastní upravitelnou `Protected Ranking Policy`, obdobně jako sezonní Best N. Může obsahovat zejména:

- minimální počet započitatelných weeků,
- délku a typ výpočtového okna,
- korekci a zaokrouhlení výsledné hodnoty,
- počet použití podle délky absence,
- použití pro entry, seeding a další turnajové účely,
- lhůtu pro aktivaci, expiraci po návratu a omezení podle kategorií turnajů,
- pravidla spotřeby použití, tie-breaků a vztahu ke skutečnému rankingu.

**[ROZHODNUTO]** Na začátku uznané absence vznikne interní `PR Case`, i když hráč ještě nesplnil minimum pro skutečné získání PR.

**[ROZHODNUTO]** `PR Case` si při svém vzniku uloží úplný snapshot tehdy platné sezonní Protected Ranking Policy. Pozdější změny sezonních pravidel proto již rozběhnutému případu neposunou podmínky ani cílové hodnoty.

Nově vznikající případy použijí novou politiku. Výjimečná zpětná změna už existujícího případu používá obecný workflow změny minulosti: výrazné varování, dopadový preview a nabídku nové branche nebo přegenerování od prvního dotčeného bodu.

### 18.4.3 Hodnota PR

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Současná výchozí hodnota PR se vypočítá z prvních 15 oficiálních rankingových snapshotů od začátku `PR Case`:

1. vezme se aritmetický průměr hráčových skutečných rankingových pozic v těchto 15 snapshotech,
2. průměr se zhorší o 10 %,
3. výsledek se vždy zaokrouhlí k horšímu pořadí.

Vzorec:

`PR = ceil(průměr prvních 15 rankingových pozic × 1,10)`

Například průměr `13,4` se změní na `14,74` a výsledkem je `PR 15`; průměr `5,0` vytvoří `PR 6`.

Původní patnáctiweekové okno se kvůli výjimečnému testovacímu návratu neposouvá. Případné skutečně dosažené výsledky se normálně projeví v oficiálních snapshotech uvnitř tohoto okna.

Tento výpočet je pracovní default určený k testování simulacemi a může být později změněn.

### 18.4.4 Použití PR

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** PR se používá pouze pro přijetí do Main Draw nebo kvalifikace. Nasazení určuje skutečný ranking hráče, nikoliv PR.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Výchozí počet použití závisí na počtu započitatelných weeků:

- 30–45 weeků absence: 8 použití,
- 46–60 weeků absence: 10 použití,
- 61 a více weeků absence: 12 použití.

Tyto hranice a počty jsou součástí sezonní Protected Ranking Policy a lze je v jiné sezoně změnit. Konkrétní hráč však vždy dokončí svůj `PR Case` podle snapshotu politiky uloženého při začátku případu.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** PR není spotřebováno jen podáním přihlášky. Jedno použití se odečte pouze tehdy, když je hráč do Main Draw nebo kvalifikace definitivně přijat právě díky PR:

- pokud by se do stejného pole dostal podle skutečného rankingu, použije se skutečný ranking a PR se neodečte;
- včasné odhlášení před rozhodnou uzávěrkou přijetí použití nespotřebuje;
- pozdní odhlášení, W/O nebo nedostavení se po definitivním přijetí díky PR už použití spotřebuje;
- jedna `Tournament Edition` může spotřebovat nejvýše jedno použití, i když hráč díky PR vstoupí do kvalifikace a následně postoupí do Main Draw.

Přesné mapování „rozhodné uzávěrky“ na budoucí Entry/Freeze okna se ještě musí dopracovat.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** Pokud může hráč využít skutečný ranking i PR, engine nejprve použije skutečný ranking. Při shodné vstupní hodnotě má hráč se skutečným rankingem přednost před hráčem s PR stejného čísla.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** O strategickém použití PR rozhoduje hráčská AI podle hodnoty turnaje, skutečného rankingu, zbývajících použití, času do expirace, zdraví a kalendáře. Možnost Admina toto rozhodnutí ručně přepsat stejně jako jiné hráčské rozhodnutí je funkcí enginu.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** `PR Case` musí být poprvé aktivován návratem do turnaje nejpozději do tří let od svého začátku, tedy do 183 weeků. Jestli hráč do této lhůty žádný návratový turnaj nezahájí, možnost využít dané PR zanikne. Hráč se může později vrátit běžně, pouze už bez tohoto PR. Tříletá hodnota je nastavením sezonní `Protected Ranking Policy`; jiný Run či sezona ji může mít jinou.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** Po prvním návratovém turnaji lze zbývající použití čerpat po dobu 61 weeků. Toto období začne prvním návratovým turnajem, i když byl hráč přijat podle skutečného rankingu nebo přes WC a PR při něm nespotřeboval. PR skončí dříve, pokud hráč vyčerpá všechna použití.

**[ROZHODNUTO][OFFICIAL RUN DEFAULT]** PR lze v současném Official Runu používat pouze pro běžné individuální turnaje World Tour a Elite Tour. Výchozími výjimkami jsou World Championship, World Tour Finals, týmové soutěže, kontinentální mistrovství, Challenger Tour a Development Tour. Seznam povolených a zakázaných soutěží je součástí `Protected Ranking Policy`, takže jiné Runy nebo sezony mohou používat jiné nastavení.

**[ODLOŽENO]** Přesná taxonomie a ověřování důvodů, omezení přerušené absence, definitivní výpočet hodnoty, definitivní pravidlo pro seeding, vztah k LL, přesný cut-off spotřeby použití a pravidla nového zranění po návratu.

## 18.5 Historie rankingu

**[ROZHODNUTO]** Ukládá se oficiální rankingový snapshot každého weeku; pro nový week vzniká při Week Transitionu z právě dokončeného předchozího weeku.

**[CÍLOVÁ FUNKCE]** Z oficiálních snapshotů se vedou historie světové jedničky, career-high, týdny na #1 a year-end #1.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Uložený Official Ranking snapshot se v běžné pokračující historii nemění. Pozdější oprava se projeví v novém snapshotu; vědomá historie „jako by chyba nikdy nevznikla“ používá branch nebo regeneraci od prvního dotčeného bodu podle kapitol 6.5 a 7.4.

### 18.5.1 Season Closing Ranking

**[ROZHODNUTO PRO PRVNÍ VERZI]** Na konci každé sezony vznikne samostatný archivní `Season Closing Ranking`. Zahrne také výsledky dokončené v Season Weeku 61 a vypočítá se ještě podle odcházející sezonní Ranking Policy. Není totožný s Official Rankingem Weeku 1 následující sezony, který už používá novou policy.

Season Closing Ranking je přímo navázaný na `Season Closure Marker` a používá se v sezonním souhrnu. Nikdy se nepoužívá pro entries, seeding ani rozhodování hráčské AI a nezobrazuje se jako volba na běžných stránkách `Leaderboards`; Viewer jej ukáže pouze v souhrnu příslušné dokončené sezony.

## 18.6 Official a Live Ranking

**[ROZHODNUTO]** MSA používá dva oddělené pohledy ve stylu ATP:

- **Official MSA Ranking** – snapshot publikovaný při otevření současného weeku z autoritativních dat právě uzavřeného předchozího weeku; na rankingové stránce je výchozí,
- **Live MSA Ranking** – průběžný stav podle nejnovějších dokončených a uložených výsledků v aktuálním weeku.

**[ROZHODNUTO]** Přepnutí na Live Ranking přesune Viewer do nejnovějšího uloženého bodu, kam `Viewer Branch` vybraného Runu právě dospěla.

**[ROZHODNUTO]** Historické průběžné stavy Live Rankingu se samostatně neukládají. Live Ranking se vypočítá z posledního oficiálního snapshotu, uložených výsledků aktuálního weeku a platných pravidel propadávání bodů. Pro rychlost může existovat dočasná cache, ale není zdrojem pravdy.

**[ODLOŽENO]** Přesný výpočet Live Rankingu, propadávání bodů uvnitř weeku a zacházení s rozehranými turnaji.

## 18.7 Další rankingy

**[ROZHODNUTO V PRINCIPU]** Existuje Country Ranking.

**[ODLOŽENO]** Co přesně Country Ranking měří a jak se počítá, se nebude určovat předčasně. Rozhodne se až ve chvíli, kdy bude fungovat základ simulace a vzniknou data, na kterých lze smysluplně porovnat možné modely. Zatím se nepředpokládá ani čisté pořadí podle nejlepší šestice hráčů, ani konkrétní měření šíře či síly národního systému.

**[STARŠÍ NÁVRH]** Race to Finals, Elo, Power Rating, Form Ranking, Next Gen Race a další žebříčky jsou zachované jako možné cílové funkce, ale jejich přesný současný rozsah je třeba znovu potvrdit.

**[POZDĚJI][CÍLOVÁ FUNKCE]** Viewer má v budoucnu získat samostatný veřejný/herní web ve stylu `FAX Game` s FIFA-style hodnocením hráčů; analytické stránky jako Elo mohou být součástí tohoto nebo jiného vhodného Viewer webu podle pozdějšího návrhu. Toto veřejné či herní OVR nebude zobrazovat skutečné interní Admin OVR. Má být samostatně odvozené z veřejných výkonů a zápasů, například z předchozího roku, takže může interní skutečnost jen odhadovat.

Pevný je zatím pouze tento budoucí směr, samostatnost veřejných webů uvnitř Vieweru a striktní oddělení veřejného/herního ratingu od interního OVR. Přesný název webu či sekce, období dat, atributy, vzorec, aktualizace, karty hráčů a všechny další funkce se navrhnou později.

---

# 19. Prize money a finance

**Rozsah kapitoly:** schopnost evidovat a vypočítat prize money a testovací abstraktní Financial Level jsou funkčnosti enginu. Konkrétní částky, měny, bonusy a rozhodnutí, zda je daná Tournament Edition v první verzi používá, jsou Run/Category/Edition konfigurací. Financial Level není účetnictví ani náhradní součet prize money.

## 19.1 Prize money

**[ROZHODNUTO PRO PRVNÍ VERZI]** Prize money nejsou u žádného turnaje povinný údaj. Tournament Edition může mít úplnou tabulku, částečnou tabulku nebo žádné prize money. V některé pozdější verzi se má úplná finanční konfigurace stát povinnou, ale v první verzi její absence neblokuje announcement, entries, los ani simulaci.

**[ROZHODNUTO]** Pokud jsou prize money nakonfigurované, engine je v první verzi plně vypočítává, vyplácí a historicky ukládá. U hráče sleduje výplaty i součty podle sezony a celé kariéry.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Chybějící finanční hodnota znamená `Not configured / Unknown`, nikdy automatickou nulu. Částečná tabulka je povolená: známé výplaty se vypočítají, neznámé zůstanou Unknown a celkový prize pool se označí `Incomplete / Unknown`. Hráčská AI neznámou částku při volbě turnaje ignoruje a nesmí ji vykládat jako turnaj s nulovou odměnou.

**[ROZHODNUTO]** Každé vyplněné pole finishing stage udává částku určenou jednomu hráči. Mezi všemi známými hodnotami souvislé Qualification + Main Draw posloupnosti musí mít každý pozdější stage přísně vyšší částku na hráče než kterýkoliv dřívější známý stage; nevyplněný mezistupeň zůstává Unknown a první verzi neblokuje. Jsou-li obě krajní hodnoty známé, nejnižší Main Draw výplata proto musí být vyšší než nejvyšší kvalifikační výplata.

**[ROZHODNUTO]** Celkový prize pool Tournament Edition zahrnuje Qualification i Main Draw a engine jej odvodí jako součet `částka za stage × počet hráčů končících v tomto stage`. Nezadává se jako druhá nezávislá autoritativní částka odporující stage tabulce.

**[ROZHODNUTO]** Hráč vyřazený v kvalifikaci dostane nakonfigurovanou výplatu svého konečného Q stage. Úspěšný kvalifikant nebo lucky loser, který vstoupí do Main Draw, dostane pouze jednu turnajovou výplatu podle svého konečného Main Draw finishing stage; kvalifikační prize money se mu k ní nepřičítají.

**[ROZHODNUTO]** Prize money se řídí skutečně dosaženým finishing stage, nikoliv rankingovým unlockem. Hráč, který po jednom či více BYE nebo po přímém pozdním placementu poprvé nastoupí až ve druhém či pozdějším kole a prohraje nebo ukončí zápas RET, dostane výplatu tohoto skutečného kola, i když rankingově získá jen hodnotu prvního kola. W/O postup rovněž odemkne výplatu následně dosaženého stage bez vytvoření zápasové výhry nebo H2H.

**[ROZHODNUTO]** Hráč nahrazený před svým prvním skutečným zápasem nedostane z Edition žádné prize money. DQ před startem znamená nula prize money; u DQ po zahájení se nejprve určí sportovně dosažená výplata a samostatná disciplinární policy ji může následně odebrat.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Je-li již zahájená Edition formálně ukončena jako `Abandoned`, dříve vyřazení hráči si ponechají běžnou výplatu svého konečného stage. Každý hráč, který byl při ukončení stále aktivní, dostane nakonfigurovaný loser payout nejvyššího fyzického stage, kterého skutečně dosáhl. Bez platného vítěze se winner payout nevyplatí.

**[ROZHODNUTO]** Hráči nemají plat.

**[ROZHODNUTO]** Engine nyní neodečítá cestovní, ubytovací ani turnajové výdaje.

**[POZDĚJI]** Mohou existovat další finanční bonusy.

**[ROZHODNUTO]** Každá známá prize-money výplata se ukládá jako částka v konkrétní původní měně Tournament Edition.

**[ROZHODNUTO]** Uživatel si může kdykoliv globálně zvolit `reporting currency`. Tato volba mění pouze zobrazení a souhrnné přepočty; nepřepisuje původní částku ani měnu uloženou u výplaty.

**[ROZHODNUTO]** Přepočet používá historický směnný kurz platný pro week, ve kterém byly prize money získány. Run proto obsahuje historickou tabulku směnných kurzů podle weeku a její hodnoty lze v editovatelném Runu upravovat.

**[ROZHODNUTO]** U jednotlivé výplaty Viewer standardně ukáže původní částku a přepočet v reporting currency v závorce. Sezonní a kariérní součty se primárně zobrazí v aktuálně zvolené reporting currency.

**[ODLOŽENO]** Přesné částky jednotlivých kategorií a sezon, zdroj nebo generování historických kurzů, výchozí základní měna tabulky, zaokrouhlování, inflace a reálné porovnávání kupní síly mezi obdobími.

## 19.2 Financial Level

**[ROZHODNUTO PRO TESTOVACÍ PRVNÍ PRE-ALPHA VERZI]** Každý hráč má dynamický `Financial Level 0–10`, který hrubě odhaduje jeho skutečně dostupné sportovní zázemí a prostředky. Nejde o peněžní částku ani účet: engine nevede balance, měny, platy, smlouvy, pravidelné příjmy ani položkové výdaje za cestování, vybavení, trénink nebo péči.

**[PROZATÍMNÍ]** Orientační význam rozsahu je od minimálního přístupu ke zdrojům na `0` po téměř neomezený přístup k elitní přípravě, cestování a péči na `10`. Přesný význam mezistupňů a jejich distribuce se budou testovat.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Výsledný level je odhad z více signálů, zejména rodinného zázemí, klubové či federační podpory, country `Elite Support`, dlouhodobého postavení a úspěchů hráče a známých prize money. Prize money mohou level zvyšovat, ale nejsou jeho podmínkou; chybějící prize money znamenají neznámý signál, nikoliv nulu. Interně lze uchovat vysvětlující zdroje odhadu, aniž by se z nich stal finanční účet.

Country `Elite Support` pouze posouvá pravděpodobnostní výchozí rozdělení. Neurčuje konkrétního hráče: mimořádně silné rodinné, klubové či federační zázemí může vytvořit vysoký level i v zemi se slabším ratingem a opačně.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Financial Level se vyhodnocuje při každém Week Transitionu. Běžně se mění pomalu a jedna obyčejná výhra ani jeden nákladný turnaj jej skokově neposunou; významná nová podpora může způsobit rychlejší růst a ztráta podpory, dlouhé období bez úspěchů nebo dlouhodobé zatížení zdrojů pozvolný pokles.

**[ROZHODNUTO PRO OFFICIAL FAX DEFAULT]** Protože je squash ve světě FAX globálním sportem s obecně širší možností profesionálního zajištění, výchozí distribuce Financial Levelu má být štědřejší než přímá kopie reálného tenisu. Hráč v TOP 1000 má mít vysokou pravděpodobnost prostředků na běžný profesionální Tour kalendář, nikoliv automatickou garanci libovolné cesty, každého turnaje nebo elitního zázemí.

Ligový squash je pouze světové vysvětlení této obecnější ekonomické situace. **[ROZHODNUTO PRO PRVNÍ VERZI]** Engine jej vůbec nesimuluje ani nepoužívá jako samostatný záznam, příjem, událost, faktor nebo položku logu; nevzniká `League Income` ani liga jako entita.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Financial Level je převážně měkký faktor hráčské AI při volbě cestování, turnajů, přípravy, vybavení, recovery a péče. Tvrdé omezení smí vzniknout pouze při krajním nesouladu zdrojů a požadované akce, pokud neexistuje výjimečná podpora. Přesné prahy a váhy zůstávají kalibrací.

**[ROZHODNUTO PRO TESTOVACÍ PRVNÍ VERZI]** Jeho sportovní účinky jsou malé, verzované, snadno vypnutelné a kalibrovatelné v řádu jednotek procent. Může mírně:

- snížit efektivní riziko Injury/Illness prostřednictvím prevence,
- zvýšit pravděpodobnost a přesnost včasného odhalení `At Risk`,
- urychlit hojení a recovery po tréninku či zápase,
- zlepšit dostupnost kvalitní přípravy, vybavení, cestování a zdravotní péče.

Vrozená náchylnost a vlastní recovery profil zůstávají samostatné; Financial Level hráče biologicky nepřepisuje.

**[ROZHODNUTO PRO PRVNÍ VERZI][ENGINE INVARIANT]** Financial Level není obecný skrytý bonus k výkonu a nesmí se započítat podruhé, pokud se jeho dlouhodobý vliv už projevil v konkrétních atributech nebo stavech. Během zápasu smí přímo působit pouze jako velmi slabý `Resource Recovery Modifier` při delších přestávkách mezi gamy a při zdravotní přestávce. Nepůsobí po každé rally a v jednom recovery procesu se započítá právě jednou. Mají-li dva hráči totožné aktuální atributy, stavy, přípravu a recovery vstupy, samotný rozdíl Financial Levelu jim mimo tento výslovně omezený recovery kontext nedá další skryté procento výkonu.

**[OTEVŘENO / KALIBRACE]** Počáteční distribuce, přesný update model, význam jednotlivých levelů, zdrojové váhy, měkké a tvrdé AI prahy a všechny číselné modifikátory zdraví, recovery a dostupnosti. Existence testovacího stavu `0–10`, jeho dynamika, malé oddělené účinky, zákaz účetnictví a zákaz přímého obecného match bonusu jsou rozhodnuté.

---

# 20. Disciplína a doping

**Rozsah kapitoly:** disciplinární a dopingový mechanismus je schopnost enginu. Konkrétní důvody, pravděpodobnosti, délky trestů, anulování výsledků a veřejnost případů jsou policy konkrétního Runu.

## 20.1 Disciplinární případy

**[ROZHODNUTO V PRINCIPU]** Engine bude umět disciplinární tresty, zákazy startu a suspendace hráčů.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Pozdě vyřešená konfliktní přihláška, neoprávněné pozdní odhlášení nebo no-show může podle závažnosti vést k odečtu rankingových bodů, časově omezené Disciplinary Zero nebo jejich kombinaci. Více samostatných provinění se může posuzovat a skládat nezávisle; přesná tabulka následků, číselné odečty a délky `X` weeků nejsou rozhodnuté.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Prokázané skutečné zranění nebo nemoc disciplinární sankci za pozdní odhlášení či nenastoupení odstraní. Tím se nemění sportovní a zdravotní následky a po Final Commitment Deadline se automaticky neruší Week Tournament Lock. Další omluvitelné důvody a důkazní pravidla zůstávají otevřené.

**[ROZHODNUTO PRO SOUČASNÝ ROZSAH]** Samotný nástup se zraněním nebo nemocí ani pozdější zveřejnění tohoto zdravotního stavu disciplinární případ nevytváří. Základní simulace řeší pouze zdravotní a sportovní následky. Případný podvod, tankování, porušení bezpečnostního protokolu nebo zneužití neveřejné zdravotní informace patří až do budoucí detailní disciplinární a integrity vrstvy.

**[ROZHODNUTO]** DQ před zahájením zápasu automaticky znamená nula rankingových bodů a nula prize money z dané Edition. U DQ po zahájení se sportovní výsledek nejprve započítá jako výhra/prohra a samostatná disciplinární policy může diskvalifikovanému hráči dosažené body, prize money nebo obojí odebrat. Přesná sazba a podmínky tohoto forfeitu zůstávají odložené.

**[ODLOŽENO]** Úplný katalog důvodů, přesné sankční stupně a délky, okamžik účinnosti a expiry, důkazní standard, odvolání, další dopad na ranking a turnajové pavouky i historické veřejné zobrazení.

## 20.2 Doping

**[ROZHODNUTO V PRINCIPU]** Mohou existovat dopingové případy a následné tresty.

**[ODLOŽENO]** Generování případu, typ porušení, dokazování, anulování výsledků, vracení prize money, přepočty rankingů a veřejné zobrazení. Jde o složitý systém, který se rozpracuje později.

---

# 21. Statistiky, H2H, historie a ocenění

**Rozsah kapitoly:** výpočty historicky správných statistik a H2H jsou funkčnost enginu. Konkrétní sada ocenění, jejich názvy, období a pravidla jsou konfigurací Runu; současné ceny popisují Official Run.

## 21.1 Automatické statistiky

**[ROZHODNUTO]** Statistiky, rekordy a H2H se automaticky aktualizují podle dokončených výsledků.

**[ROZHODNUTO]** Ve Vieweru vždy odpovídají vybranému historickému bodu a nesmějí obsahovat budoucí zápasy.

**[ROZHODNUTO]** Live H2H, statistiky a rekordy se nevytvářejí jako samostatný snapshot po každé změně. Vypočítají se z uložených zápasů a dalších autoritativních dat.

**[ROZHODNUTO]** Při výběru historického weeku se vše dopočítá pouze z dat dostupných do konce zvoleného weeku včetně. V právě probíhajícím weeku se započítají jen dokončené a uložené zápasy.

**[PROZATÍMNÍ]** Pro výkon lze používat odvozené cache, ale nejsou zdrojem pravdy.

## 21.2 H2H

**[ROZHODNUTO V PRINCIPU]** Viewer obsahuje propracované H2H a porovnání hráčů.

**[ODLOŽENO]** Přesné filtry, povrchy/kurtové typy, kola, období, důležitost zápasu a další H2H rozklady. Konkrétní rozsah první verze `Player Comparison`, včetně počtu současně porovnávaných hráčů, byl v navazujícím dialogu výslovně přeskočen a zůstává otevřený; obecná existence porovnání se tím neruší.

### 21.2.1 Rivality

**[ROZHODNUTO V PRINCIPU]** Squash Engine bude obsahovat hráčské rivality. Přesný mechanismus jejich vzniku, struktury, síly, životního cyklu a zobrazení má statusy uvedené níže.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Squash Engine má automaticky rozpoznávat rivality z autoritativní historie simulace. Rivalita nemusí spojovat pouze dva hráče: může zahrnovat tři nebo více hráčů, jeden hráč může současně patřit do více rivalit a počet těchto překrývajících se vztahů nemá mít pevný limit.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Skupinová rivalita má mít vlastní společný kontext a současně zachovat jednotlivá H2H uvnitř skupiny; vztah každé dvojice nemusí být stejně intenzivní. Rivality se mohou v čase zesilovat, slábnout a přejít do historického stavu, ale jejich dřívější existence se z historie nemaže.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Formální číselné `Rivalry Score`, jeho škála, vstupy a prahy jsou pouze slabým směrem. Případný výpočet může zvažovat četnost, vyrovnanost a aktuálnost zápasů, jejich důležitost a těsnost výsledků, ale žádný konkrétní vzorec zatím není canonem.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Samotné označení nebo skóre rivality nemá přímo přidávat či ubírat výkon a vytvářet samoposilující smyčku. Výkon mohou samostatně ovlivnit skutečné vrstvy jako tlak, motivace, znalost soupeře, zkušenost a stylový matchup; rivalita je především jejich analytickým a veřejným kontextem.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Admin může vytvořit `Manual Rivalry`, pokud engine nemá data potřebná k automatickému odvození, například u hráčů, kteří byli rivalové v nesimulované juniorské kariéře. Takový záznam může uložit původ, období a stručný kontext, ale nesmí sám vymyslet neodehrané juniorské výsledky ani je přidat do oficiálního H2H.

**[PROZATÍMNÍ]** Manual Rivalry sama pouze doplňuje známý vztah. Pokud chce Admin zvýšit pravděpodobnost společných turnajů či vzájemných zápasů, použije transparentní `Scenario Direction` z kapitoly 22.11; Direction nic nezaručuje a musí respektovat platné entry, ranking, seeding a draw možnosti. Zaručené konkrétní setkání, turnaj nebo kolo patří pod `Future Lock`. Automaticky rozpoznaná rivalita nesmí sama bez výslovné Direction manipulovat budoucí los.

**[PROZATÍMNÍ]** Rivality mají ve Vieweru MSA pravděpodobně patřit k oblasti `H2H / Rivalries`, pokud tato sekce zůstane v konečném stromu stránek. Přesné umístění není rozhodnuté.

## 21.3 Rekordy

**[ROZHODNUTO V PRINCIPU]** Viewer i Admin budou na různých kontextových stránkách zobrazovat velké množství rekordů. Nemusí existovat pouze jedna centrální stránka; globální, turnajové, hráčské, sezonní, zemské a další rekordy se mohou zobrazit tam, kde dávají význam.

**[CÍLOVÁ FUNKCE]** Engine má dlouhodobě uchovávat a vypočítávat například:

- tituly podle kategorií,
- World Championships a Finals titles,
- týdny a série na #1,
- youngest/oldest champions,
- největší upsety,
- nejlepší sezony,
- win streaks,
- nejhranější a finálové rivality,
- country records,
- historické milníky.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Jednotná znovupoužitelná vrstva pro definice a výpočet rekordů i úplná historie držitelů — vytvoření, překonání, vyrovnání a předchozí spoludržitelé — jsou zatím pouze slabým směrem. Nemění to rozhodnutý kontrakt kapitoly 21.1, že zdrojem pravdy jsou autoritativní výsledky a historický Viewer nesmí použít budoucí data.

## 21.4 Awards

**[ROZHODNUTO V PRINCIPU]** Existuje sezonní hráčské ocenění.

**[ROZHODNUTO V PRINCIPU]** Vedle něj existuje samostatné ocenění `Player of the Year` za civilní rok, nikoliv za squashovou sezonu.

**[ODLOŽENO]** Názvy, výběr vítěze, nominace, hlasování, automatický výpočet a historické zobrazení.

---

# 22. Predikce

**Status kapitoly:** hlavní Forecast systém, Future Locks, reprodukovatelné Forecast Sessions, adaptivní vizualizace, práce s jednotlivými scénáři, rare-event sampling a counterfactual analýza tvoří ucelený **silný směr**, nikoliv definitivně uzavřený matematický nebo produktový kontrakt. Je potvrzené, že se s nimi má při budoucím návrhu počítat; názvy, vzorce, znaménka, agregace, samplingové algoritmy, výkonové limity, přesné stránky a pořadí implementace se musí později znovu projednat. Podsekce výslovně označené jako běžný směr tento silný status nedědí; konkrétně jde o pracovní `Conflict Fork` a `Scenario Direction`.

## 22.1 Absolute a Viewer perspektiva

**[PROZATÍMNÍ, SILNÝ SMĚR]** Existují dva odlišné typy predikční perspektivy:

1. **Absolute Prediction** – má přístup ke všem skutečným interním a skrytým datům.
2. **Viewer Prediction** – používá pouze data, která by byla v daném Viewer režimu a historickém weeku oprávněně známá.

`Absolute` zde znamená nejlepší interní pravděpodobnost podmíněnou současným modelem enginu, jeho verzí a konkrétním vstupním snapshotem. Nejde o metafyzicky neomylnou pravdu: vyšší počet simulací zmenšuje statistickou chybu odhadu tohoto modelu, ale sám neopraví neúplný nebo špatně kalibrovaný model.

Predikce musí být vždy jasně odlišená od skutečného výsledku. Veřejný výstup nesmí nechtěně prozradit skrytou formu, zdraví, atributy, budoucí talenty ani jiné Admin informace.

## 22.2 Univerzální index odchylky a překvapivosti

**[ROZHODNUTO V PRINCIPU]** Engine významově odděluje tři hodnoty při porovnání skutečně vzniklého výsledku nebo stavu s pravděpodobnostní distribucí, která existovala před událostí:

- `p` je přirozená pravděpodobnost či četnost konkrétní události,
- `δ` na škále `−1 až +1` je směrová vzdálenost výsledku vůči nejpravděpodobnější nebo typické oblasti, pokud má výsledek smysluplný kladný a záporný směr vůči konkrétnímu hráči, zemi nebo jinému subjektu,
- `α` na škále `0 až 1` je velikost této vzdálenosti bez směru; v současném konceptu odpovídá velikosti `δ`, ale není pravděpodobností `p` ani pouze přejmenovaným `1 − p`.

Referenční distribuce vzniká ze skutečných simulací a nemusí být Gaussova. Přesný matematický vztah `α` a `δ`, normalizace obou škál a jejich robustní odhad jsou otevřené, ale výše uvedené významové oddělení je potvrzené.

Systém se může použít na zápas, výkon hráče, celý turnaj, sezonu, zemi, talentovou generaci a další později podporované oblasti. U turnaje nebo sezony může být potřeba současně zachovat celkovou překvapivost, směr vůči favoritům a individuální odchylky jednotlivých subjektů, aby se velké opačné výkyvy vzájemně nezrušily na falešnou nulu.

U zápasu se pracovně rozlišují alespoň dvě perspektivy znaménka `δ`. Hodnota vztažená ke konkrétnímu hráči jde do plusu, pokud překonal vlastní očekávání, a do minusu, pokud za ním zaostal. Souhrnný `match surprise score` může naopak používat konvenci, v níž kladná strana znamená potvrzení favorita a záporná strana vítězství outsidera neboli upset; velikost vyjadřuje sílu odchylky. U turnaje nebo sezony jediná taková kladná či záporná osa zpravidla nestačí, protože současně vznikají očekávané výsledky i upsety. Tyto konkrétní konvence znaménka jsou zatím pouze silným směrem a jejich konečné názvy i matematika zůstávají otevřené.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Referenční distribuce se váže k předudálostnímu snapshotu a pozdější skutečný výsledek ji nesmí zpětně přepsat. Pracovní nula `δ` a `α` označuje nejbližší typickou či nejpravděpodobnější oblast distribuce, nikoliv nutně jeden jediný přesný výsledek včetně skóre. Forecast Engine může být zdrojem distribuce i samostatně označeného nejpravděpodobnějšího konkrétního scénáře.

**[ODLOŽENO]** Konečný název systému, přesná matematická definice typické oblasti a nuly, pravidla znaménka, normalizace `δ` a `α`, zacházení s více stejně typickými vrcholy, vícerozměrnými výsledky, symetrií hodnot soupeřů a agregací zápasů do turnajů, sezon a kariér. Samotný modus jednoho přesného skóre nemá být bez dalšího definicí nuly; konkrétní výkonová veličina a případné použití hustoty, očekávané hodnoty, mediánu nebo jiné robustní statistiky se rozhodnou později.

## 22.3 Nezávazný Forecast Engine

**[PROZATÍMNÍ, SILNÝ SMĚR]** `Forecast Engine` je nezávazná pravděpodobnostní simulace z podporovaného uloženého bodu. Může analyzovat jeden zápas, turnaj, week, sezonu, vlastní rozsah nebo velmi vzdálenou budoucnost až k podporovanému konci Runu. Každý pokus simuluje všechny časově platné systémy potřebné na cestě k cíli, včetně vývoje hráčů, zdraví, AI, turnajů, rankingů a budoucího generování talentů podle schopností zvolené verze enginu.

Forecast:

- nemění zdrojový Run, branch, čas ani uloženou historii,
- nevytváří výsledky, rankingy, únavu nebo hráče ve skutečné branchi,
- nesmí ovlivnit náhodnost či seed pozdější skutečné simulace,
- na rozdíl od Candidate Branches nevytváří stovky pokračovatelných alternativních historií,
- ukládá nejvýše kompaktní agregovaný report a potřebné referenční metadata, nikoliv automaticky každý virtuální svět.

Candidate Branches zůstávají skutečnými alternativními časovými liniemi, které lze zachovat a dále simulovat. Forecast samples jsou naproti tomu statistické pokusy určené pouze k odhadu distribuce.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Tento rozdíl nevylučuje výslovnou akci nad jedním vybraným vzorkem. Dokud Admin nic neudělá, Forecast sample zůstává pouze virtuálním statistickým pokusem. Admin jej však může podle uloženého seedu a čísla pokusu deterministicky zrekonstruovat a samostatnou potvrzenou akcí zhmotnit jako novou branch. Nevzniká tím automatické ukládání všech vzorků ani zpětná změna původního Forecast reportu.

## 22.4 Počet pokusů, přesnost, výkon a report

**[PROZATÍMNÍ, SILNÝ SMĚR]** Uživatel může zvolit počet pokusů od velmi malého rychlého vzorku, například 10 simulací, přes tisíce či miliony až po miliardy nebo více. Systém nemá zavádět malý svévolný produktový strop, ale před spuštěním musí ukázat realistický odhad času, zátěže a potřebného prostoru a výrazně varovat před úlohou, která by na daném hardwaru trvala neúnosně dlouho.

Vedle pevného počtu pokusů může později existovat režim `Target Accuracy`, který pokračuje do dosažení zadané statistické přesnosti. Výsledek ukazuje nejen procento, ale také počet pokusů, statistickou nejistotu či interval spolehlivosti, průběh konvergence a verzi modelu. Dlouhý Forecast je úloha Task Centeru, může běžet na pozadí a používá obecné bezpečné mechanismy pozastavení a zastavení.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Přesnost se vyhodnocuje průběžně po dávkách. Engine sleduje nejen intervaly nejistoty, ale také to, zda se odhadovaná distribuce během několika po sobě jdoucích dávek už podstatně neposouvá. Stav `Stable` nesmí vzniknout po jediné náhodně klidné dávce. Výsledek s nulovým počtem výskytů se nesmí vydávat za matematicky jistých `0 %`; report zobrazí odpovídající horní mez nebo jinou poctivou informaci o vzácné události. Přesné velikosti dávek, testy stability a prahy se zkalibrují později.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Při výpočtu více metrik současně řídí automatické zastavení výslovně označené primární výstupy. Vzácná vedlejší metrika nesmí bez vědomí uživatele držet celou úlohu donekonečna; dostane vlastní počet vzorků, interval a stav nižší přesnosti. Vedle vlastního počtu pokusů nebo tolerance mohou existovat srozumitelné profily typu rychlý náhled, standardní, vysoká a extrémní přesnost, ale jejich názvy a konkrétní hodnoty jsou otevřené.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Pokud se nezměnil výchozí snapshot, model ani scénář, lze Forecast postupně zpřesňovat: například po prvních 10 pokusech přidat dalších 990 do celkových 1 000 místo zahození předchozí práce. Změna relevantního vstupu vytvoří nový jasně označený scénář či report, aby se nesloučily nekompatibilní vzorky.

Forecast Session lze po pozastavení nebo dokončení znovu otevřít a zadat `Add X Samples`, dokud zůstávají dostupné a totožné její simulačně relevantní vstupy. Před dlouhou úlohou engine provede krátký reprezentativní benchmark na daném počítači a z něj odhadne čas, RAM a pracovní prostor; přesný pilotní počet se určí podle výkonu konkrétní verze.

**[PROZATÍMNÍ, SILNÝ SMĚR]** `Absolute Forecast` automaticky používá časově platnou úroveň detailu simulace, pravidla a modely vybraného Runu a branche. Forecast nemá vlastní skrytý přepínač, který by tuto realitu potají zjednodušil. Samostatně lze zvolit pouze `Report Detail`, tedy kolik agregovaných distribucí, cest pavoukem, rankingových vývojů nebo jiných výstupů se vypočítá a uchová. Případný budoucí zrychlený aproximovaný režim musí být jasně označen jako `Fast Estimate` nebo obdobně a nesmí se vydávat za Absolute Forecast téhož modelu.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Jednotlivé virtuální budoucnosti se po započtení do výsledku standardně dlouhodobě neukládají. Forecast používá průběžnou agregaci a trvale uchová pouze kompaktní report: identitu otázky a scénáře, výchozí Run/branch/week, verzi modelu, převzatý simulační detail, počet pokusů, počty či dostatečné statistiky jednotlivých výsledků, pravděpodobnosti, nejistotu a technický stav nezbytný pro případné další zpřesnění stejného výpočtu. Velikost reportu se proto řídí především počtem sledovaných možností, metrik a historických snapshotů, nikoliv tím, zda proběhlo deset nebo miliarda pokusů.

Během výpočtu může Forecast používat dočasnou RAM a pracovní prostor na disku; jejich odhad patří do preview úlohy a nepotřebná pracovní data se po bezpečném dokončení nebo zrušení uvolní. Podrobné reporty mohou uchovávat omezené histogramy, průběh konvergence nebo jiné kompaktní aproximace, nikoliv automaticky celé virtuální světy. Přesný formát dostatečných statistik, continuation state, cache a storage politiky zůstává otevřený.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Novou otázku uvnitř již simulovaného horizontu lze vyhodnotit okamžitě pouze tehdy, pokud původní Report Detail uchoval potřebné dostatečné statistiky nebo značky vzorků. Jinak engine deterministicky přehraje stejné identifikátory vzorků a dopočítá nový údaj. Pokud nový cíl leží dále v budoucnosti, stejné vzorky se přehrají k původnímu horizontu a odtud pokračují; budoucí optimalizace může použít kompatibilní uložené koncové stavy, ale miliony úplných endpointů se nesmějí ukládat jako výchozí chování.

Pracovní storage profily mohou rozlišit `Compact`, který uchová report, seed a identifikátory vzorků a nové metriky získá replayem, a `Reusable`, který navíc ponechá vybrané mezilehlé značky či stavové souhrny pro rychlejší další analýzu. Přesné názvy a obsah profilů zůstávají otevřené; plné světy nejsou výchozím profilem.

## 22.5 Hypotetické scénáře a porovnání

**[PROZATÍMNÍ, SILNÝ SMĚR]** Forecast později dovolí vytvořit nezávazný hypotetický scénář změnou jednoho či více vstupů, například zdraví nebo únavy hráče, gameplanu, kalendáře, pravidla rankingu či talentového prostředí země. Zdrojová branch se tím nemění. Dva nebo více scénářů lze porovnat podle absolutních pravděpodobností i jejich rozdílu v procentních bodech napříč krátkým a dlouhým horizontem.

Report musí uchovat alespoň výchozí Run, branch a week, přesný rozsah, použité vstupy a overrides, verzi modelu, úroveň detailu převzatou z Runu, počet pokusů, statistickou nejistotu a čas vytvoření. Přesný datový formát, deduplikace, retence a vztah k obecnému Compare States zůstávají otevřené.

## 22.6 Forecast Markets, kurzy a historie pravděpodobností

**[PROZATÍMNÍ, SILNÝ SMĚR]** V libovolném podporovaném uloženém bodě lze definovat dlouhodobou predikční otázku neboli pracovní `Forecast Market`, například:

- kdo bude světovou jedničkou na konci zvoleného kalendářního roku,
- která země vyhraje příští Team World Championship,
- kdo se kvalifikuje na MSA Finals,
- zda hráč do určitého data získá významný titul,
- zda se v daném období objeví talent určité potenciálové třídy.

Výpočet může vytvářet férovou modelovou pravděpodobnost, odpovídající férový kurz bez marže, statistickou nejistotu a později také další oddělené vrstvy:

- `Absolute Probability` ze skutečného interního stavu,
- `Viewer/Public Probability` pouze z tehdy veřejných či oprávněně odhadovaných informací,
- `Bookmaker Odds` s marží, vlastními modelovými chybami a případnou reakcí na sázení,
- případnou budoucí `Market Probability` vznikající chováním simulovaných účastníků prediction marketu.

Tyto vrstvy se nesmějí vydávat jedna za druhou. Hráčská AI k Absolute vrstvě přístup nemá a samotná veřejná pravděpodobnost není totéž co kurz bookmakera nebo tržní cena.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Opakované výpočty stejné otázky v různých weecích nebo po podporovaných stavových událostech lze ukládat jako historické snapshoty a skládat do víceřádkového grafu ve stylu prediction marketů. Graf může zobrazit křivku každého kandidáta, přesné hodnoty po najetí, významné události a konečné rozuzlení na `100 % / 0 %`. Při historickém prohlížení Viewer ukáže pouze body, které byly k danému weeku skutečně vytvořené a veřejně dostupné; budoucí část křivky nesmí prozradit pozdější vývoj.

První verze může snapshot vytvořit ručně na vyžádání. Pozdějším směrem je automatické sledování podle zvolené frekvence nebo triggerů, například každý week, po zápase, losu, rankingovém snapshotu nebo veřejném oznámení, až případně po každý podporovaný stavový bod. Starý historický snapshot uchovává tehdejší vstupy a verzi modelu a nesmí se tiše přepsat novějším Forecast Enginem.

Ve Vieweru může vzniknout samostatná stránka či fiktivní predikční nebo sázkový web s veřejnou křivkou. Admin může později překrýt Absolute, Public, Bookmaker a případně Market křivku a analyzovat informační rozdíly. Přesné weby, jejich značky, dostupné otázky, automatická frekvence, storage politika, rozlišení bodů uvnitř weeku, marže, simulace sázejících a vizuální provedení grafu se rozhodnou později.

**[ODLOŽENO]** Přesné vzorce a výstupy jednotlivých predikcí, kalibrace, vzácné události, confidence contract, způsob sestavení vzájemně výlučných možností, položka `Other`, zrušené nebo změněné cílové události, resolution rules a technické provedení extrémně velkých Forecastů.

## 22.7 Future Locks a jejich použití

**[PROZATÍMNÍ, SILNÝ SMĚR]** `Future Lock` je povinná podmínka, kterou musí zamčená simulace splnit. Uživatelsky jde o jeden systém nucených podmínek; „conditional“ popisuje pouze technický způsob generování budoucností slučitelných s lockem, nikoliv druhý měkčí typ locku.

Stejnou konfiguraci lze použít dvěma způsoby:

1. **Locked Forecast** – nezávazná testovací laboratoř ověří proveditelnost, konflikty, přirozenou absolutní pravděpodobnost, části, které by se musely vynutit, a možné následky. Forecast sám nemění žádnou branch.
2. **Locked branch simulation** – po ověření lze locky použít v nové i současné branchi a jejich výsledky se stanou skutečnou historií této branche. Jde o samostatnou akci; neporušuje to neměnnost samotného Forecast reportu.

Lock může cílit do minulosti, přítomnosti nebo budoucnosti. Minulý lock vyžaduje přepočet od nejstaršího ovlivněného bodu a dřívější budoucnost zůstává obnovitelná prostřednictvím historie a verzování. Přítomný začne působit od současného podporovaného bodu. Budoucí čeká na svůj cílový moment a engine při cestě průběžně hlídá jeho proveditelnost.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Locky a jejich provenance vidí pouze Admin. Viewer nesmí dostat informaci o zamčené budoucnosti ani future leak; vidí až události, které se v jeho branchi a historickém čase skutečně staly. Hráčská AI tím nezískává přístup k budoucnosti a nadále rozhoduje pouze z informací, které má v daném okamžiku.

Po dosažení cíle získá lock stav `Fulfilled`, přestane omezovat pozdější simulaci a zůstane dohledatelný v Admin historii. Přesný životní cyklus úpravy nebo odstranění dosud nesplněného či již splněného locku byl v závěru dialogu výslovně přeskočen a zůstává otevřený.

## 22.8 Granularita a typy podmínek

**[PROZATÍMNÍ, SILNÝ SMĚR]** Lock vynutí pouze výslovně zadané části a všechno ostatní se simuluje přirozeně v rámci budoucností slučitelných s těmito částmi. U zápasu lze zamknout například jen vítěze, vítěze a poměr setů, přesná skóre setů nebo později ještě podrobnější podporované údaje. U turnaje lze zamknout účast, soupeře a kolo jejich setkání, postup, titul nebo jiný podporovaný stav. Stejný princip se může vztahovat na ranking, kariéru, zemi, generaci talentů či jinou doménu enginu.

Vedle přesné hodnoty jsou podporovaným směrem také rozsahové a agregační podmínky, například ranking `1–5`, alespoň dva tituly, nejvýše určitá hodnota nebo určitý počet výskytů ve zvoleném období. Vzájemně rozporné detaily, například zamčený vítěz proti neslučitelnému přesnému skóre, musí odhalit validace. Konečný katalog polí, operátorů, vnořených podmínek a jejich Admin editor se rozhodne později.

## 22.9 Proveditelnost, absolutní pravděpodobnost a síla vynucení

**[PROZATÍMNÍ, SILNÝ SMĚR]** Future Lock odděluje nejméně tři různé údaje:

1. **Feasibility / Compatibility Probability** – v kolika přirozeně simulovaných budoucnostech vznikne před rozhodujícím nuceným krokem stav, ve kterém pevná pravidla požadovanou událost vůbec dovolují. V jednom konkrétním snapshotu je proveditelnost `ano/ne`; pravděpodobností se stává až napříč mnoha možnými budoucími snapshoty.
2. **Natural Absolute Probability** – jak často by celá událost skutečně nastala bez locku, včetně náhodného losu, postupů a všech dalších nezamčených okolností.
3. **Forcing Cost / Natural Rarity** – pracovní údaj popisující, jak nepravděpodobné náhodné kroky musel lock po dosažení proveditelného stavu vynutit. Přesný název a matematika tohoto údaje zůstávají otevřené.

Pro událost `E` a nutný kompatibilní stav `C` pracovně platí rozklad `P(E) = P(C) × P(E | C)`. Na navazování locků se používá především proveditelnost `P(C)`, nikoliv čekání na přirozené splnění každého náhodného kroku z `P(E | C)`.

U cíle typu „hráč vyhraje mistrovství světa za tři roky“ může report vytvořit funnel: pravděpodobnost, že bude stále aktivní a eligible, že se vůbec může do turnaje dostat, že skutečně nastoupí, že vyhraje a že vyhraje podmíněně na účasti. Locked Forecast následně ukáže také nejčastější vývojové, rankingové, zdravotní, kvalifikační a turnajové cesty v budoucnostech slučitelných s titulem. Tím se oddělí otázka „jaká je přirozená šance?“ od otázky „co všechno se musí stát, aby to bylo možné?“

Příklad: mají-li se dva hráči potkat ve druhém kole, musí se oba dostat do turnaje a jejich ranking, nasazení, formát a pevná pravidla losu musí takové kolo dovolovat. Hráči nasazení jako `#1` a `#3–4` se ve standardně rozděleném pavouku nemohou potkat už ve druhém kole, takže takový pre-draw stav je nekompatibilní. Je-li však kombinace nasazení kompatibilní, lock může vždy zvolit odpovídající platné sloty a při locku skutečného vzájemného zápasu také nutné postupy z předchozích kol. Samostatná slabší podmínka „mohou se potkat“ vynutí jen kompatibilní cestu pavoukem, nikoliv jejich postup.

Nízká Natural Absolute Probability sama lock neblokuje. Znamená pouze, že lock vynucuje přirozeně vzácný svět. Nízká Feasibility Probability naopak říká, že jen málo předchozích vývojů vytvoří vůbec platný výchozí stav; nulová logická proveditelnost znamená skutečný konflikt.

## 22.10 Více locků, varování a konflikty

**[PROZATÍMNÍ, SILNÝ SMĚR]** Více Future Locks se vyhodnocuje jako jeden společný soubor podmínek. Pořadí, ve kterém je uživatel zadal, nesmí změnit výsledný kontrakt. Forecast ukazuje pravděpodobnost každého locku samostatně, jejich společnou přirozenou pravděpodobnost a společnou proveditelnost a určí lock nebo závislost, která prostor platných budoucností omezuje nejvíce.

Engine rozlišuje přirozeně vzácný, obtížně proveditelný a logicky nemožný soubor podmínek. Viditelnými vykřičníky vysvětlí příčinu, závažnost a dopad a nabídne konkrétní možnosti řešení, například změnu či rozšíření podmínky, vrácení konfliktní editace nebo oddělení variant do branchí. Nic nesmí potají přepsat. Oranžový vykřičník je neblokující varování a červený vykřičník operation-scoped kritický problém podle kapitoly 25.6; přesné pravděpodobnostní prahy a jejich doménové mapování zůstávají otevřené.

**[PROZATÍMNÍ]** **Běžný směr, výslovně nikoliv silný směr.** Pracovní `Conflict Fork` může při nevyřešeném konfliktu připravit dvě dočasné Candidate Branches ze společného bezpečného bodu:

- `Lock Path` zachová lock a nepoužije konfliktní změnu nebo nabídne její minimální slučitelnou úpravu,
- `Change Path` zachová změnu, dojede k poslednímu bezpečnému bodu a před porušením locku se zastaví.

Uživatel může varianty porovnat a zachovat jednu, obě nebo žádnou. Dočasný candidate režim má zabránit zahlcení běžných branchí; při dalších konfliktech se nemají varianty nekontrolovaně násobit do `2ⁿ`. Přesný trigger, retence, chování při více současných konfliktech a převod do běžných branchí nejsou rozhodnuté.

Conflict Fork neznamená ukládání všech virtuálních světů Forecastu jako branchí. Vytváří pouze cílené pracovní varianty konkrétního konfliktu ze společného bezpečného bodu.

## 22.11 Scenario Direction jako odlišný běžný směr

**[PROZATÍMNÍ]** **Běžný směr, výslovně nikoliv silný směr.** Vedle povinného Future Locku může později existovat pracovně nazvaný `Scenario Direction`. Ten nic nezaručuje, ale transparentně mění pravděpodobnosti vývoje zvoleného světa či scénáře a může mít nastavitelnou sílu. Původní model a konfigurace Runu musí zůstat rozlišitelné od této směrové vrstvy.

Možná použití zahrnují zlatou generaci určité země, podporu vzestupu prospecta, vznik dlouhé rivality bez povinných konkrétních výsledků, vyrovnanější éru, postupnou změnu dominantního herního stylu nebo globální rozšíření squashe. Scenario Direction nesmí být vydáván za přirozený Absolute Forecast nezměněného modelu.

U ručně doplněné rivality může Direction pracovně zvýšit pravděpodobnost společných turnajů a vzájemných zápasů, aniž by je garantoval nebo porušil entry, seeding či draw eligibility. Samotný záznam `Manual Rivalry` budoucnost nesměruje. Pokud má být zaručen konkrétní zápas nebo kolo, používá se samostatný `Future Lock`.

**[OTEVŘENO, VÝSLOVNĚ PŘESKOČENO]** Přesný rozsah a časové období Direction, konkrétní úrovně síly, systémy, jejichž pravděpodobnosti smí měnit, způsob skládání více Directions, vztah k branchím, lockům a hráčské AI i konečný název. Dialog se od tohoto tématu výslovně vrátil zpět k Future Locks.

## 22.12 Forecast seed, identita vzorku a přesné opakování

**[PROZATÍMNÍ, SILNÝ SMĚR]** Každá Forecast Session má 256bitový `master_seed`. Standardně jej bezpečně vytvoří engine a běžné rozhraní uživatele jím nezatěžuje; v pokročilých informacích jej lze zobrazit, zkopírovat a při založení kompatibilní session také ručně zadat.

Jednotlivé virtuální světy dostávají stabilní `sample_index` a jejich náhodné proudy se deterministicky odvozují nejméně z master seedu, čísla pokusu a jmenného prostoru či verze příslušného algoritmu. Není nutné ukládat miliardy samostatných seedů: trvale stačí master seed, použité rozsahy indexů, vstupní fingerprinty a verze. Samotný 256bitový seed má 32 bajtů a ani velmi vysoký počet pokusů proto nezvětšuje úložiště lineárně počtem seedů.

Forecast Session nabídne nejméně dvě jasně odlišené akce:

- `Repeat Exactly` použije stejné identifikátory vzorků a simulačně relevantní vstupy,
- `New Random Run` vytvoří nový master seed a novou sadu virtuálních světů.

Náhodná kolize dvou nezávislých proudů má být prakticky zanedbatelná, ale toto pravidlo nesmí zakázat dva skutečně stejné výsledky. Pokud dvě různé simulace přirozeně skončí totožným skóre nebo historií, obě se správně započítají do pravděpodobnosti.

Přesná reprodukce vyžaduje také totožný zdrojový snapshot, model, algoritmy a ostatní simulačně relevantní nastavení. Ručně opsaný seed po změně dat nebo verze není příslibem stejného výsledku. Přesný derivační algoritmus, reprodukce mezi hardwarem a operačními systémy a dlouhodobá retence starých simulačních verzí zůstávají otevřené. Tato sekce je užším Forecast kontraktem a nerozhoduje obecný determinismus celého enginu z kapitoly 17.4.

## 22.13 Adaptivní Forecast Visualizer

**[PROZATÍMNÍ, SILNÝ SMĚR]** Forecast nemá jeden graf násilně používaný na všechny otázky. `Forecast Visualizer` automaticky zvolí nejvhodnější výchozí zobrazení podle typu cíle a Admin může přepnout na jiné kompatibilní pohledy. Jeden vzorek stále reprezentuje jeden konkrétní virtuální scénář, ale jeho vizuální kódování se přizpůsobí zápasu, turnaji, rankingu, času, zemi, talentové generaci nebo jiné analyzované veličině.

Pracovní `Match Outcome Landscape` používá tento princip:

- při malém počtu pokusů je každý vzorek samostatnou kuličkou,
- osa X používá pracovní `δ`: od `−1` pro výsledek výrazně lepší pro hráče A přes `0` v typické či nejpravděpodobnější oblasti až k `+1` pro výsledek výrazně lepší pro hráče B; přesná konvence znaménka a vícevrcholové nuly zůstávají otevřené,
- nejpravděpodobnější konkrétní skóre se ukazuje samostatnou značkou a samo nemusí být celou typickou oblastí ani jedinou definicí bodu `0`,
- svislá hranice oddělí vítězství A a B; její vzdálenost od nuly názorně ukáže, jak velká odchylka je potřeba ke změně vítěze,
- podobné vzorky se skládají nad sebe, takže svislý rozměr vyjadřuje četnost či hustotu; barva nebo odstín může rozlišit vítěze a poměr setů,
- při velmi vysokém počtu pokusů se jednotlivé kuličky nahradí histogramem, hustotou nebo reprezentativním vzorkem, zatímco statistika stále používá všechny simulace.

Žádná vizualizace nesmí data uměle převést na Gaussovu křivku. Skutečná distribuce může být asymetrická nebo vícevrcholová například kolem výsledků `3:0`, `3:1` a `3:2`. Během běžícího výpočtu mohou být typická oblast a měřítko označeny jako předběžné a plynule se zpřesňovat; po dosažení konečného stavu report uchová použitou definici osy.

U turnaje může výchozí pohled tvořit jeden shluk nebo řádek pro každého možného vítěze, zatímco detail vybraného hráče zobrazí distribuci dosažených kol vůči jeho očekávání. Ranking může použít distribuci pořadí či heatmapu, časový Forecast křivku a talentová generace matici země × potenciál. Přesná knihovna grafů, definice os, rozložení kuliček, animace, výkonové hranice a ruční přepínače se navrhnou později.

## 22.14 Filtry, podmíněné pohledy a Rare Event Accelerator

**[PROZATÍMNÍ, SILNÝ SMĚR]** Forecast sample může podle zvoleného Report Detail nést kompaktní značky a agregáty, například vítěze, semifinalisty, dosažené kolo, konkrétní matchup, počet upsetů, zemi vítěze nebo vybraný rankingový stav. Nad nimi Visualizer nabídne dva základní režimy:

1. `Highlight` ponechá celou distribuci a odpovídající vzorky zvýrazní, zatímco ostatní zeslabí.
2. `Focus` zobrazí jen odpovídající vzorky a přepočítá podmíněné pravděpodobnosti v rámci této množiny.

Každý filtr musí ukázat počet odpovídajících vzorků, statistickou nejistotu a srozumitelnou známku spolehlivosti. Stejných `40 %` z osmi scénářů se nesmí tvářit stejně přesně jako `40 %` z milionu. Pokud je vybraná množina příliš malá, Admin může pokračovat příkazem typu `Continue until X matching scenarios`.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Pro vzácné podmínky se rozlišují dva výpočetní režimy:

- `Natural Sampling` nechává vznikat všechny světy přirozeně a přímo měří absolutní četnost,
- `Rare Event Accelerator` transparentně směruje generování k hledané podmínce a používá matematické váhy nebo jinou korektní rare-event metodu.

Accelerator se nikdy nezapne potají. Preview ukáže očekávanou úsporu, omezení a vliv na interpretaci. Usměrněné vzorky se nesmějí prostě přičíst k přirozeným jako stejně pravděpodobné kuličky; vzniknou v samostatném child `Conditional Forecastu`, který je propojen s původní session, vizuálně odlišen a s přirozeným reportem se kombinuje jen statisticky korektním způsobem. Report podle použité metody ukáže nejméně vážený počet nebo efektivní velikost vzorku a odpovídající nejistotu.

Rare Event Accelerator je výpočetní samplingová technika, nikoliv Future Lock, Scenario Direction ani automatická změna skutečné branche. Přesný filter builder, logické skládání podmínek, katalog uchovávaných značek, importance sampling, váhy, efektivní velikost vzorku, stopping rules a vztah k proveditelnosti Future Locks zůstávají otevřené.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Z vyfiltrované množiny lze spustit `Create Branch from Selection`. Engine nabídne konkrétní reprezentativní vzorek, například nejtypičtější odpovídající scénář, přirozeně nejpravděpodobnější, nejextrémnější nebo náhodný z výběru. Admin si jej nejprve může prohlédnout a až poté potvrdit materializaci.

## 22.15 Scenario Inspector, připnuté scénáře a převod na branch

**[PROZATÍMNÍ, SILNÝ SMĚR]** Najetí na konkrétní Forecast vzorek zobrazí rychlý souhrn. Kliknutí otevře `Scenario Inspector` s relevantní časovou osou, výsledky, pavoukem, změnami rankingů, stavem hráčů a dalšími událostmi podle typu Forecastu. Pokud už graf kvůli velikosti zobrazuje agregovanou hustotu, kliknutí na oblast nabídne konkrétní typické, extrémní nebo jinak reprezentativní vzorky z daného shluku.

Celý stav každého vzorku se standardně neukládá. Inspector jej při potřebě zrekonstruuje ze zdrojového snapshotu, master seedu, `sample_index` a kompatibilní verze enginu. Nedostupná zdrojová verze nebo poškozená závislost se musí zobrazit jako skutečný problém, nikoliv nahradit podobným vymyšleným scénářem.

Akce `Create Branch from Scenario` dovolí vybrat libovolný podporovaný bod uvnitř zrekonstruované historie, například po zápase, turnaji, weeku nebo sezoně; výchozí volbou je konec Forecast horizontu. Engine od zdrojového snapshotu přesně zrekonstruuje cestu do zvoleného bodu, zhmotní jeho stav jako novou branch a uloží provenance Forecast Session, sample indexu, seedu, modelu a zdrojového bodu.

Při materializaci z poloviny Forecast scénáře existují dva odlišné režimy:

- `Continue This Scenario` zachová pro již nasimulovanou část budoucnosti stejný náhodný proud a dovolí přesně pokračovat vybranou cestou,
- `Fork From This Point` převezme pouze stav ve vybraném bodě a další budoucnost začne s novou nezávislou náhodností.

**[PROZATÍMNÍ, SILNÝ SMĚR]** `Pin Scenario` uloží zajímavý vzorek bez okamžitého vytvoření branche. Připnutí může mít název, poznámku a značky, lze je porovnat s jinými scénáři a později zhmotnit. Ukládá především odkaz na session, sample index, seed, vstupní fingerprint a malý souhrn, takže je typicky řádově menší než materializovaná branch. Rozdílové ukládání může zlevnit i branch, ale její skutečný stav a další divergence přesto zabírají více než lehký pin.

Připnuté scénáře se zobrazují uvnitř původní Forecast Session i na společné Runové stránce pracovně nazvané `Saved Scenarios`, kde je lze filtrovat, porovnávat a převádět na branche. Při mazání zdrojového Forecastu, snapshotu nebo potřebné verze engine vypíše závislé piny a nabídne jejich zrušení, trvalou materializaci či převod na branch. Přesná retence, názvy stránek, formát trvalého archivovaného scénáře a chování při migraci verzí zůstávají otevřené.

## 22.16 Vysvětlení scénáře a counterfactual analýza

**[PROZATÍMNÍ, SILNÝ SMĚR]** Scenario Inspector obsahuje pohled pracovně nazvaný `Why This Scenario?`. Ten porovná vybraný svět s očekávanou distribucí a ukáže nejdůležitější odhadované příspěvky k odchylce, například formu, zdraví, los, únavu, změny atributů nebo těsné rozhodující zápasy. Dokud nebyl proveden skutečný counterfactual test, musí jít o poctivě označený odhad vlivu, nikoliv o falešné tvrzení, že jedna událost výsledek jistě způsobila.

Akce `Test without this event` má dvě pracovní úrovně:

1. `Quick Counterfactual` vytvoří jeden co nejpodobnější replay vybraného scénáře po změně události.
2. `Statistical Counterfactual` spustí více párových simulací se shodnými výchozími podmínkami a koordinovanými seedy, jednou s intervencí a jednou bez ní, a porovná celé distribuce včetně nejistoty.

Podle typu události lze pracovně nabídnout `Remove`, `Replace`, `Adjust`, `Reverse Outcome`, `Neutralize` nebo `Redraw`. Engine vždy nejprve ověří, zda je intervence v daném stavu definovaná a slučitelná s pevnými pravidly. Výsledek lze připnout, porovnat s originálem a explicitně převést na branch.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Counterfactual zásah vytváří jasnou kauzální hranici: celá historie před zvoleným bodem zůstane stejná, v bodě se provede přesně zadaná změna a všechny stavy, které jí mohou být ovlivněny, se odtud znovu nasimulují. Původní budoucnost se nesmí uměle zachovat, pokud její konkrétní části Admin samostatně nezamkne. Obrácený výsledek čtvrtfinále tak může změnit semifinalistu, únavu, další zápasy, body, ranking i dlouhodobý vývoj.

Přesný kauzální model, párování náhodných proudů po strukturální divergenci, katalog povolených intervencí, výpočet příspěvků, confidence contract, výkon a UI side-by-side časových os zůstávají otevřené.

---

# 23. Viewer navigace a stránky

## 23.1 Globální vyhledávání

**[ROZHODNUTO]** Viewer i Admin obsahují klasické globální vyhledávání viditelně umístěné v navbaru.

Má vyhledávat minimálně:

- hráče,
- turnaje,
- země,
- zápasy.

U Tournament Series vyhledává současný i všechny uložené historické názvy; výsledek vede na společnou historii série.

Výsledky musí respektovat aktivní Run, jeho `Viewer Branch` a vybraný week. Vyhledávání nesmí prozradit budoucí data.

**[ROZHODNUTO]** Globální vyhledávání najde také juniory/prospects, kteří ještě nevstoupili na Tour, a otevře jejich juniorský profil.

**[ROZHODNUTO]** Admin vyhledávání může navíc najít administrativní objekty a stránky, které nejsou součástí veřejného Vieweru.

**[ROZHODNUTO]** Klávesová zkratka `Ctrl+K` otevře nebo aktivuje tentýž navbarový vyhledávač; nejde o druhý samostatný systém.

## 23.2 Profily hráčů

**[ROZHODNUTO]** Profil retired hráče zůstává ve Vieweru trvale dostupný.

**[ROZHODNUTO]** Prospect má už před vstupem na Tour vlastní omezený Viewer profil. Po vstupu na Tour pokračuje tentýž profil.

**[ROZHODNUTO]** Historický profil vždy ukazuje věk, status a časově proměnlivé fyzické údaje platné v právě vybraném Viewer weeku. Uživatel tedy vidí, zda byl hráč tehdy například prospect, active, inactive nebo retired; budoucí změny se neprozradí.

**[CÍLOVÁ FUNKCE]** Hráčský profil může obsahovat overview, ranking, výsledky, tituly, statistiky, H2H, ranking history, sezonní timeline, milestones a records.

## 23.3 Juniorský / prospect profil

**[ROZHODNUTO]** Juniorský profil před vstupem hráče na Pro Tour ukazuje:

- jméno,
- stát a vlajku,
- věk,
- `birth_year` a `birth_year_week`, nikoliv přesné kalendářní datum,
- výšku,
- hmotnost,
- dominantní ruku,
- status Junior / Prospect; přesný název statusu se může změnit.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Hráčské portréty se nyní neřeší. Juniorský profil proto může použít neutrální placeholder nebo žádný obrázek.

**[ROZHODNUTO]** Pokud hráč k vybranému Viewer weeku ještě nikdy nevstoupil na Pro Tour, profesionální sekce jsou skryté, nikoliv vyplněné nulami. Skryté jsou zejména:

- Tour ranking a Tour body,
- profesionální bilance a tituly,
- prize money,
- profesionální forma,
- Tour H2H,
- další profesionální kariérní statistiky.

**[ROZHODNUTO]** Viewer před vstupem neukazuje očekávaný ani plánovaný week vstupu na Tour, interní podmínky vstupu ani predikci budoucího vstupu.

**[ROZHODNUTO]** Profil má samostatnou sekci juniorského mistrovství světa, která uchovává:

- výsledky jednotlivých ročníků,
- odehrané zápasy, výhry a prohry,
- počet účastí,
- nejlepší dosažený výsledek,
- počet titulů,
- další souhrnné statistiky vypočítané výhradně z juniorských mistrovství světa.

**[ROZHODNUTO]** Sekce juniorského mistrovství světa existuje i před první účastí hráče. Do té doby je prázdná a může zobrazit krátké sdělení typu `Zatím bez účasti`.

**[ROZHODNUTO]** Po vstupu na Tour zůstávají stejné interní ID, stejný profil a stejná trvalá URL založená na stabilním `player_id`; nevytváří se nový hráčský profil. URL se nemění ani při stavech Junior, Tour Player, Inactive nebo Retired.

**[ROZHODNUTO]** Sekce juniorského mistrovství světa zůstává na profilu navždy. Před vstupem na Tour může být výchozí či výraznou částí; po vstupu se profil standardně otevře na profesionálním přehledu a juniorská sekce zůstane dostupná jako samostatná historická část.

**[ROZHODNUTO]** Obsah profilu se vždy řídí vybraným Viewer weekem. Budoucí vstup na Tour, budoucí profesionální sekce ani pozdější juniorské výsledky se ve starším historickém pohledu nesmějí prozradit.

**[OTEVŘENO]** Přesný název juniorského statusu, grafické rozložení profilu, přesná podoba souhrnných statistik juniorského mistrovství světa a vizuální provedení prázdné juniorské sekce.

## 23.4 MSA navbar

**[ROZHODNUTO V PRINCIPU]** Oficiální MSA web používá klasický stálý vodorovný navbar, nikoliv Admin sidebar. Po najetí myší na hlavní kategorii se rozbalí nabídka jejích dalších stránek; stejná nabídka musí být dostupná také kliknutím a klávesnicí.

**[ODLOŽENO]** Přesné hlavní kategorie, jejich názvy, pořadí a strom podstránek MSA navbaru uživatel navrhne později. V současném bloku byly výslovně přeskočeny a žádný asistentský seznam se proto nepovažuje za rozhodnutý.

**[STARŠÍ SILNĚ ROZPRACOVANÝ NÁVRH]** Dřívější navigace používala:

`MSA | Rankings | Tour | Players | Countries | H2H | Stats | Predictions | Search | Season/Week selector`

Tato struktura je vhodný základ, ale nebyla v aktuálním dialogu kompletně znovu potvrzena.

Možné sekce z předchozího návrhu:

- Rankings a Race,
- Season Hub, Calendar, Current Week a Match Center,
- Players, Prospects a Retired Players,
- Countries a Country Ranking,
- H2H Explorer a Player Comparison,
- Records, Streaks, Awards a Era Rankings,
- Predictions,
- globální Search.

## 23.5 Viewer jako prostředí více veřejných webů

**[ROZHODNUTO]** Viewer není pouze jeden web MSA ani jedna společná stránka s kategorií `Others`. Je to společné read-only prostředí, ve kterém mohou existovat samostatné fiktivní veřejné weby se svou vlastní rolí, značkou, homepage a navigací nad stejným Runem a prohlíženým časem.

**[ROZHODNUTO]** MSA je oficiální sportovní web a současný hlavní předmět návrhu. Obsah, který by v reálném světě nepatřil světové sportovní organizaci, se nemá bezdůvodně schovávat do MSA. Budoucí samostatné weby mohou zahrnout například sázkový web, `FAX Game`, sportovní média nebo analytický web; jejich přesný seznam, názvy a funkce zatím nejsou rozhodnuté a budou se přidávat postupně.

**[ROZHODNUTO]** V levé horní části Vieweru je společné `Viewer` logo. Otevírá rozcestník/seznam všech právě dostupných fiktivních webů vybraného Runu; nejde o domovskou stránku samotného MSA. Vedle něj je logo právě otevřeného webu, například MSA, které vede na homepage tohoto webu a zachovává Run i season/week.

**[ROZHODNUTO]** Globální kontext Runu, season/weeku a přepnutí Viewer/Admin zůstává zachovaný při pohybu mezi veřejnými weby. Pod globálním aplikačním rámcem se může měnit značka, vzhled a navbar právě otevřeného webu.

## 23.6 Historická MSA homepage

**[ROZHODNUTO]** Úvodní stránka MSA je živá titulní stránka oficiální sportovní organizace, ne statický rozcestník. Její obsah se vždy skládá podle globálně vybraného season/weeku.

**[ROZHODNUTO]** Při otevření historického weeku MSA homepage ukazuje svět tak, jak byl v daném okamžiku oprávněně známý: tehdejší probíhající či nejbližší turnaje, již dostupné čerstvé výsledky, tehdejší lídry žebříčků a další veřejné souhrny. Nesmí prozradit pozdější výsledky ani budoucí změny.

**[ROZHODNUTO]** MSA homepage obsahuje automaticky vytvářené veřejné zprávy. Každá zpráva musí být odvozena z jedné nebo více konkrétních strukturovaných událostí veřejné části World Event Logu platné ve zvoleném historickém čase. Text zprávy není novým zdrojem pravdy a nesmí si vymyslet výsledek, důvod, stav ani budoucí informaci, kterou autoritativní data neobsahují.

**[ROZHODNUTO V PRINCIPU]** Veřejné zprávy mohou pokrývat například výsledky, změny žebříčku, rekordy, překvapení, odstoupení nebo rivalry příběhy. Admin může v podporovaném rozsahu upravit jejich veřejné podání, skrýt je nebo ovlivnit jejich redakční prioritu, aniž by tím přepsal zdrojovou World Event.

**[ODLOŽENO]** Zda MSA dostane také samostatnou stránku `News`, na kterých dalších Viewer stránkách či veřejných webech se zprávy použijí, úplný archiv, filtry, layout, textové šablony, styl a přesné redakční workflow.

**[ODLOŽENO]** Přesná skladba, pořadí, velikost a vizuální provedení bloků MSA homepage.

## 23.7 Run switcher a výchozí kontext

**[ROZHODNUTO]** Viewer a Runový Admin mají na každé stránce s aktivním Runem vpravo nahoře trvale dostupný Run switcher. Globální stránky bez Runu jej nemají. Jeho rychlý panel a úplný přehled popisují kapitoly 3.9 a 27.8.

**[ROZHODNUTO]** Po běžném spuštění se otevře `Squash Engine Home`, nikoliv automaticky `Všechny Runy`, oficiální vestavěný GitHub Run ani samostatný mode-choice rozcestník. Na `Všechny Runy` se přechází volbou `Runs`.

**[ROZHODNUTO]** Při přepnutí Admin → Viewer má přednost právě otevřený Admin Run a přesný kontext, nikoliv výchozí oficiální Run.

**[ROZHODNUTO]** Viewer vždy používá `Viewer Branch` zvoleného Runu a při běžném otevření ukáže její nejnovější uložený bod.

## 23.8 Osobní navigace

**[ROZHODNUTO]** Hráče, turnaje, Tournament Series, země, sezony, stránky a další podporované objekty lze označit hvězdičkou jako osobní oblíbené.

**[ROZHODNUTO]** Jeden globální panel `Oblíbené` je dostupný ve Vieweru i Adminu a seskupuje položky podle Runů. Oblíbené položky jsou pouze navigační pomůckou a nijak neovlivňují simulaci.

**[ROZHODNUTO]** Viewer i Admin automaticky vedou osobní seznam `Nedávno navštívené`. Lze z něj znovu otevřít nedávné objekty a jeho historii lze vymazat.

**[ROZHODNUTO V PRINCIPU]** Vlastní kombinaci filtrů a řazení v tabulce nebo seznamu lze uložit pod vlastním názvem jako znovupoužitelný `Saved View`.

**[ROZHODNUTO]** Saved View lze skrýt a později znovu zobrazit ve správci uložených pohledů.

**[ROZHODNUTO]** Pokud Saved View v některém Runu nelze použít kvůli chybějícím polím nebo jinému nekompatibilnímu datovému modelu, skryje se z rychlé nabídky, ale ve správci zůstane dohledatelný s vysvětlením.

**[PROZATÍMNÍ]** Saved Views jsou zatím pouze globální napříč Runy; samostatný Run-only scope se nyní neplánuje.

**[ODLOŽENO]** Přesný počet a řazení nedávných položek, organizace oblíbených do vlastních skupin, ostatní výchozí klávesové zkratky a další správa Saved Views.

## 23.9 Scores a Match Replay

**[ROZHODNUTO PRO PRVNÍ VERZI]** Viewer obsahuje samostatný základní veřejný web `Scores` ve stylu sportovní výsledkové služby. Zobrazuje seznam veřejných simulovaných zápasů, výsledky, podporované veřejné statistiky a vstup do `Match Replay`. Kurzy a skutečné průběžné live zveřejňování ještě nejsou součástí tohoto základu.

**[ROZHODNUTO PRO PRVNÍ VERZI]** Dokončený uložený zápas lze v read-only `Match Replay` postupně přehrát rally po rally z jeho autoritativního logu a uložených Post-Rally State Snapshotů. Replay nic znovu nesimuluje, nelosuje, nevolá současný RNG/model ani nemění; pouze časově přehrává původní skóre, sportovní příčiny, délky, veřejně přípustné stavy a zdravotní či časové události. Stejný uložený zápas proto zůstává totožný i po pozdější změně Match Enginu. Viewer ukazuje pouze veřejné sportovní informace, zatímco Admin může zobrazit interní průběh a skryté detaily, které už autoritativní zápas skutečně obsahuje; integritu ověřuje uložený `match_log_hash`.

**[ROZHODNUTO PRO SOUČASNOU VERZI]** `Scores` pokrývá celý skutečně simulovaný veřejný rozsah: detailně simulovanou část MSA Tour, juniorské mistrovství světa, olympijské hry a případné později přidané veřejné soutěže. Běžné juniorské turnaje se tím nezačínají simulovat.

**[ODLOŽENO]** Přesný layout Scores, chronologické řazení, filtry, štítky soutěží, úplný katalog veřejných statistik, replay ovládání, URL struktura, vizuální styl a případný pozdější live režim. Detailní návrh stránky byl výslovně zastaven, aby se nejprve řešila důležitější funkčnost první verze.

---

# 24. Export, import a přenositelnost

## 24.1 Úplný export Runu

**[ROZHODNUTO]** Run lze exportovat jako kompletní přenositelný balíček.

**[ROZHODNUTO]** Export Runu nabízí tři rozsahy:

1. `Úplný archiv` – celý Run se všemi aktivními i archivovanými branchemi, historií, checkpointy, nastavením a daty,
2. `Vlastní export` – výslovný výběr branchí, checkpointů, hloubky historie a dalších podporovaných datových částí,
3. `Kompaktní snapshot` – pouze aktuální uložený stav jedné vybrané branche bez její staré technické historie.

Úplný export obsahuje všechno:

- veškerý skutečný World, Category, Series a Calendar obsah Runu, jeho Package provenance a zachované unresolved reference,
- informace o případném použití Setup Package; export Runu však není závislý na dostupnosti původních externích zdrojů,
- všech 50 sezon,
- všechny aktivní i archivované branche,
- checkpointy,
- hráče,
- turnaje, losy a zápasy,
- rankingy, statistiky a historii,
- metadata a nastavení.

Export slouží pro:

- zálohu,
- přenos na jiný počítač,
- sdílení,
- další úpravu,
- vložení vlastního lokálního Runu do GitHubu jako vestavěného read-only Runu.

**[ROZHODNUTO]** U vlastního exportu engine automaticky zahrne společnou minulost a všechny povinné závislosti vybraných branchí. Nevalidní nebo neúplnou kombinaci nedovolí vytvořit. Před potvrzením ukáže přesný obsah, vynechané části a odhad výsledné velikosti.

**[ROZHODNUTO]** Recovery Drafty, cache, rozpracované dočasné výpočty a jiné regenerovatelné technické soubory se do žádného exportu Runu nezahrnují.

**[OTEVŘENO]** Přesný formát archivu, komprese, velikost, verzování schématu a případné použití Git LFS.

**[ROZHODNUTO]** Export vždy používá pouze poslední uložený stav. Pokud existují neuložené změny, engine nabídne jejich uložení nebo zrušení exportu.

## 24.2 Import Runu

**[ROZHODNUTO V PRINCIPU]** Exportovaný Run lze znovu importovat a obnovit se všemi daty.

**[ROZHODNUTO]** Import celého Runu nejdříve provede validaci a zobrazí preview obsahu, varování a chyby. Skutečný zápis proběhne až po potvrzení.

**[ROZHODNUTO]** Při konfliktu názvu engine upozorní, navrhne nový jedinečný název a dovolí ho upravit. Import nelze dokončit s neplatným konfliktním názvem.

**[ROZHODNUTO]** Run ze starší podporované verze schématu se nejdříve validuje a migruje jako bezpečná nová lokální kopie. Původní importovaný soubor zůstává beze změny. Před dokončením engine ukáže převáděné části, změny významu, varování a případné již nepodporované funkce.

**[ROZHODNUTO]** Soubor vytvořený novější nepodporovanou verzí se nenačte částečně ani se tiše nepřevede směrem dolů. Import se bezpečně zastaví a přesně oznámí minimální potřebnou verzi enginu. Neznámá data se nikdy potichu nezahodí.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Pokud importovaný Run používá stejné `run_id` jako existující lokální Run, engine jej rozpozná jako jinou verzi stejné identity a nejprve nabídne read-only porovnání. Pracovní možnosti jsou:

- importovat jej jako nezávislou kopii s novým `run_id`,
- obnovit existující Run po automatickém bezpečnostním checkpointu jeho současného stavu,
- při rozdílně rozvětvených historiích načíst import jako kopii nebo novou branch k ručnímu porovnání.

Nic se nesmí automaticky přepsat a dvě divergující historie se nesmějí automaticky sloučit. Toto workflow je silný směr, nikoliv rozhodnuté konečné pravidlo.

**[ODLOŽENO]** Konečné řešení všech konfliktů interních ID, přesné rozpoznání společného předka a definitivní UX obnovy stejného Runu.

## 24.3 Obecný princip přenositelnosti

**[ROZHODNUTO V PRINCIPU]** Prakticky všechny důležité části enginu půjde vhodným způsobem exportovat a importovat: Runy, World Packages, Category Packages, Series Packages, Calendar Packages, Setup Packages, hráče, turnaje, nastavení, historii a další data.

**[ROZHODNUTO]** Package import smí zachovat unresolved reference a neúplný scope podle kapitoly 4.8. Neúplnost sama nezakazuje import; preview musí odlišit `Not included`, `Unresolved` a skutečně `Invalid` data a červeně zablokovat jen operaci, která nevalidní či chybějící vstup potřebuje.

**[ROZHODNUTO]** Každý import nejprve projde validací a preview.

**[ROZHODNUTO]** Obecné tabulkové importy používají vysvětlující a opravitelné staging preview z kapitoly 5.4: žádná data se před potvrzením nezmění, hard errors jsou přesně lokalizované a vysvětlené a částečný import je možný pouze pro prokazatelně nezávislé platné řádky.

**[ROZHODNUTO]** Vestavěná GitHub data nelze importem přepsat. Import může vytvořit novou lokální kopii.

**[ROZHODNUTO][ENGINE INVARIANT]** Přenesený Package si zachovává svůj stabilní `package_id` a číslo verze také na jiném počítači. Běžné uložení, duplikace, obnovení starší verze, archivace a další lifecycle pravidla se řídí kapitolou 4.11.

**[ROZHODNUTO]** Opakovaný import přesně stejného Package a verze nevytváří duplicity. Nezměněná data jsou `Already imported` a nic se nezapíše; lokálně změněná data se nejprve porovnají a řeší bezpečnou výslovnou volbou.

**[ROZHODNUTO]** Package update lze přijmout pouze pro vybranou datově platnou část. Preview znovu validuje její závislosti, ukáže všechny proveditelné možnosti chybějícího navazujícího obsahu a nikdy jej samo skrytě nepřidá.

**[ROZHODNUTO][ENGINE INVARIANT]** Package export vytvoří jeden soubor s přesně uživatelem vybraným rozsahem. Vynechané závislosti se označí a jejich reference se zachovají, ale engine do souboru nic automaticky nepřibalí. Pokud uživatel výslovně vybere více Package payloadů nebo Setup, mohou být součástí téhož zvoleného exportního souboru.

**[ODLOŽENO]** Přesné přípony a vnitřní formáty souborů, komprese, schema migration, nejjemnější podporovaná granularita a ID kontrakty dílčích exportů mimo výše rozhodnutý Package/Run model. Základ tří rozsahů exportu Runu, bezpečný kontrakt kompatibility verzí, identita Package i přesný uživatelsky vybraný Package scope jsou rozhodnuté.

---

# 25. Audit, bezpečné mutace a validace

## 25.1 Audit

**[ROZHODNUTO][ENGINE INVARIANT]** Admin uchovává samostatný `Audit Log`: dohledatelnou historii potvrzených ručních a systémových změn dat, důležitých operací a jejich původu. Audit Log odpovídá na otázku „co změnilo data a odkud změna přišla“; není totožný s historií událostí fiktivního světa, Task Centerem ani seznamem nepřečtených upozornění.

Pokud by audit zabíral příliš mnoho prostoru, může se bezztrátově komprimovat nebo na výslovnou akci uživatele archivovat či vyčistit podle obecných pravidel úložiště. Nic se nesmí potichu odstranit. **[ODLOŽENO]** Přesný retenční model se dořeší podle reálné velikosti dat.

**[ROZHODNUTO PRO LOSY]**

- každá potvrzená ruční změna losu se interně zaznamená,
- důvod nebo poznámka jsou volitelné,
- jednotlivé pohyby pouze uvnitř nepotvrzeného preview se samostatně auditovat nemusí,
- výchozí obrazovka ukazuje současný los,
- samostatná historie umožní dohledat a porovnat předchozí stav.

Zatím se historie uchovává co nejúplněji. Pokud by v reálném provozu zabírala příliš mnoho místa, může se později bezztrátově optimalizovat nebo uživatelsky řízeně archivovat a čistit; engine ji nesmí sám potichu omezit nebo částečně odstranit.

**[ROZHODNUTO V PRINCIPU]** Relevantní datové objekty a důležité změny nesou informaci o svém původu. Admin ji může zobrazit a filtrovat, například jako:

- vestavěné (`Built-in`),
- vytvořené simulací (`Generated/Simulated`),
- importované (`Imported`),
- ručně vytvořené nebo upravené (`Manual`),
- přegenerované (`Regenerated`).

Jde o sjednocení dříve implicitně řešeného auditu, importů, simulace a ručních zásahů do jednoho dohledatelného mechanismu.

**[ODLOŽENO]** Konečné názvy a úplná taxonomie původu, kombinace více zdrojů a přesné dědění provenance při kopírování, importu, větvení a regeneraci.

## 25.2 Bezpečné změny

**[CÍLOVÁ FUNKCE]** Nebezpečné operace musí mít preview, jasný rozsah a výslovné potvrzení.

Patří sem zejména:

- změna minulosti,
- smazání budoucnosti branche,
- velká regenerace hráčů,
- import dat,
- přepsání kalendáře,
- změna `Viewer Branch`.

Neúspěšná operace nesmí zanechat poloviční nebo skrytě nekonzistentní stav.

**[ROZHODNUTO][ENGINE INVARIANT]** Obecný Admin override z kapitoly 2.3 může přepsat sportovní policy, hráčskou AI i běžné automatické rozhodnutí, ale nemůže obejít referenční a logickou integritu. Všechny vzájemně závislé změny se nejprve zobrazí v jednom impact preview a potvrdí jako atomický `Manual Override`; buď se uloží celý konzistentní celek, nebo nic. Zásah vždy zachová Run/branch/time provenance a Audit Log.

**[ROZHODNUTO][ENGINE INVARIANT]** Při importním, aktualizačním nebo identitním konfliktu engine nikdy tajně nevybere jednu stranu. Nabídne všechny právě proveditelné logické a datově bezpečné možnosti a u každé ukáže její dopad; neproveditelnou možnost přesně vysvětlí. Toto pravidlo neznamená, že každý konflikt musí mít stejnou nabídku ani že už jsou rozhodnuté názvy tlačítek a detailní UI.

## 25.3 Úložiště

**[ROZHODNUTO][ENGINE INVARIANT]** Engine nemá umělé kvóty ani pevný limit velikosti Runu, branche, počtu obnovitelných verzí nebo historie. Limitem je skutečně dostupné úložiště počítače. Žádná data se kvůli internímu prahu automaticky nemažou.

**[ROZHODNUTO V PRINCIPU]** Historie, společná minulost branchí a obnovitelné verze se ukládají prostorově úsporně pomocí rozdílových dat, deduplikace a bezztrátové komprese. Periodické úplné technické snapshoty mohou zrychlit načítání, ale nesmějí bezdůvodně duplikovat celý Run po každém Save. Přesná architektura se zvolí podle skutečných měření.

**[ROZHODNUTO]** Admin ukazuje fyzicky zabrané místo minimálně pro celý engine, každý Run, každou branch a významné datové oblasti. U branche oddělí:

- její vlastní unikátní data,
- data sdílená se společnou minulostí nebo jinými branchemi,
- odhad prostoru, který by skutečně uvolnilo její odstranění.

Součet zobrazovaných velikostí nesmí společná deduplikovaná data mylně započítat několikrát.

**[ROZHODNUTO]** Při spuštění engine i v centrálním přehledu úložiště neblokujícím oranžovým vykřičníkem upozorní, že celková spotřeba je vysoká nebo počítači zbývá málo volného prostoru. Nabídne konkrétní bezpečné možnosti, například bezztrátovou optimalizaci, export či archivaci, odstranění zvolených nepotřebných branchí nebo uživatelsky potvrzené promazání vybraných starých běžných verzí, a předem odhadne uvolněné místo.

**[ROZHODNUTO]** Named checkpoints, body vzniku branchí a jiné chráněné stavy se nikdy neodstraní jako vedlejší efekt obecného čištění. Každé ztrátové odstranění vyžaduje výslovný výběr a potvrzení uživatele; automaticky smí proběhnout pouze bezztrátová optimalizace.

**[ROZHODNUTO]** Před uložením, simulací, importem, exportem nebo jinou prostorově náročnou operací engine odhadne potřebné dočasné i trvalé místo včetně rezervy pro atomické dokončení či bezpečný návrat. Pokud prostor skutečně nestačí, zablokuje jen tuto konkrétní operaci a ukáže například potřebnou a volnou kapacitu. Pokud je místa málo, ale pro bezpečné dokončení stále stačí, pouze varuje a dovolí pokračovat.

**[ODLOŽENO]** Číselné hranice varování, přesnost odhadu velikosti a času, konkrétní kompresní a deduplikační algoritmy, interval technických snapshotů a kalibrace dočasné rezervy. Nyní neznáme reálnou spotřebu ani rychlost budoucího detailního enginu; tyto hodnoty se proto budou upravovat podle měření fungujících verzí, nikoliv hádat napevno předem.

## 25.4 Automatická validita Runu

**[ROZHODNUTO]** Každý Run má automaticky vypočítaný souhrnný stav:

- `Valid` – lze normálně pokračovat a simulovat,
- `Warnings` – obsahuje nejméně jedno oranžové neblokující varování; simulovat lze, případně po upozornění,
- `Errors` – obsahuje nejméně jeden červený kritický problém, ale jeho skutečný dopad se posuzuje podle dotčených objektů a požadované operace.

**[ROZHODNUTO]** Validita se přepočítá po každé změně, importu a obnovení verze a znovu bezprostředně před spuštěním simulace. Uživatel ji nemůže ručně nastavit.

**[ROZHODNUTO][ENGINE INVARIANT]** Blokování simulace je operation-scoped. Chyba zablokuje operaci, která potřebuje nevalidní objekt nebo na něm závisí; nesmí automaticky zablokovat všechny ostatní nezávislé a validní části Runu. Souhrnný stav `Errors` je tedy upozorněním na existenci blokující chyby někde v Runu, nikoliv povinným globálním zákazem veškeré simulace.

**[ROZHODNUTO]** Úplně prázdný Run bez Packages a bez vytvořených sportovních objektů může být platným `Working` stavem bez chyby, i když v něm zatím není žádná spustitelná sportovní simulace. `Valid` zde znamená, že přítomná data nejsou neplatná; neznamená, že jsou automaticky splněné prerequisites každého možného rozsahu.

Příklad: neúplný budoucí sezonní kalendář může blokovat simulaci celé sezony, ale ne samostatný validní testovací zápas dvou již vytvořených hráčů. Před každou akcí Admin ukáže konkrétní blokující chyby právě zvoleného rozsahu a oddělí je od nesouvisejících warnings/errors jinde v Runu.

Další příklad: neúplná bodová tabulka Ranked Edition zablokuje její oznámení, zveřejnění hráčům, entry proces a simulaci, ale Edition může zůstat uložená jako interní Draft a jiné turnaje nejsou dotčené. Chybějící či částečné prize money v první verzi nejsou validační chybou; pouze vytvářejí `Unknown` výplaty a `Incomplete / Unknown` celkový prize pool.

**[ODLOŽENO]** Úplná dependency matice objektů a simulačních rozsahů, pravidla propagace závažnosti a přesný UX lokálních i souhrnných validací.

## 25.5 Osobní Admin poznámky

**[ROZHODNUTO]** Admin umožňuje připojit čistě osobní poznámku prakticky ke kterémukoliv podporovanému objektu, například k:

- celému Runu,
- konkrétní branchi nebo checkpointu,
- sezoně nebo weeku,
- hráči,
- Tournament Series nebo Tournament Edition,
- zápasu,
- jinému konkrétnímu objektu enginu.

Poznámka může mít vlastní text, barvu a symbol, včetně vlastního vykřičníku vizuálně odlišného od automatických stavů. Je viditelná pouze v Adminu a sama o sobě nemění stav `Valid / Warnings / Errors` ani neblokuje simulaci. Vyhrazený oranžový a červený vykřičník z kapitoly 25.6 nesmí osobní poznámka napodobovat tak, aby vypadala jako systémové varování nebo kritický problém.

**[ROZHODNUTO]** Runové poznámky zůstávají společné napříč branchemi. Poznámky specifické pro zdrojovou branch se při vytvoření nové branche zkopírují jako snapshot a potom se v obou branchích vyvíjejí nezávisle.

**[ROZHODNUTO]** Poznámka může být `Active` nebo `Resolved`. Vyřešené poznámky se standardně skryjí, ale zůstanou dohledatelné filtrem společně se svou historií úprav.

**[ODLOŽENO]** Připomenutí poznámky při dosažení konkrétního weeku a případné automatické pozastavení simulace bylo přeskočeno.

## 25.6 World Event Log a Notification Center

**[ROZHODNUTO][ENGINE INVARIANT]** Engine rozlišuje čtyři samostatné vrstvy, které se nesmějí vydávat jedna za druhou:

| Vrstva | Hlavní otázka | Typický obsah |
|---|---|---|
| `World Event Log` | Co se stalo ve fiktivním světě? | zápasy a turnaje, změny rankingu, zranění a návraty, retirement, změna reprezentované země, vznik hráče nebo významná změna pravidel světa |
| `Audit Log` | Co změnilo data a odkud změna přišla? | potvrzené ruční editace, importy, regenerace, systémové mutace a provenance |
| `Task Center` | Co engine právě počítá nebo dokončil? | simulace, Forecasty, importy, exporty a validace se stavem, průběhem a výsledkem |
| `Notification Center` | Čemu má Admin věnovat pozornost? | vybraná upozornění odkazující na příslušnou světovou událost, auditní záznam, úlohu nebo validaci |

**[ROZHODNUTO]** `World Event Log` je trvalá chronologická historie skutečností dané časové linie, nikoliv dočasná schránka upozornění. Umožní dohledat, jak a proč vznikl současný stav hráče, rankingu, turnaje, země nebo jiné části světa. Záznam odkazuje na související objekty a podporovaný časový bod; pokud jde o uložený validní bod historie, používá obecné read-only preview, porovnání, obnovu a vytvoření branche z kapitoly 7.

**[ROZHODNUTO]** `Notification Center` je pouze vrstva pozornosti nad zdrojovými záznamy. Označení upozornění jako přečtené, jeho skrytí nebo odstranění ze schránky nikdy nesmaže původní World Event, auditní záznam, výsledek úlohy ani validační problém.

**[ROZHODNUTO]** Upozornění vznikají dvěma způsoby:

1. **automaticky systémem**, například při konfliktu, neplatných datech, ohroženém Future Locku, neúspěšné simulaci nebo rizikové spotřebě úložiště;
2. **podle uživatelských watchlistů**, ve kterých lze sledovat podporovaného hráče, zemi, turnaj, branch nebo jiný objekt a zvolené triggery, například zranění, vstup do Top 10, změnu vedení žebříčku, vygenerování talentu S+ nebo překvapivý výsledek.

**[ROZHODNUTO]** Opakující se související informace a varování se automaticky seskupují do jedné rozbalitelné položky s počtem výskytů. Kritické problémy musí zůstat jednotlivě a výrazně viditelné, aby je souhrn nezakryl.

**[ROZHODNUTO][ENGINE INVARIANT]** Stejný systém závažnosti platí v celém Adminu – v Notification Centeru, formulářích, tabulkách, importech, validacích, Runech, branchích, Packages, Future Locks, úložišti i při simulaci:

| Úroveň | Značení | Dopad |
|---|---|---|
| `Information` | modrá ikona `i` a text | informuje; nic neblokuje a běžící operace pokračuje |
| `Warning` | oranžový vykřičník a text | upozorňuje na riziko nebo doporučenou opravu; operace může pokračovat |
| `Critical` | červený vykřičník a text | označuje chybu, nemožný stav nebo závažný konflikt; zablokuje pouze dotčenou akci, případně běžící simulaci zastaví v nejbližším bezpečném bodě |

**[ROZHODNUTO]** Kritický problém nikdy bezdůvodně nezablokuje celý engine. Ostatní nezávislé Runy, branche a validní operace zůstávají dostupné. U dotčené věci Admin vždy ukáže, co je špatně, proč je to problém a jaké jsou dostupné možnosti nápravy; může mezi nimi být oprava vstupu, vrácení změny, bezpečné zastavení nebo vytvoření nové branche.

**[ROZHODNUTO]** Barva není jediným nositelem významu. Každý stav používá současně odpovídající ikonu a srozumitelný text; najetí nebo kliknutí otevře vysvětlení příčiny, dopadu a možností opravy.

**[ROZHODNUTO]** Notification Center je dostupný přes ikonu zvonku vpravo nahoře na každé Admin stránce. Nabízí scope alespoň `Aktuální branch`, `Celý Run` a `Všechny Runy a Packages`; volby bez smysluplného aktivního kontextu se nezobrazí nebo jsou jasně neaktivní.

**[ROZHODNUTO]** Viewer technická Admin upozornění, Audit Log ani interní validační problémy nezobrazuje. Jeho veřejné zprávy a události smějí vycházet pouze z veřejně známé části World Event Logu platné ve zvoleném historickém čase a nesmějí způsobit future leak.

**[ROZHODNUTO][ENGINE INVARIANT]** Automatická Viewer zpráva je prezentační výstup nad strukturovaným World Eventem, nikoliv pátá autoritativní historie. Úprava, skrytí nebo změna redakční priority zprávy nesmí změnit samotný zápas, ranking, hráčský stav ani zdrojový World Event. Soukromý Admin digest může vedle světových faktů shrnovat také technické úlohy, warnings, critical stavy a Future Locks, ale tento neveřejný obsah se nesmí převést do MSA článku bez samostatného veřejného podkladu.

**[PROZATÍMNÍ, SLABÝ SMĚR]** Každá relevantní událost může mít oddělené `News Importance Score` pro Viewer a Admin. Výpočet může zohlednit prestiž turnaje, překvapivost, význam hráče, změnu rankingu, rekord, rivalitu a další kontext; Admin může zprávu připnout, skrýt nebo její redakční význam upravit. Přesný název, škála, vzorec a automatické prahy nejsou rozhodnuté.

**[ODLOŽENO]** Přesná taxonomie a granularita World Events, pravidla veřejnosti, úplný katalog automatických triggerů, editor watchlistů, možnosti ztišení, seskupovací klíče a časová okna, číselné badge, pořadí a filtry, retenční a storage model, textové šablony, redakční seskupování událostí do příběhů a přesná transformace veřejné události do Viewer zprávy.

---

# 26. Velké samostatné soutěže

**Rozsah celé kapitoly:** jde o obsah a výchozí kalendář **Official Runu**. Engine musí umět tyto soutěžní typy reprezentovat, ale jiný Run nemusí obsahovat žádnou z nich nebo může mít jiné názvy, cykly, formáty a kvalifikace.

Tato kapitola rozlišuje současná rozhodnutí od starších nebo odložených návrhů jednotlivých velkých soutěží.

## 26.1 World Tour Finals

**[STARŠÍ NÁVRH]** Finals jako samostatný vrchol sezony pro osm hráčů kvalifikovaných přes Race.

Preferovaná originální varianta používala jméno `The Eight / Final Eight` a ladder strukturu, ve které lepší Race pozice poskytuje výhodnější cestu. Starší alternativou byly dvě skupiny po čtyřech.

**[ODLOŽENO]** Počet hráčů, kvalifikace, formát, rankingové body a definitivní identita Finals.

## 26.2 Individual World Championship

**[CÍLOVÁ FUNKCE]** Samostatný největší individuální turnaj odlišný od Finals.

**[STARŠÍ NÁVRH]** Umístění přibližně kolem W48–W50 a velmi vysoká bodová tabulka. Konkrétní dřívější čísla nejsou canonem.

## 26.3 Team World Championship

**[ROZHODNUTO]** Official Run obsahuje mužský Team World Championship.

**[ROZHODNUTO]** Team World Championship se koná každý lichý kalendářní rok, tedy jednou za dva roky.

**[ROZHODNUTO]** Každý mezistátní duel obsahuje přesně šest individuálních zápasů. Každý zápas se hraje BO5 do 11 bodů o dva body.

### Rankingový snapshot, soupiska a sestava

**[ROZHODNUTO]** Celé mistrovství používá jediný pevný `Team Championship Ranking Snapshot`. Stejně jako u běžného turnaje jde o poslední dokončený Official MSA Ranking snapshot před rozhodným roster lockem. Pozdější rankingové změny během šampionátu už nominace ani pořadí pozic nemění.

**[ROZHODNUTO]** Hráč, který v tomto rozhodném snapshotu vůbec není klasifikován, nesmí být na turnajovou soupisku nominován ani později použit jako náhrada. Nestačí, že se do rankingu dostane až po roster locku.

**[ROZHODNUTO PRO PRVNÍ PRE-ALPHA VERZI]** K národnímu týmu je způsobilý pouze hráč s typem Sporting Representation `Country` platným k rozhodnému roster locku a reprezentující právě danou zemi. `World` ani `FAX Neutral` nelze nominovat. Team World Championship neobsahuje tým World či Neutral; případný budoucí `World Select` může existovat jen jako oddělená exhibice mimo stav a statistiky tohoto šampionátu.

**[ROZHODNUTO][ENGINE INVARIANT]** Každá týmová Tournament Edition má konfigurovatelný atribut `roster_capacity`, který lze zdědit z vyšší úrovně nebo pro danou Edition přepsat. Engine neurčuje jednu univerzální kapacitu pro všechny týmové soutěže; konkrétní validace se musí řídit formátem dané soutěže. U Team World Championship je rozhodnuto šest pozic v duelu a možnost neúplné sestavy s technickými W/O, nikoliv univerzální minimum atributu pro každou týmovou Edition.

**[ROZHODNUTO][ENGINE INVARIANT]** Každá týmová Tournament Edition má také `roster_lock_week`. Výchozí hodnotou je poslední dokončený week před začátkem šampionátu, ale konkrétní Edition ji může změnit. Rankingový snapshot je navázán právě na tento lock a musí být v Adminu dohledatelný.

**[ROZHODNUTO]** Pro každý mezistátní duel země vybere ze své uzamčené turnajové soupisky až šest dostupných hráčů. Mezi jednotlivými duely lze sestavu měnit.

**[ROZHODNUTO]** Vybranou šestici engine automaticky seřadí podle pevného rankingového snapshotu celého mistrovství. Kapitán nebo výběrová AI smí rozhodnout, kdo nastoupí, ale nesmí hráče takticky přeházet mezi pozicemi. Hraje tedy národní `#1` proti `#1` až `#6` proti `#6`.

### Mimořádné náhrady po roster locku

**[ROZHODNUTO]** Po uzamčení soupisky je náhrada možná pouze kvůli doloženému zranění, nemoci nebo jiné skutečně závažné mimořádné události. Taktická výměna, reakce na formu či ranking nebo snaha zlepšit matchup nejsou povoleným důvodem.

**[ROZHODNUTO]** Každou náhradu jednotlivě schvaluje FAX. Nový hráč musí splnit běžnou reprezentační eligibility a musí být klasifikován už v původním rankingovém snapshotu mistrovství.

**[ROZHODNUTO]** Náhrada je pro danou Tournament Edition trvalá a probíhá jedna za jednoho. Nahrazený hráč je ze soupisky definitivně vyřazen, v pozdější fázi stejného mistrovství se nemůže vrátit a počet hráčů nikdy nesmí překročit `roster_capacity`.

**[ROZHODNUTO]** Počet mimořádných náhrad nemá pevný číselný strop. Každá jednotlivá výměna je však samostatně posuzovaná a má být extrémně vzácná; neomezenost nesmí vytvořit zadní cestu k průběžnému přestavování soupisky.

### Neúplná sestava a technické W/O

**[ROZHODNUTO]** Pokud země pro konkrétní duel nemá šest dostupných oprávněných hráčů, nastoupí všichni dostupní hráči v pořadí podle pevného rankingového snapshotu na nejvyšších obsazených pozicích. Chybějí nejnižší pozice sestavy; například s pěti hráči vznikne W/O na pozici `#6`.

**[ROZHODNUTO]** Technické W/O na chybějící týmové pozici zůstává pro individuální statistiky neodehraným zápasem: nevytváří hráčskou výhru, prohru, H2H ani délku zápasu.

**[ROZHODNUTO PRO TEAM TIE-BREAK]** Pouze pro výpočet výsledku mezistátního duelu, souhrnného rozdílu setů a případně míčů se toto technické W/O započítá ve prospěch soupeřovy země jako `3:0` na sety a `33:0` na míče, tedy ekvivalent tří setů `11:0`. Ve výsledku musí zůstat viditelně označeno jako `W/O`, nikoliv jako skutečně odehraný zápas.

**[POZDĚJI]** Ve fiktivním světě FAX by neschopnost země postavit plnou sestavu vedla také k vysoké pokutě. Výše, workflow ani ekonomický dopad této pokuty se nyní nesimulují a nejsou součástí současného pravidlového modelu.

**[ROZHODNUTO]** Pokud šest dvouher skončí `3:3`, vítěze země určí v tomto pořadí:

1. lepší souhrnný rozdíl vyhraných a prohraných setů ve všech šesti dvouhrách,
2. při shodě lepší souhrnný rozdíl získaných a ztracených míčů ve všech šesti dvouhrách,
3. při úplné shodě vítěz dvouhry hráčů na pozici číslo 1.

**[STARŠÍ NÁVRH]** Dříve se uvažoval dvouletý cyklus, W23–W24 a field 32 nebo 48 zemí.

**[ODLOŽENO]** Počet zemí, kvalifikace, skupinová a vyřazovací struktura, přesný turnajový formát, kalendářní weeky, konkrétní výchozí `roster_capacity` jednotlivých Editions, úplný seznam uznávaných důkazů a Admin workflow náhrad a přesné pořadí odehrání šesti dvouher. Otázka skupin a play-off byla výslovně přeskočena. Dříve navržené automatické pořadí od pozice `#6` k `#1` bylo odmítnuto; pořadí rozhodně nemá být mechanicky od nejhorších hráčů k nejlepším.

## 26.4 Kontinentální mistrovství

**[ROZHODNUTO]** Official Run obsahuje individuální mistrovství pro každý kontinent.

**[ROZHODNUTO]** Official Run obsahuje také týmové mistrovství pro každý kontinent.

**[ROZHODNUTO][ENGINE INVARIANT]** Engine těmto soutěžím nevynucuje jeden globální roční či víceletý cyklus. Periodicita, konkrétní sezony a weeky jsou konfigurací Tournament Series/Editions daného Runu a mohou se v historii změnit stejně jako u ostatních turnajů.

**[ROZHODNUTO][RUN CONFIG]** Konkrétní periodicita zde není stanovena: zda budou individuální nebo týmová kontinentální mistrovství v Official Runu každoročně, ob rok nebo jinak, určí uživatel při tvorbě obsahu Runu. Není to nevyřešená otázka funkčnosti enginu a nemá se znovu pokládat jako engine rozhodnutí.

**[ODLOŽENO]** Přesné formáty, kvalifikace, počet účastníků, soupisky, bodování, umístění v kalendáři a řešení nerozhodného týmového skóre.

## 26.5 Národní mistrovství

**[ROZHODNUTO V PRINCIPU][OFFICIAL RUN DEFAULT]** Official Run bude obsahovat národní mistrovství jednotlivých zemí. Nebudou vznikat automaticky ve všech zemích najednou; budou se přidávat postupně spolu s rozšiřováním světa, počtu hráčů a simulovaného squashového prostředí.

**[PROZATÍMNÍ][OFFICIAL RUN DEFAULT]** V první fázi budou národní mistrovství pouze u největších squashových zemí. Později se budou postupně přidávat také u menších zemí.

**[OTEVŘENO]** Přesný počáteční seznam zemí, termíny zavedení dalších mistrovství, eligibility, formáty, kapacity, bodování, prize money a umístění v kalendáři.

## 26.6 IFSL a ligový squash

**[POZDĚJI]** Ligový/klubový squash může patřit do stejného fiktivního univerza, ale není současnou prioritou Squash Enginu.

Starší ligový návrh připouštěl remízy v týmovém výsledku. To není v rozporu s pravidlem, že jednotlivá dvouhra nikdy remízou skončit nesmí.

## 26.7 Olympijské hry

**[ROZHODNUTO PRO SOUČASNOU VERZI][OFFICIAL RUN DEFAULT]** Olympijské hry jsou vedle MSA Tour a juniorského mistrovství světa součástí veřejně simulovaného rozsahu Official Runu. Jejich zápasy se simulují stejným Match Enginem a ukládají se do Scores, statistik a Match Replay.

**[ODLOŽENO]** Periodicita, sezonní a weekové umístění, eligibility, kvalifikace, počet hráčů, formát, bodování, veřejná značka a ostatní olympijská pravidla. Jde o obsah Official Runu, nikoliv o další univerzální soutěž vnucenou všem Runům.

---

# 27. Design a UX

**[PROZATÍMNÍ, SILNÁ PREFERENCE]** Vzhled má být prémiový, praktický sports-manager/sports-data styl.

- vysoká čitelnost,
- jasná hierarchie,
- žádné překrývající se panely,
- přehledné tabulky optimalizované pro desktop,
- nejprve srozumitelný souhrn, technické detaily až níže,
- výrazné rozlišení Vieweru a Adminu,
- jasné oddělení preview od skutečné mutace,
- žádný zbytečně přehnaný neonový nebo sci-fi vzhled.

**[ROZHODNUTO]** Aplikace nemá samostatnou landing page s velkými kartami `Viewer / MSA Website` a `Admin / Engine`. Běžnou úvodní stránkou je neutrální `Squash Engine Home` s globálními vstupy `Runs` a `Packages`; nejde o volbu módu. Viewer lze otevřít až nad konkrétně zvoleným Runem.

## 27.1 Jazyk

**[ROZHODNUTO]** Rozhraní podporuje pouze češtinu a angličtinu. Jeden globální přepínač jazyka platí současně pro Viewer i Admin.

**[ROZHODNUTO]** Překládají se systémové a uživatelské prvky rozhraní. Uživatelské a historické vlastní názvy, například jména hráčů, vlastní názvy turnajů, názvy branchí a osobní poznámky, se automaticky nepřekládají.

**[ROZHODNUTO]** Země mohou mít český i anglický lokalizovaný název pod stejným stabilním ID nebo kódem. Pokud překlad v jednom jazyce chybí, použije se dostupný název jako fallback.

## 27.2 Jednotky a měny

**[ROZHODNUTO]** Engine používá pouze metrické jednotky: výška v centimetrech a hmotnost v kilogramech. Přepínání na stopy, palce ani libry se v současném rozsahu nedělá.

**[ROZHODNUTO]** Reporting currency je globální uživatelská zobrazovací volba. Datová pravidla původních měn a historických přepočtů popisuje kapitola 19.

## 27.3 Vzhled a přístupnost

**[ROZHODNUTO]** Aplikace má globální volbu vzhledu `Light / Dark / System`.

**[ROZHODNUTO]** Viewer a Admin zůstanou jasně rozlišitelné akcentní barvou a viditelným textovým označením aktivního módu.

**[ROZHODNUTO]** Důležitý stav se nesmí sdělovat pouze barvou. Warning, Error, osobní Admin poznámka a stav simulace používají kromě barvy také ikonu, text nebo jiný jednoznačný znak.

**[ROZHODNUTO]** Automatické stavy používají napříč celým Adminem stejnou sémantiku z kapitoly 25.6: modré `i` informuje, oranžový vykřičník varuje bez blokování a červený vykřičník blokuje nebo bezpečně zastaví pouze dotčenou operaci.

## 27.4 Podporovaná zařízení

**[ROZHODNUTO PRO SOUČASNOU VERZI]** Squash Engine se navrhuje jako desktopová aplikace. Mobilní ani plnohodnotné responzivní zobrazení se nyní neřeší; může být přidáno až v budoucí verzi.

## 27.5 Hromadný výběr v Adminu

**[ROZHODNUTO]** Vhodné Admin tabulky a seznamy používají checkboxy pro výběr více položek, například hráčů, turnajů, Tournament Editions, zemí, Runů nebo branchí.

**[ROZHODNUTO]** Nabídnou se pouze hromadné akce platné pro všechny právě vybrané objekty. Před skutečným provedením se zobrazí preview dopadů, validace a potvrzení.

**[ROZHODNUTO]** Celá potvrzená hromadná operace zůstává až do uložení jedním společným krokem v `Undo`.

## 27.6 Globální horní lišta

**[ROZHODNUTO]** Hlavní Runové kontextové ovladače jsou vpravo nahoře a zůstávají dostupné na každé stránce s aktivním Runem. Jejich základní pořadí je:

- ve Vieweru: `Run → Čas (sezona/week) → Viewer/Admin`,
- v Adminu: `Run → Branch → Čas (sezona/week) → Viewer/Admin`.

Globální vyhledávání a dříve rozhodnutá zkratka `Ctrl+K` zůstávají součástí globálního aplikačního rámce; jejich přesné umístění vůči uvedené kontextové skupině se doladí při návrhu celé horní lišty.

**[ROZHODNUTO]** Na každé Admin stránce je v pravé horní oblasti dostupný zvonek Notification Centeru. Jde o globální vrstvu upozornění; jeho filtry se podle kontextu přepínají mezi aktuální branchí, celým Runem a všemi Runy a Packages podle kapitoly 25.6.

**[ROZHODNUTO]** Na globálních stránkách bez aktivního Runu se skupina Run/Branch/Čas vůbec nezobrazuje. Viewer volba zůstává viditelná, ale neaktivní s vysvětlením `Nejdříve otevři Run`; naposledy otevřený Run se nesmí použít skrytě.

**[ROZHODNUTO]** Branch selector je dostupný pouze v Adminu a vždy se vztahuje k právě vybranému Runu. Viewer žádný volič branchí nezobrazuje, neodhaluje existenci alternativních branchí a automaticky používá `Viewer Branch` vybraného Runu.

## 27.7 Rychlý Branch switcher

**[ROZHODNUTO V PRINCIPU]** Po kliknutí na aktivní branch zobrazí Admin kompaktní rychlý panel nejvýše pěti branchí aktuálního Runu včetně právě vybrané. Aktuální branch je jednoznačně označená, přednost mají branche označené hvězdičkou a zbývající místa doplní naposledy otevřené branche.

Panel vhodným kompaktním způsobem rozliší `Viewer Branch` a může ukázat relevantní stav běžící simulace, neuložených změn nebo validity. Tlačítko `Všechny branche` otevře úplnou správu branchí včetně již rozhodnuté interaktivní mapy větvení a propojené časové osy. Přesný vzhled řádků, badge a prioritizace při více než pěti oblíbených položkách se ještě může doladit.

## 27.8 Úplné přehledy Runů a branchí

**[ROZHODNUTO]** `Všechny Runy` a `Všechny branche` jsou plné stránky, nikoliv rozbalené obří varianty rychlých switcherů. Rychlé panely slouží pouze ke změně současného kontextu. `Všechny branche` nese úplnou Admin správu branchí; `Všechny Runy` je naproti tomu neutrální globální stránka mimo oba módy a její obsah se nepřestavuje podle Viewer/Admin.

**[ROZHODNUTO]** Runy jsou na úplné stránce zobrazené jako široké řádky pod sebou, nikoliv jako mřížka velkých karet. Kliknutí na řádek vyvolá tři akce `Otevřít v Adminu`, `Otevřít branche` a `Otevřít ve Vieweru` popsané v kapitole 3.9.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Každý řádek může viditelně obsahovat hvězdičku, název, krátký popis, aktuální season/week `Viewer Branch`, počet branchí, lifecycle stav, poslední aktivitu, fyzickou velikost a případný vykřičník. Jde pouze o pracovní obsahový návrh; přesné položky se rozhodnou později.

**[OTEVŘENO]** Přesné rozdělení vestavěných, lokálních a archivovaných Runů, konečná sada údajů v řádku, řazení, filtry, rozložení tří akcí a další správa celé stránky. Rozhodnuté jsou neutralita vůči módu, řádkové zobrazení, tři způsoby otevření Runu, absence mode-choice landing page a dostupnost Viewer/Admin přepínání až po otevření Runu.

## 27.9 Admin sidebar

**[ROZHODNUTO]** Hlavní navigaci Adminu tvoří skrývací levý sidebar. V rozbaleném stavu ukazuje ikony a názvy sekcí; ve sbaleném stavu zůstává úzký pruh ikon, aby byla hlavní navigace stále okamžitě dostupná. V malém okně se může skrýt úplně a otevřít jako dočasná vrstva.

**[ROZHODNUTO]** Sidebar je kontextový. V globálním Admin scope ukazuje pouze globální správu, například `Runs` a `Packages`. Po otevření Runu se přepne na Runové administrační sekce a nemíchá obě sady do jednoho obřího menu. Návrat do globálního scope zajišťuje logo Squash Engine.

**[ROZHODNUTO V PRINCIPU]** Najetí na úzký pruh sidebar dočasně vysune do plné šířky jako vrstvu nad stránkou, takže se hlavní obsah kvůli krátkému otevření neposouvá. Po opuštění celé oblasti se sidebar s krátkým ochranným zpožděním znovu sbalí; přesná délka zpoždění a animace jsou implementační detaily.

**[ROZHODNUTO V PRINCIPU]** Najetí na kategorii rozbalí její podstránky svisle přímo pod ní a následující kategorie posune níže uvnitř sidebaru. Přechod kurzoru do podnabídky ji nesmí zavřít. Současně se rozbaluje nejvýše jedna kategorie a aktivní kategorie i stránka zůstávají jednoznačně zvýrazněné také po opětovném otevření sidebaru.

**[ROZHODNUTO V PRINCIPU]** Uživatel může sidebar připnout, aby zůstal trvale otevřený při delší práci. Volba připnutí se na daném zařízení zapamatuje; při dočasném vysunutí se automaticky otevře kategorie současné stránky.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Současný pracovní strom hlavních kategorií Runového Adminu je:

1. `Home`,
2. `World`,
3. `Players`,
4. `Tour`,
5. `Rankings & Analytics`,
6. `Simulation`,
7. `History`,
8. `Data`,
9. `Settings`, vizuálně oddělené u spodního okraje.

Celé toto složení je jediný společný silný směr: názvy, pořadí, počet kategorií, jejich skupiny i rozdělení podstránek nejsou definitivně rozhodnuté. `Tour` je zatím vhodnější pracovní název než příliš úzké `Seasons`; obecná samostatná kategorie `Results` se nyní nenavrhuje, protože výsledky mají zůstat také u zdrojových turnajů, zápasů a sezon.

**[ODLOŽENO]** Přesné ikony, konečný obsah kategorií, navigace při neuložené práci, chování kliknutí na samotný název kategorie tam, kde nemá vlastní Overview, a případné jemnější uživatelské nastavení hover/pin režimu.

## 27.10 Viewer navbar a veřejné weby

**[ROZHODNUTO]** Viewer nepoužívá Admin sidebar. Právě otevřený fiktivní web má vlastní stálý vodorovný navbar; najetí na kategorii rozbalí její podstránky a stejná navigace je dostupná také kliknutím či klávesnicí.

**[ROZHODNUTO]** Jednotlivé veřejné weby mohou pod společnou globální lištou používat vlastní logo, vizuální identitu a vlastní strom stránek. Přechod mezi nimi nemění zvolený Run ani časový kontext.

**[ODLOŽENO]** Přesný vizuální vztah globální lišty a navbaru konkrétního webu, včetně toho, zda budou tvořit jeden nebo dva fyzické řádky. Přesné kategorie MSA navbaru byly výslovně přeskočeny a navrhne je později uživatel.

## 27.11 Kontextové přepínání Viewer/Admin

**[ROZHODNUTO]** Přepínač módů funguje jako kontextový odkaz na tentýž objekt, ne jako prostý návrat na naposledy navštívenou titulní stránku. Přenáší Run, sezonu/week, objekt a podle možností také odpovídající podstránku.

**[ROZHODNUTO]** Viewer vždy řeší cíl v současné `Viewer Branch`. Neexistující nebo neveřejný přesný protějšek vede na nejbližší smysluplnou stránku s jasným vysvětlením; až posledním fallbackem je hlavní stránka MSA nebo Adminu.

## 27.12 Globální kořen a hierarchie log

**[ROZHODNUTO]** `Squash Engine Home` je úplný globální kořen aplikace. V současném rozsahu nabízí `Runs` a `Packages`; přesný vzhled, souhrnné údaje a případné další globální oblasti se navrhnou později.

**[ROZHODNUTO]** Levá část Admin hlavičky používá tuto hierarchii:

- logo `Squash Engine` vždy otevře `Squash Engine Home`,
- pouze v Runovém Adminu je vedle něj obecná společná Run ikona doplněná názvem současného Runu; kliknutí otevře jeho `Home`,
- na globálních Package a dalších stránkách bez Runu se Run ikona ani název nezobrazují.

Vlastní logo pro každý jednotlivý Run není potřeba; všechny Runy mohou používat stejnou obecnou ikonu.

**[ROZHODNUTO]** Levá část Viewer hlavičky používá jinou dvoustupňovou hierarchii:

- společné `Viewer` logo otevře rozcestník veřejných webů současného Runu,
- logo právě otevřeného webu otevře jeho vlastní homepage.

Viewer logo i logo webu zachovávají současný Run a prohlížený season/week. Původně navržená univerzální ikona domečku nebo mřížky už pro tento účel není potřeba.

## 27.13 Globální a Runový Admin scope

**[ROZHODNUTO]** Admin rozlišuje dva jasné kontexty:

- `Global Admin` – správa Runů, zdrojových Packages a dalších dat nezávislých na konkrétním Runu; nemá aktivní Run, branch ani week,
- `Run Admin` – práce uvnitř konkrétního Runu a aktivní branche se season/week kontextem.

Přechod na globální Package stránku opustí Runový scope, ale nesmí zahodit neuloženou práci. Přesné chování návratu, případné uchování rozpracovaného Runového kontextu a upozornění při navigaci se rozhodne společně s širším Save/Draft UX.

## 27.14 Run Home

**[ROZHODNUTO]** Hlavní stránka konkrétního Runu se v navigaci i hlavičce označuje `Home`. Nejde o globální `Squash Engine Home`: první patří vybranému Runu a aktivní branchi, druhá je kořenem celé aplikace bez Runového kontextu.

**[ROZHODNUTO]** Run Home zobrazuje, ve které ze současných 50 sezon se Run nachází, a pod údajem používá segmentovaný ukazatel s jedním segmentem pro každou sezonu. Stejně zobrazuje současný week a druhý segmentovaný ukazatel s jedním segmentem pro každý z 61 weeků sezony. Současná pozice musí být na obou ukazatelích jednoznačně rozsvícená či jinak zvýrazněná.

**[PROZATÍMNÍ SMĚR]** Run Home může obsahovat soukromý Admin přehled poslední větší simulace nebo zvoleného období: důležité výsledky a změny, rekordy, překvapení, warnings, critical problémy a stav Future Locks. Jde o pracovní nástroj pro uživatele enginu, nikoliv o veřejně formulované zprávy pro diváky. Podrobný neblokující post-simulační digest popisuje kapitola 17.3.

**[ODLOŽENO]** Přesné barvy dokončených, současných a budoucích segmentů, případná klikatelnost segmentů, vztah ukazatelů k prohlíženému historickému času oproti nejnovějšímu stavu branche, konečný layout případného soukromého digestu a všechny další bloky Home. Je potvrzené, že na Home později bude více obsahu, ale nyní se nemá předčasně zaplnit nahodilými widgety.

## 27.15 Přehledové stránky kategorií a World

**[PROZATÍMNÍ, SILNÝ SMĚR]** Větší Run Admin kategorie mohou mít vlastní `Overview`: nahoře krátký souhrn hlavních informací a pod ním přehledné bloky odkazující na podstránky téže kategorie. Blok nemá být pouze prázdné tlačítko; může ukázat krátký popis, několik nejdůležitějších údajů nebo upozornění. Stejné cíle jsou současně dostupné v rozbalené nabídce sidebaru. Přesné použití tohoto vzoru u každé jednotlivé kategorie se ještě může lišit.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Současný pracovní strom kategorie `World` tvoří:

- `World Overview` – hlavní informace o světě a bloky s náhledy a odkazy na ostatní World stránky,
- `Countries` – seznam zemí, jejich profily a data konkrétních zemí,
- `Population & Demography` – populační vývoj napříč zeměmi a časem, porovnávání a případné hromadné datové operace,
- `Talent Preview` – pravděpodobnostní náhled potenciálových tříd hráčů, kteří se mohou objevit ve zvoleném období, včetně očekávaného rozdělení podle zemí.

Celý seznam, jeho názvy, pořadí i přesné hranice stránek zůstávají pouze silným směrem. `World Overview` není závislé na mapě fiktivního světa. Mapa se může v budoucnu přidat, pokud vznikne použitelný podklad, ale její obtížné vytvoření nesmí blokovat tuto stránku. `Talent Preview` pracuje s pravděpodobnostmi generačního prostředí zemí; již skutečně vzniklí konkrétní hráči patří do `Players`.

**[OTEVŘENO]** Samostatné budoucí stránky `Regions & Groups`, `World Events` a `Names & Identity Data` mohou vzniknout teprve tehdy, až pro ně bude dost skutečných funkcí. Do současného stromu se nepřidávají jen kvůli úplnosti.

## 27.16 Rankings & Analytics jako pracovní kategorie

**[PROZATÍMNÍ, SILNÝ SMĚR]** `Rankings & Analytics` má být samostatnou Run Admin kategorií, protože Admin musí nejen nastavovat vstupy, ale také kontrolovat, vysvětlovat a případně přepočítávat odvozená data. Pracovní podstránky jsou:

- `Rankings` – současné a historické pořadí, změny, body, vysvětlení výpočtu a diagnostika,
- `Ratings` – Elo a pozdější alternativní ratingové modely, jejich verze, nastavení a porovnání,
- `Odds` – pravděpodobnosti výsledků, výpočet kurzů a později modely či marže jednotlivých fiktivních sázkových webů,
- `Statistics / Reports` – filtrované statistiky, srovnávání a další analytické výstupy.

**[PROZATÍMNÍ, SILNÝ SMĚR]** Hranice odpovědností je zatím tato: `Tour` nastavuje oficiální sportovní pravidla rankingu, bodování a soutěží; `Rankings & Analytics` ukazuje a vysvětluje jejich vypočtené výsledky a spravuje analytické modely jako Elo nebo kurzy; správa konkrétního Viewer webu později určí, který model a jakým způsobem veřejně zobrazuje. Konečný název kategorie, podstránky i přesné rozdělení zůstávají otevřené.

---

# 28. Přehled nyní pevně rozhodnutých základů

Následující seznam je rychlá kontrola nejdůležitějších pravidel potvrzených v tomto konkrétním chatu:

**Rozsah tohoto seznamu:** technické schopnosti a bezpečnostní kontrakty jsou Engine invarianty. Sportovní hodnoty, věkové hranice, názvy a cykly soutěží, kategoriální katalogy, bodování, počty, formáty a policy jsou naopak **Official Run defaulty**, pokud daný bod výslovně neříká něco jiného. Jejich uvedení v seznamu „pevně rozhodnutých“ znamená, že jsou pevně rozhodnuté pro svůj rozsah, nikoliv že je engine vnucuje každému Runu.

1. Engine dělá pouze mužský squash a jednotlivé zápasy jsou pouze dvouhry.
2. Viewer je vždy read-only; změny patří pouze do Adminu.
3. Produkt je pro jednoho uživatele bez účtů, rolí a přihlašování.
4. Každý Run má přesně 50 sezon `2000/01–2049/50`, každá má 61 weeků a za poslední sezonu nelze pokračovat.
5. Mohou existovat prázdné weeky i neomezený počet souběžných turnajů.
6. Run lze vytvořit úplně prázdný bez Package nebo Setup Package. Obsah může vzniknout ručně nebo jednorázovým importem volitelných balíčků kdykoliv později; absence blokuje pouze operaci, která daná data skutečně potřebuje.
7. `Official FAX World` a `Official FAX Category Package` jsou nabízené Official Run defaulty, nikoliv povinné součásti Runu.
8. Vestavěné GitHub Runy a zdrojové balíčky jsou read-only; obsah zkopírovaný do editovatelného lokálního Runu lze měnit pouze pro tento Run. Změna zdroje existující Run sama nezmění.
9. Každý Run má neustále jednu `Viewer Branch`; pouze ona určuje, kterou uloženou časovou linii zobrazuje Viewer, ale ostatní branche tím nejsou méně důležité.
10. Branch lze vytvořit z uloženého bodu včetně poloviny turnaje po konkrétním zápase.
11. Názvy branchí jsou v rámci Runu jedinečné a jejich popis je volitelný.
12. Vše archivované lze obnovit. Trvale smazat lze lokální objekt až z archivu po potvrzení.
13. Completed Run se automaticky nearchivuje a lze z něj větvit alternativní historii.
14. Po běžném spuštění aplikace se otevře neutrální `Squash Engine Home` s volbami `Runs` a `Packages`; samostatný rozcestník Viewer/Admin ani automatické otevření Runu se nepoužívají.
15. Viewer a Runový Admin mají na každé stránce s aktivním Runem vpravo nahoře stálý Run switcher; při změně se podle dostupnosti zachová typ stránky i zvolená sezona/week. Globální stránky bez Runu jej nemají.
16. Viewer standardně otevře nejnovější uložený bod vybraného Runu.
17. Viewer ukáže probíhající week, ale pouze jeho dokončené a uložené části. Budoucí week neukáže.
18. Historický Viewer stav počítá data pouze do konce zvoleného weeku včetně.
19. Neuložené změny z Adminu se ve Vieweru nikdy neprojeví.
20. Nový hráč se objeví přesně ve weeku svých 15. narozenin jako prospect.
21. Prospect je od té chvíle viditelný v Adminu a v samostatné juniorské Viewer sekci, má profil a je globálně vyhledatelný.
22. Prospect vstoupí na MSA Tour prvním platným podáním přihlášky do turnaje MSA Tour, i když se nedostane přes cut; u wild card až jejím definitivním přidělením do fieldu, které se považuje za implicitně přijaté bez samostatné accept akce. Pokračuje tentýž profil i trvalá URL. Každý automaticky vygenerovaný prospect nakonec na Tour vstoupí, přičemž od 15 let nemá další pevný maximální vstupní věk. Juniorské mistrovství světa samo vstup nespouští a běžná juniorská zápasová historie se nesimuluje.
23. Počáteční aktivní hráči mají 15–45 let a již retired předhistorické hráče nepotřebujeme.
24. Admin může v principu ručně vytvořit hráče ve věku 15–45 let kdykoliv během Runu.
25. Hráč stárne ve svém birth weeku a ve 46 letech automaticky končí bez možnosti návratu.
26. Inactive a retired jsou odlišné stavy; dobrovolný retirement je možný v kterémkoliv weeku. Hráč, který skončil před 46 lety, se může vrátit výjimečně automaticky simulací nebo ručně v Adminu.
27. Engine nepoužívá hráčské licence. Hráči po vstupu na Tour zůstávají v MSA rankingu, dokud nejsou retired, i jako inactive a s 0 body.
28. Hráči mohou mít shodná jména; rozlišuje je interní ID. Mohou mít přezdívky, handedness, výšku a hmotnost.
29. Locked Players existují; ručně vytvořený hráč je locked, ale lze ho odemknout.
30. Výchozí zápas je BO5 do 11 o dva body, ale formát lze měnit i podle kola.
31. Individuální zápas nikdy nekončí remízou. Podporuje RET, W/O, DQ a neutrální ABN/No Contest.
32. Ukládá se přesné skóre jednotlivých setů a u každého zahájeného zápasu také celková skutečná délka v sekundách. W/O má délku `null`; RET, DQ a ABN po zahájení uchovají skutečně odehraný čas.
33. Tournament Series si zachovává společnou historii přes trvalé `series_id`, i když turnaj změní název, kategorii, místo, week, formát nebo jiný sezonní parametr.
34. Ranking se aktualizuje týdně a po každém dokončeném weeku vznikne během přechodu do dalšího weeku nový oficiální snapshot označený tímto novým weekem, i beze změny.
35. Turnajové body se přidělí až po dokončení celého turnaje nebo jeho formálním terminálním uzavření jako Abandoned, poprvé se objeví v následujícím weeku a jejich výchozí platnost je 61 weeků; dočasné Suspended je neaktivuje a Admin může dobu platnosti konkrétního turnaje výjimečně změnit s varováním.
36. První sezona Official Runu používá Best 15; v každé sezoně se podle jejího právě platného Best N vybírají nejvyšší platné bodové výsledky a žádný turnaj se nepočítá povinně. Při rovnosti bodů nevzniká sdílené pořadí: rozhodne skladba Best N výsledků, jejich recency, předchozí Official Ranking a nakonec stabilní reprodukovatelný token.
37. Official Ranking je výchozí a Live Ranking dopočítává nejnovější uložený průběžný stav.
38. Historické live rankingové snapshoty se neukládají; vypočítají se z autoritativních dat.
39. Totéž platí pro live H2H, statistiky a rekordy.
40. Globální Viewer search respektuje Run, jeho `Viewer Branch` a časový bod.
41. Retired profily zůstávají trvale ve Vieweru.
42. Ukládání je ruční, včetně výsledků simulace; při odchodu s neuloženými změnami se zobrazí varování.
43. Delší simulace probíhá postupně; lze ji okamžitě pozastavit, bezpečně zastavit po právě zpracovávaném zápase nebo jí naplánovat zastavení v podporovaném budoucím bodě.
44. Run lze kompletně exportovat pouze z posledního uloženého stavu.
45. Prakticky všechny důležité datové oblasti půjdou nějakým způsobem exportovat a importovat, včetně World, Category, Series, Calendar a Setup Packages.
46. Import vždy nejprve projde validací a preview; vestavěná GitHub data jím nelze přepsat.
47. Zobrazované názvy Runů jsou jedinečné napříč aktivními i archivovanými Runy a archiv název rezervuje; skutečnou identitu určuje `run_id`. Konflikt při kopírování nebo importu nabídne upravitelný jedinečný odvozený název a kolizní název nelze uložit.
48. Disciplinární zákazy, suspendace a dopingové případy jsou součástí světa. U entry konfliktů je rozhodnutý odečet bodů a časově omezená Disciplinary Zero podle bodu 253; úplná disciplinární taxonomie a kalibrace se vyřeší později. Samotný nástup zraněného či nemocného hráče ani pozdější zveřejnění stavu se v současném rozsahu netrestá.
49. Official Run obsahuje Team World Championship každý lichý rok. Duel tvoří šest dvouher `#1` proti `#1` až `#6` proti `#6`; sestavu určuje výběr z širší uzamčené soupisky a jeden rankingový snapshot před roster lockem pro celý turnaj. Edition má vlastní `roster_capacity` a `roster_lock_week`; neklasifikovaní hráči nemohou být nominováni. Mimořádné náhrady jsou jedna za jednoho, trvalé pro Edition, schvalované FAX a bez pevného početního stropu. Chybějící spodní pozice vytvářejí technické W/O `3:0 / 33:0` pouze pro týmové součty. Stav 3:3 rozhoduje rozdíl setů, potom rozdíl míčů a nakonec vítěz zápasu pozic #1.
50. Official Run obsahuje individuální i týmové mistrovství každého kontinentu.
51. Současným oficiálním testovacím základem jsou World, Elite, Challenger a Development Tour s kategoriemi vypsanými v kapitole 14. Category Package používá hierarchii `Competition System → volitelný Tour → Category`; tyto entity se mohou historicky měnit, mají stabilní číselná ID a použité identity se nesmějí tvrdě smazat.
52. V současné verzi se zápasy a turnaje detailně simulují pouze na World Tour a Elite Tour.
53. Klasický turnajový pavouk má kapacitu v mocnině dvou; prázdné sloty jsou BYE a počet seedů je `min(field, max(1, capacity/4))`.
54. Los používá idealizované sloty; seed skupiny se náhodně rozdělují pouze uvnitř povolených sektorů a nenasazení se losují bez ochrany podle země, klubu či H2H.
55. Prvotní BYE obsazují nejvyšší idealizované sloty. Pozdě vzniklé BYE zůstává přesně v uvolněném fyzickém slotu.
56. Objekty Q1, Q2 atd. jsou trvale propojené s konkrétní kvalifikací a lze je přesouvat pouze i s tímto propojením.
57. První verze podporuje pavoukové a skupinové kvalifikace; pavouk je výchozí.
58. Všechny Q pavouky jednoho turnaje mají stejnou kapacitu, používají společné seed vrstvy a BYE vrstvy a každý produkuje právě jednoho hráče do svého Q slotu.
59. Všechny kvalifikační skupiny jednoho turnaje jsou stejně velké, mají minimálně tři hráče, hrají každý s každým jednou a každá produkuje jednoho vítěze do jednoho Q slotu.
60. LL sloty se číslují pořadím vzniku. V pavoukové kvalifikaci určuje LL pořadí nejdříve dosažené kolo a potom rozhodný rankingový snapshot.
61. U uvolněného místa vyhrazeného pro WC mají před běžným zdrojem náhrady přednost stále dostupné WC rezervy. V obyčejném LL workflow po vyčerpání LL následují dostupní původně přihlášení hráči mimo kvalifikaci podle stejného snapshotu; potom před startem BYE, nebo po uzavření náhrad W/O.
62. Slot konkrétního hráče lze nahradit jen do zahájení jeho prvního skutečného zápasu, i když předtím prošel přes BYE. Potom už jej při běžném odstoupení nelze nahradit LL ani rezervou a další soupeř postupuje přes W/O; je-li před prvním zápasem skutečně nahrazen, původní hráč získá nula bodů a nula prize money.
63. Admin může regenerovat mnoho přednastavených i vlastních částí losu s locks, preview a potvrzením; nevalidní stav nelze aktivovat ani uložit.
64. Po prvním zápase hlavního turnaje nesmí automatika kompletně přelosovat pavouk. Admin to může ručně vynutit pouze s výraznými výstrahami a ochranou historie.
65. Každá automatická verze losu má reprodukovatelný draw seed oddělený od náhodnosti Match Enginu.
66. Za jménem hráče se vždy ukazuje relevantní označení; výchozí individuální styl používá například `[11]`, `[Q6]`, `[LL2]`, alternativní skupinový styl `[9/16]`, `[Q]`, `[LL]`.
67. Tvrdá ruční změna hráče po odehraném zápase může buď vynulovat budoucnost, nebo vědomě zachovat a převést výsledky na nového hráče; branch se vždy nabídne, ale není povinná.
68. Turnaj má samostatné Qualification Weeks a Main Draw Weeks; mohou se překrývat, ale kvalifikace musí být vždy dokončena před zahájením Main Draw.
69. Entry proces má Main Entry Window a následný Qualification Entry Window; hráč z hlavního okna kvalifikaci znovu nepotvrzuje a zůstává v ní, dokud se neodhlásí.
70. Každý aktivní entry/draw proces turnaje používá právě jeden efektivní Tournament Ranking Snapshot pro vstup, pořadí, posuny, nasazení a rankingová kritéria LL. Pouze výslovné `Reopen Entry Process` starý proces uzavře a nahradí jej jedním novým snapshotem; původní zůstane historicky dohledatelný.
71. Výchozí Tournament Ranking Snapshot je ranking po `Main Entry Closing Week − 1`; Admin může turnaji nastavit jiný existující snapshot.
72. Hráč přihlášený až v Qualification Entry Window se seřadí podle stejného snapshotu a může se při pozdějším uvolnění místa posunout do Main Draw před níže postavené hráče.
73. Všechny kvalifikační losy a Main Draw se výchozím způsobem vytvoří naráz na začátku Draw Weeku.
74. Výchozí Draw Week je jeden week před prvním Qualification Weekem, nebo před prvním Main Draw Weekem u turnaje bez kvalifikace; lze jej změnit v Adminu.
75. Kvalifikace a Main Draw jsou jedním turnajovým rankingovým výsledkem a dohromady zabírají jedno místo v právě platném Best N. Uvnitř Q i Main Draw se použije jedna hodnota konečného dosaženého stage a obě složky se potom sečtou; nejde o sčítání bodů za každé vyhrané kolo. Q složka úspěšného kvalifikanta je vyšší než Q složka LL.
76. Sezonní rankingová pravidla včetně Best N lze změnit i během sezony; zpětná změna používá obecný branch nebo regeneration workflow od prvního dotčeného bodu.
77. Před začátkem kvalifikace má nejvýše postavený oprávněný hráč Q seznamu přednost při přesunu do volného Main Draw místa. Následná oprava Qualification Draw se řídí jeho právě platnou fází: před Redraw Cutoff úplný redraw, do Draw Freeze případný seed cascade a po Freeze přímé doplnění původního fyzického Q slotu.
78. Každé konkrétní uskutečnění turnaje je Tournament Edition s vlastním `edition_id`, sezonou, weeky a parametry; před startem smí mít jen provisional pořadí a oficiální `edition_number` vzniká podle následujícího pravidla.
79. `edition_number` se přidělí automaticky při první skutečně zahájené rally Edition podle reálného pořadí startu; lze nastavit počáteční číslo a auditovaně opravit kladnou unikátní hodnotu. Vynechaný, zrušený nebo pouze technicky posunutý ročník bez startu číslo nezvýší; po zahájení se započítá i při pozdějším nedokončení.
80. Při plánování nové sezony se aktivní opakující se Series ukazují jako průhledné `Inherited Plans`; uložený Plan či Edition vznikne při editaci, potvrzení, importu, publication nebo první trvalé provozní potřebě. Prohlížení ID nevytváří; k dispozici jsou vytvoření, úprava, přesun, vynechání, odložení rozhodnutí a hromadné vytvoření s preflightem.
81. RET po zahájení je oficiální výhra/prohra a H2H se skutečně odehraným skóre; neodehraný zbytek se nedoplňuje.
82. W/O před zahájením znamená postup bez odehraného zápasu, výhry, prohry a H2H; postupující však odemkne body a případné prize money podle svého následně dosaženého finishing stage.
83. DQ po zahájení se započítá jako výhra/prohra a H2H a samostatná disciplinární policy může odebrat body či prize money. DQ před zahájením dává diskvalifikovanému nula bodů a nula prize money a soupeř postupuje statisticky jako přes W/O.
84. Dočasně přerušený zápas určený k pokračování je `Suspended`; terminální `ABN / No Contest` nemá vítěze, poraženého ani H2H, ale uchová částečné skóre, čas, rally log a vzniklé fyzické následky.
85. RET, W/O, DQ i ABN mají povinnou kategorii důvodu, volitelnou poznámku a kontextovou nabídku v Adminu včetně možnosti `Jiné`.
86. Všechny nenormální výsledkové statusy může vytvářet simulace i Admin; automatické DQ a ABN jsou extrémně vzácné a pravděpodobnosti jsou nastavitelné.
87. Při comebacku z dobrovolného retirementu se znovu započítají stále platné výsledky; během retirementu normálně stárnou a propadlé výsledky se neobnovují.
88. Protected Ranking vzniká pouze při uznané nedobrovolné překážce. Official Run default vyžaduje nejméně 30 započitatelných weeků a výjimečný neúspěšný návrat nemusí dříve nasbíranou absenci vynulovat.
89. Každá sezona má upravitelnou Protected Ranking Policy. Na začátku uznané absence vznikne `PR Case`, který si uloží neměnný snapshot tehdy platné politiky; to je funkčnost enginu.
90. Official Run default poskytuje 8 použití PR po absenci 30–45 weeků, 10 po absenci 46–60 weeků a 12 po absenci alespoň 61 weeků; jiná sezona či Run může mít jiné hodnoty.
91. PR nepřepisuje skutečný ranking ani nepřidává body. Ve Vieweru lze vedle skutečného pořadí zobrazit například `(PR 14)` a hráče bez turnaje alespoň 30 weeků vizuálně odlišit.
92. Jedno použití PR se spotřebuje až definitivním přijetím do Main Draw nebo kvalifikace právě díky PR; jedna Tournament Edition spotřebuje nejvýše jedno použití.
93. Skutečný ranking má před PR přednost. Hráčská AI strategicky rozhoduje, kdy PR využije, a Admin může její volbu ručně přepsat.
94. Official Run default vyžaduje první návrat do tří let od začátku PR Case. Pracovní 61weekové období pro čerpání zbývajících použití po návratu zůstává prozatímním pravidlem kapitoly 18.4 a není součástí tohoto pevného bodu.
95. Official Run default povoluje PR jen v běžných individuálních turnajích World Tour a Elite Tour, s výslovnými výjimkami popsanými v kapitole 18.4.
96. Každé podporované nastavení může být `Inherited` nebo výslovný `Override`; Admin ukazuje efektivní hodnotu i její zdroj.
97. Změna nadřazené hodnoty mění pouze zděděné hodnoty. Obnovení dědění i změna nadřazeného nastavení mají dopadový preview a Admin nabízí centrální přehled všech overrides.
98. Běžná úprava turnaje mění jen konkrétní Tournament Edition. Přes rozbalenou Tournament Series lze s editovatelným preview hromadně upravovat Editions a jednorázově mezi nimi kopírovat vybrané vlastnosti.
99. Run má automatický souhrnný stav `Valid`, `Warnings` nebo `Errors`, ale blokování je operation-scoped: chyba blokuje jen operace závislé na nevalidních objektech, nikoliv automaticky každou jinou validní simulaci v Runu.
100. Osobní Admin poznámky lze připojit prakticky ke kterémukoliv objektu, dát jim vlastní barvu a symbol a označit je jako Active/Resolved. Neovlivňují validaci ani simulaci.
101. Oblíbené položky se označují hvězdičkou a globální panel je seskupuje podle Runů. Viewer i Admin vedou také vymazatelný seznam nedávno navštívených položek.
102. Vlastní kombinace filtrů a řazení lze v principu ukládat pod názvem jako Saved Views.
103. Stará uložená verze se nejprve otevře v read-only preview; lze ji prohlédnout, vytvořit z ní branch nebo jí potvrzeně obnovit současnou branch. Před obnovením se aktuální stav automaticky zachová jako checkpoint.
104. Potvrzená hromadná operace zůstává do uložení jedním společným krokem v Undo.
105. Více simulací téhož uloženého platného bodu vzniká jako Candidate Branches s různými seedy; potřebný technický checkpoint připraví engine a žádný kandidát se po dokončení automaticky nevybere ani nesmaže.
106. Candidate Branches lze plánovat sekvenčně, po weecích, po sezonách nebo automaticky a se souběžností 1/2/4/Auto, aniž by plán změnil jejich deterministický výsledek.
107. Dlouhé simulace, importy, exporty a validace spravuje Task Center. Zdrojová branch a právě používaná společná data jsou během simulace zamčené proti mutacím, ale lze je prohlížet a s ostatními Runy pracovat.
108. Okamžité pozastavení zmrazí i nedokončený interní výpočet a ponechá branch uzamčenou pro přesné pokračování; bezpečné zastavení nejprve dokončí současný zápas a potom ponechá dosažený stav jako neuložené změny.
109. Compare States umí v principu porovnat dvě branche, verze nebo checkpointy a vypsat jejich rozdíly.
110. Rozhraní má právě češtinu a angličtinu pod jedním globálním přepínačem; vlastní historické názvy se automaticky nepřekládají.
111. Engine používá pouze centimetry a kilogramy a globální vzhled `Light / Dark / System`.
112. Současný rozsah je desktopový; důležité stavy jsou kromě barvy vždy odlišené také ikonou, textem nebo jiným znakem.
113. Každá výplata prize money zachovává původní měnu a přepočítává se do uživatelem zvolené reporting currency historickým kurzem příslušného weeku.
114. Relevantní objekty a operace mají v Adminu dohledatelný a filtrovatelný původ, například Built-in, Simulated, Imported, Manual nebo Regenerated.
115. Saved Views lze skrývat; nekompatibilní pohled zůstane ve správci s vysvětlením, ale nezobrazuje se v rychlé nabídce daného Runu.
116. Viewer umožňuje zobrazit současný čas ročně, sezoně nebo oběma způsoby; výchozí je roční zobrazení.
117. Věk lze zobrazit jako celé roky, roky a weeky nebo desetinně; výchozí jsou celé roky.
118. Desetinný věk používá podle potřeby nejvýše tři desetinná místa a vychází z 61weekového roku.
119. Engine umožňuje historickou změnu reprezentované země a v Official Runu jde o velmi výjimečnou událost. Konkrétní eligibility, 122weeková lhůta, počet změn, schvalování a abstraktní simulace zůstávají prozatímním modelem kapitol 10.3 a 29, nikoliv součástí tohoto pevného bodu.
120. Výška i hmotnost jsou časově proměnlivé a historický Viewer vždy ukazuje hodnoty platné ve zvoleném weeku.
121. Historický profil ukazuje věk i status hráče platný ve zvoleném weeku a neprozrazuje budoucí změny.
122. V současné verzi neexistuje samostatný juniorský ranking. V MSA rankingu lze podle běžných MSA bodů filtrovat hráče juniorského věku, kteří už vstoupili na Tour; pre-Tour prospecti zůstávají v samostatné juniorské/prospect sekci. Samostatný juniorský ranking může přijít až ve vzdálené budoucnosti.
123. World, Elite, Challenger a Development Tour jsou součástmi jednoho MSA Tour. Hráč k žádné z nich není výlučně přiřazen a může hrát napříč Tour podle pravidel turnajů.
124. Official Run bude postupně přidávat národní mistrovství. Přesný počáteční rozsah zůstává odděleným prozatímním pravidlem kapitoly 29.
125. Main Draw nemá pevnou maximální délku, ale při délce nad dva weeky vznikne neblokující varování s oranžovým vykřičníkem.
126. Vhodné Admin seznamy umožňují hromadný výběr pomocí checkboxů, společné preview a jeden krok Undo.
127. Viewer i Admin mají globální vyhledávání v navbaru a `Ctrl+K` aktivuje tentýž vyhledávač.
128. Aktuální schopnosti, forma, únava a zdraví jsou oddělené vrstvy. Časově proměnlivý hráčský stav se ukládá historicky a starý week používá tehdejší hodnoty i tehdejší verzi modelu.
129. Potenciálová škála Official Runu je `L, S, A, B, C, D, E, F`, vždy ve variantách `+`, bez znaménka a `−`, od `L+` po `F−`; skutečný potenciál zůstává ve výchozím Vieweru skrytý.
130. OVR je odvozený souhrnný přepočet, jehož váhy se mohou mezi hráči lišit podle predispozic a stylu. Není samostatnou schopností ani přímým rozhodnutím výsledku zápasu.
131. Kariéra nemá jeden povinný pevný `peak_week`; může mít více vrcholů, plateau, poklesů a návratů.
132. Match Engine používá skutečný stav hráčů, zatímco hráčská AI soupeře pouze odhaduje ze scoutingu, výsledků, H2H a pozorování. Může se mýlit, měnit styl i gameplan a pokus o adaptaci nemusí uspět.
133. Hráč může nastoupit s lehčím zraněním či nemocí; stav ovlivní výkon, riziko zhoršení a možnost RET. Objektivní neschopnost před startem vede k W/O a oprávněná zdravotní autorita může start zakázat.
134. Každý Run uchovává verzované nastavení úrovně podrobnosti simulace. První verze může být jednoduchá, dlouhodobým cílem je extrémně detailní simulace; přesné profily a jejich hierarchie jsou odložené.
135. Run se buduje průběžně bez povinného globálního `Setup → Start Run` gate. Každý právě validní zápas nebo jiný dílčí rozsah lze simulovat už od prvních vytvořených objektů; širší simulace vyžadují pouze své vlastní širší prerequisites.
136. Vestavěný GitHub Match Test Lab má read-only baseline a oddělené editovatelné testovací sessions. Historický hráč z jiného Runu se přebírá jako nezávislý snapshot s provenance; test nikdy nemění zdrojový Run, ranking, H2H ani statistiky.
137. Únava je kontinuální stav a přenáší se mezi zápasy, turnaji i weeky; automaticky se na jejich hranicích neresetuje.
138. Admin zná skutečný zdravotní stav. Viewer ukazuje jen tehdy veřejnou či oprávněně odhadovanou informaci a skrytý lehčí problém nemusí zobrazit vůbec.
139. `Inactive` nevzniká automaticky po určité době bez zápasu, ale skutečným rozhodnutím hráče/AI nebo Admina. Dlouhá absence je jen údaj či vizuální signál. První platná Tour přihláška nebo definitivní přidělení wild card do fieldu hráče okamžitě vrátí do `Active`; samostatné přijetí WC se nevyžaduje a běžná přihláška aktivuje návrat, i když se hráč přes cut nakonec do fieldu nedostane.
140. Pád nebo nechtěné zavření zachová neuloženou práci v odděleném Recovery Draftu. Při dalším spuštění ji lze obnovit, nejprve read-only prohlédnout nebo zahodit; recovery samo nic neukládá, nepřepisuje ani nepublikuje do Vieweru.
141. Undo/Redo je více-kroková historie aktuální pracovní relace; potvrzená hromadná operace je jeden krok. Dlouhodobý návrat po ukončení relace nebo ke staršímu uloženému stavu probíhá přes verze a checkpointy.
142. Engine nevynucuje pevnou periodicitu kontinentálních ani jiných soutěží. Konkrétní cyklus a jeho historické změny jsou obsahem příslušného Runu, nikoliv další otázkou funkčnosti enginu.
143. CSV/XLSX import používá opravitelné staging preview bez předčasné mutace dat. Každou chybu přesně lokalizuje a vysvětlí včetně příkladu opravy; bezpečný částečný import dovolí pouze u nezávislých platných řádků a potvrzený zápis je atomický, jeden auditní záznam a jeden krok Undo.
144. Kopírování Runu s neuloženými změnami nikdy potichu nezvolí zdroj. Lze kopírovat poslední uložený stav, nejdříve uložit a kopírovat, vytvořit kopii přímo z pracovního draftu bez uložení originálu, nebo akci zrušit.
145. Kopírování Runu nabízí výchozí úplnou kopii a pokročilý bezpečný výběr podporovaných dat. Engine doplní povinné závislosti, znemožní nevalidní kombinace, předem ukáže obsah i velikost a kopii vždy oddělí novým `run_id` bez živého propojení.
146. Lifecycle Runu tvoří `Working`, `Completed` a `Archived`; povinný přechod `Setup → Active` neexistuje. `Built-in / Local`, `Read-only / Editable` a `Valid / Warnings / Errors` jsou samostatné osy a trvalé smazání je operace, nikoliv stav.
147. Branch lze vytvořit a stav obnovit z kteréhokoliv uloženého platného bodu historie, nejen z checkpointu. Checkpoint je pojmenovaná uživatelská záložka nebo technicky připravený bod obnovy.
148. Admin má centrální interaktivní Historii Runu: přehlednou mapu branchí a bodů divergence propojenou s detailní časovou osou vybrané branche, read-only náhledy uložených bodů a kontextové akce pro porovnání, branch a obnovu.
149. Rozdílné simulované historie branchí se nikdy automaticky neslučují. Lze je porovnat, jednu zvolit jako `Viewer Branch` nebo z nich pokračovat; kompatibilní nastavení či ruční změna se smí přenést jen jako nová výslovná operace s preview a validací.
150. Export Runu nabízí `Úplný archiv`, `Vlastní export` a `Kompaktní snapshot`. Povinné závislosti a společná minulost se doplní automaticky, nevalidní výběr je zakázaný a recovery drafty, cache ani jiné regenerovatelné dočasné soubory se neexportují.
151. Starší podporované schéma Runu se validuje a migruje jako nová lokální kopie bez změny zdrojového souboru; novější nepodporované schéma se bezpečně odmítne s požadovanou verzí. Neznámá data se nikdy tiše nezahazují ani částečně nenačítají.
152. Výchozí `Uložit` zapisuje všechny bezpečně slučitelné neuložené změny. `Uložit vybrané změny` pracuje s logickými balíčky, automaticky doplní povinné závislosti nebo neoddělitelný výběr zablokuje a zbytek ponechá jako neuložený draft.
153. Každé úplné i částečné uložení je atomické, vytváří jednu obnovitelnou verzi, automatický souhrn a auditní událost; název či poznámka verze jsou nepovinné.
154. Engine nemá umělý limit velikosti Runu, branche, historie ani počtu uložených verzí a nic kvůli interní kvótě automaticky nemaže. Sdílená minulost, verze a historie používají rozdílové ukládání, deduplikaci a bezztrátovou kompresi.
155. Admin ukazuje skutečnou fyzickou velikost celého enginu, Runů, branchí a datových oblastí. U branche rozlišuje vlastní a sdílená data i prostor, který by její odstranění skutečně uvolnilo.
156. Při vysoké spotřebě nebo malém volném prostoru engine neblokujícím oranžovým vykřičníkem varuje a navrhne konkrétní úspory s odhadem uvolněného místa. Ztrátové čištění nikdy neproběhne bez výběru a potvrzení uživatele.
157. Pokud pro bezpečné dokončení a případný návrat není dost fyzického místa, engine zablokuje pouze dotčené uložení, simulaci, import, export nebo jinou operaci a ukáže potřebnou a volnou kapacitu. Při nízkém, ale dostačujícím prostoru pouze varuje.
158. Checkpointy se automaticky nevytvářejí periodicky po zápasech či weecích. Ruční pojmenovaný checkpoint lze vytvořit kdykoliv a automatický bezpečnostní checkpoint vzniká pouze před operací, která může nahradit či odstranit uložený stav nebo budoucnost.
159. Základní sportovní taxonomie Category Package je obsahově nezávislá na World Package a nevyžaduje jeho země ani regiony. Případné reference navazujících Series nebo Calendar dat na World či Category objekty používají měkké unresolved vazby a neblokují samotný import.
160. Branche jednoho Runu mohou mít po odvětvení rozdílné kalendáře, Tournament Editions, výsledky, rankingy, hráčské stavy i pravidla. Sdílejí `run_id` a společnou minulost, ale každá má vlastní `branch_id`; kvůli alternativnímu kalendáři není potřeba nový Run.
161. Tentýž `player_id` může mít v různých branchích jiné atributy a další časové stavy. Ruční atribut lze nastavit od konkrétního weeku s následným běžným developmentem, nebo jeho hodnotu výslovně uzamknout do odemčení; zásah nese původ `Manual`.
162. Obsah zkopírovaný z případně použitých Packages se stává nezávislou součástí Runu; jeho pozdější historické změny platí pouze v upravované branchi. Přenos do dalších vybraných branchí je samostatná operace s preview a validací.
163. V jednom Runu je právě jedna `Viewer Branch`, která pouze určuje zobrazenou uloženou časovou linii. Není důležitější než ostatní branche a neexistuje žádná `Official Branch`; technický ukazatel je `viewer_branch_id`.
164. Simulaci lze `Pozastavit okamžitě` i uprostřed interního výpočtu zápasu se zachováním přesného stavu pro pokračování, `Bezpečně zastavit` po dokončení právě zpracovávaného zápasu nebo jí přes `Naplánovat zastavení` zvolit budoucí zápas, kolo, turnaj, week, sezonu či jiný podporovaný konzistentní bod. Naplánovaný cíl lze změnit či zrušit a bez něj simulace doběhne do původně zvoleného konce.
165. Při zavírání okna během dlouhé simulace jsou možnosti `Pokračovat na pozadí`, `Bezpečně zastavit a zavřít` a `Nezavírat`.
166. Při pokračování na pozadí zůstane lokální engine v oznamovací oblasti Windows, ukazuje průběh, dovolí znovu otevřít Task Center a oznámí dokončení. `Ukončit engine` je samostatná bezpečná akce.
167. Konfliktní změna nesmí změnit vstupy běžící simulace. Admin nabídne nejméně vytvoření nové branche z vhodného bodu, bezpečné zastavení původní simulace nebo zrušení změny.
168. Po znovuotevření se Task Center napojí na stále běžící úlohu nebo ukáže bezpečně zastavený výsledek. Po pádu či vypnutí počítače se použije poslední bezpečně zachovaný stav a Recovery Draft, nikdy předstírané pokračování z neuloženého mezistavu.
169. Současná verze používá jedno hlavní okno aplikace. Nemá samostatný rozcestník Viewer/Admin; běžnou úvodní stránkou je neutrální `Squash Engine Home` s globálními vstupy `Runs` a `Packages` a automaticky se neotevírá žádný Run.
170. Na Run-scoped stránkách obsahuje globální kontextová skupina ve Vieweru `Run → Čas → Viewer/Admin` a v Adminu `Run → Branch → Čas → Viewer/Admin`. Viewer volič branchí nemá a vždy zobrazuje `Viewer Branch`; globální stránky bez Runu tuto skupinu nemají.
171. Jeden společný ovladač sezony/weeku mění pouze prohlížený časový kontext, nikdy stav simulace. Viewer dovolí jen skutečně zobrazitelné body, zatímco Admin může otevřít také podporovaný budoucí week pro plánování.
172. Rychlé voliče Runu a branche ukazují nejvýše pět položek včetně aktuální, upřednostní oblíbené a doplní nedávné. `Všechny Runy` a `Všechny branche` vedou na samostatné úplné stránky; Branch switcher existuje pouze v Adminu.
173. Úplná stránka `Všechny Runy` používá široké řádky pod sebou. Kliknutí na Run nabídne otevření jeho `Viewer Branch` na běžné hlavní stránce Adminu, otevření úplné stránky branchí nebo otevření ve Vieweru.
174. Admin má skrývací levý sidebar: rozbalený ukazuje ikony a názvy, sbalený zůstává jako úzký pruh ikon a v malém okně se může skrýt úplně.
175. Viewer Admin sidebar nepoužívá. Každý právě otevřený veřejný web má vlastní stálý vodorovný navbar s rozbalením podstránek po najetí i s dostupnou obsluhou kliknutím a klávesnicí.
176. Viewer je read-only prostředím více samostatných fiktivních webů nad stejným Runem a časem. MSA je hlavní právě navrhovaný oficiální web; ostatní weby se mohou přidávat postupně a nemusejí předstírat, že jsou částí MSA.
177. Společné Viewer logo vlevo nahoře otevírá rozcestník dostupných veřejných webů současného Runu; vedlejší logo právě otevřeného webu vede na jeho homepage. Obě akce zachovají Run i season/week.
178. MSA homepage je živá titulní stránka podle vybraného season/weeku. Historický week ukáže pouze tehdejší známé turnaje, výsledky, žebříčky a veřejné souhrny bez prozrazení budoucnosti.
179. Přepnutí Viewer/Admin se pokusí zachovat Run, sezonu/week, objekt a odpovídající podstránku. Viewer vždy použije současnou `Viewer Branch`; při chybějícím protějšku otevře nejbližší smysluplnou stránku s vysvětlením a teprve poté hlavní stránku cílového módu.
180. Pod season/week ovladačem je ve Vieweru stav `PRESENT` nebo `PAST` a v Adminu `PRESENT`, `PAST` nebo `FUTURE`. Kliknutí na neaktuální stav vrátí pouze prohlížený kontext do současného bodu a nikdy nezmění simulaci.
181. Hlavní stránka Runového Adminu se nazývá `Home`, nikoliv Dashboard. Je nejvyšším souhrnem vybraného Runu a branche; vlastní simulační řízení a hluboké nástroje patří primárně na své specializované stránky.
182. Admin má oddělený `Global Admin` scope bez Runu, branche a weeku a `Run Admin` scope se všemi Runovými ovladači.
183. Na globálních Admin stránkách Viewer nelze otevřít: volba je viditelná, ale neaktivní s vysvětlením `Nejdříve otevři Run`, a aplikace nikdy skrytě nepoužije minulý Run. Do Vieweru se vstupuje přes `Runs → vybraný Run → Otevřít ve Vieweru`.
184. Zdrojové World, Category, Series, Calendar a Setup Packages mají vlastní globální Admin správu. Jejich editace musí být jednoznačně oddělená od editace nezávislého obsahu uvnitř Runu.
185. V Adminu vede logo Squash Engine na globální kořen. V Runovém scope je vedle něj obecná Run ikona s názvem současného Runu, která vede na jeho `Home`; na globálních stránkách druhý prvek chybí.
186. Všechny Runy mohou používat stejné obecné Run logo/ikonu; samostatné vlastní logo pro každý testovací nebo běžný Run není vyžadované.
187. Admin sidebar je kontextový: globální scope ukazuje globální správu, Runový scope Runové sekce, a obě sady nemíchá v jednom menu.
188. Run Admin sidebar se při najetí dočasně vysune jako vrstva nad stránkou, při najetí na kategorii rozbalí její stránky svisle dolů, drží otevřenou nejvýše jednu kategorii a zvýrazňuje aktivní cestu.
189. Sidebar lze připnout natrvalo; volba se na zařízení zapamatuje. Dočasné otevření má ochranné zpoždění proti nechtěnému zavření a automaticky ukáže kategorii současné stránky.
190. Run Home má dva pevné segmentované ukazatele: 50 sezon celého Runu a 61 weeků současné sezony, vždy s jasně označenou aktuální pozicí.
191. Engine důsledně odděluje World Event Log světových faktů, Audit Log změn dat a provenance, Task Center běžících či dokončených operací a Notification Center věcí vyžadujících Adminovu pozornost.
192. World Event Log tvoří trvalou chronologickou historii konkrétní časové linie a dovoluje dohledat, jak a proč vznikl současný stav. Přečtení, skrytí nebo odstranění upozornění nikdy nesmaže jeho zdrojovou událost, audit, úlohu ani validaci.
193. Notification Center přijímá automatická systémová upozornění a uživatelské watchlisty hráčů, zemí, turnajů, branchí a dalších podporovaných objektů s volitelnými triggery.
194. Opakující se informace a varování se seskupují do rozbalitelných položek; kritické problémy zůstávají jednotlivě viditelné.
195. V celém Adminu platí stejný systém: modré `i` pouze informuje, oranžový vykřičník neblokujícím způsobem varuje a červený vykřičník zablokuje nebo bezpečně zastaví pouze dotčenou operaci či branch. Každý stav současně obsahuje text příčiny, dopadu a možností opravy.
196. Notification Center se otevírá zvonkem vpravo nahoře na každé Admin stránce a filtruje alespoň aktuální branch, celý Run nebo všechny Runy a Packages.
197. Viewer nezobrazuje technická upozornění, interní validaci ani Audit Log. Jeho veřejné zprávy vycházejí pouze z tehdy veřejné části World Event Logu bez future leaku.
198. Trenéři, podpůrné týmy, agenti a tréninková centra se nesimulují jako samostatné entity, bonusy ani vztahy. Abstraktní development nebo příprava hráče tím nejsou zakázané.
199. Viewer i Admin budou na různých kontextových stránkách zobrazovat velké množství historicky správných rekordů; jejich zdrojem zůstávají autoritativní data příslušné branche a weeku.
200. Každý hráč používá vlastní individuální AI a může se ve stejné vnější situaci rozhodovat jinak; první verze může být jednoduchá a přesné chování se bude kalibrovat až nad fungující simulací.
201. Historická MSA homepage obsahuje automatické veřejné zprávy odvozené výhradně ze strukturované veřejné části World Event Logu platné v daném čase. Zpráva není samostatným zdrojem pravdy a nesmí vytvářet future leak.
202. Přechod do nového weeku provádí samostatný automatický `Week Transition`, který se nepočítá mezi Simulation Slots. Aktivuje nové turnajové body, vytvoří Official Ranking nového weeku, provede narozeniny a příchod patnáctiletých prospectů a připraví jeho počáteční stav.
203. Součástí každého Week Transitionu první verze je `Weekly Player Development Update`. Používá hráčův stav a historii známé nejpozději do konce právě skončeného weeku, nikdy však informace z nově otevíraného nebo budoucího weeku. Může atributy zlepšit, zhoršit nebo ponechat stejné a nové hodnoty platí od prvního slotu následujícího weeku. Únava, zdraví ani jiné kontinuální stavy se přechodem automaticky neresetují.
204. Každý week první verze má jednu globální chronologickou osu s proměnlivým počtem Simulation Slots. Události stejného slotu jsou současné, používají společný vstupní snapshot a jejich technické pořadí nesmí změnit jejich vstupy; další slot začne až po platném vyřešení všech událostí současného slotu.
205. `Simulate Next Slot` dokončí všechny zbývající události nejbližšího neuzavřeného globálního slotu. Dělené `Simulate Next Match` dovolí vybrat pouze jiný nevyřešený současný zápas bez nesplněné schedule dependency; pozdější zápas téhož Match Day Slotu nelze přeskočit, pokud musí číst následky dřívějšího.
206. `Season Transition` je speciální rozšíření Week Transitionu při přechodu ze Season Weeku 61 do Weeku 1, nikoliv druhé hodiny ani normální slot. Dokončí se jen po platném terminálním vyřešení všech povinných událostí uzavírané sezony; červený problém blokuje pouze tento přechod a označí příčinu.
207. Nové sezonní policy se při Season Transitionu aktivují atomicky bez tichého přepočtu staré sezony. Resetují se pouze výslovně season-scoped hodnoty; kontinuální hráčské a historické stavy pokračují. Uzavření vytváří lehký `Season Closure Marker`, ne kopii světa.
208. Všech 50 sezon lze plánovat dopředu pomocí úsporných virtuálních `Inherited Plans`; virtuální výskyt je před materializací adresovaný deterministickým klíčem a nemá ID. Uložený Plan dostane stabilní `edition_plan_id`, Edition odlišné `edition_id`; triggerem je editace, potvrzení, import, publication nebo první trvalá provozní potřeba včetně simulace či Season Transitionu.
209. Budoucí kalendář rozlišuje scopes `Only this Edition` a `From this season onward`. Druhý mění pouze zděděné budoucí plány; individuální overrides chrání impact preview. Budoucnost aktivní sezony je editovatelná a minulost používá obecný branch/history workflow.
210. Tournament Edition má ze skutečných událostí odvozený hlavní lifecycle, detailní komponentní stavy a z nich vypočtený veřejný `Public Stage`. Viewer vidí jen tehdy veřejně důležité fáze, Admin také interní deadlines, freezes, dependencies a chyby.
211. Neúplný Draft lze uložit. Chybějící pole neblokují nesouvisející práci, ale přechod do Scheduled, otevření entries, los nebo simulace vyžadují své platné prerequisites a případně zobrazí červený operation-scoped problém s opravou. Ranked Edition bez úplné bodové tabulky zůstává neveřejným Admin Draftem; prize money publikaci první verze neblokují.
212. Každá Tournament Edition má historicky platný `announcement_week`. Do jeho aktivace při Week Transitionu a vzniku veřejného World Eventu ji zná pouze Admin; Viewer ani hráčská AI nesmějí skrytou informaci použít. První verze používá pro Viewer i všechny hráče stejné veřejné datum.
213. `announcement_week` se dědí z explicitního Edition override, jinak z Tournament Series a nakonec z typického fallbacku kategorie. Musí být alespoň jeden celý week před nejčasnější provozní událostí Edition; interní tvorba Draftu se nepočítá.
214. Veřejně podstatná změna již oznámené Edition vytváří nový `Tournament Update`; do jeho publication weeku platí poslední veřejná verze. Odůvodněný `Emergency Update` může být při skutečně mimořádné události zveřejněn okamžitě a nesmí obcházet běžné pravidlo.
215. Všechny hráčské entry volby jednoho decision slotu používají společný zmrazený startovní snapshot a použijí se společně až na konci slotu. Technicky později zpracovaný hráč nevidí rozhodnutí jiného hráče ze stejného slotu.
216. Každá vícezáznamová operace nebo kauzálně či konfliktně propojený batch se nejprve vypočítá a zvaliduje ve staging vrstvě a potom se commitne celý, nebo vůbec. Nezávislé skupiny stejného slotu mohou podle novějšího bodu 361 commitnout odděleně. Retry stejné neúspěšné skupiny se stejnými vstupy reprodukuje kandidátní výsledek a lokální oprava bezdůvodně nepřehodí kauzálně nesouvisející rozhodnutí; úplný seed contract tím není uzavřený.
217. `Tournament Entry/Application` je samostatný historický objekt se status history, časem a původem. Staré stavy se nepřepisují ani nemažou a Viewer v minulosti vidí jen tehdy veřejné informace.
218. První verze Match Enginu simuluje každý zápas rally po rally, nikoliv shot-by-shot. Jedna rally prochází `Rally Setup`, skrytým vývojem kontroly a tlaku, terminálním incidentem a oficiálním vyřešením s následky.
219. Každá rally odděluje dopad na skóre, oficiální rozhodnutí a sportovní příčinu; u sportovní příčiny se navíc samostatně ukládá fyzický terminální mechanismus a kontext typu clean winner, forced error nebo unforced error.
220. Skrytý průběh rally používá pět stavů od silné kontroly hráče A přes neutral až po silnou kontrolu hráče B, může mezi nimi vícekrát přejít a počítá individuální asymetrickou zátěž obou hráčů. Nejde o veřejný `Surprise Score`.
221. První verze používá tři dynamické fyzické bary `Explosive Stamina`, `Rally Stamina` a `Match Stamina`. Jejich kapacita, aktuální naplnění a recovery se odvozují z podkladových atributů a aktuálního stavu; nejde o tři další samostatně authorované dlouhodobé schopnosti.
222. Dlouhodobá `Fatigue` ovlivňuje výchozí dostupnost tří fyzických barů, ale není čtvrtým zápasovým barem. `Health / Injury State` je rovněž samostatná vrstva. Detailní trénink a mapování podkladových atributů do barů zůstávají odložené nebo otevřené.
223. Stamina se přepočítá po každé rally, dopad vyčerpání je spojitý a nelineární a začátek zápasu nic automaticky neresetuje. Kompaktní rally log ukládá po každé rally všechny tři aktuální stavy obou hráčů.
224. Match Engine zná skutečný fyzický stav; hráčská AI vlastní stav pouze vnímá a soupeřův odhaduje. Před rally volí základní úsilí a během skrytého průběhu je může měnit, přičemž úsudek i provedení mohou selhat.
225. Podání je samostatnou součástí Rally Setupu, ale má squashově malou váhu: uchovává servera a service box, jednoduchou volbu přístupu, možný fault a spolu s returnem pouze nastavuje počáteční kontrolu.
226. První verze používá správné zjednodušené `No Let / Yes Let / Stroke`; skutečně uplynulý čas mezi rally ovlivňuje recovery. Od v60 běžná mezera vzniká kauzálně z připravenosti obou hráčů, rozhodčího a kurtu a zahrnuje individualizované i taktické tempo na podání a returnu s minimálním conduct resolverem. Chyby rozhodčích, detailní review, okrajové interference a individuální profil rozhodčího patří do pokročilejší verze.
227. Squash Engine bude obsahovat hráčské rivality. Automatická detekce, vícečlenné a překrývající se vztahy, skóre, životní cyklus, ruční doplnění a přesné Viewer umístění zůstávají směry o síle uvedené v kapitole 21.2.1.
228. Best N není pevná hodnota všech sezon: první sezona Official Runu má výchozí Best 15 a každá další jako počáteční výchozí návrh převezme efektivní Best N bezprostředně předchozí sezony; každá sezona zůstává samostatně konfigurovatelná.
229. Každý hráč má jednu společnou aktuální Form. Aktualizuje se po každém skutečně odehraném zápase, ovlivní už další zápas stejného turnaje a vychází z kvality výkonu vzhledem k soupeři a očekávání, nikoliv pouze z výhry či prohry.
230. Forma se při Week Transitionu postupně vrací k individuálnímu dlouhodobému normálu a nikdy se neresetuje; její přesný normál, výpočet a rychlost návratu zůstávají otevřené.
231. Forma krátkodobě ovlivňuje provedení existujících schopností, ale nepřepisuje dlouhodobé atributy ani z nich odvozenou fyzickou kapacitu. První verze nemá samostatný atribut ani bonus Match Momentum.
232. W/O a DQ před startem formu nemění; RET a DQ po startu započítají pouze skutečně odehraný výkon s vahou podle množství dat. `Suspended` odloží přepočet do obnovení nebo definitivního ukončení a po dohrání či terminálním ABN se odehraný výkon započítá právě jednou; disciplinární důvod se do sportovní formy nemíchá.
233. Match Engine zná skutečnou Form, ale hráčská AI svou vlastní pouze odhaduje z posledních výkonů a soupeřovu ještě méně přesně z dostupných výsledků a pozorování.
234. První verze podporuje během zápasu zdravotní výsledky `pokračovat / zdravotní přestávka / RET`; po přestávce se znovu vyhodnotí zdravotní stav a teprve potom AI rozhodne mezi pokračováním a RET.
235. Zdravotní přestávka je konfigurovatelným pravidlem soutěže s Official Run defaultem tři minuty. Oba hráči během skutečně uplynulého času používají vlastní běžnou stamina recovery, ošetřovaný nedostává automatický stamina bonus a ošetření působí na samostatný Injury State.
236. Nominální přestávka mezi gamy/sety je konfigurovatelným pravidlem zápasu s Official Run defaultem dvě minuty. Stamina se během skutečně uplynulého času pouze obnovuje a žádná stamina, zranění ani dlouhodobá fatigue se na hranici gamu neresetuje.
237. Autoritativní zápasová časová osa ukládá skutečnou mezeru před každou další rally, každou přestávku mezi gamy samostatně a zdravotní událost včetně délky přestávky a následného `pokračovat / RET`; celková délka zápasu vzniká ze všech těchto událostí a rally.
238. První verze obsahuje Match Reconstruction: ručně zadaná fakta jsou závazné constraints, Builder podporuje kombinace přesných hodnot, rozsahů, minim a maxim a odděluje Pre-match Form, Match Performance a odvozenou Post-match Form. Validace používá globální oranžovou/červenou závažnost; přesný katalog a prahy zůstávají otevřené nebo pouze směrem.
239. Admin si pro každou Match Reconstruction nastaví počet kandidátů. Všechny se nejprve ukážou v kompaktním přehledu, každý lze otevřít v úplném read-only Admin detailu a pouze výslovně vybraný kandidát se stane autoritativní historií a zdrojem následků.
240. Country Model V1 používá šest ručně authorovaných ratingů `1–5`: Squash Popularity, Squash Access, Development Quality, Competition Quality, Elite Support a Squash Tradition, každý s významem vymezeným v kapitole 5.3.
241. Population Timeline, Area, Region, Travel Region, Timezone Area a případný Court Count jsou faktická data oddělená od ratingů. Effective Squash Pool, Competitive Depth, Talent Discovery Rate, Professional Conversion Rate a Current Country Strength jsou naopak časově a branchově odvozené hodnoty, nikoliv další ruční ratingy.
242. Země nesmí přímo měnit vrozenou distribuci talentu, potenciálový strop ani vytvářet národní technický, mentální či stylový bias. Ovlivňuje sampling a conversion pipeline; i systémově slabá země má nenulovou šanci na generační L+ talent.
243. Kategorie hráčských atributů jsou pouze organizační a samy nejsou simulačním souhrnným atributem. Historický zápas uchovává použitou verzi atributového a simulačního modelu; konkrétní pracovní katalog první verze zůstává prozatímní.
244. Každá rally podle svého Rally Setupu a situace používá vlastní váženou podmnožinu relevantních jednotlivých atributů, nikoliv stejný průměr všech schopností; tím nevzniká shot-by-shot simulace.
245. První verze používá dynamické mentální bary Current Focus a Current Confidence aktualizované po každé rally. Focus reaguje rychleji, Confidence pomaleji a oba se na začátku zápasu nově odvodí z aktuálního hráčova stavu místo přímého převzetí konečných čísel z minulého zápasu.
246. Admin v běžném Runu i Match Test Labu podporuje `Simulate Next Rally`, `Simulate Game` a `Simulate Rest of Match`; všechny pokračují z přesného současného stavu a po každé rally lze zobrazit rozhodnutý interní detail bez simulace jednotlivých úderů.
247. Před `Simulate Game` a `Simulate Rest of Match` vzniká automatický dočasný návratový bod. Pracovní zápas uchovává jejich časovou osu a po návratu a nové simulaci ponechá původní cestu dočasně dostupnou pro porovnání.
248. Auto Play postupuje jednu rally za druhou, má nastavitelnou rychlost, lze jej pozastavit a sám se zastaví na konci gamu nebo při mimořádné události. Uložený dokončený zápas lze stejným principem pouze přehrát v read-only Match Replay bez nové simulace; Viewer vidí veřejné a Admin interní informace.
249. První verze Vieweru obsahuje základní samostatný web Scores se zápasy, výsledky, veřejnými statistikami a Replayem. Pokrývá detailně simulovanou část MSA Tour, juniorské mistrovství světa a olympijské hry; běžná juniorská historie se tím nezavádí.
250. Match Reconstruction řadí kandidáty výchozím způsobem podle nalezení, významová editace vytváří novou constraint a kandidáta až po tlačítku a do potvrzení zachovává původní preview. Při příliš dlouhém či neúspěšném hledání Admin volí vynucení, nejbližší kandidáty nebo změnu podmínek; autoritativní zůstane jen potvrzený kandidát. `p` znamená přirozenou pravděpodobnost, `δ` směrovou a `α` bezsměrovou vzdálenost od typické oblasti, nikoliv totéž co `p`; přesná matematika zůstává otevřená.
251. V každém nakonfigurovaném entry decision slotu hráčská AI společně přehodnotí všechny tehdy známé turnajové možnosti, může změnit přihlášky i priority a nesmí rozhodovat izolovaně podle technického pořadí turnajů. Po dokončení slotu se aktuální předběžný entry list zveřejní AI i Vieweru; rozhodnutí uvnitř běžícího slotu zůstávají do společného commitu skrytá.
252. Počet předběžných či podmíněných přihlášek hráče nemá pevný strop. Více konfliktů lze dočasně držet, ale po relevantní uzávěrce podle Main Draw/Qualification stavu se prodlení sankcionuje stále přísněji; hráč může skutečně odehrát jen jednu akci nebo nenastoupit ani na jednu, nikoliv dva turnaje téhož weeku.
253. Entry provinění může vést k odečtu bodů, Disciplinary Zero nebo kombinaci. Každá nula po vlastních `X` weeků povinně zabírá jedno místo v Best N, poté nezávisle zanikne; více nul se skládá a Admin může jejich délku změnit. Přesné sazby a délky jsou otevřené.
254. Admin může ručně zasáhnout do každého produktově modelovaného pravidla, stavu, rozhodnutí AI a autoritativního údaje. Smí vědomě porušit běžnou sportovní policy jako označenou výjimku, ale nesmí uložit vnitřně nemožný či poškozený stav; související změny tvoří atomický, branchově a časově správný Manual Override s Audit Logem.
255. Ruční změna přihlášky má režimy `Jednorázová změna`, kterou AI smí v dalším entry slotu znovu přehodnotit, a `Uzamknout rozhodnutí` do odemčení či nastaveného expiry. Prokázané zranění nebo nemoc odstraňuje disciplinární sankci za pozdní odhlášení či no-show, ne však automaticky sportovní Week Tournament Lock.
256. První verze používá Week Tournament Lock: začátek hráčovy kvalifikace nebo Main Draw mu obsadí celý příslušný week, ani po vyřazení v něm nesmí začít druhý turnaj a do dalšího weeku se lock přenese jen tehdy, pokud v původním turnaji stále pokračuje. Formální dlouhé Suspended období lock v mezilehlých weecích uvolní a aktivuje jej znovu v resume weeku; přímý Main Draw hráč není blokovaný dřívějším qualification-only weekem své Edition.
257. Week Tournament Lock platí pro všechny oficiální soutěže včetně MSA Tour, olympijských her, juniorského mistrovství světa a jejich kvalifikací. `Still Competing` dovoluje omluvenou podmíněnou přihlášku na následující week; navazující turnajová kombinace navíc vyžaduje zjednodušeně proveditelný přesun a turnaj kvůli hráči automaticky nemění schedule.
258. Před Final Commitment Deadline lze zvolený turnajový závazek změnit v mezích entry pravidel. Po deadline každý odpovídající potvrzený závazek zamkne daný week i po odstoupení; zdravotní důvod ruší sankci, ne lock. Uvolnit jej může zrušení akce, odklad na nový termín s novým rozhodnutím hráčů, formální dlouhé Suspended období pro mezilehlé weeky, chyba organizátora nebo výslovné rozhodnutí FAX/Admina; přesné umístění deadline zůstává otevřené.
259. Proveditelný přesun v první verzi automaticky vytváří `Low / Medium / High Travel Load` podle hrubé vzdálenosti a dostupného času. Bez nového baru dočasně přidává Fatigue, omezuje recovery, snižuje počáteční naplnění tří stamina barů, odeznívá odpočinkem a nemění trvalé atributy.
260. Každá Tournament Edition první verze má zjednodušený Round/Match Schedule: jedno kolo dostane jeden `Match Day Slot` nebo rozsah denních slotů, konkrétní zápasy se přiřadí do dnů a uvnitř dne mají uložené pořadí bez přesných časů. Tato jednotka není globálním Simulation Slotem ani entry/draw procesním oknem.
261. Qualification i Main Draw mají samostatně tři repair fáze. Před `Redraw Cutoff` se dotčený los celý přelosuje, od tohoto cut-offu do `Draw Freeze` se používá seed cascade a od Freeze se doplňuje přímo uvolněný fyzický slot. Redraw Cutoff začíná předposledním a Draw Freeze posledním procesním oknem příslušného losu.
262. Všechny odchody, posuny, WC/RWC změny, LL sloty a náhrady téhož procesního okna se počítají atomicky ze společného pre-window stavu; technické pořadí zpracování nesmí změnit sportovní výsledek.
263. Seed cascade je tier-aware a zachovává vyváženost seed sektorů. Seed 2 po odchodu seedu 1 nezíská číslo 1, přesunutí seedy si ponechají původní čísla a nejvýše postavený oprávněný nenasazený hráč uzavře cascade povýšením do uvolněné seed struktury; jeho původní slot dostane běžnou náhradu.
264. Běžné odhlášení nenasazeného hráče prostřední seed-cascade fázi samo nespouští. Po Draw Freeze náhradník vždy vstupuje do konkrétního fyzického slotu bez převzetí seed čísla nebo entry statusu původního hráče a Freeze sama náhradu před hráčovým prvním skutečným zápasem nezakazuje.
265. Uvolněnou WC alokaci dostane před běžným náhradním zdrojem dostupná Reserve Wild Card. Její `Available` status trvá až do skutečného využití, odstoupení nebo ztráty eligibility; po vyčerpání WC rezerv se použije normální replacement workflow dané fáze.
266. Vstoupí-li držitel WC přímo podle Tournament Ranking Snapshotu, WC se mu automaticky odebere a může přejít na další rezervu, ale historický entry objekt jeho původní WC trvale pamatuje. Definitivní přidělení WC je implicitně přijaté a samostatná accept akce neexistuje.
267. Lucky loser vložený do slotu odhlášeného seedu zůstává `[LLx]`, nepřebírá jeho seed číslo ani status a historie pouze zaznamená, který původní seed slot nahradil.
268. BYE ani přímé pozdní vložení náhradníka do vyššího kola samy neodemknou vyšší rankingovou hodnotu. Prohra nebo RET v prvním skutečném zápase znamená v dané draw složce body prvního kola; první skutečná výhra odemkne další hodnoty. Prize money se naproti tomu řídí skutečným finishing stage a W/O je výslovná postupová výjimka z tohoto unlocku.
269. Ranked výsledek Qualification + Main Draw zabírá jedno místo v Best N. Každá draw složka přidělí jednu hodnotu za konečný dosažený stage, tyto dvě hodnoty se sečtou a Q složka úspěšného kvalifikanta musí být vyšší než Q složka LL; body se nesčítají po jednotlivých výhrách.
270. Každá Tournament Edition první verze je `Ranked` nebo `Unranked`. Běžná Edition vzniká jako Ranked, bodová kategorie status neurčuje a Admin ji může výslovně označit Unranked; Package může konkrétní typ přednastavit jako `Unranked Only`, který v žádné Edition nelze změnit na Ranked.
271. Ranked Edition potřebuje před oznámením, zveřejněním hráčům, entry rozhodováním a simulací úplnou bodovou tabulku. Neúplná smí existovat jen jako neveřejný Admin Draft a hráčská AI používá zveřejněné bodové hodnoty při výběru turnajů; prize money tento publikační gate první verze neovlivňují.
272. Bodová tabulka Tournament Edition vychází z konfigurace její kategorie pro konkrétní sezonu. Při vytvoření nové sezony se tabulka každé pokračující kategorie předvyplní efektivní tabulkou bezprostředně předchozí sezony a lze ji pro novou sezonu samostatně změnit bez přepsání historie.
273. Prize money jsou v první verzi všude nepovinné a povinnými se mají stát až v některé další verzi. Pokud nakonfigurované jsou, engine už v první verzi vede výplaty, historii, sezonní i kariérní součty a všechny odvozené finanční výstupy.
274. Chybějící prize money znamenají `Not configured / Unknown`, nikoliv nulu. Částečná tabulka neblokuje simulaci: známé výplaty se spočítají, neznámé zůstanou Unknown, celkový prize pool je `Incomplete / Unknown` a hráčská AI neznámou částku ignoruje.
275. Každé vyplněné stage pole udává částku pro jednoho hráče a každá známá pozdější Qualification/Main Draw hodnota musí být přísně vyšší než každá známá dřívější; jsou-li obě hodnoty zadané, Main Draw R1 je proto vyšší než nejvyšší Q výplata. Celkový prize pool je součet částky stage násobené počtem hráčů, kteří v něm skončili, napříč Q i Main Draw.
276. Hráč vyřazený v kvalifikaci dostane Q výplatu svého konečného stage. Kvalifikant nebo LL postupující do Main Draw dostane pouze jednu výplatu podle konečného Main Draw stage a Q prize money se nepřičítají; nahrazený hráč před prvním zápasem a hráč s DQ před startem dostanou nulu, zatímco DQ po startu může mít samostatný disciplinární forfeit.
277. U běžné neveřejné Draft Edition lze Ranked/Unranked status opravit oběma směry. Veřejně oznámenou Unranked Edition už nelze změnit na Ranked; oznámená Ranked Edition smí být před startem downgradována pouze veřejným Tournament Update či rozhodnutím FAX/Admina s impact preview a přepočtem.
278. Od prvního skutečného zápasu je běžná změna statusu uzamčená. Jen mimořádné rozhodnutí FAX smí odebrat `Ranked → Unranked` s důvodem, veřejným updatem, Audit Logem a přepočtem; opačný směr je zakázaný. Po dokončení se body odstraní až od účinného bodu rozhodnutí a historické snapshoty, losy ani tehdy známé události se nepřepisují.
279. Unranked Edition nemá MSA body ani Best N výsledek, ale její zápasy plně ovlivní stamina, fatigue, health/injuries, formu a development a vedou se v titulech, historii, statistikách, rekordech a H2H.
280. Hráčská AI při volbě Unranked turnaje počítá s nulovým bodovým přínosem, ale může jej zvolit kvůli prestiži, prize money, titulu, reprezentaci nebo jiné motivaci; přesné váhy jsou otevřené.
281. Edition zrušená před prvním skutečným zápasem je `Cancelled`: nevzniknou body, prize money ani titul a její přihlášky, závazky i Week Tournament Locky se uvolní bez sankcí; zrušení a důvod zůstávají v historii.
282. Uvolnění hráče po Cancelled Edition neobchází entry, deadline, freeze ani replacement pravidla jiné akce; může do ní vstoupit jen tehdy, když to její normální workflow ještě dovoluje.
283. `Postponed` zachovává stejné `edition_id` a historii a změnu schedule ukládá časově verzovaně. Již uzamčené oficiální `edition_number` zůstane; před prvním skutečným zápasem je pořadí jen provisional a může se změnit. Přihlášky zůstávají, ale všichni hráči mohou kvůli novému termínu znovu rozhodnout nebo bez sankce odstoupit.
284. Režim odkladu `Preserve Field & Draw` zachová původní field, los a Tournament Ranking Snapshot; odhlášení se řeší normálními náhradami.
285. Režim odkladu `Reopen Entry Process` zruší budoucí los, nastaví nové deadlines, vytvoří nový Tournament Ranking Snapshot a turnaj znovu vylosuje bez změny identity Edition. Mezi režimy není pevný počet weeků; FAX/Admin jej výslovně zvolí s impact preview.
286. Již zahájený turnaj s reálnou možností pokračování může být dočasně `Suspended`: výsledky a přesný rozpracovaný stav se zachovají a další turnajová simulace se zastaví do obnovení.
287. Obnovený zápas pokračuje ze stejného skóre a zachovaného logu; stamina, focus, fatigue a health se znovu odvodí podle skutečné délky přerušení a mezilehlých událostí, nikdy se automaticky neresetují.
288. Dlouhé Suspended období automaticky nezamyká všechny mezilehlé weeky. Hráči mohou při splnění pravidel hrát jiné akce a Week Tournament Lock původní Edition se znovu aktivuje v resume weeku.
289. Nemůže-li při obnovení pokračovat konkrétní hráč kvůli zdraví, použije se RET; neodůvodněné odmítnutí či no-show je Default. ABN je vyhrazeno pro vnější příčinu bez zavinění hráčů.
290. U formálně Abandoned Edition zůstávají dokončené zápasy oficiální ve statistikách a H2H. Bez platného finále nevzniká automatický šampion ani titul, ale FAX může výslovně přiznat mimořádný výsledek či titul.
291. U Abandoned Edition získá hráč jen nejvyšší body skutečně odemčené běžným win/BYE/W/O kontraktem a bez platného finále nikdo nezíská champion points. Nakonfigurované prize money dají aktivním hráčům loser payout nejvyššího dosaženého fyzického stage, ne winner payout. Terminální zahájený zápas je ABN se zachovaným částečným stavem bez W/L/H2H; nezahájené sloty nejsou ABN výsledky.
292. Nezaviněné vnější přerušení živé rally v první verzi znamená `Yes Let`, žádný bod a replay ze stejného skóre s uloženým důvodem. Po již skončené rally bod zůstává a hráčem způsobená událost se řeší příslušnými player/interference/conduct pravidly; přesný přechod od krátkého přerušení do Suspended zůstává otevřený.
293. Potvrzenými samostatnými typy jsou `World Package`, `Category Package`, `Series Package`, `Calendar Package` a `Setup Package`; další typy mohou být přidány později pouze jako rozšíření.
294. Použití Package vždy kopíruje vybraný payload a provenance do nezávislého stavu Runu bez živého propojení. Pozdější převzetí nové verze je výslovná previewovaná operace, nikoliv automatická synchronizace.
295. Závislosti mezi Packages jsou měkké: Series či Calendar lze importovat i bez odkazovaného World, Category nebo Series objektu. Původní reference zůstane zachovaná jako `Unresolved` a lze ji později vyřešit importem nebo ručním mapováním.
296. Package validace významově rozlišuje `Not included`, `Unresolved` a `Invalid`. Neúplná skladba sama není globální chybou; červeně se blokuje pouze operace, která bez chybějícího či neplatného vstupu nemůže proběhnout.
297. Setup Package je volitelný kompoziční obal World, Category, Series a Calendar Packages, mapování, validace a provenance. Smí být neúplný, nepřidává vlastní sportovní pravidla a přenositelný export obsahuje skutečně zahrnuté payloady, ne pouze lokální odkazy.
298. World, kategoriální systém, Series nebo kalendář ručně vytvořené v Runu lze vyexportovat jako nové nezávislé Packages s provenance a bez živého propojení se zdrojovým Runem.
299. Competition System, Tour a Category používají stabilní číselná ID v rámci Category Package. ID se nerecykluje ani nekóduje pořadí; oddělené `display_order` a volitelný sportovní/tier rank používají jen entity, pro které dávají smysl.
300. Tour může pod stejným ID měnit název, být deaktivována a reaktivována; skutečně nová Tour dostane nové ID. Hráči nejsou členy Tour, protože Tour organizuje soutěže a kategorie.
301. Calendar Package může pokrýt jednu, více nebo všech 50 sezon i jen zvolenou část sezony, Tour či Series. Neuvedený scope je mimo balíček a nikdy sám neznamená prázdná data nebo příkaz ke smazání.
302. Výchozí import Calendar Package provádí merge přes preview. Úplné nahrazení je možné jen po výslovné volbě přesně vymezeného scope a nesmí odstranit nic mimo něj.
303. Edition Plan ukládá cílovou sezonu, week či rozsah weeků a explicitní overrides. Zhmotněná Edition má samostatné `edition_id`, odkaz na `edition_plan_id` a nepřebírá výsledky, přihlášky ani losy staršího ročníku.
304. Další sezonní plán standardně dědí efektivní hodnoty posledního existujícího ročníku či plánu stejné Series. Po vynechané sezoně se vychází z posledního skutečného ročníku, nikoliv z prázdné mezery.
305. Pravidla cílové sezony, zejména bodová tabulka, se vždy vyřeší z konfigurace `Category × target season`; nekopírují se slepě z předchozí Edition ani z jiného kalendářového rozsahu.
306. Zápasy jednoho Match Day Slotu se simulují postupně v uloženém pořadí, takže pozdější zápas vidí aktuální fyzické a zdravotní následky dřívějšího zápasu hráče. Viewer vidí pořadí, nikoliv neexistující přesný čas začátku.
307. Scheduler první verze prioritizuje feeder vazby, odpočinek, srovnatelnou recovery soupeřů a carryover z minulého weeku; například finalistu minulého weeku umístí v dalším turnaji co nejpozději. Náhodnost rozhoduje jen mezi stejně vhodnými platnými variantami.
308. Potvrzený schedule se uloží, zveřejní a při simulaci se znovu nehází. Změny po publikaci se označí a přepočítají nejmenší nutný rozsah; budoucí feeder zápasy mohou používat provisional placeholdery typu `vítěz zápasu 12` a po určení hráčů se potvrdí nebo minimálně přesunou kvůli odpočinku.
309. Zdrojovou identitu Package entity určuje dvojice `source_package_id + source_entity_id`: stejná dvojice označuje tutéž entitu, zatímco stejné číslo v různých Packages je výchozím způsobem odlišné. Skutečně totožné entity lze výslovně ručně namapovat; shoda názvu sama nestačí.
310. Importovaná entita dostane vlastní stabilní číselné ID uvnitř Runu a zdrojovou dvojici si ponechá jako provenance.
311. Každá Category patří v jedné sezoně právě do jednoho Competition Systemu a nejvýše do jedné Tour; mezi sezonami se může přesunout při zachování `category_id` a historie.
312. Tournament Series nemá vlastní přímou vazbu na Tour. Edition používá kategorii své sezony a z ní odvozenou tehdejší Tour a Competition System; reorganizace hierarchie nemění identitu Series ani staré Editions.
313. Jedna Tournament Series může mít v jedné sezoně více Editions, každou s vlastním `edition_plan_id` a `edition_id`.
314. `display_order` i `tier_rank` jsou sezonní historické hodnoty: standardně se dědí a reorganizace je může změnit bez přepsání minulosti.
315. Název musí být v jedné sezoně unikátní pouze mezi sourozenci pod stejným rodičem. Stejný název pod jiným rodičem je platný a přejmenování zachovává ID i historii.
316. Engine rozlišuje srovnatelné tierové entity a speciální nesrovnatelné entity s `tier_rank = null`; tier se porovnává pouze mezi sourozenci pod stejným rodičem, zatímco význam speciálních soutěží určují jiné vlastnosti. Shodný tier sourozenců je odložený.
317. Series Package nese identity Tournament Series a jejich dlouhodobé děděné defaulty; Calendar Package nese Edition Plans, sezony, weeky a konkrétní overrides.
318. Entita vyexportovaná z Runu dostane vlastní stabilní Package ID a Run ID zůstane jen v provenance. Exportní soubor obsahuje přesně výslovně vybraný rozsah a nic dalšího se automaticky nepřibalí.
319. Běžné uložení editovatelného Package vytváří novou verzi stejného `package_id`; `Duplikovat` vytváří nový Package s novým ID a verzí 1. Vestavěný read-only Package lze v enginu měnit jen takovou nezávislou duplikací.
320. Všechny předchozí Package verze zůstávají read-only dostupné k prohlížení, porovnání a importu. Obnovení staršího obsahu vytvoří novou nejnovější verzi stejného Package a mezilehlou historii nemaže.
321. Lokální Package se nejprve archivuje a lze jej obnovit; trvale smazat jde až z archivu po potvrzení. Existující Runy zůstávají beze změny.
322. Export/import téhož Package mezi počítači zachovává jeho `package_id` i číslo verze; novou identitu vytváří pouze duplikace.
323. Každá Setup Package verze je přesný reprodukovatelný snapshot konkrétních verzí vložených Packages. Zdrojové aktualizace ji automaticky nemění a vědomě nové složení vytvoří novou verzi stejného Setupu.
324. Pouhá dostupnost novější Package verze je modrá informace, skutečný problém kompatibility či závislosti oranžové varování a neproveditelná operace červený blokující stav.
325. Přesně odpovídající `source_package_id + source_entity_id` po potvrzeném preview automaticky vyřeší čekající `Unresolved` vazbu; pouhá shoda názvu nikdy ne.
326. Opakovaný import stejného Package a verze nevytváří duplicity: nezměněný obsah je `Already imported` no-op a Runově upravený obsah se nejprve zobrazí v diffu.
327. Z novější Package verze lze přijmout pouze vybranou bezpečnou část změn a engine znovu validuje její vazby.
328. Potřebuje-li vybraná Package změna další nevybraná data, engine ukáže závislost a všechny proveditelné možnosti; nic skrytě nepřidá ani nezmění.
329. Package konflikt se nikdy neřeší tichým výběrem. Admin dostane všechny právě proveditelné logické a datově bezpečné možnosti; jejich konkrétní sada závisí na situaci a přesné UI zůstává otevřené.
330. Virtuální Inherited Plan získá stabilní `edition_plan_id` až prvním skutečným zhmotněním při editaci, potvrzení, importu, announcement/publication nebo první trvalé provozní potřebě; pouhé prohlížení, filtrování, hledání či preview vzdálené budoucnosti žádný objekt nevytváří.
331. Jeden Edition Plan může vytvořit nejvýše jednu Tournament Edition. Více Editions téže Series potřebuje více plánů; Postponed zachovává původní plán i Edition.
332. Více Editions téže Series se čísluje podle skutečného pořadí zahájení. Edition zrušená před prvním zápasem číslo nespotřebuje.
333. Čistě interní nepoužitý Edition Plan nebo Draft lze odstranit z aktivního kalendáře se zachováním auditu a verze. Veřejně oznámená nebo již datově použitá Edition se v současné historii řeší lifecycle stavem, nikoliv beze stop smazáním.
334. Alternativní historie, ve které veřejně oznámený turnaj nikdy nevznikl, vyžaduje návrat před první veřejnou událost, odstranění plánu v této časové linii a novou simulaci všech kauzálně navazujících následků; původní branch zůstane zachovaná či obnovitelná.
335. Hráčská AI první verze používá pouze tehdy veřejně potvrzené turnaje a změny a nesmí číst skryté Edition Plans. Vlastní očekávání pravidelných turnajů je až směr pro pozdější verze.
336. Jediným uživatelsky zadávaným povinným údajem pro vznik pre-alpha Runu je jeho jedinečný zobrazovaný název. `run_id` a prázdný časový rámec vytvoří engine; ostatní obsah lze doplňovat později.
337. Pre-alpha používá všech 57 atributů z kapitoly 11.1 jako samostatně uložené hodnoty na škále `0–200`. Šest kategorií je pouze organizačních a Match Engine v konkrétní situaci používá jen relevantní podmnožinu atributů.
338. OVR používá rozsah `0–200` a je normalizovaným váženým průměrem aktuálních atributů, nikoliv přímým vstupem Match Enginu. Pre-alpha může používat jeden společný verzovaný profil vah; cílem dalších verzí jsou individuální profily hráčů.
339. Skutečný potenciál se přidělí při vytvoření hráče a běžná simulace jej nemění. První verze používá jeden skrytý celkový měkký `Potential OVR`, nikoliv samostatné pevné potenciálové stropy každého atributu.
340. `Potential OVR` není zaručený ani očekávaný vrchol a lze jej extrémně vzácně překročit. Nevzniká další tvrdý limit typu `potential + 2`; absolutním stropem současné OVR škály je `200`.
341. Každý hráč má od vytvoření pevný a na potenciálu nezávislý typ načasování vývoje `Early Bloomer / Standard / Late Bloomer`. Zjednodušená první verze posouvá jednu společnou základní věkovou křivku přibližně o `−3 / 0 / +3` roky.
342. Věkový vývoj nepůsobí jednotně na všechny atributy: fyzické schopnosti mohou klesat dříve, zatímco technické, taktické a mentální schopnosti se mohou držet nebo zlepšovat později. Přesné křivky zůstávají kalibrací.
343. Experience je z kariérní historie odvozený profil `General Experience + High-Pressure Experience`, nikoliv atribut, OVR ani omezený bar. Běžnou simulací neklesá, nemá pevné maximum a její přínos používá klesající mezní efekt.
344. Match Sharpness je samostatný bar `0–100 %`. Po soutěžním zápase roste podle délky a intenzity, za week bez soutěžního zápasu klesá a nikdy se automaticky neresetuje.
345. Vyšší Match Sharpness je vždy výhodnější; přetížení se řeší přes Fatigue, tři stamina systémy, recovery a Health/Injury State, nikoliv skrytým obrácením Sharpness křivky.
346. Match Preparation je dočasný bar `0–100 %` navázaný na konkrétní připravovaný zápas. Engine odděleně uchovává podíl `Opponent Study` a `Match-specific Court Training`.
347. Při neznámém soupeři lze zvolit obecnou přípravu nebo cílit na jednoho pravděpodobného soupeře. Aktuální příprava se po cílovém zápase uzavře, ale autoritativní historie a předchozí H2H mohou zjednodušeně usnadnit budoucí přípravu.
348. Opponent Study spotřebovává čas a soustředění s téměř nulovou fyzickou únavou, zatímco cílený trénink na kurtu spotřebovává tréninkovou kapacitu a vytváří zátěž. Účinnost závisí na relevantních atributech; okamžitý efekt patří do Match Preparation a malý dlouhodobý příspěvek do běžného developmentu, nikoliv do dočasného skoku atributu.
349. Pre-alpha má dva povinné akceptační průchody: kompletní sezonu Official Runu až po Season Transition do Weeku 1 další sezony a samostatný prázdný Run se dvěma ručně vytvořenými hráči a jedním zápasem pro ověření operation-scoped modularity.
350. Povinně funkční jsou Runs/Packages, hráči/development/AI, čas/transitions, turnaje, entries, losy, Match Engine, minimální Match Reconstruction, rankingy a bezpečný save/load. Pre-alpha je hotová teprve tehdy, když oba průchody opakovaně proběhnou od začátku do konce bez pádu, poškozené historie nebo ruční opravy databáze; správný operation-scoped blok není selhání.
351. Validní simulace může běžet z Working Draftu, její následky zůstanou neuložené a Viewer dál čte poslední Saved Revision. Zahození draftu zahodí i simulaci vzniklou z jeho neuložených vstupů.
352. `SAVE` je trvale dostupné, aktivuje se při změnách a před potvrzením ukáže krátký diff. Červená chyba zablokuje běžné uložení dotčeného celku, ale `Uložit vybrané změny` smí uložit prokazatelně nezávislé validní logické balíčky.
353. Změna označení Viewer Branch začne ve Vieweru platit až potvrzeným Save. `Nová branch z Working Draftu` přesune neuložené změny do nové branche a původní ponechá na její poslední Saved Revision.
354. Week Transition je atomický devítikrokový proces `preflight/staging → development dokončeného weeku → Between-Week State Update → nová konfigurace → lifecycle → výsledky/discipline/corrections → jediný Official Ranking → veřejné události → validace/commit`; při selhání se nezapíše nic.
355. Development používá konečnou Form dokončeného weeku před jejím návratem k normálu a starou development policy; nová policy poprvé řídí vývoj nového weeku. Official Ranking nového weeku naproti tomu používá nově účinnou Ranking Policy.
356. Rankingové body, pořadí a existující Official snapshoty jsou přímo read-only. Před každým novým snapshotem se provede povinný recompute z autoritativních vstupů; mismatch je červený a blokuje celý transition. Pozdější korekce se projeví v novém snapshotu, zatímco historie „jako by chyba nevznikla“ vyžaduje branch/regeneraci.
357. Narozeniny a další lifecycle změny se provedou při otevření stejného `birth_year_week`; nový věk platí už pro jeho první sloty a Official Ranking daného weeku.
358. Každou sezonu uzavírá samostatný archivní Season Closing Ranking podle odcházející policy včetně výsledků Weeku 61. Odkazuje na něj Closure Marker, zobrazuje se pouze v sezonním souhrnu a nikdy neřídí entries, seeding ani AI.
359. Season Transition používá atomické pořadí `validace Weeku 61 → Closing Ranking → sezonní souhrn/Closure Marker → development a recovery staré sezony → aktivace nové sezony a reset jen season-scoped hodnot → lifecycle → Official Ranking Weeku 1 → veřejný stav → commit`. Sezonní statistiky se před resetem zmrazí, career statistiky a zbývající disciplína pokračují.
360. Pre-alpha zakazuje jednu Tournament Edition přes hranici Season Week 61→1 jako okamžitou červenou validační chybu. Poslední sezona 2049/50 po Closing Rankingu, souhrnu a Closure Markeru označí Run Completed a nevytvoří neexistující další Week 1.
361. Atomickou jednotkou uvnitř Simulation Slotu je nezávislá událost nebo kauzálně či konfliktně propojená skupina, nikoliv automaticky celý slot. Nezávislé skupiny lze uložit samostatně, ale všechny nevyřešené skupiny čtou původní frozen slot-start snapshot a další slot čeká na jejich terminální stav.
362. Výstup závislý jen na dokončené skupině se může po uložení zveřejnit okamžitě; agregát čeká na celý relevantní batch. Známý feeder se doplní ihned, neznámý zůstane placeholderem a navazující zápas čeká na všechny prerequisites i uzavření předchozího globálního slotu.
363. Retry selhané skupiny se stejnými vstupy a verzí modelu zachová seed i kandidátní výsledek. Novou náhodnost vyvolá jen relevantní změna nebo výslovné `Resimulate`; hotové nezávislé skupiny se znovu nehází.
364. Velká ruční změna atributu nabídne vedle okamžitého skoku s varováním také `Dopočítat historický vývoj` přes novou branch nebo regeneraci. Pre-alpha nabízí režimy přirozeně přegenerovat, zachovat přesné výsledky a zachovat podobnou historii.
365. Přesný historický režim chrání potřebný soutěžní skelet: entries/účast/odhlášení, los a soupeře, vítěze, `RET/W/O/ABN`, celkové a game skóre, postup, body a odvozené rankingy.
366. Délka, rally/shot odhady, Form, stamina, Fatigue, Health a další navazující stavy jsou cíle podobnosti podřízené oficiálním faktům. Engine ukáže všechny odchylky, proveditelnost, dostupný odhad realističnosti včetně `p / α`, počtu vzorků či nejistoty a problematické zápasy a nabídne více kandidátních cest i ruční počáteční week či rozsah.
367. Běžný development i historická rekonstrukce zakazují nevysvětlené účelové kličkování. Oranžová hranice znamená extrémní, ale možný vývoj; červený absolutní limit nelze vynutit. Samostatné pokročilé osy rozsahu regenerace × míry zachování jsou odložené.
368. Pre-alpha zdraví rozlišuje Injury a Illness, dovoluje více současných samostatných záznamů a nepoužívá jeden univerzální Health bar.
369. Každý zdravotní záznam má Severity `0–100` a typově odvozený profil omezení. Více stavů se skládá podle zasažených domén s klesajícím dodatečným dopadem a bezpečným maximem, nikoliv prostým součtem.
370. Zdravotní lifecycle je `At Risk → Active → Recovering → Recovered`, přičemž včas zvládnutý signál smí přejít přímo `At Risk → Recovered` bez vymyšlené aktivní diagnózy; Recovered zůstává v historii. Zotavení používá nejisté rozmezí a skutečný průběh se může zrychlit, protáhnout nebo zhoršit.
371. Hráči mají oddělenou náchylnost k Injury a Illness, možné predispozice podle typu či oblasti a vlastní rychlosti zotavení; tyto vlastnosti zůstávají oddělené od Financial Levelu.
372. Jeden kontextový Health Check pokrývá události mezi Simulation Slots, abstraktní týdenní trénink a akutní rally situace a škáluje riziko podle času a zátěže, aby se stejná náchylnost nezapočítala duplicitně. Rally check proběhne po každé rally.
373. Engine uchovává zdravotní pravdu, ale hráčská AI rozhoduje podle vlastního nedokonalého odhadu. Odhalený At Risk nabízí volbu, nevynucuje odpočinek; preventivně lehčí trénink snižuje riziko a podporuje recovery za cenu developmentu a Match Preparation.
374. Testovací pre-alpha používá dynamický Financial Level `0–10` jako hrubý odhad dostupného zázemí, nikoliv peníze či účetnictví. Vychází z rodiny, klubu/federace, Elite Support, kariéry a případně známých prize money; chybějící prize money nejsou nula.
375. Financial Level se vyhodnocuje každý Week Transition, běžně se mění pomalu oběma směry a velká změna zázemí může působit rychleji. Elite Support posouvá pouze výchozí distribuci a Official FAX default je kvůli globálnímu sportu štědřejší; TOP 1000 má vysokou pravděpodobnost běžného profesionálního kalendáře bez absolutní garance.
376. Financial Level je převážně měkký AI faktor a jen v krajním nesouladu může vytvořit hard limit. Jeho malé verzované účinky v řádu jednotek procent působí přes prevenci/detekci, healing, recovery a přístup k přípravě, cestování a péči, nikoliv biologickým přepsáním predispozic.
377. V zápase smí Financial Level přímo ovlivnit jen delší recovery mezi gamy a během zdravotní přestávky jedním slabým Resource Recovery Modifierem. Nepůsobí po každé rally ani jako obecný skrytý výkonový bonus a nesmí být dvojitě započítán.
378. Ligový squash se v první verzi úplně ignoruje: nemá entitu, data, příjem, událost, faktor ani log. Slouží jen jako světové vysvětlení, proč je výchozí FAX ekonomické zázemí obecně štědřejší.
379. Minimální Rally Setup obsahuje skóre/pravidla/server/service box, elapsed time a recovery, relevantní atributy, Form a Sharpness, Fatigue a zdraví, tři fyzické a dva mentální bary, styl/matchup/gameplan/úsilí/serve-return, tlak stavu zápasu a model/random state pro Replay.
380. OVR, ranking, Travel Load ani Financial Level se do rally znovu nepřidávají jako obecný bonus, pokud se jejich účinek už materializoval v konkrétních atributech a stavech; výslovný slabý finanční modifier patří pouze do delšího recovery procesu.
381. Úspěšné založení Runu je současně jeho první uloženou verzí: atomicky vznikne Run, jeho počáteční Viewer Branch, neměnná Saved Revision bez rodičovské revize a čistý Working Draft založený na této revizi. Selhání kterékoliv části nezanechá částečný stav a všechna pozdější ukládání zůstávají ruční.
382. Počáteční branch se automaticky jmenuje `Timeline 1`; každá další běžná branch nabídne první nepoužitý název `Timeline N` v daném Runu a uživatel jej může před vytvořením nahradit vlastním jedinečným názvem.
383. Všech pět současných Package typů podporuje nedestruktivní partial scope: neuvedené entity zůstávají beze změny a úplné nahrazení či odstranění vyžaduje samostatnou scopeovanou operaci s preview a potvrzením.
384. Chybějící bezpečně uložitelná Package závislost se zachová jako `Unresolved` s oranžovým upozorněním; přesná kompatibilní source identita se propojí až po viditelném návrhu, nevalidní balíček nelze vynutit a červeně se blokuje pouze operace, která závislost potřebuje.
385. Divergentní historie stejného `package_id` se v pre-alpha neslučují ani nepřepisují. Příchozí větev lze zachovat pouze výslovným importem jako nový samostatný Package s novou identitou, odlišeným názvem a provenance divergence; kanonický merge je odložený.
386. Neúplný Setup aplikuje nedestruktivně pouze obsažené validní komponenty do Working Draftu, nic chybějícího nevymýšlí a nesouvisející práci neblokuje; unresolved prerequisite zastaví až operaci, která jej skutečně potřebuje.
387. Globální Simulation Slot první pre-alpha verze používá pořadí `Slot-Start Activation → Freeze Slot-Start Snapshot → Calculate to Staging → Resolve Conflicts → Validate and Commit → Publish Committed Outputs → Close Slot`; pozdější změna po praktickém testování je dovolena pouze jako vědomá revize kontraktu.
388. Každá simulační akce používá hierarchickou operation-scoped prerequisite matici svého cíle a skutečných kauzálních závislostí. Širší akce dědí požadavky obsažených užších akcí; červená chyba blokuje celý zvolený hromadný rozsah, nikoliv nezávislou validní užší operaci. Vzdálená budoucnost se u Next Season a Full Simulation validuje progresivně.
389. `Simulation Slot` je jediná autoritativní časová osa branche. Procesní okna nabývají účinnosti na hranicích globálních slotů a Match Day Slot se mapuje na jeden či více po sobě jdoucích globálních slotů; nezávislé události mohou být současné, závislé musí topologicky následovat.
390. Nový Tour Player se do již publikovaného Official Ranking snapshotu zpětně nevkládá, do dalšího snapshotu je `NR` a pak se zařadí i s nulou bodů. Ranked výsledek je vstupem až následujícího Official snapshotu; nevzniká žádné zvláštní přidělení bodů před rankingem. Předchozí nulová pozice má přednost před novým hráčem bez pozice a shodu nových hráčů řeší uložený token.
391. Simulačně validní hráč má povinné stabilní identitní, narozeninové, původové, fyzické, lifecycle, atributové a stavové jádro; shodná jména se rozliší reprezentací, rokem, případně birth weekem a stabilním veřejným diskriminátorem. `Sporting Representation` je neprázdná, časově verzovaná a rozlišuje `Country / World / FAX Neutral`; World je dobrovolná globální identita, FAX Neutral regulační status a ani jedno není Country entita ani národní tým.
392. Pre-alpha používá jeden `General Training Load: Recovery / Light / Normal / Heavy`, který sdílí omezenou týdenní kapacitu s Opponent Study a Match-specific Court Training. AI jej volí z nedokonalého odhadu zdraví, únavy, vytížení, kalendáře a významu soutěží; Admin může volbu přepsat a přesná číselná účinnost zůstává kalibrací.
393. Aktivní styl a gameplan pre-alpha používají osy `Risk / Tempo / Court Positioning / Variation`, oddělené Natural Style Profile, Style Familiarity a Style Execution a nedokonalé counterování soupeře. Plán má zamýšlený mechanismus, time horizon, confidence a reassessment threshold; AI u něj může správně i chybně setrvat navzdory krátkodobému neúspěchu.
394. Každý abstraktní rally kontext aktivuje jen relevantní atributy v rolích `Primary / Supporting / Constraint`; dynamické stavy upravují jejich provedení a jeden kauzální vstup ani materializovaný následek se nesmí započítat dvakrát.
395. Rally Resolution Record odděluje primární trigger, rule context, oficiální call, seřazené score mutations, analytical attribution a side incidents. Pre-alpha katalog má jedenáct triggerů od `GOOD_RETURN_UNANSWERED` po `CONDUCT_STOP`; winner/forced/unforced jsou analytická připsání a minimální ball-hit/turning/further-attempt flagy se řeší bez shot-by-shot trajektorie.
396. Pět stavů kontroly používá lokální přechody se setrvačností: běžně stejný nebo sousední stav, dvoustupňový posun po výrazném sportovním zlomu a přímý obrat mezi oběma silnými kontrolami jen výjimečně. Relevantní atributy, styl, gameplan a dynamické stavy ovlivňují získání i udržení kontroly; střídání není vynucené.
397. Rally má 0–24 abstraktních control segmentů. Přímý konec při podání či prvním returnu má nula segmentů a jeden či dva údery; běžné pokračování převážně 1–10 segmentů, potom rostoucí closure pressure a na 24. segmentu kontextově vážený povinný terminal bez hodu 50:50.
398. Engine vytváří ground-truth situační fakta a verzovaný rules resolver z nich v pre-alpha deterministicky určí správný bod, `No Let`, `Yes Let` či `Stroke`. Náhodná chyba rozhodčího není aktivní; budoucí perception, initial call a review mohou změnit call, nikoliv sportovní pravdu.
399. Podání nemá obecný server bonus ani persistentní modifier. `Serve Execution × Return Execution` určí pouze opening, běžně nejvýše jeden krok od neutral; safe/normal/aggressive mění trade-off faultu, opening pressure a attackable returnu a získaná kontrola pak pokračuje jen běžnou transition logikou.
400. Počet úderů, aktivní délka a individuální workload rally vznikají kauzálně společně z openingu, segmentů a terminalu podle historicky verzovaného RallyCalibrationProfile. Profil se kontextově posouvá podle hráčů, stylu, gameplanu, matchupu a stavů; přesná novější čísla mohou být rekalibrována bez přepisu odehraných rally.
401. Mezera mezi rally vzniká jako maximum připravenosti servera, receivera, rozhodčího a kurtu. Hráči mají oddělené přirozené restartové tendence pro podání a return a mohou takticky zrychlit, držet přirozené tempo či zpomalit; skutečný čas dává oběma recovery právě jednou, účinek není garantovaný a bezdůvodné zdržování vstupuje do minimálního prompt/warning/Conduct Stroke resolveru.
402. Oficiální Match Format fallback je atomický `BO5 / do 11 / win by 2`. Pre-alpha dovoluje celý override na Tournament Edition a její fázi či kole; bez něj se vrací přímo k oficiálnímu fallbacku, nikoliv přes skrytou úplnou hierarchii. Konkrétní zápas ukládá efektivní snapshot a od první rally jej zamkne.
403. Zápas před startem ukládá neměnný Match Input Snapshot a po každé dokončené rally atomický Rally Event s Post-Rally State Snapshotem. Rally log je hashově řetězený, crash pokračuje z poslední celé rally a Replay ani Step Back/Forward nikdy znovu nespouštějí RNG či nový model.
404. Competition System, Tour, Category, Tournament Series, Edition Plan a Tournament Edition mají vymezené minimální identity, vazby a lifecycle-required pole. Povinná nevyřešená reference je explicitní `Unresolved`, ne nejednoznačné `null`; virtuální Plan vlastní ID získá až materializací.
405. Obecná konfigurační hierarchie je `Official default → Package → Run → season → Competition System → Tour → Category → Series → Edition Plan → Edition → phase → round → match`; na každém poli vítězí nejbližší povolený override podle field-specific scope registry. Match Format používá vlastní užší kontrakt.
406. Virtuální Inherited Plan materializují jen editace, potvrzení, import, publication či první trvalá provozní potřeba. Re-resolve a validace proběhnou těsně před atomickým vznikem; bulk preflight viditelně oddělí konflikty a změněný zdroj před commitem vyžádá nové potvrzení.
407. Více Editions stejné Series má samostatná Plan/Edition ID a v pre-alpha nepřekrývající se aktivní termíny. Oficiální edition number se přidělí až prvním skutečně zahájeným zápasem; pre-start zrušení, W/O, DQ či technický postup číslo nespotřebují, po první rally se už nevrací.
408. Tournament Edition používá pevnou třívrstvou lifecycle matici hlavního stavu, komponent a Public Stage. Veřejná či použitá Edition se nevrací do Draftu, terminální stav vyžaduje branchovou opravu a Admin provádí přechody doménovými akcemi, nikoliv raw dropdownem; Entries výslovně rozlišují Main a Qualification Entry Window.
409. Announcement week je společný okamžik veřejné znalosti Vieweru a hráčské AI. Každá veřejně podstatná změna je buď součástí stavu `Before Announcement`, nebo verzovaným Tournament Update od zvoleného weeku; již běžící week používá od nejbližší bezpečné hranice odůvodněný Emergency Update a nikdy zpětně nepřepočítá minulost.
410. Nezahájená pokračující Edition je `Postponed`, nezahájená definitivně ukončená `Cancelled`, zahájená pokračující `Suspended` a zahájená definitivně ukončená `Abandoned`. Krátké vnější přerušení zůstává In Progress jen při pokračování ve stejném Match Day Slotu; pozdější slot či week vyžaduje Suspended.
411. Scheduler nejprve vynucuje feeder, jeden zápas hráče za Match Day Slot, nejdříve následující slot, dokončení Qualification a configured range. Platné varianty pak řadí lexikograficky podle menšího odpočinku, recovery imbalance, pořadí minulého zápasu, maximálního rozumného restu Q/LL, carryoveru, minimální změny publikovaného schedule a teprve pak uloženého deterministického tie-breaku.

---

# 29. Prozatímní pracovní pravidla

Také zde platí rozlišení rozsahu z úvodu dokumentu: prozatímní sportovní hodnoty jsou pracovními **Official Run defaulty**, zatímco prozatímní workflow a technické mechanismy popisují směr enginu.

1. Week může mít několik interních procesních oken. Rozhodnuté je, že předposlední okno příslušného losu začíná `Redraw Cutoff` a poslední `Draw Freeze`; prozatímní zůstává přesný celkový počet, výchozí názvy a rozmístění dřívějších oken.
2. Při konfliktu názvu kopírovaného nebo importovaného Runu se pracovně nabízí tvar jako `Copy of X` nebo `X (2)`; přesný styl automatického suffixu je implementační detail.
3. Počet branchí je neomezený.
4. Mimo rozhodnuté turnajové `Match Day Slots` zůstává otevřené, zda některé další systémy později potřebují skutečné kalendářní dny; první verze nepotřebuje přesné hodiny zápasů.
5. Výška i hmotnost se v čase rozhodnutě mění; jejich přesný vliv na atributy, herní styl a gameplan je zatím prozatímní.
6. Týdenní vyhodnocení schopností během Week Transitionu je pro první verzi rozhodnuté; prozatímní je jednoduchost prvního development modelu a jeho pozdější postupné prohlubování.
7. Pre-alpha škála atributů `0–200` je od v49 rozhodnutá. Prozatímním směrem zůstává její pozdější hlubší kalibrace a významové zpřesňování; změna samotného rozsahu po pre-alpha rozhodnutá není.
8. Zápasy turnaje se pravděpodobně simulují až ve chvíli, kdy na ně dojde.
9. Větší simulace mají preview a přiměřený výsledkový souhrn.
10. Season Transition a úsporné Inherited Plans jsou pro první verzi rozhodnuté; prozatímní zůstává hloubka automatického Season Builderu, přesný materializační UX a jeho pozdější rozšiřování.
11. Pracovním popiskem trvale dostupného hlavního ukládacího tlačítka je `SAVE`; jeho přesný lokalizovaný text, vzhled, umístění a animace zvýraznění se rozhodnou až při návrhu frontendu. Funkční aktivace při změnách, potvrzovací diff a Saved Revision jsou již pevné.
12. Audit se uchovává co nejúplněji a případně se později bezztrátově komprimuje; ztrátové čištění je vždy uživatelsky řízené.
13. Pracovním obsahem jednoho řádku na stránce `Všechny Runy` jsou hvězdička, název, krátký popis, aktuální season/week `Viewer Branch`, počet branchí, lifecycle stav, poslední aktivita, fyzická velikost a případný vykřičník. Přesná sada údajů se rozhodne později.
14. Existuje Absolute Prediction a Viewer Prediction.
15. Přesné technické uložení a editace sezonních bodových tabulek mezi Category Package snapshotem a Runem zůstávají součástí prozatímní konfigurační hierarchie. Pevné už je, že tabulka náleží kategorii v konkrétní sezoně, Edition ji odtud přebírá a nová sezona se předvyplní předchozí sezonou.
16. Vestavěné GitHub položky se zatím nebudou skrývat ani archivovat.
17. Současný katalog tour a kategorií je pracovní testovací základ a výsledky simulací jej mohou částečně nebo úplně překopat.
18. Výchozí Main Entry Window trvá dva weeky a následný Qualification Entry Window jeden week; konkrétní timing je nastavitelný a tato čísla se ještě mohou změnit.
19. Saved Views mají zatím pouze globální scope napříč Runy.
20. Každý Run rozhodnutě uchovává úroveň podrobnosti simulace; pracovním směrem je možnost odkládat nepotřebné náročné analytické výpočty. Konkrétní profily, názvy a užší hierarchie ještě nejsou rozhodnuté.
21. Národní mistrovství budou zpočátku pravděpodobně pouze u největších squashových zemí a později se rozšíří i k menším.
22. Zbývající model dobrovolné změny `Country ↔ Country` prozatím vyžaduje občanství nové země a alespoň jednu skutečnou vazbu: narození hráče, narození rodiče nebo pět let reálného pobytu. Standardně je možná jedna dobrovolná změna a platí lhůta 122 weeků od posledního závazného reprezentačního startu. Hráč během ní nemusí reprezentovat starou zemi, může dál hrát běžnou MSA Tour pod dosavadní vlajkou a nový závazný start za starou zemi lhůtu spustí znovu. Žádost lze podat už během lhůty a FAX může předem určit budoucí effective week; účinnost vždy vyžaduje jeho výslovné schválení. Druhá dobrovolná změna je pouze mimořádná a náhodnost má řídit především vznik úvahy a žádosti, nikoliv bezdůvodnou schvalovací loterii. Pevný obecný kontrakt `Country / World / FAX Neutral` a historické Sporting Representation určuje kapitola 10.3.
23. Okamžik prvního vstupu prospecta na Tour má hráčská AI pracovně odvozovat ze schopností, věku, osobnosti, ambicí, příležitostí a rostoucího tlaku po delším odkládání. Přesný vzorec se bude kalibrovat až nad fungující simulací; rozhodnuté je, že každý automaticky generovaný prospect nakonec vstoupí.
24. Při importu se stejným `run_id` engine pracovně rozpozná jinou verzi stejné identity, nejprve nabídne read-only porovnání a teprve potom novou kopii s novým ID, bezpečnou obnovu existujícího Runu nebo načtení rozvětvené historie k ručnímu porovnání. Nic se automaticky nepřepisuje ani neslučuje.
25. Compare States má při různých weecích pracovně nabídnout výchozí porovnání ve stejném weeku a zvláštní režim přesně vybraných bodů s viditelným časovým rozdílem a oddělením běžného vývoje od divergence.
26. Přesné úplné UI a implementační katalog toho, která jednotlivá pole jsou dostupná na každé povolené úrovni dědičnosti, se bude doplňovat podle reálných konfiguračních objektů. Samotné pořadí hierarchie, nearest-permitted-override princip, provenance a samostatná užší výjimka Match Formatu jsou od v62 pevné.
27. Cílovým směrem je zamykat pouze simulovanou branch a skutečně sdílená Runová data, dovolit bezpečné úpravy nezávislých branchí a konfliktní editaci případně uložit jako čekající návrh. Přesná lock/prerequisite matice a fronta ještě nejsou rozhodnuté.
28. Globální systém Packages je rozhodnutě rozšířen o World, Category, Series, Calendar a Setup. Pouze silným směrem zůstávají další budoucí typy, například `Player Package`, a jejich konkrétní schémata.
29. Celý současný strom Run Adminu `Home / World / Players / Tour / Rankings & Analytics / Simulation / History / Data / Settings`, jeho pořadí, názvy, skupiny i podstránky jsou pouze silným směrem a mohou se měnit podle reálné funkčnosti a pohodlí.
30. `Rankings & Analytics` pracovně obsahuje Rankings, Ratings, Odds a Statistics/Reports. `Tour` definuje oficiální pravidla, zatímco analytická kategorie kontroluje vypočtené výsledky a modely Elo či kurzů; konečné rozdělení není rozhodnuté.
31. `World` pracovně obsahuje World Overview, Countries, Population & Demography a Talent Preview. Overview funguje jako souhrn a blokový rozcestník bez povinné mapy; celý strom je pouze silným směrem.
32. Významové oddělení `p` jako přirozené pravděpodobnosti, `δ` jako směrové vzdálenosti `−1 až +1` a `α` jako její bezsměrové velikosti `0 až 1` je rozhodnuté. Silným směrem zůstává univerzální použití na zápasy, hráče, turnaje, sezony, země a talentové generace; přesná definice typické oblasti a nuly, znaménka, normalizace, vícerozměrná agregace a multimodální distribuce zůstávají otevřené.
33. Nezávazný Forecast Engine může z podporovaného uloženého bodu analyzovat jeden zápas i libovolně vzdálenou budoucnost. Nemění Run, branch, historii, čas ani budoucí náhodnost a na rozdíl od Candidate Branches vytváří statistický report, nikoliv automaticky pokračovatelnou časovou linii; pouze výslovně vybraný vzorek lze později zrekonstruovat a materializovat jako branch.
34. Forecast pracovně dovolí pevný počet pokusů od přibližně 10 po miliardy či více i budoucí Target Accuracy. Předem a průběžně ukazuje očekávaný čas, zátěž, prostor, statistickou nejistotu a konvergenci a dlouhá úloha používá Task Center.
35. Absolute Forecast dědí časově platnou simulační podrobnost a model Runu; samostatně se volí jen Report Detail. Nezměněný Forecast lze postupně zpřesňovat přidáním dalších pokusů, zatímco změna vstupu vytváří nový scénář.
36. Hypotetické Forecast scénáře mohou později měnit vybrané vstupy bez mutace branche a porovnávat dopad na budoucí pravděpodobnosti a jejich rozdíly v procentních bodech.
37. Hráčská AI nemá přístup k Absolute Forecastu ani skutečným pravděpodobnostem. Rozhoduje se z omezených informací a vlastních odhadů; Admin může její rozhodnutí Forecastem pouze nezávisle analyzovat.
38. Persistentní Forecast Markets pracovně sledují otázky jako světová jednička na konci zvoleného kalendářního roku nebo vítěz Team World Championship. Absolute, Public, Bookmaker a případně Market hodnoty zůstávají oddělené a historické snapshoty lze později skládat do Viewer grafů bez prozrazení budoucnosti.
39. Forecast standardně dlouhodobě neukládá jednotlivé virtuální světy. Používá průběžnou agregaci a uchovává kompaktní výsledek, provenance, počet pokusů, dostatečné statistiky, nejistotu a stav potřebný k pozdějšímu zpřesnění; velikost reportu se řídí výstupy a snapshoty, nikoliv přímo počtem pokusů.
40. Future Lock je povinná budoucí podmínka. Stejnou konfiguraci lze nejprve nezávazně ověřit v Locked Forecastu a následně ji použít při skutečné simulaci současné nebo nové branche, aniž by samotný Forecast změnil zdrojová data.
41. Future Lock může cílit do minulosti, přítomnosti i budoucnosti. Viewer lock ani jeho budoucí obsah nevidí, Admin uchovává provenance a splněný lock se označí `Fulfilled`, přestane omezovat další simulaci a zůstane v Admin historii.
42. Lock pracovně vynucuje jen zadanou granularitu a ostatní detaily simuluje přirozeně v rámci slučitelných budoucností. Podporovaným směrem jsou přesné hodnoty, rozsahy, minima, maxima i počty výskytů od vítěze zápasu přes skóre či kolo setkání až po rankingové a kariérní podmínky.
43. U locku se odděluje pravděpodobnost vzniku strukturálně kompatibilního stavu, přirozená absolutní pravděpodobnost celé události a pracovní míra vzácnosti kroků, které musel lock vynutit. Na navazování locků se používá proveditelnost, nikoliv čekání na každou přirozeně náhodnou shodu.
44. Je-li budoucí ranking, nasazení, účast a formát slučitelný se zamčeným kolem vzájemného zápasu, lock může vynutit platné draw sloty a podle své podrobnosti i nutné předchozí postupy. Neslučitelnou kombinaci nasazení však nesmí tajně porušit; takový pre-draw stav se vyřadí jako neproveditelný.
45. Více Future Locks se vyhodnocuje jako pořadím nezávislý společný soubor. Forecast pracovně ukazuje jednotlivé i společné pravděpodobnosti, společnou proveditelnost a hlavní bottleneck, který nejvíc zužuje množinu platných budoucností.
46. Konflikty a extrémní vzácnost mají viditelné vykřičníky, vysvětlení a nabízená řešení bez tichých oprav. `Conflict Fork` se dvěma dočasnými Candidate Branches `Lock Path / Change Path` je výslovně pouze běžný, nikoliv silný směr a musí zabránit nekontrolovanému růstu `2ⁿ` variant.
47. `Scenario Direction` je výslovně pouze běžný směr odlišný od povinného locku: s volitelnou silou může transparentně ovlivňovat pravděpodobnosti vývoje světa, ale nic nezaručuje. Přesný rozsah, čas, skládání a technický model byly přeskočeny a zůstávají otevřené.
48. Forecast Session má pracovně 256bitový master seed, stabilní sample indexy a dvě akce `Repeat Exactly / New Random Run`. Seed se běžně generuje automaticky, v pokročilém režimu jej lze zobrazit, kopírovat či zadat ručně; miliardy samostatných seedů se neukládají a totožné přirozené výsledky se normálně započítají.
49. Forecast pracovně vyhodnocuje přesnost po dávkách pomocí intervalů a stability distribuce v několika po sobě jdoucích dávkách. Primární metriky řídí zastavení, vedlejší ukazují vlastní přesnost; session lze při totožných vstupech prodloužit o další vzorky a nový údaj dopočítat z uchovaných statistik nebo deterministickým replayem.
50. Adaptivní Forecast Visualizer volí graf podle otázky. U zápasu pracovní `Match Outcome Landscape` skládá vzorky na ose `δ` kolem typické nebo nejpravděpodobnější oblasti, odděleně značí konkrétní nejpravděpodobnější skóre a hranici vítěze a při velkém počtu přechází z kuliček na poctivou agregovanou hustotu bez nucené Gaussovy křivky.
51. Forecast filtry mají režimy `Highlight` a `Focus`, vždy ukazují počet odpovídajících vzorků a nejistotu a mohou pokračovat do cílového počtu shod. `Natural Sampling` zůstává nedotčený; transparentní `Rare Event Accelerator` vytváří oddělený vážený child `Conditional Forecast` a nesmí usměrněné vzorky vydávat za běžné přirozené světy.
52. Kliknutí na konkrétní nebo reprezentativní Forecast vzorek otevírá `Scenario Inspector`; vzorek se na vyžádání rekonstruuje ze snapshotu, seedu, sample indexu a verze. `Pin Scenario` uloží jen lehký odkaz, poznámku a souhrn a připnuté scénáře jsou dostupné v původní session i na Runové stránce `Saved Scenarios`.
53. Vybraný vzorek nebo reprezentant filtrované množiny lze explicitně převést na branch v libovolném podporovaném bodě jeho historie. `Continue This Scenario` zachová již nasimulovaný náhodný proud, zatímco `Fork From This Point` převezme dosažený stav a další budoucnost znovu znáhodní; vždy se uloží úplná provenance.
54. `Why This Scenario?` pracovně ukazuje odhadované přispívající faktory bez předstírání jisté kauzality. `Quick Counterfactual` vytvoří jeden podobný replay a `Statistical Counterfactual` porovná více párových simulací s intervencí a bez ní; podporované zásahy mohou událost odstranit, nahradit, upravit, obrátit výsledek, neutralizovat nebo znovu vylosovat.
55. Counterfactual zachová celou minulost před bodem zásahu, provede vybranou změnu a od ní znovu nasimuluje všechny potenciálně ovlivněné následky. Původní budoucnost se uměle nedrží, pokud její konkrétní části Admin samostatně nezamkne.
56. World Package pracovně používá dvě nezávislé geografické vrstvy: Travel Regions pro hrubou fyzickou vzdálenost a kruhové Timezone Areas pro biologický posun. První verze nepočítá kilometry a přesný pobyt hráče; jet lag hrubě odvozuje z poslední známé turnajové zóny, směru a mezery mezi zápasy.
57. Už první verze může hráčům generovat oddělené predispozice `Jet Lag Resistance` a `Travel Resilience`; přesné škály, účinky a jejich vazba na rozhodnutý tříúrovňový Travel Load, jet lag, Fatigue a recovery jsou otevřené.
58. Silným směrem jsou automaticky rozpoznané dvojicové i vícečlenné rivality, více souběžných rivalit jednoho hráče, jejich historický vývoj a Manual Rivalry pro známou nesimulovanou minulost bez vymyšlených H2H. Číselné Rivalry Score je pouze slabý směr.
59. Manual Rivalry sama nemění los. Běžný Scenario Direction může transparentně zvýšit pravděpodobnost společných turnajů a vzájemných zápasů, zatímco záruka konkrétního setkání patří pod Future Lock.
60. Tournament Series může mít vlastní proměnlivé Prestige Score s typickým výchozím defaultem kategorie. Prestiž se změnou kategorie neresetuje, mění se postupně a Admin ji může upravit či zamknout; přesný výpočet je otevřený.
61. Oddělení obecného Prestige Score od individuálního Tournament Appeal je pouze slabý směr. Běžným směrem je zobrazovat přesnou interní hodnotu v Adminu a ve Vieweru spíše slovní úroveň, pořadí a historický vývoj.
62. Dobrovolný retirement má běžným směrem vycházet z průběžné individuální ochoty pokračovat, do níž vstupuje věk, zdraví, výkonnostní trend, ambice, výsledky, motivace, osobnost, očekávaná budoucnost, neaktivita, zranění, neúspěchy, úspěchy a blízkost významného cíle; nemá jít pouze o jeden věkový náhodný hod.
63. Pouze slabým směrem je, aby hráčská AI při kariérní krizi výslovně porovnávala pokračování jako Active, dočasný stav Inactive a dobrovolný retirement.
64. Po větší simulaci má Admin běžným směrem nabídnout znovu otevřitelný neblokující soukromý digest výsledků, změn, rekordů, překvapení, upozornění a Future Locks, aniž by jeho zavření nebo přečtení podmiňovalo další simulaci.
65. Oddělené `News Importance Score` pro Viewer a Admin je pouze slabý směr. Přesná škála, vzorec, prahy a název nejsou rozhodnuté; uvažovanými vstupy jsou například prestiž, překvapivost, význam hráče, rankingový dopad, rekord a rivalita.
66. Silným směrem je měnit lifecycle Tournament Edition přes explicitní Admin akce jako Cancel, Postpone, Edit Result nebo Force Resolve s povinným důvodem, impact preview a Audit Logem, nikoliv raw dropdownem.
67. Společné přehodnocení všech relevantních turnajů v jednom entry decision slotu je už rozhodnuté. Prozatímní zůstává konkrétní inteligence portfolia: faktory, váhy, náhodnost, práce s podobně výhodnými možnostmi, míra plánování dopředu a její postupné zlepšování v dalších verzích enginu.
68. Silným směrem je, aby změna sezonního Best N automaticky upravila všechny navazující budoucí sezony, které hodnotu pouze dědí, zatímco ruční sezonní overrides zůstanou chráněné.
69. Prozatímní pracovní interpretace krajů škály Financial Levelu je `0 = minimální přístup ke zdrojům` a `10 = téměř neomezený přístup k elitní přípravě, cestování a péči`. Samotná škála `0–10` a její testovací použití jsou pevné; význam mezistupňů a výchozí distribuce zůstávají otevřené kalibraci.
70. Silným směrem je jedna obecná zdravotní přestávka první verze bez detailního rozlišení původu či zavinění zranění a použití stejného základu `pokračovat / zdravotní přestávka / RET` také při náhlém zhoršení nemoci.
71. Pracovním, nikoliv pevným výchozím počtem první Match Reconstruction je deset kandidátů; hodnota se může po testování změnit.
72. Silným směrem je po prvním použití zapamatovat poslední zvolený počet kandidátů jako výchozí pro další rekonstrukci, přičemž jej lze před každým spuštěním změnit.
73. Pouze běžným směrem je statistická architektura Match Reconstruction: oddělené `Validate Constraints / Calculate Probability / Generate Matching Scenarios`, výskyty `k/N`, interval nejistoty, průběžné či cílově přesné výpočty, bezpečné early pruning, diagnostické plné průchody, transparentní Rare Event Accelerator a rozlišení logické nemožnosti od výpočetní neproveditelnosti. Význam `p / δ / α` je již rozhodnutý, ale jejich výpočet, pevný limit jedné miliardy simulací a přesné oranžové/červené prahy nikoliv.
74. Pouze slabým podmíněným směrem je trvalá Reconstruction Session po zavření okna; nepatří mezi požadavky první verze a má se přidat jen při úsporné retenci bez významné datové režie.
75. Pouze běžným směrem je pracovní obsah kompaktní karty kandidáta: výsledek a skóre gamů, délka, Match Performance obou hráčů, počet rally, konečná stamina a nejdůležitější mimořádná událost. Konečný obsah se navrhne později.
76. Prozatímním směrem je v první verzi nepřidávat automatický domácí bonus pouze podle národnosti. Případný pozdější model potřebuje skutečné místo utkání, bydliště či Home Base, tréninkové zázemí, publikum a individuální reakci hráče.
77. Pouze slabým směrem je skrytá `Match-Day Baseline` lepšího či horšího dne před zápasem. Nesmí nahradit skutečnou Match Performance vznikající z rally, soupeře, atributů, formy a aktuálního stavu a není rozhodnutým povinným vstupem první verze.
78. Pre-alpha katalog šesti kategorií a 57 aktivních atributů je od v49 rozhodnutý. Prozatímním směrem zůstává jeho výrazné pozdější testování, rozšiřování, slučování a změny taxonomie v dalších verzích enginu.
79. Silným směrem pro dobu po pre-alpha je ruční sloučení dvou skutečně totožných Runových entit pod jedno kanonické ID se zachováním druhého ID jako aliasu, bezpečným převodem vazeb a provenance všech zdrojů. Automatické sloučení pouze podle názvu je vyloučené.
80. Pro dobu po pre-alpha zůstává směrem pokročilé porovnání a vědomé slučování divergentních Package historií. Bezpečné minimum první verze – odmítnutí přepsání a případný import jako nový Package – je již rozhodnuté.
81. Širší zákaz tichého conflict resolution a nabídka všech proveditelných datově bezpečných možností jsou rozhodnuté. Pouze směrem zůstávají konkrétní field-level nabídky, pojmenování akcí, layout a přesné zacházení s entitou `Removed from source` v jednotlivých historických situacích.
82. Pro pozdější verze je směrem vlastní pravděpodobné očekávání hráčské AI, že se pravidelná Tournament Series uskuteční v podobném období i další sezonu, odvozené pouze z veřejné historie, pravidelnosti a významu. První verze tento odhad nepoužívá a skryté Edition Plans nesmějí být jeho zdrojem.
83. Prozatímním Official Run defaultem první verze je číselná mapa Potential OVR `L+ 194` až `F− 171` po jednom bodu mezi sousedními labely. Jde o orientační první odhad; existence jednoho měkkého Potential OVR a možnost jeho extrémně vzácného překročení jsou již rozhodnuté.
84. Prozatímní výchozí distribuce typů vývoje při vytvoření hráče je `Early Bloomer 16 % / Standard 68 % / Late Bloomer 16 %`.
85. Prozatímní věkové středy jsou `26 / 29 / 32` let a orientační prime pásma `24–28 / 27–31 / 30–34` pro Early / Standard / Late. Nejde o pevný skutečný peak hráče ani rankingu.
86. Potvrzeným směrem pro verzi 3+ je, aby se nízký Match Sharpness nejsilněji projevil na začátku zápasu a jeho bezprostřední vliv se během zápasu mohl částečně zmenšovat. Přesný intra-match model není součástí pre-alpha brány.
87. Prozatímní mužský elitní RallyCalibrationProfile pre-alpha cílí napříč reprezentativním vzorkem na medián přibližně `11–13` úderů a 75. percentil `19–23`; hráčské matchupové průměry se mohou podle stylu pohybovat přibližně `13,5–20`. Starý 95. percentil `42` je pouze historický benchmark, nikoliv zamčený současný cíl, a přesné tempo, higher-tail křivka i opening-end rate čekají na datový fit a testování.
88. Prozatímní mužská elitní kalibrace běžných mezer mezi rally míří převážně na `8–18 s` a průměr kolem `13 s`; velmi rychlé navázání může být přibližně `5–9 s`, přirozený reset po mimořádné zátěži `15–25 s` a interval nad `30 s` obvykle potřebuje samostatný důvod nebo time-wasting posouzení. Nejde o pevnou lhůtu ani tvrdý cap a profil se bude testovat na větších současných datech.

---

# 30. Hlavní otevřené a odložené otázky

Každý očíslovaný bod této kapitoly je od verze 48a stabilní **široký okruh nezodpovězených nebo výslovně odložených otázek**. Jeho kanonické označení vzniká doplněním čísla na tři místa: bod 1 je `OQ-001`, bod 37 je `OQ-037` a bod 69 je `OQ-069`. Toto označení dovoluje otázku přesně citovat, aniž by se měnil původní souvislý registr.

`OQ` není nový status. O skutečném stavu vždy rozhoduje text bodu a odpovídající detailní kapitola: jeden široký okruh může současně obsahovat již rozhodnutý základ, otevřený detail i část odloženou na později. Atomické podotázky skutečně nutné pro první pre-alpha verzi jsou odděleně vedené v kapitole 31 jako `PAQ`; tím se zabrání tomu, aby se kalibrace, technický detail, Official Run obsah a uživatelské produktové rozhodnutí zaměnily za jednu otázku.

**Příklad:** `OQ-037` říká, že dlouhodobá historie losu není uzavřená. `PAQ-093` z ní izoluje konkrétní produktovou otázku, zda každý potvrzený los nebo jeho oprava vytvoří neměnnou `Draw Version`.

## Runy, ukládání a branche

1. Detailní UX operation-scoped validace, konkrétní checklisty, katalog budoucích simulačních akcí a případný neblokující onboarding. Hierarchická prerequisite matice současných rozsahů, blokování pouze zvoleného závislého scope, progresivní validace dlouhého horizontu a vyloučení povinné globální Setup/Start brány jsou od v57 rozhodnuté.
2. Přesný automatický formát odvozeného názvu při kopírování nebo importu Runu, pravidla porovnávání velikosti písmen a drobné UX pozdějšího přejmenování branchí. Jedinečnost názvů Runů napříč aktivními i archivovanými Runy, jedinečnost názvů branchí uvnitř Runu a výchozí řada `Timeline N` s upravitelným návrhem jsou rozhodnuté.
3. Úplný konečný seznam datových skupin a nejjemnější granularita `Pokročilé kopie` Runu; její dva režimy, doplňování závislostí, preview a nové `run_id` jsou rozhodnuté. Dále přesné obrazovky, importní volby, rozsah snapshotu a životní cyklus sessions vestavěného Match Test Labu; read-only baseline, oddělená session, provenance a nulový dopad na zdrojový Run jsou rozhodnuté.
4. Úplný katalog rizikových operací vyžadujících automatický fork-safe checkpoint a jeho technický formát. Je rozhodnuto, že checkpointy nevznikají periodicky, ruční lze vytvořit kdykoliv a automatický vzniká před operací schopnou nahradit nebo odstranit uložený stav či budoucnost.
5. Přesné algoritmy rozdílového ukládání, deduplikace, komprese, interval technických snapshotů a výkon obnovy; přesná kapacita Undo/Redo v jedné relaci, slučování rychlých editací a jeho chování po částečném uložení. Každý Save vytváří verzi, umělé storage limity neexistují a částečné ukládání logických balíčků je rozhodnuté. Od v50 je rozhodnutá také hranice Working Draft/Saved Revision, simulace z validního draftu, potvrzovací diff, zákaz běžného Save při červené chybě a možnost uložit nezávislé validní balíčky; otevřený zůstává přesný katalog těchto balíčků a frontendové provedení.
6. Retence, velikost, více souběžných recovery draftů a jejich vztah k novější pracovní relaci nebo Candidate Branch recovery. Základ obnovit / read-only prohlédnout / zahodit je rozhodnutý.
7. Retence dočasně obnovených Candidate Branches, přesné chování jejich odstranění a okamžik uvolnění recovery dat po běžném uložení.
8. Přesné vizuální provedení, badge, filtry a přechody rozhodnutých lifecycle stavů `Working / Completed / Archived` a samostatných os původu, editovatelnosti a validity. Samotný stavový model je rozhodnutý a nesmí zavést povinný globální přechod `Setup → Active`.

## Packages, země a populace

9. Přesné pokročilé UX, priority a field-level varianty řešení konfliktů při importu více Packages stejného typu nebo při výslovném přenosu novější verze zdroje do existujícího Runu. Rozhodnuté jsou source identity, Run-local ID, no-op stejné verze, bezpečný výběr části aktualizace, zákaz tichého přepsání a pre-alpha fallback divergentní historie jako nového Package. Ruční kanonický merge a pokročilé porovnání či slučování divergence zůstávají směry mimo pre-alpha.
10. Úplný field-specific katalog, přesné konfigurační UI, validace a migrace hodnot dostupných na jednotlivých úrovních. Samotná hierarchie `Official default → Package → Run → season → Competition System → Tour → Category → Series → Edition Plan → Edition → phase → round → match`, nearest-permitted-override pravidlo, provenance, lock minulosti a užší Match Format výjimka jsou od v62 rozhodnuté.
11. Přesný datový formát, Admin UX a validace vzniku, deaktivace, reaktivace a nahrazení Competition Systems, Tours a Categories. Historická proměnlivost, stabilní číselná ID, nerecyklování ID, sezonní hierarchie, lokální význam `tier_rank`, speciální `tier_rank = null`, dědění pořadí i sourozenecká unikátnost názvů jsou rozhodnuté. Shodný `tier_rank` více srovnatelných sourozenců je výslovně odložen do dalších verzí.
12. Individuální kompatibilita a migrace World, Category, Series, Calendar a Setup Packages vůči starší či novější verzi schématu enginu; heuristické matching a detailní pozdější ruční mapping UX unresolved referencí; konfliktní priority; konečný obsah Setup mapování a přesná souborová schémata. Významová hranice Series versus Calendar Package, nedestruktivní partial scope všech pěti typů, přesné automatické vyřešení podle kompatibilní source identity, bezpečné pre-alpha minimum chybějící závislosti, Setup version snapshot, aplikace neúplného Setupu a Package version lifecycle už jsou rozhodnuté. Samostatně zůstává otevřený katalog dalších budoucích typů včetně případného `Player Package`.
13. Country Model V1: přesné váhy a vzorce šesti ratingů, význam hranic `1/2/3/4/5`, conversion rates, velikost každého ročníku talentů, kalibrace konkrétních zemí, odvození Effective Squash Pool / Competitive Depth / Talent Discovery Rate / Professional Conversion Rate / Current Country Strength a případný dynamický historický vývoj ratingů. Rozhodnuté jsou názvy, významy, škála 1–5, oddělení faktických a odvozených hodnot a zákaz přímého národního vlivu na vrozený talent. `style_dna` zůstává odložené do zralé atributové a stylové verze.
14. Přesné mapování libovolně pojmenovaných sloupců, úplná sada doménových validátorů a konkrétní vzhled CSV/XLSX importního editoru. Staging preview, přesné vysvětlení chyb, opravování bez nového uploadu, bezpečný částečný import nezávislých řádků a atomický zápis jsou rozhodnuté.

## Hráči

15. Přesný počáteční pool a baseline ranking sezony 2000/01.
16. Přesný model hráčské AI pro okamžik a volbu první platné turnajové přihlášky nebo získání wild card: váhy schopností, věku, osobnosti, příležitostí a kumulativního tlaku. Formální trigger, implicitní přijetí definitivně přidělené WC, trvalost statusu po neúspěchu pod cutem, počáteční `NR`, zařazení až v následujícím Official Ranking snapshotu i pravidlo, že každý automaticky vygenerovaný prospect nakonec vstoupí, jsou rozhodnuté.
17. Přesný název juniorského statusu, grafické rozložení profilu, podoba souhrnných statistik juniorského mistrovství světa a vzhled prázdné juniorské sekce.
18. Přesná matematika developmentu, růstu, plateau, decline a návratů; hráčská inteligence, scouting, odhad soupeře, paměť, tvorba gameplanu a kariérní i zápasová adaptace stylu. Pevný jediný `peak_week` je vyloučený. Rozhodnuté jsou typy `Early Bloomer / Standard / Late Bloomer`, jejich celoživotní stálost, nezávislost na potenciálu, jednoduchý posun společné křivky o `−3 / 0 / +3` roky a princip dřívějšího poklesu fyzických schopností oproti možnému pozdějšímu růstu technických, taktických a mentálních schopností. Distribuce `16/68/16` a středy `26/29/32` jsou pouze prozatímní; otevřené zůstávají přesné atributové křivky, development matematika, rozhodovací váhy, chyby odhadu a kalibrace.
19. Přesné kontextové váhy 57 aktivních pre-alpha atributů, konkrétní první OVR váhy a normalizace, pozdější individuální váhové profily, pravděpodobnostní křivka vývoje v okolí a nad Potential OVR, distribuce potenciálových labelů a pokročilá granularita potenciálu. Rozhodnuté jsou atributová škála `0–200`, samostatné uložení všech 57 hodnot, jejich kontextové používání, organizační role kategorií, OVR `0–200` jako normalizovaný vážený průměr, oddělená letter škála potenciálu `L+–F−`, jeden celoživotně pevný měkký Potential OVR bez per-attribute stropů, možnost extrémně vzácného překročení a absolutní OVR cap `200`. Číselná mapa Potential OVR zůstává prozatímní.
20. Přesná matematika Form, Experience, Match Sharpness, Match Preparation, výšky, hmotnosti, zdraví, dlouhodobé únavy, recovery, travel a nového Financial Levelu. Rozhodnuté hráčské základy zahrnují Experience `General + High-Pressure`, Match Sharpness `0–100 %`, Match Preparation `0–100 %`, tři dynamické fyzické a dva mentální bary a kontinuitu Fatigue bez resetů. Zdravotní minimum od v50 rozlišuje Injury/Illness, více souběžných záznamů, Severity `0–100`, typové profily, lifecycle `At Risk / Active / Recovering / Recovered`, nejisté rozmezí zotavení, individuální predispozice, nesčítavé skládání, jednotný kontextový Health Check a oddělení engine truth od hráčova nedokonalého odhadu. Financial Level `0–10` je experimentální dynamický odhad zázemí bez účetnictví, s malými oddělenými účinky a bez obecného přímého match bonusu; ligový squash se nemodeluje. Otevřené zůstávají všechny číselné křivky, pravděpodobnosti, skládání, detekce, léčba, výchozí distribuce a update Financial Levelu, AI prahy, rozhodnutí nastoupit a RET/W/O či lékařský zákaz. U travel jsou rozhodnuté Travel Regions, kruhové Timezone Areas a `Low / Medium / High Travel Load`; otevřené zůstávají jeho prahy, síla, topologie, odeznívání a hlubší vazba na výkon.
21. Doklady a ověřování Country eligibility, číselné pravděpodobnosti a jejich kalibrace včetně extrémně vzácné AI žádosti o World, juniorské a přesně vymezené mimořádné nesportovní případy, podmínky případné druhé dobrovolné změny, úplný workflow schvalování FAX a detailní Admin UX. U `Country ↔ Country` není rozhodnuto, zda a kdy smí FAX zkrátit 122weekovou lhůtu. Pevné už je oddělení `origin_country_id` od časově verzované Sporting Representation, její typy `Country / World / FAX Neutral`, jejich účinky na individuální Tour a týmovou eligibility i nepřepisování historických výsledků.
22. Přesné AI důvody a pravděpodobnosti vstupu do `Inactive`, dobrovolného retirementu a comebacku, Viewer/Admin workflow ruční změny a jejich načasování uvnitř weeku. Pro retirement už existuje běžný faktorový směr a pouze slabý směr třícestného porovnání `Active / Inactive / retired`; konkrétní algoritmus se má kalibrovat až nad funkční první verzí. Je rozhodnuté, že pouhá dlouhá absence status nezmění a první platná Tour přihláška nebo přijatá WC obnoví `Active` i bez průchodu cutem.
23. Přesná vizuální stylizace, responzivní zkracování a lokalizace již rozhodnutého rozlišení shodných jmen. Funkční fallback `Sporting Representation + birth year → birth_year_week → stabilní veřejný diskriminátor`, povinný kontext vyhledávání a technická identita `player_id` jsou od v57 pevné.

## Turnaje a zápasy

24. Zda se současný testovací katalog Competition Systems, Tours a kategorií stane konečným, nebo jej simulace částečně či úplně překopou. Funkční hierarchie `Competition System → volitelný Tour → Category`, sezonní přesuny při zachování identity a oddělení tierových od speciálních kategorií jsou již rozhodnuté; otevřený je konkrétní Official FAX obsah.
25. Přesné číselné bodové tabulky, případné prize-money částky, konkrétní kapacity pavouků a kvalifikací a další sezonní hodnoty jednotlivých kategorií. Rozhodnuté jsou Ranked default, možnost typu `Unranked Only`, povolené statusové přechody a mimořádné odebrání statusu, úplnost bodů pro zveřejněnou Ranked Edition, sezonní dědění bodové tabulky, její Q + Main Draw struktura a nepovinné prize money první verze.
26. Přesné umístění `Final Commitment Deadline`, případné další entry cut-offy, konec dostupnosti jednotlivých náhradních zdrojů a jejich vztah k Draw Weeku. `Redraw Cutoff` na začátku předposledního a `Draw Freeze` na začátku posledního procesního okna jsou už samostatně rozhodnuté pro Qualification i Main Draw; stejně tak po Final Commitment zůstává week zamčený i po odstoupení, s výjimkami vymezenými v kapitole 15.1.
27. Přesná sankční tabulka konfliktů, pozdních odhlášení a no-show: velikost odečtu bodů, délky `X` weeků a okamžik účinnosti či expiry Disciplinary Zero, kombinace více provinění, důkazní standard a další omluvitelné důvody. Základ stavově závislých uzávěrek, rostoucí závažnost, skládání nul, zdravotní výjimka a zákaz dvou skutečně hraných turnajů v jednom weeku jsou rozhodnuté. Pro pokročilejší verzi zůstávají přesná hrací období, případné dva krátké turnaje v jednom weeku, clash lift, detailní doprava a víza.
28. Přesné weekové načasování kvalifikačních fází a číselné Q bodové tabulky. Rozhodnuté jsou jedna Q stage hodnota, její přičtení k Main Draw složce u kvalifikanta i LL, vyšší hodnota `Qualified` než LL a společné jedno místo v Best N.
29. Detailní FAX/Admin lifecycle UI, složité přesuny přes hranici sezony, další mimořádné kompenzace a okrajové podmínky výslovného přiznání výsledku či titulu. Třívrstvý katalog a přechodová matice, explicitní doménové akce, `Postponed / Cancelled / Suspended / Abandoned`, jejich sportovní důsledky i hranice krátkého přerušení podle Match Day Slotu jsou od v62 rozhodnuté.
30. Kurty, venues a případné budoucí přesné časy. První verze už má denní Match Day Slots, tvrdé scheduler podmínky, přesné lexikografické fair-rest priority, pevné uložené pořadí, feeder placeholdery, carryover a minimální přepočet po zveřejnění. Otevřená zůstává číselná délka a kapacita slotů, detailní optimalizace v rámci shodných priorit, složité odklady, přeložení, paralelní kurty a venue logistika. Vliv rychlosti či pomalosti prostředí, odskoku a dalších podmínek kurtu je výslovně určen až pro pozdější pokročilou verzi a první verze jej ignoruje.
31. Přesný obecný vztah technického statusu `Default` k DQ, konkrétní katalog a sazby disciplinárního forfeitu bodů či prize money po DQ zahájeného zápasu a pravděpodobnostní model RET/W/O/DQ/ABN. Při obnovení suspendovaného zápasu je už rozhodnuto, že zdravotní nemožnost pokračovat znamená RET, neodůvodněné odmítnutí či no-show Default a vnější příčina ABN. DQ před startem s nulou bodů i prize money a sportovní výhra/prohra po zahájeném DQ jsou rovněž rozhodnuté.
32. Přesná matematika rally-by-rally Match Enginu: transition probabilities mezi pěti stavy kontroly, pravděpodobnosti terminálních incidentů, kontextové váhy atributů, styly, gameplany a úsilí, dva mentální a tři fyzické bary, finální kalibrace délky, úderů, pace, individuální zátěže, podání a interference. Granularita bez shot-by-shot simulace, čtyřvrstvá pipeline, atributové role, čtyřosý styl/gameplan, setrvačné transitions, `0–24` segmentů, opening podání, ground truth, rules resolver, terminální katalog, Rally Resolution Record, společný zdroj délky/úderů/workloadu, RallyCalibrationProfile, kauzální tempo mezi rally i neměnný hashovaný Rally Event/Post-Rally Snapshot log jsou rozhodnuté. Stejně tak Step Back/Forward, Auto Play a Replay používají uloženou pravdu bez rerunu RNG. Otevřené zůstávají přesné matice a distribuční křivky, datový fit, retence alternativních pracovních cest po opuštění zápasu, ruční override AI, kalibrace analytického připsání, finální restartové distribuce a conduct thresholds, zdravotní triggery, účinek ošetření a matematika dalších přerušení. Minimální turning, further attempt, zásah hráče míčem i taktické tempo patří do pre-alpha; chyby a individuální profily rozhodčích, detailní review, přesné trajektorie a jemná subjektivita enforcementu zůstávají pokročilé.
33. Mimořádné edge cases seed cascade, detailní atomické preview a pravidla vědomého ručního porušení standardního repair workflow. Běžné tři fáze, tier-aware cascade, zachování seed čísel, přímá náhrada nenasazeného slotu a zákaz automatického úplného redraw po příslušném cut-offu jsou již rozhodnuté.
34. Kompletní pořadí skupinové kvalifikace, tie-breaky, odstoupení během skupiny a srovnání stejných nepostupových míst pro LL.
35. Přesná WC eligibility, tvorba a seřazení RWC seznamu, důvody ztráty dostupnosti a detailní Admin/Viewer historie. Priorita dostupné RWC, její trvající `Available` status, implicitní přijetí finálního přidělení, automatické odebrání WC při přímém vstupu a zachování historického původu jsou již rozhodnuté.
36. Přesný celkový počet, názvy, délka a výchozí rozložení časných procesních oken uvnitř weeku, optimalizace souběžných turnajů, vztah samostatných Qualification a Main Draw plánů a mimořádné edge cases přesunu hráče z hotového Q losu. Pevné už je, že existuje jediná globální osa Simulation Slots, procesní okna začínají na jejích hranicích, Match Day Slots se na ni mapují a dependency scheduler dovolí současnost jen nezávislým událostem.
37. Přesná dlouhodobá historie draw verzí a rozdíl mezi preview Undo, auditem, uloženou verzí a branchí. Poslední návrh, aby každý potvrzený los nebo jeho oprava vytvořily novou neměnnou `Draw Version`, zůstal bez uživatelské odpovědi a není rozhodnutý.
38. Team World Championship: field, kvalifikace, kalendářní weeky, skupinová/play-off struktura, úplný turnajový formát, konkrétní výchozí hodnoty a minimální validace `roster_capacity`, seznam uznávaných důkazů a detailní Admin workflow mimořádných náhrad a přesné pořadí odehrání šesti dvouher. Atribut kapacity, default roster locku, pevný rankingový snapshot, zákaz neklasifikovaných hráčů, Country-only týmová eligibility, vyloučení World/FAX Neutral a automatického World týmu, pravidla náhrad, neúplná sestava, technické W/O a řešení stavu 3:3 jsou rozhodnuté. Pořadí od `#6` k `#1` bylo odmítnuto.
39. Kontinentální mistrovství: kompletní individuální i týmové formáty, kvalifikace a bodování. Jejich konkrétní periodicita je obsah Runu a nemá se pokládat jako otázka funkčnosti enginu. Národní mistrovství: počáteční seznam zemí, postupné rozšiřování, eligibility, formáty, kapacity, bodování a kalendář. Olympijské hry jsou rozhodnutě v současném veřejně simulovaném rozsahu, ale jejich periodicita, eligibility, kvalifikace, field, formát, bodování a kalendář zůstávají odložené jako obsah Official Runu.
40. Abstraktní fungování Challenger Tour a Development Tour bez detailní simulace zápasů a pavouků.

## Rankingy, historie a predikce

41. Protected Ranking: přesná taxonomie a ověřování důvodů, omezení přerušené absence, definitivní výpočet hodnoty, definitivní seeding, vztah k LL, přesné napojení spotřeby použití na Entry/Freeze cut-offy a nové zranění po návratu. Tříletá aktivace, základ spotřeby, tie-break a současné povolené kategorie už mají Official Run default.
42. Další sezonní pravidla výpočtu rankingu, povolené hodnoty Best N a jejich validace. Rozhodnuté je, že první sezona Official Runu začíná Best 15, další převezme efektivní hodnotu předchozí sezony a každá sezona zůstává samostatně konfigurovatelná; automatické propsání změny do všech budoucích zděděných sezon je zatím pouze silným směrem.
43. Přesné číselné Qualification points pro jednotlivé kategorie, sezony a stages. Jejich jedna-stage hodnota, aditivní vztah k Main Draw, rozdíl kvalifikanta a LL, BYE unlock a jedno společné Best N místo jsou již rozhodnuté.
44. Přesný Live Ranking a propadávání bodů uvnitř weeku.
45. Country Ranking: jeho význam a vzorec jsou výslovně odložené do doby, kdy bude fungovat základ simulace a vzniknou srovnatelná data. Race, Elo, Form a další metodiky zůstávají otevřené samostatně. Budoucí FAX Game má používat veřejné výkonové OVR oddělené od Admin truth, ale přesná data, období, atributy, vzorec a Viewer UX se vymyslí později.
46. Technický model historických snapshotů a dopočtu po změně minulosti. Od v50 je rozhodnuto, že velká změna atributu nabídne okamžitou změnu nebo `Dopočítat historický vývoj`, tři pre-alpha režimy přirozené/přesné/podobné historie, kandidátní cesty, tvrdý soutěžní skelet přesného režimu, měkké cíle podobnosti, výpis odchylek a development guardrails. Otevřené zůstávají algoritmus cest, metrika podobnosti a realističnosti, kalibrace `p / α`, výkon a přesná technická propagace; samostatné osy rozsahu × míry zachování jsou výslovně odložené do dalších verzí.
47. Awards a Player of the Year.
48. Konečný kontrakt Forecast Enginu: matematika Absolute a Viewer/Public Prediction, definice „absolutní“ modelové pravděpodobnosti, přesnost a confidence intervaly, práce se vzácnými výsledky, maximální praktický rozsah, Target Accuracy, dávkové stopping rules, stabilita distribuce, primární a vedlejší metriky, průběžná agregace, dostatečné statistiky a continuation state, dočasná pracovní data, retence, cache, deduplikace a profily Compact/Reusable. U Forecast seedu zůstává otevřený konkrétní derivační algoritmus, reprodukce napříč hardwarem a dlouhodobá dostupnost starých modelových verzí; samotný 256bitový master seed, sample index, přesné opakování a nový náhodný běh jsou silným směrem. Dále jsou otevřené přesné adaptivní grafy, mapování nuly a os, reprezentativní body agregovaných oblastí, filter builder, uchovávané značky, Natural Sampling, Rare Event Accelerator, importance weights, efektivní velikost vzorku a pravidla oddělených Conditional Forecasts. U Scenario Inspectoru a Saved Scenarios zůstává otevřený formát replaye, retence pinů, výběr reprezentativních scénářů, materializace do branche a migrace provenance. U counterfactualů přesný kauzální model, párování seedů po divergenci, intervenční katalog, vysvětlení vlivu, confidence contract a side-by-side UX. Dále scenario overrides a porovnávání, datový formát reportu, resolution rules a vztah k Candidate Branches a Compare States. U Future Locks přesná matematika Feasibility, Natural Absolute Probability a Forcing Cost, cílené generování a korektní váhy, konečný katalog přesných/rozsahových/agregačních podmínek, kombinace více locků, bottleneck výpočet, statusy, warning prahy, conflict UX, aplikace do současné či nové branche a přepočet minulosti. Výslovně přeskočený a otevřený zůstává životní cyklus pozdější úpravy nebo odstranění nesplněného či splněného locku. `Conflict Fork` i `Scenario Direction` jsou pouze běžné směry; u Direction navíc zůstává otevřený rozsah, období, síla, skládání a systémy, které smí ovlivnit. Významy `p`, `δ` a `α` jsou již oddělené; otevřené zůstávají přesná definice typické oblasti, nula, znaménka jednotlivých perspektiv, normalizace, multimodální a vícerozměrné výsledky a agregace. U Forecast Markets přesná definice možností a `Other`, frekvence či triggery přepočtu, fair odds, bookmaker marže, případná simulace tržních účastníků, historické grafy, Viewer web a ochrana před future leakem.

## Technika a UX

49. Determinismus a seed contract celého enginu; otázka byla 5. 8. 2026 výslovně přeskočena. Determinismus samotného losu je rozhodnutý, reprodukovatelnost konkrétních Forecast vzorků je užší silný směr a nově je rozhodnutý úzký retry contract neúspěšného batch procesu. Ani tyto tři užší kontrakty samy neuzavírají obecnou otázku.
50. Úplná tabulka konkrétních Admin/Viewer route protějšků a celý strom jednotlivých stránek; obecný přenos Runu, času, objektu a podstránky, mapování do současné `Viewer Branch` i vysvětlený fallback už jsou rozhodnuté. Od v50 je rovněž rozhodnuto, že nové označení Viewer Branch začne působit až potvrzeným Save. Dále zůstávají otevřené přesný layout a případné budoucí další vstupy `Squash Engine Home`; úplný obsah Run `Home`, přesná vizualizace a případná klikatelnost jeho 50/61 segmentů a jejich vztah k prohlíženému versus nejnovějšímu času; konečné potvrzení pracovního Run Admin stromu a podstránek `World` a `Rankings & Analytics`; přesný obsah řádků, filtry, řazení a rozložení tří akcí na `Všechny Runy`; layout globálního Packages přehledu a jeho typových seznamů; navigace při neuložené práci a jemné chování hover/pin sidebaru; vztah globální lišty k navbaru jednotlivého Viewer webu; konečné kategorie a podstránky MSA, které uživatel navrhne později; seznam, značky a funkce dalších veřejných webů; detailní MSA homepage včetně výslovně přeskočeného návrhu hlavního bloku `Current Week`, umístění automatických zpráv a hráčské profily; zda vznikne samostatná MSA stránka `News` a na kterých dalších Viewer stránkách či webech se zprávy použijí; detailní layout, zoom, seskupování, filtry, barvy a výkon rozhodnuté mapy branchí s časovou osou Historie Runu; případná budoucí synchronizace samostatného Viewer okna. U Forecastu navíc přesný Visualizer pro jednotlivé typy otázek, Match Outcome Landscape, živé a agregované kuličky, Highlight/Focus, Conditional Forecast, Scenario Inspector, `Why This Scenario?`, Saved Scenarios, výběr bodu pro materializaci branche a side-by-side counterfactual UX. Dále editor Future Locks, strom jejich závislostí, jednotlivá a společná pravděpodobnost, feasibility/bottleneck report, vykřičníky a návrhy řešení, compare Candidate Branches pro případný Conflict Fork a Admin-only provenance bez future leaku do Vieweru.
51. Přesné Viewer reveal režimy; otázka byla 5. 8. 2026 výslovně přeskočena a pracovní názvy `Public / Ratings / Full Reveal` nejsou rozhodnuté. Pro zdraví je již rozhodnuto, že Admin zná pravdu a Viewer pouze tehdy veřejnou nebo odhadovanou informaci; otevřený zůstává konkrétní vizuální a pravděpodobnostní model odhadu.
52. Přesný vzhled BYE compact/full pohledu, draw badge a přepínače individuální/skupinové podrobnosti.
53. Přesné formáty exportů, přípony, komprese, schema migration, rozpoznání společného předka a nejjemnější granularita. Tři rozsahy exportu Runu, přenos pěti současných Package typů, zachování `package_id + version`, nové Package-scoped ID entity vyexportované z Runu, přesně uživatelsky vybraný Package payload a bezpečný kontrakt kompatibility jsou rozhodnuté; workflow konfliktu stejného `run_id` je pouze silný směr.
54. Číselné hranice storage varování, přesnost měření vlastních a sdílených dat, odhady uvolněného místa, cache, výkon a bezpečná kalibrace dočasné diskové rezervy. Žádné umělé kvóty ani tiché automatické mazání nebudou.
55. Compare States: konečné potvrzení dvou silně navržených režimů pro různé weeky, pravidla oddělení běžného časového vývoje od divergence, filtry, agregace a přesná podoba porovnání.
56. Zdroj nebo generování historických směnných kurzů, základní měna tabulky, zaokrouhlování a inflace.
57. Přesná definice důležitých momentů, detail Task Center feedu, soukromého post-simulačního digestu a výpočet odhadu zbývajícího času; technická serializace okamžitě pozastaveného mid-match stavu, nejjemnější granularita plánovaného zastavení, automatické pokračování jednotlivých typů úloh po restartu, lock matice branch-local/Run-global dat, řazení čekajících změn a souběh úloh v různých branchích či Runech. Pro Forecast navíc kalibrace pilotního benchmarku a odhadu času, RAM a pracovního prostoru od 10 po miliardy pokusů, bezpečné průběžné přidávání vzorků, deterministic replay, dopočítání nových metrik, prodloužení horizontu, rekonstrukce připnutého vzorku, rare-event sampling, uvolnění dočasných dat a pozastavení či zastavení bez poškození agregovaného reportu. U Future Locks také výkon cíleného hledání proveditelných světů, průběžná detekce nekompatibility a bezpečné zastavení nebo conflict návrh při pozdější změně vstupů.
58. Přesné profily podrobnosti simulace, jejich případná hierarchie, hranice povinných výpočtů a technické podmínky zpětného dopočtu pravděpodobností. Silným směrem je, že Absolute Forecast dědí detail Runu a odděleně volí pouze podrobnost reportu; otevřená zůstává hranice Report Detail, případný jasně neabsolutní Fast Estimate a kompatibilita Forecast reportů mezi verzemi detailu.
59. Konečná taxonomie původu dat a její skládání při kopírování, importu, větvení a regeneraci; dále provenance Forecast Session, sample indexu, seedu, Conditional Forecastu, pinu, materializované branche a counterfactual intervence. Stejně tak provenance Future Locks, jednotlivých vynucených kroků, přirozeně dosimulovaných detailů, splněných podmínek a případných Scenario Directions tak, aby Admin dokázal rekonstruovat zásah bez jeho prozrazení Vieweru.
60. Přesná taxonomie, granularita, veřejnost, technické uložení a retence World Events; úplný katalog automatických upozornění, editor a rozsah watchlistů, možnosti ztišení, seskupovací klíče a časová okna, badge a řazení Notification Centeru, textové šablony a seskupování veřejných událostí do Viewer zpráv. Rozdělení World Event Log / Audit Log / Task Center / Notification Center, globální tři úrovně závažnosti, operation-scoped blokování, Admin zvonek, zákaz technických upozornění ve Vieweru, autoritativní vazba automatické MSA zprávy na veřejný World Event a announcement gating Tournament Edition jsou rozhodnuté. Otevřený zůstává přesný katalog Announcement, Tournament Update a Emergency Update událostí; `News Importance Score` je pouze slabý směr.
61. Geografie a cestování: přesný počet a síť Travel Regions a Timezone Areas, jejich import a validace ve World Package, východní/západní koeficienty, křivka aklimatizace, prahy a matematika rozhodnutého `Low / Medium / High Travel Load`, přesná kontrola proveditelnosti navazujících weeků, vztah Travel Resilience a Jet Lag Resistance k výkonu a případný budoucí model polohy, Home Base, letů, tras, příjezdů, víz, publika a domácího efektu. Home Base byl pro současnou verzi výslovně přeskočen a absence automatického bonusu jen podle národnosti je zatím prozatímním směrem.
62. Rivality a rekordy: automatická detekce dvojicových a skupinových rivalit, jejich vznik, zánik, překryvy, Manual Rivalry, přesná vazba na Scenario Direction a Viewer H2H UX. Rivalry Score je pouze slabý směr. U rekordů jsou rozhodnutá jejich četná kontextová zobrazení; jednotná výpočetní vrstva a úplná historie držitelů jsou jen slabým směrem.
63. Prestiž turnajů: číselná škála, typické defaulty kategorií, automatické vstupy a tempo změn, Edition modifier, Admin lock/override, ochrana před zpětnou smyčkou a dopad na entry AI. Oddělený Tournament Appeal je pouze slabý směr; Admin přesná hodnota a Viewer slovní či pořadové zobrazení jsou běžným směrem.
64. `Week Transition`, globální `Simulation Slots` a turnajové `Match Day Slots`: hlavní atomické pořadí Week Transitionu, frozen slot-start contract, jediná globální časová osa, účinnost procesních oken na hranici slotu a mapování jednoho Match Day Slotu na jeden či více navazujících globálních slotů jsou rozhodnuté. Otevřené zůstávají úplný katalog a matematika týdenních podkroků, datový formát snapshotu, detailní dependency graph, přesná klasifikace konfliktních skupin, pravidla jiných než zápasových událostí, optimalizace, rest minima, kapacity dnů a případné pozdější hodiny. Žádný pevný počet sedmi globálních slotů ani sedmi procesních oken rozhodnutý není.
65. `Season Transition`, Season Builder a Edition Plans: hlavní atomické pořadí, Season Closing Ranking, zákaz Edition přes 61→1, materializační triggery/atomicita/conflict behavior, více Editions, nepřekryvnost a číslování podle prvního skutečného startu jsou rozhodnuté. Otevřené zůstávají schéma Closure Markeru, katalog season-scoped hodnot, pořadí nezávislých podkroků uvnitř uzavřených vrstev, konečný UX, verze šablon, layout všech 50 Inherited Plans, texty a pokročilé řešení konfliktů a opravy už materializovaného kalendáře.
66. Tournament Edition lifecycle a veřejná znalost: tři vrstvy stavů, úplná pre-alpha přechodová matice, doménové Admin akce, společný Viewer/AI announcement week, public version timing, Tournament/Emergency Update a 2×2 mimořádný stav jsou od v62 rozhodnuté. Otevřené zůstávají detailní UI, některé vyšší kompenzace, přesuny přes sezonu a šablony veřejných eventů; vlastní pravděpodobné očekávání pravidelných turnajů hráčskou AI je až směr dalších verzí.
67. Entry historie a souběžná rozhodnutí: konečný status katalog `Tournament Entry/Application` včetně `Still Competing`, detailní Viewer označení předběžných listů, konkrétní portfolio optimalizace hráčské AI, staging datový model a chování při změně vstupů nebo verze algoritmu. Historický objekt, společný slot-start snapshot, společné přehodnocení turnajů a zveřejnění aktuálního seznamu po dokončeném konfliktním entry batchu jsou rozhodnuté. Od v50 je upřesněno, že tento konfliktní batch je atomický, ale nezávislé skupiny stejného globálního slotu mohou commitnout samostatně; retry při stejných vstupech drží stejný seed/výsledek. Přesné rozpoznání kauzálních hranic, faktory, váhy a chytrost AI zůstávají otevřené.
68. Match Reconstruction: úplný katalog, kombinovatelnost a hard/preferred status constraints, feasibility a validační prahy, algoritmy přirozeného hledání, bezpečného early pruning, vynucení, nearest-distance a rozmanitosti kandidátů, výkonové rozpočty a warning prahy, přesný probability/naturalness model, kalibrace `δ / α`, provenance, konečný výchozí počet, retence preview/session a výslovně uložených alternativ, batch workflow a detailní Admin UI. Rozhodnuté jsou ručně uzamčené vstupy, nastavitelný počet kandidátů, oddělení Pre-match Form / Match Performance / Post-match Form, řaditelný kompaktní přehled s výchozím pořadím nalezení, úplný read-only detail, nový kandidát po simulačně významové editaci spuštěné tlačítkem, dočasná historie do potvrzení, volba vynucení / nejbližších / změny constraints při problému a autoritativní commit pouze vybraného kandidáta. Statistické passy, Rare Event Accelerator a přesný obsah kompaktní karty jsou pouze směry podle kapitoly 17.9; princip a omezení forcing režimu zůstávají otevřené.
69. Kroková simulace, Replay, Scores a porovnání hráčů: otevřená je retence alternativních pracovních cest po opuštění či potvrzení zápasu, přesný rozsah ručního AI override, layout/filtry/statistiky/URL a ovládání Scores, případný live režim a kurzy a výslovně přeskočený rozsah první verze `Player Comparison`. Kanonický rally log, snapshot po každé rally, atomicita, hash chain, read-only Step Back/Forward, Auto Play bez změny sportovní logiky a stabilní Replay bez rerunu RNG jsou od v62 rozhodnuté.

---

# 31. Rozhodovací brána první pre-alpha verze

## 31.1 Účel a hranice

Tato kapitola je pracovní fronta otázek, které musí být pro první pre-alpha buď výslovně rozhodnuté, nebo opatřené vědomým minimálním defaultem či stubem podle priority. **Není novým seznamem rozhodnutí.** Odpověď vznikne až následným výslovným potvrzením a teprve potom se propíše do detailní kapitoly a příslušného registru.

Pre-alpha zde znamená první end-to-end backendovou verzi, která opakovaně zvládne dva povinné akceptační průchody popsané v kapitole 31.3. Nemusí mít finální vyvážení, úplný frontend, úplný obsah ani všechny vzdálené cílové funkce.

**[ROZHODNUTO PRO PRE-ALPHA]** Funkční minimum zahrnuje Runs a Packages, hráče/development/AI, čas a transitions, turnaje, entries, losy, Match Engine, minimální Match Reconstruction, rankingy a bezpečný save/load. Plný Forecast/Future Locks/Markets, hluboký trénink, detailní Awards/Records/Rivalries a pokročilé edge cases mohou být viditelně odložené nebo mimo build a dokončení pre-alpha neblokují.

**[ROZHODNUTO – VÝVOJOVÁ PRIORITA v64, 8. 9. 2026]** Nejprve dokončit funkční pre-alpha podle obou akceptačních průchodů v 31.3; další jemné ladění, vyvažování a empirické zrealističťování odložit na následnou fázi. Dosavadní měřicí nástroje a výsledky zůstávají zachované, ale další autonomní práce nemá pokračovat sérií kalibračních auditů místo chybějících funkcí. Neodkládají se správnost pravidel, determinismus, bezpečný save/load, integrita historie ani nezbytné opravy. Existující verzované výchozí profily lze použít jako prozatímní základ; nejsou tím prohlášeny za empiricky realistické. Chybí-li skutečné produktové rozhodnutí nutné pro další řez, předložit jednu doporučenou variantu s vysvětlením a krátce ji s uživatelem uzavřít. Toto rozhodnutí mění pořadí práce, nikoliv rozsah pre-alpha či status všech otevřených kalibračních PAQ.

## 31.2 Pravidlo uzavření

- Ve verzi 62 existují stabilní otázky `PAQ-001–PAQ-157`. Čtyřicet osm je **[RESOLVED]** a zbývajících 109 je stále **[OPEN]**. Kvůli čitelnosti se `[OPEN]` v nadpisu každé neuzavřené otázky neopakuje: absence výslovného terminálního markeru znamená otevřený stav. ID se nikdy nerecykluje ani nepřečísluje; otázka se pouze označí `[RESOLVED]`, `[DEFERRED]`, `[NOT REQUIRED FOR PRE-ALPHA]` nebo `[SUPERSEDED BY PAQ-…]` a zůstane auditovatelná.
- Každá otázka `PA0` musí mít před označením specifikace pre-alpha za behaviorálně úplnou jedinou výslovnou odpověď, případně schválený konfigurovatelný default.
- Každá otázka `PA1` musí mít před použitelnou pre-alpha alespoň bezpečné minimální chování; jemná kalibrace, bohatší UI nebo širší obsah mohou pokračovat později.
- `PRODUCT` se nesmí rozhodnout pouze implementací. `TECH` může implementátor uzavřít autonomně při zachování Masteru. `CALIBRATION` vyžaduje měřitelný výchozí profil a testy. `CONTENT` se uzavírá daty konkrétního Runu, nikoliv globální konstantou enginu.
- Jedna odpověď může uzavřít více navazujících `PAQ`, ale musí být zapsáno, které přesně. Nejisté „asi“ ponechá otázku prozatímní.

**Příklad:** u vyčerpávání stamina nemusí být před pre-alpha definitivně realistická křivka, ale musí existovat zvolená škála, výchozí vzorec a test, že delší a náročnější rally obecně zatěžuje hráče více.

## 31.3 Rozsah a definice hotové pre-alpha

1. **PAQ-001 [RESOLVED v50][PA0][PRODUCT] – Jaký je nejmenší povinný end-to-end uživatelský průchod pre-alpha?** Odpověď: hlavní průchod odsimuluje kompletní sezonu Official Runu, bezpečně ji uloží/načte a dokončí Season Transition až do Weeku 1 následující sezony. Příklad: nestačí jeden turnajový week; musí se prokázat kontinuita výsledků, hráčských stavů, rankingů a season-scoped uzávěrky.
2. **PAQ-002 [RESOLVED v50][PA0][PRODUCT] – Které moduly musí být skutečně funkční a které smějí být pouze viditelný stub?** Odpověď: funkční musí být Runs/Packages, hráči/development/AI, čas/transitions, turnaje, entries, losy, Match Engine, minimální Match Reconstruction, rankingy a bezpečný save/load. Forecast/Future Locks/Markets, hluboký trénink, detailní Awards/Records/Rivalries a pokročilé edge cases pre-alpha neblokují.
3. **PAQ-003 [RESOLVED v50][PA0][PRODUCT] – Jaké operace musí umět částečně sestavený Run bez globálního Start gate?** Odpověď: druhý povinný akceptační průchod vytvoří prázdný Run, ručně přidá dva hráče a jeden zápas a bezpečně jej odsimuluje bez kalendáře; chybějící data smějí blokovat jen operaci, která je potřebuje.
4. **PAQ-004 [RESOLVED v50][PA0][PRODUCT] – Co přesně znamená „pre-alpha dokončena“ z pohledu uživatele?** Odpověď: oba povinné průchody musí opakovaně proběhnout čistě od začátku do konce včetně save/load bez pádu, poškozené historie nebo ruční opravy databáze. Správné operation-scoped zablokování operace s chybějícími či nevalidními vstupy není selhání testu.
5. **PAQ-005 [RESOLVED v50][PA1][PRODUCT] – Bude hlavní akceptační průchod používat Official Run, prázdný Run, nebo oba?** Odpověď: povinné jsou oba; pouze Official Run musí dokončit celou sezonu a otevřít další, zatímco prázdný Run ověřuje operation-scoped modularitu na dvou hráčích a jednom zápase.
6. **PAQ-006 [PA1][TECH] – Jak velký referenční Run musí pre-alpha zvládnout v přijatelném čase a paměti?** Příklad: jedna sezona se 300 hráči a 80 turnaji doběhne na běžném notebooku bez pádu.

## 31.4 Datový model, identity a historická pravda

7. **PAQ-007 [PA0][TECH] – Jaká je minimální povinná sada entit a polí pro end-to-end simulaci?** Příklad: zápas potřebuje stabilní ID, účastníky, formát, časový kontext, stav a výsledek.
8. **PAQ-008 [PA0][TECH] – Jak se generují, validují a nerecyklují stabilní ID ve všech scopes?** Příklad: smazané `player_id = 418` už nikdy nezíská jiný hráč.
9. **PAQ-009 [PA0][TECH] – Jak se technicky ukládá časová platnost měnících se pravidel a vztahů?** Příklad: kategorie Series v sezoně 2005/06 nesmí zpětně změnit její kategorii v sezoně 2003/04.
10. **PAQ-010 [PA0][TECH] – Jaký jednotný význam mají `null`, `Unknown`, `Unresolved`, `Not applicable` a chybějící hodnota?** Příklad: neznámé venue není totéž jako turnaj, který venue vůbec nepoužívá.
11. **PAQ-011 [PA0][TECH] – Jak se archive/delete pravidla promítnou do referencí a historie?** Příklad: archivovaný Package nezneplatní Run, který z něj dříve importoval data.
12. **PAQ-012 [PA1][TECH] – Jaké minimum provenance musí mít ruční, importovaná, generovaná a simulovaná data?** Příklad: u kategorie lze dohledat zdrojový Package, verzi a pozdější Runový override.
13. **PAQ-013 [PA1][TECH] – Jak se bude verzovat schéma dat a migrovat starší pre-alpha uložené stavy?** Příklad: novější build přidá pole bez tiché ztráty starých zápasů.

## 31.5 Runy, ukládání, branche a návraty

14. **PAQ-014 [RESOLVED v50][PA0][PRODUCT] – Kde přesně vede hranice mezi Working Draftem a poslední Saved Revision?** Odpověď: validní simulace může běžet z Working Draftu a její následky zůstanou v něm; Viewer vždy čte poslední Saved Revision. Zahození draftu zahodí také výsledky vzniklé z jeho neuložených vstupů.
15. **PAQ-015 [PA0][TECH] – Jaké logické balíčky lze uložit odděleně a jak se ověří jejich atomická konzistence?** Příklad: změna kategorie se neuloží bez související sezonní vazby.
16. **PAQ-016 [RESOLVED v50][PA0][PRODUCT] – Kdy přesně začne Viewer zobrazovat nově zvolenou Viewer Branch?** Odpověď: označení je neuložená změna a Viewer se přepne až po potvrzeném Save; zobrazí poslední uložený stav nové Viewer Branch.
17. **PAQ-017 [PA0][TECH] – Které uložené body smějí založit branch a co přesně snapshot obsahuje?** Příklad: branch po čtvrtfinále zachová odehrané zápasy a znovu simuluje až semifinále.
18. **PAQ-018 [PA1][TECH] – Které konkrétní rizikové operace musí automaticky vytvořit fork-safe checkpoint?** Příklad: regenerace budoucího kalendáře ano, běžná změna filtru ne.
19. **PAQ-019 [PA1][TECH] – Jaká je minimální retence Undo/Redo, recovery draftů a dočasných Candidate Branches?** Příklad: pád aplikace během editace nabídne poslední konzistentní recovery draft.
20. **PAQ-020 [PA1][PRODUCT] – Jak se potvrzuje, zahazuje nebo mění autoritativní kandidátní budoucnost?** Příklad: z deseti simulací se pouze ručně zvolená větev stane historií Runu.
21. **PAQ-021 [PA1][PRODUCT] – Jaký minimální Compare States patří už do pre-alpha?** Příklad: porovnání stejného weeku dvou branchí ukáže odlišné výsledky, ranking a zdravotní stav.

## 31.6 Packages, import, export a Setup

22. **PAQ-022 [PA0][TECH] – Jaké je minimální přesné schéma každého z pěti Package typů?** Příklad: Calendar Package odkazuje na Series, ale nedefinuje její trvalou identitu.
23. **PAQ-023 [RESOLVED v56][PA0][PRODUCT] – Jak se v pre-alpha chová partial-scope Package k entitám, které neobsahuje?** Odpověď: všech pět Package typů je nedestruktivních; neuvedené entity zůstávají beze změny a nahrazení či odstranění vyžaduje samostatnou scopeovanou operaci s preview a potvrzením. Příklad: Category Package s jedinou Tour nesmaže ostatní Tours ani neuvedené kategorie.
24. **PAQ-024 [RESOLVED v56][PA0][PRODUCT] – Jaké minimální možnosti dostane Admin při chybějící nebo nekompatibilní závislosti?** Odpověď: přesná kompatibilní source identita se viditelně navrhne k propojení, bezpečně uložitelný chybějící cíl zůstane `Unresolved` s oranžovým upozorněním a nevalidní logický balíček nelze vynutit; červeně se zablokuje teprve operace, která závislost potřebuje. Příklad: Calendar lze importovat bez Series, ale dotčený turnaj nelze simulovat.
25. **PAQ-025 [PA0][TECH] – Jak přesně proběhne opakovaný import stejné verze po lokálních Runových změnách?** Příklad: engine ukáže diff a nepřepíše ručně změněný název.
26. **PAQ-026 [PA0][TECH] – Jak se aplikuje selektivní aktualizace na novější Package verzi a její závislosti?** Příklad: přijetí nové kategorie nabídne také chybějící Tour, ale nepřidá ji skrytě.
27. **PAQ-027 [RESOLVED v56][PA0][PRODUCT] – Jaké bezpečné minimum platí pro divergentní historie stejného `package_id` a kanonické slučování entit?** Odpověď: pre-alpha divergentní historie neslučuje ani nepřepisuje; příchozí větev odmítne jako aktualizaci a dovolí ji zachovat pouze jako výslovně importovaný nový Package s novým `package_id` a provenance. Ruční kanonický merge je odložený. Příklad: dvě odlišné verze `v3` odvozené z téže `v2` zůstanou dvěma samostatnými Packages.
28. **PAQ-028 [PA1][TECH] – Jaký souborový formát, manifest, checksum a schema version používá export Runu a Packages?** Příklad: import před zápisem pozná poškozený nebo nepodporovaný soubor.
29. **PAQ-029 [RESOLVED v56][PA0][PRODUCT] – Co přesně udělá neúplný Setup při aplikaci do prázdného či rozpracovaného Runu?** Odpověď: preview rozliší obsažená validní data, nezahrnuté části, unresolved vazby a nevalidní balíčky; validní scope se nedestruktivně připraví do Working Draftu a nic chybějícího se nevymýšlí. Příklad: World a Category bez Series či Calendar vytvoří dílčí Run, ale simulace turnaje vysvětlí a zablokuje jen chybějící prerequisite.

## 31.7 Čas, Simulation Slots a přechody

30. **PAQ-030 [RESOLVED v56][PA0][PRODUCT] – Jaké je přesné pořadí událostí uvnitř jednoho globálního Simulation Slotu?** Odpověď pro první pre-alpha verzi: `Slot-Start Activation → Freeze Slot-Start Snapshot → Calculate to Staging → Resolve Conflicts → Validate and Commit → Publish Committed Outputs → Close Slot`. Po praktickém testování lze kontrakt vědomě vylepšit. Příklad: nejprve se z téhož snapshotu uzavře celý entry batch a teprve po jeho commitu se zveřejní entry list; závislý los patří do dalšího slotu.
31. **PAQ-031 [RESOLVED v50][PA0][PRODUCT] – Jaké je úplné pořadí operací Week Transitionu?** Odpověď: preflight/staging → development z dokončeného weeku → Between-Week State Update → aktivace nové konfigurace → narozeniny/lifecycle → expirace/aktivace výsledků a korekce → jediný nový Official Ranking → veřejné události → validace a atomický commit. Podrobnosti jsou v kapitole 6.5.
32. **PAQ-032 [RESOLVED v50][PA0][PRODUCT] – Jaké je úplné pořadí Season Transitionu a jeho atomického commitu?** Odpověď: validace Weeku 61 → Season Closing Ranking podle starých pravidel → sezonní souhrn a Closure Marker → development/recovery podle starých pravidel → aktivace nové sezony a reset jen season-scoped hodnot → lifecycle → Official Ranking Weeku 1 podle nových pravidel → veřejný stav → atomický commit. Poslední sezona skončí po uzávěrce jako Completed.
33. **PAQ-033 [RESOLVED v50][PA0][TECH] – Jak se řeší závislé a nezávislé události se stejným slot-start snapshotem?** Odpověď: atomickou jednotkou je nezávislá událost nebo konfliktní/kauzální skupina. Nezávislé skupiny lze commitovat odděleně, ale všechny nevyřešené části čtou původní slot-start snapshot a další slot čeká na jejich terminální stav.
34. **PAQ-034 [RESOLVED v57][PA0][PRODUCT] – Jaká je operation-scoped prerequisite matice všech podporovaných simulačních akcí?** Odpověď: matice je hierarchická podle cíle a kauzálních závislostí; širší rozsah dědí minima užších rozsahů, červená chyba blokuje vybranou hromadnou akci, ale ne nezávislou validní užší operaci, a Next Season/Full validují vzdálenou budoucnost progresivně. Konkrétní minima pro Rally/Game/Match/Slot/Round/Tournament/Week/Season/Full/Custom určuje kapitola 17.1. Příklad: chybějící body budoucího Ranked turnaje nezablokují samostatný platný zápas.
35. **PAQ-035 [PA1][TECH] – Jak se dlouhá úloha pozastaví, bezpečně zastaví, obnoví po restartu a zobrazí v Task Centeru?** Příklad: zastavení po současném zápase nezanechá napůl zapsaný ranking.
36. **PAQ-036 [RESOLVED v57][PA0][PRODUCT] – Jak se mapují globální Slots, entry/draw okna a denní Match Day Slots?** Odpověď: existuje jediná autoritativní globální osa Simulation Slots. Procesní okno začne na hranici konkrétního slotu, Match Day Slot se mapuje na jeden či více navazujících globálních slotů a scheduler topologicky umístí závislé události později, zatímco nezávislé turnaje mohou sdílet slot. Přesný počet časných oken a optimalizace zůstávají otevřené.
37. **PAQ-037 [RESOLVED v50][PA1][PRODUCT] – Jak se pre-alpha zachová na konci weeku 61 poslední sezony?** Odpověď: vytvoří Season Closing Ranking, sezonní souhrn a Closure Marker, označí Run jako Completed a nevytvoří neexistující Week 1 ani sezonu 2050/51; starší body lze nadále prohlížet a větvit.

## 31.8 Hráčský pool, generování a identita

38. **PAQ-038 [PA0][CONTENT] – Jak velký a věkově rozložený je počáteční hráčský pool Official Runu 2000/01?** Příklad: obsahuje aktivní hráče od 15 do 45 let a dost hráčů pro první kvalifikace.
39. **PAQ-039 [PA0][CALIBRATION] – Kolik nových patnáctiletých prospectů vzniká v jednotlivých weekech a zemích?** Příklad: velikost ročníku vychází z populace a country pipeline, ne z pevného stejného počtu pro každou zemi.
40. **PAQ-040 [PA1][CALIBRATION] – Jaké jsou výchozí distribuce narození, výšky, hmotnosti, rukovosti a základních identit?** Příklad: dvě země mohou používat jiné name pooly, ale ne jiné vrozené squashové nadání jen kvůli národnosti.
41. **PAQ-041 [PA0][CALIBRATION] – Jaký reprodukovatelný výchozí vzorec použije Country Model V1 od populace po profesionální konverzi?** Příklad: slabší infrastruktura sníží objevení a přechod na Tour, nikoliv maximum potenciálu narozeného hráče.
42. **PAQ-042 [RESOLVED v57][PA0][PRODUCT] – Jak se určí první formální vstup prospecta na Tour a jeho výchozí soutěžní postavení?** Odpověď: dosavadní trigger první platné přihlášky nebo definitivního přidělení WC zůstává; hráč vstupuje s 0 body, do dalšího Official snapshotu je `NR` a teprve v něm se zařadí. Dokončený Ranked výsledek je vstupem následujícího snapshotu stejně jako u všech ostatních, nikoliv zvláštními body přidělenými před rankingem. Starší snapshot jej vede pod klasifikovanými hráči; více NR řadí entry slot a stabilní turnajový token.
43. **PAQ-043 [RESOLVED v57][PA0][PRODUCT] – Která hráčská pole jsou pro pre-alpha povinná a jak se zobrazí shodná jména?** Odpověď: povinné jádro obsahuje stabilní ID a jméno, narození, původ, časově verzovanou Sporting Representation, handedness, fyzické a lifecycle údaje, creation origin, rankingový token, 57 atributů, potenciál, development type a potřebné sportovní stavy; neúplný profil může zůstat Draft. Shodná jména se rozliší reprezentací a rokem, poté birth weekem a stabilním diskriminátorem. Sporting Representation má typy `Country / World / FAX Neutral`; World je dobrovolná globální identita, Neutral regulační status, oba hrají individuální Tour bez národní týmové eligibility a historické výsledky se nepřepisují.
44. **PAQ-044 [RESOLVED v50][PA1][PRODUCT] – Jak ruční hráč, field-level lock a regenerace ovlivní již existující historii a budoucnost?** Odpověď: okamžitá velká změna dostane varování a alternativu `Dopočítat historický vývoj` přes branch/regeneraci. Pre-alpha nabízí přirozené přegenerování, přesné zachování soutěžního skeletu a výsledků nebo podobnou historii s měkkými cíli; vývoj chrání oranžový možný a červený absolutní limit. Samostatné pokročilé osy rozsahu × zachování jsou odložené.

## 31.9 Atributy, potenciál, forma, development a trénink

45. **PAQ-045 [RESOLVED v49][PA0][PRODUCT] – Jaký přesný atributový katalog bude skutečně aktivní v pre-alpha výpočtech?** Odpověď: všech 57 atributů z kapitoly 11.1 je aktivních, samostatně uložených a používá se pouze jejich situačně relevantní podmnožina. Příklad: `Drop Shot` není konstantním bonusem ke každé rally.
46. **PAQ-046 [RESOLVED v49][PA0][PRODUCT] – Jaká interní číselná škála platí pro atributy a jak se významově odděluje od potenciálu?** Odpověď: každý atribut používá `0–200`; potenciál používá samostatné labely `L+–F−` a skrytý měkký Potential OVR. Přímý převod hodnoty atributu 120 na potenciálový letter grade neexistuje. Tímto je opravena chybná smíšená formulace v48a.
47. **PAQ-047 [PA0][CALIBRATION] – Jaký konkrétní společný profil vah a normalizační vzorec vypočte první OVR `0–200` a jak se později přejde k individuálním profilům?** Příklad: dva hráči mohou mít stejné OVR, přesto jeden těží z rychlosti a druhý z kontroly.
48. **PAQ-048 [PA0][CALIBRATION] – Jaká výchozí pravděpodobnostní křivka řídí přibližování k měkkému Potential OVR a extrémně vzácný růst nad něj?** Příklad: `A−` používá prozatímní Potential OVR 186, ale nejde o zaručený ani tvrdý strop.
49. **PAQ-049 [PA0][CALIBRATION] – Jaký minimální týdenní development výpočet mění atributy a z čeho smí čerpat?** Příklad: Week 20 používá jen informace známé nejpozději na konci Weeku 19.
50. **PAQ-050 [PA1][CALIBRATION] – Jaké konkrétní výchozí věkové křivky řídí růst, plateau, decline a možné návraty jednotlivých skupin atributů?** Rozhodnuté typy Early/Standard/Late, posun `−3/0/+3` a prozatímní středy `26/29/32` samy ještě neurčují úplnou křivku ani test. Příklad: fyzická rychlost může klesat dříve než rozhodování, ale ne podle jediného pevného `peak_week`.
51. **PAQ-051 [RESOLVED v58][PA0][PRODUCT] – Jaké minimální týdenní tréninkové volby vedle již rozhodnutého Opponent Study a Match-specific Court Training skutečně patří do pre-alpha?** Odpověď: jeden aggregate `General Training Load` s volbami `Recovery / Light / Normal / Heavy` sdílí omezenou týdenní kapacitu s oběma zdroji Match Preparation. Zvyšuje či snižuje development, recovery, Fatigue a riziko přetížení; Admin jej může přepsat. Hluboký plán, focus, periodizace a burnout zůstávají odložené.
52. **PAQ-052 [PA0][CALIBRATION] – Jaká je škála, inicializace, zápasová aktualizace a návrat Form k individuálnímu normálu?** Příklad: těsná výhra outsidera zvedne Form více než očekávaná hladká výhra favorita.
53. **PAQ-053 [RESOLVED v58][PA1][PRODUCT] – Jaký nejmenší vliv herního stylu, gameplanu a znalosti soupeře musí být skutečně aktivní?** Odpověď: aktivní osy jsou `Risk / Tempo / Court Positioning / Variation`; Natural Style Profile, Style Familiarity a skutečná Style Execution z relevantních atributů, adaptability, preparation a stavů se neslučují. AI může z nedokonalého odhadu counterovat soupeře, ale také zůstat u vlastní hry nebo plánu s pozdějším očekávaným efektem; gameplan nese mechanismus, horizon, confidence a reassessment threshold a setrvání může být správné i chybné.

## 31.10 Fatigue, stamina, mentální stav, zdraví a travel

54. **PAQ-054 [PA0][CALIBRATION] – Jaká škála a časová kontinuita platí pro dlouhodobou Fatigue a recovery mezi rally, zápasy a weeky?** Příklad: konec pozdního finále ovlivní začátek turnaje v dalším weeku.
55. **PAQ-055 [PA0][CALIBRATION] – Jak se při startu zápasu odvodí tři fyzické bary `Explosive / Rally / Match Stamina`?** Příklad: vycházejí z atributů, fatigue, zdraví a travel load, nikoliv ze tří ručně authorovaných schopností.
56. **PAQ-056 [PA0][CALIBRATION] – Jaké křivky řídí individuální úbytek a obnovu všech tří fyzických barů po každé rally?** Příklad: hráč pod tlakem může ve stejné rally ztratit více než soupeř.
57. **PAQ-057 [PA0][CALIBRATION] – Jak se inicializují a po rally mění `Current Focus` a `Current Confidence`?** Příklad: Focus může kolísat rychleji, zatímco Confidence se po jednom bodu změní méně.
58. **PAQ-058 [RESOLVED v50][PA0][PRODUCT] – Jaký minimální Injury/Illness datový model rozlišuje typ, závažnost, omezení a trvání?** Odpověď: samostatné typy Injury/Illness, více souběžných záznamů, Severity `0–100`, typový profil omezení, lifecycle `At Risk / Active / Recovering / Recovered` včetně možnosti včasného `At Risk → Recovered`, nejisté rozmezí zotavení a individuální predispozice/recovery. Číselné křivky řeší PAQ-155.
59. **PAQ-059 [PA0][CALIBRATION] – Co spustí zdravotní přestávku a jak přesně tři minuty ovlivní recovery a Injury State?** Příklad: oba hráči částečně obnoví stamina, ošetřovanému se navíc může mírně snížit akutní dopad zranění.
60. **PAQ-060 [PA0][CALIBRATION] – Jak se určí skutečná délka přestávky mezi gamy a její recovery efekt?** Příklad: Official Run default jsou dvě minuty, ale hráči je nemusí dodržet na sekundu přesně.
61. **PAQ-061 [PA1][CALIBRATION] – Jaké prahy a účinky mají `Low / Medium / High Travel Load` a jak odeznívají?** Příklad: dlouhá cesta na východ sníží počáteční stamina více než krátký regionální přesun.
62. **PAQ-062 [PA0][CALIBRATION] – Jak hráč a případně zdravotní pravidlo rozhodnou `nastoupit / W/O / pokračovat / medical timeout / RET`?** Příklad: vysoké riziko trvalého zhoršení může přebít motivaci dohrát finále.

## 31.11 Rally-by-rally Match Engine

63. **PAQ-063 [RESOLVED v50][PA0][PRODUCT] – Jaké přesné vstupy obsahuje `Rally Setup`?** Odpověď: skóre/pravidla/podání, elapsed time a recovery, relevantní atributy, Form a Sharpness, Fatigue a zdravotní omezení, tři fyzické a dva mentální bary, styl/matchup/gameplan/úsilí/serve-return, tlak stavu zápasu a model/random state pro Replay. OVR, ranking, Travel Load a Financial Level se nesmějí znovu započíst jako obecný bonus po materializaci jejich účinku.
64. **PAQ-064 [RESOLVED v59][PA0][CALIBRATION] – Jaká je výchozí přechodová logika mezi pěti stavy kontroly a tlaku?** Odpověď: lokální přechody mají setrvačnost; běžně se stav nezmění nebo posune o jeden stupeň, dvoustupňový posun vyžaduje významný zlom a přímý silný obrat je vzácný. Relevantní atributy, styl, gameplan, fyzické a mentální stavy upravují získání i držení kontroly, malá náhodnost zachovává variabilitu a nic nevynucuje alternaci. Přesná matice zůstává numerickou kalibrací.
65. **PAQ-065 [RESOLVED v59][PA0][CALIBRATION] – Kolik abstraktních skrytých úseků může rally mít a kdy se ukončí?** Odpověď: `0–24` control segmentů. Nula dovoluje konec při podání nebo prvním returnu s jedním či dvěma údery; pokračující rally má převážně `1–10` segmentů, potom roste closure pressure a 24. segment vyvolá kontextově vážený terminal bez mechanického 50:50. Segment je fáze, ne úder.
66. **PAQ-066 [RESOLVED v58][PA0][PRODUCT] – Které atributy mohou v jednotlivých rally kontextech působit a jak se skládají?** Odpověď: každý abstraktní kontext aktivuje pouze relevantní atributy v rolích `Primary / Supporting / Constraint`; dynamické fyzické a mentální stavy upravují jejich provedení a OVR, ranking, Travel, Financial ani jeden materializovaný kauzální vliv se nesmějí započítat podruhé.
67. **PAQ-067 [RESOLVED v58][PA0][PRODUCT] – Jaký je minimální katalog terminálních sportovních incidentů první verze?** Odpověď: Rally Resolution Record odděluje primární terminal trigger, rule context, initial/final official call, seřazené score mutations, analytical attribution a side incidents. Katalog triggerů je `GOOD_RETURN_UNANSWERED / SERVE_FAULT / RETURN_DOWN / RETURN_OUT / RETURN_NOT_UP / INTERFERENCE_STOP / BALL_HIT_PLAYER / PROCEDURAL_OR_OFFICIAL_STOP / BALL_COURT_OR_EXTERNAL_STOP / HEALTH_STOP / CONDUCT_STOP`; Clean Winner, Forced Error a Unforced Error jsou analytická připsání. Minimální ball-hit, turning a further-attempt flagy patří do pre-alpha, přesné trajektorie a referee/video chyby nikoliv.
68. **PAQ-068 [RESOLVED v59][PA0][CALIBRATION] – Jak se z incidentu a situace rozhodne bod, `No Let`, `Yes Let` nebo `Stroke`?** Odpověď: engine nejprve vytvoří ground-truth fakta a historicky verzovaný rules resolver z jejich kombinace deterministicky určí správný výsledek. Pre-alpha nemá náhodnou referee chybu a initial call se rovná final call; budoucí perception/review vrstva smí změnit call, nikdy pravdu situace. `Yes Let` nepřidá bod a zopakuje rally ze stejného skóre.
69. **PAQ-069 [RESOLVED v59][PA0][CALIBRATION] – Jak velký a jak dlouhý je menší počáteční vliv podání?** Odpověď: žádný obecný server bonus. Serve Execution × Return Execution určí pouze opening, obvykle nejvýše jeden stav od neutral; silná kontrola a přímý konec jsou výjimečné. Safe/normal/aggressive mění fault/pressure/attackable-return trade-off a po openingu už neexistuje persistentní serve modifier.
70. **PAQ-070 [RESOLVED v59][PA1][CALIBRATION] – Jak se z průběhu rally odvodí délka a odhad počtu úderů?** Odpověď: opening, každý segment a terminal společně kauzálně vytvářejí estimated shots, active duration, Phase Pace a individuální workload podle verzovaného RallyCalibrationProfile. Prozatímní mužský elitní acceptance koridor je medián `11–13` a 75. percentil `19–23` úderů; stylové matchupové průměry se mohou výrazně lišit. Studie publikovaná 2016 je pouze historická kontrola a přesná současná higher-tail křivka zůstává rekalibrovatelná.
71. **PAQ-071 [RESOLVED v60][PA1][CALIBRATION] – Jak vznikají běžné mezery mezi rally a jiné autoritativní časové události?** Odpověď: běžná mezera od konce rally ke kontaktu dalšího podání je maximem připravenosti servera, receivera, rozhodčího a kurtu. Hráči mají rozdílné přirozené tendence na podání a returnu a situačně volí `accelerate / natural / delay`; skutečný čas dává recovery oběma právě jednou, taktický efekt není jistý a přehnané bezdůvodné zdržování používá minimální prompt/warning/Conduct Stroke resolver. Samostatné objektivní události se časově nepřičítají podruhé. Prozatímní běžný koridor je převážně `8–18 s` s průměrem kolem `13 s`, nikoliv pevná lhůta.
72. **PAQ-072 [RESOLVED v62][PA0][PRODUCT] – Jak se dědí a přepisuje match format od Official defaultu po konkrétní zápas?** Odpověď: oficiální fallback je atomický `BO5 / do 11 / win by 2`; povolený celý override patří Tournament Edition a její fázi či kolu, nejbližší vítězí a jinak se jde přímo k fallbacku bez skryté plné hierarchie. Materializovaný zápas uloží efektivní formát/provenance a od první rally jej zamkne.
73. **PAQ-073 [RESOLVED v62][PA0][TECH] – Jak se serializuje rally log, krokové návratové body, Auto Play a read-only Replay?** Odpověď: neměnný Match Input Snapshot a po každé dokončené rally atomický Rally Event + Post-Rally State Snapshot tvoří hash chain s finálním `match_log_hash`. Crash zahodí neúplnou rally; Step Back/Forward a Replay pouze čtou uloženou pravdu a nikdy znovu nespouštějí RNG či nový model. Auto Play mění jen rychlost/postup zobrazení.

## 31.12 Tournament model, kalendář a lifecycle

74. **PAQ-074 [RESOLVED v62][PA0][TECH] – Jaká minimální pole potřebují Competition System, Tour, Category, Series, Edition Plan a Edition?** Odpověď: všechny používají stabilní Run-local ID, schema/provenance envelope a minimum identity, názvu, platnosti, rodičů a pořadí podle kapitoly 4.6; Series nenese konkrétní sezonu/week/výsledek, Plan nese season/occurrence/term/overrides a Edition vlastní identitu, plan provenance, skutečný termín, lifecycle a efektivní sportovní konfiguraci. Povinné chybějící vazby jsou `Unresolved`; další pole se stanou povinnými podle lifecycle.
75. **PAQ-075 [RESOLVED v62][PA0][PRODUCT] – Jaká je úplná pre-alpha hierarchie dědění a nejbližšího povoleného override?** Odpověď: `Official default → Package → Run → season → Competition System → optional Tour → Category → Series → Edition Plan → Edition → phase → round → match`; nejbližší povolený explicitní override vítězí podle field-specific scope registry, rodič působí jen do provozního locku a historie se nepřepisuje. Match Format má užší kontrakt PAQ-072.
76. **PAQ-076 [RESOLVED v62][PA0][TECH] – Které akce materializují Inherited Plan a co se stane při konfliktu během materializace?** Odpověď: editace/override, potvrzení, import, announcement/publication a první trvalá potřeba entries/AI/simulace/reference; pouhé prohlížení či preview ne. Engine těsně před atomickým vznikem re-resolvuje dědičnost, při chybě nespotřebuje ID a bulk preflight ponechá konflikty viditelně virtuální; změna zdroje mezi preview a commit vyžádá nové potvrzení.
77. **PAQ-077 [RESOLVED v62][PA0][PRODUCT] – Jak se validují a číslují více Editions stejné Series v jedné sezoně ve všech edge cases?** Odpověď: samostatné Plan/Edition ID a v pre-alpha nepřekrývající se aktivní termíny. Před startem je číslo provisional; oficiální `edition_number` se přidělí prvním skutečným zápasem podle pořadí startu. Pre-start cancellation, W/O, DQ či technický postup číslo nespotřebují; po první rally se nevrací a ruční oprava je auditovaná, kladná a unikátní.
78. **PAQ-078 [RESOLVED v62][PA0][PRODUCT] – Jaká je minimální úplná přechodová matice hlavního, komponentního a Public Stage lifecycle Edition?** Odpověď: pevná matice hlavního lifecycle, přesné komponentní stavy Entries/Entry List/Draw/Q/Main Draw a Public Stage z kapitoly 13.8. Veřejná či použitá Edition se nevrací do Draftu, terminální stav vyžaduje branch a přechody provádějí validované doménové akce. Entries rozlišují Main a následné Qualification Entry Window.
79. **PAQ-079 [RESOLVED v62][PA0][PRODUCT] – Jak přesně fungují announcement, update a emergency update vůči Vieweru a hráčské AI?** Odpověď: Edition má společný `announcement_week` pro Viewer i AI. Veřejná změna je buď `Before Announcement`, nebo nová public version/Tournament Update od zvoleného weeku; do té doby zůstává skrytá. Již běžící week používá odůvodněný Emergency Update na nejbližší bezpečné hranici, bez retroaktivního přepočtu, a historický Viewer čte tehdy známou verzi.
80. **PAQ-080 [RESOLVED v62][PA0][PRODUCT] – Jaké přechody a sportovní následky pokrývá pre-alpha pro `Cancelled / Postponed / Suspended / Abandoned`?** Odpověď: před startem pokračuje `Postponed`, nepokračuje `Cancelled`; po startu pokračuje `Suspended`, nepokračuje `Abandoned`. Důsledky zachování identity, entries/draw, score/logu, restavu po uplynulém čase, bodů, nakonfigurovaných výplat a absence automatického vítěze jsou v kapitole 13.2. Přesun pokračování za současný Match Day Slot vyžaduje Suspended.
81. **PAQ-081 [RESOLVED v62][PA0][CALIBRATION] – Jak Round Schedule přiřadí zápasy do dnů a pořadí s fair-rest prioritou?** Odpověď: nejprve nepřekročitelné feedery, nejvýše jeden zápas hráče za Match Day Slot, další nejdříve v následujícím slotu, Qualification před Main Draw a configured range. Platné varianty se lexikograficky řadí podle méně odpočatého hráče, imbalance, pozdějšího minulého zápasu, Q/LL restu, previous-week carryoveru, minimální změny publikace a až pak uloženého deterministic tie-breaku; ranking/seed/národnost/popularita výhodu nedávají.
82. **PAQ-082 [PA1][PRODUCT] – Jaký zjednodušený fallback použije pre-alpha bez hodin, paralelních kurtů a detailní venue logistiky?** Příklad: jeden Match Day Slot představuje den a zápasy mají uložené pořadí.

## 31.13 Přihlášky, kvalifikace, los a náhrady

83. **PAQ-083 [PA0][PRODUCT] – Kolik entry decision slots a procesních oken má pre-alpha a kde leží jednotlivé deadlines?** Příklad: během dvouweekového přihlašování lze rozhodnutí v každém okně změnit.
84. **PAQ-084 [PA0][TECH] – Jak přesně vzniká společný ranking/data snapshot a atomicky zveřejněný entry list?** Příklad: všichni hráči ve slotu rozhodují ze stejného vstupu a list se ukáže až po commitu.
85. **PAQ-085 [PA0][CALIBRATION] – Jaký výchozí scoring použije hráčská AI při volbě turnajového portfolia?** Příklad: zvažuje šanci na cut, body, únavu, travel a alternativy, nikoliv budoucí skrytý los.
86. **PAQ-086 [PA0][PRODUCT] – Jak se přesně vyřeší více předběžných přihlášek před a po jednotlivých uzávěrkách?** Příklad: hráč v Main Draw jednoho turnaje může včas odstranit kolidující druhou přihlášku bez nejvyšší sankce.
87. **PAQ-087 [PA1][CONTENT] – Jaké jsou výchozí odečty bodů, délky Disciplinary Zero a časové stupně pozdního odhlášení?** Příklad: okamžité odhlášení po deadline je méně závažné než no-show v obou turnajích.
88. **PAQ-088 [PA0][CONTENT] – Jaké konkrétní kapacity, seed counts a BYE pravidla používají první Official Run šablony?** Příklad: draw 48 používá 16 seedů a BYE podle rozhodnutého obecného mechanismu.
89. **PAQ-089 [PA0][PRODUCT] – Jaké úplné pořadí a tie-breaky platí pro skupinovou kvalifikaci a LL srovnání?** Příklad: musí být jasné, co rozhodne při stejných výhrách, setech i míčích.
90. **PAQ-090 [PA0][PRODUCT] – Kdo je způsobilý pro WC/RWC, jak se rezervy řadí a kdy přestanou být dostupné?** Příklad: hráči po přímém postupu WC zmizí, ale historie původního přidělení zůstane.
91. **PAQ-091 [PA0][PRODUCT] – Jaké je úplné LL pořadí a bodový původ všech náhradníků?** Příklad: poražený finalista kvalifikace má prioritu před semifinalistou a shodu řeší určený ranking snapshot.
92. **PAQ-092 [PA0][PRODUCT] – Jak se řeší všechny pre-alpha edge cases mezi redraw, seed cascade a direct-slot replacement?** Příklad: souběžná odstoupení se zpracují atomicky a seed čísla zůstanou zachovaná.
93. **PAQ-093 [PA0][PRODUCT] – Vytvoří každý potvrzený los nebo jeho potvrzená oprava novou neměnnou `Draw Version`?** Příklad: původní los je `v1` a cascade po odstoupení seedu `v2`, zatímco preview před potvrzením verzí není.
94. **PAQ-094 [PA0][PRODUCT] – Jaké ruční draw zásahy smí Admin provést a jak se označí vědomě nestandardní výsledek?** Příklad: ruční výměna dvou slotů zůstane auditovaná a Viewer neukáže technické interní varování.

## 31.14 Ranking, body, prize money a disciplína

95. **PAQ-095 [PA0][PRODUCT] – Jaký povolený rozsah a validační pravidla má sezonní Best N a jeho dědění?** Příklad: první Official sezona nabídne 15 a další převezme předchozí efektivní hodnotu, pokud nemá override.
96. **PAQ-096 [PA0][CONTENT] – Jaké úplné bodové tabulky dostanou všechny Ranked kategorie a jejich kvalifikace v první Official sadě?** Příklad: zveřejněná Ranked Edition nesmí mít chybějící body pro žádný dosažitelný výsledek.
97. **PAQ-097 [RESOLVED v50][PA0][PRODUCT] – Jaké je přesné pořadí výpočtu Official snapshotu, expirace, nových bodů a sezonních změn?** Odpověď: po aktivaci nové policy se expirace, nové výsledky, disciplína a korekce zpracují atomicky a Official Ranking se z autoritativních vstupů vypočítá právě jednou. Na sezonní hranici mu předchází archivní Season Closing Ranking podle starých pravidel.
98. **PAQ-098 [PA0][PRODUCT] – Jak se ve všech případech skládá kvalifikační a Main Draw část jediného výsledku?** Příklad: kvalifikant dostane `Qualified + dosažené Main Draw kolo`, LL svou Q stage plus Main Draw výsledek.
99. **PAQ-099 [PA0][PRODUCT] – Jaké minimální Protected Ranking chování musí pre-alpha skutečně podporovat?** Příklad: je-li PR aktivní, musí být určeno použití pro entry, seeding a případně LL, nebo se některá část výslovně odloží.
100. **PAQ-100 [PA1][PRODUCT] – Potřebuje pre-alpha samostatný Live Ranking, a pokud ano, jak propadávají body uvnitř weeku?** Příklad: Viewer může dočasně ukazovat jen poslední Official snapshot, pokud je Live Ranking vědomě stubovaný.
101. **PAQ-101 [PA1][PRODUCT] – Jak se chová nepovinné prize money od nevyplněné tabulky po úplný souhrn?** Příklad: turnaj bez částek funguje, ale zadaná tabulka musí správně pokrýt Q, Main Draw, W/O i DQ pravidla.
102. **PAQ-102 [PA1][CONTENT] – Jaké konkrétní sankční a disciplinární defaulty potřebuje první Official Run?** Příklad: je určeno, o kolik bodů a na kolik weeků se použije Disciplinary Zero při no-show.

## 31.15 Match Reconstruction

103. **PAQ-103 [PA0][PRODUCT] – Jaký úplný katalog constraints podporuje pre-alpha a které jsou hard versus preferred?** Příklad: výsledek 3:2 je hard constraint, zatímco požadovaná přibližná délka může být preferred range.
104. **PAQ-104 [PA0][PRODUCT] – Jaké přesné uživatelské režimy hledání budou dostupné při nesplnitelných nebo vzácných constraints?** Příklad: změnit parametry, hledat nejbližší, nebo použít později definovaný vynucující režim.
105. **PAQ-105 [PA0][TECH] – Jak funguje přirozené hledání, bezpečný early pruning a podmínka ukončení?** Příklad: kandidát se zahodí po prvním gamu, pokud už nemůže splnit požadovanou cestu skóre.
106. **PAQ-106 [PA0][PRODUCT] – Jaké hranice a sportovní invarianty nesmí porušit vynucující režim?** Příklad: smí ovlivnit náhodné výsledky rally, ale nesmí vytvořit neplatné skóre nebo neexistujícího soupeře.
107. **PAQ-107 [PA1][CALIBRATION] – Jak se měří vzdálenost nejbližšího kandidáta a rozmanitost výsledné sady?** Příklad: deset téměř totožných zápasů nemá být vydáváno za deset smysluplně odlišných možností.
108. **PAQ-108 [PA1][CALIBRATION] – Jak se přesně počítají a zobrazují `p`, `δ` a `α` a kdy mají dost vzorků?** Příklad: probability se neukáže jako přesná po deseti pokusech, ale až s viditelnou nejistotou nebo po dosažení prahu.
109. **PAQ-109 [PA1][PRODUCT] – Co obsahuje kompaktní kandidátní karta, úplný detail a dostupné řazení?** Příklad: karta ukáže skóre, délku a naturalness, detail celý rally log a řazení může být podle nalezení či pravděpodobnosti.
110. **PAQ-110 [PA0][PRODUCT] – Jak se kandidát po editaci regeneruje, jak dlouho se session drží a co přesně commitne výběr?** Příklad: významová změna vytvoří nový kandidát a pouze potvrzený výběr se zapíše do autoritativní historie.

## 31.16 Hráčská AI a rozhodování

111. **PAQ-111 [PA0][PRODUCT] – Jaká data smí hráčská AI v každém rozhodovacím bodě znát?** Příklad: zná veřejně oznámený turnaj a svůj odhad soupeře, ale ne skrytý Edition Plan ani Admin truth zranění soupeře.
112. **PAQ-112 [PA0][CALIBRATION] – Jaký minimální model řídí přihlášky, odhlášky a volbu mezi turnaji?** Příklad: AI porovná body, cut probability, únavu, travel a kolize ve stejném slotu.
113. **PAQ-113 [PA0][CALIBRATION] – Jak AI volí před rally úsilí, gameplan a jejich změnu během skrytého průběhu?** Příklad: unavený hráč může snížit úsilí, ale nesmí dokonale znát budoucí terminální incident.
114. **PAQ-114 [PA0][CALIBRATION] – Jak AI rozhoduje o nástupu, zdravotní přestávce, pokračování a RET?** Příklad: význam turnaje zvyšuje ochotu riskovat, ale lékařský zákaz může rozhodnutí zablokovat.
115. **PAQ-115 [RESOLVED v58][PA1][PRODUCT] – Jaký minimální tréninkový a recovery choice AI používá, dokud je hluboký trénink odložený?** Odpověď: AI volí stejný `General Training Load: Recovery / Light / Normal / Heavy` podle vlastního nedokonalého odhadu zdraví a únavy, současného zápasového vytížení, kalendáře a významu nejbližších soutěží. Volba využívá společnou kapacitu s Match Preparation a nemusí být optimální; Admin override je povolený.
116. **PAQ-116 [PA1][CALIBRATION] – Jak vzniká Inactive, dobrovolný retirement a comeback bez pevného časového automatu?** Příklad: dlouhá absence sama hráče neretiruje; musí vzniknout faktorové rozhodnutí.
117. **PAQ-117 [PA0][TECH] – Jak se oddělí reprodukovatelná náhodnost, individuální preference a budoucí zlepšování AI?** Příklad: stejný seed a verze modelu zopakují volbu, novější AI verze se historicky zaznamená.
118. **PAQ-118 [PA0][PRODUCT] – Jakou přesnou prioritu má univerzální Admin override vůči AI a automatickým validacím?** Příklad: Admin může jednorázově vynutit přihlášku, ale engine stále odmítne technicky nemožný dvojí start.

## 31.17 Minimální Admin a Viewer UX

119. **PAQ-119 [PA0][PRODUCT] – Které konkrétní Admin stránky tvoří minimální pre-alpha navigační strom?** Příklad: Run Home, Players, Tour/Calendar, Simulation, History a Settings mohou být funkční minimum.
120. **PAQ-120 [PA0][PRODUCT] – Které konkrétní Viewer stránky musí být skutečně funkční?** Příklad: MSA homepage, Rankings, Players, Tournaments, Draw/Results a Scores.
121. **PAQ-121 [PA1][PRODUCT] – Jaká je úplná minimální mapa Viewer ↔ Admin protějšků a fallbacků?** Příklad: přepnutí z Viewer profilu hráče otevře Admin profil stejného `player_id` ve stejném weeku.
122. **PAQ-122 [PA0][PRODUCT] – Jaký společný formulářový kontrakt používají editace, preview, Save/Discard a validační chyby?** Příklad: červený blok ukáže přesné pole a důvod, aniž by ztratil ostatní rozpracované změny.
123. **PAQ-123 [PA0][PRODUCT] – Jak se zobrazí neúplná data, `Unresolved` reference a tři úrovně závažnosti?** Příklad: chybějící nepovinná cena je modrá informace, neplatný účastník zápasu červený blok.
124. **PAQ-124 [PA0][PRODUCT] – Jaké minimum musí ukázat draw, zápasový detail, Scores a Replay?** Příklad: kompaktní výsledek se rozklikne na gamy, rally log, časové události a stavy stamina.
125. **PAQ-125 [PA1][PRODUCT] – Jaké minimum mapy branchí a časové Historie Runu patří do pre-alpha?** Příklad: lze vybrat branch a uložený bod, i když pokročilý graf a filtry přijdou později.
126. **PAQ-126 [PA1][PRODUCT] – Jaké jsou minimální jazykové, zařízení a accessibility cíle?** Příklad: české Admin UI na desktopu musí být plně ovladatelné klávesnicí; mobil může být zatím read-only omezený.

## 31.18 Technická integrita, determinismus, testy a výkon

127. **PAQ-127 [PA0][PRODUCT] – Jaký uživatelsky viditelný determinism contract platí pro pre-alpha?** Příklad: stejné vstupy, seed a verze modelu vytvoří stejný zápas, pokud se vědomě nezvolí nový náhodný běh.
128. **PAQ-128 [PA0][TECH] – Jak se odvozují a ukládají seedy pro Run, slot, draw, zápas, rally a batch retry?** Příklad: retry jednoho selhaného turnaje bezdůvodně nepřehodí výsledek jiného turnaje.
129. **PAQ-129 [PA0][TECH] – Jaká úplná invariant/validation matice chrání všechny kritické entity a operace?** Příklad: jeden hráč nemůže současně obsadit dva fyzické sloty stejného zápasu.
130. **PAQ-130 [PA0][TECH] – Které operace jsou transakční a jak proběhne rollback při částečném selhání?** Příklad: entry slot buď zapíše všechna rozhodnutí a list, nebo žádné.
131. **PAQ-131 [PA0][TECH] – Jaké povinné údaje ukládá Audit Log pro ruční, importní a simulační mutace?** Příklad: kdo/co/kdy/proč, předchozí hodnota, nová hodnota, branch, čas a provenance.
132. **PAQ-132 [PA0][CALIBRATION] – Jaké golden fixtures a statistické testy prokážou sportovní smysluplnost základních modelů?** Příklad: silnější hráč dlouhodobě vyhrává častěji, ale upsety zůstávají možné.
133. **PAQ-133 [PA1][TECH] – Jaké výkonové rozpočty platí pro zápas, turnaj, week, sezonu, import a uložení?** Příklad: UI zůstane responzivní a dlouhá sezona ukazuje průběh místo zamrznutí.
134. **PAQ-134 [PA0][TECH] – Jaké recovery, round-trip a corruption testy musí projít před prvním pre-alpha buildem?** Příklad: exportovaný a znovu importovaný Run zachová fingerprinty, výsledky, historii i branch vztahy.

## 31.19 Minimální Official Run obsah pro akceptační průchod

135. **PAQ-135 [PA0][CONTENT] – Jaký World dataset zemí, regionů, časových pásem a populační historie je minimálně úplný?** Příklad: každá země použitá hráčem či turnajem má platnou identitu a potřebná data pro příslušný week.
136. **PAQ-136 [PA0][CONTENT] – Jaký počáteční seznam hráčů, věků, atributů, stavů a baseline rankingu se použije?** Příklad: první turnaj má dost eligible hráčů pro Main Draw i kvalifikaci.
137. **PAQ-137 [PA0][CONTENT] – Jaká první hierarchie Competition Systems, Tours a Categories je pro akceptační sezonu autoritativní?** Příklad: tierové kategorie mají lokální pořadí a speciální soutěž může mít `tier_rank = null`.
138. **PAQ-138 [PA0][CONTENT] – Jaké Tournament Series, Edition Plans a konkrétní kalendářové Editions obsahuje testovací sezona?** Příklad: kalendář zahrne souběžné možnosti, kvalifikaci, vícetýdenní turnaj i navazující week.
139. **PAQ-139 [PA0][CONTENT] – Jaké šablony formátů, entry, qualification, draw a lifecycle policy budou přiřazené jednotlivým kategoriím?** Příklad: Ranked turnaj má úplnou Q/Main Draw strukturu a všechny deadlines.
140. **PAQ-140 [PA0][CONTENT] – Jaké bodové tabulky, Best N, PR a disciplinární defaulty platí v první testovací sezoně?** Příklad: každý dosažitelný výsledek Ranked Edition má právě jednu konečnou hodnotu.
141. **PAQ-141 [PA1][CONTENT] – Které soutěže mimo běžnou MSA Tour musí být v pre-alpha skutečně simulovatelné end-to-end?** Příklad: pokud se zahrne olympiáda nebo juniorské MS, potřebují minimální field, eligibility, formát a kalendář; jinak zůstanou vědomě mimo akceptační průchod.
142. **PAQ-142 [PA0][CONTENT] – Jaké referenční scénáře a očekávané výsledky tvoří akceptační sadu Official Runu?** Příklad: seed cascade, LL náhrada, medical timeout, RET, změna Best N a Season Transition mají každý uložený testovací případ.

## 31.20 Doplňkové průřezové mechanismy pre-alpha

143. **PAQ-143 [PA1][PRODUCT] – Jaké minimální chování má změna reprezentované země, pokud nastane v akceptačním Runu?** Příklad: pre-alpha buď podporuje současný prozatímní eligibility workflow, nebo změnu dočasně bezpečně nepovolí místo náhodného nedokončeného výsledku.
144. **PAQ-144 [PA0][PRODUCT] – Jaké historické objekty a stavy musí Viewer time machine umět zobrazit v minulém weeku?** Příklad: profil hráče ve Weeku 20 ukáže tehdejší zemi, ranking a veřejný zdravotní stav, ne dnešní hodnoty.
145. **PAQ-145 [PA1][PRODUCT] – Jaký minimální katalog World Events a Notification pravidel potřebuje funkční turnajový průchod?** Příklad: oznámení turnaje vytvoří veřejnou MSA zprávu, zatímco neplatná reference zůstane jen Admin varováním.
146. **PAQ-146 [PA1][TECH] – Jaké základní H2H a statistiky se musí automaticky dopočítat z autoritativních výsledků?** Příklad: RET se počítá jako sportovní výhra/prohra, ABN bez vítěze se do H2H výher nezapočte.
147. **PAQ-147 [PA1][PRODUCT] – Jaké minimum pokrývá kopie Runu a vestavěný Match Test Lab?** Příklad: testovací session používá read-only snapshot hráčů a její výsledek nikdy nezmění zdrojový Run.
148. **PAQ-148 [PA1][TECH] – Jaká minimální lock/concurrency matice platí pro souběžné úlohy, Runy a branche?** Příklad: Forecast v jedné branchi nesmí blokovat čtení jiné, ale dva zápisy do stejného snapshotu se serializují.
149. **PAQ-149 [PA1][PRODUCT] – Jaké minimum CSV/XLSX staging importu musí být dostupné pro tvorbu potřebných dat?** Příklad: chybný řádek země lze opravit v preview a nezávislé platné řádky bezpečně importovat.
150. **PAQ-150 [PA0][PRODUCT] – Jaký minimální Viewer reveal/privacy režim zabrání úniku Admin truth, dokud jsou detailní reveal režimy odložené?** Příklad: Viewer u zranění ukáže jen veřejný údaj nebo odhad, nikdy skrytou přesnou závažnost známou Adminu.

## 31.21 Pokrytí kapitol Masteru pre-alpha bránou

| Kapitoly Masteru | Hlavní `PAQ` | Zacházení v pre-alpha |
|---|---|---|
| 1–2 Vize, Viewer a Admin | 001–005, 119–126, 150 | rozsah a minimální obě uživatelské vrstvy |
| 3, 7–8 Runy, branche a ukládání | 014–021, 127–134, 147–148, 157 | autoritativní historie, bezpečné návraty, názvy branchí a technická integrita |
| 4, 24 Packages a přenositelnost | 022–029, 134 | pět Package typů, bezpečný import/export a Setup |
| 5, 9–10 Země a hráči | 038–044, 135–136, 143, 149 | počáteční data, generování, identity a minimální import |
| 6 Čas a sezony | 030–037, 144 | Slots, transitions a historické zobrazení |
| 11–12 Schopnosti a lifecycle hráče | 045–062, 111–117, 151–155 | vývoj, forma, zdraví, AI, retirement a nové stavové minimum |
| 13–15 Turnaje, kategorie, entries a los | 074–094, 137–141 | end-to-end Tournament Edition workflow |
| 16–17 Zápasy a simulace | 063–073, 103–110 | rally-by-rally model, výsledky, Replay a Reconstruction |
| 18–20 Ranking, finance a disciplína | 095–102, 140, 156 | Official ranking, Financial Level a konfigurovatelné doprovodné policy |
| 21 Statistiky a historie | 146 | odvozené minimum; pokročilé Awards/Records/Rivalries později |
| 22 Predikce | mimo blokující bránu | současné směry zůstávají nezávazné a neautoritativní |
| 23, 27 Viewer a UX | 119–126, 144–145, 150 | minimální navigace, veřejné stránky a informační hranice |
| 25 Audit a validace | 121–134, 145, 148 | validace, audit, recovery a bezpečný souběh |
| 26 Samostatné soutěže | 141 | jen ty, které budou výslovně součástí akceptačního Runu |

## 31.22 Co tuto bránu vědomě neblokuje

Výslovně odložená nebo pozdější funkce se do pre-alpha nevrací jen proto, že je uvedena v Masteru. Bránu neblokuje jejich detailní dopracování, pokud nejsou nutné pro zvolený akceptační průchod. Patří sem zejména plný Forecast/Future Locks/Forecast Markets systém, pokročilý forcing a rare-event výzkum nad rámec minimálního Match Reconstruction, hluboký tréninkový model, detailní kurtová fyzika a venue logistika, pokročilé rozhodcovské edge cases, vlastní očekávání budoucích turnajů hráčskou AI, Country Ranking, úplné Awards/Records/Rivalry modely, další veřejné weby a soutěžní obsah, který nebude součástí první testovací sady.

Tato hranice není nové rozhodnutí o jejich definitivním odstranění. Znamená pouze, že již označené `ODLOŽENO / POZDĚJI` zůstává mimo pre-alpha, dokud uživatel výslovně nezmění rozsah.

## 31.23 Dodatečně objevené pre-alpha otázky ve verzích 49–52

151. **PAQ-151 [PA0][CALIBRATION] – Jak se pro první verzi vypočítá dvousložková Experience a její klesající mezní přínos?** Příklad: 300 běžných zápasů nemusí dát stejnou `High-Pressure Experience` jako 150 zápasů s několika velkými finále.
152. **PAQ-152 [PA0][CALIBRATION] – Jak se inicializuje a aktualizuje Match Sharpness `0–100 %` a jaký má minimální výkonový účinek?** Příklad: hráč po osmi weekách bez zápasu má nižší Sharpness než pravidelně hrající soupeř, ale vysoké zatížení se řeší přes fatigue a zdraví, nikoliv záporným účinkem vysoké Sharpness.
153. **PAQ-153 [PA0][CALIBRATION] – Jak první verze spojí Opponent Study a Match-specific Court Training do jedné Match Preparation `0–100 %` včetně nákladů a přenosu historie?** Příklad: hráč s vyšším `Analysis` vytěží ze stejné doby sledování více a po zápase mu zůstane historická znalost soupeře, nikoliv otevřený dočasný přípravný bonus.
154. **PAQ-154 [PA1][CALIBRATION] – Jaký první algoritmus vytváří kandidátní historické vývojové cesty a měří jejich realističnost a podobnost?** Příklad: cesta `Analysis 145 → 160` od Weeku 18 zachová přesný soutěžní skelet, vypíše odchylky v délce a stavu a nepřekročí červený development limit.
155. **PAQ-155 [PA0][CALIBRATION] – Jaké první pravděpodobnosti a křivky řídí jednotný Health Check, aktivaci `At Risk`, skládání omezení, detekci a zotavení?** Příklad: stejné predispozice se nesmějí započítat jako tři plné nezávislé šance ve slotu, tréninku a rally.
156. **PAQ-156 [PA0][CALIBRATION] – Jak se inicializuje a týdně mění Financial Level `0–10` a jaké malé modifikátory a AI prahy používá?** Příklad: TOP 1000 má ve FAX vysokou pravděpodobnost prostředků na normální kalendář, ale ranking sám nezaručí konkrétní level ani každou vzdálenou cestu.
157. **PAQ-157 [RESOLVED v52][PA1][PRODUCT] – Jaký výchozí zobrazovaný název a pojmenovací workflow použije počáteční a každá další běžná branch?** Odpověď: počáteční branch se automaticky jmenuje `Timeline 1`; další běžná branch dostane první nepoužitý návrh `Timeline N`, který může uživatel před vytvořením nahradit vlastním jedinečným názvem.

## 31.24 Souhrn rozhodovací brány

Ve v64 zůstávají níže uvedené počty z v63 beze změny. Nová vývojová priorita z 31.1 není další sportovní pravidlo a neuzavírá žádnou další PAQ.

| Vrstva | Počet | Podmínka uzavření |
|---|---:|---|
| Široké otevřené/odložené okruhy `OQ` | 69 | Zůstávají zdrojovým registrem kapitoly 30 |
| Atomické pre-alpha otázky `PAQ` | 157 | Každá má odpověď, minimální default nebo vědomý stub podle `PA0 / PA1` |
| Z toho ve verzi 63 `[RESOLVED]` | 48 | `PAQ-001–005`, `014`, `016`, `023–024`, `027`, `029–034`, `036–037`, `042–046`, `051`, `053`, `058`, `063–081`, `097`, `115` a `157` |
| Z toho ve verzi 63 stále otevřeno | 109 | `PAQ-082` zůstává výslovně otevřená; absence terminálního markeru znamená `[OPEN]` a vyžaduje odpověď, default, kalibraci, obsah nebo vědomý stub podle vlastníka |
| Pevná rozhodnutí | 411 | Včetně Match Format/snapshot kontraktu, minimálních turnajových entit, dědičnosti, materializace, lifecycle/public version matice a fair-rest scheduleru z v62 |
| Prozatímní pravidla a směry | 88 | Přesný field-specific katalog, Country↔Country model, hluboký trénink, číselná kalibrace rally i mezi-rally času a další výslovně označené směry zůstávají prozatímní či otevřené |

Počet `PAQ` není odhad všech budoucích rozhodnutí. Je to současná behaviorální a obsahová brána první pre-alpha; jedna otázka se při kalibraci může rozpadnout na další podotázky a několik otázek může uzavřít jedna společná odpověď.


# 32. Procentuální audit stavu specifikace

## 32.1 Metodika

**Upřesnění v64:** orientační odhad hotového kódu 25–35 %, vyslovený v navazujícím chatu, nebyl podložen úplným váženým auditem implementace. Není přijat jako ověřené procento dokončení pre-alpha. Počty testů, PR ani simulovaných zápasů nejsou jeho náhradou. Rozhodující jsou konkrétní funkční mezery a dva akceptační průchody v 31.3.

Tato procenta jsou **odhad stavu rozhodování**, nikoliv stav naprogramování. Jednotlivé oblasti jsou vážené podle rozsahu a složitosti; jedno rozhodnutí typu „BO5 do 11“ proto nemá stejnou váhu jako celý development nebo entry systém.

Auditní opravy ve verzi 21 zpřesnily několik statusů. Ve verzi 24 byly odhady přepočítány po uzavření package snapshotů, formálního vstupu prospecta na Tour, historického vývoje kategorií a části Team World Championship. Verze 25 je orientačně upravila po rozhodnutí rankingového tie-breaku, další velké části Team World Championship a základního kontraktu potenciálu, OVR, hráčského stavu, Match Enginu, AI a zdraví. Verze 26 je znovu mírně posunula po uzavření operation-scoped spustitelnosti a validace, kontinuity únavy, Inactive triggerů, recovery a hranice Undo/Redo. Verze 27 přidala uzavřený lifecycle Runu, bezpečný CSV/XLSX import, kopírování, historii branchí a hlavní kontrakt přenositelnosti. Verze 28 uzavírá částečné a verzované ukládání, základ storage bezpečnosti bez kvót, dlouhé úlohy po zavření aplikace, tři druhy zastavení, checkpoint policy, obsahovou nezávislost balíčků a velkou část branch-specific stavu. Verze 29 uzavírá první vrstvu cílové navigace: vstup přes Všechny Runy, jedno hlavní okno, globální Run/Branch/Čas/mode kontext a kompaktní rychlé voliče. Verze 30 doplňuje neutrální řádkový přehled Runů se třemi vstupy, rozdílnou Admin/Viewer navigační kostru, kontextové mapování módů a Viewer jako ekosystém více historicky věrných veřejných webů s MSA jako hlavním současným webem. Verze 31 zavádí `Squash Engine Home`, globální a Runový Admin scope, kontextový sidebar, přesnou dostupnost Vieweru, logo hierarchii a Present/Past/Future stavy času. Verze 32 potvrzuje Run `Home`, jeho dva progress ukazatele a základní hover/pin mechaniku sidebaru; konkrétní strom kategorií, `Rankings & Analytics` a World stránky započítává pouze jako prozatímní silné směry. Verze 33 přidává pouze jako silný směr univerzální index odchylky, nezávazný Forecast Engine, extrémně škálovatelný počet pokusů, hypotetické scenario comparison, striktní oddělení od hráčské AI a historické Forecast Markets s více pravděpodobnostními vrstvami. Verze 34 jako silný směr rozšiřuje Forecast o kompaktní průběžnou agregaci a hlavní kontrakt Future Locks včetně feasibility, přirozené pravděpodobnosti, granulárních podmínek, společného vyhodnocení a použití v branchích. Verze 35 jako silný směr doplňuje 256bitový Forecast seed, dávkové sledování přesnosti, replay a prodlužování vzorků, adaptivní Visualizer, Highlight/Focus, oddělený Rare Event Accelerator, Scenario Inspector, piny, materializaci branche a párové counterfactualy. Verze 36 uzavírá World Event Log, Audit Log, Task Center a Notification Center jako oddělené vrstvy, automatická upozornění a watchlisty, jednotné informační/oranžové/červené stavy, operation-scoped kritické blokování a Admin/Viewer hranici upozornění. Verze 37 doplňuje dva pevné vyloučené body a několik různě silných směrů: zjednodušená geografie a jet lag mají rozhodnutý základ, individuální cestovní predispozice jsou běžným směrem, skupinové rivality silným směrem, Rivalry Score a Tournament Appeal slabým směrem a turnajová prestiž běžným směrem. Verze 38 nově uzavírá první kontrakt Week Transitionu, týdenního developmentu, současných globálních Simulation Slots a jejich základního ovládání a potvrzuje automatické veřejné zprávy na historické MSA homepage. Individuální hráčská AI je rozhodnutý princip, její konkrétní chování zůstává pozdější kalibrací; retirement propensity a Admin digest jsou běžné směry, třícestné lifecycle rozhodování a News Importance Score pouze slabé směry. `Conflict Fork` a `Scenario Direction` nadále započítává pouze jako běžné směry a přeskočený lifecycle úprav splněného locku jako otevřený. Další Package typy nad nyní potvrzenou pětici zůstávají pouze prozatímním směrem. Jemné branchové zámky jsou také pouze prozatímní a okamžik přepnutí Viewer Branch zůstává otevřený. Konflikt stejného `run_id`, porovnání různých weeků a konfigurační hierarchie také zůstávají jen prozatímní; přeskočené Viewer reveal režimy, přesné MSA menu, samostatná stránka News, počet procesních oken ani plný seed contract celého enginu se do rozhodnuté části nezapočítávají. Verze 39 uzavírá základ Season Transitionu, plánování všech 50 sezon přes Inherited Plans, odvozený lifecycle a Public Stage Tournament Edition, historickou hranici veřejné znalosti přes announcement week a transakční entry sloty s úzkým retry contractem. Admin lifecycle akce zůstávají silným směrem, zatímco mimořádné ukončení rozběhnutého turnaje a společné AI portfolio přihlášek jsou pouze běžné směry. Verze 40 nově uzavírá rally-by-rally granularitu první verze, čtyřvrstvou rally pipeline, pět stavů kontroly, tři stamina systémy s jejich tréninkem a průběžnou aktualizací, kompaktní rally log, squashově malou váhu podání a základ správně rozhodovaných zjednodušených interferencí. Konkrétní matematiku, kalibraci a pokročilé rozhodčí či zdržování započítává jako otevřené nebo pozdější. Verze 41 opravuje pouze doložené statusové hranice a jednu opomenutou potvrzenou existenci rivalit; nejisté detaily nepovyšuje a celkové procentní odhady se tím materiálně nemění. Verze 42 uzavírá významnou část sezonního Best N, formy, zdravotních a časových událostí zápasu a Match Reconstruction, ale výchozích deset kandidátů, detailní probability architekturu, retenci session, compact-card fields a zdravotní okraje započítává pouze v jejich skutečně prozatímních, směrových či otevřených statusech. Odhad zmapované specifikace se proto mírně posouvá, zatímco široký odhad celého budoucího enginu zůstává beze změny. Stále jde o kvalifikovaný odhad, nikoliv mechanickou metriku.

Verze 43 zvyšuje rozhodnutou část především uzavřením Country Modelu V1, významového oddělení `p / δ / α`, odvozených fyzických a mentálních zápasových stavů, kontextového atributového výpočtu, krokové simulace, Replay, Scores a rozšířeného kandidátního workflow. Konkrétní katalog 57 atributů, Match-Day Baseline a domácí efekt započítává pouze v jejich prozatímních statusech; trénink, country matematiku, forcing, multimodální indexy, pracovní retenci a detailní UI ponechává otevřené nebo odložené. Starší v40 formulace samostatně trénovatelných stamina schopností je pro současný stav nahrazena odvozenými bary podle kapitol 11.4–11.5.

Verze 44 zvyšuje rozhodnutou část zejména v oblasti turnajů, entries a časového plánování: společné slotové rozhodování AI, veřejné předběžné listy, konflikt a základ sankcí, Week Tournament Lock, Still Competing, Final Commitment, Travel Load a Round Schedule nyní tvoří kontrakt první verze. Do rozhodnuté části nezapočítává přesnou AI, číselné sankce, konkrétní umístění cut-offů, travel matematiku, detailní logistiku ani budoucí výjimky umožňující více akcí v jednom weeku. Široký odhad celého budoucího enginu se kvůli těmto úzkým prvním kontraktům materiálně nemění.

Verze 45 zvyšuje rozhodnutou část turnajů a rankingu uzavřením třífázového draw repair workflow, atomických náhrad, standardního seed cascade, WC/RWC a LL identity, BYE unlocku, aditivních Q + Main Draw bodů, Ranked/Unranked Editions, publikační úplnosti bodové tabulky a sezonního dědění bodů. Finance první verze nově přesně rozlišují nepovinnou či neúplnou konfiguraci od nulové hodnoty a uzavírají finishing-stage výplaty, Q/Main Draw payout i odvozený prize pool. Číselné tabulky, celkový počet procesních oken, Final Commitment, mimořádné cascade edge cases a disciplinární forfeity po zahájeném DQ zůstávají otevřené. Souvislé registry nyní obsahují 276 pevných, 80 prozatímních a 69 otevřených bodů; široký odhad celého budoucího enginu se tímto relativně úzkým kontraktem materiálně nemění.

Verze 46 konsoliduje bez nového auditu starších archivů pouze explicitně potvrzený blok po v45. Uzavírá zdroj a lifecycle Ranked/Unranked statusu, plné sportovní následky a AI motivace Unranked akcí, předstartovní Cancelled, dva režimy Postponed, dočasné Suspended a terminální Abandoned včetně rankingových a nakonfigurovaných finančních důsledků. Zápasový model doplňuje terminální ABN se zachovaným částečným stavem a `External Interruption → Yes Let → replay` první verze. Výslovně přeskočený práh přechodu do Suspended a dříve otevřené seeding/LL otázky Protected Rankingu zůstávají otevřené. Souvislé registry nyní obsahují 292 pevných, 79 prozatímních a 69 otevřených bodů; široké procentní odhady se tímto tematicky úzkým doplněním materiálně nemění.

Verze 47 opravuje jednu zásadní zastaralou package formulaci a uzavírá větší část přenositelné skladby Runu. Do rozhodnuté části nově započítává prázdný Run, pět současných typů Packages, měkké závislosti a unresolved reference, volitelný neúplný Setup, stabilní kategoriální identity, rozsah a merge Calendar Package, Edition Plan provenance a denní Match Schedule s uloženým pořadím a fair-rest základem. Nezapočítává jako pevné přesnou hranici Series/Calendar polí, více Editions téže Series v jedné sezoně, matching a konfliktní merge pravidla, detailní scheduler matematiku ani přesné hodiny. Souvislé registry nyní obsahují 308 pevných, 81 prozatímních a 69 otevřených bodů.

Verze 48 načítá do konce veřejný snapshot navazujícího chatu a konsoliduje pouze skutečně potvrzený blok po v47. Uzavírá source a Run-local identity Package entit, lifecycle a přenos verzí, Setup version snapshot, bezpečný opakovaný a selektivní import, přesný uživatelský scope exportu, sezonní kategorickou hierarchii, významovou hranici Series/Calendar, více Editions jedné Series, materializaci `edition_plan_id`, kontrakt jednoho plánu a lifecycle odstranění Draftu oproti veřejně známé Edition. Ruční kanonický merge, divergentní Package historie a úplnost jiných než Calendar partial scopes zůstávají silnými směry; shodné `tier_rank` je odložené a poslední otázka o neměnných Draw Versions zůstává bez odpovědi otevřená. Souvislé registry nyní obsahují 335 pevných, 84 prozatímních a 69 otevřených bodů.

Verze 48a pouze zpřesňuje měření a plán dalšího rozhodování. Zavádí 69 stabilních `OQ` identifikátorů pro široké otevřené okruhy a 150 atomických `PAQ` otázek tvořících současnou pre-alpha bránu. Protože žádná z těchto otázek nebyla ve v48a obsahově zodpovězena, procenta rozhodnutosti ani registry 335 / 84 / 69 se nemění. Nový backlog naopak ukazuje, že vysoké procento zmapované kostry nelze zaměnit za připravenost všech vzorců, dat, UI a technických kontraktů k end-to-end implementaci.

Verze 49 uzavírá funkční pre-alpha základ atributů, OVR, Potential OVR, celoživotního vývojového typu, Experience, Match Sharpness a Match Preparation, ale nepovyšuje jejich orientační číselné defaulty ani přesné budoucí projevy. Registry se tím mění na 348 pevných, 88 prozatímních a 69 širokých otevřených bodů. Pre-alpha brána má 153 atomických `PAQ`: dvě jsou vyřešené a 151 zůstává otevřených. Nové body zvyšují rozhodnutost zmapované hráčské vrstvy pouze mírně, protože její vzorce, distribuce, kalibrace a část minimálního tréninkového kontraktu se teprve musí určit.

Verze 50 uzavírá hlavní akceptační hranici a významnou část dosud otevřeného behaviorálního kontraktu: dva povinné end-to-end průchody, Draft/Save/Viewer hranici, pořadí Week a Season Transitionu, Season Closing Ranking, jemnější atomické skupiny Simulation Slotu, tři režimy historického dopočtu vývoje, minimální zdravotní datový model, testovací Financial Level a minimální Rally Setup. Registry nyní obsahují 380 pevných, 88 prozatímních a 69 širokých otevřených bodů. Pre-alpha brána byla rozšířena na 156 atomických `PAQ`; 17 je vyřešených a 139 zůstává otevřených. Samostatné osy regenerace byly správně ponechány odložené, ligový squash nebyl omylem zaveden do modelu a nové číselné křivky se nezapočítávají jako rozhodnuté. Závěrečný porovnávací a konfliktní audit v50 nenašel nevysvětlenou kolizi.

Verze 51 přidává jediné nové pevné produktové pravidlo: úspěšné vytvoření Runu je jeho první uloženou verzí s počáteční Viewer Branch, Saved Revision bez rodičovské revize a čistým Working Draftem v jedné atomické operaci. Zpřesnění, že Run je celý strom historie a nikdy jedna sezona, pouze odstraňuje možnou výkladovou nejasnost již existujícího modelu. Registry proto obsahují 381 pevných, 88 prozatímních a 69 širokých otevřených bodů. Pre-alpha brána má nově 157 atomických `PAQ`; 17 zůstává vyřešených a 140 otevřených, protože výchozí pojmenování branchí nebylo potvrzeno. Samostatná implementační evidence v kapitole 35 se do procent rozhodnutosti ani do těchto registrů nezapočítává.

Verze 52 uzavírá jediný zbývající produktový detail potřebný pro právě dokončený branchový řez: `Timeline 1` a první nepoužitý návrh `Timeline N` s možností vlastního jedinečného názvu. Registry proto obsahují 382 pevných, 88 prozatímních a 69 širokých otevřených bodů. Pre-alpha brána zůstává na 157 atomických `PAQ`; 18 je vyřešených a 139 otevřených. Ověřená implementace PR #672 je vedena odděleně v kapitole 35 a sama nemění procenta rozhodnutosti.

Verze 53 nepřidává žádné produktové rozhodnutí ani nový implementační claim. Úplný handoff audit posledního sdíleného chatu potvrdil, že v52 už správně obsahovala celý jeho věcný rozdíl, včetně hranic `IMP-003` a dalšího kandidáta na backbone. Registry proto zůstávají 382 / 88 / 69 a pre-alpha brána 18 vyřešených / 139 otevřených z celkem 157 `PAQ`. Dokument je od této verze výslovně soběstačný pro další práci; předchozí chat není nutné znovu načítat ani citovat, pokud se neprovádí historický audit původu.

Verze 54 přidává pouze ověřenou implementační evidenci `IMP-004` pro sloučený PR #673 a nahrazuje již splněný pokračovací bod dalším úzkým technickým řezem. Nemění žádné produktové rozhodnutí, proto registry zůstávají 382 / 88 / 69 a pre-alpha brána 18 vyřešených / 139 otevřených z celkem 157 `PAQ`.

Verze 55 přidává pouze ověřenou implementační evidenci `IMP-005` pro sloučený PR #674 a potvrzuje splnění read-only Saved Revision History řezu včetně přímé použitelnosti vrácených revision ID pro existující branch workflow. Nemění žádné produktové rozhodnutí, proto registry zůstávají 382 / 88 / 69 a pre-alpha brána 18 vyřešených / 139 otevřených z celkem 157 `PAQ`.

Verze 56 uzavírá pět `[PA0][PRODUCT]` položek `PAQ-023 / 024 / 027 / 029 / 030`: univerzální nedestruktivní partial scope, minimální dependency-resolution workflow, bezpečný pre-alpha fallback Package divergence, aplikaci neúplného Setupu a testovatelné pořadí Simulation Slotu. Registry se tím mění na 387 pevných / 87 prozatímních / 69 širokých otevřených bodů a pre-alpha brána na 23 vyřešených / 134 otevřených z celkem 157 `PAQ`. Široký registr `OQ` zůstává na 69 bodech, protože `OQ-009` a `OQ-012` nadále obsahují pokročilé schema compatibility, ruční mapping, field-level conflict UX a post-pre-alpha kanonický merge. Procentní odhady se pěti úzkými kontrakty materiálně nemění. Implementační evidence zůstává po PR #674 beze změny.

Verze 57 uzavírá čtyři `[PA0][PRODUCT]` položky `PAQ-034 / 036 / 042 / 043`: hierarchickou operation-scoped prerequisite matici, jedinou globální slotovou časovou osu a mapování procesních a Match Day oken, přesné první rankingové postavení nového Tour Playera a povinné hráčské jádro se stabilním duplicate-name fallbackem a časově verzovanou Sporting Representation `Country / World / FAX Neutral`. Registry se tím mění na 391 pevných / 86 prozatímních / 69 širokých otevřených bodů a pre-alpha brána na 27 vyřešených / 130 otevřených z celkem 157 `PAQ`. Široké `OQ-001 / 016 / 021 / 023 / 036` zůstávají jako zdroj dosud otevřeného UX, AI, Country↔Country, kalibračního a optimalizačního detailu; jejich rozhodnutý základ je v textu výslovně oddělen. Procentní odhady se čtyřmi úzkými kontrakty materiálně nemění. Implementační evidence zůstává po PR #674 beze změny.

Verze 58 uzavírá pět položek `PAQ-051 / 053 / 066 / 067 / 115` jedním souvislým hráčským a zápasovým blokem. General Training Load `Recovery / Light / Normal / Heavy` tvoří společné minimum pro obecný trénink i AI recovery choice; aktivní styl/gameplan dostává osy `Risk / Tempo / Court Positioning / Variation`, Style Familiarity, nedokonalé counterování a vědomé či chybné setrvání. Rally kontext skládá atributy jako `Primary / Supporting / Constraint` bez dvojího započtení a terminální model odděluje jedenáct primary triggerů, pravidlový kontext, call, score mutations, analytické připsání a side incidents. Minimální ball-hit/turning/further-attempt flagy se přesouvají do pre-alpha bez zavedení shot-by-shot trajektorie. Registry se tím mění na 395 pevných / 86 prozatímních / 69 širokých otevřených bodů a pre-alpha brána na 32 vyřešených / 125 otevřených z celkem 157 `PAQ`. Číselné tréninkové účinky, transition a terminal probabilities, analytické thresholds, detailní referee/video model a široké zdravotní okraje zůstávají kalibrací nebo pozdější vrstvou. Procentní odhady se tímto úzkým kontraktem materiálně nemění a implementační evidence zůstává po PR #674 beze změny.

Verze 59 uzavírá `PAQ-064 / 065 / 068 / 069 / 070`. Rally nyní používá setrvačné lokální transitions, konečný rozsah `0–24` abstraktních segmentů s přímými serve/return konci a rostoucím closure pressure, ground truth oddělenou od deterministického rules resolveru bez náhodné chyby rozhodčího a podání působící pouze přes Serve Execution × Return Execution v openingu. Počet úderů, čas, pace a workload vznikají společně z téhož průběhu podle verzovaného RallyCalibrationProfile. Prozatímní mužský elitní koridor `median 11–13 / Q3 19–23` vychází z větší PSA analytiky a je kontrolován novější akademickou prací nad zápasy 2018–2020; stará práce publikovaná v roce 2016 a její vyšší percentily jsou pouze historickou referencí. Registry se mění na 400 pevných / 87 prozatímních / 69 širokých otevřených bodů a pre-alpha brána na 37 vyřešených / 120 otevřených z celkem 157 `PAQ`. Přesné transition a terminal probabilities, per-segment sampling, opening-end rate, moderní 95. percentil a finální časová křivka zůstávají kalibrací. Procentní odhady se úzkým kontraktem materiálně nemění a implementační evidence zůstává po PR #674 beze změny.

Verze 60 uzavírá `PAQ-071`. Mezera mezi rally nyní vzniká kauzálně jako maximum připravenosti servera, receivera, rozhodčího a kurtu; hráči mají rozdílné stabilnější tendence na podání a returnu a situačně volí `accelerate / natural / delay` podle vlastního stavu, soupeře, skóre, momenta a gameplanu. Taktika působí pouze přes skutečný čas, recovery, připravenost a omezený rhythm-pressure kontext, může pomoci i soupeři nebo se obrátit proti iniciátorovi. Přirozený reset po dramatické rally se odlišuje od bezdůvodného time-wastingu, který v pre-alpha vstupuje do zjednodušeného prompt/warning/Conduct Stroke resolveru bez náhodné chyby a bez individuálního referee profilu. Pracovní mužský koridor běžných mezer je převážně `8–18 s` s průměrem kolem `13 s`; samostatné objektivní události se do recovery nepřičítají podruhé. Registry se mění na 401 pevných / 88 prozatímních / 69 širokých otevřených bodů a pre-alpha brána na 38 vyřešených / 119 otevřených z celkem 157 `PAQ`. Finální distribuce, conduct thresholds a detailní rozdíly rozhodčích zůstávají kalibrací či pozdější vrstvou; implementační evidence zůstává po PR #674 beze změny.

Verze 61 přidává pouze ověřenou implementační evidenci `IMP-006` pro sloučený PR #675 a posouvá pokračovací hranici za první atomický Saved Revision restore a Admin historii. Nemění žádné produktové rozhodnutí, proto registry zůstávají 401 / 88 / 69 a pre-alpha brána 38 vyřešených / 119 otevřených z celkem 157 `PAQ`. Přesný podporovaný restore scope i jeho současné hranice jsou oddělené od cílového sporting restore; dalším technickým kandidátem je pouze read-only dohledatelnost existujících safety checkpointů a branch revision Audit Eventů.

Verze 62 uzavírá `PAQ-072–081` jako jeden navazující kontrakt od konkrétního zápasu přes Tournament Edition až po její schedule a veřejnou historii. Přidává atomický oficiální Match Format fallback, neměnný rally snapshot/hash/replay model, minimální entity, pevnou obecnou dědičnost s field scopes, bezpečnou materializaci, startem řízené edition numbering, třívrstvý lifecycle, verzované public timing, 2×2 mimořádné stavy a deterministické fair-rest priority. Registry se tím mění na 411 / 88 / 69 a pre-alpha brána na 48 vyřešených / 109 otevřených z 157 `PAQ`; `PAQ-082` zůstává záměrně otevřená a orientační výkonové či storage odhady zápasu nejsou canon. Implementační evidence se posouvá na `IMP-007` po PR #676.

Verze 63 rozšiřuje pouze implementační evidenci na IMP-017 po deseti sloučených zápasových PR #677–686. Produktové registry zůstávají 411 / 88 / 69 a pre-alpha brána 48 vyřešených / 109 otevřených ze 157 PAQ. Funkční první numerická kalibrace není uzavření finální matematiky PAQ-055/056/060/113/132. Procenta této kapitoly nadále popisují stav specifikace, nikoliv podíl hotového kódu. Zelený Fast CI ani existence zápasového enginu v9 samy neznamenají dokončenou pre-alpha.

Kategorie auditu:

- **Rozhodnuto** – dostatečně pevné pro návrh základního kontraktu.
- **Prozatímní směr** – existuje pracovní odpověď, ale ještě se může změnit.
- **Projednáno, ale otevřeno** – téma jsme otevřeli, přeskočili nebo výslovně odložili.
- **Vůbec neprojednáno** – v tomto konkrétním chatu jsme zatím neřešili ani podstatnou část oblasti.

## 32.2 Odhad podle oblastí

| Oblast | Váha | Rozhodnuto | Prozatímní | Projednáno, otevřeno | Vůbec neprojednáno |
|---|---:|---:|---:|---:|---:|
| Základ produktu a módy | 6 % | 85 % | 6 % | 6 % | 3 % |
| Runy, ukládání, archivace a přenos | 9 % | 87 % | 7 % | 3 % | 3 % |
| Branche, checkpointy a změny minulosti | 8 % | 77 % | 16 % | 4 % | 3 % |
| Packages, země a populace | 10 % | 92 % | 4 % | 3 % | 1 % |
| Čas, sezony a Viewer time machine | 7 % | 93 % | 4 % | 2 % | 1 % |
| Hráči, generování a lifecycle | 12 % | 66 % | 18 % | 12 % | 4 % |
| Schopnosti, vývoj, zdraví a AI chování | 10 % | 76 % | 13 % | 9 % | 2 % |
| Turnaje, kalendář, entries a losy | 12 % | 91 % | 4 % | 4 % | 1 % |
| Match engine a výsledkové detaily | 9 % | 92 % | 4 % | 3 % | 1 % |
| Rankingy, live data, statistiky a predikce | 8 % | 63 % | 32 % | 4 % | 1 % |
| Viewer/Admin UX a navigace | 5 % | 89 % | 8 % | 2 % | 1 % |
| Technika, úložiště, výkon a audit | 4 % | 81 % | 14 % | 3 % | 2 % |

## 32.3 Stav dnes známého a zmapovaného rozsahu

Následující tabulka se vztahuje **pouze k oblastem, které už jsou v tomto masteru pojmenované**. Není to procento celého budoucího Squash Enginu, protože jeho úplný konečný rozsah zatím neznáme.

| Stav dnes zmapované specifikace | Odhad |
|---|---:|
| **Pevně rozhodnuto** | **82 %** |
| **Prozatímní směr** | **11 %** |
| **Projednáno, ale stále otevřeno/odloženo** | **5 %** |
| **V tomto chatu zatím vůbec neprojednáno** | **2 %** |

V rámci dnes známého seznamu témat z toho plyne:

- **98 %** dnes zmapované specifikace jsme už alespoň nějak otevřeli.
- Přibližně **82 %** je skutečně rozhodnutých.
- Pokud se prozatímní směry počítají poloviční vahou, celková rozhodovací vyspělost je přibližně **88 %**.
- Největší hotové bloky jsou základ Runů, Viewer/Admin a Draft/Save logika, časový rozsah, archivace/přenos, volitelná Package skladba včetně identity a lifecycle verzí World/Category/Series/Calendar/Setup, nedestruktivní partial scope, bezpečné minimum unresolved závislostí, aplikace neúplného Setupu, bezpečný pre-alpha divergence fallback, sezonní kategoriální hierarchie, bezpečný selektivní import a přesný exportní scope, Country Model V1, povinné hráčské jádro a Sporting Representation `Country / World / FAX Neutral`, pre-alpha katalog 57 atributů na škále `0–200`, význam OVR a Potential OVR, základ Experience, Match Sharpness a Match Preparation, hlavní algoritmická kostra losování, základ rankingu včetně Season Closing Rankingu a prvního `NR` období Tour Playera, rally-by-rally kostra Match Enginu a minimální Rally Setup, odvozené fyzické a mentální stavy, minimální Injury/Illness lifecycle, experimentální Financial Level, kroková simulace a Replay, Match Reconstruction, historický dopočet vývoje, hierarchická prerequisite matice, přesné hlavní pořadí Week/Season Transitionu, jediná globální slotová osa, procesní pořadí a skupinová atomicita Simulation Slots, materializace Edition Plans, veřejná znalost Tournament Editions, Tournament lifecycle, Week Tournament Lock, zjednodušený Travel Load a denní Match Schedule.
- Největší mezery už nejsou v samotné existenci country pipeline, Package typů a lifecycle, developmentu, minimálního tréninku a stylu, AI, zdravotního datového základu, Match Enginu, storage bezpečnosti, sezonního přechodu, týdenního turnajového locku, Tournament Edition lifecycle/public version matice ani standardního draw repair workflow, ale v jejich přesné matematice, datových algoritmech, obsahu a UI. U hráčské vrstvy zůstávají otevřené zejména OVR váhy, růst kolem Potential OVR, úplné věkové křivky, Experience, Sharpness a Preparation výpočty, číselné účinky General Training Loadu, Health Check/healing/detekční křivky, Financial Level distribuce a modifikátory a budoucí taxonomie atributů. Dále zůstávají pokročilé porovnání a slučování divergentních Package historií, ruční kanonický merge, schema compatibility a detailní conflict/mapping UI, přesný form model, historický solver a probability/forcing/candidate-generation architektura Match Reconstruction, Final Commitment a některé replacement edge cut-offy, číselné body a finance kategorií, sankce, travel a číselná Match Schedule kapacita, transition a terminal probabilities Match Enginu, detailní lifecycle UI a přesuny přes sezonu, nezodpovězené Draw Versions, jemná concurrency/lock matice a hluboký performance contract.

## 32.4 Poctivější odhad celého budoucího enginu

Úplně přesné procento nyní **nelze spočítat**, protože neznáme jmenovatel: během dalšího dlouhého dialogu budou přibývat nové systémy, podstránky, pravidla a nápady, které zatím nejsou ani v seznamu.

Konzervativní pracovní odhad celého budoucího enginu je proto:

| Stav celého budoucího návrhu | Pracovní střed odhadu | Rozumné rozpětí |
|---|---:|---:|
| Pevně rozhodnuto | přibližně **40 %** | 35–45 % |
| Prozatímní směr | přibližně **15 %** | 11–19 % |
| Známé a projednané, ale otevřené | přibližně **19 %** | 15–25 % |
| Vůbec neprojednané nebo zatím ani neobjevené | přibližně **26 %** | 21–36 % |

Tento druhý odhad lépe odpovídá skutečnosti, že už máme poměrně silnou kostru produktu, ale ještě neznáme všechny budoucí požadavky. Nesmí se vydávat za matematicky změřenou hodnotu.

Prakticky tedy nyní platí:

- opravdu hotová rozhodovací specifikace tvoří přibližně **40 % celého předpokládaného enginu**,
- přibližně **26 %** může být úplně neprojednaných nebo dosud neobjevených,
- čísla se budou přirozeně měnit i tím, že uživatel přidá nové nápady a zvětší celkový rozsah projektu.

## 32.5 Co tvoří známou část dosud neprojednaných témat

Především hluboké části systémů, jejichž základní kontrakt už známe, ale přesné fungování jsme zatím nenavrhli:

- konkrétní matematika skrytých rally přechodů, terminálních incidentů, délky, zátěže, podání, interferencí a vlivu atributů na jednotlivé rally, sety a skóre,
- přesné váhy a matematické vazby rozhodnutého pre-alpha katalogu 57 atributů, OVR, měkkého Potential OVR, developmentu, formy, Experience, Match Sharpness, Match Preparation, tří odvozených fyzických barů, dvou mentálních barů, dlouhodobé fatigue, Health Checku a experimentálního Financial Levelu,
- přesný katalog, validace, probability model, přirozené a vynucené hledání, nearest-distance, rozmanitost, provenance, retence a konečné Admin UI Match Reconstruction i historického dopočtu vývoje,
- zbývající Final Commitment a replacement edge cut-offy, mimořádné cascade kombinace, číselné bodové a prize-money tabulky a zbývající skupinová qualification pravidla,
- přesné AI rozhodování hráčů o turnajích, vstupu na Tour, scoutingu, gameplanu, neaktivitě a retirementu,
- přesná pravidla všech kategorií v každé sezoně,
- Package schema compatibility, pokročilé porovnání a slučování divergentních historií, ruční kanonické slučování totožných entit a detailní conflict/mapping UI nad již rozhodnutým bezpečným pre-alpha minimem,
- technická konzistence, concurrency, recovery, výkon a dlouhodobá migrace dat,
- přesná granularita a retence World Event Logu, watchlistové triggery, seskupování a detailní Notification Center UX,
- přesná matematika cíleného Forecast samplingu, Future Locks, feasibility, forcing vah, společných podmínek, adaptivních vizualizací, replaye, Scenario Inspectoru, counterfactualů, Conflict Forku a kompaktního report storage,
- zbývající formáty týmových soutěží, kontinentálních mistrovství, Finals a individuálního World Championship,
- velká část detailního UI jednotlivých Admin obrazovek.

## 32.6 Odhad počtu zbývajících rozhodovacích otázek

Přesný počet neexistuje, dokud není známá úplná budoucí specifikace a jednotná granularita otázky. Například „jak fungují zranění“ může být jedna široká otázka, nebo několik desítek samostatných rozhodnutí.

Současný pracovní odhad při rozumném dělení je:

| Typ zbývajících otázek | Odhad |
|---|---:|
| Již výslovně pojmenované, ale nedořešené otázky po rozdělení širokých bodů na jednotlivá rozhodnutí | přibližně **140–240** |
| Otázky, které jsme v tomto chatu dosud vůbec nezmínili nebo ještě ani neobjevili | přibližně **170–290** |
| Pracovní střed odhadu dosud nezmíněných otázek | přibližně **220–230** |

Kapitola 31 nyní z tohoto neurčitého celku vyčleňuje **157 konkrétních atomických otázek `PAQ`**, které jsou v současnosti považované za rozhodovací, výchozí, implementační, kalibrační nebo obsahovou bránu první pre-alpha. Čtyřicet osm je ve v63 vyřešených a 109 zůstává otevřených. Neznamená to, že všech 157 musí uživatel osobně rozhodnout: položky `TECH` patří implementaci, `CALIBRATION` testování a `CONTENT` konkrétním datům Official Runu. Uživatelovo výslovné rozhodnutí vyžadují především položky `PRODUCT`.

Největší zdroje dosud nezmíněných otázek budou pravděpodobně podrobná matematika Match Enginu, zdraví a vývoj hráčů, AI rozhodování, sezonní ekonomika a pravidla kategorií, týmové soutěže, kompletní Admin/Viewer obrazovky, datová konzistence, migrace, výkon, testování a chybové stavy.

Tento odhad se může dočasně zvyšovat: objevením nového systému se zvětší známý rozsah enginu a jedna dosud neviditelná oblast se může rozpadnout na mnoho samostatných otázek.

---

# 33. Zásady pro další rozhodování

1. Vždy rozlišovat pevné rozhodnutí, prozatímní směr a otevřenou otázku.
2. Když je odpověď „asi“, nesmí být bod označen jako pevně rozhodnutý.
3. Když se otázka přeskočí, zůstane v otevřeném seznamu a nevymyslí se za uživatele.
4. Nejprve rozhodovat malé srozumitelné části systému; složité oblasti rozdělit později.
5. Ptát se hlavně na to, jak celý systém funguje, ne zahlcovat dialog jednotlivými okrajovými situacemi.
6. Nové náhodné nápady lze kdykoliv přidat a následně zařadit do správné kapitoly.
7. Tento dokument průběžně aktualizovat, aby dlouhý chat nebyl jediným nositelem rozhodnutí.
8. Informace z jiných chatů vždy označit pouze jako návrh, starší podklad nebo otevřený bod, dokud není potvrzena v tomto konkrétním chatu.
9. Každé nové pravidlo nebo rozhodovací otázku doprovodit krátkým konkrétním příkladem, aby byl zamýšlený význam jednoznačný.
10. Při dialogu vybírat vždy jen jednu dosud nezodpovězenou otázku, přednostně `[PA0][PRODUCT]`, a před položením ověřit její stav v detailní kapitole, registru `OQ` i backlogu `PAQ`.
11. Odpověď na `PAQ` se nesmí automaticky zapsat do Masteru po každé zprávě; rozhodnutí se shromažďují a dokument se aktualizuje až na výslovný pokyn uživatele.
12. `TECH` otázky může implementace později rozhodnout autonomně, ale nesmí tím změnit produktové pravidlo. Příklad: může zvolit formát interního checksumu, nikoliv sama určit sportovní bodovou tabulku.
13. `CALIBRATION` otázka je pro pre-alpha uzavřená teprve tehdy, když má výchozí hodnoty, reprodukovatelný test a možnost pozdějšího ladění. Příklad: první stamina křivka nemusí být finální, ale musí mít verzi a měřitelný očekávaný efekt.
14. Při výslovné aktualizaci Masteru se od verze 51 aktualizuje také samostatný registr ověřené implementace. Zapisuje se pouze přesně doložený scope, cílová branch, PR/commit, ověření a známá omezení; neověřená domněnka se nevydává za stav celého repozitáře.
15. Implementační evidence nesmí měnit status produktového pravidla. Pokud kód použije dosud nerozhodnutý viditelný default, Master jej označí jako implementační default nebo otevřenou otázku, nikoliv jako `[ROZHODNUTO]`.
16. Od verze 53 je tento Master úplným pokračovacím podkladem také pro práci navazující po PR #672; verze 54 tuto hranici posouvá za PR #673, verze 55 za PR #674, verze 61 za PR #675 a verze 62 za PR #676. Starší chaty a share odkazy jsou pouze auditní provenance; k běžnému pokračování se nemají znovu vyžadovat. Aktuální implementační hranice a současný pracovní režim se vždy čtou z kapitoly 35; není-li tam další kódový kandidát výslovně určený, nesmí se z historie domýšlet.

---

# 34. Definice produktu jednou větou

**Squash Engine má být dlouhodobý správce a simulátor mužského profesionálního squashového světa FAX, ve kterém lze od zemí, populace a narození talentů projít celými kariérami, turnaji, rankingy a padesáti sezonami, pravděpodobnostně analyzovat budoucnost, bezpečně vytvářet alternativní i podmíněné časové linie a celý výsledek prohlížet jako historicky přesné read-only prostředí několika fiktivních veřejných webů v čele s oficiálním webem MSA.**

---

# 35. Ověřený stav implementace

## 35.1 Význam a autorita registru

Tato kapitola je evidenční snapshot skutečného kódu, nikoliv další registr produktových rozhodnutí. Aktuální audit k **12. 9. 2026** je ukotven v `buuk` na `08a29074250675a61434ba58fb42a185474648d5` (PR #720). Jednotlivé IMP popisují historický okamžik svého vzniku; aktuální souhrn a překonaná omezení jsou v 35.29–35.31. Dřívější IMP-020–021 jsou již součástí `buuk`, nikoliv čekající feature větev. Pro živější implementační přehled a přesné další zadání slouží repo `CURRENT_STATE.md`; změna implementace nikdy sama nemění produktové rozhodnutí.

Za implementované se zde považuje pouze přesně vymezené chování, které je:

1. sloučené do uvedené cílové branche,
2. dohledatelné konkrétním PR a Git stromem,
3. ověřené relevantními testy nebo přímou kontrolou kontraktu,
4. zapsané včetně známých hranic a technického dluhu.

Lokální commit, otevřený PR, návrh dalšího řezu ani samotná existence podobně pojmenovaného legacy kódu nestačí. Stejně tak implementační default nevytváří produktový canon. Není-li oblast v této kapitole uvedená, její implementační stav je pro v63 **neauditovaný**, nikoliv automaticky neexistující. U jednotlivých IMP se rozsah popisuje k okamžiku jejich merge; pozdější řez může odstranit dřívější omezení. Aktuální souhrnná hranice je v 35.29–35.31; 35.20 zachovává starší mapu zápasového základu.

## 35.2 IMP-001 – kanonický prázdný kořen Runu

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #670 – Create canonical empty product Run root](https://github.com/Jasmetk0/squash-tour-beta/pull/670) sloučený do `buuk` merge commitem `2e155d2bd134c24bfe2cfe0ff1ec1732d0ce4451`. GitHub feature commit `8543842` a původní lokální commit `a7d4450` mají totožný strom `6976ae25bd65fbde32b0e47c25aab00ce549d3d3`.

Ověřený rozsah:

- `POST /run-containers` vytvoří nový produktový Run pouze z jedinečného neprázdného zobrazovaného názvu; ostatní obsah uživatel při založení zadávat nemusí,
- `GET /run-containers` a `GET /run-containers/{run_id}` poskytují seznam a detail uložených kanonických Runů, takže identita a prázdný stav přežijí restart databázového spojení,
- engine přidělí stabilní `run_id`, uloží lifecycle stav `Working` a hranice padesátileté historie `2000/01–2049/50`,
- v téže transakci vznikne právě jedna počáteční branch, její prázdný branchový stav a nastavení této branche jako Viewer Branch,
- nevytvářejí se Packages, hráči, turnaje, kalendář ani simulační výsledky,
- kolize názvu se kontroluje také proti archivovaným Runům a neúspěch uprostřed zápisu provede úplný rollback,
- persistence bezpečně otevře i starší podporované SQLite schéma, které dříve vyžadovalo `world_id`, aniž by nový prázdný Run nutilo vymyslet World Package,
- nové veřejné API používá produktový pojem `viewer_branch_id`; starší interní sloupec a kompatibilní rozhraní `official_branch_id` zatím zůstávají jako vědomá migrační vrstva.

Hlavní kód řezu leží v `src/beta_engine/application/run_container_creation_service.py`, `src/beta_engine/infrastructure/db/models.py`, `src/beta_engine/infrastructure/db/repositories.py` a `src/beta_engine/api/routers/run_containers.py`. Při PR prošly cílené Run/Branch/persistence testy, smoke sada `17/17` a GitHub Fast CI.

Hranice: automatický zobrazovaný název první branche `Timeline 1`, původně pouze technický default tohoto PR, je od v52 samostatně potvrzeným produktovým pravidlem. Tento PR sám ještě nezaváděl obecnou Saved Revision/Working Draft vrstvu; tu přidává až `IMP-002`. Oba řezy jsou backendové a nepřidávají finální frontendové obrazovky správy Runů.

## 35.3 IMP-002 – počáteční Saved Revision a čistý Working Draft

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #671 – Establish initial Saved Revision boundary](https://github.com/Jasmetk0/squash-tour-beta/pull/671) sloučený do `buuk` merge commitem `1db1e8266375d6c5ffc39ed887e7094f07842068`. GitHub feature commit `a605a40` a původní lokální commit `5a8e5f0` mají totožný strom `93c3d158f7f273945d84d6e80205b9a4fcce343e`.

Ověřený rozsah:

- vytvoření nového Runu nyní ve stejné atomické transakci přidá neměnnou počáteční `Saved Revision` se sekvencí `1` a bez rodičovské revize,
- počáteční Viewer Branch má tuto revizi jako svůj uložený head a současně dostane právě jeden čistý `Working Draft`, jehož base odpovídá první revizi a který neobsahuje neuložené změny,
- revision payload zachycuje celý podporovaný prázdný bootstrap stav a výslovně nevytváří checkpoint, simulační snapshot, Package snapshot ani sportovní obsah,
- obsahový hash chrání celý neměnný revision envelope včetně identity Runu, branche, pořadí, lineage, druhu, schema verze, payloadu a souhrnu změn,
- načtení revision state je fail-closed: před vrácením dat ověří identity, vlastnictví, pořadí a druh první revize, hash i soudržnost Working Draftu; poškozený či vzájemně nesouvisející stav odmítne,
- migrace přidá potřebné tabulky starší databázi, ale starým Runům zpětně nevymýšlí počáteční Saved Revisions, které historicky nevznikly,
- jakýkoliv konflikt nebo vložené selhání vrátí celou tvorbu Runu, branche, stavu, revize i draftu zpět.

Hlavní doménový kontrakt je v `src/beta_engine/domain/run_revisions.py`; aplikační a persistence hranice navazují v creation service a repository z `IMP-001`. Při PR prošel dotčený kontrakt `35/35`, smoke sada `18/18`, kompilace, kontrola diffu a GitHub Fast CI. Dvě chyby objevené při širším běhu byly samostatně reprodukované už na nezměněném předchozím `buuk`, proto se nevydávají za regrese těchto dvou PR ani za důkaz kompletně zelené celé sady.

Hranice: současné draft schema úmyslně umí pouze čistý prázdný bootstrap draft. Obecná reprezentace neuložených změn, běžné `Uložit → nová Saved Revision + Audit Event`, částečné ukládání logických balíčků, recovery a restore workflow tím ještě nejsou implementované.

## 35.4 IMP-003 – běžná branch z libovolné Saved Revision

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #672 – Create Run branches from Saved Revisions](https://github.com/Jasmetk0/squash-tour-beta/pull/672) sloučený do `buuk` merge commitem `972d163c2fb2a4146c998717124840f9a9722a4c`. GitHub feature commit `f279124` a původní lokální commit `e9a9b47` mají totožný strom `c94826b2ae9ca81b9f7ce45729f71a926f4c0081`.

Ověřený rozsah:

- nové API `POST /run-containers/{run_id}/branches` přijímá `source_branch_id`, `source_saved_revision_id` a volitelný `display_name`,
- zdrojová Saved Revision může být současný head i starší revize ve skutečné historii zvolené source branche; cizí Run, revize mimo její lineage, cyklus, poškozený hash nebo nesoudržné ownership údaje se odmítnou bez mutace,
- nová branch dostane stabilní `branch_id`, uložený bezprostřední původ `forked_from_branch_id`, přesný bod `forked_from_saved_revision_id` a stejnou existující revizi jako svůj počáteční `saved_head_revision_id`,
- společná neměnná minulost se neduplikuje: fork nevytváří druhou Saved Revision, checkpoint ani legacy simulační namespace; nová branch vlastní pouze samostatný čistý Working Draft založený na vybrané revizi,
- vytvoření další branche nikdy samo nepřepne `viewer_branch_id`; dosavadní Viewer Branch i její uložený stav zůstanou beze změny,
- počáteční branch se jmenuje `Timeline 1`; další automatický návrh vyplní první nepoužitý přesný název `Timeline N`, vlastní název se před zápisem ořízne a uvnitř Runu musí zůstat jedinečný,
- nested fork správně uchová bezprostřední source branch i tehdy, když více branchí sdílí stejnou fyzicky uloženou revizi,
- vytvoření celé branch/draft dvojice je atomické; kolize identity či názvu a vložené pozdní selhání provedou úplný rollback,
- kompatibilní migrace doplní lineage pole a Run-scoped ochranu názvů, aniž by svévolně přejmenovávala již existující legacy branche; načtení po restartu zachová stejný kanonický stav.

Hlavní doménová a aplikační hranice jsou v `src/beta_engine/domain/run_branches.py` a `src/beta_engine/application/run_branch_creation_service.py`; persistence a API navazují v repository, DB modelu a routeru Run containers. Při PR prošlo `66/66` cílených Run/Branch/API testů, smoke sada `19/19`, samostatný Viewer-context regresní soubor `19/19`, Ruff, format check, kompilace, kontrola diffu a GitHub Fast CI. Jeden serverový startup timeout v širším lokálním dávkovém běhu se v přesném testu ani při opakování celého příslušného souboru nereprodukoval; úplná repository sada 1 443 testů nebyla znovu spuštěna a dvě dříve známá nesouvisející selhání základní větve se nevydávají za opravená.

Hranice: tento řez nepřenáší rozpracovaný Working Draft do nové branche, nevytváří obecné změnové balíčky, neimplementuje běžné `Uložit`, Audit Event, restore, přepínání Viewer Branch, archivaci, popis či pozdější přejmenování branche, frontend ani slučování rozdílných historií. Fork draft používá úzké schéma čistého draftu založeného na Saved Revision; obecný draftový obsah zůstává implementačně otevřený.

## 35.5 IMP-004 – první skutečný Working Draft → Save cyklus

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #673 – Save Viewer Branch changes through Working Drafts](https://github.com/Jasmetk0/squash-tour-beta/pull/673) sloučený do `buuk` merge commitem `17db035ff66f7825ba857bf68a86d255152468b1`. GitHub feature commit `16c9a3c09e1ef32f73194521e91292855b30b32b` a původní lokální commit `30998fa` mají totožný strom `e5ad044c6ab258d09ea42efe7e26640edde7f948`.

Ověřený rozsah:

- první podporovaný skutečný draftový změnový balíček `set_viewer_branch` je explicitní, verzovaný a nese právě jeden atomický záměr: která aktivní branch téhož Runu se má po uložení stát Viewer Branch,
- `GET /run-containers/{run_id}/branches/{branch_id}/working-draft` vrací uloženou i navrhovanou Viewer Branch, čistý/špinavý stav, počet změn, verzi draftu a odvozené `can_save`; `PUT .../working-draft/viewer-branch` změnu pouze stageuje a návrat k uložené hodnotě draft znovu vyčistí,
- pouhé stageování nikdy nemění Viewer: `runs.official_branch_id` zůstává do potvrzeného Save pouze kompatibilním úložištěm dosavadního kanonického `viewer_branch_id`,
- `POST .../working-draft/save` v jediné transakci vytvoří novou neměnnou Saved Revision, append-only Audit Event, přepne Viewer Branch, posune uložený head editované branche a tentýž Working Draft resetuje na čistý stav založený na nové revizi,
- opakované Save zachovává souvislou lineage a sekvence `1 → 2 → 3`; první Save ve forknuté branchi vytvoří její vlastní child revizi nad sdíleným bodem historie, aniž by duplikoval zděděnou minulost,
- optimistická kontrola `expected_draft_version` odmítne zastaralého klienta; cizí Run, chybějící nebo neaktivní cílová branch, read-only stav, poškozený hash či lineage, nepodporovaný změnový balíček a kolize generované identity se odmítnou bez částečné mutace,
- pozdní chyba až při zápisu Audit Eventu vrátí zpět novou revizi, Viewer pointer, branch head i reset draftu, takže Save hranice je skutečně atomická,
- kompatibilní bootstrap přidá tabulku `branch_revision_audit_events` také existující podporované databázi a zachová její dosavadní Run, Saved Revision i Working Draft.

Hlavní aplikační hranice je v `src/beta_engine/application/run_working_draft_service.py`; doménový payload a hashing v `src/beta_engine/domain/run_revisions.py`; persistence, schema a API navazují v repository, DB modelech a routeru Run containers. Při PR prošla kompilace, Ruff kontrola dotčených ploch, zaměřená sada `13/13`, širší Run/Branch/persistence/API sada `169/169`, smoke sada `20/20` a GitHub Fast CI. Plný běh odhalil již existující calendar-builder HTTP 400 selhání; první přesný případ byl reprodukován beze změny také na předchozím čistém `buuk` `972d163`, a není proto vydáván za regresi ani opravu tohoto řezu.

Hranice: tento řez podporuje pouze `set_viewer_branch`; nejde ještě o obecný katalog draftových změn ani pokročilé částečné ukládání více logických balíčků. Veřejné API zatím neumí vypsat úplnou dosažitelnou historii Saved Revisions, načíst historický revision payload podle Run/Branch kontextu ani číst Audit Eventy. Recovery, restore, Undo/Redo relace, archivace, frontend a migrace legacy simulačního obsahu zůstávají mimo tento PR.

## 35.6 IMP-005 – validovaná read-only Saved Revision History

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #674 – Expose validated Saved Revision history](https://github.com/Jasmetk0/squash-tour-beta/pull/674) sloučený do `buuk` merge commitem `1166aa52682e6091f43c469f52b9267716f89c2b`. GitHub feature commit `a511a287f9b79380260e7c8d7dcd8ade12e683e5` a původní lokální commit `1b7d942cc6697ed3c372e5baaeb45515f89e4330` mají totožný strom `04990ae31b9e071663bcb76b42245f0c52eb2bc9`.

Ověřený rozsah:

- `GET /run-containers/{run_id}/branches/{branch_id}/saved-revisions` vrací úplnou Saved Revision lineage dosažitelnou z uloženého headu vybrané branche, deterministicky od nejstarší revize k nejnovější,
- historie obsahuje také fyzicky sdílenou minulost před forkem; metadata každé položky výslovně rozlišují sdílenou revizi a současný head vybrané branche,
- `GET /run-containers/{run_id}/branches/{branch_id}/saved-revisions/{revision_id}` načte neměnný revision detail pouze tehdy, když je revision skutečně dosažitelná v zadaném Run/Branch kontextu; jinou revizi skryje scopeovaným `404`,
- vrácené `revision_id` lze bez interního přístupu k persistence přímo použít jako `source_saved_revision_id` existujícího `POST /run-containers/{run_id}/branches`, takže workflow historického forku je uzavřené přes veřejné API,
- čtení fail-closed ověřuje Run/Branch ownership, identity každého payloadu, obsahový hash, parent a sequence kontinuitu, cyklus i deklarovaný společný fork origin; nesoudržná uložená lineage končí konfliktem `409`,
- list ani detail nemutují Viewer Branch, branch head, Working Draft, Saved Revisions ani Audit Eventy.

Hlavní aplikační hranice je v `src/beta_engine/application/run_saved_revision_history_service.py`; doménový revision kontrakt, persistence a API navazují v již existujících Run revision, repository a router vrstvách. Při PR prošla kompilace, Ruff kontrola a formátování nových ploch, zaměřená history sada `6/6`, smoke sada `21/21`, širší Run/Branch/checkpoint/Viewer/API regresní sada `185/185` a GitHub Fast CI run `#811`. Přesný vzdálený strom odpovídá lokálně testovanému stromu uvedenému výše. Již známá nesouvisející calendar-builder HTTP 400 selhání základní větve nebyla tímto řezem měněna ani vydávána za opravená.

Hranice: tento řez je pouze read-only. Nezavádí stránkování velkých historií, obnovení současné branche ze starší revize, porovnávací UI, veřejné čtení Audit Eventů, recovery, nové typy Working Draft změn, frontend ani migraci legacy simulačního obsahu.

## 35.7 IMP-006 – bezpečné obnovení Saved Revision a první Admin historie

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #675 – Add guarded Saved Revision restore workflow](https://github.com/Jasmetk0/squash-tour-beta/pull/675) sloučený do `buuk` merge commitem `369ea5074129b8dc84d7c06ba78e2313b265c113`. GitHub feature commit `e0c7a18e9201c1236c7acd1426250bb10fca3ef3` a původní lokální commit `3e589b9706e91aa15e3d3329ae2d4e3f84383965` mají totožný strom `f8b0e5bb9c8585b0c7da34198aa116739a78f4e6`.

Ověřený rozsah:

- nové potvrzené API obnovení přijímá přesný očekávaný Saved Revision head, verzi Working Draftu a současnou Viewer Branch; zastaralý preview, špinavý draft, změněný Viewer kontext, cizí identita, poškozená lineage nebo chybějící výslovné potvrzení skončí bez částečné mutace,
- cílem může být pouze validovaná starší Saved Revision dosažitelná v historii zvolené branche; současný head se znovu obnovit nedá,
- před změnou engine ve stejné transakci vytvoří hashově chráněný samostatný `pre_restore_saved_revision` checkpoint odkazující na stav těsně před obnovou,
- restore nemaže ani nepřepisuje předchozí revize: vytvoří novou neměnnou Saved Revision jako další child dosavadního headu, přidá append-only Audit Event, atomicky přepne podporovaný Viewer stav a resetuje Working Draft na nový čistý základ,
- pozdní chyba při checkpointu, revizi nebo auditu vrátí celý zápis zpět; nejistá chyba klienta se automaticky neopakuje,
- současný pre-alpha restore fail-closed podporuje pouze stav kompletně zachycený současným revision payloadem; sporting, Package, config, seed a legacy checkpoint/run stav je výslovně blokovaný, dokud jej Saved Revision neumí bezeztrátově obnovit,
- Admin stránka Branches nyní zobrazuje úplnou historii zvolené branche, read-only detail revize, změnový souhrn i payload; samotné otevření nic nemutuje,
- ze stejného preview lze vytvořit novou branch bez změny Viewer Branch nebo otevřít výrazný restore dialog vyžadující přesnou potvrzovací frázi a checkbox; UI před odesláním ověří čistý draft a zachycené concurrency údaje,
- neúspěšný restore zavře potvrzení, obnoví dotčené read modely a vyžádá nové ruční posouzení místo automatického retry.

Hlavní aplikační hranice je v `src/beta_engine/application/run_saved_revision_restore_service.py`; doménový kontrakt, hashování checkpointu, atomická persistence a API navazují v revision doméně, repository, DB modelech a routeru Run containers. První Admin UI je v `web/src/components/SavedRevisionHistoryPanel.tsx`. Po finálním rebase na tehdejší `origin/buuk` prošlo `57/57` relevantních backendových a `137/137` cílených frontendových testů, TypeScript projektová kontrola a produkční Vite build. Vzdálený Git strom byl před vytvořením PR porovnán s lokálně testovaným stromem; větev byla jeden commit před a nula commitů za `buuk`. Širší frontendová sada nadále obsahovala nesouvisející Viewer chyby, z nichž reprezentativní CSS architecture selhání bylo shodně reprodukováno na čistém cílovém `origin/buuk`.

Hranice: nejde ještě o restore kompletního sporting ani legacy simulačního stavu. Safety checkpoint je uložený a hashově ověřitelný, ale nemá samostatný veřejný browser; odpovídající branch revision Audit Eventy také dosud nemají veřejné read-only API. Obecný Compare States, recovery draft, Undo/Redo relace, stránkování, archivace a úplný Audit Log zůstávají mimo tento PR.

## 35.8 IMP-007 – validovaná read-only Saved Revision recovery activity

**[IMPLEMENTOVÁNO A OVĚŘENO]** V uvedeném rozsahu je [PR #676 – Expose Saved Revision recovery activity](https://github.com/Jasmetk0/squash-tour-beta/pull/676) sloučený do `buuk` merge commitem `8db6fc6eef2c21b897627b18578eadaed2bb9029`. GitHub feature commit `532e9a0037d77ea302ce79f99b64f692042acc23` má stejný výsledný strom `3fda975634dfc3d97c8ba7cd8cd23008a7507928` jako sloučený stav.

Ověřený rozsah:

- nové read-only API vrací recovery aktivitu zvolené branche: existující `pre_restore_saved_revision` checkpointy a související branch revision Audit Eventy,
- před vrácením ověřuje úplnou dosažitelnou Saved Revision lineage, identity, obsahové hashe a přesné párování restore checkpointu s odpovídajícím restore Audit Eventem; poškozený, cizí či nespárovaný stav končí fail-closed,
- pořadí je deterministické podle Saved Revision sequence, nikoliv podle UUID nebo timestampu,
- Admin zobrazuje pre-restore head, restore target/result, tehdejší Viewer/Draft kontext a checkpoint hash,
- otevření checkpointu pouze zobrazí původní Saved Revision v již existujícím read-only preview; samo nic nemutuje a případný návrat nadále používá potvrzený restore workflow z `IMP-006`.

Relevantní ověření zahrnovalo `60/60` backendových regresních testů, `23/23` smoke testů, `138/138` cílených frontendových testů, TypeScript kontrolu a produkční Vite build. Vzdálený Git strom byl porovnán s testovaným stromem.

Hranice: nejde o úplný Audit Log, obecný checkpoint browser, Compare States ani nový restore mechanismus. Řez zpřístupňuje pouze přesně párovanou recovery aktivitu existujícího Saved Revision restore kontraktu a nerozšiřuje dosud nepodporovaný sporting/legacy restore scope.

## 35.9 IMP-008 – Effective Match Format Snapshot

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #677](https://github.com/Jasmetk0/squash-tour-beta/pull/677), sloučen 31. 8. 2026; merge `42832a2a01137dafd392471135c0b1df9ce2e6a7`.

- `MatchFormat` je atomická trojice `best_of / games_to / win_by`; oficiální fallback je `BO5 / 11 / 2`.
- Resolver používá nejbližší celý override `round → phase → Tournament Edition → official fallback`. Nezavádí jinou skrytou hierarchii Match Formatu ani skládání jednotlivých polí z různých úrovní.
- Materializovaný zápas ukládá efektivní formát, jeho původ a SHA-256 kontrolu. Simulace používá tento uložený snapshot, nikoliv pozdější živou konfiguraci turnaje.
- Balíček obsahující dokončený zápas nelze přegenerovat; navazuje odpovídající TypeScript API kontrakt.

Hranice: jde o uložený formát a ochranu současného match package. Samotný řez nedokazuje plný interaktivní lock rozpracovaného zápasu od první rally, obecný editor dědičnosti ani audit všech turnajových změn. Při PR prošlo 57 relevantních backendových testů; dřívější API calendar/build HTTP 400 je oddělený baseline problém.

## 35.10 IMP-009 – neměnný Match Input Snapshot

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #678](https://github.com/Jasmetk0/squash-tour-beta/pull/678), sloučen 31. 8. 2026; merge `fbaeeda9a6f5106ba86589b083ec989a0d5e3186`.

- První `match_input_snapshot.v1` ukládá přesné tehdejší hráče a jejich podporované atributy, match context/modifikátory, efektivní formát, seed a verzi enginu.
- Simulace spotřebuje tento vstup a fingerprint výsledku na něj odkazuje; pozdější změna hráče, formátu, seedu či kontextu nesmí tiše reinterpretovat historii.
- Vstup výslovně deklaroval tehdy nepodporované gameplany, rally konfiguraci a rally seed stream. Novější generace doplňují právě tyto vrstvy, ne zpětné domýšlení do historické v1.

Při PR prošlo 60 relevantních testů. Snapshot je základ historické pravdy, ale samotný seed a snapshot nejsou náhradou uloženého eventového Replaye ani obecným slibem spustitelnosti každé staré verze enginu v současném kódu.

## 35.11 IMP-010 – autoritativní Rally Log a uložený Replay

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #679](https://github.com/Jasmetk0/squash-tour-beta/pull/679), sloučen 1. 9. 2026; merge `dfabf3d6918b9059b1fe8e085f5f4c6837463673`.

- Match Engine v2 přestal zahazovat skutečně simulované bodové rally. Každý event ukládá skóre před/po, servera, vítěze, terminální trigger, oddělené analytické připsání, seřazené score mutations, abstraktní detail, odhad úderů a aktivní čas.
- Kompaktní Post-Rally State Snapshot a SHA-256 řetězec ukotvený v Match Input Snapshotu propojují rally, game a celý výsledek. Rally seed se v API přenáší jako přesný desetinný řetězec bez ztráty přesnosti v JavaScriptu.
- `GET /admin/matches/{event_id}/replay/{match_id}` vrací uloženou pravdu bez spuštění Match Enginu nebo RNG. Test Replaye záměrně znemožní nové simulování a čtení přesto funguje.
- Tournament Result používá kanonickou JSON serializaci pro SQLite round-trip. Rankingový `CompletedTournamentPointsInput` má kompaktní výsledkové podklady a neduplikuje celý rally log.
- Match Input Snapshot se posunul na v2; historická v1 zůstala čitelná.

Při PR prošlo 83 cílených testů. Dvě skutečné persistence regrese `tuple → JSON list` byly opraveny před předáním; sedm ostatních širších selhání bylo reprodukováno na čistém base. Tehdejší rally log byl pouze bodový a bez úplné timeline; tyto hranice postupně odstraňují IMP-011–017. Řez nepřidal Step Back/Forward UI, Auto Play ani průběžný databázový commit každé rozehrané rally.

## 35.12 IMP-011 – autoritativní časová osa zápasu

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #680](https://github.com/Jasmetk0/squash-tour-beta/pull/680), sloučen 1. 9. 2026; merge `cc7730690116153f1c099b0b0502887f644a17aa`.

- `effective_match_timing.v1` je součástí hashovaného input snapshotu v3; Match Engine přechází na v3.
- Časová osa obsahuje odkazy na rally, běžné mezi-rally intervaly a samostatné přestávky mezi gamy. Zápas už má celkový čas, nejen součet aktivních výměn.
- Běžná mezera je maximum připravenosti servera, receivera, rozhodčího a kurtu. Ukládá role-specific restart intents, vysvětlující faktory, jednotlivé readiness složky, dominantní příčinu, seed a hash.
- Hráči mají odlišné tendence na podání a returnu. Časování používá oddělenou RNG větev. V samotné v3 ještě neměnilo skóre; od IMP-013 jej může kauzálně změnit přes recovery.
- Game break má Official default 120 sekund a nahrazuje běžnou mezeru, takže se čas nezdvojuje. API dovoluje timing override konkrétní simulace.
- Finální hash chrání celou timeline a uložený Replay ji pouze čte. Starší rally-only výsledky bez timeline zůstávají podporované.

Při PR prošlo 37 match/input/timeline/application a 19 progression/persistence testů. Tehdejší vzorek 12 333 běžných mezer měl průměr 13,03 s a 98,8 % v koridoru 8–18 s; jde o výstup dané kalibrace, ne nový sportovní předpis. Proměnlivá skutečná délka game breaku, plná situační restart AI, rhythm disruption, prompt/warning/Conduct Stroke a zdravotní přestávky tím nejsou hotové. Objektivní přerušení doplňuje až IMP-017.

## 35.13 IMP-012 – dynamická fyzická stamina a její historie

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #681](https://github.com/Jasmetk0/squash-tour-beta/pull/681), sloučen 2. 9. 2026; merge `3531fc9d56690f5935f6ea8f4391d9c7835c544a`.

- Match Engine/input v4 přidaly tři dynamické bary `Explosive / Rally / Match Stamina` a verzovanou kalibraci `pre_alpha_physical_v1`.
- Individuální kapacity, počáteční naplnění, cena workloadu a recovery vycházejí z dostupných fyzických atributů a fatigue/health/travel modifikátorů. Nevznikají tři nové ručně authorované schopnosti.
- Po rally se odečte workload odvozený z času, odhadu úderů a segmentů. Běžný interval i game break obnovují oba hráče za stejný autoritativní čas právě jednou; obnova nepřekročí osobní kapacitu a přestávka bary neresetuje.
- Hashovaný MatchStaminaLog navazuje na finální timeline hash, ukládá stavy po časových událostech a ověřuje reference, kalibraci i počáteční stav při Replayi.

Při PR prošlo 64 cílených testů; širší domain běh měl 270 průchodů a čtyři známá rankingová selhání. V této historické v4 byla stamina observační; skutečný vliv na výkon přidává IMP-013. Přenos konkrétních rezerv mezi zápasy, drobná explosive recovery uvnitř rally a injury-specific cost profily zůstávají neimplementované i po IMP-017.

## 35.14 IMP-013 – kauzální vliv stamina na výkon rally

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #682](https://github.com/Jasmetk0/squash-tour-beta/pull/682), sloučen 2. 9. 2026; merge `729afaf047ca95edc723ff26224272339f631953`.

- Match Engine/input v5 a `pre_alpha_physical_v2` používají živou stamina před rally, až hotová rally odebere workload a následný skutečný interval obnoví oba hráče.
- Nízké rezervy působí spojitě a nelineárně; vysoká rezerva má malý efekt, propad se zrychluje při vyčerpání a nula neznamená automatickou prohru bodu.
- První implementace používá omezený physical strength penalty, nikoliv hotovou úplnou mapu všech 57 atributů na pohyb a přesnost. Tehdejší deficit váží Explosive 45 %, Rally 35 %, Match 20 %; nízká Match Stamina navíc zhoršuje účinnost obnovy.
- Rally Event v2 ukládá fill ratios, deficit, penalty a pravděpodobnost A před/po fyzickém vlivu; validace porovnává záznam s autoritativním stavem před příslušnou rally.
- Starý recovery bonus podle počtu bodů byl odstraněn, aby se obnova nepočítala podruhé. Čas tak může ovlivnit další výsledek, ale oba hráči odpočívají současně.

Při PR prošlo 71 cílených testů a 274 domain testů; zůstala stejná čtyři baseline selhání. Tehdejší kontrola 2 548 rally vykázala průměrný absolutní posun 1,32 procentního bodu, maximum 5,00 p. b.; proti observačnímu modelu se u 300 stejných seedů změnil vítěz 20 zápasů. Čísla jsou historický kalibrační výsledek, nikoliv finální matematika nebo záruka pro následující generace.

## 35.15 IMP-014 – individuální úsilí a asymetrický workload

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #683](https://github.com/Jasmetk0/squash-tour-beta/pull/683), sloučen 2. 9. 2026; merge `361a83322e4251cc6c9bfc32a61575ccf66af527`.

- Match Engine/input v6, Rally Event v3 a `pre_alpha_physical_v3` přidaly před-rally volbu `CONSERVE / NORMAL / INCREASED / MAXIMUM` pro každého hráče zvlášť.
- AI vychází ze stylu, skóre, nedokonalého odhadu vlastní rezervy a reprodukovatelné taktické variace. Požadovaná a skutečně provedená intenzita jsou odlišné: fyzický stav může realizaci omezit.
- Provedená intenzita má mírný omezený účinek na výkon a současně energetickou cenu. Konzervativní úsilí energii šetří za cenu výkonového kompromisu.
- Workload každého hráče skládá skutečný průběh rally, provedené úsilí, pohybovou efektivitu, pracovní profil stylu a tlak. Oba hráči nemusejí za stejnou rally zaplatit stejně.
- Hashovaný effort kontext ukládá důvody volby, odhad rezervy, multipliers a individuální workload. Stamina Transition v2 jej porovnává s rally i živým stavem.

Při PR prošlo 89 cílených testů a 280 domain testů, čtyři známé rankingové testy dál selhávaly. Finální vzorek tohoto PR: 2 639 rally, průměrný absolutní effort posun 0,70 p. b., maximum 3,71 p. b., průměrný poměr vyššího/nižšího workloadu 1,20× a změna vítěze u 10/300 párových seedů. Dřívější průběžná čísla z chatu nejsou finální výsledky tohoto commitu. Změny úsilí uvnitř rally doplnil až IMP-015; PAQ-113 se samotnou implementací neuzavírá.

## 35.16 IMP-015 – jeden kauzální skrytý průběh rally

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #684](https://github.com/Jasmetk0/squash-tour-beta/pull/684), sloučen 4. 9. 2026; merge `5a45745d15a184ced114a88c1079be1e9afef89b`.

- Match Engine/input v7 vytvářejí jeden trace `opening → 0–24 control segmentů → terminal`. Pět stavů kontroly má setrvačnost, běžné lokální posuny a vzácné silné obraty.
- Podání ovlivní opening, ne trvalý server bonus. Rally může skončit podáním či prvním returnem bez control segmentu. Segment představuje fázi, nikoliv jeden úder.
- Tentýž průběh vytváří kontrolu/tlak, tempo, odhad úderů, aktivní čas, terminální sportovní výsledek a individuální workload; detail není zpětná kosmetická rekonstrukce podle vítěze.
- Hráči mohou v segmentech upravovat úsilí podle vnímané rezervy, kontroly, tlaku a taktiky. Současná kalibrace omezuje jednu segmentovou změnu úsilí na sousední stupeň. Neznají budoucí terminal.
- Match Input Snapshot v7 hashově chrání numerický RallyCalibrationProfile, včetně přechodů, closure a distribucí tempa/úderů/času. Event a log v4 chrání trace; stamina používá `effective_match_stamina.v3`, `match_stamina_log.v3` a `pre_alpha_physical_v4`.
- Nové verze mají přísnou kontinuitu schémat i rozhodovacích údajů; staré replaye respektují svůj historický kontrakt. Prázdný výsledek podporované před-rally cesty také nese odpovídající generaci logů.

Při PR prošlo 61 cílených a 23 smoke testů; širší doména měla 290 průchodů a čtyři známá rankingová selhání. Finální deterministický vzorek 1 200 rally: medián 13 úderů, p75 21, p95 34, medián aktivního času 12,362 s a průměr 14,298 s; 8,417 % opening terminals, 96,659 % setrvání/lokálních přechodů a 0,034 % přímých strong-A/strong-B obratů. Jde o výstup této konkrétní pre-alpha kalibrace, nikoliv nové naměřené PSA statistiky nebo závazný moderní p95. Úplná geometrie úderů a reálná empirická kalibrace zůstávají další práce.

## 35.17 IMP-016 – Active Gameplan V1

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #685](https://github.com/Jasmetk0/squash-tour-beta/pull/685), sloučen 4. 9. 2026; merge `41151cfe80d2465961f8337158f9a88d06134526`.

- Match Engine/input v8 ukládají `effective_match_gameplans.v1 / pre_alpha_gameplan_v1`: individuální Natural Style Profile se současnými osami `Risk / Tempo / Court Positioning / Variation`, familiarity, adaptability proxy, nepřesný odhad soupeře a počáteční plán.
- Plán obsahuje záměr, mechanismus, časový horizont, confidence, práh přehodnocení a očekávaný payoff. AI volí `OWN_STRENGTH / COUNTER_ESTIMATE / DELAYED_PAYOFF` a před další rally rozhoduje `START / STICK / ADAPT` pouze z dosavadních pozorování.
- Hráč může vědomě setrvat při dočasném neúspěchu, čekat na pozdější přínos, přecenit svůj plán nebo chybně přečíst soupeře. Counter není povinná okamžitá reakce na prohraný úsek a není automaticky úspěšný.
- Oba hráči vyhodnotí stejný pre-rally stav ještě před aplikací nových plánů. Znalost stylu a skutečné schopnosti omezují provedení; plán působí přes kontrolu, phase pace, closure pressure a workload, ne přímým bonusem za údajně správný counter.
- Původní kategorický style matchup bonus se při aktivním gameplanu vypíná, aby se nepočítal dvakrát. Samostatná legacy archetype interakce zatím zůstává.
- Rally Event/log v5 ukládají revize plánů, důvody rozhodnutí i kauzální účinky; ADAPT zvyšuje revizi právě jednou a STICK ji zachová. Hash i návaznost revizí jsou kontrolované, Replay neprovádí dnešní AI znovu.

Současná implementační omezení: Natural Style se zatím deterministicky materializuje z legacy `play_style`, nejde o trvale authorované a kariérně vyvíjené spojité profily. Adaptability používá dočasnou mental/consistency proxy; plná 57atributová Style Execution, Match Preparation, scouting/H2H paměť, mentální bary a samostatná osobnost/tvrdohlavost nejsou hotové vstupy. Tyto proxy nejsou novým canonem a musí být později nahrazeny verzovaně.

Při PR prošly cílené match/gameplan/replay testy, čistý backend smoke běh, 272 kritických frontendových testů, TypeScript produkční build, Ruff, compileall a GitHub CI. Detailní technický popis je v `docs/ACTIVE_GAMEPLAN_V1.md`; jeho v8/v5 označení popisuje okamžik zavedení, současná obálka je novější podle 35.19.

## 35.18 IMP-017 – Rally Rules Resolver V1, Yes Let a objektivní přerušení

**[IMPLEMENTOVÁNO A OVĚŘENO]** [PR #686](https://github.com/Jasmetk0/squash-tour-beta/pull/686), sloučen 7. 9. 2026 v 22:48:54 UTC; merge `92981287be4a10f07640e0aaa6a2f49eeb18e5ed`. Finální feature commit `b95996681ce9e4a295c40296d117b197b7368bd3` a lokálně testovaný commit `729817f` mají shodný Git strom `3a6e553494da0374ba46638f813eb6972eead9ae`.

- Nový čistý resolver v `src/beta_engine/domain/matches/rally_rules.py` přijímá diskrétní ground-truth fakta a bez RNG určuje `POINT_AWARDED / NO_LET / YES_LET / STROKE`, příjemce bodu nebo replay a decision code.
- Fakta interference rozlišují výhled, přístup, prostor pro rozumný švih a přední stěnu, good/winning return, clearing/striker effort, vlastní špatnou cestu, wrong-footed recovery, minimální interference, pokračování, excessive swing, turning a first/further attempt. Rozporné kombinace jsou odmítnuty; minimální interference nesmí současně tvrdit zablokovaný výhled, švih nebo svobodu přední stěny.
- Zásah hráče míčem rozlišuje zasaženého hráče, míč od/před přední stěnou, direct/via-wall, good/winning return, pokus, turning a úmyslné zachycení. U vracejícího se míče jsou správně použity role přijímajícího hráče. Stroke nepřipadne automaticky vždy strikerovi; rozhoduje konkrétní pravidlová větev.
- Historická verze je `world_squash_singles_2025_v1_2_2`, resolver `pre_alpha_rules_v1`. Initial a final call jsou odděleně uložené, ale v této pre-alpha stejné; náhodné chyby rozhodčího ani review se nesimulují.
- Yes Let má `winner_player_id = null`, žádnou bodovou mutation a zachová skóre, podávajícího i service box. Odehraná práce nezmizí. Při běžném bodu se box/podání mění podle příslušného pokračování, handoutu či nového gamu.
- Log odděluje `scoring_rallies` a `replay_rallies`; celkový počet výměn už nemusí odpovídat počtu bodů. Gameplan evidence vede let jako neutrálně pozorovanou rally, nikoliv jako výhru/prohru; pozorování jsou ověřena proti předchozím autoritativním eventům.
- Nezaviněný vnější incident v rozehrané rally vyvolá Yes Let a `OBJECTIVE_DELAY` s důvodem/délkou. Nahrazuje běžnou mezeru: elapsed je maximum objektivního zdržení a restart readiness; oba hráči mají právě jednu `OBJECTIVE_DELAY_RECOVERY` za tento skutečný čas.
- Match Engine/input v9 vyžadují hashovaný `effective_rally_rules.v1`; rally event/log přechází na v6 a timeline na v2. Společná validace živého i uloženého výsledku kontroluje pravidlové facts, verdict, skóre, podání, gameplan evidence a důvod/délku/účastníky navazující timeline.
- Rehashování upraveného záznamu samo nestačí obejít doménovou kontrolu. Nová pravidlová data nelze schovat pod starší číslo schématu. Historické v1–v8 vstupy a v1–v5 rally eventy zůstávají čitelné s původními hashovými pravidly.

**[IMPLEMENTAČNÍ KALIBRACE, NIKOLIV NOVÉ PRODUKTOVÉ ROZHODNUTÍ]** Situace vznikají z abstraktního terminal trace přes oddělený RNG stream. `pre_alpha_rule_situations_v1` používá základní interference pravděpodobnost 0,04 upravenou tlakem/pohybem, ball-hit 0,004 a external interruption 0,001. Generátor nyní vzorkuje krátká objektivní zdržení 30–90 s. Po osmi po sobě jdoucích replay rally guard potlačí vznik dalšího incidentu; nemění verdikt už vzniklé situace a není squashovým limitem počtu letů. Tato čísla nejsou naměřené profesionální četnosti ani závazné finální parametry.

Hranice: krátké opening konce podáním/prvním returnem a serve faulty zatím zůstávají běžnými konci bez nového samplingu incidentů. Jde o diskrétní abstraktní situace, nikoliv kolizní geometrii; odhad úderů není seznam skutečných kontaktů rakety. Přesnější délka konkrétního incidentu a doba rozhodcovské diskuse zůstávají další kalibrací. Nejsou implementované conduct escalation, health/procedural stops, dlouhé suspension/rescheduling, review ani referee errors. Časové rozmezí generátoru nevytváří práh pro Suspended; výslovně přeskočená otázka z kapitoly 17.8.3 zůstává otevřená v rámci již rozhodnutého širšího turnajového kontraktu.

Ověření finálního řezu: 141 cílených domain/application testů; 26 smoke testů z čistého worktree; Ruff, compileall a kontrola diffu. Skutečný fixture `tests/fixtures/matches/legacy_engine_v8.json` vznikl nemodifikovaným base commitem `41151cf` s jednobodovým testovacím formátem a načítá se bez rehashování či nového spuštění enginu. Fast CI #825 pro finální feature commit prošel backend smoke, frontend critical tests i frontend build. Širší doména: 363 passed / 4 failed; všechny čtyři stejné rankingové chyby byly znovu reprodukovány na čistém base. Podrobný implementační kontrakt je v `docs/RALLY_RULES_RESOLVER_V1.md`.

## 35.19 Současná schémata a historická kompatibilita

Tato tabulka popisuje nově vytvářený zápas po IMP-017, nikoliv povinnou migraci minulosti:

| Vrstva | Aktuální generace |
|---|---|
| Match Engine | `match_engine_v9` |
| Vstup zápasu | `match_input_snapshot.v9` |
| Rally event / log | `rally_event.v6` / `match_rally_log.v6` |
| Časová osa | `match_timeline_log.v2` |
| Efektivní timing | `effective_match_timing.v1` |
| Efektivní stamina / log | `effective_match_stamina.v3` / `match_stamina_log.v3` |
| Stamina transition | `stamina_transition.v2` |
| Fyzická kalibrace | `pre_alpha_physical_v4` |
| Gameplan | `effective_match_gameplans.v1` / `pre_alpha_gameplan_v1` |
| Pravidla | `effective_rally_rules.v1` / `pre_alpha_rules_v1` |
| Vznik pravidlových situací | `pre_alpha_rule_situations_v1` |
| Objektivní časová událost | `objective_delay_event.v1` |

Postupný vstup v1 → v9 doplňoval hráče/formát/seed, rally provenance, timing, observační staminu, stamina coupling, individuální effort, hidden control, gameplany a pravidla. Nová generace neznamená, že mají staré výsledky dostat nová pole přepočtem dnešního modelu. Historický Replay čte uložené eventy; legacy hash payloady nová pole nezahrnují. Nové schema generation a související logy se validují společně, včetně kontrol proti obcházení pouhým snížením verze obálky.

Finální `match_log_hash` chrání celý podporovaný řetězec rally → timeline → stamina a jeho vazbu na input. U staršího rally-only záznamu má rozsah daný tehdejším schématem; nelze mu připsat pozdější timeline, kterou historicky neměl. Read-only uložený Replay je odlišný od nového experimentálního rerunu: změna modelu či kalibrace může změnit nový výsledek i při stejném seedu, nikdy již uloženou historii.

## 35.20 Mapa hotového základu a zbývajících pre-alpha mezer

**Produktová otázka může být rozhodnutá a přesto dosud neimplementovaná; funkční první implementace zase nemusí uzavírat kalibraci.** Následující tabulka nemění statusy PAQ.

| Oblast / související PAQ | Co nyní funguje | Co tím není dokončeno |
|---|---|---|
| Match Format, PAQ-072 | Atomický override, provenance, snapshot a ochrana hotového match package | Plné editační UI a průběžný lifecycle rozpracovaného zápasu |
| Historie zápasu, PAQ-073 | Hashovaný vstup, eventy, čas, stamina, read-only Replay hotového uloženého výsledku | Databázový commit po každé rally, restart po pádu z poslední rally, pracovní větvení rozehraného zápasu, Step Back/Forward a Auto Play UI |
| Kontrola, opening, PAQ-064/065/069/070 | Jeden kauzální trace, 0–24 fází, krátké opening konce, pět stavů, tempo/údery/workload | Shot-by-shot geometrie, finální moderní empirický fit a úplná mapa všech atributů |
| Fyzický stav, PAQ-055/056 | Tři živé bary, náklady, recovery, nelineární výkonový vliv | Přenos konkrétních rezerv mezi zápasy, explosive recovery uvnitř rally, injury-specific cost profily; finální křivky zůstávají otevřené |
| Úsilí/gameplan, PAQ-113 | Individuální effort před i uvnitř rally, čtyřosé plány a jejich přehodnocení | Trvalé kariérní style profily, plná Adaptability/osobnost, příprava a scouting paměť; finální AI matematika |
| Mental state, PAQ-057 | Dosavadní dostupné atributy/proxy v aktuálním modelu | Dynamické Current Focus a Current Confidence a jejich úplné kauzální napojení |
| Restart a pauzy, PAQ-060/071 | Role-specific tendence/intents, readiness maximum, timing override, samostatný game break, recovery | Plná situační restart AI, rhythm disruption, variabilita game breaku, minimální prompt/warning/Conduct Stroke resolver |
| Pravidla, PAQ-067/068 | No Let / Yes Let / Stroke, ball-hit/turning/attempt flags, neutral replay a krátký external delay | Conduct, health/procedural stops a širší side incidents; přesná hranice a workflow dlouhého přerušení |
| Zdraví a nenormální konce | Stávající omezené cesty a vstupní health modifikátory | Celý health-check/medical/RET/DQ/ABN lifecycle; jediný prázdný nebo RET test není důkaz kompletního systému |
| Saved Revision backbone, IMP-001–007 | Prázdný Run, branch, draft/save, historie, guarded restore a recovery activity v podporovaném rozsahu | Automatické bezeztrátové zahrnutí veškerých nových zápasových logů do sporting restore a Run export/import |
| Tournament lifecycle, PAQ-074–081 | Produktový kontrakt z v62 zůstává rozhodnutý | Zápasová PR nepotvrzují hotový celý announcement/entries/Q window/materialization/fair-rest scheduler |
| Admin / Viewer | Zápasové API a TypeScript kontrakty; starší UI Saved Revision historie | Nová kompletní Viewer obrazovka rules/replay/stamina, plná reveal/privacy vrstva a celá pre-alpha akceptační sezona |

Zvlášť: přidání `CONDUCT_STOP`, `HEALTH_STOP` nebo jiné položky do enumu samo neznamená její funkční simulaci. První resolver nyní vrací jednu bodovou mutation nebo žádnou při letu; více navazujících mutations kvůli conduct zůstává požadavkem, nikoliv hotovou funkcí. Minimální tempo/conduct z PAQ-071 patří do rozhodnuté pre-alpha, takže nesmí být při dalším plánování omylem přesunut celý do „později“ jen proto, že ho #686 neobsahuje. Pozdější zůstávají individuální referee chyby a vyšší pokročilá eskalace podle příslušných kapitol.

## 35.21 Stav ověření a technický dluh po PR #686

**Historický stav v63:** níže uvedené čtyři rankingové chyby a přípravu dotčených API fixtures následně řeší IMP-018 v 35.23. Původní čísla se zachovávají jako historie testování; nejsou aktuálním tvrzením, že tyto konkrétní chyby zůstávají neopravené. Celá repository sada tím přesto nebyla znovu ověřena.

- Finální cílená sada #686: **141 passed**. Čistá smoke sada: **26 passed**, 1 582 ostatních testů deselected. Tyto množiny se mohou překrývat; nejde o součet unikátních testů.
- Celá domain sada na finálním commitu: **363 passed / 4 failed**. Selhávají `test_official_ranking_respects_rolling_61_week_window`, `test_race_counts_only_target_season_results`, `test_point_awards_resolve_from_distribution_ref_and_inline_distribution` a `test_point_awards_infer_round_based_finishes_when_rounds_are_provided` v `tests/domain/test_ranking_race_engine.py`. Stejný soubor na čistém předchozím `41151cf` skončil **2 passed / 4 failed** se stejnými bodovými očekáváními. Nový rules resolver je nezpůsobil; opravené však nejsou.
- Starší API match integrační běhy se zastavovaly už v přípravě `calendar/build` na HTTP 400 před match endpointem; reprezentativní případ byl potvrzen i na základní větvi. Úplná API sada se proto nevydává za zelenou. Match persistence a uložený Replay mají vlastní procházející application/SQLite kontroly v uvedených řezech.
- Fast CI #825 na feature commitu `b959966` prošel backend smoke a frontend critical tests/build. Lokální dřívější nedostupnost frontendových dependencies není selhání finálního buildu, ale ani důvod tvrdit, že prošla každá frontendová sada.
- Ruff dotčených doménových/testových ploch prošel; service/API kontrola vynechala už existující nesouvisející nález `FURB192`. Python compileall a diff whitespace kontrola prošly.
- Staré country/points/Viewer baseline nálezy zaznamenané u dřívějších IMP se bez nového ověření nepovažují za opravené. Plná repository akceptační sada nebyla tímto souhrnem prohlášena za zelenou.
- Nesouvisející lokální změna `config/world_packages/real_world/countries/MWI/attributes/population.json` nebyla součástí těchto zápasových PR. Její případný dopad na lokální validaci dat nelze připsat vzdálenému otestovanému stromu.

Při tomto vydání Masteru se znovu ověřily merge stavy a aktuální `buuk`, přečetly se navazující kontrakty a sjednotila existující testová evidence. Celá testová sada nebyla jen kvůli editaci dokumentu spouštěna znovu. Kalibrační kohorty u starších IMP jsou historické výstupy dané verze, nikoliv benchmark aktuální v9 nebo důkaz shody s dnešním profesionálním squashem.

## 35.22 Historická hranice v63 a pokračovací režim

Tato část zachovává výchozí stav po #686. Aktuální dokončené řezy, jejich integrace a nová priorita v64 jsou v 35.23–35.28; doporučení pokračovat empirickým laděním je nově odloženo.

Sedm původních sloučených backbone PR zůstává základem tohoto trvalého řezu v jeho výslovně omezeném podporovaném rozsahu:

`Create Empty Run → Initial Viewer Branch → Initial Saved Revision → Clean Working Draft → Stage Viewer Branch change → Inspect diff → Save → Immutable Saved Revision + Audit Event → Switch Viewer → Next Clean Working Draft → Persist → Reload and validate → List complete reachable Saved Revision history → Read scoped historical revision → View history in Admin → Fork Branch from returned revision ID → Confirm guarded restore → Create recoverable pre-restore checkpoint → Append restore revision + Audit Event → Reload and validate → Read validated recovery activity → Open original Saved Revision preview without mutation`

Na něj nyní v oddělené zápasové implementaci navazuje: **uložený formát → neměnný vstup → gameplan a před-rally stav → opening/skrytý control trace s individuálním úsilím → terminal facts → deterministický rules resolver → bod nebo neutral replay → fyzická cena → autoritativní čas a recovery → další rally → uložený validovaný výsledek a read-only Replay**. Existence obou vrstev sama nedokazuje jejich úplné propojení pro sporting restore či průběžné ukládání rozehraného zápasu.

V době vydání v63 jsou PR #677–686 skutečně sloučené. Další programování má vycházet z aktuálně ověřeného `buuk`, nikoliv ze starého otevřeného feature PR; nové změny se připravují jako samostatný otestovaný PR a merge potvrzuje uživatel. Master se aktualizuje hromadně na jeho žádost nebo po delším dohodnutém bloku, ne po každé odpovědi. U návrhových otázek se předkládá jedno doporučené řešení s vysvětlením významu, důvodu a důsledků; rozhodnutá pre-alpha se může po praktické zkušenosti vědomě změnit.

Konkrétní další implementační řez po #686 uživatel ještě nevybral. Kandidáty jsou doplnění minimálního tempo/conduct kontraktu, mentálních barů nebo skutečné per-rally persistence a krokového ovládání; jde pouze o pokračovací kandidáty, nikoliv nové rozhodnutí či pevné pořadí. Při výběru je nutné posoudit závislosti a zbývající kalibraci podle 35.20. PAQ-082 ani přesný dlouhý suspension práh se nesmějí uzavřít pouhým „pokračuj“. Samostatně zůstává práce na již doložených rankingových/API baseline chybách, než bude možné tvrdit, že celá pre-alpha akceptace prochází.

## 35.23 IMP-018 – oprava bodových stages a turnajová integrace

**[IMPLEMENTOVÁNO A OVĚŘENO V buuk]** [PR #687](https://github.com/Jasmetk0/squash-tour-beta/pull/687), merge 8. 9. 2026 v 13:52:26 UTC, `fbcdd729b91d7734335fc4477c918198e7e9172b`.

- Loader normalizoval názvy kol na `champion / semifinal / quarterfinal`, zatímco legacy RankingRaceEngine vyhledával `winner / semifinalist / quarterfinalist`. To mohlo platným výsledkům přidělit nulu. Nyní sdílejí čistý normalizátor; starší aliases zůstávají čitelné, konfliktní duplicity jsou odmítnuté.
- Dotčené API fixtures inicializují vlastní Season Category Points včetně kvalifikačních stages. Produkční validace není oslabena. Očekávání award-service testů vycházejí z authorované tabulky Edition, ne ze zastaralého fallbacku.
- Skutečný čtyřhráčový main-draw integrační scénář prochází calendar → entries → draw → Match Engine v9 → výsledky → uložení awards → reload → odmítnutí duplicitního generování. Kontroluje nezměněné hráčské záznamy. Samostatné existující kontroly ověřují uložený Replay bez nového RNG běhu.
- Při předání prošlo **76 cílených domain/application/API testů**, Ruff a diff check. Tím je aktualizována evidence konkrétních rankingových/fixture problémů z 35.21, nikoliv automaticky všech starších repository nálezů.

**Hranice:** nejde o úplný qualification/WC lifecycle ani Official Ranking publikaci. Legacy apply endpoint nadále mění aktivní hráčské součty a starší snapshot cesta je kopíruje. Uložení turnajových awards se nesmí zaměnit za publikaci nového Official snapshotu. Kontrakt: `docs/TOURNAMENT_INTEGRATION_STABILIZATION.md`.

## 35.24 IMP-019 – čistý výpočet Official Rankingu V1

**[IMPLEMENTOVÁNO A OVĚŘENO V buuk, DOSUD BEZ PRODUKČNÍ PUBLIKACE]** [PR #688](https://github.com/Jasmetk0/squash-tour-beta/pull/688), merge 8. 9. 2026 v 14:04:02 UTC, `ce6fd7e945c46711385155804321af4073ed54dc`.

`src/beta_engine/domain/rankings/official.py` obsahuje samostatný čistý výpočet nad neměnnými modely policy, hráčů, výsledků a kandidátních snapshotů. Nemění stávající API ani tím sám nenahrazuje legacy rankingovou cestu.

- Vstup má explicitní Run/Branch scope, cílový Season Week, historicky efektivní policy, lifecycle a autoritativní vyřešené výsledky s provenance.
- Default první Official sezony je Best 15; návrh další sezonní policy převezme dodanou efektivní Best N předchozí sezony, pokud není override. Pozdější změny se tím automaticky nepropagují přes všechny budoucí sezonní plány.
- Jeden výsledek Edition/hráč skládá kvalifikační a main složku do jednoho Best N místa. Hodnoty jednotlivých stages, BYE unlock, W/O a body za abandonment musí správně dodat volající; tento kernel je neodvozuje z logů zápasů.
- Přijímá terminálně Completed nebo formálně Abandoned výsledky. První publikace musí následovat po dokončení; eligibility začíná explicitním first-publication weekem. Default platnosti je 61 weeků, konec je exkluzivní na first publication + validity. Korekce nesmí restartovat původní dobu platnosti.
- Unranked se nezapočítává. Retired, pre-Tour a aktuálně vstoupivší hráči nejsou v prvním nepříslušném snapshotu klasifikovaní; existující Tour hráči s nulou zůstávají podle kontraktu.
- Jedinečné pořadí používá součet, profil započtených bodů, novost příslušných výsledků, předchozí pořadí a unikátní uložený token. Schopnosti hráče ani nahodilé pořadí vstupních položek nejsou tie-break.
- Kandidát odkazuje hash předchozího snapshotu stejného scope. Bez předchozího snapshotu musí volající řešit výslovný bootstrap; kernel sám neověřuje celou uloženou historii. Přeskupené vstupní tuple vedou ke stejnému fingerprintu, načtení historického JSON nepřepočítává simulaci.

Při předání prošlo **35 domain testů**: 23 nových a 12 legacy rankingových. Pokrývají odloženou publikaci/expiraci, Week 61 rollover, dědičnost, Q+main, Unranked/Abandoned, lifecycle, tie-break, nevalidní vstupy, determinismus a zachování historie. Nejsou to end-to-end testy publikace.

**Zbývá:** transition adapter pro historickou znalost a first publication, provenance a korekce, atomický commit celého Week Transitionu, přidělení persisted tokenů, branch-fork ancestry, disciplína/povinné nuly, Protected Ranking, Race, Season Closing Ranking, API/UI a bezpečné nahrazení legacy součtů. Scénáře s disciplínou zatím nesmějí tento omezený kernel vydávat za úplnou autoritu. Kontrakt: `docs/OFFICIAL_RANKING_CALCULATION_V1.md`.

## 35.25 IMP-020 – reprodukovatelný audit 3 000 zápasů

> Historický záznam k v64 (8. 9. 2026); aktuální merge stav a další postup viz 35.29–36.

**[OTESTOVANÝ KÓD VE FEATURE VĚTVI; PR #689 DOSUD OTEVŘENÝ DO buuk]** [PR #689](https://github.com/Jasmetk0/squash-tour-beta/pull/689). Původní feature commit `2c2c593d9db80bc5069d9fff39dbc167218cb6d3`; po merge #690 má větev head `eef4bf7ea8ad53ff15c5e3cadca91f79eab67ef3`. Výsledky níže vznikly před diagnostickým rozšířením; engine se mezi oběma běhy neměnil.

Skript `scripts/audit_match_realism.py` skutečně spustil 3 000 úplných BO5 zápasů, šest scénářů po 500, celkem **188 072 výměn**. Hráči jsou syntetičtí, čerství pro každý zápas, bez přenosu sezonních stavů; číslo síly nastavuje shodnou hodnotu sedmi základních atributů, nikoliv PSA ranking nebo kalibrované Elo. Pořadí A/B se střídá; seed base je 20260908 a match ID obsahuje scénář/index. CSV ukládá seed, výsledek, časové/servisní metriky a rally-log hash; JSON souhrny používají Wilsonovy intervaly. Úplné logy celé dávky se nearchivují, lze je reprodukovat přes přesnou verzi enginu a vstupy.

| Scénář | Výhry A | Průměr výměny |
|---|---:|---:|
| 84 vs 84, oba tempo-controller | 50,6 % | 16,49 s |
| 90 vs 84, oba tempo-controller | 80,4 % | 16,36 s |
| 90 vs 68, oba tempo-controller | 100 % ve vzorku | 16,21 s |
| 84 attacking vs 84 retrieving | 52,2 % | 15,40 s |
| 84 front-court vs 84 counter-punching | 46,4 % | 14,51 s |
| 60 vs 60, oba tempo-controller | 53,8 % | 17,65 s |

U stejné síly 84/84 má výhra A 95% interval 46,23–54,96 %. Výhra 500/500 není matematická jistota; u 90/68 je interval přibližně 99,24–100 %. Intervaly obou stylových duelů obsahují 50 %, proto nebyla prokázána převaha jednoho stylu. Odlišná match ID navíc znamenají odlišné RNG proudy; nejde o párovaný kauzální experiment stylu.

**[DIAGNOSTIKA, NE NOVÝ CANON]** Výsledky nepotvrzují realistický profesionální squash. Otazníky zůstávají u délky výměn, absolutní úrovně hráčů, tempa a zakončování. Podíl bodů aktuálního podávajícího není sám o sobě kauzální výhoda podání, protože vítěz dále podává; první podávající vyhrál u 84/84 49,8 % zápasů. Zkoumaný starší/malý vzorek nemá být jediným kalibračním cílem.

Výzkumná evidence z uskutečněného auditu (nikoliv nové cílové normy): Carboch/Dušek 2023, DOI `10.7752/jpes.2023.04126`, 14 mužských PSA zápasů z **2018–2020**, průměr výměny 25,1 s; Girard et al. 2007, sedm hráčů a tři experimentální gamy, 18,6 s; Cross Court Analytics 2022, přibližně 13 000 mužských/ženských výměn s výběrem hlavně pozdějších kol, mužské podskupiny medián 11–13 úderů. Rozdílné kohorty, definice i stáří brání přímému potvrzení realismu. V auditu nebyl zajištěn odpovídající reprezentativní dataset 2025–2026.

Zdroje: https://efsupit.ro/images/stories/aprilie2023/Art%20126.pdf ; https://pubmed.ncbi.nlm.nih.gov/17685699/ ; https://crosscourtanalytics.com/blog/how-long-is-a-typical-squash-rally . Podrobnosti a původní souhrn: `docs/MATCH_REALISM_AUDIT_2026-09-08.md`, `docs/match_realism_audit_2026-09-08.json`.

Při předání prošly tři testy instrumentace a Ruff; tato evidence není test celé sezony, zdraví, fyziologie nebo skutečných četností let/stroke. Nezapisuje se žádný nový výkonový či storage příslib na jeden zápas. Další empirické ladění je nyní odložené podle 31.1, nikoliv dokončené.

## 35.26 IMP-021 – diagnostika tempa a zakončení V2

> Historický záznam k v64 (8. 9. 2026); aktuální merge stav a další postup viz 35.29–36.

**[OTESTOVÁNO A SLOUČENO DO VĚTVE #689, NIKOLIV DOSUD DO buuk]** [PR #690](https://github.com/Jasmetk0/squash-tour-beta/pull/690), merge 8. 9. 2026 v 18:49:32 UTC do `codex/match-realism-audit-v1`, commit `eef4bf7ea8ad53ff15c5e3cadca91f79eab67ef3`.

- Audit čte existující control traces bez změny enginu/RNG. Měří trace coverage, odhadované údery, opening/control/terminal čas a closure reason `OPENING_TERMINAL / NATURAL_TERMINAL / HARD_SEGMENT_CAP`.
- Pro `PATIENT / BALANCED / FAST` agreguje segmenty, odhad úderů a čas; poměr času k úderům je vážený přes součty, nikoliv průměr segmentových poměrů. Zahrnuje režii segmentu a není totožný s empirickou dobou mezi kontakty rakety.
- Chybějící historické traces a nepoužité pace třídy mají nedostupné poměry (`null`), ne falešné nuly. Closure reason není klasifikace winner/error/let/stroke. Odhad úderů nepovyšuje engine na shot-by-shot model.
- CSV má aditivní pole, summary JSON `audit_schema_version: 2`. CLI odmítne existující output directory, aby nepřepsalo předchozí audit. Původní V1 report zůstává zachován.

Kontrolních **600 zápasů / 37 700 výměn** používá prvních 100 seedů každého původního scénáře. Každé původní CSV pole kromě měřené doby výpočtu a všech **600 rally-log hashů** odpovídá předchozí dávce. Jde o překrývající se replay kontrolu, ne dalších 600 nezávislých empirických pozorování.

Ve vzorku se nevyskytl hard-cap closure. To vylučuje přímé ukončování limitem v této konkrétní dávce, nikoliv vliv modelu na rozdělení délek nebo jeho nerealistický dlouhý konec. Odhad úderů na výměnu činil 15,354 pro 84/84 a 16,042 pro 60/60; rozdíl délky proto nelze jednoduše popsat jako čistě tempo-only efekt. Není stanovena nová cílová hodnota.

Prošlo **21 testů** audit/rally-control/match-engine (samotná audit sada má šest), Ruff/format a diff check. Souhrny: `docs/RALLY_DIAGNOSTICS_V2.md`, `docs/rally_diagnostics_v2_600.json`. Tato PR nemění doménová schémata z 35.19, pravidla, API, kalibraci ani uloženou historii.

## 35.27 Aktuální pre-alpha priorita a doporučené navázání

> Historický záznam k v64 (8. 9. 2026); aktuální merge stav a další postup viz 35.29–36.

**[POTVRZENÁ PRIORITA]** Uživatel po diagnostice výslovně zvolil návrat k dokončování funkční pre-alpha a ladění realismu až poté. V tomto vydání požaduje pouze aktualizaci Masteru, nikoliv další změnu kódu či automatický merge. Měření z 35.25–26 je zachované pro pozdější návrat, ale není další aktivní implementační frontou.

**[DOPORUČENÝ DALŠÍ TECHNICKÝ ŘEZ, NE NOVÉ PRODUKTOVÉ ROZHODNUTÍ]** Navázat na IMP-019 propojením Official Ranking kandidátů s reálným Week Transitionem, historickými výsledky a atomickou persistencí. Nejdřív ověřit aktuální kód, vyřešené hranice a závislosti. Pokud disciplína, first publication, fork ancestry nebo jiná nezbytná produktová otázka nemají dostatečný kontrakt, krátce ji rozhodnout; nedoplnit tichý sportovní default.

| Oblast | Současná hranice / další funkční práce |
|---|---|
| Turnaj → body | Stabilizovaný main-draw průchod a persistence awards; širší entries/Q/WC/LL, historická veřejná znalost a scheduler podle rozhodnutého kontraktu ještě vyžadují samostatné ověření/integraci |
| Official Ranking | Výpočet kandidáta existuje; publikace při Week Transition, korekce/expiry/provenance, disciplína a návazné rankingové větve nejsou tím dokončené |
| Match lifecycle | Rally model a uložený Replay existují; per-rally persistence, restart, krokové ovládání, mentální stav a rozhodnuté minimální zdravotní/conduct chování zůstávají v mapě 35.20 |
| Kontinuita Runu | Doložit přenos stavů, save/load, historii a scoped transitions v celém skutečném uživatelském průchodu; jednotlivé kernel testy nestačí |
| Akceptace | Official Run: celá sezona → save/load → Season Transition do Weeku 1; prázdný Run: dva ruční hráči + zápas bez kalendáře. Oba opakovaně bez ručních oprav DB |
| Realismus | Zachovat současné profilové verze a diagnostiku; další empirické fitování, větší kohorty a vyvažování odložit, pokud nejde o nezbytnou opravu funkční chyby |

Další PR má dodat konkrétní funkční řez v tomto rámci a jeho testy. Priorita není svolení vypustit již rozhodnuté pre-alpha funkce ani požadavek na plný finální frontend. Není nutné před každým technickým krokem otevírat více variant; vysvětlení významu, důvodu a důsledků zůstává součástí předání. Master aktualizovat po dohodnutém delším bloku nebo na výslovnou žádost. Při přerušení práce nejdřív ověřit rozpracovanou branch/diff/checkpoint a navázat; nezačínat automaticky od nuly ani bez kontroly opakovat externí zápisy.

## 35.28 Auditní uzávěrka v64 a GitHub handoff

> Historický záznam k v64 (8. 9. 2026); aktuální merge stav a další postup viz 35.29–36.

- Zachovaný původní v63 není nahrazen krátkým souhrnem. Nová vývojová priorita je oddělená od sportovního canonu, implementace a výzkumných pozorování. Registry 411/88/69 a PAQ 48/109 zůstávají beze změny; PAQ-082 ani přesná hranice dlouhého suspension nejsou uzavřené.
- Živá kontrola GitHubu: #687 a #688 merged do `buuk`; #690 merged do větve #689; **#689 je stále open do `buuk` a obsahuje i #690**. Uživatelovo „mergnuto“ tedy odpovídá merge #690, nikoliv zatím prokázanému přenosu obou auditů do cílové větve.
- Pro přenos obou diagnostických změn zbývá zkontrolovat a sloučit [PR #689](https://github.com/Jasmetk0/squash-tour-beta/pull/689). #690 se znovu nemerguje ani nerebasuje jen na základě staršího handoffu; už je jeho součástí. Tento dokument žádný merge sám neprovádí.
- Testové počty 76, 35, 3 a 21 popisují různé řezy a překrývající se sady; nesčítat je jako unikátní celkovou akceptační sadu. Kvůli aktualizaci dokumentu nebyla znovu spuštěna celá repository sada.
- PR či úspěšný batch nedokazují úplnost pre-alpha; skutečná hranice je popsaná výše a v 31.3. Původní timing/storage odhady nejsou závazek a orientační procento kódu není ověřená metrika.
- Zdrojový share odkaz se nepodařilo načíst. Konsolidace proto pokrývá dostupnou chronologii a doložené změny, nikoliv neviděnou část snapshotu. Staré audity nejsou v tomto vydání znovu prováděné od nuly. Obsah pro navázání na doložený stav je uložen přímo v tomto Masteru.


## 35.29 Synchronizovaný stav po #720

**[IMPLEMENTAČNÍ EVIDENCE, NE NOVÉ SPORTOVNÍ PRAVIDLO]** Git historie `buuk` obsahuje #689–720. #689 bylo sloučeno commitem `ea0ad6e` a obsahuje dřívější merge #690. Poslední ověřený merge #720: `08a29074250675a61434ba58fb42a185474648d5`, 12. 9. 2026; feature head `c216fe64fd9983cd2346cba6ad9b4b0f1c0692ec`. Fast CI #861 na tomto feature head skončilo `success`. Níže jsou souhrnné schopnosti, ne nový seznam položek za každé PR.

| Systém | Doložená implementace | Zbývající hranice |
|---|---|---|
| Run / Branch / Saved Revision | Prázdný Run, počáteční uložený kořen, Working Draft, Save výběru Viewer Branch, validovaná historie, podporovaný fork a restore s audit/checkpointem | Kompletní sporting-world Save/Restore není doložen; fork revision obsahující ranking preparation je výslovně odmítnut kvůli chybějícímu remappingu |
| Svět a hráči | Package/registry a generovací/bootstrap služby existují, stejně jako Run-scoped prospect komponenty | Legacy sezónní soubory hráčů nejsou samy jednotným historickým stavem nové Run/Branch větve; úplný lifecycle/token/policy resolver pro ranking chybí |
| Turnaj / zápas | Stabilizovaný čtyřhráčový main-draw API průchod k uloženým awards; rally Match Engine, vstupní/formátové snapshoty a uložený replay | Plný scoped provoz entries/Q/WC/LL, scheduler a sporting recovery nejsou tím prokázány; stará souborová cesta vyžaduje vlastnický bridge |
| Official Ranking | Best N, Q+main jako jeden výsledek, expiry, tie-break, validované immutable kandidáty a návaznost týdnů, result history a korekce, frozen input manifests a receipts | Kandidát není publikovaný Official Ranking světa; authoritative vstupy a skutečný Week/Season Transition chybí |
| Admin příprava rankingu | Počáteční/týdenní formulář, soupiska a policy, verzované disciplinární nuly, opravy uložených výsledků, audit, skutečný rollback preview, potvrzení s request/result guardy, přesný retry a inspekce | API odmítá ingest nescopovaných turnajových souborů; formulář zadává vstupy, nenahrazuje automatický lifecycle ani politiku sankcí |
| Ranking Save / recovery | Verifikovaný komponentní bundle s výsledky/nulami/receipts/manifests; samostatný Save, obnovení a kompatibilita historických payloadů | Podpora tohoto komponentního stavu se nesmí vydávat za obnovu celého rozehraného světa |
| Week / Season | Starší týdenní/range runner a MVP rollover existují, ranking staging má transakční komponovatelnost | Legacy week runner výslovně nemá rollback a snapshot kopíruje aktivní součty. MVP rollover není rozhodnutý nový Season Transition |
| Viewer / další konzumenti | Viewer a legacy ranking/Race/Finals cesty existují | Nový Official snapshot není integrovaný do historické publikace, entry/seeding a Finals; stará přítomnost polí neprokazuje Protected Ranking |

Disciplinární nuly mají samostatný začátek, dobu platnosti a verzované opravy; aktivní nuly rezervují Best N sloty. Přesná automatická issuance politika, tarify a kombinace s odečty bodů zůstávají otevřené dle produktových kapitol. Opravy výsledků zachovávají původní dokončení, první publikaci a platnost; předchozí snapshoty se nepřepisují. Nové komponenty neuzavírají Season Closing Ranking, Protected Ranking, Race ani všechny downstream cesty.

## 35.30 Audit driftu a ověření v65

- Aktivní odkazy `AGENTS.md` → v61, constitution/README/ROADMAP → v54 a UX guide → v50 byly zastaralá navigace, nikoliv rozhodnutí vrátit produkt ke starší verzi. V synchronizačním návrhu se nahrazují stabilní canonical cestou; historické verze uváděné jako původ konkrétního pravidla zůstávají.
- Historické omezení „discipline none only“ v ranking staging dokumentu překonaly pozdější zero kontrakty; není oprávněním ignorovat uložené sankce.
- Rozdíl mezi legacy týdenním runnerem a novým scoped rankingem je implementační mezera, nikoliv spor o sportovní pravidla. `prepare_official_ranking` odmítá nescopované tournament bindings. `SeasonRankingSnapshotService` přiznává aktivní součty bez Best N/rolling expiry. `SeasonWeekSimulationExecutionService` přiznává absenci rollbacku.
- V tomto synchronizačním auditu prošlo **41 testů za 126,38 s** v cílené sadě Run foundation, ranking restore, legacy week execution/rollover, match input a ranking preview API. Přesný rozsah je v commitově ukotveném `CURRENT_STATE.md`. Mockované orchestrace nejsou end-to-end důkaz. Historických 60 backendových a 36 frontendových testů z #720 se nesčítá s jinými běhy jako unikátní celková akceptace.
- Plná repository sada, browser end-to-end, celá sezona a full Run nebyly v tomto dokumentačním úkolu provedeny. Starší baseline nálezy nejsou automaticky opravené. Zelené Fast CI není důkaz dokončené pre-alpha.
- Původní produktové kapitoly a registry nejsou redukovány na souhrn. Toto vydání mění vývojový protokol a evidenci implementace, nikoliv sportovní matematiku, PAQ-082 či ostatní otevřená rozhodnutí.

## 35.31 Cesta k pre-alpha a první navazující řez

**[TECHNICKÉ DOPORUČENÍ, PRŮBĚŽNĚ PŘEHODNOCOVAT]** Další lokální rankingové detaily nyní nejsou hlavní priorita. Nejbližší závislost je bezpečný přenos skutečných turnajových výsledků do nové Run/Branch rankingové historie. První řez: **uložený podporovaný main-draw turnaj → ověřený scoped snapshot zdrojů → Official kandidát → Save/reload/restore**. Vyžaduje doložené vlastnictví zdroje, nikoliv pouhé přejmenování globálního eventu přidaným `run_id`. Musí využít již existující produkční výsledky/awards a auditovaný command; přesné technické uložení zvolí Codex po inspekci. Tento mezikrok se nesmí nazvat hotovým Week Transitionem.

Následuje integrační checkpoint a skutečný Week Transition nad uloženými world/player/policy vstupy v pořadí kapitoly 6.5: atomicky aktualizovat stav, ranking a veřejné události; Viewer zůstává na posledním Save. Pak více týdnů, integrace entries/draws a ostatních nutných konzumentů, Season Closing/Season Transition včetně konce 50. sezony, a celosezonní Save/Restore/replay akceptace. Přesné pořadí aktualizuje `ROADMAP.md` podle aktuálních závislostí.

Oba průchody kapitoly 31.3 zůstávají povinné: Official Run přes celou sezonu a otevření další; prázdný Run se dvěma ručně vytvořenými hráči a jedním zápasem bez kalendáře. Minimální Reconstruction a ostatní již rozhodnuté pre-alpha schopnosti se tím nevypouštějí. Chybějící produktové odpovědi se řeší až u skutečně závislého kroku, ne tichým stubem, který by byl vydáván za hotovou funkci.

# 36. AI-Assisted Development / Development Operating Model

**[ROZHODNUTO – PRACOVNÍ PROTOKOL, 12. 9. 2026]** Tato kapitola nahrazuje dřívější organizační instrukce, pokud jsou s ní v rozporu; nemění sportovní pravidla.

## 36.1 Role a autorita

- Uživatel je product owner / game designer: rozhoduje produktová pravidla, skutečné otevřené chování a schvaluje merge PR. Nemusí určovat architekturu, pořadí souborů, databázové změny nebo testovací strategii.
- ChatGPT Work je technical lead: ověřuje GitHub, udržuje kontext, hodnotí závislosti, navrhuje jeden nejlepší další řez, aktualizuje Master a připravuje hotové zadání pro Codex.
- Codex je preferované implementační prostředí: repository, kód, debugging, migrace, testy, build, integrační ověření, review a PR. Work a Codex nemají duplicitně implementovat stejný úkol. Při nedostupnosti nástroje agent pravdivě popíše hranici a dodá předatelné zadání; nesmí předstírat spuštění Codexu.
- GitHub a aktuální kód/testy jsou zdrojem pravdy o implementaci. Tento Master je produktový canon a přenosná handoff paměť; statusové značky zůstávají oddělené od implementace.
- Pořadí autority: novější explicitní uživatelské rozhodnutí → canonical Master → podřízená constitution → relevantní specifikace; stará dokumentace/kód jsou pouze historie či evidence. Technický a dokumentační drift agent opravuje sám. Nové sportovní pravidlo ani OPEN matematiku nesmí odvodit z existujícího defaultu.

## 36.2 Jednoduchá trvalá paměť

Repo obsahuje jeden `SQUASH_ENGINE_MASTER_VISION.md`, krátký `CURRENT_STATE.md` s auditovaným commitem a hlavními hranicemi, `ROADMAP.md` jako cestu k pre-alpha a `AGENTS.md` jako navigaci a engineering invarianty. Constitution zůstává podřízený zachovaný technický souhrn; nepřidává se další paralelní registr. Historii změn uchovává Git. Verze v exportu označuje kopii canonical dokumentu, nikoliv konkurenční zdroj pravdy.

Po aktualizaci Masteru se uživateli vždy vrací celý aktualizovaný soubor pro budoucí chaty. Neplní se detaily každého PR; změny se konsolidují po významném bloku, integračním checkpointu nebo na žádost. PR aktualizuje krátký implementační stav, když mění jeho hranice. Neoznačuje vlastní otevřený PR jako již sloučený.

## 36.3 Výběr práce a autonomní rozhodování

Po „mergnuto“, „pokračuj“ nebo „dodělej“ ověřit nový `buuk`, poslední merge, rozpracované změny a relevantní kód/testy. Porovnat s pre-alpha, identifikovat blocker a závislosti, vybrat **jeden coherent vertical slice na PR** s ověřitelným koncem. Preferovat propojený tok, odblokování více systémů a odstranění rizikového architektonického dluhu před prohlubováním izolované komponenty. Nepracovat slepě podle starého TODO.

Technické, reverzibilní a architektonicky kompatibilní volby řeší agent. Skutečný nerozhodnutý produktový konflikt předloží stručně s možnostmi a jedním doporučením. Stávající pravidla ani UX s podstatně různými legitimními výsledky svévolně nepředefinuje. Nejprve funkční pre-alpha; hluboký realism tuning, velký visual polish a sekundární systémy až následně, pokud nejsou nezbytné pro správnost.

## 36.4 Codex zadání, Definition of Done a review

Zadání musí být přímo vložitelné: objective a důvod, autoritativní zdroje, existující kód k ověření, in-scope/non-goals, invarianty, acceptance criteria, rizikově odpovídající testy a integrační ověření, očekávaný PR a výslovně nerozhodnuté otázky. Codex nejprve prozkoumá skutečný checkout; prompt není důkaz nezměněné struktury kódu.

Hotovo vyžaduje relevantní domain/unit, skutečnou backend/persistence integraci, frontend/component, build a statické kontroly podle dopadu. Podle rizika přidat migrace/kompatibilitu, determinismus/replay, rollback, Save/Restore, scope isolation, historical boundary, no-future-leak a browser průchod. Nevyžadovat vše mechanicky; uvést přesně spuštěné kontroly, výsledek a limity. Mockovaný frontend není full integration. Neříkat „prošlo“ bez běhu. Kód vzniklý bez relevantního ověření není hotová implementace.

U rizikových změn samostatný review průchod hledá invarianty, nondeterminismus/order dependence, scope/future leaks, nekonzistentní historii, neúplné transakce, chybný retry, restore/migrace, skryté produktové změny, chybějící regrese a rozdíl preview/commit. Není to jen potvrzení původního návrhu. Review nemusí znamenat další paralelní agent; nástroje se nezdvojují bez důvodu.

## 36.5 Integrační checkpointy

Přibližně po 5–10 významných PR nebo po velkém subsystému zvážit checkpoint před další feature. Postupně doložit: jeden úplný uživatelský tok → celý týden → Week N/N+1 → více týdnů bez oprav → sezona → Season Transition → více sezon → dlouhý/full Run s determinismem. Checkpoint hledá mezery mezi subsystémy. Rozšířená budoucí akceptace nesmí být zaměněna za již proběhlý test ani za tiché rozšíření sportovního canonu.

## 36.6 Nástroje a předání

GitHub používat aktivně pro stav a historii. Context7 jen při závislosti správnosti na dokumentaci externí knihovny/API. Figma později pro cílený design; Linear zatím není paralelní source of truth. Nedostupný Codex Security neblokuje vývoj. Neslibovat dostupnost pluginu bez skutečného nástroje.

Významné předání obsahuje: **Stav**, **Nejlepší další krok**, **Co mám udělat já** a při následné implementaci kompletní **Codex prompt**. Uživatel dostane jednu jasnou instrukci, ne pět technických variant. Pokud není nic potřeba, agent to řekne a pokračuje v autorizovaném úkolu. Merge provádí uživatel.
