# Formal Monitor Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current monitor experience into a formal NOC-style platform with 1-second continuous updates, structured operational information, and a stronger real-time frontend presentation.

**Architecture:** Keep `GET /monitor/overview` for first-paint hydration, convert `GET /monitor/stream` into a continuous SSE stream that emits one full `MonitorOverview` per second, teach the frontend store to maintain both the latest snapshot and a 60-point rolling history, and redesign `/monitor` into a formal NOC-style single page composed of focused monitor panels.

**Tech Stack:** Go 1.24, Gin, Vue 3, Pinia, Vitest, native SSE over `fetch`, scoped CSS

---

## File Structure

- Modify: `services/monitor-service/service/monitor_service.go`
- Modify: `services/monitor-service/service/stream_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Modify: `services/monitor-service/controller/monitor_controller.go`
- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/stores/platform.ts`
- Modify: `web-console/src/stores/platform.spec.ts`
- Modify: `web-console/src/views/MonitorCockpitView.vue`
- Modify: `web-console/src/views/MonitorCockpitView.spec.ts`

### Task 1: Convert Monitor SSE Into A Continuous 1-Second Stream

**Files:**
- Modify: `services/monitor-service/service/monitor_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Test: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write the failing Go test that expects multiple SSE snapshots**

```go
func TestDefaultMonitorService_Stream_EmitsContinuousSnapshots(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	fake := &fakeOverviewCollector{
		raw: RawSnapshot{Platform: RawPlatform{OS: "darwin"}},
		overview: model.MonitorOverview{
			OverallHealth: "healthy",
			HostSnapshot: &model.HostSnapshot{
				PlatformFamily:  "macos",
				CPUUsagePercent: 10,
			},
			ServiceSnapshots: []model.ServiceSnapshot{},
			TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
			ActiveAlerts: []model.MonitorAlert{},
			RecentAlerts: []model.MonitorAlert{},
		},
	}

	svc := NewDefaultMonitorServiceWithCollector(fake)
	reader, err := svc.Stream(ctx)
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}

	buf := make([]byte, 8192)
	n, err := reader.Read(buf)
	if err != nil && err != io.EOF {
		t.Fatalf("expected to read stream data, got %v", err)
	}

	body := string(buf[:n])
	if strings.Count(body, "event: snapshot") < 2 {
		t.Fatalf("expected at least 2 snapshot events, got %q", body)
	}
}
```

- [ ] **Step 2: Run the targeted Go test to verify RED**

Run: `cd services/monitor-service && go test ./service -run 'TestDefaultMonitorService_Stream_EmitsContinuousSnapshots'`

Expected: FAIL because `Stream` only emits one SSE snapshot today.

- [ ] **Step 3: Implement a ticker-driven streaming reader that emits one full overview per second**

```go
func (s *DefaultMonitorService) Stream(ctx context.Context) (io.Reader, error) {
	pr, pw := io.Pipe()

	go func() {
		ticker := time.NewTicker(time.Second)
		defer ticker.Stop()
		defer pw.Close()

		writeSnapshot := func() error {
			overview, err := s.buildOverview(ctx)
			if err != nil {
				return err
			}
			payload, err := json.Marshal(overview)
			if err != nil {
				return fmt.Errorf("marshal monitor overview for sse: %w", err)
			}
			_, err = io.WriteString(pw, FormatSSE("snapshot", payload))
			return err
		}

		if err := writeSnapshot(); err != nil {
			_ = pw.CloseWithError(err)
			return
		}

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if err := writeSnapshot(); err != nil {
					_ = pw.CloseWithError(err)
					return
				}
			}
		}
	}()

	return pr, nil
}
```

- [ ] **Step 4: Add a test-friendly shorter tick interval constructor instead of hardcoding `time.Second` everywhere**

```go
type DefaultMonitorService struct {
	collector      overviewCollector
	streamInterval time.Duration
}

