/* ============================================================
 * config.js — 全局配置（唯一配置入口）
 * ------------------------------------------------------------
 * 后端地址/数据库切换只改 backend/.env 的 DATABASE_URL；
 * 前端 API 地址由下面 API_BASE_URL 自动识别，通常无需手工修改。
 *
 * 两种运行模式（自动识别，无需改代码）：
 *   1) 本地开发：前端 python -m http.server 8000，后端 127.0.0.1:5000
 *      → 访问本机 localhost/127.0.0.1 时，API 指向 http://127.0.0.1:5000/api/v1
 *   2) 线上部署：由 Flask 同时托管前端页面与 API（同源）
 *      → API 自动指向当前域名 + /api/v1，不存在跨域问题
 * ============================================================ */
// 本机访问判定：localhost / 127.0.0.1 / 直接用浏览器打开 html 文件
var IS_LOCAL_ENV =
  location.protocol === "file:" ||
  location.hostname === "localhost" ||
  location.hostname === "127.0.0.1";

var APP_CONFIG = {
  // 后端 REST API 根地址（本地开发指向 127.0.0.1:5000；线上自动同源）
  API_BASE_URL: IS_LOCAL_ENV
    ? "http://127.0.0.1:5000/api/v1"   // 本地开发：后端独立运行在 5000 端口
    : location.origin + "/api/v1",      // 线上部署：与页面同源，走 Flask 托管的 API

  // 列表默认每页条数（后端上限 500）
  PAGE_SIZE: 10,

  // 库存预警监控系数：库存总量 < 安全库存 × 该系数 即进入预警监控
  // （与后端 dashboard_service.WARNING_RATIO 保持一致）
  WARNING_RATIO: 1.2,

  // 仓库字典（与 seed.py 初始化数据一致，新增仓库时同步维护）
  WAREHOUSES: ["原材料仓", "半成品仓", "成品仓"],
};
