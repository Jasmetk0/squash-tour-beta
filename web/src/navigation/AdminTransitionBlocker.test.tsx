import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, Link, RouterProvider, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { AdminTransitionBlocker } from './AdminTransitionBlocker'
import { allowConfirmedAdminNavigation } from './runContextGuard'

function Harness(): JSX.Element {
  const navigate = useNavigate()
  const location = useLocation()
  const [dirty, setDirty] = useState(false)
  return <div>
    <AdminTransitionBlocker isDirty={() => dirty} warning="Unsaved edits?" />
    <output aria-label="Current route">{location.pathname}</output>
    <label>Edit <input aria-label="Edit" defaultValue="original" /></label>
    <button type="button" onClick={() => setDirty(value => !value)}>Toggle dirty</button>
    <Link to="/next">Next link</Link>
    <button onClick={() => navigate('/next')}>Imperative next</button>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
    <button onClick={() => {
      allowConfirmedAdminNavigation('/next')
      navigate('/next')
    }}>Preapproved next</button>
  </div>
}
function setup(entries=['/initial'], index=0) {
  const router=createMemoryRouter([{path:'*',element:<Harness/>}],{
    initialEntries:entries,initialIndex:index
  })
  render(<RouterProvider router={router}/>)
  return router
}
describe('data-router Admin blocker',()=>{
  beforeEach(()=>vi.restoreAllMocks())

  it('preserves the route and entered values after rejecting link and imperative navigation',async()=>{
    setup()
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button',{name:'Toggle dirty'}))
    fireEvent.change(screen.getByRole('textbox',{name:'Edit'}),{target:{value:'keep me'}})
    fireEvent.click(screen.getByRole('link',{name:'Next link'}))
    await waitFor(()=>expect(confirm).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/initial')
    fireEvent.click(screen.getByRole('button',{name:'Imperative next'}))
    await waitFor(()=>expect(confirm).toHaveBeenCalledTimes(2))
    expect(screen.getByRole('textbox',{name:'Edit'})).toHaveValue('keep me')
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/initial')
  })

  it('handles browser history Back and Forward without losing the current screen',async()=>{
    setup(['/previous','/current','/future'],1)
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button',{name:'Toggle dirty'}))
    fireEvent.click(screen.getByRole('button',{name:'Back'}))
    await waitFor(()=>expect(confirm).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/current')
    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button',{name:'Forward'}))
    await waitFor(()=>expect(screen.getByLabelText('Current route')).toHaveTextContent('/future'))
    expect(confirm).toHaveBeenCalledTimes(2)
  })

  it('does not warn in a clean context and skips an explicitly preapproved navigation',async()=>{
    setup()
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button',{name:'Imperative next'}))
    await waitFor(()=>expect(screen.getByLabelText('Current route')).toHaveTextContent('/next'))
    expect(confirm).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Toggle dirty'}))
    fireEvent.click(screen.getByRole('button',{name:'Preapproved next'}))
    expect(confirm).not.toHaveBeenCalled()
  })
})
