import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY, clearViewerActiveRunId, writeViewerActiveRunId } from './activeRun'
import { useActiveViewerRunId } from './useActiveViewerRunId'

describe('useActiveViewerRunId', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns null when no active run is stored', () => {
    const { result } = renderHook(() => useActiveViewerRunId())

    expect(result.current).toBeNull()
  })

  it('returns the stored active run id initially', () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run-a')

    const { result } = renderHook(() => useActiveViewerRunId())

    expect(result.current).toBe('run-a')
  })

  it('updates after writeViewerActiveRunId dispatches the active-run event', () => {
    const { result } = renderHook(() => useActiveViewerRunId())

    act(() => {
      writeViewerActiveRunId('run-b')
    })

    expect(result.current).toBe('run-b')
  })

  it('updates after a storage event when localStorage changes', () => {
    const { result } = renderHook(() => useActiveViewerRunId())

    act(() => {
      localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run-c')
      window.dispatchEvent(new StorageEvent('storage', { key: VIEWER_ACTIVE_RUN_STORAGE_KEY, newValue: 'run-c' }))
    })

    expect(result.current).toBe('run-c')
  })

  it('cleans up listeners without crashing', () => {
    const { unmount } = renderHook(() => useActiveViewerRunId())

    unmount()

    act(() => {
      clearViewerActiveRunId()
      localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run-d')
      window.dispatchEvent(new StorageEvent('storage', { key: VIEWER_ACTIVE_RUN_STORAGE_KEY, newValue: 'run-d' }))
    })
  })
})
