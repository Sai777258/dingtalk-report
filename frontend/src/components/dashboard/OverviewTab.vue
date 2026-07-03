<script setup>
/**
 * OverviewTab — Team Pulse dashboard.
 *
 * Pulse bars: submission rate, avg daily hours, project concentration
 * 2x2 chart grid:
 *   top-left  — Daily trend bar chart
 *   top-right — Work type distribution donut (new)
 *   bot-left  — Department hours distribution donut (new, replaces employee ranking)
 *   bot-right — Project hours distribution donut
 * Health cards: simplified per-project cards (hours, employees, %, bar)
 */
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  summary: { type: Object, required: true },
  canViewEmployee: { type: Boolean, default: false },
  variant: { type: String, default: 'classic' },
})
const emit = defineEmits(['navigate'])

// ---- Chart refs ----
const trendChartRef = ref(null)
const workTypeChartRef = ref(null)
const departmentChartRef = ref(null)
const projectChartRef = ref(null)

let trendChart = null
let workTypeChart = null
let departmentChart = null
let projectChart = null

// ---- Theme ----
const STEEL = '#1B1F2A'
const PAPER = '#F5F3EE'
const BRASS = '#C8A45C'
const BLUEPRINT = '#4A90A4'
const SAGE = '#7D9B76'
const VERMILION = '#D4695A'
const chartColors = [
  '#C8A45C', '#4A90A4', '#7D9B76', '#D4695A',
  '#D4B87A', '#5EA0C0', '#8EB89A', '#E8956E',
  '#B8956A', '#6BA5B8', '#6A9478', '#C47A6B',
  '#8B7AA0', '#9B8EC4',
]
const hiskyChartColors = [
  '#0B8491', '#18A7A8', '#67A87D', '#E8A356',
  '#4C9AB0', '#8BD7CA', '#5E8F78', '#C9524C',
  '#6EB7BD', '#A7D9D0',
]
const isHiskySkin = computed(() => props.variant === 'hisky')

const chartTextColor = computed(() => isHiskySkin.value ? 'rgba(21,52,61,0.58)' : 'rgba(255,255,255,0.4)')
const chartStrongTextColor = computed(() => isHiskySkin.value ? 'rgba(18,49,58,0.82)' : 'rgba(255,255,255,0.92)')
const chartSplitColor = computed(() => isHiskySkin.value ? 'rgba(12,94,108,0.09)' : 'rgba(255,255,255,0.05)')
const chartLineColor = computed(() => isHiskySkin.value ? 'rgba(12,94,108,0.14)' : 'rgba(255,255,255,0.1)')
const chartPanelColor = computed(() => isHiskySkin.value ? '#fbfefd' : STEEL)
const activeChartColors = computed(() => isHiskySkin.value ? hiskyChartColors : chartColors)

const donutChartLayout = {
  radius: ['30%', '62%'],
  center: ['50%', '42%'],
}

function makeDonutLabel() {
  return {
    color: chartStrongTextColor.value,
    fontSize: 9,
    fontWeight: 600,
    position: 'inside',
    align: 'center',
    verticalAlign: 'middle',
    width: 30,
    overflow: 'truncate',
    formatter: (p) => p.percent < 8 ? '' : `${Math.round(p.percent)}%`,
  }
}

function makeTooltip() {
  return {
    backgroundColor: isHiskySkin.value ? '#ffffff' : STEEL,
    borderColor: isHiskySkin.value ? 'rgba(12,94,108,0.14)' : 'rgba(255,255,255,0.08)',
    textStyle: {
      color: isHiskySkin.value ? '#12313A' : PAPER,
      fontFamily: 'var(--font-body)',
    },
  }
}

// ---- Computed: pulse bar metrics ----
const pulseMetrics = computed(() => {
  const s = props.summary
  const submissionRate = s.working_days_this_month > 0 && s.active_employees > 0
    ? Math.round(s.total_reports_this_month / (s.active_employees * s.working_days_this_month) * 100)
    : 0

  // Top-2 project concentration
  const breakdown = s.project_breakdown || []
  const top2Hours = breakdown.slice(0, 2).reduce((sum, p) => sum + p.hours, 0)
  const totalHours = s.total_hours_this_month || 1
  const concentration = Math.round(top2Hours / totalHours * 100)

  // Per-employee daily average
  const avgDaily = (s.working_days_this_month > 0 && s.active_employees > 0)
    ? Math.round(s.total_hours_this_month / (s.active_employees * s.working_days_this_month) * 10) / 10
    : 0

  return {
    submissionRate: Math.min(submissionRate, 100),
    avgDaily,
    concentration,
  }
})

