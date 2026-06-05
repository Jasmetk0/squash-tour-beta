import { readFileSync } from 'fs'
import { resolve } from 'path'

import { describe, expect, it } from 'vitest'

const manualQaSource = readFileSync(
  resolve(process.cwd(), '../docs/viewer_phase_1_manual_qa.md'),
  'utf8',
)

describe('viewer visual QA documentation guard', () => {
  it('keeps the Phase 7D responsive, accessibility, and read-only checklist anchors', () => {
    expect(manualQaSource).toContain('Responsive and accessibility visual QA')
    expect(manualQaSource).toContain('Desktop width')
    expect(manualQaSource).toContain('Tablet width')
    expect(manualQaSource).toContain('Mobile width')
    expect(manualQaSource).toContain('Keyboard-only navigation')
    expect(manualQaSource).toContain('Viewer read-only safety')
    expect(manualQaSource).toContain('No horizontal page scroll')
    expect(manualQaSource).toContain('topbar links')
    expect(manualQaSource).toContain('search input')
    expect(manualQaSource).toContain('active-run links')
    expect(manualQaSource).toContain('forbidden mutation labels')
  })
})
