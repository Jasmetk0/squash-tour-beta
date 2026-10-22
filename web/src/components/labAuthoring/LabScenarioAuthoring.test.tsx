import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { changeLabField, changePlayerMatchCounts, changePlayerWeeks, labChangedPaths, labChangeDetails, LabScenarioAuthoring, readLabScenario } from './LabScenarioAuthoring'

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

  it('edits one Player workload without modifying other variants or the historical Health timeline', () => {
    const withHealth = {...player, variants: [
      {...player.variants[0], health_timeline: [{state: 'start'}, {state: 'week1'}, {state: 'week2'}]},
      player.variants[1]
    ]}
    const changed = JSON.parse(changePlayerMatchCounts(JSON.stringify(withHealth), 0, '0, 32'))
    expect(changed.variants[0].competitive_match_counts).toEqual([0, 32])
    expect(changed.variants[1].competitive_match_counts).toEqual([0, 0])
    expect(changed.variants[0].health_timeline).toEqual([{state: 'start'}, {state: 'week1'}, {state: 'week2'}])
    expect(changed.source_snapshot).toEqual(withHealth.source_snapshot)
    expect(() => changePlayerMatchCounts(JSON.stringify(withHealth), 0, '1, 2, 3')).toThrow('counts')
    expect(() => changePlayerMatchCounts(JSON.stringify(withHealth), 0, '1, 33')).toThrow('counts')
    expect(() => changePlayerMatchCounts(JSON.stringify(withHealth), 0, '1, 2.5')).toThrow('counts')
  })

  it('requires an explicit Apply before shortening a Player workload', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(player))
      return <><LabScenarioAuthoring kind="player" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Player Lab scenario JSON" />
        <output data-testid="player-draft">{text}</output></>
    }
    const user = userEvent.setup()
    render(<Harness />)
    await user.selectOptions(screen.getByLabelText('player Lab editor mode'), 'form')
    const duration = screen.getByLabelText('player Lab experiment duration')
    await user.clear(duration)
    await user.type(duration, '1')
    expect(JSON.parse(screen.getByTestId('player-draft').textContent ?? '').variants[0].competitive_match_counts).toEqual([1, 2])
    await user.click(screen.getByRole('button', {name: 'Apply duration'}))
    const changed = JSON.parse(screen.getByTestId('player-draft').textContent ?? '')
    expect(changed.variants[0].competitive_match_counts).toEqual([1])
    expect(changed.source_snapshot).toEqual(player.source_snapshot)
  })

  it('reports changed JSON paths against a saved Session without mutating the baseline', () => {
    const edited = {...match, seed: 99, context: {...match.context, best_of: 3}}
    expect(labChangedPaths(match, edited)).toEqual(['seed', 'context.best_of'])
    expect(labChangeDetails(match, edited)).toEqual([
      {path: 'seed', before: '42', after: '99'},
      {path: 'context.best_of', before: '5', after: '3'}
    ])
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
    // An incomplete scalar input does not change the authoritative editor buffer.
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'json')
    expect(JSON.parse((screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value).context.best_of).toBe(5)
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'form')
    fireEvent.change(screen.getByLabelText('match Lab context.best_of'), {target: {value: '3'}})
    await user.click(screen.getByRole('button', {name: 'match Lab apply context.best_of'}))
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'json')
    const text = (screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value
    expect(JSON.parse(text).context.best_of).toBe(3)
    expect(JSON.parse(text).source_fingerprint).toBe(match.source_fingerprint)
    expect(JSON.parse(text).context.extra).toEqual(match.context.extra)
  })

  it('does not commit a partially typed invalid guided number', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      return <><LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
        <output data-testid="scenario">{text}</output></>
    }
    const user = userEvent.setup()
    render(<Harness />)
    await user.selectOptions(screen.getByLabelText('match Lab editor mode'), 'form')
    const input = screen.getByLabelText('match Lab context.best_of')
    await user.clear(input)
    expect(JSON.parse(screen.getByTestId('scenario').textContent ?? '').context.best_of).toBe(5)
    await user.type(input, '4')
    await user.click(screen.getByRole('button', {name: 'match Lab apply context.best_of'}))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid number')
    expect(JSON.parse(screen.getByTestId('scenario').textContent ?? '').context.best_of).toBe(5)
    await user.clear(input)
    await user.type(input, '7')
    await user.click(screen.getByRole('button', {name: 'match Lab apply context.best_of'}))
    expect(JSON.parse(screen.getByTestId('scenario').textContent ?? '').context.best_of).toBe(7)
    expect(JSON.parse(screen.getByTestId('scenario').textContent ?? '').source_fingerprint).toBe(match.source_fingerprint)
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


  it('stages a valid file for review, then applies only to the draft after an explicit click', async () => {
    const save = vi.fn(), run = vi.fn()
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      return <><LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
        <output data-testid="draft">{text}</output>
        <button type="button" onClick={save}>Save manually</button>
        <button type="button" onClick={run}>Run manually</button></>
    }
    render(<Harness />)
    const incoming = {...match, seed: 210, source_reference: 'new-saved-copy'}
    const file = new File([JSON.stringify(incoming)], 'importable.json', {type: 'application/json'})
    Object.defineProperty(file, 'text', {value: () => Promise.resolve(JSON.stringify(incoming))})
    const user = userEvent.setup()
    await user.upload(screen.getByLabelText('match Lab JSON file'), file)
    expect(await screen.findByText('File ready for review. Editor, Session and Run are unchanged.')).toBeInTheDocument()
    expect(JSON.parse(screen.getByTestId('draft').textContent ?? '')).toEqual(match)
    const review = screen.getByLabelText('match Lab imported draft review')
    expect(review).toHaveTextContent('source_reference')
    expect(review).toHaveTextContent('seed')
    await user.click(screen.getByRole('button', {name: 'Apply imported scenario to editor'}))
    await waitFor(() => expect(JSON.parse(screen.getByTestId('draft').textContent ?? '')).toEqual(incoming))
    expect(screen.getByText('Draft applied to editor only. Session and Run are unchanged.')).toBeInTheDocument()
    expect(save).not.toHaveBeenCalled()
    expect(run).not.toHaveBeenCalled()
  })


  it('exports only the current JSON scenario under a safe filename without running or saving', async () => {
    const objectUrl = vi.fn().mockReturnValue('blob:test-scenario')
    const old = URL.createObjectURL
    const oldRevoke = URL.revokeObjectURL
    let downloadName = ''
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      downloadName = this.download
    })
    URL.createObjectURL = objectUrl
    URL.revokeObjectURL = vi.fn()
    try {
      const run = vi.fn()
      render(<><LabScenarioAuthoring kind="match" text={JSON.stringify({...match, scenario_id: 'Match A/B'})}
        onChange={vi.fn()} selection="scratch" revision={0} jsonLabel="Match Lab scenario JSON" />
        <button onClick={run}>Run manually</button></>)
      await userEvent.setup().click(screen.getByRole('button', {name: 'Download scenario JSON'}))
      expect(objectUrl).toHaveBeenCalledTimes(1)
      expect(objectUrl.mock.calls[0][0]).toBeInstanceOf(Blob)
      expect((objectUrl.mock.calls[0][0] as Blob).type).toContain('application/json')
      expect(downloadName).toBe('Match_A_B.json')
      expect(run).not.toHaveBeenCalled()
    } finally {
      URL.createObjectURL = old
      URL.revokeObjectURL = oldRevoke
      click.mockRestore()
    }
  })

  it('canceling a staged file preserves the current editor and the saved baseline', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      return <><LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection="saved-1" revision={0} jsonLabel="Match Lab scenario JSON"
        savedScenario={match} savedName="Stored" sessionName="Stored" />
        <output data-testid="draft">{text}</output></>
    }
    const user = userEvent.setup()
    render(<Harness />)
    const incoming = {...match, seed: 500}
    const file = new File([JSON.stringify(incoming)], 'replace.json', {type: 'application/json'})
    Object.defineProperty(file, 'text', {value: () => Promise.resolve(JSON.stringify(incoming))})
    await user.upload(screen.getByLabelText('match Lab JSON file'), file)
    expect(await screen.findByLabelText('match Lab imported draft review')).toBeInTheDocument()
    expect(screen.getByLabelText('match Lab unsaved changes')).toHaveTextContent('No local changes')
    await user.click(screen.getByRole('button', {name: 'Cancel import'}))
    expect(screen.queryByLabelText('match Lab imported draft review')).not.toBeInTheDocument()
    expect(JSON.parse(screen.getByTestId('draft').textContent ?? '')).toEqual(match)
  })

  it('discarding a staged import on editor change prevents an old proposal from appearing again', async () => {
    function Harness() {
      const [text, setText] = useState(JSON.stringify(match))
      const [selection, setSelection] = useState('one')
      return <><LabScenarioAuthoring kind="match" text={text} onChange={setText}
        selection={selection} revision={0} jsonLabel="Match Lab scenario JSON" />
        <button type="button" onClick={() => setSelection('two')}>Switch Session</button>
        <button type="button" onClick={() => setSelection('one')}>Back to original</button></>
    }
    const user = userEvent.setup()
    render(<Harness />)
    const file = new File([JSON.stringify(match)], 'staged.json', {type: 'application/json'})
    Object.defineProperty(file, 'text', {value: () => Promise.resolve(JSON.stringify(match))})
    await user.upload(screen.getByLabelText('match Lab JSON file'), file)
    expect(await screen.findByLabelText('match Lab imported draft review')).toBeInTheDocument()
    await user.click(screen.getByRole('button', {name: 'Switch Session'}))
    expect(screen.queryByLabelText('match Lab imported draft review')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', {name: 'Back to original'}))
    expect(screen.queryByLabelText('match Lab imported draft review')).not.toBeInTheDocument()
  })

  it('shows the exact changed paths before an explicit saved-Session operation', () => {
    render(<LabScenarioAuthoring kind="tournament"
      text={JSON.stringify({...tournament, draw_seed: 404})} onChange={vi.fn()}
      selection="saved-1" revision={1} jsonLabel="Tournament Lab scenario JSON"
      savedScenario={tournament} savedName="Previous name" sessionName="New name" />)
    const comparison = screen.getByLabelText('tournament Lab unsaved changes')
    expect(comparison).toHaveTextContent('Session name changed')
    expect(comparison).toHaveTextContent('draw_seed')
    expect(comparison).toHaveTextContent('10 → 404')
    expect(comparison).toHaveTextContent('Saving the Session requires a separate explicit action')
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
