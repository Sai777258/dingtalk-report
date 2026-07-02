<script setup>
/**
 * DepartmentTab — department tree with summary + employee detail.
 *
 * Left panel:  department tree (el-tree)
 * Right panel: department summary (KPI + project bars + work types)
 *              + employee table with expandable project cards
 */
import { ref, computed } from 'vue'
import { getDashboardByView } from '@/api/dashboard'
import { typeTagStyle } from '@/utils/typeColors'
import DepartmentSummary from '@/components/dashboard/DepartmentSummary.vue'
import EmployeeReportDrawer from '@/components/dashboard/EmployeeReportDrawer.vue'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const activeDeptId = ref(null)

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
    data.value = await getDashboardByView('department')
  } catch (e) {
    error.value = e.response?.data?.detail || '加载部门数据失败'
  } finally {
    loading.value = false
  }
}

// Flatten department tree for el-tree
function buildTreeNodes(departments, parentId = null) {
  return departments.map((d) => ({
    id: d.department_id,
    label: d.department_name,
    hours: d.total_hours,
    employeeCount: d.employees?.length || 0,
    children: d.children?.length ? buildTreeNodes(d.children, d.department_id) : [],
  }))
}

const treeData = computed(() => {
  if (!data.value?.departments) return []
  return buildTreeNodes(data.value.departments)
})

// Currently selected department
const selectedDept = computed(() => {
  if (!activeDeptId.value || !data.value?.departments) return null
  return findDept(data.value.departments, activeDeptId.value)
})

function findDept(departments, id) {
  for (const d of departments) {
    if (d.department_id === id) return d
    if (d.children?.length) {
      const found = findDept(d.children, id)
      if (found) return found
    }
  }
  return null
}

function handleNodeClick(node) {
  activeDeptId.value = node.id
}

// Auto-select first department
function autoSelect() {
  if (data.value?.departments?.length && !activeDeptId.value) {
    activeDeptId.value = data.value.departments[0].department_id
  }
}

load()
</script>

<template>
  <div class="dept-tab">
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
          部门工时概览
          <span class="tab-summary">{{ data.total_hours }}h</span>
        </h3>
      </div>

      <div class="dept-layout">
        <!-- Left: department tree -->
        <div class="dept-tree-panel">
          <el-tree
            :data="treeData"
            :props="{ children: 'children', label: 'label' }"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="handleNodeClick"
            @current-change="autoSelect"
          >
            <template #default="{ data: node }">
              <span class="tree-node">
                <span class="tree-label">{{ node.label }}</span>
                <span class="tree-meta">{{ node.hours }}h · {{ node.employeeCount }}人</span>
              </span>
            </template>
          </el-tree>
        </div>

        <!-- Right: selected department detail -->
        <div class="dept-detail-panel">
          <template v-if="selectedDept">
            <!-- Department header -->
            <h4 class="detail-title">
              {{ selectedDept.department_name }}
              <span class="detail-summary">
                {{ selectedDept.total_hours }}h · {{ selectedDept.employees.length }} 人
              </span>
            </h4>

            <!-- 📊 Department summary -->
            <DepartmentSummary
              :employees="selectedDept.employees"
              :total-hours="selectedDept.total_hours"
            />

            <!-- 📋 Employee detail table -->
            <div class="employee-section" v-if="selectedDept.employees.length">
              <h5 class="section-label">员工明细</h5>
              <el-table
                :data="selectedDept.employees"
                row-key="employee_id"
                size="small"
                style="width: 100%"
              >
                <el-table-column type="expand">
                  <template #default="{ row: emp }">
                    <div class="expand-content">
                      <h4 class="expand-title">
                        {{ emp.employee_name }} 参与的项目
                        <span class="expand-count">{{ emp.projects?.length || 0 }} 个项目</span>
                      </h4>
                      <div class="project-grid">
                        <div
                          v-for="proj in emp.projects"
                          :key="proj.project_id"
                          class="project-card"
                        >
                          <div class="proj-header">
                            <span class="proj-name">{{ proj.project_name }}</span>
                            <span class="proj-hours">{{ proj.hours }}h</span>
                          </div>

                          <!-- Work types -->
                          <div class="work-types" v-if="proj.work_types?.length">
                            <span
                              v-for="wt in proj.work_types"
                              :key="wt.type"
                              class="type-tag"
                              :style="typeTagStyle(wt.type)"
                            >
                              {{ wt.display }} {{ wt.hours }}h
                            </span>
                          </div>

                          <!-- Entries -->
                          <div class="dept-entries" v-if="proj.entries?.length">
                            <div
                              v-for="(entry, ei) in proj.entries"
                              :key="ei"
                              class="dept-entry"
                            >
                              <span class="entry-date">{{ entry.date }}</span>
                              <span
                                class="entry-type-tag"
                                :style="typeTagStyle(entry.type || 'other')"
                              >{{ entry.work_type }}</span>
                              <span class="entry-hours">{{ entry.hours }}h</span>
                              <span class="entry-desc">{{ entry.task_description }}</span>
                            </div>
                          </div>
                        </div>
                        <div v-if="!emp.projects?.length" class="empty-hint">暂无项目</div>
                      </div>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column prop="employee_name" label="姓名" min-width="100" sortable />
                <el-table-column prop="total_hours" label="总工时 (h)" width="100" sortable />
                <el-table-column label="项目数" width="80">
                  <template #default="{ row }">{{ row.projects?.length || 0 }}</template>
                </el-table-column>
                <el-table-column label="操作" width="85" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      size="small"
                      text
                      type="primary"
                      @click="openReportDrawer(row)"
                    >
                      查看日志
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-else class="empty-hint" style="padding: var(--space-6);">
              该部门暂无员工数据
            </div>
          </template>

          <div v-else class="empty-hint" style="padding: var(--space-10); text-align: center;">
            请选择左侧部门
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
.dept-tab {
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

/* Layout */
.dept-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 400px;
}

