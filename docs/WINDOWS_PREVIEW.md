# Squash Engine: interní Windows preview

Přenosný testovací balíček pro Windows x64. Obsahuje Python runtime, backend,
zkompilované Admin/Viewer UI a výchozí konfigurační balíčky. Na počítači není potřeba
instalovat Python, Node.js, Git ani editor. Není to certifikované vydání pre-alphy:
platí stále úplná vydávací brána v [testovací politice](PRE_ALPHA_TEST_POLICY.md).

## Stažení a spuštění

1. V repozitáři otevři **Actions → Windows preview**, vyber úspěšné sestavení
   odpovídající požadovanému commitu a dole stáhni artefakt
   **SquashEngine-Windows-Preview**. Ke stažení artefaktu je potřeba přihlášení na GitHub.
   GitHub **Code → Download ZIP** obsahuje pouze zdrojový kód a spustit nejde.
   Pro nové sestavení aktuálního `buuk` lze po merge launcheru v témže workflow
   zvolit **Run workflow → buuk**. Každý běžný merge nemusí znovu stavět balíček.
2. Rozbal **celý** ZIP do běžné uživatelské složky, například Dokumenty.
   Nespouštěj soubor přímo uvnitř ZIPu a neodděluj EXE od `_internal`, `config`, `src` a `web`.
3. Dvojklik na **Spustit_Squash_Engine.bat**. Otevře se konzole a následně prohlížeč
   na `http://127.0.0.1:5173`. Konzoli nech otevřenou. První příprava kopíruje
   výchozí konfiguraci do samostatné datové složky a může chvíli trvat.
4. V Adminu lze vytvořit Run a používat aktuálně implementované funkce.
   Zápisy a Save se nadále provádějí výhradně explicitními operacemi aplikace.
5. Před ukončením dokonči operaci a ulož práci v Adminu, potom v konzoli stiskni
   **Enter** a počkej na `STOPPED / UKONCENO`. Zavření samotného prohlížeče backend
   nezastaví. Násilné zavření konzole není bezpečný způsob dokončení běžící operace.

Balíček není digitálně podepsaný. Windows jej může označit jako neznámou aplikaci.
Stahuj pouze ověřené sestavení tohoto repozitáře. Pokud ochrana spuštění blokuje,
předej přesné hlášení; nevypínej kvůli tomu antivirus ani systémovou ochranu.
Služby poslouchají pouze na tomto počítači. Porty **5173 a 8000** musí být volné;
při obsazení se launcher zastaví a cizí procesy neukončuje.

## Data, restart a další sestavení

Konzole vypíše přesný source commit a datovou složku. Výchozí umístění je:

```text
%LOCALAPPDATA%\SquashEngine\Preview\<celý source commit>
```

Obsahuje `beta_engine.db`, upravitelné kopie konfigurace, identitu sestavení a
`launcher.log`. Zápisy nepatří do rozbalené programové složky. Opakované spuštění
**stejného sestavení** otevře stejná data i po přesunutí programové složky.

Každý jiný commit dostane **vlastní** datovou složku. Neprobíhá automatická migrace,
aktualizace ani přepsání starého světa. Starší balíček a jeho data si ponech.
Neupravuj `preview-owner.json` a nekopíruj starou databázi do nového sestavení.
Přenos celého Runu mezi verzemi a jeho kompatibilita potřebují samostatné ověření.
Export vybrané Branche není náhradou kompletní zálohy všech Runů a Package změn.

Záloha: ukonči engine, počkej na potvrzení zastavení a zkopíruj **celou datovou
složku**. Obnova: se zastaveným enginem vrať celou složku pro stejné sestavení;
nejprve si uchovej i poškozenou/neúplnou kopii. Samotný launcher neprovádí automatické
zálohování ani opravování databáze. Selhání kopírování, neznámá data nebo jiné
sestavení vyvolají chybu bez automatického resetu. Při chybě pošli text z konzole,
source commit a `launcher.log`; původní data nemaž.

