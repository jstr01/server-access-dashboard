/**
 * Shared Axios instance for the entire app.
 * Handles runtime configuration resolution, token attachment, and
 * automatic token refresh on 401 responses.
 */

import axios from 'axios'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../auth/store'

let cachedBaseUrl = ''
let _apiClient = null
let isRefreshing = false
let pendingRequests = []

export async function getApiBaseUrl() {
  if (cachedBaseUrl) return cachedBaseUrl

  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl) {
    cachedBaseUrl = envUrl
    return cachedBaseUrl
  }

  try {
    const response = await fetch('/config.json', { cache: 'no-cache' })
    const contentType = response.headers.get('content-type')
    if (response.ok && contentType && contentType.includes('application/json')) {
      const config = await response.json()
      if (config.apiUrl) {
        cachedBaseUrl = config.apiUrl
        return cachedBaseUrl
      }
    }
  } catch (e) {
    console.error('api/client: failed to load /config.json', e)
  }

  cachedBaseUrl = 'http://localhost:8000'
  console.warn('api/client: falling back to', cachedBaseUrl)
  return cachedBaseUrl
}

function redirectToLogin() {
  clearTokens()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

function createClient() {
  const c = axios.create({ baseURL: cachedBaseUrl || undefined })

  // --- Request interceptor: attach the access token ---
  c.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  // --- Response interceptor: refresh the token on 401 ---
  c.interceptors.response.use(
    (response) => response,
    async (error) => {
      const { config, response } = error
      if (!response || response.status !== 401) {
        return Promise.reject(error)
      }
      // The refresh call itself failed — nothing left to try.
      if (config.url === '/auth/refresh') {
        redirectToLogin()
        return Promise.reject(error)
      }

      const originalRequest = config
      if (!originalRequest._retry) {
        originalRequest._retry = true
      }

      const retryWith = (newAccess) => {
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return c(originalRequest)
      }

      if (!isRefreshing) {
        isRefreshing = true
        try {
          const refreshToken = getRefreshToken()
          if (!refreshToken) {
            redirectToLogin()
            throw new Error('No refresh token available')
          }
          const baseUrl = c.defaults.baseURL || (await getApiBaseUrl())
          const res = await axios.post(
            `${baseUrl}/auth/refresh`,
            {},
            {
              headers: {
                Authorization: `Bearer ${refreshToken}`,
                'Content-Type': 'application/json',
              },
            },
          )
          const { access_token: newAccess, refresh_token: newRefresh } = res.data
          setTokens(newAccess, newRefresh)

          isRefreshing = false
          const queued = pendingRequests
          pendingRequests = []
          queued.forEach((q) => q.resolve(newAccess))
          return retryWith(newAccess)
        } catch (refreshError) {
          isRefreshing = false
          redirectToLogin()
          const queued = pendingRequests
          pendingRequests = []
          queued.forEach((q) => q.reject(refreshError))
          return Promise.reject(refreshError)
        }
      }

      // A refresh is already in flight — wait for it, then retry.
      return new Promise((resolve, reject) => {
        pendingRequests.push({ resolve, reject })
      }).then((newAccess) => retryWith(newAccess))
    },
  )

  return c
}

export function getClient() {
  if (!_apiClient) {
    _apiClient = createClient()
  }
  return _apiClient
}

export async function initApiClient() {
  const baseUrl = await getApiBaseUrl()
  const client = getClient()
  client.defaults.baseURL = baseUrl
  return baseUrl
}
