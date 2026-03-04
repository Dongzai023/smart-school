const api = require('../../utils/api');

Page({
  data: {
    userInfo: null,
    activities: [],
    punchesCount: 0,
    attendanceRate: 0,
    schoolRank: 0,
    unlocked_count: 0,
    total_count: 0,
    darkMode: false,
    baseUrl: api.BASE_URL,
    // 编辑弹窗
    showEditModal: false,
    editForm: {},
    genderOptions: ['男', '女'],
    editGenderIndex: -1,
    isSaving: false
  },

  onLoad() {
    wx.showLoading({ title: '加载中...' });
    Promise.all([
      this.loadUserInfo(),
      this.loadActivities(),
      this.loadUserStats()
    ]).finally(() => {
      wx.hideLoading();
    });
  },

  onShow() {
    // 每次显示时刷新用户数据（防止修改资料后信息过时）
    this.loadUserInfo();
  },

  // 加载用户信息
  loadUserInfo() {
    const app = getApp();
    if (app.globalData.userInfo) {
      this.setData({ userInfo: app.globalData.userInfo });
    }
    return api.getMe()
      .then(userInfo => {
        app.globalData.userInfo = userInfo;
        wx.setStorageSync('userInfo', userInfo);
        this.setData({ userInfo });
        return userInfo;
      })
      .catch(err => {
        console.error('获取用户信息失败', err.message);
        throw err;
      });
  },

  // 加载最近活动
  loadActivities() {
    return api.getActivities()
      .then(res => {
        this.setData({ activities: res.items || [] });
        return res;
      })
      .catch(err => {
        console.error('获取最近活动失败', err.message);
        throw err;
      });
  },

  // 加载统计状态
  loadUserStats() {
    return api.getUserStats()
      .then(stats => {
        this.setData({
          punchesCount: stats.total_days,
          attendanceRate: stats.attendance_rate,
          schoolRank: stats.rank,
          unlocked_count: stats.achievement_count,
          total_count: stats.total_achievements || 6  // Backend currently doesn't provide total_achievements in user_stats, so fallback to 6
        });
        return stats;
      })
      .catch(err => {
        console.error('获取用户统计失败', err.message);
        throw err;
      });
  },

  // 复制工号
  copyId() {
    const id = (this.data.userInfo && this.data.userInfo.employee_id) || '';
    wx.setClipboardData({
      data: id,
      success: () => {
        wx.showToast({ title: '工号已复制', icon: 'success' });
      }
    });
  },

  // 上传头像
  onUploadAvatar() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const filePath = res.tempFilePaths[0];
        wx.showLoading({ title: '上传中...' });
        api.uploadAvatar(filePath)
          .then(() => {
            wx.showToast({ title: '头像更新成功', icon: 'success' });
            this.loadUserInfo(); // 重新加载用户信息以刷新头像
          })
          .catch(err => {
            wx.showToast({ title: err.message || '上传失败', icon: 'none' });
          })
          .finally(() => {
            wx.hideLoading();
          });
      }
    });
  },

  // 显示编辑弹窗
  showEditProfile() {
    const userInfo = this.data.userInfo || {};
    let editGenderIndex = -1;
    if (userInfo.gender === '男') editGenderIndex = 0;
    else if (userInfo.gender === '女') editGenderIndex = 1;

    this.setData({
      showEditModal: true,
      editForm: { ...userInfo },
      editGenderIndex
    });
  },

  // 隐藏编辑弹窗
  hideEditProfile() {
    this.setData({ showEditModal: false });
  },

  // 编辑性别选择
  onEditGenderChange(e) {
    this.setData({
      editGenderIndex: e.detail.value
    });
  },

  // 提交编辑表单
  submitEditForm(e) {
    const formData = e.detail.value;
    const { editGenderIndex, genderOptions } = this.data;

    if (editGenderIndex >= 0) {
      formData.gender = genderOptions[editGenderIndex];
    }

    this.setData({ isSaving: true });
    wx.showLoading({ title: '保存中...' });

    api.updateMe(formData)
      .then(updatedInfo => {
        const app = getApp();
        app.globalData.userInfo = updatedInfo;
        wx.setStorageSync('userInfo', updatedInfo);
        this.setData({ userInfo: updatedInfo, showEditModal: false });
        wx.showToast({ title: '保存成功', icon: 'success' });
      })
      .catch(err => {
        console.error('保存失败', err);
        wx.showToast({ title: err.message || '保存失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ isSaving: false });
        wx.hideLoading();
      });
  },

  goToMessages() { wx.showToast({ title: '消息通知', icon: 'none' }); },
  goToLeaveApplication() {
    wx.navigateTo({
      url: '/pages/leave-application/leave-application'
    });
  },
  goToAchievements() { wx.showToast({ title: '我的成就', icon: 'none' }); },
  goToSettings() { wx.showToast({ title: '系统设置', icon: 'none' }); },
  viewActivityDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.showToast({ title: `活动 #${id}`, icon: 'none' });
  },
  goToProfile() { wx.showToast({ title: '个人资料', icon: 'none' }); },
  goToSecurity() { wx.showToast({ title: '账号安全', icon: 'none' }); },
  goToEmail() { wx.showToast({ title: '邮箱绑定', icon: 'none' }); },
  goToNotification() { wx.showToast({ title: '通知设置', icon: 'none' }); },
  goToLanguage() { wx.showToast({ title: '语言设置', icon: 'none' }); },
  goToHelp() { wx.showToast({ title: '帮助中心', icon: 'none' }); },
  goToAbout() { wx.showToast({ title: '关于我们', icon: 'none' }); },
  goToFeedback() { wx.showToast({ title: '意见反馈', icon: 'none' }); },

  // 切换深色模式
  toggleDarkMode(e) {
    this.setData({ darkMode: e.detail.value });
    wx.showToast({ title: e.detail.value ? '深色模式已开启' : '深色模式已关闭', icon: 'none' });
  },

  // 退出登录 — 清除 token 后跳回登录页
  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      confirmColor: '#FF2056',
      success: (res) => {
        if (res.confirm) {
          // 清除所有登录状态
          const app = getApp();
          app.globalData.token = null;
          app.globalData.userInfo = null;
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');

          wx.showToast({ title: '已退出登录', icon: 'success' });
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/login/login' });
          }, 800);
        }
      }
    });
  },

  // 切换底部导航
  switchTab(e) {
    const page = e.currentTarget.dataset.page;
    if (page === 'profile') return;
    if (page === 'index') {
      wx.reLaunch({ url: '/pages/index/index' });
    } else if (page === 'statistics') {
      wx.reLaunch({ url: '/pages/statistics/statistics' });
    }
  },

  onShareAppMessage() {
    return {
      title: '清涧中学教师考勤管理系统',
      path: '/pages/profile/profile'
    };
  }
});
