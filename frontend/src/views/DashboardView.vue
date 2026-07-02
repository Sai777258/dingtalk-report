<script setup>
/**
 * DashboardView — multi-perspective analytics dashboard.
 *
 * KPI cards are shared across all views. Four tabs provide different
 * data perspectives: Overview, Employee, Project, Department.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getDashboard } from '@/api/dashboard'
import OverviewTab from '@/components/dashboard/OverviewTab.vue'
import EmployeeTab from '@/components/dashboard/EmployeeTab.vue'
import ProjectTab from '@/components/dashboard/ProjectTab.vue'
import DepartmentTab from '@/components/dashboard/DepartmentTab.vue'

const auth = useAuthStore()
const router = useRouter()

// ---- State ----
const loading = ref(true)
const error = ref('')
const summary = ref(null)
const activeTab = ref('overview')

// ---- Computed ----
const scopeLabel = computed(() => {
  if (auth.isAdmin) return '全公司'
  if (auth.isDeptManagerL1) return '全公司'
  if (auth.isDeptManagerL2) return auth.user?.department?.name || '部门'
  if (auth.isProjectManager) return '负责项目'
  return '个人'
})

const showEmployeeTab = computed(() => !auth.isEmployee)
const showDepartmentTab = computed(() => auth.isAdmin || auth.isDeptManagerL1 || auth.isDeptManagerL2)

// ---- Load summary (KPI + overview charts) ----
async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    summary.value = await getDashboard()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载仪表盘数据失败'
  } finally {
    loading.value = false
  }
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <div class="dashboard">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="brand-mark" />
      <p>加载中…</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <el-button size="small" @click="loadDashboard">重试</el-button>
    </div>

    <!-- Content -->
    <template v-else-if="summary">
      <!-- ---- KPI Cards (shared) ---- -->
      <div class="kpi-scope">
        <span class="scope-badge">{{ scopeLabel }}</span>
      </div>
      <div class="kpi-row">
        <div class="kpi-card">
          <span class="kpi-value">{{ summary.total_hours_this_month }}</span>
          <span class="kpi-label">本月总工时 (h)</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">{{ summary.total_reports_this_month }}</span>
          <span class="kpi-label">本月日志数</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">{{ summary.active_projects }}</span>
          <span class="kpi-label">活跃项目</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">{{ summary.active_employees }}</span>
          <span class="kpi-label">活跃人员</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">{{ summary.avg_daily_hours }}</span>
          <span class="kpi-label">日均工时 (h)</span>
        </div>
      </div>

      <!-- ---- Tabs ---- -->
      <el-tabs v-model="activeTab" class="dash-tabs">
        <el-tab-pane label="概览" name="overview">
          <OverviewTab :summary="summary" />
        </el-tab-pane>

        <el-tab-pane v-if="showEmployeeTab" label="员工视角" name="employee">
          <Suspense>
            <EmployeeTab />
            <template #fallback>
              <div class="tab-loading">加载中…</div>
            </template>
          </Suspense>
        </el-tab-pane>

        <el-tab-pane label="项目视角" name="project">
          <Suspense>
            <ProjectTab />
            <template #fallback>
              <div class="tab-loading">加载中…</div>
            </template>
          </Suspense>
        </el-tab-pane>

        <el-tab-pane v-if="showDepartmentTab" label="部门视角" name="department">
          <Suspense>
            <DepartmentTab />
            <template #fallback>
              <div class="tab-loading">加载中…</div>
            </template>
          </Suspense>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  padding: var(--space-6);
  max-width: 1280px;
  margin: 0 auto;
}

/* ---- Loading / Error ---- */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: var(--space-4);
  color: rgba(255, 255, 255, 0.5);
}

.brand-mark {
  width: 28px;
  height: 3px;
  background: var(--brass);
  border-radius: 2px;
}

.tab-loading {
  padding: var(--space-8);
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
}

/* ---- Scope badge ---- */
.kpi-scope {
  display: flex;
  align-items: center;
  margin-bottom: var(--space-3);
}

.scope-badge {
  display: inline-block;
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 500;
  color: var(--brass);
  border: 1px solid rgba(200, 164, 92, 0.25);
  border-radius: 100px;
  letter-spacing: 0.5px;
}

/* ---- KPI cards ---- */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.kpi-card {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: var(--space-5) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 300;
  color: var(--brass);
}

.kpi-label {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.4);
}

/* ---- Tabs ---- */
:deep(.el-tabs__header) {
  margin-bottom: var(--space-4);
}

:deep(.el-tabs__nav-wrap::after) {
  background: rgba(255, 255, 255, 0.06);
}

:deep(.el-tabs__item) {
  color: rgba(255, 255, 255, 0.4);
  font-size: var(--text-sm);
  height: 40px;
  line-height: 40px;
}

:deep(.el-tabs__item.is-active) {
  color: var(--brass);
}

:deep(.el-tabs__active-bar) {
  background: var(--brass);
}

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 540px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
