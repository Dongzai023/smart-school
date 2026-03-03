// pages/scan-unlock/scan-unlock.js
const api = require('../../utils/api');

Page({
    data: {
        status: 'loading', // loading | success | error | no_permission | no_login
        message: '',
        deviceName: '',
        agentKey: '',
    },

    onLoad(options) {
        // 从二维码 URL 参数中提取 device_id (即 agent_key)
        const agentKey = options.device_id || '';

        if (!agentKey) {
            this.setData({
                status: 'error',
                message: '无效的二维码',
            });
            return;
        }

        // 检查是否已登录
        const token = wx.getStorageSync('token');
        if (!token) {
            this.setData({
                status: 'no_login',
                message: '请先登录签到系统',
            });
            return;
        }

        this.setData({ agentKey });
        this.doUnlock(agentKey);
    },

    doUnlock(agentKey) {
        this.setData({ status: 'loading', message: '正在验证权限...' });

        api.scanUnlock(agentKey)
            .then(res => {
                if (res.success) {
                    this.setData({
                        status: 'success',
                        message: res.message || '解锁成功',
                        deviceName: res.device_name || '',
                    });
                    // 振动反馈
                    wx.vibrateShort({ type: 'medium' });
                } else {
                    const statusType = (res.message || '').includes('权限') ? 'no_permission' : 'error';
                    this.setData({
                        status: statusType,
                        message: res.message || '解锁失败',
                        deviceName: res.device_name || '',
                    });
                }
            })
            .catch(err => {
                const msg = err.message || '网络请求失败';
                if (msg.includes('登录') || msg.includes('过期')) {
                    this.setData({
                        status: 'no_login',
                        message: msg,
                    });
                } else {
                    this.setData({
                        status: 'error',
                        message: msg,
                    });
                }
            });
    },

    // 重试
    onRetry() {
        if (this.data.agentKey) {
            this.doUnlock(this.data.agentKey);
        }
    },

    // 去登录
    goLogin() {
        wx.reLaunch({ url: '/pages/login/login' });
    },

    // 返回首页
    goHome() {
        wx.reLaunch({ url: '/pages/index/index' });
    },
});
