import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useMemo, useState } from 'react'

import {
  createManualPlayerOverride,
  deleteManualPlayerOverride,
  listManualPlayerOverrides,
  updateManualPlayerOverride
} from '../api/client'
import type { ManualPlayerOverrideRecord, ManualPlayerOverrideUpsertPayload } from '../api/types'
import { EmptyState, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type Mode = 'create' | 'edit'

type FormState = {
  override_id: string
  season: number
  country_code: string
  player_name: string
  age: number
  profile_tier: 'strong' | 'elite' | 'special' | 'generational'
  quality_band_override: string
  technique: string
  movement: string
  physical: string
  mental: string
  is_exceptional: boolean
  enabled: boolean
  notes: string
}

const EMPTY_FORM: FormState = {
  override_id: '',
  season: 2027,
  country_code: '',
  player_name: '',
  age: 18,
  profile_tier: 'elite',
  quality_band_override: '',
  technique: '',
  movement: '',
  physical: '',
  mental: '',
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
    age: item.age,
    profile_tier: item.profile_tier,
    quality_band_override: item.quality_band_override ?? '',
    technique: item.attribute_overrides?.technique ? String(item.attribute_overrides.technique) : '',
    movement: item.attribute_overrides?.movement ? String(item.attribute_overrides.movement) : '',
    physical: item.attribute_overrides?.physical ? String(item.attribute_overrides.physical) : '',
    mental: item.attribute_overrides?.mental ? String(item.attribute_overrides.mental) : '',
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
  return {
    override_id: form.override_id.trim(),
    season: form.season,
    country_code: form.country_code.trim().toUpperCase(),
    player_name: form.player_name.trim(),
    age: form.age,
    profile_tier: form.profile_tier,
    quality_band_override: form.quality_band_override || null,
    attribute_overrides: {
      technique: toInt(form.technique),
      movement: toInt(form.movement),
      physical: toInt(form.physical),
      mental: toInt(form.mental)
    },
    is_exceptional: form.is_exceptional,
    enabled: form.enabled,
    notes: form.notes.trim() || null
  }
}

export function ManualPlayerOverridesPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>('create')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)

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

  return (
    <section className="panel">
      <PageIntro title="Manual Player Overrides" subtitle="Manage world-level manual exceptional players for fresh run generation." />
      <div className="grid">
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
