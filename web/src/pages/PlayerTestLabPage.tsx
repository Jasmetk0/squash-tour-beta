import {InitialPopulationComparisonPanel} from '../components/InitialPopulationComparisonPanel'
import { LabNavigation } from '../components/LabNavigation'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { getPlayerLabBuiltInScenarios, runPlayerTestLab } from '../api/client'
import type { PlayerLabResult, PlayerLabScenario } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

function ResultPanels({ data }: { data: PlayerLabResult }): JSX.Element {
  const [variantFilter, setVariantFilter] = useState('all')
  const [weekLimit, setWeekLimit] = useState<'all' | '10' | '25'>('all')
  const selectedVariant = data.variants.some(variant => variant.variant_id === variantFilter) ? variantFilter : 'all'
  const visibleVariants = selectedVariant === 'all'
    ? data.variants : data.variants.filter(variant => variant.variant_id === selectedVariant)

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

    <SectionCard title="Compare variant outcomes">
      <p className="status">All saved Lab variants are included. Filters below change only the displayed timelines.</p>
      {data.variants.length > 0 ? <table aria-label="Player Lab variant comparison">
        <thead><tr><th>Variant</th><th>Snapshots</th><th>Final OVR</th><th>Final sharpness</th><th>Final fatigue</th><th>Final state</th></tr></thead>
        <tbody>{data.variants.map(variant => {
          const last = variant.snapshots[variant.snapshots.length - 1]
          return <tr key={variant.variant_id}>
            <td>{variant.display_name}</td><td>{variant.snapshots.length}</td>
            <td>{last?.ovr ?? '—'}</td><td>{last?.match_sharpness ?? '—'}</td>
            <td>{last?.long_term_fatigue ?? '—'}</td>
            <td><code>{variant.final_state_fingerprint.slice(0, 12)}</code></td>
          </tr>
        })}</tbody>
      </table> : <p className="status">No variant results were returned.</p>}
    </SectionCard>

    <SectionCard title="Timeline display options">
      <label>Show variants
        <select aria-label="Player Lab variant filter" value={selectedVariant} onChange={event => setVariantFilter(event.target.value)}>
          <option value="all">All variants</option>
          {data.variants.map(variant => <option key={variant.variant_id} value={variant.variant_id}>{variant.display_name}</option>)}
        </select>
      </label>
      <label>Timeline weeks
        <select aria-label="Player Lab timeline limit" value={weekLimit} onChange={event => setWeekLimit(event.target.value as typeof weekLimit)}>
          <option value="all">All snapshots</option>
          <option value="10">Last 10 snapshots</option>
          <option value="25">Last 25 snapshots</option>
        </select>
      </label>
      <p className="status">Showing {visibleVariants.length} of {data.variants.length} variants. Filters do not recalculate development.</p>
    </SectionCard>

    {visibleVariants.map((variant) => <SectionCard key={variant.variant_id} title={variant.display_name}>
      <SummaryPills items={[
        { label: 'Variant', value: variant.variant_id },
        { label: 'Final OVR', value: variant.snapshots[variant.snapshots.length - 1]?.ovr ?? '—' },
        { label: 'Final sharpness', value: variant.snapshots[variant.snapshots.length - 1]?.match_sharpness ?? '—' },
        { label: 'Final fatigue', value: variant.snapshots[variant.snapshots.length - 1]?.long_term_fatigue ?? '—' },
        { label: 'Final Health severity', value: variant.snapshots[variant.snapshots.length - 1]?.health_projection.highest_current_severity ?? 0 },
        { label: 'Health numeric effect', value: variant.snapshots[variant.snapshots.length - 1]?.health_projection.numeric_effect_applied ? 'active' : 'not calibrated' },
        { label: 'Final state', value: variant.final_state_fingerprint.slice(0, 12) }
      ]} />
      <p className="status">
        Showing {weekLimit === 'all' ? variant.snapshots.length : Math.min(variant.snapshots.length, Number(weekLimit))} of {variant.snapshots.length} saved snapshots.
      </p>
      <table aria-label={`Player Lab ${variant.variant_id} timeline`}>
        <thead><tr>
          <th>Week</th><th>Age</th><th>Matches</th><th>OVR</th><th>Potential</th>
          <th>Form</th><th>Sharpness</th><th>Fatigue</th><th>Health severity</th><th>Health domains</th><th>Changed attrs</th><th>Δ attributes</th>
        </tr></thead>
        <tbody>{(weekLimit === 'all' ? variant.snapshots : variant.snapshots.slice(-Number(weekLimit))).map((snapshot) => <tr key={snapshot.state_fingerprint}>
          <td>S{snapshot.week.season_index + 1} W{snapshot.week.week}</td>
          <td>{snapshot.age}</td>
          <td>{snapshot.completed_competitive_matches}</td>
          <td>{snapshot.ovr}</td>
          <td>{snapshot.potential_ovr}</td>
          <td>{snapshot.current_form}</td>
          <td>{snapshot.match_sharpness}</td>
          <td>{snapshot.long_term_fatigue}</td>
          <td>{snapshot.health_projection.highest_current_severity}</td>
          <td>{snapshot.health_projection.affected_domains.join(', ') || '—'}</td>
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
  const initialScenarioHandled = useRef(false)

  useEffect(() => {
    if (!initialScenarioHandled.current && builtIns.data?.[0]) {
      initialScenarioHandled.current = true
      setScenarioText(JSON.stringify(builtIns.data[0].scenario, null, 2))
    }
  }, [builtIns.data])

  // This is an editor preview only. The API remains authoritative for full validation.
  const parsedPreview = useMemo(() => {
    try {
      const value: unknown = scenarioText.trim() ? JSON.parse(scenarioText) : null
      if (!value || typeof value !== 'object' || Array.isArray(value)) return null
      const candidate = value as Partial<PlayerLabScenario>
      return candidate.schema_version === 'player_test_lab_scenario.v1'
        && typeof candidate.scenario_id === 'string' && candidate.scenario_id.length > 0
        && Array.isArray(candidate.variants)
        ? candidate as PlayerLabScenario : null
    } catch { return null }
  }, [scenarioText])

  const runMutation = useMutation({
    mutationFn: (scenario: PlayerLabScenario) => runPlayerTestLab({ scenario })
  })

  const editScenario = (value: string) => {
    initialScenarioHandled.current = true
    setScenarioText(value)
    setLocalError(null)
    runMutation.reset()
  }

  const formatScenario = () => {
    if (!parsedPreview) {
      setLocalError('Enter a valid Player Lab scenario before formatting.')
      return
    }
    editScenario(JSON.stringify(parsedPreview, null, 2))
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError(null)
    runMutation.reset()
    try {
      if (!scenarioText.trim()) throw new Error('Load or enter a Player Lab scenario first.')
      if (!parsedPreview) throw new Error('Player Lab scenario must contain its schema, ID and variants.')
      runMutation.mutate(parsedPreview)
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error))
    }
  }

  return <section className="panel">
    <PageIntro
      title="Player Test Lab"
      subtitle="Global isolated development sandbox using the same canonical weekly sporting kernels as Product Runs."
    />

    <LabNavigation active="player" />
    <InitialPopulationComparisonPanel />

    <SectionCard title="Safety boundary">
      <p>
        Player Lab V1 never creates, saves or mutates a Product Run. Portable scenarios are replayable JSON.
        Player Lab now also accepts an explicit canonical Health timeline and projects it through the same
        Match Health limitation authority used by Product Runs. Health generation/healing and numeric sporting
        effects remain deliberately uncalibrated; Training Load, Experience, Match Preparation, Financial Level
        and career AI remain explicit follow-up work.
      </p>
      <SummaryPills items={[
        { label: 'Run mutation', value: 'never' },
        { label: 'Live Run link', value: 'none' },
        { label: 'Kernel', value: 'weekly development + Match Health projection' }
      ]} />
    </SectionCard>

    <SectionCard title="Built-in read-only scenarios">
      {builtIns.isLoading ? <p className="status">Loading built-in scenarios…</p> : null}
      {builtIns.isError ? <p className="error">Built-in Player Lab scenarios unavailable.</p> : null}
      {builtIns.data?.map((item) => <article key={item.scenario_id}>
        <strong>{item.display_name}</strong>
        <p>{item.description}</p>
        <p className="status"><code>{item.scenario_fingerprint.slice(0, 12)}</code> · read-only baseline</p>
        <button type="button" onClick={() => editScenario(JSON.stringify(item.scenario, null, 2))}>
          Load scenario
        </button>
      </article>)}
    </SectionCard>

    <form onSubmit={submit}>
      <SectionCard title="Portable Player Lab scenario JSON">
        <textarea
          aria-label="Player Lab scenario JSON"
          value={scenarioText}
          onChange={(event) => editScenario(event.target.value)}
          rows={30}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        <button type="button" onClick={formatScenario} disabled={runMutation.isPending || !parsedPreview}>
          Format JSON
        </button>{' '}
        <button type="submit" disabled={runMutation.isPending || !parsedPreview}>
          {runMutation.isPending ? 'Running…' : 'Run scenario'}
        </button>
        {localError ? <p className="error">{localError}</p> : null}
        {runMutation.isError ? <p className="error">Player Lab failed: {String(runMutation.error)}</p> : null}
        <p className="status">
          Scenario: {parsedPreview?.scenario_id ?? 'invalid / incomplete JSON'} · variants {parsedPreview?.variants.length ?? '—'}
        </p>
      </SectionCard>
    </form>

    {runMutation.data ? <ResultPanels data={runMutation.data} /> : null}
  </section>
}
