import { readFileSync } from 'node:fs'

import { describe, expect, it } from 'vitest'

describe('scripts/mac/start-platform.sh', () => {
  const script = readFileSync(new URL('./start-platform.sh', import.meta.url), 'utf8')

  it('starts the monitor service and wires the gateway monitor upstream', () => {
    expect(script).toContain('services/monitor-service/cmd/server')
    expect(script).toContain('MONITOR_SERVICE_URL')
    expect(script).toContain('http://127.0.0.1:8086')
  })

  it('starts the python api, worker, and web console', () => {
    expect(script).toContain('uvicorn app.main:app')
    expect(script).toContain('python3 -m app.worker')
    expect(script).toContain('npm run dev -- --host 127.0.0.1 --port 5173')
  })
})
