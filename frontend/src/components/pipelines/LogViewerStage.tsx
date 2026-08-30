// src/components/pipeline/LogViewerStage.tsx
import { StageShell } from './shared'
import type { LogLine } from '../../api/types'

export type { LogLine }

export interface LogViewerStageProps {
    logPath: string
    lines: LogLine[]
}

export default function LogViewerStage({ logPath, lines }: LogViewerStageProps) {
    const errorCount = lines.filter((l) => l.level === 'ERROR').length

    return (
        <StageShell
            stageNumber={1}
            label="subagent a · log analyzer"
            title="log viewer"
            description={`Tail of ${logPath}`}
        >
            {errorCount > 0 && (
                <div className="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2">
                    <span className="h-2 w-2 rounded-full bg-red-400" />
                    <p className="font-mono text-xs text-red-400">
                        {errorCount} error{errorCount > 1 ? 's' : ''} found in log
                    </p>
                </div>
            )}

            <pre className="overflow-auto rounded-md border border-zinc-800 bg-black/40 p-3 font-mono text-xs leading-relaxed">
                {lines.map((line, i) => {
                    const color: string =
                        line.level === 'ERROR'
                            ? 'text-red-400 bg-red-500/10'
                            : line.level === 'WARN'
                                ? 'text-amber-400'
                                : 'text-zinc-500'
                    return (
                        <div key={i} className={`px-1 ${color}`}>
                            <span className="text-zinc-700">{line.time}</span>{' '}
                            <span className="font-semibold">[{line.level}]</span> {line.message}
                        </div>
                    )
                })}
            </pre>
        </StageShell>
    )
}
