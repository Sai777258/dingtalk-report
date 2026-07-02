<script setup>
/**
 * ReportsView — work report list with filters and detail drawer.
 *
 * The drawer now shows parsed work entries (WorkEntry records) as the
 * primary content, grouped by project.  Original report template fields
 * are still available in a collapsible "原始日志" section.
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getReports, getReportDetail } from '@/api/reports'
import { Search, Refresh, ArrowDown } from '@element-plus/icons-vue'

const auth = useAuthStore()

// ---- State ----
const loading = ref(false)
const error = ref('')
const reports = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(15)

const filters = reactive({
  date_from: '',
  date_to: '',
  username: '',
  department: '',
  search: '',
})

// Detail drawer
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const showRawContents = ref(false)

// ---- Work-type colour palette ----
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

// ---- Group work entries by project ----
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
  // Sort groups by total hours desc
  return Object.values(map).sort((a, b) => b.total_hours - a.total_hours)
})

const totalEntryHours = computed(() => {
  return groupedEntries.value.reduce((s, g) => s + g.total_hours, 0).toFixed(1)
})

// ---- Load ----
async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to
    if (filters.username) params.username = filters.username
    if (filters.department) params.department = filters.department
    if (filters.search) params.search = filters.search

    const res = await getReports(params)
    reports.value = res.results
    total.value = res.count
  } catch (e) {
    error.value = e.response?.data?.detail || '加载日志列表失败'
  } finally {
    loading.value = false
  }
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

function handleSearch() {
  page.value = 1
  loadReports()
}

function handleReset() {
  filters.date_from = ''
  filters.date_to = ''
  filters.username = ''
  filters.department = ''
  filters.search = ''
  page.value = 1
  loadReports()
}

// ---- Detail drawer ----
async function openDetail(reportId) {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  showRawContents.value = false
  try {
    detail.value = await getReportDetail(reportId)
  } catch (e) {
    // ignore
  } finally {
    detailLoading.value = false
  }
}

function statusTag(status) {
  return status === 'submitted' ? 'success' : 'info'
}

onMounted(loadReports)
</script>

<template>
  <div class="reports-page">
    <h2 class="page-title">工作日志</h2>

    <!-- ---- Filters ---- -->
    <div class="filter-bar">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="搜索日志内容..."
          :prefix-icon="Search"
          clearable
          size="default"
          class="filter-search"
          @keyup.enter="handleSearch"
        />
        <el-input
          v-model="filters.username"
          :placeholder="auth.isEmployee ? '仅可查看自身' : '用户名'"
          :disabled="auth.isEmployee"
          clearable
          size="default"
          class="filter-sm"
        />
        <el-input
          v-model="filters.department"
          :placeholder="auth.isEmployee ? '仅可查看自身' : '部门'"
          :disabled="auth.isEmployee"
          clearable
          size="default"
          class="filter-sm"
        />
        <el-date-picker
          v-model="filters.date_from"
          type="date"
          placeholder="开始日期"
          size="default"
          class="filter-date"
          value-format="YYYY-MM-DD"
        />
        <el-date-picker
          v-model="filters.date_to"
          type="date"
          placeholder="结束日期"
          size="default"
          class="filter-date"
          value-format="YYYY-MM-DD"
        />
        <el-button size="default" @click="handleSearch">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button size="default" text @click="handleReset">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>
    </div>

    <!-- ---- Error ---- -->
    <div v-if="error" class="error-bar">{{ error }}</div>

    <!-- ---- Table ---- -->
    <div class="table-wrap">
      <el-table
        :data="reports"
        v-loading="loading"
        size="default"
        row-key="id"
        @row-click="(row) => openDetail(row.id)"
      >
        <el-table-column prop="report_date" label="日期" width="110" sortable />
        <el-table-column prop="creator_name" label="姓名" width="100" />
        <el-table-column prop="creator_username" label="用户名" width="100" />
        <el-table-column prop="department_name" label="部门" width="100" />
        <el-table-column prop="entry_count" label="条目" width="70" align="center" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">
              {{ row.status === 'submitted' ? '已提交' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="入库时间" width="170">
          <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 15, 20, 30]"
          layout="total, sizes, prev, pager, next"
          small
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- ---- Detail Drawer ---- -->
    <el-drawer v-model="drawerVisible" title="日志详情" size="560px">
      <div class="report-drawer-content">
        <!-- Loading -->
        <div v-if="detailLoading" class="drawer-loading">加载中…</div>

        <template v-else-if="detail">
          <!-- ---- Header ---- -->
          <div class="detail-header">
            <div class="detail-meta">
              <span class="detail-creator">{{ detail.creator_name }}</span>
              <span class="detail-username">@{{ detail.creator_username }}</span>
              <span class="detail-dept">{{ detail.department_name }}</span>
            </div>
            <div class="detail-date">{{ detail.report_date }}</div>
          </div>

          <!-- ---- KPI strip ---- -->
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

          <!-- ---- Work entries grouped by project ---- -->
          <div v-if="groupedEntries.length" class="entries-section">
            <h3 class="section-title">工时明细</h3>

            <div
              v-for="group in groupedEntries"
              :key="group.project_name"
              class="project-group"
            >
              <!-- Project group header -->
              <div class="project-group-header">
                <span class="project-group-name">{{ group.project_name }}</span>
                <span v-if="group.project_code" class="project-group-code">{{ group.project_code }}</span>
                <span class="project-group-hours">{{ group.total_hours.toFixed(1) }}h</span>
              </div>

              <!-- Individual entries -->
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

          <!-- Empty state -->
          <div v-else class="drawer-empty">
            该日志暂无解析出的工时条目
          </div>

          <!-- ---- Divider ---- -->
          <div class="drawer-divider" />

          <!-- ---- Raw report contents (collapsible) ---- -->
          <div class="raw-section">
            <button class="raw-toggle" @click="showRawContents = !showRawContents">
              <span>原始日志内容 ({{ detail.contents?.length || 0 }} 项)</span>
              <el-icon :class="{ rotated: showRawContents }">
                <ArrowDown />
              </el-icon>
            </button>

            <div v-if="showRawContents" class="raw-blocks">
              <div
                v-for="content in detail.contents"
                :key="content.id"
                class="raw-block"
              >
                <h4 class="raw-field-key">{{ content.field_key }}</h4>
                <div class="raw-field-value">{{ content.field_value || '(空白)' }}</div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.reports-page {
  padding: var(--space-6);
  max-width: 1280px;
  margin: 0 auto;
}

.page-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: var(--space-5);
  letter-spacing: 1px;
}

/* ---- Filter bar ---- */
.filter-bar {
  margin-bottom: var(--space-4);
}

