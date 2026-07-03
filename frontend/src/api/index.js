/**
 * Axios instance with JWT interceptor.
 *
 * - Injects Authorization header from Pinia auth store
 * - On 401, attempts to refresh the access token using the refresh token.
 *   If refresh fails, clears token and redirects to /login.
 * - All responses go through the same instance
 */
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import { refreshToken as refreshTokenApi } from '@/api/auth'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---- Refresh token lock ----
// Prevents multiple simultaneous refresh attempts when several requests
// fail with 401 at the same time (e.g. on page load).
let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// ---- Request interceptor: attach JWT ----
api.interceptors.request.use(
  (config) => {
    const auth = useAuthStore()
    if (auth.token) {
      config.headers.Authorization = `Bearer ${auth.token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ---- Response interceptor: handle 401 with token refresh ----
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Only handle 401; skip if the request has already been retried.
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    const auth = useAuthStore()

    // No refresh token available → force logout immediately.
    if (!auth.refreshToken) {
      auth.logout()
      router.push('/login')
      return Promise.reject(error)
    }

    // If a refresh is already in progress, queue this request.
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        })
        .catch((err) => Promise.reject(err))
    }

    // Mark as retried and start refresh.
    originalRequest._retry = true
    isRefreshing = true

    try {
      const { data } = await refreshTokenApi(auth.refreshToken)
      const newAccessToken = data.access
      const newRefreshToken = data.refresh || auth.refreshToken

      auth.setTokens(newAccessToken, newRefreshToken)
      processQueue(null, newAccessToken)

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      auth.logout()
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
