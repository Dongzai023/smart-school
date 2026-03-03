const api = require('../../utils/api');

Page({
    data: {
        currentTab: 'apply', // 'apply' or 'history'

        // 表单数据
        leaveTypes: ['公假', '事假', '病假', '年休假', '婚假', '产假', '丧假', '其他'],
        typeIndex: -1,
        startDate: '',
        startTime: '',
        endDate: '',
        endTime: '',
        reason: '',
        isSaving: false,

        // 历史记录数据
        historyList: [],
        statusMap: {
            'pending': '处理中',
            'approved': '已批准',
            'rejected': '已驳回'
        },
        page: 0,
        pageSize: 10,
        hasMore: true,
        isLoadingMore: false,
        totalRecords: 0
    },

    onLoad(options) {
        // 设置默认起始时间和结束时间 (今天到明天)
        const now = new Date();
        const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

        this.setData({
            startDate: this.formatDate(now),
            startTime: '08:00',
            endDate: this.formatDate(tomorrow),
            endTime: '17:00'
        });

        if (options.tab === 'history') {
            this.setData({ currentTab: 'history' });
            this.loadHistory(true);
        }
    },

    onShow() {
        if (this.data.currentTab === 'history' && this.data.historyList.length === 0) {
            this.loadHistory(true);
        }
    },

    switchTab(e) {
        const tab = e.currentTarget.dataset.tab;
        this.setData({ currentTab: tab });

        if (tab === 'history' && this.data.historyList.length === 0) {
            this.loadHistory(true);
        }
    },

    // --- 表单处理 ---

    onTypeChange(e) {
        this.setData({ typeIndex: e.detail.value });
    },

    onStartDateChange(e) { this.setData({ startDate: e.detail.value }); },
    onStartTimeChange(e) { this.setData({ startTime: e.detail.value }); },
    onEndDateChange(e) { this.setData({ endDate: e.detail.value }); },
    onEndTimeChange(e) { this.setData({ endTime: e.detail.value }); },

    submitForm(e) {
        const { reason } = e.detail.value;
        const { typeIndex, leaveTypes, startDate, startTime, endDate, endTime } = this.data;

        if (typeIndex < 0) return wx.showToast({ title: '请选择请假类型', icon: 'none' });
        if (!startDate || !startTime) return wx.showToast({ title: '请选择完整开始时间', icon: 'none' });
        if (!endDate || !endTime) return wx.showToast({ title: '请选择完整结束时间', icon: 'none' });
        if (!reason || !reason.trim()) return wx.showToast({ title: '请填写请假事由', icon: 'none' });

        const startDateTimeStr = `${startDate}T${startTime}:00`;
        const endDateTimeStr = `${endDate}T${endTime}:00`;

        const startTimeStamp = new Date(startDateTimeStr).getTime();
        const endTimeStamp = new Date(endDateTimeStr).getTime();

        if (startTimeStamp >= endTimeStamp) {
            return wx.showToast({ title: '结束时间必须晚于开始时间', icon: 'none' });
        }

        const start_time = new Date(startTimeStamp).toISOString();
        const end_time = new Date(endTimeStamp).toISOString();

        const formData = {
            leave_type: leaveTypes[typeIndex],
            start_time: start_time,
            end_time: end_time,
            reason: reason.trim()
        };

        wx.showLoading({ title: '提交中...' });
        this.setData({ isSaving: true });

        api.applyLeave(formData)
            .then(res => {
                wx.showToast({ title: '提交成功', icon: 'success' });

                // 重置表单并跳到历史记录
                this.setData({
                    typeIndex: -1,
                    reason: '',
                    currentTab: 'history',
                    isSaving: false
                });

                // 强制重新加载历史记录
                setTimeout(() => {
                    this.loadHistory(true);
                }, 1000);
            })
            .catch(err => {
                console.error('请假提交失败', err);
                wx.showToast({ title: err.message || '提交失败', icon: 'none' });
                this.setData({ isSaving: false });
            })
            .finally(() => {
                wx.hideLoading();
            });
    },

    // --- 历史记录处理 ---

    loadHistory(refresh = false) {
        if (this.data.isLoadingMore || (!this.data.hasMore && !refresh)) return;

        if (refresh) {
            this.setData({ page: 0, historyList: [], hasMore: true });
        }

        const { page, pageSize, historyList } = this.data;
        const skip = page * pageSize;

        this.setData({ isLoadingMore: true });
        if (refresh) wx.showLoading({ title: '加载中...' });

        api.getLeaveList(skip, pageSize)
            .then(res => {
                const itemsStr = res.items.map(item => {
                    return {
                        ...item,
                        start_formatted: this.formatDateTime(item.start_time),
                        end_formatted: this.formatDateTime(item.end_time),
                        created_formatted: this.formatDateTime(item.created_at)
                    };
                });

                this.setData({
                    historyList: refresh ? itemsStr : [...historyList, ...itemsStr],
                    totalRecords: res.total,
                    hasMore: skip + itemsStr.length < res.total,
                    page: page + 1
                });
            })
            .catch(err => {
                console.error('加载历史记录失败', err);
                wx.showToast({ title: '加载历列表失败', icon: 'none' });
            })
            .finally(() => {
                this.setData({ isLoadingMore: false });
                if (refresh) wx.hideLoading();
            });
    },

    onReachBottom() {
        if (this.data.currentTab === 'history') {
            this.loadHistory();
        }
    },

    // --- 工具函数 ---

    formatDate(dateObj) {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, '0');
        const d = String(dateObj.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

    formatDateTime(isoString) {
        if (!isoString) return '';
        const d = new Date(isoString);
        const y = d.getFullYear();
        const mo = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const h = String(d.getHours()).padStart(2, '0');
        const mi = String(d.getMinutes()).padStart(2, '0');
        return `${y}-${mo}-${day} ${h}:${mi}`;
    }
});
