import { HistoricalLabSourcePicker } from '../components/HistoricalLabSourcePicker'
import { useLanguage } from '../i18n/LanguageContext'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createMatchLabSession,
  getMatchLabBuiltInScenarios,
  getMatchLabSessions,
  importMatchLabSavedRevisionPlayer,
  runMatchLabSession,
  runMatchTestLab,
  updateMatchLabSession
} from '../api/client'
import type { MatchLabRequest, MatchLabResult, MatchLabScenario, MatchLabSession } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { prettyLabJson } from '../components/LabJson'
import { LabNavigation } from '../components/LabNavigation'
import { LabScenarioAuthoring, readLabScenario } from '../components/labAuthoring/LabScenarioAuthoring'
import { LabSessionConflict, useLabSessionEditor, validateLabSession, type LabEditorTicket } from '../components/LabSessionEditor'

const traits = {
  potential_ceiling: 90, growth_curve: 'balanced', professionalism: 0.7, ambition: 0.7,
  travel_tolerance: 0.7, schedule_aggression: 0.6, injury_proneness: 0.2, resilience: 0.8
}

const defaultScenario: MatchLabScenario = {
  schema_version: 'match_test_lab_scenario.v1',
  scenario_id: 'portable-match-example',
  seed: 777,
  source_kind: 'portable',
  context: {
    match_id: 'match-lab-example',
    player_a: { player: { player_id: 'LAB-A', name: 'Lab Player A', age: 27, nationality: 'TST',
      technique: 86, movement: 86, physical: 86, mental: 86, consistency: 86, clutch: 86, recovery: 86,
      play_style: 'tempo-controller', archetype: 'all-court tactician', hidden_career_traits: traits },
      form_modifier: 0, sharpness_modifier: 0, fatigue_modifier: 0, health_modifier: 0, travel_modifier: 0 },
    player_b: { player: { player_id: 'LAB-B', name: 'Lab Player B', age: 27, nationality: 'TST',
      technique: 81, movement: 81, physical: 81, mental: 81, consistency: 81, clutch: 81, recovery: 81,
      play_style: 'counter-punching', archetype: 'durable grinder', hidden_career_traits: traits },
      form_modifier: 0, sharpness_modifier: 0, fatigue_modifier: 0, health_modifier: 0, travel_modifier: 0 },
    best_of: 5, games_to: 11, win_by: 2, upset_variance: 0.12,
    retirement_rule: { enabled: false, retired_player_id: null, trigger: 'EXPLICIT_SET_START', set_number: null, probability: 0 }
  }
}

function parseSeeds(value: string, cs: boolean): number[] {
  const trimmed = value.trim()
  if (!trimmed) return []
  const parts = trimmed.split(',').map((part) => part.trim())
  const seeds = parts.map(Number)
  if (parts.some((part) => !/^[+-]?\d+$/.test(part))
    || seeds.some((seed) => !Number.isSafeInteger(seed))) throw new Error(cs ? 'Seedy dávky musí být celá čísla oddělená čárkami.' : 'Batch seeds must be comma-separated integers.')
  if (new Set(seeds).size !== seeds.length) throw new Error(cs ? 'Seedy dávky se nesmí opakovat.' : 'Batch seeds must be unique.')
  if (seeds.length > 100) throw new Error(cs ? 'Dávka může mít nejvýše 100 seedů.' : 'At most 100 batch seeds are supported.')
  return seeds
}

