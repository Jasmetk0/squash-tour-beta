import { HistoricalLabSourcePicker } from '../components/HistoricalLabSourcePicker'
import { LabSessionConflict, useLabSessionEditor, validateLabSession, type LabEditorTicket } from '../components/LabSessionEditor'
import { useLanguage } from '../i18n/LanguageContext'
import {InitialPopulationComparisonPanel} from '../components/InitialPopulationComparisonPanel'
import { LabNavigation } from '../components/LabNavigation'
import { LabScenarioAuthoring } from '../components/labAuthoring/LabScenarioAuthoring'
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useIsMutating, useMutation, useQuery } from '@tanstack/react-query'

import { getPlayerLabBuiltInScenarios, runPlayerTestLab, listPlayerLabSessions, savePlayerLabSession, importPlayerLabHistory, runPlayerLabSession } from '../api/client'
import type { PlayerLabResult, PlayerLabScenario, PlayerLabSession } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

function ResultPanels({ data }: { data: PlayerLabResult }): JSX.Element {
  const {language} = useLanguage(), cs = language === 'cs'
  const [variantFilter, setVariantFilter] = useState('all')
  const [weekLimit, setWeekLimit] = useState<'all' | '10' | '25'>('all')
  const selectedVariant = data.variants.some(variant => variant.variant_id === variantFilter) ? variantFilter : 'all'
  const visibleVariants = selectedVariant === 'all'
    ? data.variants : data.variants.filter(variant => variant.variant_id === selectedVariant)

  return <>
    <SectionCard title={cs ? "Kompatibilita a izolace" : "Compatibility & isolation"}>
      <SummaryPills items={[
        { label: cs ? 'Varianty' : 'Variants', value: data.diagnostics.variant_count },
        { label: cs ? 'Týdny' : 'Weeks', value: data.diagnostics.duration_weeks },
        { label: cs ? 'Různé konečné stavy' : 'Distinct final states', value: data.diagnostics.distinct_final_state_count },
        { label: 'Health', value: data.compatibility.health_supported ? (cs ? 'podporováno' : 'supported') : (cs ? 'dosud nepodporováno' : 'not yet supported') },
        { label: 'Training Load', value: data.compatibility.training_load_supported ? (cs ? 'podporováno' : 'supported') : (cs ? 'dosud nepodporováno' : 'not yet supported') },
        { label: 'Career AI', value: data.compatibility.career_ai_supported ? (cs ? 'podporováno' : 'supported') : (cs ? 'dosud nepodporováno' : 'not yet supported') }
      ]} />
      <p className="status">{cs ? "Sdílená produkční jádra" : "Shared production kernels"}: <code>{data.compatibility.production_kernels.join(" + ")}</code></p>
      <ul>{data.compatibility.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
    </SectionCard>

    <SectionCard title={cs ? "Porovnání výsledků variant" : "Compare variant outcomes"}>
      <p className="status">{cs ? "Porovnání zahrnuje všechny varianty. Změny měří rozdíl mezi prvním a posledním uloženým snapshotem, nikoli vůči počátečnímu stavu hráče. Filtr mění pouze zobrazení časových os." : "All Lab variants are included. Changes compare first and last recorded snapshots, not the initial player state. Filters below change only the displayed timelines."}</p>
      {data.variants.length > 0 ? <table aria-label="Player Lab variant comparison">
        <thead><tr><th>{cs ? "Varianta" : "Variant"}</th><th>{cs ? "Snapshoty" : "Snapshots"}</th><th>{cs ? "Konečné OVR" : "Final OVR"}</th><th>{cs ? "Změna OVR" : "OVR change"}</th><th>{cs ? "Konečná připravenost" : "Final sharpness"}</th><th>{cs ? "Změna připravenosti" : "Sharpness change"}</th><th>{cs ? "Konečná únava" : "Final fatigue"}</th><th>{cs ? "Konečný stav" : "Final state"}</th></tr></thead>
        <tbody>{data.variants.map(variant => {
          const first = variant.snapshots[0]
          const last = variant.snapshots[variant.snapshots.length - 1]
          const change = (finalValue: number, firstValue: number) => {
            const delta = finalValue - firstValue
            return delta > 0 ? `+${delta}` : String(delta)
          }
          return <tr key={variant.variant_id}>
            <td>{variant.display_name}</td><td>{variant.snapshots.length}</td>
            <td>{last?.ovr ?? '—'}</td>
            <td>{variant.snapshots.length > 1 ? change(last.ovr, first.ovr) : '—'}</td>
            <td>{last?.match_sharpness ?? '—'}</td>
            <td>{variant.snapshots.length > 1 ? change(last.match_sharpness, first.match_sharpness) : '—'}</td>
            <td>{last?.long_term_fatigue ?? '—'}</td>
            <td><code>{variant.final_state_fingerprint.slice(0, 12)}</code></td>
          </tr>
        })}</tbody>
      </table> : <p className="status">{cs ? "Nejsou dostupné výsledky žádné varianty." : "No variant results were returned."}</p>}
    </SectionCard>

    <SectionCard title={cs ? "Nastavení zobrazení časové osy" : "Timeline display options"}>
      <label>{cs ? "Zobrazit varianty" : "Show variants"}
        <select aria-label="Player Lab variant filter" value={selectedVariant} onChange={event => setVariantFilter(event.target.value)}>
          <option value="all">{cs ? "Všechny varianty" : "All variants"}</option>
          {data.variants.map(variant => <option key={variant.variant_id} value={variant.variant_id}>{variant.display_name}</option>)}
        </select>
      </label>
      <label>{cs ? "Počet zobrazených snapshotů" : "Timeline weeks"}
        <select aria-label="Player Lab timeline limit" value={weekLimit} onChange={event => setWeekLimit(event.target.value as typeof weekLimit)}>
          <option value="all">{cs ? "Všechny snapshoty" : "All snapshots"}</option>
          <option value="10">{cs ? "Posledních 10 snapshotů" : "Last 10 snapshots"}</option>
          <option value="25">{cs ? "Posledních 25 snapshotů" : "Last 25 snapshots"}</option>
        </select>
      </label>
      <p role="status" className="status">{cs ? `Zobrazeno ${visibleVariants.length} z ${data.variants.length} variant` : `Showing ${visibleVariants.length} of ${data.variants.length} variants`}. {cs ? "Filtry nespouští nový výpočet vývoje." : "Filters do not recalculate development."}</p>
    </SectionCard>

    {visibleVariants.map((variant) => <SectionCard key={variant.variant_id} title={variant.display_name}>
      <SummaryPills items={[
        { label: cs ? 'Varianta' : 'Variant', value: variant.variant_id },
        { label: cs ? 'Konečné OVR' : 'Final OVR', value: variant.snapshots[variant.snapshots.length - 1]?.ovr ?? '—' },
        { label: cs ? 'Konečná připravenost' : 'Final sharpness', value: variant.snapshots[variant.snapshots.length - 1]?.match_sharpness ?? '—' },
        { label: cs ? 'Konečná únava' : 'Final fatigue', value: variant.snapshots[variant.snapshots.length - 1]?.long_term_fatigue ?? '—' },
        { label: cs ? 'Konečná závažnost Health' : 'Final Health severity', value: variant.snapshots[variant.snapshots.length - 1]?.health_projection.highest_current_severity ?? 0 },
        { label: cs ? 'Číselný vliv Health' : 'Health numeric effect', value: variant.snapshots[variant.snapshots.length - 1]?.health_projection.numeric_effect_applied ? (cs ? 'aktivní' : 'active') : (cs ? 'nenakalibrováno' : 'not calibrated') },
        { label: cs ? 'Konečný stav' : 'Final state', value: variant.final_state_fingerprint.slice(0, 12) }
      ]} />
      <p className="status">
        {cs ? "Zobrazeno" : "Showing"} {weekLimit === "all" ? variant.snapshots.length : Math.min(variant.snapshots.length, Number(weekLimit))} {cs ? "z" : "of"} {variant.snapshots.length} {cs ? "uložených snapshotů." : "saved snapshots."}
      </p>
      <table aria-label={`Player Lab ${variant.variant_id} timeline`}>
        <thead><tr>
          <th>{cs ? "Týden" : "Week"}</th><th>{cs ? "Věk" : "Age"}</th><th>{cs ? "Zápasy" : "Matches"}</th><th>OVR</th><th>{cs ? "Potenciál" : "Potential"}</th>
          <th>{cs ? "Forma" : "Form"}</th><th>{cs ? "Připravenost" : "Sharpness"}</th><th>{cs ? "Únava" : "Fatigue"}</th><th>{cs ? "Závažnost Health" : "Health severity"}</th><th>{cs ? "Oblasti Health" : "Health domains"}</th><th>{cs ? "Změněné atributy" : "Changed attrs"}</th><th>{cs ? "Δ atributů" : "Δ attributes"}</th>
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
  const {language} = useLanguage(), cs = language === 'cs'
  const sessions = useQuery({queryKey: ['player-lab-sessions'], queryFn: listPlayerLabSessions, retry: false})
  const editor = useLabSessionEditor<PlayerLabSession>(sessions.data, sessions.isSuccess, '', 'Player experiment')
  const {scenarioText, setScenarioText, selectedSession, sessionConflict, sessionHasUnsavedChanges} = editor
  const [discard, setDiscard] = useState(false)
  const [source, setSource] = useState({run: '', branch: '', revision: '', player: ''})
  const [duration, setDuration] = useState(8)
  const sourceSelection = useRef('')
  sourceSelection.current = JSON.stringify([source, duration])
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
      return ['player_test_lab_scenario.v1', 'player_test_lab_scenario.v2'].includes(candidate.schema_version ?? '')
        && typeof candidate.scenario_id === 'string' && candidate.scenario_id.length > 0
        && Array.isArray(candidate.variants)
        ? candidate as PlayerLabScenario : null
    } catch { return null }
  }, [scenarioText])

  const runPending = useIsMutating({ mutationKey: ['player-lab-run'] }) > 0
  const runMutation = useMutation({
    mutationKey: ['player-lab-run'],
    mutationFn: (input: {scenario: PlayerLabScenario; session: Pick<PlayerLabSession, 'session_id' | 'session_fingerprint'> | null}) =>
      input.session ? runPlayerLabSession(input.session.session_id, input.session.session_fingerprint) : runPlayerTestLab({ scenario: input.scenario })
  })

  const saveMutation = useMutation({
    mutationKey: ['player-lab-write'],
    mutationFn: async (input: {scenario: PlayerLabScenario; session: PlayerLabSession | null; name: string; ticket: LabEditorTicket}) =>
      validateLabSession(await savePlayerLabSession({display_name: input.name, scenario: input.scenario,
        expected_session_fingerprint: input.session?.session_fingerprint}, input.session?.session_id), input.session?.session_id),
    onSuccess: (saved, {ticket}) => { void sessions.refetch(); if (editor.acceptSession(saved, ticket)) runMutation.reset() }
  })
  const importMutation = useMutation({
    mutationKey: ['player-lab-write'],
    mutationFn: (input: {source: typeof source; duration: number; selection: string; ticket: LabEditorTicket}) => importPlayerLabHistory({
      product_run_id: input.source.run, branch_id: input.source.branch, saved_revision_id: input.source.revision,
      player_id: input.source.player, duration_weeks: input.duration}),
    onSuccess: (scenario, input) => {
      if (input.selection === sourceSelection.current && editor.acceptScenario(JSON.stringify(scenario, null, 2), input.ticket)) {
        initialScenarioHandled.current = true; runMutation.reset()
      }
    }
  })
  const writePending = useIsMutating({mutationKey: ['player-lab-write']}) > 0
  useEffect(() => {runMutation.reset()}, [editor.selectedSessionId, sessionConflict, selectedSession?.session_fingerprint])

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
    if (runPending || sessionConflict || sessionHasUnsavedChanges) return
    setLocalError(null)
    runMutation.reset()
    try {
      if (!scenarioText.trim()) throw new Error('Load or enter a Player Lab scenario first.')
      if (!parsedPreview) throw new Error('Player Lab scenario must contain its schema, ID and variants.')
      // Mutation setup and offline resumption may run after another selection.
      // Bind the reviewed source at submission, never through a live closure.
      runMutation.mutate({scenario: parsedPreview, session: selectedSession ? {
        session_id: selectedSession.session_id,
        session_fingerprint: selectedSession.session_fingerprint
      } : null})
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
    <SectionCard title={cs ? 'Uložené experimenty hráče' : 'Saved Player experiments'}>
      <label>{cs ? 'Session' : 'Session'} <select aria-label="Open Player Test Session" value={editor.selectedSessionId ?? ''}
        disabled={sessionHasUnsavedChanges && !discard} onChange={e => {initialScenarioHandled.current = true; editor.setSelectedSessionId(e.target.value || null); setDiscard(false)}}>
        <option value="">{cs ? 'Pracovní scénář' : 'Scratch scenario'}</option>
        {sessions.data?.map(item => <option key={item.session_id} value={item.session_id}>{item.display_name}</option>)}
      </select></label>
      {sessionHasUnsavedChanges && <label><input type="checkbox" checked={discard} onChange={e => setDiscard(e.target.checked)} />{cs ? 'Zahodit místní změny při změně Session' : 'Discard local edits when switching Session'}</label>}
      <label>{cs ? 'Název' : 'Name'} <input aria-label="Player Test Session name" value={editor.sessionName} onChange={e => editor.setSessionName(e.target.value)} /></label>
      <button type="button" onClick={() => void sessions.refetch()}>{cs ? 'Obnovit seznam Session' : 'Refresh Player Test Sessions'}</button>
      <button type="button" disabled={!parsedPreview || writePending || Boolean(sessionConflict)} onClick={() => parsedPreview && saveMutation.mutate({scenario: parsedPreview, session: selectedSession, name: editor.sessionName, ticket: editor.captureEditor()})}>{cs ? 'Uložit experiment' : 'Save Player Test Session'}</button>
      <LabSessionConflict conflict={sessionConflict} dirty={sessionHasUnsavedChanges} canReload={editor.canReloadSession} onReload={editor.reloadSession} />
      {saveMutation.isError && <p role="alert">{String(saveMutation.error)}</p>}
    </SectionCard>
    <SectionCard title={cs ? 'Historický hráč → nezávislý experiment' : 'Historical player → independent experiment'}>
      <HistoricalLabSourcePicker lab="Player Lab" run={source.run} branch={source.branch} revision={source.revision}
        onChange={(run, branch, revision) => setSource({...source, run, branch, revision})} />
      {(['run', 'branch', 'revision', 'player'] as const).map(key => <label key={key}>{cs ? ({run: 'Run', branch: 'Větev', revision: 'Uložená revize', player: 'Hráč', event: 'Turnaj'})[key] : key}
        <input aria-label={`Player Lab import ${key}`} value={source[key]} onChange={e => setSource({...source, [key]: e.target.value})} />
      </label>)}
      <label>{cs ? 'Počet týdnů experimentu' : 'Experiment weeks'} <input aria-label="Player Lab experiment weeks" type="number" min={1} max={61} value={duration} onChange={e => setDuration(Number(e.target.value))} /></label>
      <button type="button" disabled={writePending || sessionHasUnsavedChanges || Boolean(sessionConflict) || !Object.values(source).every(Boolean)}
        onClick={() => importMutation.mutate({source, duration, selection: sourceSelection.current, ticket: editor.captureEditor()})}>{cs ? 'Importovat historického hráče' : 'Import historical Player scenario'}</button>
      {importMutation.isError && <p role="alert">{String(importMutation.error)}</p>}
      {parsedPreview?.source_snapshot && <p aria-label="Player Lab historical provenance">
        {parsedPreview.source_snapshot.biography.name} · {parsedPreview.source_snapshot.run_id} / {parsedPreview.source_snapshot.selected_branch_id} / {parsedPreview.source_snapshot.saved_revision_id}
        {' · '}{cs ? 'Vlastník historie' : 'Historical owner'}: {parsedPreview.source_snapshot.owner_branch_id}
        {' · '}W{parsedPreview.source_snapshot.week.calendar.weeks_per_year} · S{parsedPreview.source_snapshot.week.season_index + 1} W{parsedPreview.source_snapshot.week.week}
        {' · '}{cs ? 'Úplný sportovní stav a uložené Health; automatické léčení není podporováno.' : 'Complete sporting state and stored Health; automatic healing is unsupported.'}
      </p>}
    </SectionCard>

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
      <button type="button" disabled={builtIns.isFetching} onClick={() => { void builtIns.refetch() }}>
        {builtIns.isFetching ? 'Refreshing Player Lab scenarios…' : 'Refresh built-in scenarios'}
      </button>
      {builtIns.isLoading ? <p role="status">Loading built-in scenarios…</p> : null}
      {builtIns.isError ? <p role="alert" className="error">Built-in Player Lab scenarios unavailable.</p> : null}
      {builtIns.isSuccess && builtIns.data.length === 0
        ? <p className="status">No built-in Player Lab scenarios are available.</p> : null}
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
        <LabScenarioAuthoring kind="player" text={scenarioText} onChange={editScenario}
          jsonLabel="Player Lab scenario JSON" selection={selectedSession ? `${selectedSession.session_id}:${selectedSession.session_fingerprint}` : 'scratch'} revision={editor.editorEdit}
          savedScenario={selectedSession?.scenario} savedName={selectedSession?.display_name}
          sessionName={editor.sessionName} />
        <button type="button" onClick={formatScenario} disabled={runPending || Boolean(sessionConflict) || sessionHasUnsavedChanges || !parsedPreview}>
          Format JSON
        </button>{' '}
        <button type="submit" disabled={runPending || Boolean(sessionConflict) || sessionHasUnsavedChanges || !parsedPreview}>
          {runPending ? 'Running…' : 'Run scenario'}
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
