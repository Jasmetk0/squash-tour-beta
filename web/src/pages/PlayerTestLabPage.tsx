import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { getPlayerLabBuiltInScenarios, runPlayerTestLab } from '../api/client'
import type { PlayerLabResult, PlayerLabScenario } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

function ResultPanels({ data }: { data: PlayerLabResult }): JSX.Element {
  return <>
    <SectionCard title="Compatibility & isolation">
      <SummaryPills items={[
        { label: 'Variants', value: data.diagnostics.variant_count },
        { label: 'Weeks', value: data.diagnostics.duration_weeks },
        { label: 'Distinct final states', value: data.diagnostics.distinct_final_state_count },
        { label: 'Health', value: data.compatibility.health_supported ? 'supported' : 'not yet supported' },
        { label: 'Training Load', value: data.compatibility.training_load_supported ? 'supported' : 'not yet supported' },
        { label: 'Career AI', value: data.compatibility.career_ai_supported ? 'supported' : 'not yet supported' }
      ]} />
      <p className="status">Shared production kernels: <code>{data.compatibility.production_kernels.join(' + ')}</code></p>
      <ul>{data.compatibility.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
    </SectionCard>

    {data.variants.map((variant) => <SectionCard key={variant.variant_id} title={variant.display_name}>
      <SummaryPills items={[
        { label: 'Variant', value: variant.variant_id },
        { label: 'Final OVR', value: variant.snapshots.at(-1)?.ovr ?? '—' },
        { label: 'Final sharpness', value: variant.snapshots.at(-1)?.match_sharpness ?? '—' },
        { label: 'Final fatigue', value: variant.snapshots.at(-1)?.long_term_fatigue ?? '—' },
        { label: 'Final state', value: variant.final_state_fingerprint.slice(0, 12) }
      ]} />
      <table aria-label={`Player Lab ${variant.variant_id} timeline`}>
        <thead><tr>
          <th>Week</th><th>Age</th><th>Matches</th><th>OVR</th><th>Potential</th>
          <th>Form</th><th>Sharpness</th><th>Fatigue</th><th>Changed attrs</th><th>Δ attributes</th>
        </tr></thead>
        <tbody>{variant.snapshots.map((snapshot) => <tr key={snapshot.state_fingerprint}>
          <td>S{snapshot.week.season_index + 1} W{snapshot.week.week}</td>
          <td>{snapshot.age}</td>
          <td>{snapshot.completed_competitive_matches}</td>
          <td>{snapshot.ovr}</td>
          <td>{snapshot.potential_ovr}</td>
          <td>{snapshot.current_form}</td>
          <td>{snapshot.match_sharpness}</td>
          <td>{snapshot.long_term_fatigue}</td>
          <td>{snapshot.changed_attribute_count}</td>
          <td>{snapshot.attribute_delta_total > 0 ? '+' : ''}{snapshot.attribute_delta_total}</td>
        </tr>)}</tbody>
      </table>
    </SectionCard>)}
  </>
}

export function PlayerTestLabPage(): JSX.Element {
  const builtIns = useQuery({
    queryKey: ['player-lab-built-ins'],
    queryFn: getPlayerLabBuiltInScenarios,
    retry: false
  })
  const [scenarioText, setScenarioText] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    if (!scenarioText && builtIns.data?.[0]) {
      setScenarioText(JSON.stringify(builtIns.data[0].scenario, null, 2))
    }
  }, [builtIns.data, scenarioText])

  const parsedPreview = useMemo(() => {
    try { return scenarioText ? JSON.parse(scenarioText) as PlayerLabScenario : null }
    catch { return null }
  }, [scenarioText])

  const runMutation = useMutation({
    mutationFn: (scenario: PlayerLabScenario) => runPlayerTestLab({ scenario })
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError(null)
    runMutation.reset()
    try {
      if (!scenarioText.trim()) throw new Error('Load or enter a Player Lab scenario first.')
      runMutation.mutate(JSON.parse(scenarioText) as PlayerLabScenario)
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return <section className="panel">
    <PageIntro
      title="Player Test Lab"
      subtitle="Global isolated development sandbox using the same canonical weekly sporting kernels as Product Runs."
    />

    <SectionCard title="Safety boundary">
      <p>
        Player Lab V1 never creates, saves or mutates a Product Run. Portable scenarios are replayable JSON.
        V1 deliberately tests only development inputs already supported by the canonical sporting kernel;
        Health, Training Load, Experience, Match Preparation, Financial Level and career AI remain explicit follow-up work.
      </p>
      <SummaryPills items={[
        { label: 'Run mutation', value: 'never' },
        { label: 'Live Run link', value: 'none' },
        { label: 'Kernel', value: 'canonical weekly development' }
      ]} />
    </SectionCard>

    <SectionCard title="Built-in read-only scenarios">
      {builtIns.isLoading ? <p className="status">Loading built-in scenarios…</p> : null}
      {builtIns.isError ? <p className="error">Built-in Player Lab scenarios unavailable.</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · read-only baseline</p>
        <button type="button" onClick={() => setScenarioText(JSON.stringify(item.scenario, null, 2))}>
          Load scenario
        </button>
      </article>)}
    </SectionCard>

    <form onSubmit={submit}>
      <SectionCard title="Portable Player Lab scenario JSON">
        <textarea
          aria-label="Player Lab scenario JSON"
          value={scenarioText}
          onChange={(event) => setScenarioText(event.target.value)}
          rows={30}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        <button type="submit" disabled={runMutation.isPending || !parsedPreview}>
          {runMutation.isPending ? 'Running…' : 'Run scenario'}
        </button>
        {localError ? <p className="error">{localError}</p> : null}
        {runMutation.isError ? <p className="error">Player Lab failed: {String(runMutation.error)}</p> : null}
        <p className="status">
          Scenario: {parsedPreview?.scenario_id ?? 'invalid JSON'} · variants {parsedPreview?.variants.length ?? '—'}
        </p>
      </SectionCard>
    </form>

    {runMutation.data ? <ResultPanels data={runMutation.data} /> : null}
  </section>
}
