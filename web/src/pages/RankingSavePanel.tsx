import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { previewRankingSave, saveRankingPreparation } from '../api/client'
import { formatApiError } from '../utils/apiErrors'
import { useRankingWorkflowLanguage, rankingWorkflowText } from './rankingWorkflowText'

export function RankingSavePanel({ runId, branchId }: { runId: string; branchId: string }): JSX.Element {
  const language = useRankingWorkflowLanguage()
  const t = (value: string) => rankingWorkflowText(value, language)
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
  return <section aria-label={t('Save ranking preparation')}>
    {!opened ? <button type="button" onClick={() => setOpened(true)}>{t('Review ranking changes')}</button> : <>
      <p>{t('Save the current Branch’s prepared ranking history as a recoverable revision. Rankings remain unpublished and the Viewer Branch stays selected.')}</p>
      {preview.isPending ? <p role="status">{t('Checking ranking changes…')}</p> : preview.isError ? <p role="alert">{t('Unable to review ranking save.')} {t(formatApiError(preview.error))}</p> : preview.data && <>
        <p>{preview.data.has_unsaved_changes ? (preview.data.can_save ? t('Ranking changes are ready to save.') : t('Saving is unavailable. Check Branch permissions and resolve pending draft changes.')) : t('Ranking preparation is already saved.')}</p>
        <button type="button" disabled={!preview.data.can_save || preview.isFetching || save.isPending} onClick={() => save.mutate()}>{t('Save ranking preparation')}</button>
      </>}
      <button type="button" disabled={save.isPending || preview.isFetching} onClick={() => { save.reset(); void preview.refetch() }}>{t('Refresh ranking review')}</button>
      {save.isPending && <p role="status">{t('Saving ranking preparation…')}</p>}
      {save.isError && <p role="alert">{t('Unable to save ranking preparation.')} {t(formatApiError(save.error))} {t('Save failed. Refresh the review and explicitly retry after resolving the error.')}</p>}
      {save.isSuccess && <p role="status">{t('Ranking preparation saved.')}</p>}
    </>}
  </section>
}
