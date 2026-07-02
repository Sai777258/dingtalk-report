<script setup>
/**
 * ProjectSummary — project-level aggregation panel.
 *
 * Renders KPI cards (hours, employees, departments) + work type distribution
 * from a pre-computed project object returned by the backend.
 *
 * Props:
 *   project   Object   { total_hours, employee_count, department_count, work_types[] }
 */
import { typeTagStyle } from '@/utils/typeColors'

defineProps({
  project: { type: Object, required: true },
})
</script>

<template>
  <div class="proj-summary">
    <!-- ---- KPI cards ---- -->
    <div class="summary-kpi-row">
      <div class="summary-kpi">
        <span class="kpi-val">{{ project.total_hours }}</span>
        <span class="kpi-label">总工时 (h)</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ project.employee_count }}</span>
        <span class="kpi-label">参与人数</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ project.department_count }}</span>
        <span class="kpi-label">涉及部门</span>
      </div>
    </div>

    <!-- ---- Work type distribution ---- -->
    <div class="summary-section" v-if="project.work_types?.length">
      <h5 class="section-label">工作类型分布</h5>
      <div class="work-type-strip">
        <span
          v-for="wt in project.work_types"
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
.proj-summary {
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
