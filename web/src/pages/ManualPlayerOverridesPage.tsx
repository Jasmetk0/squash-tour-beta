import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChangeEvent, FormEvent, useMemo, useRef, useState } from 'react'

import {
  createManualPlayerOverride,
  deleteManualPlayerOverride,
  exportManualPlayerOverridesCsv,
  importManualPlayerOverrides,
  listManualPlayerOverrides,
  updateManualPlayerOverride
} from '../api/client'
import type {
  ManualPlayerOverrideRecord,
  ManualPlayerOverridesImportResponse,
  ManualPlayerOverrideUpsertPayload
} from '../api/types'
import { EmptyState, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type Mode = 'create' | 'edit'

type FormState = {
  override_id: string
  season: number
  country_code: string
  player_name: string
  player_slug: string
  player_id: string
  age: number
  profile_tier: 'strong' | 'elite' | 'special' | 'generational'
  quality_band_override: string
  technique: string
  movement: string
  physical: string
  mental: string
  consistency: string
  clutch: string
  recovery: string
  potential_ceiling: string
  growth_curve: string
  professionalism: string
  ambition: string
  travel_tolerance: string
  schedule_aggression: string
  injury_proneness: string
  resilience: string
  is_exceptional: boolean
  enabled: boolean
  notes: string
}

const EMPTY_FORM: FormState = {
  override_id: '',
  season: 2027,
  country_code: '',
  player_name: '',
  player_slug: '',
  player_id: '',
  age: 18,
  profile_tier: 'elite',
  quality_band_override: '',
  technique: '',
  movement: '',
  physical: '',
  mental: '',
  consistency: '',
  clutch: '',
  recovery: '',
  potential_ceiling: '',
  growth_curve: '',
  professionalism: '',
  ambition: '',
  travel_tolerance: '',
  schedule_aggression: '',
  injury_proneness: '',
  resilience: '',
  is_exceptional: false,
  enabled: true,
  notes: ''
}

function toForm(item: ManualPlayerOverrideRecord): FormState {
  return {
    override_id: item.override_id,
    season: item.season,
    country_code: item.country_code,
    player_name: item.player_name,
    player_slug: item.player_slug ?? '',
    player_id: item.player_id ?? '',
    age: item.age,
    profile_tier: item.profile_tier,
    quality_band_override: item.quality_band_override ?? '',
    technique: item.attribute_overrides?.technique ? String(item.attribute_overrides.technique) : '',
    movement: item.attribute_overrides?.movement ? String(item.attribute_overrides.movement) : '',
    physical: item.attribute_overrides?.physical ? String(item.attribute_overrides.physical) : '',
    mental: item.attribute_overrides?.mental ? String(item.attribute_overrides.mental) : '',
    consistency: item.attribute_overrides?.consistency ? String(item.attribute_overrides.consistency) : '',
    clutch: item.attribute_overrides?.clutch ? String(item.attribute_overrides.clutch) : '',
    recovery: item.attribute_overrides?.recovery ? String(item.attribute_overrides.recovery) : '',
    potential_ceiling: item.hidden_trait_overrides?.potential_ceiling
      ? String(item.hidden_trait_overrides.potential_ceiling)
      : '',
    growth_curve: item.hidden_trait_overrides?.growth_curve ?? '',
    professionalism: item.hidden_trait_overrides?.professionalism ? String(item.hidden_trait_overrides.professionalism) : '',
    ambition: item.hidden_trait_overrides?.ambition ? String(item.hidden_trait_overrides.ambition) : '',
    travel_tolerance: item.hidden_trait_overrides?.travel_tolerance ? String(item.hidden_trait_overrides.travel_tolerance) : '',
    schedule_aggression: item.hidden_trait_overrides?.schedule_aggression
      ? String(item.hidden_trait_overrides.schedule_aggression)
      : '',
    injury_proneness: item.hidden_trait_overrides?.injury_proneness ? String(item.hidden_trait_overrides.injury_proneness) : '',
    resilience: item.hidden_trait_overrides?.resilience ? String(item.hidden_trait_overrides.resilience) : '',
    is_exceptional: item.is_exceptional,
    enabled: item.enabled,
    notes: item.notes ?? ''
  }
}

function toPayload(form: FormState): ManualPlayerOverrideUpsertPayload {
  const toInt = (value: string): number | null => {
    if (!value.trim()) return null
    const parsed = Number.parseInt(value, 10)
    return Number.isFinite(parsed) ? parsed : null
  }
  const toFloat = (value: string): number | null => {
    if (!value.trim()) return null
    const parsed = Number.parseFloat(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return {
    override_id: form.override_id.trim(),
    season: form.season,
    country_code: form.country_code.trim().toUpperCase(),
    player_name: form.player_name.trim(),
    player_slug: form.player_slug.trim() || null,
    player_id: form.player_id.trim() || null,
    age: form.age,
    profile_tier: form.profile_tier,
    quality_band_override: form.quality_band_override || null,
    attribute_overrides: {
      technique: toInt(form.technique),
      movement: toInt(form.movement),
      physical: toInt(form.physical),
      mental: toInt(form.mental),
      consistency: toInt(form.consistency),
      clutch: toInt(form.clutch),
      recovery: toInt(form.recovery)
    },
    hidden_trait_overrides: {
      potential_ceiling: toInt(form.potential_ceiling),
      growth_curve: form.growth_curve.trim() || null,
      professionalism: toFloat(form.professionalism),
      ambition: toFloat(form.ambition),
      travel_tolerance: toFloat(form.travel_tolerance),
      schedule_aggression: toFloat(form.schedule_aggression),
      injury_proneness: toFloat(form.injury_proneness),
      resilience: toFloat(form.resilience)
    },
    is_exceptional: form.is_exceptional,
    enabled: form.enabled,
    notes: form.notes.trim() || null
  }
}

export function ManualPlayerOverridesPage(): JSX.Element {
  const queryClient = useQueryClient()
  const importFileRef = useRef<HTMLInputElement | null>(null)
  const [mode, setMode] = useState<Mode>('create')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const [importText, setImportText] = useState<string>('')
  const [importResult, setImportResult] = useState<ManualPlayerOverridesImportResponse | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  const overridesQuery = useQuery({ queryKey: ['manual-player-overrides'], queryFn: () => listManualPlayerOverrides(), retry: false })

  const rows = useMemo(
    () => [...(overridesQuery.data?.overrides ?? [])].sort((a, b) => a.override_id.localeCompare(b.override_id)),
    [overridesQuery.data?.overrides]
  )

  const refetch = async () => {
    await queryClient.invalidateQueries({ queryKey: ['manual-player-overrides'] })
  }

  const createMutation = useMutation({
    mutationFn: createManualPlayerOverride,
    onSuccess: async (item) => {
      setSubmitSuccess(`Override ${item.override_id} created.`)
      setSubmitError(null)
      setMode('edit')
      setSelectedId(item.override_id)
      setForm(toForm(item))
      await refetch()
    },
    onError: (error) => setSubmitError(formatApiError(error))
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ManualPlayerOverrideUpsertPayload }) => updateManualPlayerOverride(id, payload),
    onSuccess: async (item) => {
      setSubmitSuccess(`Override ${item.override_id} updated.`)
      setSubmitError(null)
      setMode('edit')
      setSelectedId(item.override_id)
      setForm(toForm(item))
      await refetch()
    },
    onError: (error) => setSubmitError(formatApiError(error))
  })

  const deleteMutation = useMutation({
    mutationFn: deleteManualPlayerOverride,
    onSuccess: async () => {
      setSubmitSuccess('Override deleted.')
      setSubmitError(null)
      setMode('create')
      setSelectedId(null)
      setForm(EMPTY_FORM)
      await refetch()
    },
    onError: (error) => setSubmitError(formatApiError(error))
  })

  const exportMutation = useMutation({
    mutationFn: exportManualPlayerOverridesCsv,
    onSuccess: (csvText) => {
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'manual-player-overrides-export.csv'
      link.click()
      URL.revokeObjectURL(url)
    }
  })

  const importMutation = useMutation({
    mutationFn: importManualPlayerOverrides,
    onSuccess: async (result) => {
      setImportResult(result)
      setImportError(null)
      if (result.ok && !result.dry_run) {
        await refetch()
      }
    },
    onError: (error) => {
      setImportError(formatApiError(error))
      setImportResult(null)
    }
  })

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    setSubmitSuccess(null)
    const payload = toPayload(form)
    if (mode === 'create') {
      createMutation.mutate(payload)
      return
    }
    if (!selectedId) {
      setSubmitError('Select an override before update.')
      return
    }
    updateMutation.mutate({ id: selectedId, payload })
  }

  const runImport = (dryRun: boolean) => {
    setImportError(null)
    setImportResult(null)
    if (!importText.trim()) {
      setImportError('Paste CSV text or upload file first.')
      return
    }
    if (!dryRun && !window.confirm('Import replaces the full canonical manual overrides dataset. Continue?')) {
      return
    }
    importMutation.mutate({ csv_text: importText, dry_run: dryRun })
  }

  const handleImportFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setImportText(text)
    event.target.value = ''
  }

  const startDuplicate = (row: ManualPlayerOverrideRecord) => {
    const duplicated = toForm(row)
    duplicated.override_id = ''
    setMode('create')
    setSelectedId(null)
    setSubmitError(null)
    setSubmitSuccess('Duplicate template loaded. Enter a new unique Override ID before saving.')
    setForm(duplicated)
  }

  return (
    <section className="panel">
      <PageIntro title="Manual Player Overrides" subtitle="Manage world-level manual exceptional players for fresh run generation." />
      <div className="grid">
        <SectionCard title="Bulk import/export">
          <p className="status">Export canonical overrides to CSV or validate/apply a full replacement import.</p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
              {exportMutation.isPending ? 'Exporting…' : 'Export overrides CSV'}
            </button>
            <button type="button" onClick={() => importFileRef.current?.click()}>Import overrides file</button>
          </div>
          <input ref={importFileRef} type="file" accept=".csv,text/csv" hidden onChange={handleImportFile} />
          <textarea
            rows={9}
            value={importText}
            onChange={(event) => setImportText(event.target.value)}
            placeholder="Paste manual overrides CSV here"
          />
          <p className="error">Warning: apply import replaces the entire manual overrides dataset after confirmation.</p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => runImport(true)} disabled={importMutation.isPending}>
              Validate import (dry run)
            </button>
            <button type="button" onClick={() => runImport(false)} disabled={importMutation.isPending}>
              Apply import
            </button>
          </div>
          {importError ? <p className="error">{importError}</p> : null}
          {importResult ? (
            <div>
              <p className={importResult.ok ? 'status' : 'error'}>
                {importResult.ok
                  ? importResult.dry_run
                    ? 'Dry run validation passed.'
                    : 'Import applied to canonical manual overrides dataset.'
                  : 'Import validation failed.'}
              </p>
              <ul>
                <li>Total records: {importResult.summary.total_records}</li>
                <li>New records: {importResult.summary.new_records}</li>
                <li>Updated records: {importResult.summary.updated_records}</li>
                <li>Unchanged records: {importResult.summary.unchanged_records}</li>
              </ul>
              {importResult.errors.length ? (
                <ul>
                  {importResult.errors.map((item, index) => (
                    <li key={`${item.row_number ?? 'global'}-${item.field ?? 'field'}-${index}`}>
                      row {item.row_number ?? 'n/a'} · field {item.field ?? 'n/a'} · {item.message}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </SectionCard>

        <SectionCard title="Overrides list">
          {overridesQuery.isLoading ? <p className="status">Loading overrides…</p> : null}
          {overridesQuery.error ? <p className="error">Failed to load overrides: {formatApiError(overridesQuery.error)}</p> : null}
          {!overridesQuery.isLoading && !rows.length ? <EmptyState message="No manual overrides configured." /> : null}
          {!!rows.length ? (
            <table aria-label="Manual overrides table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Season</th>
                  <th>Country</th>
                  <th>Player</th>
                  <th>Tier</th>
                  <th>Exceptional</th>
                  <th>Enabled</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.override_id}>
                    <td>{row.override_id}</td>
                    <td>{row.season}</td>
                    <td>{row.country_code}</td>
                    <td>{row.player_name}</td>
                    <td>{row.profile_tier}</td>
                    <td>{row.is_exceptional ? 'Yes' : 'No'}</td>
                    <td>{row.enabled ? 'Yes' : 'No'}</td>
                    <td>
                      <button type="button" onClick={() => { setMode('edit'); setSelectedId(row.override_id); setForm(toForm(row)) }}>Edit</button>{' '}
                      <button type="button" onClick={() => startDuplicate(row)}>Duplicate override</button>{' '}
                      <button
                        type="button"
                        onClick={() =>
                          updateMutation.mutate({ id: row.override_id, payload: { ...row, enabled: !row.enabled } })
                        }
                      >
                        {row.enabled ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </SectionCard>

        <SectionCard title={mode === 'create' ? 'Create override' : `Edit override ${selectedId ?? ''}`}>
          <form onSubmit={onSubmit}>
            <div className="grid">
              <label>Override ID<input required value={form.override_id} onChange={(e) => setForm((x) => ({ ...x, override_id: e.target.value }))} /></label>
              <label>Season<input type="number" min={1900} required value={form.season} onChange={(e) => setForm((x) => ({ ...x, season: Number(e.target.value) }))} /></label>
              <label>Country code<input required maxLength={3} value={form.country_code} onChange={(e) => setForm((x) => ({ ...x, country_code: e.target.value.toUpperCase() }))} /></label>
              <label>Player name<input required value={form.player_name} onChange={(e) => setForm((x) => ({ ...x, player_name: e.target.value }))} /></label>
              <label>Player slug<input value={form.player_slug} onChange={(e) => setForm((x) => ({ ...x, player_slug: e.target.value }))} /></label>
              <label>Player ID<input value={form.player_id} onChange={(e) => setForm((x) => ({ ...x, player_id: e.target.value }))} /></label>
              <label>Age<input type="number" min={15} max={45} required value={form.age} onChange={(e) => setForm((x) => ({ ...x, age: Number(e.target.value) }))} /></label>
              <label>Profile tier
                <select value={form.profile_tier} onChange={(e) => setForm((x) => ({ ...x, profile_tier: e.target.value as FormState['profile_tier'] }))}>
                  <option value="strong">strong</option><option value="elite">elite</option><option value="special">special</option><option value="generational">generational</option>
                </select>
              </label>
              <label>Quality band override (optional)
                <select value={form.quality_band_override} onChange={(e) => setForm((x) => ({ ...x, quality_band_override: e.target.value }))}>
                  <option value="">(from tier)</option>
                  <option value="strong_prospect">strong_prospect</option>
                  <option value="elite_prospect">elite_prospect</option>
                  <option value="special_prospect">special_prospect</option>
                  <option value="generational_talent">generational_talent</option>
                </select>
              </label>
              <label>Technique override<input value={form.technique} onChange={(e) => setForm((x) => ({ ...x, technique: e.target.value }))} /></label>
              <label>Movement override<input value={form.movement} onChange={(e) => setForm((x) => ({ ...x, movement: e.target.value }))} /></label>
              <label>Physical override<input value={form.physical} onChange={(e) => setForm((x) => ({ ...x, physical: e.target.value }))} /></label>
              <label>Mental override<input value={form.mental} onChange={(e) => setForm((x) => ({ ...x, mental: e.target.value }))} /></label>
              <label>Consistency override<input value={form.consistency} onChange={(e) => setForm((x) => ({ ...x, consistency: e.target.value }))} /></label>
              <label>Clutch override<input value={form.clutch} onChange={(e) => setForm((x) => ({ ...x, clutch: e.target.value }))} /></label>
              <label>Recovery override<input value={form.recovery} onChange={(e) => setForm((x) => ({ ...x, recovery: e.target.value }))} /></label>
              <label>Potential ceiling override<input value={form.potential_ceiling} onChange={(e) => setForm((x) => ({ ...x, potential_ceiling: e.target.value }))} /></label>
              <label>Growth curve override<input value={form.growth_curve} onChange={(e) => setForm((x) => ({ ...x, growth_curve: e.target.value }))} /></label>
              <label>Professionalism override<input value={form.professionalism} onChange={(e) => setForm((x) => ({ ...x, professionalism: e.target.value }))} /></label>
              <label>Ambition override<input value={form.ambition} onChange={(e) => setForm((x) => ({ ...x, ambition: e.target.value }))} /></label>
              <label>Travel tolerance override<input value={form.travel_tolerance} onChange={(e) => setForm((x) => ({ ...x, travel_tolerance: e.target.value }))} /></label>
              <label>Schedule aggression override<input value={form.schedule_aggression} onChange={(e) => setForm((x) => ({ ...x, schedule_aggression: e.target.value }))} /></label>
              <label>Injury proneness override<input value={form.injury_proneness} onChange={(e) => setForm((x) => ({ ...x, injury_proneness: e.target.value }))} /></label>
              <label>Resilience override<input value={form.resilience} onChange={(e) => setForm((x) => ({ ...x, resilience: e.target.value }))} /></label>
              <label><input type="checkbox" checked={form.is_exceptional} onChange={(e) => setForm((x) => ({ ...x, is_exceptional: e.target.checked }))} /> Exceptional</label>
              <label><input type="checkbox" checked={form.enabled} onChange={(e) => setForm((x) => ({ ...x, enabled: e.target.checked }))} /> Enabled</label>
              <label>Notes<textarea value={form.notes} onChange={(e) => setForm((x) => ({ ...x, notes: e.target.value }))} /></label>
            </div>
            <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
              <button type="submit">{mode === 'create' ? 'Create override' : 'Save changes'}</button>
              <button type="button" onClick={() => { setMode('create'); setSelectedId(null); setForm(EMPTY_FORM) }}>New</button>
              {mode === 'edit' && selectedId ? (
                <button type="button" onClick={() => deleteMutation.mutate(selectedId)}>Delete override</button>
              ) : null}
            </div>
          </form>
          {submitError ? <p className="error">{submitError}</p> : null}
          {submitSuccess ? <p className="status">{submitSuccess}</p> : null}
        </SectionCard>
      </div>
    </section>
  )
}
