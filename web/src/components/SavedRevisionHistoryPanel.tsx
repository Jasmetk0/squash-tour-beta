import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

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
  branches
}: SavedRevisionHistoryPanelProps): JSX.Element {
  const queryClient = useQueryClient()
  const [requestedBranchId, setRequestedBranchId] = useState('')
  const [selectedRevisionId, setSelectedRevisionId] = useState('')
  const [comparisonRevisionId, setComparisonRevisionId] = useState('')
  const [newBranchName, setNewBranchName] = useState('')
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
    mutationFn: () => {
      const displayName = newBranchName.trim()
      return createRunBranchFromSavedRevision(runId, {
        source_branch_id: branchId,
        source_saved_revision_id: selectedRevisionId,
        ...(displayName ? { display_name: displayName } : {})
      })
    },
    onSuccess: async () => {
      setNewBranchName('')
      await queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
    },
    onError: async () => {
      await queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
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
        `Restore was not retried. The current state must be reviewed again. ${formatApiError(error)}`
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

  let restoreBlocker: string | null = null
  if (!detailIdentityIsValid) restoreBlocker = 'Open a valid Saved Revision preview first.'
  else if (!historyIdentityIsValid) restoreBlocker = 'Saved Revision history identity is inconsistent.'
  else if (restorePreflightQuery.isLoading) restoreBlocker = 'Checking restore preflight...'
  else if (restorePreflightQuery.error) restoreBlocker = `Restore preflight failed: ${formatApiError(restorePreflightQuery.error)}`
  else if (!restorePreflightIdentityIsValid) restoreBlocker = 'Restore preflight identity is inconsistent.'
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
    setRestoreReview(null)
    setRestoreNotice(null)
    createBranchMutation.reset()
    restoreMutation.reset()
  }

  function selectRevision(revisionId: string): void {
    setSelectedRevisionId(revisionId)
    setComparisonRevisionId('')
    setNewBranchName('')
    setRestoreReview(null)
    setRestoreNotice(null)
    createBranchMutation.reset()
    restoreMutation.reset()
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
    <SectionCard title="Saved Revision history">
      <p>
        Opening a Saved Revision is always read-only. No Branch, Working Draft, or Viewer state
        changes until a separate action is explicitly submitted.
      </p>
      {branches.length === 0 ? (
        <EmptyState message="No Branch is available for Saved Revision history." />
      ) : (
        <label>
          History Branch
          <select
            aria-label="Saved Revision history Branch"
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

      {historyQuery.isLoading && <p className="status">Loading Saved Revision history...</p>}
      {historyQuery.error && (
        <p className="error">Failed to load Saved Revision history: {formatApiError(historyQuery.error)}</p>
      )}
      {history && !historyIdentityIsValid && (
        <p className="error">Saved Revision history returned a mismatched Run or Branch identity.</p>
      )}
      {historyIdentityIsValid && history?.saved_revisions.length === 0 && (
        <EmptyState message="This Branch has no reachable Saved Revisions." />
      )}
      {historyIdentityIsValid && history && history.saved_revisions.length > 0 && (
        <div className="saved-revision-layout">
          <ol className="history-list" aria-label="Saved Revision history">
            {history.saved_revisions.map((revision) => (
              <li key={revision.revision_id}>
                <button
                  type="button"
                  className={`history-list-item${selectedRevisionId === revision.revision_id ? ' is-selected' : ''}`}
                  aria-pressed={selectedRevisionId === revision.revision_id}
                  onClick={() => selectRevision(revision.revision_id)}
                >
                  <span className="history-list-item__title">
                    Revision {revision.sequence}: {revision.kind}
                  </span>
                  <span className="history-list-item__meta">
                    {revision.revision_id}
                    {revision.is_branch_head ? ' · current head' : ''}
                    {revision.is_shared_revision ? ' · shared history' : ''}
                  </span>
                </button>
              </li>
            ))}
          </ol>
          {historyQuery.hasNextPage && (
            <button
              type="button"
              disabled={historyQuery.isFetchingNextPage}
              onClick={() => historyQuery.fetchNextPage()}
            >
              {historyQuery.isFetchingNextPage ? 'Loading older revisions...' : 'Load older revisions'}
            </button>
          )}

          <div>
            {!selectedRevisionId && (
              <EmptyState message="Select a Saved Revision to open its read-only preview." />
            )}
            {detailQuery.isLoading && <p className="status">Loading read-only preview...</p>}
            {detailQuery.error && (
              <p className="error">Failed to load Saved Revision preview: {formatApiError(detailQuery.error)}</p>
            )}
            {detail && !detailIdentityIsValid && (
              <p className="error">The preview returned a mismatched Saved Revision identity.</p>
            )}
            {detailIdentityIsValid && detail && (
              <article className="saved-revision-preview" aria-label="Saved Revision read-only preview">
                <p className="status"><strong>Read-only preview</strong> · nothing has been changed.</p>
                <MetadataList
                  items={[
                    { label: 'Revision', value: `${detail.sequence} · ${detail.revision_id}` },
                    { label: 'Revision kind', value: detail.kind },
                    { label: 'Parent revision', value: detail.parent_revision_id ?? 'None' },
                    { label: 'Created', value: detail.created_at ?? '—' },
                    { label: 'Current Branch head', value: history.saved_head_revision_id },
                    { label: 'Shared history', value: detail.is_shared_revision ? 'Yes' : 'No' },
                    { label: 'Content hash', value: `${detail.content_hash_algorithm}:${detail.content_hash}` },
                    { label: 'Summary', value: revisionSummary(detail) }
                  ]}
                />
                <JsonPayloadBlock
                  title="Saved change summary"
                  emptyText="No change summary is available."
                  payload={detail.change_summary}
                />
                <JsonPayloadBlock
                  title="Saved Revision payload"
                  emptyText="No Saved Revision payload is available."
                  payload={detail.payload}
                />

                <section aria-label="Saved Revision comparison">
                  <h4>Compare revisions</h4>
                  <label>
                    Compare from
                    <select
                      aria-label="Compare selected revision with"
                      value={comparisonRevisionId}
                      onChange={(event) => setComparisonRevisionId(event.target.value)}
                    >
                      <option value="">Choose another loaded revision</option>
                      {history.saved_revisions
                        .filter((revision) => revision.revision_id !== selectedRevisionId)
                        .map((revision) => (
                          <option key={revision.revision_id} value={revision.revision_id}>
                            Revision {revision.sequence}: {revision.kind}
                          </option>
                        ))}
                    </select>
                  </label>
                  {comparisonQuery.isLoading && (
                    <p className="status">Comparing Saved Revisions...</p>
                  )}
                  {comparisonQuery.error && (
                    <p className="error">
                      Failed to compare Saved Revisions: {formatApiError(comparisonQuery.error)}
                    </p>
                  )}
                  {comparison && !comparisonIdentityIsValid && (
                    <p className="error">Saved Revision comparison identity is inconsistent.</p>
                  )}
                  {comparisonIdentityIsValid && comparison && (
                    <div>
                      <MetadataList
                        items={[
                          {
                            label: 'From',
                            value: `Revision ${comparison.from_revision.sequence} · ${comparison.from_revision.revision_id}`
                          },
                          {
                            label: 'To',
                            value: `Revision ${comparison.to_revision.sequence} · ${comparison.to_revision.revision_id}`
                          },
                          {
                            label: 'Changed components',
                            value: String(
                              comparison.components.filter((item) => item.status !== 'unchanged').length
                            )
                          }
                        ]}
                      />
                      <JsonPayloadBlock
                        title="Run metadata changes"
                        emptyText="No Run metadata changed."
                        payload={comparison.run_changes}
                      />
                      <JsonPayloadBlock
                        title="Branch metadata changes"
                        emptyText="No Branch metadata changed."
                        payload={comparison.branch_changes}
                      />
                      {comparison.components.length === 0 ? (
                        <EmptyState message="Neither revision contains Saved Revision components." />
                      ) : (
                        <ul aria-label="Saved Revision component comparison">
                          {comparison.components.map((item) => (
                            <li key={item.component_key}>
                              <strong>{item.component_key}</strong>: {item.status}
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
                      if (!createBranchMutation.isPending) createBranchMutation.mutate()
                    }}
                  >
                    <label>
                      New Branch name (optional)
                      <input
                        aria-label="New Branch name from Saved Revision"
                        value={newBranchName}
                        maxLength={256}
                        onChange={(event) => setNewBranchName(event.target.value)}
                      />
                    </label>
                    <button type="submit" disabled={createBranchMutation.isPending}>
                      {createBranchMutation.isPending ? 'Creating Branch...' : 'Create new Branch from this revision'}
                    </button>
                  </form>
                  <div>
                    <button
                      type="button"
                      className="button-danger"
                      disabled={Boolean(restoreBlocker) || restoreMutation.isPending}
                      onClick={openRestoreReview}
                    >
                      Restore current Branch from this revision
                    </button>
                    {restoreBlocker && <p className="status">Restore unavailable: {restoreBlocker}</p>}
                    {!restoreBlocker && (
                      <p className="status">
                        The engine will create a separate recoverable checkpoint before restoring.
                      </p>
                    )}
                  </div>
                </div>
              </article>
            )}
          </div>
        </div>
      )}

      <section aria-label="Saved Revision recovery activity">
        <h4>Recovery activity</h4>
        <p>
          Safety checkpoints and revision events are read-only. Opening a checkpoint only opens
          its pre-restore Saved Revision; returning to it still requires the guarded restore review.
        </p>
        {recoveryActivityQuery.isLoading && (
          <p className="status">Loading recovery activity...</p>
        )}
        {recoveryActivityQuery.error && (
          <p className="error">
            Failed to load recovery activity: {formatApiError(recoveryActivityQuery.error)}
          </p>
        )}
        {recoveryActivity && !recoveryActivityIdentityIsValid && (
          <p className="error">
            Recovery activity returned mismatched or unreachable Run, Branch, or revision data.
          </p>
        )}
        {recoveryActivityIdentityIsValid && recoveryActivity && (
          <>
            <h5>Pre-restore safety checkpoints</h5>
            {recoveryActivity.safety_checkpoints.length === 0 ? (
              <EmptyState message="No pre-restore safety checkpoint has been created for this Branch." />
            ) : (
              <ol className="history-list" aria-label="Pre-restore safety checkpoints">
                {[...recoveryActivity.safety_checkpoints].reverse().map((checkpoint) => (
                  <li key={checkpoint.checkpoint_id}>
                    <article>
                      <MetadataList
                        items={[
                          { label: 'Checkpoint', value: checkpoint.checkpoint_id },
                          { label: 'Created', value: checkpoint.created_at ?? '—' },
                          { label: 'Pre-restore head', value: checkpoint.saved_revision_id },
                          { label: 'Restore target', value: checkpoint.target_saved_revision_id },
                          { label: 'Restore result', value: checkpoint.restore_saved_revision_id },
                          { label: 'Reviewed Viewer Branch', value: checkpoint.viewer_branch_id },
                          { label: 'Reviewed Draft', value: `${checkpoint.draft_id} · version ${checkpoint.draft_version}` },
                          { label: 'Content hash', value: `${checkpoint.content_hash_algorithm}:${checkpoint.content_hash}` }
                        ]}
                      />
                      <button
                        type="button"
                        onClick={() => selectRevision(checkpoint.saved_revision_id)}
                      >
                        Open checkpoint recovery source
                      </button>
                    </article>
                  </li>
                ))}
              </ol>
            )}

            <h5>Branch revision events</h5>
            {recoveryActivity.audit_events.length === 0 ? (
              <EmptyState message="No revision Audit Event has been recorded for this Branch." />
            ) : (
              <ol className="history-list" aria-label="Branch revision Audit Events">
                {[...recoveryActivity.audit_events].reverse().map((auditEvent) => (
                  <li key={auditEvent.audit_event_id}>
                    <article>
                      <MetadataList
                        items={[
                          { label: 'Audit Event', value: auditEvent.audit_event_id },
                          { label: 'Kind', value: auditEvent.event_kind },
                          { label: 'Saved Revision', value: auditEvent.saved_revision_id },
                          { label: 'Created', value: auditEvent.created_at ?? '—' }
                        ]}
                      />
                      <JsonPayloadBlock
                        title="Audit Event payload"
                        emptyText="No Audit Event payload is available."
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

      {createBranchMutation.error && (
        <p className="error">Branch creation result is uncertain; review the refreshed Branch list before retrying. {formatApiError(createBranchMutation.error)}</p>
      )}
      {createBranchMutation.data && (
        <p className="status" aria-label="Saved Revision Branch result">
          Created Branch {createBranchMutation.data.display_name} ({createBranchMutation.data.branch_id})
          from Saved Revision {selectedRevisionId}. The Viewer Branch was not changed.
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
            <h4 id="restore-dialog-title">Confirm Saved Revision restore</h4>
            <p>
              This will restore <strong>{branch.display_name}</strong> from Saved Revision{' '}
              <strong>{detail.revision_id}</strong>. It will not delete later history. A separate
              pre-restore checkpoint of head{' '}
              <strong>{restoreReview.expectedHeadSavedRevisionId}</strong> will be created first.
            </p>
            <MetadataList
              items={[
                { label: 'Reviewed head', value: restoreReview.expectedHeadSavedRevisionId },
                { label: 'Reviewed Draft version', value: restoreReview.expectedDraftVersion },
                { label: 'Reviewed Viewer Branch', value: restoreReview.expectedCurrentViewerBranchId },
                { label: 'Restore target', value: detail.revision_id }
              ]}
            />
            {!reviewStillCurrent && (
              <p className="error">
                The reviewed state changed. Close this dialog and review the refreshed state.
              </p>
            )}
            <label>
              Type <code>{restoreReview.confirmationPhrase}</code>
              <input
                aria-label="Restore confirmation phrase"
                autoComplete="off"
                autoFocus
                value={typedConfirmation}
                onChange={(event) => setTypedConfirmation(event.target.value)}
              />
            </label>
            <label className="checkbox-label">
              <input
                aria-label="Confirm Saved Revision restore"
                type="checkbox"
                checked={restoreConfirmed}
                onChange={(event) => setRestoreConfirmed(event.target.checked)}
              />
              I understand that the current Branch state will be replaced by a new restore revision,
              while the pre-restore state remains recoverable.
            </label>
            <div className="actions">
              <button type="button" className="button-ghost" onClick={closeRestoreReview}>
                Cancel
              </button>
              <button
                type="button"
                className="button-danger"
                disabled={!canSubmitRestore}
                onClick={() => restoreReview && restoreMutation.mutate(restoreReview)}
              >
                {restoreMutation.isPending ? 'Restoring...' : 'Confirm restore'}
              </button>
            </div>
          </section>
        </div>
      )}
    </SectionCard>
  )
}

function RestoreResult({ result }: { result: RestoreSavedRevisionResponse }): JSX.Element {
  return (
    <div className="status" aria-label="Saved Revision restore result">
      Restore completed. New Saved Revision: {result.saved_revision.revision_id}; safety checkpoint:{' '}
      {result.safety_checkpoint.checkpoint_id}; restored target: {result.target_saved_revision_id}; Viewer
      Branch: {result.viewer_branch_id}. Later history remains preserved.
    </div>
  )
}
