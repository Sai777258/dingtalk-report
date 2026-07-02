/**
 * Shared work-type colour map and tag style helper.
 *
 * Used by all dashboard tab components (EmployeeTab, ProjectTab, DepartmentTab)
 * to keep type colouring consistent across views.
 */

export const typeColors = {
  development: '#C8A45C',
  testing: '#4A90A4',
  meeting: '#7D9B76',
  documentation: '#8B7AA0',
  design: '#D4695A',
  other: 'rgba(255,255,255,0.3)',
}

/**
 * Return a style object for a work-type tag badge.
 *
 * Colours the border and text with the configured type colour,
 * and applies a low-opacity background tint.
 *
 * @param {string} type  Raw type key (e.g. 'development', 'testing')
 * @returns {{ background: string, borderColor: string, color: string }}
 */
export function typeTagStyle(type) {
  const c = typeColors[type] || typeColors.other
  return {
    background: c + '22',
    borderColor: c,
    color: c,
  }
}
