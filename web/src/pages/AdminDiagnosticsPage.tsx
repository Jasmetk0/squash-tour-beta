import { Link } from 'react-router-dom'

import { SectionCard } from '../components/RunScopedUi'
import { readLastRunId } from '../viewer/activeRun'

export function AdminDiagnosticsPage(): JSX.Element {
  const lastRunId = readLastRunId()
  const lastRunDiagnosticsPath = lastRunId ? `/admin/runs/${lastRunId}/diagnostics` : null

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Diagnostics</h2>
        <p className="subtitle">Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.</p>
      </div>
      <p className="status">Top-level diagnostics is being consolidated here. Operational diagnostics currently remain run-scoped in Run Diagnostics.</p>

      <SectionCard title="Overview">
        <p>Open a run first to inspect current operational diagnostics.</p>
        <p>
          <Link to="/admin/runs">Open Runs</Link>
          {lastRunDiagnosticsPath ? (
            <>
              {' '}
              · <Link to={lastRunDiagnosticsPath}>Open last run diagnostics ({lastRunId})</Link>
            </>
          ) : null}
        </p>
      </SectionCard>

      <div className="dashboard-stack">
        <SectionCard title="World Balance">
          <p>
            Checks country input completeness, talent distribution balance, population dominance risk, small-country zero-chance
            risk, and Talent Preview anomalies.
          </p>
          <p>
            Current action: <Link to="/admin/world/talent-preview">Talent Preview</Link> ·{' '}
            <Link to="/admin/world/library/official_fax_world/countries">Official FAX World countries</Link>
          </p>
        </SectionCard>

        <SectionCard title="Calendar Validation">
          <p>
            Checks W01–W61 range, multi-week event blocks, qualifying before main draw, mandatory events, invalid
            categories/hosts, and schedule conflicts.
          </p>
          <p>
            Current action: <Link to="/admin/tour-seasons/validation">Calendar Validation</Link> · <Link to="/admin/seasons">Seasons</Link>
          </p>
        </SectionCard>

        <SectionCard title="Run Health">
          <p>Checks run progress, incomplete events, missing results, stale artifacts, snapshots, and operational blockers.</p>
          <p>
            Current action: <Link to="/admin/runs">Runs</Link>
            {lastRunDiagnosticsPath ? (
              <>
                {' '}
                · <Link to={lastRunDiagnosticsPath}>Last run diagnostics</Link>
              </>
            ) : null}
          </p>
        </SectionCard>

        <SectionCard title="Invalidated Data">
          <p>
            Planned downstream invalidation tracking after calendar, entry, draw, result, points, or ranking edits.
          </p>
          <p className="status">Current action: Planned / run-scoped diagnostics later.</p>
        </SectionCard>

        <SectionCard title="Narrative Locks">
          <p>Planned conflict/plausibility checks for Soft/Hard/Winner/Round/Exact Match/Path locks.</p>
          <p className="status">Current action: Planned.</p>
        </SectionCard>

        <SectionCard title="Audit / Warnings">
          <p>
            Future consolidated feed for manual edits, lock changes, regeneration skips, invalidation events, and warning
            history.
          </p>
          <p className="status">Current action: Audit remains embedded in specific operational pages.</p>
        </SectionCard>
      </div>

      <SectionCard title="What Diagnostics should explain">
        <ul className="dashboard-help-list">
          <li>what happened</li>
          <li>why it matters</li>
          <li>what is affected</li>
          <li>what to do next</li>
          <li>where to click</li>
        </ul>
      </SectionCard>

      <SectionCard title="Current vs planned">
        <p>
          <strong>Current:</strong> real diagnostics are mostly run-scoped; this top-level page is a launcher/triage shell;
          existing Run Diagnostics is the operational source today.
        </p>
        <p>
          <strong>Planned:</strong> top-level aggregation across World, Calendar, Runs, Invalidated Data, Narrative Locks,
          and Audit.
        </p>
      </SectionCard>
    </section>
  )
}
