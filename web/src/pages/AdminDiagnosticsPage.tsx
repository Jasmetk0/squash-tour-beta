import { useState } from 'react'
import { Link } from 'react-router-dom'

import { SectionCard } from '../components/RunScopedUi'
import { readLastRunId } from '../viewer/activeRun'

export function AdminDiagnosticsPage(): JSX.Element {
  const lastRunId = readLastRunId()?.trim() || null
  const lastRunDiagnosticsPath = lastRunId ? `/admin/runs/${encodeURIComponent(lastRunId)}/diagnostics` : null
  const [sectionFilter, setSectionFilter] = useState<'all' | 'available' | 'planned'>('all')
  const displayedSectionCount = sectionFilter === 'all' ? 6 : 3

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Diagnostics</h2>
        <p className="subtitle">Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.</p>
      </div>
      <p className="status">This is a navigation and triage page, not a consolidated diagnostic scan. Existing tools are linked below; planned coverage is explicitly separate. Run-specific diagnostics remain under Run Diagnostics.</p>

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

      <label>Show diagnostics sections
        <select value={sectionFilter} onChange={event => setSectionFilter(event.target.value as typeof sectionFilter)}>
          <option value="all">All areas</option>
          <option value="available">Linked tools</option>
          <option value="planned">Planned areas</option>
        </select>
      </label>
      <p role="status">Showing {displayedSectionCount} of 6 diagnostic areas</p>

      <div className="dashboard-stack">
        {sectionFilter !== 'planned' && (
        <SectionCard title="World Balance">
          <p>
            Use linked World tools to inspect country inputs and Talent Preview. Broader balance diagnostics, population dominance
            and small-country risk checks are planned; links here do not imply that all such checks are implemented.
          </p>
          <p>
            Current action: <Link to="/admin/world/talent-preview">Talent Preview</Link> ·{' '}
            <Link to="/admin/world/library/official_fax_world/countries">Official FAX World countries</Link>
          </p>
        </SectionCard>
        )}

        {sectionFilter !== 'planned' && (
        <SectionCard title="Calendar Validation">
          <p>
            Calendar checks should use each Run's configured season-week range rather than assuming W01–W61.
            Existing validation tools also cover event timing, qualifiers, categories, hosts and schedule conflicts within their supported scope.
          </p>
          <p>
            Current action: <Link to="/admin/tour-seasons/validation">Calendar Validation</Link> · <Link to="/admin/seasons">Seasons</Link>
          </p>
        </SectionCard>
        )}

        {sectionFilter !== 'planned' && (
        <SectionCard title="Run Health">
          <p>Open the Run Diagnostics page for currently supported operational checks. Broader health, snapshot and stale-artifact
          coverage is not implied by this navigation card.</p>
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
        )}

        {sectionFilter !== 'available' && (
        <SectionCard title="Invalidated Data">
          <p>
            Planned downstream invalidation tracking after calendar, entry, draw, result, points, or ranking edits.
          </p>
          <p className="status">Current action: Planned / run-scoped diagnostics later.</p>
        </SectionCard>
        )}

        {sectionFilter !== 'available' && (
        <SectionCard title="Narrative Locks">
          <p>Planned conflict/plausibility checks for Soft/Hard/Winner/Round/Exact Match/Path locks.</p>
          <p className="status">Current action: Planned.</p>
        </SectionCard>
        )}

        {sectionFilter !== 'available' && (
        <SectionCard title="Audit / Warnings">
          <p>
            Future consolidated feed for manual edits, lock changes, regeneration skips, invalidation events, and warning
            history.
          </p>
          <p className="status">Current action: Audit remains embedded in specific operational pages.</p>
        </SectionCard>
        )}
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
