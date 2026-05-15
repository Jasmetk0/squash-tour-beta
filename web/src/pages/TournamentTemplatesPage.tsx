import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChangeEvent, FormEvent, useMemo, useState } from 'react'

import {
  ApiError,
  createTournamentTemplate,
  deleteTournamentTemplate,
  exportTournamentTemplates,
  getTournamentTemplatesMetadata,
  importTournamentTemplates,
  listTournamentTemplates,
  updateTournamentTemplate
} from '../api/client'
import type {
  LuckyLoserRules,
  TournamentPointDistribution,
  TournamentTemplateRecord,
  TournamentTemplateUpsertPayload,
  TournamentTemplatesDatasetResponse,
  TournamentTemplatesImportResponse
} from '../api/types'
import { EmptyState, PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

type Mode = 'create' | 'edit'

type FormState = Omit<TournamentTemplateUpsertPayload, 'lucky_loser_rules' | 'point_distribution'> & {
  lucky_loser_rules: LuckyLoserRules
  point_distribution: TournamentPointDistribution | null
}

const EMPTY_FORM: FormState = {
  template_id: '',
  tour_level: 'WORLD_TOUR',
  category: '',
  event_name: '',
  region: '',
  host_country: '',
  main_draw_size: 32,
  qualification_draw_size: 16,
  seeds_count: 8,
  qualifier_spots: 4,
  wild_cards: 2,
  byes: 0,
  lucky_loser_rules: { enabled: true, max_spots: 2, replacement_window: 'pre_main_draw_round_1' },
  point_distribution_ref: '',
  point_distribution: null,
  event_duration_days: 6,
  qualification_duration_days: 2,
  preferred_week_type: '',
  seasonal_grouping: '',
  prize_money: 0,
  prestige: 0,
  duration_in_season_weeks: 1,
  host_requirements: {},
  category_specific_rules: {},
  notes: '',
  active: true
}

function formatApiError(error: unknown): string {
  if (error instanceof ApiError) return `${error.status}: ${error.message}`
  if (error instanceof Error) return error.message
  return 'Unknown error'
}

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? null, null, 2)
}

function templateToForm(template: TournamentTemplateRecord): FormState {
  return {
    ...template,
    point_distribution_ref: template.point_distribution_ref ?? '',
    point_distribution: template.point_distribution ?? null,
    preferred_week_type: template.preferred_week_type ?? '',
    seasonal_grouping: template.seasonal_grouping ?? '',
    prize_money: template.prize_money ?? 0,
    prestige: template.prestige ?? 0,
    duration_in_season_weeks: template.duration_in_season_weeks ?? 1,
    host_requirements: template.host_requirements ?? {},
    category_specific_rules: template.category_specific_rules ?? {},
    notes: template.notes ?? '',
    active: template.active ?? true
  }
}

function normalizeTemplateId(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, '_')
}

