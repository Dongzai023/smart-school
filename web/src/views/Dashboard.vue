<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>设备运行中心</h2>
      <div class="description">全校一体机在线状态与远程控制台</div>
    </div>

    <!-- 顶部状态统计 (Premium Glass Cards) -->
    <el-row :gutter="24" style="margin-bottom:32px;">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <div class="stat-card glass-panel" :style="{ borderTop: `4px solid ${stat.accent}` }">
          <div class="stat-inner">
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-icon-wrapper" :style="{ background: stat.bg }">
              <el-icon><component :is="stat.icon" /></el-icon>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主表格区域 -->
    <div class="content-card glass-panel">
      <div class="card-title">
        <div class="title-left">
          <el-icon><Monitor /></el-icon>
          <span>实时设备状态</span>
        </div>
        <div class="title-right">
          <el-radio-group v-model="filter" size="small">
            <el-radio-button label="all">全部设备</el-radio-button>
            <el-radio-button label="online">在线中</el-radio-button>
            <el-radio-button label="offline">离线</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      
      <el-table :data="filteredDevices" class="premium-table" v-loading="loading">
        <el-table-column label="设备名称" min-width="180">
          <template #default="{ row }">
            <div class="device-cell">
              <div class="status-pulse" :class="{ online: row.online_status }"></div>
              <span class="device-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="room_name" label="部署教室" width="140" />
        <el-table-column label="网络连接" width="120">
          <template #default="{ row }">
            <el-tag :type="row.online_status ? 'success' : 'danger'" effect="light" round size="small">
              {{ row.online_status ? '稳定在线' : '网络中断' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="安全态势" width="120">
          <template #default="{ row }">
            <div class="lock-status" :class="row.lock_status">
              <el-icon v-if="row.lock_status === 'locked'"><Lock /></el-icon>
              <el-icon v-else><Unlock /></el-icon>
              <span>{{ row.lock_status === 'locked' ? '已锁屏' : '共享中' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="内网IP" width="140">
           <template #default="{ row }">
             <code class="ip-code">{{ row.ip }}</code>
           </template>
        </el-table-column>
        <el-table-column label="远程指令" width="220" fixed="right" v-if="isAdmin">
          <template #default="{ row }">
            <div class="action-btns">
              <el-tooltip content="指令：锁定屏幕" placement="top">
                <el-button size="small" type="warning" circle :icon="Lock" @click="control(row.id, 'lock_screen')" :disabled="!row.online_status"></el-button>
              </el-tooltip>
              <el-tooltip content="指令：全效解锁" placement="top">
                <el-button size="small" type="success" circle :icon="Unlock" @click="control(row.id, 'unlock_screen')" :disabled="!row.online_status"></el-button>
              </el-tooltip>
              <el-tooltip content="指令：立即关机" placement="top">
                <el-button size="small" type="danger" circle :icon="SwitchButton" @click="control(row.id, 'shutdown')" :disabled="!row.online_status"></el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Monitor, CircleCheck, CircleClose, Lock, 
  Unlock, SwitchButton 
} from '@element-plus/icons-vue'
import { deviceApi, controlApi } from '../api'

const loading = ref(false)
const summary = ref({ total: 0, online: 0, offline: 0, locked: 0, unlocked: 0 })
const devices = ref([])
const filter = ref('all')
let timer = null

const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const stats = computed(() => [
  { label: '注册设备', value: summary.value.total, icon: Monitor, accent: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
  { label: '在线节点', value: summary.value.online, icon: CircleCheck, accent: '#0ea5e9', bg: 'rgba(14, 165, 233, 0.1)' },
  { label: '离线预警', value: summary.value.offline, icon: CircleClose, accent: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  { label: '安全加锁', value: summary.value.locked, icon: Lock, accent: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' }
])

const filteredDevices = computed(() => {
  if (filter.value === 'online') return devices.value.filter(d => d.online_status)
  if (filter.value === 'offline') return devices.value.filter(d => !d.online_status)
  return devices.value
})

async function loadData() {
  try {
    const [s, d] = await Promise.all([deviceApi.statusSummary(), deviceApi.list()])
    summary.value = s
    devices.value = d
  } catch (e) { /* silent */ }
}

async function control(deviceId, action) {
  const actionLabels = { lock_screen: '锁屏', unlock_screen: '解锁', shutdown: '关机' }
  try {
    await ElMessageBox.confirm(`确定要对该设备执行"${actionLabels[action]}"操作吗？`, '安全身份确认', { 
      type: 'warning',
      confirmButtonClass: 'el-button--primary'
    })
    const res = await controlApi.execute({ device_ids: [deviceId], action })
    const result = res.results[deviceId]
    if (result?.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result?.message || '指令下发失败')
    }
    loadData()
  } catch (e) { /* User cancelled */ }
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.stat-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 900;
  color: #0f172a;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-top: 8px;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #334155;
  transition: var(--transition-smooth);
}

.stat-card:hover .stat-icon-wrapper {
  transform: scale(1.1);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 800;
}

.device-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.device-name {
  font-weight: 700;
  color: #1e293b;
}

.status-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cbd5e1;
  position: relative;
}

.status-pulse.online {
  background: #10b981;
}

.status-pulse.online::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 4px solid #10b981;
  animation: pulse 2s infinite;
  opacity: 0.5;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.5; }
  100% { transform: scale(2.5); opacity: 0; }
}

.lock-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.lock-status.locked { color: #f59e0b; }
.lock-status.unlocked { color: #10b981; }

.ip-code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #64748b;
}

.action-btns {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