// ---- Chart renderers ----

function renderTrendChart() {
  if (!trendChartRef.value || !props.summary?.daily_trend?.length) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const data = props.summary.daily_trend
  trendChart.setOption({
    tooltip: { ...makeTooltip(), trigger: 'axis' },
    grid: { left: 16, right: 16, top: 16, bottom: 8 },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.date.slice(5)),
      axisLine: { lineStyle: { color: chartLineColor.value } },
      axisLabel: { color: chartTextColor.value, fontSize: 11 },
    },
    yAxis: {
      type: 'value', name: 'h',
      splitLine: { lineStyle: { color: chartSplitColor.value } },
      axisLabel: { color: chartTextColor.value, fontSize: 11 },
    },
    series: [{
      data: data.map((d) => d.hours),
      type: 'bar',
      itemStyle: { color: isHiskySkin.value ? '#18A7A8' : BRASS, borderRadius: [4, 4, 0, 0] },
      barWidth: 14,
    }],
  })
}

function renderWorkTypeChart() {
  if (!workTypeChartRef.value || !props.summary?.work_type_breakdown?.length) return
  if (!workTypeChart) workTypeChart = echarts.init(workTypeChartRef.value)

  const data = props.summary.work_type_breakdown
  workTypeChart.setOption({
    tooltip: { ...makeTooltip(), trigger: 'item', formatter: '{b}: {c}h ({d}%)' },
    legend: {
      orient: 'horizontal', bottom: 2, left: 'center',
      textStyle: { color: chartTextColor.value, fontSize: 10 },
      itemWidth: 8, itemHeight: 8, itemGap: 12,
    },
    series: [{
      type: 'pie',
      ...donutChartLayout,
      avoidLabelOverlap: true,
      itemStyle: { borderColor: chartPanelColor.value, borderWidth: 2 },
      label: makeDonutLabel(),
      labelLayout: { hideOverlap: true },
      labelLine: { show: false },
      data: data.map((w, i) => ({
        name: w.display, value: w.hours,
        itemStyle: { color: activeChartColors.value[i % activeChartColors.value.length] },
      })),
    }],
  })
}

function renderDepartmentChart() {
  if (!departmentChartRef.value || !props.summary?.employee_breakdown?.length) return
  if (!departmentChart) departmentChart = echarts.init(departmentChartRef.value)

  // Aggregate employee_breakdown by department_name
  const deptMap = {}
  props.summary.employee_breakdown.forEach((e) => {
    const name = e.department_name || '未分配'
    if (!deptMap[name]) deptMap[name] = 0
    deptMap[name] += e.hours
  })
  const data = Object.entries(deptMap)
    .map(([name, hours]) => ({ name, hours }))
    .sort((a, b) => b.hours - a.hours)

  departmentChart.setOption({
    tooltip: { ...makeTooltip(), trigger: 'item', formatter: '{b}: {c}h ({d}%)' },
    legend: {
      orient: 'horizontal', bottom: 2, left: 'center',
      textStyle: { color: chartTextColor.value, fontSize: 10 },
      itemWidth: 8, itemHeight: 8, itemGap: 12,
    },
    series: [{
      type: 'pie',
      ...donutChartLayout,
      avoidLabelOverlap: true,
      itemStyle: { borderColor: chartPanelColor.value, borderWidth: 2 },
      label: makeDonutLabel(),
      labelLayout: { hideOverlap: true },
      labelLine: { show: false },
      data: data.map((d, i) => ({
        name: d.name, value: d.hours,
        itemStyle: { color: activeChartColors.value[i % activeChartColors.value.length] },
      })),
    }],
  })
}

function renderProjectChart() {
  if (!projectChartRef.value || !props.summary?.project_breakdown?.length) return
  if (!projectChart) projectChart = echarts.init(projectChartRef.value)

  const data = props.summary.project_breakdown.filter((p) => p.project_id)
  projectChart.setOption({
    tooltip: { ...makeTooltip(), trigger: 'item', formatter: '{b}: {c}h ({d}%)' },
    legend: {
      orient: 'horizontal', bottom: 2, left: 'center',
      textStyle: { color: chartTextColor.value, fontSize: 10 },
      itemWidth: 8, itemHeight: 8, itemGap: 12,
    },
    series: [{
      type: 'pie',
      ...donutChartLayout,
      avoidLabelOverlap: true,
      itemStyle: { borderColor: chartPanelColor.value, borderWidth: 2 },
      label: makeDonutLabel(),
      labelLayout: { hideOverlap: true },
      labelLine: { show: false },
      data: data.map((p, i) => ({
        name: p.project_name, value: p.hours,
        itemStyle: { color: activeChartColors.value[i % activeChartColors.value.length] },
      })),
    }],
  })
}

