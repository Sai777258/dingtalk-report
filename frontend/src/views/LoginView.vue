<script setup>
/**
 * LoginView — Demo mode login page.
 *
 * Design: "Precision Instrument" — a measuring tool for work hours.
 * The brass gauge line animates in as the page loads, then pauses,
 * like a caliper settling into position.
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref(null)
const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const showGauge = ref(false)

// Animate the gauge line in after mount
import { onMounted } from 'vue'
onMounted(() => {
  requestAnimationFrame(() => {
    showGauge.value = true
  })
})

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch {
    // Error is already set in the store
  }
}

function handleKeyup(event) {
  if (event.key === 'Enter') handleLogin()
}
</script>

<template>
  <div class="login-page">
    <!-- Signature: brass gauge line -->
    <div class="gauge-line" :class="{ active: showGauge }" />

    <div class="login-card">
      <!-- Header -->
      <div class="card-header">
        <div class="brand-mark" />
        <h1>工作汇报统计</h1>
        <p class="subtitle">Demo 模式 — 使用本地账号登录</p>
      </div>

      <!-- Form -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup="handleKeyup"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>

        <!-- Error message -->
        <transition name="fade">
          <div v-if="auth.error" class="error-message" @click="auth.clearError()">
            {{ auth.error }}
          </div>
        </transition>

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="auth.loading"
          @click="handleLogin"
        >
          {{ auth.loading ? '验证中…' : '登录' }}
        </el-button>
      </el-form>

      <!-- Demo hints -->
      <div class="demo-hints">
        <p class="hint-title">可用 Demo 账号</p>
        <div class="hint-grid">
          <span class="hint-chip">admin</span>
          <span class="hint-chip">executive</span>
          <span class="hint-chip">dept_mgr</span>
          <span class="hint-chip">prod_mgr</span>
          <span class="hint-chip">employee</span>
        </div>
        <p class="hint-password">密码均为 <code>admin123</code></p>
      </div>
    </div>

    <p class="footer-text">钉钉工作汇报统计系统 v0.1</p>
  </div>
</template>

<style scoped>
/* ================================================================
   Login Page — "Precision Instrument"
   ================================================================ */

.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-6);
  background:
    radial-gradient(ellipse at 50% 40%, rgba(200, 164, 92, 0.04) 0%, transparent 70%),
    var(--steel);
}

/* ---- Signature: brass gauge line ---- */
.gauge-line {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--brass) 20%,
    var(--brass) 80%,
    transparent 100%
  );
  transition: width var(--duration-slow) var(--ease-out);
  z-index: 10;
}

.gauge-line.active {
  width: 100%;
}

/* ---- Card ---- */
.login-card {
  width: 400px;
  max-width: 100%;
  background: var(--paper);
  border-radius: var(--radius-lg);
  padding: var(--space-12) var(--space-10);
  box-shadow: var(--shadow-elevated);
  animation: card-rise var(--duration-slow) var(--ease-out) both;
}

@keyframes card-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---- Header ---- */
.card-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.brand-mark {
  width: 36px;
  height: 4px;
  background: var(--brass);
  margin: 0 auto var(--space-5);
  border-radius: 2px;
}

.card-header h1 {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 2px;
  margin-bottom: var(--space-2);
}

.subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

/* ---- Form ---- */
.login-form {
  margin-top: var(--space-6);
}

.login-form :deep(.el-input__wrapper) {
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border) inset;
  transition: box-shadow var(--duration-fast) var(--ease-out);
}

.login-form :deep(.el-form-item) {
  margin-bottom: var(--space-5);
}

.submit-btn {
  width: 100%;
  margin-top: var(--space-4);
  height: 44px;
  font-size: var(--text-base);
  font-weight: 600;
  letter-spacing: 2px;
  border-radius: var(--radius-md);
  background: var(--brass) !important;
  border-color: var(--brass) !important;
  transition:
    background var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.submit-btn:hover:not(:disabled) {
  background: var(--brass-hover) !important;
  border-color: var(--brass-hover) !important;
  transform: translateY(-1px);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* ---- Error ---- */
.error-message {
  background: rgba(212, 105, 90, 0.08);
  border: 1px solid rgba(212, 105, 90, 0.25);
  color: var(--vermilion);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  margin-bottom: var(--space-2);
  cursor: pointer;
  transition: opacity var(--duration-fast);
}

.error-message:hover {
  opacity: 0.8;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ---- Demo hints ---- */
.demo-hints {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--border);
  text-align: center;
}

.hint-title {
  font-size: var(--text-xs);
  color: var(--text-muted);
  letter-spacing: 0.5px;
  margin-bottom: var(--space-3);
}

.hint-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: center;
  margin-bottom: var(--space-3);
}

.hint-chip {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--border);
  padding: 2px 10px;
  border-radius: 100px;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.hint-chip:hover {
  color: var(--brass);
  border-color: var(--brass);
}

.hint-password {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.hint-password code {
  font-family: var(--font-mono);
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: var(--text-xs);
}

/* ---- Footer ---- */
.footer-text {
  margin-top: var(--space-8);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.2);
  letter-spacing: 1px;
}

/* ---- Responsive ---- */
@media (max-width: 480px) {
  .login-card {
    padding: var(--space-8) var(--space-6);
  }

  .card-header h1 {
    font-size: var(--text-xl);
  }
}
</style>
