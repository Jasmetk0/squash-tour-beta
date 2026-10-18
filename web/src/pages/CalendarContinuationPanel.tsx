import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { previewCalendarSportingWeek, commitCalendarSportingWeek, inspectCalendarContinuation, simulateCalendarContinuation, simulateCalendarFollowupKnockout, simulateCalendarScoredFollowupKnockout, simulateCalendarEightFollowupKnockout, saveCalendarContinuation, replayCalendarContinuation } from '../api/client'
import { verifyFollowupKnockout, verifyEightFollowupKnockout, type FollowupEightCommand, type FollowupKnockoutCommand, type FollowupScoredCommand, verifySportingWeek, type SportingWeekCommand, type SportingWeekPreview, verifyContinuation, type ContinuationView, type ContinuationReceipt } from '../api/calendarContinuation'
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
  const [knockoutEntrants, setKnockoutEntrants] = useState<string[]>([])
  const [knockoutConsent, setKnockoutConsent] = useState(false)
  const [eightEntrants, setEightEntrants] = useState<string[]>([])
  const [eightConsent, setEightConsent] = useState(false)
  const eightCommandId = useRef<string | null>(null)
  const [preparePoints, setPreparePoints] = useState(false)
  const [pointConsent, setPointConsent] = useState(false)
  const [category, setCategory] = useState('Operator-reviewed exhibition')
  const [championPoints, setChampionPoints] = useState('100')
  const [finalistPoints, setFinalistPoints] = useState('60')
  const [semiPoints, setSemiPoints] = useState('30')
  const knockoutCommandId = useRef<string | null>(null)
  const [review, setReview] = useState<ContinuationView | null>(null), [receipt, setReceipt] = useState<ContinuationReceipt | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null), [notice, setNotice] = useState<string | null>(null)
  const [weekReview, setWeekReview] = useState<{ command: SportingWeekCommand; preview: SportingWeekPreview } | null>(null)
  const [weekConsent, setWeekConsent] = useState(false)
  const weekCommandId = useRef<string | null>(null)
  const commandId = useRef<string | null>(null)
  useEffect(() => {
    const stamp = epoch.current
    setWeekReview(null); setWeekConsent(false); setView(null); setReview(null); setReceipt(null); setConsent(false); setSaveConsent(false)
    setKnockoutConsent(false); setEightConsent(false); setPointConsent(false); knockoutCommandId.current = null; eightCommandId.current = null
    setError(null); setNotice(null); setBusy(true)
    void inspectCalendarContinuation(runId, branchId).then(v => {
      if (epoch.current !== stamp || current.current !== target) return
      const checked = verifyContinuation(v, runId, branchId, head)
      setView(checked); setA(checked.player_ids[0] ?? ''); setB(checked.player_ids[1] ?? '')
      setKnockoutEntrants(checked.player_ids.slice(0, 4))
      setEightEntrants(checked.player_ids.slice(0, 8))
    }).catch(e => { if (epoch.current === stamp && current.current === target) setError(formatApiError(e)) })
      .finally(() => { if (epoch.current === stamp && current.current === target) setBusy(false) })
    return () => { epoch.current += 1 }
  }, [target, runId, branchId, head])
  useEffect(() => { commandId.current = null; weekCommandId.current = null; knockoutCommandId.current = null; eightCommandId.current = null
    setConsent(false); setKnockoutConsent(false); setEightConsent(false); setPointConsent(false); setWeekConsent(false); setWeekReview(null) }, [target, a, b, seed, reason, knockoutEntrants.join('|'), eightEntrants.join('|'), preparePoints, category, championPoints, finalistPoints, semiPoints])
  const read = async () => verifyContinuation(await inspectCalendarContinuation(runId, branchId), runId, branchId, head)
  const perform = async (action: 'play' | 'review' | 'save' | 'replay' | 'week-review' | 'week-commit' | 'knockout' | 'knockout-eight', matchId?: string) => {
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
      } else if (action === 'knockout-eight') {
        if (!view.can_play || !view.saved || !view.checkpoint_fingerprint
          || !view.sporting_week || view.sporting_week.week < 2
          || eightEntrants.length !== 8 || new Set(eightEntrants).size !== 8
          || eightEntrants.some(p => !view.player_ids.includes(p))
          || !eightConsent || !reason.trim() || !/^-?\d+$/.test(seed)
          || !Number.isSafeInteger(Number(seed))) return
        eightCommandId.current ??= newCommandId()
        const command: FollowupEightCommand = {
          command_id: eightCommandId.current,
          tournament_id: 'eight-' + eightCommandId.current,
          expected_saved_head: head, expected_checkpoint_fingerprint: view.checkpoint_fingerprint,
          entrant_ids: eightEntrants as FollowupEightCommand['entrant_ids'],
          seed: Number(seed), operator_label: 'Admin', audit_reason: reason.trim(),
        }
        const played = verifyEightFollowupKnockout(
          await simulateCalendarEightFollowupKnockout(runId, branchId, command), command, view,
        )
        if (!valid()) return
        const latest = await read(); if (!valid()) return
        const last = latest.tournaments?.[latest.tournaments.length - 1]
        if (latest.checkpoint_fingerprint !== played.checkpoint_fingerprint
          || last?.fingerprint !== played.fingerprint
          || latest.matches.length !== view.matches.length + 7)
          throw Error('Eight-player sporting owner changed after play')
        setView(latest); setEightConsent(false); setReceipt(null)
        setReview(null); setSaveConsent(false); onChange()
      } else if (action === 'knockout') {
        if (!view.can_play || !view.saved || !view.checkpoint_fingerprint
          || !view.sporting_week || view.sporting_week.week < 2
          || knockoutEntrants.length !== 4 || new Set(knockoutEntrants).size !== 4
          || knockoutEntrants.some(p => !view.player_ids.includes(p))
          || !knockoutConsent || (preparePoints && !pointConsent) || !reason.trim() || !/^-?\d+$/.test(seed)
          || !Number.isSafeInteger(Number(seed))) return
        knockoutCommandId.current ??= newCommandId()
        const command: FollowupKnockoutCommand = {
          command_id: knockoutCommandId.current,
          tournament_id: 'later-' + knockoutCommandId.current,
          expected_saved_head: head, expected_checkpoint_fingerprint: view.checkpoint_fingerprint,
          entrant_ids: knockoutEntrants as [string, string, string, string],
          seed: Number(seed), operator_label: 'Admin', audit_reason: reason.trim(),
        }
        const values = [championPoints, finalistPoints, semiPoints].map(Number)
        const goodPoints = [championPoints, finalistPoints, semiPoints].every(n => /^\d+$/.test(n) && Number.isSafeInteger(Number(n)) && Number(n) <= 1000000)
          && values[0] >= values[1] && values[1] >= values[2] && values[0] > values[2]
        if (preparePoints && (!goodPoints || !category.trim())) return
        const scored: FollowupScoredCommand = {
          ...command,
          point_policy: {category_label: category.trim(), champion: values[0],
            finalist: values[1], semifinal: values[2],
            validity_weeks: view.sporting_week.calendar.weeks_per_year},
          explicit_point_confirmation: true,
        }
        const played = verifyFollowupKnockout(
          preparePoints
            ? await simulateCalendarScoredFollowupKnockout(runId, branchId, scored)
            : await simulateCalendarFollowupKnockout(runId, branchId, command),
          preparePoints ? scored : command, view,
        )
        if (!valid()) return
        const latest = await read(); if (!valid()) return
        const last = latest.tournaments?.[latest.tournaments.length - 1]
        if (latest.checkpoint_fingerprint !== played.checkpoint_fingerprint
          || last?.fingerprint !== played.fingerprint
          || latest.matches.length !== view.matches.length + 3)
          throw Error('Knockout sporting owner changed after play')
        setView(latest); setKnockoutConsent(false); setPointConsent(false); setReceipt(null)
        setReview(null); setSaveConsent(false); onChange()
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
      {view.sporting_week && view.sporting_week.week >= 2 && <section aria-label="Later-week sporting knockout">
        <h5>{cs ? 'Další turnaj ze skutečného stavu hráčů' : 'Next knockout from actual player state'}</h5>
        <p className="status">{cs ? 'Čtyři hráči, dvě semifinále a finále v jedné atomické operaci. Skutečné zápasy ovlivní formu a únavu. Zatím bez Official Tour bodů.' : 'Four players, two semifinals and final in one atomic operation. Real matches affect form and fatigue. No Official Tour points yet.'}</p>
        {[0, 1, 2, 3].map(index => <label key={index}>{cs ? 'Nasazení' : 'Draw position'} {index + 1}
          <select aria-label={(cs ? 'Nasazení' : 'Draw position') + ' ' + (index + 1)}
            disabled={busy || !view.can_play} value={knockoutEntrants[index] ?? ''}
            onChange={e => setKnockoutEntrants(old => old.map((p, i) => i === index ? e.target.value : p))}>
            {view.player_ids.map(player => <option key={player} value={player}>{player}</option>)}
          </select>
        </label>)}
        <label><input type="checkbox" checked={preparePoints} disabled={busy || !view.can_play}
          onChange={e => setPreparePoints(e.target.checked)} />
          {cs ? 'Připravit bodové odměny (NE Official Ranking)' : 'Prepare point awards (NOT Official Ranking)'}
        </label>
        {preparePoints && <>
          <p role="status">{cs ? 'Bodová politika je ruční. Skutečné výsledky určí odměny, ale oficiální žebříček se nezmění. Platnost je W týdnů.' : 'Manual point policy: actual results determine awards, but Official Ranking does not change. Valid for W weeks.'}</p>
          <label>{cs ? 'Kategorie' : 'Category'}<input value={category} disabled={busy} onChange={e => setCategory(e.target.value)} /></label>
          <label>{cs ? 'Body vítěze' : 'Champion points'}<input type="number" min="0" max="1000000" value={championPoints} disabled={busy} onChange={e => setChampionPoints(e.target.value)} /></label>
          <label>{cs ? 'Body finalisty' : 'Finalist points'}<input type="number" min="0" max="1000000" value={finalistPoints} disabled={busy} onChange={e => setFinalistPoints(e.target.value)} /></label>
          <label>{cs ? 'Body semifinalisty' : 'Semifinalist points'}<input type="number" min="0" max="1000000" value={semiPoints} disabled={busy} onChange={e => setSemiPoints(e.target.value)} /></label>
          <label><input type="checkbox" checked={pointConsent} disabled={busy} onChange={e => setPointConsent(e.target.checked)} />
            {cs ? 'Výslovně potvrzuji připravené body, ne jejich oficiální publikaci.' : 'Explicitly confirm prepared points only, not Official publication.'}
          </label>
        </>}
        <label><input type="checkbox" checked={knockoutConsent}
          disabled={busy || !view.can_play || new Set(knockoutEntrants).size !== 4}
          onChange={e => setKnockoutConsent(e.target.checked)} />{cs ? 'Potvrzuji odehrání všech tří zápasů z tohoto Save.' : 'Confirm playing all three matches from this Save.'}</label>
        <button disabled={busy || !knockoutConsent || (preparePoints && (!pointConsent || !category.trim()
          || ![championPoints, finalistPoints, semiPoints].every(n => /^\d+$/.test(n) && Number.isSafeInteger(Number(n)) && Number(n) <= 1000000)
          || Number(championPoints) < Number(finalistPoints) || Number(finalistPoints) < Number(semiPoints)
          || Number(championPoints) === Number(semiPoints))) || !view.can_play
          || knockoutEntrants.length !== 4 || new Set(knockoutEntrants).size !== 4
          || !reason.trim() || !/^-?\d+$/.test(seed) || !Number.isSafeInteger(Number(seed))}
          onClick={() => void perform('knockout')}>{cs ? 'Odehrát další čtyřčlenný turnaj' : 'Play next four-player knockout'}</button>
        {view.player_ids.length >= 8 && <>
          <h5>{cs ? 'Osmičlenný vyřazovací turnaj' : 'Eight-player knockout'}</h5>
          <p className="status">{cs ? 'Čtyři čtvrtfinále, dvě semifinále, finále. Sedm skutečně odehraných zápasů v jedné operaci. Po odehrání je nutný ruční Save; bez Official Tour bodů.' : 'Four quarterfinals, two semifinals and a final. Seven actual MatchEngine matches in one operation; manual Save required afterward. No Official Tour points.'}</p>
          {Array.from({length: 8}, (_, index) => <label key={index}>
            {cs ? 'Pozice v pavouku' : 'Bracket position'} {index + 1}
            <select aria-label={(cs ? 'Pozice v pavouku' : 'Bracket position') + ' ' + (index + 1)}
              disabled={busy || !view.can_play} value={eightEntrants[index] ?? ''}
              onChange={e => setEightEntrants(old => old.map((p, i) => i === index ? e.target.value : p))}>
              {view.player_ids.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>)}
          <label><input type="checkbox" checked={eightConsent}
            disabled={busy || !view.can_play || new Set(eightEntrants).size !== 8}
            onChange={e => setEightConsent(e.target.checked)} />
            {cs ? 'Potvrzuji sedm skutečných zápasů ze současného uloženého stavu.' : 'Confirm all seven real matches from the current Saved checkpoint.'}
          </label>
          <button disabled={busy || !view.can_play || !eightConsent || eightEntrants.length !== 8
            || new Set(eightEntrants).size !== 8 || !reason.trim()
            || !/^-?\d+$/.test(seed) || !Number.isSafeInteger(Number(seed))}
            onClick={() => void perform('knockout-eight')}>
            {cs ? 'Odehrát osmičlenný turnaj' : 'Play eight-player knockout'}
          </button>
        </>}
      </section>}
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
      {!!view.tournaments?.length && <table aria-label="Later-week knockout history"><thead><tr><th>{cs ? 'Turnaj' : 'Tournament'}</th><th>{cs ? 'Vítěz' : 'Winner'}</th><th>{cs ? 'Týden' : 'Week'}</th><th>{cs ? 'Připravené body (neoficiální)' : 'Prepared points (unofficial)'}</th><th>Save</th></tr></thead><tbody>
        {view.tournaments.map(t => <tr key={t.fingerprint}><td>{t.tournament_id} · {t.entrant_ids.length} {cs ? 'hráčů' : 'players'}</td><td>{t.winner_player_id}</td><td>{t.week}</td><td>{
          t.prepared_points_status === 'prepared_not_official'
            ? (t.prepared_awards ?? []).map(a => `${a.player_id}: ${a.main_points}`).join(' · ')
            : '—'
        }</td><td>{t.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuloženo' : 'Unsaved')}</td></tr>)}
      </tbody></table>}
      {view.matches.length > 0 && <table aria-label="Continued match history"><thead><tr><th>{cs ? 'Zápas' : 'Match'}</th><th>{cs ? 'Vítěz' : 'Winner'}</th><th>Save</th><th>Replay</th></tr></thead>
        <tbody>{view.matches.map(m => <tr key={m.match_id}><td>{m.sequence} · {m.match_id}</td><td>{m.winner_player_id}</td><td>{m.saved ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Neuloženo' : 'Unsaved')}</td>
          <td><button disabled={busy} onClick={() => void perform('replay', m.match_id)}>{cs ? 'Ověřit navazující replay' : 'Verify continuation replay'}</button></td></tr>)}</tbody></table>}
    </>}
  </section>
}
