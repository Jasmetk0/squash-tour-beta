import { ApiError } from '../api/client'

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // Fall back to the raw API error text when body is not JSON.
    }
    return error.message
  }

  if (error instanceof Error) return error.message
  return String(error)
}

export function isApiNotFound(error: unknown): boolean {
  if (error instanceof ApiError) return error.status === 404
  if (typeof error === 'object' && error !== null && 'status' in error) {
    return (error as { status?: unknown }).status === 404
  }
  return false
}
