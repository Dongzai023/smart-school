<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>时间策略</h2>
      <div class="description">配置自动锁屏、解锁、关机的时间规则</div>
    </div>

    <div class="content-card">
      <div class="card-title">
        <span>策略列表</span>
        <el-button type="primary" size="small" @click="openDialog()">
          <el-icon><Plus /></el-icon> 新建策略
        </el-button>
      </div>
      <el-table :data="schedules" stripe>
        <el-table-column prop="name" label="策略名称" />
        <el-table-column label="操作类型" width="120">
          <template #default="{ row }">
            <el-tag :type="actionType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="执行时间" width="100" />
        <el-table-column label="执行日" width="200">
          <template #default="{ row }">
            <span>{{ weekdayLabel(row.weekdays) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="目标分组" width="120">
          <template #default="{ row }">
            {{ row.target_group_id ? groupName(row.target_group_id) : '全部设备' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="deleteSchedule(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Dialog -->
    <el-dialog v-model="showDialog" :title="form.id ? '编辑策略' : '新建策略'" width="500">
      <el-form :model="form" label-width="80px">
        <el-form-item label="策略名称">
          <el-input v-model="form.name" placeholder="如：上午锁屏" />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="form.action">
            <el-option label="🔒 锁屏" value="lock_screen" />
            <el-option label="🔓 解锁" value="unlock_screen" />
            <el-option label="🔌 关机" value="shutdown" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行时间">
          <el-time-picker v-model="form.timeObj" format="HH:mm" placeholder="选择时间" />
        </el-form-item>
        <el-form-item label="执行日">
          <el-checkbox-group v-model="form.weekdaysArr">
            <el-checkbox v-for="d in dayOptions" :key="d.value" :label="d.value">{{ d.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="目标分组">
          <el-select v-model="form.target_group_id" clearable placeholder="全部设备">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSchedule">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { scheduleApi, deviceApi } from '../api'

const schedules = ref([])
const groups = ref([])
const showDialog = ref(false)

const dayOptions = [
  { label: '一', value: '1' }, { label: '二', value: '2' },
  { label: '三', value: '3' }, { label: '四', value: '4' },
  { label: '五', value: '5' }, { label: '六', value: '6' },
  { label: '日', value: '7' },
]

const form = reactive({
  id: null, name: '', action: 'lock_screen', timeObj: null,
  weekdaysArr: ['1', '2', '3', '4', '5'],
  target_group_id: null, description: '',
})

function actionLabel(a) {
  return { lock_screen: '锁屏', unlock_screen: '解锁', shutdown: '关机' }[a] || a
}

function actionType(a) {
  return { lock_screen: 'warning', unlock_screen: 'success', shutdown: 'danger' }[a] || 'info'
}

function weekdayLabel(wd) {
  const names = { '1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '日' }
  return wd.split(',').map(d => `周${names[d] || d}`).join(' ')
}

function groupName(id) {
  return groups.value.find(g => g.id === id)?.name || '-'
}

async function loadData() {
  ;[schedules.value, groups.value] = await Promise.all([scheduleApi.list(), deviceApi.listGroups()])
}

function openDialog(item) {
  if (item) {
    form.id = item.id
    form.name = item.name
    form.action = item.action
    const [h, m] = item.time.split(':')
    form.timeObj = new Date(2000, 0, 1, parseInt(h), parseInt(m))
    form.weekdaysArr = item.weekdays.split(',')
    form.target_group_id = item.target_group_id
    form.description = item.description
  } else {
    Object.assign(form, {
      id: null, name: '', action: 'lock_screen', timeObj: null,
      weekdaysArr: ['1', '2', '3', '4', '5'], target_group_id: null, description: '',
    })
  }
  showDialog.value = true
}

async function saveSchedule() {
  const time = form.timeObj
    ? `${String(form.timeObj.getHours()).padStart(2, '0')}:${String(form.timeObj.getMinutes()).padStart(2, '0')}`
    : '00:00'
  const data = { name: form.name, action: form.action, time, weekdays: form.weekdaysArr.join(','), target_group_id: form.target_group_id, description: form.description }

  if (form.id) {
    await scheduleApi.update(form.id, data)
  } else {
    await scheduleApi.create(data)
  }
  // Reload scheduler
  await scheduleApi.reload()
  ElMessage.success('保存成功')
  showDialog.value = false
  loadData()
}

async function toggleActive(row) {
  await scheduleApi.update(row.id, { is_active: row.is_active })
  await scheduleApi.reload()
  ElMessage.success(row.is_active ? '策略已启用' : '策略已禁用')
}

async function deleteSchedule(id) {
  await scheduleApi.delete(id)
  await scheduleApi.reload()
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>