## Bezpečná offline záloha (nově)

Po dokončení všech operací v Adminu proveď **Save** a ukonči engine přes Enter
v okně Spustit_Squash_Engine.bat. Po zobrazení STOPPED / UKONCENO můžeš
dvojklikem spustit **Zalohovat_Squash_Engine.bat**. Tento druhý soubor
nespouští simulaci ani webserver a neprovádí obnovu nebo migraci.

- Výchozí cílová složka: `Dokumenty\SquashEngineBackups` (uvnitř
  aktuálního uživatelského profilu). Konzole vypíše přesnou cestu ZIPu.
- Archiv má unikátní jméno se source commitem a časem. Existující archiv
  se nikdy úmyslně nepřepíše.
- Obsahuje `preview-owner.json`, všechny běžné soubory uživatelské
  konfigurace, kopii SQLite databáze pořízenou přímo databázovým backup API
  a ostatní uživatelské soubory. Do zálohy se nepřidává otevřený lock,
  SQLite WAL/SHM ani dočasný journal; transakčně potvrzený obsah WAL je
  součástí SQLite snapshotu.
- Před vytvořením ZIPu launcher ověří identitu sestavení, bezpečné cesty,
  nepřítomnost symbolických odkazů v datech, výhradní vlastnictví datové
  složky a konzistenci SQLite. Po vytvoření archiv celý přečte a porovná
  otisky SHA-256 všech souborů s manifestem.
- Pokud engine právě běží, data patří jinému sestavení nebo soubor není
  čitelný, operace skončí chybou. Nevypíná cizí procesy ani nemaže zdrojová
  data. Při selhání nevydává hotovou zálohu.

Volitelně lze v konzoli s rozbaleným balíčkem určit přesný nový cíl:

```bat
SquashEnginePreview.exe --backup --backup-output "D:\Zalohy\Moje-zaloha.zip"
SquashEnginePreview.exe --verify-backup "D:\Zalohy\Moje-zaloha.zip"
```

Příkaz `--verify-backup` **pouze ověřuje ZIP bez rozbalení**.
Příkaz `--data-dir` je určen pro pokročilé testování explicitní datové složky
téhož source commitu. Archiv nesmí být uložen v datové či programové složce.

**Uchovávej ZIP v soukromí.** Obsahuje hráče, Runy, Package změny a další
lokální data; neposílej jej jako diagnostický soubor a nenahrávej veřejně.
Záloha není automatická a není digitálně podepsaná. Automatické přenesení
do jiného commitu ani tlačítko Obnovit nejsou implementovány. Pro obnovu
zachovej původní balíček stejného commitu, vypni engine a nejprve si
ponech i původní datovou složku. Význam obnovy a kompletní kompatibilita
stále podléhají separátnímu testování; samotné `--verify-backup`
není end-to-end test skutečné obnovy Runu.

## Co ověřuje sestavení

Workflow vždy i pro Draft PR spouští úzké testy launcheru a skutečné Windows
ověření přenosného balíčku: bez Pythonu/Node/Gitu v PATH, z cesty s mezerami a
diakritikou, s reálným Chromium, FastAPI a SQLite. Vytvoří prázdný Run jehož vytvoření
je první Save, ukončí proces, znovu jej spustí a porovná uloženou revizi. Ověří také
konflikt portu a zachování zdrojové konfigurace. ZIP se zveřejní jen po úspěchu.
To nedokazuje celé sportovní průchody ani 50sezonovou akceptaci.

`build-info.json` určuje commit a otisk manifestu závislostí;
`build-dependencies.txt` eviduje sestavovací prostředí. Zdrojové `src` soubory jsou
přibaleny pro stávající kontrolu provenance enginu. Spuštění je nepřekládá a
nestahuje nové závislosti. Vývojářské `run_backend.bat` a `run_frontend.bat`
zůstávají odděleným postupem vyžadujícím vývojové nástroje.
