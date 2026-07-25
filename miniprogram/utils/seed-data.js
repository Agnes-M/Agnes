/** 本地模式初始种子数据（小程序内请 require 此文件，不要直接 require .json） */
module.exports = {
  reps: [
    {
      _id: 'rep_demo_fufang',
      name: '傅芳',
      supervisor: '张主管',
      manager: '李经理',
      region: '01杭州'
    },
    {
      _id: 'rep_demo_wangming',
      name: '王明',
      supervisor: '张主管',
      manager: '李经理',
      region: '02宁波'
    },
    {
      _id: 'rep_demo_chenli',
      name: '陈丽',
      supervisor: '赵主管',
      manager: '周经理',
      region: '03温州'
    }
  ],
  hospitals: [
    {
      _id: 'hosp_demo_001',
      repId: 'rep_demo_fufang',
      name: '宁波明州医院',
      level: '民营一级',
      businessSystem: '常规业务'
    },
    {
      _id: 'hosp_demo_002',
      repId: 'rep_demo_fufang',
      name: '杭州市第一人民医院',
      level: '公立三级',
      businessSystem: '共建客户(专线)'
    },
    {
      _id: 'hosp_demo_003',
      repId: 'rep_demo_wangming',
      name: '宁波市第二医院',
      level: '公立三级',
      businessSystem: '常规业务'
    },
    {
      _id: 'hosp_demo_004',
      repId: 'rep_demo_chenli',
      name: '温州医科大学附属第一医院',
      level: '公立三级',
      businessSystem: '常规业务'
    }
  ],
  projects: [
    {
      _id: 'proj_demo_001',
      hospitalId: 'hosp_demo_001',
      name: 'tNGS',
      biddingInfo: '检验科标段A',
      discount: '普检19%；特检38%',
      addDifficulty: '需与检验科主任沟通加项流程，目前卡在物价审批环节。',
      status: '加项入院',
      currentMonthlyVolume: 0,
      targetMonthlyVolume: 50,
      keyDepartments: ['呼吸内科-王主任', '检验科-李主任'],
      actionPlan: '1. 本周完成物价备案材料准备\n2. 下周约检验科主任面谈',
      weeklyProgress: '已提交物价备案申请，等待审批结果。',
      nextWeekPlan: '跟进物价审批进度，准备科室培训PPT。',
      blocker: '物价审批周期较长，预计还需2周。',
      bronchoscopyCases: 12,
      bronchoalveolarLavage: 8,
      remark: '重点跟进项目',
      marketRemark: '市场部可提供学术支持',
      updatedBy: '傅芳'
    },
    {
      _id: 'proj_demo_002',
      hospitalId: 'hosp_demo_001',
      name: 'mNGS',
      biddingInfo: '',
      discount: '35%',
      addDifficulty: '',
      status: '已入院-上量',
      currentMonthlyVolume: 30,
      targetMonthlyVolume: 80,
      keyDepartments: ['ICU-张主任'],
      actionPlan: '加强ICU科室推广，组织病例讨论会。',
      weeklyProgress: '本月已送检28例，较上月增长15%。',
      nextWeekPlan: '安排一次科室学术会议。',
      blocker: '',
      bronchoscopyCases: 0,
      bronchoalveolarLavage: 0,
      remark: '',
      marketRemark: '',
      updatedBy: '傅芳'
    },
    {
      _id: 'proj_demo_003',
      hospitalId: 'hosp_demo_002',
      name: '质谱维生素',
      biddingInfo: '体检中心标段',
      discount: '25%',
      addDifficulty: '体检中心已有竞品入驻，需差异化竞争。',
      status: '未入院-上量',
      currentMonthlyVolume: 0,
      targetMonthlyVolume: 100,
      keyDepartments: ['体检中心-刘主任', '营养科'],
      actionPlan: '提供对比实验数据，争取试用机会。',
      weeklyProgress: '已送样对比，等待结果。',
      nextWeekPlan: '根据对比结果制定推广方案。',
      blocker: '竞品价格优势明显。',
      bronchoscopyCases: 0,
      bronchoalveolarLavage: 0,
      remark: '',
      marketRemark: '可申请特价政策支持',
      updatedBy: '傅芳'
    },
    {
      _id: 'proj_demo_004',
      hospitalId: 'hosp_demo_003',
      name: '肿瘤伴随诊断',
      biddingInfo: '',
      discount: '30%',
      addDifficulty: '',
      status: '非重点跟进',
      currentMonthlyVolume: 5,
      targetMonthlyVolume: 20,
      keyDepartments: ['肿瘤科'],
      actionPlan: '维持现有送检量。',
      weeklyProgress: '本周送检3例。',
      nextWeekPlan: '常规维护。',
      blocker: '',
      bronchoscopyCases: 0,
      bronchoalveolarLavage: 0,
      remark: '',
      marketRemark: '',
      updatedBy: '王明'
    }
  ]
};
