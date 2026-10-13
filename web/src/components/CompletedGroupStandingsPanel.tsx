import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  generateAdminCompletedGroupStandings, getAdminCompletedGroupStandings,
  getAdminGroupTieResolutionState,
} from '../api/client'
import { newCommandId } from '../admin/branchSimulation'
import { GroupTieResolutionEditor } from './GroupTieResolutionEditor'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { useLanguage } from '../i18n/LanguageContext'

type Props = { runId: string; branchId: string; eventId: string; enabled: boolean }

/**
 * Never derives positions from current matches or fabricated scorelines:
 * renders only immutable production Group Standings authority.
 */
export function CompletedGroupStandingsPanel({
  runId, branchId, eventId, enabled,
}: Props): JSX.Element {
  const client = useQueryClient()
  const {language}=useLanguage(),cs=language==='cs'
  const [confirmed, setConfirmed] = useState(false)
  const [commandId, setCommandId] = useState(() => newCommandId())
  const key = ['admin-completed-group-standings', runId, branchId, eventId]
  const standings = useQuery({
    queryKey: key,
    queryFn: () => getAdminCompletedGroupStandings(runId, branchId, eventId),
    enabled: enabled && Boolean(runId && branchId && eventId),
    retry: false,
  })
  const absent = isApiNotFound(standings.error)
  const tieState = useQuery({
    queryKey: ['admin-group-tie-resolution', runId, branchId, eventId],
    queryFn: () => getAdminGroupTieResolutionState(runId, branchId, eventId),
    enabled: enabled && absent && Boolean(runId && branchId && eventId),
    retry: false,
  })
  const unresolved = tieState.data?.unresolved_case
  const generate = useMutation({
    mutationFn: () => generateAdminCompletedGroupStandings(runId, branchId, eventId, commandId),
    onSuccess: async (data) => {
      client.setQueryData(key, data)
      setConfirmed(false)
      setCommandId(newCommandId())
      await Promise.all([
        client.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId, eventId] }),
        client.invalidateQueries({ queryKey: ['admin-group-tie-resolution', runId, branchId, eventId] }),
      ])
    },
    onError: async () => {
      await tieState.refetch()
    },
  })

  useEffect(() => {
    setConfirmed(false)
    setCommandId(newCommandId())
  }, [runId, branchId, eventId])

  return <section className="panel" aria-label={cs?'Potvrzené konečné tabulky skupin':'Canonical completed group standings'}>
    <h3>{cs?'Konečné tabulky skupin':'Completed group standings'}</h3>
    <p>{cs?'Neměnná konečná tabulka vzniká jen z odehraných autoritativních zápasů a výslovného rozhodnutí shod, nikoli z odhadu podle rozpisu.':
      'This is a final, immutable table derived from authoritative played match results and explicit tie decisions, never an estimate from the Match Schedule.'}</p>
    {standings.isPending && enabled ? <p role="status">{cs?'Načítám potvrzené tabulky skupin…':'Loading frozen group tables…'}</p> : null}
    {standings.error && !absent ? (
      <p role="alert">{cs?'Tabulky skupin nebylo možné ověřit: ':'Frozen Group Standings could not be verified: '}{formatApiError(standings.error)}</p>
    ) : null}
    {standings.data ? (
      <>
        <p role="status">{cs?'Potvrzená autorita':'Frozen authority'}: <code>{standings.data.authority_fingerprint}</code></p>
        {standings.data.groups.map(group => (
          <div key={group.group_index}>
            <h4>{cs?'Skupina':'Group'} {group.group_index}</h4>
            <table aria-label={cs?`Konečná tabulka skupiny ${group.group_index}`:`Canonical group ${group.group_index} standings`}>
              <thead><tr><th>{cs?'Poř.':'Pos.'}</th><th>{cs?'ID hráče':'Player ID'}</th><th>{cs?'V':'W'}</th><th>{cs?'P':'L'}</th><th>{cs?'Body skupiny':'Group pts'}</th><th>{cs?'Sety':'Games'}</th><th>{cs?'Míče':'Points'}</th></tr></thead>
              <tbody>{group.rows.map(row => (
                <tr key={row.player_id}>
                  <td>{row.position}</td>
                  <td><code>{row.player_id}</code></td>
                  <td>{row.wins}</td><td>{row.losses}</td><td>{row.group_points}</td>
                  <td>{row.games_won}–{row.games_lost}</td>
                  <td>{row.points_won}–{row.points_lost}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ))}
        <p className="status">{cs?'Tato tabulka není uloženou revizí, dokud neproběhne úspěšné Simulation Save.':
        'This table is not a Saved Revision until Simulation Save succeeds.'}</p>
      </>
    ) : null}
    {absent && !standings.data ? (
      <div className="grid">
        <p role="status">{cs?'Není uložena žádná konečná tabulka skupin. Samotný rozpis není výsledkem.':
          'No completed group-table authority is stored. The Match Schedule alone is not a result.'}</p>
        <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>
          {cs?'Otevřít autoritativní simulaci a odehrát všechna kola skupin':'Open authoritative Simulation to play all group Match Days'}
        </Link></p>
        {unresolved ? <>
          <p role="alert">
            {cs?'Skupina':'Group'} {unresolved.group_index}{cs?' má nerozhodnou shodu hráčů':' has an unresolved tie among'}
            {' '}{unresolved.player_ids.join(', ')} ({unresolved.reason}).
            {cs?'Je nutné výslovně a auditovatelně určit pořadí; automatické rozhodnutí není povoleno.':
              'An explicit audited Admin ordering is required; no automatic ordering is permitted.'}
          </p>
          <GroupTieResolutionEditor
            key={[runId, branchId, eventId, tieState.data?.unresolved_case_fingerprint].join(':')}
            runId={runId} branchId={branchId} eventId={eventId}
            tieState={tieState.data!}
            enabled={enabled && absent}
            onResolution={async () => {
              setConfirmed(false)
              await Promise.all([
                client.invalidateQueries({ queryKey: ['admin-group-tie-resolution', runId, branchId, eventId] }),
                client.invalidateQueries({ queryKey: ['admin-completed-group-standings', runId, branchId, eventId] }),
              ])
            }}
          />
        </> : null}
        {tieState.error && !isApiNotFound(tieState.error) &&
          (tieState.error as { status?: number }).status !== 409 ? (
          <p role="alert">{cs?'Stav řešení shody není dostupný: ':'Tie-resolution status unavailable: '}{formatApiError(tieState.error)}</p>
        ) : null}
        <label><input type="checkbox" checked={confirmed}
          aria-label={cs?'Potvrdit generování ze všech odehraných zápasů skupin':'Confirm generation from all completed canonical group matches'}
          onChange={e => setConfirmed(e.target.checked)}/>
          {cs?'Potvrdit generování ze všech odehraných zápasů skupin':
            'Confirm generation from all completed canonical group matches'}
        </label>
        <button type="button"
          disabled={!confirmed || !enabled || Boolean(unresolved) || generate.isPending ||
            !tieState.isSuccess || tieState.data?.unresolved_case !== null}
          onClick={() => generate.mutate()}>
          {cs?'Vytvořit konečné tabulky skupin':'Generate canonical group standings'}
        </button>
        {generate.error ? <p role="alert">{cs?'Vytvoření tabulek skupin bylo zablokováno: ':
          'Group Standings generation blocked: '}{formatApiError(generate.error)}</p> : null}
      </div>
    ) : null}
  </section>
}
