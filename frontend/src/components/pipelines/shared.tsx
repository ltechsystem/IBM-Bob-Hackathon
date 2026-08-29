// src/components/pipeline/shared.tsx
import type { ReactNode } from 'react'

export interface StageShellProps {
    stageNumber: number
    label: string
    title: string
    description?: string
    children: ReactNode
}

export function StageShell({ stageNumber, label, title, description, children }: StageShellProps) {
    return (
        <section className="flex flex-col gap-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-5">
            <div>
                <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600">
                    stage {stageNumber} · {label}
                </p>
                <h2 className="mt-1 font-mono text-lg font-bold text-zinc-100">{title}</h2>
                {description && <p className="mt-1 text-sm text-zinc-500">{description}</p>}
            </div>
            {children}
        </section>
    )
}

export function Connector() {
    return (
        <div className="flex justify-center py-1">
            <div className="h-6 w-px bg-zinc-800" />
        </div>
    )
}

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW'

const CONFIDENCE_STYLE: Record<ConfidenceLevel, string> = {
    HIGH: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    MEDIUM: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    LOW: 'bg-red-500/15 text-red-400 border-red-500/30',
}

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
    const style = CONFIDENCE_STYLE[level] ?? CONFIDENCE_STYLE.MEDIUM
    return (
        <span className={`inline-flex items-center rounded-full border px-2.5 py-1 font-mono text-xs font-bold ${style}`}>
            {level}
        </span>
    )
}

export type AgentStatus = 'done' | 'running' | 'pending'

const STATUS_STYLE: Record<AgentStatus, string> = {
    done: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    running: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
    pending: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30',
}

export function StatusBadge({ status }: { status: AgentStatus }) {
    const style = STATUS_STYLE[status] ?? STATUS_STYLE.pending
    return (
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${style}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${status === 'done' ? 'bg-emerald-400' : status === 'running' ? 'bg-sky-400 animate-pulse' : 'bg-zinc-500'}`} />
            {status}
        </span>
    )
}