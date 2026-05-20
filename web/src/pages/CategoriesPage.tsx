import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getCategories } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminTourSeasonsCategoriesPage(): JSX.Element {
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const payload = categoriesQuery.data

  return (
    <section className="panel">
      <PageIntro title="Categories" subtitle="Read-only category rules packages derived from current tournament template config." />
      <SectionCard title="Read-only foundation notes">
        <ul className="dashboard-help-list">
          <li>Read-only foundation.</li>
          <li>Full category editor/versioning is planned.</li>
          <li>Existing operational tooling remains in <Link to="/admin/tournament-templates">/admin/tournament-templates</Link>.</li>
          <li>Category values may be null when source templates contain mixed values.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Summary">
        {categoriesQuery.isLoading ? <p className="status">Loading categories…</p> : null}
        {categoriesQuery.error ? <p className="error">Failed to load categories: {formatApiError(categoriesQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Categories: {payload.categories.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
      </SectionCard>
      {payload ? (
        <SectionCard title="Category rules packages">
          <table>
            <thead><tr><th>Category</th><th>Templates</th><th>Main Draw</th><th>Qualifying Draw</th><th>Footprint</th><th>Mandatory</th><th>Source Templates</th><th>Status</th></tr></thead>
            <tbody>
              {payload.categories.map((category) => (
                <tr key={category.category_id}>
                  <td>{category.name} ({category.category_id})</td><td>{category.template_count}</td><td>{category.main_draw_size ?? '—'}</td><td>{category.qualification_draw_size ?? '—'}</td><td>{category.schedule_footprint_weeks ?? '—'}</td><td>{category.mandatory === null ? '—' : category.mandatory ? 'Yes' : 'No'}</td><td>{category.source_template_ids.join(', ')}</td><td>{category.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {payload.categories.map((category) => category.notes.length ? <p key={`${category.category_id}-notes`}>{category.name} notes: {category.notes.join('; ')}</p> : null)}
          <p>Category editor — planned.</p>
        </SectionCard>
      ) : null}
      <SectionCard title="Navigation">
        <p><Link to="/admin/tournament-templates">Open Tournament Templates</Link></p>
        <p><Link to="/admin/tour-seasons/season-templates">Open Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
      </SectionCard>
    </section>
  )
}
