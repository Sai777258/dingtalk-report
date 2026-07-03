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

const props = defineProps({
  variant: { type: String, default: 'classic' },
})

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
    autoSelect()
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

// Aggregate work types across all projects for an employee
function aggregateWorkTypes(employee) {
  const map = {}
  if (!employee.projects) return []
  employee.projects.forEach((p) => {
    if (!p.work_types) return
    p.work_types.forEach((wt) => {
      if (!map[wt.type]) {
        map[wt.type] = { type: wt.type, display: wt.display, hours: 0 }
      }
      map[wt.type].hours += wt.hours
    })
  })
  return Object.values(map).sort((a, b) => b.hours - a.hours)
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
  <div :class="['dept-tab', `dept-tab--${props.variant}`]">
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
              :variant="props.variant"
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
                <el-table-column label="参与项目" width="150">
                  <template #default="{ row }">
                    <div class="proj-inline" v-if="row.projects?.length">
                      <span
                        v-for="p in row.projects"
                        :key="p.project_id"
                        class="proj-tag-sm"
                      >{{ p.project_name }}</span>
                    </div>
                    <span v-else class="no-wt">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="工作类型" width="170">
                  <template #default="{ row }">
                    <div class="wt-inline" v-if="aggregateWorkTypes(row).length">
                      <span
                        v-for="wt in aggregateWorkTypes(row)"
                        :key="wt.type"
                        class="type-tag-sm"
                        :style="typeTagStyle(wt.type)"
                      >{{ wt.display }} {{ wt.hours }}h</span>
                    </div>
                    <span v-else class="no-wt">—</span>
                  </template>
                </el-table-column>
                <el-table-column prop="total_hours" label="总工时 (h)" width="100" sortable />
                <el-table-column label="项目数" width="80" sortable
                  :sort-method="(a, b) => (a.projects?.length || 0) - (b.projects?.length || 0)">
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
        :variant="props.variant"
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

/* Inline work type tags in employee table */
.wt-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  line-height: 1.5;
}

.proj-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  line-height: 1.5;
}

.proj-tag-sm {
  display: inline-block;
  padding: 0 5px;
  border-radius: 2px;
  font-size: 10px;
  color: var(--blueprint);
  border: 1px solid rgba(74, 144, 164, 0.35);
  white-space: nowrap;
  background: rgba(74, 144, 164, 0.08);
}

.type-tag-sm {
  display: inline-block;
  padding: 0 5px;
  border-radius: 2px;
  font-size: 10px;
  border: 1px solid;
  white-space: nowrap;
}

