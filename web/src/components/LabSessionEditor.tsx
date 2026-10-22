import { useRef, useState } from 'react'

type Session = { session_id: string; display_name: string; version: number; session_fingerprint: string; scenario: unknown }
export type LabEditorTicket = { selection: number; edit: number }

/** An inventory refresh is discovery, never permission to replace an editor. */
export function useLabSessionEditor<T extends Session>(inventory: T[] | undefined, inventoryReady: boolean, initialText: string, initialName: string) {
  type Editor = { session: T | null; text: string; name: string; selection: number; edit: number }
  const [state, setState] = useState<Editor>({ session: null, text: initialText, name: initialName, selection: 0, edit: 0 })
  const current = useRef(state)
  const change = (next: Editor) => { current.current = next; setState(next) }
  const selectSnapshot = (session: T | null) => {
    const previous = current.current
    change({
      session, text: session ? JSON.stringify(session.scenario, null, 2) : previous.text,
      name: session?.display_name ?? previous.name, selection: previous.selection + 1, edit: 0
    })
  }
  const remote = inventory?.find(item => item.session_id === state.session?.session_id)
  const conflict = !state.session ? null : !inventoryReady ? 'unavailable'
    : !remote ? 'missing' : remote.session_fingerprint !== state.session.session_fingerprint ? 'changed' : null
  let unchanged = false
  try { unchanged = JSON.stringify(JSON.parse(state.text)) === JSON.stringify(state.session?.scenario) } catch { /* retain malformed edits */ }
  const dirty = Boolean(state.session && (state.name !== state.session.display_name || !unchanged))

  return {
    selectedSession: state.session, selectedSessionId: state.session?.session_id ?? null,
    scenarioText: state.text, sessionName: state.name, sessionHasUnsavedChanges: dirty, editorEdit: state.edit,
    sessionConflict: conflict, canReloadSession: Boolean(inventoryReady && remote),
    setScenarioText: (text: string) => change({ ...current.current, text, edit: current.current.edit + 1 }),
    setSessionName: (name: string) => change({ ...current.current, name, edit: current.current.edit + 1 }),
    setSelectedSessionId: (id: string | null) => {
      const session = id ? inventory?.find(item => item.session_id === id) : null
      if (id && !session) return
      selectSnapshot(session ?? null)
    },
    reloadSession: () => { if (inventoryReady && remote) selectSnapshot(remote) },
    captureEditor: (): LabEditorTicket => ({ selection: current.current.selection, edit: current.current.edit }),
    acceptSession: (session: T, ticket: LabEditorTicket, rebaseEdits = true): boolean => {
      const previous = current.current
      if (previous.selection !== ticket.selection) return false
      // Our own acknowledged Save can advance the baseline, but cannot eat
      // text entered while the request was in flight. Another selection wins.
      const edited = previous.edit !== ticket.edit
      if (edited && (!rebaseEdits || previous.session?.session_id !== session.session_id)) return false
      change({ ...previous, session,
        text: edited ? previous.text : JSON.stringify(session.scenario, null, 2),
        name: edited ? previous.name : session.display_name })
      return true
    }
  }
}

export function validateLabSession<T extends Session>(session: T, expectedId?: string): T {
  if (!session || !session.session_id || (expectedId && session.session_id !== expectedId)
    || !Number.isSafeInteger(session.version) || session.version < 1
    || !/^[a-f0-9]{64}$/.test(session.session_fingerprint)
    || typeof session.display_name !== 'string' || !session.scenario) {
    throw new Error('Test Session response identity is inconsistent. Refresh the inventory before continuing.')
  }
  return session
}

export function LabSessionConflict({ conflict, dirty, canReload, onReload }: {
  conflict: string | null; dirty: boolean; canReload: boolean; onReload: () => void
}): JSX.Element | null {
  const [discardApproved, setDiscardApproved] = useState(false)
  if (!conflict) return null
  return <div>
    <p role="alert" className="error">{conflict === 'changed'
      ? 'The saved Test Session changed. Local editor contents were preserved.'
      : conflict === 'missing' ? 'The selected Test Session is no longer in the inventory. Local editor contents were preserved.'
        : 'The saved Test Session could not be verified. Local editor contents were preserved.'}
      {' '}Refresh the inventory and explicitly reload the saved version before running or saving.</p>
    {canReload && <>
      {dirty && <label><input type="checkbox" checked={discardApproved}
        onChange={event => setDiscardApproved(event.target.checked)} /> Discard local edits when reloading</label>}
      <button type="button" disabled={dirty && !discardApproved} onClick={() => { setDiscardApproved(false); onReload() }}>
        Reload saved Test Session
      </button>
    </>}
  </div>
}
