import { describe, expect, it, vi } from 'vitest'
import { decodeRunListViews, isValidRunListView, readRunListViews, RUN_LIST_VIEWS_KEY, writeRunListViews } from './runListViews'

const example = { name: 'Moje testy', query: 'test', visibility: 'editable' as const, hidden: false }

describe('versioned browser-local Run-list views', () => {
  it('round-trips only presentation preferences', () => {
    localStorage.clear()
    expect(writeRunListViews([example])).toBe(true)
    expect(readRunListViews()).toEqual({ status: 'ok', items: [example] })
    expect(JSON.parse(localStorage.getItem(RUN_LIST_VIEWS_KEY)!)).toEqual({
      schema_version: 'run_list_views.v1', items: [example]
    })
  })

  it('fails closed on unknown schema without modifying its bytes', () => {
    const raw = JSON.stringify({ schema_version: 'run_list_views.v2', items: [example] })
    localStorage.setItem(RUN_LIST_VIEWS_KEY, raw)
    expect(readRunListViews()).toEqual({ status: 'unsupported', items: [] })
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(raw)
  })

  it('rejects malformed JSON, invalid fields, duplicate names and hidden non-boolean', () => {
    expect(decodeRunListViews('{bad').status).toBe('invalid')
    expect(decodeRunListViews(JSON.stringify({ schema_version: 'run_list_views.v1', items: [
      example, { ...example, name: 'MOJE TESTY' }
    ] })).status).toBe('invalid')
    expect(decodeRunListViews(JSON.stringify({ schema_version: 'run_list_views.v1', items: [
      { ...example, hidden: 'false' }
    ] })).status).toBe('invalid')
    expect(isValidRunListView({ ...example, visibility: 'all' })).toBe(true)
    expect(isValidRunListView({ ...example, visibility: 'foreign' })).toBe(false)
  })

  it('rejects additional Run-like or URL fields so they cannot be rewritten as preferences', () => {
    expect(isValidRunListView({ ...example, runSnapshot: { players: [1] } })).toBe(false)
    expect(decodeRunListViews(JSON.stringify({ schema_version: 'run_list_views.v1', items: [
      { ...example, href: 'https://example.com' }
    ] })).status).toBe('invalid')
    expect(decodeRunListViews(JSON.stringify({
      schema_version: 'run_list_views.v1', items: [example], runs: ['run-one']
    })).status).toBe('invalid')
  })

  it('cannot save when storage rejects writes', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
    try {
      expect(writeRunListViews([example])).toBe(false)
    } finally {
      spy.mockRestore()
    }
  })
})
