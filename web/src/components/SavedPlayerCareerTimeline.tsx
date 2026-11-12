import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { getSavedPlayerCareer } from '../api/client'
import { CAREER_KINDS, validSavedPlayerCareer } from '../api/savedPlayerCareer'
import type { CareerEvent } from '../api/savedPlayerCareer'
import { formatApiError } from '../utils/apiErrors'

type Props = { runId: string; branchId: string; savedHead: string; playerId: string; cs: boolean }

const LABEL: Record<string, [string, string]> = {
  turn_pro: ['Přechod mezi profesionály', 'Turned professional'],
  first_recorded_title: ['První zaznamenaný titul', 'First recorded title'],
  first_top_rank: ['První zaznamenané TOP 100', 'First recorded TOP 100'],
  career_high_ranking: ['Nejlepší publikovaný ranking', 'Career-high published ranking'],
  edition_result: ['Výsledek Edice', 'Edition result'],
  retirement: ['Konec kariéry', 'Retirement']
}
const STAGE: Record<string, [string, string]> = {
  champion: ['vítěz', 'champion'], finalist: ['finalista', 'finalist'],
  semifinal: ['semifinále', 'semifinal'], quarterfinal: ['čtvrtfinále', 'quarterfinal']
}

function weekText(e: CareerEvent, cs: boolean): string {
  const w = e.effective_week
  if (!w) return cs ? 'před začátkem Runu' : 'before the Run started'
  return `${cs ? 'sezóna' : 'season'} ${w.season_index + 1} · ${cs ? 'týden' : 'week'} ${w.week}`
}

function detailText(e: CareerEvent, cs: boolean): string {
  const d = e.detail
  if (e.kind === 'edition_result') {
    const stage = String(d.reached_stage)
    return `${String(d.name)} · ${(STAGE[stage] ?? [stage, stage])[cs ? 0 : 1]} · ${d.awarded_points} ${cs ? 'b.' : 'pts'}`
  }
  if (e.kind === 'first_top_rank' || e.kind === 'career_high_ranking') {
    const start = d.first_recorded_ranking_week === true
    return `#${d.rank} · ${d.points} ${cs ? 'b.' : 'pts'}` + (start
      ? (cs ? ' · už v prvním zaznamenaném rankingu' : ' · already in the first recorded ranking') : '')
  }
  if (e.kind === 'turn_pro' && d.opening_professional === true) {
    return cs ? 'profesionál už při startu Runu' : 'professional before the Run started'
  }
  if (e.kind === 'retirement' && d.without_turn_pro === true) {
    return cs ? 'výjimka: bez přechodu mezi profesionály' : 'exception: without ever turning pro'
  }
  return ''
}

function sourceText(e: CareerEvent, cs: boolean): string {
  const short = e.source.fingerprint.slice(0, 12)
  return `${cs ? 'Zdroj' : 'Source'}: ${e.source.kind} · ${short}`
}