// ---- Lifecycle ----

function handleResize() {
  trendChart?.resize()
  workTypeChart?.resize()
  departmentChart?.resize()
  projectChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderTrendChart()
    renderWorkTypeChart()
    renderDepartmentChart()
    renderProjectChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  workTypeChart?.dispose()
  departmentChart?.dispose()
  projectChart?.dispose()
})

watch(() => props.summary, () => {
  nextTick(() => {
    renderTrendChart()
    renderWorkTypeChart()
    renderDepartmentChart()
    renderProjectChart()
  })
}, { deep: true })

// Paginate health cards
const healthPage = ref(0)
const cardsPerPage = 4
const showAllCards = ref(false)

const pagedProjects = computed(() => {
  const list = props.summary?.project_breakdown || []
  if (showAllCards.value || list.length <= cardsPerPage) return list
  return list.slice(0, cardsPerPage)
})

const hasMoreCards = computed(() => {
  return (props.summary?.project_breakdown?.length || 0) > cardsPerPage
})

const summaryAlerts = computed(() => props.summary?.alerts || [])
const departmentRows = computed(() => props.summary?.department_breakdown || [])
const workTypeRows = computed(() => props.summary?.work_type_structure || [])

function isNavigableAlert(alert) {
  return alert.action_view === 'employee' && props.canViewEmployee
}

function navigateAlert(alert) {
  if (!isNavigableAlert(alert)) return
  emit('navigate', {
    view: alert.action_view,
    employeeId: alert.employee_id || null,
  })
}

function formatPct(value) {
  return value || value === 0 ? `${Math.round(value)}%` : '待刷新'
}

function displayValue(value, fallback = '待刷新') {
  return value || value === 0 ? value : fallback
}
</script>

