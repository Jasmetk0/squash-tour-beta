import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CountryV1PopulationRowsEditor } from './WorldPackageCountryPopulationV1Form'

describe('CountryV1PopulationRowsEditor', () => {
  it('keeps authored 2020 population year protected while allowing other years to be removed', () => {
    const onRemove = vi.fn()
    render(
      <CountryV1PopulationRowsEditor
        rows={[
          { id: 0, year: '2000', population: '900000' },
          { id: 1, year: '2020', population: '1000000' },
        ]}
        onPopulationChange={vi.fn()}
        onRemove={onRemove}
      />,
    )

    expect(screen.getByRole('table', { name: 'Edit authored population timeline' })).toHaveTextContent('2020 · Default year')
    expect(screen.queryByRole('button', { name: 'Remove 2020' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove 2000' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Remove 2000' }))
    expect(onRemove).toHaveBeenCalledWith(0)
  })

  it('reports population edits using the authored year label', () => {
    const onPopulationChange = vi.fn()
    render(
      <CountryV1PopulationRowsEditor
        rows={[{ id: 1, year: '2020', population: '1000000' }]}
        onPopulationChange={onPopulationChange}
        onRemove={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText('Population 2020'), { target: { value: '1100000' } })

    expect(onPopulationChange).toHaveBeenCalledWith(1, '1100000')
  })
})
