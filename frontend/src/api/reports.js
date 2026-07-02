/**
 * Work report API — list and detail.
 */
import api from './index'

/** Get paginated report list. Supports: page, page_size, date_from, date_to, username, department, search. */
export function getReports(params = {}) {
  return api.get('/reports/', { params }).then((r) => r.data)
}

/** Get single report detail with contents. */
export function getReportDetail(id) {
  return api.get(`/reports/${id}/`).then((r) => r.data)
}
