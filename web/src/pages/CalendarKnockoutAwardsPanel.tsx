import { useEffect, useRef, useState } from 'react'

import { applyCalendarKnockoutAwards, reviewCalendarKnockoutAwards } from '../api/client'
import type {
  CalendarAwardPolicy, CalendarAwardProposal, CalendarAwardReview, KnockoutInspection,
} from '../api/calendarOpeningKnockout'
import { newCommandId } from '../admin/branchSimulation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

/** Only for an already Signed Saved knockout. Explicitly not Official points. */
export function CalendarKnockoutAwardsPanel({ runId, branchId, view, onApplied }: {
  runId: string; branchId: string; view: KnockoutInspection
  onApplied: () => Promise<void>
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [category, setCategory] = useState('Manual opening-week points')
  const [champion, setChampion] = useState('100')
  const [finalist, setFinalist] = useState('60')
  const [semifinal, setSemifinal] = useState('30')
  const [reason, setReason] = useState('')
  const [review, setReview] = useState<CalendarAwardReview | null>(null)
  const [reviewTarget, setReviewTarget] = useState<string | null>(null)
  const [proposal, setProposal] = useState<CalendarAwardProposal | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const commandId = useRef<string | null>(null)
  const target = [runId, branchId, view.saved_head_revision_id, view.knockout_fingerprint].join('|')
  const activeTarget = useRef(target)
  const epoch = useRef(0)
  if (activeTarget.current !== target) {
    activeTarget.current = target
    epoch.current += 1
  }

  const numeric = [champion, finalist, semifinal]
  const pointValues = numeric.map(v => Number(v))
  const valid = numeric.every(v => /^\d+$/.test(v))
    && pointValues.every(v => Number.isSafeInteger(v) && v >= 0 && v <= 1000000)
    && pointValues[0] >= pointValues[1] && pointValues[1] >= pointValues[2]
    && pointValues[0] > pointValues[2]
    && category.trim().length > 0 && category.trim().length <= 120
    && reason.trim().length > 0 && reason.trim().length <= 1000

  const invalidate = () => {
    setReview(null); setReviewTarget(null); setProposal(null); setConfirmed(false); commandId.current = null
    setError(null)
  }
  useEffect(() => {
    invalidate(); setBusy(false)
  }, [target])
  useEffect(() => () => { epoch.current += 1 }, [])
  const currentReview = reviewTarget === target ? review : null

  const doReview = async () => {
    if (!valid || !view.saved || !view.knockout_fingerprint || busy) return
    const source = target
    const requestEpoch = epoch.current
    const isCurrent = () => activeTarget.current === source && epoch.current === requestEpoch
    const policy: CalendarAwardPolicy = {
      schema_version: 'calendar_knockout_point_policy.v1',
      source_kind: 'admin_explicit_reviewed', category_label: category.trim(),
      champion: pointValues[0], finalist: pointValues[1],
      semifinal: pointValues[2], validity_weeks: view.run_calendar.weeks_per_year,
    }
    const proposed: CalendarAwardProposal = {
      expected_saved_head: view.saved_head_revision_id,
      expected_knockout_fingerprint: view.knockout_fingerprint,
      policy, operator_label: 'Admin', audit_reason: reason.trim(),
    }
    setBusy(true); setError(null); setConfirmed(false)
    try {
      const result = await reviewCalendarKnockoutAwards(runId, branchId, proposed)
      if (!isCurrent()) return
      if (result.run_id !== runId || result.branch_id !== branchId
        || result.source_saved_head !== view.saved_head_revision_id
        || result.source_knockout_fingerprint !== view.knockout_fingerprint
        || result.publication_status !== 'prepared_not_official'
        || !/^[0-9a-f]{64}$/.test(result.preview_fingerprint)
        || result.awards.length !== 4 || result.first_publication_week.week !== 2
        || result.first_publication_week.calendar.weeks_per_year !== view.run_calendar.weeks_per_year) {
        throw Error('Point review does not match the selected Saved Run/Branch')
      }
      setProposal(proposed); setReview(result); setReviewTarget(source)
    } catch (err) {
      if (isCurrent()) setError(formatApiError(err))
    } finally {
      if (isCurrent()) setBusy(false)
    }
  }

  const apply = async () => {
    if (!currentReview || !proposal || !confirmed || busy
      || proposal.expected_saved_head !== view.saved_head_revision_id
      || proposal.expected_knockout_fingerprint !== view.knockout_fingerprint) return
    const source = target
    const requestEpoch = epoch.current
    const isCurrent = () => activeTarget.current === source && epoch.current === requestEpoch
    commandId.current ??= newCommandId()
    setBusy(true); setError(null)
    try {
      const receipt = await applyCalendarKnockoutAwards(runId, branchId, {
        command_id: commandId.current, proposal,
        expected_preview_fingerprint: currentReview.preview_fingerprint,
        explicit_confirmation: true,
      })
      if (!isCurrent()) return
      if (!/^[0-9a-f]{64}$/.test(receipt.fingerprint)) {
        throw Error('Prepared award receipt is invalid')
      }
      await onApplied()
      if (isCurrent()) {
        setConfirmed(false); setReview(null); setReviewTarget(null); setProposal(null)
      }
    } catch (err) {
      if (isCurrent()) setError(formatApiError(err))
    } finally {
      if (isCurrent()) setBusy(false)
    }
  }

  return <section aria-label="Calendar knockout award preparation">
    <h4>{cs ? 'Příprava bodů turnaje' : 'Prepare knockout point awards'}</h4>
    <p className="status">{cs
      ? 'Body z reálně odehraného a uloženého pavouka. Zatím se NEPUBLIKUJÍ do oficiálního žebříčku. Platnost W týdnů; kandidátní zveřejnění Week 2.'
      : 'Points derived from a real Saved knockout. NOT yet published in Official Ranking. W-week validity; proposed first publication Week 2.'}</p>
    <label>{cs ? 'Název bodové politiky' : 'Point policy label'} <input
      value={category} disabled={busy} onChange={e => { setCategory(e.target.value); invalidate() }} /></label>
    {([
      [cs ? 'Vítěz' : 'Champion', champion, setChampion],
      [cs ? 'Finalista' : 'Finalist', finalist, setFinalist],
      [cs ? 'Semifinalista' : 'Semifinalist', semifinal, setSemifinal],
    ] as const).map(([label, value, update]) => <label key={label}>
      {label} <input type="number" min="0" step="1" value={value}
        disabled={busy} onChange={e => { update(e.target.value); invalidate() }} />
    </label>)}
    <label>{cs ? 'Důvod nastavení bodů' : 'Point policy audit reason'}
      <input value={reason} disabled={busy}
        onChange={e => { setReason(e.target.value); invalidate() }} /></label>
    {!currentReview && <button type="button" disabled={!valid || busy}
      onClick={() => void doReview()}>{cs ? 'Zkontrolovat bodovou distribuci' : 'Review prepared point awards'}</button>}
    {currentReview && <>
      <p className="status">{cs ? 'Návrh bodů z uložených výsledků:' : 'Points derived from Saved results:'}</p>
      {currentReview.awards.map(a => <p key={a.player_id}>
        {a.player_id} · {a.reached_stage} · <strong>{a.main_points}</strong>
      </p>)}
      <label><input type="checkbox" checked={confirmed} disabled={busy}
        onChange={e => setConfirmed(e.target.checked)} /> {cs
        ? 'Potvrzuji přípravu bodů bez oficiální publikace.'
        : 'Confirm preparing points without Official publication.'}</label>
      <button type="button" disabled={!confirmed || busy}
        onClick={() => void apply()}>{cs ? 'Připravit body' : 'Apply prepared awards'}</button>
    </>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>
}
