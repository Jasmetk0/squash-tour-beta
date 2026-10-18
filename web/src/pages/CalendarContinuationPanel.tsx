import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { previewCalendarSportingWeek, commitCalendarSportingWeek, inspectCalendarContinuation, simulateCalendarContinuation, saveCalendarContinuation, replayCalendarContinuation } from '../api/client'
import { verifySportingWeek, type SportingWeekCommand, type SportingWeekPreview, verifyContinuation, type ContinuationView, type ContinuationReceipt } from '../api/calendarContinuation'
import { newCommandId } from '../admin/branchSimulation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function CalendarContinuationPanel({ runId, branchId, head, onChange }: {
  runId: string; branchId: string; head: string; onChange: () => void
}) {
  const cs = useLanguage().language === 'cs', client = useQueryClient()
  const target = [runId, branchId, head].join('|'), current = useRef(target), epoch = useRef(0)
  if (current.current !== target) { current.current = target; epoch.current += 1 }
  const [view, setView] = useState<ContinuationView | null>(null)
  const [a, setA] = useState(''), [b, setB] = useState(''), [seed, setSeed] = useState('922'), [reason, setReason] = useState('')
  const [consent, setConsent] = useState(false), [saveConsent, setSaveConsent] = useState(false)
  const [review, setReview] = useState<ContinuationView | null>(null), [receipt, setReceipt] = useState<ContinuationReceipt | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null), [notice, setNotice] = useState<string | null>(null)
  const [weekReview, setWeekReview] = useState<{ command: SportingWeekCommand; preview: SportingWeekPreview } | null>(null)
  const [weekConsent, setWeekConsent] = useState(false)
  const weekCommandId = useRef<string | null>(null)
  const commandId = useRef<string | null>(null)
  useEffect(() => {
    const stamp = epoch.current
    setWeekReview(null); setWeekConsent(false); setView(null); setReview(null); setReceipt(null); setConsent(false); setSaveConsent(false)
    setError(null); setNotice(null); setBusy(true)
    void inspectCalendarContinuation(runId, branchId).then(v => {
      if (epoch.current !== stamp || current.current !== target) return
      const checked = verifyContinuation(v, runId, branchId, head)
      setView(checked); setA(checked.player_ids[0] ?? ''); setB(checked.player_ids[1] ?? '')
    }).catch(e => { if (epoch.current === stamp && current.current === target) setError(formatApiError(e)) })
      .finally(() => { if (epoch.current === stamp && current.current === target) setBusy(false) })
    return () => { epoch.current += 1 }
  }, [target, runId, branchId, head])
  useEffect(() => { commandId.current = null; weekCommandId.current = null; setConsent(false); setWeekConsent(false); setWeekReview(null) }, [target, a, b, seed, reason])
  const read = async () => verifyContinuation(await inspectCalendarContinuation(runId, branchId), runId, branchId, head)
  const perform = async (action: 'play' | 'review' | 'save' | 'replay' | 'week-review' | 'week-commit', matchId?: string) => {
    if (!view || busy) return
    const stamp = epoch.current, from = target
    const valid = () => epoch.current === stamp && current.current === from
    setBusy(true); setError(null); setNotice(null)
    try {
      if (action === 'week-review') {
        if (!view.saved || !view.checkpoint_fingerprint || !view.sporting_week || !reason.trim()
          || !/^-?\d+$/.test(seed) || !Number.isSafeInteger(Number(seed))) return
        weekCommandId.current ??= newCommandId()
        const command: SportingWeekCommand = {command_id: weekCommandId.current, expected_saved_head: head,
          expected_checkpoint_fingerprint: view.checkpoint_fingerprint, seed: Number(seed), operator_label: 'Admin', audit_reason: reason.trim()}
        const r = verifySportingWeek(await previewCalendarSportingWeek(runId, branchId, command), command, view)
        if (!valid()) return
        setWeekReview({command, preview: r}); setWeekConsent(false); setConsent(false)
      } else if (action === 'week-commit') {
        if (!weekReview || !weekConsent || !view.saved) return
        const r = verifySportingWeek(await commitCalendarSportingWeek(runId, branchId, weekReview.command, weekReview.preview.preview_fingerprint), weekReview.command, view)
        if (!valid()) return
        if (r.preview_fingerprint !== weekReview.preview.preview_fingerprint || r.checkpoint_fingerprint !== weekReview.preview.checkpoint_fingerprint) throw Error('Weekly result differs from review')
        const latest = await read(); if (!valid()) return
        if (latest.checkpoint_fingerprint !== r.checkpoint_fingerprint || latest.sporting_week?.week !== r.advance.target_week.week) throw Error('Weekly owner changed after preparation')
        setView(latest); setWeekReview(null); setWeekConsent(false); setReceipt(null); setReview(null); setSaveConsent(false); setConsent(false); onChange()
      } else if (action === 'play') {
        if (!consent || !view.can_play || !view.checkpoint_fingerprint || a === b || !reason.trim()
          || !view.player_ids.includes(a) || !view.player_ids.includes(b) || !/^-?\d+$/.test(seed) || !Number.isSafeInteger(Number(seed))) return
        commandId.current ??= newCommandId()
        const r = await simulateCalendarContinuation(runId, branchId, {
          command_id: commandId.current, match_id: 'continued-' + commandId.current,
          expected_saved_head: head, expected_checkpoint_fingerprint: view.checkpoint_fingerprint,
          player_a_id: a, player_b_id: b, seed: Number(seed), operator_label: 'Admin', audit_reason: reason.trim(),
        })
        if (!valid()) return
        if (r.match.source_saved_head !== head || r.match.source_checkpoint_fingerprint !== view.checkpoint_fingerprint
          || r.match.input_context.player_a.player.player_id !== a || r.match.input_context.player_b.player.player_id !== b
          || r.match.sequence !== view.matches.length + 1) throw Error('Played continuation source changed')
        const latest = await read(); if (!valid()) return
        if (latest.checkpoint_fingerprint !== r.checkpoint_fingerprint
          || latest.matches[latest.matches.length - 1]?.fingerprint !== r.fingerprint) throw Error('Population changed after the played continuation')
        setView(latest); setReceipt(r); setConsent(false); setReview(null); setSaveConsent(false); onChange()
      } else if (action === 'review') {
        const v = await read(); if (!valid()) return
        if (v.saved || v.checkpoint_fingerprint !== view.checkpoint_fingerprint) throw Error('Checkpoint changed before Save review')
        setView(v); setReview(v); setSaveConsent(false)
      } else if (action === 'save') {
        if (!review?.checkpoint_fingerprint || !saveConsent || review.checkpoint_fingerprint !== view.checkpoint_fingerprint) return
        await saveCalendarContinuation(runId, branchId, review.draft_version, review.checkpoint_fingerprint)
        if (!valid()) return
        setReview(null); setSaveConsent(false)
        await client.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
        await client.invalidateQueries({ queryKey: ['run-branches', runId] })
        await client.invalidateQueries({ queryKey: ['branch-working-draft', runId, branchId] })
      } else {
        const m = view.matches.find(m => m.match_id === matchId); if (!m || !matchId) return
        const r = await replayCalendarContinuation(runId, branchId, matchId); if (!valid()) return
        if (!r.exact_replay || r.match_id !== matchId || r.fingerprint !== m.fingerprint
          || r.winner_player_id !== m.winner_player_id || r.rally_count !== m.rally_count) throw Error('Replay differs from selected match')
        setNotice(cs ? 'Přesný replay ověřen.' : 'Exact replay verified.')
      }
    } catch (e) { if (valid()) setError(formatApiError(e)) }
    finally { if (valid()) setBusy(false) }
  }
  const canPlay = view?.can_play && a !== b && a && b && consent && reason.trim() && /^-?\d+$/.test(seed) && Number.isSafeInteger(Number(seed))
  return <section aria-label="Stateful calendar continuation">
    <h4>{cs ? 'Navazující zápasy z uloženého stavu' : 'Continue matches from Saved player state'}</h4>
    <p className="status">{cs ? 'Exhibice: převezme aktuálních 57 atributů, formu, rozehranost a únavu. Bez automatické regenerace, vývoje či bodů. Po každém zápase potvrď Save.' : 'Exhibitions consume the current 57 attributes, form, sharpness and fatigue. No automatic recovery, development or points. Confirm Save after each match.'}</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {view && <>
      {view.limited_player_ids.some(p => p === a || p === b) && <p role="status">{cs ? 'Vybraný hráč má zdravotní omezení. Fakta vstupují do zápasu; číselné zdravotní účinky zatím nejsou kalibrované.' : 'A selected player has Health limitations. Facts enter the match; numeric Health effects remain uncalibrated.'}</p>}
      {(['a', 'b'] as const).map(side => <label key={side}>{side === 'a' ? (cs ? 'Navazující hráč A' : 'Continuation player A') : (cs ? 'Navazující hráč B' : 'Continuation player B')}
        <select aria-label={side === 'a' ? (cs ? 'Navazující hráč A' : 'Continuation player A') : (cs ? 'Navazující hráč B' : 'Continuation player B')}
          value={side === 'a' ? a : b} disabled={busy || !view.can_play} onChange={e => side === 'a' ? setA(e.target.value) : setB(e.target.value)}>
          {view.player_ids.map(p => <option key={p} value={p}>{p}</option>)}
        </select></label>)}
      <label>{cs ? 'Seed navazujícího zápasu' : 'Continuation seed'}<input value={seed} disabled={busy || !view.can_play} onChange={e => setSeed(e.target.value)} /></label>
      <label>{cs ? 'Důvod navazujícího zápasu' : 'Continuation reason'}<input value={reason} disabled={busy || !view.can_play} onChange={e => setReason(e.target.value)} /></label>
      <label><input type="checkbox" checked={consent} disabled={busy || !view.can_play} onChange={e => setConsent(e.target.checked)} />{cs ? 'Potvrzuji zápas z tohoto uloženého stavu.' : 'Confirm playing from this Saved checkpoint.'}</label>
      <button disabled={busy || !canPlay} onClick={() => void perform('play')}>{cs ? 'Odehrát navazující zápas' : 'Play continuation match'}</button>
      {view.sporting_week && <section aria-label="Sporting weekly preparation">
        <h5>{cs ? 'Příprava dalšího sportovního týdne' : 'Prepare next sporting week'}</h5>
        <p>{cs ? 'Sportovní týden' : 'Sporting week'}: {view.sporting_week.week} / {view.sporting_week.calendar.weeks_per_year}</p>
        <p className="status">{cs ? 'Pouze exhibiční časová osa: vývoj atributů za 1/W roku, návrat formy, rozehranost a regenerace únavy. Zdraví se nehojí. Neprovádí lifecycle, intake, Official Ranking, publikaci ani úplný Week/Season Transition.' : 'Exhibition timeline only: attribute development for 1/W of a year, form regression, sharpness and fatigue recovery. No Health healing, lifecycle, intake, Official Ranking, publication or complete Week/Season Transition.'}</p>
        <button disabled={busy || !view.saved || view.sporting_week.week >= view.sporting_week.calendar.weeks_per_year || !reason.trim() || !/^-?\d+$/.test(seed) || !Number.isSafeInteger(Number(seed))} onClick={() => void perform('week-review')}>{cs ? 'Zkontrolovat přípravu týdne' : 'Review sporting week preparation'}</button>
        {view.sporting_week.week === view.sporting_week.calendar.weeks_per_year && <p role="status">{cs ? 'Konec sezóny: Season Transition zatím není podporován.' : 'Season boundary: Season Transition remains unsupported.'}</p>}
        {weekReview && <>
          <p>{cs ? 'Změnění hráči / atributy' : 'Changed players / attributes'}: {weekReview.preview.changed_player_count} / {weekReview.preview.attribute_change_count}</p>
          <p>{weekReview.preview.advance.completed_week.week} → {weekReview.preview.advance.target_week.week}</p>
          <label><input type="checkbox" checked={weekConsent} disabled={busy} onChange={e => setWeekConsent(e.target.checked)} />{cs ? 'Potvrzuji pouze sportovní přípravu tohoto týdne.' : 'Confirm this sporting-only weekly preparation.'}</label>
          <button disabled={busy || !weekConsent} onClick={() => void perform('week-commit')}>{cs ? 'Připravit sportovní týden' : 'Prepare sporting week'}</button>
        </>}
        {!!view.weekly_advances?.length && <table aria-label="Sporting week history"><thead><tr><th>{cs ? 'Týden' : 'Week'}</th><th>Save</th></tr></thead><tbody>
          {view.weekly_advances.map(w => <tr key={w.fingerprint}><td>{w.completed_week} → {w.target_week}</td><td>{w.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuloženo' : 'Unsaved')}</td></tr>)}
        </tbody></table>}
      </section>}
      {!view.saved && (view.matches.length > 0 || !!view.weekly_advance_count) && <>
        {!!view.weekly_advance_count && <p>{cs ? 'Sportovní příprava čeká na ruční Save.' : 'Sporting preparation awaiting manual Save.'}</p>}
        <p>{cs ? 'Odehráno, čeká na ruční Save.' : 'Played, awaiting manual Save.'}</p>
        <button disabled={busy} onClick={() => void perform('review')}>{cs ? 'Zkontrolovat navazující Save' : 'Review continuation Save'}</button>
        {review && <><p>{cs ? 'Uloží se aktuální stav populace a historie navazujících zápasů.' : 'Save the current population state and continued match history.'}</p>
          <label><input type="checkbox" checked={saveConsent} disabled={busy} onChange={e => setSaveConsent(e.target.checked)} />{cs ? 'Potvrzuji uložení navazujícího stavu.' : 'Confirm saving the continued state.'}</label>
          <button disabled={busy || !saveConsent} onClick={() => void perform('save')}>{cs ? 'Uložit navazující stav' : 'Save continued state'}</button></>}
      </>}
      {receipt && <p>{cs ? 'Použitá únava A / B' : 'Consumed fatigue A / B'}: {receipt.match.canonical_projections.map(p => p.long_term_fatigue).join(' / ')}</p>}
      {view.matches.length > 0 && <table aria-label="Continued match history"><thead><tr><th>{cs ? 'Zápas' : 'Match'}</th><th>{cs ? 'Vítěz' : 'Winner'}</th><th>Save</th><th>Replay</th></tr></thead>
        <tbody>{view.matches.map(m => <tr key={m.match_id}><td>{m.sequence} · {m.match_id}</td><td>{m.winner_player_id}</td><td>{m.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuloženo' : 'Unsaved')}</td>
          <td><button disabled={busy} onClick={() => void perform('replay', m.match_id)}>{cs ? 'Ověřit navazující replay' : 'Verify continuation replay'}</button></td></tr>)}</tbody></table>}
    </>}
  </section>
}
