import { ChangeEvent, useEffect, useRef, useState } from 'react'
import { useLanguage } from '../../i18n/LanguageContext'

export type LabKind = 'match' | 'tournament' | 'player'
type JsonObject = Record<string, unknown>
type Field = { path: string[]; en: string; cs: string; min?: number; max?: number; integer?: boolean; odd?: boolean }

const schemas: Record<LabKind, string[]> = {
  match: ['match_test_lab_scenario.v1'],
  tournament: ['tournament_test_lab_scenario.v1'],
  player: ['player_test_lab_scenario.v1', 'player_test_lab_scenario.v2']
}

function object(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/** An import is a *scenario*, not a Session or result envelope. Full sporting validation stays in the API. */
export function readLabScenario(text: string, kind: LabKind): JsonObject {
  let value: unknown
  try { value = JSON.parse(text) } catch { throw new Error('syntax') }
  if (!object(value)) throw new Error('object')
  if (!schemas[kind].includes(String(value.schema_version ?? ''))) throw new Error('version')
  if (typeof value.scenario_id !== 'string' || !value.scenario_id.trim() || value.scenario_id.length > 160) throw new Error('id')
  if (kind === 'match' && (!object(value.context) || !Number.isSafeInteger(value.seed))) throw new Error('shape')
  if (kind === 'tournament' && (!Array.isArray(value.participants) || !object(value.match_format)
    || !Number.isSafeInteger(value.draw_seed) || !Number.isSafeInteger(value.match_seed))) throw new Error('shape')
  if (kind === 'player' && (!Array.isArray(value.variants) || value.variants.length === 0
    || !value.variants.every(item => object(item) && Array.isArray(item.competitive_match_counts)))) throw new Error('shape')
  return value
}

function fieldValue(scenario: JsonObject, path: string[]): unknown {
  let current: unknown = scenario
  for (const part of path) {
    if (!object(current)) return undefined
    current = current[part]
  }
  return current
}

export function changeLabField(text: string, kind: LabKind, field: Field, raw: string): string {
  const scenario = readLabScenario(text, kind)
  const existing = fieldValue(scenario, field.path)
  if (existing === undefined) throw new Error('shape')
  let value: string | number = raw
  if (field.integer || field.min !== undefined || field.max !== undefined) {
    if (!raw.trim()) throw new Error('number')
    value = Number(raw)
    if (!Number.isFinite(value) || (field.integer && !Number.isSafeInteger(value))
      || (field.min !== undefined && value < field.min) || (field.max !== undefined && value > field.max)
      || (field.odd && value % 2 !== 1)) throw new Error('number')
  } else if (!raw.trim() || raw.length > 160) throw new Error('id')
  const result = { ...scenario }
  let target = result
  for (const part of field.path.slice(0, -1)) {
    const original = target[part]
    if (!object(original)) throw new Error('shape')
    const copied = { ...original }
    target[part] = copied
    target = copied
  }
  target[field.path[field.path.length - 1]] = value
  return JSON.stringify(result, null, 2)
}

/** All variants must have equal lengths. Never invent a historical Health profile. */
export function changePlayerWeeks(text: string, weeks: number): string {
  const scenario = readLabScenario(text, 'player')
  if (!Number.isSafeInteger(weeks) || weeks < 1 || weeks > 61) throw new Error('weeks')
  const variants = scenario.variants as JsonObject[]
  if (variants.some(v => v.health_timeline != null)) throw new Error('health')
  const lengths = variants.map(v => (v.competitive_match_counts as unknown[]).length)
  if (lengths.some(n => n !== lengths[0])) throw new Error('shape')
  return JSON.stringify({
    ...scenario,
    variants: variants.map(variant => ({
      ...variant,
      competitive_match_counts: [
        ...(variant.competitive_match_counts as number[]).slice(0, weeks),
        ...Array.from({ length: Math.max(0, weeks - lengths[0]) }, () => 0)
      ]
    }))
  }, null, 2)
}

/** Edit a variant's existing workload without changing its length or Health timeline. */
export function changePlayerMatchCounts(text: string, index: number, raw: string): string {
  const scenario = readLabScenario(text, 'player')
  const variants = scenario.variants as JsonObject[]
  if (!Number.isSafeInteger(index) || index < 0 || index >= variants.length) throw new Error('shape')
  const existing = variants[index].competitive_match_counts as unknown[]
  const parts = raw.split(',').map(value => value.trim())
  if (parts.length !== existing.length || parts.some(value => !/^\d+$/.test(value))) throw new Error('counts')
  const numbers = parts.map(Number)
  if (numbers.some(value => !Number.isSafeInteger(value) || value < 0 || value > 32)) throw new Error('counts')
  return JSON.stringify({
    ...scenario,
    variants: variants.map((variant, position) => position === index ? {
      ...variant, competitive_match_counts: numbers
    } : variant)
  }, null, 2)
}

type ParticipantModifier = 'form_modifier' | 'sharpness_modifier' | 'fatigue_modifier' | 'health_modifier' | 'travel_modifier'
const modifierOptions: { key: ParticipantModifier; en: string; cs: string }[] = [
  { key: 'form_modifier', en: 'Form', cs: 'Forma' },
  { key: 'sharpness_modifier', en: 'Sharpness', cs: 'Rozehranost' },
  { key: 'fatigue_modifier', en: 'Fatigue', cs: 'Únava' },
  { key: 'health_modifier', en: 'Health', cs: 'Zdraví' },
  { key: 'travel_modifier', en: 'Travel', cs: 'Cestování' }
]

type ParticipantOption = { target: 'a' | 'b' | number; id: string; name: string; modifier: JsonObject }

function participantOptions(kind: LabKind, scenario: JsonObject): ParticipantOption[] {
  const inputs: { target: ParticipantOption['target']; value: unknown }[] = kind === 'match'
    ? [{ target: 'a', value: object(scenario.context) ? scenario.context.player_a : undefined },
       { target: 'b', value: object(scenario.context) ? scenario.context.player_b : undefined }]
    : kind === 'tournament' && Array.isArray(scenario.participants)
      ? scenario.participants.map((value, target) => ({ target, value })) : []
  return inputs.flatMap(({ target, value }) => {
    if (!object(value) || !object(value.player) || typeof value.player.player_id !== 'string'
      || !value.player.player_id.trim()) return []
    if (modifierOptions.some(option => value[option.key] !== undefined
      && (typeof value[option.key] !== 'number' || !Number.isFinite(value[option.key])))) return []
    return [{ target, id: value.player.player_id,
      name: typeof value.player.name === 'string' && value.player.name.trim()
        ? value.player.name : value.player.player_id, modifier: value }]
  })
}

/** Patch exactly one existing participant context, never the player ID or historical source evidence. */
export function changeLabParticipantModifier(
  text: string, kind: 'match' | 'tournament', target: 'a' | 'b' | number,
  key: ParticipantModifier, raw: string
): string {
  const scenario = readLabScenario(text, kind)
  const input = raw.trim()
  const value = Number(input)
  if (!input || !Number.isFinite(value) || value < -0.35 || value > 0.35) throw new Error('modifier')
  if (!modifierOptions.some(option => option.key === key)) throw new Error('modifier')
  const option = participantOptions(kind, scenario).find(item => item.target === target)
  if (!option) throw new Error('shape')
  if (kind === 'match') {
    if (target !== 'a' && target !== 'b') throw new Error('shape')
    const context = scenario.context as JsonObject
    const slot = target === 'a' ? 'player_a' : 'player_b'
    return JSON.stringify({ ...scenario, context: {
      ...context, [slot]: { ...option.modifier, [key]: value }
    } }, null, 2)
  }
  if (typeof target !== 'number' || !Array.isArray(scenario.participants)) throw new Error('shape')
  return JSON.stringify({ ...scenario, participants: scenario.participants.map((participant, index) =>
    index === target ? { ...option.modifier, [key]: value } : participant) }, null, 2)
}

/** Stop after round may be unset (full draw) or 1–7, matching the canonical API contract. */
export function changeTournamentStopRound(text: string, raw: string): string {
  const scenario = readLabScenario(text, 'tournament')
  const input = raw.trim()
  let round: number | null = null
  if (input) {
    round = Number(input)
    if (!/^[1-7]$/.test(input) || !Number.isSafeInteger(round)) throw new Error('round')
  }
  return JSON.stringify({ ...scenario, stop_after_round: round }, null, 2)
}

type TournamentAssertion = 'expected_champion_player_id' | 'expected_played_match_count'

/** Optional output expectations only: no Run or simulation mutation. */
export function changeTournamentAssertion(text: string, key: TournamentAssertion, raw: string): string {
  const scenario = readLabScenario(text, 'tournament')
  const assertions = scenario.assertions
  if (assertions !== undefined && !object(assertions)) throw new Error('shape')
  const input = raw.trim()
  let value: string | number | null
  if (key === 'expected_champion_player_id') {
    if (input.length > 160) throw new Error('assertion')
    value = input || null
  } else if (key === 'expected_played_match_count') {
    if (input && (!/^(0|[1-9]\d*)$/.test(input) || !Number.isSafeInteger(Number(input)))) {
      throw new Error('assertion')
    }
    value = input ? Number(input) : null
  } else throw new Error('assertion')
  return JSON.stringify({ ...scenario, assertions: { ...(assertions ?? {}), [key]: value } }, null, 2)
}

/** Reorders only existing validated seed IDs, without editing participants or the authoritative draw. */
export function moveTournamentSeedOrder(text: string, index: number, direction: -1 | 1): string {
  const scenario = readLabScenario(text, 'tournament')
  const order = scenario.seed_order_player_ids
  const present = new Set(participantOptions('tournament', scenario).map(p => p.id))
  if (!Array.isArray(order) || order.length < 2 || order.length > 128 ||
      order.some(id => typeof id !== 'string' || !id || !present.has(id)) ||
      new Set(order).size !== order.length) throw new Error('shape')
  const destination = index + direction
  if (!Number.isSafeInteger(index) || (direction !== -1 && direction !== 1) ||
      index < 0 || destination < 0 || destination >= order.length) throw new Error('order')
  const next = order.slice()
  ;[next[index], next[destination]] = [next[destination], next[index]]
  return JSON.stringify({ ...scenario, seed_order_player_ids: next }, null, 2)
}

function changes(oldValue: unknown, newValue: unknown, prefix: string, output: string[]): void {
  if (JSON.stringify(oldValue) === JSON.stringify(newValue)) return
  if (output.length >= 40) return
  if (Array.isArray(oldValue) && Array.isArray(newValue) && oldValue.length === newValue.length) {
    for (let i = 0; i < oldValue.length; i++) {
      changes(oldValue[i], newValue[i], prefix ? prefix + '.' + i : String(i), output)
      if (output.length >= 40) return
    }
  } else if (object(oldValue) && object(newValue)) {
    for (const key of new Set([...Object.keys(oldValue), ...Object.keys(newValue)])) {
      changes(oldValue[key], newValue[key], prefix ? prefix + '.' + key : key, output)
      if (output.length >= 40) return
    }
  } else {
    output.push(prefix || '(scenario)')
  }
}

export function labChangedPaths(saved: unknown, draft: unknown): string[] {
  const output: string[] = []
  changes(saved, draft, '', output)
  return output
}

export type LabChangeDetail = { path: string; before: string; after: string }

/** Small, read-only Session review: no deep payload dumps of sporting/Health data. */
export function labChangeDetails(saved: unknown, draft: unknown): LabChangeDetail[] {
  const short = (value: unknown): string => {
    if (value === undefined) return '—'
    if (value === null) return 'null'
    if (Array.isArray(value)) return '[' + value.length + ' entries]'
    if (object(value)) return '{…}'
    const text = String(value)
    return text.length <= 65 ? text : text.slice(0, 62) + '…'
  }
  return labChangedPaths(saved, draft).map(path => ({
    path,
    before: short(path.split('.').reduce<unknown>((value, key) =>
      object(value) ? value[key] : Array.isArray(value) && /^\d+$/.test(key) ? value[Number(key)] : undefined, saved)),
    after: short(path.split('.').reduce<unknown>((value, key) =>
      object(value) ? value[key] : Array.isArray(value) && /^\d+$/.test(key) ? value[Number(key)] : undefined, draft))
  }))
}

function fieldsFor(kind: LabKind, scenario: JsonObject): Field[] {
  const result: Field[] = [{ path: ['scenario_id'], en: 'Scenario ID', cs: 'ID scénáře' }]
  const numeric = (path: string[], en: string, cs: string, min?: number, max?: number, integer = true, odd = false) => {
    if (fieldValue(scenario, path) !== undefined) result.push({ path, en, cs, min, max, integer, odd })
  }
  if (kind === 'match') {
    numeric(['seed'], 'Seed', 'Seed')
    numeric(['context', 'best_of'], 'Best of sets', 'Počet setů (best of)', 1, undefined, true, true)
    numeric(['context', 'games_to'], 'Points per game', 'Bodů v gamu', 1)
    numeric(['context', 'win_by'], 'Win by', 'Rozdíl pro výhru', 1)
    numeric(['context', 'upset_variance'], 'Upset variance', 'Variabilita překvapení', 0, 0.35, false)
  }
  if (kind === 'tournament') {
    if (typeof scenario.display_name === 'string') result.push({ path: ['display_name'], en: 'Tournament name', cs: 'Název turnaje' })
    numeric(['draw_seed'], 'Draw seed', 'Seed losu')
    numeric(['match_seed'], 'Match seed', 'Seed zápasů')
    numeric(['match_format', 'best_of'], 'Best of sets', 'Počet setů (best of)', 1, undefined, true, true)
    numeric(['match_format', 'games_to'], 'Points per game', 'Bodů v gamu', 1)
    numeric(['match_format', 'win_by'], 'Win by', 'Rozdíl pro výhru', 1)
    numeric(['match_format', 'upset_variance'], 'Upset variance', 'Variabilita překvapení', 0, 0.35, false)
  }
  if (kind === 'player' && scenario.seed !== undefined) numeric(['seed'], 'Seed', 'Seed')
  return result
}

const messages: Record<string, [string, string]> = {
  syntax: ['Invalid JSON syntax.', 'Neplatná syntaxe JSON.'],
  object: ['The file must contain a scenario object, not an array or Session.', 'Soubor musí obsahovat objekt scénáře, nikoliv pole či Session.'],
  version: ['Unsupported scenario type or schema version for this Lab.', 'Nepodporovaný typ nebo verze scénáře pro tento Lab.'],
  id: ['Scenario ID/name must be nonempty and at most 160 characters.', 'ID/název musí být neprázdný a mít nejvýše 160 znaků.'],
  shape: ['Scenario structure is incomplete. Check the advanced JSON editor.', 'Scénář nemá úplnou strukturu. Zkontrolujte pokročilý JSON editor.'],
  number: ['Enter a valid number within the supported range.', 'Zadejte platné číslo v povoleném rozsahu.'],
  weeks: ['Duration must be 1–61 weeks.', 'Délka musí být 1–61 týdnů.'],
  counts: ['Enter one comma-separated integer (0–32) per existing week.', 'Zadejte za každý existující týden jedno celé číslo (0–32) oddělené čárkou.'],
  health: ['Duration cannot be changed here because the explicit Health timeline must stay aligned. Use advanced JSON.', 'Délku zde nelze změnit: explicitní Health časová osa musí zůstat sladěná. Použijte pokročilý JSON.'],
  size: ['JSON file exceeds the 2 MB limit.', 'Soubor JSON překračuje limit 2 MB.'],
  stale: ['The editor changed while the file was being read. No file was applied.', 'Editor se během čtení souboru změnil. Soubor nebyl použit.'],
  modifier: ['Modifier must be between −0.35 and +0.35.', 'Modifikátor musí být od −0,35 do +0,35.'],
  round: ['Choose no limit or a round from 1 to 7.', 'Vyberte bez omezení nebo kolo 1 až 7.'],
  assertion: ['Expected winner must be a player ID of at most 160 characters; match count must be a nonnegative integer.', 'Očekávaný vítěz může mít nejvýše 160 znaků; počet zápasů musí být nezáporné celé číslo.'],
  order: ['Cannot move this seed priority position.', 'Tuto pozici nasazení nelze přesunout.'],
  file: ['Could not read the JSON file.', 'Soubor JSON se nepodařilo načíst.']
}

function explain(error: unknown, cs: boolean): string {
  const key = error instanceof Error ? error.message : 'file'
  return (messages[key] ?? messages.file)[cs ? 1 : 0]
}


function ParticipantModifierEditor({ kind, participants, cs, busy, onApply }: {
  kind: 'match' | 'tournament'; participants: ParticipantOption[]; cs: boolean; busy: boolean
  onApply: (target: ParticipantOption['target'], key: ParticipantModifier, raw: string) => void
}): JSX.Element {
  const [selected, setSelected] = useState(0)
  const [key, setKey] = useState<ParticipantModifier>('form_modifier')
  const current = participants[selected] ?? participants[0]
  const original = String(current?.modifier[key] ?? 0)
  const [draft, setDraft] = useState(original)
  useEffect(() => { setDraft(original) }, [original, selected, key])
  return <fieldset>
    <legend>{cs ? 'Kontext účastníků' : 'Participant context modifiers'}</legend>
    <p className="status">{cs
      ? 'Úprava ovlivní jen jeden kontextový modifikátor (−0,35 až +0,35), ne profil hráče nebo historický zdroj.'
      : 'Changes one context modifier (−0.35 to +0.35), not the player profile or historical source.'}</p>
    <label>{cs ? 'Hráč' : 'Player'}{' '}
      <select aria-label={kind + ' Lab modifier player'} value={participants.indexOf(current)}
        disabled={busy} onChange={event => setSelected(Number(event.target.value))}>
        {participants.map((participant, index) =>
          <option key={String(participant.target)} value={index}>{participant.name} ({participant.id})</option>)}
      </select>
    </label>{' '}
    <label>{cs ? 'Modifikátor' : 'Modifier'}{' '}
      <select aria-label={kind + ' Lab modifier kind'} disabled={busy} value={key}
        onChange={event => setKey(event.target.value as ParticipantModifier)}>
        {modifierOptions.map(option =>
          <option key={option.key} value={option.key}>{cs ? option.cs : option.en}</option>)}
      </select>
    </label>{' '}
    <label>{cs ? 'Hodnota' : 'Value'}{' '}
      <input aria-label={kind + ' Lab modifier value'} type="number" min={-0.35} max={0.35}
        step="0.01" disabled={busy} value={draft}
        onChange={event => setDraft(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
    </label>{' '}
    <button type="button" aria-label={kind + ' Lab apply modifier'}
      disabled={busy || draft === original}
      onClick={() => onApply(current.target, key, draft)}>
      {cs ? 'Použít modifikátor' : 'Apply modifier'}
    </button>
  </fieldset>
}

function TournamentStopRoundEditor({ current, cs, busy, onApply }: {
  current: unknown; cs: boolean; busy: boolean; onApply: (raw: string) => void
}): JSX.Element {
  const original = current == null ? '' : String(current)
  const [draft, setDraft] = useState(original)
  useEffect(() => { setDraft(original) }, [original])
  return <div>
    <label>{cs ? 'Ukončení po kole' : 'Stop after round'}{' '}
      <select aria-label="tournament Lab stop after round" disabled={busy} value={draft}
        onChange={event => setDraft(event.target.value)}>
        <option value="">{cs ? 'Bez omezení (celý turnaj)' : 'No limit (full tournament)'}</option>
        {Array.from({ length: 7 }, (_, i) =>
          <option value={i + 1} key={i}>{cs ? 'Kolo' : 'Round'} {i + 1}</option>)}
      </select>
    </label>{' '}
    <button type="button" aria-label="tournament Lab apply stop after round"
      disabled={busy || draft === original} onClick={() => onApply(draft)}>
      {cs ? 'Použít limit kol' : 'Apply round limit'}
    </button>
  </div>
}

function TournamentAssertionsEditor({ assertions, ids, cs, busy, onApply }: {
  assertions: unknown; ids: string[]; cs: boolean; busy: boolean
  onApply: (key: TournamentAssertion, raw: string) => void
}): JSX.Element {
  const current = object(assertions) ? assertions : {}
  const champion = typeof current.expected_champion_player_id === 'string' ? current.expected_champion_player_id : ''
  const matches = current.expected_played_match_count == null ? '' : String(current.expected_played_match_count)
  const [championDraft, setChampionDraft] = useState(champion)
  const [matchesDraft, setMatchesDraft] = useState(matches)
  useEffect(() => { setChampionDraft(champion) }, [champion])
  useEffect(() => { setMatchesDraft(matches) }, [matches])
  return <fieldset>
    <legend>{cs ? 'Očekávané výsledky testu' : 'Tournament test assertions'}</legend>
    <p className="status">{cs
      ? 'Volitelné ověření výsledku; simulace ani Run se nemění. Prázdné pole kontrolu vypne.'
      : 'Optional result checks; simulation and Run remain unchanged. Leave empty to disable a check.'}</p>
    <label>{cs ? 'Očekávaný vítěz – ID hráče' : 'Expected champion player ID'}{' '}
      <input type="text" list="lab-expected-champions" aria-label="tournament Lab expected champion"
        disabled={busy} value={championDraft} onChange={e => setChampionDraft(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') e.preventDefault() }} />
    </label>{' '}
    <datalist id="lab-expected-champions">{ids.map(id => <option value={id} key={id} />)}</datalist>
    <button type="button" aria-label="tournament Lab apply expected champion"
      disabled={busy || championDraft === champion}
      onClick={() => onApply('expected_champion_player_id', championDraft)}>
      {cs ? 'Použít vítěze' : 'Apply champion expectation'}
    </button>
    <div>
      <label>{cs ? 'Očekávaný počet odehraných zápasů' : 'Expected played match count'}{' '}
        <input aria-label="tournament Lab expected match count" type="number" min={0} step={1}
          disabled={busy} value={matchesDraft} onChange={e => setMatchesDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') e.preventDefault() }} />
      </label>{' '}
      <button type="button" aria-label="tournament Lab apply expected match count"
        disabled={busy || matchesDraft === matches}
        onClick={() => onApply('expected_played_match_count', matchesDraft)}>
        {cs ? 'Použít počet zápasů' : 'Apply match-count expectation'}
      </button>
    </div>
  </fieldset>
}

function TournamentSeedOrderEditor({ order, cs, busy, onMove }: {
  order: string[]; cs: boolean; busy: boolean; onMove: (index: number, direction: -1 | 1) => void
}): JSX.Element {
  return <fieldset>
    <legend>{cs ? 'Pořadí nasazení' : 'Seed priority order'}</legend>
    <p className="status">{cs
      ? 'Přesun změní jen pořadí současných ID, nikoli hráče, historický zdroj ani samotný los. Před simulací použijte kontrolu kompatibility.'
      : 'Reordering changes existing ID priority only, not players, historical source or the draw itself. Inspect compatibility before simulating.'}</p>
    <ol>{order.map((id, index) => <li key={id}>
      <code>{id}</code>{' '}
      <button type="button" aria-label={'tournament Lab seed move up ' + id}
        disabled={busy || index === 0} onClick={() => onMove(index, -1)}>
        {cs ? 'Výše' : 'Move up'}
      </button>{' '}
      <button type="button" aria-label={'tournament Lab seed move down ' + id}
        disabled={busy || index === order.length - 1} onClick={() => onMove(index, 1)}>
        {cs ? 'Níže' : 'Move down'}
      </button>
    </li>)}</ol>
  </fieldset>
}

function GuidedFieldEditor({ field, kind, value, cs, busy, onApply }: {
  field: Field; kind: LabKind; value: unknown; cs: boolean; busy: boolean
  onApply: (field: Field, draft: string) => void
}): JSX.Element {
  const original = String(value)
  const [draft, setDraft] = useState(original)
  useEffect(() => { setDraft(original) }, [original])
  const name = cs ? field.cs : field.en
  return <span style={{ display: 'inline-block', marginRight: '1rem' }}>
    <label>{name}{' '}
      <input aria-label={kind + ' Lab ' + field.path.join('.')}
        type={typeof value === 'number' ? 'number' : 'text'} min={field.min} max={field.max}
        step={field.integer ? 1 : 'any'} disabled={busy} value={draft}
        onChange={event => setDraft(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
    </label>{' '}
    <button type="button" aria-label={kind + ' Lab apply ' + field.path.join('.')}
      disabled={busy || draft === original} onClick={() => onApply(field, draft)}>
      {cs ? 'Použít' : 'Apply'}
    </button>
  </span>
}

function VariantMatchCountsEditor({ id, values, index, cs, busy, onApply }: {
  id: string; values: number[]; index: number; cs: boolean; busy: boolean
  onApply: (index: number, draft: string) => void
}): JSX.Element {
  const original = values.join(', ')
  const [weekIndex, setWeekIndex] = useState(0)
  const selectedWeek = Math.min(weekIndex, Math.max(0, values.length - 1))
  const [weekDraft, setWeekDraft] = useState(String(values[0] ?? 0))
  const [draft, setDraft] = useState(original)
  useEffect(() => { setWeekDraft(String(values[selectedWeek] ?? 0)) }, [values, selectedWeek])
  useEffect(() => { setDraft(original) }, [original])
  return <div>
    <strong>{cs ? 'Varianta' : 'Variant'} <code>{id}</code></strong>
    <div>
      <label>{cs ? 'Vybraný týden' : 'Selected week'}{' '}
        <select aria-label={'player Lab variant ' + id + ' selected week'} value={selectedWeek}
          disabled={busy} onChange={event => setWeekIndex(Number(event.target.value))}>
          {values.map((_, i) => <option key={i} value={i}>{cs ? 'Týden' : 'Week'} {i + 1}</option>)}
        </select>
      </label>{' '}
      <label>{cs ? 'Počet soutěžních zápasů' : 'Competitive matches'}{' '}
        <input aria-label={'player Lab variant ' + id + ' selected week matches'}
          type="number" min={0} max={32} step={1} disabled={busy} value={weekDraft}
          onChange={event => setWeekDraft(event.target.value)}
          onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
      </label>{' '}
      <button type="button" aria-label={'player Lab variant ' + id + ' apply selected week'}
        disabled={busy || weekDraft === String(values[selectedWeek])}
        onClick={() => onApply(index, values.map((count, i) =>
          i === selectedWeek ? weekDraft : String(count)).join(', '))}>
        {cs ? 'Použít vybraný týden' : 'Apply selected week'}
      </button>
    </div>
    <label>{cs ? 'Zápasy za týden – celý seznam' : 'Weekly matches – full list'} — <code>{id}</code>{' '}
      <input aria-label={'player Lab variant ' + id + ' weekly matches'} type="text"
        value={draft} disabled={busy} onChange={event => setDraft(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
    </label>{' '}
    <button type="button" disabled={busy || draft === original}
      onClick={() => onApply(index, draft)}>{cs ? 'Použít týdenní počty' : 'Apply weekly counts'}</button>
  </div>
}


function PlayerDurationEditor({ weeks, healthLocked, cs, busy, onApply }: {
  weeks: number; healthLocked: boolean; cs: boolean; busy: boolean
  onApply: (weeks: number) => void
}): JSX.Element {
  const [draft, setDraft] = useState(String(weeks))
  useEffect(() => { setDraft(String(weeks)) }, [weeks])
  return <div>
    <label>{cs ? 'Počet týdnů experimentu' : 'Experiment weeks'}{' '}
      <input type="number" aria-label="player Lab experiment duration" min={1} max={61}
        disabled={busy || healthLocked} value={draft} onChange={event => setDraft(event.target.value)}
        onKeyDown={event => { if (event.key === 'Enter') event.preventDefault() }} />
    </label>{' '}
    <button type="button" disabled={busy || healthLocked || draft === String(weeks)}
      onClick={() => onApply(Number(draft))}>{cs ? 'Použít délku' : 'Apply duration'}</button>
    {healthLocked && <p className="status">{cs
      ? 'Délka je svázána s explicitní Health časovou osou.'
      : 'Duration is locked to the explicit Health timeline.'}</p>}
    {!healthLocked && <p className="status">{cs
      ? 'Nové týdny mají 0 soutěžních zápasů; zkrácení odstraní pozdější týdny až po potvrzení.'
      : 'New weeks start with 0 competitive matches; shortening drops later weeks only after Apply.'}</p>}
  </div>
}

export function LabScenarioAuthoring({ kind, text, onChange, savedScenario, savedName, sessionName, selection, revision, jsonLabel, busy = false }: {
  kind: LabKind
  text: string
  onChange: (value: string) => void
  savedScenario?: unknown
  savedName?: string
  sessionName?: string
  selection: string
  revision: number
  jsonLabel: string
  busy?: boolean
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [mode, setMode] = useState<'combined' | 'form' | 'json'>('combined')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [pendingImport, setPendingImport] = useState<{ file: string; json: string; scenario: JsonObject; identity: string } | null>(null)
  const identity = selection + ':' + revision + ':' + text
  const latest = useRef(identity)
  latest.current = identity
  const readIndex = useRef(0)
  // An earlier file proposal never revives after switching away and back to a Session.
  useEffect(() => { setPendingImport(null) }, [selection, revision])
  let parsed: JsonObject | null = null
  try { parsed = readLabScenario(text, kind) } catch { /* malformed advanced JSON is retained verbatim */ }
  const fields = parsed ? fieldsFor(kind, parsed) : []
  const participants = parsed ? participantOptions(kind, parsed) : []
  const seedOrder = kind === 'tournament' && parsed && Array.isArray(parsed.seed_order_player_ids) &&
    parsed.seed_order_player_ids.length > 1 && parsed.seed_order_player_ids.length <= 128 &&
    parsed.seed_order_player_ids.every(id => typeof id === 'string' && id.length > 0 && participants.some(p => p.id === id)) &&
    new Set(parsed.seed_order_player_ids).size === parsed.seed_order_player_ids.length
    ? parsed.seed_order_player_ids as string[] : []
  const variants = kind === 'player' && parsed ? parsed.variants as JsonObject[] : []
  const weeks = variants.length ? (variants[0].competitive_match_counts as number[]).length : 0
  const healthLocked = variants.some(variant => variant.health_timeline != null)
  let savedChanges: string[] = []
  if (savedScenario !== undefined) {
    try { savedChanges = labChangedPaths(savedScenario, JSON.parse(text)) }
    catch { savedChanges = ['(invalid JSON)'] }
  }
  const nameChanged = savedName !== undefined && sessionName !== undefined && savedName !== sessionName
  const edit = (next: string) => {
    setPendingImport(null)
    setError('')
    setNotice('')
    onChange(next)
  }
  const applyField = (field: Field, raw: string) => {
    try { edit(changeLabField(text, kind, field, raw)) }
    catch (reason) { setError(explain(reason, cs)) }
  }
  const importFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    const currentIdentity = latest.current
    const currentRead = ++readIndex.current
    setError(''); setNotice(''); setPendingImport(null)
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('size')
      const contents = await file.text()
      const value = readLabScenario(contents, kind)
      if (latest.current !== currentIdentity || currentRead !== readIndex.current) throw new Error('stale')
      setPendingImport({ file: file.name, json: JSON.stringify(value, null, 2), scenario: value, identity: currentIdentity })
      setNotice(cs ? 'Soubor je připraven ke kontrole. Editor, Session ani Run se nezměnily.' : 'File ready for review. Editor, Session and Run are unchanged.')
    } catch (reason) { setError(explain(reason, cs)) }
  }
  const reviewedImport = pendingImport?.identity === identity ? pendingImport : null
  const applyImportedFile = () => {
    if (!reviewedImport || busy || reviewedImport.identity !== latest.current) {
      setPendingImport(null)
      setError(explain(new Error('stale'), cs))
      return
    }
    edit(reviewedImport.json)
    setNotice(cs ? 'Návrh byl převzat pouze do editoru. Session ani Run se nezměnily.' : 'Draft applied to editor only. Session and Run are unchanged.')
  }
  const download = () => {
    try {
      const scenario = readLabScenario(text, kind)
      const blob = new Blob([JSON.stringify(scenario, null, 2) + '\n'], { type: 'application/json;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = String(scenario.scenario_id).replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 80) + '.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
      setError('')
    } catch (reason) { setError(explain(reason, cs)) }
  }

  return <div aria-label={kind + ' Lab scenario authoring'}>
    <p className="status">{cs
      ? 'Strukturované úpravy mění jen uvedená pole; ostatní JSON a provenience zůstávají zachovány. Konečnou validaci provádí backend.'
      : 'Guided edits change only the displayed fields; all other JSON and provenance are preserved. The backend remains the final validator.'}</p>
    <button type="button" onClick={() => setMode(mode === 'form' ? 'json' : 'form')}>
      {mode === 'form' ? (cs ? 'Přepnout na JSON' : 'Switch to advanced JSON') : (cs ? 'Pouze strukturovaný editor' : 'Guided editor only')}
    </button>{' '}
    <label>{cs ? 'Režim editoru' : 'Editor mode'}{' '}
      <select aria-label={kind + ' Lab editor mode'} value={mode} onChange={event => setMode(event.target.value as 'combined' | 'form' | 'json')}>
        <option value="combined">{cs ? 'Formulář + JSON' : 'Guided fields + JSON'}</option>
        <option value="form">{cs ? 'Strukturovaný editor' : 'Guided editor'}</option>
        <option value="json">{cs ? 'Pokročilý JSON' : 'Advanced JSON'}</option>
      </select>
    </label>
    {mode !== 'json' && (parsed ? <div>
      {fields.map(field => <GuidedFieldEditor
        key={selection + ':' + revision + ':' + field.path.join('.')} field={field}
        kind={kind} value={fieldValue(parsed!, field.path)} cs={cs} busy={busy}
        onApply={applyField} />)}
      {(kind === 'match' || kind === 'tournament') && participants.length > 0 &&
        <ParticipantModifierEditor key={selection + ':' + String(parsed.scenario_id)} kind={kind}
          participants={participants} cs={cs} busy={busy}
          onApply={(target, key, value) => {
            try { edit(changeLabParticipantModifier(text, kind, target, key, value)) }
            catch (reason) { setError(explain(reason, cs)) }
          }} />}
      {kind === 'tournament' && <TournamentStopRoundEditor
        key={selection + ':' + revision} current={parsed.stop_after_round}
        cs={cs} busy={busy} onApply={raw => {
          try { edit(changeTournamentStopRound(text, raw)) }
          catch (reason) { setError(explain(reason, cs)) }
        }} />}
      {kind === 'tournament' && seedOrder.length > 1 &&
        <TournamentSeedOrderEditor order={seedOrder} cs={cs} busy={busy}
          onMove={(index, direction) => {
            try { edit(moveTournamentSeedOrder(text, index, direction)) }
            catch (reason) { setError(explain(reason, cs)) }
          }} />}
      {kind === 'tournament' && <TournamentAssertionsEditor
        key={selection + ':' + String(parsed.scenario_id)} assertions={parsed.assertions}
        ids={participants.map(p => p.id)} cs={cs} busy={busy}
        onApply={(key, raw) => {
          try { edit(changeTournamentAssertion(text, key, raw)) }
          catch (reason) { setError(explain(reason, cs)) }
        }} />}
      {kind === 'player' && variants.map((variant, index) => <VariantMatchCountsEditor
        key={String(variant.variant_id) + ':' + selection} id={String(variant.variant_id)}
        values={variant.competitive_match_counts as number[]} index={index} cs={cs} busy={busy}
        onApply={(position, draft) => {
          try { edit(changePlayerMatchCounts(text, position, draft)) }
          catch (reason) { setError(explain(reason, cs)) }
        }} />)}
      {kind === 'player' && variants.length > 0 && <PlayerDurationEditor
        key={selection + ':' + revision} weeks={weeks} healthLocked={healthLocked} cs={cs} busy={busy}
        onApply={nextWeeks => {
          try { edit(changePlayerWeeks(text, nextWeeks)) }
          catch (reason) { setError(explain(reason, cs)) }
        }} />}
    </div> : (text.trim()
      ? <p className="error">{cs ? 'Neplatný nebo nepodporovaný scénář; opravte jej v pokročilém JSON editoru.' : 'Invalid or unsupported scenario; repair it in Advanced JSON.'}</p>
      : <p className="status">{cs ? 'Nejdříve načtěte vestavěný scénář nebo importujte JSON soubor.' : 'Load a built-in scenario or import a JSON file to start editing.'}</p>))}
    {mode !== 'form' && <textarea aria-label={jsonLabel} rows={mode === 'combined' ? 12 : 24}
      style={{ width: '100%', fontFamily: 'monospace' }} disabled={busy} value={text}
      onChange={event => edit(event.target.value)} />}
    <div>
      <label>{cs ? 'Načíst scénář ze souboru JSON' : 'Load scenario JSON file'}{' '}
        <input aria-label={kind + ' Lab JSON file'} type="file" accept=".json,application/json"
          disabled={busy} onChange={event => { void importFile(event) }} />
      </label>{' '}
      <button type="button" disabled={!parsed || busy} onClick={download}>
        {cs ? 'Stáhnout JSON scénář' : 'Download scenario JSON'}
      </button>
    </div>
    {reviewedImport && <div aria-label={kind + ' Lab imported draft review'}>
      <strong>{cs ? 'Kontrola načteného scénáře' : 'Review imported scenario'}</strong>
      <p><code>{reviewedImport.file}</code> · <code>{String(reviewedImport.scenario.schema_version)}</code>
        {' · '}{String(reviewedImport.scenario.scenario_id)}</p>
      <p className="status">{cs
        ? 'Převzetí nahradí aktuální pracovní text; uložená Session i historický zdroj zůstanou nedotčeny.'
        : 'Applying replaces the current local editor text; the saved Session and historical source are unchanged.'}</p>
      <p>{cs ? 'Změněné cesty při převzetí' : 'Paths that would change'}: {labChangedPaths(
        (() => { try { return JSON.parse(text) } catch { return null } })(), reviewedImport.scenario
      ).slice(0, 12).join(', ') || (cs ? 'beze změny' : 'no changes')}</p>
      <button type="button" disabled={busy} onClick={applyImportedFile}>
        {cs ? 'Převzít načtený scénář do editoru' : 'Apply imported scenario to editor'}
      </button>{' '}
      <button type="button" onClick={() => { setPendingImport(null); setNotice('') }}>
        {cs ? 'Zrušit import' : 'Cancel import'}
      </button>
    </div>}
    <p className="status">{cs ? 'Režim' : 'Source'}: {savedScenario === undefined
      ? (cs ? 'pracovní scénář, bez automatického uložení' : 'scratch scenario, not automatically saved')
      : (cs ? 'uložená Session + místní pracovní kopie' : 'saved Session + local working copy')}
      {parsed?.source_snapshot ? (cs ? ' · historická kopie (původní zdroj se nemění)' : ' · historical copy (source unchanged)')
        : parsed?.source_kind && parsed.source_kind !== 'portable' ? (cs ? ' · provenience kopie zachována' : ' · copy provenance preserved') : ''}
    </p>
    {savedScenario !== undefined && <div aria-label={kind + ' Lab unsaved changes'}>
      <strong>{cs ? 'Změny vůči uložené Session' : 'Changes against saved Session'}</strong>
      {nameChanged && <p>{cs ? 'Název Session byl změněn.' : 'Session name changed.'}</p>}
      {savedChanges.length ? <><p>{cs ? 'Změněná pole' : 'Changed paths'} ({savedChanges.length}{savedChanges.length === 40 ? '+' : ''}):</p>
        <ul>{labChangeDetails(savedScenario, (() => { try { return JSON.parse(text) } catch { return null } })())
          .slice(0, 12).map(change => <li key={change.path}><code>{change.path}</code>
            {change.path !== '(invalid JSON)' ? <>: <code>{change.before}</code> → <code>{change.after}</code></> : null}
          </li>)}</ul>
        {savedChanges.length > 12 && <p className="status">{cs ? 'Další změny jsou viditelné v JSON.' : 'More changes are visible in JSON.'}</p>}</>
        : !nameChanged && <p className="status">{cs ? 'Žádné místní změny.' : 'No local changes.'}</p>}
      <p className="status">{cs ? 'Uložení Session vyžaduje samostatné potvrzení.' : 'Saving the Session requires a separate explicit action.'}</p>
    </div>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </div>
}
