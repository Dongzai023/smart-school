<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>设备管理</h2>
      <div class="description">管理所有希沃一体机设备和分组</div>
    </div>

    <!-- Groups & Actions -->
    <div class="content-card">
      <div class="card-title">
        <span>设备分组</span>
        <el-button type="primary" size="small" @click="showGroupDialog = true" v-if="isAdmin">
          <el-icon><Plus /></el-icon> 新建分组
        </el-button>
      </div>
      <el-tag v-for="g in groups" :key="g.id" size="large" style="margin:0 8px 8px 0;cursor:pointer;"
        :type="selectedGroup === g.id ? '' : 'info'" @click="selectedGroup = selectedGroup === g.id ? null : g.id"
        closable @close="deleteGroup(g.id)" v-if="isAdmin">
        {{ g.name }} ({{ g.device_count }})
      </el-tag>
      <el-tag v-for="g in groups" :key="g.id" size="large" style="margin:0 8px 8px 0;cursor:pointer;"
        :type="selectedGroup === g.id ? '' : 'info'" @click="selectedGroup = selectedGroup === g.id ? null : g.id"
        v-if="!isAdmin">
        {{ g.name }} ({{ g.device_count }})
      </el-tag>
    </div>

    <!-- Device List -->
    <div class="content-card">
      <div class="card-title">
        <span>设备列表{{ selectedGroup ? ' (已筛选)' : '' }}</span>
        <div v-if="isAdmin">
          <el-button type="primary" size="small" @click="openDeviceDialog()">
            <el-icon><Plus /></el-icon> 添加设备
          </el-button>
        </div>
      </div>
      <el-table :data="filteredDevices" stripe>
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="room_name" label="教室" />
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column label="在线" width="80">
          <template #default="{ row }">
            <el-tag :type="row.online_status ? 'success' : 'danger'" size="small" effect="dark">
              {{ row.online_status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="锁屏" width="80">
          <template #default="{ row }">
            <el-tag :type="row.lock_status === 'locked' ? 'warning' : 'success'" size="small">
              {{ row.lock_status === 'locked' ? '锁定' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="agent_key" label="Agent密钥" width="180" v-if="isAdmin">
          <template #default="{ row }">
            <el-tooltip :content="row.agent_key" placement="top">
              <code style="font-size:12px;cursor:pointer;" @click="copyKey(row.agent_key)">
                {{ row.agent_key?.substring(0, 12) }}...
              </code>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" v-if="isAdmin">
          <template #default="{ row }">
            <el-button size="small" @click="openDeviceDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="deleteDevice(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Group Dialog -->
    <el-dialog v-model="showGroupDialog" title="新建分组" width="400">
      <el-form :model="groupForm" label-width="60px">
        <el-form-item label="名称"><el-input v-model="groupForm.name" /></el-form-item>
        <el-form-item label="楼栋"><el-input v-model="groupForm.building" /></el-form-item>
        <el-form-item label="楼层"><el-input v-model="groupForm.floor" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="saveGroup">确定</el-button>
      </template>
    </el-dialog>

    <!-- Device Dialog -->
    <el-dialog v-model="showDeviceDialog" :title="deviceForm.id ? '编辑设备' : '添加设备'" width="450">
      <el-form :model="deviceForm" label-width="80px">
        <el-form-item label="设备名称"><el-input v-model="deviceForm.name" /></el-form-item>
        <el-form-item label="教室名称"><el-input v-model="deviceForm.room_name" /></el-form-item>
        <el-form-item label="IP地址"><el-input v-model="deviceForm.ip" /></el-form-item>
        <el-form-item label="MAC地址"><el-input v-model="deviceForm.mac" /></el-form-item>
        <el-form-item label="所属分组">
          <el-select v-model="deviceForm.group_id" clearable placeholder="选择分组">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDeviceDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDevice">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { deviceApi } from '../api'

const groups = ref([])
const devices = ref([])
const selectedGroup = ref(null)
const showGroupDialog = ref(false)
const showDeviceDialog = ref(false)

const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const groupForm = reactive({ name: '', building: '', floor: '' })
const deviceForm = reactive({ id: null, name: '', room_name: '', ip: '', mac: '', group_id: null })

const filteredDevices = computed(() => {
  if (selectedGroup.value) return devices.value.filter(d => d.group_id === selectedGroup.value)
  return devices.value
})

async function loadData() {
  ;[groups.value, devices.value] = await Promise.all([deviceApi.listGroups(), deviceApi.list()])
}

function openDeviceDialog(device) {
  if (device) {
    Object.assign(deviceForm, device)
  } else {
    Object.assign(deviceForm, { id: null, name: '', room_name: '', ip: '', mac: '', group_id: null })
  }
  showDeviceDialog.value = true
}

async function saveGroup() {
  await deviceApi.createGroup(groupForm)
  ElMessage.success('分组创建成功')
  showGroupDialog.value = false
  Object.assign(groupForm, { name: '', building: '', floor: '' })
  loadData()
}

async function deleteGroup(id) {
  try {
    await deviceApi.deleteGroup(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) { /* handled */ }
}

async function saveDevice() {
  if (deviceForm.id) {
    await deviceApi.update(deviceForm.id, deviceForm)
    ElMessage.success('更新成功')
  } else {
    const res = await deviceApi.create(deviceForm)
    ElMessage.success(`设备创建成功，Agent密钥: ${res.agent_key}`)
  }
  showDeviceDialog.value = false
  loadData()
}

async function deleteDevice(id) {
  await deviceApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

function copyKey(key) {
  navigator.clipboard.writeText(key)
  ElMessage.success('密钥已复制到剪贴板')
}

onMounted(loadData)
</script>
