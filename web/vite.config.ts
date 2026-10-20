import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // These scripts use node:test and are exercised with node --test in CI.
    exclude: [...configDefaults.exclude, 'scripts/**/*.test.mjs'],
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts'
  }
})
