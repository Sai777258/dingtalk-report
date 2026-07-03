<script setup>
import { computed, ref } from 'vue'
import OverviewTab from '@/components/dashboard/OverviewTab.vue'
import EmployeeTab from '@/components/dashboard/EmployeeTab.vue'
import ProjectTab from '@/components/dashboard/ProjectTab.vue'
import DepartmentTab from '@/components/dashboard/DepartmentTab.vue'

const props = defineProps({
  summary: { type: Object, required: true },
  scopeLabel: { type: String, default: '全公司' },
  canViewEmployee: { type: Boolean, default: false },
  showDepartment: { type: Boolean, default: false },
})

const emit = defineEmits(['navigate'])
const activeView = ref('overview')
const focusedEmployeeId = ref(null)

const alerts = computed(() => props.summary?.alerts || [])
const loadIndex = computed(() => {
  const s = props.summary
  if (!s?.active_employees || !s?.working_days_this_month) return 0
  return Math.round(s.total_hours_this_month / (s.active_employees * s.working_days_this_month) * 10) / 10
})

const diagnosticTone = computed(() => {
  if (alerts.value.some((alert) => alert.level === 'critical')) return 'critical'
  if (alerts.value.some((alert) => alert.level === 'warning')) return 'warning'
  return 'ok'
})

function formatHours(value) {
  const num = Number(value) || 0
  return Number.isInteger(num) ? String(num) : num.toFixed(1)
}

function handleNavigate(payload) {
  if (payload?.view === 'employee' && props.canViewEmployee) {
    focusedEmployeeId.value = payload.employeeId || null
    activeView.value = 'employee'
    return
  }
  emit('navigate', payload)
}

const viewTabs = computed(() => {
  const tabs = [{ name: 'overview', label: '概览检测', hint: '总览' }]
  if (props.canViewEmployee) tabs.push({ name: 'employee', label: '员工样本', hint: '人员' })
  tabs.push({ name: 'project', label: '项目负载', hint: '项目' })
  if (props.showDepartment) tabs.push({ name: 'department', label: '部门分层', hint: '组织' })
  return tabs
})
</script>

<template>
  <div class="hisky-board">
    <section class="hisky-hero" :class="'tone-' + diagnosticTone">
      <div class="hero-copy">
        <span class="hero-eyebrow">HISKY operations scan / {{ scopeLabel }}</span>
        <h2>运营检测台</h2>
        <p>用医学设备式的读数方式观察工作负载、异常提醒和项目投入；下方完整继承经典概览的所有分析模块。</p>
      </div>

      <div class="hero-reading">
        <span class="reading-label">本月总工时</span>
        <strong>{{ formatHours(summary.total_hours_this_month) }}</strong>
        <span>{{ summary.active_employees }} 人 · {{ summary.active_projects }} 项</span>
      </div>

      <div class="hero-vitals">
        <div>
          <span>日报</span>
          <strong>{{ summary.total_reports_this_month }}</strong>
        </div>
        <div>
          <span>人均日负载</span>
          <strong>{{ loadIndex }}h</strong>
        </div>
        <div>
          <span>工作日</span>
          <strong>{{ summary.working_days_this_month }}</strong>
        </div>
      </div>
    </section>

    <section class="overview-shell">
      <div class="shell-header">
        <div>
          <span>完整视角能力</span>
          <strong>概览 / 员工 / 项目 / 部门均继承经典版功能</strong>
        </div>
        <div class="scan-tabs" role="tablist" aria-label="海斯凯尔视角切换">
          <button
            v-for="tab in viewTabs"
            :key="tab.name"
            type="button"
            :class="{ active: activeView === tab.name }"
            @click="activeView = tab.name"
          >
            <span>{{ tab.hint }}</span>
            {{ tab.label }}
          </button>
        </div>
      </div>
      <OverviewTab
        v-if="activeView === 'overview'"
        :summary="summary"
        :can-view-employee="canViewEmployee"
        variant="hisky"
        @navigate="handleNavigate"
      />

      <div v-else-if="activeView === 'employee' && canViewEmployee" class="hisky-perspective">
        <EmployeeTab :focus-employee-id="focusedEmployeeId" variant="hisky" />
      </div>

      <div v-else-if="activeView === 'project'" class="hisky-perspective">
        <ProjectTab variant="hisky" />
      </div>

      <div v-else-if="activeView === 'department' && showDepartment" class="hisky-perspective">
        <DepartmentTab variant="hisky" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.hisky-board {
  --hisky-font-display: "HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;
  --hisky-font-body: "Inter", "HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;
  --hisky-font-mono: "DIN Alternate", "SF Mono", "Consolas", "Courier New", monospace;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  font-family: var(--hisky-font-body);
  font-feature-settings: "tnum";
  color: #15343d;
}

