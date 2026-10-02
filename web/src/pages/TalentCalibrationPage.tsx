import { useMutation, useQuery } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'

import { compareTalentCalibration, getTalentCalibration } from '../api/client'
import type { CalibrationDistribution, CandidatePotentialRange, TalentBandKey } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

const BAND_KEYS: TalentBandKey[] = ['solid_prospect', 'strong_prospect', 'elite_prospect', 'special_prospect', 'generational_talent']
const LABELS: Record<string, string> = {
  solid_prospect: 'Solid Prospect', strong_prospect: 'Strong Prospect', elite_prospect: 'Elite Prospect',
  special_prospect: 'Special Prospect', generational_talent: 'Generational Talent'
}

export function TalentCalibrationPage(): JSX.Element {
  const [inputs, setInputs] = useState({ seed: 0, sample_count: 5000 })
  const [params, setParams] = useState(inputs)
  const query = useQuery({ queryKey: ['talent-calibration', params], queryFn: () => getTalentCalibration(params), retry: false })
  const comparison = useMutation({ mutationFn: compareTalentCalibration })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    comparison.reset()
    setParams(inputs)
  }
  const [ranges, setRanges] = useState<Record<TalentBandKey, CandidatePotentialRange> | null>(null)
  useEffect(() => {
    if (query.data && ranges === null) setRanges(baselineRanges(query.data.baseline_potential_min, query.data.baseline_potential_max))
  }, [query.data, ranges])
  const reset = () => {
    if (query.data) setRanges(baselineRanges(query.data.baseline_potential_min, query.data.baseline_potential_max))
  }
  const compare = () => { if (ranges) comparison.mutate({ seed: params.seed, sample_count: params.sample_count, candidate_ranges: ranges }) }

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
      <SectionCard title="Candidate Policy Sandbox">
        <p className="status"><strong>Experimental only — this configuration is not saved and does not change prospect generation.</strong></p>
        <p className="status">It is not persisted or applied to Run generation. No candidate is canonical; current production rules remain unchanged.</p>
        {ranges ? <>
          <table aria-label="Candidate potential ranges"><thead><tr><th>Band</th><th>Potential Min</th><th>Potential Max</th></tr></thead>
            <tbody>{BAND_KEYS.map((band) => <tr key={band}><th scope="row">{LABELS[band]}</th><td><input aria-label={`${LABELS[band]} Potential Min`} type="number" min={0} max={200} value={ranges[band].potential_min} onChange={(event) => setRanges({ ...ranges, [band]: { ...ranges[band], potential_min: Number(event.target.value) } })} /></td><td><input aria-label={`${LABELS[band]} Potential Max`} type="number" min={0} max={200} value={ranges[band].potential_max} onChange={(event) => setRanges({ ...ranges, [band]: { ...ranges[band], potential_max: Number(event.target.value) } })} /></td></tr>)}</tbody>
          </table>
          <div className="button-row"><button type="button" onClick={compare} disabled={comparison.isPending}>Compare candidate</button><button type="button" onClick={reset}>Reset to baseline</button></div>
        </> : null}
        {comparison.isPending ? <p className="status">Comparing candidate…</p> : null}
        {comparison.isError ? <p className="error">Candidate comparison unavailable. Check every range and retry.</p> : null}
      </SectionCard>
      {comparison.data ? <ComparisonResults result={comparison.data} /> : null}
      <SectionCard title="Overview">
        <SummaryPills items={[{ label: 'Samples', value: query.data.sample_count }, { label: 'Seed', value: query.data.seed }, { label: 'Quality policy', value: query.data.quality_policy_id }, { label: 'Sporting-profile policy', value: query.data.sporting_profile_policy_id }]} />
        <p>Current OVR: {formatStats(query.data.current_ovr)}</p><p>Potential OVR: {formatStats(query.data.potential_ovr)}</p>
      </SectionCard>
      <SectionCard title="Quality band comparison">
        <table aria-label="Quality band comparison"><thead><tr><th>Band</th><th>Weight</th><th>Expected</th><th>Generated</th><th>Share</th><th>Δ</th><th>Min</th><th>P10</th><th>P25</th><th>Median</th><th>P75</th><th>P90</th><th>Max</th><th>Mean</th></tr></thead>
          <tbody>{query.data.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band] ?? row.band}</th><td>{pct(row.configured_rarity_weight)}</td><td>{row.expected_count.toFixed(1)}</td><td>{row.generated_count}</td><td>{pct(row.generated_share)}</td><td>{row.generated_minus_expected.toFixed(1)}</td><Cells stats={row.potential_ovr} /></tr>)}</tbody>
        </table>
      </SectionCard>
      <SectionCard title="Current OVR by quality band">
        <table aria-label="Current OVR by quality band">
          <thead><tr><th>Band</th><th>Min</th><th>P10</th><th>P25</th><th>Median</th><th>P75</th><th>P90</th><th>Max</th><th>Mean</th></tr></thead>
          <tbody>{query.data.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band] ?? row.band}</th><Cells stats={row.current_ovr} /></tr>)}</tbody>
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

