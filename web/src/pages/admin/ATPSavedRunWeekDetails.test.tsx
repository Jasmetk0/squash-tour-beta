import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ATPSavedRunWeekDetails } from './ATPSavedRunWeekDetails'
import type { SavedATPRunWeekPreview } from '../../api/atpCalendarReferencePackages'

const api=vi.hoisted(()=>({getSavedATPRunWeekPreview:vi.fn(),ApiError:class ApiError extends Error{}}))
vi.mock('../../api/client',()=>api)
vi.mock('../../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
const week={calendar_year:2025,year_week:38,season_index:0,season_week:38}
const fixture:SavedATPRunWeekPreview={
  events:[
    {source_identity:'atp_2025_chengdu',source_start_date:'2025-09-17',
      source_end_date:'2025-09-23',review_flags:['single_week_majority_precedes_finish_week'],
      run_weeks:[week],source_finish_run_week:{...week,year_week:39,season_week:39}},
    {source_identity:'atp_2025_vienna',source_start_date:'2025-10-20',
      source_end_date:'2025-10-26',review_flags:[],run_weeks:[{...week,year_week:43,season_week:43}],
      source_finish_run_week:{...week,year_week:43,season_week:43}}
  ],
  outside_horizon:[{source_identity:'atp_2025_brisbane',source_start_date:'2024-12-29',
    source_end_date:'2025-01-05',review_flags:['cross_iso_year'],
    outside_year_weeks:[{calendar_year:2025,year_week:1}]}],
  source_tour_bindings:{selected_occurrences:{
    atp_2025_chengdu:{series_name:'Chengdu Open',historical_category_label:'ATP 250'},
    atp_2025_vienna:{series_name:'Vienna Open',historical_category_label:'ATP 500'},
    atp_2025_brisbane:{series_name:'Brisbane',historical_category_label:'ATP 250'}
  }}
}
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const ui=(revisionId:string)=><QueryClientProvider client={client}>
    <ATPSavedRunWeekDetails runId="run" branchId="branch" revisionId={revisionId} years={[2024,2025]}/>
  </QueryClientProvider>
  const view=render(ui('rev1'))
  return {...view,changeRevision:(id:string)=>view.rerender(ui(id))}
}
const load=()=>userEvent.click(screen.getByRole('button',{name:'Preview weeks from the Saved ATP Package'}))
describe('ATP Saved reference mapping review',()=>{
  beforeEach(()=>{vi.clearAllMocks();api.getSavedATPRunWeekPreview.mockResolvedValue(fixture)})
  it('distinguishes mapped dates and review flags from actual sporting readiness',async()=>{
    mount()
    expect(api.getSavedATPRunWeekPreview).not.toHaveBeenCalled()
    await load()
    const review=await screen.findByRole('region',{name:'Reference mapping review'})
    expect(review.closest('[data-run-navigation-readonly]')).not.toBeNull()
    expect(review).toHaveTextContent('Verified source dates in preview3')
    expect(review).toHaveTextContent('Mapped inside Run horizon2')
    expect(review).toHaveTextContent('Review flags inside horizon1')
    expect(review).toHaveTextContent('not assessed by this source')
    expect(review).toHaveTextContent('No review flag does not mean approval.')
    expect(api.getSavedATPRunWeekPreview).toHaveBeenCalledWith('run','branch','rev1',2025)
    await userEvent.click(within(review).getByRole('checkbox'))
    expect(screen.getByText(/Chengdu Open/)).toBeInTheDocument()
    expect(screen.queryByText(/Vienna Open/)).not.toBeInTheDocument()
    expect(review).toHaveTextContent('Shown inside / outside horizon: 1 / 0')
    await userEvent.click(within(review).getByRole('button',{name:'Clear preview filters'}))
    await userEvent.selectOptions(within(review).getByLabelText('Historical category'),'ATP 500')
    expect(screen.getByText(/Vienna Open/)).toBeInTheDocument()
    expect(screen.queryByText(/Chengdu Open/)).not.toBeInTheDocument()
    await userEvent.type(within(review).getByRole('searchbox'),'missing')
    expect(screen.getByText('No preview rows match the filters.')).toBeInTheDocument()
    expect(api.getSavedATPRunWeekPreview).toHaveBeenCalledTimes(1)
  })
  it('does not reuse the preview after changing year or Saved revision',async()=>{
    const view=mount()
    await load()
    await screen.findByRole('region',{name:'Reference mapping review'})
    await userEvent.selectOptions(screen.getByLabelText('ATP season for this Run'),'2024')
    expect(screen.queryByRole('region',{name:'Reference mapping review'})).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('ATP season for this Run'),'2025')
    expect(screen.queryByRole('region',{name:'Reference mapping review'})).not.toBeInTheDocument()
    view.changeRevision('rev2')
    expect(api.getSavedATPRunWeekPreview).toHaveBeenCalledTimes(1)
    await load()
    await screen.findByRole('region',{name:'Reference mapping review'})
    expect(api.getSavedATPRunWeekPreview).toHaveBeenLastCalledWith('run','branch','rev2',2025)
  })
  it('hides a formerly successful preview after refresh fails',async()=>{
    api.getSavedATPRunWeekPreview.mockResolvedValueOnce(fixture).mockRejectedValueOnce(new Error('offline'))
    mount()
    await load()
    await screen.findByRole('region',{name:'Reference mapping review'})
    await load()
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
    expect(screen.queryByRole('region',{name:'Reference mapping review'})).not.toBeInTheDocument()
    expect(screen.queryByText(/Chengdu Open/)).not.toBeInTheDocument()
  })
})
