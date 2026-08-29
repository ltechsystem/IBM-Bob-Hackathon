/**
 * src/api/sentinel.ts
 *
 * Typed client for the Sentinel-related FastAPI endpoints.
 * All paths are prefixed with /api, which Vite proxies to http://localhost:8000
 * in development (see vite.config.ts).
 */

// ---------------------------------------------------------------------------
// Types — mirrors api/models.py SentinelEvent and ClassificationResult
// ---------------------------------------------------------------------------

export type SentinelEventType =
  | 'WATCHER_STARTED'
  | 'COMPILE_DETECTED'
  | 'DIFF_READY'
  | 'TESTS_RUNNING'
  | 'TESTS_PASSED'
  | 'TESTS_FAILED'
  | 'CLASSIFYING'
  | 'CLASSIFICATION_READY'
  | 'SNAPSHOT_UPDATED'
  | 'WATCHER_ERROR'
  | 'WATCHER_STOPPED'

export interface SentinelEvent {
  event_type: SentinelEventType
  member: string
  lib: string
  srcpf: string
  message: string
  diff?: string | null
  test_output?: string | null
  tests_run?: number | null
  tests_failed?: number | null
  test_name?: string | null
  timestamp: string
}

export type ClassificationVerdict = 'STALE_TEST' | 'REGRESSION' | 'UNCERTAIN'
export type RecommendedAction = 'UPDATE_TEST' | 'FIX_CODE' | 'ASK_HUMAN' | 'ADD_TEST' | 'NO_ACTION'
export type ReviewAction = 'ACCEPT' | 'REJECT' | 'FLAG'

export interface ClassificationResult {
  test_name: string
  classification: ClassificationVerdict
  confidence: number
  reason: string
  recommended_action: RecommendedAction
  proposed_diff?: string | null
  needs_human_review: boolean
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BASE = '/api'

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`POST ${path} failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<T>
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`GET ${path} failed (${res.status}): ${text}`)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Fetch the full list of historical sentinel events (REST poll). */
export function fetchSentinelEvents(member?: string): Promise<SentinelEvent[]> {
  const qs = member ? `?member=${encodeURIComponent(member)}` : ''
  return getJson<SentinelEvent[]>(`/sentinel/events${qs}`)
}

/** Fetch all stored classification results. */
export function fetchClassificationResults(): Promise<ClassificationResult[]> {
  return getJson<ClassificationResult[]>('/results')
}

/** Submit a developer review action (Accept / Reject / Flag). */
export function postReviewAction(testName: string, action: ReviewAction): Promise<{ status: string }> {
  return postJson('/review-action', { test_name: testName, action })
}

/**
 * Open a Server-Sent Events connection to /api/sentinel/stream.
 *
 * @param onEvent   Called for each parsed SentinelEvent.
 * @param onError   Called on connection error (optional).
 * @returns An EventSource that can be closed with .close().
 */
export function subscribeSentinelStream(
  onEvent: (event: SentinelEvent) => void,
  onError?: (err: Event) => void,
): EventSource {
  const es = new EventSource(`${BASE}/sentinel/stream`)
  es.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as SentinelEvent
      onEvent(parsed)
    } catch {
      // ignore malformed frames
    }
  }
  if (onError) es.onerror = onError
  return es
}
