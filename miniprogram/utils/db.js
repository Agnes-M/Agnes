const localDb = require('./local-db');

let cloudDb = null;

function useLocalStorage() {
  const app = getApp();
  return app && app.globalData && app.globalData.useLocalStorage === true;
}

function getCloudDb() {
  if (!cloudDb) {
    cloudDb = require('./cloud-db');
  }
  return cloudDb;
}

function getAdapter() {
  return useLocalStorage() ? localDb : getCloudDb();
}

function listReps() {
  return getAdapter().listReps();
}

function listHospitalsByRep(repId) {
  return getAdapter().listHospitalsByRep(repId);
}

function getHospital(hospitalId) {
  return getAdapter().getHospital(hospitalId);
}

function createHospital(data) {
  return getAdapter().createHospital(data);
}

function listProjectsByHospital(hospitalId) {
  return getAdapter().listProjectsByHospital(hospitalId);
}

function countProjectsByHospital(hospitalId) {
  return getAdapter().countProjectsByHospital(hospitalId);
}

function countProjectsForHospitals(hospitalIds) {
  return getAdapter().countProjectsForHospitals(hospitalIds);
}

function getProject(projectId) {
  return getAdapter().getProject(projectId);
}

function createProject(data) {
  return getAdapter().createProject(data);
}

function updateProject(projectId, data, updatedBy) {
  return getAdapter().updateProject(projectId, data, updatedBy);
}

function getRep(repId) {
  return getAdapter().getRep(repId);
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
