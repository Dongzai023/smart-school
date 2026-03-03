<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>操作日志</h2>
      <div class="description">所有设备操作的审计记录</div>
    </div>

    <div class="content-card">
      <div class="card-title">
        <span>日志列表</span>
        <div style="display:flex;gap:8px;">
          <el-select v-model="filters.action" clearable placeholder="操作类型" size="small" style="width:120px;">
            <el-option label="锁屏" value="lock_screen" />
            <el-option label="解锁" value="unlock_screen" />
            <el-option label="关机" value="shutdown" />
            <el-option label="重启" value="reboot" />
          </el-select>
          <el-button size="small" @click="loadData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>

      <el-table :data="logs" stripe>
        <el-table-column prop="device_name" label="设备" width="140" />
        <el-table-column prop="user_name" label="操作人" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="actionType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
              {{ row.result === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top:16px;display:flex;justify-content:flex-end;">
        <el-pagination v-model:current-page="filters.page" :page-size="20" :total="total"
          layout="prev, pager, next" @current-change="loadData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { logApi } from '../api'

const logs = ref([])
const total = ref(0)
const filters = reactive({ action: null, page: 1 })

function actionLabel(a) {
  return { lock_screen: '锁屏', unlock_screen: '解锁', shutdown: '关机', reboot: '重启' }[a] || a
}

function actionType(a) {
  return { lock_screen: 'warning', unlock_screen: 'success', shutdown: 'danger', reboot: 'info' }[a] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadData() {
  const res = await logApi.list({ page: filters.page, page_size: 20, action: filters.action })
  logs.value = res.items
  total.value = res.total
}

watch(() => filters.action, () => { filters.page = 1; loadData() })
onMounted(loadData)
</script>
