import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { CountryV1Record } from '../api/countryV1'
import { CountryV1Table } from './WorldPackageCountriesV1Page'

const country: CountryV1Record = {
  code: 'EXP',
  name: 'Exampleland',
  flag_asset: null,
  region: 'EUR',
  population: 1_000_000,
  area_km2: 12_345,
  default_population_year: 2020,
  default_population: 1_000_000,
  population_by_year: { '2000': 900_000, '2020': 1_000_000 },
  court_count: 42,
  travel_region: 'EUROPE_CENTRAL',
  notes: null,
  squash_popularity: 4,
  squash_access: 3,
  development_quality: 5,
  competition_quality: 4,
  elite_support: 2,
  squash_tradition: 3,
}

describe('CountryV1Table', () => {
  it('renders all six canonical Country V1 ratings and no legacy rating headings', () => {
    render(
      <MemoryRouter>
        <CountryV1Table countries={[country]} worldId="custom world" />
      </MemoryRouter>,
    )

    const table = screen.getByRole('table', { name: 'World package Country V1 table' })
    const headings = within(table).getAllByRole('columnheader').map((heading) => heading.textContent)

    expect(headings).toEqual(expect.arrayContaining([
      'Squash Popularity',
      'Squash Access',
      'Development Quality',
      'Competition Quality',
      'Elite Support',
      'Squash Tradition',
    ]))
    expect(headings).not.toEqual(expect.arrayContaining([
      'Wealth Support',
      'System Quality',
      'Competition Density',
      'Federation Quality',
      'Style DNA',
    ]))
  })

  it('renders factual country data and a safely encoded detail link', () => {
    render(
      <MemoryRouter>
        <CountryV1Table countries={[country]} worldId="custom world" />
      </MemoryRouter>,
    )

    expect(screen.getByText('Exampleland')).toBeInTheDocument()
    expect(screen.getByText('2 years: 2000, 2020')).toBeInTheDocument()
    expect(screen.getByText('EUROPE_CENTRAL')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open' })).toHaveAttribute(
      'href',
      '/admin/world/library/custom%20world/countries/EXP',
    )
  })
})
