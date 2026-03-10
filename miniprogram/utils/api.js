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
    WX_LOGIN: '/api/auth/wx-login',
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
    LEAVE_APPLY: '/api/leave',
    LEAVE_MY_LIST: '/api/leave/my',
    STATS_PRINCIPAL: '/api/statistics/principal/checkin',
};

// ========================
// 核心请求函数
// ========================

/**
 * 发起请求。自动附带 token，并支持 401 静默登录重试。
 * @param {string} url      - API 路径
 * @param {string} method   - HTTP 方法
 * @param {object} data     - 请求体或查询参数
 * @param {boolean} isRetry - 是否是重试请求，防止死循环
 * @returns {Promise<any>}
 */
function request(url, method = 'GET', data = {}, isRetry = false) {
    const app = getApp();
    const token = (app && app.globalData) ? app.globalData.token : wx.getStorageSync('token');

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
                    if (isRetry) {
                        // 如果重试仍然报 401，说明静默登录失效（可能用户修改了密码或被禁用）
                        app.globalData.token = null;
                        app.globalData.userInfo = null;
                        wx.removeStorageSync('token');
                        wx.reLaunch({ url: '/pages/login/login' });
                        reject(new Error('认证失效，请重新登录'));
                        return;
                    }

                    // 尝试静默登录
                    console.log('Token 可能失效，正在尝试静默登录重试...');
                    wx.login({
                        success: (loginRes) => {
                            wxLogin(loginRes.code).then(authRes => {
                                // 更新 token 并重新发起原请求
                                app.globalData.token = authRes.access_token;
                                app.globalData.userInfo = authRes.user;
                                wx.setStorageSync('token', authRes.access_token);
                                wx.setStorageSync('userInfo', authRes.user);

                                // 发起重试请求
                                request(url, method, data, true).then(resolve).catch(reject);
                            }).catch(err => {
                                // 静默登录失败，清除本地 Token 跳回登录页 (核心修复：防止登录循环)
                                console.error('重试静默登录失败', err);
                                app.globalData.token = null;
                                app.globalData.userInfo = null;
                                wx.removeStorageSync('token');
                                wx.removeStorageSync('userInfo');

                                wx.reLaunch({ url: '/pages/login/login' });
                                reject(new Error('认证失效，请重新登录'));
                            });
                        },
                        fail: reject
                    });
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
function login(employeeId, password, code = null) {
    return request(API.LOGIN, 'POST', { employee_id: employeeId, password, code });
}

/** 微信静默登录 */
function wxLogin(code) {
    return request(API.WX_LOGIN, 'POST', { code });
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
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.CHECKIN_TODAY}?user_id=${userId}`);
}

/** 打卡签到 */
function doCheckin(timeSlotId, location = '清涧中学') {
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.CHECKIN}?user_id=${userId}`, 'POST', { time_slot_id: timeSlotId, location });
}

/** 统计概览 */
function getStatsOverview(period = 'week', userId = null) {
    const params = { period };
    const parsedId = parseInt(userId);
    if (userId && !isNaN(parsedId)) {
        params.user_id = parsedId;
    } else {
        const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
        params.user_id = userInfo ? userInfo.id : 1;
    }
    return request(API.STATS_OVERVIEW, 'GET', params);
}

/** 签到趋势 */
function getStatsTrend(period = 'week') {
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.STATS_TREND}?period=${period}&user_id=${userId}`);
}

/** 时段分析 */
function getStatsTimeslot(period = 'week') {
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.STATS_TIMESLOT}?period=${period}&user_id=${userId}`);
}

/** 最近签到记录 */
function getStatsRecords(pageSize = 10, userId = null) {
    const params = { page_size: pageSize };
    const parsedId = parseInt(userId);
    if (userId && !isNaN(parsedId)) {
        params.user_id = parsedId;
    } else {
        const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
        params.user_id = userInfo ? userInfo.id : 1;
    }
    return request(API.STATS_RECORDS, 'GET', params);
}

/** 成就勋章 */
function getAchievements() {
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.ACHIEVEMENTS}?user_id=${userId}`);
}

/** 最近活动 */
function getActivities() {
    const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
    const userId = userInfo ? userInfo.id : 1;
    return request(`${API.USER_ME_ACTIVITIES}?user_id=${userId}`);
}

/** 用户统计概要 */
function getUserStats(userId = null) {
    const params = {};
    const parsedId = parseInt(userId);
    if (userId && !isNaN(parsedId)) {
        params.user_id = parsedId;
    } else {
        const userInfo = getApp().globalData.userInfo || wx.getStorageSync('userInfo');
        params.user_id = userInfo ? userInfo.id : 1;
    }
    return request(API.USER_ME_STATS, 'GET', params);
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
    wxLogin,
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
    getPrincipalCheckin: (params) => request(API.STATS_PRINCIPAL, 'GET', params),
    getPrincipalDashboard: (params) => {
        return request('/api/statistics/principal/dashboard', 'GET', params);
    },
    updateUserPermissions: (userId, data) => {
        return request(`/api/users/admin/${userId}/permissions`, 'PUT', data);
    },
};