func NewDefaultMonitorService() *DefaultMonitorService {
	return &DefaultMonitorService{
		collector:      &CollectorService{},
		streamInterval: time.Second,
	}
}
```

```go
func NewDefaultMonitorServiceWithCollectorAndInterval(collector overviewCollector, interval time.Duration) *DefaultMonitorService {
	if interval <= 0 {
		interval = time.Second
	}
	return &DefaultMonitorService{collector: collector, streamInterval: interval}
}
```

- [ ] **Step 5: Re-run the targeted Go tests to verify GREEN**

Run: `cd services/monitor-service && go test ./service -run 'TestDefaultMonitorService_Stream_EmitsContinuousSnapshots|TestDefaultMonitorService_Stream_EmitsFullOverviewSnapshot'`

Expected: PASS

### Task 2: Extend Frontend Monitor State With Rolling Realtime History

**Files:**
- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/stores/platform.ts`
- Modify: `web-console/src/stores/platform.spec.ts`
- Test: `web-console/src/stores/platform.spec.ts`

- [ ] **Step 1: Write the failing store test for rolling 60-point history**

```ts
it('keeps only the most recent 60 monitor history points', async () => {
  const store = usePlatformStore()

  for (let i = 0; i < 75; i += 1) {
    store.applyMonitorSnapshot({
      overall_health: 'healthy',
      host_snapshot: {
        platform_family: 'macos',
        cpu_usage_percent: i,
        memory_total_bytes: 100,
        memory_used_bytes: i,
      },
      service_snapshots: [],
      task_runtime_context: { active_task_count: 0 },
      active_alerts: [],
      recent_alerts: [],
    })
  }

  expect(store.monitorHistory.cpu.length).toBe(60)
  expect(store.monitorHistory.cpu[0].value).toBe(15)
  expect(store.monitorHistory.cpu.at(-1)?.value).toBe(74)
})
```

- [ ] **Step 2: Run the targeted test to verify RED**

Run: `cd web-console && npm test -- src/stores/platform.spec.ts`

Expected: FAIL because no rolling history structure or `applyMonitorSnapshot` helper exists.

- [ ] **Step 3: Add monitor history types and state**

```ts
export type MonitorHistoryPoint = {
  at: string
  value: number
}

export type MonitorHistory = {
  cpu: MonitorHistoryPoint[]
  memory: MonitorHistoryPoint[]
  ai_memory: MonitorHistoryPoint[]
}
```

```ts
monitorHistory: {
  cpu: [],
  memory: [],
  ai_memory: [],
},
```

- [ ] **Step 4: Add a reusable `applyMonitorSnapshot` action that updates the latest overview and appends history**

```ts
applyMonitorSnapshot(incoming: Partial<MonitorOverview> | MonitorOverview) {
  this.monitorOverview = mergeMonitorOverview(this.monitorOverview, incoming)
  const overview = this.monitorOverview
  if (!overview?.host_snapshot) {
    return
  }

  const capturedAt = overview.host_snapshot.captured_at || new Date().toISOString()
  appendHistoryPoint(this.monitorHistory.cpu, {
    at: capturedAt,
    value: overview.host_snapshot.cpu_usage_percent ?? 0,
  })

  if (
    typeof overview.host_snapshot.memory_total_bytes === 'number' &&
    overview.host_snapshot.memory_total_bytes > 0 &&
    typeof overview.host_snapshot.memory_used_bytes === 'number'
  ) {
    appendHistoryPoint(this.monitorHistory.memory, {
      at: capturedAt,
      value: Math.round((overview.host_snapshot.memory_used_bytes / overview.host_snapshot.memory_total_bytes) * 100),
    })
  }

  const aiBytes = overview.accelerator_snapshot?.ai_process_memory_bytes
  if (typeof aiBytes === 'number') {
    appendHistoryPoint(this.monitorHistory.ai_memory, {
      at: capturedAt,
      value: Math.round(aiBytes / 1024 / 1024),
    })
  }
}
```

- [ ] **Step 5: Update `fetchMonitorOverview` and `startMonitorStream` to call `applyMonitorSnapshot`**

```ts
this.applyMonitorSnapshot(await getMonitorOverview())
```

```ts
this.applyMonitorSnapshot(JSON.parse(message.data) as Partial<MonitorOverview>)
```

- [ ] **Step 6: Re-run the targeted test to verify GREEN**

Run: `cd web-console && npm test -- src/stores/platform.spec.ts`

Expected: PASS

### Task 3: Redesign `/monitor` Into A Formal NOC-Style Page

