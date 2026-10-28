/** Canonical present-only Saved HEAD match detail and archived rally replay. */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getSavedPlayerMatchDetail, getSavedHomePlayerIdentities } from '../api/client'
import type { SavedPlayerMatchDetail } from '../api/types'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import {
  parseCareerCompletion, parseCareerOutcome, parseCareerPage, parseCareerSeason,
  parsePageInput, parsePlayerRally, REPLAY_PAGE_SIZE, validPlayerReplayPagePair,
} from './savedPlayerCareerNavigation'

/** Remount local input and response context before any different source can read. */
export function SavedPlayerMatchDetailPage(): JSX.Element {
  const { runId = '', playerId = '', eventId = '', matchId = '' } = useParams()
  const { selectedBranch } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = branchId ? selectedBranch?.saved_head_revision_id ?? null : null
  const identity = JSON.stringify([runId, branchId, savedHead, playerId, eventId, matchId, time.mode])
  return <SavedPlayerMatchReplay key={identity} />
}

function SavedPlayerMatchReplay(): JSX.Element {
  const { runId = '', playerId = '', eventId = '', matchId = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const queryClient = useQueryClient()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = branchId ? selectedBranch?.saved_head_revision_id ?? null : null
  const linkedBranch = params.get('replayBranch')
  const linkedHead = params.get('replayHead')
  const requestedRally = parsePlayerRally(params.get('rally'))
  // A non-default deep link is never allowed to resolve against an implicit new HEAD.
  // The API itself reads only the *current* Saved HEAD, not an arbitrary revision.
  const hasLinkScope = linkedBranch !== null || linkedHead !== null || params.has('rally')
  const exactLink = !hasLinkScope ||
    (Boolean(linkedBranch && linkedHead) && linkedBranch === branchId && linkedHead === savedHead)
  const [rallyInput, setRallyInput] = useState('')
  const index = (requestedRally ?? 1) - 1
  const offset = Math.floor(index / REPLAY_PAGE_SIZE) * REPLAY_PAGE_SIZE
  const ready = time.mode === 'present' && !time.isLoading && !time.error &&
    !isLoading && !error && exactLink && requestedRally !== null &&
    Boolean(branchId && savedHead && playerId && eventId && matchId)
  const queryScope = ['saved-match-detail', runId, branchId, savedHead, playerId, eventId, matchId]
  const q = useQuery({
    queryKey: [...queryScope, offset],
    queryFn: () => getSavedPlayerMatchDetail(runId, branchId!, playerId, eventId, matchId, offset, REPLAY_PAGE_SIZE),
    enabled: ready, retry: false,
  })
  const verified = ready && q.isSuccess && !q.isFetching &&
    q.data?.source === 'selected_branch_saved_revision' &&
    q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.player_id === playerId &&
    q.data?.match?.event_id === eventId && q.data?.match?.match_id === matchId &&
    q.data?.offset === offset && q.data?.limit === REPLAY_PAGE_SIZE &&
    Number.isSafeInteger(q.data?.total_rallies) && q.data!.total_rallies >= 0 &&
    Array.isArray(q.data?.rallies) && typeof q.data?.has_more === 'boolean' &&
    q.data.rallies.every((r, i) => r.rally_index === offset + i + 1) &&
    (q.data?.replay_status === 'unavailable'
      ? q.data.total_rallies === 0 && q.data.rallies.length === 0 && !q.data.has_more
      : q.data?.replay_status === 'available' && q.data.total_rallies > 0 &&
        q.data.rallies.length === Math.max(0, Math.min(REPLAY_PAGE_SIZE, q.data.total_rallies - offset)) &&
        q.data.has_more === (offset + REPLAY_PAGE_SIZE < q.data.total_rallies))
  const initial = verified ? q.data : null
  // Verify only real, adjacent pages of the SAME archive; an empty out-of-range
  // page must not poison a later first -> last navigation (regression #1651).
  const prev = initial && offset >= REPLAY_PAGE_SIZE && offset < initial.total_rallies
    ? queryClient.getQueryData<SavedPlayerMatchDetail>([...queryScope, offset - REPLAY_PAGE_SIZE]) : undefined
  const next = initial && offset + REPLAY_PAGE_SIZE < initial.total_rallies
    ? queryClient.getQueryData<SavedPlayerMatchDetail>([...queryScope, offset + REPLAY_PAGE_SIZE]) : undefined
  const connected = (!prev || Boolean(initial && validPlayerReplayPagePair(prev, initial))) &&
    (!next || Boolean(initial && validPlayerReplayPagePair(initial, next)))
  const data = connected ? initial : null
  const invalidResponse = Boolean(ready && q.isSuccess && !q.isFetching && !data)
  const ids = data ? [data.player_a_id || data.player_id, data.player_b_id || data.match.opponent_player_id] : []
  const namesQuery = useQuery({
    queryKey: ['saved-match-names', runId, branchId, savedHead, ids.join('|')],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId!, ids),
    enabled: ready && ids.length === 2 && ids[0] !== ids[1], retry: false,
  })
  const namesData = namesQuery.data
  const names = namesQuery.isSuccess && !namesQuery.isFetching && namesData &&
    namesData.saved_revision_id === savedHead && namesData.run_id === runId &&
    namesData.branch_id === branchId && namesData.requested_ids?.join('|') === ids.join('|') &&
    Array.isArray(namesData.players) &&
    namesData.players.every(p => ids.includes(p.player_id) && Boolean(p.display_name?.trim()))
    ? Object.fromEntries(namesData.players.map(p => [p.player_id, p.display_name])) : {}
  const frame = data?.rallies.find(r => r.rally_index === index + 1)
  const playerName = (id: string | null | undefined): string => id ? (names[id] || id) : '—'
  const moveToRally = (oneBased: number) => {
    if (!branchId || !savedHead) return
    const copy = new URLSearchParams(params)
    copy.set('replayBranch', branchId)
    copy.set('replayHead', savedHead)
    if (oneBased === 1) copy.delete('rally')
    else copy.set('rally', String(oneBased))
    setRallyInput('')
    setParams(copy, { replace: true })
  }
  const moveToCurrent = () => {
    const copy = new URLSearchParams(params)
    copy.delete('replayBranch')
    copy.delete('replayHead')
    copy.delete('rally')
    setRallyInput('')
    setParams(copy, { replace: true })
  }
  const rallyTarget = parsePlayerRally(rallyInput)
  const validRallyTarget = rallyInput !== '' && rallyTarget !== null &&
    data?.replay_status === 'available' && rallyTarget <= data.total_rallies
  const parent = new URLSearchParams()
  if (params.get('tab') === 'career') {
    parent.set('tab', 'career')
    const season = parseCareerSeason(params.get('careerSeason'))
    const page = parseCareerPage(params.get('careerPage'))
    const outcome = parseCareerOutcome(params.get('careerOutcome'))
    const completion = parseCareerCompletion(params.get('careerCompletion'))
    const search = params.get('careerQ')
    if (season && season !== 'all') parent.set('careerSeason', season)
    if (page && page > 0) parent.set('careerPage', String(page))
    if (outcome && outcome !== 'all') parent.set('careerOutcome', outcome)
    if (completion && completion !== 'all') parent.set('careerCompletion', completion)
    if (search && search.length <= 160) parent.set('careerQ', search)
  }
  const back = '/admin/runs/' + encodeURIComponent(runId) + '/people/' + encodeURIComponent(playerId) +
    (parent.size ? '?' + parent.toString() : '')

  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · SAVED MATCH</p>
      <h2>{cs ? 'Detail zápasu' : 'Match detail'}</h2>
      <p className="subtitle">{cs ? 'Ověřený výsledek a archivovaný průběh' : 'Verified result and archived rally replay'}</p>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Historický checkpoint nemá podporovaný detail zápasu. Současný HEAD není historická revize.'
      : 'Historical checkpoint match detail is unsupported. The current HEAD is not a historical revision.'}</p> : <>
      {requestedRally === null && <p role="alert">{cs
        ? 'Neplatné číslo výměny v odkazu.' : 'Invalid rally number in the link.'}{' '}
        <button type="button" onClick={moveToCurrent}>{cs ? 'Otevřít aktuální první výměnu' : 'Open current first rally'}</button></p>}
      {!exactLink && requestedRally !== null && <p role="alert">{cs
        ? 'Odkaz patří jiné Branch nebo Saved HEAD. Archiv jiného zdroje zde nelze načíst.'
        : 'This link belongs to a different Branch or Saved HEAD. A foreign archive cannot be loaded here.'}{' '}
        <button type="button" onClick={moveToCurrent}>{cs ? 'Přejít na aktuální zdroj' : 'Open current Saved HEAD'}</button></p>}
      {(isLoading || time.isLoading || (ready && (q.isPending || q.isFetching))) &&
        <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>}
      {(error || time.error) && <p role="alert" className="error">{error || time.error}</p>}
      {!ready && exactLink && requestedRally !== null && !isLoading && !time.isLoading &&
        !error && !time.error && <p role="alert">{cs
          ? 'Chybí vybraná Branch, Saved HEAD nebo ID hráče/zápasu.'
          : 'Selected Branch, Saved HEAD or player/match ID is missing.'}</p>}
      {ready && q.error && <p role="alert" className="error">{formatApiError(q.error)}</p>}
      {invalidResponse && <p role="alert" className="error">{cs
        ? 'Detail neodpovídá vybrané uložené revizi nebo sousednímu archivu.'
        : 'Match detail does not match the selected Saved Revision or adjacent archive.'}</p>}
      <button type="button" disabled={!ready || q.isFetching}
        onClick={() => { void q.refetch() }}>{cs ? 'Obnovit zápas / archiv' : 'Retry match / archive read'}</button>
      {data && <>
        <div className="run-home-status-block">
          <h3>{data.match.event_name}</h3>
          <p>{data.match.season} · W{data.match.week} · {data.match.draw_type === 'main' ? (cs ? 'hlavní část' : 'main') :
            data.match.draw_type === 'qualification' ? (cs ? 'kvalifikace' : 'qualification') :
              data.match.draw_type === 'group' ? (cs ? 'skupina' : 'group') : data.match.draw_type} ·
            {' '}{cs ? 'kolo' : 'round'} {data.match.round_number}</p>
          <p><strong>{playerName(data.winner_player_id)}</strong> {cs ? 'porazil' : 'defeated'}
            {' '}{playerName(data.loser_player_id)} · <strong>{data.match.scoreline}</strong></p>
          {data.match.completion === 'walkover' && <p>{cs ? 'Výsledek kontumací' : 'Walkover result'}</p>}
          <p className="status">Saved Revision: <code>{data.saved_revision_id}</code></p>
        </div>
        <h3>{cs ? 'Přehrání výměn' : 'Rally replay'}</h3>
        {data.replay_status === 'unavailable' && <p role="status">{cs
          ? 'Ověřený archiv výměn není pro tento zápas uložený. Výsledek je dostupný, průběh nevymýšlíme.'
          : 'No verified archived rally log exists for this match. The result is available; no replay is fabricated.'}</p>}
        {data.replay_status === 'available' && <>
          <p className="status">{cs ? 'Archivovaných výměn' : 'Archived rallies'}: {data.total_rallies}
            {' · '}{playerName(data.player_a_id)} (A) – {playerName(data.player_b_id)} (B)</p>
          {index >= data.total_rallies && <p role="alert">{cs
            ? 'Požadovaná výměna v tomto archivu neexistuje.'
            : 'Requested rally does not exist in this archive.'}{' '}
            <button type="button" onClick={() => moveToRally(1)}>{cs ? 'První platná výměna' : 'First valid rally'}</button>{' '}
            <button type="button" onClick={() => moveToRally(data.total_rallies)}>{cs ? 'Poslední platná výměna' : 'Last valid rally'}</button>
          </p>}
          {frame ? <div className="run-home-status-block">
            <p><strong>{cs ? 'Výměna' : 'Rally'} {frame.rally_index}/{data.total_rallies}</strong>
              {' · '}{cs ? 'Set' : 'Game'} {frame.set_number}</p>
            <p><strong>{frame.score_a_before} : {frame.score_b_before}</strong>
              {' → '}<strong>{frame.score_a_after} : {frame.score_b_after}</strong></p>
            <p>{cs ? 'Stav setů' : 'Games'}: {frame.sets_a_after} : {frame.sets_b_after}</p>
            <p>{cs ? 'Podává' : 'Server'}: {playerName(frame.server_player_id)}
              {' · '}{cs ? 'Vítěz výměny' : 'Rally winner'}: {playerName(frame.winner_player_id)}</p>
            {frame.set_complete && <p role="status">{cs ? 'Konec setu' : 'Game completed'}</p>}
            {frame.match_complete && <p role="status">{cs ? 'Konec zápasu' : 'Match completed'}</p>}
          </div> : index < data.total_rallies && <p role="status">{cs
            ? 'V tomto úseku není výměna.' : 'No rally at this cursor.'}</p>}
          <div className="run-home-status-block">
            <button type="button" disabled={q.isFetching || !frame || index === 0} onClick={() => moveToRally(1)}>
              {cs ? 'První výměna' : 'First rally'}</button>{' '}
            <button type="button" disabled={q.isFetching || !frame || index === 0}
              onClick={() => moveToRally(index)}>{cs ? '← Předchozí výměna' : '← Previous rally'}</button>{' '}
            <button type="button" disabled={q.isFetching || !frame || index + 1 >= data.total_rallies}
              onClick={() => moveToRally(index + 2)}>{cs ? 'Další výměna →' : 'Next rally →'}</button>{' '}
            <button type="button" disabled={q.isFetching || !frame || index + 1 >= data.total_rallies}
              onClick={() => moveToRally(data.total_rallies)}>{cs ? 'Poslední výměna' : 'Last rally'}</button>
            <form onSubmit={event => {
              event.preventDefault()
              if (validRallyTarget && rallyTarget) moveToRally(rallyTarget)
            }}>
              <label>{cs ? 'Přejít na výměnu' : 'Go to rally'}
                <input aria-label={cs ? 'Číslo archivované výměny' : 'Archived rally number'} type="number"
                  inputMode="numeric" min={1} max={data.total_rallies} step={1}
                  value={rallyInput} onChange={event => setRallyInput(event.target.value)} /></label>{' '}
              <button type="submit" disabled={q.isFetching || !frame || !validRallyTarget}>
                {cs ? 'Přejít' : 'Jump to rally'}</button>
            </form>
          </div>
          {data.rallies.length > 0 && <details>
            <summary>{cs ? 'Přehled uložených výměn' : 'Browse archived rallies'}
              {' · '}{data.rallies[0].rally_index}–{data.rallies[data.rallies.length - 1].rally_index}</summary>
            <ul>{data.rallies.map(r => <li key={r.rally_index}>
              <button type="button" aria-current={r.rally_index === index + 1 ? 'step' : undefined}
                onClick={() => moveToRally(r.rally_index)}>
                {cs ? 'Výměna' : 'Rally'} {r.rally_index} · {r.score_a_after}:{r.score_b_after}
                {r.rally_index === index + 1 ? (cs ? ' · aktuální' : ' · current') : ''}
              </button>
            </li>)}</ul>
          </details>}
          <p className="status">{cs
            ? 'Přehrání čte pouze archivované výměny současného Saved HEAD; nepřepočítává simulaci ani historickou revizi.'
            : 'Replay reads stored rallies from the current Saved HEAD only; it never re-simulates or loads historical revisions.'}</p>
        </>}
      </>}
    </>}
    <Link to={back}>{cs ? '← Zpět na profil hráče' : '← Back to player profile'}</Link>
  </section>
}
