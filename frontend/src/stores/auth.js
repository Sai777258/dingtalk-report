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

  // ---- Actions ----
  async function login(username, password) {
    loading.value = true
    error.value = null
    try {
      const { data } = await demoLogin(username, password)
      token.value = data.access
      refreshToken.value = data.refresh
      user.value = data.user

      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)

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
      // Token expired or invalid — clear it
      logout()
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
    login,
    fetchUser,
    logout,
    clearError,
  }
})
