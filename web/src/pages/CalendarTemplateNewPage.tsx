import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { createCalendarTemplate } from '../api/client'
import type { CalendarTemplateUpsertPayload } from '../api/types'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { CalendarTemplateEditor, emptyCalendarTemplateFormValue } from './CalendarTemplateEditor'

export function AdminCalendarTemplateNewPage(): JSX.Element {
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: (payload: CalendarTemplateUpsertPayload) => createCalendarTemplate(payload),
    onSuccess: (response, payload) => {
      const templateId = response.template?.id ?? payload.id
      navigate(`/admin/tour-seasons/season-templates/calendar/${encodeURIComponent(templateId)}`)
    }
  })

  return (
    <section className="panel">
      <PageIntro
        title="Create persisted Admin calendar template"
        subtitle="Admin-only create UI for persisted calendar templates. This does not mutate canonical seasons, Viewer, runs, rankings, race, history, or simulation output."
      />
      <SectionCard title="Safety boundary">
        <p>
          This create form saves only a persisted Admin calendar template. It does not mutate canonical seasons, Viewer,
          runs, rankings, race, history, or simulation output.
        </p>
      </SectionCard>
      <SectionCard title="Create form">
        {mutation.error ? <p role="alert" className="error">Create failed: {formatApiError(mutation.error)}</p> : null}
        <CalendarTemplateEditor
          mode="create"
          initialValue={emptyCalendarTemplateFormValue()}
          idEditable={true}
          submitLabel="Create persisted calendar template"
          isSubmitting={mutation.isPending}
          onSubmit={(payload) => mutation.mutate(payload)}
        />
      </SectionCard>
      <SectionCard title="Navigation">
        <p><Link to="/admin/tour-seasons/season-templates">Back to Season Templates</Link></p>
      </SectionCard>
    </section>
  )
}
