import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { CountryV1FormDraft } from '../utils/countryV1Form'
import { CountryV1EditFields } from './WorldPackageCountryEditV1Form'

const draft: CountryV1FormDraft = {
  name: 'Exampleland',
  notes: '',
  area_km2: '12345',
  region: 'EUR',
  travel_region: 'EUROPE_CENTRAL',
  court_count: '42',
  squash_popularity: '1',
  squash_access: '2',
  development_quality: '3',
  competition_quality: '4',
  elite_support: '5',
  squash_tradition: '3',
}

const geography = {
  regions: [{ code: 'EUR', name: 'Europe' }],
  travel_regions: [{ code: 'EUROPE_CENTRAL', name: 'Central Europe' }],
}

describe('CountryV1EditFields', () => {
  it('renders only canonical Country V1 authored ratings', () => {
    render(<CountryV1EditFields draft={draft} geography={geography} onChange={vi.fn()} />)

    for (const label of [
      'Squash Popularity',
      'Squash Access',
      'Development Quality',
      'Competition Quality',
      'Elite Support',
      'Squash Tradition',
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument()
    }

    expect(screen.queryByLabelText('Wealth Support')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('System Quality')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Competition Density')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Federation Quality')).not.toBeInTheDocument()
    expect(screen.queryByText('Style DNA')).not.toBeInTheDocument()
  })

  it('reports edits using canonical field names', () => {
    const onChange = vi.fn()
    render(<CountryV1EditFields draft={draft} geography={geography} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Development Quality'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Court Count'), { target: { value: '50' } })

    expect(onChange).toHaveBeenCalledWith('development_quality', '5')
    expect(onChange).toHaveBeenCalledWith('court_count', '50')
  })
})
