# 智能宠物健康监测项圈 ERP 库存管理系统

大学《ERP 与供应链管理系统》课程项目 —— 前后端分离的完整 Web 应用。

> **在线演示地址**：<https://zhouyuesong.pythonanywhere.com>
> 免费实例，浏览器直接打开即可使用，无需安装任何环境。

- **前端**：HTML5 / CSS3 / 原生 JavaScript（无框架）+ ECharts 5 + Font Awesome 6，多页面应用，全部数据通过 REST API 获取，**前端不直接访问数据库**。
- **后端**：Python 3 + Flask + Flask-SQLAlchemy + Flask-CORS，严格分层 `Route → Service → Model → Database`，统一 RESTful API。
- **数据库**：开发环境 SQLite（零配置），仅需修改 `DATABASE_URL` 即可切换 MySQL。

## 快速开始（三步）

```bash
# 1. 安装依赖（建议先创建虚拟环境，详见下文第三节）
pip install -r backend/requirements.txt

# 2. 生成演示数据（压缩包已内置 database/erp.db，可跳过此步；
#    演示数据玩乱后重新执行此命令即可一键恢复）
python backend/seed.py

# 3. 启动服务（两个终端分别执行）
python backend/app.py                              # 后端 API，地址 http://127.0.0.1:5000/api/v1
python -m http.server 8000 --directory frontend     # 前端页面，浏览器打开 http://localhost:8000
```

> 小技巧：Flask 已内置前端页面托管，**只跑后端也能用**——执行 `python backend/app.py`
> 后直接打开 http://127.0.0.1:5000 即可（前后端同源，无需第二个终端）。
> 线上部署就是用的这个模式，详见第九节。

## 一、功能总览

| 模块 | 功能 |
|---|---|
| 首页数据总览 | 物料数 / 今日入库 / 今日出库 / 待盘点 4 个 KPI + 近 7 天出入库趋势图 + 库存预警列表 |
| 物料档案 | 32 种物料增删改查、分类/ABC/状态筛选、ABC 统计卡片、删除引用保护 |
| 库存总览 | 分仓库库存、移动平均价、库存金额、库存不足自动判定（只读，不可直接改库存） |
| 采购入库 | 新建 → 保存草稿 → 提交审核 → **确认入库**（唯一入库存入口，事务+流水） |
| 生产领料 | 选择产品与生产数量 → 按 BOM 自动生成物料需求 → 库存不足拦截 → 确认出库 |
| 库存盘点 | 创建快照 → 实盘录入自动算差异 → 提交审核 → **确认调整**（ADJUST 流水） |
| 库存流水 | 全量出入库流水查询，`变动前 + 变动量 = 变动后` 恒成立 |
| BOM 产品结构 | 产品 → 半成品 → 物料 多级树形展示 + 单件物料汇总 |
| 库存预警 | 按 `安全库存 × 1.2` 监控阈值聚合预警（不足/关注） |

## 二、目录结构

```
pet-collar-erp/
├── frontend/                    # 前端（静态站点，无需构建）
│   ├── index.html               # 登录入口页（演示性质）
│   ├── pages/                   # 9 个业务页面
│   │   ├── dashboard.html       #   首页数据总览
│   │   ├── inbound.html         #   采购入库
│   │   ├── outbound.html        #   生产领料出库
│   │   ├── inventory.html       #   库存总览
│   │   ├── stocktake.html       #   库存盘点
│   │   ├── ledger.html          #   库存流水
│   │   ├── materials.html       #   物料档案
│   │   ├── bom.html             #   BOM 产品结构
│   │   └── warning.html         #   库存预警
│   ├── css/                     # global / layout / components / pages 四层样式
│   └── js/
│       ├── config.js            #   全局配置（API 地址等，部署时只需改这里）
│       ├── api.js               #   统一 fetch 封装（全站唯一请求入口）
│       ├── common.js            #   侧边栏/顶栏/Toast/分页/徽章/公共函数
│       └── *.js                 #   每个页面对应一个逻辑文件
├── backend/                     # 后端（Flask）
│   ├── app.py                   # 应用工厂 + 全局错误处理 + 启动入口
│   ├── config.py                # 配置（DATABASE_URL 在此读取）
│   ├── extensions.py            # db / cors 扩展实例
│   ├── seed.py                  # 演示数据种子脚本（一键重建数据库）
│   ├── models/                  # 7 个数据模型（material/inventory/ledger/inbound/outbound/stocktake/bom）
│   ├── routes/                  # 8 个路由蓝图（每个模块一个文件，注册在 routes/__init__.py）
│   ├── services/                # 业务逻辑层（路由只做参数校验，禁止在 routes 写业务）
│   ├── utils/                   # 统一响应 / 校验器 / 单据编号生成器
│   └── requirements.txt
├── database/
│   └── erp.db                   # SQLite 数据库文件（seed.py 自动生成）
├── .env.example                 # 环境变量示例（切换 MySQL 用）
└── README.md
```

