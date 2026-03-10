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

    wx.showLoading({ title: '正在登录...' });

    // 获取微信 login code 用于 OpenID 绑定 (安全加固)
    wx.login({
      success: (res) => {
        this._doLogin(employeeId.trim(), password, res.code);
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '微信服务不可用，请稍后重试', icon: 'none' });
        console.error('wx.login fail', err);
      }
    });
  },

  /** 统一处理登录请求 */
  _doLogin(employeeId, password, code) {
    api.login(employeeId, password, code)
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
          // 根据角色跳转 (如果是后端返回的 admin 或 principal 也可以跳看板)
          const isManager = ['admin', 'principal'].includes(res.user.role) || ['all', 'head_teacher', 'subject_teacher'].includes(res.user.view_scope);
          const url = isManager
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
  }
});
