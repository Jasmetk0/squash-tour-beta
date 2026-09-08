# První empirická kontrola Match Enginu v9

## Verdikt

Engine už zvládá tisíce úplných zápasů a některé základní kontroly chování
vycházejí rozumně. Za empiricky realistický jej ale zatím označit nelze.
Nejvýraznější otázkou je model délky výměn a jeho citlivost na kvalitu hráčů.
Tato aktualizace měří; nemění sportovní algoritmy ani kalibrační konstanty.

## Provedené měření

3 000 zápasů, šest scénářů po 500, BO5 do 11 o dva. Každý zápas začínal
s čerstvým stavem, bez explicitního zranění, formy, cestování nebo retirementu.
Použity skutečné logy současného enginu, nikoliv zjednodušená náhradní simulace.
Pořadí A/B ve vstupu se střídalo. Seed je 20260908 + index 0–499;
match ID je `audit:<scenario>:<index>`. Hráči jsou syntetičtí, nikoliv kopie
konkrétních profesionálů. Všechny jejich základní atributy mají stejnou uvedenou
hodnotu. Styl se liší jen tam, kde je to výslovně uvedeno ve scénáři.

| Scénář (hráč A proti B) | Výhry A | Průměr zápasu | Průměr výměny |
|---|---:|---:|---:|
| 84 vs 84, oba tempo-controller | 50,6 % | 38,04 min | 16,49 s |
| 90 vs 84, oba tempo-controller | 80,4 % | 35,98 min | 16,36 s |
| 90 vs 68, oba tempo-controller | 100 % | 24,17 min | 16,21 s |
| 84 attacking vs 84 retrieving | 52,2 % | 36,10 min | 15,40 s |
| 84 front-court vs 84 counter-punching | 46,4 % | 35,70 min | 14,51 s |
| 60 vs 60, oba tempo-controller | 53,8 % | 39,32 min | 17,65 s |

U 84 vs 84 je 95% Wilsonův interval výher A 46,23–54,96 %. Podle vstupní
strany vyhrál A v 50,4 % a 50,8 % případů: tato kontrola neukazuje zjevnou
stranovou nerovnováhu. Nejde však o úplný párovaný symmetry test všech seedů.
U 90 vs 68 neznamená 500/500 matematickou jistotu výhry: interval je přibližně
99,24–100 %. Hodnoty atributů nejsou kalibrované na PSA ranking nebo Elo, proto
zatím nelze říci, zda právě taková dominance odpovídá skutečnému výkonnostnímu rozdílu.

U obou stylových duelů interval výher obsahuje 50 %. Nelze tedy z tohoto běhu
prohlásit jeden styl za prokazatelně lepší. Stylové scénáře navíc používají jiné
match ID a tedy jiné náhodné proudy; rozdíly nejsou párovaným kauzálním experimentem.

## Srovnání s reálnými daty a jejich stářím

**Carboch a Dušek, 2023:** 14 mužských zápasů PSA, ale z turnajů **2018–2020**,
nikoliv z roku 2023. Výběr nebyl náhodný a průměrné pořadí mužů bylo přibližně
12,5. Uvádí průměr výměny 25,1 ± 3,5 s a 18,6 ± 2,3 úderu. Náš scénář 84 vs 84
má přibližně o 34 % kratší průměr výměny. To je kalibrační varování, ne důkaz,
že každá squashová výměna musí mířit na 25 sekund. Nemáme shodnou hráčskou kohortu
ani původní surová data pro odpovídající statistický test.

Zdroj: https://efsupit.ro/images/stories/aprilie2023/Art%20126.pdf

**Girard a kol., 2007:** sedm hráčů a tři gamy simulující soutěž, nikoliv velký
soubor současných zápasů PSA. Průměr výměny 18,6 s, 34,6 % pod 10 s a 32,6 %
nad 21 s. Náš scénář 84 vs 84 má 34,77 % pod 10 s a 30,41 % nad 21 s.
Tvar v těchto dvou hrubých pásmech je podobný, ale starý a malý experiment
nesmí sloužit jako potvrzení současného realismu.

Zdroj: https://pubmed.ncbi.nlm.nih.gov/17685699/

