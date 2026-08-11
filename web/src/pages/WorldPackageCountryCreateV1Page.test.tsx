import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { CountryV1FormDraft } from '../utils/countryV1Form'
import { CountryV1RatingsFieldset } from './WorldPackageCountryCreateV1Page'

const draft: CountryV1FormDraft = {
  name: '',
  notes: '',
  area_km2: '',
  region: '',
  travel_region: '',
  court_count: '12',
  squash_popularity: '1',
  squash_access: '2',
  development_quality: '3',
  competition_quality: '4',
  elite_support: '5',
  squash_tradition: '3',
}

describe('CountryV1RatingsFieldset', () => {
  it('renders exactly the canonical Country V1 rating controls plus factual court count', () => {
    render(<CountryV1RatingsFieldset draft={draft} onChange={vi.fn()} />)

    expect(screen.getByLabelText('Squash Popularity')).toHaveValue(1)
    expect(screen.getByLabelText('Squash Access')).toHaveValue(2)
    expect(screen.getByLabelText('Development Quality')).toHaveValue(3)
    expect(screen.getByLabelText('Competition Quality')).toHaveValue(4)
    expect(screen.getByLabelText('Elite Support')).toHaveValue(5)
    expect(screen.getByLabelText('Squash Tradition')).toHaveValue(3)
    expect(screen.getByLabelText('Court Count')).toHaveValue(12)

    expect(screen.queryByLabelText('Wealth Support')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('System Quality')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Competition Density')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Federation Quality')).not.toBeInTheDocument()
    expect(screen.queryByText('Style DNA')).not.toBeInTheDocument()
  })

  it('reports rating and court-count changes using canonical keys', () => {
    const onChange = vi.fn()
    render(<CountryV1RatingsFieldset draft={draft} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Elite Support'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Court Count'), { target: { value: '20' } })

    expect(onChange).toHaveBeenCalledWith('elite_support', '4')
    expect(onChange).toHaveBeenCalledWith('court_count', '20')
  })
})
