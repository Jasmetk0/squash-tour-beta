import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { changeLabField, changePlayerWeeks, labChangedPaths, LabScenarioAuthoring, readLabScenario } from './LabScenarioAuthoring'

vi.mock('../../i18n/LanguageContext', () => ({useLanguage: () => ({language: 'en'})}))

const match = {
  schema_version: 'match_test_lab_scenario.v1',
  scenario_id: 'importable',
  seed: 42,
  source_kind: 'run_snapshot_copy',
  source_reference: 'historical-revision',
  source_fingerprint: 'a'.repeat(64),
  context: {
    best_of: 5, games_to: 11, win_by: 2, upset_variance: 0.12,
    player_a: {player: {hidden_metadata: {origin: 'original'}}},
    extra: {future_input: [1, 2, 3]}
  }
}
const tournament = {
  schema_version: 'tournament_test_lab_scenario.v1',
  scenario_id: 'bracket',
  display_name: 'Bracket',
  participants: [{player_id: 'P1'}, {player_id: 'P2'}],
  match_format: {best_of: 5, games_to: 11, win_by: 2, upset_variance: 0.12},
  draw_seed: 10, match_seed: 11,
  source_snapshot: {saved_revision_id: 'immutable', extra: {keep: true}},
  source_kind: 'run_snapshot_copy'
}
const player = {
  schema_version: 'player_test_lab_scenario.v2',
  scenario_id: 'development',
  seed: 8,
  source_snapshot: {saved_revision_id: 'original', player: {player_id: 'A'}},
  variants: [
    {variant_id: 'a', competitive_match_counts: [1, 2], note: {extra: true}},
    {variant_id: 'b', competitive_match_counts: [0, 0]}
  ]
}

describe('Lab scenario authoring boundaries', () => {
  it('requires the exact Lab type/version and a scenario rather than Session/result envelopes', () => {
    expect(readLabScenario(JSON.stringify(match), 'match')).toEqual(match)
    expect(readLabScenario(JSON.stringify(tournament), 'tournament')).toEqual(tournament)
    expect(readLabScenario(JSON.stringify(player), 'player')).toEqual(player)
    expect(() => readLabScenario(JSON.stringify(match), 'tournament')).toThrow('version')
    expect(() => readLabScenario(JSON.stringify({...match, schema_version: 'match_test_lab_scenario.v9'}), 'match')).toThrow('version')
    expect(() => readLabScenario(JSON.stringify({schema_version: 'match_test_lab_session.v1', scenario: match}), 'match')).toThrow('version')
    expect(() => readLabScenario('[]', 'match')).toThrow('object')
    expect(() => readLabScenario('not-json', 'match')).toThrow('syntax')
  })

  it('edits only the selected nested field while preserving unknown attributes and exact provenance', () => {
    const changed = JSON.parse(changeLabField(JSON.stringify(match), 'match', {
      path: ['context', 'best_of'], en: 'Best of', cs: 'Sety', min: 1, max: 9, integer: true, odd: true
    }, '3'))
    expect(changed.context.best_of).toBe(3)
    expect(changed.context.player_a).toEqual(match.context.player_a)
    expect(changed.context.extra).toEqual(match.context.extra)
    expect(changed.source_reference).toBe(match.source_reference)
    expect(changed.source_fingerprint).toBe(match.source_fingerprint)
    expect(() => changeLabField(JSON.stringify(match), 'match', {
      path: ['context', 'best_of'], en: 'Best of', cs: 'Sety', min: 1, max: 9, integer: true, odd: true
    }, '4')).toThrow('number')
    expect(JSON.parse(changeLabField(JSON.stringify(tournament), 'tournament', {
      path: ['draw_seed'], en: 'Draw seed', cs: 'Seed', integer: true
    }, '99')).source_snapshot).toEqual(tournament.source_snapshot)
  })

  it('extends all Player workload variants with explicit zero-match weeks without changing source evidence', () => {
    const extended = JSON.parse(changePlayerWeeks(JSON.stringify(player), 4))
    expect(extended.variants.map((v: {competitive_match_counts: number[]}) => v.competitive_match_counts))
      .toEqual([[1, 2, 0, 0], [0, 0, 0, 0]])
    expect(extended.source_snapshot).toEqual(player.source_snapshot)
    expect(extended.variants[0].note).toEqual(player.variants[0].note)
    expect(JSON.parse(changePlayerWeeks(JSON.stringify(extended), 1)).variants[0].competitive_match_counts).toEqual([1])
    expect(() => changePlayerWeeks(JSON.stringify(player), 62)).toThrow('weeks')
    expect(() => changePlayerWeeks(JSON.stringify({...player, variants: [
      {...player.variants[0], health_timeline: [{}, {}, {}]}, player.variants[1]
    ]}), 3)).toThrow('health')
  })

  it('reports changed JSON paths against a saved Session without mutating the baseline', () => {
    const edited = {...match, seed: 99, context: {...match.context, best_of: 3}}
    expect(labChangedPaths(match, edited)).toEqual(['seed', 'context.best_of'])
    expect(match.seed).toBe(42)
    expect(labChangedPaths(match, match)).toEqual([])
  })

  it('lets the user switch between guided and advanced editing without losing historical fields', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match, null, 2))
      return <LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
    }
    const user = userEvent.setup()
    render(<Harness />)
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'form')
    fireEvent.change(screen.getByLabelText('match Lab context.best_of'), {target: {value: '3'}})
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'json')
    const text = (screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value
    expect(JSON.parse(text).context.best_of).toBe(3)
    expect(JSON.parse(text).source_fingerprint).toBe(match.source_fingerprint)
    expect(JSON.parse(text).context.extra).toEqual(match.context.extra)
  })

  it('rejects an unrelated uploaded scenario and never replaces the draft', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      return <><LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
        <output data-testid="current">{text}</output></>
    }
    const user = userEvent.setup()
    render(<Harness />)
    const file = new File([JSON.stringify(tournament)], 'other.json', {type: 'application/json'})
    Object.defineProperty(file, 'text', {value: () => Promise.resolve(JSON.stringify(tournament))})
    await user.upload(screen.getByLabelText('match Lab JSON file'), file)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unsupported scenario type')
    expect(screen.getByTestId('current').textContent).toBe(JSON.stringify(match))
  })

  it('does not install a late file read over a newer scenario edit', async () => {
    let finish!: (value: string) => void
    const pending = new Promise<string>(resolve => {finish = resolve})
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      return <LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
    }
    const user = userEvent.setup()
    render(<Harness />)
    const file = new File(['{}'], 'late.json', {type: 'application/json'})
    Object.defineProperty(file, 'text', {value: () => pending})
    await user.upload(screen.getByLabelText('match Lab JSON file'), file)
    const textarea = screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement
    fireEvent.change(textarea, {target: {value: JSON.stringify({...match, seed: 91})}})
    finish(JSON.stringify({...match, seed: 111}))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('The editor changed'))
    expect(JSON.parse(textarea.value).seed).toBe(91)
  })
})
