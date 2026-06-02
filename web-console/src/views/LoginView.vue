<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import galleryBackground from '../assets/generated/20260522_154546_auto__________.png'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const submitting = ref(false)
const errorMessage = ref('')
const form = reactive({ username: 'admin', password: 'admin123456' })

const redirectPath = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'))

const statusCards = [
  {
    title: 'Go 微服务编排',
    description: '围绕认证、任务、审计与网关建立可追踪的服务边界，支撑控制台稳定调度。',
    badge: '01',
    metric: 'Service Mesh',
  },
  {
    title: 'Python 模型推理与评分',
    description: '统一承接推理、质量打分与结果回传，让模型能力以标准接口进入评价流程。',
    badge: '02',
    metric: 'Inference Loop',
  },
  {
    title: '多维度质量评价能力',
    description: '从生成结果、业务规则到评分解释形成多维度评价闭环，并沉淀审计轨迹。',
    badge: '03',
    metric: 'Quality Matrix',
  },
]

const capabilityTags = [
  'Service Orchestration',
  'Model Inference',
  'Quality Evaluation',
  'Audit Trace',
]

const galleryBackgroundStyle = computed(() => ({
  backgroundImage: [
    'linear-gradient(180deg, rgba(8, 20, 33, 0.56), rgba(8, 20, 33, 0.82))',
    'linear-gradient(90deg, rgba(8, 20, 33, 0.78), rgba(8, 20, 33, 0.34))',
    `url(${galleryBackground})`,
  ].join(', '),
}))

