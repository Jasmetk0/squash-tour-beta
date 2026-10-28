/** Canonical read-only match detail, replayed from stored rally frames only. */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getSavedPlayerMatchDetail, getSavedHomePlayerIdentities } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

const PAGE = 25

/**
 * Route params and the authoritative Branch Saved Revision together define a replay.
 * Keying the actual cursor-owning component forces index=0 *during the first render*
 * of a different replay, before a pageOffset 25/50/... fetch can ever be issued.
 * This deliberately does not change the independently keyed matches list panel.
 */
export function SavedPlayerMatchDetailPage(): JSX.Element {
  const { runId = '', playerId = '', eventId = '', matchId = '' } = useParams()
  const { selectedBranch } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = branchId ? selectedBranch?.saved_head_revision_id ?? null : null
  const replayIdentity = JSON.stringify([runId, branchId, savedHead, playerId, eventId, matchId, time.mode])
  return <SavedPlayerMatchReplay key={replayIdentity} />
}

function SavedPlayerMatchReplay(): JSX.Element {
  const { runId = '', playerId = '', eventId = '', matchId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id
  const [index, setIndex] = useState(0)
  const pageOffset = Math.floor(index / PAGE) * PAGE
  const ready = time.mode === 'present' && !time.isLoading && !time.error &&
    !isLoading && !error &&
    Boolean(branchId && savedHead && playerId && eventId && matchId)
  const q = useQuery({
    queryKey: ['saved-match-detail', runId, branchId, savedHead, playerId, eventId, matchId, pageOffset],
    queryFn: () => getSavedPlayerMatchDetail(runId, branchId!, playerId, eventId, matchId, pageOffset, PAGE),
    enabled: ready, retry: false,
  })
  const scoped = ready && q.isSuccess && !q.isFetching &&
    q.data?.source === 'selected_branch_saved_revision' &&
    q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.player_id === playerId &&
    q.data?.match?.event_id === eventId && q.data?.match?.match_id === matchId &&
    q.data?.offset === pageOffset && q.data?.limit === PAGE &&
    Number.isInteger(q.data?.total_rallies) && q.data!.total_rallies >= 0 &&
    Array.isArray(q.data?.rallies) && typeof q.data?.has_more === 'boolean' &&
    (q.data?.replay_status === 'unavailable'
      ? q.data.total_rallies === 0 && q.data.rallies.length === 0 && !q.data.has_more
      : q.data?.replay_status === 'available' && q.data.total_rallies > 0 &&
        q.data.rallies.length === Math.max(0,Math.min(PAGE,q.data.total_rallies-pageOffset)) &&
        q.data.has_more === (pageOffset+PAGE<q.data.total_rallies))
  const data = scoped ? q.data : null
  const ids = data ? [data.player_a_id || data.player_id, data.player_b_id || data.match.opponent_player_id] : []
  const namesQuery = useQuery({
    queryKey: ['saved-match-names', runId, branchId, savedHead, ids.join('|')],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId!, ids),
    enabled: ready && ids.length === 2 && ids[0] !== ids[1], retry: false,
  })
  const namesData = namesQuery.data
  const names = namesQuery.isSuccess && !namesQuery.isFetching && namesData && savedHead &&
    namesData.saved_revision_id === savedHead &&
    namesData.run_id === runId && namesData.branch_id === branchId &&
    namesData.requested_ids?.join('|') === ids.join('|') && Array.isArray(namesData.players)
    ? Object.fromEntries(namesData.players.map(p => [p.player_id, p.display_name]))
    : {}
  const frame = data?.rallies.find(r => r.rally_index === index + 1)
  const playerName = (id: string | null | undefined): string => id ? (names[id] || id) : '—'
  const backParams = new URLSearchParams()
  const fromCareer = searchParams.get('tab') === 'career'
  if (fromCareer) backParams.set('tab', 'career')
  const careerSeason = searchParams.get('careerSeason')
  const careerPage = searchParams.get('careerPage')
  if (fromCareer && careerSeason !== null && /^(0|[1-9]\d*)$/.test(careerSeason) && Number(careerSeason) < 50)
    backParams.set('careerSeason', careerSeason)
  if (fromCareer && careerPage !== null && /^(0|[1-9]\d*)$/.test(careerPage) && Number(careerPage) <= 10000)
    backParams.set('careerPage', careerPage)
  const back = '/admin/runs/' + encodeURIComponent(runId) + '/people/' + encodeURIComponent(playerId) +
    (backParams.size ? '?' + backParams.toString() : '')
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · SAVED MATCH</p>
      <h2>{cs ? 'Detail zápasu' : 'Match detail'}</h2>
      <p className="subtitle">{cs ? 'Ověřený výsledek a archivovaný průběh' : 'Verified result and archived rally replay'}</p>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Zvolený historický checkpoint nemá zatím svůj detail zápasu. Současná revize se nezobrazuje jako historie.'
      : 'Historical checkpoint match detail is not supported. Current revision is not shown as history.'}</p> : <>
      {(isLoading || time.isLoading || (ready && (q.isPending||q.isFetching))) && <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>}
      {(error||time.error) && <p role="alert" className="error">{error||time.error}</p>}
      {!ready&&!isLoading&&!time.isLoading&&!error&&!time.error&&<p role="alert">{cs?
        'Chybí vybraná Branch, Saved HEAD nebo ID hráče/zápasu.':
        'Selected Branch, Saved HEAD or player/match ID is missing.'}</p>}
      {ready && q.error && <p role="alert" className="error">{formatApiError(q.error)}</p>}
      {ready && q.isSuccess && !q.isFetching && !scoped && <p role="alert" className="error">{cs
        ? 'Detail neodpovídá vybrané uložené revizi.' : 'Match detail does not match selected Saved Revision.'}</p>}
      <button type="button" disabled={!ready||q.isFetching}
        onClick={()=>{void q.refetch()}}>{cs?'Obnovit zápas / archiv':'Retry match / archive read'}</button>
      {data && <>
        <div className="run-home-status-block">
          <h3>{data.match.event_name}</h3>
          <p>{data.match.season} · W{data.match.week} · {data.match.draw_type==='main'?(cs?'hlavní část':'main'):data.match.draw_type==='qualification'?(cs?'kvalifikace':'qualification'):data.match.draw_type==='group'?(cs?'skupina':'group'):data.match.draw_type} ·
            {' '}{cs ? 'kolo' : 'round'} {data.match.round_number}</p>
          <p><strong>{playerName(data.winner_player_id)}</strong> {cs ? 'porazil' : 'defeated'}
            {' '}{playerName(data.loser_player_id)} · <strong>{data.match.scoreline}</strong></p>
          {data.match.completion === 'walkover' && <p>{cs ? 'Výsledek kontumací' : 'Walkover result'}</p>}
          <p className="status">Saved Revision: <code>{data.saved_revision_id}</code></p>
        </div>
        <h3>{cs ? 'Přehrání výměn' : 'Rally replay'}</h3>
        {data.replay_status === 'unavailable' && <p className="status">{cs
          ? 'Ověřený archiv výměn není pro tento zápas uložený. Výsledek je dostupný, průběh nevymýšlíme.'
          : 'No verified archived rally log exists for this match. The result is available; no replay is fabricated.'}</p>}
        {data.replay_status === 'available' && <>
          <p className="status">{cs ? 'Archivovaných výměn' : 'Archived rallies'}: {data.total_rallies}
            {' · '}{playerName(data.player_a_id)} (A) – {playerName(data.player_b_id)} (B)</p>
          {frame ? <div className="run-home-status-block">
            <p><strong>{cs ? 'Výměna' : 'Rally'} {frame.rally_index}/{data.total_rallies}</strong>
              {' · '}{cs ? 'Set' : 'Game'} {frame.set_number}</p>
            <p><strong>{frame.score_a_before} : {frame.score_b_before}</strong>
              {' → '}<strong>{frame.score_a_after} : {frame.score_b_after}</strong></p>
            <p>{cs ? 'Stav setů' : 'Games'}: {frame.sets_a_after} : {frame.sets_b_after}</p>
            <p>{cs ? 'Podává' : 'Server'}: {playerName(frame.server_player_id)}
              {' · '}{cs ? 'Vítěz výměny' : 'Rally winner'}: {playerName(frame.winner_player_id)}</p>
            {frame.set_complete && <p className="status">{cs ? 'Konec setu' : 'Game completed'}</p>}
            {frame.match_complete && <p className="status">{cs ? 'Konec zápasu' : 'Match completed'}</p>}
          </div> : <p className="status">{cs ? 'V tomto úseku není výměna.' : 'No rally at this cursor.'}</p>}
          <div className="run-home-status-block">
            <button type="button" disabled={q.isFetching || !frame || index === 0} onClick={() => setIndex(v => Math.max(0, v - 1))}>
              {cs ? '← Předchozí výměna' : '← Previous rally'}
            </button>
            {' '}
            <button type="button" disabled={q.isFetching || !frame || index + 1 >= data.total_rallies}
              onClick={() => setIndex(v => Math.min(data.total_rallies - 1, v + 1))}>
              {cs ? 'Další výměna →' : 'Next rally →'}
            </button>
          </div>
          <p className="status">{cs
            ? 'Přehrání používá pouze archivované výměny, nepřepočítává simulaci.'
            : 'Replay uses stored rally events only; simulation is never recalculated.'}</p>
        </>}
      </>}
    </>}
    <Link to={back}>{cs ? '← Zpět na profil hráče' : '← Back to player profile'}</Link>
  </section>
}
