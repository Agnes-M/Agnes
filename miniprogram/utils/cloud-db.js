const db = wx.cloud.database();
const _ = db.command;

function getCollection(name) {
  return db.collection(name);
}

function listReps() {
  return getCollection('reps').orderBy('name', 'asc').get();
}

function listHospitalsByRep(repId) {
  return getCollection('hospitals')
    .where({ repId })
    .orderBy('name', 'asc')
    .get();
}

function getHospital(hospitalId) {
  return getCollection('hospitals').doc(hospitalId).get();
}

function createHospital(data) {
  return getCollection('hospitals').add({
    data: {
      ...data,
      createdAt: db.serverDate()
    }
  });
}

function listProjectsByHospital(hospitalId) {
  return getCollection('projects')
    .where({ hospitalId })
    .orderBy('name', 'asc')
    .get();
}

function countProjectsByHospital(hospitalId) {
  return getCollection('projects')
    .where({ hospitalId })
    .count();
}

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

function getProject(projectId) {
  return getCollection('projects').doc(projectId).get();
}

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
