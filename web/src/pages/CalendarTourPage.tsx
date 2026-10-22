import {Link,useParams} from 'react-router-dom'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {CalendarTourPanel} from './CalendarTourPanel'
import {NativeProspectSourceEpochPanel} from './NativeProspectSourceEpochPanel'
import {useLanguage} from '../i18n/LanguageContext'

export function CalendarTourPage(){
  const {runId=''}=useParams(),{selectedBranch}=useAdminBranch(),cs=useLanguage().language==='cs'
  const branch=selectedBranch?.run_id===runId?selectedBranch:null
  return <section className="panel"><Link to={`/admin/runs/${encodeURIComponent(runId)}/tour/calendar`}>{cs?'Kalendář Tour':'Tour calendar'}</Link>
    {!branch ? <p role="status">{cs ? 'Vyberte Branch tohoto Runu.' : 'Select a Branch of this Run.'}</p>
      : !branch.saved_head_revision_id ? <p role="status">{cs
        ? 'Vybraná Branch zatím nemá uloženou HEAD revizi. Kalendář Tour nelze načíst.'
        : 'The selected Branch has no saved HEAD revision yet. Tour calendar cannot be loaded.'}</p>
      : <><CalendarTourPanel runId={runId} branchId={branch.branch_id} head={branch.saved_head_revision_id}/><NativeProspectSourceEpochPanel runId={runId} branchId={branch.branch_id} head={branch.saved_head_revision_id}/></>}
  </section>
}
