<script setup>
/**
 * EmployeeTab — per-employee view with two-panel layout.
 *
 * Left panel:  searchable employee list (name, department, hours, project count)
 * Right panel: selected employee detail:
 *              - EmployeeSummary (KPI cards + work type distribution)
 *              - Project breakdown table with expandable work type rows
 *              - "View reports" drawer via EmployeeReportDrawer
 */
import { ref, computed } from 'vue'
import { getDashboardByView } from '@/api/dashboard'
import { typeTagStyle } from '@/utils/typeColors'
import EmployeeSummary from '@/components/dashboard/EmployeeSummary.vue'
import EmployeeReportDrawer from '@/components/dashboard/EmployeeReportDrawer.vue'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const selectedEmployeeId = ref(null)
const search = ref('')

// Report drawer
const reportDrawerVisible = ref(false)
const reportDrawerEmployee = ref({ username: '', name: '' })

function openReportDrawer(emp) {
  reportDrawerEmployee.value = {
    username: emp.employee_username,
    name: emp.employee_name,
  }
  reportDrawerVisible.value = true
}

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

const selectedEmployee = computed(() => {
  if (!selectedEmployeeId.value || !data.value?.employees) return null
  return data.value.employees.find(e => e.employee_id === selectedEmployeeId.value) || null
})

function handleEmployeeClick(row) {
  selectedEmployeeId.value = row.employee_id
}

function autoSelect() {
  if (employees.value.length && !selectedEmployeeId.value) {
    selectedEmployeeId.value = employees.value[0].employee_id
  }
}

load()
</script>

<template>
  <div class="employee-tab">
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
          员工工时概览
          <span class="tab-summary">{{ data.employee_count }} 人 · {{ data.total_hours }}h</span>
        </h3>
        <el-input
          v-model="search"
          placeholder="搜索员工姓名或部门…"
          clearable
          size="small"
          style="width: 240px"
        />
      </div>

      <div class="employee-layout">
        <!-- Left: employee list -->
        <div class="employee-list-panel">
          <el-table
            :data="employees"
            row-key="employee_id"
            highlight-current-row
            size="small"
            style="width: 100%"
            @row-click="handleEmployeeClick"
            @current-change="autoSelect"
          >
            <el-table-column prop="employee_name" label="姓名" min-width="90" show-overflow-tooltip />
            <el-table-column prop="department_name" label="部门" min-width="100" show-overflow-tooltip />
            <el-table-column prop="total_hours" label="工时" width="65" sortable />
            <el-table-column prop="project_count" label="项目" width="55" sortable />
          </el-table>
        </div>

        <!-- Right: selected employee detail -->
        <div class="employee-detail-panel">
          <template v-if="selectedEmployee">
            <!-- Employee header -->
            <div class="detail-header">
              <div class="detail-header-left">
                <h4 class="detail-title">
                  {{ selectedEmployee.employee_name }}
                  <span class="detail-dept">{{ selectedEmployee.department_name }}</span>
                </h4>
                <span class="detail-summary">{{ selectedEmployee.total_hours }}h</span>
              </div>
              <el-button
                size="small"
                type="primary"
                plain
                @click="openReportDrawer(selectedEmployee)"
              >
                查看日志
              </el-button>
            </div>

            <!-- KPI cards + work type distribution -->
            <EmployeeSummary :employee="selectedEmployee" />

            <!-- Project breakdown table -->
            <div class="breakdown-section" v-if="selectedEmployee.projects?.length">
              <h5 class="section-label">按项目明细</h5>
              <el-table
                :data="selectedEmployee.projects"
                row-key="project_id"
                :key="selectedEmployeeId"
                size="small"
                style="width: 100%"
              >
                <el-table-column type="expand">
                  <template #default="{ row: projRow }">
                    <div class="expand-content">
                      <h4 class="expand-title">
                        {{ projRow.project_name }} 工作类型
                        <span class="expand-count">{{ projRow.work_types?.length || 0 }} 种</span>
                      </h4>
                      <div class="work-type-list">
                        <div
                          v-for="wt in projRow.work_types"
                          :key="wt.type"
                          class="work-type-row"
                        >
                          <span class="type-tag" :style="typeTagStyle(wt.type)">{{ wt.display }}</span>
                          <span class="wt-hours">{{ wt.hours }}h</span>
                        </div>
                      </div>
                      <div v-if="!projRow.work_types?.length" class="empty-hint">暂无工作类型数据</div>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="项目名" min-width="140">
                  <template #default="{ row }">
                    <span class="proj-name">{{ row.project_name }}</span>
                    <span class="proj-code" v-if="row.project_code">{{ row.project_code }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="total_hours" label="工时 (h)" width="90" sortable />
                <el-table-column label="工作类型" width="80">
                  <template #default="{ row }">
                    <span class="wt-count">{{ row.work_types?.length || 0 }} 种</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-else class="empty-hint" style="padding: var(--space-6);">
              该员工暂无项目数据
            </div>
          </template>

          <div v-else class="empty-hint" style="padding: var(--space-10); text-align: center;">
            请选择左侧员工
          </div>
        </div>
      </div>

      <!-- Employee report drawer -->
      <EmployeeReportDrawer
        v-model="reportDrawerVisible"
        :employee-username="reportDrawerEmployee.username"
        :employee-name="reportDrawerEmployee.name"
      />
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

/* ---- Layout ---- */
.employee-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 400px;
}

.employee-list-panel {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: var(--space-2);
  overflow-y: auto;
  max-height: 600px;
}

.employee-detail-panel {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
  max-height: 600px;
}

/* ---- Detail header ---- */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.detail-header-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.detail-title {
  font-size: var(--text-base);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.detail-dept {
  font-size: var(--text-xs);
  font-weight: 300;
  color: rgba(255, 255, 255, 0.35);
  margin-left: var(--space-2);
}

.detail-summary {
  font-weight: 300;
  color: var(--brass);
  font-size: var(--text-xs);
}

/* ---- Section ---- */
.breakdown-section {
  margin-top: var(--space-2);
}

.section-label {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.5px;
  margin: 0 0 var(--space-2);
  text-transform: uppercase;
}

/* ---- Expand content ---- */
.expand-content {
  padding: var(--space-4) var(--space-5);
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

.work-type-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.work-type-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) 0;
}

.wt-hours {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--brass);
}

/* ---- Project name + code ---- */
.proj-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.proj-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.3);
  margin-left: var(--space-2);
}

.wt-count {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.4);
}

/* ---- Tags ---- */
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
}

:deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: var(--text-xs);
}
</style>

<!-- Non-scoped: dark theme table overrides -->
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

/* ---- No hover background ---- */
.employee-tab .el-table__body tr.hover-row > td.el-table__cell,
.employee-tab .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.employee-tab .el-table__body tr.hover-row.current-row > td.el-table__cell,
.employee-tab .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.employee-tab .el-table__body tr:hover > td.el-table__cell,
.employee-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

/* ---- Kill ALL focus outlines ---- */
.employee-tab .el-table__body *:focus,
.employee-tab .el-table__body *:focus-visible,
.employee-tab .el-table__header *:focus,
.employee-tab .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

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

/* ---- Highlight current row in left panel ---- */
.employee-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: rgba(200, 164, 92, 0.08) !important;
}
</style>
