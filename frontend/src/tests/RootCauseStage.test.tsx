import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RootCauseStage from '../components/pipelines/RootCauseStage'
import type { RootCause } from '../mockdata/incident'

const rootCause: RootCause = {
  file: 'app/main.py',
  line: 13,
  summary: 'Missing None-check before accessing user.name',
  confidence: 'HIGH',
  explanation: 'get_user() returns None when the user does not exist.',
}

describe('RootCauseStage', () => {
  it('renders stage title', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText('Root Cause Analysis')).toBeTruthy()
  })

  it('renders the summary', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText('Missing None-check before accessing user.name')).toBeTruthy()
  })

  it('renders the confidence badge', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText('HIGH')).toBeTruthy()
  })

  it('renders the file name', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText('app/main.py')).toBeTruthy()
  })

  it('renders the line number', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText('13')).toBeTruthy()
  })

  it('renders the explanation text', () => {
    render(<RootCauseStage rootCause={rootCause} />)
    expect(screen.getByText(/get_user\(\) returns None/)).toBeTruthy()
  })
})
