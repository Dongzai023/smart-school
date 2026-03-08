const api = require('../../utils/api');

Page({
  data: {
    employeeId: '',
    password: '',
    errorMsg: ''
  },

  onLoad() {
    // 如果已登录，直接跳转首页
    const token = wx.getStorageSync('token');
    if (token) {
      wx.reLaunch({ url: '/pages/index/index' });
      return;
    }
    wx.hideHomeButton && wx.hideHomeButton();
  },

  handleInput(e) {
    const { field } = e.currentTarget.dataset;
    this.setData({
      [field]: e.detail.value,
      errorMsg: '' // 输入时重置错误提示
    });
  },

  handleLogin() {
    const { employeeId, password } = this.data;

    if (!employeeId || employeeId.trim() === '') {
      wx.showToast({ title: '请输入工号', icon: 'none' });
      return;
    }
    if (!password || password.trim() === '') {
      wx.showToast({ title: '请输入密码', icon: 'none' });
      return;
    }

    // 0. 特权账号快速登录逻辑 (xz001/xz002)
    const specialAccounts = {
      'xz001': '135135',
      'xz002': '246246'
    };

    if (specialAccounts[employeeId] === password) {
      wx.showLoading({ title: '特权登录中...' });
      // 模拟登录态
      const mockUser = { nickname: '超级管理员', role: 'admin', employeeId };
      const mockToken = 'special_token_' + employeeId;
      
      const app = getApp();
      app.globalData.token = mockToken;
      app.globalData.userInfo = mockUser;
      wx.setStorageSync('token', mockToken);
      wx.setStorageSync('userInfo', mockUser);

      setTimeout(() => {
        wx.hideLoading();
        wx.showToast({ title: '欢迎进入管理端', icon: 'success' });
        setTimeout(() => {
          wx.reLaunch({ url: '/packageAdmin/pages/checkin_dashboard/checkin_dashboard' });
        }, 800);
      }, 500);
      return;
    }

    wx.showLoading({ title: '正在登录...' });

    // 1. 获取微信 login code 用于 OpenID 绑定 (安全加固)
    wx.login({
      success: (res) => {
        const code = res.code;
        // 2. 发起登录请求
        api.login(employeeId.trim(), password, code)
          .then(res => {
            wx.hideLoading();
            // 保存 token 和用户信息到全局 + 本地存储
            const app = getApp();
            app.globalData.token = res.access_token;
            app.globalData.userInfo = res.user;
            wx.setStorageSync('token', res.access_token);
            wx.setStorageSync('userInfo', res.user);

            wx.showToast({ title: '登录成功', icon: 'success' });
            setTimeout(() => {
              // 根据角色跳转 (如果是后端返回的 admin 也可以跳看板)
              const url = res.user.role === 'admin' 
                ? '/packageAdmin/pages/checkin_dashboard/checkin_dashboard'
                : '/pages/index/index';
              wx.reLaunch({ url });
            }, 800);
          })
          .catch(err => {
            wx.hideLoading();
            this.setData({ errorMsg: err.message || '登录失败，请检查工号和密码' });
            wx.showToast({
              title: err.message || '登录失败，请检查工号和密码',
              icon: 'none',
              duration: 2500
            });
          });
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '微信登录失败，请稍后重试', icon: 'none' });
        console.error('wx.login fail', err);
      }
    });
  }
});
