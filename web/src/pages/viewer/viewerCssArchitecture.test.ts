import { readFileSync } from 'fs'
import { resolve } from 'path'

import { describe, expect, it } from 'vitest'

const stylesSource = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8')

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
})
