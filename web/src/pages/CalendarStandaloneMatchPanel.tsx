import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import {
  inspectCalendarStandaloneMatch, previewCalendarStandaloneMatchSave,
  replayCalendarStandaloneMatch, saveCalendarStandaloneMatch, simulateCalendarStandaloneMatch,
} from '../api/client'
import type {
  CalendarMatchReceipt, CalendarMatchSavePreview, CalendarMatchView,
} from '../api/calendarStandaloneMatch'
import { validateCalendarMatchView } from '../api/calendarStandaloneMatch'
import { newCommandId } from '../admin/branchSimulation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

/** Explicitly bounded sporting entry point for calendar-v2 Runs, not legacy simulation. */
export function CalendarStandaloneMatchPanel({ runId, branchId, savedHead }: {
  runId: string; branchId: string; savedHead: string
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const queryClient = useQueryClient()
  const [view, setView] = useState<CalendarMatchView | null>(null)
  const [playerA, setPlayerA] = useState('')
  const [playerB, setPlayerB] = useState('')
  const [seed, setSeed] = useState('418')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [saveConfirmed, setSaveConfirmed] = useState(false)
  const [savePreview, setSavePreview] = useState<CalendarMatchSavePreview | null>(null)
  const [receipt, setReceipt] = useState<CalendarMatchReceipt | null>(null)
  const [replayRallies, setReplayRallies] = useState<number | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'busy' | 'blocked'>('loading')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef<string | null>(null)
  const token = useRef(0)
  const target = [runId, branchId, savedHead].join('|')
  const activeTarget = useRef(target)
  activeTarget.current = target

  useEffect(() => {
    const sequence = ++token.current
    setView(null); setPlayerA(''); setPlayerB(''); setConfirmed(false)
    setSaveConfirmed(false); setSavePreview(null); setReceipt(null)
    setReplayRallies(null); setError(null); setNotice(null)
    setReason(''); setStatus('loading'); requestId.current = null
    void inspectCalendarStandaloneMatch(runId, branchId).then(response => {
      if (sequence !== token.current) return
      const data = validateCalendarMatchView(response, runId, branchId, savedHead)
      setView(data); setPlayerA(data.player_ids[0] ?? '')
      setPlayerB(data.player_ids[1] ?? ''); setStatus('ready')
    }).catch(err => {
      if (sequence !== token.current) return
      setStatus('blocked'); setError(formatApiError(err))
    })
    return () => { token.current += 1 }
  }, [runId, branchId, savedHead])

  const seedValid = /^-?\d+$/.test(seed) && Number.isSafeInteger(Number(seed))
  const canPlay = view && !view.match && status === 'ready'
    && playerA && playerB && playerA !== playerB
    && view.player_ids.includes(playerA) && view.player_ids.includes(playerB)
    && reason.trim() && seedValid && confirmed

  const doPlay = async () => {
    if (!canPlay || !view) return
    const current = target
    requestId.current ??= newCommandId()
    setStatus('busy'); setError(null)
    try {
      const response = await simulateCalendarStandaloneMatch(runId, branchId, {
        command_id: requestId.current, match_id: 'calendar-opening-exhibition',
        expected_saved_head: view.saved_head_revision_id,
        expected_initial_world_fingerprint: view.initial_world_fingerprint,
        player_a_id: playerA, player_b_id: playerB, seed: Number(seed),
        operator_label: 'Admin', audit_reason: reason.trim(),
      })
      if (activeTarget.current !== current) return
      if (response.match.run_id !== runId || response.match.branch_id !== branchId
        || response.match.match_id !== 'calendar-opening-exhibition'
        || response.match.week.calendar.weeks_per_year !== view.run_calendar.weeks_per_year
        || !view.player_ids.includes(response.match.result.winner_player_id)) {
        throw Error('Played match returned an unrelated Run/Branch/clock')
      }
      setReceipt(response); setConfirmed(false); setStatus('ready')
      setNotice(cs ? 'Zápas odehrán. Výsledek ještě není uloženou revizí.' : 'Match played. Save the result as an immutable revision.')
      const latest = await inspectCalendarStandaloneMatch(runId, branchId)
      if (activeTarget.current === current)
        setView(validateCalendarMatchView(latest, runId, branchId, view.saved_head_revision_id))
    } catch (err) {
      if (activeTarget.current === current) { setError(formatApiError(err)); setStatus('ready') }
    }
  }

  const inspectSave = async () => {
    if (!view?.match || view.saved || status !== 'ready') return
    const current = target
    setStatus('busy'); setError(null); setSaveConfirmed(false)
    try {
      const preview = await previewCalendarStandaloneMatchSave(runId, branchId)
      if (activeTarget.current !== current) return
      if (!preview.can_save || preview.saved_head_revision_id !== view.saved_head_revision_id
        || preview.calendar_match_fingerprint !== view.match_fingerprint
        || preview.draft_version !== view.draft_version) throw Error('Saved source changed; refresh the Run before confirming')
      setSavePreview(preview)
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  const commitSave = async () => {
    if (!savePreview || !saveConfirmed || status !== 'ready' || !view?.match
      || view.saved || savePreview.calendar_match_fingerprint !== view.match_fingerprint) return
    const current = target
    setStatus('busy'); setError(null)
    try {
      await saveCalendarStandaloneMatch(runId, branchId,
        savePreview.draft_version, savePreview.calendar_match_fingerprint!)
      if (activeTarget.current !== current) return
      setSaveConfirmed(false); setSavePreview(null); setStatus('ready')
      setNotice(cs ? 'Zápas uložen do nové neměnné revize. Ověř novou HEAD.' : 'Match saved to a new immutable revision. Verify the refreshed HEAD.')
      await queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      await queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
      await queryClient.invalidateQueries({ queryKey: ['branch-working-draft', runId, branchId] })
    } catch (err) {
      if (activeTarget.current === current) { setError(formatApiError(err)); setStatus('ready') }
    }
  }

  const verifyReplay = async () => {
    if (!view?.match || status !== 'ready') return
    const current = target
    setStatus('busy'); setError(null)
    try {
      const replay = await replayCalendarStandaloneMatch(runId, branchId, view.match.match_id)
      if (activeTarget.current !== current) return
      if (!replay.exact_replay || replay.fingerprint !== view.match_fingerprint
        || replay.match_id !== view.match.match_id
        || replay.result.winner_player_id !== view.match.result.winner_player_id)
        throw Error('Exact replay differs from the stored match')
      setReplayRallies(replay.rally_count)
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  return <section className="panel" aria-label="Calendar native standalone match">
    <h3>{cs ? 'První skutečný zápas podle Run kalendáře' : 'First real Run-calendar match'}</h3>
    <p className="status">{cs
      ? 'Samostatná exhibice dvou uložených hráčů, Season 1 Week 1, BO5. Skutečný MatchEngine a rally log; bez turnajových bodů, přechodu týdne a simulace dalšího sportovního vývoje.'
      : 'One standalone exhibition from two Saved players, Season 1 Week 1, BO5. Real MatchEngine and rally log; no tournament points, week transition or continuing player development.'}</p>
    {status === 'loading' && <p>{cs ? 'Ověřuji uložený kalendář a hráče…' : 'Verifying Saved calendar and players…'}</p>}
    {status === 'blocked' && <p className="status" role="status">{cs ? 'Zatím není připraveno: ' : 'Not ready yet: '}{error}</p>}
    {status !== 'blocked' && view && <div>
      <p className="status">W{view.run_calendar.weeks_per_year} · {view.run_calendar.start_year} · {cs ? 'HEAD' : 'HEAD'} <code>{view.saved_head_revision_id}</code></p>
      {!view.match && <div>
        <label>{cs ? 'Hráč A' : 'Player A'} <select value={playerA} disabled={status === 'busy'} onChange={e => {setPlayerA(e.target.value); setConfirmed(false); requestId.current = null}}>{view.player_ids.map(id => <option key={id} value={id}>{id}</option>)}</select></label>
        <label>{cs ? 'Hráč B' : 'Player B'} <select value={playerB} disabled={status === 'busy'} onChange={e => {setPlayerB(e.target.value); setConfirmed(false); requestId.current = null}}>{view.player_ids.map(id => <option key={id} value={id}>{id}</option>)}</select></label>
        <label>Seed <input type="number" value={seed} disabled={status === 'busy'} onChange={e => {setSeed(e.target.value); setConfirmed(false); requestId.current = null}} /></label>
        <label>{cs ? 'Důvod zásahu' : 'Audit reason'} <input value={reason} disabled={status === 'busy'} onChange={e => {setReason(e.target.value); setConfirmed(false); requestId.current = null}} /></label>
        <label><input type="checkbox" checked={confirmed} disabled={status === 'busy'} onChange={e => setConfirmed(e.target.checked)} /> {cs ? 'Potvrzuji odehrání zápasu.' : 'Confirm actual match execution.'}</label>
        <button type="button" disabled={!canPlay} onClick={() => void doPlay()}>{cs ? 'Odehrát zápas' : 'Play match'}</button>
      </div>}
      {view.match && <div>
        <p><strong>{cs ? 'Vítěz' : 'Winner'}:</strong> {view.match.result.winner_player_id} · {Object.entries(view.match.result.sets_won).map(([id,sets])=>id+': '+sets).join(' / ')}</p>
        <p>{cs ? 'Stav' : 'Status'}: {view.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuložený výsledek' : 'Unsaved result')} · {view.match.result.rally_log.events.length} rallies</p>
        <button type="button" disabled={status === 'busy'} onClick={() => void verifyReplay()}>{cs ? 'Ověřit přesný replay' : 'Verify exact replay'}</button>
        {replayRallies !== null && <p role="status">{cs ? 'Ověřený replay' : 'Verified replay'} · {replayRallies} rallies</p>}
        {!view.saved && !savePreview && <button type="button" disabled={status === 'busy'} onClick={() => void inspectSave()}>{cs ? 'Zkontrolovat ruční Save' : 'Review manual Save'}</button>}
        {savePreview && <div>
          <p className="status">{cs ? 'Uložit nový neměnný HEAD s potvrzeným výsledkem?' : 'Save a new immutable HEAD containing the confirmed result?'}</p>
          <label><input type="checkbox" checked={saveConfirmed} disabled={status === 'busy'} onChange={e=>setSaveConfirmed(e.target.checked)} /> {cs ? 'Potvrzuji nový Save.' : 'Confirm new Saved Revision.'}</label>
          <button type="button" disabled={!saveConfirmed || status === 'busy'} onClick={() => void commitSave()}>{cs ? 'Uložit revizi' : 'Save revision'}</button>
        </div>}
      </div>}
    </div>}
    {notice && <p role="status" className="status">{notice}</p>}
    {error && status !== 'blocked' && <p role="alert" className="error">{error}</p>}
    {receipt && <details><summary>{cs ? 'Doklad odehrání' : 'Match receipt'}</summary><code>{receipt.fingerprint}</code></details>}
  </section>
}
