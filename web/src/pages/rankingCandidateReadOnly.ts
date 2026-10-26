import type { Language } from '../i18n/LanguageContext'
import type { CandidateWeek, RankingCandidateHistory, RankingCandidateInputs, RankingCandidateSources } from '../api/rankingCandidates'

// Deliberately page-local; never translate persisted identifiers, fingerprints or server values.
const cs: Record<string, string> = {
  'Week': 'Týden',
  'Ranking candidates': 'Kandidáti žebříčku',
  'Unpublished preparation history. Viewing does not publish rankings or advance time.': 'Historie nepublikovaných příprav. Prohlížení nepublikuje žebříčky ani neposouvá čas.',
  'Back to Branches': 'Zpět na větve',
  'Invalid season or week.': 'Neplatná sezona nebo týden.',
  'Loading ranking history…': 'Načítání historie kandidátů…',
  'Retry loading': 'Zkusit načíst znovu',
  'Refresh candidates': 'Obnovit kandidáty',
  'Candidate weeks': 'Týdny kandidátů',
  'No ranking candidates have been prepared for this Branch.': 'Pro tuto větev zatím nebyli připraveni žádní kandidáti žebříčku.',
  'No candidate is stored for this week.': 'Pro tento týden není uložen žádný kandidát.',
  'Select a week to inspect its ranking.': 'Vyber týden pro zobrazení kandidáta.',
  'players': 'hráčů', 'points': 'bodů', 'Branch': 'Větev',
  'Best': 'Nejlepších',
  'Unpublished candidate': 'Nepublikovaný kandidát',
  'Not Official Ranking': 'Nikoli Official Ranking',
  'This candidate contains no ranked players.': 'Tento kandidát neobsahuje žádné klasifikované hráče.',
  'Candidate ranking table': 'Tabulka kandidáta žebříčku',
  'Rank': 'Pořadí', 'Player ID': 'ID hráče', 'Points': 'Body',
  'Counted results': 'Započítané výsledky',
  'active disciplinary zeros': 'aktivních disciplinárních nul',
  'tournament result slots available.': 'dostupných slotů pro turnajové výsledky.',
  'effective': 'účinné od', 'for': 'po dobu', 'weeks': 'týdnů',
  'No counted results': 'Žádné započítané výsledky',
  'counted results for': 'započítaných výsledků hráče',
  'qualification': 'kvalifikace', 'main': 'hlavní soutěž',
  'Completed': 'Dokončeno', 'first publication': 'první zveřejnění',
  'validity': 'platnost',
  'Technical provenance': 'Technický původ dat',
  'Policy': 'Pravidla', 'Fingerprint': 'Fingerprint',
  'Commands': 'Příkazy', 'No command receipt': 'Žádný záznam příkazu',
  'Historical ranking sources': 'Historické zdroje žebříčku',
  'Source results': 'Zdrojové výsledky',
  'Results effective for this candidate week, including results outside Best N. Later corrections are excluded.': 'Výsledky účinné pro tento týden, včetně výsledků mimo Best N. Pozdější opravy nejsou zahrnuty.',
  'Load source results': 'Načíst zdrojové výsledky',
  'Loading source results…': 'Načítání zdrojových výsledků…',
  'Refresh source results': 'Obnovit zdrojové výsledky',
  'Retry source results': 'Zkusit znovu načíst zdroje',
  'No source results at this boundary.': 'K tomuto okamžiku nejsou žádné zdrojové výsledky.',
  'Counted': 'Započítáno',
  'Not counted in this candidate': 'Do tohoto kandidáta nezapočítáno',
  'Effective': 'Účinné od', 'First publication': 'První zveřejnění',
  'Validity': 'Platnost',
  'Source provenance': 'Původ zdroje',
  'Source': 'Zdroj', 'Version': 'Verze', 'Previous version': 'Předchozí verze',
  'Initial result': 'První výsledek',
  'Ranking history does not match this candidate.': 'Historie žebříčku neodpovídá tomuto kandidátovi.',
  'Source history does not match this candidate.': 'Historie zdrojů neodpovídá tomuto kandidátovi.',
  'Stored inputs do not match this candidate.': 'Uložené vstupy neodpovídají tomuto kandidátovi.',
  'Stored calculation inputs': 'Uložené vstupy výpočtu',
  'Frozen roster and results supplied to this calculation, including players and results absent from the ranking.': 'Neměnná soupiska a výsledky předané výpočtu, včetně hráčů a výsledků mimo žebříček.',
  'Inspect stored inputs': 'Prohlédnout uložené vstupy',
  'Loading stored inputs…': 'Načítání uložených vstupů…',
  'Refresh stored inputs': 'Obnovit uložené vstupy',
  'Retry stored inputs': 'Zkusit znovu načíst vstupy',
  'Legacy candidate: complete calculation inputs were not stored. They cannot be reconstructed from current data.': 'Starší kandidát: úplné vstupy výpočtu nebyly uloženy. Z aktuálních dat je nelze rekonstruovat.',
  'Verified: stored inputs reproduce this candidate. This does not verify completeness against the entire world.': 'Ověřeno: uložené vstupy reprodukují tohoto kandidáta. Neznamená to ověření úplnosti celého světa.',
  'Stored inputs have no verified manifest.': 'Uložené vstupy nemají ověřený manifest.',
  'Preparation audit': 'Audit přípravy',
  'No preparation audit was recorded for this candidate.': 'Pro tohoto kandidáta nebyl zaznamenán audit přípravy.',
  'Preparation command': 'Příkaz přípravy',
  'Why equal-point players are ordered this way': 'Proč jsou hráči se stejnými body v tomto pořadí',
  'Tie explanations are unavailable from this server.': 'Vysvětlení rovnosti bodů server neposkytuje.',
  'No adjacent players have equal points.': 'Žádní sousední hráči nemají stejný počet bodů.',
  'precedes': 'je před', 'at': 's', 'versus': 'oproti',
  'Counted points at result slot': 'Započítané body na výsledkovém slotu',
  'Newer completion at result slot': 'Novější dokončení na výsledkovém slotu',
  'Previous Official position': 'Předchozí pořadí v Official Ranking',
  'Stored tie-break token': 'Uložený rozřazovací token',
  'None': 'Žádná hodnota', 'Missing': 'Chybí',
  'Stored roster': 'Uložená soupiska',
  'The stored roster is empty.': 'Uložená soupiska je prázdná.',
  'Entry': 'Vstup',
  'Retired at this boundary': 'K tomuto okamžiku ukončil kariéru',
  'Not retired at this boundary': 'K tomuto okamžiku neukončil kariéru',
  'Resolved disciplinary zero inputs': 'Vyhodnocené vstupy disciplinárních nul',
  'Each active zero reserves one Best N slot. These are stored inputs, not an automatic sanction decision.': 'Každá aktivní nula zabírá jeden slot Best N. Jde o uložené vstupy, nikoli automatické rozhodnutí o trestu.',
  'Disciplinary source': 'Zdroj disciplinárního rozhodnutí',
  'Disciplinary decision history': 'Historie disciplinárních rozhodnutí',
  'Verified against the stored decisions effective by this ranking week. Later changes are excluded.': 'Ověřeno vůči uloženým rozhodnutím účinným do tohoto týdne. Pozdější změny nejsou zahrnuty.',
  'No zero decisions were effective by this week.': 'Do tohoto týdne nebyla účinná žádná rozhodnutí o nulách.',
  'Zeros were supplied by the caller. This candidate does not verify their provenance against stored decision history.': 'Nuly předal volající. Kandidát neověřuje jejich původ vůči uložené historii rozhodnutí.',
  'Decision history verification is unavailable from this server.': 'Ověření historie rozhodnutí není na tomto serveru dostupné.',
  'Version effective': 'Verze účinná od',
  'Original start': 'Původní počátek', 'Duration': 'Doba trvání',
  'Replaced by a later version at this boundary.': 'K tomuto okamžiku nahrazeno novější verzí.',
  'Expired at this boundary.': 'K tomuto okamžiku skončila platnost.',
  'Active: reserves one Best N slot.': 'Aktivní: zabírá jeden slot Best N.',
  'Active decision; player is outside this ranking.': 'Aktivní rozhodnutí; hráč není v tomto žebříčku.',
  'Decision provenance': 'Původ rozhodnutí',
  'Initial decision': 'První rozhodnutí',
  'Stored result inputs': 'Uložené vstupy výsledků',
  'No result inputs were supplied.': 'Nebyly předány žádné výsledkové vstupy.',
  'Award': 'Přiděleno', 'Ranked result': 'Klasifikovaný výsledek',
  'Unranked result': 'Neklasifikovaný výsledek',
  'Stored source fingerprint': 'Uložený fingerprint zdroje',
}

