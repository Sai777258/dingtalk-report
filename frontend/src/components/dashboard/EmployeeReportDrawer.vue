<script setup>
/**
 * EmployeeReportDrawer — slide-out drawer showing an employee's work reports.
 *
 * Two-level view:
 *   1. List — paginated table of the employee's DingTalk reports
 *   2. Detail — parsed work entries grouped by project + raw contents
 *
 * Props:
 *   modelValue       Boolean  v-model binding for drawer visibility
 *   employeeUsername String   Employee's username (for API filter)
 *   employeeName     String   Display name for drawer title
 */
import { ref, computed, watch } from 'vue'
import { getReports, getReportDetail } from '@/api/reports'
import { typeTagStyle } from '@/utils/typeColors'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  employeeUsername: { type: String, required: true },
  employeeName: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])

// ---- List state ----
const loading = ref(false)
const error = ref('')
const reports = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// ---- Detail state ----
const detailLoading = ref(false)
const detail = ref(null)
const viewingReportId = ref(null)
const showRawContents = ref(false)

// ---- Derived ----
const groupedEntries = computed(() => {
  if (!detail.value?.work_entries?.length) return []
  const map = {}
  for (const e of detail.value.work_entries) {
    const key = e.project_name || '未归类'
    if (!map[key]) {
      map[key] = {
        project_name: key,
        project_code: e.project_code || '',
        total_hours: 0,
        entries: [],
      }
    }
    map[key].total_hours += parseFloat(e.hours) || 0
    map[key].entries.push(e)
  }
  return Object.values(map).sort((a, b) => b.total_hours - a.total_hours)
})

const totalEntryHours = computed(() => {
  return groupedEntries.value.reduce((s, g) => s + g.total_hours, 0).toFixed(1)
})

// ---- Load report list ----
async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const res = await getReports({
      username: props.employeeUsername,
      page: page.value,
      page_size: pageSize.value,
    })
    reports.value = res.results
    total.value = res.count
  } catch (e) {
    error.value = e.response?.data?.detail || '加载日志列表失败'
  } finally {
    loading.value = false
  }
}

