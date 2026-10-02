import { FormEvent, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { runMatchTestLab } from '../api/client'
import type { MatchLabRequest, MatchLabScenario } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

const traits = {
  potential_ceiling: 90,
  growth_curve: 'balanced',
  professionalism: 0.7,
  ambition: 0.7,
  travel_tolerance: 0.7,
  schedule_aggression: 0.6,
  injury_proneness: 0.2,
  resilience: 0.8
}

const defaultScenario: MatchLabScenario = {
  schema_version: 'match_test_lab_scenario.v1',
  scenario_id: 'portable-match-example',
  seed: 777,
  source_kind: 'portable',
  context: {
    match_id: 'match-lab-example',
    player_a: {
      player: {
        player_id: 'LAB-A',
        name: 'Lab Player A',
        age: 27,
        nationality: 'TST',
        technique: 86,
        movement: 86,
        physical: 86,
        mental: 86,
        consistency: 86,
        clutch: 86,
        recovery: 86,
        play_style: 'tempo-controller',
        archetype: 'all-court tactician',
        hidden_career_traits: traits
      },
      form_modifier: 0,
      sharpness_modifier: 0,
      fatigue_modifier: 0,
      health_modifier: 0,
      travel_modifier: 0
    },
    player_b: {
      player: {
        player_id: 'LAB-B',
        name: 'Lab Player B',
        age: 27,
        nationality: 'TST',
        technique: 81,
        movement: 81,
        physical: 81,
        mental: 81,
        consistency: 81,
        clutch: 81,
        recovery: 81,
        play_style: 'counter-punching',
        archetype: 'durable grinder',
        hidden_career_traits: traits
      },
      form_modifier: 0,
      sharpness_modifier: 0,
      fatigue_modifier: 0,
      health_modifier: 0,
      travel_modifier: 0
    },
    best_of: 5,
    games_to: 11,
    win_by: 2,
    upset_variance: 0.12,
    retirement_rule: {
      enabled: false,
      retired_player_id: null,
      trigger: 'EXPLICIT_SET_START',
      set_number: null,
      probability: 0
    }
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

export function MatchTestLabPage(): JSX.Element {
  const [scenarioText, setScenarioText] = useState(JSON.stringify(defaultScenario, null, 2))
  const [batchText, setBatchText] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const mutation = useMutation({ mutationFn: runMatchTestLab })

  const parsedPreview = useMemo(() => {
    try {
      return JSON.parse(scenarioText) as MatchLabScenario
    } catch {
      return null
    }
  }, [scenarioText])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError(null)
    mutation.reset()
    try {
      const scenario = JSON.parse(scenarioText) as MatchLabScenario
      const payload: MatchLabRequest = { scenario, batch_seeds: parseSeeds(batchText) }
      mutation.mutate(payload)
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <section className="panel">
      <PageIntro
        title="Match Test Lab"
        subtitle="Global isolated sandbox for portable replayable Match Engine scenarios. Lab runs never mutate a Run or Branch."
      />

      <SectionCard title="Safety boundary">
        <p>
          This V1 calls the same production <code>MatchEngine.simulate</code> kernel used by authoritative match execution,
          but the scenario is detached from every mutable Run. A copied historical snapshot must be carried as data/provenance,
          never as a live link.
        </p>
        <SummaryPills
          items={[
            { label: 'Mode', value: 'read-only / non-persistent' },
            { label: 'Scenario', value: parsedPreview?.scenario_id ?? 'invalid JSON' },
            { label: 'Default seed', value: parsedPreview?.seed ?? '—' }
          ]}
        />
      </SectionCard>

      <form onSubmit={submit}>
        <SectionCard title="Portable scenario JSON">
          <p className="status">
            Edit any supported MatchContext field directly. This intentionally permits unusual test formats; compatibility warnings are reported separately.
          </p>
          <textarea
            aria-label="Match Lab scenario JSON"
            value={scenarioText}
            onChange={(event) => setScenarioText(event.target.value)}
            rows={28}
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
          <label>
            Batch seeds (optional, comma-separated; max 100)
            <input
              aria-label="Match Lab batch seeds"
              value={batchText}
              onChange={(event) => setBatchText(event.target.value)}
              placeholder="100, 101, 102"
            />
          </label>
          <button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Running…' : 'Run scenario'}
          </button>
          {localError ? <p className="error">{localError}</p> : null}
          {mutation.isError ? <p className="error">Lab failed: {String(mutation.error)}</p> : null}
        </SectionCard>
      </form>

      {mutation.data ? (
        <>
          <SectionCard title="Compatibility & isolation">
            <SummaryPills
              items={[
                { label: 'Engine', value: mutation.data.compatibility.match_engine_version },
                { label: 'Normal format', value: mutation.data.compatibility.normal_format ? 'yes' : 'no' },
                { label: 'Run mutation', value: mutation.data.compatibility.run_mutation_performed ? 'yes' : 'no' },
                { label: 'Live Run link', value: mutation.data.compatibility.run_live_link ? 'yes' : 'no' },
                { label: 'Scenario fingerprint', value: mutation.data.scenario_fingerprint.slice(0, 12) },
                { label: 'Request fingerprint', value: mutation.data.request_fingerprint.slice(0, 12) }
              ]}
            />
            <p className="status"><code>{mutation.data.compatibility.production_kernel}</code></p>
            {mutation.data.compatibility.warnings.length > 0 ? (
              <ul>
                {mutation.data.compatibility.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            ) : <p className="status">No compatibility warnings for this scenario.</p>}
          </SectionCard>

          <SectionCard title="Batch diagnostics">
            <SummaryPills
              items={[
                { label: 'Seeds', value: mutation.data.diagnostics.seed_count },
                { label: 'Distinct results', value: mutation.data.diagnostics.distinct_result_count },
                { label: 'Avg rallies', value: mutation.data.diagnostics.average_rally_count.toFixed(1) },
                { label: 'Avg elapsed (s)', value: mutation.data.diagnostics.average_elapsed_seconds.toFixed(1) },
                { label: 'Retirements', value: mutation.data.diagnostics.retirement_count }
              ]}
            />
            <p>
              Wins: {Object.entries(mutation.data.diagnostics.wins_by_player)
                .map(([player, wins]) => `${player}: ${wins}`).join(' · ')}
            </p>
          </SectionCard>

          <SectionCard title="Replayable results">
            <table aria-label="Match Lab results">
              <thead>
                <tr>
                  <th>Seed</th>
                  <th>Winner</th>
                  <th>Sets</th>
                  <th>Set scores (A-B)</th>
                  <th>Rallies</th>
                  <th>Elapsed</th>
                  <th>Result fingerprint</th>
                </tr>
              </thead>
              <tbody>
                {mutation.data.results.map((result) => (
                  <tr key={result.seed}>
                    <td>{result.seed}</td>
                    <td>{result.winner_player_id}</td>
                    <td>{Object.entries(result.sets_won).map(([player, sets]) => `${player} ${sets}`).join(' / ')}</td>
                    <td>{result.set_scores.join(', ')}</td>
                    <td>{result.rally_count}</td>
                    <td>{result.elapsed_seconds.toFixed(1)} s</td>
                    <td><code>{result.result_fingerprint.slice(0, 12)}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