.hisky-hero {
  display: grid;
  grid-template-columns: minmax(280px, 1.35fr) minmax(220px, 0.65fr) minmax(280px, 1fr);
  gap: var(--space-5);
  padding: var(--space-6);
  background:
    radial-gradient(circle at 16% 20%, rgba(11, 132, 145, 0.12), transparent 34%),
    linear-gradient(135deg, #f8fbfb 0%, #eef7f5 100%);
  border: 1px solid rgba(12, 94, 108, 0.12);
  border-radius: var(--radius-md);
  box-shadow: 0 18px 42px rgba(7, 43, 52, 0.12);
}

.tone-warning {
  background:
    radial-gradient(circle at 16% 20%, rgba(232, 163, 86, 0.16), transparent 34%),
    linear-gradient(135deg, #f8fbfb 0%, #eef7f5 100%);
}

.tone-critical {
  background:
    radial-gradient(circle at 16% 20%, rgba(201, 82, 76, 0.14), transparent 34%),
    linear-gradient(135deg, #f8fbfb 0%, #eef7f5 100%);
}

.hero-eyebrow,
.shell-header span {
  display: block;
  font-family: var(--hisky-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0b8491;
}

.hero-copy h2 {
  margin: var(--space-2) 0 var(--space-3);
  font-family: var(--hisky-font-display);
  font-size: 36px;
  line-height: 1.08;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: #12313a;
}

.hero-copy p {
  max-width: 600px;
  font-size: var(--text-sm);
  line-height: 1.7;
  color: rgba(21, 52, 61, 0.64);
}

.hero-reading {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 150px;
  padding: var(--space-5);
  background: #ffffff;
  border-left: 4px solid #18a7a8;
  box-shadow: inset 0 0 0 1px rgba(12, 94, 108, 0.08);
}

.reading-label,
.hero-reading span:last-child {
  font-size: var(--text-xs);
  color: rgba(21, 52, 61, 0.5);
}

.hero-reading strong {
  margin: 4px 0;
  font-family: var(--hisky-font-mono);
  font-size: 50px;
  line-height: 1;
  font-weight: 300;
  color: #0b8491;
}

.hero-vitals {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.hero-vitals div {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(12, 94, 108, 0.1);
}

.hero-vitals span {
  font-size: 11px;
  color: rgba(21, 52, 61, 0.5);
}

.hero-vitals strong {
  margin-top: var(--space-1);
  font-family: var(--hisky-font-mono);
  font-size: 24px;
  font-weight: 500;
  color: #12313a;
}

.overview-shell {
  padding: var(--space-5);
  background: linear-gradient(180deg, #f8fbfb 0%, #eef7f5 100%);
  border: 1px solid rgba(12, 94, 108, 0.12);
  border-radius: var(--radius-md);
  box-shadow: 0 18px 42px rgba(7, 43, 52, 0.1);
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid rgba(12, 94, 108, 0.1);
}

.shell-header strong {
  display: block;
  margin-top: 3px;
  font-size: var(--text-xs);
  font-weight: 500;
  color: rgba(21, 52, 61, 0.58);
}

.scan-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px;
  background: rgba(12, 94, 108, 0.055);
  border: 1px solid rgba(12, 94, 108, 0.1);
  border-radius: var(--radius-sm);
}

.scan-tabs button {
  min-width: 86px;
  padding: 8px 12px;
  border: 0;
  border-radius: 3px;
  background: transparent;
  color: rgba(21, 52, 61, 0.58);
  font-family: var(--hisky-font-body);
  font-size: var(--text-xs);
  cursor: pointer;
  text-align: left;
}

.scan-tabs button span {
  display: block;
  margin-bottom: 2px;
  font-family: var(--hisky-font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: rgba(11, 132, 145, 0.72);
}

.scan-tabs button.active {
  background: #ffffff;
  color: #12313a;
  box-shadow: 0 6px 16px rgba(7, 43, 52, 0.08);
}

.hisky-perspective {
  color: #15343d;
}

.hisky-perspective :deep(.employee-tab),
.hisky-perspective :deep(.project-tab),
.hisky-perspective :deep(.department-tab) {
  background: transparent;
  border: 0;
  border-radius: 0;
  overflow: visible;
}

.hisky-perspective :deep(.tab-header),
.hisky-perspective :deep(.department-layout),
.hisky-perspective :deep(.employee-layout),
.hisky-perspective :deep(.project-layout) {
  border-color: rgba(12, 94, 108, 0.1);
}

.hisky-perspective :deep(.tab-header) {
  padding: 0 0 var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid rgba(12, 94, 108, 0.1);
}

.hisky-perspective :deep(.tab-title),
.hisky-perspective :deep(.detail-title),
.hisky-perspective :deep(.section-label),
.hisky-perspective :deep(.expand-title),
.hisky-perspective :deep(.proj-name),
.hisky-perspective :deep(.emp-name),
.hisky-perspective :deep(.dept-name),
.hisky-perspective :deep(.employee-name) {
  font-family: var(--hisky-font-display);
  color: #12313a;
}

.hisky-perspective :deep(.tab-summary),
.hisky-perspective :deep(.detail-summary),
.hisky-perspective :deep(.proj-code),
.hisky-perspective :deep(.detail-code),
.hisky-perspective :deep(.detail-dept),
.hisky-perspective :deep(.emp-hours),
.hisky-perspective :deep(.entry-hours),
.hisky-perspective :deep(.wt-hours),
.hisky-perspective :deep(.wt-count) {
  color: #0b8491 !important;
}

.hisky-perspective :deep(.employee-list-panel),
.hisky-perspective :deep(.project-list-panel),
.hisky-perspective :deep(.dept-tree-panel),
.hisky-perspective :deep(.employee-detail-panel),
.hisky-perspective :deep(.project-detail-panel),
.hisky-perspective :deep(.dept-detail-panel),
.hisky-perspective :deep(.summary-card),
.hisky-perspective :deep(.breakdown-section),
.hisky-perspective :deep(.detail-header),
.hisky-perspective :deep(.expand-content),
.hisky-perspective :deep(.project-card),
.hisky-perspective :deep(.employee-card) {
  background: #ffffff !important;
  border-color: rgba(12, 94, 108, 0.1) !important;
  box-shadow: 0 10px 24px rgba(7, 43, 52, 0.055);
}

.hisky-perspective :deep(.emp-summary),
.hisky-perspective :deep(.proj-summary),
.hisky-perspective :deep(.dept-summary) {
  background: #ffffff !important;
  border-color: rgba(12, 94, 108, 0.1) !important;
  box-shadow: 0 10px 24px rgba(7, 43, 52, 0.055);
}

.hisky-perspective :deep(.summary-kpi),
.hisky-perspective :deep(.proj-block),
.hisky-perspective :deep(.work-type-row),
.hisky-perspective :deep(.employee-row),
.hisky-perspective :deep(.entry-row),
.hisky-perspective :deep(.project-summary-card),
.hisky-perspective :deep(.metric-card) {
  background: #f8fbfb !important;
  border-color: rgba(12, 94, 108, 0.09) !important;
}

.hisky-perspective :deep(.expand-content) {
  background: #f8fbfb !important;
}

.hisky-perspective :deep(.kpi-val),
.hisky-perspective :deep(.stat-val),
.hisky-perspective :deep(.summary-value),
.hisky-perspective :deep(.total-hours) {
  font-family: var(--hisky-font-mono);
  color: #0b8491 !important;
}

.hisky-perspective :deep(.kpi-label),
.hisky-perspective :deep(.proj-meta),
.hisky-perspective :deep(.emp-dept),
.hisky-perspective :deep(.entry-date),
.hisky-perspective :deep(.stat-label),
.hisky-perspective :deep(.summary-label),
.hisky-perspective :deep(.expand-count) {
  color: rgba(21, 52, 61, 0.5) !important;
}

.hisky-perspective :deep(.entry-desc) {
  color: rgba(21, 52, 61, 0.72) !important;
}

.hisky-perspective :deep(.employee-list),
.hisky-perspective :deep(.work-type-list),
.hisky-perspective :deep(.entry-list) {
  color: #15343d !important;
}

.hisky-perspective :deep(.entry-list) {
  border-top-color: rgba(12, 94, 108, 0.08) !important;
}

.hisky-perspective :deep(.work-type-row),
.hisky-perspective :deep(.proj-block),
.hisky-perspective :deep(.employee-card),
.hisky-perspective :deep(.project-card) {
  color: #15343d !important;
}

.hisky-perspective :deep(.emp-header),
.hisky-perspective :deep(.proj-header) {
  color: #15343d !important;
}

.hisky-perspective :deep(.employee-list-panel),
.hisky-perspective :deep(.project-list-panel),
.hisky-perspective :deep(.dept-tree-panel) {
  border-right-color: rgba(12, 94, 108, 0.1);
}

.hisky-perspective :deep(.loading-state),
.hisky-perspective :deep(.error-state),
.hisky-perspective :deep(.empty-hint) {
  color: rgba(21, 52, 61, 0.46);
}

.hisky-perspective :deep(.el-input__wrapper) {
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(12, 94, 108, 0.12) inset;
}

.hisky-perspective :deep(.el-input__inner) {
  color: #12313a;
}

.hisky-perspective :deep(.el-table) {
  --el-table-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;
  --el-table-header-bg-color: rgba(12, 94, 108, 0.055);
  --el-table-row-hover-bg-color: rgba(24, 167, 168, 0.07);
  --el-table-current-row-bg-color: rgba(24, 167, 168, 0.09);
  --el-table-expanded-cell-bg-color: #f8fbfb;
  --el-table-text-color: #15343d;
  --el-table-header-text-color: rgba(21, 52, 61, 0.58);
  --el-table-border-color: rgba(12, 94, 108, 0.08);
  background: #ffffff !important;
  color: #15343d !important;
}

.hisky-perspective :deep(.el-table th.el-table__cell) {
  background: rgba(12, 94, 108, 0.055) !important;
  color: rgba(21, 52, 61, 0.58) !important;
}

.hisky-perspective :deep(.el-table td.el-table__cell) {
  background: #ffffff !important;
  border-bottom-color: rgba(12, 94, 108, 0.08);
  color: #15343d !important;
}

.hisky-perspective :deep(.el-table__expanded-cell),
.hisky-perspective :deep(.el-table__expanded-cell[class*=cell]) {
  background: #f8fbfb !important;
}

.hisky-perspective :deep(.el-table__body tr.current-row > td.el-table__cell),
.hisky-perspective :deep(.el-table__body tr.hover-row > td.el-table__cell),
.hisky-perspective :deep(.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell) {
  background: rgba(24, 167, 168, 0.07) !important;
}

.hisky-perspective :deep(.el-tree) {
  --el-tree-node-hover-bg-color: rgba(24, 167, 168, 0.07);
  --el-tree-text-color: #15343d;
  background: #ffffff !important;
  color: #15343d !important;
}

.hisky-perspective :deep(.el-tree-node__content) {
  color: #15343d !important;
}

.hisky-perspective :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(24, 167, 168, 0.1) !important;
  color: #0b8491 !important;
}

.hisky-perspective :deep(.el-tree-node__expand-icon),
.hisky-perspective :deep(.tree-node),
.hisky-perspective :deep(.tree-label) {
  color: #12313a !important;
}

.hisky-perspective :deep(.tree-node) {
  font-family: var(--hisky-font-body);
  font-weight: 600;
}

.hisky-perspective :deep(.tree-meta) {
  font-family: var(--hisky-font-mono);
  font-weight: 500;
  color: #0b8491 !important;
}

.hisky-perspective :deep(.type-tag),
.hisky-perspective :deep(.type-tag-sm),
.hisky-perspective :deep(.entry-type-tag),
.hisky-perspective :deep(.project-tag) {
  background: rgba(24, 167, 168, 0.09) !important;
  border-color: rgba(11, 132, 145, 0.26) !important;
  color: #1f5360 !important;
  font-weight: 600;
}

.hisky-perspective :deep(.hours-bar),
.hisky-perspective :deep(.summary-bar),
.hisky-perspective :deep(.project-bar) {
  background: rgba(12, 94, 108, 0.08);
}

.hisky-perspective :deep(.hours-fill),
.hisky-perspective :deep(.summary-fill),
.hisky-perspective :deep(.project-fill) {
  background: linear-gradient(90deg, #18a7a8, #8bd7ca);
}

@media (max-width: 1080px) {
  .hisky-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hisky-hero,
  .overview-shell {
    padding: var(--space-4);
  }

  .hero-copy h2 {
    font-size: 28px;
  }

  .hero-vitals {
    grid-template-columns: 1fr;
  }

  .shell-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .scan-tabs {
    width: 100%;
  }

  .scan-tabs button {
    flex: 1;
  }
}
</style>
