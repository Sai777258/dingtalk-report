<script setup>
/**
 * EmployeeSummary — employee-level aggregation panel.
 *
 * Renders KPI cards (hours, projects, work types) + work type distribution
 * computed across all of the employee's projects.
 *
 * Props:
 *   employee   Object   { total_hours, project_count, department_name, projects[{ work_types[] }] }
 */
import { computed } from 'vue'
import { typeTagStyle } from '@/utils/typeColors'

const props = defineProps({
  employee: { type: Object, required: true },
})

// Aggregate work types across all projects
const workTypeSummary = computed(() => {
  const map = {}
  if (!props.employee.projects) return []
  props.employee.projects.forEach(p => {
    if (!p.work_types) return
    p.work_types.forEach(wt => {
      if (!map[wt.type]) {
        map[wt.type] = { type: wt.type, display: wt.display, hours: 0 }
      }
      map[wt.type].hours += wt.hours
    })
  })
  return Object.values(map).sort((a, b) => b.hours - a.hours)
})

const workTypeCount = computed(() => workTypeSummary.value.length)
</script>

<template>
  <div class="emp-summary">
    <!-- ---- KPI cards ---- -->
    <div class="summary-kpi-row">
      <div class="summary-kpi">
        <span class="kpi-val">{{ employee.total_hours.toFixed(1) }}</span>
        <span class="kpi-label">总工时 (h)</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ employee.project_count }}</span>
        <span class="kpi-label">参与项目数</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ workTypeCount }}</span>
        <span class="kpi-label">工作类型</span>
      </div>
    </div>

    <!-- ---- Work type distribution ---- -->
    <div class="summary-section" v-if="workTypeSummary.length">
      <h5 class="section-label">工作类型分布</h5>
      <div class="work-type-strip">
        <span
          v-for="wt in workTypeSummary"
          :key="wt.type"
          class="type-tag"
          :style="typeTagStyle(wt.type)"
        >
          {{ wt.display }} {{ wt.hours.toFixed(1) }}h
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.emp-summary {
  background: rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-5);
  margin-bottom: var(--space-5);
}

/* ---- KPI cards ---- */
.summary-kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.summary-kpi-row:last-child {
  margin-bottom: 0;
}

.summary-kpi {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-val {
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-weight: 300;
  color: var(--brass);
}

.kpi-label {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.35);
}

/* ---- Section label ---- */
.summary-section {
  margin-top: var(--space-3);
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

/* ---- Work type tags ---- */
.work-type-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.type-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  border: 1px solid;
}
</style>