## 三、环境要求与安装

1. **安装 Python 3.8+**（建议 3.10）：https://www.python.org/downloads/
2. **安装依赖**（在项目根目录执行，建议使用虚拟环境）：

```bash
cd pet-collar-erp
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
# 网络慢时可用国内镜像：
# pip install -r backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

3. **生成演示数据**（重建数据库，可重复执行）：

```bash
python backend/seed.py
```

演示数据与首页数字完全对应：物料 32 种、今日入库 8 单、今日出库 6 单、待盘点 3 单；
库存预警：M101 28/30 库存不足、M201 42/40 正常、M301 15/25 库存不足。

4. **启动后端**（新开一个终端，先激活虚拟环境）：

```bash
python backend/app.py
```

后端启动后 API 地址为：**http://127.0.0.1:5000/api/v1**

5. **启动前端**（再新开一个终端，任意位置执行均可）：

```bash
python -m http.server 8000 --directory frontend
```

6. **访问系统**：浏览器打开 **http://localhost:8000**（登录页为演示性质，点击「进入系统」即可）

> 注意：前端页面通过 `frontend/js/config.js` 中的 `API_BASE_URL` 访问后端，
> 浏览器跨域已由 Flask-CORS 放行，前后端必须**同时启动**。

## 四、数据库切换（SQLite → MySQL）

开发环境默认使用 SQLite（`database/erp.db`，随项目走，零配置）。
切换 MySQL 只需两步，**代码零改动**：

1. 安装驱动（按 backend/requirements.txt 已含，可直接用）：

```bash
pip install pymysql cryptography
```

2. 复制 `.env.example` 为 `.env`（或直接设置环境变量），修改 `DATABASE_URL`：

```bash
# .env 示例（MySQL）
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/pet_collar_erp?charset=utf8mb4
```

`config.py` 会优先读取环境变量 `DATABASE_URL`，未设置时回退到 SQLite。
修改后重新执行 `python backend/seed.py` 建表并灌入演示数据即可。

## 五、API 设计规范

### 5.1 统一响应格式

| 场景 | 返回 |
|---|---|
| 成功 | `{"code": 200, "message": "success", "data": {...}}` |
| 业务失败 | `{"code": 400, "message": "错误信息", "data": null}`（库存不足时 data 携带 `{available, required}`） |
| 资源不存在 | `{"code": 404, ...}` |
| 服务器异常 | `{"code": 500, "message": "服务器内部错误，请查看后端日志", "data": null}` |

### 5.2 接口清单（前缀 `/api/v1`）

| 模块 | 方法 | 路径 | 说明 |
|---|---|---|---|
| Dashboard | GET | `/dashboard/summary` | 首页汇总（KPI + 预警列表 + 库存总金额） |
| 物料 | GET | `/materials` | 列表（keyword/category/abc_class/status/page/page_size，返回 abc_summary） |
| 物料 | POST | `/materials` | 新增 |
| 物料 | GET | `/materials/{id}` | 详情 |
| 物料 | PUT | `/materials/{id}` | 修改 |
| 物料 | DELETE | `/materials/{id}` | 删除（被库存/流水/单据/BOM 引用时拒绝） |
| 库存 | GET | `/inventory` | 列表（material_code/material_name/warehouse/location/abc_class/stock_status） |
| 库存 | GET | `/inventory/{material_id}` | 单个物料全仓库库存 |
| 入库 | GET | `/inbound` | 列表（inbound_no/purchase_order_no/supplier/warehouse/inbound_date/status） |
| 入库 | POST | `/inbound` | 创建（DRAFT，含明细 items） |
| 入库 | GET | `/inbound/{id}` | 详情 |
| 入库 | PUT | `/inbound/{id}` | 编辑（仅 DRAFT） |
| 入库 | POST | `/inbound/{id}/submit` | 提交审核（DRAFT → PENDING，不改库存） |
| 入库 | POST | `/inbound/{id}/confirm` | 确认入库（PENDING → COMPLETED，**唯一入库存入口**） |
| 出库 | GET | `/outbound` | 列表（outbound_no/production_order_no/department/warehouse/outbound_date/status） |
| 出库 | POST | `/outbound` | 创建（按 BOM 自动生成需求：需求 = BOM 用量 × 生产数量） |
| 出库 | GET | `/outbound/{id}` | 详情（含每行当前可用库存） |
| 出库 | PUT | `/outbound/{id}` | 编辑（仅 DRAFT，可改本次出库数量/库位） |
| 出库 | POST | `/outbound/{id}/submit` | 提交审核（检查 `可用库存 >= 出库数量`，不足 → 400） |
| 出库 | POST | `/outbound/{id}/confirm` | 确认出库（**唯一出库存入口**） |
| 盘点 | GET | `/stocktakes` | 列表（stocktake_no/warehouse/stocktake_date/status） |
| 盘点 | POST | `/stocktakes` | 创建（自动生成该仓库库存快照，状态 COUNTING） |
| 盘点 | GET | `/stocktakes/{id}` | 详情（含差异/调整状态） |
| 盘点 | PUT | `/stocktakes/{id}` | 录入实盘（自动算差异 actual - system：盘盈/盘亏/正常） |
| 盘点 | POST | `/stocktakes/{id}/submit` | 提交审核（COUNTING → PENDING_REVIEW，未录完拒绝） |
| 盘点 | POST | `/stocktakes/{id}/adjust` | 确认调整（**唯一调整库存入口**，生成 ADJUST 流水） |
| 流水 | GET | `/ledger` | 列表（start_date/end_date/material_code/warehouse/document_type + 汇总） |
| BOM | GET | `/bom` | BOM 产品/组件列表 |
| BOM | GET | `/bom/{product_code}` | 树形 BOM 结构 |

完整交互示例（curl）见 5.3；前端调用点均以 `API-BEGIN: XXX` / `API-END: XXX` 注释块标注。

### 5.3 curl 快速体验

```bash
# 首页汇总
curl http://127.0.0.1:5000/api/v1/dashboard/summary

