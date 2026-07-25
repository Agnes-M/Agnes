const cloud = require('wx-server-sdk');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

/**
 * 批量导入种子数据
 * event: { collection: 'reps'|'hospitals'|'projects', records: [...] }
 */
exports.main = async (event) => {
  const { collection, records } = event;

  if (!collection || !Array.isArray(records) || records.length === 0) {
    return { success: false, message: '参数错误：需要 collection 和 records 数组' };
  }

  const allowed = ['reps', 'hospitals', 'projects'];
  if (!allowed.includes(collection)) {
    return { success: false, message: `collection 必须是 ${allowed.join('/')}` };
  }

  const BATCH_SIZE = 20;
  let inserted = 0;
  const errors = [];

  for (let i = 0; i < records.length; i += BATCH_SIZE) {
    const batch = records.slice(i, i + BATCH_SIZE);
    const tasks = batch.map(async (record) => {
      try {
        const { _id, ...rest } = record;
        if (_id) {
          await db.collection(collection).doc(_id).set({ data: rest });
        } else {
          await db.collection(collection).add({ data: rest });
        }
        inserted += 1;
      } catch (err) {
        errors.push({ record, error: err.message });
      }
    });
    await Promise.all(tasks);
  }

  return {
    success: errors.length === 0,
    inserted,
    total: records.length,
    errors
  };
};
