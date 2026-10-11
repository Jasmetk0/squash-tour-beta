import { useMemo, useState } from 'react'

import type { CalendarTemplateEventRecord, CalendarTemplateUpsertPayload } from '../api/types'
import { tournamentCategoryCatalog } from '../tour/tournamentCategoryCatalog'

type EventFormRow = Omit<CalendarTemplateEventRecord, 'weeks' | 'qualification_weeks'> & {
  weeksText: string
  qualificationWeeksText: string
}

type TemplateStatus = 'draft' | 'active'

export type CalendarTemplateFormValue = {
  id: string
  name: string
  description: string
  status: TemplateStatus
  events: EventFormRow[]
}

type Props = {
  mode: 'create' | 'update'
  initialValue: CalendarTemplateFormValue
  idEditable: boolean
  submitLabel: string
  onSubmit: (payload: CalendarTemplateUpsertPayload) => void
  isSubmitting?: boolean
}

const emptyEvent = (): EventFormRow => ({
  id: '',
  name: '',
  category_code: tournamentCategoryCatalog[0]?.code ?? '',
  weeksText: '',
  qualificationWeeksText: '',
  locked: false,
  country_code: '',
  city: '',
  venue: '',
  notes: '',
  source_template_id: null,
  event_fingerprint: null
})

export function formValueFromTemplate(template: CalendarTemplateUpsertPayload): CalendarTemplateFormValue {
  return {
    id: template.id,
    name: template.name,
    description: template.description,
    status: template.status === 'archived' ? 'draft' : template.status,
    events: template.events.map((event) => ({
      ...event,
      weeksText: event.weeks.join(','),
      qualificationWeeksText: event.qualification_weeks.join(','),
      country_code: event.country_code ?? '',
      city: event.city ?? '',
      venue: event.venue ?? '',
      notes: event.notes ?? ''
    }))
  }
}

function parseWeeks(label: string, text: string): { values: number[]; errors: string[] } {
  const trimmed = text.trim()
  if (!trimmed) return { values: [], errors: [] }
  const values: number[] = []
  const errors: string[] = []
  const seen = new Set<number>()
  for (const part of trimmed.split(',')) {
    const token = part.trim()
    if (!/^\d+$/.test(token)) {
      errors.push(`${label} must contain comma-separated integers.`)
      continue
    }
    const value = Number(token)
    if (value < 1 || value > 61) errors.push(`${label} values must be integers 1..61.`)
    if (seen.has(value)) errors.push(`${label} values must be unique per event.`)
    seen.add(value)
    values.push(value)
  }
  return { values, errors }
}

function cleanOptional(value: string | null | undefined): string | null {
  const trimmed = (value ?? '').trim()
  return trimmed ? trimmed : null
}

function validate(value: CalendarTemplateFormValue): { payload?: CalendarTemplateUpsertPayload; errors: string[] } {
  const errors: string[] = []
  if (!value.id.trim()) errors.push('Template id is required.')
  if (!value.name.trim()) errors.push('Template name is required.')
  const eventIds = new Set<string>()
  const events: CalendarTemplateEventRecord[] = []

  value.events.forEach((event, index) => {
    const label = event.id.trim() || `Event row ${index + 1}`
    if (!event.id.trim()) errors.push(`${label}: id is required.`)
    if (!event.name.trim()) errors.push(`${label}: name is required.`)
    if (!event.category_code.trim()) errors.push(`${label}: category_code is required.`)
    if (event.id.trim() && eventIds.has(event.id.trim())) errors.push('Event ids must be unique inside template.')
    eventIds.add(event.id.trim())
    const weeks = parseWeeks(`${label} weeks`, event.weeksText)
    const qualificationWeeks = parseWeeks(`${label} qualification_weeks`, event.qualificationWeeksText)
    errors.push(...weeks.errors, ...qualificationWeeks.errors)
    if (value.status === 'active' && weeks.values.length === 0) errors.push(`${label}: active templates require weeks for every event.`)
    events.push({
      id: event.id.trim(),
      name: event.name.trim(),
      category_code: event.category_code.trim(),
      weeks: weeks.values,
      qualification_weeks: qualificationWeeks.values,
      locked: event.locked,
      country_code: cleanOptional(event.country_code),
      city: cleanOptional(event.city),
      venue: cleanOptional(event.venue),
      notes: cleanOptional(event.notes),
      source_template_id: event.source_template_id ?? null,
      event_fingerprint: event.event_fingerprint ?? null
    })
  })

  if (errors.length) return { errors }
  return {
    errors: [],
    payload: {
      id: value.id.trim(),
      name: value.name.trim(),
      description: value.description.trim(),
      status: value.status,
      events
    }
  }
}

