import { useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'

import { getTalentCalibration } from '../api/client'
import type { CalibrationDistribution } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

const LABELS: Record<string, string> = {
  solid_prospect: 'Solid Prospect', strong_prospect: 'Strong Prospect', elite_prospect: 'Elite Prospect',
  special_prospect: 'Special Prospect', generational_talent: 'Generational Talent'
}

export function TalentCalibrationPage(): JSX.Element {
  const [inputs, setInputs] = useState({ seed: 0, sample_count: 5000 })
  const [params, setParams] = useState(inputs)
  const query = useQuery({ queryKey: ['talent-calibration', params], queryFn: () => getTalentCalibration(params), retry: false })
  const submit = (event: FormEvent) => { event.preventDefault(); setParams(inputs) }

  return <section className="panel">
    <PageIntro title="Talent Calibration Lab" subtitle="Inspect the current deterministic prospect distributions before making future calibration decisions." />
    <SectionCard title="Diagnostic boundary">
      <p className="status"><strong>Calibration Lab is diagnostic only. It does not change generation or Run state.</strong></p>
      <p className="status">Quality Band and Potential OVR are currently separate authorities.</p>
    </SectionCard>
    <SectionCard title="Controls">
      <form onSubmit={submit} className="grid">
        <label>Seed<input aria-label="Seed" type="number" value={inputs.seed} onChange={(e) => setInputs({ ...inputs, seed: Number(e.target.value) })} /></label>
        <label>Sample count<input aria-label="Sample count" type="number" min={1} max={50000} value={inputs.sample_count} onChange={(e) => setInputs({ ...inputs, sample_count: Number(e.target.value) })} /></label>
        <button type="submit">Run calibration</button>
      </form>
    </SectionCard>
    {query.isLoading ? <p className="status">Loading calibration…</p> : null}
    {query.isError ? <p className="error">Calibration unavailable. Check the inputs and retry.</p> : null}
    {query.data ? <>
      <SectionCard title="Overview">
        <SummaryPills items={[{ label: 'Samples', value: query.data.sample_count }, { label: 'Seed', value: query.data.seed }, { label: 'Quality policy', value: query.data.quality_policy_id }, { label: 'Sporting-profile policy', value: query.data.sporting_profile_policy_id }]} />
        <p>Current OVR: {formatStats(query.data.current_ovr)}</p><p>Potential OVR: {formatStats(query.data.potential_ovr)}</p>
      </SectionCard>
      <SectionCard title="Quality band comparison">
        <table aria-label="Quality band comparison"><thead><tr><th>Band</th><th>Weight</th><th>Expected</th><th>Generated</th><th>Share</th><th>Δ</th><th>Min</th><th>P10</th><th>P25</th><th>Median</th><th>P75</th><th>P90</th><th>Max</th><th>Mean</th></tr></thead>
          <tbody>{query.data.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band] ?? row.band}</th><td>{pct(row.configured_rarity_weight)}</td><td>{row.expected_count.toFixed(1)}</td><td>{row.generated_count}</td><td>{pct(row.generated_share)}</td><td>{row.generated_minus_expected.toFixed(1)}</td><Cells stats={row.potential_ovr} /></tr>)}</tbody>
        </table>
      </SectionCard>
      <SectionCard title="Development timing">
        <table aria-label="Development timing"><thead><tr><th>Band</th><th>Early Bloomer</th><th>Standard</th><th>Late Bloomer</th></tr></thead><tbody>{query.data.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band] ?? row.band}</th><td>{row.development_timing_counts['Early Bloomer']}</td><td>{row.development_timing_counts.Standard}</td><td>{row.development_timing_counts['Late Bloomer']}</td></tr>)}</tbody></table>
      </SectionCard>
      <SectionCard title="Potential distribution (10-point bins)">
        <p className="status">Bins are display aids on the 0–200 scale, not quality thresholds.</p>
        <table aria-label="Potential histogram"><thead><tr><th>Band</th>{query.data.bands[0]?.potential_histogram.map((bin) => <th key={bin.lower}>{bin.lower}–{bin.upper}</th>)}</tr></thead><tbody>{query.data.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band] ?? row.band}</th>{row.potential_histogram.map((bin) => <td key={bin.lower}>{bin.count}</td>)}</tr>)}</tbody></table>
      </SectionCard>
    </> : null}
  </section>
}

function Cells({ stats }: { stats: CalibrationDistribution }): JSX.Element { return <><td>{show(stats.minimum)}</td><td>{show(stats.p10)}</td><td>{show(stats.p25)}</td><td>{show(stats.p50)}</td><td>{show(stats.p75)}</td><td>{show(stats.p90)}</td><td>{show(stats.maximum)}</td><td>{show(stats.mean)}</td></> }
function show(value: number | null): string { return value === null ? '—' : value.toFixed(1) }
function pct(value: number): string { return `${(value * 100).toFixed(2)}%` }
function formatStats(stats: CalibrationDistribution): string { return `min ${show(stats.minimum)}, mean ${show(stats.mean)}, median ${show(stats.p50)}, max ${show(stats.maximum)}` }
