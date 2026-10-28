import { useState } from 'react'
import { Link } from 'react-router-dom'

import { SectionCard } from '../components/RunScopedUi'
import { useLanguage } from '../i18n/LanguageContext'
import { readLastRunId } from '../viewer/activeRun'
import { adminDiagnosticsCountLabel, adminDiagnosticsText } from './adminDiagnosticsText'

export function AdminDiagnosticsPage(): JSX.Element {
  const { language } = useLanguage()
  const text = (english: string) => adminDiagnosticsText(english, language)
  const lastRunId = readLastRunId()?.trim() || null
  const lastRunDiagnosticsPath = lastRunId ? `/admin/runs/${encodeURIComponent(lastRunId)}/diagnostics` : null
  const [sectionFilter, setSectionFilter] = useState<'all' | 'available' | 'planned'>('all')
  const displayedSectionCount = sectionFilter === 'all' ? 6 : 3

  const areas = [
    { kind: 'available', title: 'World Balance', content: <>
          <p>
            {text('Use linked World tools to inspect country inputs and Talent Preview. Broader balance diagnostics, population dominance and small-country risk checks are planned; links here do not imply that all such checks are implemented.')}
          </p>
          <p>
            {text('Current action:')} <Link to="/admin/world/talent-preview">{text('Talent Preview')}</Link> ·{' '}
            <Link to="/admin/world/library/official_fax_world/countries">{text('Official FAX World countries')}</Link>
          </p>
        </> },
    { kind: 'available', title: 'Calendar Validation', content: <>
          <p>
            {text("Calendar checks should use each Run's configured season-week range rather than assuming W01–W61. Existing validation tools also cover event timing, qualifiers, categories, hosts and schedule conflicts within their supported scope.")}
          </p>
          <p>
            {text('Current action:')} <Link to="/admin/tour-seasons/validation">{text('Calendar Validation')}</Link> · <Link to="/admin/seasons">{text('Seasons')}</Link>
          </p>
        </> },
    { kind: 'available', title: 'Run Health', content: <>
          <p>{text('Open the Run Diagnostics page for currently supported operational checks. Broader health, snapshot and stale-artifact coverage is not implied by this navigation card.')}</p>
          <p>
            {text('Current action:')} <Link to="/admin/runs">{text('Runs')}</Link>
            {lastRunDiagnosticsPath ? (
              <>
                {' '}
                · <Link to={lastRunDiagnosticsPath}>{text('Last run diagnostics')}</Link>
              </>
            ) : null}
          </p>
        </> },
    { kind: 'planned', title: 'Invalidated Data', content: <>
          <p>
            {text('Planned downstream invalidation tracking after calendar, entry, draw, result, points, or ranking edits.')}
          </p>
          <p className="status">{text('Current action: Planned / run-scoped diagnostics later.')}</p>
        </> },
    { kind: 'planned', title: 'Narrative Locks', content: <>
          <p>{text('Planned conflict/plausibility checks for Soft/Hard/Winner/Round/Exact Match/Path locks.')}</p>
          <p className="status">{text('Current action: Planned.')}</p>
        </> },
    { kind: 'planned', title: 'Audit / Warnings', content: <>
          <p>
            {text('Future consolidated feed for manual edits, lock changes, regeneration skips, invalidation events, and warning history.')}
          </p>
          <p className="status">{text('Current action: Audit remains embedded in specific operational pages.')}</p>
        </> }
  ]

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>{text('Diagnostics')}</h2>
        <p className="subtitle">{text('Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.')}</p>
      </div>
      <p className="status">{text('This is a navigation and triage page, not a consolidated diagnostic scan. Existing tools are linked below; planned coverage is explicitly separate. Run-specific diagnostics remain under Run Diagnostics.')}</p>

      <SectionCard title={text('Overview')}>
        <p>{text('Open a run first to inspect current operational diagnostics.')}</p>
        <p>
          <Link to="/admin/runs">{text('Open Runs')}</Link>
          {lastRunDiagnosticsPath ? (
            <>
              {' '}
              · <Link to={lastRunDiagnosticsPath}>{text('Open last run diagnostics')} ({lastRunId})</Link>
            </>
          ) : null}
        </p>
      </SectionCard>

      <label>{text('Show diagnostics sections')}
        <select value={sectionFilter} onChange={event => setSectionFilter(event.target.value as typeof sectionFilter)}>
          <option value="all">{text('All areas')}</option>
          <option value="available">{text('Linked tools')}</option>
          <option value="planned">{text('Planned areas')}</option>
        </select>
      </label>
      <p role="status">{adminDiagnosticsCountLabel(displayedSectionCount, language)}</p>

      <div className="dashboard-stack">
        {areas.filter(area => sectionFilter === 'all' || area.kind === sectionFilter).map(area => (
          <SectionCard key={area.title} title={text(area.title)}>{area.content}</SectionCard>
        ))}
      </div>

      <SectionCard title={text('What Diagnostics should explain')}>
        <ul className="dashboard-help-list">
          {['what happened', 'why it matters', 'what is affected', 'what to do next', 'where to click']
            .map(question => <li key={question}>{text(question)}</li>)}
        </ul>
      </SectionCard>

      <SectionCard title={text('Current vs planned')}>
        <p>
          <strong>{text('Current:')}</strong> {text('real diagnostics are mostly run-scoped; this top-level page is a launcher/triage shell; existing Run Diagnostics is the operational source today.')}
        </p>
        <p>
          <strong>{text('Planned:')}</strong> {text('top-level aggregation across World, Calendar, Runs, Invalidated Data, Narrative Locks, and Audit.')}
        </p>
      </SectionCard>
    </section>
  )
}
