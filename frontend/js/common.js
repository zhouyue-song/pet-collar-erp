/* ============================================================
 * common.js — 公共逻辑：侧边栏/顶部栏/Toast/分页/工具函数
 * ------------------------------------------------------------
 * 每个页面在 <body data-page="xxx"> 上声明自己的页面名，
 * 本文件根据 MENU_CONFIG 动态渲染左侧导航与顶部 header，
 * 新增页面只需在 MENU_CONFIG 中登记即可，无需改动每个 HTML。
 * ============================================================ */

/* ---------------- 左侧菜单配置（集中管理，新增页面在此登记） ---------------- */
var MENU_CONFIG = [
  {
    title: "首页",
    icon: "fa-gauge-high",
    items: [
      { label: "数据总览", page: "dashboard.html" },
    ],
  },
  {
    title: "采购管理",
    icon: "fa-cart-shopping",
    items: [
      // TODO-EXTENSION: 采购订单模块（供应商管理/询价/下单）二期实现
      { label: "采购订单", page: null },
      { label: "到货登记", page: "inbound.html" },
    ],
  },
  {
    title: "库存管理",
    icon: "fa-warehouse",
    items: [
      { label: "库存总览", page: "inventory.html" },
      { label: "入库管理", page: "inbound.html" },
      { label: "出库管理", page: "outbound.html" },
      { label: "库存盘点", page: "stocktake.html" },
      { label: "库存查询", page: "inventory.html" },
      { label: "库存流水", page: "ledger.html" },
    ],
  },
  {
    title: "物料管理",
    icon: "fa-boxes-stacked",
    items: [
      { label: "物料档案", page: "materials.html" },
      { label: "BOM 产品结构", page: "bom.html" },
      { label: "ABC 分类", page: "materials.html" },
    ],
  },
  {
    title: "生产管理",
    icon: "fa-industry",
    items: [
      { label: "生产领料", page: "outbound.html" },
      { label: "完工入库", page: "inbound.html" },
    ],
  },
  {
    title: "报表中心",
    icon: "fa-chart-column",
    items: [
      { label: "库存台账", page: "ledger.html" },
      { label: "出入库统计", page: "ledger.html" },
      { label: "库存预警", page: "warning.html" },
    ],
  },
  {
    title: "系统管理",
    icon: "fa-gears",
    items: [
      // TODO-EXTENSION: 用户管理 / 角色权限 / 系统参数（登录认证二期实现）
      { label: "用户管理", page: null },
      { label: "角色权限", page: null },
      { label: "系统参数", page: null },
    ],
  },
];

/* ---------------- 侧边栏渲染 ---------------- */
function renderSidebar() {
  var box = document.getElementById("appSidebar");
  if (!box) return;

  var currentPage = document.body.dataset.page || "";
  var html = "";
  html +=
    '<div class="sidebar-logo">' +
    '<div class="logo-icon"><i class="fa-solid fa-dog"></i></div>' +
    '<div class="logo-text">宠物项圈 ERP<small>库存管理系统</small></div>' +
    "</div>";
  html += '<nav class="sidebar-nav">';

  var pageLabel = ""; // 当前页显示名（顶部栏标题用）

  MENU_CONFIG.forEach(function (group, gi) {
    var openClass = "";
    var itemsHtml = "";
    group.items.forEach(function (item) {
      if (!item.page) {
        // 未实现模块：点击提示二次开发预留
        itemsHtml +=
          '<div class="nav-item disabled" data-todo="' + escapeHtml(item.label) + '">' +
          escapeHtml(item.label) +
          "</div>";
        return;
      }
      var active = item.page === currentPage ? " active" : "";
      if (active) {
        openClass = " open";
        pageLabel = item.label;
      }
      itemsHtml +=
        '<div class="nav-item' + active + '" data-href="' + item.page + '">' +
        escapeHtml(item.label) +
        "</div>";
    });
    html += '<div class="nav-group' + openClass + '">';
    html +=
      '<div class="nav-group-title"><span class="nav-icon"><i class="fa-solid ' +
      group.icon +
      '"></i></span>' +
      escapeHtml(group.title) +
      '<span class="nav-arrow"><i class="fa-solid fa-chevron-right"></i></span></div>';
    html += '<div class="nav-group-items">' + itemsHtml + "</div>";
    html += "</div>";
  });

  html += "</nav>";
  html += '<div class="sidebar-footer">v1.0 · Flask + SQLAlchemy<br>课程项目演示系统</div>';
  box.innerHTML = html;

  // 事件：分组展开/收起
  box.querySelectorAll(".nav-group-title").forEach(function (t) {
    t.addEventListener("click", function () {
      t.parentElement.classList.toggle("open");
    });
  });
  // 事件：菜单跳转
  box.querySelectorAll(".nav-item[data-href]").forEach(function (n) {
    n.addEventListener("click", function () {
      window.location.href = n.dataset.href;
    });
  });
  // 事件：未实现模块提示
  box.querySelectorAll(".nav-item[data-todo]").forEach(function (n) {
    n.addEventListener("click", function () {
      toast("「" + n.dataset.todo + "」为二次开发预留模块（TODO-EXTENSION）", "info");
    });
  });
  return pageLabel;
}

