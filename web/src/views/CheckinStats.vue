<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>签到数字化中心</h2>
      <div class="description">全校教师实时出勤与数字化考勤报表</div>
    </div>

    <!-- 顶层关键指标 (144人特化设计) -->
    <el-row :gutter="24" class="hero-stats">
      <el-col :span="6">
        <div class="kpi-card glass-panel total-border">
          <div class="kpi-icon"><el-icon><User /></el-icon></div>
          <div class="kpi-content">
            <div class="kpi-value">{{ overview.total_users || 144 }}</div>
            <div class="kpi-label">全校教师总数</div>
          </div>
          <div class="kpi-decoration total-bg"></div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="kpi-card glass-panel signed-border">
          <div class="kpi-icon"><el-icon><CircleCheck /></el-icon></div>
          <div class="kpi-content">
            <div class="kpi-value">{{ overview.signed_today || 0 }}</div>
            <div class="kpi-label">今日已签到</div>
          </div>
          <div class="kpi-decoration signed-bg"></div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="kpi-card glass-panel late-border">
          <div class="kpi-icon"><el-icon><Timer /></el-icon></div>
          <div class="kpi-content">
            <div class="kpi-value">{{ overview.late_today || 0 }}</div>
            <div class="kpi-label">今日迟到人数</div>
          </div>
          <div class="kpi-decoration late-bg"></div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="kpi-card glass-panel absent-border">
          <div class="kpi-icon"><el-icon><Warning /></el-icon></div>
          <div class="kpi-content">
            <div class="kpi-value">{{ overview.absent_today || 0 }}</div>
            <div class="kpi-label">今日未签到</div>
          </div>
          <div class="kpi-decoration absent-bg"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 主明细面板 -->
    <div class="content-card main-panel glass-panel">
      <div class="panel-header">
        <div class="panel-title">
          <el-icon><Fold /></el-icon>
          <span>智能考勤明细</span>
          <el-tag round size="small" type="info" style="margin-left:12px">Real-time Stream</el-tag>
        </div>
        <div class="panel-actions">
          <el-select v-model="filters.department" clearable placeholder="部门筛选" style="width:140px" @change="loadData">
            <el-option v-for="dept in departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
          <el-select v-model="filters.period" placeholder="时段选择" style="width:120px" @change="loadData">
            <el-option label="本周报表" value="week" />
            <el-option label="本月报表" value="month" />
            <el-option label="本学期" value="semester" />
          </el-select>
          <el-button type="primary" :icon="Refresh" @click="loadData" :loading="loading" plain>刷新看板</el-button>
        </div>
      </div>

      <el-table :data="users" class="premium-table" v-loading="loading">
        <el-table-column label="教师基础信息" min-width="200">
          <template #default="{ row }">
            <div class="teacher-info">
              <div class="avatar-sm">{{ row.real_name ? row.real_name[0] : 'T' }}</div>
              <div class="name-meta">
                <div class="name-text">{{ row.real_name }}</div>
                <div class="id-text">#{{ row.employee_id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" min-width="120">
           <template #default="{ row }">
             <span class="dept-badge">{{ row.department || '校办公室' }}</span>
           </template>
        </el-table-column>
        <el-table-column label="职业角色" min-width="100">
          <template #default="{ row }">
            <el-tag effect="light" :type="row.role === 'admin' ? 'danger' : (row.role === 'head_teacher' ? 'warning' : 'info')" size="small">
              {{ row.role === 'admin' ? '管理员' : (row.role === 'head_teacher' ? '班主任' : '教师') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="阶段表现" min-width="240" align="center">
          <template #header>
             <div class="header-multi">
               <span>出勤表现 ({{ filters.period === 'week' ? '本周' : '本月' }})</span>
             </div>
          </template>
          <template #default="{ row }">
            <div class="stats-row">
              <div class="stat-mini"><span class="label">已签:</span><span class="val success">{{ row.signed_count }}</span></div>
              <div class="stat-mini"><span class="label">迟到:</span><span class="val warning">{{ row.late_count }}</span></div>
              <div class="stat-mini"><span class="label">未签:</span><span class="val danger">{{ row.absent_count }}</span></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="综合出勤率" min-width="160" align="center">
          <template #default="{ row }">
            <div class="rate-box">
              <el-progress 
                type="circle" 
                :percentage="row.attendance_rate" 
                :width="40" 
                :stroke-width="4" 
                :color="getRateColor(row.attendance_rate)" 
              />
              <span class="rate-text">{{ row.attendance_rate }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="快捷操作" width="100" align="right">
          <template #default="{ row }">
            <el-button size="small" circle :icon="Search" @click="viewDetail(row)"></el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-area">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 记录对话框 (Glass Style) -->
    <el-dialog v-model="showDetail" :title="selectedUser ? `${selectedUser.real_name} 签到历程` : '签到历程'" width="760px" class="premium-dialog">
      <el-table :data="records" size="small" height="450">
        <el-table-column prop="date" label="签到日期" width="130" />
        <el-table-column prop="weekday" label="星期" width="90" />
        <el-table-column prop="time" label="精确时间" width="90">
           <template #default="{ row }">
             <span class="time-bold">{{ row.time }}</span>
           </template>
        </el-table-column>
        <el-table-column prop="location" label="打卡位置" min-width="160">
           <template #default="{ row }">
             <span class="loc-text">{{ row.location || '校园内' }}</span>
           </template>
        </el-table-column>
        <el-table-column label="状态判定" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small" effect="dark">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="dialog-footer">
        <el-pagination
          v-model:current-page="detailPage"
          :page-size="30"
          :total="detailTotal"
          layout="prev, pager, next"
          small
          @current-change="loadDetail"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Refresh, Search, User, CircleCheck, 
  Timer, Warning, Fold 
} from '@element-plus/icons-vue'
import api from '../api'

const loading = ref(false)
const overview = ref({})
const users = ref([])
const departments = ref([])
const filters = reactive({
  department: null,
  period: 'week'
})
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const showDetail = ref(false)
const selectedUser = ref(null)
const records = ref([])
const detailPage = ref(1)
const detailTotal = ref(0)

function getRateColor(rate) {
  if (rate >= 90) return '#10b981'
  if (rate >= 70) return '#f59e0b'
  return '#ef4444'
}

function getStatusType(status) {
  const map = { signed: 'success', normal: 'success', late: 'warning', absent: 'danger' }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = { signed: '正常', normal: '正常', late: '迟到', absent: '缺勤' }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    const [overviewData, usersData] = await Promise.all([
      api.get('/statistics/admin/overview'),
      api.get('/statistics/admin/users', { params: { page: pagination.page, page_size: pagination.pageSize, department: filters.department, period: filters.period } })
    ])
    overview.value = overviewData
    users.value = usersData.items
    departments.value = usersData.departments || []
    pagination.total = usersData.total
  } catch (e) {
    ElMessage.error(e.message || '数据同步失败')
  } finally {
    loading.value = false
  }
}

async function viewDetail(user) {
  selectedUser.value = user
  showDetail.value = true
  detailPage.value = 1
  loadDetail()
}

async function loadDetail() {
  try {
    const res = await api.get(`/statistics/admin/user/${selectedUser.value.id}/records`, { params: { page: detailPage.value } })
    records.value = res.records
    detailTotal.value = res.total
  } catch (e) {
    ElMessage.error('获取明细失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.hero-stats {
  margin-bottom: 32px;
}

.kpi-card {
  position: relative;
  height: 140px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  padding: 0 28px;
  overflow: hidden;
  transition: var(--transition-smooth);
}

.kpi-card:hover {
  transform: translateY(-5px);
}

.kpi-icon {
  width: 56px;
  height: 56px;
  background: white;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #334155;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  margin-right: 20px;
  z-index: 2;
}

.kpi-content {
  z-index: 2;
}

.kpi-value {
  font-size: 32px;
  font-weight: 900;
  color: #0f172a;
  line-height: 1;
}

.kpi-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-top: 6px;
}

.kpi-decoration {
  position: absolute;
  top: -20px;
  right: -20px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  opacity: 0.1;
  z-index: 1;
}

.total-border { border-left: 6px solid #10b981; }
.total-bg { background: #10b981; }

.signed-border { border-left: 6px solid #0ea5e9; }
.signed-bg { background: #0ea5e9; }

.late-border { border-left: 6px solid #f59e0b; }
.late-bg { background: #f59e0b; }

.absent-border { border-left: 6px solid #ef4444; }
.absent-bg { background: #ef4444; }

.main-panel {
  padding: 32px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 800;
}

.panel-actions {
  display: flex;
  gap: 12px;
}

.teacher-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-sm {
  width: 36px;
  height: 36px;
  background: #f1f5f9;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  color: #94a3b8;
}

.name-text {
  font-weight: 700;
  font-size: 15px;
}

.id-text {
  font-size: 12px;
  color: #94a3b8;
}

.dept-badge {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.stats-row {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.stat-mini {
  font-size: 12px;
}

.stat-mini .label { color: #94a3b8; margin-right: 4px; }
.stat-mini .val { font-weight: 700; }
.val.success { color: #10b981; }
.val.warning { color: #f59e0b; }
.val.danger { color: #ef4444; }

.rate-box {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
}

.rate-text {
  font-weight: 800;
  font-size: 14px;
}

.pagination-area {
  margin-top: 32px;
  display: flex;
  justify-content: flex-end;
}

.time-bold { font-weight: 800; color: #334155; }
.loc-text { color: #64748b; font-size: 12px; }
.dialog-footer { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
