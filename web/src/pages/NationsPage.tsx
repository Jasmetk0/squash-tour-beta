import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { getRunNationDetail, listRunNations } from '../api/client'
import { CurrentContextStrip, PageIntro, SectionCard } from '../components/RunScopedUi'

const SORT_OPTIONS = ['total_players_desc', 'avg_overall_desc', 'top_band_desc']

export function NationsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('total_players_desc')
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)

  const queryParams = useMemo(
    () => ({ search: search.trim() || undefined, sort, limit: 300, offset: 0 }),
    [search, sort]
  )

  const nationsQuery = useQuery({
    queryKey: ['run-nations', runId, queryParams],
    queryFn: () => listRunNations(runId, queryParams),
    enabled: Boolean(runId)
  })

  const detailQuery = useQuery({
    queryKey: ['run-nation-detail', runId, selectedCountryCode],
    queryFn: () => getRunNationDetail(runId, selectedCountryCode ?? ''),
    enabled: Boolean(runId && selectedCountryCode)
  })

  return (
    <section className="panel">
      <PageIntro title="Run Nations Dashboard" subtitle="Country strength diagnostics over the current run player pool." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Visible nations', value: nationsQuery.data?.nations.length ?? '—' },
          { label: 'Total filtered', value: nationsQuery.data?.total ?? '—' }
        ]}
      />

      <SectionCard title="Filters">
        <div className="form-grid">
          <label>
            Search country
            <input value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label>
            Sort
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              {SORT_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Nations">
        {nationsQuery.isLoading ? <p className="status">Loading nations…</p> : null}
        {nationsQuery.error ? <p className="error">Failed to load nations: {String(nationsQuery.error)}</p> : null}
        {!nationsQuery.isLoading && !nationsQuery.error && nationsQuery.data ? (
          <table>
            <thead>
              <tr>
                <th>Country</th>
                <th>Total players</th>
                <th>Avg overall</th>
                <th>Avg age</th>
                <th>Top-band count</th>
                <th>Carryover</th>
                <th>Intake</th>
                <th>Manual</th>
                <th>Top player</th>
              </tr>
            </thead>
            <tbody>
              {nationsQuery.data.nations.map((nation) => (
                <tr key={nation.country_code}>
                  <td>
                    <button type="button" onClick={() => setSelectedCountryCode(nation.country_code)}>
                      {nation.country_code} {nation.country_name ? `— ${nation.country_name}` : ''}
                    </button>
                  </td>
                  <td>{nation.total_players}</td>
                  <td>{nation.average_overall.toFixed(2)}</td>
                  <td>{nation.average_age.toFixed(2)}</td>
                  <td>{nation.top_band_count}</td>
                  <td>{nation.rollover_carried_count}</td>
                  <td>{nation.planner_generated_count}</td>
                  <td>{nation.manual_override_count}</td>
                  <td>
                    {nation.top_player_name ?? '—'} {nation.top_player_overall ? `(${nation.top_player_overall})` : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>

      <SectionCard title="Nation detail">
        {!selectedCountryCode ? <p className="status">Select a country from the table to inspect detail.</p> : null}
        {selectedCountryCode && detailQuery.isLoading ? <p className="status">Loading nation detail…</p> : null}
        {selectedCountryCode && detailQuery.error ? <p className="error">Failed to load detail: {String(detailQuery.error)}</p> : null}
        {selectedCountryCode && detailQuery.data ? (
          <>
            <p>
              <strong>{detailQuery.data.country_code}</strong> {detailQuery.data.country_name ? `— ${detailQuery.data.country_name}` : ''}
            </p>
            <p>
              Source mix: carryover {detailQuery.data.rollover_carried_count} | intake {detailQuery.data.planner_generated_count} | manual{' '}
              {detailQuery.data.manual_override_count}
            </p>
            <p>
              Avg visible stats: tech {detailQuery.data.average_visible_stats.technique.toFixed(2)} | mov{' '}
              {detailQuery.data.average_visible_stats.movement.toFixed(2)} | phys {detailQuery.data.average_visible_stats.physical.toFixed(2)} |
              ment {detailQuery.data.average_visible_stats.mental.toFixed(2)}
            </p>
            <h4>Band distribution</h4>
            <ul>
              {detailQuery.data.band_distribution.map((item) => (
                <li key={item.band}>
                  {item.band}: {item.count}
                </li>
              ))}
            </ul>
            <h4>Top players</h4>
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Age</th>
                  <th>Overall</th>
                  <th>Source</th>
                  <th>Band</th>
                </tr>
              </thead>
              <tbody>
                {detailQuery.data.top_players.map((player) => (
                  <tr key={player.player_id}>
                    <td>
                      {player.name} ({player.player_id})
                    </td>
                    <td>{player.age}</td>
                    <td>{player.overall}</td>
                    <td>{player.source_type}</td>
                    <td>{player.quality_band ?? '—'}</td>
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
