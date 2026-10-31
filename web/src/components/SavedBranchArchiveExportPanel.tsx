import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { getBranchWorkingDraft, getRunContainer, listRunBranches } from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  downloadSavedBranchArchive, previewSavedBranchArchive,
  type SavedBranchArchivePreview
} from '../api/runBranchArchiveExport'
import { useLanguage } from '../i18n/LanguageContext'
import { savedBranchArchiveText } from '../i18n/savedBranchArchiveText'
import { formatApiError } from '../utils/apiErrors'

class UnsavedBranchChanges extends Error {}
const REVISION_PAGE_SIZE = 100
const bytes = (value: number): string => new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })
  .format(value / (1024 * 1024)) + ' MiB'

/**
 * Preview is explicitly user-triggered. Run/Branch/HEAD changes invalidate the
 * reviewed bytes. No Save/import/restore is executed in this export-only panel.
 */
export function SavedBranchArchiveExportPanel({
  run, branch
}: { run: RunContainer; branch: RunBranch | null }): JSX.Element {
  const { language } = useLanguage()
  const l = savedBranchArchiveText[language]
  // Consent also depends on live eligibility; a parent refresh that changes
  // editability/status must invalidate and abort the old reviewed download.
  const scope = JSON.stringify([
    run.run_id, run.storage_kind, run.status, run.read_only, run.display_name,
    branch?.run_id ?? null, branch?.branch_id ?? null,
    branch?.display_name ?? null, branch?.saved_head_revision_id ?? null,
    branch?.status ?? null,
    branch?.read_only ?? null
  ])
  const currentScope = useRef(scope)
  currentScope.current = scope
  const generation = useRef(0)
  const inFlight = useRef<AbortController | null>(null)
  const [reviewed, setReviewed] = useState<{scope: string; preview: SavedBranchArchivePreview} | null>(null)
  const [workingStatus, setWorkingStatus] = useState<'clean' | 'dirty' | null>(null)
  const [revisionPage, setRevisionPage] = useState(0)
  const [busy, setBusy] = useState<'preview' | 'download' | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // A changed Run/Branch/HEAD invalidates the old preview AND any in-flight
    // transport. A cancelled request must never apply a late response.
    generation.current += 1
    inFlight.current?.abort()
    inFlight.current = null
    setReviewed(null)
    setWorkingStatus(null)
    setRevisionPage(0)
    setError(null)
    setBusy(null)
    return () => {
      generation.current += 1
      inFlight.current?.abort()
      inFlight.current = null
    }
  }, [scope])

  const selected = branch?.run_id === run.run_id ? branch : null
  const allowed = run.storage_kind === 'custom_local' && !run.read_only &&
    (run.status === 'working' || run.status === 'active') && selected?.status === 'active' && !selected.read_only &&
    Boolean(selected.saved_head_revision_id)
  const active = reviewed?.scope === scope &&
    reviewed.preview.selected_head_revision_id === selected?.saved_head_revision_id
    ? reviewed.preview : null
  // Rendering a collapsed <details> still mounts all its children; keep the
  // long Saved revision inventory bounded without hiding any exported bytes.
  const revisionTotal = active?.history.length ?? 0
  const revisionStart = Math.min(revisionPage * REVISION_PAGE_SIZE,
    Math.max(0, Math.ceil(revisionTotal / REVISION_PAGE_SIZE) - 1) * REVISION_PAGE_SIZE)
  const revisionEnd = Math.min(revisionStart + REVISION_PAGE_SIZE, revisionTotal)

  /** Re-read persisted owners directly, never trust cached React Query data for export consent. */
  async function recheck(head: string, branchId: string, token: number, key: string): Promise<void> {
    const [liveRun, branchList, viewerDraft] = await Promise.all([
      getRunContainer(run.run_id), listRunBranches(run.run_id), getBranchWorkingDraft(run.run_id, branchId)
    ])
    const liveBranch = branchList.run_branches?.find(item => item.branch_id === branchId)
    if (!liveRun || liveRun.run_id !== run.run_id ||
      liveRun.display_name !== run.display_name ||
      liveRun.storage_kind !== 'custom_local' || liveRun.read_only ||
      (liveRun.status !== 'working' && liveRun.status !== 'active') ||
      !liveBranch || liveBranch.run_id !== run.run_id || liveBranch.status !== 'active' ||
      liveBranch.display_name !== selected?.display_name ||
      liveBranch.read_only || liveBranch.saved_head_revision_id !== head) {
      throw new Error(l.invalidSelection)
    }
    if (!viewerDraft || viewerDraft.run_id !== run.run_id ||
      viewerDraft.branch_id !== branchId || viewerDraft.base_saved_revision_id !== head) {
      throw new Error(l.invalidSelection)
    }
    if (viewerDraft.status === 'dirty' || viewerDraft.change_count !== 0) {
      if (generation.current === token && currentScope.current === key) setWorkingStatus('dirty')
      throw new UnsavedBranchChanges(l.manualSave)
    }
    if (viewerDraft.status !== 'clean') throw new Error(l.unknownDraft)
    if (generation.current === token && currentScope.current === key) setWorkingStatus('clean')
  }

  async function preview(): Promise<void> {
    if (!allowed || !selected?.saved_head_revision_id || busy) return
    const token = ++generation.current
    const key = scope
    const requestController = new AbortController()
    inFlight.current = requestController
    setBusy('preview')
    setError(null)
    setReviewed(null)
    setWorkingStatus(null)
    setRevisionPage(0)
    try {
      await recheck(selected.saved_head_revision_id, selected.branch_id, token, key)
      if (generation.current !== token || currentScope.current !== key) return
      const data = await previewSavedBranchArchive(run.run_id, selected.branch_id, requestController.signal)
      if (generation.current !== token || currentScope.current !== key) return
      if (data.selected_head_revision_id !== selected.saved_head_revision_id) {
        throw new Error(l.invalidSelection)
      }
      setReviewed({scope: key, preview: data})
    } catch (cause) {
      if (generation.current === token && currentScope.current === key) {
        setError(formatApiError(cause))
      }
    } finally {
      if (inFlight.current === requestController) inFlight.current = null
      if (generation.current === token && currentScope.current === key) setBusy(null)
    }
  }

  async function download(): Promise<void> {
    if (!allowed || !active || !selected?.saved_head_revision_id || busy) return
    const token = ++generation.current
    const key = scope
    const requestController = new AbortController()
    inFlight.current = requestController
    setBusy('download')
    setError(null)
    try {
      await recheck(active.selected_head_revision_id, selected.branch_id, token, key)
      if (generation.current !== token || currentScope.current !== key) return
      const blob = await downloadSavedBranchArchive(active, requestController.signal)
      if (generation.current !== token || currentScope.current !== key) return
      const url = URL.createObjectURL(blob)
      try {
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = 'saved-branch-v1.sqbranch'
        document.body.appendChild(anchor)
        try { anchor.click() } finally { anchor.remove() }
      } finally {
        // Do not revoke before the browser has consumed the object URL.
        window.setTimeout(() => URL.revokeObjectURL(url), 60000)
      }
    } catch (cause) {
      if (generation.current === token && currentScope.current === key) {
        setError(formatApiError(cause))
        // Even a transport/guard failure requires explicit new review, not implicit retry.
        setReviewed(null)
      }
    } finally {
      if (inFlight.current === requestController) inFlight.current = null
      if (generation.current === token && currentScope.current === key) setBusy(null)
    }
  }

  function cancel(): void {
    generation.current += 1
    inFlight.current?.abort()
    inFlight.current = null
    setReviewed(null)
    setError(null)
    setWorkingStatus(null)
    setBusy(null)
  }

  const base = '/admin/runs/' + encodeURIComponent(run.run_id)
  return <section aria-label={l.title} className="panel">
    <h4>{l.title}</h4>
    <p>{l.description}</p>
    <p className="status">{l.context}: <strong>{selected?.display_name || selected?.branch_id || '—'}</strong>
      {' · '}{l.head}: <code>{selected?.saved_head_revision_id || l.noHead}</code></p>
    <p>{l.warning}</p>
    <p className="status">{l.draft}: {workingStatus === null ? l.unknownDraft :
      workingStatus === 'dirty' ? l.dirty : l.clean}. {l.notAllDrafts}</p>
    {!allowed && <p role="status">{l.readOnly}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {workingStatus === 'dirty' && <p role="status"><Link to={base}>{l.saveLink}</Link>
      {' · '}<Link to={base + '/branches'}>{l.historyLink}</Link></p>}
    <div className="actions">
      <button type="button" onClick={() => void preview()} disabled={!allowed || busy !== null}>
        {busy === 'preview' ? l.loading : active ? l.refresh : error ? l.retry : l.review}
      </button>
      {active && <button type="button" onClick={() => void download()} disabled={!allowed || busy !== null}>
        {busy === 'download' ? l.downloading : l.download}
      </button>}
      {(active || error || busy) && <button type="button" onClick={cancel}>{l.cancel}</button>}
    </div>
    {busy && <p role="status">{busy === 'preview' ? l.loading : l.downloading}</p>}
    {active && <div aria-label={l.title + ' preview'}>
      <p className="status">{l.confirmed}</p>
      <dl>
        <dt>{l.revisionCount}</dt><dd>{active.history.length}</dd>
        <dt>{l.activationRevision}</dt><dd><code style={{overflowWrap: 'anywhere'}}>{active.run_activation_revision_id}</code></dd>
        <dt>{l.branches}</dt><dd>{active.branches.length}</dd>
        <dt>{l.dependencies}</dt><dd>{active.branches.filter(b => b.role === 'dependency').length}</dd>
        <dt>{l.size}</dt><dd>{active.archive_size_bytes.toLocaleString()} B ({bytes(active.archive_size_bytes)})</dd>
        <dt>{l.audit}</dt><dd>{active.audit_event_count}</dd>
        <dt>{l.checkpoints}</dt><dd>{active.checkpoint_count}</dd>
        <dt>{l.hashes}</dt><dd><code style={{overflowWrap: 'anywhere'}}>{active.archive_digest}</code></dd>
      </dl>
      <h5>{l.included}</h5>
      <ul>{active.branches.map(item => <li key={item.branch_id}>
        <strong>{item.display_name}</strong> ({item.role === 'selected' ? l.selected : l.dependency})
        {' · '}<code>{item.branch_id}</code>
        {' · '}{l.parent}: <code>{item.forked_from_branch_id || l.noParent}</code>
      </li>)}</ul>
      <p>{l.omitted}: {active.omitted_branch_ids.length ? active.omitted_branch_ids.join(', ') : l.omittedNone}</p>
      <p>{l.areas}: {active.omitted_areas.length ? active.omitted_areas.join(', ') : l.omittedNone}</p>
      <details><summary>{l.revisionParent} ({active.history.length})</summary>
        <p className="status">{l.revisionRange}: {revisionStart + 1}–{revisionEnd} / {revisionTotal}</p>
        <ol start={revisionStart + 1}>{active.history.slice(revisionStart, revisionEnd).map(item =>
          <li key={item.revision_id}>
            <code>{item.revision_id}</code> ({item.original_owner_branch_id}, #{item.sequence})
            {' → '}<code>{item.parent_revision_id || l.noParent}</code>
          </li>)}</ol>
        {revisionTotal > REVISION_PAGE_SIZE && <div className="actions">
          <button type="button" disabled={revisionStart === 0}
            onClick={() => setRevisionPage(page => Math.max(0, page - 1))}>{l.previousRevisions}</button>
          <button type="button" disabled={revisionEnd >= revisionTotal}
            onClick={() => setRevisionPage(page => page + 1)}>{l.nextRevisions}</button>
        </div>}
      </details>
      <details><summary>{l.components} ({active.included_components.length})</summary>
        <ul>{active.included_components.map(name => <li key={name}><code>{name}</code></li>)}</ul>
      </details>
      <details><summary>{l.headComponents} ({active.selected_head_components.length})</summary>
        <ul>{active.selected_head_components.map(name => <li key={name}><code>{name}</code></li>)}</ul>
      </details>
      <h5>{l.refs} ({active.unresolved_package_references.length})</h5>
      {active.unresolved_package_references.length === 0 ? <p>{l.noRefs}</p> :
        <ul>{active.unresolved_package_references.map((reference, index) =>
          <li key={index}><span>{l.source}: </span><code style={{overflowWrap: 'anywhere'}}>
            {JSON.stringify(reference)}</code></li>)}</ul>}
      <p>{l.explanation}: {active.continuation}</p>
    </div>}
  </section>
}
