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
            'user.name': name ? decodeURIComponent(name) : '未知老师',
            'user.department': department ? decodeURIComponent(department) : '教师',
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
        const { userId, period } = this.data;
        const statusMap = {
            'signed': { text: '正常', cls: 'normal' },
            'normal': { text: '正常', cls: 'normal' },
            'late': { text: '迟到', cls: 'late' },
            'absent': { text: '缺勤', cls: 'absent' },
            'pending': { text: '待打卡', cls: 'pending' }
        };
        api.getStatsRecords(50, userId, period).then(res => {
            const records = (res.records || []).map(r => {
                const slots = (r.slots || []).map(s => ({
                    label: s.label,
                    time: s.time || '--',
                    statusClass: statusMap[s.status] ? statusMap[s.status].cls : 'absent',
                    statusText: statusMap[s.status] ? statusMap[s.status].text : '缺勤',
                    hasData: !!s.time
                }));
                // 处理月份，去掉 "月" 字
                const monthNum = r.month ? r.month.replace('月', '') : '';
                return {
                    id: r.date || Math.random(),
                    day: String(r.day).padStart(2, '0'),
                    month: monthNum,
                    dateStr: `${String(r.day).padStart(2, '0')}/${monthNum}`,
                    weekday: r.weekday || '',
                    statusClass: r.status === 'normal' ? 'normal' : (r.status === 'late' ? 'late' : 'absent'),
                    slots: slots
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
                    // "总打卡" 在此处统一为“应打卡总数”，以便和列表长度逻辑一致
                    total: res.total_count || 0,
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
                        total: (res.on_time_count || 0) + (res.late_count || 0),
                        normal: res.on_time_count || 0,
                        late: res.late_count || 0,
                        absent: 0 // getUserStats 暂不返回缺勤
                    }
                });
            });
        });
    }
});
