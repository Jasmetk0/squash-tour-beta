import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getCategories } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(', ') : '—'
}

function formatBool(value: boolean | null): string {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return 'Mixed'
}

export function AdminTourSeasonsCategoryDetailPage(): JSX.Element {
  const { categoryId = '' } = useParams()
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const payload = categoriesQuery.data
  const category = payload?.categories.find((item) => item.category_id === categoryId)

  return (
    <section className="panel">
      <PageIntro title="Category" subtitle="Read-only category rules package derived from current tournament template config." />

      {categoriesQuery.isLoading ? <p className="status">Loading category…</p> : null}
      {categoriesQuery.error ? <p className="error">Failed to load category: {formatApiError(categoriesQuery.error)}</p> : null}
      {payload && !category ? <p className="status">Category not found.</p> : null}

      {category ? (
        <>
          <SectionCard title="Header summary">
            <ul className="dashboard-help-list">
              <li>Name: {category.name}</li>
              <li>Category ID: {category.category_id}</li>
              <li>Status: {category.status}</li>
              <li>Source: {category.source}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Identity">
            <ul className="dashboard-help-list">
              <li>category_id: {category.category_id}</li>
              <li>name: {category.name}</li>
              <li>template_count: {category.template_count}</li>
              <li>source_template_ids: {formatList(category.source_template_ids)}</li>
              <li>status: {category.status}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Validity / versioning">
            <ul className="dashboard-help-list">
              <li>valid_from_season: {category.valid_from_season ?? '—'}</li>
              <li>valid_to_season: {category.valid_to_season ?? '—'}</li>
              <li>Season-range category versioning is planned and not yet implemented.</li>
            </ul>
          </SectionCard>

          <SectionCard title="Draw structure">
            <ul className="dashboard-help-list">
              <li>main_draw_size: {category.main_draw_size ?? '—'}</li>
              <li>qualification_draw_size: {category.qualification_draw_size ?? '—'}</li>
              <li>direct_entries: {category.direct_entries ?? '—'}</li>
              <li>qualifiers: {category.qualifiers ?? '—'}</li>
              <li>wildcards: {category.wildcards ?? '—'}</li>
              <li>lucky_losers: {category.lucky_losers ?? '—'}</li>
              <li>seeds_count: {category.seeds_count ?? '—'}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Competition model">
            <ul className="dashboard-help-list">
              <li>tour_level: {category.tour_level ?? '—'}</li>
              <li>prestige_rank: {category.prestige_rank ?? '—'}</li>
              <li>mandatory: {formatBool(category.mandatory)}</li>
              <li>match_format: {category.match_format ?? '—'}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Scoring / economics">
            <ul className="dashboard-help-list">
              <li>prize_money_total: {category.prize_money_total ?? '—'}</li>
            </ul>
            <p>points_by_round:</p>
            {category.points_by_round ? (
              <table>
                <thead>
                  <tr><th>Round</th><th>Points</th></tr>
                </thead>
                <tbody>
                  {Object.entries(category.points_by_round).map(([round, points]) => (
                    <tr key={round}><td>{round}</td><td>{points}</td></tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No unified points table available in this derived preview.</p>
            )}
          </SectionCard>

          <SectionCard title="Schedule footprint">
            <ul className="dashboard-help-list">
              <li>qualifying_weeks_count: {category.qualifying_weeks_count ?? '—'}</li>
              <li>main_draw_weeks_count: {category.main_draw_weeks_count ?? '—'}</li>
              <li>schedule_footprint_weeks: {category.schedule_footprint_weeks ?? '—'}</li>
            </ul>
          </SectionCard>

          <SectionCard title="Notes">
            {category.notes.length > 0 ? (
              <ul className="dashboard-help-list">
                {category.notes.map((note) => <li key={note}>{note}</li>)}
              </ul>
            ) : (
              <p>No notes.</p>
            )}
          </SectionCard>

          <SectionCard title="Planned future model">
            <ul className="dashboard-help-list">
              <li>Category editor — planned.</li>
              <li>Category versioning by season range — planned.</li>
              <li>Tournament editions will snapshot category rules for historical stability.</li>
            </ul>
          </SectionCard>
        </>
      ) : null}

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/categories">Back to Categories</Link></p>
        <p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p>
        <p><Link to="/admin/tour-seasons/tournaments">Open Tournaments</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
      </SectionCard>
    </section>
  )
}