**Files:**
- Modify: `web-console/src/views/MonitorCockpitView.vue`
- Modify: `web-console/src/views/MonitorCockpitView.spec.ts`
- Test: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Write the failing SSR test for formal platform sections**

```ts
it('renders formal monitor platform sections with trends, service table, and alert panels', async () => {
  platformStore.monitorConnected = true
  platformStore.monitorOverview = {
    overall_health: 'warning',
    host_snapshot: {
      platform_family: 'macos',
      captured_at: '2026-05-03T06:37:29Z',
      cpu_usage_percent: 22,
      memory_total_bytes: 100,
      memory_used_bytes: 78,
      memory_pressure_level: 'warning',
      disk_total_bytes: 100,
      disk_used_bytes: 54,
    },
    accelerator_snapshot: {
      accelerator_type: 'apple-mps',
      available: true,
      mps_available: true,
      preferred_device_type: 'mps',
      unified_memory_pressure: 'warning',
      ai_process_memory_bytes: 629145600,
    },
    service_snapshots: [
      { service_name: 'gateway-service', display_name: 'Gateway Service', status: 'running', sample_ok: true },
    ],
    task_runtime_context: { active_task_count: 1, latest_task_stage: 'scoring' },
    active_alerts: [{ alert_id: 'm1', level: 'warning', title: '内存压力偏高', message: 'memory pressure is warning' }],
    recent_alerts: [],
  }

  const html = await renderView()

  expect(html).toContain('平台运行监控中心')
  expect(html).toContain('GLOBAL HEALTH')
  expect(html).toContain('CPU Trend')
  expect(html).toContain('Service Matrix')
  expect(html).toContain('AI Runtime')
  expect(html).toContain('Active Alerts')
})
```

- [ ] **Step 2: Run the targeted cockpit test to verify RED**

Run: `cd web-console && npm test -- src/views/MonitorCockpitView.spec.ts`

Expected: FAIL because the current view does not render formal monitor platform sections.

- [ ] **Step 3: Rework the view into a NOC-style layout**

Implement these sections in `MonitorCockpitView.vue`:

- top status hero with health, connection, platform, timestamp
- summary strip with 4 KPI cards
- trend panel driven by `platformStore.monitorHistory`
- resource cards for CPU, memory, disk, and accelerator
- service matrix table
- alert panel and signal explanation panel
- AI runtime panel

- [ ] **Step 4: Add derived helpers for trend labels, disk usage, online service count, and signal explanations**

```ts
const onlineServiceCount = computed(() => services.value.filter((item) => item.status === 'running').length)

const diskPercent = computed(() => {
  const host = overview.value?.host_snapshot
  if (!host || typeof host.disk_total_bytes !== 'number' || typeof host.disk_used_bytes !== 'number' || host.disk_total_bytes <= 0) {
    return null
  }
  return toPercent(host.disk_used_bytes, host.disk_total_bytes)
})
```

- [ ] **Step 5: Re-run the cockpit view tests to verify GREEN**

Run: `cd web-console && npm test -- src/views/MonitorCockpitView.spec.ts`

Expected: PASS

### Task 4: End-to-End Verification For The Formal Monitor Platform

**Files:**
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Modify: `web-console/src/stores/platform.spec.ts`
- Modify: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Run the backend monitor tests**

Run: `cd services/monitor-service && go test ./...`

Expected: PASS

- [ ] **Step 2: Run the frontend monitor tests**

Run: `cd web-console && npm test -- src/stores/platform.spec.ts src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 3: Run the monitor service locally and verify 1-second updates**

Run:

```bash
cd services/monitor-service
JWT_SECRET=local-dev APP_NAME=monitor-service HTTP_PORT=8086 go run ./cmd/server
```

In another terminal:

```bash
python3 - <<'PY'
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:8086/api/v1/monitor/stream', timeout=5) as r:
    print(r.read(6000).decode('utf-8', 'replace'))
PY
```

Expected: multiple `event: snapshot` blocks in one read, not a single frame only.

- [ ] **Step 4: Verify overview returns formal page data prerequisites**

Run:

```bash
curl -fsS 'http://127.0.0.1:8086/api/v1/monitor/overview'
```

Expected: host snapshot, accelerator snapshot, service snapshots, and alerts all present in one response envelope.
