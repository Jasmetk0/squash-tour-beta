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
  const kindValue = url.get('kind', 'all')
  const kind = kindValue === 'all' || CAREER_KINDS.some(k => k === kindValue) ? kindValue : 'all'
  const search = url.get('search')
  const seasonFilter=url.get('season','all')
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
  const parsed = /^(0|[1-9]\d*)$/.test(requested) ? Number(requested) : Number.NaN
  const badAsOf = requested !== '' && (!Number.isSafeInteger(parsed) || parsed < 0 ||
    (maxOrdinal !== null && parsed > maxOrdinal))
  const asOf = requested === '' ? undefined : parsed
  const query = useQuery({
    queryKey: ['saved-player-career', runId, branchId, savedHead, playerId, asOf],
    queryFn: () => getSavedPlayerCareer(runId, branchId, playerId, asOf),
    enabled: asOf !== undefined && !baseline.isPending && !baseline.error && maxOrdinal !== null && !badAsOf,
    retry: false
  })
  const title = cs ? 'Kariéra: časová osa a milníky' : 'Career: timeline and milestones'
  if (baseline.isPending || baseline.isFetching) {
    return <section aria-label={title} data-run-navigation-readonly><h3>{title}</h3><p role="status">{cs ? 'Načítám kariéru…' : 'Loading career…'}</p></section>
  }
  if (baseline.error) return <section aria-label={title}><h3>{title}</h3><p role="status">{cs ? 'Kariérní osa není pro tuto revizi dostupná: ' : 'Career timeline is unavailable for this revision: '}{formatApiError(baseline.error)}</p></section>
  if (maxOrdinal === null) return <section aria-label={title}><h3>{title}</h3><p role="alert">{cs
    ? 'Odpověď neodpovídá vybrané Branch, uložené revizi nebo hráči a nebyla zobrazena.'
    : 'The response does not match the selected Branch, Saved revision or player and was not displayed.'}</p></section>
  if (badAsOf) return <section aria-label={title}><h3>{title}</h3>
    <p role="alert">{cs ? 'Neplatný nebo budoucí týden. Zobrazení nebylo přepnuto na současnost.' : 'Invalid or future week. The view was not silently changed to the present.'}</p>
    <button type="button" onClick={() => { url.set({ asof: null, page: null, seasonpage: null, season: null }); setDraft('') }}>{cs ? 'Zpět na současnost' : 'Return to present'}</button></section>
  if (asOf !== undefined && (query.isPending || query.isFetching)) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="status">{cs ? 'Načítám kariéru…' : 'Loading career…'}</p></section>
  }
  if (asOf !== undefined && query.error) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="status">{cs ? 'Kariérní osa není pro tuto revizi dostupná: ' : 'Career timeline is unavailable for this revision: '}
        {formatApiError(query.error)}</p></section>
  }
  const data = asOf === undefined ? baseline.data : query.data
  if (!validSavedPlayerCareer(data, { runId, branchId, savedHead, playerId })) {
    return <section aria-label={title}><h3>{title}</h3>
      <p role="alert">{cs
        ? 'Odpověď neodpovídá vybrané Branch, uložené revizi nebo hráči a nebyla zobrazena.'
        : 'The response does not match the selected Branch, Saved revision or player and was not displayed.'}</p></section>
  }
  if (asOf !== undefined && data.as_of_ordinal !== asOf) return <section aria-label={title}><p role="alert">{cs ? 'Odpověď neodpovídá požadovanému týdnu.' : 'Response does not match requested week.'}</p></section>
  const label = (k: string) => (LABEL[k] ?? [k, k])[cs ? 0 : 1]
  const rows = data.timeline.map((event, index) => ({ event, index }))
    .filter(({ event }) => (kind === 'all' || event.kind === kind) &&
      (seasonFilter==='all'||(event.effective_week!==null
        &&String(event.effective_week.season_index)===seasonFilter)) &&
      [label(event.kind), weekText(event, cs), detailText(event, cs),
        sourceText(event, cs), labelSearch(event)].join(' ')
        .toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
    .sort((a, b) => {
      const aw = a.event.effective_week
      const bw = b.event.effective_week
      const diff = aw === null ? (bw === null ? 0 : -1)
        : bw === null ? 1
          : (aw.season_index - bw.season_index || aw.week - bw.week)
      return (order === 'desc' ? -diff : diff) || a.index - b.index
    })
  const timelineSeasons=[...new Set(data.timeline.flatMap(event=>event.effective_week?[event.effective_week.season_index]:[]))].sort((a,b)=>b-a)
  const pages = readerPageCount(rows.length)
  const current = Math.min(page, pages)
  const visible = readerSlice(rows, current)
  const o = data.overview
  // These are only new personal records, not weekly ranking snapshots.
  // Use event order rather than fabricating a W52/W61 elapsed-time axis.
  const records=data.timeline.filter(e=>e.kind==='career_high_ranking')
    .sort((a,b)=>(a.effective_week?.season_index??-1)-(b.effective_week?.season_index??-1)
      ||(a.effective_week?.week??0)-(b.effective_week?.week??0))
  const validRecords=records.every((e,i)=>e.effective_week!==null
    &&e.source.kind==='published_ranking'
    &&typeof e.detail.rank==='number'&&Number.isSafeInteger(e.detail.rank)&&e.detail.rank>=1
    &&(i===0||(e.detail.rank as number)<(records[i-1].detail.rank as number)))
    &&(records.length===0||records[records.length-1].detail.rank===o.career_high_rank)
  const recent=validRecords?records.slice(-20):[]
  const worst=Math.max(2,...recent.map(e=>e.detail.rank as number))
  const chartTitle=cs?'Zaznamenaná rankingová maxima':'Recorded ranking highs'
  // Season buckets describe recorded edition results, not calendar coverage.
  // Never synthesize empty years, a season-end ranking, or a season best
  // from a list containing only new lifetime personal records.
  type SeasonRow={season:number;editions:number;titles:number;runnerUps:number;newHigh:number|null}
  const seasons=new Map<number,SeasonRow>()
  const getSeason=(season:number)=>{
    let row=seasons.get(season)
    if(!row){
      row={season,editions:0,titles:0,runnerUps:0,newHigh:null}
      seasons.set(season,row)
    }
    return row
  }
  const editionIds=new Set<string>()
  let validEditions=true
  for(const event of data.timeline){
    if(event.kind!=='edition_result')continue
    const week=event.effective_week
    const id=event.detail.edition_id
    const stage=event.detail.reached_stage
    if(!week||!Number.isSafeInteger(week.season_index)
      ||event.source.kind!=='played_edition'||typeof id!=='string'||!id.trim()
      ||event.source.edition_id!==id||editionIds.has(id)
      ||typeof stage!=='string'||!stage.trim()){
      validEditions=false
      break
    }
    editionIds.add(id)
    const row=getSeason(week.season_index)
    row.editions++
    if(stage==='champion')row.titles++
    if(stage==='finalist')row.runnerUps++
  }
  const totals=[...seasons.values()].reduce((sum,row)=>({
    editions:sum.editions+row.editions,titles:sum.titles+row.titles,
    runnerUps:sum.runnerUps+row.runnerUps
  }),{editions:0,titles:0,runnerUps:0})
  validEditions=validEditions&&totals.editions===o.editions_played
    &&totals.titles===o.titles&&totals.runnerUps===o.finals
  if(validEditions&&validRecords){
    for(const event of records){
      const row=getSeason(event.effective_week!.season_index)
      row.newHigh=event.detail.rank as number
    }
  }
  const seasonRows=validEditions?[...seasons.values()].sort((a,b)=>b.season-a.season):[]
  const seasonPages=readerPageCount(seasonRows.length)
  const seasonPage=Math.min(readerPage(url.get('seasonpage','1')),seasonPages)
  const seasonTitle=cs?'Evidovaná kariéra podle sezon':'Recorded career by season'
  return <section aria-label={title} data-run-navigation-readonly>
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
      url.set({ asof: draft.trim() === '' ? null : draft.trim(), page: null, seasonpage: null, season: null })
    }}>
      <label>{cs ? 'Zobrazit k týdnu (pořadové číslo)' : 'View as of week (ordinal)'}{' '}
        <input inputMode="numeric" value={draft} placeholder={String(data.as_of_ordinal)}
          onChange={ev => setDraft(ev.target.value)} />
      </label>{' '}
      <button type="submit">{cs ? 'Použít' : 'Apply'}</button>
    </form>
    <p role="status">{cs ? 'Zobrazeno k týdnu č.' : 'Shown as of week no.'} {data.as_of_ordinal}</p>
    {asOf!==undefined&&<button type="button" onClick={()=>{url.set({asof:null,page:null,seasonpage:null,season:null});setDraft('')}}>
      {cs?'Zpět na současnost':'Return to present'}</button>}
    <section aria-label={chartTitle}>
      <h4>{chartTitle}</h4>
      <p className="status">{cs?
        'Pouze nová doložená osobní maxima. Vodorovná osa je pořadí událostí, nikoli čas; nejde o týdenní vývoj rankingu.':
        'Recorded personal bests only. Horizontal spacing is event order, not elapsed time; this is not weekly ranking history.'}</p>
      {recent.length>0?<><p>{cs?'Zobrazená maxima':'Displayed records'}: {recent.length}/{records.length}</p>
        <svg viewBox="0 0 640 180" role="img" aria-label={cs?'Graf osobních rankingových maxim':'Personal ranking records chart'}
          style={{display:'block',width:'100%',maxWidth:640,height:'auto'}}>
          <g fill="currentColor" fontSize="12">
            <text x="4" y="20">#1</text>
            <text x="4" y="152">#{worst}</text>
          </g>
          <path d="M 48 16 V 148 H 616" stroke="currentColor" fill="none" opacity="0.45"/>
          {recent.map((event,i)=>{
            const rank=event.detail.rank as number
            const x=recent.length===1?332:56+i*552/(recent.length-1)
            const y=16+(rank-1)*132/(worst-1)
            return <circle key={event.source.fingerprint+':'+i} cx={x} cy={y} r={5} fill="currentColor">
              <title>{weekText(event,cs)} · #{rank}</title>
            </circle>
          })}
          <text x="332" y="174" textAnchor="middle" fontSize="12" fill="currentColor">
            {cs?'Pořadí záznamů':'Record order'}
          </text>
        </svg>
        <details><summary>{cs?'Hodnoty a zdroje grafu':'Chart values and sources'}</summary>
          <div className="table-responsive"><table aria-label={cs?'Hodnoty rankingových maxim':'Ranking record values'}>
            <thead><tr><th>{cs?'Týden':'Week'}</th><th>Rank</th><th>{cs?'Zdroj':'Source'}</th></tr></thead>
            <tbody>{recent.map((event,i)=><tr key={event.source.fingerprint+':'+i}>
              <td>{weekText(event,cs)}</td><td>#{String(event.detail.rank)}</td><td>{sourceText(event,cs)}</td>
            </tr>)}</tbody>
          </table></div>
        </details>
      </>:<p role="status">{cs?'Ověřená rankingová maxima pro graf nejsou dostupná.':
        'Verified ranking records for the chart are unavailable.'}</p>}
    </section>
    <section aria-label={seasonTitle}>
      <h4>{seasonTitle}</h4>
      <p className="status">{cs?
        'Jen sezony s doloženými výsledky nebo novým osobním maximem do vybraného týdne. Nejde o úplné sezonní statistiky ani konečný ranking.':
        'Only seasons with recorded results or a new personal best through the selected week. Not complete season statistics or season-end rankings.'}</p>
      {seasonRows.length>0?<><div className="table-responsive">
        <table aria-label={seasonTitle}>
          <thead><tr><th>{cs?'Sezona Runu':'Run season'}</th>
            <th>{cs?'Evidované edice':'Recorded Editions'}</th>
            <th>{cs?'Tituly':'Titles'}</th>
            <th>{cs?'Prohraná finále':'Runner-up finishes'}</th>
            <th>{cs?'Nové osobní maximum':'New personal best'}</th><th>{cs?'Záznamy':'Entries'}</th></tr></thead>
          <tbody>{readerSlice(seasonRows,seasonPage).map(row=><tr key={row.season}>
            <th scope="row">{row.season+1}</th><td>{row.editions}</td><td>{row.titles}</td>
            <td>{row.runnerUps}</td><td>{row.newHigh===null?'—':'#'+row.newHigh}</td>
            <td><button type="button" onClick={()=>url.set({season:String(row.season),kind:null,search:null,page:null})}>
              {cs?'Záznamy sezony':'Season entries'} {row.season+1}</button></td>
          </tr>)}</tbody>
        </table></div>
        <p className="status">{cs?'Nula označuje počet evidovaných výsledků, ne důkaz neúčasti. Pomlčka znamená, že nové ověřené osobní maximum není dostupné.':
          'Zero counts recorded results, not proof of non-participation. A dash means no verified new personal best is available.'}</p>
        {seasonPages>1&&<nav aria-label={cs?'Stránkování sezon':'Career season pagination'}>
          <button type="button" disabled={seasonPage<=1} onClick={()=>url.set({seasonpage:String(seasonPage-1)})}>
            {cs?'Předchozí':'Previous'}</button>
          {' '}{cs?'Strana':'Page'} {seasonPage} / {seasonPages}{' '}
          <button type="button" disabled={seasonPage>=seasonPages} onClick={()=>url.set({seasonpage:String(seasonPage+1)})}>
            {cs?'Další':'Next'}</button>
        </nav>}
      </>:<p role="status">{cs?'Ověřený sezonní souhrn není dostupný.':
        'Verified season summary is unavailable.'}</p>}
    </section>
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
      : <ul className="run-home-feed">{data.milestones.map((m, i) => <li key={m.kind + i}>
        <strong>{label(m.kind)}</strong> · {weekText(m, cs)}
        {detailText(m, cs) && ` · ${detailText(m, cs)}`}
        <br /><small>{sourceText(m, cs)}</small></li>)}</ul>}
    <p>{cs ? 'Zranění a návraty zatím nemají podporovaný zdroj, proto se nezobrazují.'
      : 'Injuries and returns have no supported source yet and are not shown.'}</p>
    <h4>{cs ? 'Časová osa' : 'Timeline'}</h4>
    <label>{cs?'Sezona záznamů':'Entry season'}{' '}
      <select value={seasonFilter} onChange={ev=>url.set({season:ev.target.value==='all'?null:ev.target.value,page:null})}>
        <option value="all">{cs?'Všechny sezony':'All seasons'}</option>
        {seasonFilter!=='all'&&!timelineSeasons.some(s=>String(s)===seasonFilter)&&
          <option value={seasonFilter}>{cs?'Nedostupná sezona':'Unavailable season'}</option>}
        {timelineSeasons.map(s=><option key={s} value={String(s)}>{cs?'Sezona':'Season'} {s+1}</option>)}
      </select>
    </label>
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
      : <ol start={(current - 1) * 20 + 1}>{visible.map(({ event: e, index: i }) => <li key={e.kind + e.source.fingerprint + i}>
        <strong>{label(e.kind)}</strong> · {weekText(e, cs)}
        {detailText(e, cs) && ` · ${detailText(e, cs)}`}
        <br /><small>{sourceText(e, cs)}</small></li>)}</ol>}
    <nav aria-label={cs ? 'Stránkování kariéry' : 'Career pagination'}>
      <button type="button" disabled={current <= 1} onClick={() => url.set({ page: String(current - 1) })}>{cs ? 'Předchozí' : 'Previous'}</button>
      {' '}{cs ? 'Strana' : 'Page'} {current} / {pages}{' '}
      <button type="button" disabled={current >= pages} onClick={() => url.set({ page: String(current + 1) })}>{cs ? 'Další' : 'Next'}</button>
    </nav>
  </section>
}
