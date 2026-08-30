import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EvidenceCollectorStage from '../components/pipelines/EvidenceCollectorStage'
import type { EvidenceFile } from '../api/types'

const files: EvidenceFile[] = [
  { path: 'app/main.py',   relevance: 'HIGH',   reason: 'Route handler' },
  { path: 'app/models.py', relevance: 'MEDIUM', reason: 'User model' },
  { path: 'readme.txt',    relevance: 'LOW',    reason: 'Not relevant' },
]

describe('EvidenceCollectorStage', () => {
  it('renders stage title', () => {
    render(<EvidenceCollectorStage files={files} />)
    expect(screen.getByText('Evidence Manifest')).toBeTruthy()
  })

  it('renders all file paths', () => {
    render(<EvidenceCollectorStage files={files} />)
    expect(screen.getByText('app/main.py')).toBeTruthy()
    expect(screen.getByText('app/models.py')).toBeTruthy()
    expect(screen.getByText('readme.txt')).toBeTruthy()
  })

  it('renders relevance badges', () => {
    render(<EvidenceCollectorStage files={files} />)
    expect(screen.getByText('HIGH')).toBeTruthy()
    expect(screen.getByText('MEDIUM')).toBeTruthy()
    expect(screen.getByText('LOW')).toBeTruthy()
  })

  it('renders reasons', () => {
    render(<EvidenceCollectorStage files={files} />)
    expect(screen.getByText('Route handler')).toBeTruthy()
  })
})