.filter-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex-wrap: wrap;
}

.filter-search { width: 220px; }
.filter-sm { width: 120px; }
.filter-date { width: 150px; }

/* Override inputs for dark theme */
:deep(.el-input__wrapper) {
  background: var(--steel-light) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
  box-shadow: none !important;
}
:deep(.el-input__inner) { color: rgba(255, 255, 255, 0.7); }
:deep(.el-input__inner::placeholder) { color: rgba(255, 255, 255, 0.3); }

/* ---- Error ---- */
.error-bar {
  background: rgba(212, 105, 90, 0.12);
  color: var(--vermilion);
  font-size: var(--text-sm);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-4);
}

/* ---- Table ---- */
.table-wrap {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-wrap :deep(.el-table) {
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

.table-wrap :deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: var(--text-xs);
}

.table-wrap :deep(.el-table__body tr) {
  cursor: pointer;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .filter-row { flex-direction: column; }
  .filter-search, .filter-sm, .filter-date { width: 100%; }
}
</style>

<!-- Non-scoped: drawer teleports to body so scoped styles won't reach it -->
<style>
.report-drawer-content {
  color: rgba(255, 255, 255, 0.8);
}

.report-drawer-content .drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: rgba(255, 255, 255, 0.4);
}

/* ---- Header ---- */
.report-drawer-content .detail-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.report-drawer-content .detail-meta {
  display: flex;
  gap: 10px;
  align-items: baseline;
  margin-bottom: 4px;
}

.report-drawer-content .detail-creator {
  font-size: 1.125rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
}

