import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import {
  applyTournamentLabRunDraft,
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
import { newCommandId } from '../admin/branchSimulation'

function parseSeeds(value: string): number[] {
  const trimmed = value.trim()
  if (!trimmed) return []
  const seeds = trimmed.split(',').map((part) => Number(part.trim()))
  if (seeds.some((seed) => !Number.isInteger(seed))) {
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
      <table aria-label="Tournament Lab match results">
        <thead><tr><th>Round</th><th>Node</th><th>Players</th><th>Status</th><th>Winner</th><th>Score</th><th>Rallies</th></tr></thead>
        <tbody>{firstRun.match_results.map((row) => <tr key={row.node_id}>
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
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const selectedSession = sessions.data?.find((item) => item.session_id === selectedSessionId) ?? null
  const [scenarioText, setScenarioText] = useState('')
  const [sessionName, setSessionName] = useState('New Tournament Test Session')
  const [batchText, setBatchText] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [targetRunId, setTargetRunId] = useState('')
  const [targetBranchId, setTargetBranchId] = useState('')
  const [targetEventId, setTargetEventId] = useState('')
  const [runDraftCommandId, setRunDraftCommandId] = useState(() => newCommandId())

  useEffect(() => {
    if (selectedSession) {
      setScenarioText(JSON.stringify(selectedSession.scenario, null, 2))
      setSessionName(selectedSession.display_name)
    }
  }, [selectedSession?.session_id, selectedSession?.version])

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
  const runMutation = useMutation({
    mutationFn: async (payload: TournamentLabRequest) => {
      if (selectedSession) {
        return runTournamentLabSession(selectedSession.session_id, {
          expected_session_fingerprint: selectedSession.session_fingerprint,
          batch_match_seeds: payload.batch_match_seeds
        })
      }
      return runTournamentTestLab(payload)
    }
  })
  const runDraftPreviewMutation = useMutation({
    mutationFn: async (target: { runId: string; branchId: string; eventId: string }) => {
      if (!selectedSession) throw new Error('Open a persistent Tournament Test Session first.')
      return previewTournamentLabRunDraft(selectedSession.session_id, {
        expected_session_fingerprint: selectedSession.session_fingerprint,
        product_run_id: target.runId,
        branch_id: target.branchId,
        event_id: target.eventId
      })
    },
    onSuccess: () => {
      setRunDraftCommandId(newCommandId())
    }
  })
  const runDraftApplyMutation = useMutation({
    mutationFn: async (preview: TournamentLabRunDraftPreview) => {
      if (!selectedSession) throw new Error('Open a persistent Tournament Test Session first.')
      return applyTournamentLabRunDraft(selectedSession.session_id, {
        command_id: runDraftCommandId,
        expected_session_fingerprint: selectedSession.session_fingerprint,
        product_run_id: preview.product_run_id,
        branch_id: preview.branch_id,
        event_id: preview.event_id,
        expected_saved_revision_id: preview.target_saved_revision_id,
        expected_working_draft_version: preview.target_working_draft_version,
        expected_preview_fingerprint: preview.preview_fingerprint,
        expected_candidate_fingerprint: preview.candidate_fingerprint
      })
    }
  })
  const createMutation = useMutation({
    mutationFn: createTournamentLabSession,
    onSuccess: async (created) => {
      await sessions.refetch()
      setSelectedSessionId(created.session_id)
      setScenarioText(JSON.stringify(created.scenario, null, 2))
      setSessionName(created.display_name)
    }
  })
  const saveMutation = useMutation({
    mutationFn: async ({ session, scenario }: { session: TournamentLabSession; scenario: TournamentLabScenario }) =>
      updateTournamentLabSession(session.session_id, {
        expected_session_fingerprint: session.session_fingerprint,
        display_name: sessionName,
        scenario
      }),
    onSuccess: async (updated) => {
      await sessions.refetch()
      setSelectedSessionId(updated.session_id)
      setScenarioText(JSON.stringify(updated.scenario, null, 2))
    }
  })

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

  const save = () => {
    if (!selectedSession) return
    setLocalError(null)
    try {
      const scenario = JSON.parse(scenarioText) as TournamentLabScenario
      saveMutation.mutate({ session: selectedSession, scenario })
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError(null)
    try {
      const scenario = JSON.parse(scenarioText) as TournamentLabScenario
      const payload: TournamentLabRequest = {
        scenario,
        batch_match_seeds: parseSeeds(batchText)
      }
      runMutation.mutate(payload)
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return <section className="panel">
    <PageIntro
      title="Tournament Test Lab"
      subtitle="Global isolated tournament sandbox with persistent editable Test Sessions over shared Tournament Format, canonical Draw authority and production Match Engine kernels."
    />

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
        <button type="button" onClick={() => createMutation.mutate({
          display_name: `${item.display_name} — Test Session`,
          built_in_scenario_id: item.scenario_id
        })}>New Test Session from {item.display_name}</button>
      </article>)}
      {builtIns.isError ? <p className="error">Tournament Lab built-ins unavailable.</p> : null}
    </SectionCard>

    <SectionCard title="Tournament Test Sessions">
      <label>Open Test Session
        <select
          aria-label="Open Tournament Test Session"
          value={selectedSessionId ?? ''}
          onChange={(event) => setSelectedSessionId(event.target.value || null)}
        >
          <option value="">Portable scratch scenario</option>
          {sessions.data?.map((item) => <option key={item.session_id} value={item.session_id}>
            {item.display_name} · v{item.version}
          </option>)}
        </select>
      </label>
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
          runDraftPreviewMutation.isPending
        }
        onClick={() => runDraftPreviewMutation.mutate({
          runId: targetRunId.trim(),
          branchId: targetBranchId.trim(),
          eventId: targetEventId.trim()
        })}
      >
        {runDraftPreviewMutation.isPending ? 'Reviewing Run draft…' : 'Preview Run draft'}
      </button>
      {runDraftPreviewMutation.data ? <>
        <SummaryPills items={[
          { label: 'Ready', value: runDraftPreviewMutation.data.ready_for_draft ? 'yes' : 'no' },
          { label: 'Saved Head', value: runDraftPreviewMutation.data.target_saved_revision_id },
          { label: 'Draft version', value: runDraftPreviewMutation.data.target_working_draft_version },
          { label: 'Preview', value: runDraftPreviewMutation.data.preview_fingerprint.slice(0, 12) },
          { label: 'Candidate', value: runDraftPreviewMutation.data.candidate_fingerprint.slice(0, 12) }
        ]} />
        {runDraftPreviewMutation.data.issues.length ? <ul>
          {runDraftPreviewMutation.data.issues.map((issue) => <li key={issue.code}>
            <code>{issue.code}</code>: {issue.message}
          </li>)}
        </ul> : null}
        <button
          type="button"
          disabled={!runDraftPreviewMutation.data.ready_for_draft || runDraftApplyMutation.isPending}
          onClick={() => runDraftApplyMutation.mutate(runDraftPreviewMutation.data)}
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
          <input aria-label="Tournament Lab session name" value={sessionName} onChange={(event) => setSessionName(event.target.value)} />
        </label> : null}
        <textarea
          aria-label="Tournament Lab scenario JSON"
          value={scenarioText}
          onChange={(event) => setScenarioText(event.target.value)}
          rows={30}
          style={{ width: '100%', fontFamily: 'monospace' }}
          placeholder="Load a built-in scenario or paste tournament_test_lab_scenario.v1 JSON."
        />
        <label>Batch match seeds (optional, comma-separated; max 100)
          <input
            aria-label="Tournament Lab batch match seeds"
            value={batchText}
            onChange={(event) => setBatchText(event.target.value)}
            placeholder="100, 101, 102"
          />
        </label>
        {selectedSession ? <button type="button" onClick={save} disabled={saveMutation.isPending || !scenarioText}>
          {saveMutation.isPending ? 'Saving…' : 'Save Test Session'}
        </button> : null}
        <button type="button" onClick={inspect} disabled={!scenarioText || inspectMutation.isPending}>
          {inspectMutation.isPending ? 'Inspecting…' : 'Inspect compatibility'}
        </button>
        <button type="submit" disabled={!scenarioText || runMutation.isPending}>
          {runMutation.isPending ? 'Running…' : selectedSession ? 'Run Test Session' : 'Run tournament scenario'}
        </button>
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
