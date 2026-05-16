import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { getAdminRankingTable, getViewerRankingTable } from '../api/client'
import type { RankingTableQueryParams, RankingTableResponse, RankingTableRow, RankingTableType } from '../api/types'
import { MetadataList, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type RankingControlsState = {
  season: string
  tableType: RankingTableType
  limit: string
  countryCode: string
  search: string
  includeZeroPoints: boolean
  minPoints: string
}

const defaultControls: RankingControlsState = {
  season: '2000/2001',
  tableType: 'ranking',
  limit: '100',
  countryCode: '',
  search: '',
  includeZeroPoints: true,
  minPoints: ''
}

function buildParams(controls: RankingControlsState): RankingTableQueryParams {
  return {
    table_type: controls.tableType,
    limit: controls.limit.trim() ? Number(controls.limit) : undefined,
    country_code: controls.countryCode.trim() || undefined,
    search: controls.search.trim() || undefined,
    include_zero_points: controls.includeZeroPoints,
    min_points: controls.minPoints.trim() ? Number(controls.minPoints) : undefined
  }
}

export function AdminRankingTablesSection(): JSX.Element {
  return <RankingTablePanel mode="admin" title="Ranking / Race Tables" />
}

export function ViewerRankingsReadOnlyPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>MSA Rankings</h2>
        <p className="subtitle">Read-only ranking and race tables from active season points.</p>
      </div>
      <RankingTablePanel mode="viewer" title="Current Tables" />
    </section>
  )
}

function RankingTablePanel({ mode, title }: { mode: 'admin' | 'viewer'; title: string }): JSX.Element {
  const [controls, setControls] = useState<RankingControlsState>(defaultControls)
  const [submitted, setSubmitted] = useState(defaultControls)
  const isAdmin = mode === 'admin'
  const query = useQuery({
    queryKey: [mode, 'ranking-table', submitted],
    queryFn: () => isAdmin ? getAdminRankingTable(submitted.season, buildParams(submitted)) : getViewerRankingTable(submitted.season, buildParams(submitted)),
    retry: false
  })

  const table = query.data ?? null
  const leader = table?.rows.find((row) => row.player_id === table.summary.leader_player_id) ?? table?.rows[0] ?? null

  return (
    <SectionCard title={title}>
      <p className="status">
        {isAdmin
          ? 'This table is derived from active season player points. Rolling 61-week ranking, best-N selection, weekly snapshots, and movement are not implemented yet.'
          : 'Current ranking table from active season points. Historical weekly ranking snapshots are not available yet.'}
      </p>
      <div className="grid">
        <label>Season<input value={controls.season} onChange={(event) => setControls((current) => ({ ...current, season: event.target.value }))} /></label>
        <label>Table type<select value={controls.tableType} onChange={(event) => setControls((current) => ({ ...current, tableType: event.target.value as RankingTableType }))}>
          <option value="ranking">Ranking</option>
          <option value="race">Race</option>
        </select></label>
        <label>Top N<input type="number" min="1" value={controls.limit} onChange={(event) => setControls((current) => ({ ...current, limit: event.target.value }))} /></label>
        <label>Country filter<input value={controls.countryCode} onChange={(event) => setControls((current) => ({ ...current, countryCode: event.target.value.toUpperCase() }))} placeholder="EGY" /></label>
        <label>Search<input value={controls.search} onChange={(event) => setControls((current) => ({ ...current, search: event.target.value }))} placeholder="Player name or ID" /></label>
        <label>Min points<input type="number" min="0" value={controls.minPoints} onChange={(event) => setControls((current) => ({ ...current, minPoints: event.target.value }))} /></label>
        <label><input type="checkbox" checked={controls.includeZeroPoints} onChange={(event) => setControls((current) => ({ ...current, includeZeroPoints: event.target.checked }))} /> Include zero points</label>
      </div>
      <div className="button-row">
        <button type="button" onClick={() => setSubmitted(controls)} disabled={query.isFetching}>Load table</button>
      </div>
      {query.isError ? <p role="alert" className="error">{formatApiError(query.error)}</p> : null}
      {table ? <RankingTableSummaryCards table={table} leaderName={leader?.player_name ?? null} /> : <p className="status">Load a season ranking or race table.</p>}
      {table ? <RankingMetadata table={table} /> : null}
      {table ? <RankingRowsTable rows={table.rows} /> : null}
    </SectionCard>
  )
}

function RankingTableSummaryCards({ table, leaderName }: { table: RankingTableResponse; leaderName: string | null }): JSX.Element {
  return <SummaryPills items={[
    { label: 'Leader', value: leaderName ?? table.summary.leader_player_id ?? '—' },
    { label: 'Leader points', value: table.summary.leader_points ?? '—' },
    { label: 'Ranked players', value: table.summary.ranked_player_count },
    { label: 'Displayed players', value: table.summary.player_count },
    { label: 'Countries represented', value: table.summary.countries_represented },
    { label: 'Zero point players', value: table.summary.zero_point_players },
    { label: 'Rolling ranking', value: table.summary.rolling_ranking_implemented ? 'Implemented' : 'Not implemented' },
    { label: 'Best-N', value: table.summary.best_n_implemented ? 'Implemented' : 'Not implemented' }
  ]} />
}

function RankingMetadata({ table }: { table: RankingTableResponse }): JSX.Element {
  return <>
    <MetadataList items={[
      { label: 'Source', value: table.metadata.source },
      { label: 'Ranking basis', value: table.metadata.ranking_basis },
      { label: 'Active players fingerprint', value: table.metadata.active_players_fingerprint },
      { label: 'Generated fingerprint', value: table.metadata.generated_fingerprint }
    ]} />
    {table.validation_warnings.length ? <ul>{table.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
  </>
}

function RankingRowsTable({ rows }: { rows: RankingTableRow[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Ranking race table">
      <thead><tr><th>Rank</th><th>Dense rank</th><th>Player</th><th>Country</th><th>Age</th><th>Career stage</th><th>Ranking points</th><th>Race points</th><th>Current ability</th><th>Potential tier</th><th>Archetype</th><th>Movement</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.player_id}><td>{row.rank}</td><td>{row.dense_rank}</td><td>{row.player_name}</td><td>{row.country_code}</td><td>{row.age_years_at_season_start}</td><td>{row.career_stage}</td><td>{row.ranking_points}</td><td>{row.race_points}</td><td>{row.current_ability}</td><td>{row.potential_tier}</td><td>{row.archetype}</td><td>{row.movement ?? '—'}</td></tr>)}</tbody>
    </table>
    {!rows.length ? <p className="status">No players match the selected ranking filters.</p> : null}
  </div>
}
