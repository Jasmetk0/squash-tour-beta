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

function parseSeeds(value: string, cs: boolean): number[] {
  const trimmed = value.trim()
  if (!trimmed) return []
  const parts = trimmed.split(',').map((part) => part.trim())
  const seeds = parts.map(Number)
  if (parts.some((part) => !/^[+-]?\d+$/.test(part))
    || seeds.some((seed) => !Number.isSafeInteger(seed))) {
    throw new Error(cs ? 'Seedy zápasů musí být celá čísla oddělená čárkami.' : 'Batch match seeds must be comma-separated integers.')
  }
  if (new Set(seeds).size !== seeds.length) {
    throw new Error(cs ? 'Seedy zápasů se nesmí opakovat.' : 'Batch match seeds must be unique.')
  }
  if (seeds.length > 100) {
    throw new Error(cs ? 'Dávka může mít nejvýše 100 seedů zápasů.' : 'At most 100 batch match seeds are supported.')
  }
  return seeds
}

/** Translate presentation only; the filter and API retain the original status code. */
function visibleMatchStatus(status: string, cs: boolean): string {
  if (!cs) return status
  const translations: Record<string, string> = {
    played: 'odehráno', completed: 'dokončeno', bye: 'volný postup',
    pending: 'čeká', skipped: 'přeskočeno', blocked: 'blokováno',
    not_played: 'neodehráno', retired: 'ukončení zápasu'
  }
  return translations[status] ? `${translations[status]} (${status})` : status
}

