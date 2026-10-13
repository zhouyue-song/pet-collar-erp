/* ============================================================
 * ledger.js — 库存流水页逻辑（库存台账）
 * ------------------------------------------------------------
 * 流水由后端 change_stock() 统一生成，本页只查询与统计。
 * 恒等式：变动前 + 变动数量 = 变动后（IN 为正 / OUT 为负 / ADJUST 带符号）
 * ============================================================ */

var ledgerState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
};

/* ---------------- 页面初始化 ---------------- */
function initLedger() {
  initPage();
  loadList(1);

  document.getElementById("btnRefreshLedger").addEventListener("click", function () {
    loadList(ledgerState.page);
  });
  document.getElementById("btnLgSearch").addEventListener("click", function () {
    ledgerState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnLgReset").addEventListener("click", resetFilters);
}

function collectFilters() {
  return {
    start_date: document.getElementById("fLgStart").value,
    end_date: document.getElementById("fLgEnd").value,
    material_code: document.getElementById("fLgCode").value.trim(),
    warehouse: document.getElementById("fLgWarehouse").value,
    document_type: document.getElementById("fLgDocType").value,
  };
}

function resetFilters() {
  ["fLgStart", "fLgEnd", "fLgCode"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
  document.getElementById("fLgWarehouse").value = "";
  document.getElementById("fLgDocType").value = "";
  ledgerState.filters = {};
  loadList(1);
}

/* ======================================================
 * API: 库存流水列表（筛选 + 分页 + 出入库统计）
 * Method: GET    URL: /api/v1/ledger
 * Backend: backend/routes/ledger.py -> backend/services/ledger_service.py
 * 二次开发说明：后端 summary 随筛选条件联动，前端只做展示。
 * ====================================================== */
// API-BEGIN: LEDGER_LIST
function loadList(page) {
  ledgerState.page = page || ledgerState.page;
  var params = Object.assign({}, ledgerState.filters, {
    page: ledgerState.page,
    page_size: ledgerState.pageSize,
  });
  API.get("/ledger", params)
    .then(function (d) {
      renderSummary(d.summary || {});
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: LEDGER_LIST

function renderSummary(s) {
  document.getElementById("msLgInQty").textContent = fmtQty(s.in_quantity);
  document.getElementById("msLgOutQty").textContent = fmtQty(s.out_quantity);
  document.getElementById("msLgAdjQty").textContent = fmtQty(s.adjust_quantity);
  document.getElementById("msLgInAmount").textContent = fmtMoney(s.in_amount);
  document.getElementById("msLgOutAmount").textContent = fmtMoney(s.out_amount);
}

var DIRECTION_BADGES = {
  IN: { cls: "badge-green", label: "入库" },
  OUT: { cls: "badge-orange", label: "出库" },
  ADJUST: { cls: "badge-blue", label: "调整" },
};

function renderList(d) {
  var tbody = document.getElementById("ledgerTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(15, "暂无流水记录，请调整筛选条件");
    renderPagination(document.getElementById("ledgerPagination"), d, null);
    return;
  }
  tbody.innerHTML = items
    .map(function (r) {
      var q = r.quantity || 0;
      var qCls = q > 0 ? "text-success" : q < 0 ? "text-danger" : "";
      var qTxt = q > 0 ? "+" + fmtQty(q) : fmtQty(q);
      return (
        "<tr>" +
        '<td class="text-secondary">' + r.id + "</td>" +
        "<td>" + escapeHtml(r.document_no) + "</td>" +
        "<td>" + escapeHtml(r.document_type_label) + "</td>" +
        "<td>" + escapeHtml(r.material_code) + "</td>" +
        "<td>" + escapeHtml(r.material_name) + "</td>" +
        "<td>" + escapeHtml(r.warehouse) + "</td>" +
        "<td>" + escapeHtml(r.location) + "</td>" +
        "<td>" + statusBadge(r.direction, DIRECTION_BADGES) + "</td>" +
        '<td class="num">' + fmtQty(r.before_quantity) + "</td>" +
        '<td class="num text-bold ' + qCls + '">' + qTxt + "</td>" +
        '<td class="num">' + fmtQty(r.after_quantity) + "</td>" +
        '<td class="num">' + fmtMoney(r.unit_price) + "</td>" +
        '<td class="num">' + fmtMoney(r.amount) + "</td>" +
        '<td class="text-secondary">' + escapeHtml(r.business_time || "") + "</td>" +
        "<td>" + escapeHtml(r.operator || "") + "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("ledgerPagination"), d, loadList);
}

document.addEventListener("DOMContentLoaded", initLedger);
