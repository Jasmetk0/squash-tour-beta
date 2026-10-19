import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { CLIENT, SELECTOR, SELECTOR_TEST, WORKFLOWS,
  classifyImpact, inspectRepository } from './ciHybridBrowserImpact.mjs'

const workflowPath = WORKFLOWS[0]
const scenario = 'web/src/components/HybridRankingClosurePanel.tsx'
const nativePage = 'web/src/pages/CalendarTourPanel.tsx'
const workflow = `name: Hybrid browser
on:
  pull_request:
    paths:
      - '${workflowPath}'
      - '${scenario}'
      - '${CLIENT}'
  workflow_dispatch:
`
const shared = `const API_BASE = 'http://127.0.0.1:8000'
async function request(path: string, init?: RequestInit) {
  const response = await fetch(API_BASE + path, init)
  if (!response.ok) throw new Error('Request failed')
  return response.json()
}
export function getHybrid() { return request('/hybrid') }
`
const original = `export function inspectCalendarTour(run: string) {
  return request('/tour/' + encodeURIComponent(run))
}
`
// A realistic middle-of-file insertion from #1548, including a URL query,
// braces, a quoted brace and a string resembling another declaration.
const addition = `export function inspectCalendarTourRecords(run: string) {
  const params = new URLSearchParams({run, example: '}'})
  return request('/tour/records?' + params.toString())
}
`
function input(update = {}) {
  return { workflowPath, workflow, changedPaths: [CLIENT, nativePage],
    beforeClient: original + shared, afterClient: original + addition + shared,
    beforeConsumers: [[nativePage, "import { inspectCalendarTour } from '../api/client'\n"]],
    afterConsumers: [[nativePage, "import { inspectCalendarTour, inspectCalendarTourRecords } from '../api/client'\n"]],
    ...update }
}

test('native middle insertion or edit skips only unrelated hybrid browser', () => {
  assert.equal(classifyImpact(input()).runBrowser, false)
  assert.equal(classifyImpact(input({afterClient: original.replace('/tour/', '/native/') + shared})).runBrowser, false)
})

for (const change of [
  source => source.replace('response.ok', 'response.status === 200'),
  source => source.replace('127.0.0.1:8000', '127.0.0.1:8001'),
  source => source.replace("request('/hybrid')", "request('/hybrid-new')"),
  source => "import './new-side-effect'\n" + source,
  source => source + "\nfetch('/new-side-effect')\n",
  source => source + '\nexport const initializeCalendarTour = request("/mutate")\n',
]) test(`shared/initialization change cannot skip: ${change(shared).slice(-60)}`, () => {
  assert.equal(classifyImpact(input({afterClient: original + addition + change(shared)})).runBrowser, true)
})

test('native reference from unchanged shared code is not treated as isolated', () => {
  const caller = '\nexport function caller() { return inspectCalendarTourRecords("x") }\n'
  assert.equal(classifyImpact(input({beforeClient: original + shared + caller,
    afterClient: original + addition + shared + caller})).runBrowser, true)
})

for (const consumer of [
  "import { inspectCalendarTourRecords as other } from '../api/client'",
  "import * as api from '../api/client'",
  "export * from '../api/client'",
  "export { getHybrid } from '../api/client'",
  "import api from '../api/client'",
  "const api = import('../api/client')",
  "const api = require('../api/client')",
  'const api = import(moduleName)',
]) test(`non-isolated or reflective consumer must run: ${consumer}`, () => {
  for (const boundary of ['beforeConsumers', 'afterConsumers']) {
    assert.equal(classifyImpact(input({[boundary]: [['web/src/pages/Other.ts', consumer]]})).runBrowser, true)
  }
})

test('normal explicit non-native import does not run irrelevant browser', () => {
  assert.equal(classifyImpact(input({afterConsumers: [
    ['web/src/pages/Other.ts', "import {getHybrid as get} from '../api/client'"],
    ['web/src/main.tsx', "import ReactDOM from 'react-dom/client'"],
  ]})).runBrowser, false)
})

for (const path of [scenario, workflowPath, SELECTOR, SELECTOR_TEST,
  'web/package.json', 'web/package-lock.json']) {
  test(`scenario/selection/dependency changes always run: ${path}`, () => {
    assert.equal(classifyImpact(input({changedPaths: [CLIENT, path]})).runBrowser, true)
  })
}

test('shared backend, arbitrary frontend and fixture changes force the full browser', () => {
  for (const path of ['src/beta_engine/infrastructure/db/repositories.py',
    'src/beta_engine/application/full_simulation_tasks.py', 'web/src/App.tsx',
    'tests/support/shared_fixture.py', 'config/simulation/anything.json']) {
    assert.equal(classifyImpact(input({changedPaths: [CLIENT, path]})).runBrowser, true, path)
  }
})

