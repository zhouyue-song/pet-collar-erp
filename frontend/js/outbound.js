/* ============================================================
 * outbound.js — 生产领料出库页逻辑
 * ------------------------------------------------------------
 * 业务流程：选择产品+生产数量 → 按 BOM 自动生成物料需求（预览）
 *   → 保存草稿（后端按 BOM 正式生成明细）
 *   → 提交审核（后端检查 available_quantity >= outbound_quantity，
 *      库存不足返回 400 + {available, required}）
 *   → 确认出库（事务内扣减库存 + 生成 OUT 流水）
 * 需求数量 = BOM单位用量 × 生产数量（后端为准，前端预览算法与之一致）
 * ============================================================ */

var outboundState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
  products: [],        // BOM 产品列表
  inventoryMap: {},    // material_id -> {warehouse: {available, location}}
  editingId: null,     // null=新建(预览模式)
  status: "",
};

/* ---------------- 页面初始化 ---------------- */
function initOutbound() {
  initPage();
  loadProducts();
  loadInventoryMap();
  loadList(1);

  document.getElementById("btnNewOutbound").addEventListener("click", openCreateDrawer);
  document.getElementById("btnObSearch").addEventListener("click", function () {
    outboundState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnObReset").addEventListener("click", resetFilters);
  document.getElementById("btnObDrawerClose").addEventListener("click", function () {
    closeDrawer("outboundDrawerMask");
  });
  document.getElementById("btnObCancel").addEventListener("click", function () {
    closeDrawer("outboundDrawerMask");
  });
  document.getElementById("obProduct").addEventListener("change", regeneratePreview);
  document.getElementById("obQuantity").addEventListener("input", regeneratePreview);
  document.getElementById("btnObRegenerate").addEventListener("click", regeneratePreview);
  document.getElementById("btnObSave").addEventListener("click", saveOrder);
  document.getElementById("btnObSubmit").addEventListener("click", submitOrder);
  document.getElementById("btnObConfirm").addEventListener("click", confirmOrder);
}

function collectFilters() {
  return {
    outbound_no: document.getElementById("fObNo").value.trim(),
    production_order_no: document.getElementById("fObPoNo").value.trim(),
    product_code: document.getElementById("fObProduct").value,
    outbound_date: document.getElementById("fObDate").value,
    department: document.getElementById("fObDepartment").value.trim(),
    status: document.getElementById("fObStatus").value,
  };
}

function resetFilters() {
  ["fObNo", "fObPoNo", "fObDepartment", "fObDate"].forEach(function (id) {
    document.getElementById(id).value = "";
  });
  document.getElementById("fObProduct").value = "";
  document.getElementById("fObStatus").value = "";
  outboundState.filters = {};
  loadList(1);
}

/* ======================================================
 * API: BOM 产品列表（筛选栏 + 抽屉产品下拉）
 * Method: GET    URL: /api/v1/bom
 * Backend: backend/routes/bom.py -> backend/services/bom_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_BOM_LIST
function loadProducts() {
  API.get("/bom")
    .then(function (d) {
      outboundState.products = d.items || [];
      var opts = '<option value="">-- 请选择产品 --</option>';
      outboundState.products.forEach(function (p) {
        opts += '<option value="' + escapeHtml(p.product_code) + '">' +
          escapeHtml(p.product_code + " " + p.product_name) + "</option>";
      });
      document.getElementById("obProduct").innerHTML = opts;
      // 筛选栏产品下拉（不含半成品 has_parent 的也允许，全部列出）
      var fOpts = '<option value="">全部产品</option>';
      outboundState.products.forEach(function (p) {
        fOpts += '<option value="' + escapeHtml(p.product_code) + '">' +
          escapeHtml(p.product_code + " " + p.product_name) + "</option>";
      });
      document.getElementById("fObProduct").innerHTML = fOpts;
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: OUTBOUND_BOM_LIST

/* ======================================================
 * API: 库存列表（计算各物料可用库存，明细行预警展示用）
 * Method: GET    URL: /api/v1/inventory?page_size=500
 * Backend: backend/routes/inventory.py -> backend/services/inventory_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_INVENTORY_MAP
function loadInventoryMap() {
  API.get("/inventory", { page_size: 500 })
    .then(function (d) {
      var map = {};
      (d.items || []).forEach(function (row) {
        var key = row.material_id;
        if (!map[key]) map[key] = {};
        if (!map[key][row.warehouse]) map[key][row.warehouse] = { available: 0, location: row.location };
        map[key][row.warehouse].available += row.available_quantity || 0;
      });
      outboundState.inventoryMap = map;
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: OUTBOUND_INVENTORY_MAP

/* ======================================================
 * API: 出库单列表（筛选 + 分页）
 * Method: GET    URL: /api/v1/outbound
 * Backend: backend/routes/outbound.py -> backend/services/outbound_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_LIST
function loadList(page) {
  outboundState.page = page || outboundState.page;
  var params = Object.assign({}, outboundState.filters, {
    page: outboundState.page,
    page_size: outboundState.pageSize,
  });
  API.get("/outbound", params)
    .then(function (d) {
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: OUTBOUND_LIST

function renderList(d) {
  var tbody = document.getElementById("outboundTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(11, "暂无出库单，点击右上角「新建领料单」开始");
    renderPagination(document.getElementById("outboundPagination"), d, null);
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
        actions += '<button class="btn btn-text btn-sm" data-act="confirm" data-id="' + o.id + '">确认出库</button>';
      }
      return (
        "<tr>" +
        "<td>" + escapeHtml(o.outbound_no) + "</td>" +
        "<td>" + escapeHtml(o.production_order_no) + "</td>" +
        "<td>" + escapeHtml(o.product_code + " " + o.product_name) + "</td>" +
        '<td class="num">' + fmtQty(o.production_quantity) + "</td>" +
        "<td>" + escapeHtml(o.department) + "</td>" +
        "<td>" + escapeHtml(o.warehouse) + "</td>" +
        "<td>" + escapeHtml(o.outbound_date) + "</td>" +
        '<td class="num">' + fmtQty(o.total_quantity) + "</td>" +
        "<td>" + statusBadge(o.status, ORDER_STATUS_BADGES) + "</td>" +
        "<td>" + escapeHtml(o.operator) + "</td>" +
        '<td class="table-actions">' + actions + "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("outboundPagination"), d, loadList);

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

/* ---------------- 抽屉：新建（BOM 预览） ---------------- */
function openCreateDrawer() {
  outboundState.editingId = null;
  outboundState.status = "";
  document.getElementById("outboundDrawerTitle").textContent = "新建领料出库单";
  document.getElementById("obNo").value = "";
  document.getElementById("obPoNo").value = "";
  document.getElementById("obProduct").value = "";
  document.getElementById("obQuantity").value = "50";
  document.getElementById("obDepartment").value = "一车间";
  document.getElementById("obWarehouse").value = "原材料仓";
  document.getElementById("obDate").value = todayStr();
  document.getElementById("obOperator").value = "李娜";
  document.getElementById("obRemark").value = "";
  document.getElementById("obItemsBody").innerHTML =
    '<tr><td class="table-empty" colspan="8"><i class="fa-regular fa-hand-point-up"></i>请先选择产品与生产数量，系统按 BOM 自动生成物料需求</td></tr>';
  document.getElementById("obTotalRequired").textContent = "0";
  document.getElementById("obTotalOutbound").textContent = "0";
  setDrawerEditable(true);
  setDrawerButtons("");
  document.getElementById("btnObRegenerate").style.display = "";
  openDrawer("outboundDrawerMask");
}

/* ======================================================
 * API: 树形 BOM（前端展平为物料需求预览，与后端算法一致）
 * Method: GET    URL: /api/v1/bom/{product_code}
 * Backend: backend/routes/bom.py -> backend/services/bom_service.py
 * 二次开发说明：预览仅用于交互体验；正式需求数量以后端
 *              flatten_product 生成结果为准（保存草稿后回显）。
 * ====================================================== */
// API-BEGIN: OUTBOUND_BOM_PREVIEW
function regeneratePreview() {
  var code = document.getElementById("obProduct").value;
  if (!code) {
    document.getElementById("obItemsBody").innerHTML =
      '<tr><td class="table-empty" colspan="8"><i class="fa-regular fa-hand-point-up"></i>请先选择产品</td></tr>';
    updateObTotals();
    return;
  }
  API.get("/bom/" + code)
    .then(function (d) {
      var leaves = flattenBomTree(d.tree); // 公共展平算法见 common.js
      renderPreviewRows(leaves);
    })
    .catch(function (e) {
      document.getElementById("obItemsBody").innerHTML =
        '<tr><td class="table-empty" colspan="8"><i class="fa-solid fa-triangle-exclamation"></i>' +
        escapeHtml(e.message) + "</td></tr>";
      updateObTotals();
    });
}
// API-END: OUTBOUND_BOM_PREVIEW

/** 预览明细行（未保存，需求数量 = BOM用量 × 生产数量） */
function renderPreviewRows(leaves) {
  var tbody = document.getElementById("obItemsBody");
  var qty = Number(document.getElementById("obQuantity").value) || 0;
  var warehouse = document.getElementById("obWarehouse").value;
  if (!leaves.length) {
    tbody.innerHTML =
      '<tr><td class="table-empty" colspan="8"><i class="fa-solid fa-triangle-exclamation"></i>该产品 BOM 展开失败</td></tr>';
    updateObTotals();
    return;
  }
  tbody.innerHTML = leaves
    .map(function (leaf, i) {
      var required = Math.round(leaf.usage * qty * 10000) / 10000;
      var inv = (outboundState.inventoryMap[leaf.code] || {})[warehouse];
      var available = inv ? inv.available : 0;
      var low = available < required;
      return (
        '<tr data-code="' + escapeHtml(leaf.code) + '">' +
        "<td>" + escapeHtml(leaf.code) + "</td>" +
        "<td>" + escapeHtml(leaf.name) + "</td>" +
        "<td>" + escapeHtml(leaf.unit) + "</td>" +
        '<td class="num">' + fmtQty(leaf.usage) + "</td>" +
        '<td class="num text-bold">' + fmtQty(required) + "</td>" +
        '<td><input class="form-input num-input" data-f="outbound_quantity" type="number" min="0" step="1" value="' + required + '"></td>' +
        '<td class="num ' + (low ? "text-danger text-bold" : "text-success") + '">' + fmtQty(available) + "</td>" +
        '<td><input class="form-input" data-f="location" type="text" style="width:100px;" value="' +
        escapeHtml((inv && inv.location) || "") + '"></td>' +
        "</tr>"
      );
    })
    .join("");
  tbody.querySelectorAll('input[data-f="outbound_quantity"]').forEach(function (inp) {
    inp.addEventListener("input", updateObTotals);
  });
  updateObTotals();
}

function updateObTotals() {
  var reqTotal = 0;
  var outTotal = 0;
  document.querySelectorAll("#obItemsBody tr[data-code]").forEach(function (tr) {
    var reqTxt = tr.querySelectorAll("td.num")[1]; // td.num 依次为 BOM用量/需求数量/可用库存
    if (reqTxt) reqTotal += Number(reqTxt.textContent) || 0;
    var inp = tr.querySelector('input[data-f="outbound_quantity"]');
    if (inp) outTotal += Number(inp.value) || 0;
  });
  document.getElementById("obTotalRequired").textContent = fmtQty(reqTotal);
  document.getElementById("obTotalOutbound").textContent = fmtQty(outTotal);
}

/* ======================================================
 * API: 出库单详情（含明细 + 每项当前可用库存）
 * Method: GET    URL: /api/v1/outbound/{id}
 * Backend: backend/routes/outbound.py -> backend/services/outbound_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_DETAIL
function openEditDrawer(id, readonly) {
  API.get("/outbound/" + id)
    .then(function (o) {
      fillDrawer(o, readonly);
      openDrawer("outboundDrawerMask");
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: OUTBOUND_DETAIL

function fillDrawer(o, readonly) {
  outboundState.editingId = o.id;
  outboundState.status = o.status;
  document.getElementById("outboundDrawerTitle").textContent =
    "领料出库单 " + o.outbound_no + "（" + o.status_label + "）";
  document.getElementById("obNo").value = o.outbound_no;
  document.getElementById("obPoNo").value = o.production_order_no;
  document.getElementById("obProduct").value = o.product_code;
  document.getElementById("obQuantity").value = o.production_quantity;
  document.getElementById("obDepartment").value = o.department;
  document.getElementById("obWarehouse").value = o.warehouse;
  document.getElementById("obDate").value = o.outbound_date;
  document.getElementById("obOperator").value = o.operator;
  document.getElementById("obRemark").value = o.remark;

  var tbody = document.getElementById("obItemsBody");
  tbody.innerHTML = "";
  (o.items || []).forEach(function (it) {
    var low = (it.available_quantity || 0) < (it.outbound_quantity || 0);
    var tr = document.createElement("tr");
    tr.dataset.itemId = it.id;
    tr.dataset.code = it.material_code;
    tr.innerHTML =
      "<td>" + escapeHtml(it.material_code) + "</td>" +
      "<td>" + escapeHtml(it.material_name) + "</td>" +
      "<td>" + escapeHtml(it.unit) + "</td>" +
      '<td class="num">' + fmtQty(it.bom_quantity) + "</td>" +
      '<td class="num text-bold">' + fmtQty(it.required_quantity) + "</td>" +
      '<td><input class="form-input num-input" data-f="outbound_quantity" type="number" min="0" step="1" value="' + (it.outbound_quantity || 0) + '"' +
      (readonly || o.status !== "DRAFT" ? " disabled" : "") + "></td>" +
      '<td class="num ' + (low ? "text-danger text-bold" : "text-success") + '">' + fmtQty(it.available_quantity || 0) + "</td>" +
      '<td><input class="form-input" data-f="location" type="text" style="width:100px;" value="' + escapeHtml(it.location || "") + '"' +
      (readonly || o.status !== "DRAFT" ? " disabled" : "") + "></td>";
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('input[data-f="outbound_quantity"]').forEach(function (inp) {
    inp.addEventListener("input", updateObTotals);
  });
  updateObTotals();

  setDrawerEditable(!readonly && o.status === "DRAFT");
  setDrawerButtons(o.status);
  document.getElementById("btnObRegenerate").style.display = "none"; // 已保存：明细以后端为准
}

function setDrawerEditable(editable) {
  // 产品与生产数量仅在新建（未保存）时可选；已保存后需求数量以后端为准不可重算
  document.getElementById("obPoNo").disabled = !editable;
  document.getElementById("obProduct").disabled = !editable;
  document.getElementById("obQuantity").disabled = !editable;
  document.getElementById("obDepartment").disabled = !editable;
  document.getElementById("obWarehouse").disabled = !editable;
  document.getElementById("obDate").disabled = !editable;
  document.getElementById("obOperator").disabled = !editable;
  document.getElementById("obRemark").disabled = !editable;
}

function setDrawerButtons(status) {
  var isDraft = status === "DRAFT" || status === "";
  document.getElementById("btnObSave").style.display = isDraft ? "" : "none";
  document.getElementById("btnObSubmit").style.display = status === "DRAFT" ? "" : "none";
  document.getElementById("btnObConfirm").style.display = status === "PENDING" ? "" : "none";
}

/* ======================================================
 * API: 创建出库单（后端按 BOM 自动生成物料需求，DRAFT）
 * Method: POST   URL: /api/v1/outbound
 * 请求体: {production_order_no, product_code, production_quantity,
 *          department, warehouse, outbound_date, operator, remark}
 * Backend: backend/routes/outbound.py -> backend/services/outbound_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_SAVE
function saveOrder() {
  var poNo = document.getElementById("obPoNo").value.trim();
  var productCode = document.getElementById("obProduct").value;
  var quantity = Number(document.getElementById("obQuantity").value) || 0;
  var warehouse = document.getElementById("obWarehouse").value;
  var date = document.getElementById("obDate").value;

  if (!poNo) return toast("请填写生产工单号", "warning");
  if (!productCode) return toast("请选择产品（BOM）", "warning");
  if (quantity <= 0) return toast("生产数量必须大于 0", "warning");
  if (!warehouse) return toast("请选择领料仓库", "warning");
  if (!date) return toast("请选择出库日期", "warning");

  if (outboundState.editingId) {
    // 已保存草稿：只提交可编辑字段（本次出库数量/库位 + 主表字段）
    var items = [];
    document.querySelectorAll("#obItemsBody tr[data-item-id]").forEach(function (tr) {
      items.push({
        id: Number(tr.dataset.itemId),
        outbound_quantity: Number(tr.querySelector('input[data-f="outbound_quantity"]').value) || 0,
        location: tr.querySelector('input[data-f="location"]').value.trim(),
      });
    });
    var payload = {
      department: document.getElementById("obDepartment").value.trim(),
      operator: document.getElementById("obOperator").value.trim(),
      remark: document.getElementById("obRemark").value.trim(),
      outbound_date: date,
      items: items,
    };
    API.put("/outbound/" + outboundState.editingId, payload)
      .then(function (o) {
        toast("保存成功");
        fillDrawer(o, false);
        loadList(outboundState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  } else {
    var data = {
      production_order_no: poNo,
      product_code: productCode,
      production_quantity: quantity,
      department: document.getElementById("obDepartment").value.trim(),
      warehouse: warehouse,
      outbound_date: date,
      operator: document.getElementById("obOperator").value.trim(),
      remark: document.getElementById("obRemark").value.trim(),
    };
    API.post("/outbound", data)
      .then(function (o) {
        toast("出库单创建成功：" + o.outbound_no + "，已按 BOM 生成物料需求");
        fillDrawer(o, false);
        loadList(outboundState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  }
}
// API-END: OUTBOUND_SAVE

/* ======================================================
 * API: 提交审核（DRAFT → PENDING，提交前检查库存；
 *      库存不足返回 400 + data{available, required}）
 * Method: POST   URL: /api/v1/outbound/{id}/submit
 * Backend: backend/routes/outbound.py -> backend/services/outbound_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_SUBMIT
function submitOrder() {
  doSubmit(outboundState.editingId, true);
}
// API-END: OUTBOUND_SUBMIT

function doSubmit(id, inDrawer) {
  if (!id) return toast("请先保存草稿", "warning");
  API.post("/outbound/" + id + "/submit")
    .then(function (o) {
      toast("提交审核成功");
      if (inDrawer) fillDrawer(o, false);
      loadList(outboundState.page);
    })
    .catch(function (e) {
      // 库存不足：附带 available/required 数据，给出更明确的提示
      var msg = e.message;
      if (e.data && typeof e.data.available === "number") {
        msg += "（可用 " + fmtQty(e.data.available) + "，需要 " + fmtQty(e.data.required) + "）";
      }
      toast(msg, "error");
    });
}

/* ======================================================
 * API: 确认出库（PENDING → COMPLETED）
 * 事务内：库存校验 → 扣减库存 → 生成 OUT 流水，失败整体回滚
 * Method: POST   URL: /api/v1/outbound/{id}/confirm
 * Backend: backend/routes/outbound.py -> backend/services/outbound_service.py
 * ====================================================== */
// API-BEGIN: OUTBOUND_CONFIRM
function confirmOrder() {
  if (!confirmAction("确认出库后库存将扣减并生成流水，且不可撤销，是否继续？")) return;
  doConfirm(outboundState.editingId, true);
}
// API-END: OUTBOUND_CONFIRM

function doConfirm(id, inDrawer) {
  if (!id) return;
  API.post("/outbound/" + id + "/confirm")
    .then(function (o) {
      toast("出库成功，库存已扣减");
      if (inDrawer) fillDrawer(o, true);
      loadInventoryMap(); // 刷新可用库存缓存
      loadList(outboundState.page);
    })
    .catch(function (e) {
      var msg = e.message;
      if (e.data && typeof e.data.available === "number") {
        msg += "（可用 " + fmtQty(e.data.available) + "，需要 " + fmtQty(e.data.required) + "）";
      }
      toast(msg, "error");
    });
}

document.addEventListener("DOMContentLoaded", initOutbound);
