import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { getSavedDrawEntryEvidence, getSavedDrawNativePreflight } from '../api/client'
import {
  sameSavedDrawSource, validSavedDrawEntryEvidence, validSavedDrawPreflight
} from '../api/savedNativeReadiness'
import type { SavedDrawEntrant, SavedDrawPreflight } from '../api/savedNativeReadiness'
import { formatApiError } from '../utils/apiErrors'

type Props = {
  runId: string
  branchId: string
  /** Must be the Branch's current Saved head; the backend rejects any other revision. */
  revisionId: string
  eventId: string
  season: string
  cs: boolean
  renderPlayer?: (playerId: string) => ReactNode
}

export function SavedDrawNativeReadiness(
  { runId, branchId, revisionId, eventId, season, cs, renderPlayer }: Props
): JSX.Element {
  const key = [runId, branchId, revisionId, eventId, season]
  const preflightQuery = useQuery({
    queryKey: ['saved-draw-native-preflight', ...key],
    queryFn: () => getSavedDrawNativePreflight(runId, branchId, eventId, season, revisionId),
    retry: false
  })
  const evidenceQuery = useQuery({
    queryKey: ['saved-draw-entry-evidence', ...key],
    queryFn: () => getSavedDrawEntryEvidence(runId, branchId, eventId, season, revisionId),
    retry: false
  })
  const title = cs ? 'Nativní připravenost uloženého Draw' : 'Saved Draw native readiness'
  const intro = cs
    ? 'Pouze čtení z aktuální uložené revize. Nevytváří Entry, nepřijímá Draw do nativního běhu a nemění pořadí ani body.'
    : 'Read-only view of the current Saved revision. It creates no Entry, adopts nothing into native play and changes no ranking or points.'

  if (preflightQuery.isPending || evidenceQuery.isPending) {
    return <section aria-label={title}><h4>{title}</h4>
      <p role="status">{cs ? 'Načítám připravenost…' : 'Loading readiness…'}</p></section>
  }
  const failure = preflightQuery.error ?? evidenceQuery.error
  if (failure) {
    // Most Saved Draws are outside the supported source geometry; that is information, not a fault.
    return <section aria-label={title}><h4>{title}</h4><p>{intro}</p>
      <p role="status">{cs
        ? 'Pro tento uložený Draw není nativní připravenost dostupná: '
        : 'Native readiness is unavailable for this Saved Draw: '}{formatApiError(failure)}</p>
    </section>
  }
  const preflight = preflightQuery.data
  const evidence = evidenceQuery.data
  if (!validSavedDrawPreflight(preflight, revisionId) ||
    !validSavedDrawEntryEvidence(evidence, revisionId, eventId, { runId, branchId }) ||
    !sameSavedDrawSource(preflight, evidence)) {
    return <section aria-label={title}><h4>{title}</h4>
      <p role="alert">{cs
        ? 'Odpověď neodpovídá požadované uložené revizi, Edici nebo zdroji Draw a nebyla zobrazena.'
        : 'The response does not match the requested Saved revision, Edition or Draw source and was not displayed.'}</p>
    </section>
  }
  const entered = evidence.entrants.filter(row => row.first_entry !== null)
  const missing = evidence.entrants.length - entered.length
  const player = (id: string) => renderPlayer ? renderPlayer(id) : id
  return <section aria-label={title}>
    <h4>{title}</h4>
    <p>{intro}</p>
    <p role="status">{executionText(preflight, cs)}</p>
    <dl>
      <dt>{cs ? 'Ranking' : 'Ranking status'}</dt>
      <dd>{preflight.ranking_status === 'ranked'
        ? (cs ? 'Ranked' : 'Ranked') : (cs ? 'Unranked' : 'Unranked')}</dd>
      <dt>{cs ? 'Tabulka bodů' : 'Point table'}</dt>
      <dd>{pointTableText(preflight, cs)}</dd>
    </dl>
    {preflight.missing_point_stages.length > 0 && <p>
      {cs ? 'Chybějící fáze: ' : 'Missing stages: '}{preflight.missing_point_stages.join(', ')}</p>}
    {preflight.invalid_point_stages.length > 0 && <p>
      {cs ? 'Neplatné fáze: ' : 'Invalid stages: '}{preflight.invalid_point_stages.join(', ')}</p>}
    <h5>{cs ? 'Doložený první Tour Entry' : 'Recorded first Tour Entry'}</h5>
    <p role="status">{cs
      ? `Účastníci: ${evidence.entrants.length} · s doloženým prvním Entry: ${entered.length} · bez: ${missing}`
      : `Participants: ${evidence.entrants.length} · with recorded first Entry: ${entered.length} · without: ${missing}`}</p>
    <p>{cs
      ? 'Doklad pochází z této uložené revize a popisuje historický první vstup, ne dnešní profesionální status.'
      : 'Evidence comes from this Saved revision and describes a historical first entry, not today\u2019s professional status.'}</p>
    <p>{cs
      ? 'U Runů s pravidlem Master v87 (výchozí pro nové Runy) musí být každý účastník Ranked i Unranked Edice profesionál v cílovém životním cyklu; k tomu slouží samostatná událost Turn Pro, přihláška ji nezakládá. U Runů s historickým pravidlem vyžaduje Ranked přijetí nativní Tour Entry každého účastníka. Tento přehled nic z toho nevytváří ani neověřuje.'
      : 'In Runs under Master v87 (the default for new Runs) every participant of a Ranked or Unranked Edition must be a professional in the target lifecycle, through the separate Turn Pro event; an application does not create it. In Runs under the historical rule, Ranked adoption requires a native Tour Entry for every participant. This view neither creates nor verifies either.'}</p>
    <div className="table-responsive"><table>
      <thead><tr>
        <th>{cs ? 'Hráč' : 'Player'}</th><th>{cs ? 'Role v Draw' : 'Draw role'}</th>
        <th>{cs ? 'První Entry' : 'First Entry'}</th></tr></thead>
      <tbody>{evidence.entrants.map(row => <tr key={row.player_id}>
        <td>{player(row.player_id)}</td><td>{roleText(row.draw_role, cs)}</td>
        <td>{entryText(row, eventId, cs)}</td></tr>)}</tbody>
    </table></div>
  </section>
}

