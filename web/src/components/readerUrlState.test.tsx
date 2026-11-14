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
    <button onClick={() => url.set({ kind: 'retirement' })}>Choose</button>
    <button onClick={() => url.set({ search: 'hello' }, true)}>Search</button>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
    <button onClick={() => url.reset()}>Reset</button>
  </div>
}

describe('reader URL state (router-only, no HTTP)', () => {
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

  it('ignores selections belonging to another Saved owner', () => {
    const { rerender } = render(<MemoryRouter initialEntries={['/?career_scope=old&career_kind=retirement&foo=bar']}>
      <Reader owner="new" />
    </MemoryRouter>)
    expect(screen.getByTestId('value')).toHaveTextContent('all')
    fireEvent.click(screen.getByRole('button', { name: 'Choose' }))
    expect(screen.getByTestId('location')).toHaveTextContent('foo=bar')
    expect(screen.getByTestId('location')).toHaveTextContent('career_scope=new')
    rerender(<MemoryRouter initialEntries={['/?career_scope=old&career_kind=retirement']}><Reader owner="new" /></MemoryRouter>)
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
