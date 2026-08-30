import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EvidenceCorrelatorStage from '../components/pipelines/EvidenceCorrelatorStage'
import type { SubagentFinding } from '../api/types'

const findings: SubagentFinding[] = [
  { agent: 'Subagent A', focus: 'Logs',  finding: 'AttributeError on line 13', confidence: 'HIGH' },
  { agent: 'Subagent B', focus: 'Code',  finding: 'No None-check at line 13',  confidence: 'HIGH' },
  { agent: 'Subagent C', focus: 'Model', finding: 'get_user returns Optional',  confidence: 'MEDIUM' },
]

describe('EvidenceCorrelatorStage', () => {
  it('renders stage title', () => {
    render(<EvidenceCorrelatorStage findings={findings} />)
    expect(screen.getByText('Subagent Findings')).toBeTruthy()
  })

  it('renders all agent names', () => {
    render(<EvidenceCorrelatorStage findings={findings} />)
    expect(screen.getByText('Subagent A')).toBeTruthy()
    expect(screen.getByText('Subagent B')).toBeTruthy()
    expect(screen.getByText('Subagent C')).toBeTruthy()
  })

  it('renders findings text', () => {
    render(<EvidenceCorrelatorStage findings={findings} />)
    expect(screen.getByText('AttributeError on line 13')).toBeTruthy()
  })

  it('renders confidence badges', () => {
    render(<EvidenceCorrelatorStage findings={findings} />)
    const highBadges = screen.getAllByText('HIGH')
    expect(highBadges.length).toBeGreaterThanOrEqual(2)
  })

  it('renders done status badges', () => {
    render(<EvidenceCorrelatorStage findings={findings} />)
    const doneBadges = screen.getAllByText('done')
    expect(doneBadges.length).toBe(findings.length)
  })
})
