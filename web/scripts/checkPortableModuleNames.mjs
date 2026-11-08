import { readdirSync } from 'node:fs'
import { extname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../src/', import.meta.url))
const scriptExtensions = new Set(['.ts', '.tsx', '.js', '.jsx'])
const names = new Map()
const stems = new Map()

function claim(index, key, path) {
  const previous = index.get(key.toLowerCase())
  if (previous !== undefined && previous !== path) {
    throw new Error(`Frontend paths must be distinct on Windows: ${previous} and ${path}`)
  }
  index.set(key.toLowerCase(), path)
}

function scan(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = resolve(directory, entry.name)
    const path = relative(root, full)
    claim(names, path, path)
    if (entry.isDirectory()) {
      scan(full)
    } else if (entry.isFile() && scriptExtensions.has(extname(path))) {
      // TypeScript's extensionless imports also collide across .ts and .tsx.
      claim(stems, path.slice(0, -extname(path).length), path)
    }
  }
}

scan(root)
