<script setup>
/**
 * ProjectTab — project list + detail panel.
 *
 * Left panel:  compact project table (name, hours, employee count)
 * Right panel: selected project detail:
 *              - ProjectSummary (KPI cards + work type distribution)
 *              - Work type breakdown table with expandable employee rows
 */
import { ref, computed } from 'vue'
import { getDashboardByView } from '@/api/dashboard'
import { typeTagStyle } from '@/utils/typeColors'
import ProjectSummary from '@/components/dashboard/ProjectSummary.vue'
import EmployeeReportDrawer from '@/components/dashboard/EmployeeReportDrawer.vue'

const props = defineProps({
  variant: { type: String, default: 'classic' },
})

const loading = ref(true)
const error = ref('')
const data = ref(null)
const selectedProjectId = ref(null)

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
    data.value = await getDashboardByView('project')
    autoSelect()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载项目数据失败'
  } finally {
    loading.value = false
  }
}

const selectedProject = computed(() => {
  if (!selectedProjectId.value || !data.value?.projects) return null
  return data.value.projects.find(p => p.project_id === selectedProjectId.value) || null
})

function handleProjectClick(row) {
  selectedProjectId.value = row.project_id
}

function autoSelect() {
  if (data.value?.projects?.length && !selectedProjectId.value) {
    selectedProjectId.value = data.value.projects[0].project_id
  }
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

      <div class="project-layout">
        <!-- Left: project list -->
        <div class="project-list-panel">
          <el-table
            :data="data.projects"
            row-key="project_id"
            highlight-current-row
            size="small"
            style="width: 100%"
            @row-click="handleProjectClick"
            @current-change="autoSelect"
          >
            <el-table-column prop="project_name" label="项目名" min-width="120" show-overflow-tooltip />
            <el-table-column prop="total_hours" label="工时" width="70" sortable />
            <el-table-column prop="employee_count" label="人数" width="55" sortable />
          </el-table>
        </div>

        <!-- Right: selected project detail -->
        <div class="project-detail-panel">
          <template v-if="selectedProject">
            <!-- Project header -->
            <h4 class="detail-title">
              {{ selectedProject.project_name }}
              <span class="detail-code" v-if="selectedProject.project_code">
                {{ selectedProject.project_code }}
              </span>
              <span class="detail-summary">
                {{ selectedProject.total_hours }}h
              </span>
            </h4>

            <!-- KPI cards + work type distribution -->
            <ProjectSummary :project="selectedProject" />

            <!-- Work type breakdown table -->
            <div class="breakdown-section" v-if="selectedProject.type_breakdown?.length">
              <h5 class="section-label">按工作类型明细</h5>
              <el-table
                :data="selectedProject.type_breakdown"
                row-key="type"
                :key="selectedProjectId"
                size="small"
                style="width: 100%"
              >
                <el-table-column type="expand">
                  <template #default="{ row: typeRow }">
                    <div class="expand-content">
                      <h4 class="expand-title">
                        {{ typeRow.display }} 参与人员
                        <span class="expand-count">{{ typeRow.employee_count }} 人</span>
                      </h4>
                      <div class="employee-list">
                        <div
                          v-for="emp in typeRow.employees"
                          :key="emp.employee_id"
                          class="employee-card"
                        >
                          <div class="emp-header">
                            <div class="emp-info">
                              <span class="emp-name">{{ emp.employee_name }}</span>
                              <span class="emp-dept">{{ emp.department_name }}</span>
                            </div>
                            <div class="emp-header-right">
                              <el-button
                                size="small"
                                text
                                type="primary"
                                @click="openReportDrawer(emp)"
                              >
                                查看日志
                              </el-button>
                              <span class="emp-hours">{{ emp.hours }}h</span>
                            </div>
                          </div>
                          <!-- Entries -->
                          <div class="entry-list" v-if="emp.entries?.length">
                            <div
                              v-for="(entry, ei) in emp.entries"
                              :key="ei"
                              class="entry-row"
                            >
                              <span class="entry-date">{{ entry.date }}</span>
                              <span class="entry-hours">{{ entry.hours }}h</span>
                              <span class="entry-desc">{{ entry.task_description }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div v-if="!typeRow.employees?.length" class="empty-hint">暂无人员数据</div>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="工作类型" min-width="100">
                  <template #default="{ row }">
                    <span class="type-tag" :style="typeTagStyle(row.type)">{{ row.display }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="hours" label="工时 (h)" width="90" sortable />
                <el-table-column prop="employee_count" label="参与人数" width="80" sortable />
              </el-table>
            </div>

            <div v-else class="empty-hint" style="padding: var(--space-6);">
              该项目暂无明细数据
            </div>
          </template>

          <div v-else class="empty-hint" style="padding: var(--space-10); text-align: center;">
            请选择左侧项目
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

/* ---- Layout ---- */
.project-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 400px;
}

.project-list-panel {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: var(--space-2);
  overflow-y: auto;
  max-height: 600px;
}

.project-detail-panel {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
  max-height: 600px;
}

/* ---- Detail panel ---- */
.detail-title {
  font-size: var(--text-base);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 var(--space-4);
}

.detail-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.3);
  margin-left: var(--space-2);
}

.detail-summary {
  font-weight: 300;
  color: var(--brass);
  font-size: var(--text-xs);
  margin-left: var(--space-3);
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

.employee-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.employee-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
}

.emp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.emp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
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

.emp-hours {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--brass);
  flex-shrink: 0;
}

.emp-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* ---- Entry rows ---- */
.entry-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-top: var(--space-1);
}

.entry-row {
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

/* ---- No hover background ---- */
.project-tab .el-table__body tr.hover-row > td.el-table__cell,
.project-tab .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.project-tab .el-table__body tr.hover-row.current-row > td.el-table__cell,
.project-tab .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.project-tab .el-table__body tr:hover > td.el-table__cell,
.project-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

/* ---- Kill ALL focus outlines ---- */
.project-tab .el-table__body *:focus,
.project-tab .el-table__body *:focus-visible,
.project-tab .el-table__header *:focus,
.project-tab .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

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

/* ---- Pointer cursor on clickable rows ---- */
.project-tab .el-table__body tr {
  cursor: pointer;
}

/* ---- No bg transition ---- */
.project-tab .el-table__body td.el-table__cell {
  transition: none !important;
}

/* ---- Highlight current row in left panel ---- */
.project-tab .el-table__body tr.current-row > td.el-table__cell {
  background-color: rgba(200, 164, 92, 0.08) !important;
}
</style>