**Cross Court Analytics, 2022:** vlastní databáze přibližně 13 000 výměn
napříč mužskými a ženskými zápasy, se sběrem zaměřeným na čtvrtfinále a pozdější kola.
Mužské podskupiny mají mediány 11–13 úderů. Je to užitečné upozornění na
výběrové zkreslení a rozdíl mezi mediánem úderů a průměrem sekund. Tento audit
jeho úderové statistiky přímo neporovnává: náš engine nemá autoritativní
shot-by-shot simulaci. Národnostní členění studie není důvod přidat hráčům
vrozené stylové vlastnosti podle země.

Zdroj: https://crosscourtanalytics.com/blog/how-long-is-a-typical-squash-rally

Vyhledávání zahrnovalo novější práce, ale zde nemáme ověřený reprezentativní
soubor z let 2025–2026 pro stejné metriky. Ani novější datum publikace samo
nezaručuje nová observační data. Zápasových 38 minut proto neoznačujeme ani za
správnou, ani za chybnou moderní PSA normu bez srovnatelného vzorku.

## Co stojí za další kontrolu

1. **Kvalita hráčů versus délka výměny.** Pár 60/60 vytváří delší výměny než
   84/84; velký rozdíl 90/68 jejich délku skoro nezměnil. To není automaticky
   chyba, protože nižší tempo může výměnu prodloužit. Je ale třeba oddělit
   počet úderů, tempo, chyby a schopnost zakončení. V `_segment_closure_probability`
   nejsou přímo absolutní technika či konzistence: působí nepřímo přes stavy,
   intenzitu a gameplan. To je kandidát k vysvětlení, ne prokázaná jediná příčina.
2. **Dlouhé výměny.** U 84/84 překročilo minutu jen 0,065 % výměn; maximum
   bylo 69,22 s. Celkově nejdelší výměna měla 81,865 s. Současný model má
   nejvýše 24 abstraktních segmentů a v posledním vynucené ukončení. Existence
   tohoto limitu je fakt; správnou četnost extrémů musíme teprve odměřit z reality.
3. **Podání.** U 84/84 vyhrál podávající 54,68 % bodovaných výměn, ale první
   podávající jen 49,8 % zápasů. Jde o odlišné metriky. V nevyrovnaných párech
   je podíl bodů podávajícího zkreslen tím, že silnější hráč více vyhrává a znovu
   podává; jeho 68,94 % u 90/68 proto neznamená tak velkou kauzální výhodu podání.
4. **Rozptyl výsledků.** U 84/84 skončilo 33,6 % zápasů ve třech, 34,6 % ve
   čtyřech a 31,8 % v pěti gamech. Pro čistě matematický model nezávislých,
   stejně pravděpodobných gamů by poměr byl 25/37,5/37,5 %. Náš model má
   další proměnlivé stavy, takže rozdíl není sám o sobě bug ani empirický důkaz.

## Doporučený další postup

Neprodlužovat všechny výměny jedním násobičem. Nejprve vytvořit srovnatelnou
referenční kohortu reálných mužských BO5 zápasů, sjednotit definice výměn/letů,
oddělit úroveň a rozdíl síly, a rozdělit data na kalibrační a nezávislou ověřovací
část. Potom testovat citlivost tempa a pravděpodobnosti konce výměny při zachování
kontroly, únavy, stylu a determinismu. Tisíce simulací zpřesňují výsledek modelu;
samy nepotvrzují, že model vystihuje skutečný squash.

## Reprodukce a omezení

`PYTHONPATH=src python scripts/audit_match_realism.py --samples 500 --workers 4 --output <new-directory>`

Původní běh: místní commit `c2582ec52b7c5144e1df3777f1cbcf84414fdb24`, obsahově
odpovídající PR #688. Souhrn je v `match_realism_audit_2026-09-08.json`.
Skript vytváří také CSV po zápasech včetně seedů a rally-log hashů; úplné logy
se v auditní dávce nearchivují, lze je reprodukovat na stejné verzi enginu.
Naměřený běh trval 133,78 s se čtyřmi procesy v tomto prostředí; nejde o obecnou
výkonnostní garanci. Tři testy ověřují měřicí skript, nikoliv empirickou realističnost.
Audit nepokrývá průchod sezonou, dlouhodobý vývoj, opakované zápasy s přenesenou
únavou, skutečné zranění, správné četnosti let/stroke ani kalibraci fyziologie.
