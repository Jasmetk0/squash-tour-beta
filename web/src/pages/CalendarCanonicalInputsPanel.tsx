import { useEffect, useRef, useState } from 'react'
import { previewCalendarCanonicalKnockout } from '../api/client'
import { verifyCanonicalKnockoutSource, type CanonicalKnockoutSource } from '../api/calendarOpeningKnockout'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export function CalendarCanonicalInputsPanel({ runId, branchId, head, world, entrants, source }: {
  runId: string; branchId: string; head: string; world: string; entrants: string[]
  source?: CanonicalKnockoutSource
}) {
  const cs = useLanguage().language === 'cs'
  const target = [runId, branchId, head, world, ...entrants].join('|')
  const current = useRef(target), epoch = useRef(0)
  if (current.current !== target) { current.current = target; epoch.current += 1 }
  const [preview, setPreview] = useState<{ target: string; source: CanonicalKnockoutSource } | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null)
  useEffect(() => { setPreview(null); setBusy(false); setError(null) }, [target])
  useEffect(() => () => { epoch.current += 1 }, [])
  const shown = source ?? (preview?.target === target ? preview.source : undefined)
  const review = async () => {
    const requested = epoch.current, from = target
    const valid = () => current.current === from && epoch.current === requested
    setBusy(true); setError(null)
    try {
      const value = await previewCalendarCanonicalKnockout(runId, branchId, {
        expected_saved_head: head, expected_initial_world_fingerprint: world, entrant_ids: entrants,
      })
      if (!valid()) return
      if (value.schema_version !== 'calendar_canonical_knockout_preview.v1' || value.run_id !== runId
        || value.branch_id !== branchId || value.saved_head_revision_id !== head
        || !/^[0-9a-f]{64}$/.test(value.fingerprint)) throw Error('Canonical preview source changed')
      setPreview({ target: from, source: verifyCanonicalKnockoutSource(value.source, world, entrants) })
    } catch (err) { if (valid()) setError(formatApiError(err)) }
    finally { if (valid()) setBusy(false) }
  }
  return <div aria-label="Canonical knockout attribute inputs">
    <h4>{cs ? 'Kanonické hráčské atributy' : 'Canonical player attributes'}</h4>
    <p className="status">{cs
      ? '57 atributů na škále 0–200. Provizorní převod z uložené počáteční populace; nejde o simulaci historického ani ročního vývoje. Zápasový engine používá verzovanou projekci těchto 57 hodnot.'
      : '57 attributes on a 0–200 scale. Provisional conversion from the Saved initial population; no historical or annual development is simulated. MatchEngine uses a versioned projection of these 57 values.'}</p>
    {source ? <p>{cs ? 'Zmrazené atributy použité při odehrání.' : 'Frozen attributes used when played.'}</p>
      : <><p>{cs ? 'Náhled nic neodehraje ani neuloží.' : 'Preview does not play or Save anything.'}</p>
        <button type="button" disabled={busy || new Set(entrants).size !== 4 || entrants.some(id => !id)}
          onClick={() => void review()}>{cs ? 'Zobrazit 57 atributů' : 'Preview 57 attributes'}</button></>}
    {error && <p role="alert">{error}</p>}
    {shown?.records.map(record => <details key={record.player_id}>
      <summary>{cs ? '57 atributů' : '57 attributes'} · {record.player_id}</summary>
      <table aria-label={`${cs ? 'Atributy' : 'Attributes'} ${record.player_id}`}><thead><tr>
        <th>{cs ? 'Atribut' : 'Attribute'}</th><th>{cs ? 'Hodnota / 200' : 'Value / 200'}</th>
      </tr></thead><tbody>{record.attributes.map(([name, value]) => <tr key={name}>
        <td>{name}</td><td>{value}</td>
      </tr>)}</tbody></table>
    </details>)}
  </div>
}
