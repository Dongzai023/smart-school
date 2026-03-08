const api = require('../../../utils/api');

Page({
    data: {
        type: 'all', // normal, late, absent, leave, all
        users: [],
        filteredUsers: [],
        searchQuery: '',
        refreshing: false,
        period: 'session'
    },

    onLoad(options) {
        const { type, period } = options;
        const titles = {
            'normal': '正常签到人员',
            'late': '迟到人员名单',
            'absent': '缺勤异常名单',
            'leave': '请假人员列表',
            'all': '全部人员'
        };

        const categoryLabels = {
            'normal': '正常统计',
            'late': '迟到统计',
            'absent': '缺勤统计',
            'leave': '请假统计',
            'all': '应到统计'
        };

        wx.setNavigationBarTitle({ title: titles[type] || '人员列表' });

        this.setData({
            type: type || 'all',
            period: period || 'session',
            categoryLabel: categoryLabels[type] || '人员统计'
        }, () => {
            this.fetchUsers();
        });
    },

    onRefresh() {
        this.setData({ refreshing: true });
        this.fetchUsers(() => {
            this.setData({ refreshing: false });
        });
    },

    fetchUsers(cb) {
        api.getPrincipalDashboard({
            period: this.data.period
        }).then(res => {
            let rawList = [];
            if (this.data.type === 'all') {
                rawList = [
                    ...(res.categories.normal || []),
                    ...(res.categories.late || []),
                    ...(res.categories.absent || [])
                ];
            } else {
                rawList = res.categories[this.data.type] || [];
            }

            const users = rawList.map(u => ({
                ...u,
                statusText: this.getStatusText(u),
                statusClass: this.data.type === 'all' ? 'normal' : this.data.type
            }));

            this.setData({ users }, () => this.filterUsers());
            if (cb) cb();
        }).catch(err => {
            console.error('Fetch users failed:', err);
            if (cb) cb();
        });
    },

    getStatusText(user) {
        if (this.data.type === 'normal') return '正常';
        if (this.data.type === 'late') return '迟到';
        if (this.data.type === 'absent') return '缺勤';
        if (this.data.type === 'leave') return '请假';
        return '正常';
    },

    onSearchInput(e) {
        this.setData({ searchQuery: e.detail.value }, () => {
            this.filterUsers();
        });
    },

    filterUsers() {
        const { users, searchQuery } = this.data;
        if (!searchQuery) {
            this.setData({ filteredUsers: users });
            return;
        }
        const filtered = users.filter(u =>
            u.real_name.toLowerCase().indexOf(searchQuery.toLowerCase()) !== -1 ||
            u.department.toLowerCase().indexOf(searchQuery.toLowerCase()) !== -1
        );
        this.setData({ filteredUsers: filtered });
    },

    goToUserDetail(e) {
        const { user } = e.currentTarget.dataset;
        wx.navigateTo({
            url: `../user_detail/user_detail?userId=${user.id}&name=${user.real_name}&period=${this.data.period}&department=${user.department}`
        });
    }
});
