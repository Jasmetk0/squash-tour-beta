import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { previewRankingSave, saveRankingPreparation } from '../api/client'
import { formatApiError } from '../utils/apiErrors'

export function RankingSavePanel({ runId, branchId }: { runId: string; branchId: string }): JSX.Element {
  const [opened, setOpened] = useState(false)
  const client = useQueryClient()
  const preview = useQuery({ queryKey: ['ranking-save', runId, branchId], queryFn: () => previewRankingSave(runId, branchId), enabled: opened, retry: false })
  const save = useMutation({
    mutationFn: () => {
      if (!preview.data?.can_save) throw new Error('Refresh the ranking review before saving.')
      return saveRankingPreparation(runId, branchId, preview.data)
    },
    onSuccess: () => { void client.invalidateQueries() },
    onError: () => { void preview.refetch() },
  })
  return <section aria-label="Save ranking preparation">
    {!opened ? <button type="button" onClick={() => setOpened(true)}>Review ranking changes</button> : <>
      <p>Save the current Branch’s prepared ranking history as a recoverable revision. Rankings remain unpublished and the Viewer Branch stays selected.</p>
      {preview.isPending ? <p role="status">Checking ranking changes…</p> : preview.isError ? <p role="alert">{formatApiError(preview.error)}</p> : preview.data && <>
        <p>{preview.data.has_unsaved_changes ? (preview.data.can_save ? 'Ranking changes are ready to save.' : 'Saving is unavailable. Check Branch permissions and resolve pending draft changes.') : 'Ranking preparation is already saved.'}</p>
        <button type="button" disabled={!preview.data.can_save || preview.isFetching || save.isPending} onClick={() => save.mutate()}>Save ranking preparation</button>
      </>}
      <button type="button" disabled={save.isPending || preview.isFetching} onClick={() => { save.reset(); void preview.refetch() }}>Refresh ranking review</button>
      {save.isError && <p role="alert">{formatApiError(save.error)}</p>}
      {save.isSuccess && <p role="status">Ranking preparation saved.</p>}
    </>}
  </section>
}
