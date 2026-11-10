import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  confirmATPCalendarReference, getATPCalendarReferenceCatalog, getATPCalendarReferenceYear,
  previewATPCalendarReference,
} from '../../api/client'
import {
  ATP_CALENDAR_REFERENCE_SETUP_ID, reviewedATPCalendarReference,
} from '../../api/atpCalendarReferencePackages'
import type { ATPCalendarReferenceCatalog } from '../../api/atpCalendarReferencePackages'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'
import { ATPSavedRunWeekDetails } from './ATPSavedRunWeekDetails'
import { ATPSourceApplyPage } from './ATPSourceApplyPage'

const ATP_REFERENCE_YEARS = Array.from({length:37},(_,i)=>1990+i)

/** Compact only genuinely consecutive source-dated historical years.
 * The caller must use the actual canonical year partition, never assume it. */
const datedYearRanges=(years:readonly number[]):string=>{
  if(!years.length)return '—'
  const sorted=[...years].sort((a,b)=>a-b)
  const ranges:string[]=[]
  let first=sorted[0],last=first
  for(const year of sorted.slice(1)){
    if(year===last+1){last=year;continue}
    ranges.push(first===last?String(first):`${first}–${last}`)
    first=last=year
  }
  ranges.push(first===last?String(first):`${first}–${last}`)
  return ranges.join(', ')
}

function CalendarYearDetails({ catalog, sourceReady }: {
  catalog: ATPCalendarReferenceCatalog | undefined
  sourceReady: boolean
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [sourceYear, setSourceYear] = useState(2026)
  const calendarFingerprint=catalog?.children.find(
    child=>child.package_type==='Calendar'
  )?.source_fingerprint??''
  const yearView=useQuery({
    queryKey:['atp-calendar-year',sourceYear,calendarFingerprint],
    queryFn:()=>getATPCalendarReferenceYear(sourceYear,calendarFingerprint),
    enabled:sourceReady&&Boolean(calendarFingerprint),retry:false
  })
  return (
    <section className="package-apply-step">
      <h3>{cs?'Historický přehled datumů a ISO týdnů':'Historical exact dates and ISO weeks'}</h3>
      <label>{cs?'Ročník':'ATP season'}
        <select aria-label="ATP Calendar Year" value={sourceYear}
          onChange={e=>setSourceYear(Number(e.target.value))}>
          {[...ATP_REFERENCE_YEARS].reverse().map(y=>
            <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
      {yearView.isPending&&<p role="status">{cs?'Načítám termíny…':'Loading dated events…'}</p>}
      {yearView.isError&&<p role="alert" className="error">{formatApiError(yearView.error)}
        <button type="button" onClick={()=>{void yearView.refetch()}}>
          {cs?'Znovu načíst':'Retry'}
        </button></p>}
      {yearView.data&&<>
        <p className="status">
          {cs?'Doložené termíny':'Sourced dates'}: {yearView.data.coverage.dated_series_count}
          {' / '}{yearView.data.coverage.roster_series_count}
          {' · '}{yearView.data.coverage.date_coverage_state}
          {' · '}{cs?'Pouze reference':'Reference only'}
        </p>
        {yearView.data.events.length>0?
          <div className="table-responsive">
            <table><thead><tr>
              <th>{cs?'Turnajová série':'Series'}</th>
              <th>{cs?'Od':'From'}</th><th>{cs?'Do':'To'}</th>
              <th>{cs?'ISO týden začátku':'Start ISO week'}</th>
              <th>{cs?'ISO týden konce':'End ISO week'}</th>
              <th>{cs?'Kategorie':'Category'}</th>
              <th>{cs?'Zdroj':'Source'}</th>
            </tr></thead><tbody>{yearView.data.events.map(item=>
              <tr key={item.series_id}>
                <td>{item.series_id}</td>
                <td>{item.start_date}</td><td>{item.end_date}</td>
                <td>{item.start_year_week.iso_year}/W{String(item.start_year_week.iso_week).padStart(2,'0')}</td>
                <td>{item.end_year_week.iso_year}/W{String(item.end_year_week.iso_week).padStart(2,'0')}</td>
                <td>{item.category_id}</td>
                <td><a href={item.source_url} target="_blank" rel="noopener noreferrer">
                  {cs?'ATP zdroj':'ATP source'}</a></td>
              </tr>)}</tbody></table>
          </div>:
          <p role="status">{cs
            ? 'Pro tento rok nejsou jednotlivá data turnajů ještě ověřená. Neznamená to, že se turnaje nekonaly.'
            : 'No individual event dates have been verified for this year. It does not imply that events were not held.'}</p>}
        {yearView.data.coverage.undated_series_ids.length>0&&
          <details><summary>{cs?'Série bez doloženého data':'Series lacking exact-date evidence'}
            {' ('}{yearView.data.coverage.undated_series_ids.length}{')'}</summary>
            <p>{yearView.data.coverage.undated_series_ids.join(', ')}</p>
          </details>}
      </>}
    </section>
  )
}

export function ATPCalendarReferenceApplyPage(): JSX.Element {
  return <ATPSourceApplyPage
    queryPrefix="atp-calendar-reference"
    setupId={ATP_CALENDAR_REFERENCE_SETUP_ID}
    title={{cs: 'ATP Tour 1990–2026 – referenční kalendář', en: 'ATP Tour 1990–2026 – reference Calendar'}}
    subtitle={{
      cs: 'Historické Category + Series + Calendar v jednom Setup. Termíny jednotlivých ročníků vycházejí z archivů ATP; chybějící data se nedopočítávají odhadem. Rok 2026 zůstává předběžný. Nejde o hratelný kalendář pro squash.',
      en: 'Historical Category + Series + Calendar in one Setup. Season dates come from ATP archives; missing dates are never guessed. Year 2026 remains provisional. This is not a playable squash Calendar.',
    }}
    getCatalog={getATPCalendarReferenceCatalog}
    getPreview={previewATPCalendarReference}
    confirmReference={confirmATPCalendarReference}
    isReviewed={reviewedATPCalendarReference}
    renderSourceSummary={(catalog, cs) => (
        <p className="status">{cs
          ? `Datované ročníky: ${datedYearRanges(catalog.dated_years)} · dosud nedatovaných: ${catalog.undated_years.length}. Rok 2026 je předběžný. ISO week ≠ Run Week.`
          : `Dated seasons: ${datedYearRanges(catalog.dated_years)} · undated seasons: ${catalog.undated_years.length}. 2026 is provisional. ISO week ≠ Run Week.`}</p>
    )}
    renderSourceDetails={(catalog, sourceReady) => <CalendarYearDetails catalog={catalog} sourceReady={sourceReady} />}
    renderSavedTargetDetails={(runId, branchId, revisionId) =>
      <ATPSavedRunWeekDetails key={JSON.stringify([runId, branchId, revisionId])}
        runId={runId} branchId={branchId} revisionId={revisionId}
        years={ATP_REFERENCE_YEARS} />}
  />
}
