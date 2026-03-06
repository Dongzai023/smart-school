const api = require('../../../utils/api');

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

Page({
    data: {
        selectedDate: formatDate(new Date()),
        summary: {
            total: 0,
            signed: 0,
            late: 0,
            absent: 0
        },
        teachers: [],
        statusMap: {
            'signed': '已签',
            'late': '迟到',
            'absent': '缺勤'
        }
    },

    onLoad: function () {
        this.fetchData();
    },

    onDateChange: function (e) {
        this.setData({
            selectedDate: e.detail.value
        });
        this.fetchData();
    },

    fetchData: function () {
        wx.showLoading({ title: '加载中' });
        api.getPrincipalCheckin({ date: this.data.selectedDate })
            .then(res => {
                this.setData({
                    summary: res.summary,
                    teachers: res.teachers
                });
            })
            .catch(err => {
                console.error('Fetch error:', err);
                wx.showToast({ title: '加载失败', icon: 'none' });
            })
            .finally(() => {
                wx.hideLoading();
            });
    },

    showDetails: function (e) {
        const item = e.currentTarget.dataset.item;
        if (item.details && item.details.length > 0) {
            let detailStr = item.details.map(d => `${d.label}: ${d.time || '未签'} (${this.data.statusMap[d.status] || d.status})`).join('\n');
            wx.showModal({
                title: `${item.real_name} 签到详情`,
                content: detailStr,
                showCancel: false
            });
        } else {
            wx.showToast({ title: '暂无详情', icon: 'none' });
        }
    }
});
