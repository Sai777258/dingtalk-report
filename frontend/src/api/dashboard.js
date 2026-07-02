/**
 * Dashboard API — aggregation endpoints.
 */
import api from './index'

/** Get full dashboard summary (hours, projects, employees, trends). */
export function getDashboard() {
  return api.get('/stats/dashboard/').then((r) => r.data)
}

/** Get dashboard data for a specific view perspective. */
export function getDashboardByView(view, params = {}) {
  return api.get('/stats/dashboard/', { params: { view, ...params } }).then((r) => r.data)
}

/** Get work entry list (supports project_id / employee_id / date filters). */
export function getWorkEntries(params = {}) {
  return api.get('/stats/entries/', { params }).then((r) => r.data)
}
