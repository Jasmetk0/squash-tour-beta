/** Read-only career match timeline; every page belongs to the current Saved HEAD. */
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
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

export function SavedPlayerMatchesPanel(props: Props): JSX.Element {
  const {runId,branchId,savedHead,playerId}=props
  return <SavedPlayerMatchesTimeline key={JSON.stringify([runId,branchId,savedHead,playerId])} {...props}/>
}

function SavedPlayerMatchesTimeline({ runId, branchId, savedHead, playerId, locale }: Props): JSX.Element {
  const cs = locale === 'cs'
  const [searchParams, setSearchParams] = useSearchParams()
  const rawSeason = searchParams.get('careerSeason')
  const season = rawSeason !== null && /^(0|[1-9]\d*)$/.test(rawSeason) && Number(rawSeason) < 50
    ? rawSeason : 'all'
  const rawPage = searchParams.get('careerPage')
  const page = rawPage !== null && /^(0|[1-9]\d*)$/.test(rawPage) && Number(rawPage) <= 10000
    ? Number(rawPage) : 0
  const seasonIndex = season === 'all' ? null : Number(season)
  const navigateCareer = (nextSeason: string, nextPage: number) => {
    const copy = new URLSearchParams(searchParams)
    copy.set('tab', 'career')
    if (nextSeason === 'all') copy.delete('careerSeason')
    else copy.set('careerSeason', nextSeason)
    if (nextPage === 0) copy.delete('careerPage')
    else copy.set('careerPage', String(nextPage))
    setSearchParams(copy)
  }
  // Do not carry unrelated URL tokens to another page/replay authority.
  const matchQuery = new URLSearchParams()
  matchQuery.set('tab', 'career')
  if (season !== 'all') matchQuery.set('careerSeason', season)
  if (page > 0) matchQuery.set('careerPage', String(page))
  const q = useQuery({
    queryKey: ['saved-player-matches', runId, branchId, savedHead, playerId, seasonIndex, page],
    queryFn: () => getSavedPlayerMatchHistory(runId, branchId, playerId, seasonIndex, page * PAGE_SIZE, PAGE_SIZE),
    retry: false,
  })
  const scoped = q.isSuccess && !q.isFetching && q.data?.source === 'selected_branch_saved_revision' &&
    q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.player_id === playerId &&
    q.data?.season_index === seasonIndex && q.data?.offset === page * PAGE_SIZE &&
    q.data?.limit === PAGE_SIZE && Array.isArray(q.data?.matches) &&
    Number.isInteger(q.data?.total_results) && q.data!.total_results >= 0 &&
    typeof q.data?.has_more === 'boolean'
  const data = scoped ? q.data : null
  const opponentIds = data?.status === 'ready' ? [...new Set(data.matches.map(match => match.opponent_player_id))] : []
  const opponents = useQuery({
    queryKey: ['saved-match-opponent-names', runId, branchId, savedHead, opponentIds.join('|')],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId, opponentIds),
    enabled: opponentIds.length > 0,
    retry: false,
  })
  const names = opponents.isSuccess && !opponents.isFetching &&
    opponents.data?.saved_revision_id === savedHead &&
    opponents.data?.run_id === runId && opponents.data?.branch_id === branchId &&
    opponents.data?.requested_ids?.join('|') === opponentIds.join('|') &&
    Array.isArray(opponents.data.players) ?
    Object.fromEntries(opponents.data.players.map(value => [value.player_id, value.display_name])) : {}
  return <section aria-label={cs?"Uložená zápasová kariéra hráče":"Saved player tournament matches"}>
    <h3>{cs ? 'Zápasová kariéra' : 'Match career'}</h3>
    {(q.isPending||q.isFetching) && <p role="status">{cs ? 'Načítám zápasy…' : 'Loading matches…'}</p>}
    {q.error && <p role="alert" className="error">{cs ? 'Historie zápasů není dostupná.' : 'Match history is unavailable.'}</p>}
    {q.isSuccess && !q.isFetching && !scoped && <p role="alert" className="error">{cs ? 'Data patří jiné uložené revizi.' : 'Data does not match the selected Saved Revision.'}</p>}
    <button type="button" disabled={q.isFetching}
      onClick={()=>{void q.refetch()}}>{cs?'Obnovit kariéru':'Retry career read'}</button>
    {data?.status === 'identity_unavailable' && <p className="status">{cs
      ? 'Bez ověřené identity nelze zobrazit zápasovou kariéru.'
      : 'Match history is hidden without a verified saved player identity.'}</p>}
    {data?.status === 'ready' && <>
      <p><strong>{cs ? 'Celá kariéra (odehráno)' : 'Career (played)'}</strong> ·
        {' '}{data.career_played_wins} W / {data.career_played_losses} L
        {' · '}{data.career_walkovers} {cs ? 'kontumací' : 'walkovers'}</p>
      <label htmlFor="saved-player-season">{cs ? 'Sezóna' : 'Season'}{' '}</label>
      <select data-run-navigation-readonly id="saved-player-season" aria-label={cs ? 'Sezóna zápasů' : 'Match season'}
        value={season} onChange={event => navigateCareer(event.target.value, 0)}>
        <option value="all">{cs ? 'Všechny sezóny' : 'All seasons'}</option>
        {data.available_seasons.map(index => <option key={index} value={String(index)}>{seasonText(index)}</option>)}
      </select>
      <p className="status">{cs ? 'Výběr' : 'Selection'}: {data.played_wins} W / {data.played_losses} L
        {' · '}{data.walkovers} {cs ? 'kontumací' : 'walkovers'} ·
        {' '}{data.total_results} {cs ? 'zaznamenaných výsledků' : 'recorded results'}</p>
      {data.total_results === 0 && <p className="status">{cs
        ? (season==='all'?'Hráč nemá žádné uložené turnajové zápasy.':'Zvolená sezona neobsahuje zápasy tohoto hráče.')
        : (season==='all'?'This player has no saved tournament matches.':'No saved matches in the selected season.')}</p>}
      {data.matches.length > 0 && <ul className="run-home-feed">
        {data.matches.map(match => <li key={match.event_id + ':' + match.match_id}>
          <span><strong>{match.event_name}</strong>
            {' '}<Link to={'/admin/runs/' + encodeURIComponent(runId) + '/people/' +
              encodeURIComponent(playerId) + '/matches/' + encodeURIComponent(match.event_id) +
              '/' + encodeURIComponent(match.match_id) + '?' + matchQuery.toString()}>
              {cs ? 'Detail zápasu →' : 'Match detail →'}
            </Link>
            <small>{match.season} · W{match.week} · {match.draw_type==='main'?(cs?'hlavní část':'main'):match.draw_type==='qualification'?(cs?'kvalifikace':'qualification'):match.draw_type==='group'?(cs?'skupina':'group'):match.draw_type} ·
              {' '}{cs ? 'kolo' : 'round'} {match.round_number}</small>
            <small>{match.outcome === 'win' ? (cs ? 'Výhra' : 'Win') : (cs ? 'Prohra' : 'Loss')}
              {' · '}{names[match.opponent_player_id] || match.opponent_player_id}
              {' · '}{match.scoreline}
              {match.completion === 'walkover' ? (cs ? ' · kontumace' : ' · walkover') : ''}
            </small>
          </span>
        </li>)}
      </ul>}
      {(page>0||data.has_more) && <div className="run-home-status-block">
        <button type="button" disabled={page === 0 || q.isFetching} onClick={() => navigateCareer(season, Math.max(0, page - 1))}>
          {cs ? '← Předchozí' : '← Previous'}
        </button>
        {' '}{cs ? 'Strana' : 'Page'} {page + 1} / {Math.ceil(data.total_results / PAGE_SIZE)}{' '}
        <button type="button" disabled={!data.has_more || q.isFetching} onClick={() => navigateCareer(season, page + 1)}>
          {cs ? 'Další →' : 'Next →'}
        </button>
      </div>}
      <p className="status">{cs
        ? 'Pouze uzavřené kanonické turnaje z uložené revize. Volné losy jsou vyloučeny, kontumace se nepočítají jako odehrané zápasy. Pořadí v rámci týdne není časový rozpis.'
        : 'Only completed canonical tournaments in the Saved Revision. BYEs are excluded, walkovers are not counted as played matches. Same-week ordering is not an exact schedule.'}</p>
    </>}
  </section>
}
