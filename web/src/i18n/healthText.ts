/** Present-time Admin Health copy. Values in user-authored records remain verbatim. */
const cs: Record<string,string> = {
  'Canonical Player Health':'Zdraví hráče','Loading canonical Health state…':'Načítání zdraví…','Branch':'Větev','Week':'Týden',
  'Health records':'Zdravotní záznamy','Permanent consequences':'Trvalé následky','Draft version':'Verze konceptu',
  'The Active Admin Branch is read-only. Health can be inspected but not edited.':'Aktivní Admin větev je jen pro čtení. Zdraví lze prohlížet, ale ne upravovat.',
  'No Injury or Illness records are present at this Week.':'V tomto týdnu nejsou žádné záznamy zranění ani nemocí.',
  'Type':'Typ','Condition':'Stav','Lifecycle':'Fáze','Severity':'Závažnost','Domains':'Oblasti','Origin':'Původ','Source':'Zdroj','Pre-start':'Před začátkem',
  'Edit current Health':'Upravit zdraví','Reviewed Health edit':'Kontrolovaná úprava zdraví',
  "This replaces the selected player's complete Health profile at the current authoritative Week. Historical predecessor state is not rewritten.":'Nahrazuje celý zdravotní profil hráče v aktuálním týdnu. Předchozí historické stavy zůstávají zachované.',
  'Edit mode':'Režim úpravy','Pre-start input':'Počáteční vstup','Current-state correction':'Oprava současného stavu','Mode: current-state correction':'Režim: oprava současného stavu',
  'No records. Add an Injury or Illness below.':'Žádné záznamy. Níže lze přidat zranění nebo nemoc.',
  'Record':'Záznam','Record ID':'ID záznamu','Condition key':'Označení stavu','Severity 0–100':'Závažnost 0–100','Affected domains (comma separated)':'Zasažené oblasti (oddělené čárkou)',
  'Started before Run':'Začalo před Runem','Onset season':'Sezona vzniku','Onset week':'Týden vzniku','Recovered season':'Sezona uzdravení','Recovered week':'Týden uzdravení',
  'Recurrence of':'Opakování záznamu','None':'Žádné','Recovery estimate min weeks':'Odhad zotavení: nejméně týdnů','Recovery estimate max weeks':'Odhad zotavení: nejvýše týdnů',
  'Provenance':'Původ informace','Remove record':'Odstranit záznam','Add Health record':'Přidat zdravotní záznam','No permanent consequences.':'Žádné trvalé následky.',
  'Consequence':'Následek','Consequence ID':'ID následku','Recovered source record':'Zdrojový vyléčený záznam','Select source':'Vyber zdroj','Limitation severity 1–100':'Závažnost omezení 1–100',
  'Remove consequence':'Odstranit následek','Add permanent consequence':'Přidat trvalý následek','Audit and review':'Audit a kontrola','Operator label':'Označení operátora','Reason':'Důvod',
  'I reviewed the complete current Health profile and this correction.':'Zkontroloval/a jsem celý zdravotní profil a tuto úpravu.',
  'Calculate Health preview':'Připravit náhled zdraví','Cancel edit':'Zrušit úpravu','Calculating Health preview…':'Příprava náhledu…','Review Health preview':'Kontrola návrhu zdraví',
  'Records after':'Záznamů po změně','Consequences after':'Následků po změně','Before':'Před změnou','After':'Po změně','After component':'Výsledek','Preview fingerprint:':'Otisk návrhu:',
  'Confirm reviewed Health edit':'Potvrdit návrh zdraví','Retry exact Health commit':'Opakovat přesně tuto úpravu','Edit inputs and recalculate':'Upravit vstupy a přepočítat','Committing Health edit…':'Potvrzování úpravy…',
  'No automatic write retry. Reload and inspect, or explicitly approve the exact retry.':'Zápis se automaticky neopakuje. Načti a zkontroluj stav, případně výslovně schval přesné opakování.',
  'Save Health Revision':'Uložit zdravotní revizi','Checking Health Save state…':'Kontrola možnosti uložení…','Health Save state unavailable:':'Podklady pro uložení nejsou dostupné:',
  'Health differs from the current Saved Revision.':'Zdraví se liší od uložené revize.','Current Health is already captured by the Saved Revision.':'Současné zdraví je již uložené.',
  'Saving Health Revision…':'Ukládání zdravotní revize…','Confirm Health changes':'Schválit zdravotní změny','I approve these reviewed Health changes.':'Schvaluji tyto zkontrolované zdravotní změny.',
  'Confirm Health Save':'Schválit uložení zdraví','Save this Health draft in a new revision.':'Uložit tento zdravotní koncept do nové revize.',
  'Run calendar':'Kalendář Runu','offset':'posun','seasons':'sezon','Historical FAX calendar':'Historický kalendář FAX','Complete change for this player':'Úplná změna pro tohoto hráče',
  'This exact Health edit was already committed.':'Tato přesná úprava již byla potvrzena.',
  'Health edit committed to the Working Draft. Save a Health Revision to make it recoverable.':'Zdravotní úprava je v pracovním konceptu. Pro možnost obnovy ulož zdravotní revizi.',
  'Health Saved Revision created.':'Zdravotní revize byla uložena.','Injury':'Zranění','Illness':'Nemoc','At Risk':'Riziko','Active':'Aktivní','Recovering':'Zotavování','Recovered':'Vyléčeno',
  'Health edit preview':'Náhled zdravotní úpravy','Edit current Player Health':'Úprava zdraví hráče','Current Health records':'Současné zdravotní záznamy','Permanent Health consequences':'Trvalé zdravotní následky','Save Player Health revision':'Uložení zdravotní revize',
  'State':'Stav','Health state unavailable:':'Zdravotní stav není dostupný:',
}
export function healthText(en:string,locale:'cs'|'en') {return locale==='cs' ? cs[en] ?? en : en}

export function healthIssue(issue:string,locale:'cs'|'en') {
  if(locale==='en')return issue
  if(issue==='Operator label is required.')return 'Vyplň označení operátora.'
  if(issue==='Audit reason is required.')return 'Vyplň důvod úpravy.'
  if(issue==='Explicit review confirmation is required.')return 'Výslovně potvrď kontrolu vstupů.'
  if(issue.includes('future'))return 'Zdravotní fakt nesmí ležet v budoucnosti.'
  if(issue.includes('zero acute'))return 'Vyléčený záznam musí mít nulovou akutní závažnost.'
  if(issue.includes('season/week'))return 'Vyplň platnou sezonu a týden podle kalendáře Runu.'
  if(issue.includes('started before'))return 'Počáteční vstup musí být výslovně označen jako stav před Runem a nesmí mít týden vzniku.'
  if(issue.includes('provenance'))return 'Vyplň původ informace u každého záznamu i následku.'
  if(issue.includes('condition key'))return 'Vyplň označení zdravotního stavu.'
  if(issue.includes('domain'))return 'Vyplň alespoň jednu zasaženou oblast.'
  if(issue.includes('recovery window'))return 'Odhad zotavení vyžaduje obě hranice, 0 až 520 týdnů, minimum nejvýše maximum.'
  if(issue.includes('severity'))return 'Závažnost musí být celé číslo v povoleném rozsahu.'
  if(issue.includes('Recovered'))return 'Datum uzdravení a trvalé následky vyžadují vyléčený zdrojový záznam.'
  if(issue.includes('unique')||issue.includes('ID'))return 'Identifikátory musí být vyplněné a jedinečné.'
  return 'Zkontroluj konzistenci zdravotních záznamů, dat a jejich vazeb.'
}
