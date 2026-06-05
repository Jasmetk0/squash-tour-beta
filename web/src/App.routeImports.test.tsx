import { describe, expect, it } from 'vitest'

import appSource from './App.tsx?raw'

describe('App route imports', () => {
  it('imports route page components directly instead of through ModePages', () => {
    expect(appSource).not.toMatch(/from ['"]\.\/pages\/ModePages['"]/)
  })
})
