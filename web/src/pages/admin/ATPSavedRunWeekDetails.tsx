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
  const [requested, setRequested] = useState(false)
  const preview = useQuery({
    queryKey: ['atp-saved-run-week-preview', runId, branchId, revisionId, year],
    queryFn: () => getSavedATPRunWeekPreview(runId, branchId, revisionId, year),
    enabled: false,
    retry: false,
  })
  const result = requested && preview.isSuccess ? preview.data : undefined
  const bindings = result?.source_tour_bindings.selected_occurrences
  const chronological = <T extends {source_start_date: string}>(rows: T[]) =>
    [...rows].sort((a,b) => a.source_start_date.localeCompare(b.source_start_date))

  return <section className="package-apply-step">
    <h3>{cs ? 'ATP kalendář v týdnech Runu (W52)' : 'ATP calendar in Run weeks (W52)'}</h3>
    <p>{cs
      ? 'Nejprve přidej a ulož ATP Setup do vybrané větve. Náhled pak načte uložené termíny pro kontrolu před plánováním zápasů.'
      : 'First apply and save the ATP Setup to the selected branch. Then preview the Saved dates before scheduling matches.'}</p>
    <label>{cs ? 'ATP ročník pro Run' : 'ATP season for this Run'}
      <select value={year} onChange={event => {
        setYear(Number(event.target.value)); setRequested(false)
      }}>
        {[...years].reverse().map(value => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
    <button type="button" disabled={preview.isFetching} onClick={() => {
      setRequested(true); void preview.refetch()
    }}>{cs ? 'Načíst týdny z uloženého ATP balíčku' : 'Preview weeks from the Saved ATP Package'}</button>
    {preview.isFetching && <p role="status">{cs ? 'Počítám týdny Runu…' : 'Mapping Run weeks…'}</p>}
    {requested && preview.isError && <p role="alert" className="error">{formatApiError(preview.error)}</p>}
    {result && bindings && <>
      <p className="status">{cs ? 'V rozsahu Runu' : 'Within Run horizon'}: {result.events.length}
        {' · '}{cs ? 'Mimo rozsah' : 'Outside Run horizon'}: {result.outside_horizon.length}
        {year === 2026 && (cs ? ' · Předběžný ročník' : ' · Provisional season')}</p>
      {result.events.length > 0 && <div className="table-responsive"><table>
        <thead><tr>
          <th>{cs ? 'Turnaj a kategorie' : 'Tournament and category'}</th>
          <th>{cs ? 'Původní termín' : 'Original dates'}</th>
          <th>{cs ? 'Navržené týdny Runu' : 'Projected Run weeks'}</th>
          <th>{cs ? 'Týden původního konce' : 'Original finish week'}</th>
        </tr></thead>
        <tbody>{chronological(result.events).map(row => <tr key={row.source_identity}>
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
        </tr>)}</tbody>
      </table></div>}
      {result.outside_horizon.length > 0 && <details>
        <summary>{cs ? 'Turnaje mimo rozsah Runu' : 'Tournaments outside Run horizon'}
          {' ('}{result.outside_horizon.length}{')'}</summary>
        <ul>{chronological(result.outside_horizon).map(row => <li key={row.source_identity}>
          {bindings[row.source_identity].series_name}{' · '}{row.source_start_date} – {row.source_end_date}
          {' · '}{row.outside_year_weeks.map(labelYearWeek).join(', ')}
        </li>)}</ul>
      </details>}
    </>}
  </section>
}
