import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import { isAuthenticated } from '../auth/store'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { public: false },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const requiresAuth = !to.meta.public
  const isAuthed = isAuthenticated()

  if (requiresAuth && !isAuthed) {
    // Redirect to login, preserving the intended destination
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (!requiresAuth && isAuthed) {
    // Already logged in — send them to the dashboard
    return next({ path: '/' })
  }

  return next()
})

export default router