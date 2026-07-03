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

/** Export filtered reports as Excel (.xlsx) blob. Same filter params as getReports, minus pagination.
 *  Supports report_ids array for individual export mode (serialized as repeated params for Django getlist). */
export function exportReports(params = {}) {
  const p = new URLSearchParams()
  for (const [key, val] of Object.entries(params)) {
    if (Array.isArray(val)) {
      val.forEach(v => p.append(key, v))
    } else if (val !== '' && val != null) {
      p.append(key, String(val))
    }
  }
  return api.get('/reports/export/', {
    params: p,
    responseType: 'blob',
  }).then((r) => r.data)
}
