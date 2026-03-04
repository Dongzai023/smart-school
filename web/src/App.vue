<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <div v-else class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>🏫 清涧中学智慧校园</h1>
        <div class="subtitle">Smart Campus Manager</div>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
          <span class="nav-icon">📊</span>
          <span>仪表盘</span>
        </router-link>
        <router-link to="/devices" class="nav-item" :class="{ active: $route.path === '/devices' }">
          <span class="nav-icon">🖥️</span>
          <span>设备管理</span>
        </router-link>
        <router-link to="/control" class="nav-item" :class="{ active: $route.path === '/control' }">
          <span class="nav-icon">⚙️</span>
          <span>设备控制</span>
        </router-link>
        <router-link to="/users" class="nav-item" :class="{ active: $route.path === '/users' }">
          <span class="nav-icon">👥</span>
          <span>用户管理</span>
        </router-link>
        <router-link to="/checkin-stats" class="nav-item" :class="{ active: $route.path === '/checkin-stats' }">
          <span class="nav-icon">📈</span>
          <span>签到统计</span>
        </router-link>
        <router-link to="/schedules" class="nav-item" :class="{ active: $route.path === '/schedules' }">
          <span class="nav-icon">⏰</span>
          <span>时间策略</span>
        </router-link>
        <router-link to="/images" class="nav-item" :class="{ active: $route.path === '/images' }">
          <span class="nav-icon">🖼️</span>
          <span>锁屏画面</span>
        </router-link>
        <router-link to="/unlock-requests" class="nav-item" :class="{ active: $route.path === '/unlock-requests' }">
          <span class="nav-icon">🔓</span>
          <span>解锁申请</span>
        </router-link>
        <router-link v-if="isAdmin" to="/logs" class="nav-item" :class="{ active: $route.path === '/logs' }">
          <span class="nav-icon">📝</span>
          <span>操作日志</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span>{{ userName }}</span>
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
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login')

const userName = computed(() => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      const user = JSON.parse(raw)
      return user.name || user.real_name || user.nickname || '用户'
    }
  } catch (e) {
    console.error('Parse user error:', e)
  }
  return '用户'
})

const isAdmin = computed(() => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      const user = JSON.parse(raw)
      return user.role === 'admin' || user.employee_id === 'admin'
    }
  } catch (e) {}
  return false
})

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.nav-icon {
  font-size: 18px;
  width: 20px;
  text-align: center;
}
</style>
