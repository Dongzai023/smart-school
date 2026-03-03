import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/Login.vue'),
        meta: { public: true },
    },
    {
        path: '/',
        redirect: '/dashboard',
    },
    {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
    },
    {
        path: '/devices',
        name: 'Devices',
        component: () => import('../views/Devices.vue'),
    },
    {
        path: '/schedules',
        name: 'Schedules',
        component: () => import('../views/Schedules.vue'),
    },
    {
        path: '/images',
        name: 'Images',
        component: () => import('../views/Images.vue'),
    },
    {
        path: '/unlock-requests',
        name: 'UnlockRequests',
        component: () => import('../views/UnlockRequests.vue'),
    },
    {
        path: '/logs',
        name: 'Logs',
        component: () => import('../views/Logs.vue'),
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

// Navigation guard
router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')
    if (!to.meta.public && !token) {
        next('/login')
    } else {
        next()
    }
})

export default router
