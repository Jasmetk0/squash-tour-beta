import {Link,useParams} from 'react-router-dom'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {CalendarTourPanel} from './CalendarTourPanel'
import {useLanguage} from '../i18n/LanguageContext'

export function CalendarTourPage(){
  const {runId=''}=useParams(),{selectedBranch}=useAdminBranch(),cs=useLanguage().language==='cs'
  const branch=selectedBranch?.run_id===runId?selectedBranch:null
  return <section className="panel"><Link to={`/admin/runs/${encodeURIComponent(runId)}/tour/calendar`}>{cs?'Kalendář Tour':'Tour calendar'}</Link>
    {branch?.saved_head_revision_id?<CalendarTourPanel runId={runId} branchId={branch.branch_id} head={branch.saved_head_revision_id}/>:<p>{cs?'Vyberte Branch tohoto Runu.':'Select a Branch of this Run.'}</p>}
  </section>
}