test('native Tour workflows can never be skipped by this selector', () => {
  for (const workflowPath of ['.github/workflows/prealpha-native-tour-browser.yml',
    '.github/workflows/prealpha-native-tour-api.yml', '.github/workflows/prealpha-native-season-api.yml']) {
    assert.equal(classifyImpact(input({workflowPath})).runBrowser, true)
  }
})

test('unknown YAML, globs, malformed TS and unsupported declarations run', () => {
  for (const update of [
    {workflow: 'on: [pull_request]'},
    {workflow: workflow.replace(scenario, 'web/src/**')},
    {afterClient: original + 'export function inspectCalendarTourRecords( {'},
    {afterClient: original + '\nexport declare function inspectCalendarTourRecords(): void;\n' + shared},
    {afterClient: original + '\nexport default function inspectCalendarTourRecords() {}\n' + shared},
    {afterClient: original + '\nexport function* inspectCalendarTourRecords() {}\n' + shared},
    {afterClient: original + original + shared},
    {changedPaths: [nativePage]},
    {afterConsumers: [['web/src/broken.ts', 'export function (']]},
  ]) assert.equal(classifyImpact(input(update)).runBrowser, true, JSON.stringify(update))
})

test('manual run, missing event/base and missing Git evidence run the browser', () => {
  assert.equal(inspectRepository({workflowPath, eventName: 'workflow_dispatch'}).runBrowser, true)
  assert.equal(inspectRepository({workflowPath, eventName: 'pull_request', eventPath: '/missing'}).runBrowser, true)
})

test('actual Git comparison handles middle insertion, rename/delete and stale/missing base', () => {
  const repo = mkdtempSync(join(tmpdir(), 'hybrid-browser-impact-'))
  try {
    const git = args => execFileSync('git', args, {cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}).trim()
    const write = (path, content) => {
      mkdirSync(join(repo, path, '..'), {recursive: true})
      writeFileSync(join(repo, path), content)
    }
    git(['init', '-q'])
    git(['config', 'user.name', 'CI test'])
    git(['config', 'user.email', 'ci@example.invalid'])
    const commit = () => { git(['add', '.']); git(['commit', '-qm', 'fixture']) }
    write(CLIENT, original + shared)
    write(workflowPath, workflow)
    write(nativePage, "import {inspectCalendarTour} from '../api/client'")
    write(scenario, 'export const hybrid = true')
    write('web/src/Unicode.ts', 'export const label = "Příliš žluťoučký kůň"')
    commit()
    const base = git(['rev-parse', 'HEAD'])
    const eventPath = join(repo, '.git', 'event.json')
    writeFileSync(eventPath, JSON.stringify({pull_request: {base: {sha: base}}}))
    const inspect = () => inspectRepository({workflowPath, eventName: 'pull_request', eventPath, repo})
    write(CLIENT, original + addition + shared)
    commit()
    assert.equal(inspect().runBrowser, false)
    const output = join(repo, '.git', 'outputs.txt')
    const summary = join(repo, '.git', 'summary.md')
    execFileSync(process.execPath, [fileURLToPath(new URL('./ciHybridBrowserImpact.mjs', import.meta.url)), workflowPath], {
      cwd: repo, stdio: 'pipe', env: {...process.env, GITHUB_EVENT_NAME: 'pull_request',
        GITHUB_EVENT_PATH: eventPath, GITHUB_OUTPUT: output, GITHUB_STEP_SUMMARY: summary},
    })
    assert.equal(readFileSync(output, 'utf8'), 'run_browser=false\n')
    assert.match(readFileSync(summary, 'utf8'), /inspectCalendarTourRecords/)
    assert.ok(readFileSync(summary, 'utf8').includes(base))
    git(['mv', scenario, 'web/src/components/Renamed.tsx'])
    commit()
    assert.equal(inspect().runBrowser, true, 'renames must include deleted triggering path')
    writeFileSync(eventPath, JSON.stringify({pull_request: {base: {sha: 'a'.repeat(40)}}}))
    assert.equal(inspect().runBrowser, true, 'unavailable base fails to full browser')
  } finally {
    rmSync(repo, {recursive: true, force: true})
  }
})

test('all real wired hybrid workflows have supported exact filters and selectors', () => {
  for (const path of WORKFLOWS) {
    const source = readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8')
    assert.equal(classifyImpact(input({workflowPath: path, workflow: source,
      changedPaths: [CLIENT]})).runBrowser, false, path)
    assert.match(source, /id: impact/)
    assert.match(source, /if: steps\.impact\.outputs\.run_browser == 'true'/)
  }
})
