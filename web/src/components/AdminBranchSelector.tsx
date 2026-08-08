import { useAdminBranch } from '../admin/AdminBranchContext'

function branchLabel(displayName: string, branchId: string): string {
  return displayName.trim() || branchId
}

export function AdminBranchSelector(): JSX.Element {
  const context = useAdminBranch()
  const selectedLabel = context.selectedBranch
    ? branchLabel(context.selectedBranch.display_name, context.selectedBranch.branch_id)
    : context.isLoading ? 'Loading…' : 'Unavailable'

  return (
    <div className="admin-active-branch-compact" aria-label="Admin Branch context">
      <span className="admin-active-branch-compact__status">
        Branch <strong>{selectedLabel}</strong>
        {context.selectedBranchId && context.selectedBranchId === context.viewerBranchId ? <small>Viewer Branch</small> : null}
      </span>
      <label className="admin-active-branch-compact__field">
        <span className="sr-only">Admin active Branch</span>
        <select
          aria-label="Admin active Branch"
          value={context.selectedBranchId ?? ''}
          onChange={event => context.selectBranch(event.target.value)}
          disabled={context.isLoading || context.branches.length === 0}
        >
          {context.selectedBranchId === null ? <option value="">{context.isLoading ? 'Loading Branches' : 'Branch unavailable'}</option> : null}
          {context.branches.map(branch => (
            <option key={branch.branch_id} value={branch.branch_id}>
              {branchLabel(branch.display_name, branch.branch_id)}{branch.branch_id === context.viewerBranchId ? ' · Viewer Branch' : ''}
            </option>
          ))}
        </select>
      </label>
      {context.error ? <span className="sr-only" role="status">{context.error}</span> : null}
      {context.viewerBranchMissing ? <span className="sr-only" role="status">Viewer Branch is missing from the available Branches; using a deterministic fallback.</span> : null}
    </div>
  )
}
