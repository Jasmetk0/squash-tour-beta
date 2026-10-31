import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SavedCrossRunComparePage } from './SavedCrossRunComparePage'
import { LanguageProvider } from '../i18n/LanguageContext'
import { vi } from 'vitest'

const api = vi.hoisted(() => {
  return {
    compareCrossSavedRevisions: vi.fn(),
  }
})

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client')
  return {
    ...actual,
    compareCrossSavedRevisions: api.compareCrossSavedRevisions,
  }
})

describe('SavedCrossRunComparePage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderWithRoute(route = '/admin/compare-runs') {
    return render(
      <LanguageProvider>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[route]}>
            <Routes>
              <Route path="/admin/compare-runs" element={<SavedCrossRunComparePage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </LanguageProvider>
    )
  }

  it('renders correctly with no initial data', () => {
    renderWithRoute()
    expect(screen.getByText('Cross-Run Saved Comparison')).toBeInTheDocument()
    expect(screen.getByText('Source A')).toBeInTheDocument()
    expect(screen.getByText('Source B')).toBeInTheDocument()
  })

  it('fetches and displays comparison data when URL parameters are present', async () => {
    api.compareCrossSavedRevisions.mockResolvedValue({
      from_source: { run_id: 'run-a', branch_id: 'branch-a', saved_head_revision_id: 'head-a', revision: { revision_id: 'rev-a', sequence: 1, content_hash: 'hash-a' } },
      to_source: { run_id: 'run-b', branch_id: 'branch-b', saved_head_revision_id: 'head-b', revision: { revision_id: 'rev-b', sequence: 1, content_hash: 'hash-b' } },
      run_changes: { 'some_val': { before: 'a', after: 'b' } },
      branch_changes: {},
      components: [
        { component_key: 'comp-1', status: 'changed', before_fingerprint: '1', after_fingerprint: '2' },
        { component_key: 'comp-2', status: 'removed', before_fingerprint: 'x', after_fingerprint: null }
      ]
    })

    renderWithRoute('/admin/compare-runs?run_a=run-a&branch_a=branch-a&rev_a=rev-a&run_b=run-b&branch_b=branch-b&rev_b=rev-b')

    await waitFor(() => {
      expect(screen.getByText('Changes overview')).toBeInTheDocument()
    })

    expect(screen.getByText('some_val')).toBeInTheDocument()
    expect(screen.getByText('comp-1')).toBeInTheDocument()
    expect(screen.getByText('comp-2')).toBeInTheDocument()
  })

  it('swaps A and B inputs correctly', async () => {
    renderWithRoute('/admin/compare-runs?run_a=run-a&branch_a=branch-a&rev_a=rev-a&run_b=run-b&branch_b=branch-b&rev_b=rev-b')

    const swapButton = screen.getByText('Swap A/B')
    fireEvent.click(swapButton)

    await waitFor(() => {
      const inputs = screen.getAllByRole('textbox')
      expect(inputs[0]).toHaveValue('run-b')
      expect(inputs[3]).toHaveValue('run-a')
    })
  })
})
