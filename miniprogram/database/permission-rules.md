# 云开发数据库权限规则

在云开发控制台 → 数据库 → 对应集合 → 权限设置中，配置如下规则。

## 一期（当前）：所有用户可读写

适合内部小团队快速上线，通过「选择代表」隔离数据视图（前端按 repId 过滤）。

```
{
  "read": true,
  "write": true
}
```

## 二期（接入微信登录后）：按 openid 绑定代表

在 `reps` 集合增加 `openid` 字段，销售首次使用时绑定手机号/代表身份。

```
// reps 集合
{
  "read": "doc.openid == auth.openid || doc._openid == auth.openid",
  "write": "doc.openid == auth.openid"
}

// hospitals 集合 — 只能读写自己 repId 下的医院
{
  "read": "get(`database.reps.${doc.repId}`).openid == auth.openid",
  "write": "get(`database.reps.${doc.repId}`).openid == auth.openid"
}

// projects 集合 — 通过 hospitalId 关联到 rep
{
  "read": "get(`database.hospitals.${doc.hospitalId}`).repId in [auth.openid绑定的repId]",
  "write": "同上"
}
```

> 二期权限规则较复杂，建议在云函数中做鉴权，前端不直接写库。

## 必要的数据库索引

在云开发控制台 → 数据库 → 索引管理 中创建：

| 集合 | 索引字段 | 说明 |
|------|----------|------|
| reps | name (升序) | 代表列表排序 |
| hospitals | repId (升序) + name (升序) | 按代表查医院并排序 |
| projects | hospitalId (升序) + name (升序) | 按医院查项目并排序 |
