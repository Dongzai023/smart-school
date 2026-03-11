<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <div v-else class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>海亮教育·清涧中学</h1>
        <div class="subtitle">Smart Campus Manager</div>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
          <el-icon class="nav-icon"><Monitor /></el-icon>
          <span>仪表盘</span>
        </router-link>
        <router-link to="/devices" class="nav-item" :class="{ active: $route.path === '/devices' }">
          <el-icon class="nav-icon"><Connection /></el-icon>
          <span>设备管理</span>
        </router-link>
        <router-link to="/control" class="nav-item" :class="{ active: $route.path === '/control' }">
          <el-icon class="nav-icon"><Setting /></el-icon>
          <span>设备控制</span>
        </router-link>
        <router-link to="/users" class="nav-item" :class="{ active: $route.path === '/users' }">
          <el-icon class="nav-icon"><User /></el-icon>
          <span>用户管理</span>
        </router-link>
        <router-link to="/checkin-stats" class="nav-item" :class="{ active: $route.path === '/checkin-stats' }">
          <el-icon class="nav-icon"><PieChart /></el-icon>
          <span>签到统计</span>
        </router-link>
        <router-link to="/schedules" class="nav-item" :class="{ active: $route.path === '/schedules' }">
          <el-icon class="nav-icon"><Timer /></el-icon>
          <span>时间策略</span>
        </router-link>
        <router-link to="/images" class="nav-item" :class="{ active: $route.path === '/images' }">
          <el-icon class="nav-icon"><Picture /></el-icon>
          <span>锁屏画面</span>
        </router-link>
        <router-link to="/unlock-requests" class="nav-item" :class="{ active: $route.path === '/unlock-requests' }">
          <el-icon class="nav-icon"><Unlock /></el-icon>
          <span>解锁申请</span>
        </router-link>
        <router-link v-if="isAdmin" to="/logs" class="nav-item" :class="{ active: $route.path === '/logs' }">
          <el-icon class="nav-icon"><Files /></el-icon>
          <span>操作日志</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="user-avatar">{{ userName[0] }}</div>
          <div class="user-info">
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ isAdmin ? '管理员' : '教师' }}</div>
          </div>
          <el-button class="logout-btn" type="danger" circle :icon="SwitchButton" @click="logout" size="small"></el-button>
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
import { 
  Monitor, Connection, Setting, User, PieChart, 
  Timer, Picture, Unlock, Files, SwitchButton 
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login')

const userName = computed(() => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      const user = JSON.parse(raw)
      return user.real_name || user.name || user.nickname || '用户'
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
.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: var(--primary);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: white;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 11px;
  color: #94a3b8;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.05);
  border: none;
  color: #94a3b8;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
</style>
