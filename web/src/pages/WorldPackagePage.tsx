import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChangeEvent, useState } from 'react'

import { exportWorldPackageJson, importWorldPackage } from '../api/client'
import type { WorldPackageImportResponse } from '../api/types'
import { PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function WorldPackagePage(): JSX.Element {
  const queryClient = useQueryClient()
  const [packageText, setPackageText] = useState('')
  const [packageFileName, setPackageFileName] = useState<string | null>(null)
  const [importResult, setImportResult] = useState<WorldPackageImportResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const exportMutation = useMutation({
    mutationFn: exportWorldPackageJson,
    onSuccess: (jsonText) => {
      const blob = new Blob([jsonText], { type: 'application/json;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'world-package-export.json'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setErrorMessage(null)
    },
    onError: (error) => setErrorMessage(`Export failed: ${formatApiError(error)}`)
  })

  const importMutation = useMutation({
    mutationFn: importWorldPackage,
    onSuccess: async (result) => {
      setImportResult(result)
      setErrorMessage(null)
      if (result.ok && !result.dry_run) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['countries-list'] }),
          queryClient.invalidateQueries({ queryKey: ['countries-metadata'] }),
          queryClient.invalidateQueries({ queryKey: ['manual-player-overrides'] })
        ])
      }
    },
    onError: (error) => {
      setImportResult(null)
      setErrorMessage(`Import failed: ${formatApiError(error)}`)
    }
  })

  const busy = exportMutation.isPending || importMutation.isPending

  const onSelectFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setPackageText(text)
    setPackageFileName(file.name)
    setImportResult(null)
    setErrorMessage(null)
  }

  const runImport = (dryRun: boolean) => {
    if (!packageText.trim()) {
      setErrorMessage('Paste world package JSON or upload file first.')
      return
    }
    if (!dryRun && !window.confirm('Apply world package will replace both countries and manual overrides datasets. Continue?')) {
      return
    }
    setImportResult(null)
    setErrorMessage(null)
    importMutation.mutate({ package_text: packageText, dry_run: dryRun })
  }

  return (
    <section className="panel">
      <PageIntro
        title="World Package"
        subtitle="Export/import the full authored world as one JSON package (countries + manual overrides)."
      />

      <SectionCard title="Package workflow">
        <p className="status">Use dry-run to validate package consistency before applying canonical replacement.</p>
        <div className="dashboard-actions-row">
          <button type="button" onClick={() => exportMutation.mutate()} disabled={busy}>
            {exportMutation.isPending ? 'Exporting…' : 'Export world package'}
          </button>
        </div>

        <label>
          Import world package file
          <input type="file" accept=".json,application/json,text/json" onChange={onSelectFile} disabled={busy} />
        </label>

        <label>
          World package JSON
          <textarea
            rows={14}
            value={packageText}
            onChange={(event) => setPackageText(event.target.value)}
            placeholder="Paste world package JSON here"
          />
        </label>

        {packageFileName ? <p className="status">Loaded file: {packageFileName}</p> : null}
        <p className="error">Warning: apply replaces both canonical countries and manual overrides datasets.</p>

        <div className="dashboard-actions-row">
          <button type="button" onClick={() => runImport(true)} disabled={busy || !packageText.trim()}>
            {importMutation.isPending ? 'Validating…' : 'Validate package (dry run)'}
          </button>
          <button type="button" onClick={() => runImport(false)} disabled={busy || !packageText.trim()}>
            {importMutation.isPending ? 'Applying…' : 'Apply package'}
          </button>
        </div>

        {errorMessage ? <p className="error">{errorMessage}</p> : null}

        {importResult ? (
          <>
            <p className={importResult.ok ? 'status' : 'error'}>
              {importResult.ok
                ? importResult.dry_run
                  ? 'Dry-run succeeded. Package is valid for apply.'
                  : 'World package applied to canonical datasets.'
                : 'World package validation failed. No data was written.'}
            </p>

            <SummaryPills
              items={[
                { label: 'Countries records', value: importResult.countries_summary.total_records },
                { label: 'Countries updated', value: importResult.countries_summary.updated_records },
                { label: 'Overrides records', value: importResult.manual_overrides_summary.total_records },
                { label: 'Overrides updated', value: importResult.manual_overrides_summary.updated_records }
              ]}
            />

            {importResult.errors.length ? (
              <ul>
                {importResult.errors.map((item, index) => (
                  <li key={`${item.field ?? 'global'}-${index}`} className="error">
                    {item.field ?? 'package'}: {item.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}
