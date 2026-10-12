import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { RunWorldCountry, WorldRatingKey } from './runWorldReadModel'
import { worldRatingKeys } from './runWorldReadModel'
import type {
  CountryRatingEvidence, RunWorldCountryHistory
} from './runWorldCountryHistory'

type Props={
  history:RunWorldCountryHistory;country:RunWorldCountry
  tab:'population'|'ratings';cs:boolean;language:string
  yearLink:(year:number)=>string
}
const names:Record<WorldRatingKey,{cs:string;en:string}>={
  squash_popularity:{cs:'Popularita squashe',en:'Squash Popularity'},
  squash_access:{cs:'Dostupnost squashe',en:'Squash Access'},
  development_quality:{cs:'Kvalita rozvoje',en:'Development Quality'},
  competition_quality:{cs:'Kvalita soutěží',en:'Competition Quality'},
  elite_support:{cs:'Podpora elity',en:'Elite Support'},
  squash_tradition:{cs:'Tradice squashe',en:'Squash Tradition'}
}
function count(value:number,language:string):string {
  return new Intl.NumberFormat(language==='cs'?'cs-CZ':'en-US').format(value)
}
function label(method:string,cs:boolean):string {
  switch(method){
    case 'exact':return cs?'Přesný údaj':'Exact authored value'
    case 'nearest':return cs?'Nejbližší doložený rok':'Nearest authored year'
    case 'default':return cs?'Výchozí hodnota 2020':'Default value (2020)'
    case 'legacy':return cs?'Starší údaj bez roku':'Legacy value (year unknown)'
    default:return cs?'Hodnota chybí':'Missing'
  }
}
function EvidenceDetails({value,cs}:{value:CountryRatingEvidence;cs:boolean}):JSX.Element {
  return <details className="run-world-evidence">
    <summary>{cs?'Podrobnosti původu hodnoty':'Value provenance details'}</summary>
    <dl>
      <dt>{cs?'Metoda':'Method'}</dt><dd>{value.method??'—'}</dd>
      <dt>{cs?'Jistota':'Confidence'}</dt><dd>{value.confidence??'—'}</dd>
      <dt>{cs?'Podkladové roky':'Anchor years'}</dt><dd>{value.anchorYears.join(', ')||'—'}</dd>
      <dt>{cs?'Zdrojová ID':'Source IDs'}</dt><dd>{value.sourceIds.join(', ')||'—'}</dd>
      <dt>{cs?'ID pozorování':'Observation IDs'}</dt><dd>{value.observationIds.join(', ')||'—'}</dd>
      <dt>{cs?'Zdůvodnění':'Rationale'}</dt><dd>{value.rationale??'—'}</dd>
    </dl>
  </details>
}
function AnchorBars({points,max,link,cs}:{points:{year:number;value:number}[];max:number;link:(year:number)=>string;cs:boolean}):JSX.Element {
  return <div className="run-world-anchor-chart" aria-label={cs?'Graf pouze doložených roků':'Chart of authored years only'}>
    {points.map(p=><Link key={p.year} to={link(p.year)} title={p.year+' · '+p.value}
      aria-label={(cs?'Zobrazit rok ':'View year ')+p.year}>
      <span className="run-world-anchor-bar" style={{height:(Math.max(8,100*p.value/max))+'%'}}/>
      <small>{p.year}</small>
    </Link>)}
  </div>
}
export function RunWorldCountryHistoryPanel({history,country,tab,cs,language,yearLink}:Props):JSX.Element {
  const [field,setField]=useState<WorldRatingKey>('squash_popularity')
  if(tab==='population'){
    const exact=history.populationAnchors.filter(p=>p.value!==null).map(p=>({year:p.year,value:p.value!}))
    const max=Math.max(1,...exact.map(p=>p.value))
    const selected=history.selectedPopulation
    return <section className="section-subtle" aria-label="Country population history">
      <h4>{cs?'Historie populace':'Population history'}</h4>
      <p className="run-world-selected-value">{cs?'Zvolený rok':'Selected year'}: <strong>{history.selectedYear}</strong> ·
        {' '}{selected.value===null?'—':count(selected.value,language)} · {label(selected.kind,cs)}
        {selected.sourceYear===null?'':' ('+selected.sourceYear+')'}
      </p>
      {selected.kind!=='exact'&&<p role="status">{cs
        ? 'Zobrazená hodnota je fallback, ne přesná populace zvoleného roku. Nepoužívá se jako historicky doložený bod grafu.'
        : 'Displayed value is a fallback, not exact population for the selected year. It is not plotted as an authored historical point.'}</p>}
      {exact.length>0?<>
        <p className="status">{cs?'Graf obsahuje pouze roky s explicitní číselnou hodnotou. Kliknutí změní rok náhledu.':'Only explicit numeric year anchors appear in the chart. Click a bar to inspect its year.'}</p>
        <AnchorBars points={exact} max={max} link={yearLink} cs={cs}/>
        <div className="table-responsive">
          <table aria-label="Authored population timeline"><thead><tr>
            <th>{cs?'Rok':'Year'}</th><th>{cs?'Uložená populace':'Authored population'}</th>
            <th>{cs?'Stav':'Status'}</th>
          </tr></thead><tbody>{history.populationAnchors.map(p=><tr key={p.year}>
            <td><Link aria-current={p.year===history.selectedYear?'page':undefined} to={yearLink(p.year)}>{p.year}</Link></td>
            <td>{p.value===null?'—':count(p.value,language)}</td>
            <td>{p.value===null?(cs?'Výslovně chybí':'Explicitly missing'):(cs?'Zadaná hodnota':'Authored')}</td>
          </tr>)}</tbody></table>
        </div>
      </>:<p role="status">{cs?'Tento Run nemá pro zemi uloženou populační časovou řadu. Graf se nevytváří.':'No authored population timeline exists for this country in the Run. No chart is fabricated.'}</p>}
      <p className="status">{cs?'Výchozí údaj (rok 2020)':'Default (2020)'}: {history.defaultPopulation===null?'—':count(history.defaultPopulation,language)}
        {' '}· {cs?'Starší scalar bez časového určení':'Legacy scalar, year unknown'}: {history.legacyPopulation===null?'—':count(history.legacyPopulation,language)}</p>
      <p className="status">{cs?'Pouze pro čtení. Změny zemí vyžadují samostatně schválený Runový editor a ruční Save.':'Read only. Changes require an explicitly approved Run-owned editor and separate manual Save.'}</p>
    </section>
  }
  const anchors=history.ratingAnchors
  const points=anchors.map(a=>({year:a.year,value:a.ratings[field].value}))
  const max=Math.max(1,...points.map(p=>p.value))
  const nearest=history.selectedRatingSourceYear===null?null:anchors.find(a=>a.year===history.selectedRatingSourceYear)
  return <section className="section-subtle" aria-label="Country rating history">
    <h4>{cs?'Historie šesti ratingů':'History of six country ratings'}</h4>
    <p>{cs?'Škála':'Scale'}: 1–{country.ratingScale}. {cs?'Zvolený rok':'Selected year'}: {history.selectedYear}
      {nearest && history.selectedYear!==nearest.year && <> · {cs?'Nejbližší doložený rok':'Nearest authored year'}: <strong>{nearest.year}</strong></>}
    </p>
    <div className="table-responsive"><table aria-label="Country rating snapshot"><thead><tr>
      <th>{cs?'Atribut':'Attribute'}</th><th>{cs?'Hodnota':'Value'}</th>
      <th>{cs?'Původ':'Provenance'}</th>
    </tr></thead><tbody>{worldRatingKeys.map(key=><tr key={key}>
      <td>{names[key][cs?'cs':'en']}</td><td>{country.ratings[key].value??'—'}</td>
      <td>{country.ratings[key].provenance}{country.ratings[key].sourceYear===null?'':' · '+country.ratings[key].sourceYear}
        {nearest && <EvidenceDetails value={nearest.ratings[key]} cs={cs}/>}
      </td>
    </tr>)}</tbody></table></div>
    {anchors.length>0?<>
      <p className="status">{cs?'Historicky doložených roků':'Authored rating years'}: {anchors.length}.
        {' '}{cs?'Roky mimo uloženou historii se nevydávají za nové doložené body.':'Unstored years are not represented as new authored rating observations.'}</p>
      <label>{cs?'Graf atributu':'Rating trend field'}
        <select aria-label="Country rating trend field" value={field}
          onChange={e=>setField(e.target.value as WorldRatingKey)}>
          {worldRatingKeys.map(key=><option key={key} value={key}>{names[key][cs?'cs':'en']}</option>)}
        </select>
      </label>
      <AnchorBars points={points} max={max} link={yearLink} cs={cs}/>
      <div className="table-responsive"><table aria-label="Authored country rating years"><thead><tr>
        <th>{cs?'Rok':'Year'}</th><th>{names[field][cs?'cs':'en']}</th>
        <th>{cs?'Metoda a jistota':'Method / confidence'}</th>
        <th>{cs?'Územní provenance':'Historical territory'}</th>
      </tr></thead><tbody>{anchors.map(a=><tr key={a.year}>
        <td><Link aria-current={a.year===history.selectedYear?'page':undefined} to={yearLink(a.year)}>{a.year}</Link></td>
        <td>{a.ratings[field].value}</td>
        <td>{a.ratings[field].method??'—'} / {a.ratings[field].confidence??'—'}
          <EvidenceDetails value={a.ratings[field]} cs={cs}/></td>
        <td>{a.historicalEntity??'—'} · {a.territoryMappingNote??'—'}</td>
      </tr>)}</tbody></table></div>
      <p className="status">{cs?'Referenční rok':'Reference year'}: {history.ratingReferenceYear??'—'} ·
        {' '}{cs?'Datová uzávěrka':'Data cutoff'}: {history.ratingDataCutoff??'—'}</p>
    </>:<p role="status">{cs
      ? 'Tento Run nemá pro zemi evidenčně doloženou časovou řadu ratingů. Zobrazené scalar ratingy nejsou historickým grafem.'
      : 'No source-evidenced rating timeline exists in this Run. Legacy scalar ratings cannot produce an historical chart.'}</p>}
  </section>
}