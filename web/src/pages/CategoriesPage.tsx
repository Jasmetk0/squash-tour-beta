import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getCategories } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { tournamentCategoryGroups } from '../tour/tournamentCategoryCatalog'
import type { TournamentCategoryCatalogEntry } from '../tour/tournamentCategoryCatalog'
import { formatApiError } from '../utils/apiErrors'

function CategorySticker({ category }: { category: TournamentCategoryCatalogEntry }): JSX.Element {
  const stickerText = [category.stickerSymbol, category.stickerLabel].filter(Boolean).join(' ')

  return (
    <span
      className={`category-sticker category-sticker--${category.visualTone}`}
      aria-label={`${category.name} category sticker: ${stickerText}`}
    >
      {category.stickerSymbol ? <span aria-hidden="true">{category.stickerSymbol}</span> : null}
      <span>{category.stickerLabel}</span>
    </span>
  )
}

export function AdminTourSeasonsCategoriesPage(): JSX.Element {
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories, retry: false })
  const payload = categoriesQuery.data

  return (
    <section className="panel">
      <PageIntro
        title="Categories"
        subtitle="Canonical tournament category identity catalog for the MSA/FAX squash world."
      />
      <SectionCard title="Canonical category identity catalog">
        <p>
          These are stable tournament category identities. Season-specific points, prize money, draw sizes, qualification formats,
          and ranking rules will be defined later through season rules and templates.
        </p>
        <p className="status">
          This catalog intentionally stores display identity only: code, name, tour level, ordering, sticker metadata, and a short description.
        </p>
      </SectionCard>

      <SectionCard title="Category stickers by tour level">
        <div className="category-catalog" aria-label="Canonical tournament category catalog">
          {tournamentCategoryGroups.map((group) => (
            <section className="category-catalog__group" key={group.tourLevel} aria-labelledby={`category-group-${group.tourLevel}`}>
              <h3 id={`category-group-${group.tourLevel}`}>{group.tourLevelName}</h3>
              <div className="category-catalog__cards">
                {group.categories.map((category) => (
                  <article className="category-catalog-card" key={category.code} aria-label={`${category.name} category`}>
                    <div className="category-catalog-card__header">
                      <CategorySticker category={category} />
                      <span className="category-catalog-card__code">{category.code}</span>
                    </div>
                    <h4>{category.name}</h4>
                    <p>{category.shortDescription}</p>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Read-only derived backend preview">
        <ul className="dashboard-help-list">
          <li>Existing backend category previews remain read-only and derived from current tournament template config.</li>
          <li>Full category editor/versioning is planned.</li>
          <li>Existing operational tooling remains in <Link to="/admin/tournament-templates">/admin/tournament-templates</Link>.</li>
          <li>Derived backend values may be null when source templates contain mixed values.</li>
        </ul>
      </SectionCard>
      <SectionCard title="Backend preview summary">
        {categoriesQuery.isLoading ? <p className="status">Loading categories…</p> : null}
        {categoriesQuery.error ? <p className="error">Failed to load categories: {formatApiError(categoriesQuery.error)}</p> : null}
        {payload ? <ul className="dashboard-help-list"><li>Derived backend categories: {payload.categories.length}</li><li>Source path: {payload.source_path ?? '—'}</li><li>Status: {payload.status}</li></ul> : null}
      </SectionCard>
      {payload ? (
        <SectionCard title="Derived category rules packages">
          <table>
            <thead><tr><th>Category</th><th>Templates</th><th>Main Draw</th><th>Qualifying Draw</th><th>Footprint</th><th>Mandatory</th><th>Source Templates</th><th>Status</th></tr></thead>
            <tbody>
              {payload.categories.map((category) => (
                <tr key={category.category_id}>
                  <td><Link to={`/admin/tour-seasons/categories/${category.category_id}`}>{category.name} ({category.category_id})</Link></td><td>{category.template_count}</td><td>{category.main_draw_size ?? '—'}</td><td>{category.qualification_draw_size ?? '—'}</td><td>{category.schedule_footprint_weeks ?? '—'}</td><td>{category.mandatory === null ? '—' : category.mandatory ? 'Yes' : 'No'}</td><td>{category.source_template_ids.join(', ')}</td><td>{category.status}</td>
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