.no-wt {
  color: rgba(255, 255, 255, 0.2);
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

/* ---- Hisky light clinical skin ---- */
.dept-tab--hisky {
  background: transparent;
  border: 0;
  border-radius: 0;
  color: #15343d;
}

.dept-tab--hisky .tab-header {
  padding: 0 0 var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom-color: rgba(12, 94, 108, 0.1);
}

.dept-tab--hisky .tab-title,
.dept-tab--hisky .detail-title,
.dept-tab--hisky .section-label,
.dept-tab--hisky .expand-title,
.dept-tab--hisky .proj-name {
  font-family: "HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #12313a;
}

.dept-tab--hisky .tab-title,
.dept-tab--hisky .detail-title {
  font-weight: 650;
  letter-spacing: 0.02em;
}

.dept-tab--hisky .tab-summary,
.dept-tab--hisky .detail-summary,
.dept-tab--hisky .expand-count,
.dept-tab--hisky .proj-hours,
.dept-tab--hisky .entry-hours {
  color: #0b8491;
}

.dept-tab--hisky .dept-layout {
  border: 1px solid rgba(12, 94, 108, 0.1);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 28px rgba(7, 43, 52, 0.055);
  overflow: hidden;
}

.dept-tab--hisky .dept-tree-panel,
.dept-tab--hisky .dept-detail-panel,
.dept-tab--hisky .expand-content,
.dept-tab--hisky .project-card {
  background: #ffffff;
}

.dept-tab--hisky .dept-tree-panel {
  border-right-color: rgba(12, 94, 108, 0.1);
}

.dept-tab--hisky .tree-label {
  color: #12313a;
  font-weight: 600;
}

.dept-tab--hisky .tree-meta,
.dept-tab--hisky .entry-date {
  color: rgba(11, 132, 145, 0.72);
}

.dept-tab--hisky .section-label {
  color: rgba(21, 52, 61, 0.5);
  font-weight: 650;
  letter-spacing: 0.04em;
}

.dept-tab--hisky .expand-content {
  border: 1px solid rgba(12, 94, 108, 0.08);
  border-radius: var(--radius-sm);
}

.dept-tab--hisky .project-card {
  border-color: rgba(12, 94, 108, 0.1);
  box-shadow: 0 8px 18px rgba(7, 43, 52, 0.045);
}

.dept-tab--hisky .proj-tag-sm {
  color: #1f5360;
  border-color: rgba(11, 132, 145, 0.24);
  background: rgba(24, 167, 168, 0.08);
}

.dept-tab--hisky .type-tag,
.dept-tab--hisky .type-tag-sm,
.dept-tab--hisky .entry-type-tag {
  background: rgba(24, 167, 168, 0.09) !important;
  border-color: rgba(11, 132, 145, 0.26) !important;
  color: #1f5360 !important;
  font-weight: 600;
}

.dept-tab--hisky .dept-entry {
  border-bottom-color: rgba(12, 94, 108, 0.06);
}

.dept-tab--hisky .entry-desc {
  color: rgba(21, 52, 61, 0.72);
}

.dept-tab--hisky .no-wt,
.dept-tab--hisky .empty-hint {
  color: rgba(21, 52, 61, 0.38);
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

.dept-tab--hisky .el-tree {
  --el-tree-text-color: #15343d;
  --el-tree-node-hover-bg-color: rgba(24, 167, 168, 0.07);
  background: #ffffff !important;
  color: #15343d !important;
}

.dept-tab--hisky .el-tree-node__content {
  color: #15343d !important;
}

/* Current/selected node — use brass tint instead of light primary */
.dept-tab .el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content {
  background-color: rgba(200, 164, 92, 0.08) !important;
}

.dept-tab--hisky .el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content {
  background-color: rgba(24, 167, 168, 0.1) !important;
  color: #0b8491 !important;
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

.dept-tab--hisky .el-table {
  --el-table-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;
  --el-table-header-bg-color: rgba(12, 94, 108, 0.055);
  --el-table-border-color: rgba(12, 94, 108, 0.08);
  --el-table-text-color: #15343d;
  --el-table-header-text-color: rgba(21, 52, 61, 0.58);
  --el-table-row-hover-bg-color: rgba(24, 167, 168, 0.07);
  --el-table-current-row-bg-color: rgba(24, 167, 168, 0.09);
  --el-table-expanded-cell-bg-color: #f8fbfb;
  background: #ffffff !important;
  color: #15343d !important;
}

.dept-tab--hisky .el-table th.el-table__cell {
  background: rgba(12, 94, 108, 0.055) !important;
  color: rgba(21, 52, 61, 0.62) !important;
}

.dept-tab--hisky .el-table td.el-table__cell {
  background: #ffffff !important;
  border-bottom-color: rgba(12, 94, 108, 0.08);
  color: #15343d !important;
}

.dept-tab--hisky .el-table__expanded-cell,
.dept-tab--hisky .el-table__expanded-cell[class*=cell] {
  background: #f8fbfb !important;
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

.dept-tab--hisky .el-table__body tr.hover-row > td.el-table__cell,
.dept-tab--hisky .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.dept-tab--hisky .el-table__body tr.hover-row.current-row > td.el-table__cell,
.dept-tab--hisky .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.dept-tab--hisky .el-table__body tr:hover > td.el-table__cell,
.dept-tab--hisky .el-table__body tr.current-row > td.el-table__cell {
  background-color: rgba(24, 167, 168, 0.07) !important;
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
