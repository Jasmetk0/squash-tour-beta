import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { resolveAdminGroupStandingsTie } from '../api/client'
import type { GroupStandingsTieState } from '../api/tournamentGroupStandings'
import { newCommandId } from '../admin/branchSimulation'
import { formatApiError } from '../utils/apiErrors'
import { useLanguage } from '../i18n/LanguageContext'

type Props = {
  runId: string
  branchId: string
  eventId: string
  tieState: GroupStandingsTieState
  enabled: boolean
  onResolution: () => Promise<unknown>
}

/** Explicit operator decision over the exact server-fingerprinted unresolved case. */
export function GroupTieResolutionEditor({
  runId, branchId, eventId, tieState, enabled, onResolution,
}: Props): JSX.Element | null {
  const {language}=useLanguage(),cs=language==='cs'
  const tie = tieState.unresolved_case
  const fingerprint = tieState.unresolved_case_fingerprint
  const [order, setOrder] = useState<string[]>(() => [...(tie?.player_ids ?? [])])
  const [reason, setReason] = useState('')
  const [approved, setApproved] = useState(false)
  const [commandId, setCommandId] = useState(() => newCommandId())

  useEffect(() => {
    // A previous Admin decision cannot be reused for another case or branch.
    setOrder([...(tie?.player_ids ?? [])])
    setReason('')
    setApproved(false)
    setCommandId(newCommandId())
  }, [runId, branchId, eventId, fingerprint])

  const validOrder = Boolean(tie && order.length === tie.player_ids.length &&
    new Set(order).size === order.length && order.every(id => tie.player_ids.includes(id)))
  const validReason = reason.trim().length > 0 && reason.length <= 1000
  const validFingerprint = Boolean(fingerprint && /^[a-f0-9]{64}$/.test(fingerprint))
  const mutation = useMutation({
    mutationFn: () => {
      if (!tie || !fingerprint || !validFingerprint || !validOrder || !validReason ||
          !approved || !enabled) {
        throw new Error('An exact confirmed Admin tie decision is required.')
      }
      return resolveAdminGroupStandingsTie(runId, branchId, eventId, tie.player_ids, {
        command_id: commandId,
        case_fingerprint: fingerprint,
        ordered_player_ids: order,
        admin_reason: reason.trim(),
      })
    },
    onSuccess: async () => {
      setApproved(false)
      setReason('')
      setCommandId(newCommandId())
      await onResolution()
    },
    onError: async () => {
      setApproved(false)
      await onResolution()
    },
  })

  if (!tie) return null

  const move = (index: number, delta: number) => {
    const other = index + delta
    if (other < 0 || other >= order.length) return
    const next = [...order]
    ;[next[index], next[other]] = [next[other], next[index]]
    setOrder(next)
    setApproved(false)
  }

  return <div className="grid" role="group" aria-label={cs?'Výslovné rozhodnutí shody ve skupině':'Explicit group tie decision'}>
    <h4>{cs?'Prověřit nerozhodné pořadí ve skupině':'Review unresolved Group'} {tie.group_index}{cs?'':' ordering'}</h4>
    <p>{cs?'Sportovní kritéria nedokázala rozhodnout pořadí':'The sporting tie-break criteria could not resolve this order'} ({tie.reason}).
      {cs?' Přesuň hráče do zamýšleného konečného pořadí. Výchozí seznam je pouze návrh k prověření, nikoli automatické rozhodnutí.':
      ' Move each exact participant into your intended final order. The initial list is only a review proposal, not a generated tie-break decision.'}</p>
    <p>{cs?'Otisk případu':'Case fingerprint'}: <code>{fingerprint ?? (cs?'Chybí':'Missing')}</code></p>
    <ol aria-label={cs?'Navržené pořadí při shodě':'Proposed tie order'}>
      {order.map((id, index) => <li key={id}>
        <code>{id}</code>{' '}
        <button type="button" aria-label={cs?`Posunout hráče ${id} nahoru`:`Move ${id} up`}
          onClick={() => move(index, -1)} disabled={!enabled || mutation.isPending || index === 0}>
          ↑
        </button>{' '}
        <button type="button" aria-label={cs?`Posunout hráče ${id} dolů`:`Move ${id} down`}
          onClick={() => move(index, 1)} disabled={!enabled || mutation.isPending || index === order.length - 1}>
          ↓
        </button>
      </li>)}
    </ol>
    <label>{cs?'Auditní důvod rozhodnutí shody':'Admin tie decision reason'}
      <textarea aria-label={cs?'Auditní důvod rozhodnutí shody':'Admin tie decision reason'} rows={3} maxLength={1000}
        value={reason} onChange={e => { setReason(e.target.value); setApproved(false) }}
        disabled={!enabled || mutation.isPending}/>
    </label>
    <label><input type="checkbox" checked={approved}
      aria-label={cs?'Potvrdit přesné pořadí hráčů a auditní důvod':'Confirm this exact player order and recorded audit reason'}
      onChange={e => setApproved(e.target.checked)}
      disabled={!enabled || mutation.isPending || !validOrder || !validReason || !validFingerprint}/>
      {cs?'Potvrdit přesné pořadí hráčů a auditní důvod':'Confirm this exact player order and recorded audit reason'}
    </label>
    <button type="button" onClick={() => mutation.mutate()}
      disabled={!enabled || !validOrder || !validReason || !validFingerprint ||
        !approved || mutation.isPending}>
      {cs?'Uložit auditované rozhodnutí shody':'Commit audited group tie decision'}
    </button>
    {mutation.isPending ? <p role="status">{cs?'Ukládám přesné rozhodnutí shody…':'Recording exact tie decision…'}</p> : null}
    {mutation.isSuccess ? <p role="status">{cs?'Rozhodnutí bylo zaznamenáno. Před vytvořením konečné tabulky se znovu ověří další nerozhodná shoda.':
      'Tie decision recorded. Rechecking the next unresolved case before final table generation.'}</p> : null}
    {mutation.error ? <p role="alert">
      {cs?'Rozhodnutí shody nebylo uloženo: ':'Group tie decision not committed: '}{formatApiError(mutation.error)}.
      {cs?' Před dalším pokusem znovu ověř aktuální případ.':' Recheck the live case before retrying.'}
    </p> : null}
  </div>
}
