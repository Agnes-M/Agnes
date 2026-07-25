const dbApi = require('../../utils/db');
const { PRESET_PROJECT_TYPES, STATUS_CLASS_MAP } = require('../../utils/constants');

Page({
  data: {
    repId: '',
    repName: '',
    hospitalId: '',
    hospitalName: '',
    projects: [],
    loading: true,
    showAddModal: false,
    presetTypes: PRESET_PROJECT_TYPES,
    selectedTypeIndex: 0,
    customProjectName: '',
    useCustomName: false
  },

  onLoad(options) {
    this.setData({
      repId: options.repId,
      repName: decodeURIComponent(options.repName || ''),
      hospitalId: options.hospitalId,
      hospitalName: decodeURIComponent(options.hospitalName || '')
    });
    wx.setNavigationBarTitle({ title: this.data.hospitalName });
    this.loadProjects();
  },

  onShow() {
    if (this.data.hospitalId) {
      this.loadProjects();
    }
  },

  async loadProjects() {
    this.setData({ loading: true });
    try {
      const res = await dbApi.listProjectsByHospital(this.data.hospitalId);
      const projects = res.data.map((p) => ({
        ...p,
        statusClass: STATUS_CLASS_MAP[p.status] || 'status-low-priority'
      }));
      this.setData({ projects, loading: false });
    } catch (err) {
      console.error('加载项目列表失败', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onSelectProject(e) {
    const project = e.currentTarget.dataset.project;
    const app = getApp();
    app.globalData.currentProject = project;

    wx.navigateTo({
      url: `/pages/project-detail/project-detail?projectId=${project._id}&repName=${encodeURIComponent(this.data.repName)}&hospitalName=${encodeURIComponent(this.data.hospitalName)}&repId=${this.data.repId}`
    });
  },

  onShowAddModal() {
    this.setData({
      showAddModal: true,
      selectedTypeIndex: 0,
      customProjectName: '',
      useCustomName: false
    });
  },

  onHideAddModal() {
    this.setData({ showAddModal: false });
  },

  onToggleCustomName() {
    this.setData({ useCustomName: !this.data.useCustomName });
  },

  onTypeChange(e) {
    this.setData({ selectedTypeIndex: Number(e.detail.value) });
  },

  onCustomNameInput(e) {
    this.setData({ customProjectName: e.detail.value });
  },

  async onConfirmAdd() {
    const projectName = this.data.useCustomName
      ? this.data.customProjectName.trim()
      : this.data.presetTypes[this.data.selectedTypeIndex];

    if (!projectName) {
      wx.showToast({ title: '请输入或选择项目名称', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '创建中' });
    try {
      const res = await dbApi.createProject({
        hospitalId: this.data.hospitalId,
        name: projectName,
        biddingInfo: '',
        discount: '',
        addDifficulty: '',
        status: '',
        currentMonthlyVolume: 0,
        targetMonthlyVolume: 0,
        keyDepartments: ['', ''],
        actionPlan: '',
        weeklyProgress: '',
        nextWeekPlan: '',
        blocker: '',
        bronchoscopyCases: 0,
        bronchoalveolarLavage: 0,
        remark: '',
        marketRemark: '',
        updatedBy: this.data.repName
      });

      wx.hideLoading();
      this.setData({ showAddModal: false });
      wx.showToast({ title: '创建成功', icon: 'success' });

      wx.navigateTo({
        url: `/pages/project-detail/project-detail?projectId=${res._id}&repName=${encodeURIComponent(this.data.repName)}&hospitalName=${encodeURIComponent(this.data.hospitalName)}&repId=${this.data.repId}`
      });
    } catch (err) {
      wx.hideLoading();
      console.error('新增项目失败', err);
      wx.showToast({ title: '创建失败', icon: 'none' });
    }
  }
});
