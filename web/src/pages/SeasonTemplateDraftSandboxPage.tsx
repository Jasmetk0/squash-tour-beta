import { FormEvent, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageIntro, SectionCard } from '../components/RunScopedUi'
import {
  describeCalendarEventTiming,
  type CalendarEventDraft,
  validateSeasonWeeks
} from '../tour/calendarEventModel'
import { tournamentCategoryCatalog } from '../tour/tournamentCategoryCatalog'

type DraftFormState = {
  name: string
  categoryCode: string
  weeksInput: string
  qualificationWeeksInput: string
  locked: boolean
  city: string
  notes: string
}

type ParsedWeeksResult = {
  weeks: number[]
  errors: string[]
}

const initialDraftEvents: CalendarEventDraft[] = [
  {
    id: 'sandbox-nemarque-open',
    name: 'Némarque Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [5],
    weeks: [6, 7],
    locked: true,
    status: 'template'
  },
  {
    id: 'sandbox-ameriga-open',
    name: 'Ameriga Open',
    categoryCode: 'DIAMOND',
    qualificationWeeks: [43],
    weeks: [44, 45],
    locked: true,
    status: 'template'
  },
  {
    id: 'sandbox-world-championship',
    name: 'World Championship',
    categoryCode: 'WORLD_CHAMPIONSHIP',
    qualificationWeeks: [48],
    weeks: [49, 50],
    locked: true,
    status: 'template'
  },
  {
    id: 'sandbox-world-tour-finals',
    name: 'World Tour Finals',
    categoryCode: 'WORLD_TOUR_FINALS',
    qualificationWeeks: [],
    weeks: [55],
    locked: true,
    status: 'template'
  }
]

const emptyForm: DraftFormState = {
  name: '',
  categoryCode: 'DIAMOND',
  weeksInput: '',
  qualificationWeeksInput: '',
  locked: false,
  city: '',
  notes: ''
}

