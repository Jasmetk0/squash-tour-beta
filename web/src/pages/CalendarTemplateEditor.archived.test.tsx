import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  CalendarTemplateEditor, emptyCalendarTemplateFormValue, formValueFromTemplate
} from './CalendarTemplateEditor'

describe('Calendar template archived status safety', () => {
  const source = {
    id: 'archived-one', name: 'Archived Calendar', status: 'archived' as const,
    description: 'An existing archived source', events: [{
      id: 'final', name: 'Final', category_code: 'DIAMOND', weeks: [10],
      qualification_weeks: [], locked: true, country_code: 'ENG',
    }],
  }

  it('preserves archived status rather than silently substituting draft', () => {
    const value = formValueFromTemplate(source)
    expect(value.status).toBe('archived')
    expect(value.events[0].weeksText).toBe('10')
  })

  it('prevents editing and saving archived sources until an explicit restoration workflow exists', () => {
    const submit = vi.fn()
    render(<CalendarTemplateEditor
      mode="update" initialValue={formValueFromTemplate(source)} idEditable={false}
      onSubmit={submit} submitLabel="Update persisted calendar template"
    />)
    expect(screen.getByRole('status')).toHaveTextContent('Archived calendar templates are read-only.')
    expect(screen.getByRole('combobox', { name: 'Template status' })).toHaveValue('archived')
    expect(screen.getByRole('combobox', { name: 'Template status' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Template name' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add event row' })).toBeDisabled()
    const save = screen.getByRole('button', { name: 'Update persisted calendar template' })
    expect(save).toBeDisabled()
    fireEvent.click(save)
    expect(submit).not.toHaveBeenCalled()
  })

  it('does not prevent normal draft authoring or saving', () => {
    const submit = vi.fn()
    render(<CalendarTemplateEditor
      mode="create" initialValue={{ ...emptyCalendarTemplateFormValue(), id: 'new-one', name: 'New template' }}
      idEditable onSubmit={submit} submitLabel="Create persisted calendar template"
    />)
    expect(screen.queryByText(/Archived calendar templates are read-only/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create persisted calendar template' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Create persisted calendar template' }))
    expect(submit).toHaveBeenCalledWith(expect.objectContaining({
      id: 'new-one', name: 'New template', status: 'draft', events: [],
    }))
  })
})
