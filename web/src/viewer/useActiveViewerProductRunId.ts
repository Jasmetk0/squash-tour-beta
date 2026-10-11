import { useEffect, useState } from 'react'
import { VIEWER_ACTIVE_PRODUCT_RUN_CHANGED_EVENT, readViewerActiveProductRunId } from './activeProductRun'

export function useActiveViewerProductRunId(): string | null {
  const [productRunId, setProductRunId] = useState(readViewerActiveProductRunId)
  useEffect(() => {
    const update = () => setProductRunId(readViewerActiveProductRunId())
    window.addEventListener(VIEWER_ACTIVE_PRODUCT_RUN_CHANGED_EVENT, update)
    window.addEventListener('storage', update)
    return () => { window.removeEventListener(VIEWER_ACTIVE_PRODUCT_RUN_CHANGED_EVENT, update); window.removeEventListener('storage', update) }
  }, [])
  return productRunId
}
