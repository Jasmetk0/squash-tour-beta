import { describe, expect, it } from 'vitest'

import {
  appShellClassNameForMode,
  appShellSubtitleForMode,
  appShellTitleForMode,
  readAppShellMode,
  readAppShellRunId,
  resolveAdminScope
} from './appShellMode'

describe('appShellMode', () => {
  it('reads Admin, Viewer, and landing shell modes from pathnames', () => {
    expect(readAppShellMode('/admin')).toBe('admin')
    expect(readAppShellMode('/admin/runs/run-a/finals')).toBe('admin')
    expect(readAppShellMode('/viewer')).toBe('viewer')
    expect(readAppShellMode('/viewer/runs/run-a/rankings')).toBe('viewer')
    expect(readAppShellMode('/')).toBe('landing')
    expect(readAppShellMode('/something-else')).toBe('landing')
  })

  it('reads run IDs without decoding path segments and lets route params win', () => {
    expect(readAppShellRunId('/admin/runs/run-a/finals')).toBe('run-a')
    expect(readAppShellRunId('/viewer/runs/run-a/rankings')).toBe('run-a')
    expect(readAppShellRunId('/admin/runs/new')).toBeUndefined()
    expect(readAppShellRunId('/viewer/runs/new/calendar')).toBeUndefined()
    expect(readAppShellRunId('/admin/runs/run%20alpha/finals')).toBe('run%20alpha')
    expect(readAppShellRunId('/viewer', 'param-run')).toBe('param-run')
    expect(readAppShellRunId('/viewer')).toBeUndefined()
  })

  it('derives Global and Run Admin scopes from the route', () => {
    expect(resolveAdminScope('/admin')).toEqual({ kind: 'global' })
    expect(resolveAdminScope('/admin/world')).toEqual({ kind: 'global' })
    expect(resolveAdminScope('/admin/runs')).toEqual({ kind: 'global' })
    expect(resolveAdminScope('/admin/runs/new')).toEqual({ kind: 'global' })
    expect(resolveAdminScope('/admin/runs/run-a')).toEqual({ kind: 'run', runId: 'run-a' })
    expect(resolveAdminScope('/admin/runs/run-a/finals')).toEqual({ kind: 'run', runId: 'run-a' })
    expect(resolveAdminScope('/viewer/runs/run-a')).toEqual({ kind: 'global' })
  })

  it('returns stable title, subtitle, and class name strings for each shell mode', () => {
    expect(appShellTitleForMode('viewer')).toBe('MSA Squash')
    expect(appShellTitleForMode('admin')).toBe('Squash Tour Beta Engine')
    expect(appShellTitleForMode('landing')).toBe('Squash Tour Beta Engine')

    expect(appShellSubtitleForMode('admin')).toBe('Admin / Engine Mode')
    expect(appShellSubtitleForMode('viewer')).toBe('Viewer / MSA Website Mode')
    expect(appShellSubtitleForMode('landing')).toBe('Mode selection')

    expect(appShellClassNameForMode('admin')).toBe('app-shell app-shell--admin')
    expect(appShellClassNameForMode('viewer')).toBe('app-shell app-shell--viewer')
    expect(appShellClassNameForMode('landing')).toBe('app-shell app-shell--landing')
  })
})
