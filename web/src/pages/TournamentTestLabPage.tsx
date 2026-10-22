import { HistoricalLabSourcePicker } from '../components/HistoricalLabSourcePicker'
import { useLanguage } from '../i18n/LanguageContext'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  applyTournamentLabRunDraft,
  copySavedRevisionTournamentToLab,
  createTournamentLabSession,
  getTournamentLabBuiltInScenarios,
  getTournamentLabSessions,
  inspectTournamentLabScenario,
  previewTournamentLabRunDraft,
  runTournamentLabSession,
  runTournamentTestLab,
  updateTournamentLabSession
} from '../api/client'
import type {
  TournamentLabCompatibility,
  TournamentLabRequest,
  TournamentLabRunDraftPreview,
  TournamentLabResult,
  TournamentLabScenario,
  TournamentLabSession
} from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { prettyLabJson } from '../components/LabJson'
import { LabNavigation } from '../components/LabNavigation'
import { LabScenarioAuthoring, readLabScenario } from '../components/labAuthoring/LabScenarioAuthoring'
import { LabSessionConflict, useLabSessionEditor, validateLabSession, type LabEditorTicket } from '../components/LabSessionEditor'
import { newCommandId } from '../admin/branchSimulation'

function parseSeeds(value: string): number[] {
  const trimmed = value.trim()
  if (!trimmed) return []
  const parts = trimmed.split(',').map((part) => part.trim())
  const seeds = parts.map(Number)
  if (parts.some((part) => !/^[+-]?\d+$/.test(part))
    || seeds.some((seed) => !Number.isSafeInteger(seed))) {
    throw new Error('Batch match seeds must be comma-separated integers.')
  }
  if (new Set(seeds).size !== seeds.length) {
    throw new Error('Batch match seeds must be unique.')
  }
  if (seeds.length > 100) {
    throw new Error('At most 100 batch match seeds are supported.')
  }
  return seeds
}

function CompatibilityPanel({ compatibility }: { compatibility: TournamentLabCompatibility }): JSX.Element {
  return <SectionCard title="Compatibility diagnostics">
    <SummaryPills items={[
      { label: 'Runnable in Lab', value: compatibility.runnable_in_lab ? 'yes' : 'no' },
      { label: 'Normal Run compatible', value: compatibility.normal_run_compatible ? 'yes' : 'no' },
      { label: 'Run mutation', value: compatibility.run_mutation_performed ? 'yes' : 'no' },
      { label: 'Live Run link', value: compatibility.run_live_link ? 'yes' : 'no' }
    ]} />
    <p className="status">Shared authorities:</p>
    <ul>{compatibility.shared_authorities.map((item) => <li key={item}><code>{item}</code></li>)}</ul>
    {compatibility.issues.length ? <table aria-label="Tournament Lab compatibility issues">
      <thead><tr><th>Severity</th><th>Code</th><th>Explanation</th></tr></thead>
      <tbody>{compatibility.issues.map((issue) => <tr key={issue.code}>
        <td>{issue.severity}</td><td><code>{issue.code}</code></td><td>{issue.message}</td>
      </tr>)}</tbody>
    </table> : <p className="status">No compatibility issues.</p>}
  </SectionCard>
}

