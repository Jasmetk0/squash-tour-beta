import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { generateAdminRankingSnapshot, getAdminPointBreakdown, getAdminRankingSnapshot, getAdminRankingTable, getViewerPointBreakdown, getViewerRankingSnapshot, getViewerRankingTable } from '../api/client'
import type { PlayerPointBreakdownEntry, PlayerPointBreakdownQueryParams, PlayerPointBreakdownResponse, PlayerPointBreakdownSummaryRow, PointBreakdownTableType, RankingSnapshotRow, WeeklyRankingSnapshotResult, RankingTableQueryParams, RankingTableResponse, RankingTableRow, RankingTableType } from '../api/types'
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
  return <>
    <RankingTablePanel mode="admin" title="Ranking / Race Tables" />
    <PointBreakdownPanel mode="admin" title="Player Point Breakdown" />
    <WeeklyRankingSnapshotPanel mode="admin" />
  </>
}

export function ViewerRankingsReadOnlyPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>MSA Rankings</h2>
        <p className="subtitle">Read-only ranking and race tables from active season points.</p>
      </div>
      <RankingTablePanel mode="viewer" title="Current Tables" />
      <WeeklyRankingSnapshotPanel mode="viewer" />
      <PointBreakdownPanel mode="viewer" title="Point Breakdown" />
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
          : 'Current ranking table from active season points. Historical weekly ranking snapshots are read-only publications below.'}
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

type PointBreakdownControlsState = {
  season: string
  playerId: string
  search: string
  countryCode: string
  appliedOnly: boolean
  includeZeroPointAwards: boolean
  tableType: PointBreakdownTableType
  limit: string
}

const defaultPointBreakdownControls: PointBreakdownControlsState = {
  season: '2000/2001',
  playerId: '',
  search: '',
  countryCode: '',
  appliedOnly: true,
  includeZeroPointAwards: false,
  tableType: 'both',
  limit: '100'
}

function buildPointBreakdownParams(controls: PointBreakdownControlsState): PlayerPointBreakdownQueryParams {
  return {
    player_id: controls.playerId.trim() || undefined,
    search: controls.search.trim() || undefined,
    country_code: controls.countryCode.trim() || undefined,
    applied_only: controls.appliedOnly,
    table_type: controls.tableType,
    limit: controls.limit.trim() ? Number(controls.limit) : undefined,
    include_zero_point_awards: controls.includeZeroPointAwards
  }
}

function PointBreakdownPanel({ mode, title }: { mode: 'admin' | 'viewer'; title: string }): JSX.Element {
  const [controls, setControls] = useState<PointBreakdownControlsState>(defaultPointBreakdownControls)
  const [submitted, setSubmitted] = useState(defaultPointBreakdownControls)
  const [enabled, setEnabled] = useState(false)
  const isAdmin = mode === 'admin'
  const query = useQuery({
    queryKey: [mode, 'point-breakdown', submitted],
    queryFn: () => isAdmin ? getAdminPointBreakdown(submitted.season, buildPointBreakdownParams(submitted)) : getViewerPointBreakdown(submitted.season, buildPointBreakdownParams(submitted)),
    enabled,
    retry: false
  })
  const data = query.data ?? null

  return <SectionCard title={title}>
    <p className="status">Point breakdowns are read from persisted point award packages. This does not implement rolling expiry or best-N selection yet.</p>
    <div className="grid">
      <label>Season<input value={controls.season} onChange={(event) => setControls((current) => ({ ...current, season: event.target.value }))} /></label>
      <label>Player ID<input value={controls.playerId} onChange={(event) => setControls((current) => ({ ...current, playerId: event.target.value }))} placeholder="P1" /></label>
      <label>Search<input value={controls.search} onChange={(event) => setControls((current) => ({ ...current, search: event.target.value }))} placeholder="Player name or ID" /></label>
      {isAdmin ? <label>Country filter<input value={controls.countryCode} onChange={(event) => setControls((current) => ({ ...current, countryCode: event.target.value.toUpperCase() }))} placeholder="EGY" /></label> : null}
      {isAdmin ? <label>Table type<select value={controls.tableType} onChange={(event) => setControls((current) => ({ ...current, tableType: event.target.value as PointBreakdownTableType }))}>
        <option value="both">Both</option>
        <option value="ranking">Ranking</option>
        <option value="race">Race</option>
      </select></label> : null}
      {isAdmin ? <label>Limit<input type="number" min="1" value={controls.limit} onChange={(event) => setControls((current) => ({ ...current, limit: event.target.value }))} /></label> : null}
      <label><input type="checkbox" checked={controls.appliedOnly} onChange={(event) => setControls((current) => ({ ...current, appliedOnly: event.target.checked }))} /> Applied only</label>
      {isAdmin ? <label><input type="checkbox" checked={controls.includeZeroPointAwards} onChange={(event) => setControls((current) => ({ ...current, includeZeroPointAwards: event.target.checked }))} /> Include zero-point awards</label> : null}
    </div>
    <div className="button-row">
      <button type="button" onClick={() => { setSubmitted(controls); setEnabled(true) }} disabled={query.isFetching}>Load point breakdown</button>
    </div>
    {query.isError ? <p role="alert" className="error">{formatApiError(query.error)}</p> : null}
    {data ? <PointBreakdownContent response={data} /> : <p className="status">Load a persisted season point breakdown.</p>}
  </SectionCard>
}

