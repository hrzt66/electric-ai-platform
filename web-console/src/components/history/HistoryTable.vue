<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { buildImageUrl } from '../../api/platform'
import type { AssetHistoryItem } from '../../types/platform'
import { shouldUseHistoryCards } from '../../utils/mobile-layout'

const props = defineProps<{
  items: AssetHistoryItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  open: [item: AssetHistoryItem]
}>()

const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const isMobile = computed(() => shouldUseHistoryCards(viewportWidth.value))

function syncViewport() {
  viewportWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', syncViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
})
</script>

<template>
  <section class="table-card">
    <div class="table-header">
      <div>
        <p class="table-eyebrow">资产结果</p>
        <h2 class="table-title">历史中心</h2>
      </div>
      <el-tag type="info">共 {{ props.items.length }} 条</el-tag>
    </div>

    <div v-if="isMobile" class="history-cards">
      <article v-for="row in props.items" :key="row.id" class="history-card" @click="emit('open', row)">
        <img class="thumb history-card__thumb" :src="buildImageUrl(row.file_path)" :alt="row.image_name" />
        <div class="history-card__body">
          <strong>{{ row.image_name }}</strong>
          <p>{{ row.positive_prompt }}</p>
          <div class="history-card__meta">
            <span>{{ row.model_name }}</span>
            <span>总分 {{ row.total_score.toFixed(2) }}</span>
            <span>{{ row.status }}</span>
            <span>{{ row.created_at }}</span>
          </div>
          <el-button link type="primary" @click.stop="emit('open', row)">查看详情</el-button>
        </div>
      </article>

      <el-empty v-if="!props.loading && props.items.length === 0" description="暂无历史资产" />
    </div>

    <el-table v-else :data="props.items" stripe v-loading="props.loading" class="history-table" empty-text="暂无历史资产" @row-click="emit('open', $event)">
      <el-table-column label="预览" width="110">
        <template #default="{ row }">
          <img class="thumb" :src="buildImageUrl(row.file_path)" :alt="row.image_name" />
        </template>
      </el-table-column>
      <el-table-column label="提示词" min-width="260">
        <template #default="{ row }">
          <div class="prompt-cell">
            <strong>{{ row.image_name }}</strong>
            <span>{{ row.positive_prompt }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="model_name" label="模型" min-width="150" />
      <el-table-column label="总分" width="110">
        <template #default="{ row }">
          {{ row.total_score.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column prop="created_at" label="生成时间" min-width="180" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="emit('open', row)">查看详情</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<style scoped>
.table-card {
  padding: 22px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}

.table-eyebrow,
.table-title {
  margin: 0;
}

.table-eyebrow {
  font-size: 0.8rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.table-title {
  margin-top: 6px;
  color: #17202b;
  font-size: 1.4rem;
}

.history-table :deep(.el-table__row) {
  cursor: pointer;
}

.history-cards {
  display: grid;
  gap: 14px;
}

.history-card {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
  background: #f8fafc;
  cursor: pointer;
}

.thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 14px;
  background: #edf2f7;
}

.history-card__thumb {
  width: 88px;
  height: 88px;
}

.prompt-cell,
.history-card__body {
  display: grid;
  gap: 6px;
}

.prompt-cell span,
.history-card__body p {
  color: #53606f;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-card__body strong,
.history-card__body p {
  margin: 0;
}

.history-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  color: #64748b;
  font-size: 0.8rem;
}

@media (max-width: 600px) {
  .table-header {
    flex-direction: column;
  }

  .history-card {
    grid-template-columns: 1fr;
  }

  .history-card__thumb {
    width: 100%;
    height: 180px;
  }
}
</style>
