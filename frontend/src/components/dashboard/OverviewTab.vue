<script setup>
/**
 * OverviewTab — existing dashboard charts and project detail table.
 * Extracted from DashboardView.vue to be a tab within the new multi-view layout.
 *
 * Props: summary — the full /api/stats/dashboard/ response object
 */
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  summary: { type: Object, required: true },
})

// Chart refs
const trendChartRef = ref(null)
const projectChartRef = ref(null)
const employeeChartRef = ref(null)

let trendChart = null
let projectChart = null
let employeeChart = null

// Theme colours
const STEEL = '#1B1F2A'
const PAPER = '#F5F3EE'
const BRASS = '#C8A45C'
const BLUEPRINT = '#4A90A4'
const SAGE = '#7D9B76'
const VERMILION = '#D4695A'
const chartColors = [
  // Brass / gold family
  '#C8A45C', // brass
  '#D4B87A', // pale gold
  '#E0C78A', // champagne
  '#B8956A', // bronze
  // Blueprint / blue family
  '#4A90A4', // blueprint
  '#5EA0C0', // sky blue
  '#6BA5B8', // light steel
  '#58A0A8', // teal
  // Sage / green family
  '#7D9B76', // sage
  '#6A9478', // forest
  '#8EB89A', // mint
  // Vermilion / warm family
  '#D4695A', // vermilion
  '#E8956E', // coral
  '#C47A6B', // dusty rose
  // Purple / slate family
  '#8B7AA0', // muted purple
  '#9B8EC4', // lavender
]

function makeTooltip() {
  return {
    backgroundColor: STEEL,
    borderColor: 'rgba(255,255,255,0.08)',
    textStyle: { color: PAPER, fontFamily: 'var(--font-body)' },
  }
}

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
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 11 },
    },
    yAxis: {
      type: 'value', name: 'h',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 11 },
    },
    series: [{
      data: data.map((d) => d.hours),
      type: 'bar',
      itemStyle: { color: BRASS, borderRadius: [4, 4, 0, 0] },
      barWidth: 14,
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
      orient: 'horizontal', bottom: 8, left: 'center',
      textStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 11 },
      itemWidth: 10, itemHeight: 10, itemGap: 16,
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'], center: ['50%', '46%'],
      itemStyle: { borderColor: STEEL, borderWidth: 2 },
      label: {
        color: STEEL, fontSize: 12, fontWeight: 600,
        position: 'inside', formatter: '{d}%',
      },
      labelLine: { show: false },
      data: data.map((p, i) => ({
        name: p.project_name, value: p.hours,
        itemStyle: { color: chartColors[i % chartColors.length] },
      })),
    }],
  })
}

function renderEmployeeChart() {
  if (!employeeChartRef.value || !props.summary?.employee_breakdown?.length) return
  if (!employeeChart) employeeChart = echarts.init(employeeChartRef.value)

  const data = props.summary.employee_breakdown
  employeeChart.setOption({
    tooltip: { ...makeTooltip(), trigger: 'axis', formatter: '{b}: {c}h' },
    grid: { left: 16, right: 24, top: 8, bottom: 8 },
    xAxis: {
      type: 'value', name: 'h',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: data.map((e) => e.employee_name),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: data.map((e, i) => ({
        value: e.hours,
        itemStyle: { color: chartColors[i % chartColors.length], borderRadius: [0, 4, 4, 0] },
      })),
      barWidth: 16,
    }],
  })
}

function handleResize() {
  trendChart?.resize()
  projectChart?.resize()
  employeeChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderTrendChart()
    renderProjectChart()
    renderEmployeeChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  projectChart?.dispose()
  employeeChart?.dispose()
})

// Re-render if summary changes
watch(() => props.summary, () => {
  nextTick(() => {
    renderTrendChart()
    renderProjectChart()
    renderEmployeeChart()
  })
}, { deep: true })
</script>

<template>
  <div class="overview-tab">
    <!-- Charts -->
    <div class="charts-grid">
      <div class="chart-card chart-trend">
        <h3 class="chart-title">每日工时趋势 (近 30 天)</h3>
        <div ref="trendChartRef" class="chart-body" />
      </div>
      <div class="chart-card chart-project">
        <h3 class="chart-title">项目工时分布 (本月)</h3>
        <div ref="projectChartRef" class="chart-body" />
      </div>
      <div class="chart-card chart-employee">
        <h3 class="chart-title">人员工时排名 (本月)</h3>
        <div ref="employeeChartRef" class="chart-body" />
      </div>
    </div>

    <!-- Project detail table -->
    <div class="table-card">
      <h3 class="chart-title">项目明细</h3>
      <el-table
        :data="summary.project_breakdown"
        size="small"
        row-key="project_id"
        style="width: 100%"
      >
        <el-table-column prop="project_name" label="项目" min-width="140" />
        <el-table-column prop="project_code" label="代号" width="100" />
        <el-table-column prop="hours" label="工时 (h)" width="100" sortable />
        <el-table-column prop="entry_count" label="条目数" width="80" />
        <el-table-column prop="percentage" label="占比" width="80">
          <template #default="{ row }">{{ row.percentage }}%</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
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
.chart-project { grid-column: 2; grid-row: 1 / 3; }
.chart-employee { grid-column: 1; grid-row: 2; }

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
}

.table-card {
  background: var(--steel-light);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: var(--space-5);
}

.table-card :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: rgba(255, 255, 255, 0.7);
  --el-table-header-text-color: rgba(255, 255, 255, 0.4);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
}

.table-card :deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: var(--text-xs);
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
    grid-template-rows: 260px 260px 260px;
  }
  .chart-trend { grid-column: 1; grid-row: 1; }
  .chart-project { grid-column: 1; grid-row: 2; }
  .chart-employee { grid-column: 1; grid-row: 3; }
}
</style>
