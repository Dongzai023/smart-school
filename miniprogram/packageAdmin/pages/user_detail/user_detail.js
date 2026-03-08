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
        const { userId, name, period, department } = options;
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
            period: period || 'session',
            periodLabel: periods[period] || '时段'
        });

        this.fetchUserRecords();
    },

    fetchUserRecords() {
        // 获取个人打卡详细记录
        api.getStatsRecords(20).then(res => {
            // 后端返回的记录可能需要简单的格式化以匹配 UI 需求
            const records = (res.records || []).map(r => {
                const date = new Date(r.checkin_time);
                return {
                    id: r.id,
                    day: String(date.getDate()).padStart(2, '0'),
                    month: (date.getMonth() + 1) + '月',
                    time: r.checkin_time ? r.checkin_time.split(' ')[1].substring(0, 5) : '--:--',
                    statusText: r.status === 'normal' ? '正常签到' : (r.status === 'late' ? '迟到' : '缺勤'),
                    statusClass: r.status,
                    location: r.location || '未知位置'
                };
            });
            this.setData({ records });
        }).catch(err => {
            console.error('Fetch user records failed:', err);
        });
    }
});
