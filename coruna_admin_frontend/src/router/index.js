import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('../views/Devices.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/devices/:uuid',
    name: 'DeviceDetail',
    component: () => import('../views/DeviceDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/channels',
    name: 'Channels',
    component: () => import('../views/Channels.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/templates',
    name: 'Templates',
    component: () => import('../views/Templates.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil',
    name: 'Exfil',
    component: () => import('../views/Exfil.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/keychain',
    name: 'Keychain',
    component: () => import('../views/Keychain.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/wifi',
    name: 'WiFi',
    component: () => import('../views/WiFi.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/contacts',
    name: 'Contacts',
    component: () => import('../views/Contacts.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/sms',
    name: 'SMS',
    component: () => import('../views/SMS.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/calls',
    name: 'Calls',
    component: () => import('../views/Calls.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/photos',
    name: 'Photos',
    component: () => import('../views/Photos.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exfil/files',
    name: 'FileBrowser',
    component: () => import('../views/FileBrowser.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/wallets',
    name: 'Wallets',
    component: () => import('../views/Wallets.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/commands',
    name: 'Commands',
    component: () => import('../views/Commands.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/scripts',
    name: 'Scripts',
    component: () => import('../views/Scripts.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('../views/Logs.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/audit',
    name: 'AuditLog',
    component: () => import('../views/AuditLog.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('../views/Notifications.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('../views/Users.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('../views/Agents.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.path === '/login') {
    if (token) {
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          next('/dashboard')
          return
        }
      } catch (_) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
    next()
    return
  }

  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  if (to.meta.requiresAdmin) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        next('/login')
        return
      }
      const data = await res.json()
      if (data.role !== 'admin') {
        next('/dashboard')
        return
      }
    } catch (_) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      next('/login')
      return
    }
  }

  next()
})

export default router
