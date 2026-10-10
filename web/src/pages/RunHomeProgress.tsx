import { SEASONS, WEEKS, seasonLabel, seasonOrdinal, weekOrdinal } from './runHomeModel'

type Props = {
  season: number | null
  week: number | null
  loading: boolean
  unavailable: boolean
  historical: boolean
  locale: 'cs' | 'en'
}

export function RunHomeProgress({ season, week, loading, unavailable, historical, locale }: Props): JSX.Element {
  const index = seasonOrdinal(season)
  const currentWeek = weekOrdinal(week)
  const prefix = historical
    ? locale === 'cs' ? 'Záznam checkpointu' : 'Checkpoint metadata'
    : locale === 'cs' ? 'Aktuální pozice branche' : 'Current Branch position'
  const state = (item: 'season' | 'week') =>
    loading ? locale === 'cs' ? 'Načítání…' : 'Loading…'
      : unavailable ? locale === 'cs' ? 'Nedostupné' : 'Unavailable'
        : (item === 'season' ? index === null : currentWeek === null)
          ? locale === 'cs' ? 'Zatím neurčeno' : 'Not positioned yet'
          : item === 'season' ? seasonLabel(index!) : 'W' + currentWeek
  return <section className="run-home-progress" aria-label="Run timeline">
    <p className="status">{prefix}{historical
      ? locale === 'cs' ? ' · zobrazeny pouze lokátory, nikoliv rekonstruovaná historie' : ' · locators only, not reconstructed history'
      : ''}</p>
    <div className="run-home-progress__heading"><h3>{locale === 'cs' ? 'Sezóny' : 'Seasons'}</h3>
      <span>{state('season')} · {SEASONS} {locale === 'cs' ? 'sezón' : 'seasons'}</span></div>
    <div className="run-home-progress__track" role="img" aria-label={locale === 'cs' ? '50 sezón' : '50 seasons'}>
      {Array.from({ length: SEASONS }, (_, i) => <span key={i} title={seasonLabel(i)}
        className={index === i && !unavailable && !loading ? 'is-current' : index !== null && i < index && !unavailable && !loading ? 'is-past' : ''} />)}
    </div>
    <div className="run-home-progress__heading"><h3>{locale === 'cs' ? 'Týdny sezóny' : 'Season weeks'}</h3>
      <span>{state('week')} · {WEEKS} {locale === 'cs' ? 'týdnů' : 'weeks'}</span></div>
    <div className="run-home-progress__track run-home-progress__track--weeks" role="img" aria-label={locale === 'cs' ? '61 týdnů' : '61 weeks'}>
      {Array.from({ length: WEEKS }, (_, i) => <span key={i} title={'W' + (i + 1)}
        className={currentWeek === i + 1 && !unavailable && !loading ? 'is-current' : currentWeek !== null && i + 1 < currentWeek && !unavailable && !loading ? 'is-past' : ''} />)}
    </div>
  </section>
}
