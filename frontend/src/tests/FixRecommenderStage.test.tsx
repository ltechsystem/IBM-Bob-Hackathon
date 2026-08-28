import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FixRecommenderStage from '../components/pipelines/FixRecommenderStage'
import type { DiffHunk } from '../mockdata/incident'

const hunk: DiffHunk = {
  file: 'app/main.py',
  lineNumber: 11,
  before: ['    user = get_user(db, user_id)', '    return {"id": user.id, "name": user.name}'],
  after: [
    '    user = get_user(db, user_id)',
    '    if user is None:',
    '        raise HTTPException(status_code=404, detail="User not found")',
    '    return {"id": user.id, "name": user.name}',
  ],
}

describe('FixRecommenderStage', () => {
  it('renders stage title', () => {
    render(<FixRecommenderStage hunk={hunk} />)
    expect(screen.getByText('Proposed Fix')).toBeTruthy()
  })

  it('renders file name in description', () => {
    render(<FixRecommenderStage hunk={hunk} />)
    expect(screen.getAllByText(/app\/main\.py/).length).toBeGreaterThan(0)
  })

  it('renders Before section header', () => {
    render(<FixRecommenderStage hunk={hunk} />)
    expect(screen.getByText(/Before/)).toBeTruthy()
  })

  it('renders After section header', () => {
    render(<FixRecommenderStage hunk={hunk} />)
    expect(screen.getByText(/After/)).toBeTruthy()
  })

  it('renders the None-check fix line', () => {
    render(<FixRecommenderStage hunk={hunk} />)
    expect(screen.getByText(/if user is None/)).toBeTruthy()
  })
})
