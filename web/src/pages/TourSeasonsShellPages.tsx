import { type ReactNode, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getCategories, getSeasonRegistry, getSeasonTemplates, getTournaments } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'


type ValidationSeverity = 'OK' | 'Info' | 'Warning'
type ValidationFilter = 'All' | ValidationSeverity


function TourSeasonsShellPage({
  title,
  subtitle,
  children
}: {
  title: string
  subtitle: string
  children: ReactNode
}): JSX.Element {


  return (
    <section className="panel">
      <PageIntro title={title} subtitle={subtitle} />
      <SectionCard title="Planned model">{children}</SectionCard>
      <SectionCard title="Current tooling">
        <p>
          This page is a transitional shell. Continue operational editing in{' '}
          <Link to="/admin/tournament-templates">Tournament Templates</Link> and{' '}
          <Link to="/admin/seasons">Seasons</Link>.
        </p>
        <p>
          Return to the <Link to="/admin/tour-seasons">Tour &amp; Seasons hub</Link>.
        </p>
      </SectionCard>
    </section>
  )
}

export function AdminTourSeasonsComparePage(): JSX.Element {


  return (
    <TourSeasonsShellPage title="Calendar Compare / Apply" subtitle="Compare a current season with a template or another season.">
      <p>Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.</p>
      <p>Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.</p>
      <p>
        Current operational calendar editing remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsValidationPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const tournamentsQuery = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })

  const registry = registryQuery.data
  const categories = categoriesQuery.data?.categories ?? []
  const tournaments = tournamentsQuery.data?.tournaments ?? []
  const templates = templatesQuery.data?.templates ?? []
  const slotCountTotal = templates.reduce((total, template) => total + template.slots.length, 0)
  const [severityFilter, setSeverityFilter] = useState<ValidationFilter>('All')

  const registryChecks: { severity: ValidationSeverity; message: string }[] = registry
    ? [
        { severity: registry.season_count === 40 ? 'OK' : 'Warning', message: `season_count is ${registry.season_count} (expected 40).` },
        { severity: registry.week_count === 61 ? 'OK' : 'Warning', message: `week_count is ${registry.week_count} (expected 61).` },
        { severity: registry.season_week_1_year_week === 37 ? 'OK' : 'Warning', message: `season_week_1_year_week is ${registry.season_week_1_year_week} (expected 37).` }
      ]
    : []

  const categoryIssues = categories.flatMap((category) => {
    const issues: { severity: 'Info' | 'Warning'; message: string; id: string; name: string }[] = []
    if (category.notes.length > 0) issues.push({ severity: 'Warning', message: `Notes present: ${category.notes.join('; ')}`, id: category.category_id, name: category.name })
    if (category.main_draw_size === null) issues.push({ severity: 'Info', message: 'Main draw mixed or unavailable.', id: category.category_id, name: category.name })
    if (category.qualification_draw_size === null) issues.push({ severity: 'Info', message: 'Qualification draw mixed or unavailable.', id: category.category_id, name: category.name })
    if (category.schedule_footprint_weeks === null) issues.push({ severity: 'Info', message: 'Schedule footprint weeks mixed or unavailable.', id: category.category_id, name: category.name })
    if (category.source_template_ids.length === 0) issues.push({ severity: 'Warning', message: 'No source template IDs linked.', id: category.category_id, name: category.name })
    return issues
  })

  const tournamentIssues = tournaments.flatMap((tournament) => {
    const issues: { severity: 'Info' | 'Warning'; message: string; id: string; name: string }[] = []
    if (tournament.notes.length > 0) issues.push({ severity: 'Warning', message: `Notes present: ${tournament.notes.join('; ')}`, id: tournament.tournament_id, name: tournament.name })
    if (tournament.default_category === null) issues.push({ severity: 'Info', message: 'Mixed category in source templates.', id: tournament.tournament_id, name: tournament.name })
    if (tournament.default_host_country === null) issues.push({ severity: 'Info', message: 'Mixed host in source templates.', id: tournament.tournament_id, name: tournament.name })
    if (tournament.default_region === null) issues.push({ severity: 'Info', message: 'Mixed region in source templates.', id: tournament.tournament_id, name: tournament.name })
    if (tournament.source_template_ids.length === 0) issues.push({ severity: 'Warning', message: 'No source template IDs linked.', id: tournament.tournament_id, name: tournament.name })
    return issues
  })

  const seasonTemplateIssues = templates.flatMap((template) => {
    const issues: { severity: 'Info' | 'Warning'; message: string; id: string; name: string }[] = []
    if (template.week_count !== 61) issues.push({ severity: 'Warning', message: `week_count is ${template.week_count} (expected 61).`, id: template.template_id, name: template.name })
    if (template.slot_count !== template.slots.length) issues.push({ severity: 'Warning', message: `slot_count (${template.slot_count}) does not match slots.length (${template.slots.length}).`, id: template.template_id, name: template.name })
    if (template.source === 'derived_preview:tournament_templates') issues.push({ severity: 'Info', message: 'Derived preview source; dedicated season template source ID is not yet explicit.', id: template.template_id, name: template.name })
    if (template.slots.length === 0) issues.push({ severity: 'Info', message: 'No slots present.', id: template.template_id, name: template.name })

    template.slots.forEach((slot) => {
      if (slot.season_week_start < 1 || slot.season_week_end > 61) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has week range SW${slot.season_week_start}–SW${slot.season_week_end} outside SW1–SW61.`, id: template.template_id, name: template.name })
      }
      if (slot.season_week_end < slot.season_week_start) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has end week before start week.`, id: template.template_id, name: template.name })
      }
      if (slot.has_qualification && slot.qualifying_week_start === null) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has qualification enabled but qualifying_week_start is null.`, id: template.template_id, name: template.name })
      }
      if (slot.source_template_id === null) {
        issues.push({ severity: 'Info', message: `Slot ${slot.slot_id} has no source_template_id.`, id: template.template_id, name: template.name })
      }
    })
    return issues
  })


  const allChecks = useMemo(() => [...registryChecks, ...categoryIssues, ...tournamentIssues, ...seasonTemplateIssues], [registryChecks, categoryIssues, tournamentIssues, seasonTemplateIssues])
  const counts = useMemo(() => ({
    total: allChecks.length,
    warning: allChecks.filter((issue) => issue.severity === 'Warning').length,
    info: allChecks.filter((issue) => issue.severity === 'Info').length,
    ok: allChecks.filter((issue) => issue.severity === 'OK').length
  }), [allChecks])

  const filterBySeverity = <T extends { severity: ValidationSeverity }>(items: T[]): T[] =>
    severityFilter === 'All' ? items : items.filter((item) => item.severity === severityFilter)

  const filteredRegistryChecks = filterBySeverity(registryChecks)
  const filteredCategoryIssues = filterBySeverity(categoryIssues)
  const filteredTournamentIssues = filterBySeverity(tournamentIssues)
  const filteredSeasonTemplateIssues = filterBySeverity(seasonTemplateIssues)

  return (
    <section className="panel">
      <PageIntro title="Calendar Validation" subtitle="Read-only validation overview for Tour & Seasons foundation data." />
      <SectionCard title="Summary">
        <ul className="dashboard-help-list">
          <li>Season Registry: {registryQuery.isLoading ? 'Loading…' : registryQuery.error ? `Error: ${formatApiError(registryQuery.error)}` : 'Loaded'}</li>
          <li>Categories: {categoriesQuery.isLoading ? 'Loading…' : categoriesQuery.error ? `Error: ${formatApiError(categoriesQuery.error)}` : categories.length}</li>
          <li>Tournaments: {tournamentsQuery.isLoading ? 'Loading…' : tournamentsQuery.error ? `Error: ${formatApiError(tournamentsQuery.error)}` : tournaments.length}</li>
          <li>Season Templates: {templatesQuery.isLoading ? 'Loading…' : templatesQuery.error ? `Error: ${formatApiError(templatesQuery.error)}` : templates.length}</li>
          <li>Season Template Slots (total): {templatesQuery.error ? '—' : slotCountTotal}</li>
          <li>Total checks: {counts.total}</li>
          <li>Warnings: {counts.warning}</li>
          <li>Info: {counts.info}</li>
          <li>OK: {counts.ok}</li>
        </ul>
        <p>Severity filter:</p>
        <div role="group" aria-label="Validation severity filters">
          {(['All', 'Warnings', 'Info', 'OK'] as const).map((option) => {
            const mapped = option === 'Warnings' ? 'Warning' : option
            const isActive = severityFilter === mapped
            return (
              <button key={option} type="button" onClick={() => setSeverityFilter(mapped)} aria-pressed={isActive}>
                {option}
              </button>
            )
          })}
        </div>
      </SectionCard>

      <SectionCard title="Registry checks">
        {registryChecks.length === 0 ? <p>No issues detected from current read-only checks.</p> : filteredRegistryChecks.length === 0 ? <p>No checks match the current filter.</p> : <ul className="dashboard-help-list">{filteredRegistryChecks.map((check, index) => <li key={`registry-check-${index}`}>[{check.severity}] Registry — <Link to="/admin/tour-seasons/season-registry">Season Registry</Link>: {check.message}</li>)}</ul>}
      </SectionCard>

      <SectionCard title="Category checks">
        {categoryIssues.length === 0 ? <p>No issues detected from current read-only checks.</p> : filteredCategoryIssues.length === 0 ? <p>No checks match the current filter.</p> : <ul className="dashboard-help-list">{filteredCategoryIssues.map((issue, index) => <li key={`category-issue-${index}`}>[{issue.severity}] Category — <Link to={`/admin/tour-seasons/categories/${issue.id}`}>{issue.name} ({issue.id})</Link>: {issue.message}</li>)}</ul>}
      </SectionCard>

      <SectionCard title="Tournament checks">
        {tournamentIssues.length === 0 ? <p>No issues detected from current read-only checks.</p> : filteredTournamentIssues.length === 0 ? <p>No checks match the current filter.</p> : <ul className="dashboard-help-list">{filteredTournamentIssues.map((issue, index) => <li key={`tournament-issue-${index}`}>[{issue.severity}] Tournament — <Link to={`/admin/tour-seasons/tournaments/${issue.id}`}>{issue.name} ({issue.id})</Link>: {issue.message}</li>)}</ul>}
      </SectionCard>

      <SectionCard title="Season Template checks">
        {seasonTemplateIssues.length === 0 ? <p>No issues detected from current read-only checks.</p> : filteredSeasonTemplateIssues.length === 0 ? <p>No checks match the current filter.</p> : <ul className="dashboard-help-list">{filteredSeasonTemplateIssues.map((issue, index) => <li key={`template-issue-${index}`}>[{issue.severity}] Season Template — <Link to={`/admin/tour-seasons/season-templates/${issue.id}`}>{issue.name} ({issue.id})</Link>: {issue.message}</li>)}</ul>}
      </SectionCard>

      <SectionCard title="Planned future validation">
        <ul className="dashboard-help-list">
          <li>Backend validation engine — planned.</li>
          <li>Compare/apply validation — planned.</li>
          <li>Edition lifecycle validation — planned.</li>
          <li>Simulation-impact validation — planned.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Navigation">
        <p>
          <Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link>
        </p>
        <p>
          <Link to="/admin/tour-seasons/categories">Open Categories</Link>
        </p>
        <p>
          <Link to="/admin/tour-seasons/tournaments">Open Tournaments</Link>
        </p>
        <p>
          <Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link>
        </p>
      </SectionCard>
    </section>
  )
}
