<script setup lang="ts">
type HistoryFiltersState = {
  promptKeyword: string
  modelName: string
  status: string
  minTotalScore: number
}

defineProps<{
  filters: HistoryFiltersState
  expanded: boolean
}>()

const emit = defineEmits<{
  reset: []
  toggle: []
}>()
</script>

<template>
  <section class="filters filters--compact">
    <div class="filters-header">
      <div>
        <p class="filters-eyebrow">历史检索</p>
        <h2 class="filters-title">多条件筛选</h2>
      </div>
      <div class="filters-actions">
        <button class="filters-toggle" type="button" @click="emit('toggle')">
          {{ expanded ? '收起筛选' : '展开筛选' }}
        </button>
        <el-button plain @click="emit('reset')">重置筛选</el-button>
      </div>
    </div>

    <div class="grid" :class="{ collapsed: !expanded }">
      <el-form-item label="提示词关键词">
        <el-input v-model="filters.promptKeyword" placeholder="按提示词或图片名筛选" clearable />
      </el-form-item>
      <el-form-item label="模型名称">
        <el-input v-model="filters.modelName" placeholder="例如 sd15-electric" clearable />
      </el-form-item>
      <el-form-item label="资产状态">
        <el-select v-model="filters.status">
          <el-option label="全部" value="all" />
          <el-option label="已评分" value="scored" />
          <el-option label="已生成" value="generated" />
        </el-select>
      </el-form-item>
      <el-form-item label="最低总分">
        <el-slider v-model="filters.minTotalScore" :min="0" :max="100" show-input />
      </el-form-item>
    </div>
  </section>
</template>

<style scoped>
.filters {
  padding: 22px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.filters-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.filters-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filters-eyebrow,
.filters-title {
  margin: 0;
}

.filters-eyebrow {
  font-size: 0.8rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.filters-title {
  margin-top: 6px;
  color: #17202b;
  font-size: 1.4rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.filters-toggle {
  display: none;
  border: 1px solid rgba(20, 71, 166, 0.16);
  border-radius: 999px;
  padding: 10px 14px;
  background: #f8fbff;
  color: #1447a6;
  cursor: pointer;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .filters--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .filters-title {
    font-size: 1rem;
  }

  .filters-header {
    margin-bottom: 10px;
  }

  .filters-header,
  .filters-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filters-toggle {
    display: inline-flex;
    justify-content: center;
  }

  .grid.collapsed {
    display: none;
  }
}

@media (max-width: 600px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
