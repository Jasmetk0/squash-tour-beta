import type { Language } from './LanguageContext'

const czech: Readonly<Record<string, string>> = {
  'Resumable Full Simulation parents': 'Obnovitelné původní příkazy Full Simulation',
  'These durable parents survived page/process state loss. Resume the exact parent instead of creating a new Full Simulation command.': 'Uložené původní příkazy zůstávají zachovány po zavření stránky nebo procesu. Pokračuj s přesně stejným příkazem.',
  'Pausing…': 'Pozastavuji…',
  'Paused': 'Pozastaveno',
  'completed season(s)': 'dokončených sezon',
  'Current': 'Aktuálně',
  'Resolve': 'Vyřeš',
  'Authorized – invocation activity unverified': 'Povoleno – aktivita výpočtu nepotvrzena',
  'Resume this Full Simulation': 'Připravit pokračování stejné Full Simulation',
  'Acknowledge safe pause': 'Ověřit bezpečné pozastavení',
  'Authorize resume': 'Povolit pokračování',
  'Request safe pause': 'Pozastavit bezpečně',
  'Stop simulation': 'Ukončit simulaci',
  'Change week target': 'Změnit cílový týden',
  'Change Full Simulation week target': 'Změnit cílový týden Full Simulation',
  'The new target is the START of the selected week (season index 0 = 2000/01). No sport from that week will be simulated by this parent. Original command and Saved Revisions remain unchanged.': 'Novým cílem je ZAČÁTEK vybraného týdne (index sezony 0 = 2000/01). Tento původní příkaz už nebude simulovat sport z tohoto týdne. Původní zadání ani uložené revize se nemění.',
  'Target season index (0–49)': 'Index cílové sezony (0–49)',
  'Target week (1–61)': 'Cílový týden (1–61)',
  'Target change operator': 'Operátor změny cíle',
  'Target change audit reason': 'Důvod změny cíle do auditu',
  'Apply week target': 'Použít nový cílový týden',
  'Stop Full Simulation': 'Ukončení Full Simulation',
  'Stop original simulation': 'Ukončit původní simulaci',
  'Confirm permanent stop': 'Potvrzuji ukončení této simulace; dokončené výsledky zůstanou zachované a Save je ruční.',
  'Stopping permanently prevents resuming this parent. The current committed child results persist. No automatic Save.': 'Ukončení trvale znemožní pokračovat v tomto původním příkazu. Potvrzené výsledky zůstanou zachované. Save se neprovede automaticky.',
  'Full Simulation stopped safely; original command cannot resume. Save remains manual.': 'Simulace byla bezpečně ukončena; původní příkaz už nelze obnovit. Save je ruční.',
  'Full Simulation pause or resume': 'Pozastavení nebo pokračování Full Simulation',
  'This controls the original command in this Run and Branch. Pause is acknowledged at a safe transaction boundary. Completed child results and the original target persist. No implicit Save.': 'Ovládání se týká původního příkazu v tomto Runu a větvi. Pauza se potvrzuje na bezpečné hranici transakce. Dokončené výsledky a původní cíl zůstávají zachovány. Save vyžaduje výslovnou akci.',
  'Control request ID:': 'ID ovládacího příkazu:',
  'If the response is lost, retrying reuses this exact ID and cannot duplicate the audit event.': 'Při ztrátě odpovědi opakuj přesně stejný příkaz s tímto ID; nevznikne druhý auditní záznam.',
  'Operator': 'Operátor',
  'Audit reason': 'Důvod do auditu',
  'Full Simulation control operator': 'Operátor ovládání Full Simulation',
  'Full Simulation control audit reason': 'Důvod ovládání Full Simulation do auditu',
  'Request pause': 'Požádat o pauzu',
  'Resume same parent': 'Povolit pokračování původního příkazu',
  'Cancel': 'Zrušit',
  'Full Simulation paused at a safe transaction boundary.': 'Full Simulation je pozastavena na bezpečné hranici transakce.',
  'Authorize resume, then prepare and confirm continuation of the original command. Completed child results persist. Save remains explicit.': 'Povol pokračování, potom připrav a potvrď pokračování původního příkazu. Dokončené výsledky zůstávají zachovány. Save je samostatná výslovná akce.'
}

export function fullSimulationControlText(language: Language, text: string): string {
  return language === 'cs' ? czech[text] ?? text : text
}
