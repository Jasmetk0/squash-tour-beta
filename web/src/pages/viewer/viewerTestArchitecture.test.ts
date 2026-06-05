import { describe, expect, it } from 'vitest'

const productionSources = import.meta.glob('/src/**/*.{ts,tsx}', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

const testImportPatterns = [
  /from ['"](?:\.\.\/)+test\//,
  /from ['"]\.\/test\//,
  /from ['"]src\/test\//,
  /import\(['"](?:\.\.\/)+test\//,
  /import\(['"]\.\/test\//,
  /import\(['"]src\/test\//,
]

describe('viewer test architecture', () => {
  it('does not import shared test utilities from production source files', () => {
    const offenders = Object.entries(productionSources)
      .filter(([path]) => !path.includes('/src/test/') && !/\.test\.(ts|tsx)$/.test(path))
      .filter(([, source]) => testImportPatterns.some((pattern) => pattern.test(source)))
      .map(([path]) => path.replace('/src/', ''))

    expect(offenders).toEqual([])
  })
})
