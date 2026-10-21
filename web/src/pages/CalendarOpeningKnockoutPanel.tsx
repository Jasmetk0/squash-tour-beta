import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
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
import { CalendarContinuationPanel } from './CalendarContinuationPanel'
import { CalendarPopulationSportingPanel } from './CalendarPopulationSportingPanel'
import { CalendarCanonicalInputsPanel } from './CalendarCanonicalInputsPanel'
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

  // A read-only Admin view preference must not navigate the entire Run
  // shell: its router revalidation would transiently replace the active
  // Branch context. Retain the selected week per TAB and exact real Signed
  // Saved HEAD; neither Viewer nor sporting/Official writers consume this.
  const scoresContext = [runId, branchId, view?.saved_head_revision_id ?? ''].join('|')
  const [asOfPreference, setAsOfPreference] = useState<{
    context: string; season: number; week: number
  } | null>(null)
  const asOfSeason = asOfPreference?.context === scoresContext
    ? asOfPreference.season : 0
  const asOfWeek = asOfPreference?.context === scoresContext
    ? asOfPreference.week : 2
  useEffect(() => {
    if (!view?.saved || !view.prepared_points) return
    const context = scoresContext
    let position = { season: 0, week: 2 }
    try {
      const stored = window.sessionStorage.getItem('squash-calendar-asof:' + context)
      if (stored) {
        const data: unknown = JSON.parse(stored)
        if (typeof data === 'object' && data !== null
          && 'season' in data && 'week' in data
          && typeof data.season === 'number' && typeof data.week === 'number'
          && Number.isSafeInteger(data.season) && Number.isSafeInteger(data.week)
          && data.season >= 0 && data.season < view.run_calendar.season_count
          && data.week >= 1 && data.week <= view.run_calendar.weeks_per_year
          && !(data.season === 0 && data.week === 1)) {
          position = { season: data.season, week: data.week }
        }
      }
    } catch {
      // A disabled/invalid browser preference is not sporting authority.
    }
    setAsOfPreference({ context, ...position })
  }, [scoresContext, view?.saved, view?.prepared_points?.scored_fingerprint])
  const changeAsOf = (next: { season: number; week: number }) => {
    if (!view?.saved || !view.prepared_points) return
    const position = { context: scoresContext, ...next }
    setAsOfPreference(position)
    try {
      window.sessionStorage.setItem('squash-calendar-asof:' + scoresContext,
        JSON.stringify(next))
    } catch {
      // The in-memory selection is still valid for this mounted Admin panel.
    }
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
    {!view?.knockout && <p className="status">{cs
      ? 'Nový pavouk používá provizorní počáteční stav (forma 100, rozehranost 100, únava 0) a po semifinále přenese změny do finále. Atributy používají verzovanou projekci 57 kanonických hodnot.'
      : 'New brackets use a provisional fresh baseline (form 100, sharpness 100, fatigue 0) and carry semifinal effects into the final. Attribute inputs use a versioned projection of 57 canonical values.'}</p>}
    {status === 'loading' && <p>{cs ? 'Ověřuji Run…' : 'Inspecting Run…'}</p>}
    {status === 'blocked' && <p role="status">{cs ? 'Nedostupné: ' : 'Not available: '}{error}</p>}
    {view && status !== 'blocked' && <>
      <p className="status">W{view.run_calendar.weeks_per_year} · HEAD <code>{view.saved_head_revision_id}</code></p>
      {(!view.knockout || view.knockout.canonical_source) && <CalendarCanonicalInputsPanel
        runId={runId} branchId={branchId} head={view.saved_head_revision_id}
        world={view.initial_world_fingerprint} entrants={view.knockout?.entrant_ids ?? entrants}
        source={view.knockout?.canonical_source}
      />}
      {view.health_readiness && <div aria-label="Saved knockout Health readiness">
        <p>{cs ? 'Turnaj používá uložená zdravotní fakta.' : 'Knockout uses Saved Health facts.'}</p>
        <p className="status">{cs
          ? 'Číselný vliv omezení, léčení a rozhodování o nenastoupení nebo skreči zatím nejsou podporované.'
          : 'Numeric limitation effects, healing and medical start/retirement decisions are not yet supported.'}</p>
        {view.health_readiness.limited_player_ids.some(id => (view.knockout?.entrant_ids ?? entrants).includes(id)) && <p role="status">{cs
          ? 'Pozor: vybraní hráči mají zdravotní omezení. Fakta zůstanou zaznamenaná, jejich číselný vliv se zatím nepočítá.'
          : 'Warning: selected entrants have Health limitations. Facts remain recorded; their numeric effect is not yet calculated.'}</p>}
      </div>}
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
        {view.knockout.health_source && <div aria-label="Frozen knockout Health inputs">
          <p>{cs ? 'Zdravotní fakta použitá při odehrání (pozdější úpravy je nemění)' : 'Health facts used when played (later edits do not change them)'}</p>
          <table aria-label="Frozen knockout Health table"><thead><tr>
            <th scope="col">{cs ? 'Hráč' : 'Player'}</th><th scope="col">{cs ? 'Omezení' : 'Conditions'}</th>
            <th scope="col">{cs ? 'Závažnost' : 'Severity'}</th><th scope="col">{cs ? 'Trvalé omezení' : 'Permanent limitation'}</th>
          </tr></thead><tbody>{view.knockout.health_source.profiles.map(profile => <tr key={profile.player_id}>
            <td>{profile.player_id}</td><td>{profile.current_records.map(r => r.condition_key).join(', ') || '—'}</td>
            <td>{profile.highest_current_severity}</td><td>{profile.highest_permanent_limitation}</td>
          </tr>)}</tbody></table>
          <p className="status">{cs ? 'Číselný vliv zdravotních omezení nebyl aplikován.' : 'Numeric Health limitation effects were not applied.'}</p>
        </div>}
        <p>{cs ? 'Šampion' : 'Champion'}: <strong>{view.knockout.matches[2].result.winner_player_id}</strong></p>
        {view.saved && view.population_sporting_checkpoint && <CalendarContinuationPanel
          runId={runId} branchId={branchId} head={view.saved_head_revision_id} onChange={() => {
            const from = target, stamp = token.current
            void inspectCalendarOpeningKnockout(runId, branchId).then(v => {
              if (activeTarget.current === from && token.current === stamp) setView(verifyKnockoutInspection(v, runId, branchId, savedHead))
            }).catch(e => { if (activeTarget.current === from && token.current === stamp) setError(formatApiError(e)) })
          }} />}
        {view.population_sporting_checkpoint && <CalendarPopulationSportingPanel
          runId={runId} branchId={branchId} head={view.saved_head_revision_id}
          checkpoint={view.population_sporting_checkpoint} playerIds={view.player_ids} />}
        {view.knockout.sporting && <div aria-label="Knockout player state checkpoints">
          <p className="status">{cs
            ? 'Finalisté používají formu, rozehranost a dlouhodobou únavu po semifinále. Provizorní kalibrace; bez automatické regenerace, vývoje atributů a zdravotních změn.'
            : 'Finalists consume post-semifinal form, sharpness and long-term fatigue. Provisional calibration; no automatic recovery, attribute development or Health changes.'}</p>
          <table aria-label="Knockout player state table"><thead><tr>
            <th scope="col">{cs ? 'Hráč' : 'Player'}</th><th scope="col">{cs ? 'Fáze' : 'Stage'}</th>
            <th scope="col">{cs ? 'Forma' : 'Form'}</th><th scope="col">{cs ? 'Rozehranost' : 'Sharpness'}</th>
            <th scope="col">{cs ? 'Dlouhodobá únava' : 'Long-term fatigue'}</th>
          </tr></thead><tbody>
            {(['initial', 'after_semifinals', 'terminal'] as const).flatMap(stage =>
              view.knockout!.sporting![stage].map(player => <tr key={stage + player.player_id}>
                <td>{player.player_id}</td><td>{stage === 'initial' ? (cs ? 'Před turnajem' : 'Before knockout')
                  : stage === 'after_semifinals' ? (cs ? 'Po semifinále' : 'After semifinals') : (cs ? 'Po finále' : 'After final')}</td>
                <td>{player.current_form}</td><td>{player.match_sharpness}</td><td>{player.long_term_fatigue}</td>
              </tr>))}
          </tbody></table>
        </div>}
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