<template>
  <div class="overview-tab" :class="'overview-' + variant">
    <!-- ---- Pulse bars ---- -->
    <div class="pulse-row">
      <div class="pulse-item">
        <span class="pulse-label">日志提交率</span>
        <div class="pulse-track">
          <div
            class="pulse-fill"
            :class="pulseMetrics.submissionRate >= 80 ? 'ok' : pulseMetrics.submissionRate >= 60 ? 'warn' : 'low'"
            :style="{ width: pulseMetrics.submissionRate + '%' }"
          />
        </div>
        <span class="pulse-value">{{ pulseMetrics.submissionRate }}%</span>
      </div>
      <div class="pulse-item">
        <span class="pulse-label">人均日工时</span>
        <div class="pulse-track">
          <div
            class="pulse-fill"
            :class="pulseMetrics.avgDaily >= 6 ? 'ok' : pulseMetrics.avgDaily >= 4 ? 'warn' : 'low'"
            :style="{ width: Math.min(pulseMetrics.avgDaily / 10 * 100, 100) + '%' }"
          />
        </div>
        <span class="pulse-value">{{ pulseMetrics.avgDaily }}h</span>
      </div>
      <div class="pulse-item">
        <span class="pulse-label">项目集中度</span>
        <div class="pulse-track">
          <div
            class="pulse-fill"
            :class="pulseMetrics.concentration <= 70 ? 'ok' : pulseMetrics.concentration <= 85 ? 'warn' : 'low'"
            :style="{ width: pulseMetrics.concentration + '%' }"
          />
        </div>
        <span class="pulse-value">前2={{ pulseMetrics.concentration }}%</span>
      </div>
    </div>

    <!-- ---- Alerts ---- -->
    <section class="alerts-section" aria-label="异常提醒">
      <div class="alerts-header">
        <div>
          <h3 class="alerts-title">异常提醒</h3>
          <p class="alerts-subtitle">基于当前已有日志生成，单日数据优先检查质量、负载与资源集中度。</p>
        </div>
        <span class="alerts-count">{{ summaryAlerts.length }} 项</span>
      </div>

      <div class="alerts-grid">
        <article
          v-for="alert in summaryAlerts"
          :key="alert.title + alert.metric"
          class="alert-card"
          :class="'alert-' + alert.level"
        >
          <div class="alert-topline">
            <span class="alert-level">{{ alert.level === 'ok' ? '正常' : alert.level === 'critical' ? '重点' : alert.level === 'warning' ? '关注' : '提示' }}</span>
            <span class="alert-metric">{{ alert.metric }}</span>
          </div>
          <h4 class="alert-title">{{ alert.title }}</h4>
          <p class="alert-message">{{ alert.message }}</p>
          <button
            v-if="isNavigableAlert(alert)"
            type="button"
            class="alert-action alert-action-link"
            @click="navigateAlert(alert)"
          >
            {{ alert.action }}
          </button>
          <p v-else class="alert-action">{{ alert.action }}</p>
        </article>
      </div>
    </section>

    <!-- ---- Charts ---- -->
    <div class="charts-grid">
      <div class="chart-card chart-trend">
        <h3 class="chart-title">每日工时趋势 (近 30 天)</h3>
        <div ref="trendChartRef" class="chart-body" />
      </div>
      <div class="chart-card chart-worktype">
        <h3 class="chart-title">工作类型分布 (本月)</h3>
        <div ref="workTypeChartRef" class="chart-body" />
      </div>
      <div class="chart-card chart-department">
        <h3 class="chart-title">部门工时分布 (本月)</h3>
        <div ref="departmentChartRef" class="chart-body" />
      </div>
      <div class="chart-card chart-project">
        <h3 class="chart-title">项目工时分布 (本月)</h3>
        <div ref="projectChartRef" class="chart-body" />
      </div>
    </div>

    <!-- ---- Work type structure ---- -->
    <section class="type-structure-section">
      <div class="health-header">
        <div>
          <h3 class="chart-title" style="margin-bottom: 4px;">工作类型结构</h3>
          <p class="section-subtitle">观察投入是否过度集中在会议、其他或单一工作类型上。</p>
        </div>
      </div>

      <div v-if="workTypeRows.length" class="type-structure-grid">
        <article
          v-for="item in workTypeRows"
          :key="item.type"
          class="type-card"
          :class="'type-status-' + (item.structure_status || 'ok')"
        >
          <div class="type-card-head">
            <div>
              <span class="type-name">{{ item.display }}</span>
              <span class="type-label">{{ item.structure_label || '观察' }}</span>
            </div>
            <span class="type-score">{{ displayValue(item.structure_score) }}</span>
          </div>

          <div class="type-share-row">
            <div class="type-share-track">
              <div class="type-share-fill" :style="{ width: item.percentage + '%' }" />
            </div>
            <span>{{ item.percentage }}%</span>
          </div>

          <div class="type-metrics">
            <div>
              <strong>{{ item.hours }}</strong>
              <span>工时</span>
            </div>
            <div>
              <strong>{{ item.employee_count }}</strong>
              <span>人员</span>
            </div>
            <div>
              <strong>{{ item.project_count }}</strong>
              <span>项目</span>
            </div>
            <div>
              <strong>{{ displayValue(item.avg_hours_per_employee) }}</strong>
              <span>人均/日</span>
            </div>
          </div>

          <div class="type-footer">
            <span>{{ item.department_count }} 个部门</span>
            <span>{{ item.entry_count }} 条记录</span>
          </div>

          <div class="type-tags">
            <span
              v-for="tag in item.risk_tags || ['结构稳定']"
              :key="tag"
              class="type-tag"
            >
              {{ tag }}
            </span>
          </div>
        </article>
      </div>
      <div v-else class="health-empty">暂无工作类型数据</div>
    </section>

    <!-- ---- Department load ---- -->
    <section class="dept-load-section">
      <div class="health-header">
        <div>
          <h3 class="chart-title" style="margin-bottom: 4px;">部门效率与负载</h3>
          <p class="section-subtitle">用人均日工时、项目覆盖和投入集中度观察部门状态。</p>
        </div>
      </div>

      <div v-if="departmentRows.length" class="dept-load-list">
        <article
          v-for="dept in departmentRows"
          :key="dept.department_id || dept.department_name"
          class="dept-load-card"
          :class="'dept-status-' + (dept.load_status || 'ok')"
        >
          <div class="dept-main">
            <div class="dept-heading">
              <span class="dept-name">{{ dept.department_name }}</span>
              <span class="dept-badge">{{ dept.load_label || '观察' }}</span>
            </div>
            <div class="dept-score-line">
              <span class="dept-score">{{ displayValue(dept.load_score) }}</span>
              <span class="dept-score-label">负载分</span>
              <div class="dept-score-track">
                <div class="dept-score-fill" :style="{ width: (dept.load_score || 0) + '%' }" />
              </div>
            </div>
          </div>

          <div class="dept-metrics">
            <div>
              <strong>{{ dept.hours }}</strong>
              <span>工时</span>
            </div>
            <div>
              <strong>{{ dept.employee_count }}</strong>
              <span>人员</span>
            </div>
            <div>
              <strong>{{ dept.project_count }}</strong>
              <span>项目</span>
            </div>
            <div>
              <strong>{{ displayValue(dept.avg_hours_per_employee) }}</strong>
              <span>人均/日</span>
            </div>
          </div>

          <div class="dept-signals">
            <div class="dept-signal">
              <span>主项目</span>
              <strong>{{ dept.top_project || '暂无' }} {{ formatPct(dept.top_project_percentage) }}</strong>
            </div>
            <div class="dept-signal">
              <span>主类型</span>
              <strong>{{ dept.top_work_type || '暂无' }} {{ formatPct(dept.top_work_type_percentage) }}</strong>
            </div>
          </div>

          <div class="dept-tags">
            <span
              v-for="tag in dept.risk_tags || ['负载稳定']"
              :key="tag"
              class="dept-tag"
            >
              {{ tag }}
            </span>
          </div>
        </article>
      </div>
      <div v-else class="health-empty">暂无部门数据</div>
    </section>

    <!-- ---- Project health cards ---- -->
    <div class="health-section">
      <div class="health-header">
        <h3 class="chart-title" style="margin-bottom: 0;">项目健康一览</h3>
        <el-button
          v-if="hasMoreCards"
          size="small"
          text
          @click="showAllCards = !showAllCards"
        >
          {{ showAllCards ? '收起' : '查看全部 (' + summary.project_breakdown.length + ')' }}
        </el-button>
      </div>
      <div v-if="pagedProjects.length" class="health-cards">
        <div
          v-for="p in pagedProjects"
          :key="p.project_id || p.project_name"
          class="health-card"
          :class="'hc-status-' + (p.health_status || 'ok')"
        >
          <div class="hc-header">
            <div class="hc-title-wrap">
              <span class="hc-name">{{ p.project_name }}</span>
              <span class="hc-code" v-if="p.project_code">{{ p.project_code }}</span>
            </div>
            <span class="hc-health-badge">{{ p.health_label || '观察' }}</span>
          </div>

          <div class="hc-score-row">
            <div>
              <span class="hc-score">{{ displayValue(p.health_score) }}</span>
              <span class="hc-score-label">健康分</span>
            </div>
            <div class="hc-score-track">
              <div
                class="hc-score-fill"
                :style="{ width: (p.health_score || 0) + '%' }"
              />
            </div>
          </div>

          <div class="hc-stats">
            <div class="hc-stat">
              <span class="hc-stat-val">{{ p.hours }}</span>
              <span class="hc-stat-label">工时 (h)</span>
            </div>
            <div class="hc-stat">
              <span class="hc-stat-val">{{ p.employee_count || '-' }}</span>
              <span class="hc-stat-label">人数</span>
            </div>
            <div class="hc-stat">
              <span class="hc-stat-val">{{ displayValue(p.avg_hours_per_employee) }}</span>
              <span class="hc-stat-label">人均/日</span>
            </div>
          </div>

          <div class="hc-signals">
            <div class="hc-signal">
              <span>主类型</span>
              <strong>{{ p.top_work_type || '待刷新' }} {{ formatPct(p.top_work_type_percentage) }}</strong>
            </div>
            <div class="hc-signal">
              <span>单人占比</span>
              <strong>{{ formatPct(p.dominant_employee_percentage) }}</strong>
            </div>
          </div>

          <div class="hc-bar-wrapper">
            <div
              class="hc-bar"
              :style="{ width: p.percentage + '%' }"
            />
          </div>

          <div class="hc-risks">
            <span
              v-for="tag in p.risk_tags || ['节奏正常']"
              :key="tag"
              class="hc-risk-tag"
            >
              {{ tag }}
            </span>
          </div>

          <div class="hc-footer">
            <span class="hc-entries">{{ p.entry_count }} 条记录</span>
            <span>{{ p.percentage }}% 总投入</span>
          </div>
        </div>
      </div>
      <div v-else class="health-empty">暂无项目数据</div>
    </div>
  </div>
