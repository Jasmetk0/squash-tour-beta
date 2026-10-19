/** Conservative exception for native-Tour-only edits to the shared API client.
 * All uncertainty, shared transport changes, and scenario changes run the browser.
 * This never selects or weakens the native Tour API/browser acceptance gates.
 */
import { execFileSync } from 'node:child_process'
import { appendFileSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { posix, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const require = createRequire(new URL('../package.json', import.meta.url))
const ts = require('typescript')
export const CLIENT = 'web/src/api/client.ts'
const NATIVE_PAGE = 'web/src/pages/CalendarTourPanel.tsx'
export const SELECTOR = 'web/scripts/ciHybridBrowserImpact.mjs'
export const SELECTOR_TEST = 'web/scripts/ciHybridBrowserImpact.test.mjs'
export const WORKFLOWS = [
  'prealpha-hybrid-format-browser.yml',
  'prealpha-hybrid-multiround-browser.yml',
  'prealpha-full-sim-real-hybrid-week-browser.yml',
  'prealpha-full-sim-real-hybrid-second-week-browser.yml',
  'prealpha-full-sim-same-parent-restart-browser.yml',
  'prealpha-full-sim-week61-save-boundary-browser.yml',
].map(name => `.github/workflows/${name}`)

const run = reason => ({ runBrowser: true, reason })
const nativeName = name => /^(inspect|preview|execute|save)CalendarTour[A-Z\da-z_]*$/.test(name)

function nativeOnlyPath(path) {
  // Do not rely on incomplete historical workflow filters to pronounce another
  // subsystem independent. Any extra production/config/test-support path runs.
  return [CLIENT, NATIVE_PAGE, 'web/src/pages/CalendarTourPanel.test.tsx',
    'web/src/api/calendarTour.ts', 'web/src/api/calendarTour.test.ts',
    'src/beta_engine/api/routers/admin_calendar_tour.py',
    'src/beta_engine/api/routers/viewer_calendar_tour.py',
    'src/beta_engine/domain/tournaments/calendar_tour.py',
    'src/beta_engine/infrastructure/db/calendar_tour.py',
    'tests/api/test_calendar_tour_flow.py',
    'tests/api/test_native_calendar_season_transition.py',
    'tests/api/test_native_cross_season_edition.py',
  ].includes(path)
    || /^src\/beta_engine\/application\/calendar_tour_[a-z_]+\.py$/.test(path)
    || /^tests\/(application|domain)\/test_calendar_tour_[a-z_]+\.py$/.test(path)
    || /^[^/]+\.md$/.test(path) || /^docs\/.+\.md$/.test(path)
}

function parse(source, path) {
  const ast = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true,
    path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
  if (ast.parseDiagnostics.length) throw new Error(`Unparseable TypeScript: ${path}`)
  return ast
}

function splitClient(source) {
  const ast = parse(source, CLIENT)
  const native = new Map()
  const shared = []
  for (const statement of ast.statements) {
    const name = statement.name?.text
    if (ts.isFunctionDeclaration(statement) && name && nativeName(name)) {
      const modifiers = statement.modifiers ?? []
      if (!statement.body || statement.asteriskToken || native.has(name)
          || !modifiers.some(m => m.kind === ts.SyntaxKind.ExportKeyword)
          || modifiers.some(m => ![ts.SyntaxKind.ExportKeyword, ts.SyntaxKind.AsyncKeyword].includes(m.kind))) {
        throw new Error('Unsupported native declaration')
      }
      native.set(name, statement.getText(ast))
    } else {
      shared.push(statement)
    }
  }
  // An unchanged shared caller could start invoking a newly added declaration.
  // Disallow any native-name reference outside the isolated function bodies.
  for (const statement of shared) {
    visit(statement, node => {
      if (ts.isIdentifier(node) && nativeName(node.text)) {
        throw new Error('Native function referenced by shared client code')
      }
    })
  }
  return { native, shared: shared.map(statement => statement.getText(ast)) }
}

function visit(node, check) {
  check(node)
  ts.forEachChild(node, child => visit(child, check))
}

function isClientSpecifier(target, path) {
  if (target.startsWith('.')) {
    return posix.normalize(posix.join(posix.dirname(path), target))
      .replace(/\.[cm]?[jt]s$/, '') === CLIENT.replace(/\.ts$/, '')
  }
  // This package entry point is unrelated to our application API client.
  // Unknown aliases ending in /client are conservative, not silently resolved.
  return target !== 'react-dom/client' && /(?:^|\/)client(?:\.[cm]?[jt]s)?$/.test(target)
}

function checkConsumers(files) {
  for (const [path, source] of files) {
    if (path === CLIENT || /\.(test|spec)\.[cm]?[jt]sx?$/.test(path)
        || path.startsWith('web/src/test/')) continue
    const ast = parse(source, path)
    visit(ast, node => {
      // Only this dedicated page may consume the isolated native function family.
      if (path !== NATIVE_PAGE && ts.isIdentifier(node) && nativeName(node.text)) {
        throw new Error(`Native API referenced outside its dedicated page: ${path}`)
      }
      if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node))
          && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)
          && isClientSpecifier(node.moduleSpecifier.text, path)) {
        if (ts.isExportDeclaration(node) || !node.importClause
            || node.importClause.name
            || !node.importClause.namedBindings
            || !ts.isNamedImports(node.importClause.namedBindings)) {
          throw new Error(`Non-explicit shared-client consumer: ${path}`)
        }
      }
      if (ts.isCallExpression(node) && (
        node.expression.kind === ts.SyntaxKind.ImportKeyword
        || (ts.isIdentifier(node.expression) && node.expression.text === 'require')
      )) {
        const target = node.arguments[0]
        if (!target || !ts.isStringLiteral(target)
            || isClientSpecifier(target.text, path)) {
          throw new Error(`Dynamic shared-client consumer: ${path}`)
        }
      }
    })
  }
}

