const api = require('../../../utils/api');

Page({
    data: {
        userInfo: null,
        stats: {
            total: 0,
            normal: 0,
            late: 0,
            absent: 0
        },
        records: [],
        selectedMonth: '',
        loading: false,
        page: 1,
        pageSize: 50,
        hasMore: true,
        baseUrl: api.BASE_URL
    },

    onLoad() {
        // Initialize month
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const selectedMonth = `${year}-${month}`;

        const app = getApp();
        this.setData({
            userInfo: app.globalData.userInfo,
            selectedMonth
        });

        this.fetchStats();
        this.fetchRecords();
    },

    onMonthChange(e) {
        this.setData({
            selectedMonth: e.detail.value,
            records: [],
            page: 1,
            hasMore: true
        }, () => {
            this.fetchStats();
            this.fetchRecords();
        });
    },

    fetchStats() {
        // We use 'month' period for stats based on selected month
        // The API might need enhancement to support specific months, 
        // but for now we follow the general pattern from statistics.js
        api.getStatsOverview('month').then(res => {
            this.setData({
                stats: {
                    total: (res.signed_count || 0) + (res.late_count || 0) + (res.absent_count || 0),
                    normal: res.signed_count || 0,
                    late: res.late_count || 0,
                    absent: res.absent_count || 0
                }
            });
        }).catch(err => {
            console.error('Fetch stats failed:', err);
        });
    },

    fetchRecords() {
        if (this.data.loading) return;

        this.setData({ loading: true });

        const statusMap = {
            'signed': { text: '正常', cls: 'normal' },
            'normal': { text: '正常', cls: 'normal' },
            'late': { text: '迟到', cls: 'late' },
            'absent': { text: '缺勤', cls: 'absent' }
        };

        // Fetching records. PageSize set to 50 for "View All"
        api.getStatsRecords(this.data.pageSize).then(res => {
            const records = (res.records || []).map(r => {
                const slots = (r.slots || []).map(s => ({
                    label: s.label,
                    time: s.time || '--',
                    statusClass: statusMap[s.status] ? statusMap[s.status].cls : 'absent',
                    statusText: statusMap[s.status] ? statusMap[s.status].text : '缺勤'
                }));
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

            this.setData({
                records,
                loading: false,
                hasMore: false // For now assume one page is enough or API doesn't support pagination well
            });
        }).catch(err => {
            console.error('Fetch records failed:', err);
            this.setData({ loading: false });
            wx.showToast({ title: '加载失败', icon: 'none' });
        });
    },

    onPullDownRefresh() {
        this.setData({
            records: [],
            page: 1,
            hasMore: true
        }, () => {
            Promise.all([this.fetchStats(), this.fetchRecords()]).finally(() => {
                wx.stopPullDownRefresh();
            });
        });
    }
});
