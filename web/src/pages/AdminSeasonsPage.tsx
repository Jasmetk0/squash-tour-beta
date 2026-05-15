import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { bootstrapSeasonFromInitialPool, buildSeasonCalendar, getSeasonActivePlayers, getSeasonCalendar } from '../api/client'
import type { SeasonActivePlayer, SeasonBootstrapResponse, SeasonCalendarBuildResponse, SeasonCalendarEvent } from '../api/types'
import { PageIntro, SectionCard, SummaryPills, MetadataList } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminSeasonsPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [season, setSeason] = useState('2000/2001')
  const [sourceSeason, setSourceSeason] = useState('2000/2001')
  const [seed, setSeed] = useState(12345)
  const [dryRun, setDryRun] = useState(true)
  const [overwriteExisting, setOverwriteExisting] = useState(false)
  const [preview, setPreview] = useState<SeasonBootstrapResponse | null>(null)
  const [calendarSeed, setCalendarSeed] = useState(12345)
  const [seasonStartCalendarYear, setSeasonStartCalendarYear] = useState(2000)
  const [seasonStartYearWeek, setSeasonStartYearWeek] = useState(35)
  const [calendarDryRun, setCalendarDryRun] = useState(true)
  const [calendarOverwriteExisting, setCalendarOverwriteExisting] = useState(false)
  const [includeInactiveTemplates, setIncludeInactiveTemplates] = useState(false)
  const [maxEvents, setMaxEvents] = useState('')
  const [calendarBuildResult, setCalendarBuildResult] = useState<SeasonCalendarBuildResponse | null>(null)
  const playersQuery = useQuery({ queryKey: ['season-active-players', season], queryFn: () => getSeasonActivePlayers(season), retry: false })
  const calendarQuery = useQuery({ queryKey: ['season-calendar', season], queryFn: () => getSeasonCalendar(season), retry: false })

  const bootstrapMutation = useMutation({
    mutationFn: (persist: boolean) => bootstrapSeasonFromInitialPool(season, { source_season: sourceSeason, seed, dry_run: !persist, overwrite_existing: overwriteExisting }),
    onSuccess: (result) => {
      setPreview(result)
      if (!result.metadata.dry_run) {
        void queryClient.invalidateQueries({ queryKey: ['season-active-players', season] })
      }
    }
  })

  const calendarMutation = useMutation({
    mutationFn: (persist: boolean) => buildSeasonCalendar(season, {
      seed: calendarSeed,
      dry_run: !persist,
      overwrite_existing: calendarOverwriteExisting,
      season_start_calendar_year: seasonStartCalendarYear,
      season_start_year_week: seasonStartYearWeek,
      include_inactive_templates: includeInactiveTemplates,
      max_events: maxEvents.trim() ? Number(maxEvents) : null
    }),
    onSuccess: (result) => {
      setCalendarBuildResult(result)
      if (!result.metadata?.dry_run) {
        void queryClient.invalidateQueries({ queryKey: ['season-calendar', season] })
      }
    }
  })

  const displayedPlayers = preview?.players.length ? preview.players : playersQuery.data?.players ?? []
  const displayedSummary = preview?.summary ?? playersQuery.data?.summary
  const displayedWarnings = preview?.warnings ?? playersQuery.data?.warnings ?? []
  const metadata = preview?.metadata ?? playersQuery.data?.metadata ?? null
  const activeCount = playersQuery.data?.summary.total_active_players ?? 0
  const hasActivePlayers = activeCount > 0
  const tierCounts = useMemo(() => displayedSummary?.by_potential_tier ?? {}, [displayedSummary])
  const displayedCalendar = calendarBuildResult?.calendar ?? calendarQuery.data?.calendar ?? null
  const displayedCalendarSummary = calendarBuildResult?.summary ?? calendarQuery.data?.summary
  const validationWarnings = calendarBuildResult?.validation_warnings ?? displayedCalendar?.validation_warnings ?? []
  const validationErrors = calendarBuildResult?.validation_errors ?? displayedCalendar?.validation_errors ?? []

  return (
    <section className="panel">
      <PageIntro title="Seasons / Bootstrap" subtitle="Convert the curated initial pool into deterministic first-season active player records." />
      <p className="status">Bootstrap converts the curated initial pool into active first-season players. It does not simulate tournaments yet.</p>

      <SectionCard title="Bootstrap controls">
        <div className="grid">
          <label>Target season<input value={season} onChange={(event) => setSeason(event.target.value)} /></label>
          <label>Source initial pool season<input value={sourceSeason} onChange={(event) => setSourceSeason(event.target.value)} /></label>
          <label>Seed<input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={overwriteExisting} onChange={(event) => setOverwriteExisting(event.target.checked)} /> Overwrite existing active players</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setDryRun(true); bootstrapMutation.mutate(false) }} disabled={bootstrapMutation.isPending}>Preview bootstrap</button>
          <button type="button" onClick={() => { setDryRun(false); bootstrapMutation.mutate(true) }} disabled={bootstrapMutation.isPending}>Persist bootstrap</button>
        </div>
        {bootstrapMutation.isError ? <p role="alert" className="error">{formatApiError(bootstrapMutation.error)}</p> : null}
      </SectionCard>

      <SectionCard title="Season status">
        <SummaryPills items={[
          { label: 'Active players exist', value: hasActivePlayers ? 'Yes' : 'No' },
          { label: 'Persisted active players', value: activeCount },
          { label: 'Displayed players', value: displayedPlayers.length },
          { label: 'Last result', value: preview ? (preview.metadata.dry_run ? 'Preview' : 'Persisted bootstrap') : 'Persisted state' }
        ]} />
        {metadata ? <MetadataList items={[
          { label: 'Bootstrap ID', value: metadata.bootstrap_id },
          { label: 'Bootstrap fingerprint', value: metadata.bootstrap_fingerprint },
          { label: 'Source pool fingerprint', value: metadata.source_initial_pool_fingerprint },
          { label: 'Ranking seeding', value: metadata.ranking_seeding_implemented ? 'Implemented' : 'Not implemented yet' }
        ]} /> : <p className="status">No bootstrap metadata has been persisted for this season yet.</p>}
      </SectionCard>

      <SectionCard title="Bootstrap summary">
        <SummaryPills items={[
          { label: 'Total active players', value: displayedSummary?.total_active_players ?? 0 },
          { label: 'Countries represented', value: displayedSummary?.countries_represented ?? 0 },
          { label: 'Manual players', value: displayedSummary?.manual_players ?? 0 },
          { label: 'Generated players', value: displayedSummary?.generated_players ?? 0 },
          { label: 'Locked from initial pool', value: displayedSummary?.locked_from_initial_pool ?? 0 },
          { label: 'Average current ability', value: displayedSummary?.average_current_ability ?? 0 },
          { label: 'Average potential ability', value: displayedSummary?.average_potential_ability ?? 0 },
          { label: 'S/A/B tier counts', value: `S: ${tierCounts.S ?? 0}, A: ${tierCounts.A ?? 0}, B: ${tierCounts.B ?? 0}` }
        ]} />
      </SectionCard>

      <SectionCard title="Warnings">
        {displayedWarnings.length ? <ul>{displayedWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p className="status">No bootstrap warnings.</p>}
      </SectionCard>

      <SectionCard title="Season Calendar Builder">
        <p className="status">Calendar builder creates planned season events from editable tournament templates. It does not generate entries, draws, matches, or ranking changes yet.</p>
        <div className="grid">
          <label>Target season<input value={season} onChange={(event) => setSeason(event.target.value)} /></label>
          <label>Seed<input type="number" value={calendarSeed} onChange={(event) => setCalendarSeed(Number(event.target.value))} /></label>
          <label>Season start calendar year<input type="number" value={seasonStartCalendarYear} onChange={(event) => setSeasonStartCalendarYear(Number(event.target.value))} /></label>
          <label>Season start year week<input type="number" value={seasonStartYearWeek} onChange={(event) => setSeasonStartYearWeek(Number(event.target.value))} /></label>
          <label>Max events<input type="number" value={maxEvents} onChange={(event) => setMaxEvents(event.target.value)} placeholder="all templates" /></label>
          <label><input type="checkbox" checked={calendarDryRun} onChange={(event) => setCalendarDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={calendarOverwriteExisting} onChange={(event) => setCalendarOverwriteExisting(event.target.checked)} /> Overwrite existing calendar</label>
          <label><input type="checkbox" checked={includeInactiveTemplates} onChange={(event) => setIncludeInactiveTemplates(event.target.checked)} /> Include inactive templates</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setCalendarDryRun(true); calendarMutation.mutate(false) }} disabled={calendarMutation.isPending}>Preview calendar</button>
          <button type="button" onClick={() => { setCalendarDryRun(false); calendarMutation.mutate(true) }} disabled={calendarMutation.isPending}>Persist calendar</button>
        </div>
        {calendarMutation.isError ? <p role="alert" className="error">{formatApiError(calendarMutation.error)}</p> : null}
      </SectionCard>

      <SectionCard title="Calendar status">
        <SummaryPills items={[
          { label: 'Persisted calendar exists', value: calendarQuery.data?.summary.calendar_exists ? 'Yes' : 'No' },
          { label: 'Persisted event count', value: calendarQuery.data?.summary.event_count ?? 0 },
          { label: 'Displayed event count', value: displayedCalendarSummary?.event_count ?? 0 },
          { label: 'Last build result', value: calendarBuildResult ? (calendarBuildResult.metadata?.dry_run ? 'Preview' : 'Persisted calendar') : 'Persisted state' }
        ]} />
      </SectionCard>

      <SectionCard title="Calendar summary">
        <SummaryPills items={[
          { label: 'Event count', value: displayedCalendarSummary?.event_count ?? 0 },
          { label: 'Season weeks used', value: displayedCalendarSummary?.season_weeks_used ?? 0 },
          { label: 'First event week', value: displayedCalendarSummary?.first_event_week ?? '—' },
          { label: 'Last event week', value: displayedCalendarSummary?.last_event_week ?? '—' },
          { label: 'World Tour events', value: displayedCalendarSummary?.world_tour_events ?? 0 },
          { label: 'Elite Tour events', value: displayedCalendarSummary?.elite_tour_events ?? 0 },
          { label: 'Validation warnings', value: displayedCalendarSummary?.validation_warning_count ?? validationWarnings.length },
          { label: 'Validation errors', value: displayedCalendarSummary?.validation_error_count ?? validationErrors.length }
        ]} />
      </SectionCard>

      <SectionCard title="Calendar validation">
        {validationErrors.length ? <><h4>Errors</h4><ul>{validationErrors.map((issue) => <li key={`e-${issue.code}-${issue.event_id ?? 'calendar'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No calendar validation errors.</p>}
        {validationWarnings.length ? <><h4>Warnings</h4><ul>{validationWarnings.map((issue) => <li key={`w-${issue.code}-${issue.event_id ?? 'calendar'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No calendar validation warnings.</p>}
      </SectionCard>

      <SectionCard title="Season calendar events">
        {calendarQuery.isError ? <p role="alert" className="error">{formatApiError(calendarQuery.error)}</p> : null}
        <div className="table-wrap">
          <table aria-label="Season calendar events table">
            <thead><tr><th>event_id</th><th>Season week</th><th>Calendar week</th><th>Name</th><th>Category</th><th>Tour</th><th>template_id</th><th>Host</th><th>Region</th><th>Duration</th><th>Draw</th><th>Qual</th><th>Prestige</th><th>Prize</th><th>Status</th></tr></thead>
            <tbody>{displayedCalendar?.events.map((event) => <CalendarEventRow key={event.event_id} event={event} />)}</tbody>
          </table>
        </div>
        {!displayedCalendar?.events.length ? <p className="status">No season calendar exists yet. Preview or persist a first-season calendar.</p> : null}
      </SectionCard>

      <SectionCard title="Active season players">
        {playersQuery.isError ? <p role="alert" className="error">{formatApiError(playersQuery.error)}</p> : null}
        <div className="table-wrap">
          <table aria-label="Active season players table">
            <thead><tr><th>player_id</th><th>Name</th><th>Country</th><th>Age</th><th>Current</th><th>Potential</th><th>Tier</th><th>Career stage</th><th>Source</th><th>Manual</th><th>Locked</th><th>Ranking</th><th>Race</th><th>Health</th><th>Status</th></tr></thead>
            <tbody>{displayedPlayers.map((player) => <PlayerRow key={player.player_id} player={player} />)}</tbody>
          </table>
        </div>
        {!displayedPlayers.length ? <p className="status">No active season players yet. Persist an initial pool, then preview or persist bootstrap.</p> : null}
      </SectionCard>
    </section>
  )
}

function CalendarEventRow({ event }: { event: SeasonCalendarEvent }): JSX.Element {
  return <tr><td>{event.event_id}</td><td>{event.season_week}</td><td>{event.calendar_year}/W{event.year_week}</td><td>{event.event_name}</td><td>{event.category}</td><td>{event.tour_level}</td><td>{event.template_id}</td><td>{event.host_country}</td><td>{event.region}</td><td>{event.duration_in_season_weeks}</td><td>{event.main_draw_size}</td><td>{event.qualification_draw_size}</td><td>{event.prestige}</td><td>{event.prize_money}</td><td>{event.status}</td></tr>
}

function PlayerRow({ player }: { player: SeasonActivePlayer }): JSX.Element {
  return <tr><td>{player.player_id}</td><td>{player.name}</td><td>{player.country_code}</td><td>{player.age_years_at_season_start}</td><td>{player.current_ability}</td><td>{player.potential_ability}</td><td>{player.potential_tier}</td><td>{player.career_stage}</td><td>{player.source_generation}</td><td>{player.manual_override ? 'yes' : 'no'}</td><td>{player.locked_from_initial_pool ? 'yes' : 'no'}</td><td>{player.ranking_points}</td><td>{player.race_points}</td><td>{player.health_status}</td><td>{player.active_status}</td></tr>
}