export function TournamentTemplatesPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>('create')
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [luckyLoserText, setLuckyLoserText] = useState(formatJson(EMPTY_FORM.lucky_loser_rules))
  const [pointsText, setPointsText] = useState('null')
  const [hostRequirementsText, setHostRequirementsText] = useState('{}')
  const [categoryRulesText, setCategoryRulesText] = useState('{}')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [importText, setImportText] = useState('')
  const [importDryRun, setImportDryRun] = useState(true)
  const [importResult, setImportResult] = useState<TournamentTemplatesImportResponse | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  const templatesQuery = useQuery({ queryKey: ['tournament-templates-list'], queryFn: listTournamentTemplates, retry: false })
  const metadataQuery = useQuery({ queryKey: ['tournament-templates-metadata'], queryFn: getTournamentTemplatesMetadata, retry: false })

  const sortedTemplates = useMemo(
    () => [...(templatesQuery.data?.templates ?? [])].sort((left, right) => left.template_id.localeCompare(right.template_id)),
    [templatesQuery.data?.templates]
  )

  const refetchAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['tournament-templates-list'] }),
      queryClient.invalidateQueries({ queryKey: ['tournament-templates-metadata'] })
    ])
  }

  const createMutation = useMutation({
    mutationFn: createTournamentTemplate,
    onSuccess: async (created) => {
      setSubmitSuccess(`Tournament template ${created.template_id} created.`)
      setSubmitError(null)
      setSelectedTemplateId(created.template_id)
      setMode('edit')
      setForm(templateToForm(created))
      setLuckyLoserText(formatJson(created.lucky_loser_rules))
      setPointsText(formatJson(created.point_distribution))
      setHostRequirementsText(formatJson(created.host_requirements ?? {}))
      setCategoryRulesText(formatJson(created.category_specific_rules ?? {}))
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setSubmitError(`Create failed: ${formatApiError(error)}`)
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ templateId, payload }: { templateId: string; payload: TournamentTemplateUpsertPayload }) => updateTournamentTemplate(templateId, payload),
    onSuccess: async (updated) => {
      setSubmitSuccess(`Tournament template ${updated.template_id} updated.`)
      setSubmitError(null)
      setSelectedTemplateId(updated.template_id)
      setForm(templateToForm(updated))
      setLuckyLoserText(formatJson(updated.lucky_loser_rules))
      setPointsText(formatJson(updated.point_distribution))
      setHostRequirementsText(formatJson(updated.host_requirements ?? {}))
      setCategoryRulesText(formatJson(updated.category_specific_rules ?? {}))
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setSubmitError(`Update failed: ${formatApiError(error)}`)
    }
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTournamentTemplate,
    onSuccess: async (_, templateId) => {
      setDeleteError(null)
      setSubmitSuccess(`Tournament template ${templateId} deleted.`)
      resetCreate()
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setDeleteError(`Delete failed: ${formatApiError(error)}`)
    }
  })

  const exportMutation = useMutation({
    mutationFn: exportTournamentTemplates,
    onSuccess: (dataset) => {
      const text = JSON.stringify(dataset, null, 2)
      setImportText(text)
      const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = 'tournament-templates-export.json'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(href)
      setSubmitSuccess('Tournament templates JSON export downloaded and copied into the import editor.')
      setImportError(null)
    },
    onError: (error) => setImportError(`Export failed: ${formatApiError(error)}`)
  })

  const importMutation = useMutation({
    mutationFn: importTournamentTemplates,
    onSuccess: async (result) => {
      setImportResult(result)
      setImportError(null)
      if (result.ok && !result.dry_run) {
        setSubmitSuccess(`Tournament templates import complete. Replaced dataset with ${result.template_count} templates.`)
        await refetchAll()
      }
    },
    onError: (error) => {
      setImportResult(null)
      setImportError(`Import failed: ${formatApiError(error)}`)
    }
  })

  function resetCreate() {
    setMode('create')
    setSelectedTemplateId(null)
    setForm(EMPTY_FORM)
    setLuckyLoserText(formatJson(EMPTY_FORM.lucky_loser_rules))
    setPointsText('null')
    setHostRequirementsText('{}')
    setCategoryRulesText('{}')
    setSubmitError(null)
    setDeleteError(null)
  }

  const onSelect = (template: TournamentTemplateRecord) => {
    setMode('edit')
    setSelectedTemplateId(template.template_id)
    setForm(templateToForm(template))
    setLuckyLoserText(formatJson(template.lucky_loser_rules))
    setPointsText(formatJson(template.point_distribution))
    setHostRequirementsText(formatJson(template.host_requirements ?? {}))
    setCategoryRulesText(formatJson(template.category_specific_rules ?? {}))
    setSubmitError(null)
    setSubmitSuccess(null)
    setDeleteError(null)
  }

  const onDuplicate = (template: TournamentTemplateRecord) => {
    setMode('create')
    setSelectedTemplateId(null)
    setForm({
      ...templateToForm(template),
      template_id: '',
      event_name: `${template.event_name} Copy`
    })
    setLuckyLoserText(formatJson(template.lucky_loser_rules))
    setPointsText(formatJson(template.point_distribution))
    setHostRequirementsText(formatJson(template.host_requirements ?? {}))
    setCategoryRulesText(formatJson(template.category_specific_rules ?? {}))
    setSubmitError(null)
    setSubmitSuccess('Template duplicated into create form. Set a unique template_id before saving.')
  }

  const buildPayload = (): TournamentTemplateUpsertPayload | null => {
    let luckyLoserRules: LuckyLoserRules
    let pointDistribution: TournamentPointDistribution | null
    let hostRequirements: Record<string, unknown>
    let categoryRules: Record<string, unknown>
    try {
      const parsed = JSON.parse(luckyLoserText || '{}') as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('Lucky loser rules must be a JSON object.')
      luckyLoserRules = parsed as LuckyLoserRules
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Lucky loser rules must be valid JSON.')
      return null
    }
    try {
      const parsed = JSON.parse(pointsText || 'null') as unknown
      if (parsed !== null && (Array.isArray(parsed) || typeof parsed !== 'object')) throw new Error('Inline points must be null or a JSON object.')
      pointDistribution = parsed as TournamentPointDistribution | null
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Inline points must be valid JSON.')
      return null
    }

    try {
      const parsed = JSON.parse(hostRequirementsText || '{}') as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('Host requirements must be a JSON object.')
      hostRequirements = parsed as Record<string, unknown>
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Host requirements must be valid JSON.')
      return null
    }
    try {
      const parsed = JSON.parse(categoryRulesText || '{}') as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('Category-specific rules must be a JSON object.')
      categoryRules = parsed as Record<string, unknown>
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Category-specific rules must be valid JSON.')
      return null
    }

    const pointDistributionRef = form.point_distribution_ref?.trim() || null
    if (!pointDistributionRef && pointDistribution === null) {
      setSubmitError('Provide either a point distribution reference or inline points JSON.')
      return null
    }

    return {
      ...form,
      template_id: normalizeTemplateId(form.template_id),
      category: form.category.trim(),
      event_name: form.event_name.trim(),
      region: form.region.trim(),
      host_country: form.host_country.trim().toUpperCase(),
      main_draw_size: Number(form.main_draw_size),
      qualification_draw_size: Number(form.qualification_draw_size),
      seeds_count: Number(form.seeds_count),
      qualifier_spots: Number(form.qualifier_spots),
      wild_cards: Number(form.wild_cards),
      byes: Number(form.byes),
      lucky_loser_rules: luckyLoserRules,
      point_distribution_ref: pointDistributionRef,
      point_distribution: pointDistribution,
      event_duration_days: Number(form.event_duration_days),
      qualification_duration_days: Number(form.qualification_duration_days),
      preferred_week_type: form.preferred_week_type?.trim() || null,
      seasonal_grouping: form.seasonal_grouping?.trim() || null,
      prize_money: Number(form.prize_money),
      prestige: Number(form.prestige),
      duration_in_season_weeks: Number(form.duration_in_season_weeks),
      host_requirements: hostRequirements,
      category_specific_rules: categoryRules,
      notes: form.notes?.trim() || null,
      active: Boolean(form.active)
    }
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    setSubmitSuccess(null)
    const payload = buildPayload()
    if (!payload) return

    if (mode === 'create') {
      createMutation.mutate(payload)
      return
    }
    if (!selectedTemplateId) {
      setSubmitError('Select a tournament template before update.')
      return
    }
    updateMutation.mutate({ templateId: selectedTemplateId, payload })
  }

  const onDelete = () => {
    if (!selectedTemplateId) return
    if (!window.confirm(`Delete tournament template ${selectedTemplateId}? Calendar-referenced templates will be rejected by the API.`)) return
    deleteMutation.mutate(selectedTemplateId)
  }

  const onImportFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setImportText(await file.text())
    event.target.value = ''
  }

  const onImport = () => {
    setImportError(null)
    setImportResult(null)
    let dataset: TournamentTemplatesDatasetResponse
    try {
      dataset = JSON.parse(importText) as TournamentTemplatesDatasetResponse
      if (!dataset || !Array.isArray(dataset.templates)) throw new Error('JSON must be an object with a templates array.')
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Import JSON is invalid.')
      return
    }
    importMutation.mutate({ dataset, dry_run: importDryRun })
  }

  const setNumber = (field: keyof FormState, value: string) => setForm((current) => ({ ...current, [field]: Number(value) }))
  const setText = (field: keyof FormState, value: string) => setForm((current) => ({ ...current, [field]: value }))

  return (
    <section className="stack">
      <PageIntro
        title="Tournament Templates"
        subtitle="Templates define reusable categories. Seasons later assign these templates to specific weeks/events. Create every category manually; no fixed category set is required."
      />

      <SectionCard title="Dataset status">
        <p className="status">File-backed tournament template config used by future generated seasons/runs.</p>
        {metadataQuery.data ? (
          <SummaryPills
            items={[
              { label: 'Templates', value: metadataQuery.data.template_count },
              { label: 'Source', value: metadataQuery.data.source_path },
              { label: 'Calendar references', value: metadataQuery.data.referenced_template_ids.length }
            ]}
          />
        ) : metadataQuery.isLoading ? (
          <p className="status">Loading metadata…</p>
        ) : (
          <p className="error">Could not load tournament template metadata.</p>
        )}
        <p className="status">Examples you may create later: World Championship, Diamond, Emerald, Platinum, Gold, Silver, Bronze, Elite, Challenger, Future.</p>
        <p className="status">Warning: Changing templates can affect future generated seasons/runs. Existing completed history is not automatically regenerated.</p>
      </SectionCard>

      <div className="grid two-column-grid">
        <SectionCard title="Existing templates">
          <p className="status">Select, duplicate, or delete reusable tournament category definitions.</p>
          {templatesQuery.isLoading ? <p className="status">Loading templates…</p> : null}
          {templatesQuery.isError ? <p className="error">Could not load tournament templates.</p> : null}
          {!templatesQuery.isLoading && sortedTemplates.length === 0 ? <EmptyState message="No tournament templates. Create the first user-defined template with the form." /> : null}
          {sortedTemplates.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Template ID</th>
                  <th>Tour</th>
                  <th>Category</th>
                  <th>Main</th>
                  <th>Qual</th>
                  <th>Prize</th>
                  <th>Prestige</th>
                  <th>Weeks</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedTemplates.map((template) => (
                  <tr key={template.template_id}>
                    <td>{template.template_id}</td>
                    <td>{template.tour_level}</td>
                    <td>{template.category}</td>
                    <td>{template.main_draw_size}</td>
                    <td>{template.qualification_draw_size}</td>
                    <td>{(template.prize_money ?? 0).toLocaleString()}</td>
                    <td>{template.prestige ?? 0}</td>
                    <td>{template.duration_in_season_weeks ?? 1}</td>
                    <td>{template.active ?? true ? 'Yes' : 'No'}</td>
                    <td className="actions-cell">
                      <button type="button" onClick={() => onSelect(template)}>Edit</button>
                      <button type="button" onClick={() => onDuplicate(template)}>Duplicate</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </SectionCard>

        <SectionCard title={mode === 'create' ? 'Create template' : `Edit ${selectedTemplateId ?? ''}`}>
          <p className="status">Core fields are first-class inputs; nested rules and inline points stay as JSON so data is not lost.</p>
          <form className="form-grid" onSubmit={onSubmit}>
            <label>
              Template ID
              <input value={form.template_id} onChange={(event) => setText('template_id', event.target.value)} placeholder="user_diamond_32" />
            </label>
            <label>
              Tour level
              <select value={form.tour_level} onChange={(event) => setForm((current) => ({ ...current, tour_level: event.target.value as FormState['tour_level'] }))}>
                <option value="WORLD_TOUR">WORLD_TOUR</option>
                <option value="ELITE_TOUR">ELITE_TOUR</option>
              </select>
            </label>
            <label>
              Category
              <input value={form.category} onChange={(event) => setText('category', event.target.value)} placeholder="USER_DIAMOND" />
            </label>
            <label>
              Event/category name
              <input value={form.event_name} onChange={(event) => setText('event_name', event.target.value)} placeholder="User Diamond" />
            </label>
            <label>
              Region/default host region
              <input value={form.region} onChange={(event) => setText('region', event.target.value)} placeholder="EUROPE" />
            </label>
            <label>
              Host country default (3 letters)
              <input value={form.host_country} onChange={(event) => setText('host_country', event.target.value.toUpperCase().slice(0, 3))} placeholder="ENG" />
            </label>
            <label>
              Main draw size
              <input type="number" min="1" value={form.main_draw_size} onChange={(event) => setNumber('main_draw_size', event.target.value)} />
            </label>
            <label>
              Qualification draw size
              <input type="number" min="0" value={form.qualification_draw_size} onChange={(event) => setNumber('qualification_draw_size', event.target.value)} />
            </label>
            <label>
              Seeds count
              <input type="number" min="0" value={form.seeds_count} onChange={(event) => setNumber('seeds_count', event.target.value)} />
            </label>
            <label>
              Qualifier spots
              <input type="number" min="0" value={form.qualifier_spots} onChange={(event) => setNumber('qualifier_spots', event.target.value)} />
            </label>
            <label>
              Wildcard slots
              <input type="number" min="0" value={form.wild_cards} onChange={(event) => setNumber('wild_cards', event.target.value)} />
            </label>
            <label>
              Byes
              <input type="number" min="0" value={form.byes} onChange={(event) => setNumber('byes', event.target.value)} />
            </label>
            <label>
              Point distribution ref
              <input value={form.point_distribution_ref ?? ''} onChange={(event) => setText('point_distribution_ref', event.target.value)} placeholder="world_tour_gold" />
            </label>
            <label>
              Event duration days
              <input type="number" min="1" value={form.event_duration_days} onChange={(event) => setNumber('event_duration_days', event.target.value)} />
            </label>
            <label>
              Qualification duration days
              <input type="number" min="0" value={form.qualification_duration_days} onChange={(event) => setNumber('qualification_duration_days', event.target.value)} />
            </label>
            <label>
              Preferred week type (optional)
              <input value={form.preferred_week_type ?? ''} onChange={(event) => setText('preferred_week_type', event.target.value)} />
            </label>
            <label>
              Seasonal grouping (optional)
              <input value={form.seasonal_grouping ?? ''} onChange={(event) => setText('seasonal_grouping', event.target.value)} />
            </label>
            <label>
              Prize money
              <input type="number" min="0" value={form.prize_money} onChange={(event) => setNumber('prize_money', event.target.value)} />
            </label>
            <label>
              Prestige
              <input type="number" min="0" step="0.1" value={form.prestige} onChange={(event) => setNumber('prestige', event.target.value)} />
            </label>
            <label>
              Duration in season weeks
              <input type="number" min="1" value={form.duration_in_season_weeks} onChange={(event) => setNumber('duration_in_season_weeks', event.target.value)} />
            </label>
            <label className="inline-checkbox">
              <input type="checkbox" checked={form.active} onChange={(event) => setForm((current) => ({ ...current, active: event.target.checked }))} /> Active/enabled
            </label>
            <label className="full-width">
              Notes
              <textarea rows={3} value={form.notes ?? ''} onChange={(event) => setText('notes', event.target.value)} />
            </label>
            <label className="full-width">
              Host requirements (JSON)
              <textarea rows={5} value={hostRequirementsText} onChange={(event) => setHostRequirementsText(event.target.value)} />
            </label>
            <label className="full-width">
              Category-specific rules (JSON)
              <textarea rows={5} value={categoryRulesText} onChange={(event) => setCategoryRulesText(event.target.value)} />
            </label>
            <label className="full-width">
              Lucky loser rules (JSON)
              <textarea rows={5} value={luckyLoserText} onChange={(event) => setLuckyLoserText(event.target.value)} />
            </label>
            <label className="full-width">
              Inline point distribution (JSON or null)
              <textarea rows={7} value={pointsText} onChange={(event) => setPointsText(event.target.value)} />
            </label>
            <div className="button-row full-width">
              <button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>{mode === 'create' ? 'Create template' : 'Update template'}</button>
              <button type="button" onClick={resetCreate}>New blank template</button>
              {mode === 'edit' ? <button type="button" className="danger" onClick={onDelete}>Delete template</button> : null}
            </div>
          </form>
          {submitSuccess ? <p className="success">{submitSuccess}</p> : null}
          {submitError ? <p className="error">{submitError}</p> : null}
          {deleteError ? <p className="error">{deleteError}</p> : null}
        </SectionCard>
      </div>

      <SectionCard title="Import / export JSON">
        <p className="status">Export the full dataset or validate/replace it from JSON without flattening nested rules.</p>
        <div className="button-row">
          <button type="button" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>Export templates JSON</button>
          <label className="inline-checkbox">
            <input type="checkbox" checked={importDryRun} onChange={(event) => setImportDryRun(event.target.checked)} /> Dry run import
          </label>
          <input aria-label="Import tournament templates JSON file" type="file" accept="application/json,.json" onChange={onImportFileSelected} />
          <button type="button" onClick={onImport} disabled={importMutation.isPending}>{importDryRun ? 'Validate import JSON' : 'Import and replace JSON'}</button>
        </div>
        <label>
          Tournament templates JSON
          <textarea rows={12} value={importText} onChange={(event) => setImportText(event.target.value)} placeholder={'{\n  "templates": []\n}'} />
        </label>
        {importResult ? (
          <div className={importResult.ok ? 'success' : 'error'}>
            Import {importResult.ok ? 'valid' : 'invalid'} ({importResult.template_count} templates, dry_run={String(importResult.dry_run)})
            {importResult.errors.length > 0 ? (
              <ul>
                {importResult.errors.map((item, index) => <li key={`${item.field ?? 'dataset'}-${index}`}>{item.field ?? 'dataset'}: {item.message}</li>)}
              </ul>
            ) : null}
          </div>
        ) : null}
        {importError ? <p className="error">{importError}</p> : null}
      </SectionCard>
    </section>
  )
}
