<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <div v-else class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>🖥️ 希沃管理</h1>
        <div class="subtitle">Seewo Device Manager</div>
      </div>
      <nav class="sidebar-nav">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          class="nav-item" :class="{ active: $route.path === item.path }">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span>{{ currentUser?.real_name || '用户' }}</span>
          <el-button type="danger" text size="small" @click="logout">退出</el-button>
        </div>
      </div>
    </aside>
    <!-- Main -->
    <main class="main-content fade-in">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login')
const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})

const isAdmin = computed(() => currentUser.value?.role === 'admin')

const navItems = computed(() => {
  const items = [
    { path: '/dashboard', label: '仪表盘', icon: 'DataBoard' },
    { path: '/devices', label: '设备管理', icon: 'Monitor' },
    { path: '/schedules', label: '时间策略', icon: 'Clock' },
    { path: '/images', label: '锁屏画面', icon: 'Picture' },
    { path: '/unlock-requests', label: '解锁申请', icon: 'Unlock' },
  ]
  if (isAdmin.value) {
    items.push({ path: '/logs', label: '操作日志', icon: 'Document' })
  }
  return items
})

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>
