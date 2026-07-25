const { generateId } = require('./util');
const seedData = require('./seed-data');

const STORAGE_KEYS = {
  reps: 'db_reps',
  hospitals: 'db_hospitals',
  projects: 'db_projects',
  initialized: 'db_initialized'
};

function readCollection(key) {
  return wx.getStorageSync(key) || [];
}

function writeCollection(key, records) {
  wx.setStorageSync(key, records);
}

function ensureInitialized() {
  if (wx.getStorageSync(STORAGE_KEYS.initialized)) {
    return;
  }
  writeCollection(STORAGE_KEYS.reps, seedData.reps);
  writeCollection(STORAGE_KEYS.hospitals, seedData.hospitals);
  writeCollection(STORAGE_KEYS.projects, seedData.projects);
  wx.setStorageSync(STORAGE_KEYS.initialized, true);
}

function sortByName(records) {
  return [...records].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'zh-CN'));
}

function nowIso() {
  return new Date().toISOString();
}

function listReps() {
  ensureInitialized();
  return Promise.resolve({ data: sortByName(readCollection(STORAGE_KEYS.reps)) });
}

function listHospitalsByRep(repId) {
  ensureInitialized();
  const data = sortByName(
    readCollection(STORAGE_KEYS.hospitals).filter((item) => item.repId === repId)
  );
  return Promise.resolve({ data });
}

function getHospital(hospitalId) {
  ensureInitialized();
  const item = readCollection(STORAGE_KEYS.hospitals).find((h) => h._id === hospitalId);
  if (!item) return Promise.reject(new Error('医院不存在'));
  return Promise.resolve({ data: item });
}

function createHospital(data) {
  ensureInitialized();
  const record = {
    _id: generateId('hosp'),
    ...data,
    createdAt: nowIso()
  };
  const hospitals = readCollection(STORAGE_KEYS.hospitals);
  hospitals.push(record);
  writeCollection(STORAGE_KEYS.hospitals, hospitals);
  return Promise.resolve({ _id: record._id });
}

function listProjectsByHospital(hospitalId) {
  ensureInitialized();
  const data = sortByName(
    readCollection(STORAGE_KEYS.projects).filter((item) => item.hospitalId === hospitalId)
  );
  return Promise.resolve({ data });
}

function countProjectsByHospital(hospitalId) {
  ensureInitialized();
  const total = readCollection(STORAGE_KEYS.projects).filter(
    (item) => item.hospitalId === hospitalId
  ).length;
  return Promise.resolve({ total });
}

function countProjectsForHospitals(hospitalIds) {
  ensureInitialized();
  const counts = {};
  hospitalIds.forEach((id) => {
    counts[id] = 0;
  });
  readCollection(STORAGE_KEYS.projects).forEach((project) => {
    if (counts[project.hospitalId] !== undefined) {
      counts[project.hospitalId] += 1;
    }
  });
  return Promise.resolve(counts);
}

function getProject(projectId) {
  ensureInitialized();
  const item = readCollection(STORAGE_KEYS.projects).find((p) => p._id === projectId);
  if (!item) return Promise.reject(new Error('项目不存在'));
  return Promise.resolve({ data: item });
}

function createProject(data) {
  ensureInitialized();
  const record = {
    _id: generateId('proj'),
    ...data,
    status: data.status || '',
    currentMonthlyVolume: data.currentMonthlyVolume ?? 0,
    targetMonthlyVolume: data.targetMonthlyVolume ?? 0,
    bronchoscopyCases: data.bronchoscopyCases ?? 0,
    bronchoalveolarLavage: data.bronchoalveolarLavage ?? 0,
    updatedAt: nowIso(),
    updatedBy: data.updatedBy || '',
    createdAt: nowIso()
  };
  const projects = readCollection(STORAGE_KEYS.projects);
  projects.push(record);
  writeCollection(STORAGE_KEYS.projects, projects);
  return Promise.resolve({ _id: record._id });
}

function updateProject(projectId, data, updatedBy) {
  ensureInitialized();
  const projects = readCollection(STORAGE_KEYS.projects);
  const index = projects.findIndex((item) => item._id === projectId);
  if (index < 0) return Promise.reject(new Error('项目不存在'));

  const { _id, _openid, ...rest } = data;
  projects[index] = {
    ...projects[index],
    ...rest,
    updatedAt: nowIso(),
    updatedBy
  };
  writeCollection(STORAGE_KEYS.projects, projects);
  return Promise.resolve({ stats: { updated: 1 } });
}

function getRep(repId) {
  ensureInitialized();
  const item = readCollection(STORAGE_KEYS.reps).find((rep) => rep._id === repId);
  if (!item) return Promise.reject(new Error('代表不存在'));
  return Promise.resolve({ data: item });
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
