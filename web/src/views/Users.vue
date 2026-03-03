<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="description">权限和管理签到用户账号状态</div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_users || 0 }}</div>
          <div class="stat-label">总用户数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-active">
          <div class="stat-value">{{ stats.active_users || 0 }}</div>
          <div class="stat-label">活跃用户</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-unlock">
          <div class="stat-value">{{ stats.can_scan_unlock || 0 }}</div>
          <div class="stat-label">可扫码解锁</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-checkin">
          <div class="stat-value">{{ stats.today_checkins || 0 }}</div>
          <div class="stat-label">今日签到</div>
        </div>
      </el-col>
    </el-row>

    <!-- 搜索和筛选 -->
    <div class="content-card">
      <div class="card-title">
        <span>用户列表</span>
        <div class="card-actions">
          <el-select v-model="filters.role" clearable placeholder="全部角色" style="width:120px;margin-right:10px" @change="loadUsers">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="head_teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
          <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
        </div>
      </div>

      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="employee_id" label="工号" width="100" />
        <el-table-column prop="real_name" label="姓名" min-width="100" />
        <el-table-column prop="department" label="部门/科室" width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可扫码解锁" width="110">
          <template #default="{ row }">
            <el-switch v-model="row.can_scan_unlock" @change="toggleScanUnlock(row)" :loading="row._loading" />
          </template>
        </el-table-column>
        <el-table-column label="已认证" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.is_verified" @change="toggleVerified(row)" :loading="row._loading" />
          </template>
        </el-table-column>
        <el-table-column label="账号状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="班主任" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.is_headmaster" @change="toggleHeadmaster(row)" :loading="row._loading" />
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </div>

    <!-- 用户详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="用户详情" width="500">
      <el-descriptions :column="2" border v-if="selectedUser">
        <el-descriptions-item label="工号">{{ selectedUser.employee_id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ selectedUser.real_name }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ selectedUser.username }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ selectedUser.department || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ roleLabel(selectedUser.role) }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatDate(selectedUser.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { userApi } from '../api'

const loading = ref(false)
const users = ref([])
const stats = ref({})
const filters = reactive({ role: null })
const pagination = reactive({ page: 1, pageSize: 50, total: 0 })
const showDetailDialog = ref(false)
const selectedUser = ref(null)

function roleLabel(role) {
  const labels = { admin: '管理员', head_teacher: '班主任', teacher: '教师' }
  return labels[role] || role
}

function roleType(role) {
  const types = { admin: 'danger', head_teacher: 'warning', teacher: 'primary' }
  return types[role] || 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadData() {
  loading.value = true
  try {
    const [usersData, statsData] = await Promise.all([
      userApi.list({ page: pagination.page, page_size: pagination.pageSize, role: filters.role }),
      userApi.getStats()
    ])
    users.value = usersData.items.map(u => ({ ...u, _loading: false }))
    pagination.total = usersData.total
    stats.value = statsData
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const usersData = await userApi.list({ page: pagination.page, page_size: pagination.pageSize, role: filters.role })
    users.value = usersData.items.map(u => ({ ...u, _loading: false }))
    pagination.total = usersData.total
  } finally {
    loading.value = false
  }
}

async function toggleScanUnlock(user) {
  user._loading = true
  try {
    await userApi.updatePermissions(user.id, { can_scan_unlock: user.can_scan_unlock })
    ElMessage.success(user.can_scan_unlock ? '已授权扫码解锁' : '已取消扫码解锁权限')
  } catch {
    user.can_scan_unlock = !user.can_scan_unlock
  } finally {
    user._loading = false
  }
}

async function toggleVerified(user) {
  user._loading = true
  try {
    await userApi.updatePermissions(user.id, { is_verified: user.is_verified })
    ElMessage.success(user.is_verified ? '已认证用户' : '已取消认证')
  } catch {
    user.is_verified = !user.is_verified
  } finally {
    user._loading = false
  }
}

async function toggleHeadmaster(user) {
  user._loading = true
  try {
    await userApi.updatePermissions(user.id, { is_headmaster: user.is_headmaster })
    ElMessage.success(user.is_headmaster ? '已设为班主任' : '已取消班主任')
  } catch {
    user.is_headmaster = !user.is_headmaster
  } finally {
    user._loading = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.stats-row {
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

.stat-active .stat-value { color: #67c23a; }
.stat-unlock .stat-value { color: #409eff; }
.stat-checkin .stat-value { color: #e6a23c; }

.card-actions {
  display: flex;
  align-items: center;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
