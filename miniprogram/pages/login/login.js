const api = require('../../utils/api');

Page({
  data: {
    employeeId: '',
    password: ''
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
      [field]: e.detail.value
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

    wx.showLoading({ title: '正在登录...' });

    api.login(employeeId.trim(), password)
      .then(res => {
        wx.hideLoading();
        // 保存 token 和用户信息到全局 + 本地存储
        const app = getApp();
        app.globalData.token = res.access_token;
        app.globalData.userInfo = res.teacher;
        wx.setStorageSync('token', res.access_token);
        wx.setStorageSync('userInfo', res.teacher);

        wx.showToast({ title: '登录成功', icon: 'success' });
        setTimeout(() => {
          wx.reLaunch({ url: '/pages/index/index' });
        }, 800);
      })
      .catch(err => {
        wx.hideLoading();
        wx.showToast({
          title: err.message || '登录失败，请检查工号和密码',
          icon: 'none',
          duration: 2500
        });
      });
  }
});
