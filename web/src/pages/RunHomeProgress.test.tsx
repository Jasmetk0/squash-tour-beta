import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RunHomeProgress, runHomeClock } from './RunHomeProgress'

const props = {season: null, week: null, loading: false, unavailable: false, historical: false, locale: 'en' as const}
describe('Run-local Home timeline', () => {
  it('renders the chosen empty Earth range without inventing a position', () => {
    const clock = runHomeClock({run_calendar: {schema_version:'run_calendar.v1', weeks_per_year:52,
      season_count:3, start_year:2030, season_start_year_week:1}})
    const view = render(<RunHomeProgress {...props} clock={clock} />)
    expect(screen.getByRole('img', {name:'3 seasons'}).children).toHaveLength(3)
    expect(screen.getByRole('img', {name:'52 weeks'}).children).toHaveLength(52)
    expect(screen.getByTitle('2030')).toBeVisible()
    expect(view.container.querySelector('.is-current')).toBeNull()
  })
  it('labels the Run timeline consistently in Czech including unavailable and loading states', () => {
    const unavailable = render(<RunHomeProgress {...props} locale="cs" clock={null} />)
    expect(screen.getByRole('region', { name: 'Časová osa Runu' })).toHaveTextContent('Kalendář Runu není dostupný.')
    unavailable.unmount()

    const loading = render(<RunHomeProgress {...props} locale="cs" clock={null} loading />)
    expect(screen.getByRole('region', { name: 'Časová osa Runu' })).toHaveTextContent('Načítání…')
    loading.unmount()

    render(<RunHomeProgress {...props} locale="cs" clock={runHomeClock({})} />)
    expect(screen.getByRole('region', { name: 'Časová osa Runu' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '50 sezón' })).toBeInTheDocument()
  })
  it('bounds rendering for a very large valid horizon and week count', () => {
    const view = render(<RunHomeProgress {...props} clock={{weeks_per_year:1000000,season_count:1000000,
      start_year:2030,season_start_year_week:1}} />)
    expect(view.container.querySelectorAll('progress')).toHaveLength(2)
    expect(view.container.querySelectorAll('span')).toHaveLength(2)
  })
  it('distinguishes absent legacy metadata from corrupt explicit metadata', () => {
    expect(runHomeClock({})?.weeks_per_year).toBe(61)
    expect(runHomeClock({run_calendar:null})).toBeNull()
    expect(runHomeClock({run_calendar:{schema_version:'new'}})).toBeNull()
    render(<RunHomeProgress {...props} clock={null} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Run calendar is unavailable')
  })
})
