# Parallel ChatGPT task — saved Run-list filters, 12 November 2026

This is a bounded implementation task for the ordinary ChatGPT chat alongside
Claude and Work. It is grounded in Master 23.8, not a new sporting decision.
Reviewed base: `buuk 75bf9443d85fc51c33c8f1f7dc15a0096eaa3042`, including
owner-merged #1784/#1785/#1786. Fetch current refs and inspect open PRs first.
Claude keeps the lifecycle/career/season/notification queue; Work keeps ATP source,
calendar and native scheduled Q/Main integration. Neither assignment is replaced.

## Prompt for the ordinary ChatGPT chat

Pomáháš s vývojem Squash Enginu v `Jasmetk0/squash-tour-beta`, integrační větev
`buuk`. Jsi třetí, samostatně pracující pomocník. Work koordinuje a kontroluje
výsledky, Claude má svůj přidělený vývoj a Radim jako jediný merguje PR.

Nejdřív ověř, jaký přístup ke skutečnému repozitáři a nástrojům máš. Nezaměňuj
čtení přes GitHub za možnost upravovat soubory, spouštět testy nebo vytvářet PR.
Pokud můžeš programovat v checkoutu, pracuj tam. Pokud můžeš pouze číst, připrav
patch vůči skutečně načteným aktuálním souborům a přesně označ nespouštěné testy;
nepředstírej provedené změny nebo existující PR. Pokud nevidíš potřebný zdroj,
požádej pouze o chybějící soubory nebo přístup, nevymýšlej jejich obsah.

Přečti `AGENTS.md`, `CLAUDE.md`, `CURRENT_STATE.md`, příslušné části Masteru
(zejména 23.8 a první pre-alpha Admin v75) a rozdělení práce v
`docs/AI_REVIEW_HANDOFF.md`. Nepřebírej Claudovo obecné zadání: toto je tvůj
samostatný, omezený celek.

### Výsledek: pojmenované pohledy přehledu Runů

V `web/src/pages/RunsPage.tsx` už funguje hledání podle jména/ID a filtr všech,
upravitelných nebo chráněných Runů. Doplň ucelené ukládání a používání těchto
osobních pohledů. Neimplementuj znovu stávající hledání ani jiný seznam Runů.

1. Uživatel pojmenuje aktuální kombinaci hledání, existujícího filtru a případného
   podporovaného řazení a výslovně ji uloží. Později ji vybere, skryje z rychlé
   nabídky a znovu zpřístupní ve správci. Přepis stejného pohledu nesmí být tichý.
   Pro V1 stačí jednoduché ovládání; žádný velký nový globální framework.
2. Nastavení přežije reload jako verzovaná osobní preference v prohlížeči.
   Použij stávající konvence bezpečného `localStorage`; řekni v UI pravdivě, kde
   je preference uložená. Tato technická V1 netvrdí synchronizaci mezi zařízeními
   ani hotovou implementaci Saved Views ve všech modulech.
3. Uchovávej pouze preference zobrazení, ne kopie Runů, Branchí, výsledků,
   autentizační údaje nebo libovolné URL. Vždy filtruj aktuální skutečný inventář.
   Nepodporované hodnoty/schéma neaplikuj a neoznačuj je jako kompatibilní; případnou
   nedostupnost vysvětli bez automatického přepsání původních dat.
4. Hledání, přejmenování Runu v datech, prázdný inventář, nulový výsledek hledání,
   chyba API a nefunkční či plné browser storage musí mít srozumitelný stav.
   Základní seznam a navigace fungují i bez úložiště předvoleb. Uživatelská jména
   pohledů se automaticky nepřekládají; ovládání funguje v CS/EN a klávesnicí.
5. Výběr pohledu pouze mění prezentaci seznamu. Nevytváří Run, nepřepíná aktivní
   Branch nebo Viewer Branch, neposouvá čas, neprovádí Save a nespouští úlohu.
   Zachovej současné ruční otevření Runu a načítání Branchí až po rozbalení.

Příklad ověření: vytvoř pohled „Moje testy“ pro text `test` a pouze upravitelné
Runy. Po reloadu jej znovu vyber a ověř stejné filtry nad aktuálními daty. Skryj
jej a obnov ze správce. Jiná kombinace nesmí změnit uložený pohled bez výslovného
uložení. Poškozený uložený JSON nesmí shodit stránku ani změnit jediný Run.

### Přesné hranice práce

- Smíš měnit `web/src/pages/RunsPage.tsx`, jeho testy a přidat malé izolované
  helpery/komponenty/testy/styly výhradně pro tuto funkci. Nejprve ověř, že tyto
  soubory nemá rozpracované jiné otevřené PR.
- Neměň `src/beta_engine/`, `config/`, API kontrakty, `web/src/api/client.ts`,
  `CalendarTourPanel`, Saved Draw UI, kariérní nebo sezonní stránky, společný
  sidebar, stop rules, watchlisty/oblíbené ani obecnou navigaci. Master neměň.
- Nepřidávej nové závislosti ani nepřepisuj další stránky pod záminkou refaktoru.
  Pokud skutečný blocker vyžaduje překročit hranici, popiš ho Workovi; neřeš jej
  konkurenční implementací sdíleného systému.
- Jde o V1 pohledů přehledu Runů. Další moduly Saved Views jsou budoucí návaznost,
  nikoliv oprávnění zasáhnout do Claudových filtrů a souhrnů.

### Ověření a předání

Spusť relevantní Vitest testy současné stránky a nové logiky a `npm run build`
z adresáře `web`. Ověř skutečnou stránku v browseru, pokud jej máš k dispozici.
Testuj zejména zachování kombinace filtrů po uložení/reloadu, skrytí/obnovení,
nekompatibilní či poškozené uložení, nedostupné storage, CS/EN a zachování
stávajících navigačních/načítacích invariantů. Neměň očekávání starých testů jen
proto, aby vyšly zeleně. Rozliš komponentové mocky a skutečný browser/API běh.

Pracuj na vlastní větvi a připrav jeden Draft PR do `buuk`; nic nemerguj ani
nepiš přímo do buuk. Vrať změněné soubory, konkrétní funkční příklad, přesné
výsledky skutečně provedených kontrol a omezení. Work provede nezávislou kontrolu.
Pokud nemáš nástroje k zápisu/testům, odevzdej místo PR skutečný patch a jasně
uvedené neprovedené kontroly. Po dokončení tohoto celku nepřebírej další oblast
enginu bez přidělení, aby se paralelní práce nezačaly překrývat.
