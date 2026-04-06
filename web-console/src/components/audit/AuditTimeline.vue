<script setup lang="ts">
import { computed } from 'vue'

import type { AuditEvent } from '../../types/platform'
import { presentAuditEvent } from './audit-event-presenter'

const props = withDefaults(
  defineProps<{
    events: AuditEvent[]
    emptyDescription?: string
  }>(),
  {
    emptyDescription: '当前没有可展示的审计事件。',
  },
)

// 统一把后端审计字段转换成适合人阅读的中文标题与正文，页面层只负责摆放组件。
const presentedEvents = computed(() =>
  props.events.map((event) => ({
    ...event,
    ...presentAuditEvent(event),
  })),
)
</script>

<template>
  <el-empty v-if="presentedEvents.length === 0" :description="emptyDescription" />

  <el-timeline v-else class="audit-timeline">
    <el-timeline-item v-for="event in presentedEvents" :key="event.id" :timestamp="event.created_at" placement="top">
      <strong class="timeline-title">{{ event.title }}</strong>
      <p class="timeline-body">{{ event.description }}</p>
    </el-timeline-item>
  </el-timeline>
</template>

<style scoped>
.audit-timeline {
  min-width: 0;
}

.timeline-title,
.timeline-body {
  margin: 0;
}

.timeline-title {
  color: #17202b;
}

.timeline-body {
  margin-top: 6px;
  color: #53606f;
  line-height: 1.55;
  word-break: break-word;
}
</style>
