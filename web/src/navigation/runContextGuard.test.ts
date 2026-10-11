import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { allowConfirmedBranchLink, confirmAdminContextChange } from './runContextGuard'

describe('programmatic Run context decisions',()=>{
  const initialUrl=window.location.href
  beforeEach(()=>{
    vi.restoreAllMocks()
    document.body.innerHTML='<div class="app-shell--admin" data-run-form-edited="true"></div>'
  })
  afterEach(()=>{
    document.body.innerHTML=''
    window.history.replaceState(null,'',initialUrl)
  })
  it('asks once for an imperative Run switch and honors a cancellation',()=>{
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    expect(confirmAdminContextChange('Run')).toBe(false)
    expect(confirm).toHaveBeenCalledTimes(1)
    confirm.mockReturnValue(true)
    expect(confirmAdminContextChange('Run')).toBe(true)
    expect(confirm).toHaveBeenCalledTimes(2)
  })
  it('consumes exactly one already-approved branch link when the URL matches',()=>{
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    const target=new URL('/admin/runs/run-a?branch=a-other',window.location.origin)
    allowConfirmedBranchLink('run-a',target)
    window.history.replaceState(null,'',target.pathname+target.search)
    expect(confirmAdminContextChange('Branch','run-a','a-other')).toBe(true)
    expect(confirm).not.toHaveBeenCalled()
    expect(confirmAdminContextChange('Branch','run-a','a-other')).toBe(false)
    expect(confirm).toHaveBeenCalledTimes(1)
  })
  it('cannot reuse link approval for a different branch or path',()=>{
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false)
    const target=new URL('/admin/runs/run-a?branch=a-other',window.location.origin)
    allowConfirmedBranchLink('run-a',target)
    window.history.replaceState(null,'','/admin/runs/run-a/manage?branch=a-other')
    expect(confirmAdminContextChange('Branch','run-a','a-other')).toBe(false)
    expect(confirm).toHaveBeenCalledTimes(1)
  })
  it('skips warnings for clean Run transitions',()=>{
    document.querySelector('.app-shell--admin')?.removeAttribute('data-run-form-edited')
    const confirm=vi.spyOn(window,'confirm')
    expect(confirmAdminContextChange('Branch','run-a','a-other')).toBe(true)
    expect(confirm).not.toHaveBeenCalled()
  })
})
