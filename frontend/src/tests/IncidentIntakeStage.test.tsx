import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import IncidentIntakeStage from '../components/pipelines/IncidentIntakeStage'
import type { IncidentBrief } from '../api/types'

const brief: IncidentBrief = {
  id: 'INC-2024-001',
  title: "GET /users/{user_id} crashes",
  severity: 'P1',
  service: 'user-service',
  errorType: 'AttributeError',
  errorMessage: "'NoneType' object has no attribute 'name'",
  affectedEndpoint: 'GET /users/{user_id}',
  reportedAt: '2024-01-15 21:14:02 UTC',
}

describe('IncidentIntakeStage', () => {
  it('renders stage title', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText('Incident Brief')).toBeTruthy()
  })

  it('displays incident ID', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText('INC-2024-001')).toBeTruthy()
  })

  it('displays service name', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText('user-service')).toBeTruthy()
  })

  it('displays severity badge', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText('P1')).toBeTruthy()
  })

  it('displays error message', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText(brief.errorMessage)).toBeTruthy()
  })

  it('displays affected endpoint', () => {
    render(<IncidentIntakeStage brief={brief} />)
    expect(screen.getByText('GET /users/{user_id}')).toBeTruthy()
  })
})
