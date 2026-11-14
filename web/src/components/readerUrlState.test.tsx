import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { readerPage, readerPageCount, readerSlice, useReaderParams } from './readerUrlState'

function Reader({ owner }: { owner: string }) {
  const url = useReaderParams('career', owner)
  const location = useLocation()
  const navigate = useNavigate()
  return <div>
    <output data-testid="value">{url.get('kind', 'all')}</output>
    <output data-testid="location">{location.search}</output>
    <output data-testid="hash">{location.hash}</output>
    <button onClick={() => url.set({ kind: 'retirement' })}>Choose</button>
    <button onClick={() => url.set({ search: 'hello' }, true)}>Search</button>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
    <button onClick={() => url.reset()}>Reset</button>
  </div>
}

describe('reader URL state (router-only, no HTTP)', () => {
  it('preserves the current anchor for selection, search, reset and history', () => {
    render(<MemoryRouter initialEntries={['/?branch=one#timeline']}><Reader owner="scope" /></MemoryRouter>)
    for (const action of ['Choose', 'Search', 'Reset', 'Back', 'Forward']) {
      fireEvent.click(screen.getByRole('button', { name: action }))
      expect(screen.getByTestId('hash')).toHaveTextContent('#timeline')
      expect(screen.getByTestId('location')).toHaveTextContent('branch=one')
    }
  })

  it('preserves foreign parameters and restores choices with Back/Forward', () => {
    render(<MemoryRouter initialEntries={['/?branch=one&external=keep']}><Reader owner="run|branch|revision|player" /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Choose' }))
    expect(screen.getByTestId('value')).toHaveTextContent('retirement')
    expect(screen.getByTestId('location')).toHaveTextContent('external=keep')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByTestId('value')).toHaveTextContent('all')
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByTestId('value')).toHaveTextContent('retirement')
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(screen.getByTestId('location')).toHaveTextContent('external=keep')
    expect(screen.getByTestId('location')).not.toHaveTextContent('career_')
  })

  it('does not leak controls when the displayed Run, Branch, Saved revision or player changes', () => {
    const { rerender } = render(<MemoryRouter initialEntries={['/?career_scope=old&career_kind=retirement&foo=bar']}>
      <Reader owner="old" />
    </MemoryRouter>)
    expect(screen.getByTestId('value')).toHaveTextContent('retirement')
    rerender(<MemoryRouter><Reader owner="new" /></MemoryRouter>)
    expect(screen.getByTestId('value')).toHaveTextContent('all')
    fireEvent.click(screen.getByRole('button', { name: 'Choose' }))
    const location = screen.getByTestId('location')
    expect(location).toHaveTextContent('foo=bar')
    expect(location).toHaveTextContent('career_scope=new')
    expect(location).toHaveTextContent('career_kind=retirement')
    expect(location).not.toHaveTextContent('career_scope=old')
    rerender(<MemoryRouter><Reader owner="other-run|other-branch|other-revision|other-player" /></MemoryRouter>)
    expect(screen.getByTestId('value')).toHaveTextContent('all')
  })

  it('preserves other reader controls and history without adding a step for typed search', () => {
    render(<MemoryRouter initialEntries={['/?branch=one&season_selected=2&alert_hidden=true']}>
      <Reader owner="scope" />
    </MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Choose' }))
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(screen.getByTestId('location')).toHaveTextContent('career_search=hello')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByTestId('value')).toHaveTextContent('all')
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByTestId('value')).toHaveTextContent('retirement')
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(screen.getByTestId('location')).toHaveTextContent('season_selected=2')
    expect(screen.getByTestId('location')).toHaveTextContent('alert_hidden=true')
    expect(screen.getByTestId('location')).toHaveTextContent('branch=one')
    expect(screen.getByTestId('location')).not.toHaveTextContent('career_')
  })

  it('paginates without mutating source and rejects invalid page values', () => {
    const source = Object.freeze([1, 2, 3, 4])
    expect(readerPage('0')).toBe(1)
    expect(readerPage('2x')).toBe(1)
    expect(readerPage('2')).toBe(2)
    expect(readerPageCount(4, 2)).toBe(2)
    expect(readerSlice(source, 2, 2)).toEqual([3, 4])
    expect(source).toEqual([1, 2, 3, 4])
  })
})