export function tr(english: string, language: Language): string {
  return language === 'cs' ? cs[english] ?? english : english
}

export function weekLabel(w: CandidateWeek, language: Language): string {
  return String(2000 + w.season_index) + '/' + String(2001 + w.season_index).slice(-2) +
    ' · ' + tr('Week', language) + ' ' + w.week
}

export function sameWeek(actual: CandidateWeek | null | undefined, expected: CandidateWeek): boolean {
  return actual?.season_index === expected.season_index && actual?.week === expected.week
}

export function validCandidateHistory(data: RankingCandidateHistory, runId: string, branchId: string): boolean {
  return data?.run_id === runId && data.branch_id === branchId &&
    data.publication_status === 'candidate_only' && Array.isArray(data.candidates) &&
    data.candidates.every(c => c?.publication_status === 'candidate_only' &&
      typeof c.fingerprint === 'string' && c.fingerprint.length > 0 &&
      c.snapshot?.run_id === runId && c.snapshot.branch_id === branchId &&
      Number.isInteger(c.snapshot.week?.season_index) && Number.isInteger(c.snapshot.week?.week) &&
      Array.isArray(c.snapshot.rows) &&
      c.snapshot.rows.every(row => !row.disciplinary_zeros?.some(z => z.run_id !== runId || z.branch_id !== branchId)))
}

export function validCandidateResponse(
  data: RankingCandidateSources | RankingCandidateInputs,
  runId: string, branchId: string, week: CandidateWeek, fingerprint: string,
): boolean {
  if (!data || data.run_id !== runId || data.branch_id !== branchId ||
      !sameWeek(data.week, week) || data.publication_status !== 'candidate_only' ||
      data.candidate_fingerprint !== fingerprint) return false
  if ('sources' in data) {
    return Array.isArray(data.sources) && data.sources.every(s =>
      s.version?.run_id === runId && s.version.branch_id === branchId)
  }
  return data.verification_status === 'legacy_without_manifest'
    ? data.manifest === null
    : data.verification_status === 'complete_manifest' &&
      data.manifest !== null && Array.isArray(data.manifest?.players) &&
      Array.isArray(data.manifest?.results) &&
      !data.manifest?.disciplinary_zeros?.some(z => z.run_id !== runId || z.branch_id !== branchId) &&
      !data.zero_sources?.some(s => s.version.zero.run_id !== runId || s.version.zero.branch_id !== branchId)
}

// Numeric zero, null and an absent field must remain distinguishable.
export function storedValue(value: number | string | null | undefined, language: Language): string {
  return value === null ? tr('None', language) : value === undefined ? tr('Missing', language) : String(value)
}
