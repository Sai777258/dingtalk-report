<script setup>
/**
 * ProjectTab — per-project view: employees, work types, hours.
 *
 * Shows a table of projects with expandable rows
 * that reveal each project's contributing employees.
 */
import { ref } from 'vue'
import { getDashboardByView } from '@/api/dashboard'

const loading = ref(true)
const error = ref('')
const data = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getDashboardByView('project')
  } catch (e) {
    error.value = e.response?.data?.detail || '加载项目数据失败'
  } finally {
    loading.value = false
  }
}

const typeColors = {
  development: '#C8A45C',
  testing: '#4A90A4',
  meeting: '#7D9B76',
  documentation: '#8B7AA0',
  design: '#D4695A',
  other: 'rgba(255,255,255,0.3)',
}

function typeTagStyle(type) {
  return {
    background: (typeColors[type] || typeColors.other) + '22',
    borderColor: typeColors[type] || typeColors.other,
    color: typeColors[type] || typeColors.other,
  }
}

// Max hours for progress bar calculation
function maxEmpHours(proj) {
  if (!proj.employees?.length) return 1
  return Math.max(...proj.employees.map((e) => e.hours))
}

load()
</script>

<template>
  <div class="project-tab">
    <div v-if="error" class="error-state">
      <p>{{ error }}</p>
      <el-button size="small" @click="load">重试</el-button>
    </div>

    <div v-else-if="loading" class="loading-state">
      <p>加载中…</p>
    </div>

    <template v-else-if="data">
      <div class="tab-header">
        <h3 class="tab-title">
          项目工时概览
          <span class="tab-summary">{{ data.project_count }} 个项目 · {{ data.total_hours }}h</span>
        </h3>
      </div>

      <el-table
        :data="data.projects"
        row-key="project_id"
        size="small"
        style="width: 100%"
      >
        <el-table-column type="expand">
          <template #default="{ row: proj }">
            <div class="expand-content">
              <h4 class="expand-title">
                {{ proj.project_name }} 参与人员
                <span class="expand-count">{{ proj.employee_count }} 人</span>
              </h4>
              <div class="employee-list">
                <div
                  v-for="emp in proj.employees"
                  :key="emp.employee_id"
                  class="employee-row"
                >
                  <div class="emp-info">
                    <span class="emp-name">{{ emp.employee_name }}</span>
                    <span class="emp-dept">{{ emp.department_name }}</span>
                  </div>
                  <div class="emp-hours-bar">
                    <div class="bar-track">
                      <div
                        class="bar-fill"
                        :style="{
                          width: (emp.hours / maxEmpHours(proj)) * 100 + '%',
                          background: typeColors.development,
                        }"
                      />
                    </div>
                    <span class="bar-value">{{ emp.hours }}h</span>
                  </div>
                  <div class="emp-types">
                    <span
                      v-for="wt in emp.work_types"
                      :key="wt.type"
                      class="type-tag"
                      :style="typeTagStyle(wt.type)"
                    >
                      {{ wt.display }} {{ wt.hours }}h
                    </span>
                  </div>
                </div>
                <div v-if="!proj.employees.length" class="empty-hint">暂无人员数据</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="project_name" label="项目名" min-width="140" />
        <el-table-column prop="project_code" label="代号" width="100" />
        <el-table-column prop="total_hours" label="总工时 (h)" width="110" sortable />
        <el-table-column prop="employee_count" label="参与人数" width="90" sortable />
      </el-table>
    </template>
  </div>
</template>

<style scoped>
.project-tab {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.loading-state,
.error-state {
  padding: var(--space-10);
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
}

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.tab-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.5px;
  margin: 0;
}

.tab-summary {
  font-weight: 300;
  color: var(--brass);
  margin-left: var(--space-3);
  font-size: var(--text-xs);
}

/* Expand */
.expand-content {
  padding: var(--space-4) var(--space-6) var(--space-5);
  background: rgba(0, 0, 0, 0.15);
}

.expand-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 var(--space-3);
}

.expand-count {
  font-weight: 300;
  color: var(--brass);
  font-size: var(--text-xs);
  margin-left: var(--space-2);
}

.employee-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.employee-row {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.emp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 90px;
}

.emp-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.emp-dept {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.emp-hours-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 120px;
}

.bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
  opacity: 0.7;
}

.bar-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--brass);
  width: 36px;
  text-align: right;
}

.emp-types {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.type-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  border: 1px solid;
}

.empty-hint {
  color: rgba(255, 255, 255, 0.2);
  font-size: var(--text-sm);
  padding: var(--space-3);
}

:deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: var(--text-xs);
}
</style>

<!-- Non-scoped: kill ALL table hover, focus, and highlight effects -->
<style>
/* ---- CSS variables ---- */
.project-tab .el-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: rgba(255, 255, 255, 0.7);
  --el-table-header-text-color: rgba(255, 255, 255, 0.4);
  --el-table-row-hover-bg-color: transparent;
  --el-table-current-row-bg-color: transparent;
  --el-table-expanded-cell-bg-color: transparent;
}

/* ---- No hover background (JS classes + CSS pseudo) ---- */
.project-tab .el-table__body tr.hover-row > td.el-table__cell,
.project-tab .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.project-tab .el-table__body tr.hover-row.current-row > td.el-table__cell,
.project-tab .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.project-tab .el-table__body tr:hover > td.el-table__cell,
.project-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

/* ---- Kill ALL focus outlines & box-shadows inside table ---- */
.project-tab .el-table__body *:focus,
.project-tab .el-table__body *:focus-visible,
.project-tab .el-table__header *:focus,
.project-tab .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* ---- Also target the tr/td focus directly (sometimes * doesn't catch tr) ---- */
.project-tab .el-table__body tr,
.project-tab .el-table__body td,
.project-tab .el-table__body th {
  outline: none !important;
}
.project-tab .el-table__body tr:focus,
.project-tab .el-table__body tr:focus-visible,
.project-tab .el-table__body td:focus,
.project-tab .el-table__body td:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* ---- No bg transition ---- */
.project-tab .el-table__body td.el-table__cell {
  transition: none !important;
}
</style>
