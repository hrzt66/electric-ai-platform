<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

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
    title: 'Go 微服务边界',
    description: '认证、模型、任务、资产、审计、网关全部独立运行。',
    badge: '6 Services',
  },
  {
    title: 'Python 模型中心',
    description: '统一承接 SD1.5、UniPic2、ImageReward 与美学评分。',
    badge: '4 Models',
  },
  {
    title: '统一运行时',
    description: '模型、缓存、日志与输出统一落在 G 盘运行时目录。',
    badge: 'G:\\Runtime',
  },
]

async function submit() {
  submitting.value = true
  errorMessage.value = ''

  try {
    const { data } = await http.post('/auth/login', form)
    authStore.setSession({
      accessToken: data.data.access_token,
      userName: data.data.user_name,
      displayName: data.data.display_name,
    })
    ElMessage.success('登录成功，正在进入工业工作台。')
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
    <section class="control-stage">
      <div class="stage-grid" />
      <div class="stage-glow stage-glow-left" />
      <div class="stage-glow stage-glow-right" />

      <div class="stage-copy">
        <p class="eyebrow">Industrial Control Center</p>
        <h1>工业电力图像生成与评分平台</h1>
        <p class="lead">
          面向变电站巡检、设备数字孪生、工业场景合成与结果评分的统一入口。
          这里不是普通后台，而是当前平台的工业控制中心与运行门厅。
        </p>

        <div class="stage-badges">
          <span>真实生成</span>
          <span>真实评分</span>
          <span>任务审计</span>
          <span>模型中心</span>
        </div>

        <div class="status-grid">
          <article v-for="card in statusCards" :key="card.title" class="status-card">
            <div class="status-head">
              <strong>{{ card.title }}</strong>
              <span>{{ card.badge }}</span>
            </div>
            <p>{{ card.description }}</p>
          </article>
        </div>
      </div>

      <div class="system-board">
        <div class="board-header">
          <p>工业控制中心</p>
          <span class="board-live"><i /> Online</span>
        </div>

        <div class="board-panel">
          <div class="board-row">
            <span>Gateway</span>
            <strong>API Routing Active</strong>
          </div>
          <div class="board-row">
            <span>Model Runtime</span>
            <strong>Python Inference Ready</strong>
          </div>
          <div class="board-row">
            <span>Asset Pipeline</span>
            <strong>Generate / Score / Audit</strong>
          </div>
        </div>

        <div class="board-diagram">
          <div class="node">Go</div>
          <div class="line" />
          <div class="node active">AI</div>
          <div class="line" />
          <div class="node">Files</div>
        </div>
      </div>
    </section>

    <section class="login-shell">
      <div class="login-shell-inner">
        <div class="shell-header">
          <div>
            <p class="shell-eyebrow">访问入口</p>
            <h2>进入工作台</h2>
          </div>
          <el-tag type="warning" effect="dark">本机原生优先</el-tag>
        </div>

        <p class="shell-text">
          登录后将直接进入当前平台的生成工作台。默认演示账户已预填，便于你快速联调前后端链路。
        </p>

        <div class="account-hint">
          <span>默认账号：admin</span>
          <span>默认密码：admin123456</span>
        </div>

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
            <el-input v-model="form.username" size="large" placeholder="请输入账号" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" />
          </el-form-item>

          <el-button type="primary" size="large" class="submit-button" :loading="submitting" @click="submit">
            {{ submitting ? '正在登录...' : '进入工作台' }}
          </el-button>
        </el-form>

        <div class="login-footer">
          <span>当前入口已接入真实认证链路</span>
          <span>登录后按 redirect 或默认总览页跳转</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(380px, 440px);
  overflow: hidden;
  background:
    linear-gradient(120deg, #081019 0%, #0d1723 42%, #eaf0f7 42%, #eef3f8 100%);
}

.control-stage,
.login-shell {
  position: relative;
}

.control-stage {
  padding: 36px 32px 32px 40px;
  color: #f8fafc;
  isolation: isolate;
}

.stage-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.95), rgba(0, 0, 0, 0.25));
  pointer-events: none;
}

.stage-glow {
  position: absolute;
  border-radius: 999px;
  filter: blur(50px);
  opacity: 0.5;
  pointer-events: none;
}

.stage-glow-left {
  width: 280px;
  height: 280px;
  background: rgba(18, 98, 214, 0.24);
  left: -80px;
  top: 60px;
}

.stage-glow-right {
  width: 220px;
  height: 220px;
  background: rgba(211, 164, 73, 0.18);
  right: 120px;
  bottom: 40px;
}

.stage-copy {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 20px;
  max-width: 860px;
}

.eyebrow,
.stage-copy h1,
.lead,
.shell-eyebrow,
.shell-header h2,
.shell-text {
  margin: 0;
}

