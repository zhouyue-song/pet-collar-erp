/* ============================================================
 * stocktake.js — 库存盘点页逻辑
 * ------------------------------------------------------------
 * 业务流程（步骤条联动）：
 *   1 创建盘点任务：后端自动生成该仓库全部库存的账面快照（COUNTING）
 *   2 录入实盘数量：保存后自动计算差异 = 实盘 − 账面（盘盈/盘亏/正常）
 *   3 提交审核：全部录入完成后可提交（PENDING_REVIEW）
 *   4 确认调整：差异≠0 生成 ADJUST 流水调整库存（COMPLETED）
 * 重要：盘点永远不能直接覆盖库存，必须先产生差异记录再调整。
 * ============================================================ */

var stocktakeState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
  editingId: null,
  status: "",
};

/* ---------------- 页面初始化 ---------------- */
function initStocktake() {
  initPage();
  loadList(1);

  document.getElementById("btnNewStocktake").addEventListener("click", openCreateDrawer);
  document.getElementById("btnStSearch").addEventListener("click", function () {
    stocktakeState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnStReset").addEventListener("click", resetFilters);
  document.getElementById("btnStDrawerClose").addEventListener("click", function () {
    closeDrawer("stocktakeDrawerMask");
  });
  document.getElementById("btnStCancel").addEventListener("click", function () {
    closeDrawer("stocktakeDrawerMask");
  });
  document.getElementById("btnStSave").addEventListener("click", saveOrder);
  document.getElementById("btnStSubmit").addEventListener("click", submitOrder);
  document.getElementById("btnStAdjust").addEventListener("click", adjustOrder);
}

function collectFilters() {
  return {
    stocktake_no: document.getElementById("fStNo").value.trim(),
    warehouse: document.getElementById("fStWarehouse").value,
    stocktake_type: document.getElementById("fStType").value,
    stocktake_date: document.getElementById("fStDate").value,
    status: document.getElementById("fStStatus").value,
  };
}

function resetFilters() {
  ["fStNo", "fStDate"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
  document.getElementById("fStWarehouse").value = "";
  document.getElementById("fStType").value = "";
  document.getElementById("fStStatus").value = "";
  stocktakeState.filters = {};
  loadList(1);
}

/* ======================================================
 * API: 盘点单列表（筛选 + 分页）
 * Method: GET    URL: /api/v1/stocktakes
 * Backend: backend/routes/stocktake.py -> backend/services/stocktake_service.py
 * ====================================================== */
// API-BEGIN: STOCKTAKE_LIST
function loadList(page) {
  stocktakeState.page = page || stocktakeState.page;
  var params = Object.assign({}, stocktakeState.filters, {
    page: stocktakeState.page,
    page_size: stocktakeState.pageSize,
  });
  API.get("/stocktakes", params)
    .then(function (d) {
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: STOCKTAKE_LIST

var STOCKTAKE_TYPE_LABELS = { FULL: "全面盘点", SAMPLE: "抽样盘点", CYCLE: "循环盘点" };

function renderList(d) {
  var tbody = document.getElementById("stocktakeTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(9, "暂无盘点任务，点击右上角「新建盘点任务」开始");
    renderPagination(document.getElementById("stocktakePagination"), d, null);
    return;
  }
  tbody.innerHTML = items
    .map(function (o) {
      var actions = '<button class="btn btn-text btn-sm" data-act="view" data-id="' + o.id + '">查看</button>';
      if (o.status === "COUNTING") {
        actions += '<button class="btn btn-text btn-sm" data-act="edit" data-id="' + o.id + '">录入实盘</button>';
      }
      if (o.status === "PENDING_REVIEW") {
        actions += '<button class="btn btn-text btn-sm" data-act="adjust" data-id="' + o.id + '">确认调整</button>';
      }
      return (
        "<tr>" +
        "<td>" + escapeHtml(o.stocktake_no) + "</td>" +
        "<td>" + escapeHtml(o.warehouse) + "</td>" +
        "<td>" + escapeHtml(STOCKTAKE_TYPE_LABELS[o.stocktake_type] || o.stocktake_type) + "</td>" +
        "<td>" + escapeHtml(o.stocktake_date) + "</td>" +
        '<td class="num">' + o.item_count + "</td>" +
        '<td class="num ' + (o.difference_count ? "text-danger text-bold" : "") + '">' + o.difference_count + "</td>" +
        "<td>" + statusBadge(o.status, STOCKTAKE_STATUS_BADGES) + "</td>" +
        "<td>" + escapeHtml(o.operator) + "</td>" +
        '<td class="table-actions">' + actions + "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("stocktakePagination"), d, loadList);

  tbody.querySelectorAll("button[data-act]").forEach(function (b) {
    b.addEventListener("click", function () {
      var id = Number(b.dataset.id);
      var act = b.dataset.act;
      if (act === "view" || act === "edit") {
        openEditDrawer(id, act === "view");
      } else if (act === "adjust") {
        doAdjust(id, false);
      }
    });
  });
}

/* ---------------- 步骤条联动 ---------------- */
/** 1创建 / 2录入 / 3提交 / 4调整 */
function renderSteps(status) {
  var activeStep = { "": 1, DRAFT: 1, COUNTING: 2, PENDING_REVIEW: 3, COMPLETED: 4 }[status] || 1;
  document.querySelectorAll("#stSteps .step").forEach(function (s) {
    var n = Number(s.dataset.step);
    s.classList.remove("active", "done");
    if (n < activeStep) s.classList.add("done");
    else if (n === activeStep) s.classList.add("active");
  });
}

/* ---------------- 抽屉 ---------------- */
function openCreateDrawer() {
  stocktakeState.editingId = null;
  stocktakeState.status = "";
  document.getElementById("stocktakeDrawerTitle").textContent = "新建盘点任务（第1步：创建盘点单）";
  document.getElementById("stNo").value = "";
  document.getElementById("stType").value = "FULL";
  document.getElementById("stWarehouse").value = "原材料仓";
  document.getElementById("stDate").value = todayStr();
  document.getElementById("stOperator").value = "王芳";
  document.getElementById("stRemark").value = "";
  document.getElementById("stItemsBody").innerHTML =
    '<tr><td class="table-empty" colspan="10"><i class="fa-regular fa-hand-point-up"></i>创建任务后，系统自动生成该仓库全部库存的账面快照</td></tr>';
  renderSteps("");
  setDrawerEditable(true);
  setDrawerButtons("");
  openDrawer("stocktakeDrawerMask");
}

/* ======================================================
 * API: 盘点单详情（含快照明细）
 * Method: GET    URL: /api/v1/stocktakes/{id}
 * Backend: backend/routes/stocktake.py -> backend/services/stocktake_service.py
 * ====================================================== */
// API-BEGIN: STOCKTAKE_DETAIL
function openEditDrawer(id, readonly) {
  API.get("/stocktakes/" + id)
    .then(function (o) {
      fillDrawer(o, readonly);
      openDrawer("stocktakeDrawerMask");
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: STOCKTAKE_DETAIL

function fillDrawer(o, readonly) {
  stocktakeState.editingId = o.id;
  stocktakeState.status = o.status;
  document.getElementById("stocktakeDrawerTitle").textContent =
    "盘点单 " + o.stocktake_no + "（" + o.status_label + "）";
  document.getElementById("stNo").value = o.stocktake_no;
  document.getElementById("stType").value = o.stocktake_type;
  document.getElementById("stWarehouse").value = o.warehouse;
  document.getElementById("stDate").value = o.stocktake_date;
  document.getElementById("stOperator").value = o.operator;
  document.getElementById("stRemark").value = o.remark;

  var tbody = document.getElementById("stItemsBody");
  tbody.innerHTML = "";
  (o.items || []).forEach(function (it) {
    var diff = it.difference_quantity;
    var diffTxt = diff === null || diff === undefined ? "--" : (diff > 0 ? "+" : "") + fmtQty(diff);
    var diffCls = it.difference_type === "SHORTAGE" ? "diff-shortage"
      : it.difference_type === "SURPLUS" ? "diff-surplus" : "diff-normal";
    var typeBadge = it.difference_type === "SHORTAGE"
      ? '<span class="badge badge-red">盘亏</span>'
      : it.difference_type === "SURPLUS"
        ? '<span class="badge badge-orange">盘盈</span>'
        : '<span class="badge badge-gray">正常</span>';
    var adjBadge = it.adjustment_status === "ADJUSTED"
      ? '<span class="badge badge-green">已调整</span>'
      : it.adjustment_status === "SKIPPED"
        ? '<span class="badge badge-gray">无差异</span>'
        : '<span class="badge badge-blue">待调整</span>';
    var editable = !readonly && o.status === "COUNTING";
    var tr = document.createElement("tr");
    tr.dataset.itemId = it.id;
    tr.innerHTML =
      "<td>" + escapeHtml(it.material_code) + "</td>" +
      "<td>" + escapeHtml(it.material_name) + "</td>" +
      "<td>" + escapeHtml(it.unit) + "</td>" +
      "<td>" + escapeHtml(it.location) + "</td>" +
      '<td class="num">' + fmtQty(it.system_quantity) + "</td>" +
      '<td><input class="form-input num-input" data-f="actual_quantity" type="number" min="0" step="1" value="' +
      (it.actual_quantity === null || it.actual_quantity === undefined ? "" : it.actual_quantity) +
      '" placeholder="待录入"' + (editable ? "" : " disabled") + '></td>' +
      '<td class="num ' + diffCls + ' text-bold">' + diffTxt + "</td>" +
      "<td>" + typeBadge + "</td>" +
      "<td>" + adjBadge + "</td>" +
      '<td><input class="form-input" data-f="difference_reason" type="text" style="width:130px;" placeholder="差异原因(选填)" value="' +
      escapeHtml(it.difference_reason || "") + '"' + (editable ? "" : " disabled") + "></td>";
    tbody.appendChild(tr);
  });
  renderSteps(o.status);
  setDrawerEditable(!readonly && o.status === "COUNTING");
  setDrawerButtons(o.status);
}

function setDrawerEditable(editable) {
  document.getElementById("stType").disabled = !editable;
  document.getElementById("stWarehouse").disabled = !editable;
  document.getElementById("stDate").disabled = !editable;
  document.getElementById("stOperator").disabled = !editable;
  document.getElementById("stRemark").disabled = !editable;
}

function setDrawerButtons(status) {
  document.getElementById("btnStSave").style.display = status === "" || status === "DRAFT" || status === "COUNTING" ? "" : "none";
  document.getElementById("btnStSubmit").style.display = status === "COUNTING" ? "" : "none";
  document.getElementById("btnStAdjust").style.display = status === "PENDING_REVIEW" ? "" : "none";
}

/* ======================================================
 * API: 创建 / 保存盘点数据
 * Method: POST   URL: /api/v1/stocktakes          （创建任务，自动生成快照）
 * Method: PUT    URL: /api/v1/stocktakes/{id}     （录入实盘数量，自动算差异）
 * Backend: backend/routes/stocktake.py -> backend/services/stocktake_service.py
 * ====================================================== */
// API-BEGIN: STOCKTAKE_SAVE
function saveOrder() {
  if (!stocktakeState.editingId) {
    // 新建：创建盘点任务（后端生成账面快照 → COUNTING）
    var data = {
      warehouse: document.getElementById("stWarehouse").value,
      stocktake_type: document.getElementById("stType").value,
      stocktake_date: document.getElementById("stDate").value,
      operator: document.getElementById("stOperator").value.trim(),
      remark: document.getElementById("stRemark").value.trim(),
    };
    if (!data.stocktake_date) return toast("请选择盘点日期", "warning");
    API.post("/stocktakes", data)
      .then(function (o) {
        toast("盘点任务创建成功：" + o.stocktake_no + "，盘点表已生成");
        fillDrawer(o, false);
        loadList(stocktakeState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  } else {
    // 录入实盘数量（后端自动计算差异 盘盈/盘亏/正常）
    var items = [];
    document.querySelectorAll("#stItemsBody tr[data-item-id]").forEach(function (tr) {
      var v = tr.querySelector('input[data-f="actual_quantity"]').value;
      items.push({
        id: Number(tr.dataset.itemId),
        actual_quantity: v === "" ? null : Number(v),
        difference_reason: tr.querySelector('input[data-f="difference_reason"]').value.trim(),
      });
    });
    var payload = {
      operator: document.getElementById("stOperator").value.trim(),
      remark: document.getElementById("stRemark").value.trim(),
      items: items,
    };
    API.put("/stocktakes/" + stocktakeState.editingId, payload)
      .then(function (o) {
        toast("盘点数据已保存，差异已自动计算");
        fillDrawer(o, false);
        loadList(stocktakeState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  }
}
// API-END: STOCKTAKE_SAVE

/* ======================================================
 * API: 提交审核（COUNTING → PENDING_REVIEW，要求全部录入实盘）
 * Method: POST   URL: /api/v1/stocktakes/{id}/submit
 * Backend: backend/routes/stocktake.py -> backend/services/stocktake_service.py
 * ====================================================== */
// API-BEGIN: STOCKTAKE_SUBMIT
function submitOrder() {
  if (!stocktakeState.editingId) return toast("请先创建盘点任务", "warning");
  API.post("/stocktakes/" + stocktakeState.editingId + "/submit")
    .then(function (o) {
      toast("提交审核成功");
      fillDrawer(o, true);
      loadList(stocktakeState.page);
    })
    .catch(function (e) { toast(e.message, "error"); });
}
// API-END: STOCKTAKE_SUBMIT

/* ======================================================
 * API: 确认调整（PENDING_REVIEW → COMPLETED）
 * 事务内：差异≠0 按差异调整库存并生成 ADJUST 流水，失败整体回滚
 * Method: POST   URL: /api/v1/stocktakes/{id}/adjust
 * Backend: backend/routes/stocktake.py -> backend/services/stocktake_service.py
 * ====================================================== */
// API-BEGIN: STOCKTAKE_ADJUST
function adjustOrder() {
  if (!confirmAction("确认调整后库存将按盘点差异变动并生成调整流水，且不可撤销，是否继续？")) return;
  doAdjust(stocktakeState.editingId, true);
}
// API-END: STOCKTAKE_ADJUST

function doAdjust(id, inDrawer) {
  if (!id) return;
  API.post("/stocktakes/" + id + "/adjust")
    .then(function (o) {
      toast("库存调整完成");
      if (inDrawer) fillDrawer(o, true);
      loadList(stocktakeState.page);
    })
    .catch(function (e) { toast(e.message, "error"); });
}

document.addEventListener("DOMContentLoaded", initStocktake);
