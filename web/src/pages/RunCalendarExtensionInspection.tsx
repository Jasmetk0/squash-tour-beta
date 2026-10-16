import { useState } from 'react'
import { previewRunCalendarExtension } from '../api/client'
import type { RunCalendarExtensionPreview } from '../api/runCalendarCreation'
import { formatApiError } from '../utils/apiErrors'

export function RunCalendarExtensionInspection({ runId, branchId, currentCount, language }: {
  runId: string; branchId: string; currentCount: number; language: 'cs' | 'en'
}): JSX.Element {
  const [input, setInput] = useState(String(currentCount + 1))
  const [result, setResult] = useState<RunCalendarExtensionPreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const count = Number(input)
  const valid = /^\d+$/.test(input) && Number.isSafeInteger(count)
    && count > currentCount && count <= 2147483647
  const cs = language === 'cs'
  async function inspect() {
    if (!valid) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const preview = await previewRunCalendarExtension(runId, branchId, count)
      if (preview.original_calendar.season_count !== currentCount) {
        throw Error('Run calendar changed since the page was loaded')
      }
      setResult(preview)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setBusy(false)
    }
  }
  return <section aria-label="Run calendar extension inspection">
    <h4>{cs ? 'Prodloužení kalendáře – pouze náhled' : 'Calendar horizon extension – preview only'}</h4>
    <p className="status">{cs
      ? 'Zatím nelze prodloužení potvrdit ani uložit. Náhled nic nemění a nespouští simulaci.'
      : 'Extension cannot be confirmed or saved yet. This preview changes nothing and starts no simulation.'}</p>
    <label>{cs ? 'Nový celkový počet sezón' : 'New total season count'}
      <input type="number" min={currentCount + 1} max={2147483647} step="1"
        value={input} onChange={event => { setInput(event.target.value); setResult(null); setError(null) }} />
    </label>
    <button type="button" disabled={!valid || busy} onClick={() => void inspect()}>
      {busy ? (cs ? 'Ověřuji…' : 'Inspecting…') : (cs ? 'Zobrazit náhled' : 'Inspect extension')}
    </button>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <div role="status" className="run-home-status-block">
      <p>{cs ? 'Původní horizont' : 'Original horizon'}: <strong>{result.original_calendar.season_count}</strong></p>
      <p>{cs ? 'Nový horizont' : 'Proposed horizon'}: <strong>{result.proposed_calendar.season_count}</strong></p>
      <p>{cs ? 'Přidáno sezón' : 'Added seasons'}: {result.added_seasons}
        {' · '}{cs ? 'týdnů' : 'weeks'}: {result.added_weeks}</p>
      <p>{cs ? 'První nový týden' : 'First added week'}: {result.first_added_week.season_label}
        {' · W'}{result.first_added_week.season_week}</p>
      <p>{cs ? 'Nový konec' : 'New end'}: {result.new_last_week.season_label}
        {' · W'}{result.new_last_week.season_week}</p>
      <p><small>Saved Revision: {result.source_saved_head_revision_id}</small></p>
      <p className="status">{cs ? 'Pouze plán – zápis zatím není podporován.' : 'Planning only – committing is not supported yet.'}</p>
    </div>}
  </section>
}
