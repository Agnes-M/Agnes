# 重大项目跟进小程序

医学检验行业销售项目跟进工具，将 Excel 台账改造为微信小程序，支持销售在手机上填报和查看项目进展。

## 功能概览

四层导航结构：

```
选择销售代表 → 医院列表 → 项目列表 → 项目详情表单
```

每层支持返回上一层，顶部显示路径面包屑（如：傅芳 > 宁波明州医院 > tNGS）。

## 技术栈

- 微信小程序原生开发
- 微信云开发（CloudBase）— 云数据库 + 云函数

## 快速开始

### 1. 准备工作

- 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
- 注册微信小程序账号，获取 AppID
- 开通云开发，创建环境

### 2. 导入项目

1. 用微信开发者工具打开 `miniprogram/` 目录
2. 修改 `project.config.json` 中的 `appid` 为你的 AppID
3. 修改 `app.js` 中的 `cloudEnvId` 为你的云开发环境 ID

### 3. 创建数据库集合

在云开发控制台 → 数据库，创建三个集合：

- `reps` — 销售代表
- `hospitals` — 医院
- `projects` — 项目

权限规则参考 `database/permission-rules.md`。

### 4. 创建索引

| 集合 | 索引 |
|------|------|
| reps | `name` 升序 |
| hospitals | `repId` 升序 + `name` 升序 |
| projects | `hospitalId` 升序 + `name` 升序 |

### 5. 导入种子数据

**方式 A：控制台直接导入（推荐）**

云开发控制台 → 数据库 → 选择集合 → 导入 → 上传 `seed-data/` 下对应的 JSON 文件。

**方式 B：云函数批量导入**

```bash
# 部署云函数
cd cloudfunctions/importSeedData && npm install

# 在微信开发者工具中右键 importSeedData → 上传并部署
# 然后在云端测试中传入：
# { "collection": "reps", "records": [...] }
```

**方式 C：从 Excel 转换**

```bash
pip install openpyxl
python3 scripts/excel_to_seed.py 重大项目跟进表.xlsx --output-dir seed-data
```

如果 Excel 表头与脚本默认映射不一致，请修改 `scripts/excel_to_seed.py` 中的 `COLUMN_MAP`。

### 6. 编译运行

在微信开发者工具中点击「编译」，即可在模拟器或真机上预览。

## 目录结构

```
miniprogram/
├── app.js / app.json / app.wxss     # 全局配置
├── project.config.json              # 项目配置
├── pages/
│   ├── rep-list/                    # 第1层：选择销售代表
│   ├── hospital-list/               # 第2层：医院列表
│   ├── project-list/                # 第3层：项目列表
│   └── project-detail/              # 第4层：项目详情表单
├── utils/
│   ├── constants.js                 # 常量（状态选项、预设项目类型等）
│   ├── db.js                        # 云数据库 CRUD 封装
│   └── util.js                      # 工具函数
├── cloudfunctions/
│   └── importSeedData/              # 种子数据批量导入云函数
├── seed-data/                       # 示例种子数据
├── scripts/
│   ├── excel_to_seed.py             # Excel → JSON 转换脚本
│   └── generate_import_calls.py     # 生成云函数导入批次
└── database/
    └── permission-rules.md          # 数据库权限规则说明
```

## 数据模型

### reps（销售代表）

| 字段 | 类型 | 说明 |
|------|------|------|
| _id | string | 主键 |
| name | string | 代表姓名 |
| supervisor | string | 主管姓名 |
| manager | string | 经理姓名 |
| region | string | 区域 |

### hospitals（医院）

| 字段 | 类型 | 说明 |
|------|------|------|
| _id | string | 主键 |
| repId | string | 关联销售代表 |
| name | string | 医院名称 |
| level | string | 医院等级 |
| businessSystem | string | 业务体系 |

### projects（项目）

完整字段见需求文档第三节 3.3。关键逻辑：

- `status` 下拉选项：加项入院 / 已入院-上量 / 未入院-上量 / 非重点跟进
- `bronchoscopyCases` 和 `bronchoalveolarLavage` 仅在项目名称为 **tNGS** 时显示
- 每次保存自动更新 `updatedAt` 和 `updatedBy`

## 验收对照

| # | 验收项 | 实现方式 |
|---|--------|----------|
| 1 | 代表只能看到自己的医院 | 医院列表按 `repId` 过滤查询 |
| 2 | 新增项目可用 | 项目列表页「+ 新增项目」按钮 |
| 3 | 保存后数据不丢失 | 云数据库持久化 + 保存成功 Toast |
| 4 | tNGS 专属字段条件显示 | `wx:if="{{isTNGS}}"` 条件渲染 |
| 5 | 状态下拉选择 | 原生 `picker` 组件 |

## 二期预留

- 微信登录鉴权（`wx.cloud.callFunction` 获取 openid）
- 手机号绑定销售代表身份
- 主管/经理查看下属数据
- 数据导出为 Excel

## 常见问题

**Q: 列表加载报 index 错误？**
A: 请在云开发控制台为对应集合创建复合索引（见上方「创建索引」）。

**Q: 数据为空？**
A: 确认已导入 `seed-data/` 下的 JSON 文件，且 `cloudEnvId` 配置正确。

**Q: 如何替换真实 Excel 数据？**
A: 运行 `python3 scripts/excel_to_seed.py 你的台账.xlsx`，然后在控制台重新导入生成的 JSON。