</template>

<style scoped>
/* ---- Pulse bars ---- */
.pulse-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.pulse-item {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.pulse-label {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.4);
  white-space: nowrap;
  width: 72px;
  flex-shrink: 0;
}

.pulse-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.pulse-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s var(--ease-out);
}

.pulse-fill.ok { background: var(--sage); }
.pulse-fill.warn { background: var(--brass); }
.pulse-fill.low { background: var(--vermilion); }

.pulse-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.6);
  width: 60px;
  text-align: right;
  flex-shrink: 0;
}

/* ---- Alerts ---- */
.alerts-section {
  margin-bottom: var(--space-5);
  padding: var(--space-5);
  background:
    linear-gradient(135deg, rgba(200, 164, 92, 0.08), transparent 40%),
    var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
}

.alerts-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.alerts-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.72);
  margin: 0 0 4px;
}

.alerts-subtitle {
  margin: 0;
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.36);
}

.alerts-count {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--brass);
  white-space: nowrap;
}

.alerts-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.alert-card {
  position: relative;
  min-height: 148px;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.055);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.alert-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--blueprint);
}

.alert-critical::before { background: var(--vermilion); }
.alert-warning::before { background: var(--brass); }
.alert-ok::before { background: var(--sage); }

.alert-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.alert-level {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.48);
  letter-spacing: 0.08em;
}

