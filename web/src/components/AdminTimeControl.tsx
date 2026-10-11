import { useAdminTime } from '../admin/AdminTimeContext'

export function AdminTimeControl(): JSX.Element {
  const time = useAdminTime()
  const unavailable = time.mode === 'present' ? time.error || !time.branchId : time.checkpointsError || !time.selectedCheckpoint
  const locator = time.mode === 'present' && time.isLoading ? 'Loading…' : unavailable ? 'Unavailable' : time.viewSeason != null && time.viewWeek != null
    ? `S${time.viewSeason} · W${time.viewWeek}`
    : '—'
  const event = time.viewEventId ? `, event ${time.viewEventId}` : ''

  return (
    <div
      className="admin-time-compact"
      aria-label="Admin view time"
      title={`${time.mode === 'present' ? 'Present Branch HEAD' : `Historical checkpoint ${time.viewCheckpointId}`}: ${locator}${event}`}
    >
      <label><span>Time</span> <strong>{time.mode === 'present' ? 'Present' : 'Past'} · {locator}</strong>
        <select aria-label="Admin Time context" value={time.mode === 'present' ? 'present' : time.viewCheckpointId ?? ''} onChange={event => event.target.value === 'present' ? time.selectPresent() : time.selectCheckpoint(event.target.value)}>
          <option value="present">Present — Branch HEAD</option>
          {time.checkpoints.map(checkpoint => <option key={checkpoint.checkpoint_id} value={checkpoint.checkpoint_id}>
            #{checkpoint.sequence} · S{checkpoint.season} · {checkpoint.week == null ? '—' : `W${checkpoint.week}`} · {checkpoint.event_id ?? checkpoint.command_kind ?? checkpoint.kind}
          </option>)}
        </select>
      </label>
      {time.checkpointsLoading ? <span className="sr-only" role="status">Loading historical checkpoints…</span> : null}
      {time.checkpointsError ? <span className="sr-only" role="status">Historical checkpoints unavailable: {time.checkpointsError}</span> : null}
      {time.error ? <span className="sr-only" role="status">Admin Time unavailable: {time.error}</span> : null}
    </div>
  )
}
