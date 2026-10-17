import { useEffect, useRef, useState } from 'react'
import { inspectSignedCalendarKnockoutStandings } from '../api/client'
import type {
  KnockoutInspection, SignedKnockoutStandings,
} from '../api/calendarOpeningKnockout'
import { verifySignedKnockoutStandings } from '../api/calendarOpeningKnockout'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

/** Read-only as-of one-event ranking evidence; never Official Tour Ranking. */
export function CalendarSignedKnockoutStandingsPanel({
  runId, branchId, view, season, week, onPositionChange,
}: {
  runId: string; branchId: string; view: KnockoutInspection
  season: number; week: number
  onPositionChange: (position: { season: number; week: number }) => void
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const seasonInput = useRef<HTMLInputElement>(null)
  const weekInput = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<SignedKnockoutStandings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const head = view.saved_head_revision_id
  const clock = view.run_calendar

  useEffect(() => {
    let active = true
    setResult(null)
    setError(null)
    if (!view.saved || !view.prepared_points) return () => { active = false }
    if (!Number.isSafeInteger(season) || !Number.isSafeInteger(week)
      || season < 0 || season >= clock.season_count || week < 1 || week > clock.weeks_per_year
      || season === 0 && week < 2) {
      setError(cs
        ? 'Zvolený týden není způsobilý pro tento bodový výsledek.'
        : 'Selected week is not eligible for this scored result.')
      return () => { active = false }
    }
    setBusy(true)
    void inspectSignedCalendarKnockoutStandings(
      runId, branchId, head, season, week,
    ).then(response => {
      if (!active) return
      setResult(verifySignedKnockoutStandings(response, view, season, week))
    }).catch(err => {
      if (active) setError(formatApiError(err))
    }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [
    runId, branchId, head, view.knockout_fingerprint,
    view.saved, view.prepared_points?.scored_fingerprint, season, week,
    clock.season_count, clock.weeks_per_year, cs,
  ])

  if (!view.saved || !view.prepared_points) return <></>

  return <section aria-label="Signed calendar knockout as-of standings">
    <h4>{cs ? 'Bodové pořadí turnaje v čase' : 'Tournament point standings over time'}</h4>
    <p className="status">{cs
      ? 'Jen 4 účastníci tohoto uloženého turnaje. NENÍ to oficiální žebříček Tour ani skutečný přechod týdne. Bodová platnost je hypotetický pohled k vybranému týdnu.'
      : 'Only the 4 Saved tournament entrants. NOT the Official Tour Ranking or an executed Week Transition. This is a hypothetical as-of point-validity view.'}</p>
    <form onSubmit={event => {
      event.preventDefault()
      const proposedSeason = Number(seasonInput.current?.value) - 1
      const proposedWeek = Number(weekInput.current?.value)
      if (!Number.isSafeInteger(proposedSeason)
        || !Number.isSafeInteger(proposedWeek)
        || proposedSeason < 0 || proposedSeason >= clock.season_count
        || proposedWeek < 1 || proposedWeek > clock.weeks_per_year
        || (proposedSeason === 0 && proposedWeek < 2)) {
        setError(cs ? 'Zadaná sezona nebo týden není platný.' : 'Invalid season or week.')
        return
      }
      onPositionChange({ season: proposedSeason, week: proposedWeek })
    }}>
      <label>{cs ? 'Sezona' : 'Season'}{' '}
        <input key={'s|' + runId + '|' + branchId + '|' + head + '|' + season}
          ref={seasonInput} aria-label="Standings season number"
          type="number" min={1} max={clock.season_count} step={1}
          defaultValue={season + 1} required />
      </label>
      <label>{cs ? 'Týden' : 'Week'}{' '}
        <input key={'w|' + runId + '|' + branchId + '|' + head + '|' + week}
          ref={weekInput} aria-label="Standings week number"
          type="number" min={1} max={clock.weeks_per_year} step={1}
          defaultValue={week} required />
      </label>
      <button type="submit">{cs ? 'Zobrazit zvolený týden' : 'Show selected week'}</button>
    </form>
    <div>
      <button type="button"
        disabled={season === 0 && week === 2}
        onClick={() => onPositionChange({ season: 0, week: 2 })}>
        {cs ? 'První týden platnosti' : 'View opening week'}
      </button>
      {clock.season_count > 1 && <button type="button"
        disabled={season === 1 && week === 2}
        onClick={() => onPositionChange({ season: 1, week: 2 })}>
        {cs ? 'První týden po vypršení' : 'View first expired week'}
      </button>}
    </div>
    {busy && <p role="status">{cs ? 'Ověřuji uložená data…' : 'Verifying Signed Saved data…'}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {result && !busy && <>
      <p role="status">{result.points_in_period
        ? (cs ? 'Body v tomto týdnu platí.' : 'Points are still within their validity period.')
        : (cs ? 'Body již vypršely.' : 'Points have expired.')}
        {' · '}{cs ? 'Platnost' : 'Validity'}: {result.validity_weeks} {cs ? 'týdnů' : 'weeks'}
      </p>
      <table aria-label="Signed tournament standings table">
        <thead><tr>
          <th>{cs ? 'Umístění' : 'Finish'}</th>
          <th>{cs ? 'Hráč' : 'Player'}</th>
          <th>{cs ? 'Země' : 'Country'}</th>
          <th>{cs ? 'Body v týdnu' : 'As-of points'}</th>
          <th>{cs ? 'Původní body' : 'Awarded points'}</th>
        </tr></thead>
        <tbody>
          {result.rows.map(row => <tr key={row.player_id}>
            <td>{row.tournament_place}</td>
            <td>{row.player_name}</td>
            <td>{row.nationality}</td>
            <td>{row.as_of_counted_points}</td>
            <td>{row.awarded_main_points}</td>
          </tr>)}
        </tbody>
      </table>
      <p className="status">{cs
        ? 'K oficiální publikaci stále chybí Tour Entry, ověřená politika Category/Edition a nativní Week Transition.'
        : 'Official publication remains blocked by Tour Entry, authenticated Category/Edition policy and native Week Transition.'}
      </p>
    </>}
  </section>
}