.alert-metric {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  line-height: 1;
  color: var(--paper);
}

.alert-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.82);
}

.alert-message {
  margin: 0;
  min-height: 36px;
  font-size: var(--text-xs);
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.48);
}

.alert-action {
  margin: var(--space-3) 0 0;
  font-size: 11px;
  color: rgba(200, 164, 92, 0.78);
}

.alert-action-link {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  text-align: left;
}

.alert-action-link:hover,
.alert-action-link:focus-visible {
  color: var(--brass);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.alert-action-link:focus-visible {
  outline: 1px solid rgba(200, 164, 92, 0.7);
  outline-offset: 3px;
}

/* ---- Charts grid ---- */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 300px 300px;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.chart-card {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
}

.chart-trend { grid-column: 1; grid-row: 1; }
.chart-worktype { grid-column: 2; grid-row: 1; }
.chart-department { grid-column: 1; grid-row: 2; }
.chart-project { grid-column: 2; grid-row: 2; }

.chart-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.5px;
  margin-bottom: var(--space-2);
}

.chart-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ---- Work type structure ---- */
.type-structure-section {
  margin-bottom: var(--space-6);
  padding: var(--space-5);
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
}

.type-structure-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.type-card {
  position: relative;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.type-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: var(--sage);
}

.type-status-warning::before { background: var(--brass); }
.type-status-critical::before { background: var(--vermilion); }
.type-status-info::before { background: var(--blueprint); }

.type-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.type-name {
  display: block;
  font-size: var(--text-sm);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.82);
}

.type-label {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.type-score {
  font-family: var(--font-mono);
  font-size: 26px;
  line-height: 1;
  font-weight: 300;
  color: var(--paper);
}

.type-share-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.58);
}

.type-share-track {
  height: 7px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.type-share-fill {
  height: 100%;
  min-width: 2px;
  background: linear-gradient(90deg, var(--blueprint), var(--brass));
  border-radius: 2px;
  transition: width 0.6s var(--ease-out);
}

.type-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.type-metrics div {
  min-width: 0;
}

.type-metrics strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: 400;
  color: var(--brass);
}

.type-metrics span {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.type-footer {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.28);
}

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.type-tag {
  padding: 3px 7px;
  border: 1px solid rgba(125, 155, 118, 0.2);
  border-radius: 3px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.52);
  background: rgba(125, 155, 118, 0.07);
}

/* ---- Department load ---- */
.dept-load-section {
  margin-bottom: var(--space-6);
  padding: var(--space-5);
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
}

.section-subtitle {
  margin: 0;
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.36);
}

.dept-load-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

.dept-load-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(180px, 1.2fr) minmax(280px, 1.4fr) minmax(260px, 1.2fr) minmax(140px, 0.8fr);
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.dept-load-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--sage);
}

.dept-status-warning::before { background: var(--brass); }
.dept-status-critical::before { background: var(--vermilion); }
.dept-status-info::before { background: var(--blueprint); }

.dept-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.dept-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-sm);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.82);
}

.dept-badge {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--sage);
}

.dept-status-warning .dept-badge { color: var(--brass); }
.dept-status-critical .dept-badge { color: var(--vermilion); }
.dept-status-info .dept-badge { color: var(--blueprint); }

.dept-score-line {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: var(--space-2);
}