export function SavedPlayerCareerTimeline({ runId, branchId, savedHead, playerId, cs }: Props): JSX.Element {
  const [kind, setKind] = useState('all')
  const [draft, setDraft] = useState('')
  const [asOf, setAsOf] = useState<number | undefined>(undefined)
  const query = useQuery({
    queryKey: ['saved-player-career', runId, branchId, savedHead, playerId, asOf],
    queryFn: () => getSavedPlayerCareer(runId, branchId, playerId, asOf),
    retry: false
  })
  const title = cs ? 'Kariéra: časová osa a milníky' : 'Career: timeline and milestones'
  if (query.isPending) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="status">{cs ? 'Načítám kariéru…' : 'Loading career…'}</p></section>
  }
  if (query.error) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="status">{cs ? 'Kariérní osa není pro tuto revizi dostupná: ' : 'Career timeline is unavailable for this revision: '}
        {formatApiError(query.error)}</p></section>
  }
  const data = query.data
  if (!validSavedPlayerCareer(data, { runId, branchId, savedHead, playerId })) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="alert">{cs
        ? 'Odpověď neodpovídá vybrané Branch, uložené revizi nebo hráči a nebyla zobrazena.'
        : 'The response does not match the selected Branch, Saved revision or player and was not displayed.'}</p></section>
  }
  const rows = data.timeline.filter(e => kind === 'all' || e.kind === kind)
  const label = (k: string) => (LABEL[k] ?? [k, k])[cs ? 0 : 1]
  const o = data.overview
  return <section aria-label={title}>
    <h3>{title}</h3>
    <p>{cs
      ? 'Pouze čtení z uložené revize vybrané Branch. Zobrazuje jen doložená fakta do zvoleného týdne; nic nevytváří ani neovlivňuje simulaci.'
      : 'Read-only from the selected Branch Saved revision. Shows only recorded facts up to the chosen week; it creates nothing and does not affect the simulation.'}</p>
    <p role="note">{cs
      ? 'Pokrytí začíná prvním zaznamenaným rankingem Runu; dřívější historie je neznámá, ne nulová. „První zaznamenaný“ proto neznamená první v životě.'
      : data.covered_period.note + ' “First recorded” therefore does not mean first ever.'}</p>
    <dl>
      <dt>{cs ? 'Stav' : 'Status'}</dt>
      <dd>{o.status === 'retired' ? (cs ? 'ukončil kariéru' : 'retired')
        : o.status === 'professional' ? (cs ? 'profesionál' : 'professional')
        : (cs ? 'zatím neprofesionál' : 'not yet professional')}</dd>
      <dt>{cs ? 'Tituly / finále / Edice' : 'Titles / finals / Editions'}</dt>
      <dd>{o.titles} / {o.finals} / {o.editions_played}</dd>
      <dt>{cs ? 'Nejlepší ranking / aktuální' : 'Career-high / current rank'}</dt>
      <dd>{o.career_high_rank ?? '—'} / {o.current_rank ?? '—'}</dd>
    </dl>
    <form onSubmit={ev => {
      ev.preventDefault()
      const n = Number(draft)
      setAsOf(draft.trim() !== '' && Number.isInteger(n) && n >= 0 ? n : undefined)
    }}>
      <label>{cs ? 'Zobrazit k týdnu (pořadové číslo)' : 'View as of week (ordinal)'}{' '}
        <input inputMode="numeric" value={draft} placeholder={String(data.as_of_ordinal)}
          onChange={ev => setDraft(ev.target.value)} />
      </label>{' '}
      <button type="submit">{cs ? 'Použít' : 'Apply'}</button>
    </form>
    <p role="status">{cs ? 'Zobrazeno k týdnu č.' : 'Shown as of week no.'} {data.as_of_ordinal}</p>
    <h4>{cs ? 'Milníky' : 'Milestones'}</h4>
    {data.milestones.length === 0
      ? <p>{cs ? 'K tomuto týdnu zatím není doložený žádný milník.' : 'No milestone is recorded as of this week.'}</p>
      : <ul>{data.milestones.map((m, i) => <li key={m.kind + i}>
        <strong>{label(m.kind)}</strong> · {weekText(m, cs)}
        {detailText(m, cs) && ` · ${detailText(m, cs)}`}
        <br /><small>{sourceText(m, cs)}</small></li>)}</ul>}
    <p>{cs ? 'Zranění a návraty zatím nemají podporovaný zdroj, proto se nezobrazují.'
      : 'Injuries and returns have no supported source yet and are not shown.'}</p>
    <h4>{cs ? 'Časová osa' : 'Timeline'}</h4>
    <label>{cs ? 'Typ' : 'Type'}{' '}
      <select value={kind} onChange={ev => setKind(ev.target.value)}>
        <option value="all">{cs ? 'Vše' : 'All'}</option>
        {CAREER_KINDS.map(k => <option key={k} value={k}>{label(k)}</option>)}
      </select></label>
    {rows.length === 0 ? <p>{cs ? 'Žádné záznamy.' : 'No entries.'}</p>
      : <ol>{rows.map((e, i) => <li key={e.kind + e.source.fingerprint + i}>
        <strong>{label(e.kind)}</strong> · {weekText(e, cs)}
        {detailText(e, cs) && ` · ${detailText(e, cs)}`}
        <br /><small>{sourceText(e, cs)}</small></li>)}</ol>}
  </section>
}