async function submit() {
  if (submitting.value) {
    return
  }

  submitting.value = true
  errorMessage.value = ''

  try {
    const { data } = await http.post('/auth/login', form)
    authStore.setSession({
      accessToken: data.data.access_token,
      userName: data.data.user_name,
      displayName: data.data.display_name,
    })
    ElMessage.success('登录成功，正在进入评价控制台。')
    await router.push(redirectPath.value)
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.message || '登录失败，请检查网关服务与账号密码。'
    ElMessage.error(errorMessage.value)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="platform-gallery" :style="galleryBackgroundStyle">
      <div class="gallery-orbit gallery-orbit-cyan" />
      <div class="gallery-orbit gallery-orbit-warm" />

      <div class="gallery-copy">
        <p class="gallery-label">技术平台展厅</p>
        <h1>多维度质量评价 AI 平台</h1>
        <p class="gallery-lead">
          以 Go 微服务编排为骨架，衔接 Python 模型推理与评分能力，形成面向业务质量治理、结果追踪与审计闭环的统一平台入口。
        </p>

        <div class="gallery-highlights">
          <span>精密门厅</span>
          <span>评分链路可追踪</span>
          <span>模型能力统一接入</span>
        </div>

        <div class="module-grid">
          <article v-for="card in statusCards" :key="card.title" class="module-card">
            <div class="module-head">
              <span class="module-badge">{{ card.badge }}</span>
              <span class="module-metric">{{ card.metric }}</span>
            </div>
            <h2>{{ card.title }}</h2>
            <p>{{ card.description }}</p>
          </article>
        </div>
      </div>

      <div class="summary-band">
        <div class="summary-copy">
          <p class="summary-label">技术摘要带</p>
          <strong>Go 微服务编排 / Python 模型推理与评分 / 多维度质量评价能力</strong>
        </div>
        <div class="summary-tags">
          <span v-for="tag in capabilityTags" :key="tag">{{ tag }}</span>
        </div>
      </div>
    </section>

    <section class="login-foyer">
      <div class="foyer-card">
        <div class="foyer-header">
          <div>
            <p class="foyer-label">登录门厅</p>
            <h2>进入评价控制台</h2>
          </div>
          <el-tag effect="dark" class="foyer-tag">统一控制台</el-tag>
        </div>

        <p class="foyer-text">
          登录后将进入评价控制台，继续访问多维度质量评价任务、模型推理结果与审计追踪能力。默认演示账户已预填，便于快速校验真实认证链路。
        </p>

        <el-alert
          v-if="errorMessage"
          class="login-alert"
          type="error"
          :closable="false"
          show-icon
          :title="errorMessage"
        />

        <el-form label-position="top" class="login-form" @submit.prevent="submit">
          <el-form-item label="账号">
            <el-input v-model="form.username" size="large" placeholder="请输入账号" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              show-password
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </el-form-item>

          <el-button type="primary" size="large" class="submit-button" :loading="submitting" @click="submit">
            {{ submitting ? '正在登录...' : '进入评价控制台' }}
          </el-button>
        </el-form>

        <div class="login-footer">
          <span>当前入口已接入真实认证链路</span>
          <span>登录成功后将按访问来源或默认总览页跳转</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  --bg-900: #081421;
  --bg-800: #0d1b2a;
  --panel-700: rgba(19, 38, 58, 0.88);
  --line-500: rgba(120, 154, 188, 0.24);
  --text-100: #eaf4ff;
  --text-300: #9fb0c3;
  --accent-500: #35d6ff;
  --accent-600: #27c7e8;
  --warm-500: #f4b860;
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 460px);
  overflow-x: hidden;
  overflow-y: auto;
  background:
    radial-gradient(circle at 16% 18%, rgba(53, 214, 255, 0.18), transparent 28%),
    radial-gradient(circle at 82% 14%, rgba(244, 184, 96, 0.12), transparent 22%),
    linear-gradient(135deg, var(--bg-900) 0%, #0a1624 48%, #0f1f31 100%);
}

.platform-gallery,
.login-foyer {
  position: relative;
}

.platform-gallery {
  padding: 40px 38px 34px 44px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 28px;
  color: var(--text-100);
  isolation: isolate;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.gallery-orbit {
  position: absolute;
  border-radius: 999px;
  filter: blur(42px);
  opacity: 0.8;
  pointer-events: none;
}

.gallery-orbit-cyan {
  width: 280px;
  height: 280px;
  top: 68px;
  left: -68px;
  background: rgba(53, 214, 255, 0.17);
}

.gallery-orbit-warm {
  width: 220px;
  height: 220px;
  right: 92px;
  bottom: 96px;
  background: rgba(244, 184, 96, 0.12);
}

.gallery-copy,
.summary-band {
  position: relative;
  z-index: 1;
}

.gallery-copy {
  display: grid;
  gap: 22px;
  max-width: 860px;
}

.gallery-label,
.gallery-copy h1,
.gallery-lead,
.summary-label,
.foyer-label,
.foyer-card h2,
.foyer-text {
  margin: 0;
}

.gallery-label,
.summary-label,
.foyer-label {
  font-size: 0.8rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.gallery-label {
  color: rgba(234, 244, 255, 0.66);
}

.gallery-copy h1 {
  font-size: clamp(2.7rem, 4.2vw, 4.8rem);
  line-height: 1.02;
  letter-spacing: -0.035em;
}

.gallery-lead {
  max-width: 760px;
  color: var(--text-300);
  font-size: 1.04rem;
  line-height: 1.9;
}

.gallery-highlights {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.gallery-highlights span,
.summary-tags span {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(53, 214, 255, 0.16);
  background: rgba(8, 20, 33, 0.32);
  color: rgba(234, 244, 255, 0.88);
  font-size: 0.86rem;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.module-card {
  padding: 20px 18px 18px;
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(19, 38, 58, 0.9), rgba(10, 24, 37, 0.76)),
    rgba(19, 38, 58, 0.88);
  border: 1px solid var(--line-500);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 24px 42px rgba(2, 7, 14, 0.26);
  backdrop-filter: blur(18px);
}

.module-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.module-badge,
.module-metric {
  display: inline-flex;
  align-items: center;
}

.module-badge {
  width: 36px;
  height: 36px;
  justify-content: center;
  border-radius: 14px;
  background: rgba(53, 214, 255, 0.12);
  color: var(--accent-500);
  font-size: 0.8rem;
  font-weight: 700;
}

.module-metric {
  color: rgba(234, 244, 255, 0.56);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.module-card h2 {
  margin: 18px 0 10px;
  color: var(--text-100);
  font-size: 1.08rem;
  line-height: 1.45;
}

.module-card p {
  margin: 0;
  color: var(--text-300);
  font-size: 0.93rem;
  line-height: 1.8;
}

.summary-band {
  display: grid;
  gap: 16px;
  padding: 22px 24px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(12, 28, 43, 0.92), rgba(12, 31, 49, 0.72));
  border: 1px solid var(--line-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.summary-label {
  color: rgba(159, 176, 195, 0.7);
}

.summary-copy strong {
  display: block;
  margin-top: 10px;
  color: var(--text-100);
  font-size: 1rem;
  line-height: 1.7;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.summary-tags span {
  background: rgba(53, 214, 255, 0.08);
}

.login-foyer {
  display: grid;
  align-items: center;
  padding: 28px 26px 28px 14px;
}

.foyer-card {
  position: relative;
  padding: 30px 26px 24px;
  border-radius: 30px;
  background:
    linear-gradient(180deg, rgba(19, 38, 58, 0.96), rgba(10, 22, 35, 0.92)),
    var(--panel-700);
  border: 1px solid rgba(120, 154, 188, 0.3);
  box-shadow:
    0 24px 50px rgba(3, 10, 18, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(22px);
}

.foyer-card::before {
  content: '';
  position: absolute;
  inset: 14px;
  border-radius: 22px;
  border: 1px solid rgba(53, 214, 255, 0.1);
  pointer-events: none;
}

.foyer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.foyer-label {
  color: rgba(159, 176, 195, 0.78);
}

.foyer-card h2 {
  margin-top: 8px;
  color: var(--text-100);
  font-size: 2.06rem;
  line-height: 1.08;
}

.foyer-tag {
  border: 1px solid rgba(244, 184, 96, 0.26);
  background: rgba(244, 184, 96, 0.14);
  color: var(--warm-500);
}

.foyer-text {
  margin-top: 16px;
  color: var(--text-300);
  line-height: 1.8;
}

.account-hint {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}

.account-hint span {
  display: block;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(120, 154, 188, 0.18);
  background: rgba(8, 20, 33, 0.45);
  color: var(--text-100);
  font-size: 0.92rem;
}

.login-alert {
  margin-top: 16px;
}

.login-form {
  margin-top: 18px;
}

:deep(.login-form .el-form-item__label) {
  color: var(--text-300);
}

:deep(.login-form .el-input__wrapper) {
  border-radius: 16px;
  background: rgba(6, 17, 28, 0.92);
  box-shadow: inset 0 0 0 1px rgba(120, 154, 188, 0.18);
}

:deep(.login-form .el-input__inner) {
  color: var(--text-100);
}

:deep(.login-form .el-input__inner::placeholder) {
  color: rgba(159, 176, 195, 0.56);
}

:deep(.login-form .el-input__wrapper.is-focus) {
  box-shadow:
    inset 0 0 0 1px rgba(53, 214, 255, 0.46),
    0 0 0 4px rgba(53, 214, 255, 0.08);
}

.submit-button {
  width: 100%;
  height: 50px;
  border: 0;
  border-radius: 16px;
  background: linear-gradient(90deg, var(--accent-500), var(--accent-600));
  box-shadow: 0 16px 28px rgba(39, 199, 232, 0.2);
  color: #03111d;
  font-weight: 700;
}

.submit-button:hover,
.submit-button:focus-visible {
  background: linear-gradient(90deg, #60e2ff, var(--accent-500));
}

.login-footer {
  display: grid;
  gap: 6px;
  margin-top: 18px;
  color: rgba(159, 176, 195, 0.84);
  font-size: 0.84rem;
}

@media (max-width: 1220px) {
  .module-grid {
    grid-template-columns: 1fr;
    max-width: 540px;
  }
}

@media (max-width: 1040px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .platform-gallery {
    padding: 30px 22px 14px;
  }

  .login-foyer {
    padding: 10px 22px 24px;
  }
}

@media (max-width: 720px) {
  .gallery-copy h1 {
    font-size: 2.35rem;
  }

  .summary-band,
  .foyer-card,
  .module-card {
    border-radius: 24px;
  }

  .foyer-card {
    padding: 24px 18px 20px;
  }

  .foyer-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
