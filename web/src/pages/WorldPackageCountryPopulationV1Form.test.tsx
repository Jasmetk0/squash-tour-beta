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
        onChange={vi.fn()}
        onRemove={onRemove}
        onAdd={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Population year 1')).toHaveAttribute('readonly')
    expect(screen.getAllByRole('button', { name: 'Remove' })).toHaveLength(1)

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(onRemove).toHaveBeenCalledWith(0)
  })

  it('reports population edits and add-row requests explicitly', () => {
    const onChange = vi.fn()
    const onAdd = vi.fn()
    render(
      <CountryV1PopulationRowsEditor
        rows={[{ id: 1, year: '2020', population: '1000000' }]}
        onChange={onChange}
        onRemove={vi.fn()}
        onAdd={onAdd}
      />,
    )

    fireEvent.change(screen.getByLabelText('Population value 2020'), { target: { value: '1100000' } })
    fireEvent.click(screen.getByRole('button', { name: '+ Add authored year' }))

    expect(onChange).toHaveBeenCalledWith(1, 'population', '1100000')
    expect(onAdd).toHaveBeenCalledOnce()
  })
})
