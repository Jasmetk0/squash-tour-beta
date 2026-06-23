import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsCategoriesPage } from './CategoriesPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getCategories: vi.fn()
}))

vi.mock('../api/client', () => api)

const requiredCategories = [
  'World Championship',
  'World Tour Finals',
  'Diamond',
  'Emerald',
  'Platinium',
  'Gold',
  'Silver',
  'Bronze',
  'Copper',
  'Cobalt',
  'Iron',
  'Nickel',
  'Tin',
  'Zinc',
  'Challenger 100',
  'Challenger 80',
  'Challenger 60',
  'Challenger 40',
  'Future 25',
  'Future 15',
  'Future 10',
  'Future 5'
]

const requiredGroups = ['World Tour', 'Elite Tour', 'Challenger Tour', 'Development Tour']

const requiredStickerLabels = ['WC', 'Finals', 'Diamond', 'Emerald', 'Platinium', 'Gold', 'Silver', 'Bronze', 'Copper', 'Cobalt', 'Iron', 'Nickel', 'Tin', 'Zinc', 'C100', 'C80', 'C60', 'C40', 'F25', 'F15', 'F10', 'F5']

describe('AdminTourSeasonsCategoriesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getCategories.mockResolvedValue({ categories: [], source_path: 'derived-preview.json', status: 'read_only_foundation' })
  })

  it('renders the canonical identity catalog grouped by tour level with accessible stickers', async () => {
    renderWithRoute(<AdminTourSeasonsCategoriesPage />, '/admin/tour-seasons/categories')

    expect(await screen.findByRole('heading', { name: 'Categories' })).toBeInTheDocument()
    expect(screen.getByText(/stable tournament category identities/i)).toBeInTheDocument()
    expect(screen.getByText(/Season-specific points, prize money, draw sizes, qualification formats, and ranking rules will be defined later/i)).toBeInTheDocument()

    for (const group of requiredGroups) {
      expect(screen.getByRole('heading', { name: group })).toBeInTheDocument()
    }

    for (const category of requiredCategories) {
      expect(screen.getByRole('article', { name: `${category} category` })).toBeInTheDocument()
    }

    for (const sticker of requiredStickerLabels) {
      expect(screen.getAllByText(sticker).length).toBeGreaterThan(0)
    }

    expect(screen.getByLabelText('World Championship category sticker: 🌍 WC')).toBeInTheDocument()
    expect(screen.getByLabelText('World Tour Finals category sticker: 🏆 Finals')).toBeInTheDocument()
    expect(screen.getByLabelText('Platinium category sticker: 🛡 Platinium')).toBeInTheDocument()
    expect(screen.getByLabelText('Challenger 100 category sticker: C100')).toBeInTheDocument()
    expect(screen.getByLabelText('Future 5 category sticker: F5')).toBeInTheDocument()
  })

  it('keeps category catalog cards free of fake points, prize, draw, and ranking values', async () => {
    renderWithRoute(<AdminTourSeasonsCategoriesPage />, '/admin/tour-seasons/categories')

    const catalog = await screen.findByLabelText('Canonical tournament category catalog')
    expect(within(catalog).getAllByText('Platinium').length).toBeGreaterThan(0)
    expect(catalog).not.toHaveTextContent(/points|prize|money|draw|qualification|ranking|winner|mandatory/i)
    expect(catalog).not.toHaveTextContent(/\$|€|£|\b[0-9]{2,}\s*(pts|points)\b/i)
  })
})