function CompatibilityPanel({ compatibility }: { compatibility: TournamentLabCompatibility }): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
  return <SectionCard title={cs ? "Diagnostika kompatibility" : "Compatibility diagnostics"}>
    <SummaryPills items={[
      { label: cs ? 'Spustitelné v Labu' : 'Runnable in Lab', value: compatibility.runnable_in_lab ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
      { label: cs ? 'Kompatibilní s běžným Runem' : 'Normal Run compatible', value: compatibility.normal_run_compatible ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
      { label: cs ? 'Zápis do Runu' : 'Run mutation', value: compatibility.run_mutation_performed ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
      { label: cs ? 'Živé propojení' : 'Live Run link', value: compatibility.run_live_link ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') }
    ]} />
    <p className="status">{cs
      ? "Kompatibilita s Runem je pouze výsledkem existující kontroly návrhu; spuštění v Labu samo nepotvrzuje platný Run turnaj, Entry, los ani uloženou revizi."
      : "Run compatibility is only the existing inspection result; execution in the Lab alone does not certify a valid Run tournament, Entry, Draw or Saved Revision."}</p>
    <p className="status">{cs ? "Sdílené autority:" : "Shared authorities:"}</p>
    <ul>{compatibility.shared_authorities.map((item) => <li key={item}><code>{item}</code></li>)}</ul>
    {compatibility.issues.length ? <table aria-label="Tournament Lab compatibility issues">
      <thead><tr><th>{cs ? "Závažnost" : "Severity"}</th><th>{cs ? "Kód" : "Code"}</th><th>{cs ? "Vysvětlení" : "Explanation"}</th></tr></thead>
      <tbody>{compatibility.issues.map((issue) => <tr key={issue.code}>
        <td>{issue.severity}</td><td><code>{issue.code}</code></td><td>{issue.message}</td>
      </tr>)}</tbody>
    </table> : <p className="status">{cs ? "Nejsou hlášeny problémy s kompatibilitou." : "No compatibility issues."}</p>}
  </SectionCard>
}

function TournamentResultPanels({ data }: { data: TournamentLabResult }): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
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
    <SectionCard title={cs ? "Identita opakování" : "Replay identity"}>
      <SummaryPills items={[
        { label: cs ? 'Scénář' : 'Scenario', value: data.scenario_fingerprint.slice(0, 12) },
        { label: cs ? 'Požadavek' : 'Request', value: data.request_fingerprint.slice(0, 12) },
        { label: cs ? 'Autorita formátu' : 'Format authority', value: data.format_authority_fingerprint?.slice(0, 12) ?? (cs ? 'nevytvořeno' : 'not built') },
        { label: cs ? 'Vstup losu' : 'Draw input', value: data.draw_input_fingerprint?.slice(0, 12) ?? (cs ? 'nevytvořeno' : 'not built') },
        { label: cs ? 'Autorita losu' : 'Draw authority', value: data.draw_authority_fingerprint?.slice(0, 12) ?? (cs ? 'nevytvořeno' : 'not built') },
        { label: cs ? 'Topologie' : 'Topology', value: data.topology_authority_fingerprint?.slice(0, 12) ?? (cs ? 'nevytvořeno' : 'not built') },
        { label: cs ? 'Rozpis skupin' : 'Group schedule', value: data.group_schedule_fingerprint?.slice(0, 12) ?? (cs ? 'nevytvořeno' : 'not built') }
      ]} />
    </SectionCard>
    <SectionCard title={cs ? "Diagnostika dávky" : "Batch diagnostics"}>
      <SummaryPills items={[
        { label: cs ? 'Běhy' : 'Runs', value: data.diagnostics.run_count },
        { label: cs ? 'Dokončeno' : 'Completed', value: data.diagnostics.completed_run_count },
        { label: cs ? 'Neúspěšné kontroly' : 'Assertion failures', value: data.diagnostics.assertion_failure_count },
        { label: cs ? 'Průměr zápasů' : 'Avg played matches', value: data.diagnostics.average_played_match_count.toFixed(1) }
      ]} />
      <p>{cs ? "Vítězové" : "Champions"}: {Object.entries(data.diagnostics.champions).map(([player, count]) => `${player}: ${count}`).join(' · ') || '—'}</p>
    </SectionCard>
    {data.draw ? <SectionCard title={cs ? "Kanonický hlavní los" : "Canonical Main Draw"}>
      <SummaryPills items={[
        { label: cs ? 'Velikost pavouka' : 'Bracket size', value: data.draw.main.bracket_size },
        { label: cs ? 'Algoritmus' : 'Algorithm', value: data.draw.algorithm_version },
        { label: 'BYEs', value: data.draw.main.bye_slot_indexes.length },
        { label: cs ? 'Sekce kvalifikace' : 'Q sections', value: data.draw.qualification_sections?.length ?? (data.draw.qualification ? 1 : 0) },
        { label: cs ? 'Uzly' : 'Nodes', value: data.draw.main.nodes.length }
      ]} />
      <table aria-label="Tournament Lab draw slots">
        <thead><tr><th>{cs ? "Pozice" : "Slot"}</th><th>{cs ? "Účastník" : "Entrant"}</th><th>{cs ? "Hráč" : "Player"}</th><th>Seed</th></tr></thead>
        <tbody>{data.draw.main.slots.map((slot) => <tr key={slot.slot_index}>
          <td>{slot.slot_index}</td>
          <td>{slot.entrant_kind}</td>
          <td>{slot.player_id ?? slot.placeholder_id ?? '—'}</td>
          <td>{slot.seed_number ?? '—'}</td>
        </tr>)}</tbody>
      </table>
    </SectionCard> : null}
    {firstRun && (firstRun.qualification_results?.length ?? 0) > 0 ? <SectionCard title={cs ? "Průběh kvalifikace" : "Qualification progression"}>
      <table aria-label="Tournament Lab qualification results">
        <thead><tr><th>{cs ? "Sekce" : "Section"}</th><th>{cs ? "Vítěz" : "Winner"}</th><th>{cs ? "Odehráno" : "Played"}</th><th>{cs ? "Postupy díky BYE" : "BYE advances"}</th></tr></thead>
        <tbody>{firstRun.qualification_results?.map((row) => <tr key={row.section_id}>
          <td>{row.section_id}</td>
          <td>{row.winner_player_id ?? '—'}</td>
          <td>{row.played_match_count}</td>
          <td>{row.bye_advance_count}</td>
        </tr>)}</tbody>
      </table>
    </SectionCard> : null}
    {firstRun?.group_stage ? <SectionCard title={cs ? "Skupinová fáze" : "Group stage"}>
      <SummaryPills items={[
        { label: cs ? 'Hrací dny' : 'Match days', value: firstRun.group_stage.match_day_count },
        { label: cs ? 'Zápasy skupin' : 'Group matches', value: firstRun.group_stage.match_results.length },
        { label: cs ? 'Tabulky' : 'Standings', value: firstRun.group_stage.standings ? (cs ? 'vyhodnoceno' : 'resolved') : (cs ? 'blokováno' : 'blocked') },
        { label: cs ? 'Hybridní pavouk' : 'Hybrid bracket', value: firstRun.hybrid_knockout_bracket ? `${firstRun.hybrid_knockout_bracket.entrant_count} ${cs ? 'účastníků' : 'entrants'}` : (cs ? 'žádný' : 'none') }
      ]} />
      {firstRun.group_stage.blocking_issue ? <p role="alert" className="error">{cs ? "Skupinovou fázi nelze vyhodnotit" : "Group stage could not be resolved"} · {firstRun.group_stage.blocking_issue.code}: {firstRun.group_stage.blocking_issue.message}</p> : null}
      {firstRun.group_stage.standings?.groups.map((group) => <table
        key={group.group_index}
        aria-label={`Tournament Lab group ${group.group_index} standings`}
      >
        <thead><tr><th>{cs ? "Pořadí" : "Pos"}</th><th>{cs ? "Hráč" : "Player"}</th><th>{cs ? "V" : "W"}</th><th>{cs ? "P" : "L"}</th><th>{cs ? "Body" : "Pts"}</th><th>{cs ? "Sety" : "Games"}</th><th>{cs ? "Míčky" : "Points"}</th></tr></thead>
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
    {firstRun ? <SectionCard title={cs ? "První běh dávky" : "First batch run"}>
      <SummaryPills items={[
        { label: cs ? 'Seed zápasů' : 'Match seed', value: firstRun.match_seed },
        { label: cs ? 'Dokončená kola' : 'Completed rounds', value: firstRun.completed_rounds },
        { label: cs ? 'Turnaj dokončen' : 'Tournament complete', value: firstRun.tournament_complete ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
        { label: cs ? 'Vítěz' : 'Champion', value: firstRun.champion_player_id ?? (cs ? 'neurčeno' : 'not resolved') },
        { label: cs ? 'Odehrané zápasy' : 'Played matches', value: firstRun.played_match_count },
        { label: cs ? 'Vyhodnocené sekce kvalifikace' : 'Q sections resolved', value: firstRun.qualification_results?.length ?? 0 },
        { label: cs ? 'Skupinová fáze' : 'Group stage', value: firstRun.group_stage ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
        { label: cs ? 'Postupy díky BYE' : 'BYE advances', value: firstRun.bye_advance_count }
      ]} />
      <label>{cs ? "Filtrovat zápasy prvního běhu podle stavu" : "Filter first-run matches by status"}
        <select aria-label="Tournament Lab match status filter" value={activeFilter} onChange={event => setStatusFilter(event.target.value)}>
          <option value="all">{cs ? "Všechny stavy" : "All match statuses"}</option>
          {statuses.map(status => <option key={status} value={status}>{visibleMatchStatus(status, cs)}</option>)}
        </select>
      </label>
      <p role="status" className="status">{cs ? `Zobrazeno ${displayedMatches.length} z ${firstRun.match_results.length} zápasů prvního běhu` : `Showing ${displayedMatches.length} of ${firstRun.match_results.length} first-run matches`} · {cs ? "Souhrn dávky se filtrem nemění." : "Batch totals remain unchanged."}</p>
      {firstRun.match_results.length === 0 ? <p className="status">{cs ? "První běh neobsahuje výsledky zápasů." : "No match results in the first run."}</p> : displayedMatches.length === 0 ? <p className="status">{cs ? "Zvolenému stavu neodpovídá žádný zápas." : "No matches match this status filter."}</p> : null}
      <table aria-label="Tournament Lab match results">
        <thead><tr><th>{cs ? "Kolo" : "Round"}</th><th>{cs ? "Uzel" : "Node"}</th><th>{cs ? "Hráči" : "Players"}</th><th>{cs ? "Stav" : "Status"}</th><th>{cs ? "Vítěz" : "Winner"}</th><th>{cs ? "Skóre" : "Score"}</th><th>{cs ? "Výměny" : "Rallies"}</th></tr></thead>
        <tbody>{displayedMatches.map((row) => <tr key={row.node_id}>
          <td>{row.round_number}</td>
          <td>{row.node_id}</td>
          <td>{row.player_a_id ?? 'BYE'} vs {row.player_b_id ?? 'BYE'}</td>
          <td>{visibleMatchStatus(row.status, cs)}</td>
          <td>{row.winner_player_id ?? '—'}</td>
          <td>{row.set_scores.join(', ') || '—'}</td>
          <td>{row.rally_count}</td>
        </tr>)}</tbody>
      </table>
      {firstRun.assertions.length ? <table aria-label="Tournament Lab assertions">
        <thead><tr><th>{cs ? "Kontrola" : "Assertion"}</th><th>{cs ? "Stav" : "Status"}</th><th>{cs ? "Očekáváno" : "Expected"}</th><th>{cs ? "Skutečnost" : "Actual"}</th></tr></thead>
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
  const [scratchName, setScratchName] = useState('New Tournament Test Session')
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
        display_name: scratchName.trim() || 'New Tournament Test Session',
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
        throw new Error(cs ? 'Před spuštěním turnaje uložte změny Test Session.' : 'Save Test Session changes before running this tournament.')
      }
      const payload: TournamentLabRequest = {
        scenario,
        batch_match_seeds: parseSeeds(batchText, cs)
      }
      if (sessionConflict) throw new Error(cs ? 'Před spuštěním obnovte seznam a znovu načtěte uloženou Test Session.' : 'Refresh and reload the saved Test Session before running.')
      if (writePending || runPending) return
      runMutation.mutate({ payload, session: selectedSession })
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return <section className="panel">
    <PageIntro
      title={cs ? "Testovací laboratoř turnajů" : "Tournament Test Lab"}
      subtitle={cs ? "Samostatné turnajové scénáře a trvalé upravitelné Test Sessions využívající sdílený Tournament Format, kanonický los a Match Engine." : "Global isolated tournament sandbox with persistent editable Test Sessions over shared Tournament Format, canonical Draw authority and production Match Engine kernels."}
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
    <SectionCard title={cs ? "Hranice izolace" : "Isolation boundary"}>
      <p>{cs ? "Turnajové Test Sessions existují mimo Runy. Kontrola ani spuštění Run nemění. Teprve samostatně zkontrolované potvrzení může vložit návrh do Working Draft cílového Runu; neplatný návrh se tím nestává autoritativním výsledkem." : "Tournament Lab Sessions exist outside Runs. Inspect/Run remain isolated; only the separate reviewed Apply workflow may stage a proposal into a target Run Working Draft. An invalid draft never becomes a fabricated authoritative result."}</p>
      <SummaryPills items={[
        { label: cs ? 'Zápis během testu' : 'Lab execution mutation', value: cs ? 'nikdy' : 'never' },
        { label: cs ? 'Vložení návrhu' : 'Reviewed draft apply', value: cs ? 'pouze po potvrzení' : 'explicit only' },
        { label: cs ? 'Spustitelné formáty' : 'Executable formats', value: cs ? 'pavouk · skupiny · skupiny→pavouk' : 'knockout · groups · groups→knockout' },
        { label: cs ? 'Vybraný režim' : 'Selected mode', value: selectedSession ? (cs ? 'samostatná Test Session' : 'isolated Test Session') : (cs ? 'pracovní přenosný scénář' : 'portable scratch scenario') }
      ]} />
      <p className="status">{cs ? "Spustit lze pavouk, kvalifikaci, skupiny a skupiny→pavouk. Kopie Run→Lab a kontrolovaný návrh Lab→Working Draft existují; odstoupení, nahrazení a žebříčkové dopady zůstávají samostatnými úkoly." : "Knockout, Qualification, pure groups and groups→knockout are executable. Run→Lab copy and reviewed Lab→Run Working Draft proposal are available; withdrawals/replacements and ranking consequences remain separate shared-authority slices."}</p>
    </SectionCard>

    <SectionCard title={cs ? "Vestavěné scénáře pouze ke čtení" : "Built-in read-only scenarios"}>
      {builtIns.isLoading ? <p role="status" className="status">{cs ? "Načítám scénáře…" : "Loading scenarios…"}</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · {cs ? "výchozí scénář pouze ke čtení" : "read-only baseline"}</p>
        <button type="button" onClick={() => useBuiltIn(item.scenario)}>{cs ? "Načíst pracovní kopii" : "Load scratch copy"}</button>
        <button type="button" disabled={writePending} onClick={() => createMutation.mutate({ ticket: editor.captureEditor(), request: {
          display_name: `${item.display_name} — Test Session`,
          built_in_scenario_id: item.scenario_id
        }})}>{cs ? "Nová Test Session ze scénáře" : "New Test Session from"} {item.display_name}</button>
      </article>)}
      {builtIns.isError ? <p role="alert" className="error">{cs ? "Vestavěné turnajové scénáře nejsou dostupné." : "Tournament Lab built-ins unavailable."}</p> : null}
      {builtIns.isSuccess && builtIns.data?.length === 0 ? <p role="status" className="status">{cs ? "Žádné vestavěné turnajové scénáře." : "No built-in Tournament Lab scenarios."}</p> : null}
    </SectionCard>

    <SectionCard title={cs ? "Turnajové Test Sessions" : "Tournament Test Sessions"}>
      <button type="button" disabled={sessions.isFetching} onClick={() => { void sessions.refetch() }}>
        {sessions.isFetching ? (cs ? 'Obnovuji seznam Test Sessions…' : 'Refreshing Test Sessions…') : (cs ? 'Obnovit seznam Test Sessions' : 'Refresh Test Sessions')}
      </button>
      <label>{cs ? "Otevřít Test Session" : "Open Test Session"}
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
          <option value="">{cs ? "Pracovní přenosný scénář" : "Portable scratch scenario"}</option>
          {selectedSession && !sessions.data?.some(item => item.session_id === selectedSessionId)
            ? <option value={selectedSession.session_id}>{selectedSession.display_name} · v{selectedSession.version} ({cs ? "nedostupná v seznamu" : "unavailable"})</option> : null}
          {sessions.data?.map((item) => <option key={item.session_id} value={item.session_id}>
            {item.display_name} · v{item.version}
          </option>)}
        </select>
      </label>
      {sessions.isLoading ? <p role="status">{cs ? "Načítám uložené turnajové Sessions…" : "Loading saved Tournament Test Sessions…"}</p> : null}
      {sessions.isError ? <p role="alert" className="error">{cs ? "Seznam uložených turnajových Sessions není dostupný." : "Saved Tournament Test Sessions unavailable."}</p> : null}
      {sessions.isSuccess && sessions.data.length === 0
        ? <p className="status">{cs ? "Zatím žádná uložená Session; pracovní režim je dostupný." : "No saved Tournament Test Sessions yet. Scratch mode remains available."}</p> : null}
      <LabSessionConflict key={`${selectedSessionId}:${selectedSession?.session_fingerprint}:${sessionConflict}:${editor.editorEdit}`}
        conflict={sessionConflict} dirty={sessionHasUnsavedChanges} canReload={editor.canReloadSession} onReload={editor.reloadSession} />
      {selectedSession ? <SummaryPills items={[
        { label: 'Session', value: selectedSession.display_name },
        { label: cs ? 'Verze' : 'Version', value: selectedSession.version },
        { label: cs ? 'Zdroj' : 'Source', value: selectedSession.scenario.source_kind },
        { label: cs ? 'Otisk Session' : 'Session fingerprint', value: selectedSession.session_fingerprint.slice(0, 12) }
      ]} /> : <p className="status">{cs ? "Pracovní režim se neukládá. Pro trvalou kopii vytvoř Test Session." : "Scratch mode is non-persistent. Create a Test Session to keep an editable isolated tournament draft."}</p>}
    </SectionCard>

    <SectionCard title={cs ? "Zkontrolovaný návrh Lab → Working Draft Runu" : "Reviewed Lab → Run Working Draft proposal"}>
      <p>{cs ? "Z uložené Test Session lze připravit návrh pro událost Runu. Náhled je pouze ke čtení. Potvrzení vloží zkontrolovaný návrh pouze do Working Draft; nevytváří Entry, los, výsledky ani žebříčkovou autoritu a neobchází kontrolu původu. K vytvoření uložené revize je potřebný samostatný Run Save." : "Copy the currently saved Test Session into one Run-owned event proposal. Preview is read-only; Apply only stages a reviewed proposal in the target Working Draft. It does not create Entry, Draw, Result or ranking authority and does not bypass their provenance rules."}</p>
      <label>{cs ? "ID cílového Runu" : "Target Product Run ID"}
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
      <label>{cs ? "ID cílové větve" : "Target Branch ID"}
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
      <label>{cs ? "ID cílové události" : "Target event ID"}
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
        {runDraftPreviewMutation.isPending ? (cs ? 'Kontroluji návrh…' : 'Reviewing Run draft…') : (cs ? 'Zobrazit náhled návrhu' : 'Preview Run draft')}
      </button>
      {reviewedPreview ? <>
        <SummaryPills items={[
          { label: cs ? 'Připraveno' : 'Ready', value: reviewedPreview.ready_for_draft ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
          { label: cs ? 'Uložený základ' : 'Saved Head', value: reviewedPreview.target_saved_revision_id },
          { label: cs ? 'Verze návrhu' : 'Draft version', value: reviewedPreview.target_working_draft_version },
          { label: cs ? 'Otisk náhledu' : 'Preview', value: reviewedPreview.preview_fingerprint.slice(0, 12) },
          { label: cs ? 'Otisk kandidáta' : 'Candidate', value: reviewedPreview.candidate_fingerprint.slice(0, 12) }
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
          {runDraftApplyMutation.isPending ? (cs ? 'Vkládám zkontrolovaný návrh…' : 'Applying reviewed proposal…') : (cs ? 'Vložit návrh do Working Draft' : 'Apply to Run Working Draft')}
        </button>
      </> : null}
      {runDraftPreviewMutation.isError ? <p role="alert" className="error">
        {cs ? 'Náhled návrhu selhal' : 'Run draft preview failed'}: {String(runDraftPreviewMutation.error)}
      </p> : null}
      {runDraftApplyMutation.isError ? <p role="alert" className="error">
        {cs ? 'Vložení návrhu selhalo' : 'Run draft apply failed'}: {String(runDraftApplyMutation.error)}
      </p> : null}
      {runDraftApplyMutation.data ? <SummaryPills items={[
        { label: cs ? 'Verze návrhu' : 'Proposal version', value: runDraftApplyMutation.data.proposal_version },
        { label: cs ? 'Otisk návrhu' : 'Proposal', value: runDraftApplyMutation.data.proposal_fingerprint.slice(0, 12) },
        { label: cs ? 'Verze Working Draft' : 'Working Draft version', value: runDraftApplyMutation.data.working_draft_version },
        { label: cs ? 'Opakování' : 'Replay', value: runDraftApplyMutation.data.already_applied ? (cs ? 'idempotentní opakování' : 'idempotent') : (cs ? 'nové vložení návrhu' : 'new mutation') }
      ]} /> : null}
      {runDraftApplyMutation.data ? <p role="status" className="status">{cs ? "Návrh je vložen pouze do Working Draft cílového Runu. Autoritativní uložená revize vznikne až samostatným potvrzeným Run Save." : "Proposal is staged in the target Run Working Draft. Use normal Run Save to create an immutable Saved Revision before authoritative adoption."}</p> : null}
    </SectionCard>

    <form onSubmit={submit}>
      <SectionCard title={selectedSession ? (cs ? 'Upravitelná turnajová Test Session' : 'Editable Tournament Test Session') : (cs ? 'JSON pracovního turnajového scénáře' : 'Portable Tournament Lab scenario JSON')}>
        {selectedSession ? <label>{cs ? "Název Session" : "Session name"}
          <input aria-label="Tournament Lab session name" value={sessionName} onChange={(event) => {
            setSessionName(event.target.value)
            runMutation.reset()
            runDraftPreviewMutation.reset()
            runDraftApplyMutation.reset()
          }} />
        </label> : null}
        {!selectedSession ? <label>{cs ? "Název nové turnajové Session" : "Tournament Lab new Session name"}
          <input aria-label="Tournament Lab new Session name" value={scratchName} onChange={event => {
            setScratchName(event.target.value)
            editor.setSessionName(event.target.value)
          }} />
        </label> : null}
        <LabScenarioAuthoring kind="tournament" text={scenarioText} onChange={editScenario}
          jsonLabel="Tournament Lab scenario JSON" selection={selectedSession ? `${selectedSession.session_id}:${selectedSession.session_fingerprint}` : 'scratch'} revision={editor.editorEdit}
          savedScenario={selectedSession?.scenario} savedName={selectedSession?.display_name}
          sessionName={editor.sessionName} />
        <label>{cs ? "Seedy dávky zápasů (volitelné, oddělené čárkami, max. 100)" : "Batch match seeds (optional, comma-separated; max 100)"}
          <input
            aria-label="Tournament Lab batch match seeds"
            value={batchText}
            onChange={(event) => { setBatchText(event.target.value); runMutation.reset() }}
            placeholder="100, 101, 102"
          />
        </label>
        <button type="button" onClick={formatScenario} disabled={runPending || writePending}>{cs ? "Formátovat JSON" : "Format JSON"}</button>
        {!selectedSession ? <button type="button" onClick={createFromDraft} disabled={writePending || !scenarioText.trim()}>
          {cs ? 'Vytvořit Session z pracovního scénáře' : 'Create Test Session from scratch'}
        </button> : null}
        {selectedSession ? <button type="button" onClick={save} disabled={writePending || Boolean(sessionConflict) || !scenarioText}>
          {saveMutation.isPending ? (cs ? 'Ukládám…' : 'Saving…') : (cs ? 'Uložit Test Session' : 'Save Test Session')}
        </button> : null}
        <button type="button" onClick={inspect} disabled={!scenarioText || inspectMutation.isPending}>
          {inspectMutation.isPending ? (cs ? 'Kontroluji…' : 'Inspecting…') : (cs ? 'Zkontrolovat kompatibilitu' : 'Inspect compatibility')}
        </button>
        <button type="submit" disabled={!scenarioText || runPending || writePending || Boolean(sessionConflict) || sessionHasUnsavedChanges}>
          {runPending ? (cs ? 'Spouštím…' : 'Running…') : selectedSession ? (cs ? 'Spustit Test Session' : 'Run Test Session') : (cs ? 'Spustit turnajový scénář' : 'Run tournament scenario')}
        </button>
        {sessionHasUnsavedChanges ? <p role="status">{cs ? "Neuložené změny Session. Ulož je před spuštěním či náhledem návrhu pro Run." : "Unsaved Tournament Test Session changes. Save before running or reviewing a Run proposal."}</p> : null}
        {localError ? <p role="alert" className="error">{localError}</p> : null}
        {inspectMutation.isError ? <p role="alert" className="error">{cs ? 'Kontrola selhala' : 'Inspection failed'}: {String(inspectMutation.error)}</p> : null}
        {createMutation.isError ? <p role="alert" className="error">{cs ? 'Vytvoření Session selhalo' : 'Session creation failed'}: {String(createMutation.error)}</p> : null}
        {saveMutation.isError ? <p role="alert" className="error">{cs ? 'Uložení Session selhalo' : 'Session save failed'}: {String(saveMutation.error)}</p> : null}
        {runMutation.isError ? <p role="alert" className="error">{cs ? 'Turnajová laboratoř selhala' : 'Tournament Lab failed'}: {String(runMutation.error)}</p> : null}
        <p className="status">{cs ? 'Scénář' : 'Scenario'}: {parsedScenario?.scenario_id ?? (scenarioText ? (cs ? 'neplatný JSON' : 'invalid JSON') : (cs ? 'nic nenačteno' : 'none loaded'))}</p>
      </SectionCard>
    </form>

    {inspectMutation.data ? <CompatibilityPanel compatibility={inspectMutation.data} /> : null}
    {runMutation.data ? <TournamentResultPanels data={runMutation.data} /> : null}
  </section>
}
