import { Link, useParams } from 'react-router-dom'
import { DetailFieldGrid, DetailList } from '../components/DetailUi'
import { SeasonCalendarPreview } from './SeasonCalendarPreview'
import { SeasonRankingPointsPreview } from './SeasonRankingPointsPreview'
import { SeasonHealthPreview } from './SeasonHealthPreview'
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

      <section id="season-profile">
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
      </section>

      <SectionCard title="Season detail sections">
        <DetailList items={[
          <a key="profile" href="#season-profile">Profile / route labels</a>,
          <a key="workspace" href="#selected-season-workspace">Selected season workspace</a>,
          <a key="calendar" href="#calendar-preview">Calendar preview</a>,
          <a key="ranking" href="#ranking-points-preview">Ranking &amp; points preview</a>,
          <a key="health" href="#season-health-preview">Season health preview</a>,
          <a key="navigation" href="#season-navigation">Navigation</a>
        ]} emptyLabel="No sections." />
      </SectionCard>

      <section id="selected-season-workspace">
        <SelectedSeasonWorkspace selectedSeasonRaw={seasonLabel} />
      </section>

      <section id="calendar-preview">
        <SectionCard title="Calendar preview (read-only)">
          <SeasonCalendarPreview seasonLabelRaw={seasonLabel} />
        </SectionCard>
      </section>

      <section id="ranking-points-preview">
        <SectionCard title="Ranking & points preview (read-only)">
          <SeasonRankingPointsPreview seasonLabelRaw={seasonLabel} />
        </SectionCard>
      </section>

      <section id="season-health-preview">
        <SectionCard title="Season Health / Readiness Preview">
          <SeasonHealthPreview seasonLabelRaw={seasonLabel} />
        </SectionCard>
      </section>

      <section id="season-navigation">
        <SectionCard title="Navigation">
        <DetailList items={[
          <Link key="tour-seasons" to="/admin/tour-seasons">Tour &amp; Seasons</Link>,
          <Link key="season-registry" to="/admin/tour-seasons/season-registry">Season Registry</Link>,
          <Link key="seasons" to="/admin/seasons">Seasons</Link>,
          <Link key="season-builder" to="/admin/seasons/build">Season Builder</Link>,
          <Link key="validation" to="/admin/tour-seasons/validation">Calendar Validation</Link>,
          <Link key="compare-apply" to="/admin/tour-seasons/compare">Calendar Compare / Apply</Link>
        ]} emptyLabel="No links." />
      </SectionCard>

      {canonicalDetailRoute ? (
        <SectionCard title="Canonical route">
          <p>Canonical compact detail route: <Link to={canonicalDetailRoute}>{canonicalDetailRoute}</Link></p>
        </SectionCard>
      ) : null}

      </section>

      <SectionCard title="Related links">
        <p><Link to="/admin/seasons">Back to Seasons</Link></p>
        <p><Link to="/admin/tour-seasons/season-registry">Open Season Registry</Link></p>
        <p><Link to="/admin/tour-seasons/validation">Open Calendar Validation</Link></p>
        <p><Link to="/admin/tour-seasons/compare">Open Calendar Compare / Apply</Link></p>
        <p><Link to="/admin/seasons/build">Open Season Builder</Link></p>
      </SectionCard>
    </section>
  )
}