function PointBreakdownContent({ response }: { response: PlayerPointBreakdownResponse }): JSX.Element {
  const breakdown = response.breakdown
  return <>
    {breakdown ? <SummaryPills items={[
      { label: 'Player', value: breakdown.player_name },
      { label: 'Current ranking points', value: breakdown.current_ranking_points },
      { label: 'Current race points', value: breakdown.current_race_points },
      { label: 'Applied ranking total', value: breakdown.applied_ranking_points_total },
      { label: 'Applied race total', value: breakdown.applied_race_points_total },
      { label: 'Event count', value: `${breakdown.applied_event_count}/${breakdown.total_event_count}` },
      { label: 'Consistency ok', value: breakdown.consistency.ranking_points_match_active_player && breakdown.consistency.race_points_match_active_player ? 'Yes' : 'No' }
    ]} /> : null}
    <MetadataList items={[
      { label: 'Source', value: response.metadata.source },
      { label: 'Point awards fingerprint', value: response.metadata.point_awards_fingerprint },
      { label: 'Generated fingerprint', value: response.metadata.generated_fingerprint },
      { label: 'Rolling ranking', value: response.metadata.rolling_ranking_implemented ? 'Implemented' : 'Not implemented' },
      { label: 'Best-N', value: response.metadata.best_n_implemented ? 'Implemented' : 'Not implemented' }
    ]} />
    {response.validation_warnings.length ? <ul>{response.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
    {breakdown ? <PointBreakdownEntriesTable entries={breakdown.entries} /> : <PointBreakdownSummaryRowsTable rows={response.summary_rows} />}
  </>
}

function shortFingerprint(value: string | null | undefined): string {
  return value ? value.slice(0, 12) : '—'
}

function PointBreakdownEntriesTable({ entries }: { entries: PlayerPointBreakdownEntry[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Player point breakdown table">
      <thead><tr><th>Season week</th><th>Event</th><th>Category/tour</th><th>Reached stage</th><th>Qualifier</th><th>Ranking points</th><th>Race points</th><th>Applied</th><th>Fingerprint</th></tr></thead>
      <tbody>{entries.map((entry) => <tr key={`${entry.event_id}-${entry.award_fingerprint}`}><td>{entry.season_week ?? '—'}</td><td>{entry.event_name ?? entry.event_id}</td><td>{entry.category ?? '—'} / {entry.tour_level ?? '—'}</td><td>{entry.reached_stage}</td><td>{entry.qualifier ? 'yes' : 'no'}</td><td>{entry.ranking_points_awarded}</td><td>{entry.race_points_awarded}</td><td>{entry.applied ? 'yes' : 'no'}</td><td>{shortFingerprint(entry.award_fingerprint)}</td></tr>)}</tbody>
    </table>
    {!entries.length ? <p className="status">No event point awards match this player and filter.</p> : null}
  </div>
}

function PointBreakdownSummaryRowsTable({ rows }: { rows: PlayerPointBreakdownSummaryRow[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Point breakdown summary rows table">
      <thead><tr><th>Player</th><th>Country</th><th>Active ranking points</th><th>Active race points</th><th>Breakdown ranking total</th><th>Breakdown race total</th><th>Applied events</th><th>Consistency</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.player_id}><td>{row.player_name}</td><td>{row.country_code}</td><td>{row.ranking_points}</td><td>{row.race_points}</td><td>{row.breakdown_ranking_points_total}</td><td>{row.breakdown_race_points_total}</td><td>{row.applied_event_count}/{row.total_event_count}</td><td>{row.consistency_ok ? 'ok' : 'mismatch'}</td></tr>)}</tbody>
    </table>
    {!rows.length ? <p className="status">No players match the selected point breakdown filters.</p> : null}
  </div>
}

type SnapshotControlsState = {
  season: string
  seasonWeek: string
  seed: string
  dryRun: boolean
  overwriteExisting: boolean
  includeZeroPoints: boolean
  limit: string
}

const defaultSnapshotControls: SnapshotControlsState = {
  season: '2000/2001',
  seasonWeek: '1',
  seed: '12345',
  dryRun: true,
  overwriteExisting: false,
  includeZeroPoints: true,
  limit: '100'
}

function WeeklyRankingSnapshotPanel({ mode }: { mode: 'admin' | 'viewer' }): JSX.Element {
  const isAdmin = mode === 'admin'
  const [controls, setControls] = useState<SnapshotControlsState>(defaultSnapshotControls)
  const [result, setResult] = useState<WeeklyRankingSnapshotResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const seasonWeek = Number(controls.seasonWeek || 1)
  const loadSnapshot = async () => {
    setLoading(true); setError(null)
    try {
      const response = isAdmin ? await getAdminRankingSnapshot(controls.season, seasonWeek) : await getViewerRankingSnapshot(controls.season, seasonWeek)
      setResult(response)
    } catch (caught) {
      setError(formatApiError(caught))
    } finally {
      setLoading(false)
    }
  }
  const generateSnapshot = async (persist: boolean) => {
    setLoading(true); setError(null)
    try {
      const response = await generateAdminRankingSnapshot(controls.season, seasonWeek, {
        seed: Number(controls.seed || 12345),
        dry_run: !persist,
        overwrite_existing: controls.overwriteExisting,
        include_zero_points: controls.includeZeroPoints,
        limit: controls.limit.trim() ? Number(controls.limit) : null
      })
      setResult(response)
    } catch (caught) {
      setError(formatApiError(caught))
    } finally {
      setLoading(false)
    }
  }
  const snapshot = result?.snapshot ?? null
  return <SectionCard title="Weekly Ranking Snapshots">
    <p className="status">Snapshots publish the current active-player ranking/race tables for a season week. Rolling 61-week expiry and best-N selection are not implemented yet.</p>
    <div className="grid">
      <label>Snapshot season<input value={controls.season} onChange={(event) => setControls((current) => ({ ...current, season: event.target.value }))} /></label>
      <label>Season week<input type="number" min="1" max="61" value={controls.seasonWeek} onChange={(event) => setControls((current) => ({ ...current, seasonWeek: event.target.value }))} /></label>
      {isAdmin ? <label>Seed<input type="number" value={controls.seed} onChange={(event) => setControls((current) => ({ ...current, seed: event.target.value }))} /></label> : null}
      {isAdmin ? <label>Limit<input type="number" min="1" value={controls.limit} onChange={(event) => setControls((current) => ({ ...current, limit: event.target.value }))} /></label> : null}
      {isAdmin ? <label><input type="checkbox" checked={controls.dryRun} onChange={(event) => setControls((current) => ({ ...current, dryRun: event.target.checked }))} /> Dry-run default</label> : null}
      {isAdmin ? <label><input type="checkbox" checked={controls.overwriteExisting} onChange={(event) => setControls((current) => ({ ...current, overwriteExisting: event.target.checked }))} /> Overwrite existing</label> : null}
      {isAdmin ? <label><input type="checkbox" checked={controls.includeZeroPoints} onChange={(event) => setControls((current) => ({ ...current, includeZeroPoints: event.target.checked }))} /> Include zero-point players</label> : null}
    </div>
    <div className="button-row">
      {isAdmin ? <button type="button" onClick={() => generateSnapshot(false)} disabled={loading}>Preview snapshot</button> : null}
      {isAdmin ? <button type="button" onClick={() => generateSnapshot(true)} disabled={loading}>Persist snapshot</button> : null}
      <button type="button" onClick={loadSnapshot} disabled={loading}>{isAdmin ? 'Load persisted snapshot' : 'Load weekly snapshot'}</button>
    </div>
    {error ? <p role="alert" className="error">{error}</p> : null}
    {result && !snapshot ? <p className="status">No published snapshot for this week.</p> : null}
    {result && snapshot ? <SnapshotContent result={result} /> : null}
  </SectionCard>
}

function SnapshotContent({ result }: { result: WeeklyRankingSnapshotResult }): JSX.Element {
  const snapshot = result.snapshot
  if (!snapshot) return <p className="status">No published snapshot for this week.</p>
  const rankingLeader = snapshot.ranking_table.rows.find((row) => row.player_id === snapshot.ranking_table.summary.leader_player_id)
  const raceLeader = snapshot.race_table.rows.find((row) => row.player_id === snapshot.race_table.summary.leader_player_id)
  return <>
    <SummaryPills items={[
      { label: 'Snapshot exists', value: result.snapshot_exists ? 'Yes' : 'No' },
      { label: 'Ranking leader', value: rankingLeader?.player_name ?? snapshot.ranking_table.summary.leader_player_id ?? '—' },
      { label: 'Race leader', value: raceLeader?.player_name ?? snapshot.race_table.summary.leader_player_id ?? '—' },
      { label: 'Ranking players', value: snapshot.ranking_table.summary.player_count },
      { label: 'Race players', value: snapshot.race_table.summary.player_count },
      { label: 'New entries', value: snapshot.ranking_table.summary.new_entries_count },
      { label: 'Moved up', value: snapshot.ranking_table.summary.moved_up_count },
      { label: 'Moved down', value: snapshot.ranking_table.summary.moved_down_count },
      { label: 'Unchanged', value: snapshot.ranking_table.summary.unchanged_count },
      { label: 'Rolling ranking', value: snapshot.metadata.rolling_ranking_implemented ? 'Implemented' : 'Not implemented' },
      { label: 'Best-N', value: snapshot.metadata.best_n_implemented ? 'Implemented' : 'Not implemented' }
    ]} />
    <MetadataList items={[
      { label: 'Publication basis', value: snapshot.metadata.publication_basis },
      { label: 'Snapshot fingerprint', value: shortFingerprint(snapshot.metadata.snapshot_fingerprint) },
      { label: 'Previous fingerprint', value: shortFingerprint(snapshot.metadata.previous_snapshot_fingerprint) },
      { label: 'Calendar week', value: snapshot.calendar_year && snapshot.year_week ? `${snapshot.calendar_year}/W${snapshot.year_week}` : '—' }
    ]} />
    {[...snapshot.validation_warnings, ...result.validation_warnings].length ? <ul>{[...snapshot.validation_warnings, ...result.validation_warnings].map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul> : null}
    {[...snapshot.validation_errors, ...result.validation_errors].length ? <ul>{[...snapshot.validation_errors, ...result.validation_errors].map((errorText, index) => <li className="error" key={`${errorText}-${index}`}>{errorText}</li>)}</ul> : null}
    <SnapshotRowsTable title="Ranking snapshot table" rows={snapshot.ranking_table.rows} primary="ranking" />
    <SnapshotRowsTable title="Race snapshot table" rows={snapshot.race_table.rows} primary="race" />
  </>
}

function formatMovement(row: RankingSnapshotRow): string {
  if (row.movement_label === 'none') return '—'
  if (row.movement === null) return row.movement_label
  return row.movement > 0 ? `+${row.movement}` : String(row.movement)
}

function SnapshotRowsTable({ title, rows, primary }: { title: string; rows: RankingSnapshotRow[]; primary: 'ranking' | 'race' }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label={title}>
      <thead><tr><th>Rank</th><th>Previous rank</th><th>Movement</th><th>Player</th><th>Country</th><th>{primary === 'ranking' ? 'Ranking points' : 'Race points'}</th><th>{primary === 'ranking' ? 'Race points' : 'Ranking points'}</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.player_id}><td>{row.rank}</td><td>{row.previous_rank ?? '—'}</td><td>{formatMovement(row)}</td><td>{row.player_name}</td><td>{row.country_code}</td><td>{primary === 'ranking' ? row.ranking_points : row.race_points}</td><td>{primary === 'ranking' ? row.race_points : row.ranking_points}</td></tr>)}</tbody>
    </table>
    {!rows.length ? <p className="status">No snapshot rows available.</p> : null}
  </div>
}
