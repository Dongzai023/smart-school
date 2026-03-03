/**
 * API 配置与请求工具
 * 后端地址：http://<你的腾讯云服务器IP>:8001
 */

// ========================
// 配置
// ========================
const BASE_URL = 'https://www.qjzxmd.cn';

// API 端点
const API = {
    LOGIN: '/api/auth/login',
    USER_ME: '/api/users/me',
    USER_ME_PASSWORD: '/api/users/me/password',
    USER_ME_ACTIVITIES: '/api/users/me/activities',
    USER_ME_STATS: '/api/users/me/stats',
    USER_ME_AVATAR: '/api/users/me/avatar',
    CHECKIN: '/api/checkin',
    CHECKIN_TODAY: '/api/checkin/today',
    STATS_OVERVIEW: '/api/statistics/overview',
    STATS_TREND: '/api/statistics/trend',
    STATS_TIMESLOT: '/api/statistics/timeslot',
    STATS_RECORDS: '/api/statistics/records',
    ACHIEVEMENTS: '/api/achievements',
    LEAVE_APPLY: '/api/leave/',
    LEAVE_MY_LIST: '/api/leave/my',
};

// ========================
// 核心请求函数
// ========================

/**
 * 发起请求。自动附带 token，统一处理 401。
 * @param {string} url      - API 路径（如 API.USER_ME）
 * @param {string} method   - HTTP 方法，默认 GET
 * @param {object} data     - 请求体（POST/PUT）或查询参数（GET）
 * @returns {Promise<any>}  - 解析后的响应数据
 */
function request(url, method = 'GET', data = {}) {
    const app = getApp();
    const token = app.globalData.token || wx.getStorageSync('token');

    const header = {
        'Content-Type': 'application/json',
    };
    if (token) {
        header['Authorization'] = `Bearer ${token}`;
    }

    return new Promise((resolve, reject) => {
        wx.request({
            url: BASE_URL + url,
            method,
            data,
            header,
            success(res) {
                if (res.statusCode === 401) {
                    // token 失效，清除并跳回登录页
                    app.globalData.token = null;
                    app.globalData.userInfo = null;
                    wx.removeStorageSync('token');
                    wx.reLaunch({ url: '/pages/login/login' });
                    reject(new Error('未登录或登录已过期'));
                    return;
                }
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(res.data);
                } else {
                    const msg = (res.data && res.data.detail) || `请求失败 (${res.statusCode})`;
                    reject(new Error(msg));
                }
            },
            fail(err) {
                reject(new Error(err.errMsg || '网络请求失败'));
            }
        });
    });
}

// ========================
// 封装各模块 API
// ========================

/** 登录 */
function login(employeeId, password) {
    return request(API.LOGIN, 'POST', { employee_id: employeeId, password });
}

/** 获取当前用户信息 */
function getMe() {
    return request(API.USER_ME);
}

/** 更新当前用户信息 */
function updateMe(data) {
    return request(API.USER_ME, 'PUT', data);
}

/** 上传头像 */
function uploadAvatar(filePath) {
    const app = getApp();
    const token = app.globalData.token || wx.getStorageSync('token');

    return new Promise((resolve, reject) => {
        wx.uploadFile({
            url: BASE_URL + API.USER_ME_AVATAR,
            filePath: filePath,
            name: 'file',
            header: {
                'Authorization': `Bearer ${token}`
            },
            success(res) {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    const data = JSON.parse(res.data);
                    resolve(data);
                } else {
                    const data = JSON.parse(res.data);
                    reject(new Error(data.detail || '头像上传失败'));
                }
            },
            fail(err) {
                reject(new Error(err.errMsg || '网络请求失败'));
            }
        });
    });
}

/** 获取今日签到安排 */
function getTodayCheckin() {
    return request(API.CHECKIN_TODAY);
}

/** 打卡签到 */
function doCheckin(timeSlotId, location = '清涧中学') {
    return request(API.CHECKIN, 'POST', { time_slot_id: timeSlotId, location });
}

/** 统计概览 */
function getStatsOverview(period = 'week') {
    return request(`${API.STATS_OVERVIEW}?period=${period}`);
}

/** 签到趋势 */
function getStatsTrend(period = 'week') {
    return request(`${API.STATS_TREND}?period=${period}`);
}

/** 时段分析 */
function getStatsTimeslot(period = 'week') {
    return request(`${API.STATS_TIMESLOT}?period=${period}`);
}

/** 最近签到记录 */
function getStatsRecords(limit = 10) {
    return request(`${API.STATS_RECORDS}?limit=${limit}`);
}

/** 成就勋章 */
function getAchievements() {
    return request(API.ACHIEVEMENTS);
}

/** 最近活动 */
function getActivities() {
    return request(API.USER_ME_ACTIVITIES);
}

/** 用户统计概要 */
function getUserStats() {
    return request(API.USER_ME_STATS);
}

/** 提交请假申请 */
function applyLeave(data) {
    return request(API.LEAVE_APPLY, 'POST', data);
}

/** 获取我的请假记录 */
function getLeaveList(skip = 0, limit = 20) {
    return request(`${API.LEAVE_MY_LIST}?skip=${skip}&limit=${limit}`);
}

module.exports = {
    BASE_URL,
    login,
    getMe,
    updateMe,
    uploadAvatar,
    getTodayCheckin,
    doCheckin,
    getStatsOverview,
    getStatsTrend,
    getStatsTimeslot,
    getStatsRecords,
    getAchievements,
    getActivities,
    getUserStats,
    applyLeave,
    getLeaveList,
};
