import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  LAST_RUN_ID_STORAGE_KEY,
  VIEWER_ACTIVE_RUN_CHANGED_EVENT,
  VIEWER_ACTIVE_RUN_STORAGE_KEY,
  clearViewerActiveRunId,
  readLastRunId,
  readViewerActiveRunId,
  writeLastRunId,
  writeViewerActiveRunId
} from './activeRun'

describe('Viewer active run storage helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads an empty active run and last run as null', () => {
    expect(readViewerActiveRunId()).toBeNull()
    expect(readLastRunId()).toBeNull()
  })

  it('writes the active run id and dispatches the active-run changed event', () => {
    const listener = vi.fn()
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)

    writeViewerActiveRunId(' run-a ')

    expect(localStorage.getItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)).toBe('run-a')
    expect(readViewerActiveRunId()).toBe('run-a')
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)
  })

  it('writes the last run id without dispatching the active-run changed event', () => {
    const listener = vi.fn()
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)

    writeLastRunId(' run-a ')

    expect(localStorage.getItem(LAST_RUN_ID_STORAGE_KEY)).toBe('run-a')
    expect(readLastRunId()).toBe('run-a')
    expect(listener).not.toHaveBeenCalled()
    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)
  })

  it('ignores blank last run ids', () => {
    writeLastRunId('   ')

    expect(localStorage.getItem(LAST_RUN_ID_STORAGE_KEY)).toBeNull()
    expect(readLastRunId()).toBeNull()
  })

  it('clears the active run id and dispatches the active-run changed event', () => {
    const listener = vi.fn()
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run-a')
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)

    clearViewerActiveRunId()

    expect(readViewerActiveRunId()).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)
  })

  it('keeps storage helper reads and writes safe when localStorage is unavailable', () => {
    const listener = vi.fn()
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)

    expect(readViewerActiveRunId()).toBeNull()
    expect(readLastRunId()).toBeNull()
    expect(() => writeLastRunId('run-a')).not.toThrow()
    expect(() => writeViewerActiveRunId('run-a')).not.toThrow()
    expect(() => clearViewerActiveRunId()).not.toThrow()
    expect(listener).toHaveBeenCalledTimes(2)

    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)
  })

  it('exports the existing localStorage keys and event name', () => {
    expect(VIEWER_ACTIVE_RUN_STORAGE_KEY).toBe('beta_engine:viewer_active_run_id')
    expect(LAST_RUN_ID_STORAGE_KEY).toBe('beta_engine:last_run_id')
    expect(VIEWER_ACTIVE_RUN_CHANGED_EVENT).toBe('beta_engine:viewer_active_run_changed')
  })
})
