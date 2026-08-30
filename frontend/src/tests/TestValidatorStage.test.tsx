import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TestValidatorStage from '../components/pipelines/TestValidatorStage'
import type { TestResult } from '../api/types'

const allPassed: TestResult[] = [
  { name: 'test_get_existing_user',    status: 'PASSED' },
  { name: 'test_get_missing_user_404', status: 'PASSED', message: 'New regression test' },
  { name: 'test_create_user',          status: 'PASSED' },
]

const withFailure: TestResult[] = [
  { name: 'test_get_existing_user',    status: 'PASSED' },
  { name: 'test_get_missing_user_404', status: 'FAILED', message: 'Expected 404 got 500' },
]

describe('TestValidatorStage', () => {
  it('renders stage title', () => {
    render(<TestValidatorStage results={allPassed} />)
    expect(screen.getByText('Test Results')).toBeTruthy()
  })

  it('renders all test names', () => {
    render(<TestValidatorStage results={allPassed} />)
    expect(screen.getByText('test_get_existing_user')).toBeTruthy()
    expect(screen.getByText('test_get_missing_user_404')).toBeTruthy()
    expect(screen.getByText('test_create_user')).toBeTruthy()
  })

  it('shows passed count in summary', () => {
    render(<TestValidatorStage results={allPassed} />)
    expect(screen.getByText('3 passed')).toBeTruthy()
  })

  it('shows optional test message', () => {
    render(<TestValidatorStage results={allPassed} />)
    expect(screen.getByText('New regression test')).toBeTruthy()
  })

  it('shows failed count when failures exist', () => {
    render(<TestValidatorStage results={withFailure} />)
    expect(screen.getByText('1 failed')).toBeTruthy()
  })

  it('does not show failed count when all pass', () => {
    render(<TestValidatorStage results={allPassed} />)
    expect(screen.queryByText(/failed/)).toBeNull()
  })

  it('renders PASSED and FAILED status badges', () => {
    render(<TestValidatorStage results={withFailure} />)
    expect(screen.getByText('PASSED')).toBeTruthy()
    expect(screen.getByText('FAILED')).toBeTruthy()
  })
})
