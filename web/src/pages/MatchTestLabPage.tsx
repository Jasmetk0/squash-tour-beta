import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import {
  createMatchLabSession,
  getMatchLabBuiltInScenarios,
  getMatchLabSessions,
  runMatchLabSession,
  runMatchTestLab,
  updateMatchLabSession
} from '../api/client'
import type { MatchLabRequest, MatchLabResult, MatchLabScenario, MatchLabSession } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

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

function parseSeeds(value: string): number[] {
  const trimmed = value.trim()
  if (!trimmed) return []
  const seeds = trimmed.split(',').map((part) => Number(part.trim()))
  if (seeds.some((seed) => !Number.isInteger(seed))) throw new Error('Batch seeds must be comma-separated integers.')
  if (new Set(seeds).size !== seeds.length) throw new Error('Batch seeds must be unique.')
  if (seeds.length > 100) throw new Error('At most 100 batch seeds are supported.')
  return seeds
}

function ResultPanels({ data }: { data: MatchLabResult }): JSX.Element {
  return <>
    <SectionCard title="Compatibility & isolation">
      <SummaryPills items={[
        { label: 'Engine', value: data.compatibility.match_engine_version },
        { label: 'Normal format', value: data.compatibility.normal_format ? 'yes' : 'no' },
        { label: 'Run mutation', value: data.compatibility.run_mutation_performed ? 'yes' : 'no' },
        { label: 'Live Run link', value: data.compatibility.run_live_link ? 'yes' : 'no' },
        { label: 'Scenario fingerprint', value: data.scenario_fingerprint.slice(0, 12) },
        { label: 'Request fingerprint', value: data.request_fingerprint.slice(0, 12) }
      ]} />
      <p className="status"><code>{data.compatibility.production_kernel}</code></p>
      {data.compatibility.warnings.length > 0
        ? <ul>{data.compatibility.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        : <p className="status">No compatibility warnings for this scenario.</p>}
    </SectionCard>
    <SectionCard title="Batch diagnostics">
      <SummaryPills items={[
        { label: 'Seeds', value: data.diagnostics.seed_count },
        { label: 'Distinct results', value: data.diagnostics.distinct_result_count },
        { label: 'Avg rallies', value: data.diagnostics.average_rally_count.toFixed(1) },
        { label: 'Avg elapsed (s)', value: data.diagnostics.average_elapsed_seconds.toFixed(1) },
        { label: 'Retirements', value: data.diagnostics.retirement_count }
      ]} />
      <p>Wins: {Object.entries(data.diagnostics.wins_by_player).map(([player, wins]) => `${player}: ${wins}`).join(' · ')}</p>
    </SectionCard>
    <SectionCard title="Replayable results">
      <table aria-label="Match Lab results"><thead><tr>
        <th>Seed</th><th>Winner</th><th>Sets</th><th>Set scores (A-B)</th><th>Rallies</th><th>Elapsed</th><th>Result fingerprint</th>
      </tr></thead><tbody>
        {data.results.map((result) => <tr key={result.seed}>
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
  const builtIns = useQuery({ queryKey: ['match-lab-built-ins'], queryFn: getMatchLabBuiltInScenarios, retry: false })
  const sessions = useQuery({ queryKey: ['match-lab-sessions'], queryFn: getMatchLabSessions, retry: false })
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const selectedSession = sessions.data?.find((item) => item.session_id === selectedSessionId) ?? null
  const [scenarioText, setScenarioText] = useState(JSON.stringify(defaultScenario, null, 2))
  const [sessionName, setSessionName] = useState('New Match Test Session')
  const [batchText, setBatchText] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    if (selectedSession) {
      setScenarioText(JSON.stringify(selectedSession.scenario, null, 2))
      setSessionName(selectedSession.display_name)
    }
  }, [selectedSession?.session_id, selectedSession?.version])

  const parsedPreview = useMemo(() => {
    try { return JSON.parse(scenarioText) as MatchLabScenario } catch { return null }
  }, [scenarioText])

  const runMutation = useMutation({
    mutationFn: async ({ scenario, seeds }: { scenario: MatchLabScenario; seeds: number[] }) => {
      if (selectedSession) {
        return runMatchLabSession(selectedSession.session_id, {
          expected_session_fingerprint: selectedSession.session_fingerprint,
          batch_seeds: seeds
        })
      }
      const payload: MatchLabRequest = { scenario, batch_seeds: seeds }
      return runMatchTestLab(payload)
    }
  })

  const createMutation = useMutation({
    mutationFn: createMatchLabSession,
    onSuccess: async (created) => {
      await sessions.refetch()
      setSelectedSessionId(created.session_id)
      setScenarioText(JSON.stringify(created.scenario, null, 2))
      setSessionName(created.display_name)
    }
  })

  const saveMutation = useMutation({
    mutationFn: async ({ session, scenario }: { session: MatchLabSession; scenario: MatchLabScenario }) =>
      updateMatchLabSession(session.session_id, {
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

  const parseScenario = (): MatchLabScenario => JSON.parse(scenarioText) as MatchLabScenario

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError(null)
    runMutation.reset()
    try { runMutation.mutate({ scenario: parseScenario(), seeds: parseSeeds(batchText) }) }
    catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) }
  }

  const save = () => {
    if (!selectedSession) return
    setLocalError(null)
    try { saveMutation.mutate({ session: selectedSession, scenario: parseScenario() }) }
    catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) }
  }

  return <section className="panel">
    <PageIntro title="Match Test Lab" subtitle="Global isolated sandbox for built-in baselines, editable Test Sessions and portable replayable Match Engine scenarios." />

    <SectionCard title="Safety boundary">
      <p>Built-in scenarios are read-only. <strong>New Test Session</strong> creates an independent editable copy outside every Run and Branch; copied provenance is data only, never a live link.</p>
      <SummaryPills items={[
        { label: 'Kernel', value: 'MatchEngine.simulate' },
        { label: 'Run mutation', value: 'never' },
        { label: 'Selected mode', value: selectedSession ? 'isolated Test Session' : 'portable scratch scenario' }
      ]} />
    </SectionCard>

    <SectionCard title="Built-in read-only scenarios">
      {builtIns.isLoading ? <p className="status">Loading built-in scenarios…</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · read-only baseline</p>
        <button type="button" onClick={() => createMutation.mutate({
          display_name: `${item.display_name} — Test Session`,
          built_in_scenario_id: item.scenario_id
        })}>New Test Session from {item.display_name}</button>
      </article>)}
      {builtIns.isError ? <p className="error">Built-in scenarios unavailable.</p> : null}
    </SectionCard>

    <SectionCard title="Test Sessions">
      <label>Open Test Session
        <select aria-label="Open Match Test Session" value={selectedSessionId ?? ''} onChange={(e) => setSelectedSessionId(e.target.value || null)}>
          <option value="">Portable scratch scenario</option>
          {sessions.data?.map((item) => <option key={item.session_id} value={item.session_id}>{item.display_name} · v{item.version}</option>)}
        </select>
      </label>
      {selectedSession ? <SummaryPills items={[
        { label: 'Session', value: selectedSession.display_name },
        { label: 'Version', value: selectedSession.version },
        { label: 'Source', value: selectedSession.scenario.source_kind },
        { label: 'Session fingerprint', value: selectedSession.session_fingerprint.slice(0, 12) }
      ]} /> : <p className="status">Scratch mode is non-persistent. Create a Test Session to keep an editable isolated copy.</p>}
    </SectionCard>

    <form onSubmit={submit}>
      <SectionCard title={selectedSession ? 'Editable Test Session scenario' : 'Portable scratch scenario JSON'}>
        {selectedSession ? <label>Session name
          <input aria-label="Match Lab session name" value={sessionName} onChange={(e) => setSessionName(e.target.value)} />
        </label> : null}
        <textarea aria-label="Match Lab scenario JSON" value={scenarioText} onChange={(e) => setScenarioText(e.target.value)}
          rows={28} style={{ width: '100%', fontFamily: 'monospace' }} />
        <label>Batch seeds (optional, comma-separated; max 100)
          <input aria-label="Match Lab batch seeds" value={batchText} onChange={(e) => setBatchText(e.target.value)} placeholder="100, 101, 102" />
        </label>
        {selectedSession ? <button type="button" onClick={save} disabled={saveMutation.isPending}>Save Test Session</button> : null}
        <button type="submit" disabled={runMutation.isPending}>{runMutation.isPending ? 'Running…' : selectedSession ? 'Run Test Session' : 'Run scenario'}</button>
        {localError ? <p className="error">{localError}</p> : null}
        {saveMutation.isError ? <p className="error">Save failed: {String(saveMutation.error)}</p> : null}
        {runMutation.isError ? <p className="error">Lab failed: {String(runMutation.error)}</p> : null}
        <p className="status">Scenario: {parsedPreview?.scenario_id ?? 'invalid JSON'} · seed {parsedPreview?.seed ?? '—'}</p>
      </SectionCard>
    </form>

    {runMutation.data ? <ResultPanels data={runMutation.data} /> : null}
  </section>
}
