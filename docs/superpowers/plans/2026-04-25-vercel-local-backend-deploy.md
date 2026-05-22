# Vercel Frontend And Local Backend Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `web-console` deploy cleanly on `Vercel`, point it at `https://api.camartshub.xyz`, and document the domain and local-gateway setup needed for full public access.

**Architecture:** Keep the existing Vite dev proxy for local development, but introduce explicit runtime URL helpers so production builds no longer depend on relative `/api` and `/files` paths. Deploy only the frontend to `Vercel`, keep the local machine as the backend gateway host, and add a concise deployment runbook for GitHub, Vercel, DNS, and local gateway exposure.

**Tech Stack:** Vue 3, Vite 5, Vitest, Axios, Vercel, DNS, local gateway-service

---

### Task 1: Lock In Production URL Behavior With Failing Frontend Tests

**Files:**
- Create: `web-console/src/api/runtime-config.spec.ts`
- Modify: `web-console/src/api/platform.spec.ts`
- Modify: `web-console/src/vite-host.spec.ts`
- Test: `web-console/src/api/runtime-config.spec.ts`
- Test: `web-console/src/api/platform.spec.ts`
- Test: `web-console/src/vite-host.spec.ts`

- [ ] **Step 1: Write the failing runtime config tests**

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.resetModules()
  vi.unstubAllEnvs()
})

describe('runtime config', () => {
  it('falls back to the relative gateway paths when no env is configured', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    vi.stubEnv('VITE_FILE_BASE_URL', '')

    const { getApiBaseUrl, getFileBaseUrl } = await import('./runtime-config')

    expect(getApiBaseUrl()).toBe('/api/v1')
    expect(getFileBaseUrl()).toBe('')
  })

  it('uses the configured production gateway origin', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.camartshub.xyz/api/v1')
    vi.stubEnv('VITE_FILE_BASE_URL', 'https://api.camartshub.xyz')

    const { getApiBaseUrl, getFileBaseUrl } = await import('./runtime-config')

    expect(getApiBaseUrl()).toBe('https://api.camartshub.xyz/api/v1')
    expect(getFileBaseUrl()).toBe('https://api.camartshub.xyz')
  })
})
```

- [ ] **Step 2: Run the new test to prove it fails before implementation**

Run: `cd web-console && npx vitest run src/api/runtime-config.spec.ts`
Expected: FAIL because `./runtime-config` does not exist yet and Vitest reports a module resolution error.

- [ ] **Step 3: Extend image URL tests to lock production file host behavior**

```ts
import { describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('./http', () => api)
vi.mock('./runtime-config', () => ({
  getFileBaseUrl: vi.fn(() => 'https://api.camartshub.xyz'),
}))

import { buildImageUrl, listAssetHistoryPage } from './platform'

describe('buildImageUrl', () => {
  it('routes checked images to the dedicated image-check static path', () => {
    expect(buildImageUrl('model/image_check/19_0_1639449177.png')).toBe(
      'https://api.camartshub.xyz/files/image-checks/19_0_1639449177.png',
    )
  })

  it('keeps generated images on the default image path', () => {
    expect(buildImageUrl('model/image/19_0_1639449177.png')).toBe(
      'https://api.camartshub.xyz/files/images/19_0_1639449177.png',
    )
  })
})
```

- [ ] **Step 4: Run the platform API tests to prove the image URL expectation now fails**

Run: `cd web-console && npx vitest run src/api/platform.spec.ts`
Expected: FAIL because `buildImageUrl()` still returns relative `/files/...` paths.

- [ ] **Step 5: Expand the Vite config test to pin both `/api` and `/files` proxies**

```ts
import { describe, expect, it } from 'vitest'

import config from '../vite.config'

describe('vite config', () => {
  it('binds the dev server to ipv4 localhost', () => {
    expect(config.server?.host).toBe('127.0.0.1')
  })

  it('keeps both gateway proxy prefixes for local development', () => {
    expect(config.server?.proxy?.['/api']).toMatchObject({
      target: 'http://127.0.0.1:8080',
      changeOrigin: true,
    })
    expect(config.server?.proxy?.['/files']).toMatchObject({
      target: 'http://127.0.0.1:8080',
      changeOrigin: true,
    })
  })
})
```

- [ ] **Step 6: Run the Vite config test to confirm the updated expectations are green before implementation**

Run: `cd web-console && npx vitest run src/vite-host.spec.ts`
Expected: PASS because the current `vite.config.ts` already exposes both proxies.

- [ ] **Step 7: Commit the test-only changes**

```bash
git add web-console/src/api/runtime-config.spec.ts web-console/src/api/platform.spec.ts web-console/src/vite-host.spec.ts
git commit -m "test: lock vercel gateway runtime config"
```

### Task 2: Implement Runtime URL Helpers And Wire Production API/File Hosts

**Files:**
- Create: `web-console/src/api/runtime-config.ts`
- Modify: `web-console/src/api/http.ts`
- Modify: `web-console/src/api/platform.ts`
- Modify: `web-console/src/api/runtime-config.spec.ts`
- Modify: `web-console/src/api/platform.spec.ts`
- Test: `web-console/src/api/runtime-config.spec.ts`
- Test: `web-console/src/api/platform.spec.ts`

- [ ] **Step 1: Add the shared runtime config helper**

```ts
function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, '')
}

