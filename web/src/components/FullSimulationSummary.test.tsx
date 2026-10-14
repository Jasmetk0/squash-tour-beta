import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {render,screen,within} from '@testing-library/react'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {FullSimulationSummary} from './FullSimulationSummary'

const api=vi.hoisted(()=>({getFullSimulationSummary:vi.fn()}))
vi.mock('../api/fullSimulationSummary',()=>api)
const payload={available:true,summary:{target_reached:false,start_week:{season_index:0,week:1},
  end_week:{season_index:0,week:7},original_final_week:{season_index:49,week:61},
  effective_target_week:{season_index:1,week:2},persisted_child_command_count:3,
  terminal_saved_revision_id:'saved-technical-id',terminal_audit_reason:'User-authored original reason',completed_tournaments:[{edition_id:'edition-id',
    completed_week:{season_index:0,week:5},champion_player_id:'champion-id',finalist_player_id:'finalist-id'}]}}
function open(language:'cs'|'en') {
  localStorage.setItem('squash-engine-language-v1',language)
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <LanguageProvider><FullSimulationSummary runId="run" branchId="branch" commandId="parent"/></LanguageProvider>
  </QueryClientProvider>)
}
afterEach(()=>vi.clearAllMocks())
describe('Full Simulation terminal summary presentation (mock HTTP boundary)',()=>{
  it.each(['cs','en'] as const)('shows frozen evidence in %s without translating technical IDs',async(language)=>{
    api.getFullSimulationSummary.mockResolvedValue(payload);open(language)
    const section=await screen.findByRole('region',{name:language==='cs'?'Uložený souhrn simulace':'Stored simulation summary'})
    expect(await within(section).findByText('S0 W7')).toBeInTheDocument()
    expect(section).toHaveTextContent(language==='cs'?'Skutečný konec':'Actual end')
    expect(section).toHaveTextContent('champion-id')
    expect(section).toHaveTextContent('saved-technical-id')
    expect(api.getFullSimulationSummary).toHaveBeenCalledWith('run','branch','parent')
    expect(api.getFullSimulationSummary).toHaveBeenCalledTimes(1)
  })
  it('explains missing legacy summaries without a current-position fallback',async()=>{
    api.getFullSimulationSummary.mockResolvedValue({available:false,summary:null});open('en')
    expect(await screen.findByText(/No terminal summary was recorded/)).toBeInTheDocument()
    expect(screen.queryByText('Actual end')).not.toBeInTheDocument()
  })
})
