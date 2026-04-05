import { describe, expect, it } from 'vitest'

import config from '../vite.config'

describe('vite config', () => {
  it('binds the dev server to ipv4 localhost', () => {
    expect(config.server?.host).toBe('127.0.0.1')
  })
})
