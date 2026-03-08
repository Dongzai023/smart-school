const api = require('../../../utils/api');

Page({
    data: {
        userId: null,
        user: {
            name: '',
            department: '',
            display_avatar: '/assets/CodeBubbyAssets/2_423/5.svg',
            statusClass: 'normal'
        },
        period: 'session',
        periodLabel: '本次',
        stats: {
            total: 12,
            normal: 10,
            late: 1,
            absent: 1
        },
        records: []
    },

    onLoad(options) {
        const { userId, name, period, department, avatar } = options;
        const periods = {
            'session': '本次时段',
            'today': '今日',
            'week': '本周',
            'month': '本月'
        };

        this.setData({
            userId,
            'user.name': name || '未知老师',
            'user.department': department || '教师',
            'user.display_avatar': avatar ? decodeURIComponent(avatar) : '/assets/CodeBubbyAssets/2_423/5.svg',
            period: period || 'session',
            periodLabel: periods[period] || '时段'
        }, () => {
            console.log('User Detail Load: userId=', this.data.userId, 'period=', this.data.period);
            this.fetchUserRecords();
            this.fetchUserStats();
        });
    },

    fetchUserRecords() {
        const { userId } = this.data;
        // 获取个人打卡详细记录 (后端返回的是按日分组的汇总)
        api.getStatsRecords(20, userId).then(res => {
            const records = (res.records || []).map(r => {
                return {
                    id: r.id || Math.random(),
                    day: String(r.day).padStart(2, '0'),
                    month: r.month,
                    time: r.first_checkin_time || '--:--',
                    statusText: r.status === 'normal' ? '正常签到' : (r.status === 'late' ? '迟到' : '缺勤'),
                    statusClass: r.status,
                    location: r.location || '清涧中学'
                };
            });
            this.setData({ records });
        }).catch(err => {
            console.error('Fetch user records failed:', err);
        });
    },

    fetchUserStats() {
        const { userId, period } = this.data;
        // 使用 getStatsOverview 获取更准确的出勤统计 (包含 absent)
        api.getStatsOverview(period || 'month', userId).then(res => {
            this.setData({
                stats: {
                    total: (res.signed_count || 0) + (res.late_count || 0) + (res.absent_count || 0),
                    normal: res.signed_count || 0,
                    late: res.late_count || 0,
                    absent: res.absent_count || 0
                }
            });
        }).catch(err => {
            console.error('Fetch user stats failed:', err);
            // 如果 overview 失败，回退到 getUserStats (虽然字段不同，但作为兜底)
            api.getUserStats(userId).then(res => {
                this.setData({
                    stats: {
                        total: res.total_checkins || 0,
                        normal: res.on_time_count || 0,
                        late: res.late_count || 0,
                        absent: 0 // getUserStats 暂不返回缺勤
                    }
                });
            });
        });
    }
});
