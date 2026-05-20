import { Link, useParams } from 'react-router-dom'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { SeasonCalendarPreview } from './SeasonCalendarPreview'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { safeToCompactSeasonLabel, safeToLongSeasonLabel } from '../utils/seasonLabels'
import { SelectedSeasonWorkspace } from './SelectedSeasonWorkspace'

export function AdminSeasonDetailPage(): JSX.Element {
  const { seasonLabel: seasonLabelParam = '' } = useParams()
  const seasonLabel = decodeURIComponent(seasonLabelParam)
  const compactLabel = safeToCompactSeasonLabel(seasonLabel)
  const legacyLabel = safeToLongSeasonLabel(seasonLabel)
  const canonicalDetailRoute = compactLabel ? `/admin/seasons/detail/${encodeURIComponent(compactLabel)}` : null

  return (
    <section className="panel">
      <PageIntro
        title="Concrete Season"
        subtitle="Read-only season profile and operational status preview."
      />

      <SectionCard title="Read-only concrete season profile">
        <p>This page does not create, build, simulate, or edit the season.</p>
        <p>Concrete season editor is planned.</p>
        <p>Build from template is planned.</p>
        <p>Compare/apply workflow is planned.</p>
        <DetailFieldGrid fields={[
          { label: 'Raw route label', value: seasonLabelParam },
          { label: 'Decoded route label', value: seasonLabel || 'Unavailable' },
          ...(compactLabel ? [{ label: 'Compact label', value: compactLabel }] : []),
          ...(legacyLabel ? [{ label: 'Legacy label', value: legacyLabel }] : [])
        ]} />
      </SectionCard>

      <SectionCard title="Navigation">
        <DetailList items={[
          <Link key="tour-seasons" to="/admin/tour-seasons">Tour &amp; Seasons</Link>,
          <Link key="season-registry" to="/admin/tour-seasons/season-registry">Season Registry</Link>,
          <Link key="seasons" to="/admin/seasons">Seasons</Link>,
          <Link key="validation" to="/admin/tour-seasons/validation">Calendar Validation</Link>,
          <Link key="compare-apply" to="/admin/tour-seasons/compare">Calendar Compare / Apply</Link>
        ]} emptyLabel="No links." />
      </SectionCard>

      {canonicalDetailRoute ? (
        <SectionCard title="Canonical route">
          <p>Canonical compact detail route: <Link to={canonicalDetailRoute}>{canonicalDetailRoute}</Link></p>
        </SectionCard>
      ) : null}

      <SectionCard title="Related links">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
      </SectionCard>

      <SectionCard title="Calendar preview (read-only)">
        <SeasonCalendarPreview seasonLabelRaw={seasonLabel} />
      </SectionCard>

      <SelectedSeasonWorkspace selectedSeasonRaw={seasonLabel} />
    </section>
  )
}