function executionText(p: SavedDrawPreflight, cs: boolean): string {
  switch (p.native_execution_status) {
    case 'requires_adoption_preview':
      return cs
        ? 'Geometrie Draw splňuje předpoklady pro samostatný náhled přijetí. Přijetí je zvláštní explicitní příkaz.'
        : 'The Draw geometry meets the prerequisites for a separate adoption preview. Adoption itself is a separate explicit command.'
    case 'ranked_points_incomplete':
      return cs
        ? 'Ranked tabulka bodů je neúplná nebo neplatná; přijetí není možné.'
        : 'The Ranked point table is incomplete or invalid; adoption is not possible.'
    case 'ranked_not_supported':
      return cs
        ? 'Nativní Ranked provedení této Edice zatím není podporováno (týden nebo délka).'
        : 'Native Ranked execution is not yet supported for this Edition (week or duration).'
  }
}

function pointTableText(p: SavedDrawPreflight, cs: boolean): string {
  if (p.point_table_status === 'not_required') return cs ? 'Není vyžadována' : 'Not required'
  return p.point_table_status === 'complete'
    ? (cs ? 'Úplná' : 'Complete') : (cs ? 'Neúplná' : 'Incomplete')
}

function roleText(role: SavedDrawEntrant['draw_role'], cs: boolean): string {
  if (role === 'direct_main') return cs ? 'Přímo do hlavní části' : 'Direct Main'
  return role === 'qualification' ? (cs ? 'Kvalifikace' : 'Qualification')
    : (cs ? 'Divoká karta' : 'Wild card')
}

function entryText(row: SavedDrawEntrant, eventId: string, cs: boolean): string {
  const t = row.first_entry
  if (t === null) {
    return cs ? 'V této uložené revizi není doloženo' : 'Not established by this Saved revision'
  }
  const kind = t.trigger_kind === 'valid_tournament_application'
    ? (cs ? 'platná přihláška' : 'valid application')
    : (cs ? 'definitivní divoká karta' : 'definitive wild card')
  const where = t.event_id === eventId
    ? (cs ? 'tato Edice' : 'this Edition')
    : (cs ? `jiná Edice ${t.event_id}` : `another Edition ${t.event_id}`)
  return `${kind} · ${where} · ${cs ? 'index sezóny' : 'season index'} ${t.trigger_week.season_index}`
    + ` · ${cs ? 'týden' : 'week'} ${t.trigger_week.week}`
}
