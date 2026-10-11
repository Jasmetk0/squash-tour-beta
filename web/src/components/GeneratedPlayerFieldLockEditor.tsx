/** Run-owned preview fields, not a persistent player/career lock editor. */
import { useState } from 'react'
import type {
  GeneratedPlayerFieldKey, RunInitialWorldPlayer, RunWorldPreviewFieldLock
} from '../api/runInitialWorldSetup'
import { PREVIEW_FIELD_KEYS } from '../api/runInitialWorldSetup'

const labels: Record<GeneratedPlayerFieldKey,string> = {
  current_ability:'Current ability',
  potential_ability:'Potential ability',
  'attributes.technique':'Technique',
  'attributes.movement':'Movement',
  'attributes.physical':'Physical',
  'attributes.mental':'Mental',
  'attributes.consistency':'Consistency',
  'attributes.clutch':'Clutch',
  'attributes.recovery':'Recovery'
}
function observed(player: RunInitialWorldPlayer, field: GeneratedPlayerFieldKey): number | undefined {
  if (field === 'current_ability' || field === 'potential_ability') return player[field]
  return player.attributes?.[field.split('.')[1]]
}
export function GeneratedPlayerFieldLockEditor({
  player, locks, onChange, onApply, onRegenerate, onClose, busy, disabled, dirty, error, seed
}: {
  player: RunInitialWorldPlayer
  locks: RunWorldPreviewFieldLock[]
  onChange: (field: GeneratedPlayerFieldKey, value: number | null) => void
  onApply: () => void
  onRegenerate: () => void
  onClose: () => void
  busy: boolean
  disabled: boolean
  dirty: boolean
  error?: string | null
  seed: number
}): JSX.Element {
  const [entered, setEntered] = useState<Partial<Record<GeneratedPlayerFieldKey,string>>>({})
  const [localError,setLocalError] = useState('')
  const valueFor = (field: GeneratedPlayerFieldKey) => {
    const locked = locks.find(v => v.player_id === player.player_id && v.field === field)
    return entered[field] ?? String(locked?.value ?? observed(player,field) ?? '')
  }
  const lock = (field: GeneratedPlayerFieldKey) => {
    const raw=valueFor(field)
    const n=Number(raw)
    if (!/^[0-9]+$/.test(raw) || !Number.isInteger(n) || n < 1 || n > 99) {
      setLocalError(field + ': value must be a whole number from 1 to 99.')
      return
    }
    onChange(field,n);setLocalError('')
  }
  return <aside className="generated-field-editor" role="region" aria-label="Generated player field editor">
    <div className="actions">
      <h5>Preview field editor · {player.name}</h5>
      <button type="button" onClick={onClose} aria-label="Close player field editor">Close</button>
    </div>
    <p><code>{player.player_id}</code> · {player.country_code} · {player.age_years_at_season_start} years</p>
    <p className="status">Only legacy source abilities 1–99 exist here; not canonical OVR 0–200.
      Locked values constrain this preview and are not permanent career locks.
      Height and unimplemented 57 canonical attributes are unavailable.</p>
    <div className="form-grid">
      {PREVIEW_FIELD_KEYS.map(field=>{
        const known = observed(player,field)
        const locked = locks.find(v=>v.player_id===player.player_id && v.field===field)
        return <div key={field}>
          <label>{labels[field]} (1–99)
            <input type="number" min={1} max={99} step={1}
              aria-label={'Preview field '+field}
              disabled={disabled || known == null}
              value={valueFor(field)}
              onChange={event=>setEntered(v=>({...v,[field]:event.target.value}))} />
          </label>
          <div className="actions">
            <button type="button" disabled={disabled || known == null}
              aria-label={'Lock preview field '+field} onClick={()=>lock(field)}>
              {locked ? 'Update lock' : 'Lock field'}
            </button>
            <button type="button" disabled={disabled || !locked}
              aria-label={'Automatic preview field '+field}
              onClick={()=>{onChange(field,null);setEntered(v=>({...v,[field]:undefined}))}}>
              Automatic
            </button>
            {locked && <strong aria-label={'Locked preview field '+field}>🔒 {locked.value}</strong>}
          </div>
        </div>
      })}
    </div>
    {localError && <p role="alert">{localError}</p>}
    {error && <p role="alert">Conflicting field locks: {error}</p>}
    {dirty && <p role="status">Pending field locks must be previewed by the server before Adopt.</p>}
    <div className="actions">
      <button type="button" disabled={!dirty || busy || disabled}
        onClick={onApply}>Apply field locks to preview</button>
      <button type="button" disabled={dirty || busy || disabled || !locks.length}
        onClick={onRegenerate} title="Use the next seed; missing identities or incompatible values return a conflict">
        Regenerate other fields · seed {seed}
      </button>
    </div>
  </aside>
}
