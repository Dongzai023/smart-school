App({
  onLaunch() {
    // 恢复本地登录态
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    if (token) {
      this.globalData.token = token;
    }
    if (userInfo) {
      this.globalData.userInfo = userInfo;
    }
  },
  globalData: {
    token: null,
    userInfo: null
  }
})