.dept-score {
  font-family: var(--font-mono);
  font-size: 24px;
  line-height: 1;
  color: var(--paper);
}

.dept-score-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.dept-score-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.dept-score-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--vermilion), var(--brass), var(--sage));
  border-radius: 2px;
  transition: width 0.6s var(--ease-out);
}

.dept-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.dept-metrics div {
  min-width: 0;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.035);
  border-radius: 3px;
}

.dept-metrics strong {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: 400;
  color: var(--brass);
}

.dept-metrics span {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.dept-signals {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  min-width: 0;
}

.dept-signal {
  min-width: 0;
}

.dept-signal span {
  display: block;
  margin-bottom: 4px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.28);
}

.dept-signal strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.68);
}

.dept-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.dept-tag {
  padding: 3px 7px;
  border: 1px solid rgba(74, 144, 164, 0.2);
  border-radius: 3px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.52);
  background: rgba(74, 144, 164, 0.07);
}

/* ---- Health cards ---- */
.health-section {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: var(--space-5);
}

.health-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.health-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.health-card {
  position: relative;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  transition: border-color var(--duration-fast) var(--ease-out);
  overflow: hidden;
}

.health-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--sage);
}

.hc-status-warning::before { background: var(--brass); }
.hc-status-critical::before { background: var(--vermilion); }
.hc-status-info::before { background: var(--blueprint); }

.hc-status-warning .hc-health-badge { color: var(--brass); }
.hc-status-critical .hc-health-badge { color: var(--vermilion); }
.hc-status-info .hc-health-badge { color: var(--blueprint); }

.health-card:hover {
  border-color: rgba(200, 164, 92, 0.2);
}

.hc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.hc-title-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.hc-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hc-code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.hc-health-badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--sage);
}

.hc-score-row {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: end;
  gap: var(--space-3);
}

.hc-score {
  font-family: var(--font-mono);
  font-size: 28px;
  line-height: 1;
  font-weight: 300;
  color: var(--paper);
}

.hc-score-label {
  margin-left: 6px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.32);
}

.hc-score-track {
  height: 7px;
  margin-bottom: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.hc-score-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--vermilion), var(--brass), var(--sage));
  border-radius: 2px;
  transition: width 0.6s var(--ease-out);
}

.hc-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.hc-stat {
  display: flex;
  flex-direction: column;
}

.hc-stat-val {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 300;
  color: var(--brass);
}

.hc-stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.hc-signals {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.hc-signal {
  min-width: 0;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.035);
  border-radius: 3px;
}

.hc-signal span {
  display: block;
  margin-bottom: 3px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.28);
}

.hc-signal strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.68);
}

.hc-bar-wrapper {
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.hc-bar {
  height: 100%;
  background: var(--brass);
  border-radius: 2px;
  transition: width 0.6s var(--ease-out);
  min-width: 2px;
}

.hc-risks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.hc-risk-tag {
  padding: 3px 7px;
  border: 1px solid rgba(200, 164, 92, 0.18);
  border-radius: 3px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.52);
  background: rgba(200, 164, 92, 0.06);
}

.hc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
}

.hc-entries {
  color: inherit;
}

.health-empty {
  padding: var(--space-8);
  text-align: center;
  color: rgba(255, 255, 255, 0.2);
  font-size: var(--text-sm);
}

/* ---- Hisky light clinical skin ---- */
.overview-hisky {
  color: #15343d;
}

.overview-hisky .pulse-item,
.overview-hisky .alerts-section,
.overview-hisky .chart-card,
.overview-hisky .type-structure-section,
.overview-hisky .dept-load-section,
.overview-hisky .health-section {
  background: rgba(255, 255, 255, 0.88);
  border-color: rgba(12, 94, 108, 0.1);
  box-shadow: 0 12px 28px rgba(7, 43, 52, 0.06);
}

.overview-hisky .alerts-section {
  background:
    linear-gradient(135deg, rgba(24, 167, 168, 0.08), transparent 42%),
    rgba(255, 255, 255, 0.9);
}

.overview-hisky .pulse-label,
.overview-hisky .alerts-subtitle,
.overview-hisky .section-subtitle,
.overview-hisky .kpi-label,
.overview-hisky .alert-message,
.overview-hisky .dept-score-label,
.overview-hisky .hc-score-label,
.overview-hisky .hc-stat-label,
.overview-hisky .type-metrics span,
.overview-hisky .dept-metrics span {
  color: rgba(21, 52, 61, 0.5);
}

