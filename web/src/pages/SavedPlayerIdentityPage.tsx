/** Branch-owned present-time profile from a single verified Saved Revision. */
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getSavedPlayerProfile } from '../api/client'
import { PlayerHealthAdminPanel } from './PlayerHealthAdminPanel'
import { SavedPlayerMatchesPanel } from './SavedPlayerMatchesPanel'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import {safeCountryRosterReturn} from './countrySavedRosterPermalink'

export function SavedPlayerIdentityPage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  // Profile tabs are URL state so the match-detail Back link can restore the career view.
  const requestedTab = searchParams.get('tab')
  const tab: 'overview' | 'attributes' | 'career' | 'health' =
    requestedTab === 'attributes' || requestedTab === 'career' || requestedTab === 'health'
      ? requestedTab : 'overview'
  const setTab = (next: typeof tab) => {
    const copy = new URLSearchParams(searchParams)
    if (next === 'overview') copy.delete('tab')
    else copy.set('tab', next)
    setSearchParams(copy)
  }
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id
  const ready = time.mode === 'present' && !time.isLoading && !time.error &&
    !isLoading && !error && Boolean(branchId && savedHead && playerId)
  const q = useQuery({
    queryKey: ['saved-player-profile', runId, branchId, savedHead, playerId],
    queryFn: () => getSavedPlayerProfile(runId, branchId!, playerId),
    enabled: ready,
    retry: false,
  })
  const scoped = ready && q.isSuccess && !q.isFetching &&
    q.data?.source === 'selected_branch_saved_revision' &&
    q.data?.run_id === runId && q.data.branch_id === branchId &&
    q.data.saved_revision_id === savedHead && q.data.player_id === playerId
  const profile = scoped ? q.data : null
  const player = profile?.identity
  const countryReturn = safeCountryRosterReturn(searchParams.get('fromCountry'),
    runId,player?.country_code??null)
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · SAVED PLAYER PROFILE</p>
      <h2>{player?.display_name || playerId}</h2>
      <p className="subtitle">{tab==='health' ? (cs?'Současný zdravotní stav v Adminu':'Current Admin health state') : (cs ? 'Sportovní přehled z uložené revize vybrané branche' : 'Sporting summary from the selected Branch Saved Revision')}</p>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Historický profil pro tento checkpoint zatím není podporovaný. Současná data nevydáváme za historii.'
      : 'Historical player profile for this checkpoint is not supported. Current data is not presented as history.'}</p> :
      <>
        {(isLoading || time.isLoading || (ready && (q.isPending || q.isFetching))) && <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>}
        {(error||time.error) && <p className="error" role="alert">{error||time.error}</p>}
        {!ready&&!isLoading&&!time.isLoading&&!error&&!time.error&&<p role="alert">{cs?
          'Chybí vybraná Branch, Saved HEAD nebo ID hráče.':'Selected Branch, Saved HEAD or player ID is missing.'}</p>}
        {ready && q.error && <p className="error" role="alert">{formatApiError(q.error)}</p>}
        {ready && q.isSuccess && !q.isFetching && !scoped && <p className="error" role="alert">{cs ? 'Profil neodpovídá vybrané revizi.' : 'Profile does not match selected Saved Revision.'}</p>}
        <button type="button" disabled={!ready||q.isFetching}
          onClick={()=>{void q.refetch()}}>{cs?'Obnovit profil':'Retry profile read'}</button>
        {profile && !player && <p className="status">{cs
          ? 'Ověřená identita není v této uložené revizi dostupná. Sportovní údaje nezobrazujeme.'
          : 'No verified player identity in this Saved Revision. No sporting information is shown.'}</p>}
        {profile && player && <>
          <div className="actions" role="tablist" aria-label={cs ? 'Záložky profilu hráče' : 'Player profile tabs'}
            onKeyDown={event=>{
              const order=['overview','attributes','career','health'] as const
              const at=order.indexOf(tab)
              const next=event.key==='ArrowRight'?order[(at+1)%order.length]:
                event.key==='ArrowLeft'?order[(at+order.length-1)%order.length]:
                event.key==='Home'?order[0]:event.key==='End'?order[order.length-1]:null
              if(next){
                event.preventDefault()
                setTab(next)
                const buttons=event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')
                buttons[order.indexOf(next)]?.focus()
              }
            }}>
            <button type="button" role="tab" aria-selected={tab==='overview'}
              onClick={()=>setTab('overview')}>{cs ? 'Přehled' : 'Overview'}</button>
            <button type="button" role="tab" aria-selected={tab==='attributes'}
              onClick={()=>setTab('attributes')}>{cs ? 'Atributy' : 'Attributes'}</button>
            <button type="button" role="tab" aria-selected={tab==='career'}
              onClick={()=>setTab('career')}>{cs ? 'Kariéra a výsledky' : 'Career & results'}</button>
            <button type="button" role="tab" aria-selected={tab==='health'}
              onClick={()=>setTab('health')}>{cs ? 'Zdraví' : 'Health'}</button>
          </div>
          {tab==='health' && <section role="tabpanel" aria-label={cs?'Zdraví':'Health'}>
            <PlayerHealthAdminPanel key={branchId+':'+savedHead+':'+playerId} runId={runId} branchId={branchId!}
              savedHead={savedHead!} playerId={playerId} branchReadOnly={Boolean(selectedBranch?.read_only)} locale={language}/>
          </section>}
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
            <strong>#{profile.rank ?? '—'}</strong> · {profile.points ?? '—'} {cs ? 'bodů' : 'points'}
          </p>}
          {profile.ranking_week_ordinal != null && <p className="status">
            {cs ? 'Poslední publikace · index týdne: ' : 'Latest publication · week index: '}
            {profile.ranking_week_ordinal}
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
          <p className="status">{tab==='health' ? (cs?'Zdraví zobrazuje současný pracovní stav v Adminu. Samostatné uložení vytvoří obnovitelnou revizi.':'Health shows the current Admin working state. A separate Save creates a recoverable revision.') : cs
            ? 'Zdroj: ověřená Saved Revision. Nezahrnuje nepublikované turnaje, legacy kariéru, atributy ani jinou branch.'
            : 'Source: verified Saved Revision. Excludes unpublished tournaments, legacy career, attributes and other Branches.'}</p>
        </>}
      </>}
    {countryReturn&&<p><Link to={countryReturn}>{cs
      ? '← Zpět na filtrovanou soupisku země' : '← Back to filtered country roster'}</Link></p>}
    <p><Link to={'/admin/runs/' + encodeURIComponent(runId) + '/players'}>{cs ? '← Zpět na Hráče' : '← Back to Players'}</Link></p>
    <Link to={'/admin/runs/' + encodeURIComponent(runId)}>{cs ? '← Domů do Runu' : '← Back to Run Home'}</Link>
  </section>
}
