import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { deleteRunFollow, getRunFollows, putRunFollow } from '../api/client'
import { validFollowList } from '../api/followNotifications'
import { formatApiError } from '../utils/apiErrors'

type Props = { runId: string; kind: 'player' | 'country'; subjectId: string; cs: boolean }

/** Run-level follow toggle (a preference, never Saved content; it changes no sport). */
export function FollowStar({ runId, kind, subjectId, cs }: Props): JSX.Element {
  const client = useQueryClient()
  const key = ['run-follows', runId]
  const follows = useQuery({ queryKey: key, queryFn: () => getRunFollows(runId), retry: false })
  const toggle = useMutation({
    mutationFn: (on: boolean) => (on ? putRunFollow(runId, kind, subjectId, true) : deleteRunFollow(runId, kind, subjectId)),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: key })
      void client.invalidateQueries({ queryKey: ['follow-alerts', runId] })
    }
  })
  const list = follows.data && validFollowList(follows.data, runId) ? follows.data : null
  if (follows.isPending) return <span role="status">{cs ? 'Sledování…' : 'Following…'}</span>
  if (!list) {
    return <span role="status">{cs ? 'Sledování není dostupné' : 'Following is unavailable'}
      {follows.error ? `: ${formatApiError(follows.error)}` : ''}</span>
  }
  const on = list.follows.some(f => f.kind === kind && f.subject_id === subjectId)
  const label = on ? (cs ? 'Přestat sledovat' : 'Unfollow') : (cs ? 'Sledovat' : 'Follow')
  return <span>
    <button type="button" aria-pressed={on} disabled={toggle.isPending} onClick={() => toggle.mutate(!on)}
      title={cs ? 'Sledování platí pro celý Run a nemění simulaci.' : 'Following applies to the whole Run and does not change the simulation.'}>
      {on ? '★' : '☆'} {label}</button>
    {toggle.error && <span role="alert"> {formatApiError(toggle.error)}</span>}
  </span>
}