.eyebrow,
.shell-eyebrow {
  font-size: 0.82rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.eyebrow {
  color: rgba(248, 250, 252, 0.7);
}

.stage-copy h1 {
  font-size: clamp(2.5rem, 4vw, 4.6rem);
  line-height: 1.04;
  letter-spacing: -0.02em;
}

.lead {
  max-width: 760px;
  color: rgba(248, 250, 252, 0.78);
  line-height: 1.85;
  font-size: 1.02rem;
}

.stage-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stage-badges span {
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(248, 250, 252, 0.88);
  font-size: 0.88rem;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 8px;
}

.status-card {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.status-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.status-head strong,
.status-head span,
.status-card p {
  display: block;
}

.status-head strong {
  font-size: 1rem;
}

.status-head span {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(211, 164, 73, 0.14);
  color: #f0d78a;
  font-size: 0.74rem;
  white-space: nowrap;
}

.status-card p {
  margin: 12px 0 0;
  color: rgba(248, 250, 252, 0.72);
  line-height: 1.7;
  font-size: 0.92rem;
}

.system-board {
  position: relative;
  z-index: 1;
  margin-top: 36px;
  max-width: 520px;
  padding: 18px;
  border-radius: 24px;
  background: rgba(6, 12, 18, 0.68);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px);
}

.board-header,
.board-row,
.board-diagram {
  display: flex;
  align-items: center;
}

.board-header,
.board-row {
  justify-content: space-between;
}

.board-header p,
.board-row span,
.board-row strong {
  margin: 0;
}

.board-header p {
  color: rgba(248, 250, 252, 0.86);
  font-weight: 600;
}

.board-live {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #9ce6b0;
  font-size: 0.84rem;
}

.board-live i {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #0f9d58;
  box-shadow: 0 0 0 6px rgba(15, 157, 88, 0.16);
}

.board-panel {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

.board-row {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
}

.board-row span {
  color: rgba(248, 250, 252, 0.62);
  font-size: 0.84rem;
}

.board-row strong {
  color: rgba(248, 250, 252, 0.9);
  font-size: 0.9rem;
}

.board-diagram {
  gap: 12px;
  margin-top: 16px;
}

.node {
  width: 84px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(248, 250, 252, 0.9);
  font-weight: 700;
}

.node.active {
  background: linear-gradient(135deg, rgba(20, 71, 166, 0.46), rgba(211, 164, 73, 0.22));
  border-color: rgba(211, 164, 73, 0.34);
}

.line {
  flex: 1;
  height: 2px;
  background: linear-gradient(90deg, rgba(211, 164, 73, 0.18), rgba(20, 71, 166, 0.8));
}

.login-shell {
  display: grid;
  align-items: center;
  padding: 24px;
}

.login-shell-inner {
  position: relative;
  padding: 28px 24px 24px;
  border-radius: 30px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.82)),
    linear-gradient(135deg, rgba(255, 255, 255, 0.75), rgba(234, 240, 247, 0.95));
  border: 1px solid rgba(15, 23, 32, 0.08);
  box-shadow:
    0 28px 60px rgba(9, 18, 30, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(18px);
}

.login-shell-inner::before {
  content: '';
  position: absolute;
  inset: 14px;
  border-radius: 22px;
  border: 1px solid rgba(20, 71, 166, 0.08);
  pointer-events: none;
}

.shell-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.shell-eyebrow {
  color: #875f1f;
}

.shell-header h2 {
  margin-top: 8px;
  color: #17202b;
  font-size: 2rem;
  line-height: 1.1;
}

.shell-text {
  margin-top: 14px;
  color: #53606f;
  line-height: 1.7;
}

.account-hint {
  margin-top: 16px;
  display: grid;
  gap: 10px;
}

.account-hint span {
  display: block;
  padding: 12px 14px;
  border-radius: 16px;
  background: #f3f7fb;
  color: #334155;
  font-size: 0.92rem;
}

.login-alert {
  margin-top: 16px;
}

.login-form {
  margin-top: 18px;
}

.submit-button {
  width: 100%;
  height: 48px;
  border: 0;
  border-radius: 16px;
  background: linear-gradient(90deg, #1447a6, #0f3278);
  box-shadow: 0 12px 24px rgba(20, 71, 166, 0.22);
}

.login-footer {
  display: grid;
  gap: 6px;
  margin-top: 18px;
  color: #64748b;
  font-size: 0.84rem;
}

@media (max-width: 1240px) {
  .status-grid {
    grid-template-columns: 1fr;
    max-width: 520px;
  }
}

@media (max-width: 1120px) {
  .login-page {
    grid-template-columns: 1fr;
    background: linear-gradient(180deg, #081019 0%, #0d1723 52%, #eef3f8 52%, #eef3f8 100%);
  }

  .control-stage {
    padding: 28px 20px 10px;
  }

  .login-shell {
    padding: 20px;
  }

  .system-board {
    max-width: none;
  }
}

@media (max-width: 720px) {
  .stage-copy h1 {
    font-size: 2.3rem;
  }

  .board-diagram {
    flex-wrap: wrap;
  }

  .line {
    display: none;
  }

  .login-shell-inner {
    padding: 22px 18px 18px;
  }
}

@media (max-width: 768px) {
  .control-stage {
    padding: 24px 16px 8px;
  }

  .stage-copy {
    gap: 14px;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .system-board,
  .login-shell {
    margin-top: 18px;
  }

  .shell-header {
    flex-direction: column;
  }
}
</style>
