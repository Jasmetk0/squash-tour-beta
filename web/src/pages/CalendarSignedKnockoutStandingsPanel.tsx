import { useEffect, useState } from 'react'
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
  // Editing the form must not navigate or reload the Run/Branch context.
  // Confirm a pair of positions as ONE reviewed read; the selected as-of
  // position is then anchored in the URL by the parent Run Simulation page.
  const [draftPeriod, setDraftPeriod] = useState({ season, week })
  const [result, setResult] = useState<SignedKnockoutStandings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const head = view.saved_head_revision_id
  const clock = view.run_calendar

  useEffect(() => {
    setDraftPeriod({ season, week })
  }, [runId, branchId, head, season, week])

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
    <label>{cs ? 'Sezona' : 'Season'}{' '}
      <select aria-label="Standings season" value={draftPeriod.season} onChange={e => {
        const next = Number(e.currentTarget.value)
        setDraftPeriod(current => ({
          season: next,
          week: next === 0 && current.week === 1 ? 2 : current.week,
        }))
      }}>
        {Array.from({ length: clock.season_count }, (_, i) =>
          <option key={i} value={i}>{i + 1}</option>)}
      </select>
    </label>
    <label>{cs ? 'Týden' : 'Week'}{' '}
      <select aria-label="Standings week" value={draftPeriod.week}
        onChange={e => setDraftPeriod(current => ({
          ...current, week: Number(e.currentTarget.value),
        }))}>
        {Array.from({ length: clock.weeks_per_year }, (_, i) => i + 1)
          .filter(w => draftPeriod.season !== 0 || w >= 2)
          .map(w => <option key={w} value={w}>{w}</option>)}
      </select>
    </label>
    <button type="button"
      disabled={draftPeriod.season === season && draftPeriod.week === week}
      onClick={() => onPositionChange(draftPeriod)}>
      {cs ? 'Zobrazit zvolený týden' : 'Apply selected week'}
    </button>
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
