App({
  globalData: {
    // true = 本地存储模式（无需云开发）；false = 云开发模式
    useLocalStorage: true,

    // 云开发模式时填写环境 ID
    cloudEnvId: 'your-cloud-env-id',
    currentRep: null,
    currentHospital: null,
    currentProject: null
  },

  onLaunch() {
    if (this.globalData.useLocalStorage) {
      console.log('[数据模式] 本地存储，无需开通云开发');
      return;
    }

    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上基础库以使用云能力');
      return;
    }

    wx.cloud.init({
      env: this.globalData.cloudEnvId,
      traceUser: true
    });
    console.log('[数据模式] 云开发');
  }
});
