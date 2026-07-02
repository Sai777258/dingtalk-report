<script setup>
/**
 * EmployeeTab — per-employee view: projects, work types, hours.
 *
 * Shows a searchable table of employees with expandable rows
 * that reveal each employee's project breakdown.
 */
import { ref, computed } from 'vue'
import { getDashboardByView } from '@/api/dashboard'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const search = ref('')

// Load data
async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getDashboardByView('employee')
  } catch (e) {
    error.value = e.response?.data?.detail || '加载员工数据失败'
  } finally {
    loading.value = false
  }
}

// Filtered employees
const employees = computed(() => {
  if (!data.value?.employees) return []
  const q = search.value.toLowerCase()
  if (!q) return data.value.employees
  return data.value.employees.filter(
    (e) =>
      e.employee_name.toLowerCase().includes(q) ||
      e.department_name.toLowerCase().includes(q)
  )
})

// Work type colour tags
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

load()
</script>

<template>
  <div class="employee-tab">
    <!-- Error -->
    <div v-if="error" class="error-state">
      <p>{{ error }}</p>
      <el-button size="small" @click="load">重试</el-button>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="loading-state">
      <p>加载中…</p>
    </div>

    <!-- Content -->
    <template v-else-if="data">
      <!-- Header -->
      <div class="tab-header">
        <h3 class="tab-title">
          员工工时概览
          <span class="tab-summary">{{ data.employee_count }} 人 · {{ data.total_hours }}h</span>
        </h3>
        <el-input
          v-model="search"
          placeholder="搜索员工姓名或部门…"
          clearable
          size="small"
          style="width: 260px"
          class="search-input"
        />
      </div>

      <!-- Employee table -->
      <el-table
        :data="employees"
        row-key="employee_id"
        size="small"
        style="width: 100%"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <h4 class="expand-title">
                {{ row.employee_name }} 参与的项目
                <span class="expand-count">{{ row.project_count }} 个项目</span>
              </h4>
              <div class="project-grid">
                <div
                  v-for="proj in row.projects"
                  :key="proj.project_id"
                  class="project-card"
                >
                  <div class="proj-header">
                    <span class="proj-name">{{ proj.project_name }}</span>
                    <span class="proj-code" v-if="proj.project_code">{{ proj.project_code }}</span>
                  </div>
                  <div class="proj-hours">
                    <span class="proj-hours-value">{{ proj.total_hours }}h</span>
                    <span class="proj-entries">{{ proj.entry_count }} 条</span>
                  </div>
                  <div class="work-types">
                    <span
                      v-for="wt in proj.work_types"
                      :key="wt.type"
                      class="type-tag"
                      :style="typeTagStyle(wt.type)"
                    >
                      {{ wt.display }} {{ wt.hours }}h
                    </span>
                  </div>
                </div>
                <div v-if="!row.projects.length" class="empty-hint">暂无项目</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="employee_name" label="姓名" min-width="100" sortable />
        <el-table-column prop="department_name" label="部门" min-width="120" />
        <el-table-column prop="total_hours" label="总工时 (h)" width="110" sortable />
        <el-table-column prop="project_count" label="项目数" width="80" sortable />
      </el-table>
    </template>
  </div>
</template>

<style scoped>
.employee-tab {
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

/* Expand row */
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

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-3);
}

.project-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
}

.proj-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.proj-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.proj-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.3);
}

.proj-hours {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.proj-hours-value {
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: 300;
  color: var(--brass);
}

.proj-entries {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.35);
}

.work-types {
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
.employee-tab .el-table {
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
.employee-tab .el-table__body tr.hover-row > td.el-table__cell,
.employee-tab .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.employee-tab .el-table__body tr.hover-row.current-row > td.el-table__cell,
.employee-tab .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.employee-tab .el-table__body tr:hover > td.el-table__cell,
.employee-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

/* ---- Kill ALL focus outlines & box-shadows inside table ---- */
.employee-tab .el-table__body *:focus,
.employee-tab .el-table__body *:focus-visible,
.employee-tab .el-table__header *:focus,
.employee-tab .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* ---- Also target the tr/td focus directly (sometimes * doesn't catch tr) ---- */
.employee-tab .el-table__body tr,
.employee-tab .el-table__body td,
.employee-tab .el-table__body th {
  outline: none !important;
}
.employee-tab .el-table__body tr:focus,
.employee-tab .el-table__body tr:focus-visible,
.employee-tab .el-table__body td:focus,
.employee-tab .el-table__body td:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* ---- No bg transition ---- */
.employee-tab .el-table__body td.el-table__cell {
  transition: none !important;
}
</style>
