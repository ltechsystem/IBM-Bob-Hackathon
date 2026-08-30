/**
 * Shared TypeScript types that mirror the Pydantic models in backend/models.py.
 * All frontend components import their types from here — never from mockdata/.
 */

export interface LogLine {
  time: string
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

export interface IncidentBrief {
  id: string
  title: string
  severity: 'P1' | 'P2' | 'P3'
  service: string
  errorType: string
  errorMessage: string
  affectedEndpoint: string
  reportedAt: string
}

export interface EvidenceFile {
  path: string
  relevance: 'HIGH' | 'MEDIUM' | 'LOW'
  reason: string
}

export interface SubagentFinding {
  agent: string
  focus: string
  finding: string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface RootCause {
  file: string
  line: number
  summary: string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  explanation: string
}

export interface DiffHunk {
  file: string
  before: string[]
  after: string[]
  lineNumber: number
}

export interface TestResult {
  name: string
  status: 'PASSED' | 'FAILED'
  message?: string
}

export interface PipelineResult {
  incident: IncidentBrief
  logLines: LogLine[]
  evidenceFiles: EvidenceFile[]
  subagentFindings: SubagentFinding[]
  rootCause: RootCause
  diffHunk: DiffHunk
  testResults: TestResult[]
}

// ---------------------------------------------------------------------------
// Sentinel classification (IBM i RPG test maintenance)
// ---------------------------------------------------------------------------

export type SentinelVerdict =
  | 'STALE'
  | 'REGRESSION'
  | 'NEW_COVERAGE_NEEDED'
  | 'UNCERTAIN'

export interface SentinelClassification {
  _db_id?: number
  lib: string
  srcpf: string
  mbr: string
  test_name: string
  verdict: SentinelVerdict
  confidence: number
  rationale: string
  proposed_patch?: string | null
  developer_action?: string | null
  received_at?: string | null
}
