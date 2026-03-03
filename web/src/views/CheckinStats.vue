<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>签到统计</h2>
      <div class="description">查看全校教师签到情况</div>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ overview.total_users || 0 }}</div>
          <div class="stat-label">教师总数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-signed">
          <div class="stat-value">{{ overview.signed_today || 0 }}</div>
          <div class="stat-label">今日已签</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-late">
          <div class="stat-value">{{ overview.late_today || 0 }}</div>
          <div class="stat-label">今日迟到</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-absent">
          <div class="stat-value">{{ overview.absent_today || 0 }}</div>
          <div class="stat-label">今日未签</div>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选和列表 -->
    <div class="content-card">
      <div class="card-title">
        <span>签到明细</span>
        <div class="card-actions">
          <el-select v-model="filters.department" clearable placeholder="全部部门" style="width:140px;margin-right:10px" @change="loadData">
            <el-option v-for="dept in departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
          <el-select v-model="filters.period" placeholder="统计周期" style="width:120px;margin-right:10px" @change="loadData">
            <el-option label="本周" value="week" />
            <el-option label="本月" value="month" />
            <el-option label="本学期" value="semester" />
          </el-select>
          <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
        </div>
      </div>

      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="employee_id" label="工号" min-width="90">
          <template #default="{ row }">
            <span class="nowrap">{{ row.employee_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="real_name" label="姓名" min-width="80" />
        <el-table-column prop="department" label="部门" min-width="100" />
        <el-table-column label="角色" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : (row.role === 'head_teacher' ? 'warning' : 'primary')" size="small">
              {{ row.role === 'admin' ? '管理员' : (row.role === 'head_teacher' ? '班主任' : '教师') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="signed_count" label="已签" min-width="60" align="center">
          <template #default="{ row }">
            <span class="text-success">{{ row.signed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="late_count" label="迟到" min-width="60" align="center">
          <template #default="{ row }">
            <span class="text-warning">{{ row.late_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="absent_count" label="未签" min-width="60" align="center">
          <template #default="{ row }">
            <span class="text-danger">{{ row.absent_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="attendance_rate" label="出勤率" min-width="80" align="center">
          <template #default="{ row }">
            <el-progress :percentage="row.attendance_rate" :color="getRateColor(row.attendance_rate)" :stroke-width="10" :show-text="false" style="width:60px;display:inline-block" />
            <span style="margin-left:8px">{{ row.attendance_rate }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" title="签到记录" width="700px">
      <div v-if="selectedUser" style="margin-bottom:20px">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="姓名">{{ selectedUser.real_name }}</el-descriptions-item>
          <el-descriptions-item label="工号">{{ selectedUser.employee_id }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ selectedUser.department || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <el-table :data="records" size="small" max-height="400">
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column prop="weekday" label="星期" width="70" />
        <el-table-column prop="time" label="时间" width="60" />
        <el-table-column prop="location" label="地点" min-width="100" />
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
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
import { Refresh } from '@element-plus/icons-vue'
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
  if (rate >= 90) return '#67c23a'
  if (rate >= 70) return '#e6a23c'
  return '#f56c6c'
}

function getStatusType(status) {
  const map = { signed: 'success', normal: 'success', late: 'warning', absent: 'danger' }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = { signed: '已签', normal: '已签', late: '迟到', absent: '未签' }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    const [overviewData, usersData] = await Promise.all([
      api.get('/api/statistics/admin/overview'),
      api.get('/api/statistics/admin/users', { params: { page: pagination.page, page_size: pagination.pageSize, department: filters.department, period: filters.period } })
    ])
    overview.value = overviewData
    users.value = usersData.items
    departments.value = usersData.departments || []
    pagination.total = usersData.total
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
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
    const res = await api.get(`/api/statistics/admin/user/${selectedUser.value.id}/records`, { params: { page: detailPage.value } })
    records.value = res.records
    detailTotal.value = res.total
  } catch (e) {
    ElMessage.error(e.message || '加载详情失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.stats-row { margin-bottom: 20px; }

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-card .stat-value { font-size: 32px; font-weight: bold; color: #333; }
.stat-card .stat-label { font-size: 14px; color: #888; margin-top: 5px; }
.stat-signed .stat-value { color: #67c23a; }
.stat-late .stat-value { color: #e6a23c; }
.stat-absent .stat-value { color: #f56c6c; }

.card-actions { display: flex; align-items: center; }
.pagination-wrapper { margin-top: 20px; display: flex; justify-content: flex-end; }
.nowrap { white-space: nowrap; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }
</style>
