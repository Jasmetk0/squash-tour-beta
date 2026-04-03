import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { ApiError, getTalentClassPreview, getTalentClassSummary } from '../api/client'
import type { TalentClassPreviewCountry, TalentClassSummaryCountry } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

type SingleYearSort = 'planned_desc' | 'elite_desc' | 'country_asc'
type SummarySort = 'total_desc' | 'top_rate_desc' | 'country_asc'

export function TalentPreviewPage(): JSX.Element {
  const [seed, setSeed] = useState(123)
  const [year, setYear] = useState(2030)
  const [spanYears, setSpanYears] = useState(10)
  const [countryFilter, setCountryFilter] = useState('')
  const [singleSort, setSingleSort] = useState<SingleYearSort>('planned_desc')
  const [summarySort, setSummarySort] = useState<SummarySort>('total_desc')

  const previewQuery = useQuery({
    queryKey: ['talent-class-preview', year, seed],
    queryFn: () => getTalentClassPreview({ year, seed }),
    retry: false
  })
  const summaryQuery = useQuery({
    queryKey: ['talent-class-summary', year, spanYears, seed],
    queryFn: () => getTalentClassSummary({ year_start: year, years: spanYears, seed }),
    retry: false
  })

  const filteredSingleYear = useMemo(() => {
    const filter = countryFilter.trim().toLowerCase()
    const rows = (previewQuery.data?.countries ?? []).filter(
      (item) => !filter || item.country_code.toLowerCase().includes(filter) || item.country_name.toLowerCase().includes(filter)
    )
    return sortSingleYear(rows, singleSort)
  }, [countryFilter, previewQuery.data?.countries, singleSort])

  const filteredSummary = useMemo(() => {
    const filter = countryFilter.trim().toLowerCase()
    const rows = (summaryQuery.data?.countries ?? []).filter(
      (item) => !filter || item.country_code.toLowerCase().includes(filter) || item.country_name.toLowerCase().includes(filter)
    )
    return sortSummary(rows, summarySort)
  }, [countryFilter, summaryQuery.data?.countries, summarySort])

  return (
    <section className="panel">
      <PageIntro
        title="Talent Class Preview"
        subtitle="Read-only diagnostics over current countries config and deterministic annual talent planner."
      />

      <SectionCard title="Preview controls">
        <div className="grid">
          <label>
            Seed
            <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </label>
          <label>
            Preview year
            <input type="number" min={1900} value={year} onChange={(event) => setYear(Number(event.target.value))} />
          </label>
          <label>
            Multi-year span
            <input type="number" min={1} max={100} value={spanYears} onChange={(event) => setSpanYears(Number(event.target.value))} />
          </label>
          <label>
            Country filter
            <input value={countryFilter} onChange={(event) => setCountryFilter(event.target.value)} placeholder="Code or name" />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Single-year preview">
        {previewQuery.isLoading ? <p className="status">Loading year preview…</p> : null}
        {previewQuery.isError ? <p className="error">Preview unavailable: {formatApiError(previewQuery.error)}</p> : null}
        {previewQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Year', value: previewQuery.data.year },
                { label: 'Seed', value: previewQuery.data.seed },
                { label: 'Total talents', value: previewQuery.data.total_talents },
                { label: 'Country count', value: previewQuery.data.country_count },
                { label: 'Dataset status', value: previewQuery.data.dataset_status ?? 'unset' }
              ]}
            />
            <p className="status">Source path: {previewQuery.data.source_path}</p>
            <label>
              Sort
              <select value={singleSort} onChange={(event) => setSingleSort(event.target.value as SingleYearSort)}>
                <option value="planned_desc">Planned count (desc)</option>
                <option value="elite_desc">Top-band count (desc)</option>
                <option value="country_asc">Country (A-Z)</option>
              </select>
            </label>
            <table aria-label="Talent preview single-year table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Planned</th>
                  <th>Solid</th>
                  <th>Strong</th>
                  <th>Elite</th>
                  <th>Special</th>
                  <th>Generational</th>
                  <th>Top-band weight</th>
                  <th>Bias</th>
                </tr>
              </thead>
              <tbody>
                {filteredSingleYear.map((item) => (
                  <tr key={item.country_code}>
                    <td>{item.country_code}</td>
                    <td>{item.country_name}</td>
                    <td>{item.planned_count}</td>
                    <td>{item.actual_band_counts.solid_prospect ?? 0}</td>
                    <td>{item.actual_band_counts.strong_prospect ?? 0}</td>
                    <td>{item.actual_band_counts.elite_prospect ?? 0}</td>
                    <td>{item.actual_band_counts.special_prospect ?? 0}</td>
                    <td>{item.actual_band_counts.generational_talent ?? 0}</td>
                    <td>{formatPercent(topBandWeight(item))}</td>
                    <td>
                      P {item.bias_profile.professionalism_tendency?.toFixed(2) ?? '0.00'} / T{' '}
                      {item.bias_profile.technical_vs_physical_lean?.toFixed(2) ?? '0.00'} / M{' '}
                      {item.bias_profile.mental_sharpness_tendency?.toFixed(2) ?? '0.00'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Multi-year summary">
        {summaryQuery.isLoading ? <p className="status">Loading multi-year summary…</p> : null}
        {summaryQuery.isError ? <p className="error">Summary unavailable: {formatApiError(summaryQuery.error)}</p> : null}
        {summaryQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Years', value: summaryQuery.data.years },
                { label: 'Total talents', value: summaryQuery.data.total_talents_across_span },
                { label: 'Avg per year', value: summaryQuery.data.average_total_talents_per_year.toFixed(2) }
              ]}
            />
            <p className="status">
              Global band totals: solid {summaryQuery.data.global_band_totals.solid_prospect ?? 0}, strong{' '}
              {summaryQuery.data.global_band_totals.strong_prospect ?? 0}, elite{' '}
              {summaryQuery.data.global_band_totals.elite_prospect ?? 0}, special{' '}
              {summaryQuery.data.global_band_totals.special_prospect ?? 0}, generational{' '}
              {summaryQuery.data.global_band_totals.generational_talent ?? 0}
            </p>
            <label>
              Sort
              <select value={summarySort} onChange={(event) => setSummarySort(event.target.value as SummarySort)}>
                <option value="total_desc">Total talents (desc)</option>
                <option value="top_rate_desc">Top-band rate (desc)</option>
                <option value="country_asc">Country (A-Z)</option>
              </select>
            </label>
            <table aria-label="Talent preview multi-year summary table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Total</th>
                  <th>Avg/year</th>
                  <th>Elite</th>
                  <th>Special</th>
                  <th>Generational</th>
                  <th>Avg top-band rate</th>
                  <th>Badge</th>
                </tr>
              </thead>
              <tbody>
                {filteredSummary.map((item) => (
                  <tr key={item.country_code}>
                    <td>{item.country_code}</td>
                    <td>{item.country_name}</td>
                    <td>{item.total_planned_talents}</td>
                    <td>{item.average_talents_per_year.toFixed(2)}</td>
                    <td>{item.total_elite_count}</td>
                    <td>{item.total_special_count}</td>
                    <td>{item.total_generational_count}</td>
                    <td>{formatPercent(item.average_top_band_rate)}</td>
                    <td>{item.total_generational_count > 0 ? '⭐ Generational' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}

function topBandWeight(country: TalentClassPreviewCountry): number {
  return (
    (country.quality_weights.elite_prospect ?? 0) +
    (country.quality_weights.special_prospect ?? 0) +
    (country.quality_weights.generational_talent ?? 0)
  )
}

function sortSingleYear(items: TalentClassPreviewCountry[], mode: SingleYearSort): TalentClassPreviewCountry[] {
  const clone = [...items]
  if (mode === 'country_asc') return clone.sort((a, b) => a.country_code.localeCompare(b.country_code))
  if (mode === 'elite_desc') {
    return clone.sort((a, b) => {
      const left = (a.actual_band_counts.elite_prospect ?? 0) + (a.actual_band_counts.special_prospect ?? 0) + (a.actual_band_counts.generational_talent ?? 0)
      const right = (b.actual_band_counts.elite_prospect ?? 0) + (b.actual_band_counts.special_prospect ?? 0) + (b.actual_band_counts.generational_talent ?? 0)
      return right - left || a.country_code.localeCompare(b.country_code)
    })
  }
  return clone.sort((a, b) => b.planned_count - a.planned_count || a.country_code.localeCompare(b.country_code))
}

function sortSummary(items: TalentClassSummaryCountry[], mode: SummarySort): TalentClassSummaryCountry[] {
  const clone = [...items]
  if (mode === 'country_asc') return clone.sort((a, b) => a.country_code.localeCompare(b.country_code))
  if (mode === 'top_rate_desc') {
    return clone.sort((a, b) => b.average_top_band_rate - a.average_top_band_rate || a.country_code.localeCompare(b.country_code))
  }
  return clone.sort((a, b) => b.total_planned_talents - a.total_planned_talents || a.country_code.localeCompare(b.country_code))
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatApiError(error: unknown): string {
  if (error instanceof ApiError) return `${error.status} ${error.message}`
  return String(error)
}
