<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>设备控制</h2>
      <div class="description">手动控制希沃一体机的锁屏、解锁和关机</div>
    </div>

    <!-- Status Summary -->
    <el-row :gutter="20" class="status-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ statusSummary.total || 0 }}</div>
          <div class="stat-label">设备总数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-online">
          <div class="stat-value">{{ statusSummary.online || 0 }}</div>
          <div class="stat-label">在线设备</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-locked">
          <div class="stat-value">{{ statusSummary.locked || 0 }}</div>
          <div class="stat-label">已锁屏</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-offline">
          <div class="stat-value">{{ statusSummary.offline || 0 }}</div>
          <div class="stat-label">离线设备</div>
        </div>
      </el-col>
    </el-row>

    <!-- Quick Actions -->
    <div class="content-card">
      <div class="card-title">
        <span>快速操作</span>
      </div>
      <div class="action-buttons">
        <el-button type="warning" :icon="Lock" :loading="locking" @click="lockAll" :disabled="!isAdmin">
          全部锁屏
        </el-button>
        <el-button type="success" :icon="Unlock" :loading="unlocking" @click="unlockAll" :disabled="!isAdmin">
          全部解锁
        </el-button>
        <el-button type="danger" :icon="SwitchButton" :loading="shuttingDown" @click="shutdownAll" :disabled="!isAdmin">
          全部关机
        </el-button>
        <el-button type="info" :icon="Refresh" @click="refreshStatus" :loading="refreshing">
          刷新状态
        </el-button>
      </div>
    </div>

    <!-- Device List -->
    <div class="content-card">
      <div class="card-title">
        <span>设备列表</span>
        <div class="card-actions">
          <el-select v-model="selectedGroup" clearable placeholder="全部分组" style="width:150px;margin-right:10px">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
          <el-checkbox v-model="showOffline" v-if="isAdmin">显示离线设备</el-checkbox>
          <el-button type="primary" size="small" style="margin-left:10px" @click="controlSelected" :disabled="selectedDevices.length === 0 || !isAdmin">
            <el-icon><Operation /></el-icon> 批量控制选中设备 ({{ selectedDevices.length }})
          </el-button>
        </div>
      </div>

      <el-table :data="filteredDevices" stripe @selection-change="handleSelectionChange" v-loading="loading">
        <el-table-column type="selection" width="50" v-if="isAdmin" />
        <el-table-column prop="name" label="设备名称" min-width="150">
          <template #default="{ row }">
            <div class="device-name">
              <span>{{ row.name }}</span>
              <el-tag v-if="row.group_id" size="small" type="info">{{ groupName(row.group_id) }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="room_name" label="教室" width="120" />
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column label="在线" width="90">
          <template #default="{ row }">
            <el-tag :type="row.online_status ? 'success' : 'danger'" size="small" effect="dark">
              {{ row.online_status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="锁屏" width="90">
          <template #default="{ row }">
            <el-tag :type="row.lock_status === 'locked' ? 'warning' : 'success'" size="small">
              {{ row.lock_status === 'locked' ? '已锁定' : '已解锁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" width="160">
          <template #default="{ row }">
            {{ row.last_heartbeat ? formatTime(row.last_heartbeat) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" v-if="isAdmin">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" type="warning" @click="controlDevice(row, 'lock_screen')" :disabled="!row.online_status">
                <el-icon><Lock /></el-icon>
              </el-button>
              <el-button size="small" type="success" @click="controlDevice(row, 'unlock_screen')" :disabled="!row.online_status">
                <el-icon><Unlock /></el-icon>
              </el-button>
              <el-button size="small" type="danger" @click="controlDevice(row, 'shutdown')" :disabled="!row.online_status">
                <el-icon><SwitchButton /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Batch Control Dialog -->
    <el-dialog v-model="showControlDialog" title="批量控制设备" width="450">
      <div class="control-info">
        <p>已选择 <strong>{{ selectedDevices.length }}</strong> 台设备</p>
        <p class="tip">选择要执行的操作：</p>
      </div>
      <el-radio-group v-model="controlAction" class="action-group">
        <el-radio-button value="lock_screen">
          <el-icon><Lock /></el-icon> 锁屏
        </el-radio-button>
        <el-radio-button value="unlock_screen">
          <el-icon><Unlock /></el-icon> 解锁
        </el-radio-button>
        <el-radio-button value="shutdown">
          <el-icon><SwitchButton /></el-icon> 关机
        </el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="showControlDialog = false">取消</el-button>
        <el-button type="primary" @click="executeControl" :loading="executing">执行</el-button>
      </template>
    </el-dialog>

    <!-- Result Dialog -->
    <el-dialog v-model="showResultDialog" title="操作结果" width="600">
      <div v-if="controlResults" class="result-content">
        <el-alert :title="`${actionLabel(controlResults.action)}操作完成`" :type="controlResults.all_success ? 'success' : 'warning'" :closable="false" />
        <el-table :data="resultList" stripe size="small" style="margin-top:15px">
          <el-table-column prop="device_name" label="设备" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.success ? 'success' : 'danger'" size="small">{{ row.success ? '成功' : '失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="消息" />
        </el-table>
      </div>
      <template #footer>
        <el-button type="primary" @click="showResultDialog = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock, Unlock, SwitchButton, Refresh, Operation } from '@element-plus/icons-vue'
import { deviceApi, controlApi } from '../api'

const loading = ref(false)
const refreshing = ref(false)
const locking = ref(false)
const unlocking = ref(false)
const shuttingDown = ref(false)
const executing = ref(false)
const devices = ref([])
const groups = ref([])
const statusSummary = ref({})
const selectedGroup = ref(null)
const selectedDevices = ref([])
const showOffline = ref(true)
const showControlDialog = ref(false)
const showResultDialog = ref(false)
const controlAction = ref('lock_screen')
const controlResults = ref(null)
const resultList = ref([])

const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})
const isAdmin = computed(() => currentUser.value?.role === 'admin' || currentUser.value?.employee_id === 'admin')

const filteredDevices = computed(() => {
  let list = devices.value
  if (selectedGroup.value) {
    list = list.filter(d => d.group_id === selectedGroup.value)
  }
  if (!showOffline.value) {
    list = list.filter(d => d.online_status)
  }
  return list
})

function groupName(id) {
  return groups.value.find(g => g.id === id)?.name || '-'
}

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

function actionLabel(a) {
  return { lock_screen: '锁屏', unlock_screen: '解锁', shutdown: '关机' }[a] || a
}

async function loadData() {
  loading.value = true
  try {
    const [devs, grps, summary] = await Promise.all([
      deviceApi.list(),
      deviceApi.listGroups(),
      deviceApi.statusSummary()
    ])
    devices.value = devs
    groups.value = grps
    statusSummary.value = summary
  } finally {
    loading.value = false
  }
}

async function refreshStatus() {
  refreshing.value = true
  await loadData()
  refreshing.value = false
  ElMessage.success('状态已刷新')
}

function handleSelectionChange(val) {
  selectedDevices.value = val
}

async function controlDevice(device, action) {
  try {
    await ElMessageBox.confirm(
      `确定要对设备 "${device.name}" 执行「${actionLabel(action)}」操作吗？`,
      '确认操作',
      { type: 'warning' }
    )
  } catch { return }

  const res = await controlApi.execute({
    device_ids: [device.id],
    action
  })
  const result = res.results[device.id]
  if (result.success) {
    ElMessage.success(`${device.name} ${actionLabel(action)}成功`)
  } else {
    ElMessage.warning(`${device.name} ${actionLabel(action)}失败: ${result.message}`)
  }
  refreshStatus()
}

function controlSelected() {
  if (selectedDevices.value.length === 0) {
    ElMessage.warning('请先选择要控制的设备')
    return
  }
  showControlDialog.value = true
}

async function executeControl() {
  executing.value = true
  try {
    const deviceIds = selectedDevices.value.map(d => d.id)
    const res = await controlApi.execute({
      device_ids: deviceIds,
      action: controlAction.value
    })
    controlResults.value = { action: controlAction.value, ...res }
    resultList.value = Object.entries(res.results).map(([id, r]) => ({
      device_name: devices.value.find(d => d.id == id)?.name || `设备${id}`,
      ...r
    }))
    showControlDialog.value = false
    showResultDialog.value = true
    refreshStatus()
  } finally {
    executing.value = false
  }
}

async function lockAll() {
  try {
    await ElMessageBox.confirm('确定要锁屏所有在线设备吗？', '确认', { type: 'warning' })
  } catch { return }
  locking.value = true
  const onlineDevices = devices.value.filter(d => d.online_status)
  if (onlineDevices.length === 0) {
    ElMessage.warning('没有在线设备')
    locking.value = false
    return
  }
  const res = await controlApi.execute({
    device_ids: onlineDevices.map(d => d.id),
    action: 'lock_screen'
  })
  const successCount = Object.values(res.results).filter(r => r.success).length
  ElMessage.success(`已成功锁屏 ${successCount}/${onlineDevices.length} 台设备`)
  locking.value = false
  refreshStatus()
}

async function unlockAll() {
  try {
    await ElMessageBox.confirm('确定要解锁所有在线设备吗？', '确认', { type: 'warning' })
  } catch { return }
  unlocking.value = true
  const onlineDevices = devices.value.filter(d => d.online_status)
  if (onlineDevices.length === 0) {
    ElMessage.warning('没有在线设备')
    unlocking.value = false
    return
  }
  const res = await controlApi.execute({
    device_ids: onlineDevices.map(d => d.id),
    action: 'unlock_screen'
  })
  const successCount = Object.values(res.results).filter(r => r.success).length
  ElMessage.success(`已成功解锁 ${successCount}/${onlineDevices.length} 台设备`)
  unlocking.value = false
  refreshStatus()
}

async function shutdownAll() {
  try {
    await ElMessageBox.confirm('确定要关机所有在线设备吗？此操作将关闭设备电源！', '危险操作', { type: 'error' })
  } catch { return }
  shuttingDown.value = true
  const onlineDevices = devices.value.filter(d => d.online_status)
  if (onlineDevices.length === 0) {
    ElMessage.warning('没有在线设备')
    shuttingDown.value = false
    return
  }
  const res = await controlApi.execute({
    device_ids: onlineDevices.map(d => d.id),
    action: 'shutdown'
  })
  const successCount = Object.values(res.results).filter(r => r.success).length
  ElMessage.success(`已发送关机指令至 ${successCount}/${onlineDevices.length} 台设备`)
  shuttingDown.value = false
  refreshStatus()
}

onMounted(loadData)
</script>

<style scoped>
.status-row {
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-card .stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-card .stat-label {
  font-size: 14px;
  color: #888;
  margin-top: 5px;
}

.stat-online .stat-value { color: #67c23a; }
.stat-locked .stat-value { color: #e6a23c; }
.stat-offline .stat-value { color: #f56c6c; }

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.device-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-actions {
  display: flex;
  align-items: center;
}

.control-info {
  margin-bottom: 20px;
}

.control-info p {
  margin: 5px 0;
}

.control-info .tip {
  color: #888;
  font-size: 14px;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-group :deep(.el-radio-button) {
  width: 100%;
}

.action-group :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.result-content {
  max-height: 400px;
  overflow-y: auto;
}
</style>