# 树形 BOM
curl http://127.0.0.1:5000/api/v1/bom/P001

# 库存不足拦截演示（OUT-10 草稿单提交，生产 50 套）
curl -X POST http://127.0.0.1:5000/api/v1/outbound/10/submit
# → {"code":400,"message":"M101 心率PPG传感器库存不足","data":{"available":28.0,"required":50.0}}
```

## 六、核心业务规则（考试/答辩重点）

1. **库存不可直接修改**：前端没有任何直接改库存的入口，只有三个业务入口：
   入库确认（IN 流水）、出库确认（OUT 流水）、盘点确认调整（ADJUST 流水）。
2. **所有库存变动必须留痕**：`InventoryLedger` 记录 `变动前 / 变动量 / 变动后`，
   恒等式 `before + quantity = after`；核心实现见 `backend/services/inventory_service.py: change_stock()`。
3. **事务保证**：确认入库/确认出库/确认调整均为 `try: ... commit / except: rollback`，
   库存与流水要么同时生效，要么同时回滚。
4. **入库四态流转**：`草稿 DRAFT → 待审核 PENDING → 已完成 COMPLETED / 已驳回 REJECTED`，
   创建/保存/提交都不改库存，**只有确认入库才改**。
5. **出库 BOM 需求**：需求数量 = BOM 单位用量 × 生产数量（多级 BOM 路径乘数累加），
   提交时检查 `available_quantity >= outbound_quantity`，不足返回 400 与可用/需求数。
6. **盘点四步**：创建（快照 system_quantity）→ 实盘录入（差异 = 实盘 − 账面）
   → 提交审核 → 确认调整（按差异生成 ADJUST 流水），**绝不直接覆盖库存**。
7. **重复操作保护**：已完成单据重复确认/调整返回 400（如「该入库单已经完成，不能重复入库」）。
8. **移动加权平均**：入库按移动加权平均更新单价，出库/盘亏按当前平均价出账。

## 七、API 二次开发指南

### 7.1 分层规范（多人协作必须遵守）

```
routes/（路由：只做参数校验与调用 service，禁止写业务）
   ↓
