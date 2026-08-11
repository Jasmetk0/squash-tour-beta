import { useState, type FormEvent } from 'react'

import type {
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1UpdatePayload,
} from '../api/countryV1'
import {
  COUNTRY_V1_RATING_FIELDS,
  countryV1FormDraftFromRecord,
  countryV1UpdatePayloadFromDraft,
  type CountryV1FormDraft,
} from '../utils/countryV1Form'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export type CountryV1GeographyOptions = {
  regions: Array<{ code: string, name: string }>
  travel_regions: Array<{ code: string, name: string }>
}

export function CountryV1EditFields({
  draft,
  geography,
  onChange,
}: {
  draft: CountryV1FormDraft
  geography?: CountryV1GeographyOptions
  onChange: (key: keyof CountryV1FormDraft, value: string) => void
}): JSX.Element {
  return (
    <>
      <fieldset>
        <legend>Identity</legend>
        <label>
          Name
          <input required value={draft.name} onChange={(event) => onChange('name', event.target.value)} />
        </label>
        <label>
          Notes
          <textarea value={draft.notes} onChange={(event) => onChange('notes', event.target.value)} />
        </label>
        <label>
          Area km²
          <input
            type="number"
            min="1"
            step="1"
            value={draft.area_km2}
            onChange={(event) => onChange('area_km2', event.target.value)}
          />
        </label>
      </fieldset>

      <fieldset>
        <legend>Geography</legend>
        <label>
          Region
          <select required value={draft.region} onChange={(event) => onChange('region', event.target.value)}>
            {geography?.regions.map((item) => (
              <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
            ))}
          </select>
        </label>
        <label>
          Travel Region
          <select value={draft.travel_region} onChange={(event) => onChange('travel_region', event.target.value)}>
            <option value="">None</option>
            {geography?.travel_regions.map((item) => (
              <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
            ))}
          </select>
        </label>
      </fieldset>

      <fieldset>
        <legend>Squash / Country strength</legend>
        {COUNTRY_V1_RATING_FIELDS.map(({ key, label }) => (
          <label key={key}>
            {label}
            <input
              type="number"
              required
              min="1"
              max="5"
              step="1"
              value={draft[key]}
              onChange={(event) => onChange(key, event.target.value)}
            />
          </label>
        ))}
        <label>
          Court Count
          <input
            type="number"
            min="0"
            step="1"
            value={draft.court_count}
            onChange={(event) => onChange('court_count', event.target.value)}
          />
        </label>
      </fieldset>
    </>
  )
}

export function CountryV1EditForm({
  detail,
  geography,
  saving,
  error,
  onCancel,
  onSave,
}: {
  detail: WorldPackageCountryV1Detail
  geography?: CountryV1GeographyOptions
  saving: boolean
  error: unknown
  onCancel: () => void
  onSave: (payload: WorldPackageCountryV1UpdatePayload) => void
}): JSX.Element {
  const [draft, setDraft] = useState<CountryV1FormDraft>(() => countryV1FormDraftFromRecord(detail.country))
  const [validationError, setValidationError] = useState('')

  function setDraftValue(key: keyof CountryV1FormDraft, value: string): void {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    try {
      const payload = countryV1UpdatePayloadFromDraft(draft, detail.package.fingerprint)
      setValidationError('')
      onSave(payload)
    } catch (submitError) {
      setValidationError(submitError instanceof Error ? submitError.message : String(submitError))
    }
  }

  return (
    <SectionCard title="Edit country">
      <form onSubmit={submit}>
        {(validationError || error != null) && (
          <p className="error" role="alert">
            {validationError || formatApiError(error)}
          </p>
        )}
        <CountryV1EditFields draft={draft} geography={geography} onChange={setDraftValue} />
        <p>
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>{' '}
          <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
        </p>
      </form>
    </SectionCard>
  )
}
