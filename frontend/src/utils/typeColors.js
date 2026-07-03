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
  other: '#64748B',
  开发: '#C8A45C',
  产品开发: '#C8A45C',
  设计开发: '#C8A45C',
  测试: '#4A90A4',
  测试调试: '#4A90A4',
  调试: '#4A90A4',
  会议: '#7D9B76',
  文档: '#8B7AA0',
  文档编写: '#8B7AA0',
  设计: '#D4695A',
  其他: '#64748B',
}

function tint(color) {
  if (!color) return '#64748B22'
  if (color.startsWith('rgba') || color.startsWith('rgb')) return color
  return `${color}22`
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
    background: tint(c),
    borderColor: c,
    color: c,
  }
}
