import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WorldPackagePage } from './WorldPackagePage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  exportWorldPackageJson: vi.fn(),
  importWorldPackage: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('WorldPackagePage', () => {
  beforeEach(() => {
    vi.stubGlobal('confirm', vi.fn(() => true))
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:mock'), revokeObjectURL: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

    api.exportWorldPackageJson.mockReset()
    api.importWorldPackage.mockReset()

    api.exportWorldPackageJson.mockResolvedValue('{"package_version":"1"}')
    api.importWorldPackage.mockResolvedValue({
      ok: true,
      dry_run: true,
      countries_summary: { total_records: 1, new_records: 0, updated_records: 1, unchanged_records: 0 },
      manual_overrides_summary: { total_records: 1, new_records: 0, updated_records: 0, unchanged_records: 1 },
      errors: []
    })
  })

  it('renders and supports export action', async () => {
    renderWithRoute(<WorldPackagePage />, '/world/package')

    expect(await screen.findByRole('heading', { name: 'World Package' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Export world package' }))

    await waitFor(() => expect(api.exportWorldPackageJson).toHaveBeenCalled())
  })

  it('validates package with dry run and applies package', async () => {
    renderWithRoute(<WorldPackagePage />, '/world/package')

    fireEvent.change(screen.getByLabelText('World package JSON'), { target: { value: '{\"package_version\":\"1\"}' } })

    await userEvent.click(screen.getByRole('button', { name: 'Validate package (dry run)' }))
    await waitFor(() => expect(api.importWorldPackage).toHaveBeenCalledWith({ package_text: '{"package_version":"1"}', dry_run: true }, expect.anything()))

    api.importWorldPackage.mockResolvedValueOnce({
      ok: true,
      dry_run: false,
      countries_summary: { total_records: 1, new_records: 1, updated_records: 0, unchanged_records: 0 },
      manual_overrides_summary: { total_records: 1, new_records: 1, updated_records: 0, unchanged_records: 0 },
      errors: []
    })

    await userEvent.click(screen.getByRole('button', { name: 'Apply package' }))
    await waitFor(() => expect(api.importWorldPackage).toHaveBeenCalledWith({ package_text: '{"package_version":"1"}', dry_run: false }, expect.anything()))
    expect(globalThis.confirm).toHaveBeenCalled()
  })

  it('shows validation error path', async () => {
    api.importWorldPackage.mockResolvedValueOnce({
      ok: false,
      dry_run: true,
      countries_summary: { total_records: 0, new_records: 0, updated_records: 0, unchanged_records: 0 },
      manual_overrides_summary: { total_records: 0, new_records: 0, updated_records: 0, unchanged_records: 0 },
      errors: [{ field: 'package_version', message: 'unsupported package_version' }]
    })

    renderWithRoute(<WorldPackagePage />, '/world/package')

    fireEvent.change(screen.getByLabelText('World package JSON'), { target: { value: '{\"package_version\":\"2\"}' } })
    await userEvent.click(screen.getByRole('button', { name: 'Validate package (dry run)' }))

    expect(await screen.findByText('World package validation failed. No data was written.')).toBeInTheDocument()
    expect(screen.getByText('package_version: unsupported package_version')).toBeInTheDocument()
  })

  it('requires confirmation before apply', async () => {
    ;(globalThis.confirm as ReturnType<typeof vi.fn>).mockReturnValue(false)
    renderWithRoute(<WorldPackagePage />, '/world/package')

    fireEvent.change(screen.getByLabelText('World package JSON'), { target: { value: '{\"package_version\":\"1\"}' } })
    await userEvent.click(screen.getByRole('button', { name: 'Apply package' }))

    expect(globalThis.confirm).toHaveBeenCalled()
    expect(api.importWorldPackage).not.toHaveBeenCalledWith(expect.objectContaining({ dry_run: false }), expect.anything())
  })
})
