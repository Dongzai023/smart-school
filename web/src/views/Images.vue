<template>
  <div class="fade-in">
    <div class="page-header">
      <h2>锁屏画面管理</h2>
      <div class="description">上传和管理锁屏背景图片，支持按设备组分配</div>
    </div>

    <div class="content-card">
      <div class="card-title">
        <span>画面列表</span>
        <el-button type="primary" size="small" @click="showUpload = true" v-if="isAdmin">
          <el-icon><Upload /></el-icon> 上传图片
        </el-button>
      </div>

      <div v-if="images.length === 0" style="text-align:center;padding:40px;color:#909399;">
        暂无锁屏画面，请上传图片
      </div>

      <el-row :gutter="20">
        <el-col :span="6" v-for="img in images" :key="img.id">
          <div class="image-card" :class="{ 'is-default': img.is_default }">
            <div class="image-preview">
              <img :src="img.url" :alt="img.name" />
              <div class="image-overlay">
                <el-button-group>
                  <el-button size="small" type="primary" @click="setDefault(img.id)" v-if="isAdmin && !img.is_default">设为默认</el-button>
                  <el-popconfirm title="确定删除?" @confirm="deleteImage(img.id)" v-if="isAdmin">
                    <template #reference>
                      <el-button size="small" type="danger">删除</el-button>
                    </template>
                  </el-popconfirm>
                </el-button-group>
              </div>
            </div>
            <div class="image-info">
              <div class="image-name">{{ img.name }}</div>
              <el-tag v-if="img.is_default" type="success" size="small">默认</el-tag>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="showUpload" title="上传锁屏图片" width="500">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="图片名称">
          <el-input v-model="uploadForm.name" placeholder="如：校园风景" />
        </el-form-item>
        <el-form-item label="选择图片">
          <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".jpg,.jpeg,.png,.bmp,.webp"
            :on-change="handleFile" list-type="picture" drag>
            <el-icon style="font-size:48px;color:#c0c4cc;"><Upload /></el-icon>
            <div>拖拽图片到此处，或点击上传</div>
          </el-upload>
        </el-form-item>
        <el-form-item label="目标分组">
          <el-select v-model="uploadForm.group_id" clearable placeholder="全部设备">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="uploadForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { imageApi, deviceApi } from '../api'

const images = ref([])
const groups = ref([])
const showUpload = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const selectedFile = ref(null)

const currentUser = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const uploadForm = reactive({ name: '', group_id: null, is_default: false })

async function loadData() {
  ;[images.value, groups.value] = await Promise.all([imageApi.list(), deviceApi.listGroups()])
}

function handleFile(file) {
  selectedFile.value = file.raw
}

async function doUpload() {
  if (!uploadForm.name || !selectedFile.value) {
    ElMessage.warning('请填写名称并选择图片')
    return
  }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('name', uploadForm.name)
    if (uploadForm.group_id) fd.append('assigned_group_id', uploadForm.group_id)
    fd.append('is_default', uploadForm.is_default)
    await imageApi.upload(fd)
    ElMessage.success('上传成功')
    showUpload.value = false
    selectedFile.value = null
    Object.assign(uploadForm, { name: '', group_id: null, is_default: false })
    loadData()
  } finally {
    uploading.value = false
  }
}

async function setDefault(id) {
  await imageApi.setDefault(id)
  ElMessage.success('设置成功')
  loadData()
}

async function deleteImage(id) {
  await imageApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.image-card {
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid transparent;
  margin-bottom: 20px;
  transition: all 0.3s;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.image-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}

.image-card.is-default {
  border-color: #67c23a;
}

.image-preview {
  position: relative;
  height: 160px;
  overflow: hidden;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-preview:hover .image-overlay {
  opacity: 1;
}

.image-info {
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.image-name {
  font-size: 14px;
  font-weight: 500;
}
</style>
