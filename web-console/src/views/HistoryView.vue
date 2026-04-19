<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import HistoryDetailDrawer from '../components/history/HistoryDetailDrawer.vue'
import HistoryFilters from '../components/history/HistoryFilters.vue'
import HistoryTable from '../components/history/HistoryTable.vue'
import { usePlatformStore } from '../stores/platform'
import type { AssetHistoryItem } from '../types/platform'

const platformStore = usePlatformStore()
const drawerVisible = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const hasLoadedOnce = ref(false)
const HISTORY_LOAD_DEBOUNCE_MS = 250
let pendingHistoryLoad: ReturnType<typeof setTimeout> | null = null

const filters = reactive({
  promptKeyword: '',
  modelName: '',
  status: 'all',
  minTotalScore: 0,
})

async function openDetail(item: AssetHistoryItem) {
  // 抽屉需要同时展示资产详情和对应任务审计，因此两类数据一起预取。
  await Promise.all([platformStore.fetchAssetDetail(item.id), platformStore.fetchTaskAudit(item.job_id)])
  drawerVisible.value = true
}

function resetFilters() {
  filters.promptKeyword = ''
  filters.modelName = ''
  filters.status = 'all'
  filters.minTotalScore = 0
}

const hasHistoryData = computed(() => platformStore.historyTotal > 0 || platformStore.historyPageItems.length > 0)

async function loadHistoryPage(page = 1, pageSize = platformStore.historyPageSize) {
  historyLoading.value = !hasLoadedOnce.value
  historyError.value = ''

  try {
    await platformStore.fetchHistoryPage({
      page,
      page_size: pageSize,
      prompt_keyword: filters.promptKeyword.trim(),
      model_name: filters.modelName.trim(),
      status: filters.status,
      min_total_score: filters.minTotalScore,
    })
  } catch {
    historyError.value = platformStore.historyPageLoadError || '历史中心加载失败，请检查资产服务与网关链路。'
  } finally {
    historyLoading.value = false
    hasLoadedOnce.value = true
  }
}

function scheduleHistoryLoad(page = 1, pageSize = platformStore.historyPageSize, immediate = false) {
  if (pendingHistoryLoad) {
    clearTimeout(pendingHistoryLoad)
    pendingHistoryLoad = null
  }

  const trigger = () => {
    pendingHistoryLoad = null
    void loadHistoryPage(page, pageSize)
  }

  if (immediate) {
    trigger()
    return
  }

  pendingHistoryLoad = setTimeout(trigger, HISTORY_LOAD_DEBOUNCE_MS)
}

onMounted(() => {
  scheduleHistoryLoad(1, platformStore.historyPageSize, true)
})

onBeforeUnmount(() => {
  if (pendingHistoryLoad) {
    clearTimeout(pendingHistoryLoad)
  }
})

watch(
  () => [filters.promptKeyword, filters.modelName, filters.status, filters.minTotalScore],
  () => {
    scheduleHistoryLoad(1)
  },
)
</script>

<template>
  <div class="history-page">
    <el-alert v-if="historyError" :closable="false" type="warning" show-icon :title="historyError" />

    <el-skeleton v-if="historyLoading" class="page-skeleton" animated :rows="8" />

    <template v-else>
      <HistoryFilters :filters="filters" @reset="resetFilters" />
      <HistoryTable :items="platformStore.historyPageItems" :total="platformStore.historyTotal" :loading="platformStore.loadingHistoryPage" @open="openDetail" />
      <section v-if="hasHistoryData" class="pagination-card">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="platformStore.historyTotal"
          :current-page="platformStore.historyPage"
          :page-size="platformStore.historyPageSize"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="(page) => scheduleHistoryLoad(page, platformStore.historyPageSize, true)"
          @size-change="(pageSize) => scheduleHistoryLoad(1, pageSize, true)"
        />
      </section>
      <HistoryDetailDrawer v-model:visible="drawerVisible" :detail="platformStore.selectedAssetDetail" :audit-events="platformStore.currentTaskAudit" />
    </template>
  </div>
</template>

<style scoped>
.history-page {
  display: grid;
  gap: 20px;
}

.page-skeleton {
  border-radius: 24px;
  padding: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.pagination-card {
  display: flex;
  justify-content: flex-end;
  padding: 18px 22px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.pagination-card :deep(.el-pagination) {
  flex-wrap: wrap;
  justify-content: flex-end;
}
</style>
