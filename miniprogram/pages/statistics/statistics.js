const api = require('../../utils/api');

Page({
  data: {
    currentTime: '',
    currentDate: '',
    selectedTab: 'week',   // week | month | semester
    // 统计概览
    attendanceRate: 0,
    signedCount: 0,
    lateCount: 0,
    absentCount: 0,
    schoolRank: 0,
    rankLabel: '',
    // 趋势
    trendDays: [],
    // 时段分析
    timeslotStats: [],
    // 最近记录
    recentRecords: [],
    // 成就勋章
    items: [],
    unlocked_count: 0,
    total_count: 0,
    loading: false
  },

  onLoad() {
    this.updateTime();
    this.timer = setInterval(() => { this.updateTime(); }, 1000);
    this.loadAllStats('week');
  },

  onUnload() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const currentTime = `${hours}:${minutes}:${seconds}`;
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const date = now.getDate();
    const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const weekDay = weekDays[now.getDay()];
    const currentDate = `${year}年${month}月${date}日 ${weekDay}`;
    this.setData({ currentTime, currentDate });
  },

  // 切换时间标签（week / month / semester）
  onTabSwitch(e) {
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.selectedTab) return;
    this.setData({ selectedTab: tab });
    this.loadAllStats(tab);
  },

  // 加载所有统计数据
  loadAllStats(period) {
    wx.showLoading({ title: '加载中...' });
    this.setData({ loading: true });
    Promise.all([
      api.getStatsOverview(period),
      api.getStatsTrend(period),
      api.getStatsTimeslot(period),
      api.getStatsRecords(10),
      api.getAchievements()
    ])
      .then(([overview, trend, timeslot, records, achievements]) => {
        const timeslotItems = (timeslot.items || []).map(item => ({
          ...item,
          label: item.time_slot.label, // Flatten label for WXML
          time_range: `${(item.time_slot.start_time || '').substring(0, 5)}-${(item.time_slot.end_time || '').substring(0, 5)}`
        }));
        const attendanceRate = typeof overview.attendance_rate === 'number' ?
          overview.attendance_rate :
          parseFloat(overview.attendance_rate || 0);

        this.setData({
          attendanceRate: attendanceRate,
          signedCount: overview.signed_count,
          lateCount: overview.late_count,
          absentCount: overview.absent_count,
          schoolRank: overview.school_rank,
          rankLabel: overview.rank_label || '',
          trendDays: trend.days || [],
          timeslotStats: timeslotItems,
          recentRecords: records.records || [],
          items: achievements.items || [],
          unlocked_count: achievements.unlocked_count || 0,
          total_count: achievements.total_count || 0
        });
      })
      .catch(err => {
        console.error('加载统计数据失败', err.message);
        wx.showToast({ title: '加载失败，请重试', icon: 'none' });
      })
      .finally(() => {
        this.setData({ loading: false });
        wx.hideLoading();
      });
  },

  // 查看全部记录
  viewAllRecords() {
    wx.showToast({ title: '查看全部记录', icon: 'none' });
  },

  // 切换底部导航
  switchTab(e) {
    const page = e.currentTarget.dataset.page;
    if (page === 'statistics') return;
    if (page === 'index') {
      wx.reLaunch({ url: '/pages/index/index' });
    } else if (page === 'profile') {
      wx.reLaunch({ url: '/pages/profile/profile' });
    }
  },

  onShareAppMessage() {
    return {
      title: '清涧中学考勤统计',
      path: '/pages/statistics/statistics'
    };
  }
});