/* ---------------- 顶部栏渲染（含后端连通状态检测） ---------------- */
function renderHeader(pageLabel) {
  var box = document.getElementById("appHeader");
  if (!box) return;

  var today = new Date();
  var dateStr =
    today.getFullYear() + "年" + (today.getMonth() + 1) + "月" + today.getDate() + "日";

  box.innerHTML =
    '<div class="header-title">' + escapeHtml(pageLabel || "宠物项圈 ERP") + "</div>" +
    '<div class="header-right">' +
    '<div class="header-date"><i class="fa-regular fa-calendar"></i> ' + dateStr + "</div>" +
    '<div class="header-api-status" id="apiStatus"><span class="status-dot"></span><span class="status-text">后端连接检测中...</span></div>' +
    '<div class="header-user"><div class="avatar"><i class="fa-solid fa-user"></i></div>系统管理员</div>' +
    "</div>";

  // 后端连通性检测（轻量请求，不干扰页面主流程）
  // API-BEGIN: API_HEALTH_CHECK
  // API: 后端连通性检测（复用物料列表接口的最小分页请求）
  // Method: GET    URL: /api/v1/materials?page_size=1
  // Backend: backend/routes/materials.py -> backend/services/material_service.py
  // 二次开发说明：后端若新增 /health 接口，可替换为更轻量的健康检查
  API.get("/materials", { page_size: 1 })
    .then(function () {
      var st = document.getElementById("apiStatus");
      if (st) {
        st.className = "header-api-status ok";
        st.querySelector(".status-text").textContent = "后端已连接";
      }
    })
    .catch(function () {
      var st = document.getElementById("apiStatus");
      if (st) {
        st.className = "header-api-status error";
        st.querySelector(".status-text").textContent = "后端未连接";
      }
    });
  // API-END: API_HEALTH_CHECK
}

/* ---------------- Toast 消息 ---------------- */
var TOAST_ICONS = {
  success: "fa-circle-check",
  error: "fa-circle-xmark",
  warning: "fa-triangle-exclamation",
  info: "fa-circle-info",
};

function toast(message, type) {
  type = type || "success";
  var box = document.getElementById("toastContainer");
  if (!box) {
    alert(message);
    return;
  }
  var el = document.createElement("div");
  el.className = "toast " + type;
  el.innerHTML =
    '<i class="fa-solid ' + (TOAST_ICONS[type] || TOAST_ICONS.info) + '"></i>' +
    "<div>" + escapeHtml(message) + "</div>";
  box.appendChild(el);
  setTimeout(function () {
    el.classList.add("leaving");
    setTimeout(function () { el.remove(); }, 300);
  }, 3000);
}

/* ---------------- 危险操作确认 ---------------- */
function confirmAction(message) {
  return window.confirm(message);
}

/* ---------------- 工具函数 ---------------- */
function escapeHtml(str) {
  return String(str === null || str === undefined ? "" : str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** 金额：两位小数 */
function fmtMoney(n) {
  var v = Number(n) || 0;
  return v.toFixed(2);
}

/** 数量：最多 4 位小数，去掉多余 0 */
function fmtQty(n) {
  var v = Number(n) || 0;
  return String(Math.round(v * 10000) / 10000);
}

/* ---------------- 分页组件 ---------------- */
function renderPagination(el, pg, onPage) {
  if (!el) return;
  if (!pg || !pg.pages || pg.pages <= 1) {
    el.innerHTML = "";
    return;
  }
  var html = '<span class="page-info">共 ' + pg.total + " 条 · " + pg.page + "/" + pg.pages + " 页</span>";
  html += '<button class="page-btn" data-p="' + (pg.page - 1) + '"' + (pg.page <= 1 ? " disabled" : "") + '><i class="fa-solid fa-chevron-left"></i></button>';
  var start = Math.max(1, pg.page - 2);
  var end = Math.min(pg.pages, pg.page + 2);
  for (var p = start; p <= end; p++) {
    html += '<button class="page-btn' + (p === pg.page ? " active" : "") + '" data-p="' + p + '">' + p + "</button>";
  }
  html += '<button class="page-btn" data-p="' + (pg.page + 1) + '"' + (pg.page >= pg.pages ? " disabled" : "") + '><i class="fa-solid fa-chevron-right"></i></button>';
  el.innerHTML = html;
  el.querySelectorAll(".page-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      var p = Number(b.dataset.p);
      if (b.disabled || p < 1 || p > pg.pages || p === pg.page) return;
      onPage(p);
    });
  });
}

