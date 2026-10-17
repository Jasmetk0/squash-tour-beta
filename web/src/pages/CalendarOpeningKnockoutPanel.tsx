import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  inspectCalendarOpeningKnockout, simulateCalendarOpeningKnockout,
  replayCalendarOpeningKnockout, previewCalendarOpeningKnockoutSave,
  saveCalendarOpeningKnockout,
} from '../api/client'
import type {
  KnockoutInspection, KnockoutReceipt, KnockoutSavePreview, KnockoutReplay,
} from '../api/calendarOpeningKnockout'
import { verifyKnockoutInspection } from '../api/calendarOpeningKnockout'
import { newCommandId } from '../admin/branchSimulation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { CalendarKnockoutAwardsPanel } from './CalendarKnockoutAwardsPanel'
import { CalendarSignedKnockoutStandingsPanel } from './CalendarSignedKnockoutStandingsPanel'

/** One real main-only 4-player opening-week bracket; no points or Week Transition. */
export function CalendarOpeningKnockoutPanel({
  runId, branchId, savedHead,
}: {
  runId: string; branchId: string; savedHead: string
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const client = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [view, setView] = useState<KnockoutInspection | null>(null)
  const [entrants, setEntrants] = useState<[string, string, string, string]>(['', '', '', ''])
  const [seed, setSeed] = useState('522')
  const [reason, setReason] = useState('')
  const [playConfirmed, setPlayConfirmed] = useState(false)
  const [saveConfirmed, setSaveConfirmed] = useState(false)
  const [preview, setPreview] = useState<KnockoutSavePreview | null>(null)
  const [receipt, setReceipt] = useState<KnockoutReceipt | null>(null)
  const [replay, setReplay] = useState<KnockoutReplay | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'busy' | 'blocked'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const commandId = useRef<string | null>(null)
  const token = useRef(0)
  const target = [runId, branchId, savedHead].join('|')
  const activeTarget = useRef(target)
  activeTarget.current = target

  // Source-of-truth identity is the *verified* Signed Saved Head returned by
  // this panel's production inspection, not the asynchronously refreshed
  // Branch selector cache. The URL survives route remounts and is isolated
  // across Run, Branch and newly Saved historical revisions.
  const scoresContext = [runId, branchId, view?.saved_head_revision_id ?? ''].join('|')
  const sameScoresHead = Boolean(
    view && searchParams.get('score_context') === scoresContext
  )
  const asOfSeason = sameScoresHead && /^(0|[1-9]\\d*)$/.test(
    searchParams.get('score_season') ?? '',
  ) ? Number(searchParams.get('score_season')) : 0
  const asOfWeek = sameScoresHead && /^[1-9]\\d*$/.test(
    searchParams.get('score_week') ?? '',
  ) ? Number(searchParams.get('score_week')) : 2
  const changeAsOf = (next: { season: number; week: number }) => {
    if (!view?.saved || !view.prepared_points) return
    setSearchParams(previous => {
      const updated = new URLSearchParams(previous)
      updated.set('score_context', scoresContext)
      updated.set('score_season', String(next.season))
      updated.set('score_week', String(next.week))
      return updated
    }, { replace: true })
  }

  useEffect(() => {
    const current = ++token.current
    setView(null); setEntrants(['', '', '', '']); setReason('')
    setStatus('loading'); setPreview(null); setReceipt(null); setReplay(null)
    setError(null); setNotice(null); setPlayConfirmed(false); setSaveConfirmed(false)
    commandId.current = null
    void inspectCalendarOpeningKnockout(runId, branchId).then(response => {
      if (current !== token.current) return
      const verified = verifyKnockoutInspection(response, runId, branchId, savedHead)
      setView(verified)
      setEntrants([
        verified.player_ids[0] ?? '', verified.player_ids[1] ?? '',
        verified.player_ids[2] ?? '', verified.player_ids[3] ?? '',
      ])
      setStatus('ready')
    }).catch(err => {
      if (current !== token.current) return
      setStatus('blocked'); setError(formatApiError(err))
    })
    return () => { token.current += 1 }
  }, [runId, branchId, savedHead])

  const seedValid = /^-?\d+$/.test(seed) && Number.isSafeInteger(Number(seed))
  const canPlay = view && !view.knockout && status === 'ready'
    && entrants.every(p => p !== '' && view.player_ids.includes(p))
    && new Set(entrants).size === 4 && seedValid && reason.trim().length > 0 && playConfirmed

  const play = async () => {
    if (!canPlay || !view) return
    const current = target
    commandId.current ??= newCommandId()
    setStatus('busy'); setError(null)
    try {
      const played = await simulateCalendarOpeningKnockout(runId, branchId, {
        command_id: commandId.current, match_id: 'calendar-opening-knockout',
        expected_saved_head: view.saved_head_revision_id,
        expected_initial_world_fingerprint: view.initial_world_fingerprint,
        entrant_ids: entrants, seed: Number(seed),
        operator_label: 'Admin', audit_reason: reason.trim(),
      })
      if (activeTarget.current !== current) return
      if (played.knockout.run_id !== runId || played.knockout.branch_id !== branchId
        || played.knockout.match_id !== 'calendar-opening-knockout'
        || played.knockout.week.calendar.weeks_per_year !== view.run_calendar.weeks_per_year) {
        throw Error('Knockout response belongs to another Run/Branch/clock')
      }
      setReceipt(played); setPlayConfirmed(false)
      const latest = await inspectCalendarOpeningKnockout(runId, branchId)
      if (activeTarget.current !== current) return
      setView(verifyKnockoutInspection(latest, runId, branchId, savedHead))
      setNotice(cs ? 'Odehrána dvě semifinále a finále. Pro trvalé uložení potvrď Save.' : 'Both semifinals and final played. Confirm manual Save to preserve the result.')
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  const doReplay = async () => {
    if (!view?.knockout || status !== 'ready') return
    const current = target
    setStatus('busy'); setError(null)
    try {
      const r = await replayCalendarOpeningKnockout(runId, branchId, view.knockout.match_id)
      if (activeTarget.current !== current) return
      if (!r.exact_replay || r.fingerprint !== view.knockout_fingerprint
        || r.rally_counts.length !== 3
        || r.winner_player_id !== view.knockout.matches[2].result.winner_player_id) {
        throw Error('Knockout replay does not match the Saved bracket')
      }
      setReplay(r)
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  const reviewSave = async () => {
    if (!view?.knockout || view.saved || status !== 'ready') return
    const current = target
    setStatus('busy'); setError(null); setSaveConfirmed(false)
    try {
      const p = await previewCalendarOpeningKnockoutSave(runId, branchId)
      if (activeTarget.current !== current) return
      if (!p.can_save || p.saved_head_revision_id !== view.saved_head_revision_id
        || p.draft_version !== view.draft_version
        || p.calendar_match_fingerprint !== view.knockout_fingerprint) {
        throw Error('Knockout Save preview is stale; refresh the Run')
      }
      setPreview(p)
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  const commitSave = async () => {
    if (!preview || !saveConfirmed || !view?.knockout || view.saved
      || preview.calendar_match_fingerprint !== view.knockout_fingerprint || status !== 'ready') return
    const current = target
    setStatus('busy'); setError(null)
    try {
      await saveCalendarOpeningKnockout(runId, branchId,
        preview.draft_version, preview.calendar_match_fingerprint!)
      if (activeTarget.current !== current) return
      setPreview(null); setSaveConfirmed(false)
      setNotice(cs ? 'Pavouk uložen do nové neměnné revize.' : 'Knockout saved to a new immutable revision.')
      await client.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      await client.invalidateQueries({ queryKey: ['run-branches', runId] })
      await client.invalidateQueries({ queryKey: ['branch-working-draft', runId, branchId] })
    } catch (err) {
      if (activeTarget.current === current) setError(formatApiError(err))
    } finally {
      if (activeTarget.current === current) setStatus('ready')
    }
  }

  return <section className="panel" aria-label="Calendar native four-player knockout">
    <h3>{cs ? 'Skutečný čtyřčlenný pavouk podle Run kalendáře' : 'Real four-player Run-calendar knockout'}</h3>
    <p className="status">{cs
      ? 'Season 1 Week 1 · skutečný BO5 pavouk. Po uložení lze připravit body; oficiální publikace a přechod týdne zatím chybí.'
      : 'Season 1 Week 1 · real BO5 bracket. Prepared points can be Saved afterwards; Official publication and Week Transition are not yet supported.'}</p>
    {status === 'loading' && <p>{cs ? 'Ověřuji Run…' : 'Inspecting Run…'}</p>}
    {status === 'blocked' && <p role="status">{cs ? 'Nedostupné: ' : 'Not available: '}{error}</p>}
    {view && status !== 'blocked' && <>
      <p className="status">W{view.run_calendar.weeks_per_year} · HEAD <code>{view.saved_head_revision_id}</code></p>
      {!view.knockout && <>
        {entrants.map((player, index) => <label key={index}>
          {cs ? 'Hráč' : 'Player'} {index + 1}{' '}
          <select value={player} disabled={status === 'busy'} onChange={e => {
            setEntrants(old => old.map((id, i) => i === index ? e.target.value : id) as [string, string, string, string])
            setPlayConfirmed(false); commandId.current = null
          }}>
            {view.player_ids.map(id => <option key={id} value={id}>{id}</option>)}
          </select>
        </label>)}
        <p className="status">{cs ? 'Semifinále: 1–2 a 3–4' : 'Semifinals: 1–2 and 3–4'}</p>
        <label>Seed <input type="number" value={seed} disabled={status === 'busy'}
          onChange={e => { setSeed(e.target.value); setPlayConfirmed(false); commandId.current = null }} /></label>
        <label>{cs ? 'Auditní důvod' : 'Audit reason'} <input value={reason} disabled={status === 'busy'}
          onChange={e => { setReason(e.target.value); setPlayConfirmed(false); commandId.current = null }} /></label>
        <label><input type="checkbox" checked={playConfirmed} disabled={status === 'busy'}
          onChange={e => setPlayConfirmed(e.target.checked)} /> {cs ? 'Potvrzuji odehrání všech tří zápasů.' : 'Confirm playing all three matches.'}</label>
        <button type="button" disabled={!canPlay} onClick={() => void play()}>{cs ? 'Odehrát pavouk' : 'Play knockout'}</button>
      </>}
      {view.knockout && <>
        {view.knockout.matches.map(match => <p key={match.round}>
          <strong>{match.round === 'final' ? (cs ? 'Finále' : 'Final') : (cs ? 'Semifinále' : 'Semifinal') + ' ' + (match.round === 'semifinal_1' ? '1' : '2')}:</strong>{' '}
          {match.input_context.player_a.player.player_id} vs {match.input_context.player_b.player.player_id}
          {' · '}{cs ? 'vítěz' : 'winner'}: <strong>{match.result.winner_player_id}</strong>
          {' · '}{match.result.rally_log.events.length} rallies
        </p>)}
        <p>{cs ? 'Šampion' : 'Champion'}: <strong>{view.knockout.matches[2].result.winner_player_id}</strong></p>
        <p>{cs ? 'Stav' : 'Status'}: {view.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuloženo' : 'Unsaved')}</p>
        {view.prepared_points && <div aria-label="Calendar prepared knockout points">
          <p><strong>{cs ? 'Připravené body (neoficiální)' : 'Prepared points (not Official)'}</strong>
            {' · '}{view.prepared_points.policy.category_label}
            {' · W'}{view.prepared_points.policy.validity_weeks}</p>
          {view.prepared_points.awards.map(a => <p key={a.player_id}>
            {a.player_id} · {a.reached_stage}: <strong>{a.main_points}</strong>
          </p>)}
          <p className="status">{cs ? 'Zveřejnění do oficiálního žebříčku až po nativním Week Transition.' : 'Official ranking publication requires native Week Transition.'}</p>
        </div>}
        {view.saved && view.prepared_points && <CalendarSignedKnockoutStandingsPanel
          runId={runId} branchId={branchId} view={view}
          season={asOfSeason} week={asOfWeek}
          onPositionChange={changeAsOf}
        />}
        {view.saved && !view.prepared_points && <CalendarKnockoutAwardsPanel
          runId={runId} branchId={branchId} view={view}
          onApplied={async () => {
            const latest = await inspectCalendarOpeningKnockout(runId, branchId)
            if (activeTarget.current === target) {
              setView(verifyKnockoutInspection(latest, runId, branchId, savedHead))
              setReplay(null); setReceipt(null)
              setNotice(cs ? 'Body připraveny. Ručním Save je uložíš do nové revize.' : 'Points prepared. Use manual Save to create an immutable revision.')
            }
          }}
        />}
        <button type="button" disabled={status === 'busy'} onClick={() => void doReplay()}>
          {cs ? 'Ověřit replay všech zápasů' : 'Verify all match replays'}</button>
        {replay && <p role="status">{cs ? 'Ověřeno' : 'Verified'} · {replay.rally_counts.join(' / ')} rallies</p>}
        {!view.saved && !preview && <button type="button" disabled={status === 'busy'}
          onClick={() => void reviewSave()}>{cs ? 'Zkontrolovat Save' : 'Review Save'}</button>}
        {preview && <div>
          <label><input type="checkbox" checked={saveConfirmed} disabled={status === 'busy'}
            onChange={e => setSaveConfirmed(e.target.checked)} /> {cs ? 'Potvrzuji vytvoření neměnné revize.' : 'Confirm new immutable Saved Revision.'}</label>
          <button type="button" disabled={!saveConfirmed || status === 'busy'}
            onClick={() => void commitSave()}>{cs ? 'Uložit pavouk' : 'Save knockout'}</button>
        </div>}
      </>}
    </>}
    {notice && <p className="status" role="status">{notice}</p>}
    {error && status !== 'blocked' && <p role="alert" className="error">{error}</p>}
    {receipt && <details><summary>{cs ? 'Doklad' : 'Receipt'}</summary><code>{receipt.fingerprint}</code></details>}
  </section>
}
