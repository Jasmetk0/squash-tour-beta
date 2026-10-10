import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getRunHomePlayerIdentities } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { CurrentContextStrip, SectionCard } from '../components/RunScopedUi'

/** Deliberately scoped to the selected Branch and its Saved HEAD, not legacy career APIs. */
export function RunPlayerSavedProfilePage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const present = time.mode === 'present'
  const profileQuery = useQuery({
    queryKey: ['admin-saved-player-profile', runId, branchId, selectedBranch?.saved_head_revision_id, playerId],
    queryFn: () => getRunHomePlayerIdentities(runId, branchId!, [playerId]),
    enabled: Boolean(runId && branchId && playerId && present),
    retry: false
  })
  const valid = profileQuery.data?.run_id === runId &&
    profileQuery.data.branch_id === branchId &&
    profileQuery.data.saved_revision_id === selectedBranch?.saved_head_revision_id
  const profile = valid ? profileQuery.data?.players.find(p => p.player_id === playerId) : null
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · ADMIN · PLAYER</p>
      <h2>{profile?.name ?? (cs ? 'Profil hráče' : 'Player profile')}</h2>
      <p className="subtitle">{cs
        ? 'Identita podle uložené revize vybrané branche; žádná data z jiné branche.'
        : 'Identity from the selected Branch Saved Revision; no other-Branch fallback.'}</p>
    </div>
    <CurrentContextStrip items={[
      { label: 'Run', value: runId },
      { label: 'Branch', value: selectedBranch?.display_name ?? (isLoading ? '…' : '—') },
      { label: 'Player', value: playerId },
      { label: 'Time', value: present ? (cs ? 'Současnost' : 'Present') : (cs ? 'Historie' : 'Historical') },
    ]}/>
    {!present ? <p className="status">{cs
      ? 'Historický checkpoint nemá ověřenou rekonstrukci profilu hráče. Přepni čas na současnost.'
      : 'This checkpoint has no verified historical player profile projection. Return to Present.'}</p> : <>
      {isLoading && <p role="status">{cs ? 'Načítání branche…' : 'Loading Branch…'}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {profileQuery.isPending && branchId && <p role="status">{cs ? 'Načítání uloženého profilu…' : 'Loading saved profile…'}</p>}
      {profileQuery.isError && <p role="alert" className="error">{formatApiError(profileQuery.error)}</p>}
      {profileQuery.isSuccess && !valid && <p role="alert" className="error">Saved player profile identity mismatch</p>}
      {profileQuery.isSuccess && valid && !profile && <p className="status">{cs
        ? 'Toto ID nemá ve vybrané uložené revizi ověřené jméno ani zemi.'
        : 'This player ID has no verified name or country in the selected Saved Revision.'}</p>}
      {profile && <SectionCard title={cs ? 'Uložená identita' : 'Saved identity'}>
        <dl className="metadata-list">
          <div><dt>{cs ? 'Jméno' : 'Name'}</dt><dd>{profile.name}</dd></div>
          <div><dt>{cs ? 'Země' : 'Country'}</dt><dd>{profile.country_code}</dd></div>
          <div><dt>ID</dt><dd>{profile.player_id}</dd></div>
          <div><dt>{cs ? 'Zdroj identity' : 'Identity source'}</dt><dd>{profile.identity_source}</dd></div>
          <div><dt>Saved HEAD</dt><dd>{profileQuery.data?.saved_revision_id}</dd></div>
        </dl>
        <p className="status">{cs
          ? 'Sportovní statistiky, vývoj kariéry a historické profily zde zatím nejsou ověřenou projekcí.'
          : 'Sporting statistics, career development and historical player profiles are not verified in this view yet.'}</p>
      </SectionCard>}
    </>}
    <p><Link to={'/admin/runs/' + encodeURIComponent(runId)}>{cs ? '← Zpět na Run Home' : '← Back to Run Home'}</Link></p>
  </section>
}
