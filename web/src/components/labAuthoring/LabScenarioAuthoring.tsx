import { ChangeEvent, useRef, useState } from 'react'
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

function changes(oldValue: unknown, newValue: unknown, prefix: string, output: string[]): void {
  if (JSON.stringify(oldValue) === JSON.stringify(newValue)) return
  if (output.length >= 40) return
  if (object(oldValue) && object(newValue)) {
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
  health: ['Duration cannot be changed here because the explicit Health timeline must stay aligned. Use advanced JSON.', 'Délku zde nelze změnit: explicitní Health časová osa musí zůstat sladěná. Použijte pokročilý JSON.'],
  size: ['JSON file exceeds the 2 MB limit.', 'Soubor JSON překračuje limit 2 MB.'],
  stale: ['The editor changed while the file was being read. No file was applied.', 'Editor se během čtení souboru změnil. Soubor nebyl použit.'],
  file: ['Could not read the JSON file.', 'Soubor JSON se nepodařilo načíst.']
}

function explain(error: unknown, cs: boolean): string {
  const key = error instanceof Error ? error.message : 'file'
  return (messages[key] ?? messages.file)[cs ? 1 : 0]
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
  const [mode, setMode] = useState<'form' | 'json'>('json')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const identity = selection + ':' + revision + ':' + text
  const latest = useRef(identity)
  latest.current = identity
  const readIndex = useRef(0)
  let parsed: JsonObject | null = null
  try { parsed = readLabScenario(text, kind) } catch { /* malformed advanced JSON is retained verbatim */ }
  const fields = parsed ? fieldsFor(kind, parsed) : []
  const variants = kind === 'player' && parsed ? parsed.variants as JsonObject[] : []
  const weeks = variants.length ? (variants[0].competitive_match_counts as number[]).length : 0
  const healthLocked = variants.some(variant => variant.health_timeline != null)
  let savedChanges: string[] = []
  if (savedScenario !== undefined) {
    try { savedChanges = labChangedPaths(savedScenario, JSON.parse(text)) }
    catch { savedChanges = ['(invalid JSON)'] }
  }
  const nameChanged = savedName !== undefined && sessionName !== undefined && savedName !== sessionName
  const edit = (next: string) => { setError(''); setNotice(''); onChange(next) }
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
    setError(''); setNotice('')
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('size')
      const contents = await file.text()
      const value = readLabScenario(contents, kind)
      if (latest.current !== currentIdentity || currentRead !== readIndex.current) throw new Error('stale')
      edit(JSON.stringify(value, null, 2))
      setNotice(cs ? 'Soubor byl načten pouze do editoru. Session ani Run se nezměnily.' : 'Loaded into the editor only. No Session or Run was changed.')
    } catch (reason) { setError(explain(reason, cs)) }
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
      {mode === 'form' ? (cs ? 'Přepnout na JSON' : 'Switch to advanced JSON') : (cs ? 'Upravit pomocí formuláře' : 'Edit with guided form')}
    </button>{' '}
    <label>{cs ? 'Režim editoru' : 'Editor mode'}{' '}
      <select aria-label={kind + ' Lab editor mode'} value={mode} onChange={event => setMode(event.target.value as 'form' | 'json')}>
        <option value="form">{cs ? 'Strukturovaný editor' : 'Guided editor'}</option>
        <option value="json">{cs ? 'Pokročilý JSON' : 'Advanced JSON'}</option>
      </select>
    </label>
    {mode === 'form' && (parsed ? <div>
      {fields.map(field => {
        const value = fieldValue(parsed!, field.path)
        return <label key={field.path.join('.')} style={{ display: 'inline-block', marginRight: '1rem' }}>
          {cs ? field.cs : field.en}{' '}
          <input aria-label={kind + ' Lab ' + field.path.join('.')} disabled={busy}
            type={typeof value === 'number' ? 'number' : 'text'}
            min={field.min} max={field.max} step={field.integer ? 1 : 'any'}
            value={String(value)} onChange={event => {
              if (event.target.value !== '') applyField(field, event.target.value)
            }} />
        </label>
      })}
      {kind === 'player' && variants.length > 0 && <label>
        {cs ? 'Počet týdnů experimentu' : 'Experiment weeks'}{' '}
        <input type="number" aria-label="player Lab experiment duration" min={1} max={61}
          disabled={busy || healthLocked} value={weeks} onChange={event => {
            if (!event.target.value) return
            try { edit(changePlayerWeeks(text, Number(event.target.value))) }
            catch (reason) { setError(explain(reason, cs)) }
          }} />
        {healthLocked && <span className="status"> {cs ? 'Délka je svázána s Health časovou osou.' : 'Duration is locked to the explicit Health timeline.'}</span>}
        {!healthLocked && <span className="status"> {cs ? 'Nové týdny mají 0 soutěžních zápasů.' : 'New weeks explicitly start with 0 competitive matches.'}</span>}
      </label>}
    </div> : <p role="alert">{cs ? 'Neplatný nebo nepodporovaný scénář; opravte jej v pokročilém JSON editoru.' : 'Invalid or unsupported scenario; repair it in Advanced JSON.'}</p>)}
    {mode === 'json' && <textarea aria-label={jsonLabel} rows={24}
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
        <ul>{savedChanges.slice(0, 12).map(path => <li key={path}><code>{path}</code></li>)}</ul>
        {savedChanges.length > 12 && <p className="status">{cs ? 'Další změny jsou viditelné v JSON.' : 'More changes are visible in JSON.'}</p>}</>
        : !nameChanged && <p className="status">{cs ? 'Žádné místní změny.' : 'No local changes.'}</p>}
      <p className="status">{cs ? 'Uložení Session vyžaduje samostatné potvrzení.' : 'Saving the Session requires a separate explicit action.'}</p>
    </div>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </div>
}
