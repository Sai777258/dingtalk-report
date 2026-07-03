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
import HiskyDashboard from '@/components/dashboard/HiskyDashboard.vue'
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
const focusedEmployeeId = ref(null)
const uiVersion = ref('classic')

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

// ---- MoM deltas ----
const hoursMoM = computed(() => {
  if (!summary.value?.total_hours_last_month) return null
  return Math.round(
    (summary.value.total_hours_this_month - summary.value.total_hours_last_month) /
      summary.value.total_hours_last_month * 100
  )
})
const reportsMoM = computed(() => {
  if (!summary.value?.total_reports_last_month) return null
  return Math.round(
    (summary.value.total_reports_this_month - summary.value.total_reports_last_month) /
      summary.value.total_reports_last_month * 100
  )
})

// Per-employee daily average: total / (employees × working days)
const avgDailyPerEmployee = computed(() => {
  const s = summary.value
  if (!s || !s.active_employees || !s.working_days_this_month || !s.total_hours_this_month) return null
  const val = s.total_hours_this_month / (s.active_employees * s.working_days_this_month)
  return Math.round(val * 10) / 10
})

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

function handleOverviewNavigate(payload) {
  if (payload?.view === 'employee' && showEmployeeTab.value) {
    focusedEmployeeId.value = payload.employeeId || null
    uiVersion.value = 'classic'
    activeTab.value = 'employee'
  }
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
      <div class="version-bar">
        <div>
          <span class="version-kicker">界面对比</span>
          <strong>{{ uiVersion === 'classic' ? '经典仪表盘' : '海斯凯尔版运营检测台' }}</strong>
        </div>
        <div class="version-switch" role="group" aria-label="切换界面版本">
          <button
            type="button"
            :class="{ active: uiVersion === 'classic' }"
            @click="uiVersion = 'classic'"
          >
            经典版
          </button>
          <button
            type="button"
            :class="{ active: uiVersion === 'hisky' }"
            @click="uiVersion = 'hisky'"
          >
            海斯凯尔版
          </button>
        </div>
      </div>

      <HiskyDashboard
        v-if="uiVersion === 'hisky'"
        :summary="summary"
        :scope-label="scopeLabel"
        :can-view-employee="showEmployeeTab"
        :show-department="showDepartmentTab"
        @navigate="handleOverviewNavigate"
      />

      <!-- ---- KPI Cards (shared) ---- -->
      <div v-if="uiVersion === 'classic'" class="kpi-scope">
        <span class="scope-badge">{{ scopeLabel }}</span>
      </div>
      <div v-if="uiVersion === 'classic'" class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-value">{{ summary.total_hours_this_month }}</span>
            <span v-if="hoursMoM !== null" class="kpi-delta" :class="hoursMoM >= 0 ? 'up' : 'down'">
              {{ hoursMoM >= 0 ? '↑' : '↓' }}{{ Math.abs(hoursMoM) }}%
            </span>
          </div>
          <span class="kpi-label">本月总工时 (h)</span>
        </div>
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-value">{{ summary.total_reports_this_month }}</span>
            <span v-if="reportsMoM !== null" class="kpi-delta" :class="reportsMoM >= 0 ? 'up' : 'down'">
              {{ reportsMoM >= 0 ? '↑' : '↓' }}{{ Math.abs(reportsMoM) }}%
            </span>
          </div>
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
          <span class="kpi-value">{{ avgDailyPerEmployee ?? summary.avg_daily_hours }}</span>
          <span class="kpi-label">人均日工时 (h)</span>
        </div>
      </div>

      <!-- ---- Tabs ---- -->
      <el-tabs v-if="uiVersion === 'classic'" v-model="activeTab" class="dash-tabs">
        <el-tab-pane label="概览" name="overview">
          <OverviewTab
            :summary="summary"
            :can-view-employee="showEmployeeTab"
            @navigate="handleOverviewNavigate"
          />
        </el-tab-pane>

        <el-tab-pane v-if="showEmployeeTab" label="员工视角" name="employee">
          <Suspense>
            <EmployeeTab :focus-employee-id="focusedEmployeeId" />
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

/* ---- Version switch ---- */
.version-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  padding: var(--space-4) var(--space-5);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--radius-md);
}

.version-kicker {
  display: block;
  margin-bottom: 2px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.34);
}

.version-bar strong {
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.76);
}

.version-switch {
  display: inline-flex;
  padding: 3px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
}

.version-switch button {
  min-width: 86px;
  padding: 7px 12px;
  border: 0;
  border-radius: 3px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  cursor: pointer;
}

.version-switch button.active {
  background: var(--paper);
  color: #12313a;
}

.version-switch button:focus-visible {
  outline: 2px solid var(--brass);
  outline-offset: 2px;
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

.kpi-top {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 300;
  color: var(--brass);
}

.kpi-delta {
  font-size: 11px;
  font-weight: 500;
}

.kpi-delta.up {
  color: var(--sage);
}

.kpi-delta.down {
  color: var(--vermilion);
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
  .version-bar {
    align-items: stretch;
    flex-direction: column;
  }
  .version-switch {
    width: 100%;
  }
  .version-switch button {
    flex: 1;
  }
}
</style>