services/（业务逻辑：校验、事务、单据状态机、库存变动）
   ↓
models/（数据模型：字段与 to_dict 序列化，禁止写业务）
   ↓
Database
```

- **前端**：所有请求必须走 `frontend/js/api.js` 的 `API.get/post/put/delete`，**禁止裸 fetch**；
  跨页面复用代码放 `common.js`；页面骨架与脚本引入顺序：`config.js → api.js → common.js → 页面js`。
- **接口标注**：前端用 `// API-BEGIN: 接口名` / `// API-END` 包裹（含方法、URL、后端文件、二次开发说明），
  后端用 `# API-BEGIN:` / `# API-END:`。扩展点用 `// TODO-EXTENSION:` / `# TODO-EXTENSION:` 标注。
- **新增页面**：`pages/` 加 HTML → `js/` 加逻辑 → 在 `common.js` 的 `MENU_CONFIG` 登记菜单，即可自动出现在侧边栏。

### 7.2 新增一个接口（以「新增供应商档案」为例）

1. `backend/models/` 新建 `supplier.py` 模型（在 `models/__init__.py` 中 import，保证建表）；
2. `backend/services/supplier_service.py` 编写业务逻辑（校验 + 查询/写入）；
3. `backend/routes/supplier.py` 新建 Blueprint，只做参数接收与响应包装：
   ```python
   bp = Blueprint("supplier", __name__, url_prefix="/api/v1/suppliers")
   bp.route("", methods=["GET"])   # 集合端点用空路径
   ```
4. 在 `backend/routes/__init__.py` 的 `register_blueprints()` 中注册即可；
5. 前端在对应页面 JS 中调用 `API.get("/suppliers", params)`，并加 `API-BEGIN` 注释块。

### 7.3 新增一个完整模块（以「采购订单」为例）

1. 建模型 `PurchaseOrder` / `PurchaseItem` + 建服务 `purchase_service.py`（含状态机与单据编号）；
2. 建路由 `routes/purchase.py` 并注册；用 `generate_doc_no("CG", ...)` 生成单号；
3. 前端建 `pages/purchase.html` + `js/purchase.js`，在 `MENU_CONFIG` 的「采购管理」组登记；
4. 如需改库存，只能调用 `inventory_service.change_stock()` 保证流水留痕。

## 八、协作与部署说明

- **多人协作**：按模块认领 `routes/xxx.py + services/xxx_service.py + pages/xxx.html + js/xxx.js`，
  合并冲突天然最小化；接口字段以 `models/*.py` 的 `to_dict()` 为准。
- **换 API 地址**：`frontend/js/config.js` 的 `API_BASE_URL` 已**自动识别环境**
  （本机访问走 `127.0.0.1:5000`，线上访问自动同源），通常无需修改；
  如需固定地址，直接改该行即可。
- **换数据库**：只改环境变量 `DATABASE_URL`（见第四节）。
- **前后端解耦**：前端静态站点 + 后端 REST API 完全独立，可分别部署到不同服务器；
  后端 CORS 白名单见 `app.py` 中的 TODO-EXTENSION 说明。
- **TODO-EXTENSION 预留**：登录认证（JWT）、用户/角色权限、采购订单模块、
  BOM 维护界面、库位管理、占用库存（出库提交锁定）等，代码中均有标注。

## 九、部署上线（让别人在线访问）

本项目是「前端静态页 + 后端 REST API」结构，部署时可**合成一个服务**：
由 Flask 同时托管前端页面与 API（前后端同源，无跨域问题），一个网址即可访问整站。

> 本地开发方式完全不受影响，仍是前端 8000、后端 5000 两个服务。

### 9.1 推送到 GitHub

```bash
cd pet-collar-erp
git init
git add .
git commit -m "feat: 智能宠物健康监测项圈 ERP 库存管理系统"
git branch -M main
git remote add origin git@github.com:你的用户名/pet-collar-erp.git
git push -u origin main
```

- `.gitignore` 已排除 `.venv/`、`database/*.db`、`.env`，仓库只保留源码；
- `frontend/vendor/` 已内置 Font Awesome 6.5.2 与 ECharts 5.5.1，
  **不依赖外网 CDN**（jsdelivr 在部分网络下无法访问，会导致图标/图表白屏）。

