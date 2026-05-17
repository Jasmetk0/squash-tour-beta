import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { bootstrapSeasonFromInitialPool, buildSeasonCalendar, generateEventDrawPackage, generateEventEntryList, extractEventResultPackage, generateEventPointAwards, applyEventPointAwards, getEventPointAwards, getSeasonLifecycle, generateEventMatchPackage, getEventDrawPackage, getEventEntryList, getEventMatchPackage, getEventProgressionStatus, getEventResultPackage, getSeasonActivePlayers, getSeasonCalendar, processEventByes, promoteEventQualifiers, refreshEventProgression, simulateEventDraw, simulateEventMatch, simulateEventRound, simulateNextEventMatch, simulateOneEvent, preflightSeasonWeek } from '../api/client'
import type { DrawBracket, DrawSlotRecord, DrawValidationIssue, EntryListValidationIssue, MatchValidationIssue, ProgressionCommandResult, SeasonActivePlayer, SeasonBootstrapResponse, SeasonCalendarBuildResponse, SeasonCalendarEvent, SeasonEventDrawPackageResult, SeasonEventEntry, SeasonEventEntryListResult, SeasonEventMatchPackageResult, SeasonEventResultPackageResult, SeasonMatchRecord, TournamentProgressionStatus, PlayerEventResult, PlayerResultSummary, EventResultValidationIssue, EventPointAwardPackageResult, PointAwardApplyResult, PointAwardValidationIssue, PlayerPointAward, UpdatedPlayerPoints, SeasonLifecycleResponse, EventLifecycleStatus, SimulateOneEventReport, SimulateOneEventDrawType, SimulateSeasonWeekPreflightResult, SeasonWeekEventPreflight } from '../api/types'
import { PageIntro, SectionCard, SummaryPills, MetadataList } from '../components/RunScopedUi'
import { AdminRankingTablesSection } from './RankingTables'
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
  const [seasonStartYearWeek, setSeasonStartYearWeek] = useState(37)
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
  const [progressionResult, setProgressionResult] = useState<ProgressionCommandResult | null>(null)
  const [progressionSeed, setProgressionSeed] = useState(12345)
  const [progressionDrawType, setProgressionDrawType] = useState<'qualification' | 'main'>('qualification')
  const [progressionRoundNumber, setProgressionRoundNumber] = useState(1)
  const [resultSeed, setResultSeed] = useState(12345)
  const [resultDryRun, setResultDryRun] = useState(true)
  const [resultOverwriteExisting, setResultOverwriteExisting] = useState(false)
  const [eventResult, setEventResult] = useState<SeasonEventResultPackageResult | null>(null)
  const [pointSeed, setPointSeed] = useState(12345)
  const [pointDryRun, setPointDryRun] = useState(true)
  const [pointOverwriteExisting, setPointOverwriteExisting] = useState(false)
  const [pointAwardsResult, setPointAwardsResult] = useState<EventPointAwardPackageResult | null>(null)
  const [pointApplyResult, setPointApplyResult] = useState<PointAwardApplyResult | null>(null)
  const [lifecycleEventFilter, setLifecycleEventFilter] = useState('')
  const [lifecycleStageFilter, setLifecycleStageFilter] = useState('')
  const [selectedLifecycleEventId, setSelectedLifecycleEventId] = useState('')
  const [simulateEventId, setSimulateEventId] = useState('')
  const [simulateSeed, setSimulateSeed] = useState(12345)
  const [simulateDryRun, setSimulateDryRun] = useState(true)
  const [simulateOverwriteExisting, setSimulateOverwriteExisting] = useState(false)
  const [simulateApplyPoints, setSimulateApplyPoints] = useState(false)
  const [simulatePublishSnapshot, setSimulatePublishSnapshot] = useState(false)
  const [simulateMaxSteps, setSimulateMaxSteps] = useState(20)
  const [simulateMaxAlternates, setSimulateMaxAlternates] = useState(16)
  const [simulateIncludeNotEntered, setSimulateIncludeNotEntered] = useState(false)
  const [simulateDrawType, setSimulateDrawType] = useState<SimulateOneEventDrawType>('qualification_then_main')
  const [simulateReport, setSimulateReport] = useState<SimulateOneEventReport | null>(null)
  const [weekPreflightSeason, setWeekPreflightSeason] = useState(season)
  const [weekPreflightWeek, setWeekPreflightWeek] = useState(1)
  const [weekPreflightSeed, setWeekPreflightSeed] = useState(12345)
  const [weekPreflightApplyPoints, setWeekPreflightApplyPoints] = useState(false)
  const [weekPreflightPublishSnapshot, setWeekPreflightPublishSnapshot] = useState(false)
  const [weekPreflightOverwriteExisting, setWeekPreflightOverwriteExisting] = useState(false)
  const [weekPreflightIncludeCompleted, setWeekPreflightIncludeCompleted] = useState(true)
  const [weekPreflightAllowBlocked, setWeekPreflightAllowBlocked] = useState(false)
  const [weekPreflightAllowIncomplete, setWeekPreflightAllowIncomplete] = useState(false)
  const [weekPreflightMaxSteps, setWeekPreflightMaxSteps] = useState(20)
  const [weekPreflightMaxAlternates, setWeekPreflightMaxAlternates] = useState(16)
  const [weekPreflightDrawType, setWeekPreflightDrawType] = useState<SimulateOneEventDrawType>('qualification_then_main')
  const [weekPreflightEventFilter, setWeekPreflightEventFilter] = useState('')
  const [weekPreflightResult, setWeekPreflightResult] = useState<SimulateSeasonWeekPreflightResult | null>(null)
  const [selectedWeekPreflightEventId, setSelectedWeekPreflightEventId] = useState('')
  const playersQuery = useQuery({ queryKey: ['season-active-players', season], queryFn: () => getSeasonActivePlayers(season), retry: false })
  const calendarQuery = useQuery({ queryKey: ['season-calendar', season], queryFn: () => getSeasonCalendar(season), retry: false })
  const lifecycleQuery = useQuery<SeasonLifecycleResponse>({ queryKey: ['season-lifecycle', season], queryFn: () => getSeasonLifecycle(season), enabled: false, retry: false })

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
  const lifecycleEvents = lifecycleQuery.data?.events ?? []
  const displayedLifecycleEvents = lifecycleEvents.filter((event) => {
    const eventFilter = lifecycleEventFilter.trim().toLowerCase()
    const matchesEvent = !eventFilter || event.event_id.toLowerCase().includes(eventFilter) || event.event_name.toLowerCase().includes(eventFilter)
    const matchesStage = !lifecycleStageFilter || event.current_stage === lifecycleStageFilter
    return matchesEvent && matchesStage
  })
  const lifecycleStages = Array.from(new Set(lifecycleEvents.map((event) => event.current_stage))).sort()
  const selectedLifecycleEvent = lifecycleEvents.find((event) => event.event_id === selectedLifecycleEventId) ?? displayedLifecycleEvents[0] ?? null
  const simulateTargetEventId = simulateEventId || selectedLifecycleEvent?.event_id || selectedEventId || eventOptions[0]?.event_id || ''
  const effectiveEventId = selectedEventId || eventOptions[0]?.event_id || ''
  const persistedEntryQuery = useQuery({ queryKey: ['event-entry-list', effectiveEventId], queryFn: () => getEventEntryList(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const persistedDrawQuery = useQuery({ queryKey: ['event-draw-package', effectiveEventId], queryFn: () => getEventDrawPackage(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const persistedMatchQuery = useQuery({ queryKey: ['event-match-package', effectiveEventId], queryFn: () => getEventMatchPackage(effectiveEventId), enabled: Boolean(effectiveEventId), retry: false })
  const progressionStatusQuery = useQuery({ queryKey: ['event-progression-status', effectiveEventId], queryFn: () => getEventProgressionStatus(effectiveEventId), enabled: Boolean(effectiveEventId && (matchResult?.match_package_exists || persistedMatchQuery.data?.match_package_exists)), retry: false })
  const persistedResultQuery = useQuery({ queryKey: ['event-result-package', effectiveEventId], queryFn: () => getEventResultPackage(effectiveEventId), enabled: Boolean(effectiveEventId && (matchResult?.match_package_exists || persistedMatchQuery.data?.match_package_exists)), retry: false })
  const persistedPointAwardsQuery = useQuery({ queryKey: ['event-point-awards', effectiveEventId], queryFn: () => getEventPointAwards(effectiveEventId), enabled: Boolean(effectiveEventId && (eventResult?.result_package_exists || persistedResultQuery.data?.result_package_exists)), retry: false })
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
  const displayedProgressionStatus: TournamentProgressionStatus | null = progressionResult?.progression_status ?? progressionStatusQuery.data ?? null
  const progressionWarnings = progressionResult?.validation_warnings ?? displayedProgressionStatus?.warnings ?? []
  const progressionErrors = progressionResult?.validation_errors ?? displayedProgressionStatus?.errors ?? []
  const selectedEventHasPersistedMatchPackage = Boolean(displayedMatchResult?.match_package_exists || displayedMatchPackage)
  const displayedEventResult = eventResult ?? persistedResultQuery.data ?? null
  const displayedResultPackage = displayedEventResult?.result_package ?? null
  const displayedResultSummary = displayedEventResult?.summary ?? displayedResultPackage?.summary ?? null
  const resultWarnings = displayedEventResult?.validation_warnings ?? displayedResultPackage?.validation_warnings ?? []
  const resultErrors = displayedEventResult?.validation_errors ?? displayedResultPackage?.validation_errors ?? []
  const selectedEventHasPersistedResultPackage = Boolean(displayedEventResult?.result_package_exists || displayedResultPackage?.persisted || persistedResultQuery.data?.result_package_exists)
  const displayedPointAwardsResult = pointAwardsResult ?? persistedPointAwardsQuery.data ?? null
  const displayedPointAwardPackage = displayedPointAwardsResult?.award_package ?? null
  const displayedPointSummary = displayedPointAwardsResult?.summary ?? displayedPointAwardPackage?.summary ?? null
  const pointWarnings = displayedPointAwardsResult?.validation_warnings ?? displayedPointAwardPackage?.validation_warnings ?? []
  const pointErrors = displayedPointAwardsResult?.validation_errors ?? displayedPointAwardPackage?.validation_errors ?? []


  const resultMutation = useMutation({
    mutationFn: (persist: boolean) => extractEventResultPackage(effectiveEventId, {
      seed: resultSeed,
      dry_run: !persist,
      overwrite_existing: resultOverwriteExisting
    }),
    onSuccess: (result) => {
      setEventResult(result)
      if (!result.metadata?.dry_run && effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-result-package', effectiveEventId] })
        void queryClient.invalidateQueries({ queryKey: ['event-point-awards', effectiveEventId] })
      }
    }
  })

  const pointGenerateMutation = useMutation({
    mutationFn: (persist: boolean) => generateEventPointAwards(effectiveEventId, {
      seed: pointSeed,
      dry_run: !persist,
      overwrite_existing: pointOverwriteExisting
    }),
    onSuccess: (result) => {
      setPointAwardsResult(result)
      if (!result.metadata?.dry_run && effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-point-awards', effectiveEventId] })
      }
    }
  })

  const pointApplyMutation = useMutation({
    mutationFn: () => applyEventPointAwards(effectiveEventId, { seed: pointSeed, allow_reapply: false }),
    onSuccess: (result) => {
      setPointApplyResult(result)
      setPointAwardsResult({
        award_package: result.award_package,
        summary: result.award_package?.summary ?? null,
        metadata: result.metadata,
        validation_warnings: result.validation_warnings,
        validation_errors: result.validation_errors,
        award_package_exists: Boolean(result.award_package),
        applied: result.applied
      })
      if (effectiveEventId) {
        void queryClient.invalidateQueries({ queryKey: ['event-point-awards', effectiveEventId] })
        void queryClient.invalidateQueries({ queryKey: ['season-active-players', season] })
      }
    }
  })

  const onProgressionSuccess = (result: ProgressionCommandResult) => {
    setProgressionResult(result)
    setMatchResult({
      match_package: result.match_package,
      summary: result.match_package.summary,
      metadata: result.match_package.metadata,
      validation_warnings: result.match_package.validation_warnings,
      validation_errors: result.match_package.validation_errors,
      match_package_exists: true
    })
    if (effectiveEventId) {
      void queryClient.invalidateQueries({ queryKey: ['event-match-package', effectiveEventId] })
      void queryClient.invalidateQueries({ queryKey: ['event-progression-status', effectiveEventId] })
      void queryClient.invalidateQueries({ queryKey: ['event-result-package', effectiveEventId] })
    }
  }

  const refreshProgressionMutation = useMutation({ mutationFn: () => refreshEventProgression(effectiveEventId, { seed: progressionSeed }), onSuccess: onProgressionSuccess })
  const processByesMutation = useMutation({ mutationFn: () => processEventByes(effectiveEventId, { seed: progressionSeed }), onSuccess: onProgressionSuccess })
  const promoteQualifiersMutation = useMutation({ mutationFn: () => promoteEventQualifiers(effectiveEventId, { seed: progressionSeed }), onSuccess: onProgressionSuccess })
  const simulateRoundMutation = useMutation({ mutationFn: () => simulateEventRound(effectiveEventId, { seed: progressionSeed, draw_type: progressionDrawType, round_number: progressionRoundNumber }), onSuccess: onProgressionSuccess })
  const simulateDrawMutation = useMutation({ mutationFn: () => simulateEventDraw(effectiveEventId, { seed: progressionSeed, draw_type: progressionDrawType }), onSuccess: onProgressionSuccess })

  const weekPreflightMutation = useMutation({
    mutationFn: () => preflightSeasonWeek({
      season: weekPreflightSeason || season,
      season_week: weekPreflightWeek,
      seed: weekPreflightSeed,
      apply_points: weekPreflightApplyPoints,
      publish_snapshot: weekPreflightPublishSnapshot,
      overwrite_existing: weekPreflightOverwriteExisting,
      include_not_entered: false,
      max_alternates: weekPreflightMaxAlternates,
      simulate_draw_type: weekPreflightDrawType,
      max_steps_per_event: weekPreflightMaxSteps,
      stop_after_stage: null,
      allow_blocked: weekPreflightAllowBlocked,
      allow_incomplete_results: weekPreflightAllowIncomplete,
      event_id_filter: weekPreflightEventFilter.split(',').map((item) => item.trim()).filter(Boolean),
      include_completed_events: weekPreflightIncludeCompleted
    }),
    onSuccess: (result) => {
      setWeekPreflightResult(result)
      setSelectedWeekPreflightEventId(result.events[0]?.event_id ?? '')
    }
  })

  const simulateOneEventMutation = useMutation({
    mutationFn: (dryRunOverride: boolean) => simulateOneEvent(simulateTargetEventId, {
      seed: simulateSeed,
      dry_run: dryRunOverride,
      overwrite_existing: simulateOverwriteExisting,
      max_steps: simulateMaxSteps,
      stop_after_stage: null,
      apply_points: simulateApplyPoints,
      publish_snapshot: simulatePublishSnapshot,
      allow_incomplete_results: false,
      allow_blocked: false,
      include_not_entered: simulateIncludeNotEntered,
      max_alternates: simulateMaxAlternates,
      simulate_draw_type: simulateDrawType
    }),
    onSuccess: (result) => {
      setSimulateReport(result.report)
      if (!result.report?.dry_run) {
        void queryClient.invalidateQueries({ queryKey: ['season-lifecycle', season] })
        void queryClient.invalidateQueries({ queryKey: ['event-entry-list', simulateTargetEventId] })
        void queryClient.invalidateQueries({ queryKey: ['event-draw-package', simulateTargetEventId] })
        void queryClient.invalidateQueries({ queryKey: ['event-match-package', simulateTargetEventId] })
        void queryClient.invalidateQueries({ queryKey: ['event-result-package', simulateTargetEventId] })
        void queryClient.invalidateQueries({ queryKey: ['event-point-awards', simulateTargetEventId] })
        void queryClient.invalidateQueries({ queryKey: ['season-active-players', season] })
      }
    }
  })

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


      <SectionCard title="Event Lifecycle">
        <p className="status">Lifecycle is a read-only status derived from persisted event artifacts. It does not generate entries, simulate matches, apply points, or publish rankings.</p>
        <div className="grid">
          <label>Lifecycle event filter<input value={lifecycleEventFilter} onChange={(event) => setLifecycleEventFilter(event.target.value)} placeholder="event_id or name" /></label>
          <label>Lifecycle stage filter<select value={lifecycleStageFilter} onChange={(event) => setLifecycleStageFilter(event.target.value)}><option value="">All stages</option>{lifecycleStages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}</select></label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => void lifecycleQuery.refetch()} disabled={lifecycleQuery.isFetching}>Load lifecycle</button>
        </div>
        {lifecycleQuery.isError ? <p role="alert" className="error">{formatApiError(lifecycleQuery.error)}</p> : null}
        {lifecycleQuery.data?.validation_errors.map((error) => <p key={error} role="alert" className="error">{error}</p>)}
        <SummaryPills items={[
          { label: 'Events', value: lifecycleQuery.data?.summary.event_count ?? 0 },
          { label: 'Planned', value: lifecycleQuery.data?.summary.planned_count ?? 0 },
          { label: 'Entries generated', value: lifecycleQuery.data?.summary.entries_generated_count ?? 0 },
          { label: 'Draws generated', value: lifecycleQuery.data?.summary.draw_generated_count ?? 0 },
          { label: 'Matches generated', value: lifecycleQuery.data?.summary.matches_generated_count ?? 0 },
          { label: 'In progress', value: lifecycleQuery.data?.summary.in_progress_count ?? 0 },
          { label: 'Completed', value: lifecycleQuery.data?.summary.completed_count ?? 0 },
          { label: 'Results extracted', value: lifecycleQuery.data?.summary.results_extracted_count ?? 0 },
          { label: 'Points applied', value: lifecycleQuery.data?.summary.points_applied_count ?? 0 },
          { label: 'Snapshots published', value: lifecycleQuery.data?.summary.ranking_snapshot_published_count ?? 0 },
          { label: 'Blocked', value: lifecycleQuery.data?.summary.blocked_count ?? 0 }
        ]} />
        <div className="table-wrap">
          <table aria-label="Event lifecycle table">
            <thead><tr><th>Season week</th><th>Year week</th><th>Event</th><th>Category</th><th>Tour</th><th>Stage</th><th>Next action</th><th>Blocked</th><th>Entries</th><th>Draw</th><th>Matches</th><th>Results</th><th>Points</th><th>Snapshot</th></tr></thead>
            <tbody>{displayedLifecycleEvents.map((event) => <EventLifecycleRow key={event.event_id} event={event} selected={selectedLifecycleEvent?.event_id === event.event_id} onSelect={() => setSelectedLifecycleEventId(event.event_id)} />)}</tbody>
          </table>
        </div>
        {lifecycleQuery.data && !displayedLifecycleEvents.length ? <p className="status">No lifecycle events match the current filters.</p> : null}
        {selectedLifecycleEvent ? <EventLifecycleDetail event={selectedLifecycleEvent} /> : <p className="status">Load lifecycle to inspect persisted artifact status for each calendar event.</p>}
      </SectionCard>

      <SectionCard title="Simulate One Event">
        <p className="status">This command orchestrates existing backend services for one event. It does not simulate a full week or full season. Applying points and publishing snapshots are opt-in.</p>
        <div className="grid">
          <label>Simulation event_id<input value={simulateTargetEventId} onChange={(event) => setSimulateEventId(event.target.value)} placeholder="event_id" /></label>
          <label>Simulation seed<input type="number" value={simulateSeed} onChange={(event) => setSimulateSeed(Number(event.target.value))} /></label>
          <label>Max steps<input type="number" value={simulateMaxSteps} onChange={(event) => setSimulateMaxSteps(Number(event.target.value))} /></label>
          <label>Max alternates<input type="number" value={simulateMaxAlternates} onChange={(event) => setSimulateMaxAlternates(Number(event.target.value))} /></label>
          <label>Simulate draw type<select value={simulateDrawType} onChange={(event) => setSimulateDrawType(event.target.value as SimulateOneEventDrawType)}><option value="qualification_then_main">qualification_then_main</option><option value="qualification">qualification</option><option value="main">main</option></select></label>
          <label><input type="checkbox" checked={simulateDryRun} onChange={(event) => setSimulateDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={simulateOverwriteExisting} onChange={(event) => setSimulateOverwriteExisting(event.target.checked)} /> Overwrite existing artifacts</label>
          <label><input type="checkbox" checked={simulateApplyPoints} onChange={(event) => setSimulateApplyPoints(event.target.checked)} /> Apply points</label>
          <label><input type="checkbox" checked={simulatePublishSnapshot} onChange={(event) => setSimulatePublishSnapshot(event.target.checked)} /> Publish ranking snapshot</label>
          <label><input type="checkbox" checked={simulateIncludeNotEntered} onChange={(event) => setSimulateIncludeNotEntered(event.target.checked)} /> Include not-entered players</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setSimulateDryRun(true); simulateOneEventMutation.mutate(true) }} disabled={!simulateTargetEventId || simulateOneEventMutation.isPending}>Preview event simulation</button>
          <button type="button" onClick={() => { setSimulateDryRun(false); simulateOneEventMutation.mutate(false) }} disabled={!simulateTargetEventId || simulateOneEventMutation.isPending}>Run event simulation</button>
        </div>
        {simulateOneEventMutation.isError ? <p role="alert" className="error">{formatApiError(simulateOneEventMutation.error)}</p> : null}
        {simulateOneEventMutation.data?.validation_errors.map((error) => <p key={error} role="alert" className="error">{error}</p>)}
        {simulateOneEventMutation.data?.validation_warnings.map((warning) => <p key={warning} className="status">{warning}</p>)}
        {simulateReport ? <SimulateOneEventReportPanel report={simulateReport} /> : <p className="status">Preview or run the one-event orchestration command to see a step-by-step report.</p>}
      </SectionCard>

      <SectionCard title="Simulate One Season Week — Preflight">
        <p className="status">This is preflight only. It calls one-event dry-run planning for each event and does not mutate entries, draws, matches, points, or snapshots.</p>
        <div className="grid">
          <label>Season<input value={weekPreflightSeason} onChange={(event) => setWeekPreflightSeason(event.target.value)} /></label>
          <label>Season week<input type="number" min={1} max={61} value={weekPreflightWeek} onChange={(event) => setWeekPreflightWeek(Number(event.target.value))} /></label>
          <label>Seed<input type="number" value={weekPreflightSeed} onChange={(event) => setWeekPreflightSeed(Number(event.target.value))} /></label>
          <label>Max steps per event<input type="number" value={weekPreflightMaxSteps} onChange={(event) => setWeekPreflightMaxSteps(Number(event.target.value))} /></label>
          <label>Week max alternates<input type="number" value={weekPreflightMaxAlternates} onChange={(event) => setWeekPreflightMaxAlternates(Number(event.target.value))} /></label>
          <label>Week simulate draw type<select value={weekPreflightDrawType} onChange={(event) => setWeekPreflightDrawType(event.target.value as SimulateOneEventDrawType)}><option value="qualification_then_main">qualification_then_main</option><option value="qualification">qualification</option><option value="main">main</option></select></label>
          <label>Event ID filter<input value={weekPreflightEventFilter} onChange={(event) => setWeekPreflightEventFilter(event.target.value)} placeholder="event_id,event_id" /></label>
          <label><input type="checkbox" checked={weekPreflightApplyPoints} onChange={(event) => setWeekPreflightApplyPoints(event.target.checked)} /> Week apply points</label>
          <label><input type="checkbox" checked={weekPreflightPublishSnapshot} onChange={(event) => setWeekPreflightPublishSnapshot(event.target.checked)} /> Week publish snapshot</label>
          <label><input type="checkbox" checked={weekPreflightOverwriteExisting} onChange={(event) => setWeekPreflightOverwriteExisting(event.target.checked)} /> Week overwrite existing</label>
          <label><input type="checkbox" checked={weekPreflightIncludeCompleted} onChange={(event) => setWeekPreflightIncludeCompleted(event.target.checked)} /> Include completed events</label>
          <label><input type="checkbox" checked={weekPreflightAllowBlocked} onChange={(event) => setWeekPreflightAllowBlocked(event.target.checked)} /> Allow blocked</label>
          <label><input type="checkbox" checked={weekPreflightAllowIncomplete} onChange={(event) => setWeekPreflightAllowIncomplete(event.target.checked)} /> Allow incomplete results</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => weekPreflightMutation.mutate()} disabled={weekPreflightMutation.isPending}>Preview week simulation</button>
        </div>
        {weekPreflightMutation.isError ? <p role="alert" className="error">{formatApiError(weekPreflightMutation.error)}</p> : null}
        {weekPreflightResult ? <SeasonWeekPreflightPanel result={weekPreflightResult} selectedEventId={selectedWeekPreflightEventId} onSelectEvent={setSelectedWeekPreflightEventId} /> : <p className="status">Preview a season week to inspect backend-produced dry-run plans for persisted calendar events.</p>}
      </SectionCard>


      <SectionCard title="Event Entries">
        <p className="status">Entry generation selects players for a planned calendar event from active season players. It does not create draws or simulate matches yet.</p>
        {!eventOptions.length ? <p className="status">Persist a season calendar first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setProgressionResult(null); setEventResult(null); setPointAwardsResult(null); setPointApplyResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
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
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setProgressionResult(null); setEventResult(null); setPointAwardsResult(null); setPointApplyResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
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
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setProgressionResult(null); setEventResult(null); setPointAwardsResult(null); setPointApplyResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Match seed<input type="number" value={matchSeed} onChange={(event) => setMatchSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={matchDryRun} onChange={(event) => setMatchDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={matchOverwriteExisting} onChange={(event) => setMatchOverwriteExisting(event.target.checked)} /> Overwrite existing match package</label>
          <label>Selected match<select value={selectedMatchId} onChange={(event) => setSelectedMatchId(event.target.value)} disabled={!displayedMatches.length}><option value="">Choose a match</option>{displayedMatches.map((match) => <option key={match.match_id} value={match.match_id}>{match.status}: {match.match_id}</option>)}</select></label>
          <label>Progression seed<input type="number" value={progressionSeed} onChange={(event) => setProgressionSeed(Number(event.target.value))} /></label>
          <label>Progression draw<select value={progressionDrawType} onChange={(event) => setProgressionDrawType(event.target.value as 'qualification' | 'main')}><option value="qualification">Qualification</option><option value="main">Main draw</option></select></label>
          <label>Round number<input type="number" min={1} value={progressionRoundNumber} onChange={(event) => setProgressionRoundNumber(Number(event.target.value))} /></label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setMatchDryRun(true); matchMutation.mutate(false) }} disabled={!effectiveEventId || !selectedEventHasPersistedDrawPackage || matchMutation.isPending}>Preview match package</button>
          <button type="button" onClick={() => { setMatchDryRun(false); matchMutation.mutate(true) }} disabled={!effectiveEventId || !selectedEventHasPersistedDrawPackage || matchMutation.isPending}>Persist match package</button>
          <button type="button" onClick={() => simulateNextMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || simulateNextMutation.isPending}>Simulate next pending match</button>
          <button type="button" onClick={() => simulateSelectedMutation.mutate()} disabled={!effectiveEventId || !selectedMatchId || !displayedMatchResult?.match_package_exists || simulateSelectedMutation.isPending}>Simulate selected match</button>
          <button type="button" onClick={() => refreshProgressionMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || refreshProgressionMutation.isPending}>Refresh progression</button>
          <button type="button" onClick={() => processByesMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || processByesMutation.isPending}>Process BYEs</button>
          <button type="button" onClick={() => promoteQualifiersMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || promoteQualifiersMutation.isPending}>Promote qualifiers</button>
          <button type="button" onClick={() => simulateRoundMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || simulateRoundMutation.isPending}>Simulate round</button>
          <button type="button" onClick={() => simulateDrawMutation.mutate()} disabled={!effectiveEventId || !displayedMatchResult?.match_package_exists || simulateDrawMutation.isPending}>Simulate draw</button>
        </div>
        <p className="status">Progression commands update match states and propagate winners. They do not update ranking/race yet.</p>
        {matchMutation.isError ? <p role="alert" className="error">{formatApiError(matchMutation.error)}</p> : null}
        {simulateNextMutation.isError ? <p role="alert" className="error">{formatApiError(simulateNextMutation.error)}</p> : null}
        {simulateSelectedMutation.isError ? <p role="alert" className="error">{formatApiError(simulateSelectedMutation.error)}</p> : null}
        {persistedMatchQuery.isError ? <p role="alert" className="error">{formatApiError(persistedMatchQuery.error)}</p> : null}
        {progressionStatusQuery.isError ? <p role="alert" className="error">{formatApiError(progressionStatusQuery.error)}</p> : null}
        {refreshProgressionMutation.isError ? <p role="alert" className="error">{formatApiError(refreshProgressionMutation.error)}</p> : null}
        {processByesMutation.isError ? <p role="alert" className="error">{formatApiError(processByesMutation.error)}</p> : null}
        {promoteQualifiersMutation.isError ? <p role="alert" className="error">{formatApiError(promoteQualifiersMutation.error)}</p> : null}
        {simulateRoundMutation.isError ? <p role="alert" className="error">{formatApiError(simulateRoundMutation.error)}</p> : null}
        {simulateDrawMutation.isError ? <p role="alert" className="error">{formatApiError(simulateDrawMutation.error)}</p> : null}
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
        {displayedProgressionStatus ? <ProgressionStatusPanel status={displayedProgressionStatus} warnings={progressionWarnings} errors={progressionErrors} /> : <p className="status">No persisted progression status yet. Persist a match package to enable progression commands.</p>}
        {progressionResult ? <p className="status">Last progression action: {progressionResult.action}; changed matches: {progressionResult.changed_match_ids.length}; promoted players: {progressionResult.promoted_player_ids.join(', ') || '—'}.</p> : null}
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


      <SectionCard title="Event Results">
        <p className="status">Result extraction summarizes completed tournament outcomes. Point awards are generated and applied explicitly in the Ranking / Race Points section.</p>
        {!eventOptions.length ? <p className="status">Persist a season calendar first.</p> : null}
        {eventOptions.length && !selectedEventHasPersistedMatchPackage ? <p className="status">Persist and progress a match package first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setEntryResult(null); setDrawResult(null); setMatchResult(null); setProgressionResult(null); setEventResult(null); setPointAwardsResult(null); setPointApplyResult(null); setSelectedMatchId('') }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Result seed<input type="number" value={resultSeed} onChange={(event) => setResultSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={resultDryRun} onChange={(event) => setResultDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={resultOverwriteExisting} onChange={(event) => setResultOverwriteExisting(event.target.checked)} /> Overwrite existing result package</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setResultDryRun(true); resultMutation.mutate(false) }} disabled={!effectiveEventId || !selectedEventHasPersistedMatchPackage || resultMutation.isPending}>Preview results</button>
          <button type="button" onClick={() => { setResultDryRun(false); resultMutation.mutate(true) }} disabled={!effectiveEventId || !selectedEventHasPersistedMatchPackage || resultMutation.isPending}>Persist results</button>
        </div>
        {resultMutation.isError ? <p role="alert" className="error">{formatApiError(resultMutation.error)}</p> : null}
        {persistedResultQuery.isError ? <p role="alert" className="error">{formatApiError(persistedResultQuery.error)}</p> : null}
        <SummaryPills items={[
          { label: 'Completion status', value: displayedResultSummary?.completion_status ?? '—' },
          { label: 'Champion', value: displayedResultPackage?.champion?.player_name ?? displayedResultSummary?.champion_player_id ?? '—' },
          { label: 'Finalist', value: displayedResultPackage?.finalist?.player_name ?? displayedResultSummary?.finalist_player_id ?? '—' },
          { label: 'Players', value: displayedResultSummary?.player_count ?? 0 },
          { label: 'Completed matches', value: displayedResultSummary?.completed_matches ?? 0 },
          { label: 'Incomplete matches', value: displayedResultSummary?.incomplete_matches ?? 0 },
          { label: 'Qualification winners', value: displayedResultSummary?.qualification_winner_count ?? 0 },
          { label: 'Validation warnings/errors', value: `${displayedResultSummary?.validation_warning_count ?? resultWarnings.length}/${displayedResultSummary?.validation_error_count ?? resultErrors.length}` },
          { label: 'Points awarded', value: displayedResultSummary?.ranking_points_awarded_total ?? 0 }
        ]} />
        {displayedEventResult?.metadata ? <MetadataList items={[
          { label: 'Build fingerprint', value: displayedEventResult.metadata.build_fingerprint },
          { label: 'Match package fingerprint', value: displayedEventResult.metadata.match_package_fingerprint ?? '—' },
          { label: 'Draw package fingerprint', value: displayedEventResult.metadata.draw_package_fingerprint ?? '—' },
          { label: 'Calendar event fingerprint', value: displayedEventResult.metadata.calendar_event_fingerprint ?? '—' },
          { label: 'Ranking updates', value: displayedEventResult.metadata.ranking_updates_implemented ? 'Implemented' : 'Not implemented yet' },
          { label: 'Points awarding', value: displayedEventResult.metadata.points_awarding_implemented ? 'Implemented' : 'Not implemented yet' }
        ]} /> : null}
        <ResultValidationPanel warnings={resultWarnings} errors={resultErrors} />
        {displayedResultPackage ? <>
          <TopFinishersTable champion={displayedResultPackage.champion} finalist={displayedResultPackage.finalist} semifinalists={displayedResultPackage.semifinalists} quarterfinalists={displayedResultPackage.quarterfinalists} />
          <QualificationWinnersTable winners={displayedResultPackage.qualification_winners} playerResults={displayedResultPackage.player_results} />
          <PlayerResultsTable results={displayedResultPackage.player_results} />
        </> : <p className="status">No result package is displayed yet. Preview or persist results after progressing matches.</p>}
      </SectionCard>


      <SectionCard title="Ranking / Race Points">
        <p className="status">Point awarding uses persisted event results. Applying points mutates active season player ranking/race points. Rolling 61-week ranking and best-N logic are not implemented yet.</p>
        {!selectedEventHasPersistedResultPackage ? <p className="status">Persist event results first.</p> : null}
        <div className="grid">
          <label>Selected event<select value={effectiveEventId} onChange={(event) => { setSelectedEventId(event.target.value); setPointAwardsResult(null); setPointApplyResult(null) }} disabled={!eventOptions.length}>{eventOptions.map((event) => <option key={event.event_id} value={event.event_id}>{event.season_week}: {event.event_name} ({event.event_id})</option>)}</select></label>
          <label>Point seed<input type="number" value={pointSeed} onChange={(event) => setPointSeed(Number(event.target.value))} /></label>
          <label><input type="checkbox" checked={pointDryRun} onChange={(event) => setPointDryRun(event.target.checked)} /> Dry run default</label>
          <label><input type="checkbox" checked={pointOverwriteExisting} onChange={(event) => setPointOverwriteExisting(event.target.checked)} /> Overwrite existing point awards</label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => { setPointDryRun(true); pointGenerateMutation.mutate(false) }} disabled={!effectiveEventId || !selectedEventHasPersistedResultPackage || pointGenerateMutation.isPending}>Preview point awards</button>
          <button type="button" onClick={() => { setPointDryRun(false); pointGenerateMutation.mutate(true) }} disabled={!effectiveEventId || !selectedEventHasPersistedResultPackage || pointGenerateMutation.isPending}>Persist point awards</button>
          <button type="button" onClick={() => pointApplyMutation.mutate()} disabled={!effectiveEventId || !displayedPointAwardPackage?.persisted || displayedPointAwardPackage.applied || pointApplyMutation.isPending}>Apply points to active players</button>
        </div>
        {pointGenerateMutation.isError ? <p role="alert" className="error">{formatApiError(pointGenerateMutation.error)}</p> : null}
        {pointApplyMutation.isError ? <p role="alert" className="error">{formatApiError(pointApplyMutation.error)}</p> : null}
        {persistedPointAwardsQuery.isError ? <p role="alert" className="error">{formatApiError(persistedPointAwardsQuery.error)}</p> : null}
        <SummaryPills items={[
          { label: 'Players', value: displayedPointSummary?.player_count ?? 0 },
          { label: 'Awarded players', value: displayedPointSummary?.awarded_player_count ?? 0 },
          { label: 'Ranking points', value: displayedPointSummary?.total_ranking_points ?? 0 },
          { label: 'Race points', value: displayedPointSummary?.total_race_points ?? 0 },
          { label: 'Champion points', value: displayedPointSummary?.champion_points ?? 0 },
          { label: 'Finalist points', value: displayedPointSummary?.finalist_points ?? 0 },
          { label: 'Applied', value: displayedPointSummary?.applied ? 'yes' : 'no' },
          { label: 'Validation warnings/errors', value: `${displayedPointSummary?.validation_warning_count ?? pointWarnings.length}/${displayedPointSummary?.validation_error_count ?? pointErrors.length}` }
        ]} />
        {displayedPointAwardsResult?.metadata ? <MetadataList items={[
          { label: 'Build fingerprint', value: displayedPointAwardsResult.metadata.build_fingerprint },
          { label: 'Result package fingerprint', value: displayedPointAwardsResult.metadata.result_package_fingerprint },
          { label: 'Distribution fingerprint', value: displayedPointAwardsResult.metadata.point_distribution_fingerprint },
          { label: 'Distribution source', value: displayedPointAwardsResult.metadata.point_distribution_source },
          { label: 'Rolling ranking', value: displayedPointAwardsResult.metadata.rolling_ranking_implemented ? 'Implemented' : 'Not implemented yet' },
          { label: 'Best-N', value: displayedPointAwardsResult.metadata.best_n_implemented ? 'Implemented' : 'Not implemented yet' }
        ]} /> : null}
        <PointValidationPanel warnings={pointWarnings} errors={pointErrors} />
        {displayedPointAwardPackage ? <PointAwardsTable awards={displayedPointAwardPackage.awards} /> : <p className="status">No point award package is displayed yet. Preview or persist awards after event results are persisted.</p>}
        {pointApplyResult ? <UpdatedPointsTable updates={pointApplyResult.updated_players} /> : null}
      </SectionCard>

      <AdminRankingTablesSection />


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


function ProgressionStatusPanel({ status, warnings, errors }: { status: TournamentProgressionStatus; warnings: MatchValidationIssue[]; errors: MatchValidationIssue[] }): JSX.Element {
  return <div>
    <h4>Progression status</h4>
    <SummaryPills items={[
      { label: 'Event status', value: status.event_status },
      { label: 'Qualification', value: status.qualification_status },
      { label: 'Main draw', value: status.main_draw_status },
      { label: 'Pending', value: status.pending_matches },
      { label: 'Blocked', value: status.blocked_matches },
      { label: 'Completed', value: status.completed_matches },
      { label: 'BYEs pending', value: status.bye_auto_advances_pending },
      { label: 'Qual winners ready', value: status.qualification_winners_ready ? 'yes' : 'no' },
      { label: 'Qual winners promoted', value: status.qualification_winners_promoted ? 'yes' : 'no' },
      { label: 'Champion', value: status.champion_name ?? status.champion_player_id ?? '—' },
      { label: 'Finalist', value: status.finalist_name ?? status.finalist_player_id ?? '—' }
    ]} />
    <MatchValidationPanel warnings={warnings} errors={errors} />
  </div>
}

function MatchValidationPanel({ warnings, errors }: { warnings: MatchValidationIssue[]; errors: MatchValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Match errors</h4><ul>{errors.map((issue) => <li key={`match-error-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No match validation errors.</p>}
    {warnings.length ? <><h4>Match warnings</h4><ul>{warnings.map((issue) => <li key={`match-warning-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No match validation warnings.</p>}
  </div>
}


function SeasonWeekPreflightPanel({ result, selectedEventId, onSelectEvent }: { result: SimulateSeasonWeekPreflightResult; selectedEventId: string; onSelectEvent: (eventId: string) => void }): JSX.Element {
  const selected = result.events.find((event) => event.event_id === selectedEventId) ?? result.events[0] ?? null
  return <div>
    <h4>Week preflight summary</h4>
    {result.validation_errors.map((error) => <p key={error} role="alert" className="error">{error}</p>)}
    {result.validation_warnings.map((warning) => <p key={warning} className="status">{warning}</p>)}
    <SummaryPills items={[
      { label: 'Event count', value: result.summary.event_count },
      { label: 'Blocked events', value: result.summary.blocked_event_count },
      { label: 'Can run week', value: result.summary.can_run_week ? 'yes' : 'no' },
      { label: 'Would apply points', value: result.summary.would_apply_points ? 'yes' : 'no' },
      { label: 'Would publish snapshot', value: result.summary.would_publish_snapshot ? 'yes' : 'no' },
      { label: 'Snapshot already exists', value: result.summary.snapshot_already_exists ? 'yes' : 'no' },
      { label: 'Total planned steps', value: result.summary.total_planned_steps },
      { label: 'Stop reason', value: result.summary.stop_reason ?? '—' },
      { label: 'Next safe action', value: result.summary.next_safe_action ?? '—' }
    ]} />
    <MetadataList items={[
      { label: 'Season week / year week', value: `${result.season_week} / ${result.calendar_year ?? '—'}-${result.year_week ?? '—'}` },
      { label: 'Read only', value: result.metadata.read_only ? 'yes' : 'no' },
      { label: 'Source', value: result.metadata.source },
      { label: 'Generated fingerprint', value: shortFingerprint(result.metadata.generated_fingerprint) }
    ]} />
    <div className="table-wrap">
      <table aria-label="Season week preflight events table">
        <thead><tr><th>Season/year week</th><th>Event</th><th>Category/tour</th><th>Lifecycle before</th><th>Next action before</th><th>Stop reason</th><th>Planned steps</th><th>Blocked</th><th>Can continue</th><th>Planned player mutation</th><th>Planned snapshot mutation</th></tr></thead>
        <tbody>{result.events.map((event) => <SeasonWeekPreflightEventRow key={event.event_id} event={event} selected={selected?.event_id === event.event_id} onSelect={() => onSelectEvent(event.event_id)} />)}</tbody>
      </table>
    </div>
    {!result.events.length ? <p className="status">No persisted calendar events are included in this week preflight.</p> : null}
    {selected ? <div><h4>Selected event dry-run detail</h4><SimulateOneEventReportPanel report={selected.one_event_report} /></div> : null}
  </div>
}

function SeasonWeekPreflightEventRow({ event, selected, onSelect }: { event: SeasonWeekEventPreflight; selected: boolean; onSelect: () => void }): JSX.Element {
  return <tr aria-selected={selected} onClick={onSelect}>
    <td>{event.season_week} / {event.calendar_year ?? '—'}-{event.year_week ?? '—'}</td>
    <td><button type="button" onClick={onSelect}>{event.event_name}</button><br /><span className="muted">{event.event_id}</span></td>
    <td>{event.category} / {event.tour_level ?? '—'}</td>
    <td>{event.lifecycle_stage_before ?? '—'}</td>
    <td>{event.next_recommended_action_before ?? '—'}</td>
    <td>{event.stop_reason ?? '—'}</td>
    <td>{event.planned_step_count}</td>
    <td>{event.blocked ? 'yes' : 'no'}</td>
    <td>{event.can_continue ? 'yes' : 'no'}</td>
    <td>{event.planned_mutates_active_players ? 'yes' : 'no'}</td>
    <td>{event.planned_mutates_ranking_snapshot ? 'yes' : 'no'}</td>
  </tr>
}

function SimulateOneEventReportPanel({ report }: { report: SimulateOneEventReport }): JSX.Element {
  const changedEntries = Object.entries(report.changed_artifacts).filter(([, value]) => value).map(([key]) => key)
  const changed = changedEntries.join(', ') || 'none'
  const artifactRows: Array<[string, boolean, boolean]> = [
    ['Entries', report.artifact_state_before.entries_exists, report.artifact_state_after.entries_exists],
    ['Draw', report.artifact_state_before.draw_exists, report.artifact_state_after.draw_exists],
    ['Matches', report.artifact_state_before.matches_exists, report.artifact_state_after.matches_exists],
    ['Results', report.artifact_state_before.results_exists, report.artifact_state_after.results_exists],
    ['Point awards', report.artifact_state_before.point_awards_exists, report.artifact_state_after.point_awards_exists],
    ['Points applied', report.artifact_state_before.points_applied, report.artifact_state_after.points_applied],
    ['Ranking snapshot', report.artifact_state_before.ranking_snapshot_exists, report.artifact_state_after.ranking_snapshot_exists]
  ]
  return <div>
    <h4>Simulation report</h4>
    <p className="status">Point application mutates active season players. Snapshot publication mutates weekly ranking snapshot registry. Dry-run is plan-only.</p>
    <SummaryPills items={[
      { label: 'Initial stage', value: report.lifecycle_stage_before ?? report.initial_lifecycle?.current_stage ?? '—' },
      { label: 'Final stage', value: report.lifecycle_stage_after ?? report.final_lifecycle?.current_stage ?? '—' },
      { label: 'Stop reason', value: report.plan_summary.stop_reason ?? '—' },
      { label: 'Next safe action', value: report.plan_summary.next_safe_action ?? '—' },
      { label: 'Safe to rerun', value: report.safe_to_rerun ? 'yes' : 'no' },
      { label: 'Can continue', value: report.can_continue ? 'yes' : 'no' },
      { label: 'Changed artifact count', value: changedEntries.length },
      { label: 'Completed', value: report.completed ? 'yes' : 'no' },
      { label: 'Blocked', value: report.blocked ? 'yes' : 'no' },
      { label: 'Changed artifacts', value: changed },
      { label: 'Would duplicate points', value: report.would_duplicate_points ? 'yes' : 'no' },
      { label: 'Would overwrite existing', value: report.would_overwrite_existing ? 'yes' : 'no' }
    ]} />
    <SummaryPills items={[
      { label: 'Planned steps', value: report.plan_summary.planned_step_count },
      { label: 'Executed steps', value: report.plan_summary.executed_step_count },
      { label: 'Skipped steps', value: report.plan_summary.skipped_step_count },
      { label: 'Succeeded steps', value: report.plan_summary.succeeded_step_count },
      { label: 'Failed steps', value: report.plan_summary.failed_step_count },
      { label: 'Blocked steps', value: report.plan_summary.blocked_step_count },
      { label: 'First failed step', value: report.plan_summary.first_failed_step ?? '—' },
      { label: 'Final next action', value: report.lifecycle_next_action_after ?? report.final_lifecycle?.next_recommended_action ?? '—' }
    ]} />
    <div className="table-wrap">
      <table aria-label="Simulate one event artifact state table">
        <thead><tr><th>Artifact</th><th>Before</th><th>After</th><th>Changed</th></tr></thead>
        <tbody>{artifactRows.map(([label, before, after]) => <tr key={label}><td>{label}</td><td>{boolMark(before)}</td><td>{boolMark(after)}</td><td>{before !== after ? 'yes' : 'no'}</td></tr>)}</tbody>
      </table>
    </div>
    {report.validation_errors.length ? <><h4>Simulation errors</h4><ul>{report.validation_errors.map((error) => <li key={error} className="error">{error}</li>)}</ul></> : null}
    {report.validation_warnings.length ? <><h4>Simulation warnings</h4><ul>{report.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></> : null}
    <div className="table-wrap">
      <table aria-label="Simulate one event steps table">
        <thead><tr><th>Step</th><th>Status</th><th>Detail</th><th>Lifecycle before → after</th><th>Service called</th><th>Seed</th><th>Mutates players</th><th>Mutates snapshot</th><th>Stop reason</th><th>Before</th><th>After</th><th>Changed IDs</th><th>Fingerprint</th><th>Warnings</th><th>Errors</th></tr></thead>
        <tbody>{report.steps.map((step, index) => <tr key={`${step.step}-${index}`}><td>{step.step}</td><td>{step.status}</td><td>{step.action_detail}</td><td>{step.lifecycle_stage_before_step ?? '—'} → {step.lifecycle_stage_after_step ?? '—'}</td><td>{step.service_called ?? '—'}</td><td>{step.request_seed ?? '—'}</td><td>{step.mutates_active_players ? 'yes' : 'no'}</td><td>{step.mutates_ranking_snapshot ? 'yes' : 'no'}</td><td>{step.stop_reason ?? '—'}</td><td>{boolMark(step.artifact_exists_before)}</td><td>{boolMark(step.artifact_exists_after)}</td><td>{step.changed_ids.join(', ') || '—'}</td><td>{step.fingerprint ? step.fingerprint.slice(0, 12) : '—'}</td><td>{step.warnings.join('; ') || '—'}</td><td>{step.errors.join('; ') || '—'}</td></tr>)}</tbody>
      </table>
    </div>
  </div>
}

function boolMark(value: boolean | null): string {
  if (value === null) return '—'
  return value ? 'yes' : 'no'
}

function artifactMark(artifact: { exists: boolean; validation_error_count: number; validation_warning_count: number }): string {
  if (!artifact.exists) return 'missing'
  if (artifact.validation_error_count > 0) return `error (${artifact.validation_error_count})`
  if (artifact.validation_warning_count > 0) return `ok/warn (${artifact.validation_warning_count})`
  return 'ok'
}

function shortFingerprint(value: string | null): string {
  return value ? value.slice(0, 12) : '—'
}

function EventLifecycleRow({ event, selected, onSelect }: { event: EventLifecycleStatus; selected: boolean; onSelect: () => void }): JSX.Element {
  return <tr onClick={onSelect} aria-selected={selected}>
    <td>{event.season_week}</td>
    <td>{event.calendar_year ?? '—'} / {event.year_week ?? '—'}</td>
    <td><button type="button" onClick={onSelect}>{event.event_name}</button><br /><span className="muted">{event.event_id}</span></td>
    <td>{event.category}</td>
    <td>{event.tour_level ?? '—'}</td>
    <td><strong>{event.current_stage}</strong></td>
    <td>{event.next_recommended_action}</td>
    <td>{event.is_blocked ? 'blocked' : 'clear'}</td>
    <td>{artifactMark(event.entries)}</td>
    <td>{artifactMark(event.draw)}</td>
    <td>{artifactMark(event.matches)}</td>
    <td>{artifactMark(event.results)}</td>
    <td>{event.points_applied ? 'applied' : artifactMark(event.point_awards)}</td>
    <td>{artifactMark(event.ranking_snapshot)}</td>
  </tr>
}

function EventLifecycleDetail({ event }: { event: EventLifecycleStatus }): JSX.Element {
  const fingerprints = [
    ['Entries', event.entries.fingerprint],
    ['Draw', event.draw.fingerprint],
    ['Matches', event.matches.fingerprint],
    ['Results', event.results.fingerprint],
    ['Point awards', event.point_awards.fingerprint],
    ['Ranking snapshot', event.ranking_snapshot.fingerprint]
  ]
  return <div>
    <h4>Selected lifecycle detail</h4>
    <MetadataList items={[
      { label: 'Event', value: `${event.event_name} (${event.event_id})` },
      { label: 'Stage', value: event.current_stage },
      { label: 'Next action', value: event.next_recommended_action },
      { label: 'Blocked', value: event.is_blocked ? 'yes' : 'no' },
      { label: 'Points applied', value: event.points_applied ? 'yes' : 'no' },
      ...fingerprints.map(([label, value]) => ({ label: `${label} fingerprint`, value: shortFingerprint(value) }))
    ]} />
    {event.block_reasons.length ? <><h5>Block reasons</h5><ul>{event.block_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></> : <p className="status">No lifecycle blockers detected for this event.</p>}
    {event.validation_warnings.length ? <><h5>Lifecycle warnings</h5><ul>{event.validation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></> : null}
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

function ResultValidationPanel({ warnings, errors }: { warnings: EventResultValidationIssue[]; errors: EventResultValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Result errors</h4><ul>{errors.map((issue) => <li key={`result-error-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No result validation errors.</p>}
    {warnings.length ? <><h4>Result warnings</h4><ul>{warnings.map((issue) => <li key={`result-warning-${issue.code}-${issue.match_id ?? issue.player_id ?? issue.event_id ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No result validation warnings.</p>}
  </div>
}

function TopFinishersTable({ champion, finalist, semifinalists, quarterfinalists }: { champion: PlayerResultSummary | null; finalist: PlayerResultSummary | null; semifinalists: PlayerResultSummary[]; quarterfinalists: PlayerResultSummary[] }): JSX.Element {
  const rows = [
    ...(champion ? [{ label: 'Champion', player: champion }] : []),
    ...(finalist ? [{ label: 'Finalist', player: finalist }] : []),
    ...semifinalists.map((player) => ({ label: 'Semifinalist', player })),
    ...quarterfinalists.map((player) => ({ label: 'Quarterfinalist', player })),
  ]
  return <div className="table-wrap">
    <table aria-label="Event result top finishers table">
      <thead><tr><th>Finish</th><th>Player</th><th>Country</th><th>Seed</th><th>Qualifier</th></tr></thead>
      <tbody>{rows.map(({ label, player }) => <tr key={`${label}-${player.player_id}`}><td>{label}</td><td>{player.player_name ?? player.player_id}</td><td>{player.country_code ?? '—'}</td><td>{player.seed_number ?? '—'}</td><td>{player.qualifier ? 'yes' : 'no'}</td></tr>)}</tbody>
    </table>
    {!rows.length ? <p className="status">No completed podium/top finisher results yet.</p> : null}
  </div>
}

function QualificationWinnersTable({ winners, playerResults }: { winners: PlayerResultSummary[]; playerResults: PlayerEventResult[] }): JSX.Element {
  const byPlayer = new Map(playerResults.map((result) => [result.player_id, result]))
  return <div className="table-wrap">
    <table aria-label="Event result qualification winners table">
      <thead><tr><th>Player</th><th>Country</th><th>Later stage</th></tr></thead>
      <tbody>{winners.map((winner) => <tr key={winner.player_id}><td>{winner.player_name ?? winner.player_id}</td><td>{winner.country_code ?? '—'}</td><td>{byPlayer.get(winner.player_id)?.reached_stage ?? 'qualification_winner'}</td></tr>)}</tbody>
    </table>
    {!winners.length ? <p className="status">No qualification winners extracted yet.</p> : null}
  </div>
}

function PlayerResultsTable({ results }: { results: PlayerEventResult[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Event full player results table">
      <thead><tr><th>Player</th><th>Country</th><th>Qualifier</th><th>Seed</th><th>Reached stage</th><th>Wins</th><th>Losses</th><th>Eliminated by</th><th>Last match</th><th>Ranking points awarded</th><th>Race points awarded</th></tr></thead>
      <tbody>{results.map((result) => <tr key={result.player_id}><td>{result.player_name ?? result.player_id}</td><td>{result.country_code ?? '—'}</td><td>{result.qualifier ? 'yes' : 'no'}</td><td>{result.seed_number ?? '—'}</td><td>{result.reached_stage}</td><td>{result.wins}</td><td>{result.losses}</td><td>{result.eliminated_by_player_name ?? result.eliminated_by_player_id ?? '—'}</td><td>{result.last_match_id ?? '—'}</td><td>{result.points_awarded}</td><td>{result.race_points_awarded}</td></tr>)}</tbody>
    </table>
    {!results.length ? <p className="status">No player results extracted yet.</p> : null}
  </div>
}

function PointValidationPanel({ warnings, errors }: { warnings: PointAwardValidationIssue[]; errors: PointAwardValidationIssue[] }): JSX.Element {
  return <div>
    {errors.length ? <><h4>Point award errors</h4><ul>{errors.map((issue) => <li key={`point-error-${issue.code}-${issue.player_id ?? issue.event_id ?? issue.field ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No point award validation errors.</p>}
    {warnings.length ? <><h4>Point award warnings</h4><ul>{warnings.map((issue) => <li key={`point-warning-${issue.code}-${issue.player_id ?? issue.event_id ?? issue.field ?? 'list'}`}>{issue.code}: {issue.message}</li>)}</ul></> : <p className="status">No point award validation warnings.</p>}
  </div>
}

function PointAwardsTable({ awards }: { awards: PlayerPointAward[] }): JSX.Element {
  return <div className="table-wrap">
    <table aria-label="Event point awards table">
      <thead><tr><th>Player</th><th>Country</th><th>Reached stage</th><th>Qualifier</th><th>Previous ranking</th><th>Ranking awarded</th><th>Projected ranking</th><th>Previous race</th><th>Race awarded</th><th>Projected race</th></tr></thead>
      <tbody>{awards.map((award) => <tr key={award.player_id}><td>{award.player_name ?? award.player_id}</td><td>{award.country_code ?? '—'}</td><td>{award.reached_stage}</td><td>{award.qualifier ? 'yes' : 'no'}</td><td>{award.previous_ranking_points ?? '—'}</td><td>{award.ranking_points_awarded}</td><td>{award.projected_ranking_points ?? '—'}</td><td>{award.previous_race_points ?? '—'}</td><td>{award.race_points_awarded}</td><td>{award.projected_race_points ?? '—'}</td></tr>)}</tbody>
    </table>
    {!awards.length ? <p className="status">No player point awards in this package.</p> : null}
  </div>
}

function UpdatedPointsTable({ updates }: { updates: UpdatedPlayerPoints[] }): JSX.Element {
  return <div className="table-wrap">
    <h4>Applied point updates</h4>
    <table aria-label="Applied point updates table">
      <thead><tr><th>Player</th><th>Previous ranking</th><th>Delta ranking</th><th>New ranking</th><th>Previous race</th><th>Delta race</th><th>New race</th></tr></thead>
      <tbody>{updates.map((update) => <tr key={update.player_id}><td>{update.player_name ?? update.player_id}</td><td>{update.previous_ranking_points}</td><td>{update.delta_ranking_points}</td><td>{update.new_ranking_points}</td><td>{update.previous_race_points}</td><td>{update.delta_race_points}</td><td>{update.new_race_points}</td></tr>)}</tbody>
    </table>
    {!updates.length ? <p className="status">No active-player point updates were returned.</p> : null}
  </div>
}
