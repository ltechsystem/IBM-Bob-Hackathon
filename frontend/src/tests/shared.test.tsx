import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StageShell, ConfidenceBadge, StatusBadge, Connector } from '../components/pipelines/shared'

describe('StageShell', () => {
  it('renders stage number, label, title', () => {
    render(
      <StageShell stageNumber={3} label="my-skill" title="My Stage">
        <p>child content</p>
      </StageShell>
    )
    expect(screen.getByText(/stage 3/i)).toBeTruthy()
    expect(screen.getByText(/my-skill/)).toBeTruthy()
    expect(screen.getByText('My Stage')).toBeTruthy()
  })

  it('renders optional description', () => {
    render(
      <StageShell stageNumber={1} label="lbl" title="T" description="My description">
        <span />
      </StageShell>
    )
    expect(screen.getByText('My description')).toBeTruthy()
  })

  it('renders children', () => {
    render(
      <StageShell stageNumber={1} label="lbl" title="T">
        <span data-testid="child">hello</span>
      </StageShell>
    )
    expect(screen.getByTestId('child')).toBeTruthy()
  })
})

describe('ConfidenceBadge', () => {
  it('renders HIGH', () => {
    render(<ConfidenceBadge level="HIGH" />)
    expect(screen.getByText('HIGH')).toBeTruthy()
  })

  it('renders MEDIUM', () => {
    render(<ConfidenceBadge level="MEDIUM" />)
    expect(screen.getByText('MEDIUM')).toBeTruthy()
  })

  it('renders LOW', () => {
    render(<ConfidenceBadge level="LOW" />)
    expect(screen.getByText('LOW')).toBeTruthy()
  })
})

describe('StatusBadge', () => {
  it('renders done', () => {
    render(<StatusBadge status="done" />)
    expect(screen.getByText('done')).toBeTruthy()
  })

  it('renders running', () => {
    render(<StatusBadge status="running" />)
    expect(screen.getByText('running')).toBeTruthy()
  })

  it('renders pending', () => {
    render(<StatusBadge status="pending" />)
    expect(screen.getByText('pending')).toBeTruthy()
  })
})

describe('Connector', () => {
  it('renders without crashing', () => {
    const { container } = render(<Connector />)
    expect(container.firstChild).toBeTruthy()
  })
})
