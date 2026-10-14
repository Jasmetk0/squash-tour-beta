import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import {
  compareSavedRevisions,
  createRunBranchFromSavedRevision,
  getSavedRevision,
  getSavedRevisionRecoveryActivity,
  getSavedRevisionRestorePreflight,
  listSavedRevisionHistory,
  restoreSavedRevision
} from '../api/client'
import type {
  RestoreSavedRevisionResponse,
  RunBranch,
  RunContainer,
  SavedRevisionHistoryDetail,
  SavedRevisionHistoryResponse
} from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { EmptyState, JsonPayloadBlock, MetadataList, SectionCard } from './RunScopedUi'
import { SavedBranchMap } from './SavedBranchMap'
import {useLanguage} from '../i18n/LanguageContext'
import {historyText} from '../i18n/historyText'

type ForkReview = {
  runId: string
  sourceBranchId: string
  sourceBranchName: string
  sourceRevisionId: string
  sourceRevisionHash: string
  sourceHeadRevisionId: string
  targetDisplayName: string | null
  viewerBranchId: string | null
}

type RestoreReview = {
  expectedHeadSavedRevisionId: string
  expectedDraftVersion: number
  expectedCurrentViewerBranchId: string
  confirmationPhrase: string
}

type SavedRevisionHistoryPanelProps = {
  runId: string
  run: RunContainer
  branches: RunBranch[]
}

function revisionSummary(detail: SavedRevisionHistoryDetail): string {
  const summary = detail.change_summary.summary
  return typeof summary === 'string' && summary.trim() ? summary : detail.kind
}

