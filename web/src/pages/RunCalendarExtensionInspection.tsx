import { useEffect, useRef, useState } from 'react'
import { reviewRunCalendarExtension, saveRunCalendarExtension } from '../api/client'
import type { CalendarExtensionReceipt, CalendarExtensionReview } from '../api/runCalendarExtension'
import { formatApiError } from '../utils/apiErrors'

export function RunCalendarExtensionInspection({ runId, branchId, currentCount, language }: {
  runId: string; branchId: string; currentCount: number; language: 'cs' | 'en'
}): JSX.Element {
  const [input, setInput] = useState(String(currentCount + 1))
  const [review, setReview] = useState<CalendarExtensionReview | null>(null)
  const [receipt, setReceipt] = useState<CalendarExtensionReceipt | null>(null)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [saving, setSaving] = useState(false)
  const command = useRef<string | null>(null)
  const count = Number(input)
  const valid = /^\d+$/.test(input) && Number.isSafeInteger(count)
    && count > currentCount && count <= 2147483647
  const cs = language === 'cs'
  const source = JSON.stringify([runId, branchId, currentCount, input])
  const currentSource = useRef(source)
  currentSource.current = source
  const requestSequence = useRef(0)

  useEffect(() => {
    requestSequence.current += 1
    setReview(null); setReceipt(null); setConsent(false)
    setError(null); setBusy(false); setSaving(false); command.current = null
  }, [source])
  useEffect(() => () => { requestSequence.current += 1 }, [])

  async function inspect() {
    if (!valid || saving) return
    const sequence = ++requestSequence.current
    const requestedSource = source
    const isCurrent = () => sequence === requestSequence.current && requestedSource === currentSource.current
    setBusy(true); setError(null); setReview(null); setReceipt(null)
    setConsent(false); command.current = null
    try {
      const next = await reviewRunCalendarExtension(runId, count)
      if (next.original_calendar.season_count !== currentCount) {
        throw Error(cs ? 'Horizont Runu se změnil. Obnov stránku.' : 'Run horizon changed. Reload the page.')
      }
      if (isCurrent()) setReview(next)
    } catch (err) {
      if (isCurrent()) setError(formatApiError(err))
    } finally {
      if (isCurrent()) setBusy(false)
    }
  }

  async function commit() {
    if (!review?.can_save || !consent || busy || saving || receipt || !valid
      || review.proposed_calendar.season_count !== count
      || review.original_calendar.season_count !== currentCount) return
    const sequence = requestSequence.current
    const requestedSource = source
    const isCurrent = () => sequence === requestSequence.current && requestedSource === currentSource.current
    command.current ??= (globalThis.crypto?.randomUUID?.() ?? ('calendar-' + Date.now() + '-' + Math.random().toString(16).slice(2)))
    setSaving(true); setError(null)
    try {
      const saved = await saveRunCalendarExtension(runId, {
        command_id: command.current, new_season_count: count,
        review_fingerprint: review.review_fingerprint, explicit_confirmation: true,
      })
      if (isCurrent()) { setReceipt(saved); setConsent(false) }
    } catch (err) {
      // Preserve command id so response-loss retries return the SAME receipt.
      if (isCurrent()) setError(formatApiError(err))
    } finally {
      if (isCurrent()) setSaving(false)
    }
  }

  return <section aria-label="Run calendar extension inspection">
    <h4>{cs ? 'Prodloužení horizontu Runu' : 'Extend Run horizon'}</h4>
    <p className="status">{cs
      ? 'Kontrola všech Branches → výslovné potvrzení → jeden společný Save. Historie a cíle úloh zůstávají zachované; simulace se nespustí.'
      : 'Review every Branch → explicitly confirm → one atomic Save. History and frozen task goals remain unchanged; simulation does not start.'}</p>
    <label>{cs ? 'Nový celkový počet sezón' : 'New total season count'}
      <input type="number" min={currentCount + 1} max={2147483647} step="1"
        disabled={saving || !!receipt}
        value={input} onChange={event => {
          requestSequence.current += 1
          setInput(event.target.value); setReview(null); setReceipt(null)
          setConsent(false); setError(null); command.current = null
        }} />
    </label>
    <button type="button" disabled={!valid || busy || saving || !!receipt} onClick={() => void inspect()}>
      {busy ? (cs ? 'Kontroluji…' : 'Reviewing…') : (cs ? 'Zkontrolovat všechny Branches' : 'Review all Branches')}
    </button>
    {error && <p role="alert" className="error">{error}</p>}
    {review && !receipt && <div className="run-home-status-block">
      <p>{cs ? 'Původní horizont' : 'Original horizon'}: <strong>{review.original_calendar.season_count}</strong>
        {' → '}{cs ? 'nový horizont' : 'proposed horizon'}: <strong>{review.proposed_calendar.season_count}</strong></p>
      <p>{cs ? 'Přidáno' : 'Added'}: {review.added_seasons} {cs ? 'sezón' : 'seasons'}
        {' · '}{review.added_weeks} {cs ? 'týdnů' : 'weeks'}</p>
      <p>{cs ? 'Zkontrolované Branches' : 'Reviewed Branches'}: {review.branch_count}
        {' · '}{cs ? 'Neměnné uložené cíle úloh' : 'Frozen task targets retained'}: {review.frozen_task_count}</p>
      <ul>{review.branches.map(b => <li key={b.branch_id}><strong>{b.display_name}</strong>
        {' · '}{b.blockers.length ? b.blockers.join(', ') : (cs ? 'připraveno' : 'ready')}
        <small>{' · '}{b.saved_head_revision_id}</small></li>)}</ul>
      {!!review.blockers.length && <p role="alert" className="error">
        {cs ? 'Uložení blokováno: ' : 'Save blocked: '}{review.blockers.join(', ')}</p>}
      {review.can_save && <div>
        <label><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />
          {cs
            ? 'Potvrzuji prodloužení ve všech uvedených Branches a vytvoření nových Saved Revisions.'
            : 'I confirm extension across every listed Branch and creation of new Saved Revisions.'}</label>
        <button type="button" disabled={!consent || saving} onClick={() => void commit()}>
          {saving ? (cs ? 'Ukládám…' : 'Saving…') : (cs ? 'Potvrdit a uložit celý Run' : 'Confirm & Save entire Run')}
        </button>
      </div>}
      <p className="status">{cs
        ? 'Prodloužení zatím neodemyká sportovní simulaci pro nepodporované kalendáře.'
        : 'Extension does not unlock sporting simulation for unsupported calendars.'}</p>
    </div>}
    {receipt && <div role="status" className="run-home-status-block">
      <strong>{cs ? 'Horizont Runu úspěšně uložen' : 'Run horizon saved successfully'}</strong>
      <p>{receipt.previous_calendar.season_count} → {receipt.current_calendar.season_count}
        {' · '}{receipt.branch_count} Branches</p>
      <p>{cs ? 'Zachované staré revize, nové Saved Revisions a audit:' : 'Preserved old history, new Saved Revisions and audit:'}</p>
      <ul>{receipt.branches.map(b => <li key={b.branch_id}>{b.branch_id}: {b.saved_revision_id}</li>)}</ul>
      <p><small>{cs ? 'Potvrzení operace' : 'Command receipt'}: {receipt.command_id}</small></p>
      <p className="status">{cs ? 'Simulace nebyla spuštěna.' : 'No simulation was started.'}</p>
      <button type="button" onClick={() => window.location.reload()}>
        {cs ? 'Znovu načíst uložený Run' : 'Reload saved Run'}
      </button>
    </div>}
  </section>
}
