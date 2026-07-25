const dbApi = require('../../utils/db');
const { HOSPITAL_LEVELS, BUSINESS_SYSTEMS } = require('../../utils/constants');

Page({
  data: {
    repId: '',
    repName: '',
    hospitals: [],
    filteredHospitals: [],
    keyword: '',
    loading: true,
    showAddModal: false,
    newHospital: {
      name: '',
      levelIndex: 0,
      businessSystemIndex: 0
    },
    hospitalLevels: HOSPITAL_LEVELS,
    businessSystems: BUSINESS_SYSTEMS
  },

  onLoad(options) {
    const repId = options.repId;
    const repName = decodeURIComponent(options.repName || '');
    this.setData({ repId, repName });
    wx.setNavigationBarTitle({ title: repName });
    this.loadHospitals();
  },

  async loadHospitals() {
    this.setData({ loading: true });
    try {
      const res = await dbApi.listHospitalsByRep(this.data.repId);
      const hospitals = res.data;
      const hospitalIds = hospitals.map((h) => h._id);
      const counts = await dbApi.countProjectsForHospitals(hospitalIds);

      const hospitalsWithCount = hospitals.map((h) => ({
        ...h,
        projectCount: counts[h._id] || 0
      }));

      this.setData({
        hospitals: hospitalsWithCount,
        filteredHospitals: hospitalsWithCount,
        loading: false
      });
    } catch (err) {
      console.error('加载医院列表失败', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onSearchInput(e) {
    const keyword = e.detail.value.trim().toLowerCase();
    const filteredHospitals = this.data.hospitals.filter((h) =>
      h.name.toLowerCase().includes(keyword)
    );
    this.setData({ keyword: e.detail.value, filteredHospitals });
  },

  onSelectHospital(e) {
    const hospital = e.currentTarget.dataset.hospital;
    const app = getApp();
    app.globalData.currentHospital = hospital;

    wx.navigateTo({
      url: `/pages/project-list/project-list?hospitalId=${hospital._id}&hospitalName=${encodeURIComponent(hospital.name)}&repId=${this.data.repId}&repName=${encodeURIComponent(this.data.repName)}`
    });
  },

  onShowAddModal() {
    this.setData({
      showAddModal: true,
      newHospital: { name: '', levelIndex: 0, businessSystemIndex: 0 }
    });
  },

  onHideAddModal() {
    this.setData({ showAddModal: false });
  },

  onNewHospitalInput(e) {
    this.setData({ 'newHospital.name': e.detail.value });
  },

  onLevelChange(e) {
    this.setData({ 'newHospital.levelIndex': Number(e.detail.value) });
  },

  onBusinessSystemChange(e) {
    this.setData({ 'newHospital.businessSystemIndex': Number(e.detail.value) });
  },

  async onConfirmAdd() {
    const { name, levelIndex, businessSystemIndex } = this.data.newHospital;
    if (!name.trim()) {
      wx.showToast({ title: '请输入医院名称', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '保存中' });
    try {
      await dbApi.createHospital({
        repId: this.data.repId,
        name: name.trim(),
        level: HOSPITAL_LEVELS[levelIndex],
        businessSystem: BUSINESS_SYSTEMS[businessSystemIndex]
      });
      wx.hideLoading();
      this.setData({ showAddModal: false });
      wx.showToast({ title: '添加成功', icon: 'success' });
      this.loadHospitals();
    } catch (err) {
      wx.hideLoading();
      console.error('新增医院失败', err);
      wx.showToast({ title: '添加失败', icon: 'none' });
    }
  }
});
