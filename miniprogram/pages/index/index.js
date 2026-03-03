const api = require('../../utils/api');

Page({
  data: {
    currentTime: '',
    currentDate: '',
    userInfo: null,
    todaySchedule: [],      // 今日签到安排
    checkInStatus: '待签',  // 整体状态文字
    loading: false,
    baseUrl: api.BASE_URL
  },

  onLoad() {
    wx.showLoading({ title: '加载中...' });
    this.updateTime();
    this.timer = setInterval(() => { this.updateTime(); }, 1000);

    Promise.all([
      this.loadUserInfo(),
      this.loadTodaySchedule()
    ]).finally(() => {
      wx.hideLoading();
    });
  },

  onShow() {
    // 每次显示时刷新签到状态
    this.loadTodaySchedule();
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

    // 计算当前时段标签
    const t = now.getHours() * 60 + now.getMinutes();
    let timeLabel = '休息时段';
    if (t >= 6 * 60 + 30 && t < 12 * 60) {
      timeLabel = '早上教学时段';
    } else if (t >= 12 * 60 && t < 13 * 60 + 50) {
      timeLabel = '午休时段';
    } else if (t >= 13 * 60 + 50 && t < 17 * 60 + 30) {
      timeLabel = '下午教学时段';
    } else if (t >= 17 * 60 + 30 && t < 22 * 60 + 30) {
      timeLabel = '晚自习时段';
    }

    this.setData({ currentTime, currentDate, timeLabel });
  },

  // 加载用户信息
  loadUserInfo() {
    const app = getApp();
    // 每次都从 API 获取最新用户信息
    return api.getMe()
      .then(userInfo => {
        console.log('用户信息:', userInfo);
        app.globalData.userInfo = userInfo;
        wx.setStorageSync('userInfo', userInfo);
        this.setData({ userInfo });
        return userInfo;
      })
      .catch(err => {
        console.error('获取用户信息失败', err.message);
        // 如果 API 失败，尝试使用缓存
        const cached = wx.getStorageSync('userInfo');
        if (cached) {
          this.setData({ userInfo: cached });
        }
        throw err;
      });
  },

  // 加载今日签到安排
  loadTodaySchedule() {
    return api.getTodayCheckin()
      .then(res => {
        const now = new Date();
        const t = now.getHours() * 60 + now.getMinutes();

        const items = (res.items || []).map((item, index) => {
          const status = item.status || 'pending';
          // Ensure time bounds exist to prevent "undefined" or NaN display in WXML
          const rawStart = item.time_slot ? (item.time_slot.checkin_start || '00:00') : '00:00';
          const rawEnd = item.time_slot ? (item.time_slot.normal_end || item.time_slot.late_end || '23:59') : '23:59';

          return {
            ...item,
            status: status,
            time_slot: {
              ...(item.time_slot || {}),
              start_time: rawStart.substring(0, 5),
              end_time: rawEnd.substring(0, 5) // Map to WXML expected variables
            }
          };
        });

        const hasSigned = items.some(i => i.status === 'signed' || i.status === 'late');
        const hasUnsigned = items.some(i => i.status === 'unsigned' || i.status === 'absent');
        const allSigned = items.length > 0 && items.every(i => i.status === 'signed' || i.status === 'late');
        const checkInStatus = allSigned ? '已签' : (hasUnsigned ? '未签' : '待签');


        this.setData({ todaySchedule: items, checkInStatus });
        return res;
      })
      .catch(err => {
        console.error('获取今日签到状态失败', err.message);
        throw err;
      });
  },

  // 计算两点之间的距离（单位：米）
  getDistance(lat1, lng1, lat2, lng2) {
    const radLat1 = lat1 * Math.PI / 180.0;
    const radLat2 = lat2 * Math.PI / 180.0;
    const a = radLat1 - radLat2;
    const b = (lng1 * Math.PI / 180.0) - (lng2 * Math.PI / 180.0);
    let s = 2 * Math.asin(Math.sqrt(Math.pow(Math.sin(a / 2), 2) +
      Math.cos(radLat1) * Math.cos(radLat2) * Math.pow(Math.sin(b / 2), 2)));
    s = s * 6378.137; // 地球半径，单位公里
    s = Math.round(s * 10000) / 10; // 单位换算成米
    return s;
  },


  // 打卡逻辑
  onCheckIn() {
    const now = new Date();
    const t = now.getHours() * 60 + now.getMinutes();

    let targetSlotIndex = -1;
    let targetSlot = null;

    // 动态寻找当前允许打卡的时段
    // 条件：状态是 pending 或 unsigned（前端容错），且当前时间 >= checkin_start 且 < late_end
    for (let i = 0; i < this.data.todaySchedule.length; i++) {
      const slotInfo = this.data.todaySchedule[i];
      if (slotInfo.time_slot.checkin_start && slotInfo.time_slot.late_end) {
        const [startH, startM] = slotInfo.time_slot.checkin_start.split(':').map(Number);
        const [lateH, lateM] = slotInfo.time_slot.late_end.split(':').map(Number);
        const startTotal = startH * 60 + startM;
        const lateTotal = lateH * 60 + lateM;

        if (t >= startTotal && t <= lateTotal) {
          if (slotInfo.status === 'signed' || slotInfo.status === 'late') {
            wx.showModal({ title: '提示', content: '你已经成功签到了！', showCancel: false });
            return; // 找到了当面时段但已经签过到了，阻断执行
          }
          targetSlotIndex = i;
          targetSlot = slotInfo;
          break; // Found the active unsigned slot
        }
      }
    }

    if (!targetSlot) {
      const isHeadmaster = this.data.userInfo && this.data.userInfo.is_headmaster;
      let hint = '未在签到时间内';

      if (!isHeadmaster) { // 科任教师
        if (t < 7 * 60 + 30) hint = '未到签到时间';
        else if (t >= 10 * 60 + 10 && t < 10 * 60 + 40) hint = '未到签到时间';
        else if (t >= 12 * 60 && t < 13 * 60 + 30) hint = '未在签到时间内';
        else if (t >= 16 * 60 && t < 16 * 60 + 30) hint = '未到签到时间';
        else if (t >= 17 * 60 + 30) hint = '未在签到时间';
      } else { // 班主任
        if (t < 6 * 60 + 20) hint = '未到签到时间';
        else if (t >= 9 * 60 + 20 && t < 13 * 60 + 30) hint = '未到签到时间';
        else if (t >= 15 * 60 + 10 && t < 16 * 60 + 30) hint = '未在签到时间内';
        else if (t >= 17 * 60 + 40 && t < 18 * 60) hint = '未到签到时间';
        else if (t >= 19 * 60 + 20) hint = '未在签到时间';
      }

      wx.showModal({ title: '提示', content: hint, showCancel: false });
      return;
    }

    // 判断迟到
    let isLate = false;
    if (targetSlot && targetSlot.time_slot.normal_end) {
      const [normH, normM] = targetSlot.time_slot.normal_end.split(':').map(Number);
      isLate = t > (normH * 60 + normM);
    }

    // 2. 验证是否在签到地理范围内
    wx.getLocation({
      type: 'gcj02', // 使用国测局坐标，与微信地图一致
      success: (res) => {
        const latitude = res.latitude;
        const longitude = res.longitude;
        // 学校中心点经纬度 (根据要求，不过通常建议前端使用与服务端相同的坐标系进行距离计算)
        const targetLat = 37.112336;
        const targetLng = 110.098298;

        const distance = this.getDistance(latitude, longitude, targetLat, targetLng);
        console.log("当前经度：", longitude);
        console.log("当前纬度：", latitude);

        if (distance > 4000) {
          wx.showModal({
            title: '提示',
            content: '不在签到范围内',
            showCancel: false
          });
          return;
        }

        // 3. 时间和距离验证都通过，进行打卡
        wx.showModal({
          title: '确认打卡',
          content: `时段：${targetSlot.time_slot.label}\n当前时间：${this.data.currentTime}\n确定要打卡吗？`,
          success: (modalRes) => {
            if (modalRes.confirm) {
              wx.showLoading({ title: '打卡中...' });
              api.doCheckin(targetSlot.time_slot.id)
                .then(record => {
                  wx.hideLoading();
                  wx.showModal({
                    title: '提示',
                    content: isLate ? '签到成功 (迟到)' : '祝贺签到成功',
                    showCancel: false,
                    success: () => {
                      this.loadTodaySchedule(); // 刷新状态
                    }
                  });
                })
                .catch(err => {
                  wx.hideLoading();
                  wx.showToast({ title: err.message || '打卡失败', icon: 'none' });
                });
            }
          }
        });
      },
      fail: (err) => {
        console.error('获取定位失败', err);
        wx.showModal({
          title: '提示',
          content: '获取定位失败，请允许小程序使用位置信息',
          showCancel: false,
          success: (res) => {
            if (res.confirm) {
              wx.openSetting(); // 引导用户打开授权设置
            }
          }
        });
      }
    });
  },

  onShareAppMessage() {
    return {
      title: '清涧中学教师考勤管理系统',
      path: '/pages/index/index'
    };
  },

  switchTab(e) {
    const page = e.currentTarget.dataset.page;
    if (page === 'index') return;
    if (page === 'statistics') {
      wx.reLaunch({ url: '/pages/statistics/statistics' });
    } else if (page === 'profile') {
      wx.reLaunch({ url: '/pages/profile/profile' });
    }
  }
});