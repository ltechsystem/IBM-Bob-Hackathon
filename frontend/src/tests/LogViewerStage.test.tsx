import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LogViewerStage from '../components/pipelines/LogViewerStage'
import type { LogLine } from '../components/pipelines/LogViewerStage'

const lines: LogLine[] = [
  { time: '21:13:55', level: 'INFO',  message: 'GET /users/1 200 OK' },
  { time: '21:14:02', level: 'ERROR', message: "AttributeError: 'NoneType'" },
  { time: '21:14:05', level: 'WARN',  message: 'Slow query' },
]

describe('LogViewerStage', () => {
  it('renders the stage title', () => {
    render(<LogViewerStage logPath="app/logs/app.log" lines={lines} />)
    expect(screen.getByText('log viewer')).toBeTruthy()
  })

  it('shows the log path in the description', () => {
    render(<LogViewerStage logPath="app/logs/app.log" lines={lines} />)
    expect(screen.getByText(/app\/logs\/app\.log/)).toBeTruthy()
  })

  it('renders all log lines', () => {
    render(<LogViewerStage logPath="app/logs/app.log" lines={lines} />)
    expect(screen.getByText('GET /users/1 200 OK')).toBeTruthy()
    expect(screen.getByText(/AttributeError/)).toBeTruthy()
    expect(screen.getByText('Slow query')).toBeTruthy()
  })

  it('shows error banner when errors exist', () => {
    render(<LogViewerStage logPath="app/logs/app.log" lines={lines} />)
    expect(screen.getByText(/1 error found in log/)).toBeTruthy()
  })

  it('does not show error banner when no errors', () => {
    const clean: LogLine[] = [{ time: '21:00:00', level: 'INFO', message: 'OK' }]
    render(<LogViewerStage logPath="app/logs/app.log" lines={clean} />)
    expect(screen.queryByText(/error found in log/)).toBeNull()
  })

  it('shows plural errors message for multiple errors', () => {
    const multiError: LogLine[] = [
      { time: '21:00:01', level: 'ERROR', message: 'First error' },
      { time: '21:00:02', level: 'ERROR', message: 'Second error' },
    ]
    render(<LogViewerStage logPath="app/logs/app.log" lines={multiError} />)
    expect(screen.getByText(/2 errors found in log/)).toBeTruthy()
  })
})
