import type { LogLine } from '../components/pipelines/LogViewerStage'

export const logLines: LogLine[] = [
  { time: '21:13:55', level: 'INFO',  message: 'GET /users/1 200 OK' },
  { time: '21:13:57', level: 'INFO',  message: 'GET /users/2 200 OK' },
  { time: '21:14:02', level: 'ERROR', message: "AttributeError: 'NoneType' object has no attribute 'name' — app/main.py:13" },
  { time: '21:14:02', level: 'ERROR', message: 'Unhandled exception in get_user() — request: GET /users/999' },
  { time: '21:14:05', level: 'INFO',  message: 'POST /users 201 Created' },
  { time: '21:14:10', level: 'WARN',  message: 'Slow query detected: SELECT * FROM users (320ms)' },
]