export function SavedRevisionHistoryPanel({
  runId,
  run,
  branches
}: SavedRevisionHistoryPanelProps): JSX.Element {
  const {language}=useLanguage()
  const T=(english:string)=>historyText(english,language)
  const queryClient = useQueryClient()
  const [requestedBranchId, setRequestedBranchId] = useState('')
  const [selectedRevisionId, setSelectedRevisionId] = useState('')
  const [comparisonRevisionId, setComparisonRevisionId] = useState('')
  const [newBranchName, setNewBranchName] = useState('')
  const [forkReview, setForkReview] = useState<ForkReview | null>(null)
  const [forkConfirmed, setForkConfirmed] = useState(false)
  const [restoreReview, setRestoreReview] = useState<RestoreReview | null>(null)
  const [typedConfirmation, setTypedConfirmation] = useState('')
  const [restoreConfirmed, setRestoreConfirmed] = useState(false)
  const [restoreNotice, setRestoreNotice] = useState<string | null>(null)

  const branchId = branches.some((branch) => branch.branch_id === requestedBranchId)
    ? requestedBranchId
    : branches[0]?.branch_id ?? ''
  const branch = branches.find((candidate) => candidate.branch_id === branchId)

  const historyQuery = useInfiniteQuery({
    queryKey: ['saved-revision-history', runId, branchId],
    queryFn: ({ pageParam }) =>
      listSavedRevisionHistory(runId, branchId, {
        limit: 50,
        ...(pageParam === undefined ? {} : { beforeSequence: pageParam })
      }),
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.has_more_older ? lastPage.next_before_sequence ?? undefined : undefined,
    enabled: Boolean(runId && branchId)
  })
  const history: SavedRevisionHistoryResponse | undefined = historyQuery.data
    ? {
        run_id: historyQuery.data.pages[0].run_id,
        branch_id: historyQuery.data.pages[0].branch_id,
        saved_head_revision_id: historyQuery.data.pages[0].saved_head_revision_id,
        saved_revisions: [...historyQuery.data.pages]
          .reverse()
          .flatMap((page) => page.saved_revisions)
      }
    : undefined
  const historyIdentityIsValid = Boolean(
    history && history.run_id === runId && history.branch_id === branchId
  )
  const recoveryActivityQuery = useQuery({
    queryKey: ['saved-revision-recovery-activity', runId, branchId],
    queryFn: () => getSavedRevisionRecoveryActivity(runId, branchId),
    enabled: Boolean(runId && branchId)
  })
  const recoveryActivity = recoveryActivityQuery.data
  const reachableRevisionIds = new Set(
    historyIdentityIsValid ? history?.saved_revisions.map((revision) => revision.revision_id) : []
  )
  const recoveryActivityIdentityIsValid = Boolean(
    recoveryActivity &&
      historyIdentityIsValid &&
      recoveryActivity.run_id === runId &&
      recoveryActivity.branch_id === branchId &&
      recoveryActivity.saved_head_revision_id === history?.saved_head_revision_id &&
      recoveryActivity.safety_checkpoints.every(
        (checkpoint) =>
          checkpoint.run_id === runId &&
          checkpoint.branch_id === branchId &&
          reachableRevisionIds.has(checkpoint.saved_revision_id) &&
          reachableRevisionIds.has(checkpoint.target_saved_revision_id) &&
          reachableRevisionIds.has(checkpoint.restore_saved_revision_id)
      ) &&
      recoveryActivity.audit_events.every(
        (auditEvent) =>
          auditEvent.run_id === runId &&
          auditEvent.branch_id === branchId &&
          reachableRevisionIds.has(auditEvent.saved_revision_id)
      )
  )
  const selectedEntry = history?.saved_revisions.find(
    (revision) => revision.revision_id === selectedRevisionId
  )

  const detailQuery = useQuery({
    queryKey: ['saved-revision-detail', runId, branchId, selectedRevisionId],
    queryFn: () => getSavedRevision(runId, branchId, selectedRevisionId),
    enabled: Boolean(historyIdentityIsValid && selectedEntry)
  })
  const detail = detailQuery.data
  const detailIdentityIsValid = Boolean(
    detail &&
      detail.run_id === runId &&
      detail.branch_id === branchId &&
      detail.revision_id === selectedRevisionId
  )

  const comparisonEntry = history?.saved_revisions.find(
    (revision) => revision.revision_id === comparisonRevisionId
  )
  const comparisonQuery = useQuery({
    queryKey: [
      'saved-revision-comparison',
      runId,
      branchId,
      comparisonRevisionId,
      selectedRevisionId
    ],
    queryFn: () =>
      compareSavedRevisions(
        runId,
        branchId,
        comparisonRevisionId,
        selectedRevisionId
      ),
    enabled: Boolean(
      detailIdentityIsValid &&
        comparisonEntry &&
        comparisonRevisionId &&
        comparisonRevisionId !== selectedRevisionId
    )
  })
  const comparison = comparisonQuery.data
  const comparisonIdentityIsValid = Boolean(
    comparison &&
      comparison.run_id === runId &&
      comparison.branch_id === branchId &&
      comparison.from_revision.revision_id === comparisonRevisionId &&
      comparison.to_revision.revision_id === selectedRevisionId
  )

  const restorePreflightQuery = useQuery({
    queryKey: ['saved-revision-restore-preflight', runId, branchId, selectedRevisionId],
    queryFn: () => getSavedRevisionRestorePreflight(runId, branchId, selectedRevisionId),
    enabled: Boolean(detailIdentityIsValid && branch && selectedRevisionId)
  })
  const restorePreflight = restorePreflightQuery.data
  const restorePreflightIdentityIsValid = Boolean(
    restorePreflight &&
      restorePreflight.run_id === runId &&
      restorePreflight.branch_id === branchId &&
      restorePreflight.target_saved_revision_id === selectedRevisionId
  )

  const createBranchMutation = useMutation({
    // Submit the exact frozen source revision and name reviewed by the Admin.
    mutationFn: (review: ForkReview) => createRunBranchFromSavedRevision(review.runId, {
      source_branch_id: review.sourceBranchId,
      source_saved_revision_id: review.sourceRevisionId,
      ...(review.targetDisplayName ? { display_name: review.targetDisplayName } : {})
    }),
    onSuccess: async () => {
      setForkReview(null)
      setForkConfirmed(false)
      setNewBranchName('')
      await queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
    },
    onError: async () => {
      setForkReview(null)
      setForkConfirmed(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId] })
      ])
    }
  })

  const restoreMutation = useMutation({
    mutationFn: (review: RestoreReview) =>
      restoreSavedRevision(runId, branchId, selectedRevisionId, {
        expected_head_saved_revision_id: review.expectedHeadSavedRevisionId,
        expected_draft_version: review.expectedDraftVersion,
        expected_current_viewer_branch_id: review.expectedCurrentViewerBranchId,
        explicit_confirmation: true
      }),
    onSuccess: async () => {
      setRestoreReview(null)
      setTypedConfirmation('')
      setRestoreConfirmed(false)
      setRestoreNotice(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-recovery-activity', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['branch-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-restore-preflight', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-container', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['viewer-official-run-context', runId] })
      ])
    },
    onError: async (error) => {
      setRestoreReview(null)
      setTypedConfirmation('')
      setRestoreConfirmed(false)
      setRestoreNotice(
        `${T('Restore was not retried. The current state must be reviewed again.')} ${formatApiError(error)}`
      )
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-recovery-activity', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['branch-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-container', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
      ])
    }
  })

  const viewerBranchId = run.viewer_branch_id ?? run.official_branch_id
  const forkReady = Boolean(
    detailIdentityIsValid &&
      selectedEntry &&
      selectedEntry.content_hash === detail?.content_hash &&
      historyIdentityIsValid &&
      history &&
      branch &&
      branch.run_id === runId &&
      run.run_id === runId &&
      history.saved_head_revision_id === branch.saved_head_revision_id &&
      !run.read_only
  )
  const forkReviewStillCurrent = Boolean(
    forkReview &&
      forkReady &&
      forkReview.runId === runId &&
      forkReview.sourceBranchId === branchId &&
      forkReview.sourceRevisionId === selectedRevisionId &&
      forkReview.sourceRevisionHash === detail?.content_hash &&
      forkReview.sourceHeadRevisionId === history?.saved_head_revision_id &&
      forkReview.targetDisplayName === (newBranchName.trim() || null) &&
      forkReview.viewerBranchId === viewerBranchId
  )
  const canConfirmFork = forkReviewStillCurrent && forkConfirmed && !createBranchMutation.isPending

  let restoreBlocker: string | null = null
  if (!detailIdentityIsValid) restoreBlocker = T('Open a valid Saved Revision preview first.')
  else if (!historyIdentityIsValid) restoreBlocker = T('Saved Revision history identity is inconsistent.')
  else if (restorePreflightQuery.isLoading) restoreBlocker = T('Checking restore preflight...')
  else if (restorePreflightQuery.error) restoreBlocker = `${T('Restore preflight failed:')} ${formatApiError(restorePreflightQuery.error)}`
  else if (!restorePreflightIdentityIsValid) restoreBlocker = T('Restore preflight identity is inconsistent.')
  else if (restorePreflight && !restorePreflight.can_restore) {
    restoreBlocker = restorePreflight.blockers.map((item) => item.message).join(' ')
  }

  const reviewStillCurrent = Boolean(
    restoreReview &&
      restorePreflightIdentityIsValid &&
      restorePreflight?.can_restore &&
      restorePreflight.saved_head_revision_id === restoreReview.expectedHeadSavedRevisionId &&
      restorePreflight.draft_version === restoreReview.expectedDraftVersion &&
      restorePreflight.current_viewer_branch_id === restoreReview.expectedCurrentViewerBranchId
  )
  const canSubmitRestore = Boolean(
    restoreReview &&
      reviewStillCurrent &&
      restoreConfirmed &&
      typedConfirmation === restoreReview.confirmationPhrase &&
      !restoreMutation.isPending
  )

  function selectBranch(nextBranchId: string): void {
    setRequestedBranchId(nextBranchId)
    setSelectedRevisionId('')
    setComparisonRevisionId('')
    setNewBranchName('')
    setForkReview(null)
    setForkConfirmed(false)
    setRestoreReview(null)
    setRestoreNotice(null)
    createBranchMutation.reset()
    restoreMutation.reset()
  }

  function selectRevision(revisionId: string): void {
    setSelectedRevisionId(revisionId)
    setComparisonRevisionId('')
    setNewBranchName('')
    setForkReview(null)
    setForkConfirmed(false)
    setRestoreReview(null)
    setRestoreNotice(null)
    createBranchMutation.reset()
    restoreMutation.reset()
  }

  function openForkReview(): void {
    if (!forkReady || !branch || !history || !detail) return
    setForkReview({
      runId,
      sourceBranchId: branchId,
      sourceBranchName: branch.display_name,
      sourceRevisionId: selectedRevisionId,
      sourceRevisionHash: detail.content_hash,
      sourceHeadRevisionId: history.saved_head_revision_id,
      targetDisplayName: newBranchName.trim() || null,
      viewerBranchId
    })
    setForkConfirmed(false)
    createBranchMutation.reset()
  }

  function closeForkReview(): void {
    if (createBranchMutation.isPending) return
    setForkReview(null)
    setForkConfirmed(false)
  }

  function openRestoreReview(): void {
    if (restoreBlocker || !restorePreflight || !branch) return
    setRestoreReview({
      expectedHeadSavedRevisionId: restorePreflight.saved_head_revision_id,
      expectedDraftVersion: restorePreflight.draft_version,
      expectedCurrentViewerBranchId: restorePreflight.current_viewer_branch_id,
      confirmationPhrase: `RESTORE ${branch.display_name}`
    })
    setTypedConfirmation('')
    setRestoreConfirmed(false)
    setRestoreNotice(null)
    restoreMutation.reset()
  }

  function closeRestoreReview(): void {
    if (restoreMutation.isPending) return
    setRestoreReview(null)
    setTypedConfirmation('')
    setRestoreConfirmed(false)
  }

  return (
    <SectionCard title={T("Saved Revision history")}>
      <p>
        {T("Opening a Saved Revision is always read-only. No Branch, Working Draft, or Viewer state changes until a separate action is explicitly submitted.")}
      </p>
      <p><Link to={'/admin/runs/'+encodeURIComponent(runId)+'/branches/compare?'+
        new URLSearchParams({branch:branchId,...(selectedRevisionId?{b:selectedRevisionId}:{})}).toString()}>
        {T("Open Compare States A/B · Samostatné porovnání uložených stavů")}
      </Link></p>
      <SavedBranchMap
        runId={runId} branches={branches} selectedBranchId={branchId}
        viewerBranchId={run.viewer_branch_id??null}
        officialBranchId={run.official_branch_id??null}
        onSelect={selectBranch}
      />
      {branches.length === 0 ? (
        <EmptyState message={T("No Branch is available for Saved Revision history.")} />
      ) : (
        <label>
          {T("History Branch")}
          <select
            aria-label={T("Saved Revision history Branch")}
            value={branchId}
            onChange={(event) => selectBranch(event.target.value)}
          >
            {branches.map((candidate) => (
              <option key={candidate.branch_id} value={candidate.branch_id}>
                {candidate.display_name} ({candidate.branch_id})
              </option>
            ))}
          </select>
        </label>
      )}

      {historyQuery.isLoading && <p className="status">{T("Loading Saved Revision history...")}</p>}
      {historyQuery.error && (
        <p className="error">{T("Failed to load Saved Revision history:")} {formatApiError(historyQuery.error)}</p>
      )}
      {history && !historyIdentityIsValid && (
        <p className="error">{T("Saved Revision history returned a mismatched Run or Branch identity.")}</p>
      )}
      {historyIdentityIsValid && history?.saved_revisions.length === 0 && (
        <EmptyState message={T("This Branch has no reachable Saved Revisions.")} />
      )}
      {historyIdentityIsValid && history && history.saved_revisions.length > 0 && (
        <div className="saved-revision-layout">
          <div className="table-responsive" aria-label={T("Reachable Saved Revisions table")}>
            <p className="status">{T("Reachable Saved Revision history, including shared ancestors. Only loaded pages are shown; older entries can be loaded explicitly. Saved at is wall-clock time, not sporting simulation time.")}</p>
            <table aria-label={T("Saved Revision history table")} className="saved-revision-table">
              <thead><tr><th>{T("# / Revision")}</th><th>{T("Saved at")}</th>
                <th>{T("Actual change summary")}</th><th>{T("Source Branch")}</th>
                <th>{T("Parent")}</th><th>{T("Reachability")}</th></tr></thead>
              <tbody>{history.saved_revisions.map((revision) => (
                <tr key={revision.revision_id}
                  className={selectedRevisionId === revision.revision_id ? 'is-selected' : ''}>
                  <td><button type="button"
                    className="history-list-item"
                    aria-pressed={selectedRevisionId === revision.revision_id}
                    onClick={() => selectRevision(revision.revision_id)}>
                    <span className="history-list-item__title">
                      {T("Revision")} {revision.sequence}: {revision.kind}
                    </span>
                    <span className="history-list-item__meta"><code>{revision.revision_id}</code></span>
                  </button></td>
                  <td>{revision.created_at??T("Unavailable")}</td>
                  <td>{typeof revision.change_summary.summary === 'string' &&
                    revision.change_summary.summary.trim() ?
                    revision.change_summary.summary : revision.kind}</td>
                  <td><code>{revision.revision_branch_id}</code></td>
                  <td><code>{revision.parent_revision_id??T("Root")}</code></td>
                  <td>{revision.is_branch_head?'HEAD · ':''}
                    {revision.is_shared_revision?T("Shared ancestor"):T("Own branch")}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          {historyQuery.hasNextPage && (
            <button
              type="button"
              disabled={historyQuery.isFetchingNextPage}
              onClick={() => historyQuery.fetchNextPage()}
            >
              {historyQuery.isFetchingNextPage ? T("Loading older revisions...") : T("Load older revisions")}
            </button>
          )}

          <div>
            {!selectedRevisionId && (
              <EmptyState message={T("Select a Saved Revision to open its read-only preview.")} />
            )}
            {detailQuery.isLoading && <p className="status">{T("Loading read-only preview...")}</p>}
            {detailQuery.error && (
              <p className="error">{T("Failed to load Saved Revision preview:")} {formatApiError(detailQuery.error)}</p>
            )}
            {detail && !detailIdentityIsValid && (
              <p className="error">{T("The preview returned a mismatched Saved Revision identity.")}</p>
            )}
            {detailIdentityIsValid && detail && (
              <article className="saved-revision-preview saved-revision-detail-drawer" aria-label={T("Saved Revision read-only preview")}>
                <div className="saved-revision-detail-drawer__heading">
                  <strong>{T("Saved Revision · read-only detail")}</strong>
                  <button type="button" onClick={() => selectRevision('')}>{T("Close detail")}</button>
                </div>
                <p className="status"><strong>{T("Read-only preview")}</strong> · {T('nothing has been changed.')}</p>
                <MetadataList
                  items={[
                    { label: T("Revision"), value: `${detail.sequence} · ${detail.revision_id}` },
                    { label: T("Revision kind"), value: detail.kind },
                    { label: T("Parent revision"), value: detail.parent_revision_id ?? T("None") },
                    { label: T("Created"), value: detail.created_at ?? '—' },
                    { label: T("Current Branch head"), value: history.saved_head_revision_id },
                    { label: T("Shared history"), value: detail.is_shared_revision ? T("Yes") : T("No") },
                    { label: T("Content hash"), value: `${detail.content_hash_algorithm}:${detail.content_hash}` },
                    { label: T("Summary"), value: revisionSummary(detail) }
                  ]}
                />
                <JsonPayloadBlock
                  title={T("Saved change summary")}
                  emptyText={T("No change summary is available.")}
                  payload={detail.change_summary}
                />
                <JsonPayloadBlock
                  title={T("Saved Revision payload")}
                  emptyText={T("No Saved Revision payload is available.")}
                  payload={detail.payload}
                />

                <section aria-label={T("Saved Revision comparison")}>
                  <h4>{T("Compare revisions")}</h4>
                  <p><Link to={'/admin/runs/'+encodeURIComponent(runId)+'/branches/compare?'+
                    new URLSearchParams({branch:branchId,
                      b:selectedRevisionId,...(comparisonRevisionId?{a:comparisonRevisionId}:{})}).toString()}>
                    {T("Open these states on the dedicated Compare A/B page")}
                  </Link></p>
                  <label>
                    {T("Compare from")}
                    <select
                      aria-label={T("Compare selected revision with")}
                      value={comparisonRevisionId}
                      onChange={(event) => setComparisonRevisionId(event.target.value)}
                    >
                      <option value="">{T("Choose another loaded revision")}</option>
                      {history.saved_revisions
                        .filter((revision) => revision.revision_id !== selectedRevisionId)
                        .map((revision) => (
                          <option key={revision.revision_id} value={revision.revision_id}>
                            {T("Revision")} {revision.sequence}: {revision.kind}
                          </option>
                        ))}
                    </select>
                  </label>
                  {comparisonQuery.isLoading && (
                    <p className="status">{T("Comparing Saved Revisions...")}</p>
                  )}
                  {comparisonQuery.error && (
                    <p className="error">
                      {T("Failed to compare Saved Revisions:")} {formatApiError(comparisonQuery.error)}
                    </p>
                  )}
                  {comparison && !comparisonIdentityIsValid && (
                    <p className="error">{T("Saved Revision comparison identity is inconsistent.")}</p>
                  )}
                  {comparisonIdentityIsValid && comparison && (
                    <div>
                      <MetadataList
                        items={[
                          {
                            label: T("From"),
                            value: `Revision ${comparison.from_revision.sequence} · ${comparison.from_revision.revision_id}`
                          },
                          {
                            label: T("To"),
                            value: `Revision ${comparison.to_revision.sequence} · ${comparison.to_revision.revision_id}`
                          },
                          {
                            label: T("Changed components"),
                            value: String(
                              comparison.components.filter((item) => item.status !== 'unchanged').length
                            )
                          }
                        ]}
                      />
                      <JsonPayloadBlock
                        title={T("Run metadata changes")}
                        emptyText={T("No Run metadata changed.")}
                        payload={comparison.run_changes}
                      />
                      <JsonPayloadBlock
                        title={T("Branch metadata changes")}
                        emptyText={T("No Branch metadata changed.")}
                        payload={comparison.branch_changes}
                      />
                      {comparison.components.length === 0 ? (
                        <EmptyState message={T("Neither revision contains Saved Revision components.")} />
                      ) : (
                        <ul aria-label={T("Saved Revision component comparison")}>
                          {comparison.components.map((item) => (
                            <li key={item.component_key}>
                              <strong>{item.component_key}</strong>: {T(item.status)}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </section>

                <div className="saved-revision-actions">
                  <form
                    onSubmit={(event) => {
                      event.preventDefault()
                      openForkReview()
                    }}
                  >
                    <label>
                      {T("New Branch name (optional)")}
                      <input
                        aria-label={T("New Branch name from Saved Revision")}
                        value={newBranchName}
                        maxLength={256}
                        onChange={(event) => setNewBranchName(event.target.value)}
                      />
                    </label>
                    <p className="status">{T("A new Branch starts from this immutable revision. The original Branch and Viewer Branch remain unchanged.")}</p>
                    {!forkReady && <p className="error">{T("Branch creation requires a consistent Run, source Branch head, and Saved Revision preview. Refresh the history before creating.")}</p>}
                    <button type="submit" disabled={!forkReady || createBranchMutation.isPending}>
                      {T("Review new Branch creation")}
                    </button>
                  </form>
                  <div>
                    <button
                      type="button"
                      className="button-danger"
                      disabled={Boolean(restoreBlocker) || restoreMutation.isPending}
                      onClick={openRestoreReview}
                    >
                      {T("Restore current Branch from this revision")}
                    </button>
                    {restoreBlocker && <p className="status">{T("Restore unavailable:")} {restoreBlocker}</p>}
                    {!restoreBlocker && (
                      <p className="status">
                        {T("The engine will create a separate recoverable checkpoint before restoring.")}
                      </p>
                    )}
                  </div>
                </div>
              </article>
            )}
          </div>
        </div>
      )}

      <section aria-label={T("Saved Revision recovery activity")}>
        <h4>{T("Recovery activity")}</h4>
        <p>
          {T("Safety checkpoints and revision events are read-only. Opening a checkpoint only opens its pre-restore Saved Revision; returning to it still requires the guarded restore review.")}
        </p>
        {recoveryActivityQuery.isLoading && (
          <p className="status">{T("Loading recovery activity...")}</p>
        )}
        {recoveryActivityQuery.error && (
          <p className="error">
            {T("Failed to load recovery activity:")} {formatApiError(recoveryActivityQuery.error)}
          </p>
        )}
        {recoveryActivity && !recoveryActivityIdentityIsValid && (
          <p className="error">
            {T("Recovery activity returned mismatched or unreachable Run, Branch, or revision data.")}
          </p>
        )}
        {recoveryActivityIdentityIsValid && recoveryActivity && (
          <>
            <h5>{T("Pre-restore safety checkpoints")}</h5>
            {recoveryActivity.safety_checkpoints.length === 0 ? (
              <EmptyState message={T("No pre-restore safety checkpoint has been created for this Branch.")} />
            ) : (
              <ol className="history-list" aria-label={T("Pre-restore safety checkpoints")}>
                {[...recoveryActivity.safety_checkpoints].reverse().map((checkpoint) => (
                  <li key={checkpoint.checkpoint_id}>
                    <article>
                      <MetadataList
                        items={[
                          { label: T("Checkpoint"), value: checkpoint.checkpoint_id },
                          { label: T("Created"), value: checkpoint.created_at ?? '—' },
                          { label: T("Pre-restore head"), value: checkpoint.saved_revision_id },
                          { label: T("Restore target"), value: checkpoint.target_saved_revision_id },
                          { label: T("Restore result"), value: checkpoint.restore_saved_revision_id },
                          { label: T("Reviewed Viewer Branch"), value: checkpoint.viewer_branch_id },
                          { label: T("Reviewed Draft"), value: `${checkpoint.draft_id} · version ${checkpoint.draft_version}` },
                          { label: T("Content hash"), value: `${checkpoint.content_hash_algorithm}:${checkpoint.content_hash}` }
                        ]}
                      />
                      <button
                        type="button"
                        onClick={() => selectRevision(checkpoint.saved_revision_id)}
                      >
                        {T("Open checkpoint recovery source")}
                      </button>
                    </article>
                  </li>
                ))}
              </ol>
            )}

            <h5>{T("Branch revision events")}</h5>
            {recoveryActivity.audit_events.length === 0 ? (
              <EmptyState message={T("No revision Audit Event has been recorded for this Branch.")} />
            ) : (
              <ol className="history-list" aria-label={T("Branch revision Audit Events")}>
                {[...recoveryActivity.audit_events].reverse().map((auditEvent) => (
                  <li key={auditEvent.audit_event_id}>
                    <article>
                      <MetadataList
                        items={[
                          { label: T("Audit Event"), value: auditEvent.audit_event_id },
                          { label: T("Kind"), value: auditEvent.event_kind },
                          { label: T("Saved Revision"), value: auditEvent.saved_revision_id },
                          { label: T("Created"), value: auditEvent.created_at ?? '—' }
                        ]}
                      />
                      <JsonPayloadBlock
                        title={T("Audit Event payload")}
                        emptyText={T("No Audit Event payload is available.")}
                        payload={auditEvent.payload}
                      />
                    </article>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </section>

      {forkReview && (
        <div className="restore-dialog-backdrop">
          <section role="alertdialog" aria-modal="true" className="restore-dialog" aria-label={T("Review new Branch creation")}>
            <h4>{T("Review new Branch creation")}</h4>
            <p>{T("This creates a separate Branch from the saved history below. It does not rewind or modify the source Branch or switch the Viewer Branch.")}</p>
            <MetadataList items={[
              { label: T("Run"), value: forkReview.runId },
              { label: T("Source Branch"), value: `${forkReview.sourceBranchName} (${forkReview.sourceBranchId})` },
              { label: T("Saved Revision"), value: forkReview.sourceRevisionId },
              { label: T("Revision content hash"), value: forkReview.sourceRevisionHash },
              { label: T("Reviewed source head"), value: forkReview.sourceHeadRevisionId },
              { label: T("New Branch name"), value: forkReview.targetDisplayName ?? T("First unused Timeline N") },
              { label: T("Viewer Branch stays"), value: forkReview.viewerBranchId ?? T("None") }
            ]} />
            {!forkReviewStillCurrent && (
              <p className="error">{T("The Branch, revision, Viewer Branch or proposed name changed. Close this review and inspect the latest history.")}</p>
            )}
            <label>
              <input
                type="checkbox"
                aria-label={T("Confirm new Branch creation")}
                checked={forkConfirmed}
                onChange={(event) => setForkConfirmed(event.target.checked)}
                disabled={!forkReviewStillCurrent || createBranchMutation.isPending}
              />
              {T('I reviewed the exact source revision and understand this creates an independent Branch without changing the Viewer Branch.')}
            </label>
            <div className="saved-revision-actions">
              <button type="button" disabled={createBranchMutation.isPending} onClick={closeForkReview}>{T("Cancel Branch creation")}</button>
              <button type="button" disabled={!canConfirmFork} onClick={() => {
                if (forkReview && canConfirmFork) createBranchMutation.mutate(forkReview)
              }}>
                {createBranchMutation.isPending ? T("Creating Branch...") : T("Confirm new Branch creation")}
              </button>
            </div>
          </section>
        </div>
      )}

      {createBranchMutation.error && (
        <p className="error">{T("Branch creation result is uncertain; review the refreshed Branch list before retrying.")} {formatApiError(createBranchMutation.error)}</p>
      )}
      {createBranchMutation.data && (
        <p className="status" aria-label={T("Saved Revision Branch result")}>
          {T("Created Branch")} {createBranchMutation.data.display_name} ({createBranchMutation.data.branch_id})
          {T('from Saved Revision')} {createBranchMutation.variables?.sourceRevisionId ?? T('the reviewed revision')}. {T('The Viewer Branch was not changed.')}
        </p>
      )}
      {restoreNotice && <p className="error">{restoreNotice}</p>}
      {restoreMutation.data && <RestoreResult result={restoreMutation.data} />}

      {restoreReview && branch && detail && (
        <div className="restore-dialog-backdrop">
          <section
            role="alertdialog"
            aria-modal="true"
            className="restore-dialog"
            aria-labelledby="restore-dialog-title"
          >
            <h4 id="restore-dialog-title">{T("Confirm Saved Revision restore")}</h4>
            <p>
              {T('This will restore')} <strong>{branch.display_name}</strong> {T('from Saved Revision')}{' '}
              <strong>{detail.revision_id}</strong>. {T('It will not delete later history. A separate pre-restore checkpoint of head')}{' '}
              <strong>{restoreReview.expectedHeadSavedRevisionId}</strong> {T('will be created first.')}
            </p>
            <MetadataList
              items={[
                { label: T("Reviewed head"), value: restoreReview.expectedHeadSavedRevisionId },
                { label: T("Reviewed Draft version"), value: restoreReview.expectedDraftVersion },
                { label: T("Reviewed Viewer Branch"), value: restoreReview.expectedCurrentViewerBranchId },
                { label: T("Restore target"), value: detail.revision_id }
              ]}
            />
            {!reviewStillCurrent && (
              <p className="error">
                {T("The reviewed state changed. Close this dialog and review the refreshed state.")}
              </p>
            )}
            <label>
              {T("Type")} <code>{restoreReview.confirmationPhrase}</code>
              <input
                aria-label={T("Restore confirmation phrase")}
                autoComplete="off"
                autoFocus
                value={typedConfirmation}
                onChange={(event) => setTypedConfirmation(event.target.value)}
              />
            </label>
            <label className="checkbox-label">
              <input
                aria-label={T("Confirm Saved Revision restore")}
                type="checkbox"
                checked={restoreConfirmed}
                onChange={(event) => setRestoreConfirmed(event.target.checked)}
              />
              {T("I understand that the current Branch state will be replaced by a new restore revision, while the pre-restore state remains recoverable.")}
            </label>
            <div className="actions">
              <button type="button" className="button-ghost" onClick={closeRestoreReview}>
                {T("Cancel")}
              </button>
              <button
                type="button"
                className="button-danger"
                disabled={!canSubmitRestore}
                onClick={() => restoreReview && restoreMutation.mutate(restoreReview)}
              >
                {restoreMutation.isPending ? T("Restoring...") : T("Confirm restore")}
              </button>
            </div>
          </section>
        </div>
      )}
    </SectionCard>
  )
}

function RestoreResult({ result }: { result: RestoreSavedRevisionResponse }): JSX.Element {
  const {language}=useLanguage()
  const T=(english:string)=>historyText(english,language)
  return (
    <div className="status" aria-label={T("Saved Revision restore result")}>
      {T("Restore completed. New Saved Revision:")} {result.saved_revision.revision_id}; {T('safety checkpoint:')}{' '}
      {result.safety_checkpoint.checkpoint_id}; {T('restored target:')} {result.target_saved_revision_id}; {T('Viewer Branch:')} {result.viewer_branch_id}. {T('Later history remains preserved.')}
    </div>
  )
}