function ResultPanels({ data }: { data: MatchLabResult }): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
  const [winnerFilter, setWinnerFilter] = useState('all')
  const winners = useMemo(() =>
    Array.from(new Set(data.results.map(result => result.winner_player_id))).sort(),
    [data.results]
  )
  // Never apply a previous batch's winner filter to a different batch accidentally.
  const activeFilter = winnerFilter === 'all' || winners.includes(winnerFilter) ? winnerFilter : 'all'
  const displayed = activeFilter === 'all'
    ? data.results
    : data.results.filter(result => result.winner_player_id === activeFilter)

  return <>
    <SectionCard title={cs ? 'Kompatibilita a izolace' : 'Compatibility & isolation'}>
      <SummaryPills items={[
        { label: cs ? 'Jádro' : 'Engine', value: data.compatibility.match_engine_version },
        { label: cs ? 'Běžný formát' : 'Normal format', value: data.compatibility.normal_format ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
        { label: cs ? 'Zápis do Runu' : 'Run mutation', value: data.compatibility.run_mutation_performed ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
        { label: cs ? 'Živé propojení s Runem' : 'Live Run link', value: data.compatibility.run_live_link ? (cs ? 'ano' : 'yes') : (cs ? 'ne' : 'no') },
        { label: cs ? 'Otisk scénáře' : 'Scenario fingerprint', value: data.scenario_fingerprint.slice(0, 12) },
        { label: cs ? 'Otisk požadavku' : 'Request fingerprint', value: data.request_fingerprint.slice(0, 12) }
      ]} />
      <p className="status"><code>{data.compatibility.production_kernel}</code></p>
      {data.compatibility.warnings.length > 0
        ? <ul>{data.compatibility.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        : <p className="status">{cs ? 'Pro tento scénář nejsou hlášena varování o kompatibilitě.' : 'No compatibility warnings for this scenario.'}</p>}
    </SectionCard>
    <SectionCard title={cs ? 'Diagnostika dávky' : 'Batch diagnostics'}>
      <SummaryPills items={[
        { label: cs ? 'Seedy' : 'Seeds', value: data.diagnostics.seed_count },
        { label: cs ? 'Různé výsledky' : 'Distinct results', value: data.diagnostics.distinct_result_count },
        { label: cs ? 'Průměr výměn' : 'Avg rallies', value: data.diagnostics.average_rally_count.toFixed(1) },
        { label: cs ? 'Průměr doby (s)' : 'Avg elapsed (s)', value: data.diagnostics.average_elapsed_seconds.toFixed(1) },
        { label: cs ? 'Ukončení zápasu' : 'Retirements', value: data.diagnostics.retirement_count }
      ]} />
      <p>{cs ? 'Výhry' : 'Wins'}: {Object.entries(data.diagnostics.wins_by_player).map(([player, wins]) => `${player}: ${wins}`).join(' · ')}</p>
    </SectionCard>
    <SectionCard title={cs ? 'Opakovatelné výsledky' : 'Replayable results'}>
      <label>{cs ? 'Filtrovat podle vítěze' : 'Filter results by winner'}
        <select aria-label="Match Lab winner filter" value={activeFilter} onChange={event => setWinnerFilter(event.target.value)}>
          <option value="all">{cs ? "Všichni vítězové" : "All winners"}</option>
          {winners.map(winner => <option key={winner} value={winner}>{winner}</option>)}
        </select>
      </label>
      <p role="status" className="status">{cs ? `Zobrazeno ${displayed.length} z ${data.results.length} výsledků` : `Showing ${displayed.length} of ${data.results.length} results`} · {cs ? "Souhrn dávky zahrnuje všechny zápasy." : "Batch diagnostics above include all matches."}</p>
      {data.results.length === 0 ? <p className="status">{cs ? "Dávka nemá žádné výsledky." : "This batch has no results."}</p> : displayed.length === 0 ? <p className="status">{cs ? "Filtru neodpovídají žádné výsledky." : "No results match this filter."}</p> : null}
      <table aria-label="Match Lab results"><thead><tr>
        <th>Seed</th><th>{cs ? "Vítěz" : "Winner"}</th><th>{cs ? "Sety" : "Sets"}</th><th>{cs ? "Skóre setů (A–B)" : "Set scores (A-B)"}</th><th>{cs ? "Výměny" : "Rallies"}</th><th>{cs ? "Doba" : "Elapsed"}</th><th>{cs ? "Otisk výsledku" : "Result fingerprint"}</th>
      </tr></thead><tbody>
        {displayed.map((result) => <tr key={result.seed}>
          <td>{result.seed}</td><td>{result.winner_player_id}</td>
          <td>{Object.entries(result.sets_won).map(([player, sets]) => `${player} ${sets}`).join(' / ')}</td>
          <td>{result.set_scores.join(', ')}</td><td>{result.rally_count}</td><td>{result.elapsed_seconds.toFixed(1)} s</td>
          <td><code>{result.result_fingerprint.slice(0, 12)}</code></td>
        </tr>)}
      </tbody></table>
    </SectionCard>
  </>
}

export function MatchTestLabPage(): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
  const builtIns = useQuery({ queryKey: ['match-lab-built-ins'], queryFn: getMatchLabBuiltInScenarios, retry: false })
  const sessions = useQuery({ queryKey: ['match-lab-sessions'], queryFn: getMatchLabSessions, retry: false })
  const client = useQueryClient()
  const editor = useLabSessionEditor(sessions.data, sessions.isSuccess, JSON.stringify(defaultScenario, null, 2), 'New Match Test Session')
  const { selectedSession, selectedSessionId, setSelectedSessionId, scenarioText, setScenarioText,
    sessionName, setSessionName, sessionHasUnsavedChanges, sessionConflict } = editor
  const [batchText, setBatchText] = useState('')
  const [scratchName, setScratchName] = useState('New Match Test Session')
  const [importRunId, setImportRunId] = useState('')
  const [importBranchId, setImportBranchId] = useState('')
  const [importRevisionId, setImportRevisionId] = useState('')
  const [importPlayerId, setImportPlayerId] = useState('')
  const [importSide, setImportSide] = useState<'player_a' | 'player_b'>('player_a')
  const importSelection = useRef('')
  importSelection.current = JSON.stringify([importRunId, importBranchId, importRevisionId, importPlayerId, importSide])
  const [localError, setLocalError] = useState<string | null>(null)

  const parsedPreview = useMemo(() => {
    try { return JSON.parse(scenarioText) as MatchLabScenario } catch { return null }
  }, [scenarioText])

  const runPending = useIsMutating({ mutationKey: ['match-lab-run'] }) > 0
  const runMutation = useMutation({
    mutationKey: ['match-lab-run'],
    mutationFn: async ({ scenario, seeds, session }: { scenario: MatchLabScenario; seeds: number[]; session: MatchLabSession | null }) => {
      if (session) {
        return runMatchLabSession(session.session_id, {
          expected_session_fingerprint: session.session_fingerprint,
          batch_seeds: seeds
        })
      }
      const payload: MatchLabRequest = { scenario, batch_seeds: seeds }
      return runMatchTestLab(payload)
    }
  })

  const editScenario = (value: string) => {
    setScenarioText(value)
    setLocalError(null)
    runMutation.reset()
  }

  const formatScenario = () => {
    try {
      editScenario(prettyLabJson(scenarioText))
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error)
      setLocalError(cs ? `JSON nelze formátovat. ${detail}` : detail)
    }
  }

  const recordSession = (session: MatchLabSession) => {
    client.setQueryData<MatchLabSession[]>(['match-lab-sessions'], previous =>
      [...(previous ?? []).filter(item => item.session_id !== session.session_id), session])
    void sessions.refetch()
  }
  const createMutation = useMutation({
    mutationKey: ['match-lab-write'],
    mutationFn: (input: { request: Parameters<typeof createMatchLabSession>[0]; ticket: LabEditorTicket }) => createMatchLabSession(input.request),
    onSuccess: (response, { ticket }) => {
      const created = validateLabSession(response)
      recordSession(created)
      if (ticket && editor.acceptSession(created, ticket)) runMutation.reset()
    }
  })
  const saveMutation = useMutation({
    mutationKey: ['match-lab-write'],
    mutationFn: async ({ session, scenario, displayName }: { session: MatchLabSession; scenario: MatchLabScenario; displayName: string; ticket: LabEditorTicket }) =>
      validateLabSession(await updateMatchLabSession(session.session_id, {
        expected_session_fingerprint: session.session_fingerprint,
        display_name: displayName, scenario
      }), session.session_id),
    onSuccess: (updated, { ticket }) => {
      recordSession(updated)
      if (ticket && editor.acceptSession(updated, ticket)) runMutation.reset()
    }
  })
  const importMutation = useMutation({
    mutationKey: ['match-lab-write'],
    mutationFn: async (input: { session: MatchLabSession; runId: string; branchId: string; revisionId: string; playerId: string; side: 'player_a' | 'player_b'; sourceSelection: string; ticket: LabEditorTicket }) =>
      validateLabSession(await importMatchLabSavedRevisionPlayer(input.session.session_id, {
        expected_session_fingerprint: input.session.session_fingerprint,
        product_run_id: input.runId, branch_id: input.branchId,
        saved_revision_id: input.revisionId, player_id: input.playerId, side: input.side
      }), input.session.session_id),
    onSuccess: (updated, { ticket, sourceSelection }) => {
      recordSession(updated)
      // Import transforms participant data, so later local edits cannot be
      // silently rebased onto its new provenance. Require explicit review.
      if (sourceSelection === importSelection.current && ticket && editor.acceptSession(updated, ticket, false)) runMutation.reset()
    }
  })
  const writePending = useIsMutating({ mutationKey: ['match-lab-write'] }) > 0
  useEffect(() => { runMutation.reset() }, [selectedSessionId, selectedSession?.session_fingerprint, sessionConflict])

  const parseScenario = (): MatchLabScenario => {
    try { return JSON.parse(scenarioText) as MatchLabScenario }
    catch { throw new Error(cs ? 'Neplatný JSON scénáře. Před spuštěním nebo uložením opravte syntaxi.' : 'Invalid scenario JSON. Check the syntax before running or saving.') }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (writePending || runPending) return
    setLocalError(null)
    runMutation.reset()
    try {
      const scenario = parseScenario()
      if (sessionHasUnsavedChanges) throw new Error(cs ? 'Před spuštěním scénáře uložte změny Test Session.' : 'Save Test Session changes before running this scenario.')
      if (sessionConflict) throw new Error(cs ? 'Před spuštěním obnovte seznam a znovu načtěte uloženou Test Session.' : 'Refresh and reload the saved Test Session before running.')
      if (writePending || runPending) return
      runMutation.mutate({ scenario, seeds: parseSeeds(batchText, cs), session: selectedSession })
    }
    catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) }
  }

  const createFromDraft = () => {
    if (selectedSession || writePending || sessionConflict) return
    setLocalError(null)
    try {
      readLabScenario(scenarioText, 'match')
      createMutation.mutate({ ticket: editor.captureEditor(), request: {
        display_name: scratchName.trim() || 'New Match Test Session',
        scenario: JSON.parse(scenarioText) as MatchLabScenario
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
    try { saveMutation.mutate({ session: selectedSession, scenario: parseScenario(), displayName: sessionName, ticket: editor.captureEditor() }) }
    catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) }
  }

  return <section className="panel">
    <PageIntro title={cs ? "Testovací laboratoř zápasů" : "Match Test Lab"} subtitle={cs ? "Samostatné vestavěné scénáře, upravitelné Test Sessions a opakovatelné scénáře Match Engine mimo Run." : "Global isolated sandbox for built-in baselines, editable Test Sessions and portable replayable Match Engine scenarios."} />

    <LabNavigation active="match" />
    <SectionCard title={cs ? "Bezpečnostní hranice" : "Safety boundary"}>
      <p>{cs ? "Vestavěné scénáře jsou pouze ke čtení. Nová Test Session vytvoří samostatnou upravitelnou kopii mimo Run a větev. Původ dat není živé propojení." : "Built-in scenarios are read-only. New Test Session creates an independent editable copy outside every Run and Branch; copied provenance is data only, never a live link."}</p>
      <SummaryPills items={[
        { label: cs ? 'Jádro' : 'Kernel', value: 'MatchEngine.simulate' },
        { label: cs ? 'Zápis do Runu' : 'Run mutation', value: cs ? 'nikdy' : 'never' },
        { label: cs ? 'Vybraný režim' : 'Selected mode', value: selectedSession ? (cs ? 'samostatná Test Session' : 'isolated Test Session') : (cs ? 'pracovní přenosný scénář' : 'portable scratch scenario') }
      ]} />
    </SectionCard>

    <SectionCard title={cs ? "Vestavěné scénáře pouze ke čtení" : "Built-in read-only scenarios"}>
      <button type="button" disabled={builtIns.isFetching} onClick={() => { void builtIns.refetch() }}>
        {builtIns.isFetching ? (cs ? 'Načítám scénáře…' : 'Refreshing built-in scenarios…') : (cs ? 'Obnovit vestavěné scénáře' : 'Refresh built-in scenarios')}
      </button>
      {builtIns.isLoading ? <p role="status" className="status">{cs ? "Načítám vestavěné scénáře…" : "Loading built-in scenarios…"}</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · {cs ? "výchozí scénář pouze ke čtení" : "read-only baseline"}</p>
        <button type="button" disabled={writePending} onClick={() => createMutation.mutate({ ticket: editor.captureEditor(), request: {
          display_name: `${item.display_name} — Test Session`,
          built_in_scenario_id: item.scenario_id
        }})}>{cs ? "Nová Test Session ze scénáře" : "New Test Session from"} {item.display_name}</button>
      </article>)}
      {builtIns.isError ? <p role="alert" className="error">{cs ? "Vestavěné scénáře nelze načíst." : "Built-in scenarios unavailable."} {String(builtIns.error)}</p> : null}
      {builtIns.isSuccess && builtIns.data?.length === 0 ? <p className="status">{cs ? "Registr neobsahuje žádné vestavěné scénáře." : "No built-in scenarios were returned."}</p> : null}
      {createMutation.isError ? <p role="alert" className="error">{cs ? "Vytvoření Session selhalo" : "Session creation failed"}: {String(createMutation.error)}</p> : null}
    </SectionCard>

    <SectionCard title="Test Sessions">
      <button type="button" disabled={sessions.isFetching} onClick={() => { void sessions.refetch() }}>
        {sessions.isFetching ? (cs ? 'Obnovuji seznam Test Sessions…' : 'Refreshing Test Sessions…') : (cs ? 'Obnovit seznam Test Sessions' : 'Refresh Test Sessions')}
      </button>
      <label>{cs ? 'Otevřít Test Session' : 'Open Test Session'}
        <select aria-label="Open Match Test Session" value={selectedSessionId ?? ''} onChange={(e) => {
          setSelectedSessionId(e.target.value || null)
          runMutation.reset()
        }}>
          <option value="">{cs ? "Pracovní přenosný scénář" : "Portable scratch scenario"}</option>
          {selectedSession && !sessions.data?.some(item => item.session_id === selectedSessionId)
            ? <option value={selectedSession.session_id}>{selectedSession.display_name} · v{selectedSession.version} ({cs ? "nedostupná v seznamu" : "unavailable"})</option> : null}
          {sessions.data?.map((item) => <option key={item.session_id} value={item.session_id}>{item.display_name} · v{item.version}</option>)}
        </select>
      </label>
      {sessions.isLoading ? <p role="status">{cs ? "Načítám uložené Match Test Sessions…" : "Loading saved Match Test Sessions…"}</p> : null}
      {sessions.isError ? <p role="alert" className="error">{cs ? "Seznam uložených Match Test Sessions není dostupný." : "Saved Match Test Sessions unavailable."}</p> : null}
      {sessions.isSuccess && sessions.data.length === 0
        ? <p className="status">{cs ? "Zatím žádná uložená Session. Pracovní režim je nadále dostupný." : "No saved Match Test Sessions yet. Scratch mode remains available."}</p> : null}
      <LabSessionConflict key={`${selectedSessionId}:${selectedSession?.session_fingerprint}:${sessionConflict}:${editor.editorEdit}`}
        conflict={sessionConflict} dirty={sessionHasUnsavedChanges} canReload={editor.canReloadSession} onReload={editor.reloadSession} />
      {selectedSession ? <SummaryPills items={[
        { label: 'Session', value: selectedSession.display_name },
        { label: cs ? 'Verze' : 'Version', value: selectedSession.version },
        { label: cs ? 'Zdroj' : 'Source', value: selectedSession.scenario.source_kind },
        { label: cs ? 'Otisk Session' : 'Session fingerprint', value: selectedSession.session_fingerprint.slice(0, 12) }
      ]} /> : <p className="status">{cs ? "Pracovní režim se neukládá. Pro trvalou upravitelnou kopii vytvoř Test Session." : "Scratch mode is non-persistent. Create a Test Session to keep an editable isolated copy."}</p>}
    </SectionCard>

    {selectedSession ? <SectionCard title={cs ? "Import hráče z uložené revize" : "Import player from Saved Revision"}>
      <p className="status">{cs ? 'Zkopíruje ověřený profil a uložený sportovní stav historického hráče do této Test Session. Zdrojový Run ani Saved Revision nemění a nevytváří živé propojení.' : 'Copies one validated historical player profile and saved sporting state into this Test Session. The source Run/Saved Revision is never mutated or live-linked.'}</p>
      <HistoricalLabSourcePicker lab="Match Lab" run={importRunId} branch={importBranchId} revision={importRevisionId}
        onChange={(run, branch, revision) => {setImportRunId(run); setImportBranchId(branch); setImportRevisionId(revision)}} />
      <label>{cs ? "ID Runu" : "Product Run ID"}
        <input aria-label="Match Lab import Run ID" value={importRunId} onChange={(e) => setImportRunId(e.target.value)} />
      </label>
      <label>{cs ? "ID větve" : "Branch ID"}
        <input aria-label="Match Lab import Branch ID" value={importBranchId} onChange={(e) => setImportBranchId(e.target.value)} />
      </label>
      <label>{cs ? "ID uložené revize" : "Saved Revision ID"}
        <input aria-label="Match Lab import Saved Revision ID" value={importRevisionId} onChange={(e) => setImportRevisionId(e.target.value)} />
      </label>
      <label>{cs ? "ID hráče" : "Player ID"}
        <input aria-label="Match Lab import Player ID" value={importPlayerId} onChange={(e) => setImportPlayerId(e.target.value)} />
      </label>
      <label>{cs ? "Nahradit účastníka" : "Replace participant"}
        <select aria-label="Match Lab import side" value={importSide} onChange={(e) => setImportSide(e.target.value as 'player_a' | 'player_b')}>
          <option value="player_a">{cs ? "Hráč A" : "Player A"}</option>
          <option value="player_b">{cs ? "Hráč B" : "Player B"}</option>
        </select>
      </label>
      <button
        type="button"
        disabled={writePending || Boolean(sessionConflict) || sessionHasUnsavedChanges || !importRunId.trim() || !importBranchId.trim() || !importRevisionId.trim() || !importPlayerId.trim()}
        onClick={() => { if (selectedSession && !writePending && !sessionConflict && !sessionHasUnsavedChanges) importMutation.mutate({
          sourceSelection: importSelection.current, ticket: editor.captureEditor(), session: selectedSession, runId: importRunId.trim(), branchId: importBranchId.trim(), revisionId: importRevisionId.trim(), playerId: importPlayerId.trim(), side: importSide
        }) }}
      >
        {importMutation.isPending ? (cs ? 'Importuji…' : 'Importing…') : (cs ? 'Importovat historického hráče' : 'Import historical player')}
      </button>
      {importMutation.isError ? <p role="alert" className="error">{cs ? "Import selhal" : "Import failed"}: {String(importMutation.error)}</p> : null}
      {(selectedSession.participant_imports ?? []).length > 0 ? <table aria-label="Match Lab historical imports">
        <thead><tr><th>{cs ? "Strana" : "Side"}</th><th>{cs ? "Hráč" : "Player"}</th><th>{cs ? "Zdroj" : "Source"}</th><th>{cs ? "Týden" : "Week"}</th><th>{cs ? "Hash revize" : "Revision hash"}</th></tr></thead>
        <tbody>{selectedSession.participant_imports.map((item) => <tr key={item.side}>
          <td>{item.side === 'player_a' ? (cs ? 'Hráč A' : 'Player A') : (cs ? 'Hráč B' : 'Player B')}</td>
          <td>{item.player_id}</td>
          <td>{item.product_run_id} / {item.branch_id} / {item.saved_revision_id}</td>
          <td>{item.sporting_week_ordinal}</td>
          <td><code>{item.saved_revision_content_hash.slice(0, 12)}</code></td>
        </tr>)}</tbody>
      </table> : null}
    </SectionCard> : null}

    <form onSubmit={submit}>
      <SectionCard title={selectedSession ? (cs ? 'Upravitelný scénář Test Session' : 'Editable Test Session scenario') : (cs ? 'JSON pracovního přenosného scénáře' : 'Portable scratch scenario JSON')}>
        {selectedSession ? <label>{cs ? "Název Session" : "Session name"}
          <input aria-label="Match Lab session name" value={sessionName} onChange={(e) => { setSessionName(e.target.value); runMutation.reset() }} />
        </label> : null}
        {!selectedSession ? <label>{cs ? "Název nové Match Lab Session" : "Match Lab new Session name"}
          <input aria-label="Match Lab new Session name" value={scratchName} onChange={event => {
            setScratchName(event.target.value)
            editor.setSessionName(event.target.value)
          }} />
        </label> : null}
        <LabScenarioAuthoring kind="match" text={scenarioText} onChange={editScenario}
          jsonLabel="Match Lab scenario JSON" selection={selectedSession ? `${selectedSession.session_id}:${selectedSession.session_fingerprint}` : 'scratch'} revision={editor.editorEdit}
          savedScenario={selectedSession?.scenario} savedName={selectedSession?.display_name}
          sessionName={editor.sessionName} />
        <label>{cs ? "Seedy dávky (volitelné; oddělené čárkou; max. 100)" : "Batch seeds (optional, comma-separated; max 100)"}
          <input aria-label="Match Lab batch seeds" value={batchText} onChange={(e) => { setBatchText(e.target.value); runMutation.reset() }} placeholder="100, 101, 102" />
        </label>
        <button type="button" onClick={formatScenario} disabled={runPending || writePending}>{cs ? "Formátovat JSON" : "Format JSON"}</button>
        {!selectedSession ? <button type="button" onClick={createFromDraft} disabled={writePending || !scenarioText.trim()}>
          {cs ? 'Vytvořit Session z pracovního scénáře' : 'Create Test Session from scratch'}
        </button> : null}
        {selectedSession ? <button type="button" onClick={save} disabled={writePending || Boolean(sessionConflict)}>{cs ? "Uložit Test Session" : "Save Test Session"}</button> : null}
        <button type="submit" disabled={runPending || writePending || Boolean(sessionConflict) || sessionHasUnsavedChanges}>{runPending ? (cs ? 'Spouštím…' : 'Running…') : selectedSession ? (cs ? 'Spustit Test Session' : 'Run Test Session') : (cs ? 'Spustit scénář' : 'Run scenario')}</button>
        {sessionHasUnsavedChanges ? <p role="status">{cs ? "Neuložené změny Test Session. Před spuštěním je ulož." : "Unsaved Test Session changes. Save before running."}</p> : null}
        {localError ? <p role="alert" className="error">{localError}</p> : null}
        {saveMutation.isError ? <p role="alert" className="error">{cs ? "Uložení selhalo pro" : "Save failed for"} {saveMutation.variables?.session.display_name}: {String(saveMutation.error)}</p> : null}
        {runMutation.isError ? <p role="alert" className="error">{cs ? "Výpočet selhal" : "Lab failed"}: {String(runMutation.error)}</p> : null}
        <p className="status">{cs ? "Scénář" : "Scenario"}: {parsedPreview?.scenario_id ?? (cs ? "neplatný JSON" : "invalid JSON")} · seed {parsedPreview?.seed ?? "—"}</p>
      </SectionCard>
    </form>

    {runMutation.data ? <ResultPanels data={runMutation.data} /> : null}
  </section>
}