.report-drawer-content .detail-username {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.35);
}

.report-drawer-content .detail-dept {
  font-size: 0.75rem;
  color: #C8A45C;
  margin-left: auto;
}

.report-drawer-content .detail-date {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.4);
}

/* ---- KPI strip ---- */
.report-drawer-content .detail-kpis {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.report-drawer-content .detail-kpi {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.report-drawer-content .kpi-num {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 1.25rem;
  font-weight: 300;
  color: #C8A45C;
}

.report-drawer-content .kpi-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ---- Section ---- */
.report-drawer-content .entries-section {
  margin-bottom: 4px;
}

.report-drawer-content .section-title {
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
  margin-bottom: 14px;
}

/* ---- Project group ---- */
.report-drawer-content .project-group {
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  overflow: hidden;
}

.report-drawer-content .project-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(200, 164, 92, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.report-drawer-content .project-group-name {
  font-weight: 500;
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.85);
}

.report-drawer-content .project-group-code {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.3);
}

.report-drawer-content .project-group-hours {
  margin-left: auto;
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-weight: 300;
  color: #C8A45C;
  font-size: 0.875rem;
}

/* ---- Entry rows ---- */
.report-drawer-content .entry-list {
  padding: 6px 0;
}

.report-drawer-content .entry-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
}

.report-drawer-content .entry-row:last-child {
  border-bottom: none;
}

.report-drawer-content .entry-date {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.25);
  width: 80px;
  flex-shrink: 0;
}

.report-drawer-content .entry-type-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  border: 1px solid;
  flex-shrink: 0;
  white-space: nowrap;
}

.report-drawer-content .entry-hours {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
  font-size: 0.75rem;
  color: #C8A45C;
  width: 36px;
  flex-shrink: 0;
  text-align: right;
}

.report-drawer-content .entry-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
  word-break: break-all;
}

.report-drawer-content .drawer-empty {
  padding: 32px 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.2);
  font-size: 0.875rem;
}

/* ---- Divider ---- */
.report-drawer-content .drawer-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 24px 0;
}

/* ---- Raw contents toggle ---- */
.report-drawer-content .raw-section {
  margin-top: 0;
}

.report-drawer-content .raw-toggle {
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

.report-drawer-content .raw-toggle:hover {
  color: rgba(255, 255, 255, 0.5);
}

.report-drawer-content .raw-toggle .el-icon {
  transition: transform 0.2s;
  font-size: 12px;
}

.report-drawer-content .raw-toggle .el-icon.rotated {
  transform: rotate(180deg);
}

.report-drawer-content .raw-blocks {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 4px;
}

.report-drawer-content .raw-block {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
  padding: 14px;
}

.report-drawer-content .raw-field-key {
  font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
  font-size: 0.7rem;
  font-weight: 600;
  color: #C8A45C;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.report-drawer-content .raw-field-value {
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

/* ---- Kill ALL table hover / focus / highlight effects (non-scoped for JS-driven DOM) ---- */
.reports-page .el-table {
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

.reports-page .el-table__body tr.hover-row > td.el-table__cell,
.reports-page .el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell,
.reports-page .el-table__body tr.hover-row.current-row > td.el-table__cell,
.reports-page .el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell,
.reports-page .el-table__body tr:hover > td.el-table__cell,
.reports-page .el-table__body tr.current-row > td.el-table__cell {
  background-color: transparent !important;
}

.reports-page .el-table__body *:focus,
.reports-page .el-table__body *:focus-visible,
.reports-page .el-table__header *:focus,
.reports-page .el-table__header *:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.reports-page .el-table__body tr,
.reports-page .el-table__body td,
.reports-page .el-table__body th {
  outline: none !important;
}

.reports-page .el-table__body tr:focus,
.reports-page .el-table__body tr:focus-visible,
.reports-page .el-table__body td:focus,
.reports-page .el-table__body td:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

.reports-page .el-table__body td.el-table__cell {
  transition: none !important;
}

/* Also kill focus on date-pickers & inputs inside filter bar */
.reports-page .el-input__wrapper:focus,
.reports-page .el-input__wrapper:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}
</style>
