import { useParams } from 'react-router-dom'

import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { FollowAlertsPanel } from '../components/FollowAlertsPanel'
import { useLanguage } from '../i18n/LanguageContext'

/** Following and alerts for the selected Branch's current Saved HEAD (present time only). */
export function FollowAlertsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id
  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · FOLLOWING</p>
      <h2>{cs ? 'Sledování a upozornění' : 'Following and alerts'}</h2>
    </div>
    {time.mode !== 'present' ? <p className="status">{cs
      ? 'Historický pohled na upozornění zatím není podporovaný. Současná data nevydáváme za historii.'
      : 'A historical view of alerts is not supported yet. Current data is not presented as history.'}</p>
      : isLoading || time.isLoading ? <p role="status">{cs ? 'Načítání…' : 'Loading…'}</p>
      : error || time.error ? <p role="alert">{String(error || time.error)}</p>
      : !branchId || !savedHead ? <p role="alert">{cs ? 'Chybí vybraná Branch nebo Saved HEAD.' : 'Selected Branch or Saved HEAD is missing.'}</p>
      : <FollowAlertsPanel key={[runId, branchId, savedHead].join('|')} runId={runId} branchId={branchId} savedHead={savedHead} cs={cs} />}
  </section>
}
