/* ============================================================
 * inventory.js — 库存总览页逻辑
 * ------------------------------------------------------------
 * 账面库存只读：前端不提供任何直接修改库存的入口，
 * 只能通过 入库确认 / 出库确认 / 盘点调整 三个业务单据变动。
 * ============================================================ */

var inventoryState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
};

/* ---------------- 页面初始化 ---------------- */
function initInventory() {
  initPage();

  // 支持从其他页面跳转携带物料编码（如库存预警页「查看库存」链接）
  var urlParams = new URLSearchParams(window.location.search);
  var presetCode = urlParams.get("material_code");
  if (presetCode) {
    document.getElementById("fIvCode").value = presetCode;
    inventoryState.filters = collectFilters();
  }

  loadList(1);

  document.getElementById("btnRefreshInv").addEventListener("click", function () {
    loadList(inventoryState.page);
  });
  document.getElementById("btnIvSearch").addEventListener("click", function () {
    inventoryState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnIvReset").addEventListener("click", resetFilters);
}

function collectFilters() {
  return {
    material_code: document.getElementById("fIvCode").value.trim(),
    material_name: document.getElementById("fIvName").value.trim(),
    warehouse: document.getElementById("fIvWarehouse").value,
    location: document.getElementById("fIvLocation").value.trim(),
    abc_class: document.getElementById("fIvAbc").value,
    stock_status: document.getElementById("fIvStatus").value,
  };
}

function resetFilters() {
  ["fIvCode", "fIvName", "fIvLocation"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
  document.getElementById("fIvWarehouse").value = "";
  document.getElementById("fIvAbc").value = "";
  document.getElementById("fIvStatus").value = "";
  inventoryState.filters = {};
  loadList(1);
}

/* ======================================================
 * API: 库存列表（筛选 + 分页 + 汇总）
 * Method: GET    URL: /api/v1/inventory
 * Backend: backend/routes/inventory.py -> backend/services/inventory_service.py
 * 二次开发说明：stock_status 由后端按「物料全仓库总库存 vs 安全库存」
 *              判定，前端只做展示，不自行计算状态。
 * ====================================================== */
// API-BEGIN: INVENTORY_LIST
function loadList(page) {
  inventoryState.page = page || inventoryState.page;
  var params = Object.assign({}, inventoryState.filters, {
    page: inventoryState.page,
    page_size: inventoryState.pageSize,
  });
  API.get("/inventory", params)
    .then(function (d) {
      renderSummary(d.summary || {});
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: INVENTORY_LIST

function renderSummary(s) {
  document.getElementById("msMaterialCount").textContent = s.material_count || 0;
  document.getElementById("msTotalQuantity").textContent = fmtQty(s.total_quantity);
  document.getElementById("msTotalAmount").textContent = fmtMoney(s.total_amount);
  // 不足种数：对当前筛选结果按物料去重统计（与后端判定规则一致）
  var lowSet = {};
  document.querySelectorAll("#inventoryTbody tr[data-material-id]").forEach(function (tr) {
    if (tr.dataset.stockStatus === "LOW") lowSet[tr.dataset.materialId] = true;
  });
  document.getElementById("msLowCount").textContent = Object.keys(lowSet).length;
  var whSet = {};
  document.querySelectorAll("#inventoryTbody tr[data-material-id]").forEach(function (tr) {
    whSet[tr.dataset.warehouse] = true;
  });
  document.getElementById("msWarehouseCount").textContent = Object.keys(whSet).length;
}

function renderList(d) {
  var tbody = document.getElementById("inventoryTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(12, "暂无库存记录");
    renderPagination(document.getElementById("inventoryPagination"), d, null);
    renderSummary(d.summary || {});
    return;
  }
  tbody.innerHTML = items
    .map(function (r) {
      var low = r.stock_status === "LOW";
      return (
        '<tr data-material-id="' + r.material_id + '" data-stock-status="' + r.stock_status + '" data-warehouse="' + escapeHtml(r.warehouse) + '">' +
        "<td>" + escapeHtml(r.material_code) + "</td>" +
        "<td>" + escapeHtml(r.material_name) + "</td>" +
        "<td>" + escapeHtml(r.specification) + "</td>" +
        "<td>" + escapeHtml(r.unit) + "</td>" +
        "<td>" + escapeHtml(r.warehouse) + "</td>" +
        "<td>" + escapeHtml(r.location) + "</td>" +
        '<td class="num text-bold">' + fmtQty(r.quantity) + "</td>" +
        '<td class="num">' + fmtQty(r.safety_stock) + "</td>" +
        "<td>" +
        (low
          ? '<span class="badge badge-red"><i class="fa-solid fa-triangle-exclamation"></i> 库存不足</span>'
          : '<span class="badge badge-green">正常</span>') +
        "</td>" +
        '<td class="num">' + fmtMoney(r.average_price) + "</td>" +
        '<td class="num">' + fmtMoney(r.inventory_amount) + "</td>" +
        '<td class="text-secondary">' + escapeHtml(r.updated_at || "") + "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("inventoryPagination"), d, loadList);
  renderSummary(d.summary || {});
}

document.addEventListener("DOMContentLoaded", initInventory);