function exactWorkflowPaths(workflow) {
  // All six supported workflows have exact, single-quoted path entries.
  // A new YAML shape/glob must first gain explicit support; uncertainty runs.
  const block = workflow.match(/^  pull_request:\n    paths:\n((?:      - '[^'\n]+'\n)+)  workflow_dispatch:/m)
  if (!block) throw new Error('Unknown workflow path-filter structure')
  const paths = [...block[1].matchAll(/      - '([^'\n]+)'/g)].map(m => m[1])
  if (!paths.includes(CLIENT) || paths.some(p => /[*?!\[\]{}]/.test(p))) {
    throw new Error('Unknown workflow path patterns')
  }
  return paths
}

export function classifyImpact({ workflowPath, workflow, changedPaths, beforeClient,
  afterClient, beforeConsumers, afterConsumers }) {
  try {
    if (!WORKFLOWS.includes(workflowPath)) return run('Workflow outside the bounded hybrid exception')
    const paths = exactWorkflowPaths(workflow)
    const always = [workflowPath, SELECTOR, SELECTOR_TEST,
      'web/package.json', 'web/package-lock.json']
    if (changedPaths.some(path => always.includes(path))) return run('Workflow, selector or dependency configuration changed')
    if (changedPaths.some(path => path !== CLIENT && paths.includes(path))) {
      return run('Hybrid scenario source changed')
    }
    if (!changedPaths.includes(CLIENT)) return run('Not a shared-client-only trigger')
    if (changedPaths.some(path => !nativeOnlyPath(path))) {
      return run('Changes extend beyond the verified native Tour scope')
    }
    const before = splitClient(beforeClient)
    const after = splitClient(afterClient)
    if (JSON.stringify(before.shared) !== JSON.stringify(after.shared)) {
      return run('Shared client declarations or transport changed')
    }
    checkConsumers(typeof beforeConsumers === 'function' ? beforeConsumers() : beforeConsumers)
    checkConsumers(typeof afterConsumers === 'function' ? afterConsumers() : afterConsumers)
    return { runBrowser: false,
      nativeFunctions: [...new Set([...before.native.keys(), ...after.native.keys()])]
        .filter(name => before.native.get(name) !== after.native.get(name)).sort(),
      reason: 'Only isolated native Tour function declarations changed; native gates remain mandatory' }
  } catch (error) {
    return run(`Conservative fallback: ${error.message}`)
  }
}

export function inspectRepository({ workflowPath, eventName, eventPath, repo = process.cwd() }) {
  if (eventName !== 'pull_request') return run('Manual/non-PR execution always runs the full browser')
  try {
    const base = JSON.parse(readFileSync(eventPath, 'utf8')).pull_request.base.sha
    if (!/^[0-9a-f]{40}$/.test(base)) return run('Missing valid PR base SHA')
    const git = args => execFileSync('git', args, {
      cwd: repo, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
      timeout: 30_000, stdio: ['ignore', 'pipe', 'pipe'],
    })
    try { git(['cat-file', '-e', `${base}^{commit}`]) }
    catch { git(['fetch', '--no-tags', '--depth=1', 'origin', base]) }
    const changedPaths = git(['diff', '--name-only', '--no-renames', '-z', base, 'HEAD'])
      .split('\0').filter(Boolean)
    const consumers = ref => {
      const paths = git(['ls-tree', '-r', '--name-only', '-z', ref, '--', 'web/src'])
        .split('\0').filter(path => /\.[jt]sx?$/.test(path)
          && !/\.(test|spec)\.[jt]sx?$/.test(path) && !path.startsWith('web/src/test/'))
      if (paths.some(path => /[\r\n]/.test(path))) throw new Error('Unsupported source filename')
      // One process for the complete tree, not hundreds of git-show processes.
      const batch = execFileSync('git', ['cat-file', '--batch'], {
        cwd: repo, input: paths.map(path => `${ref}:${path}\n`).join(''),
        maxBuffer: 32 * 1024 * 1024, timeout: 30_000,
        stdio: ['pipe', 'pipe', 'pipe'],
      })
      let offset = 0
      return paths.map(path => {
        const end = batch.indexOf(10, offset)
        const header = batch.subarray(offset, end).toString('utf8').match(/^[0-9a-f]{40} blob (\d+)$/)
        if (end < offset || !header) throw new Error(`Missing source blob: ${path}`)
        const size = Number(header[1])
        offset = end + 1
        if (offset + size >= batch.length || batch[offset + size] !== 10) {
          throw new Error(`Truncated source blob: ${path}`)
        }
        const source = batch.subarray(offset, offset + size).toString('utf8')
        offset += size + 1
        return [path, source]
      })
    }
    const decision = classifyImpact({
      workflowPath, changedPaths,
      workflow: git(['show', `HEAD:${workflowPath}`]),
      beforeClient: git(['show', `${base}:${CLIENT}`]),
      afterClient: git(['show', `HEAD:${CLIENT}`]),
      beforeConsumers: () => consumers(base), afterConsumers: () => consumers('HEAD'),
    })
    return { ...decision, baseSha: base, headSha: git(['rev-parse', 'HEAD']).trim() }
  } catch (error) {
    return run(`Conservative repository fallback: ${error.message}`)
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const result = inspectRepository({ workflowPath: process.argv[2],
    eventName: process.env.GITHUB_EVENT_NAME, eventPath: process.env.GITHUB_EVENT_PATH })
  console.log(JSON.stringify(result))
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT,
    `run_browser=${result.runBrowser}\n`)
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    `### Hybrid browser selection\n\n${result.runBrowser ? 'Run' : 'Skip'}: ${result.reason}\n`
    + (result.baseSha ? `\nCompared \`${result.baseSha}\` → \`${result.headSha}\`.\n` : '')
    + (result.nativeFunctions?.length ? `\nIsolated functions: ${result.nativeFunctions.join(', ')}.\n` : ''))
}
