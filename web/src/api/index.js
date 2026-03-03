import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
    baseURL: '/api',
    timeout: 15000,
})

// Request interceptor — attach JWT token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Response interceptor — handle errors
api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const msg = error.response?.data?.detail || '请求失败'
        if (error.response?.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            window.location.href = '/login'
        } else {
            ElMessage.error(msg)
        }
        return Promise.reject(error)
    }
)

export default api

/* ========== Auth ========== */
export const authApi = {
    login: (data) => api.post('/auth/login', data),
    getMe: () => api.get('/auth/me'),
    listUsers: () => api.get('/auth/users'),
    createUser: (data) => api.post('/auth/users', data),
    toggleUser: (id) => api.put(`/auth/users/${id}/toggle`),
    changePassword: (data) => api.put('/auth/password', data),
}

/* ========== Devices ========== */
export const deviceApi = {
    list: (groupId) => api.get('/devices', { params: groupId ? { group_id: groupId } : {} }),
    create: (data) => api.post('/devices', data),
    update: (id, data) => api.put(`/devices/${id}`, data),
    delete: (id) => api.delete(`/devices/${id}`),
    statusSummary: () => api.get('/devices/status/summary'),
    // Groups
    listGroups: () => api.get('/devices/groups'),
    createGroup: (data) => api.post('/devices/groups', data),
    updateGroup: (id, data) => api.put(`/devices/groups/${id}`, data),
    deleteGroup: (id) => api.delete(`/devices/groups/${id}`),
}

/* ========== Schedules ========== */
export const scheduleApi = {
    list: () => api.get('/schedules'),
    create: (data) => api.post('/schedules', data),
    update: (id, data) => api.put(`/schedules/${id}`, data),
    delete: (id) => api.delete(`/schedules/${id}`),
    reload: () => api.post('/schedules/reload'),
}

/* ========== Control ========== */
export const controlApi = {
    execute: (data) => api.post('/control/execute', data),
    executeGroup: (data) => api.post('/control/execute-group', data),
}

/* ========== Images ========== */
export const imageApi = {
    list: () => api.get('/images'),
    upload: (formData) => api.post('/images/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
    setDefault: (id) => api.put(`/images/${id}/default`),
    delete: (id) => api.delete(`/images/${id}`),
}

/* ========== Unlock Requests ========== */
export const unlockApi = {
    list: (status) => api.get('/unlock-requests', { params: status ? { status } : {} }),
    create: (data) => api.post('/unlock-requests', data),
    review: (id, data) => api.put(`/unlock-requests/${id}/review`, data),
}

/* ========== Logs ========== */
export const logApi = {
    list: (params) => api.get('/logs', { params }),
}

/* ========== Users (签到用户管理) ========== */
export const userApi = {
    list: (params) => api.get('/users/admin/list', { params }),
    updatePermissions: (userId, data) => api.put(`/users/admin/${userId}/permissions`, data),
    getStats: () => api.get('/users/admin/stats'),
}
