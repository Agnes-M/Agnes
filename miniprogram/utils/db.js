const db = wx.cloud.database();
const _ = db.command;

function getCollection(name) {
  return db.collection(name);
}

/** 获取所有销售代表 */
function listReps() {
  return getCollection('reps').orderBy('name', 'asc').get();
}

/** 按 repId 获取医院列表 */
function listHospitalsByRep(repId) {
  return getCollection('hospitals')
    .where({ repId })
    .orderBy('name', 'asc')
    .get();
}

/** 获取医院详情 */
function getHospital(hospitalId) {
  return getCollection('hospitals').doc(hospitalId).get();
}

/** 新增医院 */
function createHospital(data) {
  return getCollection('hospitals').add({
    data: {
      ...data,
      createdAt: db.serverDate()
    }
  });
}

/** 按 hospitalId 获取项目列表 */
function listProjectsByHospital(hospitalId) {
  return getCollection('projects')
    .where({ hospitalId })
    .orderBy('name', 'asc')
    .get();
}

/** 统计医院下项目数量 */
async function countProjectsByHospital(hospitalId) {
  const res = await getCollection('projects')
    .where({ hospitalId })
    .count();
  return res.total;
}

/** 批量统计多个医院的项目数量 */
async function countProjectsForHospitals(hospitalIds) {
  const counts = {};
  hospitalIds.forEach((id) => {
    counts[id] = 0;
  });

  if (hospitalIds.length === 0) return counts;

  const res = await getCollection('projects')
    .where({
      hospitalId: _.in(hospitalIds)
    })
    .field({ hospitalId: true })
    .get();

  res.data.forEach((p) => {
    if (counts[p.hospitalId] !== undefined) {
      counts[p.hospitalId] += 1;
    }
  });

  return counts;
}

/** 获取项目详情 */
function getProject(projectId) {
  return getCollection('projects').doc(projectId).get();
}

/** 新增项目 */
function createProject(data) {
  const now = db.serverDate();
  return getCollection('projects').add({
    data: {
      ...data,
      status: data.status || '',
      currentMonthlyVolume: data.currentMonthlyVolume ?? 0,
      targetMonthlyVolume: data.targetMonthlyVolume ?? 0,
      bronchoscopyCases: data.bronchoscopyCases ?? 0,
      bronchoalveolarLavage: data.bronchoalveolarLavage ?? 0,
      updatedAt: now,
      updatedBy: data.updatedBy || '',
      createdAt: now
    }
  });
}

/** 更新项目 */
function updateProject(projectId, data, updatedBy) {
  const { _id, _openid, ...rest } = data;
  return getCollection('projects').doc(projectId).update({
    data: {
      ...rest,
      updatedAt: db.serverDate(),
      updatedBy
    }
  });
}

/** 获取代表信息 */
function getRep(repId) {
  return getCollection('reps').doc(repId).get();
}

module.exports = {
  listReps,
  listHospitalsByRep,
  getHospital,
  createHospital,
  listProjectsByHospital,
  countProjectsByHospital,
  countProjectsForHospitals,
  getProject,
  createProject,
  updateProject,
  getRep
};
