/**
 * Auth store — manages JWT token, user profile, and login/logout.
 *
 * Token is persisted to localStorage so sessions survive page refresh.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { demoLogin, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // ---- State ----
  const token = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // ---- Getters ----
  const isAuthenticated = computed(() => !!token.value)

  const userRole = computed(() => user.value?.role || null)

  const isAdmin = computed(() => user.value?.role === 'admin')
  const isDeptManagerL1 = computed(() => user.value?.role === 'dept_manager_l1')
  const isDeptManagerL2 = computed(() => user.value?.role === 'dept_manager_l2')
  const isProjectManager = computed(() => user.value?.role === 'project_manager')
  const isEmployee = computed(() => user.value?.role === 'employee')
  const isAnyManager = computed(() =>
    isDeptManagerL1.value || isDeptManagerL2.value || isProjectManager.value
  )

  // ---- Actions ----

  /**
   * Update tokens in state + localStorage.
   * Called by the 401 interceptor after a successful refresh.
   */
  function setTokens(access, refresh) {
    token.value = access
    localStorage.setItem('access_token', access)
    if (refresh) {
      refreshToken.value = refresh
      localStorage.setItem('refresh_token', refresh)
    }
  }

  async function login(username, password) {
    loading.value = true
    error.value = null
    try {
      const { data } = await demoLogin(username, password)
      setTokens(data.access, data.refresh)
      user.value = data.user

      return data
    } catch (err) {
      const msg =
        err.response?.data?.non_field_errors?.[0] ||
        err.response?.data?.detail ||
        '登录失败，请检查用户名和密码'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const { data } = await getCurrentUser()
      user.value = data
    } catch {
      // The 401 response interceptor handles token refresh or logout.
      // Only clear the user object here; do NOT call logout().
      user.value = null
    }
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    error.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function clearError() {
    error.value = null
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    userRole,
    isAdmin,
    isDeptManagerL1,
    isDeptManagerL2,
    isProjectManager,
    isEmployee,
    isAnyManager,
    setTokens,
    login,
    fetchUser,
    logout,
    clearError,
  }
})
