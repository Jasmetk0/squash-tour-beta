# Grand Slamy pro ATP Earth W52

Radim 26. 11. 2026 schválil Australian Open, Roland Garros, Wimbledon a US Open od roku 1990 jako součást plného ATP Earth Runu. [Master §§4.12 a 31.41](../SQUASH_ENGINE_MASTER_VISION.md) určuje rozsah a akceptaci. První pre-alpha vyžaduje dva po sobě jdoucí W52 ročníky, ve kterých se konaly všechny čtyři majory. U všech osmi Editions je nutné skutečně ověřit hraní v Runu. Historický katalog od roku 1990 je dlouhodobý rozsah. Každý ročník může mít vlastní stav pokrytí.

## Jak se skládá Run

Grand Slamy mají vlastní verzovaný zdroj mužské dvouhry. Plná předvolba ATP Earth při založení Runu nabídne tento zdroj spolu se stávajícím ATP Tour. Použij existující Category, Series, Calendar a sportovní profily. Pro jeden složený Setup se připnou přímo listové dokumenty obou zdrojů. Stávající Setup validátor vnořený Setup odmítá. Zachovej verze a otisky stávajícího ATP Tour zdroje. Při importu uplatni běžné preview, potvrzení a explicitní Save. Existující Runy mají své nezávislé uložené kopie.

## První úkol pro ChatGPT

1. Po ověření aktuálního `buuk` a `AGENTS.md` založ vlastní datový Draft. Začni čtyřmi stabilními Series a chronologickým soupisem od roku 1990 v samostatném zdrojovém adresáři pro Grand Slamy. Odděl odehraný, zrušený a předběžný stav. První dávku zaměř na osm Editions z dostupných dvou po sobě jdoucích dokončených ročníků, se startem u 2024 a 2025, pokud to zdroje potvrdí. Zkontroluj také nejstarší ročník 1990 a zrušený Wimbledon 2020 jako referenční případy.
2. Dolož odděleně skutečné termíny kvalifikace a hlavní soutěže, počet hráčů i míst v pavouku, Q postupy, nasazení, divoké karty, BYE, body jednotlivých fází a významné změny pravidel. Preferuj originální losy, výsledkové archivy a dobové předpisy pořadatele. Zapiš odkazy, strany a otisky skutečně získaných PDF, pokud je profil vyžaduje. Zachovej původní datum a projekci do Year Week a Run Season Week pro offsety 1 a 37. Při vícetýdenním Main použij existující W52 pravidla a uveď přesné příčiny, pokud tvar nebo návaznost fází aktuální rozhraní nepodporuje. Kolize v týdnech a sezonní hranici posuzuj podle Masteru.
3. Pro první dobře doloženou Edition připrav testovací fixture pro stávající model a dolož, kam skutečný import nebo preview došel. Na `buuk` stávající ATP cesta uložení profilu s vyřazovací kvalifikací a nativní odehrání odděluje. Work koordinuje společný import, podporu profilu, případné chybějící nativní Q/Main hraní a ranking. Pro blokovaný případ předej konkrétní chybovou zprávu, minimální fixture a přesnou změnu společného kontraktu, kterou by vyžadoval. Match Engine, RNG, FAX, Saved, timeouty a CI patří do jiných pracovních větví. Kde se dobové tenisové pravidlo nevejde do společného squashového modelu, připrav jasnou variantu k rozhodnutí.
4. Pravidelně aktualizuj počty a rozliš ověřený kalendář, sportovní profil, nativní plán, skutečné odehrání a obnovu. Spusť cílené testy a audity. V Draftu uveď přesný HEAD, skutečně spuštěné ověření a nejbližší další krok. Radim rozhoduje o mergi.

## Koordinace

- #1886 a #1888 vlastní moderní ATP Tour sportovní profily a verze dosavadního katalogu.
- #1891 vlastní historické ATP Tour podklady od roku 1990 a #1898 moderní ATP Tour podklady od roku 2025 dozadu.
- #1894 řeší nativní Dallas a je relevantním vstupem pro nativní Q/Main průchod. Work ověří společný runtime samostatně.
- Údaje pro Grand Slamy navazují ze samostatné větve a adresáře. Původní ATP Series ID, ročníkové součty a verze těchto PR zůstávají autoritativní pro jejich vlastní rozsah.

## Akceptační průchod

V Adminu založ ATP Earth W52 Run a vyber ATP Tour i Grand Slam zdroj. Projdi Preview → Confirm → explicitní Save. V obou plných sezonách projdi každým Grand Slamem od Entry přes kvalifikaci a hlavní soutěž až k potvrzeným výsledkům, bodům, Official Rankingu a kariérní historii. Po první Season Transition ulož, restartuj a pokračuj až do Week 1 třetí sezony. Použij skutečné MatchEngine zápasy a testuj na samostatném uloženém Runu. Tento dokument je zadání. Provedení akceptačního průchodu se dokládá až konkrétním výsledkem.

Oficiální východiska: [Grand Slamy a pořadatelé](https://www.world.tennis/en/tours/grand-slam-tournaments/), [archiv ATP výsledků](https://www.atptour.com/en/scores/results-archive), [zrušený Wimbledon v oficiálním kompendiu](https://www.wimbledon.com/pdf/Wimbledon_Compendium_2021v3.pdf).
