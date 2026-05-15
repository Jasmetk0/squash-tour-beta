import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { bootstrapSeasonFromInitialPool, buildSeasonCalendar, generateEventDrawPackage, generateEventEntryList, generateEventMatchPackage, getEventDrawPackage, getEventEntryList, getEventMatchPackage, getSeasonActivePlayers, getSeasonCalendar, simulateEventMatch, simulateNextEventMatch } from '../api/client'
import type { DrawBracket, DrawSlotRecord, DrawValidationIssue, EntryListValidationIssue, MatchValidationIssue, SeasonActivePlayer, SeasonBootstrapResponse, SeasonCalendarBuildResponse, SeasonCalendarEvent, SeasonEventDrawPackageResult, SeasonEventEntry, SeasonEventEntryListResult, SeasonEventMatchPackageResult, SeasonMatchRecord } from '../api/types'
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
  const [selectedEventId, setSelectedEventId] = useState('')
  const [entrySeed, setEntrySeed] = useState(12345)
  const [entryOverwriteExisting, setEntryOverwriteExisting] = useState(false)
  const [entryDryRun, setEntryDryRun] = useState(true)
  const [maxAlternates, setMaxAlternates] = useState(16)
  const [includeNotEntered, setIncludeNotEntered] = useState(false)
  const [entryResult, setEntryResult] = useState<SeasonEventEntryListResult | null>(null)
  const [drawSeed, setDrawSeed] = useState(12345)
  const [drawDryRun, setDrawDryRun] = useState(true)
  const [drawOverwriteExisting, setDrawOverwriteExisting] = useState(false)
  const [drawResult, setDrawResult] = useState<SeasonEventDrawPackageResult | null>(null)
  const [matchSeed, setMatchSeed] = useState(12345)
  const [matchDryRun, setMatchDryRun] = useState(true)
  const [matchOverwriteExisting, setMatchOverwriteExisting] = useState(false)
  const [selectedMatchId, setSelectedMatchId] = useState('')
  const [matchResult, setMatchResult] = useState<SeasonEventMatchPackageResult | null>(null)
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

  const entryMutation = useMutation({
    mutationFn: (persist: boolean) => generateEventEntryList(effectiveEventId, {
      seed: entrySeed,
      dry_run: !persist,
      overwrite_existing: entryOverwriteExisting,
      max_alternates: maxAlternates,
      include_not_entered: includeNotEntered
    }),
    onSuccess: (result) => {
      setEntryResult(result)
      if (!result.metadata?.dry_run && effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-entry-list', effectiveEventId] })
      }
    }
  })

  const drawMutation = useMutation({
    mutationFn: (persist: boolean) => generateEventDrawPackage(effectiveEventId, {
      seed: drawSeed,
      dry_run: !persist,
      overwrite_existing: drawOverwriteExisting
    }),
    onSuccess: (result) => {
      setDrawResult(result)
      if (!result.metadata?.dry_run && effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-draw-package', effectiveEventId] })
      }
    }
  })

  const matchMutation = useMutation({
    mutationFn: (persist: boolean) => generateEventMatchPackage(effectiveEventId, {
      seed: matchSeed,
      dry_run: !persist,
      overwrite_existing: matchOverwriteExisting
    }),
    onSuccess: (result) => {
      setMatchResult(result)
      if (!result.metadata?.dry_run && effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-match-package', effectiveEventId] })
      }
    }
  })

  const simulateNextMutation = useMutation({
    mutationFn: () => simulateNextEventMatch(effectiveEventId, { seed: matchSeed }),
    onSuccess: (result) => {
      setMatchResult(result)
      if (effectiveEventId) void queryClient.invalidateQueries({ queryKey: ['event-match-package', effectiveEventId] })
    }
  })

  const simulateSelectedMutation = useMutation({
    mutationFn: () => simulateEventMatch(effectiveEventId, selectedMatchId, { seed: matchSeed }),
    onSuccess: (result) => {
      setMatchResult(result)
      if (effectiveEventId) void queryClient.invalidateQueries({ queryKey: ['event-match-package', effectiveEventId] })
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
  const eventOptions = displayedCalendar?.events ?? []
  const effectiveEventId = selectedEventId || eventOptions[0]?.event_id || ''
  const persistedEntryQuery = useQuery({ queryKey: ['event-entry-list', effectiveEventId], queryFn: () => getEventEntryList(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const persistedDrawQuery = useQuery({ queryKey: ['event-draw-package', effectiveEventId], queryFn: () => getEventDrawPackage(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const persistedMatchQuery = useQuery({ queryKey: ['event-match-package', effectiveEventId], queryFn: () => getEventMatchPackage(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const displayedEntryResult = entryResult ?? persistedEntryQuery.data ?? null
  const displayedEntryList = displayedEntryResult?.entry_list ?? null
  const displayedEntrySummary = displayedEntryResult?.summary ?? displayedEntryList?.summary ?? null
  const entryWarnings = displayedEntryResult?.validation_warnings ?? displayedEntryList?.validation_warnings ?? []
  const entryErrors = displayedEntryResult?.validation_errors ?? displayedEntryList?.validation_errors ?? []
  const displayedDrawResult = drawResult ?? persistedDrawQuery.data ?? null
  const displayedDrawPackage = displayedDrawResult?.draw_package ?? null
  const displayedDrawSummary = displayedDrawResult?.summary ?? displayedDrawPackage?.summary ?? null
  const drawWarnings = displayedDrawResult?.validation_warnings ?? displayedDrawPackage?.validation_warnings ?? []
  const drawErrors = displayedDrawResult?.validation_errors ?? displayedDrawPackage?.validation_errors ?? []
  const selectedEventHasPersistedEntryList = Boolean(displayedEntryResult?.entry_list_exists || displayedEntryList)
  const selectedEventHasPersistedDrawPackage = Boolean(displayedDrawResult?.draw_package_exists || displayedDrawPackage)
  const displayedMatchResult = matchResult ?? persistedMatchQuery.data ?? null
  const displayedMatchPackage = displayedMatchResult?.match_package ?? null
  const displayedMatchSummary = displayedMatchResult?.summary ?? displayedMatchPackage?.summary ?? null
  const matchWarnings = displayedMatchResult?.validation_warnings ?? displayedMatchPackage?.validation_warnings ?? []
  const matchErrors = displayedMatchResult?.validation_errors ?? displayedMatchPackage?.validation_errors ?? []
  const displayedMatches = displayedMatchPackage ? [...displayedMatchPackage.qualification_matches, ...displayedMatchPackage.main_draw_matches] : []

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


      <SectionCard title="Event Entries">
        <p className="status">Entry generation selects players for a planned calendar event from active season players. It does not create draws or simulate matches yet.</p>
        {!eventOptions.length ? <p className="status">Persist a season calendar first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Entry seed<input type="number" value={entrySeed} onChange={(event) => setEntrySeed(Number(event.target.value))} /></label>
          <label>Max alternates<input type="number" value={maxAlternates} onChange={(event) => setMaxAlternates(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={entryDryRun} onChange={(event) => setEntryDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={entryOverwriteExisting} onChange={(event) => setEntryOverwriteExisting(event.target.checked)} /> Overwrite existing entry list</label>
          <label><input type="checkbox" checked={includeNotEntered} onChange={(event) => setIncludeNotEntered(event.target.checked)} /> Include not-entered/rejected players</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setEntryDryRun(true); entryMutation.mutate(false) }} disabled={!effectiveEventId || entryMutation.isPending}>Preview entries</button>
          <button type="button" onClick={() => { setEntryDryRun(false); entryMutation.mutate(true) }} disabled={!effectiveEventId || entryMutation.isPending}>Persist entries</button>
        </div>
        {entryMutation.isError ? <p role="alert" className="error">{formatApiError(entryMutation.error)}</p> : null}
        {persistedEntryQuery.isError ? <p role="alert" className="error">{formatApiError(persistedEntryQuery.error)}</p> : null}
        <SummaryPills items={[
          { label: 'Total active players', value: displayedEntrySummary?.total_active_players ?? 0 },
          { label: 'Considered players', value: displayedEntrySummary?.considered_players ?? 0 },
          { label: 'Entered players', value: displayedEntrySummary?.entered_players ?? 0 },
          { label: 'Main draw acceptances', value: displayedEntrySummary?.main_draw_acceptances ?? 0 },
          { label: 'Qualification acceptances', value: displayedEntrySummary?.qualification_acceptances ?? 0 },
          { label: 'Alternates', value: displayedEntrySummary?.alternates ?? 0 },
          { label: 'Countries represented', value: displayedEntrySummary?.countries_represented ?? 0 },
          { label: 'Validation warnings/errors', value: `${displayedEntrySummary?.validation_warning_count ?? entryWarnings.length}/${displayedEntrySummary?.validation_error_count ?? entryErrors.length}` }
        ]} />
        {displayedEntryResult?.metadata ? <MetadataList items={[
          { label: 'Build fingerprint', value: displayedEntryResult.metadata.build_fingerprint },
          { label: 'Active players fingerprint', value: displayedEntryResult.metadata.active_players_fingerprint },
          { label: 'Calendar event fingerprint', value: displayedEntryResult.metadata.calendar_event_fingerprint },
          { label: 'Ranking basis', value: displayedEntryResult.metadata.ranking_basis }
        ]} /> : null}
        <EntryValidationPanel warnings={entryWarnings} errors={entryErrors} />
        <div className="table-wrap">
          <table aria-label="Event entries table">
            <thead><tr><th>Decision/status</th><th>Rank priority</th><th>player_id</th><th>Name</th><th>Country</th><th>Current</th><th>Ranking points</th><th>Entry probability</th><th>Entry score</th><th>Quality score</th><th>Travel score</th><th>Notes</th></tr></thead>
            <tbody>{displayedEntryList?.entries.map((entry) => <EntryRow key={entry.entry_id} entry={entry} />)}</tbody>
          </table>
        </div>
        {!displayedEntryList?.entries.length ? <p className="status">No entry list is displayed yet. Preview or persist entries for a persisted event.</p> : null}
      </SectionCard>

      <SectionCard title="Event Draws">
        <p className="status">Draw generation creates bracket slots from persisted entry lists. It does not simulate matches or update rankings yet.</p>
        {!eventOptions.length ? <p className="status">Persist a season calendar first.</p> : null}
        {eventOptions.length && !selectedEventHasPersistedEntryList ? <p className="status">Persist an entry list first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Draw seed<input type="number" value={drawSeed} onChange={(event) => setDrawSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={drawDryRun} onChange={(event) => setDrawDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={drawOverwriteExisting} onChange={(event) => setDrawOverwriteExisting(event.target.checked)} /> Overwrite existing draw package</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setDrawDryRun(true); drawMutation.mutate(false) }} disabled={!effectiveEventId || !selectedEventHasPersistedEntryList || drawMutation.isPending}>Preview draw</button>
          <button type="button" onClick={() => { setDrawDryRun(false); drawMutation.mutate(true) }} disabled={!effectiveEventId || !selectedEventHasPersistedEntryList || drawMutation.isPending}>Persist draw</button>
        </div>
        {drawMutation.isError ? <p role="alert" className="error">{formatApiError(drawMutation.error)}</p> : null}
        {persistedDrawQuery.isError ? <p role="alert" className="error">{formatApiError(persistedDrawQuery.error)}</p> : null}
        <SummaryPills items={[
          { label: 'Main draw size', value: displayedDrawSummary?.main_draw_size ?? 0 },
          { label: 'Qualification draw size', value: displayedDrawSummary?.qualification_draw_size ?? 0 },
          { label: 'Main draw players', value: displayedDrawSummary?.main_draw_players ?? 0 },
          { label: 'Qualification players', value: displayedDrawSummary?.qualification_draw_players ?? 0 },
          { label: 'Qualifier placeholders', value: displayedDrawSummary?.qualifier_placeholders ?? 0 },
          { label: 'BYEs', value: displayedDrawSummary?.byes ?? 0 },
          { label: 'Seeds', value: displayedDrawSummary?.seeds ?? 0 },
          { label: 'Validation warnings/errors', value: `${displayedDrawSummary?.validation_warning_count ?? drawWarnings.length}/${displayedDrawSummary?.validation_error_count ?? drawErrors.length}` }
        ]} />
        {displayedDrawResult?.metadata ? <MetadataList items={[
          { label: 'Build fingerprint', value: displayedDrawResult.metadata.build_fingerprint },
          { label: 'Entry list fingerprint', value: displayedDrawResult.metadata.entry_list_fingerprint },
          { label: 'Calendar event fingerprint', value: displayedDrawResult.metadata.calendar_event_fingerprint },
          { label: 'Draw engine', value: displayedDrawResult.metadata.draw_engine_version ?? '—' },
          { label: 'Ranking basis', value: displayedDrawResult.metadata.ranking_basis }
        ]} /> : null}
        <DrawValidationPanel warnings={drawWarnings} errors={drawErrors} />
        {displayedDrawPackage ? <>
          <DrawSlotsTable title="Main draw table" bracket={displayedDrawPackage.main_draw} />
          {displayedDrawPackage.qualification_draw ? <DrawSlotsTable title="Qualification draw table" bracket={displayedDrawPackage.qualification_draw} /> : <p className="status">No qualification draw for this event.</p>}
          <DrawMatchesTable title="Main draw match preview" bracket={displayedDrawPackage.main_draw} />
          {displayedDrawPackage.qualification_draw ? <DrawMatchesTable title="Qualification draw match preview" bracket={displayedDrawPackage.qualification_draw} /> : null}
        </> : <p className="status">No draw package is displayed yet. Preview or persist a draw for a persisted event entry list.</p>}
      </SectionCard>


      <SectionCard title="Event Matches">
        <p className="status">Match generation creates match records from persisted draw packages. Simulation stores results but does not update rankings/race yet.</p>
        {!eventOptions.length ? <p className="status">Persist a season calendar first.</p> : null}
        {eventOptions.length && !selectedEventHasPersistedDrawPackage ? <p className="status">Persist a draw package first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Match seed<input type="number" value={matchSeed} onChange={(event) => setMatchSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={matchDryRun} onChange={(event) => setMatchDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={matchOverwriteExisting} onChange={(event) => setMatchOverwriteExisting(event.target.checked)} /> Overwrite existing match package</label>
          <label>Selected match<select value={selectedMatchId} onChange={(event) => setSelectedMatchId(event.target.value)} disabled={!displayedMatches.length}><option value="">Choose a match</option>{displayedMatches.map((match) => <option key={match.match_id} value={match.match_id}>{match.status}: {match.match_id}</option>)}</select></label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setMatchDryRun(true); matchMutation.mutate(false) }} disabled={!effectiveEventId || !selectedEventHasPersistedDrawPackage || matchMutation.isPending}>Preview match package</button>
          <button type="button" onClick={() => { setMatchDryRun(false); matchMutation.mutate(true) }} disabled={!effectiveEventId || !selectedEventHasPersistedDrawPackage || matchMutation.isPending}>Persist match package</button>
          <button type="button" onClick={() => simulateNextMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || simulateNextMutation.isPending}>Simulate next pending match</button>
          <button type="button" onClick={() => simulateSelectedMutation.mutate()} disabled={!effectiveEventId || !selectedMatchId || !displayedMatchResult?.match_package_exists || simulateSelectedMutation.isPending}>Simulate selected match</button>
        </div>
        {matchMutation.isError ? <p role="alert" className="error">{formatApiError(matchMutation.error)}</p> : null}
        {simulateNextMutation.isError ? <p role="alert" className="error">{formatApiError(simulateNextMutation.error)}</p> : null}
        {simulateSelectedMutation.isError ? <p role="alert" className="error">{formatApiError(simulateSelectedMutation.error)}</p> : null}
        {persistedMatchQuery.isError ? <p role="alert" className="error">{formatApiError(persistedMatchQuery.error)}</p> : null}
        <SummaryPills items={[
          { label: 'Total matches', value: displayedMatchSummary?.total_matches ?? 0 },
          { label: 'Qualification matches', value: displayedMatchSummary?.qualification_matches ?? 0 },
          { label: 'Main draw matches', value: displayedMatchSummary?.main_draw_matches ?? 0 },
          { label: 'Pending matches', value: displayedMatchSummary?.pending_matches ?? 0 },
          { label: 'Completed matches', value: displayedMatchSummary?.completed_matches ?? 0 },
          { label: 'Blocked matches', value: displayedMatchSummary?.blocked_matches ?? 0 },
          { label: 'BYE auto-advances', value: displayedMatchSummary?.bye_auto_advances ?? 0 },
          { label: 'Validation warnings/errors', value: `${displayedMatchSummary?.validation_warning_count ?? matchWarnings.length}/${displayedMatchSummary?.validation_error_count ?? matchErrors.length}` }
        ]} />
        {displayedMatchResult?.metadata ? <MetadataList items={[
          { label: 'Build fingerprint', value: displayedMatchResult.metadata.build_fingerprint },
          { label: 'Draw package fingerprint', value: displayedMatchResult.metadata.draw_package_fingerprint },
          { label: 'Active players fingerprint', value: displayedMatchResult.metadata.active_players_fingerprint },
          { label: 'Match engine', value: displayedMatchResult.metadata.match_engine_version ?? '—' },
          { label: 'Ranking updates', value: displayedMatchResult.metadata.ranking_updates_implemented ? 'Implemented' : 'Not implemented yet' }
        ]} /> : null}
        <MatchValidationPanel warnings={matchWarnings} errors={matchErrors} />
        {displayedMatchPackage ? <MatchRecordsTable matches={displayedMatches} /> : <p className="status">No match package is displayed yet. Preview or persist matches for a persisted draw package.</p>}
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

function EntryValidationPanel({ warnings, errors }: { warnings: EntryListValidationIssue[]; errors: EntryListValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Entry errors</h4><ul>{errors.map((issue) => <li key={`entry-error-${issue.code}-${issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No entry validation errors.</p>}
    {warnings.length ? <><h4>Entry warnings</h4><ul>{warnings.map((issue) => <li key={`entry-warning-${issue.code}-${issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No entry validation warnings.</p>}
  </div>
}

function EntryRow({ entry }: { entry: SeasonEventEntry }): JSX.Element {
  return <tr><td>{entry.decision}</td><td>{entry.ranking_priority}</td><td>{entry.player_id}</td><td>{entry.name}</td><td>{entry.country_code}</td><td>{entry.current_ability}</td><td>{entry.ranking_points}</td><td>{entry.entry_probability}</td><td>{entry.entry_score}</td><td>{entry.quality_score}</td><td>{entry.travel_score ?? '—'}</td><td>{entry.decision_notes ?? entry.reason}</td></tr>
}

function DrawValidationPanel({ warnings, errors }: { warnings: DrawValidationIssue[]; errors: DrawValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Draw errors</h4><ul>{errors.map((issue) => <li key={`draw-error-${issue.code}-${issue.player_id ?? issue.event_id ?? issue.field ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No draw validation errors.</p>}
    {warnings.length ? <><h4>Draw warnings</h4><ul>{warnings.map((issue) => <li key={`draw-warning-${issue.code}-${issue.player_id ?? issue.event_id ?? issue.field ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No draw validation warnings.</p>}
  </div>
}

function DrawSlotsTable({ title, bracket }: { title: string; bracket: DrawBracket }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label={title}>
      <thead><tr><th>Position</th><th>Seed</th><th>Slot</th><th>player_id</th><th>Name</th><th>Country</th><th>Source decision</th></tr></thead>
      <tbody>{bracket.slots.map((slot) => <DrawSlotRow key={slot.slot_id} slot={slot} />)}</tbody>
    </table>
  </div>
}

function DrawSlotRow({ slot }: { slot: DrawSlotRecord }): JSX.Element {
  const slotLabel = slot.is_bye ? 'BYE' : slot.is_qualifier_placeholder ? `Q placeholder` : slot.entry_decision === 'wild_card_reserved' ? 'Wildcard reserved' : slot.player_name ?? '—'
  return <tr><td>{slot.bracket_position}</td><td>{slot.seed_number ?? '—'}</td><td>{slotLabel}</td><td>{slot.player_id ?? '—'}</td><td>{slot.player_name ?? '—'}</td><td>{slot.country_code ?? '—'}</td><td>{slot.entry_decision}</td></tr>
}

function DrawMatchesTable({ title, bracket }: { title: string; bracket: DrawBracket }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label={title}>
      <thead><tr><th>Round</th><th>match_id</th><th>Top slot</th><th>Bottom slot</th><th>winner_to</th><th>Status</th></tr></thead>
      <tbody>{bracket.rounds.flatMap((round) => round.matches.map((match) => <tr key={match.match_id}><td>{round.round_name}</td><td>{match.match_id}</td><td>{match.top_slot_id}</td><td>{match.bottom_slot_id}</td><td>{match.winner_to_match_id ?? '—'}</td><td>{match.status}</td></tr>))}</tbody>
    </table>
  </div>
}


function MatchValidationPanel({ warnings, errors }: { warnings: MatchValidationIssue[]; errors: MatchValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Match errors</h4><ul>{errors.map((issue) => <li key={`match-error-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No match validation errors.</p>}
    {warnings.length ? <><h4>Match warnings</h4><ul>{warnings.map((issue) => <li key={`match-warning-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No match validation warnings.</p>}
  </div>
}

function MatchRecordsTable({ matches }: { matches: SeasonMatchRecord[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Event matches table">
      <thead><tr><th>Status</th><th>Draw type</th><th>Round</th><th>Position</th><th>match_id</th><th>Top player</th><th>Bottom player</th><th>Winner</th><th>Scoreline</th><th>winner_to</th><th>Notes</th></tr></thead>
      <tbody>{matches.map((match) => <tr key={match.match_id}><td>{match.status}</td><td>{match.draw_type}</td><td>{match.round_name}</td><td>{match.bracket_position}</td><td>{match.match_id}</td><td>{match.top_player_name ?? match.top_player_id ?? match.top_source}</td><td>{match.bottom_player_name ?? match.bottom_player_id ?? match.bottom_source}</td><td>{match.winner_player_id ?? '—'}</td><td>{match.scoreline ?? '—'}</td><td>{match.winner_to_match_id ?? '—'}</td><td>{match.result_notes ?? '—'}</td></tr>)}</tbody>
    </table>
  </div>
}