export function CalendarTemplateEditor({ initialValue, idEditable, submitLabel, onSubmit, isSubmitting = false }: Props): JSX.Element {
  const [value, setValue] = useState<CalendarTemplateFormValue>(initialValue)
  const [errors, setErrors] = useState<string[]>([])
  const categoryOptions = useMemo(() => tournamentCategoryCatalog.map((category) => category.code), [])

  function updateEvent(index: number, patch: Partial<EventFormRow>): void {
    setValue((current) => ({
      ...current,
      events: current.events.map((event, eventIndex) => eventIndex === index ? { ...event, ...patch } : event)
    }))
  }

  function submit(): void {
    const result = validate(value)
    setErrors(result.errors)
    if (result.payload) onSubmit(result.payload)
  }

  return (
    <div>
      {errors.length ? <div role="alert" className="error"><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div> : null}
      <div className="form-grid">
        <label>id<input aria-label="Template id" value={value.id} disabled={!idEditable} onChange={(event) => setValue({ ...value, id: event.target.value })} /></label>
        <label>name<input aria-label="Template name" value={value.name} onChange={(event) => setValue({ ...value, name: event.target.value })} /></label>
        <label>description<textarea aria-label="Template description" value={value.description} onChange={(event) => setValue({ ...value, description: event.target.value })} /></label>
        <label>status<select aria-label="Template status" value={value.status} onChange={(event) => setValue({ ...value, status: event.target.value as TemplateStatus })}><option value="draft">draft</option><option value="active">active</option></select></label>
      </div>
      <h3>Events</h3>
      <button type="button" onClick={() => setValue({ ...value, events: [...value.events, emptyEvent()] })}>Add event row</button>
      {value.events.map((event, index) => (
        <fieldset key={index}>
          <legend>Event row {index + 1}: {event.id || 'new event'}</legend>
          <label>id<input aria-label={`Event ${index + 1} id`} value={event.id} onChange={(e) => updateEvent(index, { id: e.target.value })} /></label>
          <label>name<input aria-label={`Event ${index + 1} name`} value={event.name} onChange={(e) => updateEvent(index, { name: e.target.value })} /></label>
          <label>category_code<select aria-label={`Event ${index + 1} category_code`} value={event.category_code} onChange={(e) => updateEvent(index, { category_code: e.target.value })}>{categoryOptions.map((code) => <option key={code} value={code}>{code}</option>)}</select></label>
          <label>weeks<input aria-label={`Event ${index + 1} weeks`} placeholder="6,7" value={event.weeksText} onChange={(e) => updateEvent(index, { weeksText: e.target.value })} /></label>
          <label>qualification_weeks<input aria-label={`Event ${index + 1} qualification_weeks`} placeholder="5" value={event.qualificationWeeksText} onChange={(e) => updateEvent(index, { qualificationWeeksText: e.target.value })} /></label>
          <label><input aria-label={`Event ${index + 1} locked`} type="checkbox" checked={event.locked} onChange={(e) => updateEvent(index, { locked: e.target.checked })} /> locked</label>
          <label>country_code<input aria-label={`Event ${index + 1} country_code`} value={event.country_code ?? ''} onChange={(e) => updateEvent(index, { country_code: e.target.value })} /></label>
          <label>city<input aria-label={`Event ${index + 1} city`} value={event.city ?? ''} onChange={(e) => updateEvent(index, { city: e.target.value })} /></label>
          <label>venue<input aria-label={`Event ${index + 1} venue`} value={event.venue ?? ''} onChange={(e) => updateEvent(index, { venue: e.target.value })} /></label>
          <label>notes<textarea aria-label={`Event ${index + 1} notes`} value={event.notes ?? ''} onChange={(e) => updateEvent(index, { notes: e.target.value })} /></label>
          <button type="button" disabled={event.locked} onClick={() => setValue({ ...value, events: value.events.filter((_, eventIndex) => eventIndex !== index) })}>Delete event row</button>
        </fieldset>
      ))}
      <button type="button" onClick={submit} disabled={isSubmitting}>{submitLabel}</button>
    </div>
  )
}

export function emptyCalendarTemplateFormValue(): CalendarTemplateFormValue {
  return { id: '', name: '', description: '', status: 'draft', events: [] }
}