function readEnv(name: 'VITE_API_BASE_URL' | 'VITE_FILE_BASE_URL') {
  const value = import.meta.env[name]
  return typeof value === 'string' ? value.trim() : ''
}

export function getApiBaseUrl() {
  const configured = trimTrailingSlash(readEnv('VITE_API_BASE_URL'))
  return configured || '/api/v1'
}

export function getFileBaseUrl() {
  const configured = trimTrailingSlash(readEnv('VITE_FILE_BASE_URL'))
  if (configured) {
    return configured
  }
  if (getApiBaseUrl().startsWith('http')) {
    return getApiBaseUrl().replace(/\/api\/v1$/, '')
  }
  return ''
}
```

- [ ] **Step 2: Make Axios read the shared API base URL**

```ts
import axios from 'axios'

import { getApiBaseUrl } from './runtime-config'
import { useAuthStore } from '../stores/auth'

export const http = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000,
})
```

- [ ] **Step 3: Make image URLs use the configured gateway host**

```ts
import { getFileBaseUrl } from './runtime-config'
import { http } from './http'

export function buildImageUrl(filePath: string) {
  const imageName = filePath.split(/[\\/]/).pop()
  if (!imageName) {
    return ''
  }
  const isCheckedImage = /(^|[\\/])image_check([\\/]|$)/.test(filePath)
  const prefix = isCheckedImage ? '/files/image-checks/' : '/files/images/'
  const baseUrl = getFileBaseUrl()
  const url = `${prefix}${encodeURIComponent(imageName)}`
  return baseUrl ? `${baseUrl}${url}` : url
}
```

- [ ] **Step 4: Run the focused frontend tests**

Run: `cd web-console && npx vitest run src/api/runtime-config.spec.ts src/api/platform.spec.ts src/vite-host.spec.ts`
Expected: PASS with runtime config tests resolving both local and production URL strategies.

- [ ] **Step 5: Run the full frontend test suite**

Run: `npm --prefix web-console run test`
Expected: PASS with all existing `web-console` Vitest suites green.

- [ ] **Step 6: Run a production build to verify Vercel-compatible output**

Run: `npm --prefix web-console run build`
Expected: PASS and emit `web-console/dist` without unresolved `import.meta.env` issues.

- [ ] **Step 7: Commit the runtime wiring**

```bash
git add web-console/src/api/runtime-config.ts web-console/src/api/http.ts web-console/src/api/platform.ts web-console/src/api/runtime-config.spec.ts web-console/src/api/platform.spec.ts
git commit -m "feat: support vercel api and file hosts"
```

### Task 3: Add Vercel And Domain Deployment Metadata

**Files:**
- Create: `web-console/.env.production.example`
- Create: `web-console/vercel.json`
- Modify: `README.md`
- Test: `web-console/vercel.json`

- [ ] **Step 1: Add a production env example for Vercel**

```dotenv
VITE_API_BASE_URL=https://api.camartshub.xyz/api/v1
VITE_FILE_BASE_URL=https://api.camartshub.xyz
```

- [ ] **Step 2: Add explicit Vercel SPA routing config inside the frontend root**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "cleanUrls": true,
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

- [ ] **Step 3: Document the GitHub, Vercel, and domain setup in the repository README**

```md
## Vercel Frontend Deployment

前端正式环境部署在 `Vercel`，建议直接连接 GitHub 仓库 `hrzt66/electric-ai-platform` 并将 Root Directory 指向 `web-console`。

