import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {FullSimulationBoundaryTargets} from './FullSimulationBoundaryTargets'
import {boundaryReview} from '../api/fullSimulationBoundaryTargets.fixture'
const api=vi.hoisted(()=>({getBoundaryOptions:vi.fn(),setBoundaryTarget:vi.fn()}))
vi.mock('../api/fullSimulationBoundaryTargets',async original=>({...await original<object>(),...api}))
afterEach(()=>vi.resetAllMocks())
function open(language:'cs'|'en'){
 localStorage.setItem('squash-engine-language-v1',language)
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><LanguageProvider>
  <FullSimulationBoundaryTargets runId="run" branchId="branch" parentId="parent" onApplied={()=>{}}/>
 </LanguageProvider></QueryClientProvider>)
}
describe('precise target controls (mock API boundary)',()=>{
 it.each(['cs','en'] as const)('reviews exact scope, explicit audit and lost-response retry (%s)',async language=>{
  api.getBoundaryOptions.mockResolvedValue(boundaryReview());api.setBoundaryTarget.mockRejectedValueOnce(Error('offline')).mockResolvedValue({boundary_target:boundaryReview().options[0]})
  open(language)
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Prověřit přesné cíle':'Review precise targets'}))
  const choice=await screen.findByLabelText(language==='cs'?'Cílová hranice':'Target boundary')
  expect(api.getBoundaryOptions).toHaveBeenCalledWith('run','branch','parent')
  fireEvent.change(choice,{target:{value:'d'.repeat(64)}})
  const operator=screen.getByLabelText(language==='cs'?'Operátor cíle':'Target operator')
  fireEvent.change(operator,{target:{value:'Auditor'}})
  fireEvent.change(screen.getByLabelText(language==='cs'?'Důvod změny cíle':'Target audit reason'),{target:{value:'Exact final boundary'}})
  const apply=screen.getByRole('button',{name:language==='cs'?'Použít přesný cíl':'Apply precise target'})
  expect(apply).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(apply)
  await screen.findByText('offline');expect(choice).toBeDisabled();expect(operator).toBeDisabled()
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Zopakovat stejný cílový požadavek':'Retry same target request'}))
  await waitFor(()=>expect(api.setBoundaryTarget).toHaveBeenCalledTimes(2))
  expect(api.setBoundaryTarget.mock.calls[1]).toEqual(api.setBoundaryTarget.mock.calls[0])
  expect(api.setBoundaryTarget.mock.calls[0][2]).toMatchObject({target_command_id:'parent',operator_label:'Auditor',audit_reason:'Exact final boundary',boundary_target:boundaryReview().options[0]})
  expect(screen.queryByRole('button',{name:/Save|Uložit/})).toBeNull()
 })
 it('shows unsupported editions as unavailable and never invents a selectable final',async()=>{
  api.getBoundaryOptions.mockResolvedValue({...boundaryReview(),options:[]})
  open('en');fireEvent.click(screen.getByRole('button',{name:'Review precise targets'}))
  await screen.findByText('No eligible precise boundary in the current week.')
  expect(screen.queryByRole('combobox')).toBeNull();expect(screen.queryByRole('button',{name:'Apply precise target'})).toBeNull()
  expect(screen.getByText('unplanned')).toBeInTheDocument()
 })
 it('keeps a stale server rejection visible and permits deliberate refresh',async()=>{
  api.getBoundaryOptions.mockRejectedValue(Error('Stale schedule; review again'))
  open('en');fireEvent.click(screen.getByRole('button',{name:'Review precise targets'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Stale schedule')
  fireEvent.click(screen.getByRole('button',{name:'Refresh canonical choices'}))
  await waitFor(()=>expect(api.getBoundaryOptions).toHaveBeenCalledTimes(2))
 })
})
