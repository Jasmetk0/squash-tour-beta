import { readFileSync } from 'fs'
import { resolve } from 'path'

import { describe, expect, it } from 'vitest'

const stylesSource = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8')

const cssBlockFor = (selector: string) => {
  const start = stylesSource.indexOf(selector)
  expect(start).toBeGreaterThanOrEqual(0)
  const end = stylesSource.indexOf('}\n', start)
  expect(end).toBeGreaterThan(start)
  return stylesSource.slice(start, end + 1)
}

describe('viewer CSS architecture guards', () => {
  it('keeps shared Viewer class hooks and excludes the jump-demo pseudo-element risk', () => {
    expect(stylesSource).not.toContain('.viewer-jump-demo::before')
    expect(stylesSource).toContain('.viewer-active-run-panel::before')
    expect(stylesSource).toContain('.viewer-active-run-card::before')
    expect(stylesSource).toContain('.viewer-home-card::before')
    expect(stylesSource).toContain('.viewer-metadata-list')
    expect(stylesSource).toContain('.viewer-status-message--loading')
    expect(stylesSource).toContain('.viewer-run-browser-list')
  })

  it('keeps Viewer responsive and focus accessibility guards in shared CSS', () => {
    expect(stylesSource).toContain('.viewer-topbar a:focus-visible')
    expect(stylesSource).toContain('.viewer-topbar-search input:focus-visible')
    expect(stylesSource).toContain('.viewer-active-run-link:focus-visible')
    expect(stylesSource).toContain('overflow-wrap: anywhere')
    expect(stylesSource).toContain('grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr))')
    expect(stylesSource).toContain('@media (max-width: 560px)')
  })

  it('keeps narrow Viewer wrapping and viewport safety contracts in shared CSS', () => {
    const topbarBlock = cssBlockFor('.viewer-topbar {')
    const searchBlock = cssBlockFor('.viewer-topbar-search {')
    const activeRunCardBlock = cssBlockFor('.viewer-active-run-panel,\n.viewer-active-run-card {')
    const activeRunLinkBlock = cssBlockFor('.viewer-active-run-link {')
    const dropdownMenuBlock = cssBlockFor('.viewer-dropdown__menu {')

    expect(topbarBlock).toContain('max-width: 100%')
    expect(searchBlock).toContain('max-width: 100%')
    expect(activeRunCardBlock).toContain('min-width: 0')
    expect(activeRunLinkBlock).toContain('white-space: normal')
    expect(activeRunLinkBlock).toContain('overflow-wrap: anywhere')
    expect(dropdownMenuBlock).toContain('min-width: min(')
    expect(dropdownMenuBlock).toContain('100vw')
  })
})
