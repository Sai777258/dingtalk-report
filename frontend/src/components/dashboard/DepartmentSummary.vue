<script setup>
/**
 * DepartmentSummary — department-level aggregation panel.
 *
 * Computes department-wide project totals and work-type breakdown
 * from the employee array returned by the department API.
 *
 * Props:
 *   employees   Array   Raw employees list from selectedDept.employees
 *   totalHours  Number  Pre-computed department total (from API)
 */
import { computed } from 'vue'
import { typeColors, typeTagStyle } from '@/utils/typeColors'

const props = defineProps({
  employees: { type: Array, required: true },
  totalHours: { type: Number, required: true },
  variant: { type: String, default: 'classic' },
})

// ---- Computed: project aggregation across all employees ----
const projectSummary = computed(() => {
  const map = {}
  for (const emp of props.employees) {
    if (!emp.projects) continue
    for (const proj of emp.projects) {
      const key = proj.project_id
      if (!map[key]) {
        map[key] = {
          project_id: proj.project_id,
          project_name: proj.project_name || '未归类',
          total_hours: 0,
          employee_count: 0,
          employee_set: new Set(),
          work_type_map: {},
          work_types: [],
        }
      }
      map[key].total_hours += proj.hours
      map[key].employee_set.add(emp.employee_id)
      map[key].employee_count = map[key].employee_set.size
      // Aggregate work types per project
      if (proj.work_types) {
        for (const wt of proj.work_types) {
          if (!map[key].work_type_map[wt.type]) {
            const entry = { type: wt.type, display: wt.display, hours: 0 }
            map[key].work_type_map[wt.type] = entry
            map[key].work_types.push(entry)
          }
          map[key].work_type_map[wt.type].hours += wt.hours
        }
      }
    }
  }
  // Sort work_types by hours desc inside each project
  const results = Object.values(map)
  for (const p of results) {
    p.work_types.sort((a, b) => b.hours - a.hours)
    delete p.work_type_map
  }
  return results.sort((a, b) => b.total_hours - a.total_hours)
})

// ---- Computed: work-type distribution across all employees/projects ----
const workTypeDistribution = computed(() => {
  const map = {}
  for (const emp of props.employees) {
    if (!emp.projects) continue
    for (const proj of emp.projects) {
      if (!proj.work_types) continue
      for (const wt of proj.work_types) {
        const key = wt.type
        if (!map[key]) {
          map[key] = { type: key, display: wt.display, hours: 0 }
        }
        map[key].hours += wt.hours
      }
    }
  }
  return Object.values(map).sort((a, b) => b.hours - a.hours)
})

// ---- Computed: stats ----
const employeeCount = computed(() => props.employees.length)
const projectCount = computed(() => projectSummary.value.length)

// Max hours for progress bar normalisation
const maxProjHours = computed(() => {
  if (!projectSummary.value.length) return 1
  return Math.max(...projectSummary.value.map((p) => p.total_hours))
})
</script>

<template>
  <div :class="['dept-summary', `dept-summary--${variant}`]">
    <!-- ---- KPI cards ---- -->
    <div class="summary-kpi-row">
      <div class="summary-kpi">
        <span class="kpi-val">{{ employeeCount }}</span>
        <span class="kpi-label">员工数</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ totalHours }}</span>
        <span class="kpi-label">总工时 (h)</span>
      </div>
      <div class="summary-kpi">
        <span class="kpi-val">{{ projectCount }}</span>
        <span class="kpi-label">参与项目</span>
      </div>
    </div>

    <!-- ---- Project hours distribution ---- -->
    <div class="summary-section" v-if="projectSummary.length">
      <h5 class="section-label">项目工时分布</h5>
      <div class="proj-list">
        <div
          v-for="p in projectSummary"
          :key="p.project_id"
          class="proj-block"
        >
          <div class="proj-row">
            <div class="proj-info">
              <span class="proj-name">{{ p.project_name }}</span>
              <span class="proj-meta">{{ p.total_hours }}h · {{ p.employee_count }}人</span>
            </div>
            <div class="proj-bar-track">
              <div
                class="proj-bar-fill"
                :style="{ width: (p.total_hours / maxProjHours * 100) + '%' }"
              />
            </div>
          </div>
          <!-- Per-project work type breakdown -->
          <div class="proj-work-types" v-if="p.work_types.length">
            <span
              v-for="wt in p.work_types"
              :key="wt.type"
              class="type-tag type-tag-sm"
              :style="typeTagStyle(wt.type)"
            >
              {{ wt.display }} {{ wt.hours.toFixed(1) }}h
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ---- Work type distribution ---- -->
    <div class="summary-section" v-if="workTypeDistribution.length">
      <h5 class="section-label">工作类型分布</h5>
      <div class="work-type-strip">
        <span
          v-for="wt in workTypeDistribution"
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
.dept-summary {
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
  margin-bottom: var(--space-3);
}

.summary-section:last-child {
  margin-bottom: 0;
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

/* ---- Project bars ---- */
.proj-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.proj-block {
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
}

.proj-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.proj-info {
  width: 160px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.proj-name {
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.7);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.proj-meta {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  font-family: var(--font-mono);
}

.proj-bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.proj-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brass), rgba(200, 164, 92, 0.4));
  border-radius: 3px;
  transition: width var(--duration-slow) var(--ease-out);
}

/* Per-project work type tags */
.proj-work-types {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
  padding-left: 4px;
}

.type-tag-sm {
  font-size: 10px;
  padding: 0 5px;
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

/* ---- Hisky light clinical skin ---- */
.dept-summary--hisky {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 251, 0.92));
  border-color: rgba(12, 94, 108, 0.1);
  box-shadow: 0 12px 28px rgba(7, 43, 52, 0.06);
}

.dept-summary--hisky .summary-kpi {
  background: #ffffff;
  border-color: rgba(12, 94, 108, 0.1);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
}

.dept-summary--hisky .kpi-val {
  color: #0b8491;
  font-weight: 400;
}

.dept-summary--hisky .kpi-label,
.dept-summary--hisky .section-label,
.dept-summary--hisky .proj-meta {
  color: rgba(21, 52, 61, 0.5);
}

.dept-summary--hisky .section-label {
  font-family: "HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.dept-summary--hisky .proj-block {
  background: #ffffff;
  border: 1px solid rgba(12, 94, 108, 0.08);
  box-shadow: 0 8px 18px rgba(7, 43, 52, 0.045);
}

.dept-summary--hisky .proj-name {
  color: #12313a;
  font-weight: 600;
}

.dept-summary--hisky .proj-bar-track {
  background: rgba(12, 94, 108, 0.08);
}

.dept-summary--hisky .proj-bar-fill {
  background: linear-gradient(90deg, #18a7a8, #8bd7ca);
}

.dept-summary--hisky .type-tag {
  background: rgba(24, 167, 168, 0.09) !important;
  border-color: rgba(11, 132, 145, 0.26) !important;
  color: #1f5360 !important;
  font-weight: 600;
}
</style>
