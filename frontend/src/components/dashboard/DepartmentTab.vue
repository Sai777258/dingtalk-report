<script setup>
/**
 * DepartmentTab — department tree view with employee/project/entry detail.
 *
 * Left panel: department tree (el-tree)
 * Right panel: selected department's employees and their project details
 */
import { ref, computed } from 'vue'
import { getDashboardByView } from '@/api/dashboard'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const activeDeptId = ref(null)

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
            <h4 class="detail-title">
              {{ selectedDept.department_name }}
              <span class="detail-summary">
                {{ selectedDept.total_hours }}h · {{ selectedDept.employees.length }} 人
              </span>
            </h4>

            <!-- Employees -->
            <div class="dept-employees" v-if="selectedDept.employees.length">
              <div
                v-for="emp in selectedDept.employees"
                :key="emp.employee_id"
                class="dept-emp-card"
              >
                <div class="dept-emp-header">
                  <span class="dept-emp-name">{{ emp.employee_name }}</span>
                  <span class="dept-emp-hours">{{ emp.total_hours }}h</span>
                </div>

                <!-- Projects for this employee -->
                <div class="dept-emp-projects" v-if="emp.projects.length">
                  <div
                    v-for="proj in emp.projects"
                    :key="proj.project_id"
                    class="dept-proj-item"
                  >
                    <div class="dept-proj-header">
                      <span class="dept-proj-name">{{ proj.project_name }}</span>
                      <span class="dept-proj-hours">{{ proj.hours }}h</span>
                    </div>

                    <!-- Work types -->
                    <div class="dept-proj-types" v-if="proj.work_types.length">
                      <span
                        v-for="wt in proj.work_types"
                        :key="wt.type"
                        class="type-tag"
                        :style="typeTagStyle(wt.type)"
                      >
                        {{ wt.display }} {{ wt.hours }}h
                      </span>
                    </div>

                    <!-- Work entries -->
                    <div class="dept-entries" v-if="proj.entries.length">
                      <div
                        v-for="(entry, ei) in proj.entries"
                        :key="ei"
                        class="dept-entry"
                      >
                        <span class="entry-date">{{ entry.date }}</span>
                        <span class="entry-type-tag" :style="typeTagStyle(entry.work_type === '开发' ? 'development' : entry.work_type === '测试' ? 'testing' : 'other')">{{ entry.work_type }}</span>
                        <span class="entry-hours">{{ entry.hours }}h</span>
                        <span class="entry-desc">{{ entry.task_description }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="empty-hint">暂无项目</div>
              </div>
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

/* Tree text colour (stays in scoped via :deep) */
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

.dept-employees {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.dept-emp-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
}

.dept-emp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.dept-emp-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.dept-emp-hours {
  font-family: var(--font-mono);
  font-weight: 300;
  color: var(--brass);
}

.dept-emp-projects {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.dept-proj-item {
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
}

.dept-proj-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dept-proj-name {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  font-size: var(--text-sm);
}

.dept-proj-hours {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--brass);
}

.dept-proj-types {
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
</style>

<!-- Non-scoped: fix el-tree white background & focus/highlight on dark theme -->
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
</style>
