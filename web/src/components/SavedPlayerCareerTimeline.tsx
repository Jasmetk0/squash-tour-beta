import * as React from 'react'
import { useQuery } from '@tanstack/react-query'

import { getSavedPlayerCareer } from '../api/client'
import { CAREER_KINDS, validSavedPlayerCareer } from '../api/savedPlayerCareer'
import type { CareerEvent } from '../api/savedPlayerCareer'
import { formatApiError } from '../utils/apiErrors'
import { readerPage, readerPageCount, readerSlice, useReaderParams } from './readerUrlState'

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
  if (e.kind === 'retirement' && d.without_tour_entry === true) {
    return cs ? 'bez vstupu na Tour' : 'never entered the Tour'
  }
  return ''
}

function labelSearch(e: CareerEvent): string {
  return [e.kind, e.source.kind, e.source.fingerprint, JSON.stringify(e.detail)].join(' ').toLocaleLowerCase()
}

function sourceText(e: CareerEvent, cs: boolean): string {
  const short = e.source.fingerprint.slice(0, 12)
  return `${cs ? 'Zdroj' : 'Source'}: ${e.source.kind} · ${short}`
}

export function SavedPlayerCareerTimeline({ runId, branchId, savedHead, playerId, cs }: Props): JSX.Element {
  const url = useReaderParams('career', JSON.stringify([runId, branchId, savedHead, playerId]))
  const requested = url.get('asof')
  const kind = url.get('kind', 'all')
  const search = url.get('search')
  const order = url.get('order', 'asc')
  const page = readerPage(url.get('page', '1'))
  const [draft, setDraft] = React.useState(requested)
  React.useEffect(() => { setDraft(requested) }, [requested, runId, branchId, savedHead, playerId])
  const baseline = useQuery({
    queryKey: ['saved-player-career', runId, branchId, savedHead, playerId, 'present'],
    queryFn: () => getSavedPlayerCareer(runId, branchId, playerId),
    retry: false
  })
  const maxOrdinal = baseline.data && validSavedPlayerCareer(baseline.data, { runId, branchId, savedHead, playerId })
    ? baseline.data.as_of_ordinal : null
  const parsed = /^(0|[1-9]\d*)$/.test(requested) ? Number(requested) : NaN
  const badAsOf = requested !== '' && (!Number.isSafeInteger(parsed) || parsed < 0 ||
    (maxOrdinal !== null && parsed > maxOrdinal))
  const asOf = requested === '' ? undefined : parsed
  const query = useQuery({
    queryKey: ['saved-player-career', runId, branchId, savedHead, playerId, asOf],
    queryFn: () => getSavedPlayerCareer(runId, branchId, playerId, asOf),
    enabled: !baseline.isPending && !baseline.error && maxOrdinal !== null && !badAsOf,
    retry: false
  })
  const title = cs ? 'Kariéra: časová osa a milníky' : 'Career: timeline and milestones'
  if (baseline.isPending) {
    return <section aria-label={title}><h3>{title}</h3><p role="status">{cs ? 'Načítám kariéru…' : 'Loading career…'}</p></section>
  }
  if (baseline.error) return <section aria-label={title}><h3>{title}</h3><p role="alert">{formatApiError(baseline.error)}</p></section>
  if (maxOrdinal === null) return <section aria-label={title}><h3>{title}</h3><p role="alert">{cs ? 'Neplatná odpověď kariéry.' : 'Invalid career response.'}</p></section>
  if (badAsOf) return <section aria-label={title}><h3>{title}</h3>
    <p role="alert">{cs ? 'Neplatný nebo budoucí týden. Zobrazení nebylo přepnuto na současnost.' : 'Invalid or future week. The view was not silently changed to the present.'}</p>
    <button type="button" onClick={() => { url.set({ asof: null, page: null }); setDraft('') }}>{cs ? 'Zpět na současnost' : 'Return to present'}</button></section>
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
  if (asOf !== undefined && data.as_of_ordinal !== asOf) return <section aria-label={title}><p role="alert">{cs ? 'Odpověď neodpovídá požadovanému týdnu.' : 'Response does not match requested week.'}</p></section>
  const rows = data.timeline.map((event, index) => ({ event, index }))
    .filter(({ event }) => (kind === 'all' || event.kind === kind) &&
      (labelSearch(event).includes(search.trim().toLocaleLowerCase())))
    .sort((a, b) => {
      const ordinal = (e: CareerEvent) => e.effective_week
        ? e.effective_week.season_index * 10000 + e.effective_week.week : -1
      const diff = ordinal(a.event) - ordinal(b.event)
      return (order === 'desc' ? -diff : diff) || a.index - b.index
    })
  const pages = readerPageCount(rows.length)
  const visible = readerSlice(rows, Math.min(page, pages))
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
      url.set({ asof: draft.trim() === '' ? null : draft.trim(), page: null })
    }}>
      <label>{cs ? 'Zobrazit k týdnu (pořadové číslo)' : 'View as of week (ordinal)'}{' '}
        <input inputMode="numeric" value={draft} placeholder={String(data.as_of_ordinal)}
          onChange={ev => setDraft(ev.target.value)} />
      </label>{' '}
      <button type="submit">{cs ? 'Použít' : 'Apply'}</button>
    </form>
    <p role="status">{cs ? 'Zobrazeno k týdnu č.' : 'Shown as of week no.'} {data.as_of_ordinal}</p>
    {data.retirement_summary && <section aria-label={cs ? 'Souhrn kariéry' : 'Career summary'}>
      <h4>{cs ? 'Souhrn kariéry při odchodu do důchodu' : 'Retirement career summary'}</h4>
      <p>{cs ? 'Konec kariéry' : 'Retired'}: {weekText({ ...data.retirement_summary.source, kind: 'retirement', effective_week: data.retirement_summary.retired_week, detail: {}, source: data.retirement_summary.source } as CareerEvent, cs)}
        {' · '}{cs ? 'Tituly / finále / Edice' : 'Titles / finals / Editions'}: {data.retirement_summary.titles} / {data.retirement_summary.finals} / {data.retirement_summary.editions_played}
        {' · '}{cs ? 'Nejlepší ranking' : 'Career-high rank'}: {data.retirement_summary.career_high_rank ?? '—'}</p>
      {data.retirement_summary.without_turn_pro === true && <p role="note">{cs
        ? 'Výjimka podle Master v87: kariéra skončila, aniž by se hráč kdy stal profesionálem. Nevzniká žádná událost Turn Pro ani zdravotní příčina.'
        : 'Master v87 exception: the career ended without the player ever turning pro. No Turn Pro event or health cause is implied.'}</p>}
      {data.retirement_summary.without_tour_entry === true && <p role="note">{cs
        ? 'Hráč nikdy nevstoupil na Tour (historické pravidlo bez události Turn Pro).'
        : 'The player never entered the Tour (historical rule, which has no Turn Pro event).'}</p>}
      <p><small>{cs ? 'Zdroj' : 'Source'}: {data.retirement_summary.source.kind} · {data.retirement_summary.source.fingerprint.slice(0, 12)}
        {' · '}{cs ? 'Souhrn pokrývá jen zaznamenanou historii; příčina konce kariéry se neodvozuje.' : 'The summary covers recorded history only; no cause of the career ending is inferred.'}</small></p>
    </section>}
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
      <select value={kind} onChange={ev => url.set({ kind: ev.target.value === 'all' ? null : ev.target.value, page: null })}>
        <option value="all">{cs ? 'Vše' : 'All'}</option>
        {CAREER_KINDS.map(k => <option key={k} value={k}>{label(k)}</option>)}
      </select></label>
    {' '}<label>{cs ? 'Hledat v záznamech' : 'Search entries'}{' '}
      <input value={search} onChange={e => url.set({ search: e.target.value, page: null }, true)} /></label>
    {' '}<label>{cs ? 'Pořadí' : 'Order'}{' '}
      <select value={order === 'desc' ? 'desc' : 'asc'} onChange={e => url.set({ order: e.target.value, page: null })}>
        <option value="asc">{cs ? 'Od nejstarších' : 'Oldest first'}</option>
        <option value="desc">{cs ? 'Od nejnovějších' : 'Newest first'}</option>
      </select></label>{' '}
    <button type="button" onClick={() => { url.reset(); setDraft('') }}>{cs ? 'Reset filtrů' : 'Reset filters'}</button>
    <p>{cs ? 'Zobrazené záznamy' : 'Matching entries'}: {rows.length} / {data.timeline.length}</p>
    {rows.length === 0 ? <p>{cs ? 'Žádné záznamy neodpovídají filtrům.' : 'No entries match the filters.'}</p>
      : <ol start={(Math.min(page, pages) - 1) * 20 + 1}>{visible.map(({ event: e, index: i }) => <li key={e.kind + e.source.fingerprint + i}>
        <strong>{label(e.kind)}</strong> · {weekText(e, cs)}
        {detailText(e, cs) && ` · ${detailText(e, cs)}`}
        <br /><small>{sourceText(e, cs)}</small></li>)}</ol>}
    <nav aria-label={cs ? 'Stránkování kariéry' : 'Career pagination'}>
      <button type="button" disabled={page <= 1} onClick={() => url.set({ page: String(page - 1) })}>{cs ? 'Předchozí' : 'Previous'}</button>
      {' '}{cs ? 'Strana' : 'Page'} {Math.min(page, pages)} / {pages}{' '}
      <button type="button" disabled={page >= pages} onClick={() => url.set({ page: String(page + 1) })}>{cs ? 'Další' : 'Next'}</button>
    </nav>
  </section>
}
