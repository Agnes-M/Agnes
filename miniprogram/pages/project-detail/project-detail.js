const dbApi = require('../../utils/db');
const { STATUS_OPTIONS } = require('../../utils/constants');
const { formatCloudDate, parseNumber } = require('../../utils/util');

const EMPTY_FORM = {
  name: '',
  biddingInfo: '',
  discount: '',
  addDifficulty: '',
  status: '',
  statusIndex: -1,
  currentMonthlyVolume: '',
  targetMonthlyVolume: '',
  keyDepartment1: '',
  keyDepartment2: '',
  actionPlan: '',
  weeklyProgress: '',
  nextWeekPlan: '',
  blocker: '',
  bronchoscopyCases: '',
  bronchoalveolarLavage: '',
  remark: '',
  marketRemark: ''
};

Page({
  data: {
    projectId: '',
    repId: '',
    repName: '',
    hospitalName: '',
    projectName: '',
    isTNGS: false,
    statusOptions: STATUS_OPTIONS,
    form: { ...EMPTY_FORM },
    updatedAtText: '',
    updatedBy: '',
    loading: true,
    saving: false
  },

  onLoad(options) {
    this.setData({
      projectId: options.projectId,
      repId: options.repId,
      repName: decodeURIComponent(options.repName || ''),
      hospitalName: decodeURIComponent(options.hospitalName || '')
    });
    this.loadProject();
  },

  async loadProject() {
    this.setData({ loading: true });
    try {
      const res = await dbApi.getProject(this.data.projectId);
      const project = res.data;
      const keyDepts = Array.isArray(project.keyDepartments)
        ? project.keyDepartments
        : (project.keyDepartments ? [project.keyDepartments] : ['', '']);
      const statusIndex = STATUS_OPTIONS.indexOf(project.status);

      this.setData({
        projectName: project.name,
        isTNGS: project.name === 'tNGS',
        form: {
          name: project.name || '',
          biddingInfo: project.biddingInfo || '',
          discount: project.discount || '',
          addDifficulty: project.addDifficulty || '',
          status: project.status || '',
          statusIndex: statusIndex >= 0 ? statusIndex : -1,
          currentMonthlyVolume: project.currentMonthlyVolume != null ? String(project.currentMonthlyVolume) : '',
          targetMonthlyVolume: project.targetMonthlyVolume != null ? String(project.targetMonthlyVolume) : '',
          keyDepartment1: keyDepts[0] || '',
          keyDepartment2: keyDepts[1] || '',
          actionPlan: project.actionPlan || '',
          weeklyProgress: project.weeklyProgress || '',
          nextWeekPlan: project.nextWeekPlan || '',
          blocker: project.blocker || '',
          bronchoscopyCases: project.bronchoscopyCases != null ? String(project.bronchoscopyCases) : '',
          bronchoalveolarLavage: project.bronchoalveolarLavage != null ? String(project.bronchoalveolarLavage) : '',
          remark: project.remark || '',
          marketRemark: project.marketRemark || ''
        },
        updatedAtText: formatCloudDate(project.updatedAt),
        updatedBy: project.updatedBy || '',
        loading: false
      });

      wx.setNavigationBarTitle({ title: project.name });
    } catch (err) {
      console.error('加载项目详情失败', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onStatusChange(e) {
    const index = Number(e.detail.value);
    this.setData({
      'form.statusIndex': index,
      'form.status': STATUS_OPTIONS[index]
    });
  },

  async onSave() {
    if (this.data.saving) return;

    const { form, repName, projectId } = this.data;
    const saveData = {
      name: form.name,
      biddingInfo: form.biddingInfo,
      discount: form.discount,
      addDifficulty: form.addDifficulty,
      status: form.status,
      currentMonthlyVolume: parseNumber(form.currentMonthlyVolume, 0),
      targetMonthlyVolume: parseNumber(form.targetMonthlyVolume, 0),
      keyDepartments: [form.keyDepartment1, form.keyDepartment2].filter(Boolean),
      actionPlan: form.actionPlan,
      weeklyProgress: form.weeklyProgress,
      nextWeekPlan: form.nextWeekPlan,
      blocker: form.blocker,
      bronchoscopyCases: parseNumber(form.bronchoscopyCases, 0),
      bronchoalveolarLavage: parseNumber(form.bronchoalveolarLavage, 0),
      remark: form.remark,
      marketRemark: form.marketRemark
    };

    this.setData({ saving: true });
    wx.showLoading({ title: '保存中' });

    try {
      await dbApi.updateProject(projectId, saveData, repName);
      wx.hideLoading();
      wx.showToast({ title: '保存成功', icon: 'success' });
      this.setData({
        saving: false,
        updatedAtText: '刚刚',
        updatedBy: repName
      });
    } catch (err) {
      wx.hideLoading();
      console.error('保存失败', err);
      this.setData({ saving: false });
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  }
});
