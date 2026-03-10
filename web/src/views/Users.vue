<template>
  <div class="fade-in">
    <div class="page-header">
      <div class="header-content">
        <h2>用户管理</h2>
        <div class="description">权限和管理签到用户账号状态</div>
      </div>
      <div class="admin-top-card" v-if="adminAccount">
        <div class="admin-info">
          <el-icon><Avatar /></el-icon>
          <span class="admin-name">系统管理员: {{ adminAccount.real_name || 'admin' }}</span>
        </div>
        <div class="admin-actions">
          <el-button type="danger" size="small" plain @click="openEditDialog(adminAccount)">修改密码/资料</el-button>
          <el-popconfirm title="确定解绑系统管理员的微信?" @confirm="unbindWx(adminAccount)" v-if="adminAccount.is_wechat_bound">
            <template #reference>
              <el-button type="warning" size="small" plain>解绑微信</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
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
          <div class="stat-label">已认证</div>
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
          <el-button type="primary" :icon="Plus" @click="openAddDialog">新增用户</el-button>
          <el-button :icon="Refresh" @click="loadData" :loading="loading" style="margin-left:10px">刷新</el-button>
        </div>
      </div>

      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="employee_id" label="工号" min-width="100">
          <template #default="{ row }">
            <span class="nowrap">{{ row.employee_id || row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="real_name" label="姓名" min-width="80" />
        <el-table-column prop="department_group" label="部门" min-width="100">
          <template #default="{ row }">
            {{ row.department_group || row.department || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="已认证" min-width="70">
          <template #default="{ row }">
            <el-switch v-model="row.is_verified" @change="toggleVerified(row)" :loading="row._loading" />
          </template>
        </el-table-column>
        <el-table-column label="班主任" min-width="60">
          <template #default="{ row }">
            <el-switch v-model="row.is_headmaster" @change="toggleHeadmaster(row)" :loading="row._loading" />
          </template>
        </el-table-column>
        <el-table-column label="微信绑定" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_wechat_bound ? 'success' : 'info'" size="small">
              {{ row.is_wechat_bound ? '已绑定' : '未绑定' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="看板范围" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.view_scope === 'all' ? 'success' : (row.view_scope === 'head_teacher' ? 'warning' : (row.view_scope === 'subject_teacher' ? 'primary' : 'info'))">
              {{ row.view_scope === 'all' ? '全校' : (row.view_scope === 'head_teacher' ? '班主任' : (row.view_scope === 'subject_teacher' ? '科任教师' : '无')) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定解绑此用户的微信?" @confirm="unbindWx(row)" v-if="row.is_wechat_bound">
              <template #reference>
                <el-button size="small" type="warning" link>解绑微信</el-button>
              </template>
            </el-popconfirm>
            <el-popconfirm title="确定删除此用户?" @confirm="deleteUser(row)">
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
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

    <!-- 新增用户对话框 -->
    <el-dialog v-model="showAddDialog" title="新增用户" width="500">
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="工号" required>
          <el-input v-model="userForm.employee_id" placeholder="请输入工号" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="userForm.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="userForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="userForm.password" type="password" placeholder="请输入初始密码" show-password />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="head_teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="看板权限">
          <el-select v-model="userForm.view_scope" placeholder="请选择查看范围" clearable>
            <el-option label="无" value="" />
            <el-option label="全校数据" value="all" />
            <el-option label="班主任数据" value="head_teacher" />
            <el-option label="科任教师" value="subject_teacher" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createUser" :loading="saving">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500">
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="工号">
          <el-input v-model="userForm.employee_id" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="userForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userForm.department" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="看板权限">
          <el-select v-model="userForm.view_scope" placeholder="请选择查看范围" clearable>
            <el-option label="无" value="" />
            <el-option label="全校数据" value="all" />
            <el-option label="班主任数据" value="head_teacher" />
            <el-option label="科任教师" value="subject_teacher" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="head_teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="重置密码">
          <el-input v-model="userForm.new_password" type="password" placeholder="留空则不修改密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateUser" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Avatar, Edit } from '@element-plus/icons-vue'
import { userApi } from '../api'

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const adminAccount = ref(null)
const stats = ref({})
const filters = reactive({ role: null })
const pagination = reactive({ page: 1, pageSize: 100, total: 0 })
const showDetailDialog = ref(false)
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const selectedUser = ref(null)
const userForm = reactive({
  id: null,
  employee_id: '',
  real_name: '',
  nickname: '',
  password: '',
  new_password: '',
  department: '',
  role: 'teacher',
  view_scope: ''
})

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
    const usersData = await userApi.list({ page: pagination.page, page_size: pagination.pageSize, role: filters.role })
    const allItems = usersData.items || (Array.isArray(usersData) ? usersData : [])
    
    // 分离出 admin 账号
    adminAccount.value = allItems.find(u => u.username === 'admin')
    
    // 过滤掉列表中的 admin
    users.value = allItems.filter(u => u.username !== 'admin').map(u => ({ 
      ...u, 
      real_name: u.real_name || u.name,
      _loading: false 
    }))
    
    // 加载统计概览 (新加)
    const statsOverview = await userApi.getStatsOverview({ role: filters.role })
    
    // 计算统计数据
    stats.value = {
      total_users: statsOverview.total_users || 0,
      active_users: statsOverview.active_users || 0,
      can_scan_unlock: statsOverview.verified_users || 0,
      today_checkins: statsOverview.signed_today || 0
    }
    pagination.total = usersData.total || 145
  } catch (e) {
    console.error('Load data error:', e)
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const usersData = await userApi.list({ page: pagination.page, page_size: pagination.pageSize, role: filters.role })
    const allItems = usersData.items || (Array.isArray(usersData) ? usersData : [])
    users.value = allItems.filter(u => u.username !== 'admin').map(u => ({ 
      ...u, 
      real_name: u.real_name || u.name,
      _loading: false 
    }))
    
    // 更新统计数据 (同步更新)
    const statsOverview = await userApi.getStatsOverview({ role: filters.role })
    stats.value = {
      total_users: statsOverview.total_users || 0,
      active_users: statsOverview.active_users || 0,
      can_scan_unlock: statsOverview.verified_users || 0,
      today_checkins: statsOverview.signed_today || 0
    }
    
    pagination.total = usersData.total || 144
  } catch (e) {
    console.error('Load users error:', e)
  } finally {
    loading.value = false
  }
}

async function toggleVerified(user) {
  user._loading = true
  try {
    await userApi.updatePermissions(user.id, { is_verified: user.is_verified })
    ElMessage.success(user.is_verified ? '已认证用户' : '已取消认证')
  } catch {
    user.is_verified = !user.is_verified
    ElMessage.error('更新失败')
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
    ElMessage.error('更新失败')
  } finally {
    user._loading = false
  }
}

function openAddDialog() {
  Object.assign(userForm, {
    id: null,
    employee_id: '',
    real_name: '',
    nickname: '',
    password: '',
    new_password: '',
    department: '',
    role: 'teacher',
    view_scope: ''
  })
  showAddDialog.value = true
}

function openEditDialog(user) {
  selectedUser.value = user
  Object.assign(userForm, {
    id: user.id,
    employee_id: user.employee_id || user.username,
    real_name: user.real_name,
    nickname: user.nickname || '',
    password: '',
    new_password: '',
    department: user.department || '',
    role: user.role,
    view_scope: user.view_scope || ''
  })
  showEditDialog.value = true
}

async function createUser() {
  if (!userForm.employee_id || !userForm.real_name || !userForm.password) {
    ElMessage.warning('请填写工号、姓名和密码')
    return
  }
  saving.value = true
  try {
    await userApi.create(userForm)
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function updateUser() {
  if (!userForm.real_name) {
    ElMessage.warning('请填写姓名')
    return
  }
  saving.value = true
  try {
    await userApi.update(userForm.id, {
      real_name: userForm.real_name,
      nickname: userForm.nickname,
      department: userForm.department,
      role: userForm.role,
      view_scope: userForm.view_scope,
      new_password: userForm.new_password || undefined
    })
    ElMessage.success('用户更新成功')
    showEditDialog.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    saving.value = false
  }
}

async function deleteUser(user) {
  try {
    await userApi.delete(user.id)
    ElMessage.success('用户已删除')
    loadData()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function unbindWx(user) {
  try {
    await userApi.unbindWx(user.id)
    ElMessage.success('微信已解绑')
    loadData()
  } catch (e) {
    ElMessage.error(e.message || '解绑失败')
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.admin-top-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(245, 108, 108, 0.05);
  border: 1px solid rgba(245, 108, 108, 0.2);
  padding: 8px 16px;
  border-radius: 12px;
}

.admin-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  font-weight: bold;
}

.admin-name {
  font-size: 14px;
}

.nowrap {
  white-space: nowrap;
}
</style>