.overview-hisky .pulse-track,
.overview-hisky .dept-score-track,
.overview-hisky .hc-score-track,
.overview-hisky .hc-bar-wrapper,
.overview-hisky .type-share-track {
  background: rgba(12, 94, 108, 0.08);
}

.overview-hisky .pulse-value,
.overview-hisky .alerts-count,
.overview-hisky .alert-metric,
.overview-hisky .type-score,
.overview-hisky .dept-score,
.overview-hisky .hc-score {
  color: #12313a;
}

.overview-hisky .alerts-title,
.overview-hisky .chart-title,
.overview-hisky .type-name,
.overview-hisky .dept-name,
.overview-hisky .hc-name,
.overview-hisky .alert-title {
  color: rgba(18, 49, 58, 0.86);
}

.overview-hisky .alert-card,
.overview-hisky .type-card,
.overview-hisky .dept-load-card,
.overview-hisky .health-card {
  background: #fbfefd;
  border-color: rgba(12, 94, 108, 0.08);
}

.overview-hisky .alert-card::before,
.overview-hisky .type-status-info::before,
.overview-hisky .dept-status-info::before,
.overview-hisky .hc-status-info::before {
  background: #4c9ab0;
}

.overview-hisky .alert-warning::before,
.overview-hisky .type-status-warning::before,
.overview-hisky .dept-status-warning::before,
.overview-hisky .hc-status-warning::before {
  background: #e8a356;
}

.overview-hisky .alert-critical::before,
.overview-hisky .type-status-critical::before,
.overview-hisky .dept-status-critical::before,
.overview-hisky .hc-status-critical::before {
  background: #c9524c;
}

.overview-hisky .alert-ok::before {
  background: #67a87d;
}

.overview-hisky .alert-level,
.overview-hisky .type-label,
.overview-hisky .type-footer,
.overview-hisky .dept-signal span,
.overview-hisky .hc-signal span,
.overview-hisky .hc-footer {
  color: rgba(21, 52, 61, 0.42);
}

.overview-hisky .alert-action,
.overview-hisky .alert-action-link,
.overview-hisky .type-metrics strong,
.overview-hisky .dept-metrics strong,
.overview-hisky .hc-stat-val {
  color: #0b8491;
}

.overview-hisky .alert-action-link:hover,
.overview-hisky .alert-action-link:focus-visible {
  color: #086b76;
}

.overview-hisky .dept-metrics div,
.overview-hisky .hc-signal {
  background: rgba(12, 94, 108, 0.055);
}

.overview-hisky .dept-signal strong,
.overview-hisky .hc-signal strong {
  color: rgba(18, 49, 58, 0.72);
}

.overview-hisky .type-share-fill {
  background: linear-gradient(90deg, #18a7a8, #8bd7ca);
}

.overview-hisky .dept-score-fill,
.overview-hisky .hc-score-fill {
  background: linear-gradient(90deg, #c9524c, #e8a356, #67a87d);
}

.overview-hisky .hc-bar {
  background: #18a7a8;
}

.overview-hisky .type-tag,
.overview-hisky .dept-tag,
.overview-hisky .hc-risk-tag {
  background: rgba(24, 167, 168, 0.09);
  border-color: rgba(11, 132, 145, 0.24);
  color: #1f5360;
  font-weight: 600;
}

.overview-hisky .health-empty {
  color: rgba(21, 52, 61, 0.35);
}

/* ---- Responsive ---- */
@media (max-width: 1000px) {
  .alerts-grid { grid-template-columns: repeat(2, 1fr); }
  .type-structure-grid { grid-template-columns: repeat(2, 1fr); }
  .pulse-row { grid-template-columns: 1fr; }
  .dept-load-card {
    grid-template-columns: 1fr 1fr;
  }
  .dept-tags { justify-content: flex-start; }
}

@media (max-width: 720px) {
  .charts-grid {
    grid-template-columns: 1fr;
    grid-template-rows: 280px 280px 280px 280px;
  }
  .chart-trend { grid-column: 1; grid-row: 1; }
  .chart-worktype { grid-column: 1; grid-row: 2; }
  .chart-department { grid-column: 1; grid-row: 3; }
  .chart-project { grid-column: 1; grid-row: 4; }
  .health-cards { grid-template-columns: 1fr; }
  .alerts-grid { grid-template-columns: 1fr; }
  .type-structure-grid { grid-template-columns: 1fr; }
  .alerts-header { flex-direction: column; }
  .dept-load-card {
    grid-template-columns: 1fr;
  }
  .dept-metrics,
  .dept-signals {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
