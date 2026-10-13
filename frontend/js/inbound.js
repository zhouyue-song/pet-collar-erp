/* ============================================================
 * inbound.js — 采购入库管理页逻辑
 * ------------------------------------------------------------
 * 业务流程：新建(草稿) → 保存草稿 → 提交审核 → 确认入库
 * 业务规则（后端保证）：
 *   创建/保存/提交 都不修改库存；
 *   只有「确认入库」才真正增加库存并生成入库流水（事务内完成）。
 * ============================================================ */

var inboundState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
  materials: [],   // 物料档案（明细行下拉选择用）
  editingId: null, // 当前抽屉中的单据 id（null=新建）
  status: "",      // 当前单据状态
};

/* ---------------- 页面初始化 ---------------- */
function initInbound() {
  initPage();
  loadMaterials();
  loadList(1);

  document.getElementById("btnNewInbound").addEventListener("click", function () {
    openCreateDrawer();
  });
  document.getElementById("btnIbSearch").addEventListener("click", function () {
    inboundState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnIbReset").addEventListener("click", resetFilters);
  document.getElementById("btnIbDrawerClose").addEventListener("click", function () {
    closeDrawer("inboundDrawerMask");
  });
  document.getElementById("btnIbCancel").addEventListener("click", function () {
    closeDrawer("inboundDrawerMask");
  });
  document.getElementById("btnIbAddRow").addEventListener("click", addItemRow);
  document.getElementById("btnIbSave").addEventListener("click", saveOrder);
  document.getElementById("btnIbSubmit").addEventListener("click", submitOrder);
  document.getElementById("btnIbConfirm").addEventListener("click", confirmOrder);
}

function collectFilters() {
  return {
    inbound_no: document.getElementById("fIbNo").value.trim(),
    purchase_order_no: document.getElementById("fIbPoNo").value.trim(),
    supplier: document.getElementById("fIbSupplier").value.trim(),
    warehouse: document.getElementById("fIbWarehouse").value,
    inbound_date: document.getElementById("fIbDate").value,
    status: document.getElementById("fIbStatus").value,
  };
}

function resetFilters() {
  ["fIbNo", "fIbPoNo", "fIbSupplier", "fIbDate"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
  document.getElementById("fIbWarehouse").value = "";
  document.getElementById("fIbStatus").value = "";
  inboundState.filters = {};
  loadList(1);
}

/* ======================================================
 * API: 物料档案（明细行下拉选择用，全量启用物料）
 * Method: GET    URL: /api/v1/materials?status=active&page_size=500
 * Backend: backend/routes/materials.py -> backend/services/material_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_MATERIALS
function loadMaterials() {
  API.get("/materials", { status: "active", page_size: 500 })
    .then(function (d) {
      inboundState.materials = d.items || [];
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: INBOUND_MATERIALS

/* ======================================================
 * API: 入库单列表（筛选 + 分页）
 * Method: GET    URL: /api/v1/inbound
 * Backend: backend/routes/inbound.py -> backend/services/inbound_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_LIST
function loadList(page) {
  inboundState.page = page || inboundState.page;
  var params = Object.assign({}, inboundState.filters, {
    page: inboundState.page,
    page_size: inboundState.pageSize,
  });
  API.get("/inbound", params)
    .then(function (d) {
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: INBOUND_LIST

function renderList(d) {
  var tbody = document.getElementById("inboundTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(11, "暂无入库单，点击右上角「新建入库单」开始");
    renderPagination(document.getElementById("inboundPagination"), d, null);
    return;
  }
  tbody.innerHTML = items
    .map(function (o) {
      var actions = '<button class="btn btn-text btn-sm" data-act="view" data-id="' + o.id + '">查看</button>';
      if (o.status === "DRAFT") {
        actions +=
          '<button class="btn btn-text btn-sm" data-act="edit" data-id="' + o.id + '">编辑</button>' +
          '<button class="btn btn-text btn-sm" data-act="submit" data-id="' + o.id + '">提交审核</button>';
      }
      if (o.status === "PENDING") {
        actions += '<button class="btn btn-text btn-sm" data-act="confirm" data-id="' + o.id + '">确认入库</button>';
      }
      return (
        "<tr>" +
        "<td>" + escapeHtml(o.inbound_no) + "</td>" +
        "<td>" + escapeHtml(o.purchase_order_no) + "</td>" +
        "<td>" + escapeHtml(o.supplier) + "</td>" +
        "<td>" + escapeHtml(o.warehouse) + "</td>" +
        "<td>" + escapeHtml(o.inbound_date) + "</td>" +
        '<td class="num">' + o.item_count + "</td>" +
        '<td class="num">' + fmtQty(o.total_quantity) + "</td>" +
        '<td class="num">' + fmtMoney(o.total_amount) + "</td>" +
        "<td>" + statusBadge(o.status, ORDER_STATUS_BADGES) + "</td>" +
        "<td>" + escapeHtml(o.operator) + "</td>" +
        '<td class="table-actions">' + actions + "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("inboundPagination"), d, loadList);

  tbody.querySelectorAll("button[data-act]").forEach(function (b) {
    b.addEventListener("click", function () {
      var id = Number(b.dataset.id);
      var act = b.dataset.act;
      if (act === "view" || act === "edit") {
        openEditDrawer(id, act === "view");
      } else if (act === "submit") {
        doSubmit(id, false);
      } else if (act === "confirm") {
        doConfirm(id, false);
      }
    });
  });
}

/* ---------------- 抽屉：新建 / 编辑 ---------------- */
function openCreateDrawer() {
  inboundState.editingId = null;
  inboundState.status = "";
  document.getElementById("inboundDrawerTitle").textContent = "新建入库单";
  document.getElementById("ibNo").value = "";
  document.getElementById("ibPoNo").value = "";
  document.getElementById("ibSupplier").value = "";
  document.getElementById("ibWarehouse").value = "原材料仓";
  document.getElementById("ibDate").value = todayStr();
  document.getElementById("ibOperator").value = "张伟";
  document.getElementById("ibRemark").value = "";
  document.getElementById("ibItemsBody").innerHTML = "";
  addItemRow();
  updateTotalAmount();
  setDrawerEditable(true);
  setDrawerButtons("");
  openDrawer("inboundDrawerMask");
}

/* ======================================================
 * API: 入库单详情（含明细）
 * Method: GET    URL: /api/v1/inbound/{id}
 * Backend: backend/routes/inbound.py -> backend/services/inbound_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_DETAIL
function openEditDrawer(id, readonly) {
  API.get("/inbound/" + id)
    .then(function (o) {
      fillDrawer(o, readonly);
      openDrawer("inboundDrawerMask");
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: INBOUND_DETAIL

function fillDrawer(o, readonly) {
  inboundState.editingId = o.id;
  inboundState.status = o.status;
  document.getElementById("inboundDrawerTitle").textContent =
    "入库单 " + o.inbound_no + "（" + o.status_label + "）";
  document.getElementById("ibNo").value = o.inbound_no;
  document.getElementById("ibPoNo").value = o.purchase_order_no;
  document.getElementById("ibSupplier").value = o.supplier;
  document.getElementById("ibWarehouse").value = o.warehouse;
  document.getElementById("ibDate").value = o.inbound_date;
  document.getElementById("ibOperator").value = o.operator;
  document.getElementById("ibRemark").value = o.remark;

  var tbody = document.getElementById("ibItemsBody");
  tbody.innerHTML = "";
  (o.items || []).forEach(function (it) {
    appendItemRow(it, readonly);
  });
  updateTotalAmount();
  setDrawerEditable(!readonly && o.status === "DRAFT");
  setDrawerButtons(o.status);
}

/** 明细行（下拉选物料自动带出名称/单位） */
function appendItemRow(it, readonly) {
  it = it || {};
  var tr = document.createElement("tr");
  tr.dataset.itemId = it.id || "";
  var materialOptions = '<option value="">-- 选择物料 --</option>';
  inboundState.materials.forEach(function (m) {
    var sel = it.material_id === m.id ? " selected" : "";
    materialOptions += '<option value="' + m.id + '"' + sel + ">" + escapeHtml(m.material_code + " " + m.material_name) + "</option>";
  });
  tr.innerHTML =
    "<td>" +
    (readonly
      ? escapeHtml(it.material_code || "")
      : '<select class="form-select" data-f="material_id" style="width:170px;">' + materialOptions + "</select>") +
    "</td>" +
    '<td data-f="material_name" class="text-secondary">' + escapeHtml(it.material_name || "") + "</td>" +
    '<td data-f="unit" class="text-secondary">' + escapeHtml(it.unit || "") + "</td>" +
    '<td><input class="form-input num-input" data-f="purchase_quantity" type="number" min="0" step="1" value="' + (it.purchase_quantity || 0) + '"' + (readonly ? " disabled" : "") + '></td>' +
    '<td class="text-secondary text-right">' + fmtQty(it.received_quantity || 0) + "</td>" +
    '<td><input class="form-input num-input" data-f="inbound_quantity" type="number" min="0" step="1" value="' + (it.inbound_quantity || 0) + '"' + (readonly ? " disabled" : "") + '></td>' +
    '<td><input class="form-input num-input" data-f="unit_price" type="number" min="0" step="0.01" value="' + (it.unit_price || 0) + '"' + (readonly ? " disabled" : "") + '></td>' +
    '<td class="num" data-f="amount">' + fmtMoney(it.amount || 0) + "</td>" +
    '<td><input class="form-input" data-f="location" type="text" style="width:100px;" value="' + escapeHtml(it.location || "") + '"' + (readonly ? " disabled" : "") + '></td>' +
    "<td>" +
    (readonly
      ? ""
      : '<button class="btn btn-text btn-sm btn-row-del"><i class="fa-solid fa-trash-can"></i></button>') +
    "</td>";

  if (!readonly) {
    // 选择物料：自动带出名称/单位/默认库位
    var sel = tr.querySelector('select[data-f="material_id"]');
    sel.addEventListener("change", function () {
      var m = inboundState.materials.find(function (x) { return x.id === Number(sel.value); });
      if (m) {
        tr.querySelector('[data-f="material_name"]').textContent = m.material_name;
        tr.querySelector('[data-f="unit"]').textContent = m.unit;
        tr.querySelector('[data-f="location"]').value = "";
      } else {
        tr.querySelector('[data-f="material_name"]').textContent = "";
        tr.querySelector('[data-f="unit"]').textContent = "";
      }
      recalcRow(tr);
    });
    // 数量/单价变化：重算金额
    tr.querySelectorAll('input[data-f="inbound_quantity"], input[data-f="unit_price"]').forEach(function (inp) {
      inp.addEventListener("input", function () { recalcRow(tr); });
    });
    tr.querySelector(".btn-row-del").addEventListener("click", function () {
      tr.remove();
      updateTotalAmount();
    });
  }
  document.getElementById("ibItemsBody").appendChild(tr);
}

function addItemRow() {
  appendItemRow({});
}

function recalcRow(tr) {
  var qty = Number(tr.querySelector('input[data-f="inbound_quantity"]').value) || 0;
  var price = Number(tr.querySelector('input[data-f="unit_price"]').value) || 0;
  tr.querySelector('[data-f="amount"]').textContent = fmtMoney(qty * price);
  updateTotalAmount();
}

function updateTotalAmount() {
  var rows = document.querySelectorAll("#ibItemsBody tr");
  var total = 0;
  rows.forEach(function (tr) {
    var txt = tr.querySelector('[data-f="amount"]');
    if (txt) total += Number(txt.textContent) || 0;
  });
  document.getElementById("ibTotalAmount").textContent = fmtMoney(total);
}

/** 收集抽屉表单 → 请求体 */
function collectDrawerData() {
  var items = [];
  document.querySelectorAll("#ibItemsBody tr").forEach(function (tr) {
    var sel = tr.querySelector('select[data-f="material_id"]');
    var materialId = sel ? Number(sel.value) : null;
    if (!materialId) return; // 未选物料的空行跳过
    items.push({
      id: tr.dataset.itemId ? Number(tr.dataset.itemId) : undefined,
      material_id: materialId,
      purchase_quantity: Number(tr.querySelector('input[data-f="purchase_quantity"]').value) || 0,
      inbound_quantity: Number(tr.querySelector('input[data-f="inbound_quantity"]').value) || 0,
      unit_price: Number(tr.querySelector('input[data-f="unit_price"]').value) || 0,
      location: tr.querySelector('input[data-f="location"]').value.trim(),
    });
  });
  return {
    purchase_order_no: document.getElementById("ibPoNo").value.trim(),
    supplier: document.getElementById("ibSupplier").value.trim(),
    warehouse: document.getElementById("ibWarehouse").value,
    inbound_date: document.getElementById("ibDate").value,
    operator: document.getElementById("ibOperator").value.trim(),
    remark: document.getElementById("ibRemark").value.trim(),
    items: items,
  };
}

/** 抽屉可编辑性 + 底部按钮按状态显隐 */
function setDrawerEditable(editable) {
  document.getElementById("ibPoNo").disabled = !editable;
  document.getElementById("ibSupplier").disabled = !editable;
  document.getElementById("ibWarehouse").disabled = !editable;
  document.getElementById("ibDate").disabled = !editable;
  document.getElementById("ibOperator").disabled = !editable;
  document.getElementById("ibRemark").disabled = !editable;
  document.getElementById("btnIbAddRow").style.display = editable ? "" : "none";
}

function setDrawerButtons(status) {
  var isDraft = status === "DRAFT" || status === "";
  document.getElementById("btnIbSave").style.display = isDraft ? "" : "none";
  document.getElementById("btnIbSubmit").style.display = status === "DRAFT" ? "" : "none";
  document.getElementById("btnIbConfirm").style.display = status === "PENDING" ? "" : "none";
}

/* ======================================================
 * API: 创建 / 保存草稿（均不修改库存）
 * Method: POST   URL: /api/v1/inbound           （新建）
 * Method: PUT    URL: /api/v1/inbound/{id}      （草稿保存）
 * Backend: backend/routes/inbound.py -> backend/services/inbound_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_SAVE
function saveOrder() {
  var data = collectDrawerData();
  if (!data.supplier) return toast("请填写供应商", "warning");
  if (!data.inbound_date) return toast("请选择入库日期", "warning");
  if (!data.items.length) return toast("请至少添加一条入库明细并选择物料", "warning");

  if (inboundState.editingId) {
    API.put("/inbound/" + inboundState.editingId, data)
      .then(function (o) {
        toast("保存成功");
        fillDrawer(o, false);
        loadList(inboundState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  } else {
    API.post("/inbound", data)
      .then(function (o) {
        toast("入库单创建成功：" + o.inbound_no);
        fillDrawer(o, false);
        loadList(inboundState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  }
}
// API-END: INBOUND_SAVE

/* ======================================================
 * API: 提交审核（DRAFT → PENDING，不修改库存）
 * Method: POST   URL: /api/v1/inbound/{id}/submit
 * Backend: backend/routes/inbound.py -> backend/services/inbound_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_SUBMIT
function submitOrder() {
  doSubmit(inboundState.editingId, true);
}
// API-END: INBOUND_SUBMIT

function doSubmit(id, inDrawer) {
  if (!id) return toast("请先保存草稿", "warning");
  API.post("/inbound/" + id + "/submit")
    .then(function (o) {
      toast("提交审核成功");
      if (inDrawer) fillDrawer(o, false);
      loadList(inboundState.page);
    })
    .catch(function (e) { toast(e.message, "error"); });
}

/* ======================================================
 * API: 确认入库（PENDING → COMPLETED）
 * 事务内：更新库存 + 生成 IN 流水 + 单据完成，失败整体回滚
 * Method: POST   URL: /api/v1/inbound/{id}/confirm
 * Backend: backend/routes/inbound.py -> backend/services/inbound_service.py
 * ====================================================== */
// API-BEGIN: INBOUND_CONFIRM
function confirmOrder() {
  if (!confirmAction("确认入库后库存将增加并生成流水，且不可撤销，是否继续？")) return;
  doConfirm(inboundState.editingId, true);
}
// API-END: INBOUND_CONFIRM

function doConfirm(id, inDrawer) {
  if (!id) return;
  API.post("/inbound/" + id + "/confirm")
    .then(function (o) {
      toast("入库成功，库存已增加");
      if (inDrawer) {
        fillDrawer(o, true);
      }
      loadList(inboundState.page);
    })
    .catch(function (e) { toast(e.message, "error"); });
}

document.addEventListener("DOMContentLoaded", initInbound);