### Vercel 项目设置

- Framework Preset：`Vite`
- Root Directory：`web-console`
- Build Command：`npm run build`
- Output Directory：`dist`

### 生产环境变量

- `VITE_API_BASE_URL=https://api.camartshub.xyz/api/v1`
- `VITE_FILE_BASE_URL=https://api.camartshub.xyz`

### 域名绑定

- `www.camartshub.xyz` 绑定到 `Vercel` 前端项目
- `camartshub.xyz` 在 `Vercel` 中配置跳转到 `https://www.camartshub.xyz`
- `api.camartshub.xyz` 指向本地电脑暴露出去的网关入口

### 本地网关要求

- 仅对公网暴露 `gateway-service`
- `https://api.camartshub.xyz/health` 可访问
- `https://api.camartshub.xyz/api/v1/auth/login` 可从公网到达
- `https://api.camartshub.xyz/files/...` 可访问生成图片
```

- [ ] **Step 4: Build again to verify `vercel.json` and env example do not break the app**

Run: `npm --prefix web-console run build`
Expected: PASS with `dist/index.html` and static assets still generated.

- [ ] **Step 5: Commit the deployment metadata**

```bash
git add web-console/.env.production.example web-console/vercel.json README.md
git commit -m "docs: add vercel frontend deployment setup"
```

### Task 4: Execute Public Deployment And Verify End-To-End Reachability

**Files:**
- Read: `web-console/.env.production.example`
- Read: `web-console/vercel.json`
- Read: `README.md`
- Read: `services/gateway-service/router/router.go`
- Read: `services/gateway-service/cmd/server/main.go`

- [ ] **Step 1: Push the branch containing the frontend deployment changes**

Run: `git push origin main`
Expected: GitHub receives the latest frontend runtime-config and Vercel setup commits on `main`, which Vercel can watch directly.

- [ ] **Step 2: Create the Vercel project from the GitHub repository**

In Vercel:
- Import repository `hrzt66/electric-ai-platform`
- Set Root Directory to `web-console`
- Confirm Build Command is `npm run build`
- Confirm Output Directory is `dist`

Expected: the initial preview deployment finishes with status `Ready`.

- [ ] **Step 3: Configure Vercel production environment variables**

Set:
- `VITE_API_BASE_URL=https://api.camartshub.xyz/api/v1`
- `VITE_FILE_BASE_URL=https://api.camartshub.xyz`

Expected: a redeploy picks up both variables and finishes successfully.

- [ ] **Step 4: Bind the production frontend domains**

In Vercel:
- add `www.camartshub.xyz` as the primary production domain
- add `camartshub.xyz` and configure redirect to `https://www.camartshub.xyz`

Expected: `https://www.camartshub.xyz` serves the app and the apex domain redirects.

- [ ] **Step 5: Point the API subdomain at the local gateway exposure layer**

DNS / tunnel / proxy target:
- `api.camartshub.xyz` must terminate TLS and forward traffic to the local machine's `gateway-service`
- only the gateway should be exposed publicly

Expected: `curl -I https://api.camartshub.xyz/health` returns `HTTP/2 200` or `HTTP/1.1 200 OK`.

- [ ] **Step 6: Verify gateway API reachability before opening the frontend**

Run:

```bash
curl -sS https://api.camartshub.xyz/health
curl -i https://api.camartshub.xyz/api/v1/auth/login
```

Expected:
- `/health` returns a JSON payload containing `status`
- `/api/v1/auth/login` returns a non-200 method or auth-related response from the real gateway rather than DNS or TLS failure

- [ ] **Step 7: Verify the deployed frontend can authenticate and load data**

Manual checks:
- open `https://www.camartshub.xyz/login`
- log in with a real account
- confirm dashboard and model center requests succeed
- submit one generation task
- confirm task polling, history records, and image preview URLs load from `https://api.camartshub.xyz/files/...`

Expected: the deployed site completes one end-to-end generation flow against the local backend.

- [ ] **Step 8: Capture the rollout status in the repo**

Append a short dated note to `README.md` or a deployment log with:
- deployed frontend URL
- active API domain
- whether local backend exposure uses tunnel or direct proxy
- result of the end-to-end smoke test

- [ ] **Step 9: Commit the rollout note**

```bash
git add README.md
git commit -m "docs: record vercel rollout status"
```