function TournamentResultPanels({ data }: { data: TournamentLabResult }): JSX.Element {
  const firstRun = data.runs[0]
  const [statusFilter, setStatusFilter] = useState('all')
  const statuses = useMemo<string[]>(
    () => Array.from(new Set(firstRun?.match_results.map(row => row.status) ?? [])).sort(),
    [firstRun]
  )
  const activeFilter = statusFilter === 'all' || statuses.includes(statusFilter) ? statusFilter : 'all'
  const displayedMatches = firstRun?.match_results.filter(row => activeFilter === 'all' || row.status === activeFilter) ?? []
  return <>
    <CompatibilityPanel compatibility={data.compatibility} />
    <SectionCard title="Replay identity">
      <SummaryPills items={[
        { label: 'Scenario', value: data.scenario_fingerprint.slice(0, 12) },
        { label: 'Request', value: data.request_fingerprint.slice(0, 12) },
        { label: 'Format authority', value: data.format_authority_fingerprint?.slice(0, 12) ?? 'not built' },
        { label: 'Draw input', value: data.draw_input_fingerprint?.slice(0, 12) ?? 'not built' },
        { label: 'Draw authority', value: data.draw_authority_fingerprint?.slice(0, 12) ?? 'not built' },
        { label: 'Topology', value: data.topology_authority_fingerprint?.slice(0, 12) ?? 'not built' },
        { label: 'Group schedule', value: data.group_schedule_fingerprint?.slice(0, 12) ?? 'not built' }
      ]} />
    </SectionCard>
    <SectionCard title="Batch diagnostics">
      <SummaryPills items={[
        { label: 'Runs', value: data.diagnostics.run_count },
        { label: 'Completed', value: data.diagnostics.completed_run_count },
        { label: 'Assertion failures', value: data.diagnostics.assertion_failure_count },
        { label: 'Avg played matches', value: data.diagnostics.average_played_match_count.toFixed(1) }
      ]} />
      <p>Champions: {Object.entries(data.diagnostics.champions).map(([player, count]) => `${player}: ${count}`).join(' · ') || '—'}</p>
    </SectionCard>
    {data.draw ? <SectionCard title="Canonical Main Draw">
      <SummaryPills items={[
        { label: 'Bracket size', value: data.draw.main.bracket_size },
        { label: 'Algorithm', value: data.draw.algorithm_version },
        { label: 'BYEs', value: data.draw.main.bye_slot_indexes.length },
        { label: 'Q sections', value: data.draw.qualification_sections?.length ?? (data.draw.qualification ? 1 : 0) },
        { label: 'Nodes', value: data.draw.main.nodes.length }
      ]} />
      <table aria-label="Tournament Lab draw slots">
        <thead><tr><th>Slot</th><th>Entrant</th><th>Player</th><th>Seed</th></tr></thead>
        <tbody>{data.draw.main.slots.map((slot) => <tr key={slot.slot_index}>
          <td>{slot.slot_index}</td>
          <td>{slot.entrant_kind}</td>
          <td>{slot.player_id ?? slot.placeholder_id ?? '—'}</td>
          <td>{slot.seed_number ?? '—'}</td>
        </tr>)}</tbody>
      </table>
    </SectionCard> : null}
    {firstRun && (firstRun.qualification_results?.length ?? 0) > 0 ? <SectionCard title="Qualification progression">
      <table aria-label="Tournament Lab qualification results">
        <thead><tr><th>Section</th><th>Winner</th><th>Played</th><th>BYE advances</th></tr></thead>
        <tbody>{firstRun.qualification_results?.map((row) => <tr key={row.section_id}>
          <td>{row.section_id}</td>
          <td>{row.winner_player_id ?? '—'}</td>
          <td>{row.played_match_count}</td>
          <td>{row.bye_advance_count}</td>
        </tr>)}</tbody>
      </table>
    </SectionCard> : null}
    {firstRun?.group_stage ? <SectionCard title="Group stage">
      <SummaryPills items={[
        { label: 'Match days', value: firstRun.group_stage.match_day_count },
        { label: 'Group matches', value: firstRun.group_stage.match_results.length },
        { label: 'Standings', value: firstRun.group_stage.standings ? 'resolved' : 'blocked' },
        { label: 'Hybrid bracket', value: firstRun.hybrid_knockout_bracket ? `${firstRun.hybrid_knockout_bracket.entrant_count} entrants` : 'none' }
      ]} />
      {firstRun.group_stage.blocking_issue ? <p className="error">
        {firstRun.group_stage.blocking_issue.code}: {firstRun.group_stage.blocking_issue.message}
      </p> : null}
      {firstRun.group_stage.standings?.groups.map((group) => <table
        key={group.group_index}
        aria-label={`Tournament Lab group ${group.group_index} standings`}
      >
        <thead><tr><th>Pos</th><th>Player</th><th>W</th><th>L</th><th>Pts</th><th>Games</th><th>Points</th></tr></thead>
        <tbody>{group.rows.map((row) => <tr key={row.player_id}>
          <td>{row.position}</td>
          <td>{row.player_id}</td>
          <td>{row.wins}</td>
          <td>{row.losses}</td>
          <td>{row.group_points}</td>
          <td>{row.games_won}-{row.games_lost}</td>
          <td>{row.points_won}-{row.points_lost}</td>
        </tr>)}</tbody>
      </table>)}
    </SectionCard> : null}
    {firstRun ? <SectionCard title="First batch run">
      <SummaryPills items={[
        { label: 'Match seed', value: firstRun.match_seed },
        { label: 'Completed rounds', value: firstRun.completed_rounds },
        { label: 'Tournament complete', value: firstRun.tournament_complete ? 'yes' : 'no' },
        { label: 'Champion', value: firstRun.champion_player_id ?? 'not resolved' },
        { label: 'Played matches', value: firstRun.played_match_count },
        { label: 'Q sections resolved', value: firstRun.qualification_results?.length ?? 0 },
        { label: 'Group stage', value: firstRun.group_stage ? 'yes' : 'no' },
        { label: 'BYE advances', value: firstRun.bye_advance_count }
      ]} />
      <label>Filter first-run matches by status
        <select aria-label="Tournament Lab match status filter" value={activeFilter} onChange={event => setStatusFilter(event.target.value)}>
          <option value="all">All match statuses</option>
          {statuses.map(status => <option key={status} value={status}>{status}</option>)}
        </select>
      </label>
      <p className="status">Showing {displayedMatches.length} of {firstRun.match_results.length} first-run matches · Batch totals remain unchanged.</p>
      <table aria-label="Tournament Lab match results">
        <thead><tr><th>Round</th><th>Node</th><th>Players</th><th>Status</th><th>Winner</th><th>Score</th><th>Rallies</th></tr></thead>
        <tbody>{displayedMatches.map((row) => <tr key={row.node_id}>
          <td>{row.round_number}</td>
          <td>{row.node_id}</td>
          <td>{row.player_a_id ?? 'BYE'} vs {row.player_b_id ?? 'BYE'}</td>
          <td>{row.status}</td>
          <td>{row.winner_player_id ?? '—'}</td>
          <td>{row.set_scores.join(', ') || '—'}</td>
          <td>{row.rally_count}</td>
        </tr>)}</tbody>
      </table>
      {firstRun.assertions.length ? <table aria-label="Tournament Lab assertions">
        <thead><tr><th>Assertion</th><th>Status</th><th>Expected</th><th>Actual</th></tr></thead>
        <tbody>{firstRun.assertions.map((row) => <tr key={row.assertion}>
          <td>{row.assertion}</td><td>{row.status}</td><td>{row.expected}</td><td>{row.actual ?? '—'}</td>
        </tr>)}</tbody>
      </table> : null}
    </SectionCard> : null}
  </>
}

