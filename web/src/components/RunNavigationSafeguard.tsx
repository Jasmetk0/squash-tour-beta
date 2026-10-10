import { useEffect } from 'react'

/**
 * Guard transitions that would unmount an edited Run form or leave the current Run.
 * This is intentionally conservative; authoritative Working Draft save/restore remains server-owned.
 * It does not replace component-level Save, Undo or recovery guards.
 */
export function RunNavigationSafeguard({ runId }: { runId: string }): null {
  useEffect(() => {
    let formEdited = false
    const currentPrefix = '/admin/runs/' + encodeURIComponent(runId)

    const recordEdit = (event: Event): void => {
      const target = event.target
      if (!(target instanceof HTMLElement) || !target.closest('main')) return
      if (target.matches('input, textarea, select')) formEdited = true
    }
    const confirmLink = (event: MouseEvent): void => {
      if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return
      const target = event.target
      if (!(target instanceof Element)) return
      const link = target.closest('a[href]')
      if (!(link instanceof HTMLAnchorElement) || link.target === '_blank') return
      const url = new URL(link.href)
      if (url.origin !== window.location.origin) return
      const staysInsideRun = url.pathname === currentPrefix || url.pathname.startsWith(currentPrefix + '/')
      if (staysInsideRun && !formEdited) return
      const warning = staysInsideRun
        ? 'This page may contain unapplied edits. Leave this form? Save or cancel first if needed.'
        : 'Leave this Run? Make sure any unsaved changes are saved before switching context.'
      if (!window.confirm(warning)) {
        event.preventDefault()
        event.stopImmediatePropagation()
        return
      }
      formEdited = false
    }
    const protectReload = (event: BeforeUnloadEvent): void => {
      if (!formEdited) return
      event.preventDefault()
      event.returnValue = ''
    }
    document.addEventListener('input', recordEdit, true)
    document.addEventListener('change', recordEdit, true)
    document.addEventListener('click', confirmLink, true)
    window.addEventListener('beforeunload', protectReload)
    return () => {
      document.removeEventListener('input', recordEdit, true)
      document.removeEventListener('change', recordEdit, true)
      document.removeEventListener('click', confirmLink, true)
      window.removeEventListener('beforeunload', protectReload)
    }
  }, [runId])
  return null
}
