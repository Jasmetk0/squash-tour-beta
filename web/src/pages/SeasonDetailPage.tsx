import { Link, useParams } from 'react-router-dom'

import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { SelectedSeasonWorkspace } from './SelectedSeasonWorkspace'

export function AdminSeasonDetailPage(): JSX.Element {
  const { seasonLabel: seasonLabelParam = '' } = useParams()
  const seasonLabel = decodeURIComponent(seasonLabelParam)

  return (
    <section className="panel">
      <PageIntro
        title="Concrete Season"
        subtitle="Read-only season profile and operational status preview."
      />

      <SectionCard title="Navigation">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
      </SectionCard>

      <SectionCard title="Read-only status">
        <p>This page is read-only. Concrete season editor, build from template, and compare/apply workflows are planned.</p>
      </SectionCard>

      <SelectedSeasonWorkspace selectedSeasonRaw={seasonLabel} />
    </section>
  )
}
