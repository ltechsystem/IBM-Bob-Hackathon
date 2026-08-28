import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StepTracker from '../components/pipelines/stepTracker'
import type { Step } from '../components/pipelines/stepTracker'
import type { AgentStatus } from '../components/pipelines/shared'

const steps: Step[] = [
  { id: 'step-a', label: 'Step Alpha' },
  { id: 'step-b', label: 'Step Beta' },
  { id: 'step-c', label: 'Step Gamma' },
]

const statuses: Record<string, AgentStatus> = {
  'step-a': 'done',
  'step-b': 'running',
  'step-c': 'pending',
}

describe('StepTracker', () => {
  it('renders all step labels', () => {
    render(<StepTracker steps={steps} statuses={statuses} />)
    expect(screen.getByText('Step Alpha')).toBeTruthy()
    expect(screen.getByText('Step Beta')).toBeTruthy()
    expect(screen.getByText('Step Gamma')).toBeTruthy()
  })

  it('renders status text for each step', () => {
    render(<StepTracker steps={steps} statuses={statuses} />)
    expect(screen.getByText('done')).toBeTruthy()
    expect(screen.getByText('running')).toBeTruthy()
    expect(screen.getByText('pending')).toBeTruthy()
  })

  it('defaults to pending for unknown step id', () => {
    const minimal: Step[] = [{ id: 'unknown-id', label: 'Orphan' }]
    render(<StepTracker steps={minimal} statuses={{}} />)
    expect(screen.getByText('pending')).toBeTruthy()
  })
})