.dept-tree-panel {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: var(--space-3);
  overflow-y: auto;
  max-height: 600px;
}

.dept-detail-panel {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
  max-height: 600px;
}

/* Tree */
.tree-node {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  font-size: var(--text-sm);
  padding-right: var(--space-2);
}

.tree-label {
  color: rgba(255, 255, 255, 0.8);
}

.tree-meta {
  font-size: 11px;
  color: var(--brass);
  margin-left: auto;
  font-family: var(--font-mono);
}

:deep(.el-tree) {
  --el-tree-text-color: rgba(255, 255, 255, 0.7);
  --el-tree-node-hover-bg-color: rgba(255, 255, 255, 0.04);
}

/* Detail panel */
.detail-title {
  font-size: var(--text-base);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 var(--space-4);
}

.detail-summary {
  font-weight: 300;
  color: var(--brass);
  font-size: var(--text-xs);
  margin-left: var(--space-3);
}

/* Employee section */
.employee-section {
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

/* Expand row */
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
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1);
}

.proj-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.proj-hours {
  font-family: var(--font-mono);
  font-weight: 300;
  color: var(--brass);
  font-size: var(--text-sm);
}

.work-types {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.type-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  border: 1px solid;
}

/* Entries */
.dept-entries {
  margin-top: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.dept-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}

.entry-date {
  color: rgba(255, 255, 255, 0.25);
  font-family: var(--font-mono);
  width: 80px;
  flex-shrink: 0;
}

.entry-type-tag {
  display: inline-block;
  padding: 0 4px;
  border-radius: 2px;
  font-size: 10px;
  border: 1px solid;
  flex-shrink: 0;
}

.entry-hours {
  font-family: var(--font-mono);
  color: var(--brass);
  width: 32px;
  flex-shrink: 0;
  text-align: right;
}

.entry-desc {
  color: rgba(255, 255, 255, 0.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

<!-- Non-scoped: fix el-tree white background & el-table dark theme overrides -->
<style>
/* Tree root hardcodes fill-color-blank (#fff) — override to transparent */
.dept-tab .el-tree {
  background: transparent !important;
}

/* Current/selected node — use brass tint instead of light primary */
.dept-tab .el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content {
  background-color: rgba(200, 164, 92, 0.08) !important;
}

/* Focus ring on a node content — remove */
.dept-tab .el-tree-node:focus > .el-tree-node__content {
  background-color: transparent !important;
}

/* Kill all focus outlines on tree nodes */
.dept-tab .el-tree-node:focus,
.dept-tab .el-tree-node:focus-visible,
.dept-tab .el-tree-node__content:focus,
.dept-tab .el-tree-node__content:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* ---- el-table dark theme overrides ---- */
.dept-tab .el-table {
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

/* No hover background */
.dept-tab .el-table__body tr.hover-row > td.el-table__cell,
.dept-tab .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.dept-tab .el-table__body tr.hover-row.current-row > td.el-table__cell,
.dept-tab .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.dept-tab .el-table__body tr:hover > td.el-table__cell,
.dept-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

/* Kill focus outlines inside table */
.dept-tab .el-table__body *:focus,
.dept-tab .el-table__body *:focus-visible,
.dept-tab .el-table__header *:focus,
.dept-tab .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.dept-tab .el-table__body tr,
.dept-tab .el-table__body td,
.dept-tab .el-table__body th {
  outline: none !important;
}
.dept-tab .el-table__body tr:focus,
.dept-tab .el-table__body tr:focus-visible,
.dept-tab .el-table__body td:focus,
.dept-tab .el-table__body td:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

/* No bg transition */
.dept-tab .el-table__body td.el-table__cell {
  transition: none !important;
}
</style>
