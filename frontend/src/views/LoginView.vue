<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { login } from '../auth/store'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref(null)

// --- Dark mode (mirrors HomeView.vue preference logic) ---
const isDarkMode = ref(
  localStorage.getItem('darkMode') === 'true' ||
    (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches),
)

function updateHtmlClass() {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

function toggleDarkMode() {
  isDarkMode.value = !isDarkMode.value
  localStorage.setItem('darkMode', isDarkMode.value)
  updateHtmlClass()
}

async function handleSubmit() {
  if (loading.value) return
  error.value = null

  if (!username.value || !password.value) {
    error.value = 'Please enter both username and password.'
    return
  }

  loading.value = true
  try {
    await login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (err) {
    if (err.response?.status === 401) {
      error.value = 'Invalid username or password.'
    } else if (err.response) {
      error.value = `Login failed (HTTP ${err.response.status}).`
    } else if (err.request) {
      error.value = 'Cannot reach the backend. Is it running and reachable?'
    } else {
      error.value = `Login failed: ${err.message}`
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  updateHtmlClass()
})
</script>

<template>
  <div
    class="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center p-4 relative"
  >
    <!-- Dark mode toggle -->
    <button
      @click="toggleDarkMode"
      title="Toggle Dark Mode"
      class="absolute top-4 right-4 p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-900 transition-colors"
    >
      <svg
        v-if="isDarkMode"
        xmlns="http://www.w3.org/2000/svg"
        class="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        class="w-6 h-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        />
      </svg>
    </button>

    <div class="w-full max-w-sm">
      <div
        class="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 sm:p-8 border border-gray-200 dark:border-gray-700"
      >
        <!-- Logo & Title -->
        <div class="flex flex-col items-center mb-6">
          <img src="/logo.png" alt="Logo" class="h-16 w-16 mb-3" />
          <h1 class="text-xl sm:text-2xl font-mono text-gray-800 dark:text-gray-100">
            <span class="text-[#2d624a] font-bold text-2xl sm:text-3xl">S</span>erver
            <span class="text-[#2d624a] font-bold text-2xl sm:text-3xl">A</span>ccess
            <span class="text-[#2d624a] font-bold text-2xl sm:text-3xl">D</span>ashboard
          </h1>
          <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Please sign in to continue</p>
        </div>

        <!-- Error message -->
        <div
          v-if="error"
          class="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <span class="block sm:inline">{{ error }}</span>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label
              for="username"
              class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-400"
            >
              Username
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              autofocus
              :disabled="loading"
              class="w-full box-border min-h-[42px] rounded border border-gray-300 bg-white p-2 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 disabled:opacity-60"
            />
          </div>

          <div>
            <label
              for="password"
              class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-400"
            >
              Password
            </label>
            <div class="relative">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                :disabled="loading"
                class="w-full box-border min-h-[42px] rounded border border-gray-300 bg-white p-2 pr-11 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 disabled:opacity-60"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                title="Toggle password visibility"
                class="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 focus:outline-none"
              >
                <svg
                  v-if="!showPassword"
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.964-7.178z"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 3l18 18M10.586 10.586a2 2 0 002.828 2.828l-2.828-2.828z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M6.71 6.71C4.77 7.88 3.15 9.62 2.036 12.322a1.012 1.012 0 000 .639C3.423 16.49 7.36 19.5 12 19.5c1.52 0 2.97-.28 4.31-.78M9.88 9.88A9.77 9.77 0 0112 9.5c4.638 0 8.573 3.007 9.963 7.178a1.012 1.012 0 010 .639 10.47 10.47 0 01-1.427 2.681"
                  />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full box-border min-h-[42px] rounded bg-blue-600 px-4 py-2 font-semibold text-white shadow transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Signing in...' : 'Sign in' }}
          </button>
        </form>
      </div>

      <p class="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
        Server Access Dashboard — protected area
      </p>
    </div>
  </div>
</template>
