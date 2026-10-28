import {render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {describe,expect,it} from 'vitest'
import {SavedFinalLookupLink,SavedPlayerProfileLink} from './savedTourPlayerLinks'

describe('shared immutable Saved Tour participant links',()=>{
  it('does not invent a current-profile link when the requested revision is historical',()=>{
    render(<MemoryRouter><SavedPlayerProfileLink runId="run-a" playerId="P1"
      showCurrent={false}/></MemoryRouter>)
    expect(screen.getByText('P1')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'P1'})).not.toBeInTheDocument()
  })
  it('only exposes a current-HEAD profile when the verified caller allows it',()=>{
    render(<MemoryRouter><SavedPlayerProfileLink runId="run/A" playerId="P#1"
      showCurrent={true}/></MemoryRouter>)
    expect(screen.getByRole('link',{name:'P#1'})).toHaveAttribute(
      'href','/admin/runs/run%2FA/people/P%231?tab=career')
  })
  it('opens final-finish evidence within the original Saved revision',()=>{
    const scope=new URLSearchParams('branch=bad&revision=other&season=17&tab=results&week=9&country=CZE&q=keep')
    render(<MemoryRouter><SavedFinalLookupLink runId="run-a" branch="branch-a"
      revision="rev-old" season={2} playerId="P1" params={scope} cs={false}/></MemoryRouter>)
    const link=screen.getByRole('link',{name:'Find published finals for P1'})
    for(const key of ['branch=branch-a','revision=rev-old','season=2','playerId=P1','q=keep'])
      expect(link).toHaveAttribute('href',expect.stringContaining(key))
    expect(link.getAttribute('href')).not.toContain('week=9')
    expect(link.getAttribute('href')).not.toContain('country=CZE')
  })
})
