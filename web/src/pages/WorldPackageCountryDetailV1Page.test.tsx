import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { CountryV1Record } from '../api/countryV1'
import { CountryV1StrengthSection } from './WorldPackageCountryDetailV1Page'

const country: CountryV1Record = {
  code: 'EXP',
  name: 'Exampleland',
  flag_asset: null,
  region: 'EUR',
  population: 1_000_000,
  area_km2: 12_345,
  default_population_year: 2020,
  default_population: 1_000_000,
  population_by_year: { '2020': 1_000_000 },
  court_count: 42,
  travel_region: 'EUROPE_CENTRAL',
  notes: null,
  squash_popularity: 1,
  squash_access: 2,
  development_quality: 3,
  competition_quality: 4,
  elite_support: 5,
  squash_tradition: 3,
}

describe('CountryV1StrengthSection', () => {
  it('shows the six canonical authored ratings and factual court count', () => {
    render(<CountryV1StrengthSection country={country} />)

    expect(screen.getByText(/Squash Popularity:/)).toHaveTextContent('1')
    expect(screen.getByText(/Squash Access:/)).toHaveTextContent('2')
    expect(screen.getByText(/Development Quality:/)).toHaveTextContent('3')
    expect(screen.getByText(/Competition Quality:/)).toHaveTextContent('4')
    expect(screen.getByText(/Elite Support:/)).toHaveTextContent('5')
    expect(screen.getByText(/Squash Tradition:/)).toHaveTextContent('3')
    expect(screen.getByText(/Court Count:/)).toHaveTextContent('42')
  })

  it('does not render superseded Country V1 concepts', () => {
    render(<CountryV1StrengthSection country={country} />)

    expect(screen.queryByText(/Wealth Support/)).not.toBeInTheDocument()
    expect(screen.queryByText(/System Quality/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Competition Density/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Federation Quality/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Style DNA/)).not.toBeInTheDocument()
  })
})
