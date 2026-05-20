import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getCategories, getSeasonRegistry, getSeasonTemplates, getTourSeasonsValidation, getTournaments } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type ValidationSeverity = 'OK' | 'Info' | 'Warning'
type ValidationFilter = 'All' | ValidationSeverity

type NormalizedValidationIssue = {
  id: string
  severity: ValidationSeverity
  itemLabel?: string
  message: string
  link?: string | null
}

function ValidationIssueList({
  title,
  issues,
  emptyMessage,
  filter,
  planned = false
}: {
  title: string
  issues: NormalizedValidationIssue[]
  emptyMessage: string
  filter: ValidationFilter
  planned?: boolean
}): JSX.Element {
  const filteredIssues = filter === 'All' ? issues : issues.filter((issue) => issue.severity === filter)

  return (
    <>
      {issues.length === 0 ? (
        <p>{emptyMessage}</p>
      ) : filteredIssues.length === 0 ? (
        <p>No checks match the current filter.</p>
      ) : (
        <ul className="dashboard-help-list">
          {filteredIssues.map((issue) => (
            <li key={issue.id}>
              [{issue.severity}] {title}{issue.itemLabel ? ` — ${issue.itemLabel}` : ''}
              {issue.link ? <>: <Link to={issue.link}>{issue.message}</Link></> : <>: {issue.message}</>}
              {planned ? ' (planned)' : ''}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export function AdminTourSeasonsValidationPage(): JSX.Element {
  const registryQuery = useQuery({ queryKey: ['season-registry'], queryFn: getSeasonRegistry, retry: false })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const tournamentsQuery = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments, retry: false })
  const templatesQuery = useQuery({ queryKey: ['season-templates'], queryFn: getSeasonTemplates, retry: false })
  const backendValidationQuery = useQuery({ queryKey: ['tour-seasons-validation'], queryFn: getTourSeasonsValidation, retry: false })

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
    const issues: NormalizedValidationIssue[] = []
    if (category.notes.length > 0) issues.push({ id: `category-${category.category_id}-notes`, severity: 'Warning', itemLabel: `Category — ${category.name} (${category.category_id})`, message: `Notes present: ${category.notes.join('; ')}`, link: `/admin/tour-seasons/categories/${category.category_id}` })
    if (category.main_draw_size === null) issues.push({ id: `category-${category.category_id}-main-draw-size`, severity: 'Info', itemLabel: `Category — ${category.name} (${category.category_id})`, message: 'Main draw mixed or unavailable.', link: `/admin/tour-seasons/categories/${category.category_id}` })
    if (category.qualification_draw_size === null) issues.push({ id: `category-${category.category_id}-qualification-draw-size`, severity: 'Info', itemLabel: `Category — ${category.name} (${category.category_id})`, message: 'Qualification draw mixed or unavailable.', link: `/admin/tour-seasons/categories/${category.category_id}` })
    if (category.schedule_footprint_weeks === null) issues.push({ id: `category-${category.category_id}-schedule-footprint`, severity: 'Info', itemLabel: `Category — ${category.name} (${category.category_id})`, message: 'Schedule footprint weeks mixed or unavailable.', link: `/admin/tour-seasons/categories/${category.category_id}` })
    if (category.source_template_ids.length === 0) issues.push({ id: `category-${category.category_id}-source-template-ids`, severity: 'Warning', itemLabel: `Category — ${category.name} (${category.category_id})`, message: 'No source template IDs linked.', link: `/admin/tour-seasons/categories/${category.category_id}` })
    return issues
  })

  const tournamentIssues = tournaments.flatMap((tournament) => {
    const issues: NormalizedValidationIssue[] = []
    if (tournament.notes.length > 0) issues.push({ id: `tournament-${tournament.tournament_id}-notes`, severity: 'Warning', itemLabel: `Tournament — ${tournament.name} (${tournament.tournament_id})`, message: `Notes present: ${tournament.notes.join('; ')}`, link: `/admin/tour-seasons/tournaments/${tournament.tournament_id}` })
    if (tournament.default_category === null) issues.push({ id: `tournament-${tournament.tournament_id}-category`, severity: 'Info', itemLabel: `Tournament — ${tournament.name} (${tournament.tournament_id})`, message: 'Mixed category in source templates.', link: `/admin/tour-seasons/tournaments/${tournament.tournament_id}` })
    if (tournament.default_host_country === null) issues.push({ id: `tournament-${tournament.tournament_id}-host`, severity: 'Info', itemLabel: `Tournament — ${tournament.name} (${tournament.tournament_id})`, message: 'Mixed host in source templates.', link: `/admin/tour-seasons/tournaments/${tournament.tournament_id}` })
    if (tournament.default_region === null) issues.push({ id: `tournament-${tournament.tournament_id}-region`, severity: 'Info', itemLabel: `Tournament — ${tournament.name} (${tournament.tournament_id})`, message: 'Mixed region in source templates.', link: `/admin/tour-seasons/tournaments/${tournament.tournament_id}` })
    if (tournament.source_template_ids.length === 0) issues.push({ id: `tournament-${tournament.tournament_id}-source-template-ids`, severity: 'Warning', itemLabel: `Tournament — ${tournament.name} (${tournament.tournament_id})`, message: 'No source template IDs linked.', link: `/admin/tour-seasons/tournaments/${tournament.tournament_id}` })
    return issues
  })

  const seasonTemplateIssues = templates.flatMap((template) => {
    const issues: NormalizedValidationIssue[] = []
    if (template.week_count !== 61) issues.push({ severity: 'Warning', message: `week_count is ${template.week_count} (expected 61).`, id: `season-template-${template.template_id}-week-count`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
    if (template.slot_count !== template.slots.length) issues.push({ severity: 'Warning', message: `slot_count (${template.slot_count}) does not match slots.length (${template.slots.length}).`, id: `season-template-${template.template_id}-slot-count`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
    if (template.source === 'derived_preview:tournament_templates') issues.push({ severity: 'Info', message: 'Derived preview source; dedicated season template source ID is not yet explicit.', id: `season-template-${template.template_id}-derived-source`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
    if (template.slots.length === 0) issues.push({ severity: 'Info', message: 'No slots present.', id: `season-template-${template.template_id}-no-slots`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })

    template.slots.forEach((slot) => {
      if (slot.season_week_start < 1 || slot.season_week_end > 61) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has week range SW${slot.season_week_start}–SW${slot.season_week_end} outside SW1–SW61.`, id: `season-template-${template.template_id}-${slot.slot_id}-week-range`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
      }
      if (slot.season_week_end < slot.season_week_start) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has end week before start week.`, id: `season-template-${template.template_id}-${slot.slot_id}-end-before-start`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
      }
      if (slot.has_qualification && slot.qualifying_week_start === null) {
        issues.push({ severity: 'Warning', message: `Slot ${slot.slot_id} has qualification enabled but qualifying_week_start is null.`, id: `season-template-${template.template_id}-${slot.slot_id}-qualification-week`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
      }
      if (slot.source_template_id === null) {
        issues.push({ severity: 'Info', message: `Slot ${slot.slot_id} has no source_template_id.`, id: `season-template-${template.template_id}-${slot.slot_id}-missing-source-template-id`, itemLabel: `Season Template — ${template.name} (${template.template_id})`, link: `/admin/tour-seasons/season-templates/${template.template_id}` })
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


  const backendPreviewIssues = useMemo(() => (backendValidationQuery.data?.sections ?? []).flatMap((section) =>
    section.issues.map((issue) => ({
      id: `backend-${section.section_id}-${issue.issue_id}`,
      severity: (issue.severity === 'ok' ? 'OK' : issue.severity === 'info' ? 'Info' : 'Warning') as ValidationSeverity,
      itemLabel: issue.item_name && issue.item_id ? `${section.title} — ${issue.item_name} (${issue.item_id})` : issue.item_name ? `${section.title} — ${issue.item_name}` : issue.item_id ? `${section.title} — ${issue.item_id}` : section.title,
      message: issue.message,
      link: issue.link_hint
    }))
  ), [backendValidationQuery.data])


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

      <SectionCard title="Backend validation foundation">
        {backendValidationQuery.isLoading ? (
          <p>Loading backend validation foundation…</p>
        ) : backendValidationQuery.error ? (
          <p>Backend validation foundation unavailable: {formatApiError(backendValidationQuery.error)}</p>
        ) : backendValidationQuery.data ? (
          <>
            <ul className="dashboard-help-list">
              <li>Status: {backendValidationQuery.data.status}</li>
              <li>Total checks: {backendValidationQuery.data.summary.total_checks}</li>
              <li>Warnings: {backendValidationQuery.data.summary.warning_count}</li>
              <li>Info: {backendValidationQuery.data.summary.info_count}</li>
              <li>OK: {backendValidationQuery.data.summary.ok_count}</li>
              <li>Sections returned: {backendValidationQuery.data.sections.length}</li>
            </ul>
            <p>Backend validation is currently a read-only foundation. Frontend-derived checks remain visible below until backend validation becomes the authoritative source.</p>
            <p>Comparison only; both systems are read-only.</p>
            <ul className="dashboard-help-list">
              <li>Frontend-derived total checks: {counts.total}</li>
              <li>Backend total checks: {backendValidationQuery.data.summary.total_checks}</li>
            </ul>
          </>
        ) : (
          <p>Backend validation foundation unavailable: empty response.</p>
        )}
      </SectionCard>

      <SectionCard title="Backend validation issue preview">
        <p>Secondary preview only. Frontend-derived checks remain primary until backend validation becomes authoritative.</p>
        <ValidationIssueList
          title="Backend"
          issues={backendPreviewIssues}
          emptyMessage="No backend issues returned in preview."
          filter={severityFilter}
          planned
        />
      </SectionCard>

      <SectionCard title="Registry checks">
        <ValidationIssueList
          title="Registry"
          issues={registryChecks.map((check, index) => ({ id: `registry-check-${index}`, severity: check.severity, itemLabel: 'Season Registry', message: check.message, link: '/admin/tour-seasons/season-registry' }))}
          emptyMessage="No issues detected from current read-only checks."
          filter={severityFilter}
        />
      </SectionCard>

      <SectionCard title="Category checks">
        <ValidationIssueList title="Category" issues={categoryIssues} emptyMessage="No issues detected from current read-only checks." filter={severityFilter} />
      </SectionCard>

      <SectionCard title="Tournament checks">
        <ValidationIssueList title="Tournament" issues={tournamentIssues} emptyMessage="No issues detected from current read-only checks." filter={severityFilter} />
      </SectionCard>

      <SectionCard title="Season Template checks">
        <ValidationIssueList title="Season Template" issues={seasonTemplateIssues} emptyMessage="No issues detected from current read-only checks." filter={severityFilter} />
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
