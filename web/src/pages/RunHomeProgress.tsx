type HomeClock = { weeks_per_year: number; season_count: number; start_year: number; season_start_year_week: number }
const legacyClock: HomeClock = { weeks_per_year: 61, season_count: 50, start_year: 2000, season_start_year_week: 37 }

/** Absent historical metadata is legacy; an explicit malformed clock fails closed. */
export function runHomeClock(metadata: Record<string, unknown> | null | undefined): HomeClock | null {
  if (!metadata || !Object.prototype.hasOwnProperty.call(metadata, 'run_calendar')) return legacyClock
  const value = metadata.run_calendar as (HomeClock & { schema_version?: string }) | null
  if (!value || value.schema_version !== 'run_calendar.v1'
    || ![value.weeks_per_year, value.season_count, value.start_year, value.season_start_year_week].every(Number.isSafeInteger)
    || value.weeks_per_year < 1 || value.season_count < 1 || value.start_year < 0
    || value.season_start_year_week < 1 || value.season_start_year_week > value.weeks_per_year) return null
  return value
}

type Props = {
  season: number | null
  week: number | null
  loading: boolean
  unavailable: boolean
  historical: boolean
  locale: 'cs' | 'en'
  clock?: HomeClock | null
}

export function RunHomeProgress({ season, week, loading, unavailable, historical, locale, clock = legacyClock }: Props): JSX.Element {
  if (clock === null && loading) return <section className="run-home-progress" aria-label={locale === 'cs' ? 'Časová osa Runu' : 'Run timeline'}><p role="status">{locale === 'cs' ? 'Načítání…' : 'Loading…'}</p></section>
  if (clock === null) return <section className="run-home-progress" aria-label={locale === 'cs' ? 'Časová osa Runu' : 'Run timeline'}><p role="alert">{locale === 'cs' ? 'Kalendář Runu není dostupný.' : 'Run calendar is unavailable.'}</p></section>
  const SEASONS = clock.season_count, WEEKS = clock.weeks_per_year
  const seasonLabel = (ordinal: number): string => clock.season_start_year_week === 1
    ? String(clock.start_year + ordinal) : `${clock.start_year + ordinal}/${String((clock.start_year + ordinal + 1) % 100).padStart(2, '0')}`
  const index = season == null || !Number.isInteger(season) ? null
    : season >= 0 && season < SEASONS ? season
      : season >= clock.start_year && season < clock.start_year + SEASONS ? season - clock.start_year : null
  const currentWeek = week != null && Number.isInteger(week) && week >= 1 && week <= WEEKS ? week : null
  const prefix = historical
    ? locale === 'cs' ? 'Záznam checkpointu' : 'Checkpoint metadata'
    : locale === 'cs' ? 'Aktuální pozice branche' : 'Current Branch position'
  const state = (item: 'season' | 'week') =>
    loading ? locale === 'cs' ? 'Načítání…' : 'Loading…'
      : unavailable ? locale === 'cs' ? 'Nedostupné' : 'Unavailable'
        : (item === 'season' ? index === null : currentWeek === null)
          ? locale === 'cs' ? 'Zatím neurčeno' : 'Not positioned yet'
          : item === 'season' ? seasonLabel(index!) : 'W' + currentWeek
  return <section className="run-home-progress" aria-label={locale === 'cs' ? 'Časová osa Runu' : 'Run timeline'}>
    <p className="status">{prefix}{historical
      ? locale === 'cs' ? ' · zobrazeny pouze lokátory, nikoliv rekonstruovaná historie' : ' · locators only, not reconstructed history'
      : ''}</p>
    <div className="run-home-progress__heading"><h3>{locale === 'cs' ? 'Sezóny' : 'Seasons'}</h3>
      <span>{state('season')} · {SEASONS} {locale === 'cs' ? 'sezón' : 'seasons'}</span></div>
    <div className="run-home-progress__track" role="img" aria-label={SEASONS + (locale === 'cs' ? ' sezón' : ' seasons')}>
      {SEASONS > 200 ? <progress max={SEASONS} value={index === null || unavailable || loading ? 0 : index + 1} /> : Array.from({ length: SEASONS }, (_, i) => <span key={i} title={seasonLabel(i)}
        className={index === i && !unavailable && !loading ? 'is-current' : index !== null && i < index && !unavailable && !loading ? 'is-past' : ''} />)}
    </div>
    <div className="run-home-progress__heading"><h3>{locale === 'cs' ? 'Týdny sezóny' : 'Season weeks'}</h3>
      <span>{state('week')} · {WEEKS} {locale === 'cs' ? 'týdnů' : 'weeks'}</span></div>
    <div className="run-home-progress__track run-home-progress__track--weeks" role="img" aria-label={WEEKS + (locale === 'cs' ? ' týdnů' : ' weeks')}>
      {WEEKS > 200 ? <progress max={WEEKS} value={currentWeek === null || unavailable || loading ? 0 : currentWeek} /> : Array.from({ length: WEEKS }, (_, i) => <span key={i} title={'W' + (i + 1)}
        className={currentWeek === i + 1 && !unavailable && !loading ? 'is-current' : currentWeek !== null && i + 1 < currentWeek && !unavailable && !loading ? 'is-past' : ''} />)}
    </div>
  </section>
}