function baselineRanges(minimum: number, maximum: number): Record<TalentBandKey, CandidatePotentialRange> {
  return { solid_prospect: { potential_min: minimum, potential_max: maximum }, strong_prospect: { potential_min: minimum, potential_max: maximum }, elite_prospect: { potential_min: minimum, potential_max: maximum }, special_prospect: { potential_min: minimum, potential_max: maximum }, generational_talent: { potential_min: minimum, potential_max: maximum } }
}

function ComparisonResults({ result }: { result: import('../api/types').TalentCalibrationCompareResponse }): JSX.Element {
  return <>
    <SectionCard title="Global candidate comparison">
      <SummaryPills items={[
        { label: 'Comparison seed', value: result.seed },
        { label: 'Samples', value: result.sample_count },
        { label: 'Baseline median', value: show(result.global_comparison.baseline_potential_ovr.p50) },
        { label: 'Candidate median', value: show(result.global_comparison.candidate_potential_ovr.p50) },
        { label: 'Median Δ', value: show(result.global_comparison.delta.p50) },
        { label: 'Mean Δ', value: show(result.global_comparison.delta.mean) }
      ]} />
      <table aria-label="Global candidate comparison">
        <thead><tr><th>Baseline P10</th><th>Candidate P10</th><th>Baseline P90</th><th>Candidate P90</th><th>Increased</th><th>Same</th><th>Decreased</th></tr></thead>
        <tbody><tr><td>{show(result.global_comparison.baseline_potential_ovr.p10)}</td><td>{show(result.global_comparison.candidate_potential_ovr.p10)}</td><td>{show(result.global_comparison.baseline_potential_ovr.p90)}</td><td>{show(result.global_comparison.candidate_potential_ovr.p90)}</td><td>{result.global_comparison.delta.increased}</td><td>{result.global_comparison.delta.unchanged}</td><td>{result.global_comparison.delta.decreased}</td></tr></tbody>
      </table>
      <p className="status">Candidate configuration fingerprint: <code>{result.candidate_sandbox_configuration_fingerprint}</code></p>
    </SectionCard>
    <SectionCard title="Candidate comparison">
      <table aria-label="Candidate comparison"><thead><tr><th>Band</th><th>Candidate range</th><th>Baseline median</th><th>Candidate median</th><th>Median Δ</th><th>Baseline P10</th><th>Candidate P10</th><th>Baseline P90</th><th>Candidate P90</th><th>Mean Δ</th><th>Increased</th><th>Same</th><th>Decreased</th></tr></thead>
        <tbody>{result.bands.map((row) => <tr key={row.band}><th scope="row">{LABELS[row.band]}</th>{row.generated_count === 0 ? <td colSpan={12}>No generated samples for this seed/sample size</td> : <><td>{row.candidate_range.potential_min}–{row.candidate_range.potential_max}</td><td>{show(row.baseline_potential_ovr.p50)}</td><td>{show(row.candidate_potential_ovr.p50)}</td><td>{show(row.delta.p50)}</td><td>{show(row.baseline_potential_ovr.p10)}</td><td>{show(row.candidate_potential_ovr.p10)}</td><td>{show(row.baseline_potential_ovr.p90)}</td><td>{show(row.candidate_potential_ovr.p90)}</td><td>{show(row.delta.mean)}</td><td>{row.delta.increased}</td><td>{row.delta.unchanged}</td><td>{row.delta.decreased}</td></>}</tr>)}</tbody>
      </table>
    </SectionCard>
    <SectionCard title="Baseline and candidate histograms">
      <p className="status">Shared 10-point display bins are not quality thresholds.</p>
      <table aria-label="Candidate histogram comparison"><thead><tr><th>Band</th><th>Range</th><th>Baseline count</th><th>Candidate count</th></tr></thead><tbody>{result.bands.flatMap((row) => row.baseline_histogram.map((bin, index) => <tr key={`${row.band}-${bin.lower}`}><th scope="row">{LABELS[row.band]}</th><td>{bin.lower}–{bin.upper}</td><td>{bin.count}</td><td>{row.candidate_histogram[index].count}</td></tr>))}</tbody></table>
    </SectionCard>
    <SectionCard title="Adjacent-band overlap">
      <p>Overlap measures how much the sampled Potential OVR distributions occupy the same histogram bins. It is diagnostic only; the Lab does not decide what overlap level is desirable.</p>
      <table aria-label="Adjacent-band overlap"><thead><tr><th>Pair</th><th>Baseline overlap</th><th>Candidate overlap</th><th>Δ</th></tr></thead><tbody>{result.adjacent_overlaps.map((row) => <tr key={row.lower_band}><th scope="row">{shortLabel(row.lower_band)} ↔ {shortLabel(row.upper_band)}</th><td>{show(row.baseline)}</td><td>{show(row.candidate)}</td><td>{row.baseline === null || row.candidate === null ? '—' : show(row.candidate - row.baseline)}</td></tr>)}</tbody></table>
    </SectionCard>
  </>
}
function shortLabel(band: TalentBandKey): string { return LABELS[band].replace(' Prospect', '').replace(' Talent', '') }