export function TournamentTestLabPage(): JSX.Element {
  const builtIns = useQuery({
    queryKey: ['tournament-lab-built-ins'],
    queryFn: getTournamentLabBuiltInScenarios,
    retry: false
  })
  const sessions = useQuery({
    queryKey: ['tournament-lab-sessions'],
    queryFn: getTournamentLabSessions,
    retry: false
  })
  const {language} = useLanguage(), cs = language === 'cs'
  const [source, setSource] = useState({run: '', branch: '', revision: '', event: ''})
  const sourceSelection = useRef('')
  sourceSelection.current = JSON.stringify(source)
  const client = useQueryClient()
  const editor = useLabSessionEditor(sessions.data, sessions.isSuccess, '', 'New Tournament Test Session')
  const { selectedSession, selectedSessionId, setSelectedSessionId, scenarioText, setScenarioText,
    sessionName, setSessionName, sessionHasUnsavedChanges, sessionConflict } = editor
  const [batchText, setBatchText] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [targetRunId, setTargetRunId] = useState('')
  const [targetBranchId, setTargetBranchId] = useState('')
  const [targetEventId, setTargetEventId] = useState('')
  const runDraftCommands = useRef(new Map<string, string>())

  const parsedScenario = useMemo(() => {
    try {
      return scenarioText ? JSON.parse(scenarioText) as TournamentLabScenario : null
    } catch {
      return null
    }
  }, [scenarioText])
  const inspectMutation = useMutation({
    mutationFn: inspectTournamentLabScenario
  })
  const runPending = useIsMutating({ mutationKey: ['tournament-lab-run'] }) > 0
  const runMutation = useMutation({
    mutationKey: ['tournament-lab-run'],
    mutationFn: async ({ payload, session }: { payload: TournamentLabRequest; session: TournamentLabSession | null }) => {
      if (session) {
        return runTournamentLabSession(session.session_id, {
          expected_session_fingerprint: session.session_fingerprint,
          batch_match_seeds: payload.batch_match_seeds
        })
      }
      return runTournamentTestLab(payload)
    }
  })
  const runDraftPreviewMutation = useMutation({
    mutationFn: async (target: { runId: string; branchId: string; eventId: string; session: TournamentLabSession }) => {
      const preview = await previewTournamentLabRunDraft(target.session.session_id, {
        expected_session_fingerprint: target.session.session_fingerprint,
        product_run_id: target.runId, branch_id: target.branchId, event_id: target.eventId
      })
      if (preview.session_id !== target.session.session_id || preview.session_fingerprint !== target.session.session_fingerprint
        || preview.product_run_id !== target.runId || preview.branch_id !== target.branchId || preview.event_id !== target.eventId
        || preview.schema_version !== 'tournament_test_lab_run_draft_preview.v1' || preview.mutation_performed !== false) {
        throw new Error('Run proposal preview does not match the reviewed Test Session and target.')
      }
      return preview
    }
  })
  const runDraftApplyMutation = useMutation({
    mutationKey: ['tournament-lab-write'],
    mutationFn: async (preview: TournamentLabRunDraftPreview) => {
      const identity = `${preview.session_id}:${preview.session_fingerprint}:${preview.preview_fingerprint}`
      let commandId = runDraftCommands.current.get(identity)
      if (!commandId) { commandId = newCommandId(); runDraftCommands.current.set(identity, commandId) }
      const applied = await applyTournamentLabRunDraft(preview.session_id, {
        command_id: commandId, expected_session_fingerprint: preview.session_fingerprint,
        product_run_id: preview.product_run_id, branch_id: preview.branch_id, event_id: preview.event_id,
        expected_saved_revision_id: preview.target_saved_revision_id,
        expected_working_draft_version: preview.target_working_draft_version,
        expected_preview_fingerprint: preview.preview_fingerprint,
        expected_candidate_fingerprint: preview.candidate_fingerprint
      })
      if (applied.product_run_id !== preview.product_run_id || applied.branch_id !== preview.branch_id
        || applied.event_id !== preview.event_id || applied.command_id !== commandId
        || applied.candidate_fingerprint !== preview.candidate_fingerprint || applied.mutation_performed !== true) {
        throw new Error('Run proposal response does not match the submitted target. Inspect the Working Draft before continuing.')
      }
      return applied
    }
  })
  const recordSession = (session: TournamentLabSession) => {
    client.setQueryData<TournamentLabSession[]>(['tournament-lab-sessions'], previous =>
      [...(previous ?? []).filter(item => item.session_id !== session.session_id), session])
    void sessions.refetch()
  }
  const resetEvidence = () => {
    inspectMutation.reset(); runMutation.reset(); runDraftPreviewMutation.reset(); runDraftApplyMutation.reset()
  }
  const copyMutation = useMutation({
    mutationKey: ['tournament-lab-write'],
    mutationFn: async (input: {source: typeof source; selection: string; ticket: LabEditorTicket}) => validateLabSession(await copySavedRevisionTournamentToLab({
      display_name: `Historical ${input.source.event}`, product_run_id: input.source.run, branch_id: input.source.branch,
      saved_revision_id: input.source.revision, event_id: input.source.event})),
    onSuccess: (created, input) => { recordSession(created)
      if (input.selection === sourceSelection.current && editor.acceptSession(created, input.ticket, false)) resetEvidence()
    }
  })
  const createMutation = useMutation({
    mutationKey: ['tournament-lab-write'],
    mutationFn: (input: { request: Parameters<typeof createTournamentLabSession>[0]; ticket: LabEditorTicket }) => createTournamentLabSession(input.request),
    onSuccess: (response, { ticket }) => {
      const created = validateLabSession(response)
      recordSession(created)
      if (ticket && editor.acceptSession(created, ticket)) resetEvidence()
    }
  })
  const saveMutation = useMutation({
    mutationKey: ['tournament-lab-write'],
    mutationFn: async ({ session, scenario, displayName }: { session: TournamentLabSession; scenario: TournamentLabScenario; displayName: string; ticket: LabEditorTicket }) =>
      validateLabSession(await updateTournamentLabSession(session.session_id, {
        expected_session_fingerprint: session.session_fingerprint,
        display_name: displayName, scenario
      }), session.session_id),
    onSuccess: (updated, { ticket }) => {
      recordSession(updated)
      if (ticket && editor.acceptSession(updated, ticket)) resetEvidence()
    }
  })
  const writePending = useIsMutating({ mutationKey: ['tournament-lab-write'] }) > 0
  useEffect(() => { resetEvidence() }, [selectedSessionId, selectedSession?.session_fingerprint, sessionConflict])
  const preview = runDraftPreviewMutation.data
  const reviewedPreview = preview && !sessionConflict && !sessionHasUnsavedChanges
    && preview.session_id === selectedSessionId && preview.session_fingerprint === selectedSession?.session_fingerprint
    && preview.product_run_id === targetRunId.trim() && preview.branch_id === targetBranchId.trim()
    && preview.event_id === targetEventId.trim() ? preview : null

  const editScenario = (value: string) => {
    setScenarioText(value)
    setLocalError(null)
    inspectMutation.reset()
    runMutation.reset()
    runDraftPreviewMutation.reset()
    runDraftApplyMutation.reset()
  }

  const formatScenario = () => {
    try {
      editScenario(prettyLabJson(scenarioText))
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  const useBuiltIn = (scenario: TournamentLabScenario) => {
    setSelectedSessionId(null)
    setScenarioText(JSON.stringify(scenario, null, 2))
    inspectMutation.reset()
    runMutation.reset()
    runDraftPreviewMutation.reset()
    runDraftApplyMutation.reset()
    setLocalError(null)
  }

  const inspect = () => {
    setLocalError(null)
    try {
      const scenario = JSON.parse(scenarioText) as TournamentLabScenario
      inspectMutation.mutate(scenario)
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  const createFromDraft = () => {
    if (selectedSession || writePending || sessionConflict) return
    setLocalError(null)
    try {
      readLabScenario(scenarioText, 'tournament')
      createMutation.mutate({ ticket: editor.captureEditor(), request: {
        display_name: sessionName.trim() || 'New Tournament Test Session',
        scenario: JSON.parse(scenarioText) as TournamentLabScenario
      } })
    } catch {
      setLocalError(cs
        ? 'Zkontrolujte platný JSON, typ a verzi scénáře před vytvořením Session.'
        : 'Check the scenario JSON, Lab type and schema version before creating a Session.')
    }
  }

  const save = () => {
    if (!selectedSession || sessionConflict || writePending) return
    setLocalError(null)
    try {
      const scenario = JSON.parse(scenarioText) as TournamentLabScenario
      saveMutation.mutate({ session: selectedSession, scenario, displayName: sessionName, ticket: editor.captureEditor() })
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (writePending || runPending) return
    setLocalError(null)
    try {
      const scenario = JSON.parse(scenarioText) as TournamentLabScenario
      if (sessionHasUnsavedChanges) {
        throw new Error('Save Test Session changes before running this tournament.')
      }
      const payload: TournamentLabRequest = {
        scenario,
        batch_match_seeds: parseSeeds(batchText)
      }
      if (sessionConflict) throw new Error('Refresh and reload the saved Test Session before running.')
      if (writePending || runPending) return
      runMutation.mutate({ payload, session: selectedSession })
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return <section className="panel">
    <PageIntro
      title="Tournament Test Lab"
      subtitle="Global isolated tournament sandbox with persistent editable Test Sessions over shared Tournament Format, canonical Draw authority and production Match Engine kernels."
    />

    <LabNavigation active="tournament" />
    <SectionCard title={cs ? 'Historický turnaj → nezávislá Session' : 'Historical tournament → independent Session'}>
      <HistoricalLabSourcePicker lab="Tournament Lab" run={source.run} branch={source.branch} revision={source.revision}
        onChange={(run, branch, revision) => setSource({...source, run, branch, revision})} />
      {(['run', 'branch', 'revision', 'event'] as const).map(key => <label key={key}>{cs ? ({run: 'Run', branch: 'Větev', revision: 'Uložená revize', player: 'Hráč', event: 'Turnaj'})[key] : key}
        <input aria-label={`Tournament Lab import ${key}`} value={source[key]} onChange={e => setSource({...source, [key]: e.target.value})} />
      </label>)}
      <button type="button" disabled={writePending || sessionHasUnsavedChanges || Boolean(sessionConflict) || !Object.values(source).every(Boolean)}
        onClick={() => copyMutation.mutate({source, selection: sourceSelection.current, ticket: editor.captureEditor()})}>{cs ? 'Zkopírovat historický turnaj' : 'Copy historical tournament'}</button>
      {copyMutation.isError && <p role="alert">{String(copyMutation.error)}</p>}
      {parsedScenario?.source_snapshot && <p>{cs ? 'Zdroj' : 'Source'}: {parsedScenario.source_reference} · {cs ? 'Uložený stav účastníků, bez změny původních výsledků.' : 'Saved participant states; source results remain unchanged.'}</p>}
    </SectionCard>
    <SectionCard title="Isolation boundary">
      <p>
        Tournament Lab Sessions exist outside Runs. Inspect/Run remain isolated; only the separate reviewed
        Apply workflow may stage a proposal into a target Run Working Draft. An invalid draft never becomes
        a fabricated authoritative result.
      </p>
      <SummaryPills items={[
        { label: 'Lab execution mutation', value: 'never' },
        { label: 'Reviewed draft apply', value: 'explicit only' },
        { label: 'Executable formats', value: 'knockout · groups · groups→knockout' },
        { label: 'Selected mode', value: selectedSession ? 'isolated Test Session' : 'portable scratch scenario' }
      ]} />
      <p className="status">
        Knockout, Qualification, pure groups and groups→knockout are executable. Run→Lab copy and reviewed
        Lab→Run Working Draft proposal are available; withdrawals/replacements and ranking consequences remain
        separate shared-authority slices.
      </p>
    </SectionCard>

    <SectionCard title="Built-in read-only scenarios">
      {builtIns.isLoading ? <p className="status">Loading scenarios…</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · read-only baseline</p>
        <button type="button" onClick={() => useBuiltIn(item.scenario)}>Load scratch copy</button>
        <button type="button" disabled={writePending} onClick={() => createMutation.mutate({ ticket: editor.captureEditor(), request: {
          display_name: `${item.display_name} — Test Session`,
          built_in_scenario_id: item.scenario_id
        }})}>New Test Session from {item.display_name}</button>
      </article>)}
      {builtIns.isError ? <p className="error">Tournament Lab built-ins unavailable.</p> : null}
    </SectionCard>

    <SectionCard title="Tournament Test Sessions">
      <button type="button" disabled={sessions.isFetching} onClick={() => { void sessions.refetch() }}>
        {sessions.isFetching ? 'Refreshing Test Sessions…' : 'Refresh Test Sessions'}
      </button>
      <label>Open Test Session
        <select
          aria-label="Open Tournament Test Session"
          value={selectedSessionId ?? ''}
          onChange={(event) => {
            setSelectedSessionId(event.target.value || null)
            inspectMutation.reset()
            runMutation.reset()
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }}
        >
          <option value="">Portable scratch scenario</option>
          {selectedSession && !sessions.data?.some(item => item.session_id === selectedSessionId)
            ? <option value={selectedSession.session_id}>{selectedSession.display_name} · loaded v{selectedSession.version} (unavailable)</option> : null}
          {sessions.data?.map((item) => <option key={item.session_id} value={item.session_id}>
            {item.display_name} · v{item.version}
          </option>)}
        </select>
      </label>
      {sessions.isLoading ? <p role="status">Loading saved Tournament Test Sessions…</p> : null}
      {sessions.isError ? <p role="alert" className="error">Saved Tournament Test Sessions unavailable.</p> : null}
      {sessions.isSuccess && sessions.data.length === 0
        ? <p className="status">No saved Tournament Test Sessions yet. Scratch mode remains available.</p> : null}
      <LabSessionConflict key={`${selectedSessionId}:${selectedSession?.session_fingerprint}:${sessionConflict}:${editor.editorEdit}`}
        conflict={sessionConflict} dirty={sessionHasUnsavedChanges} canReload={editor.canReloadSession} onReload={editor.reloadSession} />
      {selectedSession ? <SummaryPills items={[
        { label: 'Session', value: selectedSession.display_name },
        { label: 'Version', value: selectedSession.version },
        { label: 'Source', value: selectedSession.scenario.source_kind },
        { label: 'Session fingerprint', value: selectedSession.session_fingerprint.slice(0, 12) }
      ]} /> : <p className="status">Scratch mode is non-persistent. Create a Test Session to keep an editable isolated tournament draft.</p>}
    </SectionCard>

    <SectionCard title="Reviewed Lab → Run Working Draft proposal">
      <p>
        Copy the currently saved Test Session into one Run-owned event proposal. Preview is read-only;
        Apply only stages a reviewed proposal in the target Working Draft. It does not create Entry,
        Draw, Result or ranking authority and does not bypass their provenance rules.
      </p>
      <label>Target Product Run ID
        <input
          aria-label="Tournament Lab target Run ID"
          value={targetRunId}
          onChange={(event) => {
            setTargetRunId(event.target.value)
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }}
        />
      </label>
      <label>Target Branch ID
        <input
          aria-label="Tournament Lab target Branch ID"
          value={targetBranchId}
          onChange={(event) => {
            setTargetBranchId(event.target.value)
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }}
        />
      </label>
      <label>Target event ID
        <input
          aria-label="Tournament Lab target event ID"
          value={targetEventId}
          onChange={(event) => {
            setTargetEventId(event.target.value)
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }}
        />
      </label>
      <button
        type="button"
        disabled={
          !selectedSession ||
          !targetRunId.trim() ||
          !targetBranchId.trim() ||
          !targetEventId.trim() ||
          runDraftPreviewMutation.isPending || writePending || Boolean(sessionConflict) ||
          sessionHasUnsavedChanges
        }
        onClick={() => selectedSession && runDraftPreviewMutation.mutate({
          session: selectedSession,
          runId: targetRunId.trim(),
          branchId: targetBranchId.trim(),
          eventId: targetEventId.trim()
        })}
      >
        {runDraftPreviewMutation.isPending ? 'Reviewing Run draft…' : 'Preview Run draft'}
      </button>
      {reviewedPreview ? <>
        <SummaryPills items={[
          { label: 'Ready', value: reviewedPreview.ready_for_draft ? 'yes' : 'no' },
          { label: 'Saved Head', value: reviewedPreview.target_saved_revision_id },
          { label: 'Draft version', value: reviewedPreview.target_working_draft_version },
          { label: 'Preview', value: reviewedPreview.preview_fingerprint.slice(0, 12) },
          { label: 'Candidate', value: reviewedPreview.candidate_fingerprint.slice(0, 12) }
        ]} />
        {reviewedPreview.issues.length ? <ul>
          {reviewedPreview.issues.map((issue) => <li key={issue.code}>
            <code>{issue.code}</code>: {issue.message}
          </li>)}
        </ul> : null}
        <button
          type="button"
          disabled={!reviewedPreview.ready_for_draft || writePending || sessionHasUnsavedChanges}
          onClick={() => runDraftApplyMutation.mutate(reviewedPreview)}
        >
          {runDraftApplyMutation.isPending ? 'Applying reviewed proposal…' : 'Apply to Run Working Draft'}
        </button>
      </> : null}
      {runDraftPreviewMutation.isError ? <p className="error">
        Run draft preview failed: {String(runDraftPreviewMutation.error)}
      </p> : null}
      {runDraftApplyMutation.isError ? <p className="error">
        Run draft apply failed: {String(runDraftApplyMutation.error)}
      </p> : null}
      {runDraftApplyMutation.data ? <SummaryPills items={[
        { label: 'Proposal version', value: runDraftApplyMutation.data.proposal_version },
        { label: 'Proposal', value: runDraftApplyMutation.data.proposal_fingerprint.slice(0, 12) },
        { label: 'Working Draft version', value: runDraftApplyMutation.data.working_draft_version },
        { label: 'Replay', value: runDraftApplyMutation.data.already_applied ? 'idempotent' : 'new mutation' }
      ]} /> : null}
      {runDraftApplyMutation.data ? <p className="status">
        Proposal is staged in the target Run Working Draft. Use the normal Run Save workflow to create
        its immutable Saved Revision before authoritative adoption.
      </p> : null}
    </SectionCard>

    <form onSubmit={submit}>
      <SectionCard title={selectedSession ? 'Editable Tournament Test Session' : 'Portable Tournament Lab scenario JSON'}>
        {selectedSession ? <label>Session name
          <input aria-label="Tournament Lab session name" value={sessionName} onChange={(event) => {
            setSessionName(event.target.value)
            runMutation.reset()
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }} />
        </label> : null}
        <LabScenarioAuthoring kind="tournament" text={scenarioText} onChange={editScenario}
          jsonLabel="Tournament Lab scenario JSON" selection={selectedSessionId ?? 'scratch'} revision={editor.editorEdit}
          savedScenario={selectedSession?.scenario} savedName={selectedSession?.display_name}
          sessionName={editor.sessionName} />
        <label>Batch match seeds (optional, comma-separated; max 100)
          <input
            aria-label="Tournament Lab batch match seeds"
            value={batchText}
            onChange={(event) => { setBatchText(event.target.value); runMutation.reset() }}
            placeholder="100, 101, 102"
          />
        </label>
        <button type="button" onClick={formatScenario} disabled={runPending || writePending}>Format JSON</button>
        {!selectedSession ? <button type="button" onClick={createFromDraft} disabled={writePending || !scenarioText.trim()}>
          {cs ? 'Vytvořit Session z pracovního scénáře' : 'Create Test Session from scratch'}
        </button> : null}
        {selectedSession ? <button type="button" onClick={save} disabled={writePending || Boolean(sessionConflict) || !scenarioText}>
          {saveMutation.isPending ? 'Saving…' : 'Save Test Session'}
        </button> : null}
        <button type="button" onClick={inspect} disabled={!scenarioText || inspectMutation.isPending}>
          {inspectMutation.isPending ? 'Inspecting…' : 'Inspect compatibility'}
        </button>
        <button type="submit" disabled={!scenarioText || runPending || writePending || Boolean(sessionConflict) || sessionHasUnsavedChanges}>
          {runPending ? 'Running…' : selectedSession ? 'Run Test Session' : 'Run tournament scenario'}
        </button>
        {sessionHasUnsavedChanges ? <p role="status">Unsaved Tournament Test Session changes. Save before running or reviewing a Run proposal.</p> : null}
        {localError ? <p className="error">{localError}</p> : null}
        {inspectMutation.isError ? <p className="error">Inspection failed: {String(inspectMutation.error)}</p> : null}
        {createMutation.isError ? <p className="error">Session creation failed: {String(createMutation.error)}</p> : null}
        {saveMutation.isError ? <p className="error">Session save failed: {String(saveMutation.error)}</p> : null}
        {runMutation.isError ? <p className="error">Tournament Lab failed: {String(runMutation.error)}</p> : null}
        <p className="status">Scenario: {parsedScenario?.scenario_id ?? (scenarioText ? 'invalid JSON' : 'none loaded')}</p>
      </SectionCard>
    </form>

    {inspectMutation.data ? <CompatibilityPanel compatibility={inspectMutation.data} /> : null}
    {runMutation.data ? <TournamentResultPanels data={runMutation.data} /> : null}
  </section>
}
