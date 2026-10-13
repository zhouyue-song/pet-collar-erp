/* ============================================================
 * warning.js — 库存预警页逻辑
 * ------------------------------------------------------------
 * 预警规则（与后端 dashboard_service.WARNING_RATIO = 1.2 一致）：
 *   库存总量 < 安全库存          → 库存不足（LOW，红色）
 *   安全库存 ≤ 库存总量 < 安全×1.2 → 正常但进入监控（提示关注）
 * 数据来源：GET /api/v1/inventory（全量），前端按物料跨仓库汇总。
 * ============================================================ */

var warningState = {
  rows: [],      // 汇总后的预警行
  filtered: [],  // 当前筛选结果
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  statusChip: "",
  keyword: "",
};

/* ---------------- 页面初始化 ---------------- */
function initWarning() {
  initPage();
  loadAll();

  document.getElementById("btnRefreshWarning").addEventListener("click", loadAll);
  document.getElementById("btnWnSearch").addEventListener("click", function () {
    warningState.keyword = document.getElementById("fWnKeyword").value.trim();
    applyFilter();
  });
  document.getElementById("fWnKeyword").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      warningState.keyword = document.getElementById("fWnKeyword").value.trim();
      applyFilter();
    }
  });
  document.querySelectorAll(".chip-group .chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.querySelectorAll(".chip-group .chip").forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      warningState.statusChip = chip.dataset.status;
      applyFilter();
    });
  });
}

/* ======================================================
 * API: 库存列表（全量拉取后前端按物料汇总预警）
 * Method: GET    URL: /api/v1/inventory?page_size=500
 * Backend: backend/routes/inventory.py -> backend/services/inventory_service.py
 * 二次开发说明：数据量大时可改为后端提供专门的 /api/v1/inventory/warnings
 *              汇总接口，前端切换成本很低（只改本函数）。
 * ====================================================== */
// API-BEGIN: WARNING_INVENTORY
function loadAll() {
  API.get("/inventory", { page_size: 500 })
    .then(function (d) {
      aggregateWarnings(d.items || []);
      applyFilter();
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: WARNING_INVENTORY

/** 按物料跨仓库汇总 → 预警行 */
function aggregateWarnings(items) {
  var map = {};
  items.forEach(function (r) {
    if (!map[r.material_id]) {
      map[r.material_id] = {
        material_code: r.material_code,
        material_name: r.material_name,
        specification: r.specification,
        unit: r.unit,
        safety_stock: r.safety_stock || 0,
        total: 0,
      };
    }
    map[r.material_id].total += r.quantity || 0;
  });

  var rows = [];
  Object.keys(map).forEach(function (k) {
    var row = map[k];
    if (!row.safety_stock) return; // 未设置安全库存：不纳入监控
    row.threshold = Math.round(row.safety_stock * APP_CONFIG.WARNING_RATIO * 10000) / 10000;
    row.status = row.total < row.safety_stock ? "LOW" : "NORMAL";
    row.gap = Math.round((row.threshold - row.total) * 10000) / 10000;
    rows.push(row);
  });
  // 库存不足在前，其次按 总量/安全库存 比值升序（越紧急越靠前）
  rows.sort(function (a, b) {
    if (a.status !== b.status) return a.status === "LOW" ? -1 : 1;
    return a.total / a.safety_stock - b.total / b.safety_stock;
  });
  warningState.rows = rows;

  var lowCount = rows.filter(function (r) { return r.status === "LOW"; }).length;
  document.getElementById("wnLowCount").textContent = lowCount;
  document.getElementById("wnSafetyCount").textContent = rows.length;
  document.getElementById("wnTotalCount").textContent = rows.length;
}

function applyFilter() {
  var rows = warningState.rows.filter(function (r) {
    if (warningState.statusChip && r.status !== warningState.statusChip) return false;
    if (warningState.keyword) {
      var kw = warningState.keyword;
      if (r.material_code.indexOf(kw) === -1 && r.material_name.indexOf(kw) === -1) return false;
    }
    return true;
  });
  warningState.filtered = rows;
  warningState.page = 1;
  renderList();
}

function renderList() {
  var total = warningState.filtered.length;
  var pages = Math.max(1, Math.ceil(total / warningState.pageSize));
  if (warningState.page > pages) warningState.page = pages;
  var start = (warningState.page - 1) * warningState.pageSize;
  var rows = warningState.filtered.slice(start, start + warningState.pageSize);

  var tbody = document.getElementById("warningTbody");
  if (!rows.length) {
    tbody.innerHTML = emptyRow(10, "当前筛选条件下暂无预警物料");
    renderPagination(document.getElementById("warningPagination"), { page: 1, pages: 1, total: 0 }, null);
    return;
  }
  tbody.innerHTML = rows
    .map(function (r) {
      var low = r.status === "LOW";
      return (
        "<tr>" +
        "<td>" + escapeHtml(r.material_code) + "</td>" +
        "<td>" + escapeHtml(r.material_name) + "</td>" +
        '<td class="text-secondary">' + escapeHtml(r.specification || "") + "</td>" +
        "<td>" + escapeHtml(r.unit) + "</td>" +
        '<td class="num text-bold">' + fmtQty(r.total) + "</td>" +
        '<td class="num">' + fmtQty(r.safety_stock) + "</td>" +
        '<td class="num">' + fmtQty(r.threshold) + "</td>" +
        '<td class="num ' + (r.gap > 0 ? "text-danger text-bold" : "text-secondary") + '">' +
        (r.gap > 0 ? fmtQty(r.gap) : "--") + "</td>" +
        "<td>" +
        (low
          ? '<span class="badge badge-red"><i class="fa-solid fa-triangle-exclamation"></i> 库存不足</span>'
          : '<span class="badge badge-orange">正常 · 关注</span>') +
        "</td>" +
        '<td><a class="btn btn-text btn-sm" href="inventory.html?material_code=' + encodeURIComponent(r.material_code) + '">查看库存</a></td>' +
        "</tr>"
      );
    })
    .join("");
  renderPagination(
    document.getElementById("warningPagination"),
    { page: warningState.page, pages: pages, total: total },
    function (p) {
      warningState.page = p;
      renderList();
    }
  );
}

document.addEventListener("DOMContentLoaded", initWarning);
