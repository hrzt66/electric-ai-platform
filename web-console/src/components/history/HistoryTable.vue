<script setup lang="ts">
import { buildImageUrl } from '../../api/platform'
import type { AssetHistoryItem } from '../../types/platform'

defineProps<{
  items: AssetHistoryItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  open: [item: AssetHistoryItem]
}>()
</script>

<template>
  <section class="table-card">
    <div class="table-header">
      <div>
        <p class="table-eyebrow">资产结果</p>
        <h2 class="table-title">历史中心</h2>
      </div>
      <el-tag type="info">共 {{ items.length }} 条</el-tag>
    </div>

    <el-table :data="items" stripe v-loading="loading" class="history-table" empty-text="暂无历史资产" @row-click="emit('open', $event)">
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

.thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 14px;
  background: #edf2f7;
}

.prompt-cell {
  display: grid;
  gap: 4px;
}

.prompt-cell span {
  color: #53606f;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