// ---- Detail ----
async function viewDetail(reportId) {
  viewingReportId.value = reportId
  detailLoading.value = true
  detail.value = null
  showRawContents.value = false
  try {
    detail.value = await getReportDetail(reportId)
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function backToList() {
  viewingReportId.value = null
  detail.value = null
}

// ---- Helpers ----
function statusTag(status) {
  return status === 'submitted' ? 'success' : 'info'
}

function handlePageChange(p) {
  page.value = p
  loadReports()
}

function handleSizeChange(s) {
  pageSize.value = s
  page.value = 1
  loadReports()
}

// ---- Lifecycle ----
// Reset and load when drawer opens
watch(() => props.modelValue, (visible) => {
  if (visible) {
    page.value = 1
    viewingReportId.value = null
    detail.value = null
    loadReports()
  }
})
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :title="employeeName + ' 的工作日志'"
    size="560px"
  >
    <div class="emp-report-drawer-content">
      <!-- =========================================================== -->
      <!-- List View                                                    -->
      <!-- =========================================================== -->
      <template v-if="viewingReportId === null">
        <div v-if="loading" class="drawer-loading">加载中…</div>

        <div v-else-if="error" class="drawer-error">
          <p>{{ error }}</p>
          <el-button size="small" text type="primary" @click="loadReports">重试</el-button>
        </div>

        <template v-else-if="reports.length">
          <el-table
            :data="reports"
            size="small"
            row-key="id"
            @row-click="(row) => viewDetail(row.id)"
          >
            <el-table-column prop="report_date" label="日期" width="110" sortable />
            <el-table-column prop="entry_count" label="条目" width="60" align="center" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">
                  {{ row.status === 'submitted' ? '已提交' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="入库时间" min-width="140">
              <template #default="{ row }">
                {{ row.created_at?.slice(0, 19).replace('T', ' ') }}
              </template>
            </el-table-column>
          </el-table>

          <div class="drawer-pagination">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[5, 10, 20]"
              layout="total, prev, pager, next"
              small
              @current-change="handlePageChange"
              @size-change="handleSizeChange"
            />
          </div>
        </template>

        <div v-else class="drawer-empty">该员工暂无工作日志</div>
      </template>

      <!-- =========================================================== -->
      <!-- Detail View                                                  -->
      <!-- =========================================================== -->
      <template v-else>
        <button class="back-btn" @click="backToList">← 返回列表</button>

        <div v-if="detailLoading" class="drawer-loading">加载中…</div>

        <div v-else-if="!detail" class="drawer-error">
          <p>加载日志详情失败</p>
          <el-button size="small" text type="primary" @click="backToList">返回列表</el-button>
        </div>

        <template v-else>
          <!-- Header -->
          <div class="detail-header">
            <div class="detail-meta">
              <span class="detail-creator">{{ detail.creator_name }}</span>
              <span class="detail-username">@{{ detail.creator_username }}</span>
              <span class="detail-dept">{{ detail.department_name }}</span>
            </div>
            <div class="detail-date">{{ detail.report_date }}</div>
          </div>

          <!-- KPI strip -->
          <div class="detail-kpis">
            <div class="detail-kpi">
              <span class="kpi-num">{{ totalEntryHours }}</span>
              <span class="kpi-label">总工时 (h)</span>
            </div>
            <div class="detail-kpi">
              <span class="kpi-num">{{ detail.work_entries?.length || 0 }}</span>
              <span class="kpi-label">工时条目</span>
            </div>
            <div class="detail-kpi">
              <span class="kpi-num">{{ groupedEntries.length }}</span>
              <span class="kpi-label">涉及项目</span>
            </div>
          </div>

          <!-- Work entries grouped by project -->
          <div v-if="groupedEntries.length" class="entries-section">
            <h3 class="section-title">工时明细</h3>
            <div
              v-for="group in groupedEntries"
              :key="group.project_name"
              class="project-group"
            >
              <div class="project-group-header">
                <span class="project-group-name">{{ group.project_name }}</span>
                <span v-if="group.project_code" class="project-group-code">{{ group.project_code }}</span>
                <span class="project-group-hours">{{ group.total_hours.toFixed(1) }}h</span>
              </div>
              <div class="entry-list">
                <div
                  v-for="entry in group.entries"
                  :key="entry.id"
                  class="entry-row"
                >
                  <span class="entry-date">{{ entry.date }}</span>
                  <span class="entry-type-tag" :style="typeTagStyle(entry.task_type)">
                    {{ entry.task_type_display }}
                  </span>
                  <span class="entry-hours">{{ entry.hours }}h</span>
                  <span class="entry-desc">{{ entry.task_description || '(无描述)' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="drawer-empty">该日志暂无解析出的工时条目</div>

          <!-- Raw contents -->
          <div class="drawer-divider" />
          <div class="raw-section">
            <button class="raw-toggle" @click="showRawContents = !showRawContents">
              <span>原始日志内容 ({{ detail.contents?.length || 0 }} 项)</span>
              <el-icon :class="{ rotated: showRawContents }"><ArrowDown /></el-icon>
            </button>
            <div v-if="showRawContents" class="raw-blocks">
              <div v-for="c in detail.contents" :key="c.id" class="raw-block">
                <h4 class="raw-field-key">{{ c.field_key }}</h4>
                <div class="raw-field-value">{{ c.field_value || '(空白)' }}</div>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>
  </el-drawer>
</template>

<style scoped>
/* Inside-drawer content (scoped) */
.back-btn {
  display: inline-block;
  padding: 4px 0;
  margin-bottom: 16px;
  background: none;
  border: none;
  color: var(--brass);
  font-size: var(--text-sm);
  font-family: var(--font-body);
  cursor: pointer;
  transition: opacity var(--duration-fast);
}
.back-btn:hover {
  opacity: 0.7;
}

.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: rgba(255, 255, 255, 0.4);
}

.drawer-error {
  text-align: center;
  padding: 32px;
  color: var(--vermilion);
  font-size: var(--text-sm);
}

.drawer-empty {
  padding: 48px;
  text-align: center;
  color: rgba(255, 255, 255, 0.2);
  font-size: var(--text-sm);
}

.drawer-pagination {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

:deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: var(--text-xs);
}
:deep(.el-table__body tr) {
  cursor: pointer;
}
</style>

<!-- Non-scoped: drawer teleports to body -->
<style>
.emp-report-drawer-content {
  color: rgba(255, 255, 255, 0.8);
}

/* ---- Table ---- */
.emp-report-drawer-content .el-table {
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

.emp-report-drawer-content .el-table__body tr.hover-row > td.el-table__cell,
.emp-report-drawer-content .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.emp-report-drawer-content .el-table__body tr.hover-row.current-row > td.el-table__cell,
.emp-report-drawer-content .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.emp-report-drawer-content .el-table__body tr:hover > td.el-table__cell,
.emp-report-drawer-content .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

.emp-report-drawer-content .el-table__body *:focus,
.emp-report-drawer-content .el-table__body *:focus-visible,
.emp-report-drawer-content .el-table__header *:focus,
.emp-report-drawer-content .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.emp-report-drawer-content .el-table__body tr,
.emp-report-drawer-content .el-table__body td,
.emp-report-drawer-content .el-table__body th {
  outline: none !important;
}

.emp-report-drawer-content .el-table__body td.el-table__cell {
  transition: none !important;
}

/* ---- Detail header ---- */
.emp-report-drawer-content .detail-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.emp-report-drawer-content .detail-meta {
  display: flex;
  gap: 10px;
  align-items: baseline;
  margin-bottom: 4px;
}

.emp-report-drawer-content .detail-creator {
  font-size: 1.125rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
}

.emp-report-drawer-content .detail-username {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.35);
}

.emp-report-drawer-content .detail-dept {
  font-size: 0.75rem;
  color: #C8A45C;
  margin-left: auto;
}

.emp-report-drawer-content .detail-date {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.4);
}

/* ---- KPI strip ---- */
.emp-report-drawer-content .detail-kpis {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.emp-report-drawer-content .detail-kpi {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.emp-report-drawer-content .kpi-num {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 1.25rem;
  font-weight: 300;
  color: #C8A45C;
}

.emp-report-drawer-content .kpi-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ---- Section ---- */
.emp-report-drawer-content .entries-section {
  margin-bottom: 4px;
}

.emp-report-drawer-content .section-title {
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
  margin-bottom: 14px;
}

/* ---- Project group ---- */
.emp-report-drawer-content .project-group {
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  overflow: hidden;
}

.emp-report-drawer-content .project-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(200, 164, 92, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.emp-report-drawer-content .project-group-name {
  font-weight: 500;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.85);
}

.emp-report-drawer-content .project-group-code {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
}

.emp-report-drawer-content .project-group-hours {
  margin-left: auto;
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-weight: 300;
  color: #C8A45C;
  font-size: 0.875rem;
}

/* ---- Entry rows ---- */
.emp-report-drawer-content .entry-list {
  padding: 6px 0;
}

.emp-report-drawer-content .entry-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}

.emp-report-drawer-content .entry-row:last-child {
  border-bottom: none;
}

.emp-report-drawer-content .entry-date {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.25);
  width: 80px;
  flex-shrink: 0;
}

.emp-report-drawer-content .entry-type-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  border: 1px solid;
  flex-shrink: 0;
  white-space: nowrap;
}

.emp-report-drawer-content .entry-hours {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.75rem;
  color: #C8A45C;
  width: 36px;
  flex-shrink: 0;
  text-align: right;
}

.emp-report-drawer-content .entry-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
  word-break: break-all;
}

/* ---- Divider ---- */
.emp-report-drawer-content .drawer-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 24px 0;
}

/* ---- Raw contents ---- */
.emp-report-drawer-content .raw-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 0;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  font-size: 0.75rem;
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
  cursor: pointer;
  transition: color 0.2s;
}

.emp-report-drawer-content .raw-toggle:hover {
  color: rgba(255, 255, 255, 0.5);
}

.emp-report-drawer-content .raw-toggle .el-icon {
  transition: transform 0.2s;
  font-size: 12px;
}

.emp-report-drawer-content .raw-toggle .el-icon.rotated {
  transform: rotate(180deg);
}

.emp-report-drawer-content .raw-blocks {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 4px;
}

.emp-report-drawer-content .raw-block {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
  padding: 14px;
}

.emp-report-drawer-content .raw-field-key {
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
  font-size: 0.7rem;
  font-weight: 600;
  color: #C8A45C;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.emp-report-drawer-content .raw-field-value {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.8;
  white-space: pre-wrap;
}

/* ---- Dark drawer chrome ---- */
.el-drawer {
  background: #262B38 !important;
}
.el-drawer__header {
  color: rgba(255, 255, 255, 0.6) !important;
  margin-bottom: 0 !important;
}
.el-drawer__body {
  color: rgba(255, 255, 255, 0.8);
}
</style>