### 9.2 部署到 PythonAnywhere（免费，文件系统持久，不休眠）

1. 注册 https://www.pythonanywhere.com 免费 Beginner 账号；
2. 进入 **Consoles → Bash**，依次执行：

   ```bash
   git clone https://github.com/你的用户名/pet-collar-erp.git
   cd pet-collar-erp
   pip3 install --user -r requirements.txt
   python3 backend/seed.py          # 生成演示数据（必须执行一次）
   ```

3. 进入 **Web → Add a new web app → Manual configuration → Python 3.10**；
4. **Source code** 与 **Working directory** 两栏都填
   `/home/你的用户名/pet-collar-erp`；
5. 点击 **WSGI configuration file** 链接，清空文件原有内容，替换为：

   ```python
   import sys

   path = "/home/你的用户名/pet-collar-erp/backend"
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application   # noqa: E402
   ```

   > 路径要指向 `backend/`（`app.py` 所在目录）；服务器上没有 `.env` 时会自动使用 SQLite。

6. 点击 **Reload**，访问 `https://你的用户名.pythonanywhere.com` ——首页、图表、API 全部就绪。

> ⚠️ **免费账号的 Web App 有有效期（约 3 个月）**。到期后网址会显示「停用」提示，
> 需要登录 PythonAnywhere，在 **Web** 页面点一次 **Run until 3 months from today** 续期。
> **交作业/答辩前，务必先自己打开一次链接确认能访问。**

### 9.3 演示数据过期怎么刷新

种子数据里的「今日入库 8 单 / 今日出库 6 单」是按**运行 seed 的当天**生成的，
隔天再打开首页，这两个数字会变成 0（这是正常现象，不是故障）。刷新方式：

在 **Consoles → Bash** 重新执行，然后回 **Web 页面点一次 Reload**：

```bash
cd ~/pet-collar-erp && python3 backend/seed.py
```

> TODO-EXTENSION: 也可以在 PythonAnywhere 的 **Tasks** 面板加一个每日定时任务
> （命令：`python3 /home/你的用户名/pet-collar-erp/backend/seed.py`）自动刷新演示数据。

### 9.4 部署后自检清单

- [ ] 打开 `https://你的用户名.pythonanywhere.com` 能看到登录页，点击可进入系统
- [ ] 首页右上角显示绿点「后端已连接」
- [ ] 首页 4 个 KPI、近 7 天趋势图、预警列表均正常（图标与图表能显示出来）
- [ ] 出库管理 → 打开生产 50 套的草稿单 → 点「提交审核」→ 弹出 M101 库存不足提示

### 9.5 当前线上实例（维护备忘）

| 项目 | 值 |
|---|---|
| 访问网址 | <https://zhouyuesong.pythonanywhere.com> |
| PythonAnywhere 账号 | `zhouyuesong` |
| 代码目录 | `/home/zhouyuesong/erp` |
| 虚拟环境 | `/home/zhouyuesong/venv-erp` |
| WSGI 入口 | `/var/www/zhouyuesong_pythonanywhere_com_wsgi.py` |
| 数据库文件 | `/home/zhouyuesong/erp/database/erp.db`（SQLite） |

日常维护：进入 **Consoles → Bash** 执行命令，改完回 **Web** 页面点一次 **Reload**：

```bash
cd /home/zhouyuesong/erp
git pull                                                 # 拉取最新代码
/home/zhouyuesong/venv-erp/bin/python backend/seed.py    # 重置演示数据
```

## 十、常见问题

| 问题 | 解决 |
|---|---|
| 前端页面「后端未连接」 | 确认已运行 `python backend/app.py`，且浏览器可访问 http://127.0.0.1:5000/api/v1/materials |
| 5000 端口被占用 | 修改 `backend/app.py` 的 `port` 参数，并同步修改 `frontend/js/config.js` |
| 想恢复初始演示数据 | 重新执行 `python backend/seed.py`（覆盖式重建） |
| pip 安装慢 | 加国内镜像 `-i https://mirrors.aliyun.com/pypi/simple/` |
| 浏览器打开的是文件路径（file://） | 必须通过 http://localhost:8000 访问，file:// 下 fetch 无法工作 |