/* ---------------- 状态徽章映射（颜色语义：绿=完成 橙=待处理 红=异常 蓝=进行中） ---------------- */
var ORDER_STATUS_BADGES = {
  DRAFT: { cls: "badge-gray", label: "草稿" },
  PENDING: { cls: "badge-orange", label: "待审核" },
  COMPLETED: { cls: "badge-green", label: "已完成" },
  REJECTED: { cls: "badge-red", label: "已驳回" },
};

var STOCKTAKE_STATUS_BADGES = {
  DRAFT: { cls: "badge-gray", label: "草稿" },
  COUNTING: { cls: "badge-blue", label: "盘点中" },
  PENDING_REVIEW: { cls: "badge-orange", label: "待复核" },
  COMPLETED: { cls: "badge-green", label: "已完成" },
};

var ABC_BADGES = {
  A: { cls: "badge-red", label: "A类" },
  B: { cls: "badge-orange", label: "B类" },
  C: { cls: "badge-blue", label: "C类" },
};

function statusBadge(status, map) {
  var b = (map || {})[status] || { cls: "badge-gray", label: status };
  return '<span class="badge ' + b.cls + '">' + b.label + "</span>";
}

/* ---------------- 表格空状态 ---------------- */
function emptyRow(colspan, text) {
  return (
    '<tr><td class="table-empty" colspan="' + colspan + '">' +
    '<i class="fa-regular fa-folder-open"></i>' + escapeHtml(text || "暂无数据") +
    "</td></tr>"
  );
}

/* ---------------- 日期工具 ---------------- */
/** YYYY-MM-DD */
function fmtDate(d) {
  var y = d.getFullYear();
  var m = String(d.getMonth() + 1).padStart(2, "0");
  var day = String(d.getDate()).padStart(2, "0");
  return y + "-" + m + "-" + day;
}

/** 今天的 YYYY-MM-DD */
function todayStr() {
  return fmtDate(new Date());
}

/* ---------------- 抽屉/模态框开关 ---------------- */
function openDrawer(maskId) {
  document.getElementById(maskId).classList.add("open");
}
function closeDrawer(maskId) {
  document.getElementById(maskId).classList.remove("open");
}
function openModal(maskId) {
  document.getElementById(maskId).classList.add("open");
}
function closeModal(maskId) {
  document.getElementById(maskId).classList.remove("open");
}

/* ---------------- BOM 树展平（outbound.js 预览 / bom.js 汇总共用） ----------------
 * 把树形 BOM 展开为叶子物料清单，path 乘数累加，
 * 与后端 services/bom_service.py flatten_product() 算法一致：
 *   {code, name, unit, usage}，usage = 单件用量，需求数量 = usage × 生产数量
 */
function flattenBomTree(node) {
  var result = {};
  function walk(n, multiplier) {
    if (!n) return;
    var q = (Number(n.quantity) || 1) * multiplier;
    if (n.type === "material" || !(n.children && n.children.length)) {
      if (result[n.code]) {
        result[n.code].usage = Math.round((result[n.code].usage + q) * 10000) / 10000;
      } else {
        result[n.code] = {
          code: n.code,
          name: n.name,
          unit: n.unit,
          usage: Math.round(q * 10000) / 10000,
        };
      }
      return;
    }
    (n.children || []).forEach(function (c) { walk(c, q); });
  }
  walk(node, 1);
  return Object.keys(result).map(function (k) { return result[k]; });
}

/* ---------------- 页面初始化入口（每个页面 JS 底部调用） ---------------- */
function initPage() {
  var pageLabel = renderSidebar();
  renderHeader(pageLabel);
}
