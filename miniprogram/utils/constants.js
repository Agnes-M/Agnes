/** 项目状态选项 */
const STATUS_OPTIONS = [
  '加项入院',
  '已入院-上量',
  '未入院-上量',
  '非重点跟进'
];

/** 预设项目类型（新增项目时的下拉候选） */
const PRESET_PROJECT_TYPES = [
  'tNGS',
  'mNGS',
  '肿瘤伴随诊断',
  '全外显子',
  '质谱维生素',
  '质谱血药浓度',
  '宫颈癌甲基化',
  '泌尿生殖道核酸17联检',
  '药物基因',
  '阿尔茨海默病(AD)',
  '呼吸道PCR联检'
];

/** 医院等级选项 */
const HOSPITAL_LEVELS = [
  '公立三级',
  '公立二级',
  '民营一级',
  '其它'
];

/** 业务体系选项 */
const BUSINESS_SYSTEMS = [
  '常规业务',
  '共建客户(专线)',
  '其它'
];

/** 状态对应的样式类名 */
const STATUS_CLASS_MAP = {
  '加项入院': 'status-adding',
  '已入院-上量': 'status-onboard',
  '未入院-上量': 'status-offboard',
  '非重点跟进': 'status-low-priority'
};

module.exports = {
  STATUS_OPTIONS,
  PRESET_PROJECT_TYPES,
  HOSPITAL_LEVELS,
  BUSINESS_SYSTEMS,
  STATUS_CLASS_MAP
};
