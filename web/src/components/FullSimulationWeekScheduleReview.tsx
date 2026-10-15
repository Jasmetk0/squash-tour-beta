import {useQuery} from '@tanstack/react-query'
import {getNextWeekExtensionInspection} from '../api/fullSimulationWeekReview'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

export function FullSimulationWeekScheduleReview({runId,branchId}:{runId:string;branchId:string}){
 const {language}=useLanguage()
 const result=useQuery({
   queryKey:['next-week-extension-inspection',runId,branchId],
   queryFn:()=>getNextWeekExtensionInspection(runId,branchId),
   retry:false,refetchOnWindowFocus:false,
 })
 return <section aria-label={language==='cs'?'Kontrola změněného týdenního rozpisu':'Changed week schedule inspection'}>
  <p>{language==='cs'?'Kontrola je pouze pro čtení; neopravuje původní příkaz ani nespouští zápasy.':
    'Read-only inspection: no original command changes or sporting execution.'}</p>
  {result.isPending&&<p role="status">{language==='cs'?'Kontroluji zmrazené rozpisy…':'Inspecting frozen schedules…'}</p>}
  {result.error&&<p role="alert">{formatApiError(result.error)}</p>}
  {result.data?.length===0&&<p>{language==='cs'?'Pro aktuální týden nebyl nalezen čekající příkaz Next Week.':'No pending Next Week command was found for the current week.'}</p>}
  {result.data?.map(item=><div key={item.command_id}>
   <p><code>{item.command_id}</code> · {language==='cs'?'Stav kontroly':'Inspection'}: <strong>{item.status==='append_only_proven'
    ? (language==='cs'?'Původní rozpis beze změn, nové sloty navazují':'Original schedule unchanged; new slots append')
    : item.status==='unchanged'?(language==='cs'?'Rozpis beze změny':'Schedule unchanged')
    : (language==='cs'?'Nelze bezpečně prokázat návaznost':'Append-only extension not proven')}</strong></p>
   {item.status==='append_only_proven'&&<p>{language==='cs'?'Nové knockout sloty':'New knockout slots'}: {item.new_slots.map(s=>s.ordinal).join(', ')}. {language==='cs'?'I zde je nutné samostatné schválení; tento náhled nic nepovoluje.':'Separate authorization is still required; this preview approves nothing.'}</p>}
   {item.status==='blocked'&&<p><code>{item.reason}</code></p>}
  </div>)}
 </section>
}
