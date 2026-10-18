import { useEffect, useRef, useState } from 'react'
import { inspectCalendarSportingPlayer } from '../api/client'
import type { PopulationSportingCheckpoint, PopulationSportingPlayer } from '../api/calendarOpeningKnockout'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

/** Inspect actual stored world authority, including players outside the draw. */
export function CalendarPopulationSportingPanel({ runId, branchId, head, checkpoint, playerIds }: {
  runId: string; branchId: string; head: string; checkpoint: PopulationSportingCheckpoint; playerIds: string[]
}) {
  const cs = useLanguage().language === 'cs'
  const [selected, setSelected] = useState(playerIds[0] ?? '')
  const playerId = playerIds.includes(selected) ? selected : playerIds[0] ?? ''
  const target = [runId, branchId, head, checkpoint.fingerprint, playerId].join('|')
  const current = useRef(target), epoch = useRef(0)
  if (current.current !== target) { current.current = target; epoch.current += 1 }
  const [record, setRecord] = useState<{ target: string; data: PopulationSportingPlayer } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null)
  useEffect(() => { setRecord(null); setError(null); setBusy(false) }, [target])
  useEffect(() => () => { epoch.current += 1 }, [])
  const load = async () => {
    const requested = epoch.current, from = target
    const valid = () => current.current === from && epoch.current === requested
    setBusy(true); setError(null)
    try {
      const data = await inspectCalendarSportingPlayer(runId, branchId, playerId, head, checkpoint.fingerprint)
      if (!valid()) return
      const p = data.player
      if (data.schema_version !== 'calendar_sporting_checkpoint_player.v1'
        || data.run_id !== runId || data.branch_id !== branchId || data.saved_head_revision_id !== head
        || data.checkpoint_fingerprint !== checkpoint.fingerprint || p.player_id !== playerId
        || p.attributes.length !== 57 || new Set(p.attributes.map(a => a[0])).size !== 57
        || p.attributes.some(a => !Number.isInteger(a[1]) || a[1] < 0 || a[1] > 200)
        || !Number.isInteger(p.potential_ovr) || p.potential_ovr < 0 || p.potential_ovr > 200
        || !Number.isInteger(p.current_form) || p.current_form < 0 || p.current_form > 200
        || !Number.isInteger(p.match_sharpness) || p.match_sharpness < 0 || p.match_sharpness > 100
        || !Number.isInteger(p.long_term_fatigue) || p.long_term_fatigue < 0 || p.long_term_fatigue > 100) {
        throw Error('Population sporting record does not match the selected source')
      }
      setRecord({ target: from, data })
    } catch (err) { if (valid()) setError(formatApiError(err)) }
    finally { if (valid()) setBusy(false) }
  }
  const shown = record?.target === target ? record.data.player : null
  return <section aria-label="Population sporting checkpoint">
    <h4>{cs ? 'Sportovní stav celé populace' : 'Population sporting checkpoint'}</h4>
    <p>{checkpoint.player_count} {cs ? 'hráčů · 57 atributů každého hráče' : 'players · 57 attributes per player'} · {checkpoint.saved
      ? (cs ? 'Uloženo' : 'Saved') : (cs ? 'Čeká na ruční Save' : 'Awaiting manual Save')}</p>
    <p className="status">{checkpoint.annual_development_applied ? (cs ? 'Uložený stav zahrnuje provizorní roční vývoj a týdenní regeneraci z exhibiční časové osy. Zdravotní účinky a úplný Week Transition nejsou implementované.' : 'Stored state includes provisional annual development and weekly recovery from the exhibition timeline. Health effects and the complete Week Transition remain unimplemented.') : cs
      ? 'Stav přebírá formu, rozehranost a únavu z odehraných zápasů. Hráči bez zápasu zůstávají na výchozím stavu. Týden se neposouvá a roční vývoj ani zdravotní účinky se zde nepočítají.'
      : 'State retains form, sharpness and fatigue from played matches. Players without a match retain their bootstrap state. This does not advance the week or calculate annual development or Health effects.'}</p>
    <label>{cs ? 'Hráč populace' : 'Population player'}<select value={playerId} onChange={e => setSelected(e.target.value)}>
      {playerIds.map(id => <option key={id} value={id}>{id}</option>)}
    </select></label>
    <button type="button" disabled={busy || !playerId} onClick={() => void load()}>{cs ? 'Zobrazit uložený sportovní stav' : 'Inspect stored sporting record'}</button>
    {error && <p role="alert">{error}</p>}
    {shown && <div aria-label="Population sporting player record">
      <p>{shown.player_id} · {cs ? 'Forma' : 'Form'} {shown.current_form} · {cs ? 'Rozehranost' : 'Sharpness'} {shown.match_sharpness} · {cs ? 'Únava' : 'Fatigue'} {shown.long_term_fatigue}</p>
      <table><thead><tr><th>{cs ? 'Atribut' : 'Attribute'}</th><th>{cs ? 'Hodnota / 200' : 'Value / 200'}</th></tr></thead>
        <tbody>{shown.attributes.map(([name, value]) => <tr key={name}><td>{name}</td><td>{value}</td></tr>)}</tbody></table>
    </div>}
  </section>
}
