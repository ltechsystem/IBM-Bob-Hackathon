/**
 * API client for the Bob Debug Agent backend.
 *
 * All fetch calls go through here. The Vite dev server proxies /api/* to
 * http://localhost:8000 (see vite.config.ts). In production, requests hit the
 * same origin.
 */

import type { PipelineResult, IncidentBrief, SentinelClassification } from './types'

const BASE = '/api'

export interface RunIncidentRequest {
  id: string
  title: string
  severity: 'P1' | 'P2' | 'P3'
  service: string
  errorType: string
  errorMessage: string
  affectedEndpoint: string
  logPath?: string
  rawLog?: string
}

export interface IncidentSummary {
  id: string
  title: string
  severity: 'P1' | 'P2' | 'P3'
  service: string
  created_at: string
}

/** List all stored incidents (lightweight summaries). */
export async function listIncidents(): Promise<IncidentSummary[]> {
  const res = await fetch(`${BASE}/incidents`)
  if (!res.ok) throw new Error(`Failed to list incidents: ${res.status}`)
  return res.json()
}

/**
 * Load an existing stored pipeline result.
 * Returns null when the incident has not been run yet.
 */
export async function loadIncident(id: string): Promise<PipelineResult | null> {
  const res = await fetch(`${BASE}/incidents/${id}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Failed to load incident ${id}: ${res.status}`)
  return res.json()
}

/**
 * Run the full pipeline for a new incident request.
 * The backend persists the result automatically.
 */
export async function runIncident(req: RunIncidentRequest): Promise<PipelineResult> {
  const res = await fetch(`${BASE}/incidents/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Pipeline failed: ${res.status} ${text}`)
  }
  return res.json()
}

/**
 * Load an existing result or, if none exists, run the pipeline.
 * This is the primary entry point used by App.tsx.
 */
export async function fetchOrRunIncident(req: RunIncidentRequest): Promise<PipelineResult> {
  const existing = await loadIncident(req.id)
  if (existing !== null) return existing
  return runIncident(req)
}

/** Delete a stored incident from the database. */
export async function deleteIncident(id: string): Promise<void> {
  const res = await fetch(`${BASE}/incidents/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete incident ${id}: ${res.status}`)
}

/** Fetch all Sentinel RPG test classification results, newest first. */
export async function listSentinelResults(): Promise<SentinelClassification[]> {
  const res = await fetch(`${BASE}/sentinel/results`)
  if (!res.ok) throw new Error(`Failed to fetch Sentinel results: ${res.status}`)
  return res.json()
}
