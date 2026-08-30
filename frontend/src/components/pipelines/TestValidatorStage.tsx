// Stage 7: Test Validator — runs pytest, shows results
import { StageShell } from './shared'
import { StatusIcon } from '../icons/StatusIcon'
import type { TestResult } from '../../api/types'

interface Props { results: TestResult[] }

export default function TestValidatorStage({ results }: Props) {
  const passed = results.filter((r) => r.status === 'PASSED').length
  const failed = results.filter((r) => r.status === 'FAILED').length

  return (
    <StageShell
      stageNumber={7}
      label="test-validator skill"
      title="Test Results"
      description="pytest — before: 1 FAILED → after: ALL PASSED"
    >
      {/* Summary bar */}
      <div className="flex items-center gap-4 rounded-md border border-zinc-800 bg-zinc-900/50 px-4 py-2 text-sm">
        <StatusIcon kind="success" size="h-4 w-4" decorative />
        <span className="font-mono font-semibold text-emerald-400">{passed} passed</span>
        {failed > 0 && (
          <>
            <StatusIcon kind="failure" size="h-4 w-4" decorative />
            <span className="font-mono font-semibold text-red-400">{failed} failed</span>
          </>
        )}
        <span className="ml-auto font-mono text-xs text-zinc-600">tests/test_users_fixed.py</span>
      </div>
      {/* Individual tests */}
      <ul className="flex flex-col gap-1">
        {results.map((r) => (
          <li key={r.name} className="flex items-start gap-2.5 rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
            <StatusIcon
              kind={r.status === 'PASSED' ? 'success' : 'failure'}
              size="h-4 w-4"
              decorative={false}
            />
            <div>
              <code className="text-xs text-zinc-200">{r.name}</code>
              {r.message && <p className="mt-0.5 text-[11px] text-zinc-500">{r.message}</p>}
            </div>
            <span className={`ml-auto shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${r.status === 'PASSED' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
              {r.status}
            </span>
          </li>
        ))}
      </ul>
    </StageShell>
  )
}
