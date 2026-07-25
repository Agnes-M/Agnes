const dbApi = require('../../utils/db');

Page({
  data: {
    reps: [],
    filteredReps: [],
    keyword: '',
    loading: true
  },

  onLoad() {
    this.loadReps();
  },

  async loadReps() {
    this.setData({ loading: true });
    try {
      const res = await dbApi.listReps();
      this.setData({
        reps: res.data,
        filteredReps: res.data,
        loading: false
      });
    } catch (err) {
      console.error('加载代表列表失败', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onSearchInput(e) {
    const keyword = e.detail.value.trim().toLowerCase();
    const filteredReps = this.data.reps.filter((rep) =>
      rep.name.toLowerCase().includes(keyword)
    );
    this.setData({ keyword: e.detail.value, filteredReps });
  },

  onSelectRep(e) {
    const rep = e.currentTarget.dataset.rep;
    const app = getApp();
    app.globalData.currentRep = rep;
    app.globalData.currentHospital = null;
    app.globalData.currentProject = null;

    wx.navigateTo({
      url: `/pages/hospital-list/hospital-list?repId=${rep._id}&repName=${encodeURIComponent(rep.name)}`
    });
  }
});
