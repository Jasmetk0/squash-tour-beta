import { describe, expect, it } from 'vitest'

import appSource from '../App.tsx?raw'

const sourceModules = import.meta.glob('../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default'
}) as Record<string, string>

describe('page module architecture', () => {
  it('keeps the retired ModePages file deleted', () => {
    expect(sourceModules).not.toHaveProperty('../pages/ModePages.tsx')
  })

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

  it('keeps page-family modules from importing through local index barrels', () => {
    const localBarrelImports = Object.entries(sourceModules)
      .filter(([path]) => path.startsWith('../pages/'))
      .flatMap(([path, source]) => {
        const matches = source.match(/from ['"](?:\.\/index|\.\.\/index)['"]/g) ?? []
        return matches.map((match) => `${path}: ${match}`)
      })

    expect(localBarrelImports).toEqual([])
  })
})
