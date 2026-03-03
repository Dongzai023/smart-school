<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>仪表盘</h2>
      <div class="description">设备运行状态总览</div>
    </div>

    <!-- Stat Cards -->
    <el-row :gutter="20" style="margin-bottom:24px;">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <div class="stat-card">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon><component :is="stat.icon" /></el-icon>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Device list -->
    <div class="content-card">
      <div class="card-title">
        <span>设备状态</span>
        <el-button-group>
          <el-button :type="filter === 'all' ? 'primary' : ''" size="small" @click="filter='all'">全部</el-button>
          <el-button :type="filter === 'online' ? 'primary' : ''" size="small" @click="filter='online'">在线</el-button>
          <el-button :type="filter === 'offline' ? 'primary' : ''" size="small" @click="filter='offline'">离线</el-button>
        </el-button-group>
      </div>
      <el-table :data="filteredDevices" stripe style="width:100%;">
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="room_name" label="教室" />
        <el-table-column label="在线状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.online_status ? 'success' : 'danger'" size="small" effect="dark">
              {{ row.online_status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="锁屏状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.lock_status === 'locked' ? 'warning' : 'success'" size="small">
              {{ row.lock_status === 'locked' ? '已锁屏' : '已解锁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column label="操作" width="240" v-if="isAdmin">
          <template #default="{ row }">
            <el-button size="small" type="warning" @click="control(row.id, 'lock_screen')" :disabled="!row.online_status">锁屏</el-button>
            <el-button size="small" type="success" @click="control(row.id, 'unlock_screen')" :disabled="!row.online_status">解锁</el-button>
            <el-button size="small" type="danger" @click="control(row.id, 'shutdown')" :disabled="!row.online_status">关机</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deviceApi, controlApi } from '../api'

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
  { label: '设备总数', value: summary.value.total, icon: 'Monitor', color: 'linear-gradient(135deg, #409eff, #337ecc)' },
  { label: '在线设备', value: summary.value.online, icon: 'CircleCheck', color: 'linear-gradient(135deg, #67c23a, #529b2e)' },
  { label: '离线设备', value: summary.value.offline, icon: 'CircleClose', color: 'linear-gradient(135deg, #f56c6c, #c45656)' },
  { label: '已锁屏', value: summary.value.locked, icon: 'Lock', color: 'linear-gradient(135deg, #e6a23c, #b88230)' },
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
  } catch (e) { /* handled */ }
}

async function control(deviceId, action) {
  const actionLabels = { lock_screen: '锁屏', unlock_screen: '解锁', shutdown: '关机' }
  try {
    await ElMessageBox.confirm(`确定要对该设备执行"${actionLabels[action]}"操作吗？`, '确认操作', { type: 'warning' })
    const res = await controlApi.execute({ device_ids: [deviceId], action })
    const result = res.results[deviceId]
    if (result?.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result?.message || '操作失败')
    }
    loadData()
  } catch (e) { /* cancelled */ }
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 10000) // Auto-refresh every 10s
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