export function SeasonTemplateDraftSandboxPage(): JSX.Element {
  const [templateName] = useState('Default World Tour Skeleton Sandbox')
  const [events, setEvents] = useState<CalendarEventDraft[]>(initialDraftEvents)
  const [form, setForm] = useState<DraftFormState>(emptyForm)
  const [errors, setErrors] = useState<string[]>([])
  const [warning, setWarning] = useState<string | null>(null)

  const categoryOptions = useMemo(() => tournamentCategoryCatalog.map((category) => ({
    code: category.code,
    label: `${category.name} (${category.code})`
  })), [])

  function updateForm<K extends keyof DraftFormState>(key: K, value: DraftFormState[K]): void {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const validation = validateDraftForm(form)
    setErrors(validation.errors)
    setWarning(validation.warning)

    if (validation.errors.length > 0) {
      return
    }

    setEvents((current) => [
      ...current,
      {
        id: `sandbox-local-${current.length + 1}-${form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        name: form.name.trim(),
        categoryCode: form.categoryCode,
        weeks: validation.weeks,
        qualificationWeeks: validation.qualificationWeeks,
        locked: form.locked,
        city: form.city.trim() || undefined,
        notes: form.notes.trim() || undefined,
        status: 'draft'
      }
    ])
    setForm(emptyForm)
  }

  function setEventLocked(eventId: string, locked: boolean): void {
    setEvents((current) => current.map((event) => event.id === eventId ? { ...event, locked } : event))
  }

  function deleteEvent(eventId: string): void {
    setEvents((current) => current.filter((event) => event.id !== eventId || event.locked))
  }

  return (
    <section className="panel">
      <PageIntro title="Draft Template Sandbox" subtitle="Admin-only local prototype for experimenting with calendar template events." />
      <SectionCard title="Local sandbox only">
        <p><strong>Local sandbox only — not persisted, not played, not visible in Viewer.</strong></p>
        <ul className="dashboard-help-list">
          <li>Template changes stay in local React state for this page session only.</li>
          <li>No backend save, copy, apply, run creation, season-calendar creation, or Viewer behavior is enabled here.</li>
          <li>Copy to canonical season — planned.</li>
          <li>Two-pane compare/copy workspace — planned.</li>
        </ul>
      </SectionCard>

      <SectionCard title={templateName}>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Timing</th>
              <th>Lock</th>
              <th>Notes</th>
              <th>Local actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{event.name}</td>
                <td>{event.categoryCode}</td>
                <td>{describeCalendarEventTiming(event)}</td>
                <td>{event.locked ? 'Locked' : 'Unlocked'}</td>
                <td>{event.notes ?? event.status ?? '—'}</td>
                <td>
                  {event.locked ? (
                    <button type="button" onClick={() => setEventLocked(event.id, false)}>Unlock</button>
                  ) : (
                    <>
                      <button type="button" onClick={() => setEventLocked(event.id, true)}>Lock</button>{' '}
                      <button type="button" onClick={() => deleteEvent(event.id)}>Delete</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>

      <SectionCard title="Add local draft event">
        <form onSubmit={handleSubmit}>
          <p>
            <label htmlFor="draft-event-name">Name</label><br />
            <input id="draft-event-name" value={form.name} onChange={(event) => updateForm('name', event.target.value)} />
          </p>
          <p>
            <label htmlFor="draft-event-category">Category</label><br />
            <select id="draft-event-category" value={form.categoryCode} onChange={(event) => updateForm('categoryCode', event.target.value)}>
              {categoryOptions.map((category) => <option key={category.code} value={category.code}>{category.label}</option>)}
            </select>
          </p>
          <p>
            <label htmlFor="draft-event-weeks">weeks</label><br />
            <input id="draft-event-weeks" placeholder="6,7" value={form.weeksInput} onChange={(event) => updateForm('weeksInput', event.target.value)} />
          </p>
          <p>
            <label htmlFor="draft-event-qualification-weeks">qualificationWeeks</label><br />
            <input id="draft-event-qualification-weeks" placeholder="5" value={form.qualificationWeeksInput} onChange={(event) => updateForm('qualificationWeeksInput', event.target.value)} />
          </p>
          <p>
            <label htmlFor="draft-event-city">City (optional)</label><br />
            <input id="draft-event-city" value={form.city} onChange={(event) => updateForm('city', event.target.value)} />
          </p>
          <p>
            <label htmlFor="draft-event-notes">Notes (optional)</label><br />
            <input id="draft-event-notes" value={form.notes} onChange={(event) => updateForm('notes', event.target.value)} />
          </p>
          <p>
            <label><input type="checkbox" checked={form.locked} onChange={(event) => updateForm('locked', event.target.checked)} /> Locked</label>
          </p>
          {warning ? <p className="status">{warning}</p> : null}
          {errors.length > 0 ? <ul className="error">{errors.map((error) => <li key={error}>{error}</li>)}</ul> : null}
          <button type="submit">Add Local Draft Event</button>
        </form>
      </SectionCard>

      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Back to Season Templates</Link></p>
        <p><Link to="/admin/tour-seasons">Back to Tour &amp; Seasons</Link></p>
      </SectionCard>
    </section>
  )
}

function validateDraftForm(form: DraftFormState): { errors: string[], warning: string | null, weeks: number[], qualificationWeeks: number[] } {
  const errors: string[] = []
  const name = form.name.trim()
  if (!name) errors.push('Name is required.')
  if (!tournamentCategoryCatalog.some((category) => category.code === form.categoryCode)) errors.push('Category code is not recognized.')

  const weeksResult = parseWeeksInput(form.weeksInput, 'weeks')
  const qualificationWeeksResult = parseWeeksInput(form.qualificationWeeksInput, 'qualificationWeeks')

  errors.push(...weeksResult.errors, ...qualificationWeeksResult.errors)

  return {
    errors,
    warning: weeksResult.weeks.length === 0 ? 'Main weeks are empty; this event is not scheduled yet.' : null,
    weeks: weeksResult.weeks,
    qualificationWeeks: qualificationWeeksResult.weeks
  }
}

function parseWeeksInput(input: string, label: string): ParsedWeeksResult {
  const trimmed = input.trim()
  if (!trimmed) return { weeks: [], errors: [] }

  const tokens = trimmed.split(',').map((token) => token.trim()).filter(Boolean)
  const parseErrors: string[] = []
  const weeks = tokens.map((token, index) => {
    if (!/^\d+$/.test(token)) {
      parseErrors.push(`${label} value at position ${index + 1} must be an integer.`)
      return Number.NaN
    }
    return Number(token)
  })

  const validatableWeeks = weeks.filter((week) => !Number.isNaN(week))
  const validationErrors = validateSeasonWeeks(validatableWeeks).map((error) => `${label}: ${error}`)
  return { weeks: validatableWeeks, errors: [...parseErrors, ...validationErrors] }
}
