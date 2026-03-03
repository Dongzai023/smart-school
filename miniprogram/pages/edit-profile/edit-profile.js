const api = require('../../utils/api');

Page({
    data: {
        userInfo: null,
        genderOptions: ['男', '女'],
        genderIndex: -1,
        isSaving: false
    },

    onLoad(options) {
        // 获取当前用户信息
        const app = getApp();
        if (app.globalData.userInfo) {
            this.initData(app.globalData.userInfo);
        } else {
            wx.showLoading({ title: '加载中...' });
            api.getMe()
                .then(userInfo => {
                    app.globalData.userInfo = userInfo;
                    this.initData(userInfo);
                })
                .catch(err => {
                    console.error('获取用户信息失败', err);
                    wx.showToast({ title: '加载失败', icon: 'none' });
                })
                .finally(() => {
                    wx.hideLoading();
                });
        }
    },

    initData(userInfo) {
        let genderIndex = -1;
        if (userInfo.gender === '男') genderIndex = 0;
        else if (userInfo.gender === '女') genderIndex = 1;

        this.setData({
            userInfo,
            genderIndex
        });
    },

    onGenderChange(e) {
        this.setData({
            genderIndex: e.detail.value
        });
    },

    submitForm(e) {
        const formData = e.detail.value;

        // 处理性别
        if (this.data.genderIndex >= 0) {
            formData.gender = this.data.genderOptions[this.data.genderIndex];
        }

        this.setData({ isSaving: true });
        wx.showLoading({ title: '保存中...' });

        api.updateMe(formData)
            .then(updatedInfo => {
                // 更新全局对象
                const app = getApp();
                app.globalData.userInfo = updatedInfo;
                wx.setStorageSync('userInfo', updatedInfo);

                wx.showToast({ title: '保存成功', icon: 'success' });
                setTimeout(() => {
                    wx.navigateBack();
                }, 1500);
            })
            .catch(err => {
                console.error('保存失败', err);
                wx.showToast({ title: err.message || '保存失败，请重试', icon: 'none' });
            })
            .finally(() => {
                this.setData({ isSaving: false });
                wx.hideLoading();
            });
    },

    goBack() {
        wx.navigateBack();
    }
});
