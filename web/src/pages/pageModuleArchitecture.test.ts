import { describe, expect, it } from 'vitest'

import appSource from '../App.tsx?raw'
import cardSource from './viewer/deferred/ViewerDeferredSourceCard.tsx?raw'
import pureMetadataSource from './viewer/deferred/viewerDeferredSourceMetadata.ts?raw'

const sourceModules = import.meta.glob('../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default'
}) as Record<string, string>

function hasSourceModule(pathSuffix: string): boolean {
  return Object.keys(sourceModules).some((path) =>
    path.endsWith(pathSuffix) || path.endsWith(pathSuffix.replace(/^\//, '')),
  )
}

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

  it('keeps Viewer deferred source metadata render imports unambiguous', () => {
    expect(hasSourceModule('viewer/deferred/ViewerDeferredSourceMetadata.ts')).toBe(false)
    expect(hasSourceModule('viewer/deferred/ViewerDeferredSourceMetadata.tsx')).toBe(false)
    expect(hasSourceModule('viewer/deferred/ViewerDeferredSourceMetadataRender.tsx')).toBe(true)
    expect(cardSource).toContain("from './ViewerDeferredSourceMetadataRender'")
    expect(cardSource).not.toMatch(/from ['"]\.\/ViewerDeferredSourceMetadata['"]/)
  })

  it('keeps React render helpers out of the pure Viewer deferred metadata module', () => {
    expect(pureMetadataSource).not.toMatch(/renderSourceMetadataList|renderDeferredSourceLinks|commonDeferredSourceMetadataItems/)

    const renderHelperImportFromPureModule = Object.entries(sourceModules)
      .filter(([path]) => path.includes('viewer/deferred/'))
      .flatMap(([path, source]) => {
        const matches = source.match(/import\s+\{[^}]*\b(?:renderSourceMetadataList|renderDeferredSourceLinks|commonDeferredSourceMetadataItems)\b[^}]*\}\s+from ['"]\.\/viewerDeferredSourceMetadata['"]/g) ?? []
        return matches.map((match) => `${path}: ${match}`)
      })

    expect(renderHelperImportFromPureModule).toEqual([])
  })

})
