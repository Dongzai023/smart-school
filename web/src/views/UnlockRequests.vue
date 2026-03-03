<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>解锁申请</h2>
      <div class="description">{{ isAdmin ? '审批教师的临时解锁申请' : '申请临时解锁设备' }}</div>
    </div>

    <div class="content-card">
      <div class="card-title">
        <span>申请记录</span>
        <div style="display:flex;gap:8px;">
          <el-select v-model="statusFilter" clearable placeholder="全部状态" size="small" style="width:120px;">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
          <el-button type="primary" size="small" @click="showApplyDialog = true" v-if="!isAdmin">
            <el-icon><Plus /></el-icon> 申请解锁
          </el-button>
        </div>
      </div>

      <el-table :data="requests" stripe>
        <el-table-column prop="teacher_name" label="申请人" width="100" />
        <el-table-column prop="device_name" label="设备" width="140" />
        <el-table-column prop="reason" label="申请原因" />
        <el-table-column prop="duration_minutes" label="时长(分钟)" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" v-if="isAdmin">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="review(row.id, 'approved')">通过</el-button>
              <el-button size="small" type="danger" @click="review(row.id, 'rejected')">拒绝</el-button>
            </template>
            <span v-else style="color:#909399;">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Apply Dialog (Teacher) -->
    <el-dialog v-model="showApplyDialog" title="申请临时解锁" width="450">
      <el-form :model="applyForm" label-width="80px">
        <el-form-item label="选择设备">
          <el-select v-model="applyForm.device_id" filterable placeholder="搜索设备">
            <el-option v-for="d in devices" :key="d.id" :label="`${d.name} (${d.room_name || ''})`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="解锁时长">
          <el-input-number v-model="applyForm.duration_minutes" :min="15" :max="180" :step="15" />
          <span style="margin-left:8px;color:#909399;">分钟</span>
        </el-form-item>
        <el-form-item label="申请原因">
          <el-input v-model="applyForm.reason" type="textarea" :rows="3" placeholder="请说明解锁原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApplyDialog = false">取消</el-button>
        <el-button type="primary" @click="submitApply">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { unlockApi, deviceApi } from '../api'

const requests = ref([])
const devices = ref([])
const statusFilter = ref(null)
const showApplyDialog = ref(false)

const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const applyForm = reactive({ device_id: null, reason: '', duration_minutes: 45 })

function statusLabel(s) {
  return { pending: '待审批', approved: '已通过', rejected: '已拒绝', expired: '已过期' }[s] || s
}

function statusType(s) {
  return { pending: 'warning', approved: 'success', rejected: 'danger', expired: 'info' }[s] || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadData() {
  requests.value = await unlockApi.list(statusFilter.value)
  if (!isAdmin.value) {
    devices.value = await deviceApi.list()
  }
}

async function review(id, status) {
  await unlockApi.review(id, { status })
  ElMessage.success(status === 'approved' ? '已通过，解锁指令已发送' : '已拒绝')
  loadData()
}

async function submitApply() {
  if (!applyForm.device_id || !applyForm.reason) {
    ElMessage.warning('请选择设备并填写原因')
    return
  }
  await unlockApi.create(applyForm)
  ElMessage.success('申请已提交，请等待管理员审批')
  showApplyDialog.value = false
  Object.assign(applyForm, { device_id: null, reason: '', duration_minutes: 45 })
  loadData()
}

watch(statusFilter, loadData)
onMounted(loadData)
</script>
