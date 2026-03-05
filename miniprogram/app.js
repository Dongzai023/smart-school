App({
  onLaunch() {
    this.checkLogin();
  },

  checkLogin() {
    const api = require('./utils/api');
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');

    if (token && userInfo) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo;

      // 校验 token 是否有效 (异步执行，不阻塞启动)
      api.getMe().catch(() => {
        // 如果 token 失效，尝试静默登录
        this.doSilentLogin();
      });
    } else {
      // 无登录态，尝试静默登录
      this.doSilentLogin();
    }
  },

  doSilentLogin() {
    const api = require('./utils/api');
    wx.login({
      success: (res) => {
        api.wxLogin(res.code).then(res => {
          this.globalData.token = res.access_token;
          this.globalData.userInfo = res.user;
          wx.setStorageSync('token', res.access_token);
          wx.setStorageSync('userInfo', res.user);
          console.log('静默登录成功');
        }).catch(err => {
          console.log('静默登录失败，可能未绑定', err);
        });
      }
    });
  },

  globalData: {
    token: null,
    userInfo: null
  }
})