/** Read-only career match timeline; every page belongs to the current Saved HEAD. */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getSavedHomePlayerIdentities, getSavedPlayerMatchHistory } from '../api/client'

type Props = {
  runId: string
  branchId: string
  savedHead: string
  playerId: string
  locale: 'cs' | 'en'
}
const PAGE_SIZE = 20
const seasonText = (index: number): string =>
  `${2000 + index}/${String((2001 + index) % 100).padStart(2, '0')}`

export function SavedPlayerMatchesPanel({ runId, branchId, savedHead, playerId, locale }: Props): JSX.Element {
  const cs = locale === 'cs'
  const [season, setSeason] = useState<string>('all')
  const [page, setPage] = useState(0)
  const seasonIndex = season === 'all' ? null : Number(season)
  const q = useQuery({
    queryKey: ['saved-player-matches', runId, branchId, savedHead, playerId, seasonIndex, page],
    queryFn: () => getSavedPlayerMatchHistory(runId, branchId, playerId, seasonIndex, page * PAGE_SIZE, PAGE_SIZE),
    retry: false,
  })
  const scoped = q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.player_id === playerId &&
    q.data?.season_index === seasonIndex && q.data?.offset === page * PAGE_SIZE &&
    q.data?.limit === PAGE_SIZE
  const data = scoped ? q.data : null
  const opponentIds = data ? [...new Set(data.matches.map(match => match.opponent_player_id))] : []
  const opponents = useQuery({
    queryKey: ['saved-match-opponent-names', runId, branchId, savedHead, opponentIds.join('|')],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId, opponentIds),
    enabled: opponentIds.length > 0,
    retry: false,
  })
  const names = opponents.data?.saved_revision_id === savedHead &&
    opponents.data?.run_id === runId && opponents.data?.branch_id === branchId &&
    opponents.data?.requested_ids.join('|') === opponentIds.join('|') ?
    Object.fromEntries(opponents.data.players.map(value => [value.player_id, value.display_name])) : {}
  return <section aria-label="Saved player tournament matches">
    <h3>{cs ? 'Zápasová kariéra' : 'Match career'}</h3>
    {q.isPending && <p role="status">{cs ? 'Načítám zápasy…' : 'Loading matches…'}</p>}
    {q.error && <p role="alert" className="error">{cs ? 'Historie zápasů není dostupná.' : 'Match history is unavailable.'}</p>}
    {q.isSuccess && !scoped && <p role="alert" className="error">{cs ? 'Data patří jiné uložené revizi.' : 'Data does not match the selected Saved Revision.'}</p>}
    {data?.status === 'identity_unavailable' && <p className="status">{cs
      ? 'Bez ověřené identity nelze zobrazit zápasovou kariéru.'
      : 'Match history is hidden without a verified saved player identity.'}</p>}
    {data?.status === 'ready' && <>
      <p><strong>{cs ? 'Celá kariéra (odehráno)' : 'Career (played)'}</strong> ·
        {' '}{data.career_played_wins} W / {data.career_played_losses} L
        {' · '}{data.career_walkovers} {cs ? 'kontumací' : 'walkovers'}</p>
      <label htmlFor="saved-player-season">{cs ? 'Sezóna' : 'Season'}{' '}</label>
      <select data-run-navigation-readonly id="saved-player-season" aria-label={cs ? 'Sezóna zápasů' : 'Match season'}
        value={season} onChange={event => { setSeason(event.target.value); setPage(0) }}>
        <option value="all">{cs ? 'Všechny sezóny' : 'All seasons'}</option>
        {data.available_seasons.map(index => <option key={index} value={String(index)}>{seasonText(index)}</option>)}
      </select>
      <p className="status">{cs ? 'Výběr' : 'Selection'}: {data.played_wins} W / {data.played_losses} L
        {' · '}{data.walkovers} {cs ? 'kontumací' : 'walkovers'} ·
        {' '}{data.total_results} {cs ? 'zaznamenaných výsledků' : 'recorded results'}</p>
      {data.total_results === 0 && <p className="status">{cs
        ? 'Žádné uložené turnajové zápasy pro tento výběr.'
        : 'No saved tournament matches for this selection.'}</p>}
      {data.matches.length > 0 && <ul className="run-home-feed">
        {data.matches.map(match => <li key={match.event_id + ':' + match.match_id}>
          <span><strong>{match.event_name}</strong>
            {' '}<Link to={'/admin/runs/' + encodeURIComponent(runId) + '/people/' +
              encodeURIComponent(playerId) + '/matches/' + encodeURIComponent(match.event_id) +
              '/' + encodeURIComponent(match.match_id)}>
              {cs ? 'Detail zápasu →' : 'Match detail →'}
            </Link>
            <small>{match.season} · W{match.week} · {match.draw_type} ·
              {' '}{cs ? 'kolo' : 'round'} {match.round_number}</small>
            <small>{match.outcome === 'win' ? (cs ? 'Výhra' : 'Win') : (cs ? 'Prohra' : 'Loss')}
              {' · '}{names[match.opponent_player_id] || match.opponent_player_id}
              {' · '}{match.scoreline}
              {match.completion === 'walkover' ? (cs ? ' · kontumace' : ' · walkover') : ''}
            </small>
          </span>
        </li>)}
      </ul>}
      {data.total_results > PAGE_SIZE && <div className="run-home-status-block">
        <button type="button" disabled={page === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>
          {cs ? '← Předchozí' : '← Previous'}
        </button>
        {' '}{cs ? 'Strana' : 'Page'} {page + 1} / {Math.ceil(data.total_results / PAGE_SIZE)}{' '}
        <button type="button" disabled={!data.has_more} onClick={() => setPage(value => value + 1)}>
          {cs ? 'Další →' : 'Next →'}
        </button>
      </div>}
      <p className="status">{cs
        ? 'Pouze uzavřené kanonické turnaje z uložené revize. Volné losy jsou vyloučeny, kontumace se nepočítají jako odehrané zápasy. Pořadí v rámci týdne není časový rozpis.'
        : 'Only completed canonical tournaments in the Saved Revision. BYEs are excluded, walkovers are not counted as played matches. Same-week ordering is not an exact schedule.'}</p>
    </>}
  </section>
}
