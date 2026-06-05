import { describe, expect, it } from 'vitest'

import appSource from '../App.tsx?raw'

const sourceModules = import.meta.glob('../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default'
}) as Record<string, string>

describe('page module architecture', () => {
  it('keeps App route imports decoupled from ModePages', () => {
    expect(appSource).not.toMatch(/from ['"]\.\/pages\/ModePages(?:\.tsx)?['"]/)
  })

  it('keeps source files from importing the retired ModePages barrel', () => {
    const modePagesImports = Object.entries(sourceModules).flatMap(([path, source]) => {
      const matches = source.match(/from ['"][^'"]*ModePages(?:\.tsx)?['"]/g) ?? []
      return matches.map((match) => `${path}: ${match}`)
    })

    expect(modePagesImports).toEqual([])
  })
})
