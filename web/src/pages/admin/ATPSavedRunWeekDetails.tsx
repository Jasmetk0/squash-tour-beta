import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getSavedATPRunWeekPreview } from '../../api/client'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'

const labelWeek = (week: number) => `W${String(week).padStart(2, '0')}`
const labelYearWeek = (week: {calendar_year: number; year_week: number}) =>
  `${week.calendar_year}/${labelWeek(week.year_week)}`
const labelRunWeek = (week: Parameters<typeof labelYearWeek>[0] & {
  season_index: number; season_week: number
}) => `${labelYearWeek(week)} (S${week.season_index + 1}/${labelWeek(week.season_week)})`

export function ATPSavedRunWeekDetails({runId, branchId, revisionId, years}: {
  runId: string; branchId: string; revisionId: string; years: readonly number[]
}): JSX.Element {
  const {language} = useLanguage()
  const cs = language === 'cs'
  const [year, setYear] = useState(years[years.length - 1])
  const [requested, setRequested] = useState<string|null>(null)
  const [search,setSearch]=useState('')
  const [category,setCategory]=useState('')
  const [reviewOnly,setReviewOnly]=useState(false)
  const requestScope=JSON.stringify([runId,branchId,revisionId,year])
  const active=requested===requestScope
  const preview = useQuery({
    queryKey: ['atp-saved-run-week-preview', runId, branchId, revisionId, year],
    queryFn: () => getSavedATPRunWeekPreview(runId, branchId, revisionId, year),
    enabled: false,
    retry: false,
  })
  const result = active && preview.isSuccess && !preview.isFetching ? preview.data : undefined
  const bindings = result?.source_tour_bindings.selected_occurrences
  const allRows=result?[...result.events,...result.outside_horizon]:[]
  const categoryOptions=bindings?[...new Set(allRows.map(row=>bindings[row.source_identity].historical_category_label))].sort():[]
  const needsReview=(row:{review_flags:string[];run_weeks?:unknown[]})=>
    row.review_flags.length>0||(row.run_weeks?.length??0)>=3
  const reviewCount=result?.events.filter(needsReview).length??0
  const term=search.trim().toLocaleLowerCase()
  const matches=(row:typeof allRows[number])=>{
    const binding=bindings?.[row.source_identity]
    return Boolean(binding&&(!category||binding.historical_category_label===category)
      &&[binding.series_name,binding.historical_category_label,row.source_identity,
        row.source_start_date,row.source_end_date].some(value=>value.toLocaleLowerCase().includes(term))
      &&(!reviewOnly||('run_weeks' in row&&needsReview(row))))
  }
  const shown=result?.events.filter(matches)??[]
  const outside=result?.outside_horizon.filter(matches)??[]
  const chronological = <T extends {source_start_date: string}>(rows: T[]) =>
    [...rows].sort((a,b) => a.source_start_date.localeCompare(b.source_start_date))

  return <section className="package-apply-step">
    <h3>{cs ? 'ATP kalendář v týdnech Runu (W52)' : 'ATP calendar in Run weeks (W52)'}</h3>
    <p>{cs
      ? 'Nejprve přidej a ulož ATP Setup do vybrané větve. Náhled pak načte uložené termíny pro kontrolu před plánováním zápasů.'
      : 'First apply and save the ATP Setup to the selected branch. Then preview the Saved dates before scheduling matches.'}</p>
    <label>{cs ? 'ATP ročník pro Run' : 'ATP season for this Run'}
      <select value={year} onChange={event => {
        setYear(Number(event.target.value)); setRequested(null); setSearch(''); setCategory(''); setReviewOnly(false)
      }}>
        {[...years].reverse().map(value => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
    <button type="button" disabled={preview.isFetching} onClick={() => {
      setRequested(requestScope); void preview.refetch()
    }}>{cs ? 'Načíst týdny z uloženého ATP balíčku' : 'Preview weeks from the Saved ATP Package'}</button>
    {preview.isFetching && <p role="status">{cs ? 'Počítám týdny Runu…' : 'Mapping Run weeks…'}</p>}
    {active && preview.isError && <p role="alert" className="error">{formatApiError(preview.error)}</p>}
    {result && bindings && <>
      <p className="status">{cs ? 'V rozsahu Runu' : 'Within Run horizon'}: {result.events.length}
        {' · '}{cs ? 'Mimo rozsah' : 'Outside Run horizon'}: {result.outside_horizon.length}
        {year === 2026 && (cs ? ' · Předběžný ročník' : ' · Provisional season')}</p>
      <section aria-label={cs?'Kontrola referenčního mapování':'Reference mapping review'}>
        <h4>{cs?'Stav referenčních podkladů':'Reference evidence status'}</h4>
        <div className="grid">
          <div className="section-subtle"><p>{cs?'Ověřené zdrojové termíny v náhledu':'Verified source dates in preview'}</p>
            <h3>{allRows.length}</h3></div>
          <div className="section-subtle"><p>{cs?'Mapováno do rozsahu Runu':'Mapped inside Run horizon'}</p>
            <h3>{result.events.length}</h3></div>
          <div className="section-subtle"><p>{cs?'Příznaky k prověření v rozsahu':'Review flags inside horizon'}</p>
            <h3>{reviewCount}</h3></div>
        </div>
        <p role="note">{cs?
          'Jde o náhled uložené reference, nikoli import sportovních profilů, potvrzený rozpis zápasů nebo důkaz hratelnosti. Počet bez příznaku neznamená schválení.':
          'This is a Saved reference preview, not sporting profile import, a confirmed match schedule or proof of playability. No review flag does not mean approval.'}</p>
        <p>{cs?'Sportovní profily, kvalifikace, testy a skutečná hratelnost: tento zdroj neposuzuje.':
          'Sporting profiles, qualification, tests and actual playability: not assessed by this source.'}</p>
        <label>{cs?'Hledat turnaj v náhledu':'Search preview tournaments'}{' '}
          <input type="search" value={search} onChange={event=>setSearch(event.target.value)}/></label>
        <label>{cs?'Historická kategorie':'Historical category'}{' '}
          <select value={category} onChange={event=>setCategory(event.target.value)}>
            <option value="">{cs?'Všechny kategorie':'All categories'}</option>
            {category&&!categoryOptions.includes(category)&&<option value={category}>{category}</option>}
            {categoryOptions.map(value=><option key={value} value={value}>{value}</option>)}
          </select></label>
        <label><input type="checkbox" checked={reviewOnly} onChange={event=>setReviewOnly(event.target.checked)}/>
          {cs?'Pouze příznaky k prověření v rozsahu':'Only flagged rows inside horizon'}</label>
        <button type="button" onClick={()=>{setSearch('');setCategory('');setReviewOnly(false)}}>
          {cs?'Vymazat filtry náhledu':'Clear preview filters'}</button>
        <p className="status">{cs?'Zobrazeno v rozsahu / mimo rozsah':'Shown inside / outside horizon'}:
          {' '}{shown.length} / {outside.length}</p>
      </section>
      {shown.length===0&&outside.length===0&&<p role="status">{cs?'Žádné záznamy neodpovídají filtrům.':
        'No preview rows match the filters.'}</p>}
      {shown.length > 0 && <div className="table-responsive"><table>
        <thead><tr>
          <th>{cs ? 'Turnaj a kategorie' : 'Tournament and category'}</th>
          <th>{cs ? 'Původní termín' : 'Original dates'}</th>
          <th>{cs ? 'Navržené týdny Runu' : 'Projected Run weeks'}</th>
          <th>{cs ? 'Týden původního konce' : 'Original finish week'}</th><th>{cs?'Příznaky zdroje':'Source review flags'}</th>
        </tr></thead>
        <tbody>{chronological(shown).map(row => <tr key={row.source_identity}>
          <td>{bindings[row.source_identity].series_name}
            {' · '}{bindings[row.source_identity].historical_category_label}</td>
          <td>{row.source_start_date} – {row.source_end_date}</td>
          <td>{row.run_weeks.map(labelRunWeek).join(', ')}
            {row.run_weeks.length === 3 && <div>{cs
              ? 'Tři dotčené týdny. Rozvržení zápasů vyžaduje kontrolu.'
              : 'Three weeks touched. Match scheduling requires review.'}</div>}</td>
          <td>{labelRunWeek(row.source_finish_run_week)}
            {row.review_flags.includes('single_week_majority_precedes_finish_week') && <div>{cs
              ? 'Konec zdroje je týden po hlavní části.'
              : 'The source finish is one week after the main occupancy.'}</div>}</td>
          <td>{row.review_flags.length?row.review_flags.join(', '):'—'}</td>
        </tr>)}</tbody>
      </table></div>}
      {outside.length > 0 && <details>
        <summary>{cs ? 'Turnaje mimo rozsah Runu' : 'Tournaments outside Run horizon'}
          {' ('}{outside.length}{')'}</summary>
        <ul>{chronological(outside).map(row => <li key={row.source_identity}>
          {bindings[row.source_identity].series_name}{' · '}{row.source_start_date} – {row.source_end_date}
          {' · '}{row.outside_year_weeks.map(labelYearWeek).join(', ')}
        </li>)}</ul>
      </details>}
    </>}
  </section>
}
