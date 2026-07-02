<script setup>
/**
 * App.vue — main layout with sidebar navigation.
 *
 * Guest routes (login) render standalone; authenticated routes wrap in sidebar layout.
 */
import { computed } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { DataAnalysis, Document, ArrowLeft } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isGuest = computed(() => route.meta.guest)

const navItems = computed(() => {
  const items = [
    { path: '/', label: '仪表盘', icon: DataAnalysis },
    { path: '/reports', label: '工作日志', icon: Document },
  ]
  // Admin-only: link to Django Admin for user/system management
  if (auth.isAdmin) {
    items.push({ path: '/admin/', label: '系统管理', icon: 'Setting', external: true })
  }
  return items
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function navigate(item) {
  if (item.external) {
    window.open(item.path, '_blank')
    return
  }
  router.push(item.path)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <!-- Guest layout: standalone (login page) -->
  <RouterView v-if="isGuest" />

  <!-- Authenticated layout: sidebar + content -->
  <div v-else class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand" @click="router.push('/')">
        <span class="brand-icon" />
        <span class="brand-text">工作汇报统计</span>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="navigate(item)"
        >
          <el-icon v-if="!item.external" :size="16"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info" v-if="auth.user">
          <span class="user-name">{{ auth.user.first_name || auth.user.username }}</span>
          <span class="user-role">{{ auth.user.role_display }}</span>
        </div>
        <el-button text size="small" class="logout-btn" @click="handleLogout">
          <el-icon :size="14"><ArrowLeft /></el-icon>
          退出
        </el-button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--steel);
}

/* ---- Sidebar ---- */
.sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--steel-light);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 10;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5);
  cursor: pointer;
}

.brand-icon {
  width: 20px;
  height: 3px;
  background: var(--brass);
  border-radius: 2px;
  flex-shrink: 0;
}

.brand-text {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 1px;
}

/* ---- Nav ---- */
.sidebar-nav {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.45);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  width: 100%;
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.7);
}

.nav-item.active {
  background: rgba(200, 164, 92, 0.1);
  color: var(--brass);
}

/* ---- Sidebar footer ---- */
.sidebar-footer {
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: var(--space-3);
}

.user-name {
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.7);
}

.user-role {
  font-size: var(--text-xs);
  color: var(--brass);
}

.logout-btn {
  color: rgba(255, 255, 255, 0.35) !important;
  font-size: var(--text-xs);
}

.logout-btn:hover {
  color: var(--vermilion) !important;
}

/* ---- Main content ---- */
.main-content {
  flex: 1;
  margin-left: 200px;
  min-height: 100vh;
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
  .sidebar {
    width: 56px;
  }
  .brand-text,
  .nav-item span,
  .user-info,
  .logout-btn span {
    display: none;
  }
  .nav-item {
    justify-content: center;
    padding: var(--space-3);
  }
  .sidebar-brand {
    justify-content: center;
    padding: var(--space-4);
  }
  .sidebar-footer {
    display: flex;
    justify-content: center;
  }
  .main-content {
    margin-left: 56px;
  }
}
</style>
