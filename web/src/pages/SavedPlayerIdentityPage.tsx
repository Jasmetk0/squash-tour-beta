/** Branch-owned present-time profile from a single verified Saved Revision. */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getSavedPlayerProfile } from '../api/client'
import { SavedPlayerMatchesPanel } from './SavedPlayerMatchesPanel'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function SavedPlayerIdentityPage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [tab, setTab] = useState<'overview' | 'attributes' | 'career'>('overview')
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id
  const ready = time.mode === 'present' && !isLoading && !error && Boolean(branchId && savedHead && playerId)
  const q = useQuery({
    queryKey: ['saved-player-profile', runId, branchId, savedHead, playerId],
    queryFn: () => getSavedPlayerProfile(runId, branchId!, playerId),
    enabled: ready,
    retry: false,
  })
  const scoped = q.data?.run_id === runId && q.data.branch_id === branchId &&
    q.data.saved_revision_id === savedHead && q.data.player_id === playerId
  const profile = scoped ? q.data : null
  const player = profile?.identity
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · SAVED PLAYER PROFILE</p>
      <h2>{player?.display_name || playerId}</h2>
      <p className="subtitle">{cs ? 'Sportovní přehled z uložené revize vybrané branche' : 'Sporting summary from the selected Branch Saved Revision'}</p>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Historický profil pro tento checkpoint zatím není podporovaný. Současná data nevydáváme za historii.'
      : 'Historical player profile for this checkpoint is not supported. Current data is not presented as history.'}</p> :
      <>
        {(isLoading || q.isPending && ready) && <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {q.error && <p className="error" role="alert">{formatApiError(q.error)}</p>}
        {q.isSuccess && !scoped && <p className="error" role="alert">{cs ? 'Profil neodpovídá vybrané revizi.' : 'Profile does not match selected Saved Revision.'}</p>}
        {profile && !player && <p className="status">{cs
          ? 'Ověřená identita není v této uložené revizi dostupná. Sportovní údaje nezobrazujeme.'
          : 'No verified player identity in this Saved Revision. No sporting information is shown.'}</p>}
        {profile && player && <>
          <div className="actions" role="tablist" aria-label={cs ? 'Záložky profilu hráče' : 'Player profile tabs'}>
            <button type="button" role="tab" aria-selected={tab==='overview'}
              onClick={()=>setTab('overview')}>{cs ? 'Přehled' : 'Overview'}</button>
            <button type="button" role="tab" aria-selected={tab==='attributes'}
              onClick={()=>setTab('attributes')}>{cs ? 'Atributy' : 'Attributes'}</button>
            <button type="button" role="tab" aria-selected={tab==='career'}
              onClick={()=>setTab('career')}>{cs ? 'Kariéra a výsledky' : 'Career & results'}</button>
          </div>
          {tab==='overview' && <section role="tabpanel" aria-label={cs ? 'Přehled' : 'Overview'}>
          <div className="run-home-status-block">
            <p><strong>{cs ? 'Jméno' : 'Name'}:</strong> {player.display_name}</p>
            <p><strong>{cs ? 'Země' : 'Country'}:</strong> {player.country_code}</p>
            <p><strong>ID:</strong> <code>{player.player_id}</code></p>
            <p><strong>{cs ? 'Původ identity' : 'Identity source'}:</strong> {player.identity_source}</p>
            <p><strong>{cs ? 'Uložená revize' : 'Saved Revision'}:</strong> <code>{profile.saved_revision_id}</code></p>
          </div>
          <h3>{cs ? 'Oficiální žebříček' : 'Official ranking'}</h3>
          {profile.ranking_status === 'unpublished' && <p className="status">{cs
            ? 'Žádný oficiální týdenní žebříček dosud nebyl publikován.'
            : 'No official weekly ranking has been published yet.'}</p>}
          {profile.ranking_status === 'unranked' && <p className="status">{cs
            ? 'Hráč není v posledním publikovaném žebříčku zařazen.'
            : 'Player is not ranked in the latest published ranking.'}</p>}
          {profile.ranking_status === 'ranked' && <p>
            <strong>#{profile.rank}</strong> · {profile.points} {cs ? 'bodů' : 'points'}
          </p>}
          {profile.ranking_week_ordinal != null && <p className="status">
            {cs ? 'Poslední publikace: ' : 'Latest publication: '}
            {2000 + Math.floor(profile.ranking_week_ordinal / 61)}/{String((2001 + Math.floor(profile.ranking_week_ordinal / 61)) % 100).padStart(2, '0')}
            {' · W'}{profile.ranking_week_ordinal % 61 + 1}
          </p>}
          </section>}
          {tab==='attributes' && <section role="tabpanel" aria-label={cs ? 'Atributy' : 'Attributes'}>
            <h3>{cs ? 'Sportovní atributy' : 'Sporting attributes'}</h3>
            <p className="status">{cs
              ? 'Autoritativní 0–200 OVR, Potential OVR a sada atributů zatím nejsou v tomto saved-player read kontraktu dostupné. Z legacy stupnice ani jiných branchí je nepřebíráme.'
              : 'Authoritative 0–200 OVR, Potential OVR and the attribute catalogue are not available in this saved-player read contract yet. Legacy scales and other Branches are not substituted.'}</p>
            <p className="status">{cs ? 'Režim: jen čtení. Úpravy se zpřístupní samostatným výslovným krokem.' :
              'Read-only mode. Editing will require a separate explicit action.'}</p>
          </section>}
          {tab==='career' && <section role="tabpanel" aria-label={cs ? 'Kariéra a výsledky' : 'Career & results'}>
          <h3>{cs ? 'Turnajová historie' : 'Tournament history'}</h3>
          <p><strong>{cs ? 'Tituly' : 'Titles'}:</strong> {profile.titles}
            {' · '}<strong>{cs ? 'Finálové účasti' : 'Final appearances'}:</strong> {profile.final_appearances}</p>
          {profile.total_tournament_results === 0 && <p className="status">{cs
            ? 'V uložené revizi nejsou ověřené publikované finálové výsledky tohoto hráče.'
            : 'No verified published finals for this player in the Saved Revision.'}</p>}
          {profile.tournament_results.length > 0 && <ul className="run-home-feed">
            {profile.tournament_results.map(result => <li key={result.event_id}>
              <span><strong>{result.event_name}</strong><small>
                {result.season} · W{result.week} · {result.finish === 'champion'
                  ? (cs ? 'Vítěz' : 'Champion') : (cs ? 'Finalista' : 'Runner-up')}
              </small></span>
            </li>)}
          </ul>}
          {profile.total_tournament_results > profile.tournament_results.length &&
            <p className="status">{cs ? 'Zobrazeno posledních 10 finálových výsledků.' : 'Showing the last 10 final results.'}</p>}
          <SavedPlayerMatchesPanel key={branchId + ':' + savedHead + ':' + playerId}
            runId={runId} branchId={branchId!} savedHead={savedHead!}
            playerId={playerId} locale={language} />
          </section>}
          <p className="status">{cs
            ? 'Zdroj: ověřená Saved Revision. Nezahrnuje nepublikované turnaje, legacy kariéru, atributy ani jinou branch.'
            : 'Source: verified Saved Revision. Excludes unpublished tournaments, legacy career, attributes and other Branches.'}</p>
        </>}
      </>}
    <p><Link to={'/admin/runs/' + encodeURIComponent(runId) + '/players'}>{cs ? '← Zpět na Hráče' : '← Back to Players'}</Link></p>
    <Link to={'/admin/runs/' + encodeURIComponent(runId)}>{cs ? '← Domů do Runu' : '← Back to Run Home'}</Link>
  </section>
}
