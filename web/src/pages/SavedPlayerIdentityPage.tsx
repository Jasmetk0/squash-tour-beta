/** A narrowly canonical player identity card, not the legacy career/performance page. */
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getSavedHomePlayerIdentities } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function SavedPlayerIdentityPage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id
  const ready = time.mode === 'present' && !isLoading && !error && Boolean(branchId && savedHead && playerId)
  const q = useQuery({
    queryKey: ['home-player-identity', runId, branchId, savedHead, playerId],
    queryFn: () => getSavedHomePlayerIdentities(runId, branchId!, [playerId]),
    enabled: ready,
    retry: false,
  })
  const scoped = q.data?.run_id === runId && q.data.branch_id === branchId &&
    q.data.saved_revision_id === savedHead && q.data.requested_ids.length === 1 &&
    q.data.requested_ids[0] === playerId
  const player = scoped ? q.data?.players.find(item => item.player_id === playerId) : null
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · SAVED PLAYER IDENTITY</p>
      <h2>{player?.display_name || playerId}</h2>
      <p className="subtitle">{cs ? 'Čtecí detail uložené identity vybrané branche' : 'Read-only saved identity for the selected Branch'}</p>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Historický detail hráče pro vybraný checkpoint zatím není podporovaný. Aktuální identitu zde neukazujeme jako minulost.'
      : 'Historical player identity for this checkpoint is not supported. Current identity is not presented as history.'}</p> :
      <>
        {(isLoading || q.isPending && ready) && <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {q.error && <p className="error" role="alert">{formatApiError(q.error)}</p>}
        {q.isSuccess && !scoped && <p className="error" role="alert">{cs ? 'Identita neodpovídá vybrané uložené revizi.' : 'Identity does not match selected Saved Revision.'}</p>}
        {q.isSuccess && scoped && !player && <p className="status">{cs
          ? 'Pro tento identifikátor není v uložené revizi dostupné ověřené jméno.'
          : 'No verified name for this player ID exists in this Saved Revision.'}</p>}
        {player && <div className="run-home-status-block">
          <p><strong>{cs ? 'Jméno' : 'Name'}:</strong> {player.display_name}</p>
          <p><strong>{cs ? 'Země' : 'Country'}:</strong> {player.country_code}</p>
          <p><strong>ID:</strong> <code>{player.player_id}</code></p>
          <p><strong>{cs ? 'Zdroj identity' : 'Identity source'}:</strong> {player.identity_source}</p>
          <p><strong>{cs ? 'Uložená revize' : 'Saved Revision'}:</strong> <code>{q.data?.saved_revision_id}</code></p>
        </div>}
        <p className="status">{cs
          ? 'Tento detail zatím není úplný profil kariéry. Záměrně neukazuje atributy ani výsledky z legacy databáze nebo jiné branche.'
          : 'This is not yet a full career profile. It deliberately omits legacy or foreign-Branch attributes and results.'}</p>
      </>}
    <Link to={'/admin/runs/' + encodeURIComponent(runId)}>{cs ? '← Domů do Runu' : '← Back to Run Home'}</Link>
  </section>
}
