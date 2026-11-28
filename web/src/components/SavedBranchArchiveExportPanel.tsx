import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { getBranchWorkingDraft, getRunContainer, listRunBranches } from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  downloadSavedBranchArchive, isCompactSnapshotPreview, MAX_CUSTOM_BRANCHES,
  previewCompactSnapshot, previewSavedBranchArchive,
  type ArchiveExportMode, type ArchiveExportPreview, type CompactSnapshotPreview
} from '../api/runBranchArchiveExport'
import { useLanguage } from '../i18n/LanguageContext'
import { savedBranchArchiveText } from '../i18n/savedBranchArchiveText'
import { formatApiError } from '../utils/apiErrors'

class UnsavedBranchChanges extends Error {}
const REVISION_PAGE_SIZE = 100
// Archive v1 accepts every persisted Run lifecycle status. Completion/archive
// does not make a writable Saved Branch ineligible for this read-only export.
const supportedRunStatus = (status: string): boolean =>
  ['working', 'active', 'completed', 'archived'].includes(status)
function validBranchInventory(branches: RunBranch[] | undefined, runId: string): branches is RunBranch[] {
  return Array.isArray(branches) && branches.every(item => item && item.run_id === runId &&
    typeof item.branch_id === 'string' && item.branch_id.length > 0) &&
    new Set(branches.map(item => item.branch_id)).size === branches.length
}
const fill = (template: string, values: Record<string, unknown>): string =>
  template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? '—'))
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
  const [mode, setMode] = useState<ArchiveExportMode>('branch')
  const selectionOwner = JSON.stringify([run.run_id, branch?.branch_id])
  const [custom, setCustom] = useState<{owner: string; extras: string[]}>({
    owner: selectionOwner, extras: []
  })
  const extras = custom.owner === selectionOwner ? custom.extras : []
  const [inventory, setInventory] = useState<{
    owner: string; branches?: RunBranch[]; failed?: boolean
  } | null>(null)
  useEffect(() => {
    if (mode !== 'custom') return
    let current = true
    setInventory(null)
    listRunBranches(run.run_id).then(result => {
      if (!current) return
      if (validBranchInventory(result?.run_branches, run.run_id)) {
        setInventory({owner: selectionOwner, branches: result.run_branches})
      } else {
        setInventory({owner: selectionOwner, failed: true})
      }
    }).catch(() => {
      if (current) setInventory({owner: selectionOwner, failed: true})
    })
    return () => { current = false }
  }, [mode, run.run_id, selectionOwner])
  const customInventory = inventory?.owner === selectionOwner ? inventory : null
  const choices = customInventory?.branches?.filter(item =>
    item.branch_id !== branch?.branch_id && item.status === 'active' &&
    !item.read_only && Boolean(item.saved_head_revision_id)
  ) ?? []
  const customAllowed = mode !== 'custom' ||
    (extras.length > 0 && extras.every(id => choices.some(item => item.branch_id === id)))

  // Consent also depends on live eligibility; a parent refresh that changes
  // editability/status must invalidate and abort the old reviewed download.
  const scope = JSON.stringify([
    run.run_id, run.storage_kind, run.status, run.read_only, run.display_name,
    branch?.run_id ?? null, branch?.branch_id ?? null,
    branch?.display_name ?? null, branch?.saved_head_revision_id ?? null,
    branch?.status ?? null,
    branch?.read_only ?? null, mode, ...(mode === 'custom' ? extras : [])
  ])
  const currentScope = useRef(scope)
  currentScope.current = scope
  const generation = useRef(0)
  const inFlight = useRef<AbortController | null>(null)
  const [reviewed, setReviewed] = useState<{scope: string; preview: ArchiveExportPreview} | null>(null)
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
    supportedRunStatus(run.status) && selected?.status === 'active' && !selected.read_only &&
    Boolean(selected.saved_head_revision_id) && customAllowed
  const active = reviewed?.scope === scope &&
    reviewed.preview.selected_head_revision_id === selected?.saved_head_revision_id
    ? reviewed.preview : null
  const compact: CompactSnapshotPreview | null = active && isCompactSnapshotPreview(active) ? active : null
  const archive = active && !isCompactSnapshotPreview(active) ? active : null
  // Rendering a collapsed <details> still mounts all its children; keep the
  // long Saved revision inventory bounded without hiding any exported bytes.
  const revisionTotal = archive?.history.length ?? 0
  const revisionStart = Math.min(revisionPage * REVISION_PAGE_SIZE,
    Math.max(0, Math.ceil(revisionTotal / REVISION_PAGE_SIZE) - 1) * REVISION_PAGE_SIZE)
  const revisionEnd = Math.min(revisionStart + REVISION_PAGE_SIZE, revisionTotal)

  /** Re-read persisted owners directly, never trust cached React Query data for export consent. */
  async function recheck(head: string, branchId: string, token: number, key: string): Promise<void> {
    const [liveRun, branchList, viewerDraft] = await Promise.all([
      getRunContainer(run.run_id), listRunBranches(run.run_id), getBranchWorkingDraft(run.run_id, branchId)
    ])
    // Never pick the first matching Branch from an ambiguous or foreign
    // inventory. The caller has only reviewed one exact Run/Branch/HEAD.
    const liveBranches = branchList?.run_branches
    if (!validBranchInventory(liveBranches, run.run_id)) {
      throw new Error(l.invalidSelection)
    }
    if (mode === 'custom' && extras.some(id => !liveBranches.some(item =>
      item.branch_id === id && item.status === 'active' && !item.read_only &&
      Boolean(item.saved_head_revision_id)
    ))) {
      throw new Error(l.invalidSelection)
    }
    const matches = liveBranches.filter(item => item.branch_id === branchId)
    if (matches.length !== 1) throw new Error(l.invalidSelection)
    const liveBranch = matches[0]
    if (!liveRun || liveRun.run_id !== run.run_id ||
      liveRun.display_name !== run.display_name ||
      liveRun.storage_kind !== 'custom_local' || liveRun.read_only ||
      !supportedRunStatus(liveRun.status) || liveRun.status !== run.status ||
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
      const args = [run.run_id, selected.branch_id, requestController.signal] as const
      const data: ArchiveExportPreview = mode === 'compact'
        ? await previewCompactSnapshot(...args)
        : mode === 'custom'
          ? await previewSavedBranchArchive(...args, mode, [selected.branch_id, ...extras].sort())
          : mode === 'full_run' ? await previewSavedBranchArchive(...args, mode)
            : await previewSavedBranchArchive(...args)
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
        anchor.download = mode === 'compact' ? 'compact-snapshot-v1.sqsnap' :
          mode === 'custom' ? 'custom-run-v1.sqbranch' :
          mode === 'full_run' ? 'full-run-v1.sqbranch' : 'saved-branch-v1.sqbranch'
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
    <label>{l.scope}{' '}
      <select value={mode} onChange={event => {
        const value = event.target.value
        setMode(value === 'full_run' || value === 'custom' || value === 'compact' ? value : 'branch')
      }}>
        <option value="branch">{l.branchMode}</option>
        <option value="custom">{l.customMode}</option>
        <option value="full_run">{l.fullRunMode}</option>
        <option value="compact">{l.compactMode}</option>
      </select>
    </label>
    <p>{mode === 'compact' ? l.compactDescription : mode === 'custom' ? l.customDescription :
      mode === 'full_run' ? l.fullRunDescription : l.description}</p>
    {mode === 'custom' && <fieldset disabled={busy !== null}>
      <legend>{l.customBranches}</legend>
      {customInventory?.failed ? <p role="alert">{l.invalidSelection}</p> :
        !customInventory?.branches ? <p role="status">{l.customLoading}</p> :
          choices.length === 0 ? <p>{l.customEmpty}</p> :
            choices.map(item => <label key={item.branch_id} style={{display: 'block'}}>
              <input type="checkbox" checked={extras.includes(item.branch_id)}
                disabled={!extras.includes(item.branch_id) && extras.length >= MAX_CUSTOM_BRANCHES - 1}
                onChange={event => setCustom({owner: selectionOwner, extras: event.target.checked
                  ? [...extras, item.branch_id].sort() : extras.filter(id => id !== item.branch_id)})}
              /> {item.display_name}
            </label>)}
    </fieldset>}
    <p className="status">{l.context}: <strong>{selected?.display_name || selected?.branch_id || '—'}</strong>
      {' · '}{l.head}: <code>{selected?.saved_head_revision_id || l.noHead}</code></p>
    <p>{l.warning}</p>
    <p className="status">{l.draft}: {workingStatus === null ? l.unknownDraft :
      workingStatus === 'dirty' ? l.dirty : l.clean}. {l.notAllDrafts}</p>
    {!allowed && customAllowed && <p role="status">{l.readOnly}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {workingStatus === 'dirty' && <p role="status"><Link to={base}>{l.saveLink}</Link>
      {' · '}<Link to={base + '/branches'}>{l.historyLink}</Link></p>}
    <div className="actions">
      <button type="button" onClick={() => void preview()} disabled={!allowed || busy !== null}>
        {busy === 'preview' ? l.loading : active ? l.refresh : error ? l.retry : l.review}
      </button>
      {active && <button type="button" onClick={() => void download()} disabled={!allowed || busy !== null}>
        {busy === 'download' ? l.downloading : mode === 'compact' ? l.compactDownload : l.download}
      </button>}
      {(active || error || busy) && <button type="button" onClick={cancel}>{l.cancel}</button>}
    </div>
    {busy && <p role="status">{busy === 'preview' ? l.loading : l.downloading}</p>}
    {compact && <CompactPreview preview={compact} l={l} />}
    {archive && <div aria-label={l.title + ' preview'}>
      <p className="status">{l.confirmed}</p>
      <dl>
        <dt>{l.revisionCount}</dt><dd>{archive.history.length}</dd>
        <dt>{l.activationRevision}</dt><dd><code style={{overflowWrap: 'anywhere'}}>{archive.run_activation_revision_id}</code></dd>
        <dt>{l.branches}</dt><dd>{archive.branches.length}</dd>
        {mode !== 'full_run' && <><dt>{l.dependencies}</dt>
          <dd>{archive.branches.filter(b => b.role === 'dependency').length}</dd></>}
        <dt>{l.size}</dt><dd>{archive.archive_size_bytes.toLocaleString()} B ({bytes(archive.archive_size_bytes)})</dd>
        <dt>{l.audit}</dt><dd>{archive.audit_event_count}</dd>
        <dt>{l.checkpoints}</dt><dd>{archive.checkpoint_count}</dd>
        <dt>{l.hashes}</dt><dd><code style={{overflowWrap: 'anywhere'}}>{archive.archive_digest}</code></dd>
      </dl>
      <h5>{l.included}</h5>
      <ul>{archive.branches.map(item => <li key={item.branch_id}>
        <strong>{item.display_name}</strong> ({item.role === 'selected' ? l.selected :
          item.role === 'included' ? l.branchIncluded : l.dependency})
        {' · '}<code>{item.branch_id}</code>
        {' · '}{l.parent}: <code>{item.forked_from_branch_id || l.noParent}</code>
      </li>)}</ul>
      <p>{l.omitted}: {archive.omitted_branch_ids.length ? archive.omitted_branch_ids.join(', ') : l.omittedNone}</p>
      <p>{l.areas}: {archive.omitted_areas.length ? archive.omitted_areas.join(', ') : l.omittedNone}</p>
      <details><summary>{l.revisionParent} ({archive.history.length})</summary>
        <p className="status">{l.revisionRange}: {revisionStart + 1}–{revisionEnd} / {revisionTotal}</p>
        <ol start={revisionStart + 1}>{archive.history.slice(revisionStart, revisionEnd).map(item =>
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
      <details><summary>{l.components} ({archive.included_components.length})</summary>
        <ul>{archive.included_components.map(name => <li key={name}><code>{name}</code></li>)}</ul>
      </details>
      <details><summary>{l.headComponents} ({archive.selected_head_components.length})</summary>
        <ul>{archive.selected_head_components.map(name => <li key={name}><code>{name}</code></li>)}</ul>
      </details>
      <h5>{l.refs} ({archive.unresolved_package_references.length})</h5>
      {archive.unresolved_package_references.length === 0 ? <p>{l.noRefs}</p> :
        <ul>{archive.unresolved_package_references.map((reference, index) =>
          <li key={index}><span>{l.source}: </span><code style={{overflowWrap: 'anywhere'}}>
            {JSON.stringify(reference)}</code></li>)}</ul>}
      <p>{l.explanation}: {archive.continuation}</p>
    </div>}
  </section>
}

type ArchiveText = (typeof savedBranchArchiveText)[keyof typeof savedBranchArchiveText]

/** Exactly what the reviewed Compact snapshot contains, omits and is verified for. */
function CompactPreview({ preview, l }: { preview: CompactSnapshotPreview; l: ArchiveText }): JSX.Element {
  const calendar = preview.run_calendar
  const refs = preview.kept_references
  const packages = preview.package_provenance
  const code = (value: string | null): JSX.Element =>
    <code style={{overflowWrap: 'anywhere'}}>{value || l.noParent}</code>
  return <div aria-label={l.compactMode + ' preview'}>
    <p className="status">{l.compactConfirmed}</p>
    <h5>{l.compactState}</h5>
    <dl>
      <dt>{l.compactRun}</dt><dd>{preview.display_name} · {code(preview.run_id)}</dd>
      <dt>{l.compactBranch}</dt><dd>{preview.selected_branch_display_name} · {code(preview.selected_branch_id)}</dd>
      <dt>{l.head}</dt><dd>{code(preview.selected_head_revision_id)}</dd>
      <dt>{l.compactSequence}</dt><dd>#{preview.selected_head_sequence}</dd>
      <dt>{l.compactKind}</dt><dd><code>{preview.selected_head_kind}</code></dd>
      <dt>{l.compactSavedAt}</dt><dd>{preview.saved_at}</dd>
      <dt>{l.compactContentHash}</dt><dd>{code(preview.content_hash)}</dd>
      <dt>{l.compactFileHash}</dt><dd>{code(preview.archive_digest)}</dd>
      <dt>{l.size}</dt><dd>{preview.archive_size_bytes.toLocaleString()} B ({bytes(preview.archive_size_bytes)})</dd>
      <dt>{l.compactCalendar}</dt><dd>{fill(l.compactCalendarValue, {
        weeks: calendar.weeks_per_year, year: calendar.start_year, seasons: calendar.season_count
      })}</dd>
      <dt>{l.compactPackages}</dt><dd>{fill(l.compactPackageValue, {
        count: packages.run_local_entity_count,
        packages: packages.source_package_ids.length ? packages.source_package_ids.join(', ') : l.omittedNone
      })}</dd>
    </dl>
    <details><summary>{l.compactDependencies} ({preview.included_components.length})</summary>
      <ul>{preview.included_components.map(name => <li key={name}><code>{name}</code></li>)}</ul>
    </details>
    <h5>{l.compactOmitted}</h5>
    <dl>
      <dt>{l.compactOlder}</dt><dd>{preview.omitted_older_revision_count}</dd>
      <dt>{l.compactOtherBranches}</dt><dd>{preview.source_context.omitted_branch_count}</dd>
      <dt>{l.compactViewer}</dt><dd>{preview.source_context.selected_is_viewer_branch
        ? l.compactIsViewer : l.compactNotViewer}</dd>
    </dl>
    <p>{l.areas}: {preview.omitted_areas.join(', ')}</p>
    <h5>{l.compactReferences}</h5>
    <dl>
      <dt>{l.compactParent}</dt><dd>{code(refs.parent_revision_id)}</dd>
      <dt>{l.compactFork}</dt><dd>{code(refs.forked_from_branch_id)} · {code(refs.forked_from_saved_revision_id)}</dd>
      <dt>{l.compactSignedViewer}</dt><dd>{code(refs.viewer_branch_id_signed_at_save)}</dd>
    </dl>
    <h5>{l.refs} ({preview.unresolved_package_references.length})</h5>
    {preview.unresolved_package_references.length === 0 ? <p>{l.noRefs}</p> :
      <ul>{preview.unresolved_package_references.map((reference, index) =>
        <li key={index}><code style={{overflowWrap: 'anywhere'}}>{JSON.stringify(reference)}</code></li>)}</ul>}
    <h5>{l.compactVerifiedUse}</h5>
    <p>{l.compactVerifiedText}</p>
    <p role="note">{l.compactUnsupported}</p>
  </div>
}
