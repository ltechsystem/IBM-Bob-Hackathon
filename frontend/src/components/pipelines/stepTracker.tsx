// src/components/pipeline/StepTracker.tsx
import type { AgentStatus } from './shared'

export interface Step {
    id: string
    label: string
}

export interface StepTrackerProps {
    steps: Step[]
    statuses: Record<string, AgentStatus>
}

const DOT_STYLE: Record<AgentStatus, string> = {
    done: 'bg-emerald-400',
    running: 'bg-sky-400 animate-pulse',
    pending: 'bg-zinc-600',
}

const TEXT_STYLE: Record<AgentStatus, string> = {
    done: 'text-zinc-300',
    running: 'text-sky-400',
    pending: 'text-zinc-600',
}

export default function StepTracker({ steps, statuses }: StepTrackerProps) {
    return (
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
            <ol className="flex flex-col gap-0">
                {steps.map((step, i) => {
                    const status = statuses[step.id] ?? 'pending'
                    const isLast = i === steps.length - 1
                    return (
                        <li key={step.id} className="flex gap-3">
                            <div className="flex flex-col items-center">
                                <span className={`h-2.5 w-2.5 rounded-full ${DOT_STYLE[status]}`} />
                                {!isLast && (
                                    <span className={`w-px flex-1 ${status === 'done' ? 'bg-emerald-500/40' : 'bg-zinc-800'}`} style={{ minHeight: '20px' }} />
                                )}
                            </div>
                            <div className="pb-5">
                                <p className={`font-mono text-xs font-semibold uppercase tracking-wide ${TEXT_STYLE[status]}`}>
                                    {step.label}
                                </p>
                                <p className="font-mono text-[10px] text-zinc-600">{status}</p>
                            </div>
                        </li>
                    )
                })}
            </ol>
        </div>
    )
}