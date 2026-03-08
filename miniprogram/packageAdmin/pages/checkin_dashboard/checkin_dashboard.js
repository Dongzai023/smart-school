const api = require('../../../utils/api');

Page({
    data: {
        periods: [
            { id: 'session', label: '本次' },
            { id: 'today', label: '今日' },
            { id: 'week', label: '本周' },
            { id: 'month', label: '本月' },
            { id: 'semester', label: '学期' }
        ],
        activePeriod: 'session',
        activePeriodIndex: 0,
        summary: {
            total: 0,
            normal_count: 0,
            late_count: 0,
            absent_count: 0,
            leave_count: 0,
            rate: 0
        },
        categories: {
            normal: [],
            late: [],
            absent: []
        },
        expanded: {
            normal: false
        },
        sessionLabel: '',
        activePeriodLabel: '本次',
        dateRange: '',
        loading: true,
        percentages: {
            normal: '0',
            late: '0',
            absent: '0',
            leave: '0'
        },
        badgeStatus: 'warning',
        badgeText: '需关注',
        baseUrl: api.BASE_URL,
        totalLabel: '当前应到人数'
    },

    onLoad: function () {
        this.fetchData();
    },

    onPullDownRefresh: function () {
        this.fetchData(() => {
            wx.stopPullDownRefresh();
        });
    },

    onPeriodChange: function (e) {
        const period = e.currentTarget.dataset.period;
        if (period === this.data.activePeriod) return;

        const index = this.data.periods.findIndex(p => p.id === period);
        this.setData({
            activePeriod: period,
            activePeriodIndex: index,
            activePeriodLabel: this.data.periods[index].label
        });
        this.fetchData();
    },

    toggleCategory: function (e) {
        const cat = e.currentTarget.dataset.cat;
        this.setData({
            [`expanded.${cat}`]: !this.data.expanded[cat]
        });
    },

    fetchData: function (callback) {
        this.setData({ loading: true });
        api.getPrincipalDashboard({ period: this.data.activePeriod })
            .then(res => {
                const rate = res.summary.rate || 0;

                // Calculate percentages
                const total = res.summary.total || 0;
                const percentages = {
                    normal: total > 0 ? ((res.summary.normal_count / total) * 100).toFixed(1) : '0',
                    late: total > 0 ? ((res.summary.late_count / total) * 100).toFixed(1) : '0',
                    absent: total > 0 ? ((res.summary.absent_count / total) * 100).toFixed(1) : '0',
                    leave: total > 0 ? (((res.summary.leave_count || 0) / total) * 100).toFixed(1) : '0'
                };

                // Calculate badge status
                const badgeStatus = rate >= 90 ? 'excellent' : (rate >= 80 ? 'good' : 'warning');
                const badgeText = rate >= 90 ? '优秀' : (rate >= 80 ? '良好' : '需关注');

                // Process avatars for all categories
                const processList = (list) => {
                    return (list || []).map(item => {
                        let avatar = item.avatar_url || item.avatar;
                        let display_avatar = '/assets/CodeBubbyAssets/2_423/5.svg';

                        if (avatar && typeof avatar === 'string') {
                            if (avatar.startsWith('http')) {
                                display_avatar = avatar;
                            } else {
                                // Ensure single leading slash
                                const normalizedPath = avatar.startsWith('/') ? avatar : '/' + avatar;
                                display_avatar = api.BASE_URL + normalizedPath;
                            }
                        }

                        return { ...item, display_avatar };
                    });
                };

                // Formatting data for display
                this.setData({
                    summary: {
                        total: res.summary.total || 0,
                        normal_count: res.summary.normal_count || 0,
                        late_count: res.summary.late_count || 0,
                        absent_count: res.summary.absent_count || 0,
                        leave_count: res.summary.leave_count || 0,
                        rate: rate
                    },
                    categories: {
                        normal: processList(res.categories.normal),
                        late: processList(res.categories.late),
                        absent: processList(res.categories.absent)
                    },
                    sessionLabel: res.session_label || '',
                    dateRange: res.date_range || '',
                    dashboardTitle: res.dashboard_title || '清涧中学签到数据看板',
                    percentages: percentages,
                    badgeStatus: badgeStatus,
                    badgeText: badgeText,
                    debugInfo: res.debug_user || null
                });
                if (callback) callback();
            })
            .catch(err => {
                console.error('Fetch error:', err);
                wx.showToast({ title: '暂时无法连接数据中心', icon: 'none' });
                // Set default values on error
                this.setData({
                    loading: false,
                    badgeStatus: 'warning',
                    badgeText: '需关注'
                });
            })
            .finally(() => {
                this.setData({ loading: false });
            });
    },

    goToUserList: function (e) {
        const type = e.currentTarget.dataset.type;
        wx.navigateTo({
            url: `../user_list/user_list?type=${type}&period=${this.data.activePeriod}`
        });
    }
});
