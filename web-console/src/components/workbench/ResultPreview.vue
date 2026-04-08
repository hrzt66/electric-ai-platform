<script setup lang="ts">
import { computed } from 'vue'

import { buildImageUrl } from '../../api/platform'
import type { AssetHistoryItem, GenerateTask } from '../../types/platform'

const props = defineProps<{
  assets: AssetHistoryItem[]
  activeIndex: number
  task: GenerateTask | null
}>()

const emit = defineEmits<{
  'update:activeIndex': [value: number]
}>()

const activeAsset = computed(() => props.assets[props.activeIndex] ?? null)
</script>

<template>
  <section class="preview-card preview-card--compact">
    <div class="preview-header">
      <div>
        <p class="preview-eyebrow">结果输出</p>
        <h2 class="preview-title">多图预览</h2>
      </div>
      <el-tag v-if="task" :type="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'danger' : 'info'">
        {{ task.stage }}
      </el-tag>
    </div>

    <div v-if="activeAsset" class="image-stage">
      <div class="image-frame">
        <el-image
          class="main-image"
          :src="buildImageUrl(activeAsset.file_path)"
          fit="contain"
          :preview-src-list="assets.map((item) => buildImageUrl(item.file_path))"
          :initial-index="activeIndex"
        />
      </div>

      <div class="meta-row">
        <span>任务 #{{ activeAsset.job_id }}</span>
        <span>{{ activeAsset.image_name }}</span>
        <span>总分 {{ activeAsset.total_score.toFixed(2) }}</span>
      </div>

      <div v-if="assets.length > 1" class="thumbs">
        <button
          v-for="(item, index) in assets"
          :key="item.id"
          class="thumb"
          :class="{ active: index === activeIndex }"
          type="button"
          @click="emit('update:activeIndex', index)"
        >
          <img :src="buildImageUrl(item.file_path)" :alt="item.image_name" />
        </button>
      </div>
    </div>

    <el-empty v-else class="preview-empty" :description="task ? '任务已提交，正在等待生成结果。' : '先在左侧提交一个真实生成任务。'" />
  </section>
</template>

<style scoped>
.preview-card {
  min-height: 0;
  padding: 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  align-self: start;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.preview-eyebrow,
.preview-title {
  margin: 0;
}

.preview-eyebrow {
  font-size: 0.76rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.preview-title {
  margin-top: 4px;
  font-size: 1.28rem;
  color: #17202b;
}

.image-stage {
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 10px;
  align-content: start;
}

.image-frame {
  height: clamp(220px, 30vh, 320px);
  padding: 12px;
  border-radius: 18px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(15, 23, 32, 0.02), rgba(15, 23, 32, 0.08)),
    linear-gradient(45deg, rgba(19, 71, 168, 0.06), rgba(211, 164, 73, 0.12));
}

.main-image {
  width: 100%;
  height: 100%;
  border-radius: 14px;
  cursor: zoom-in;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #53606f;
  font-size: 0.82rem;
}

.thumbs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.thumb {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  overflow: hidden;
  border: 2px solid transparent;
  background: #eff3f7;
  padding: 0;
  cursor: pointer;
  flex: 0 0 auto;
}

.thumb.active {
  border-color: #1347a8;
  box-shadow: 0 0 0 3px rgba(19, 71, 168, 0.12);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.preview-empty {
  min-height: clamp(220px, 30vh, 320px);
}

:deep(.preview-empty .el-empty) {
  height: 100%;
  min-height: inherit;
}

:deep(.el-image__wrapper) {
  border-radius: inherit;
}

@media (max-width: 768px) {
  .preview-card--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .preview-header {
    flex-direction: column;
    align-items: stretch;
    margin-bottom: 8px;
  }

  .image-frame {
    height: min(54vw, 260px);
    padding: 8px;
  }

  .meta-row {
    flex-direction: column;
    gap: 4px;
  }

  .thumb {
    width: 52px;
    height: 52px;
    border-radius: 10px;
  }
}
</style>
