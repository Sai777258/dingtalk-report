<script setup>
/**
 * DashboardView — placeholder for the main dashboard.
 */
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="dashboard">
    <div class="topbar">
      <span class="topbar-title">工作汇报统计系统</span>
      <div class="topbar-right">
        <span class="user-info" v-if="auth.user">
          {{ auth.user.first_name || auth.user.username }}
          <span class="role-tag">{{ auth.user.role_display }}</span>
        </span>
        <el-button text size="small" @click="handleLogout">退出</el-button>
      </div>
    </div>

    <div class="dashboard-body">
      <div class="welcome-card">
        <div class="brand-mark" />
        <h2>欢迎使用工作汇报统计系统</h2>
        <p class="welcome-text">
          当前以 <strong>{{ auth.user?.role_display }}</strong> 身份登录。
          仪表盘功能将在后续版本中实现。
        </p>
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-value">—</span>
            <span class="stat-label">本月工时</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">—</span>
            <span class="stat-label">活跃项目</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">—</span>
            <span class="stat-label">日志条目</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--steel-light);
}

/* ---- Top bar ---- */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  height: 56px;
  background: var(--steel);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.topbar-title {
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 1px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.user-info {
  color: rgba(255, 255, 255, 0.6);
  font-size: var(--text-sm);
}

.role-tag {
  display: inline-block;
  font-size: var(--text-xs);
  color: var(--brass);
  margin-left: var(--space-2);
}

/* ---- Body ---- */
.dashboard-body {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 56px);
  padding: var(--space-6);
}

.welcome-card {
  background: var(--paper);
  border-radius: var(--radius-lg);
  padding: var(--space-12) var(--space-10);
  max-width: 520px;
  width: 100%;
  text-align: center;
  box-shadow: var(--shadow-card);
}

.brand-mark {
  width: 36px;
  height: 4px;
  background: var(--brass);
  margin: 0 auto var(--space-5);
  border-radius: 2px;
}

.welcome-card h2 {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.welcome-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.7;
}

.welcome-text strong {
  color: var(--brass);
}

/* ---- Stats row ---- */
.stats-row {
  display: flex;
  gap: var(--space-6);
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--border);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 300;
  color: var(--text-muted);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
