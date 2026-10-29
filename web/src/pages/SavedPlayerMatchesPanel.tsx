/** Read-only career matches from the current selected Branch Saved HEAD. */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { getSavedHomePlayerIdentities, getSavedPlayerMatchHistory } from '../api/client'
import {
  CAREER_PAGE_SIZE, hasAmbiguousPlayerLinkParams, matchLoadedCareer, validCareerResultWindow, parseCareerCompletion, parseCareerOutcome,
  parseCareerPage, parseCareerSeason, parsePageInput, totalCareerPages,
} from './savedPlayerCareerNavigation'

type Props = {
  runId: string
  branchId: string
  savedHead: string
  playerId: string
  locale: 'cs' | 'en'
}
const seasonText = (index: number): string =>
  `${2000 + index}/${String((2001 + index) % 100).padStart(2, '0')}`

export function SavedPlayerMatchesPanel(props: Props): JSX.Element {
  const { runId, branchId, savedHead, playerId } = props
  return <SavedPlayerMatchesTimeline key={JSON.stringify([runId, branchId, savedHead, playerId])} {...props} />
}

function SavedPlayerMatchesTimeline({ runId, branchId, savedHead, playerId, locale }: Props): JSX.Element {
  const cs = locale === 'cs'
  const [params, setParams] = useSearchParams()
  const season = parseCareerSeason(params.get('careerSeason'))
  const page = parseCareerPage(params.get('careerPage'))
  const outcome = parseCareerOutcome(params.get('careerOutcome'))
  const completion = parseCareerCompletion(params.get('careerCompletion'))
  const queryText = params.get('careerQ') ?? ''
  const invalidUrl = season === null || page === null || outcome === null || completion === null ||
    queryText.length > 160 || hasAmbiguousPlayerLinkParams(params,
      ['careerSeason', 'careerPage', 'careerQ', 'careerOutcome', 'careerCompletion'])
  const missingScope = !runId || !branchId || !savedHead || !playerId
  const [pageInput, setPageInput] = useState('')
  const update = (updates: Record<string, string | null>) => {
    const copy = new URLSearchParams(params)
    copy.set('tab', 'career')
    for (const [key, value] of Object.entries(updates)) {
      if (!value || value === 'all' || (key === 'careerPage' && value === '0')) copy.delete(key)
      else copy.set(key, value)
    }
    setParams(copy)
  }
  const navigateCareer = (nextSeason: string, nextPage: number) => {
    setPageInput('')
    update({ careerSeason: nextSeason, careerPage: String(nextPage) })
  }
  const resetInvalid = () => {
    setPageInput('')
    update({ careerSeason: null, careerPage: null, careerOutcome: null,
      careerCompletion: null, careerQ: null })
  }
  // Permit only the current verified source in a deep link to a match.
  const matchQuery = new URLSearchParams()
  matchQuery.set('tab', 'career')
  matchQuery.set('replayBranch', branchId)
  matchQuery.set('replayHead', savedHead)
  if (season && season !== 'all') matchQuery.set('careerSeason', season)
  if (page && page > 0) matchQuery.set('careerPage', String(page))
  if (outcome && outcome !== 'all') matchQuery.set('careerOutcome', outcome)
  if (completion && completion !== 'all') matchQuery.set('careerCompletion', completion)
  if (queryText) matchQuery.set('careerQ', queryText)

  const q = useQuery({
    queryKey: ['saved-player-matches', runId, branchId, savedHead, playerId, season, page],
    queryFn: () => getSavedPlayerMatchHistory(runId, branchId, playerId,
      season === 'all' ? null : Number(season), page! * CAREER_PAGE_SIZE, CAREER_PAGE_SIZE),
    enabled: !invalidUrl && !missingScope,
    retry: false,
  })
  const scoped = !invalidUrl && q.isSuccess && !q.isFetching &&
    q.data?.source === 'selected_branch_saved_revision' &&
    q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.player_id === playerId &&
    q.data?.season_index === (season === 'all' ? null : Number(season)) &&
    q.data?.offset === page! * CAREER_PAGE_SIZE &&
    q.data?.limit === CAREER_PAGE_SIZE && Array.isArray(q.data?.matches) &&
    validCareerResultWindow(q.data!.total_results, q.data!.offset, q.data!.limit,
      q.data!.matches, q.data!.status === 'identity_unavailable') &&
    typeof q.data?.has_more === 'boolean'
  const data = scoped ? q.data : null
  const opponentIds = data?.status === 'ready'
    ? [...new Set(data.matches.map(match => match.opponent_player_id))] : []
  const opponents = useQuery({
    queryKey: ['saved-match-opponent-names', runId, branchId, savedHead, opponentIds.join('|')],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId, opponentIds),
    enabled: opponentIds.length > 0, retry: false,
  })
  const names = opponents.isSuccess && !opponents.isFetching &&
    opponents.data?.saved_revision_id === savedHead &&
    opponents.data?.run_id === runId && opponents.data?.branch_id === branchId &&
    opponents.data?.source === 'selected_branch_saved_revision' &&
    opponents.data?.requested_ids?.join('|') === opponentIds.join('|') &&
    Array.isArray(opponents.data.players) &&
    opponents.data.players.every(p => opponentIds.includes(p.player_id) && Boolean(p.display_name?.trim()))
    ? Object.fromEntries(opponents.data.players.map(value => [value.player_id, value.display_name])) : {}
  const totalPages = data ? totalCareerPages(data.total_results) : 0
  const outOfRange = Boolean(data && page !== null && page > 0 && page >= totalPages)
  const filtered = data?.status === 'ready' && !outOfRange && outcome && completion
    ? data.matches.filter(match => matchLoadedCareer(match, names, queryText, outcome, completion)) : []
  const jump = parsePageInput(pageInput, totalPages)

  return <section aria-label={cs ? 'Uložená zápasová kariéra hráče' : 'Saved player tournament matches'}>
    <h3>{cs ? 'Zápasová kariéra' : 'Match career'}</h3>
    {invalidUrl && <p role="alert">{cs
      ? 'Neplatná sezona, stránka nebo filtr v odkazu. Žádná stránka nebyla načtena.'
      : 'Invalid career season, page or filter in the link. No page was loaded.'}{' '}
      <button type="button" onClick={resetInvalid}>{cs ? 'Platný výběr' : 'Reset to a valid selection'}</button></p>}
    {!invalidUrl && missingScope && <p role="alert">{cs
      ? 'Chybí vybraná Branch, Saved HEAD nebo ověřené ID hráče.'
      : 'Selected Branch, Saved HEAD or verified player ID is missing.'}</p>}
    {!invalidUrl && !missingScope && (q.isPending || q.isFetching) && <p role="status">{cs ? 'Načítám zápasy…' : 'Loading matches…'}</p>}
    {!invalidUrl && q.error && <p role="alert" className="error">{cs
      ? 'Historie zápasů není dostupná.' : 'Match history is unavailable.'}</p>}
    {!invalidUrl && q.isSuccess && !q.isFetching && !scoped && <p role="alert" className="error">{cs
      ? 'Nelze ověřit uloženou revizi nebo úplnost stránky zápasů.'
      : 'Cannot verify the Saved Revision or match page completeness.'}</p>}
    <button type="button" disabled={invalidUrl || missingScope || q.isFetching}
      onClick={() => { void q.refetch() }}>{cs ? 'Obnovit kariéru' : 'Retry career read'}</button>
    {data?.status === 'identity_unavailable' && <p className="status">{cs
      ? 'Bez ověřené identity nelze zobrazit zápasovou kariéru.'
      : 'Match history is hidden without a verified saved player identity.'}</p>}
    {data?.status === 'ready' && <>
      <p><strong>{cs ? 'Celá kariéra (odehráno)' : 'Career (played)'}</strong> ·
        {' '}{data.career_played_wins} W / {data.career_played_losses} L
        {' · '}{data.career_walkovers} {cs ? 'kontumací' : 'walkovers'}</p>
      <label htmlFor="saved-player-season">{cs ? 'Sezóna' : 'Season'}{' '}</label>
      <select data-run-navigation-readonly id="saved-player-season"
        aria-label={cs ? 'Sezóna zápasů' : 'Match season'}
        value={season!} onChange={event => navigateCareer(event.target.value, 0)}>
        <option value="all">{cs ? 'Všechny sezóny' : 'All seasons'}</option>
        {season !== 'all' && !data.available_seasons.includes(Number(season)) &&
          <option value={season!}>{seasonText(Number(season))}</option>}
        {data.available_seasons.map(index => <option key={index} value={String(index)}>{seasonText(index)}</option>)}
      </select>
      <p className="status">{cs ? 'Výběr' : 'Selection'}: {data.played_wins} W / {data.played_losses} L
        {' · '}{data.walkovers} {cs ? 'kontumací' : 'walkovers'} ·
        {' '}{data.total_results} {cs ? 'zaznamenaných výsledků' : 'recorded results'}</p>
      <div className="run-home-status-block">
        <p className="status">{cs ? 'Lokální hledání a filtry platí jen pro načtenou stránku (max. 20 zápasů), nikoli pro celou kariéru.'
          : 'Local search and filters cover this loaded page only (up to 20 matches), not the entire career.'}</p>
        <label>{cs ? 'Hledat v načtené stránce' : 'Search loaded page'}
          <input type="search" maxLength={160} aria-label={cs ? 'Hledat v načtené stránce' : 'Search loaded page'}
            value={queryText} onChange={event => update({careerQ: event.target.value})} />
        </label>
        <label>{cs ? 'Výsledek' : 'Outcome'}{' '}
          <select aria-label={cs ? 'Filtrovat výhry a prohry' : 'Filter wins and losses'} value={outcome!}
            onChange={event => update({careerOutcome: event.target.value})}>
            <option value="all">{cs ? 'Všechny výsledky' : 'All outcomes'}</option>
            <option value="win">{cs ? 'Výhry' : 'Wins'}</option>
            <option value="loss">{cs ? 'Prohry' : 'Losses'}</option>
          </select>
        </label>{' '}
        <label>{cs ? 'Způsob' : 'Completion'}{' '}
          <select aria-label={cs ? 'Filtrovat odehrané a kontumace' : 'Filter played and walkovers'} value={completion!}
            onChange={event => update({careerCompletion: event.target.value})}>
            <option value="all">{cs ? 'Všechny zápasy' : 'All matches'}</option>
            <option value="played">{cs ? 'Odehrané' : 'Played'}</option>
            <option value="walkover">{cs ? 'Kontumace' : 'Walkovers'}</option>
          </select>
        </label>
      </div>
      {data.total_results === 0 && !outOfRange && <p className="status">{cs
        ? (season === 'all' ? 'Hráč nemá žádné uložené turnajové zápasy.' : 'Zvolená sezona neobsahuje zápasy tohoto hráče.')
        : (season === 'all' ? 'This player has no saved tournament matches.' : 'No saved matches in the selected season.')}</p>}
      {outOfRange && <p role="alert">{cs ? 'Požadovaná stránka kariéry neexistuje.' : 'Requested career page does not exist.'}
        {' '}<button type="button" onClick={() => navigateCareer(season!, 0)}>{cs ? 'První platná stránka' : 'First valid page'}</button>
        {totalPages > 0 && <>{' '}<button type="button" onClick={() => navigateCareer(season!, totalPages - 1)}>
          {cs ? 'Poslední platná stránka' : 'Last valid page'}</button></>}
      </p>}
      {!outOfRange && data.matches.length > 0 && filtered.length === 0 &&
        <p role="status">{cs ? 'Na načtené stránce žádný zápas neodpovídá lokálním filtrům.'
          : 'No matches on the loaded page match the local filters.'}</p>}
      {filtered.length > 0 && <ul className="run-home-feed">
        {filtered.map(match => <li key={match.event_id + ':' + match.match_id}>
          <span><strong>{match.event_name}</strong>
            {' '}<Link to={'/admin/runs/' + encodeURIComponent(runId) + '/people/' +
              encodeURIComponent(playerId) + '/matches/' + encodeURIComponent(match.event_id) +
              '/' + encodeURIComponent(match.match_id) + '?' + matchQuery.toString()}>
              {cs ? 'Detail zápasu →' : 'Match detail →'}
            </Link>
            <small>{match.season} · W{match.week} · {match.draw_type === 'main' ? (cs ? 'hlavní část' : 'main') :
              match.draw_type === 'qualification' ? (cs ? 'kvalifikace' : 'qualification') :
                match.draw_type === 'group' ? (cs ? 'skupina' : 'group') : match.draw_type} ·
              {' '}{cs ? 'kolo' : 'round'} {match.round_number}</small>
            <small>{match.outcome === 'win' ? (cs ? 'Výhra' : 'Win') : (cs ? 'Prohra' : 'Loss')}
              {' · '}{names[match.opponent_player_id] || match.opponent_player_id}
              {' · '}{match.scoreline}
              {match.completion === 'walkover' ? (cs ? ' · kontumace' : ' · walkover') : ''}
            </small>
          </span>
        </li>)}
      </ul>}
      {totalPages > 0 && !outOfRange && <div className="run-home-status-block">
        <button type="button" disabled={page === 0 || q.isFetching}
          onClick={() => navigateCareer(season!, 0)}>{cs ? 'První stránka' : 'First page'}</button>{' '}
        <button type="button" disabled={page === 0 || q.isFetching}
          onClick={() => navigateCareer(season!, Math.max(0, page! - 1))}>{cs ? '← Předchozí' : '← Previous'}</button>
        {' '}{cs ? 'Strana' : 'Page'} {page! + 1} / {totalPages}{' '}
        <button type="button" disabled={page! + 1 >= totalPages || q.isFetching}
          onClick={() => navigateCareer(season!, page! + 1)}>{cs ? 'Další →' : 'Next →'}</button>{' '}
        <button type="button" disabled={page! + 1 >= totalPages || q.isFetching}
          onClick={() => navigateCareer(season!, totalPages - 1)}>{cs ? 'Poslední stránka' : 'Last page'}</button>
        <form onSubmit={event => {
          event.preventDefault()
          if (jump !== null) navigateCareer(season!, jump)
        }}>
          <label>{cs ? 'Přejít na stránku' : 'Go to page'}
            <input aria-label={cs ? 'Číslo stránky kariéry' : 'Career page number'} type="number"
              min={1} max={totalPages} step={1} value={pageInput}
              onChange={event => setPageInput(event.target.value)} /></label>{' '}
          <button type="submit" disabled={jump === null || q.isFetching}>{cs ? 'Přejít' : 'Jump to page'}</button>
        </form>
      </div>}
      <p className="status">{cs
        ? 'Pouze uzavřené kanonické turnaje z uložené revize. Volné losy jsou vyloučeny, kontumace se nepočítají jako odehrané zápasy. Pořadí v rámci týdne není časový rozpis.'
        : 'Only completed canonical tournaments in the Saved Revision. BYEs are excluded, walkovers are not counted as played matches. Same-week ordering is not an exact schedule.'}</p>
    </>}
  </section>
}
