/**
 * Auth API calls.
 */
import axios from 'axios'
import api from './index'

// Clean axios instance for token refresh — must NOT have the 401 interceptor
// to avoid infinite loop when the refresh endpoint itself returns 401.
const cleanApi = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

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

/**
 * Refresh access token using a refresh token.
 * Uses a clean axios instance (no interceptors) to avoid infinite loop.
 */
export function refreshToken(refresh) {
  return cleanApi.post('/auth/token/refresh/', { refresh })
}
