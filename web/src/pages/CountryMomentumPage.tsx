import { PageIntro, SectionCard } from '../components/RunScopedUi'

const MOMENTUM_EXAMPLES = [
  'Golden generation',
  'Investment era',
  'College / academy boom',
  'Federation decline',
  'League expansion'
]

export function CountryMomentumPage(): JSX.Element {
  return (
    <section className="panel">
      <PageIntro
        title="Country Momentum"
        subtitle="Plan country-level era modifiers that can change talent output, style, infrastructure and competition depth over time."
      />
      <SectionCard title="Planned modifier types">
        <ul className="dashboard-help-list">
          {MOMENTUM_EXAMPLES.map((example) => (
            <li key={example}>{example}</li>
          ))}
        </ul>
      </SectionCard>
      <SectionCard title="Placeholder status">
        <p>
          This page is planned for future authoring of time-ranged modifiers such as: Francica 2030–2045: technical golden generation,
          Ameriga 2028–2040: college squash boom, Fax &amp; Finiat 2025–2038: Macky effect.
        </p>
        <p className="status">UI placeholder only in this slice; no persistence or simulation behavior is changed.</p>
      </SectionCard>
    </section>
  )
}
