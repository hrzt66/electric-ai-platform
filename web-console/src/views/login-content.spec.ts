import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('login view content', () => {
  it('keeps the industrial control center copy', () => {
    const content = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')

    expect(content).toContain('工业电力图像生成与评分平台')
    expect(content).toContain('工业控制中心')
    expect(content).toContain('统一运行时')
    expect(content).toContain('进入工作台')
  })
})
