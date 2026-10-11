import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getBranchWorkingDraft } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { allowConfirmedBranchLink } from '../navigation/runContextGuard'

export const RUN_NAVIGATION_SAVED = 'run-navigation-saved'

/** Only a verified, matching Run/Branch Save may dismiss local form-edit evidence. */
export function acknowledgeSavedRunForm(runId: string, branchId: string): void {
  window.dispatchEvent(new CustomEvent(RUN_NAVIGATION_SAVED, {
    detail: { runId, branchId }
  }))
}

type Control = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
function editableControl(target: EventTarget | null): Control | null {
  if (!(target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement)) return null
  if (!target.closest('main') ||
      target.closest('[data-run-navigation-readonly]') ||
      target.matches('[disabled], [readonly], [data-run-navigation-readonly]')) return null
  if (target instanceof HTMLInputElement &&
      ['hidden', 'search', 'button', 'submit', 'reset', 'file'].includes(target.type)) return null
  return target
}
function controlValue(control: Control): string {
  if (control instanceof HTMLInputElement &&
      (control.type === 'checkbox' || control.type === 'radio')) return String(control.checked)
  if (control instanceof HTMLSelectElement && control.multiple)
    return JSON.stringify(Array.from(control.selectedOptions, option => option.value))
  return control.value
}
function originalValue(control: Control): string {
  if (control instanceof HTMLInputElement &&
      (control.type === 'checkbox' || control.type === 'radio')) return String(control.defaultChecked)
  if (control instanceof HTMLSelectElement) {
    if (control.multiple) return JSON.stringify(
      Array.from(control.options).filter(option => option.defaultSelected).map(option => option.value)
    )
    return Array.from(control.options).find(option => option.defaultSelected)?.value ?? control.options[0]?.value ?? ''
  }
  return control.defaultValue
}

/**
 * Blocks only evidence-backed unsaved Run changes, never read-only exploration.
 *
 * Form edits are compared with their pre-edit values; reverting the value clears
 * that control's evidence. The authoritative Branch Working Draft is checked
 * separately: staging a server mutation remains protected until a real Save.
 * A matching successful Save also clears local form evidence.
 *
 * This guards native link and reload/close transitions. The two Admin context
 * selectors consult the same shell flag for programmatic Run/Branch switching.
 * This does not purport to guard every programmatic navigation in legacy pages.
 */
export function RunNavigationSafeguard({ runId }: { runId: string }): null {
  const { selectedBranch } = useAdminBranch()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = branchId ? selectedBranch?.saved_head_revision_id : null
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId!),
    enabled: Boolean(branchId),
    retry: false
  })
  const draft = draftQuery.data
  const serverDirty = Boolean(
    branchId && draft?.run_id === runId && draft.branch_id === branchId &&
    draft.base_saved_revision_id === savedHead && draft.status === 'dirty'
  )
  const serverDirtyRef = useRef(serverDirty)
  const localDirtyRef = useRef(false)
  serverDirtyRef.current = serverDirty

  useEffect(() => {
    const shell = document.querySelector('.app-shell--admin')
    const controls = new Set<Control>()
    const baselines = new WeakMap<Control, string>()
    const currentPrefix = '/admin/runs/' + encodeURIComponent(runId)

    function unsaved(): boolean {
      for (const control of controls) {
        if (!control.isConnected || control.closest('[data-run-navigation-readonly]') ||
            controlValue(control) === baselines.get(control)) controls.delete(control)
      }
      return controls.size > 0 || serverDirtyRef.current
    }
    function sync(): void {
      localDirtyRef.current = controls.size > 0
      if (unsaved()) shell?.setAttribute('data-run-form-edited', 'true')
      else shell?.removeAttribute('data-run-form-edited')
    }
    function rememberBaseline(event: Event): void {
      const control = editableControl(event.target)
      if (control && !baselines.has(control)) baselines.set(control, controlValue(control))
    }
    function recordEdit(event: Event): void {
      const control = editableControl(event.target)
      if (!control) return
      if (!baselines.has(control)) baselines.set(control, originalValue(control))
      if (controlValue(control) === baselines.get(control)) controls.delete(control)
      else controls.add(control)
      sync()
    }
    function confirmLink(event: MouseEvent): void {
      if (event.defaultPrevented || event.button !== 0 || event.ctrlKey ||
          event.altKey || event.metaKey || event.shiftKey) return
      const target = event.target
      if (!(target instanceof Element)) return
      const anchor = target.closest('a[href]')
      if (!(anchor instanceof HTMLAnchorElement) || anchor.target === '_blank') return
      const destination = new URL(anchor.href)
      if (destination.origin !== window.location.origin || !unsaved()) return
      const staysInside = destination.pathname === currentPrefix ||
        destination.pathname.startsWith(currentPrefix + '/')
      const warning = staysInside
        ? 'This Run has unapplied form edits or an unsaved Working Draft. Leave this page?'
        : 'This Run has unapplied form edits or an unsaved Working Draft. Leave this Run?'
      if (!window.confirm(warning)) {
        event.preventDefault()
        event.stopImmediatePropagation()
        return
      }
      allowConfirmedBranchLink(runId, destination)
      for (const control of controls) baselines.set(control, controlValue(control))
      controls.clear()
      sync()
    }
    function beforeUnload(event: BeforeUnloadEvent): void {
      if (!unsaved()) return
      event.preventDefault()
      event.returnValue = ''
    }
    function afterSaved(event: Event): void {
      const detail = (event as CustomEvent<{runId?: string; branchId?: string}>).detail
      if (detail?.runId !== runId || detail.branchId !== branchId) return
      controls.clear()
      sync()
    }

    sync()
    document.addEventListener('focusin', rememberBaseline, true)
    document.addEventListener('input', recordEdit, true)
    document.addEventListener('change', recordEdit, true)
    document.addEventListener('click', confirmLink, true)
    window.addEventListener('beforeunload', beforeUnload)
    window.addEventListener(RUN_NAVIGATION_SAVED, afterSaved)
    return () => {
      shell?.removeAttribute('data-run-form-edited')
      document.removeEventListener('focusin', rememberBaseline, true)
      document.removeEventListener('input', recordEdit, true)
      document.removeEventListener('change', recordEdit, true)
      document.removeEventListener('click', confirmLink, true)
      window.removeEventListener('beforeunload', beforeUnload)
      window.removeEventListener(RUN_NAVIGATION_SAVED, afterSaved)
    }
  }, [runId, branchId, savedHead])

  // Refresh the shell flag when the backend draft is refetched or saved.
  useEffect(() => {
    const shell = document.querySelector('.app-shell--admin')
    if (serverDirty || localDirtyRef.current) shell?.setAttribute('data-run-form-edited', 'true')
    else shell?.removeAttribute('data-run-form-edited')
  }, [serverDirty])
  return null
}
