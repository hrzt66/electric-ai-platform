import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('login view content', () => {
  it('uses the new login copy for the quality evaluation AI platform narrative', () => {
    const content = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')

    expect(content).toContain('多维度质量评价 AI 平台')
    expect(content).toContain('Go 微服务编排')
    expect(content).toContain('Python 模型推理与评分')
    expect(content).toContain('进入评价控制台')
  })

  it('removes the old industrial control center narrative from the login copy', () => {
    const content = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')

    expect(content).not.toContain('工业控制中心')
    expect(content).not.toContain('统一运行时')
    expect(content).not.toContain('G:\\Runtime')
    expect(content).not.toContain('本机原生优先')
    expect(content).not.toContain('system-board')
  })

  it('adds login safety and productized form details', () => {
    const content = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')

    expect(content).toContain('if (submitting.value) {')
    expect(content).toContain('autocomplete="username"')
    expect(content).toContain('autocomplete="current-password"')
    expect(content).toContain('overflow-x: hidden')
    expect(content).toContain('overflow-y: auto')
    expect(content).not.toContain('登录成功后将按 redirectPath 或默认总览页跳转')
  })
})
