/**
 * Token storage and authentication helpers.
 * Tokens are persisted in localStorage so they survive page reloads.
 *
 * Keys:
 *   sad_access_token   — short-lived JWT (15 min) used for API requests
 *   sad_refresh_token  — long-lived JWT (7 days) used to obtain new access tokens
 */

import axios from 'axios'

const ACCESS_KEY = 'sad_access_token'
const REFRESH_KEY = 'sad_refresh_token'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(accessToken, refreshToken) {
  if (accessToken) localStorage.setItem(ACCESS_KEY, accessToken)
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function isAuthenticated() {
  return !!getAccessToken()
}

/**
 * Login: POST username/password to /auth/login, persist tokens.
 * Returns the response data (tokens + user info).
 */
export async function login(username, password) {
  // Get base URL from environment or config
  let baseUrl = import.meta.env.VITE_API_BASE_URL
  if (!baseUrl) {
    try {
      const res = await fetch('/config.json')
      const config = await res.json()
      baseUrl = config.apiUrl
    } catch {
      baseUrl = 'http://localhost:8000'
    }
  }

  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)

  const res = await axios.post(`${baseUrl}/auth/login`, form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })

  const { access_token: accessToken, refresh_token: refreshToken, user } = res.data
  setTokens(accessToken, refreshToken)
  return { accessToken, refreshToken, user }
}

/**
 * Logout: clear tokens from localStorage.
 */
export function logout() {
  clearTokens()
}
