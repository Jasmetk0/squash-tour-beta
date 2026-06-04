import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  LAST_RUN_ID_STORAGE_KEY,
  VIEWER_ACTIVE_RUN_CHANGED_EVENT,
  VIEWER_ACTIVE_RUN_STORAGE_KEY,
  clearViewerActiveRunId,
  readLastRunId,
  readViewerActiveRunId,
  writeViewerActiveRunId
} from './activeRun'
import {
  buildViewerActiveRunQuickLinks,
  formatViewerActiveRunLabel,
  formatViewerCompactRunOptionLabel,
  formatViewerRunOptionLabel
} from './activeRunDisplay'

describe('Viewer active run storage helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('reads an empty active run as null', () => {
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

  it('clears the active run id and dispatches the active-run changed event', () => {
    const listener = vi.fn()
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run-a')
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)

    clearViewerActiveRunId()

    expect(readViewerActiveRunId()).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, listener)
  })

  it('exports the existing localStorage keys and event name', () => {
    expect(VIEWER_ACTIVE_RUN_STORAGE_KEY).toBe('beta_engine:viewer_active_run_id')
    expect(LAST_RUN_ID_STORAGE_KEY).toBe('beta_engine:last_run_id')
    expect(VIEWER_ACTIVE_RUN_CHANGED_EVENT).toBe('beta_engine:viewer_active_run_changed')
  })
})

describe('Viewer active run display helpers', () => {
  const run = {
    run_id: 'run-a',
    season: 2030,
    seed: 9,
    config_version: null,
    config_fingerprint: null,
    next_event_index: 0,
    total_events: 4,
    completed_event_ids: []
  }

  it('formats selector labels without changing existing text', () => {
    expect(formatViewerRunOptionLabel(run)).toBe('run-a — season 2030, seed 9')
    expect(formatViewerCompactRunOptionLabel(run)).toBe('run-a · S2030 · seed 9')
    expect(formatViewerActiveRunLabel(null)).toBe('None')
    expect(formatViewerActiveRunLabel('run-a')).toBe('run-a')
  })

  it('builds the active run quick links in the existing label and href order', () => {
    expect(buildViewerActiveRunQuickLinks('run alpha')).toEqual([
      { label: 'Open calendar', to: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Open rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open tournaments', to: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Open players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Open countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'Open history', to: '/viewer/runs/run%20alpha/history' },
      { label: 'Open finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
  })
})
