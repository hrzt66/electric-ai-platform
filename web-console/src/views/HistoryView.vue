<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import HistoryDetailDrawer from '../components/history/HistoryDetailDrawer.vue'
import HistoryFilters from '../components/history/HistoryFilters.vue'
import HistoryTable from '../components/history/HistoryTable.vue'
import { usePlatformStore } from '../stores/platform'

const platformStore = usePlatformStore()
const drawerVisible = ref(false)
const historyLoading = ref(false)
const historyError = ref('')

const filters = reactive({
  promptKeyword: '',
  modelName: '',
  status: 'all',
  minTotalScore: 0,
})

// 历史中心优先在前端做本地筛选，减少每次输入关键字都去请求后端。
const filteredItems = computed(() =>
  platformStore.history.filter((item) => {
    const keyword = filters.promptKeyword.trim().toLowerCase()
    const matchesKeyword =
      keyword === '' ||
      item.positive_prompt.toLowerCase().includes(keyword) ||
      item.image_name.toLowerCase().includes(keyword)
    const matchesModel = filters.modelName.trim() === '' || item.model_name.toLowerCase().includes(filters.modelName.trim().toLowerCase())
    const matchesStatus = filters.status === 'all' || item.status === filters.status
    const matchesScore = item.total_score >= filters.minTotalScore
    return matchesKeyword && matchesModel && matchesStatus && matchesScore
  }),
)

async function openDetail(item: (typeof filteredItems.value)[number]) {
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

const hasHistoryData = computed(() => platformStore.history.length > 0)

async function loadHistoryPage() {
  historyLoading.value = !hasHistoryData.value
  historyError.value = ''

  try {
    await platformStore.fetchHistory()
  } catch (error) {
    historyError.value = platformStore.historyLoadError || '历史中心加载失败，请检查资产服务与网关链路。'
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  void loadHistoryPage()
})
</script>

<template>
  <div class="history-page">
    <el-alert v-if="historyError" :closable="false" type="warning" show-icon :title="historyError" />

    <el-skeleton v-if="historyLoading" class="page-skeleton" animated :rows="8" />

    <template v-else>
      <HistoryFilters :filters="filters" @reset="resetFilters" />
      <HistoryTable :items="filteredItems" :loading="platformStore.loadingHistory" @open="openDetail" />
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
</style>
