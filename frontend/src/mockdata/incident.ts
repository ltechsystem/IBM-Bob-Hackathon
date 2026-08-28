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

export const incidentBrief: IncidentBrief = {
  id: 'INC-2024-001',
  title: "GET /users/{user_id} crashes with AttributeError",
  severity: 'P1',
  service: 'user-service',
  errorType: 'AttributeError',
  errorMessage: "'NoneType' object has no attribute 'name'",
  affectedEndpoint: 'GET /users/{user_id}',
  reportedAt: '2024-01-15 21:14:02 UTC',
}

export const evidenceFiles: EvidenceFile[] = [
  { path: 'app/main.py',           relevance: 'HIGH',   reason: 'Route handler — contains the crashing line' },
  { path: 'app/models.py',         relevance: 'HIGH',   reason: 'User model definition — return type is Optional[User]' },
  { path: 'app/database.py',       relevance: 'MEDIUM', reason: 'DB session factory — get_user() can return None' },
  { path: 'tests/test_users.py',   relevance: 'MEDIUM', reason: 'Existing tests — no test for missing user' },
  { path: 'requirements.txt',      relevance: 'LOW',    reason: 'Dependency versions — FastAPI 0.104' },
]

export const subagentFindings: SubagentFinding[] = [
  {
    agent: 'Subagent A — Log Analyzer',
    focus: 'Error patterns in app logs',
    finding: 'AttributeError on line 13 of app/main.py triggered for GET /users/999 (user does not exist).',
    confidence: 'HIGH',
  },
  {
    agent: 'Subagent B — Code Inspector',
    focus: 'Route handler source code',
    finding: '`user.name` is accessed at line 13 with no None-check. `get_user()` returns `Optional[User]`.',
    confidence: 'HIGH',
  },
  {
    agent: 'Subagent C — Schema Validator',
    focus: 'DB model & return types',
    finding: 'models.py User.name is non-nullable, but get_user() legitimately returns None for missing IDs.',
    confidence: 'HIGH',
  },
  {
    agent: 'Subagent D — Test Coverage',
    focus: 'Existing test suite',
    finding: 'tests/test_users.py has no test for missing user_id. Zero coverage on the error path.',
    confidence: 'MEDIUM',
  },
]

export const rootCause: RootCause = {
  file: 'app/main.py',
  line: 13,
  summary: 'Missing None-check before accessing user.name',
  confidence: 'HIGH',
  explanation:
    'get_user(user_id) returns None when the user does not exist in the database. ' +
    'The route handler at line 13 dereferences user.name without first checking whether ' +
    'user is None, raising AttributeError for any non-existent user_id.',
}

export const diffHunk: DiffHunk = {
  file: 'app/main.py',
  lineNumber: 11,
  before: [
    '@app.get("/users/{user_id}")',
    'def get_user_route(user_id: int, db: Session = Depends(get_db)):',
    '    user = get_user(db, user_id)',
    '    return {"id": user.id, "name": user.name}',
  ],
  after: [
    '@app.get("/users/{user_id}")',
    'def get_user_route(user_id: int, db: Session = Depends(get_db)):',
    '    user = get_user(db, user_id)',
    '    if user is None:',
    '        raise HTTPException(status_code=404, detail="User not found")',
    '    return {"id": user.id, "name": user.name}',
  ],
}

export const testResults: TestResult[] = [
  { name: 'test_get_existing_user',      status: 'PASSED' },
  { name: 'test_get_missing_user_404',   status: 'PASSED', message: 'New regression test — GET /users/999 → 404' },
  { name: 'test_create_user',            status: 'PASSED' },
  { name: 'test_list_users',             status: 'PASSED' },
]
