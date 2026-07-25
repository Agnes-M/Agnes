/** 生成简单唯一 ID */
function generateId(prefix) {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${ts}_${rand}`;
}

/** 格式化日期时间 */
function formatDateTime(date) {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return String(date);

  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 云数据库 serverDate 在客户端展示时的兼容处理 */
function formatCloudDate(value) {
  if (!value) return '';
  if (typeof value === 'object' && value.$date) {
    return formatDateTime(value.$date);
  }
  return formatDateTime(value);
}

/** 安全解析数字 */
function parseNumber(value, defaultValue = 0) {
  if (value === '' || value === null || value === undefined) return defaultValue;
  const num = Number(value);
  return Number.isNaN(num) ? defaultValue : num;
}

module.exports = {
  generateId,
  formatDateTime,
  formatCloudDate,
  parseNumber
};
