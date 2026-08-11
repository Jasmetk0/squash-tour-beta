import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CountryV1DeleteConfirmation } from './WorldPackageCountryDeleteV1Confirmation'

describe('CountryV1DeleteConfirmation', () => {
  it('requires an explicit confirmation action and preserves cancel', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <CountryV1DeleteConfirmation
        code="EXP"
        name="Exampleland"
        saving={false}
        error={null}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    )

    expect(screen.getByText('This removes the Country from this Custom World source.', { exact: false })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Delete country' }))
    expect(onConfirm).toHaveBeenCalledOnce()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('disables both actions while deletion is in progress', () => {
    render(
      <CountryV1DeleteConfirmation
        code="EXP"
        name="Exampleland"
        saving
        error={null}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Deleting…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  })
})
