/**
 * Auth API calls.
 */
import api from './index'

/**
 * Demo login — username + password → JWT tokens + user profile.
 * Only available when DINGTALK_DEMO_MODE=True on the backend.
 */
export function demoLogin(username, password) {
  return api.post('/auth/demo-login/', { username, password })
}

/**
 * Get current user profile.
 */
export function getCurrentUser() {
  return api.get('/auth/me/')
}
