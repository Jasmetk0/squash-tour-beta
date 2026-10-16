import {act,fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {RunCalendarExtensionInspection} from './RunCalendarExtensionInspection'
const api=vi.hoisted(()=>({previewRunCalendarExtension:vi.fn()}))
vi.mock('../api/client',()=>api)
vi.mock('../utils/apiErrors',()=>({formatApiError:(e:unknown)=>String(e)}))
const response=(n:number)=>({original_calendar:{season_count:3},proposed_calendar:{season_count:n},added_seasons:n-3,
  added_weeks:(n-3)*52,first_added_week:{season_label:'2033',season_week:1},new_last_week:{season_label:'2034',season_week:52},source_saved_head_revision_id:'revision'})
function mount(){const props={runId:'r',branchId:'a',currentCount:3,language:'en' as const};const view=render(<RunCalendarExtensionInspection {...props}/>);
  return {...view,switchBranch:()=>view.rerender(<RunCalendarExtensionInspection {...props} branchId="b"/>)}}
describe('extension inspection response scope',()=>{
  beforeEach(()=>vi.clearAllMocks())
  it('rejects an old successful response after the requested horizon changes',async()=>{
    let finish!:(v:unknown)=>void;api.previewRunCalendarExtension.mockReturnValue(new Promise(resolve=>{finish=resolve}))
    mount();fireEvent.click(screen.getByRole('button',{name:'Inspect extension'}))
    fireEvent.change(screen.getByRole('spinbutton'),{target:{value:'5'}})
    await act(async()=>finish(response(4)))
    expect(screen.queryByText('Proposed horizon:')).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Inspect extension'})).toBeEnabled()
  })
  it('discards errors from the former Branch and allows a new request',async()=>{
    let fail!:(e:Error)=>void;api.previewRunCalendarExtension.mockReturnValueOnce(new Promise((_resolve,reject)=>{fail=reject}))
    const view=mount();fireEvent.click(screen.getByRole('button',{name:'Inspect extension'}));view.switchBranch()
    api.previewRunCalendarExtension.mockResolvedValue(response(4))
    fireEvent.click(screen.getByRole('button',{name:'Inspect extension'}))
    await act(async()=>fail(Error('Former Branch failure')))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(await screen.findByText('Proposed horizon:')).toBeInTheDocument()
    expect(api.previewRunCalendarExtension).toHaveBeenLastCalledWith('r','b',4)
  })
})
