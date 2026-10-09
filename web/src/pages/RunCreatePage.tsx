import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createEmptyRunContainer } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { writeLastRunId } from '../viewer/activeRun'

/** The canonical Run creation flow: no preselected world, seed or legacy Simulation Run. */
export function RunCreatePage(): JSX.Element {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const displayName = name.trim()
    if (!displayName || pending) return
    setPending(true)
    setError(null)
    try {
      const created = await createEmptyRunContainer(displayName)
      if (!created.run_id || created.display_name !== displayName || created.read_only || created.storage_kind !== 'custom_local') {
        throw new Error('The server returned an unexpected Run identity or ownership. Refresh the Run browser before continuing.')
      }
      writeLastRunId(created.run_id)
      await queryClient.invalidateQueries({ queryKey: ['canonical-run-containers'] })
      navigate(`/admin/runs/${encodeURIComponent(created.run_id)}`)
    } catch (cause) {
      setError(`Could not create test Run: ${formatApiError(cause)}`)
    } finally {
      setPending(false)
    }
  }

  return <section className="panel">
    <PageIntro title="Create test Run" subtitle="Start a separate Product Run and add independent World and Calendar copies later." />
    <SectionCard title="New Product Run">
      <form onSubmit={event => { void submit(event) }}>
        <label htmlFor="new-run-name">Unique Run name</label>
        <input id="new-run-name" value={name} maxLength={120} required
          autoComplete="off" onChange={event => setName(event.target.value)} />
        <p className="status">A new Run starts empty at 2000/01 with its own Timeline 1, initial Saved Revision and clean Working Draft. This does not change any existing or Official Run.</p>
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit" disabled={pending || !name.trim()}>{pending ? 'Creating Run…' : 'Create isolated Run'}</button>
        {' '}<Link to="/admin/runs">Back to Runs</Link>
      </form>
    </SectionCard>
  </section>
}
