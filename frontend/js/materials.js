/* ============================================================
 * materials.js — 物料档案页逻辑（含 ABC 分类）
 * ------------------------------------------------------------
 * 支持：列表筛选 / 分页 / 新增 / 编辑 / 删除（被引用时后端拒绝删除）
 * ABC 统计卡片来自列表接口的 abc_summary（A/B/C 各自计数）。
 * ============================================================ */

var materialsState = {
  page: 1,
  pageSize: APP_CONFIG.PAGE_SIZE,
  filters: {},
  abcCard: "", // ABC 卡片当前选择（与下拉联动）
  editingId: null,
};

/* ---------------- 页面初始化 ---------------- */
function initMaterials() {
  initPage();
  loadList(1);

  document.getElementById("btnNewMaterial").addEventListener("click", function () {
    openModal(null);
  });
  document.getElementById("btnMtSearch").addEventListener("click", function () {
    materialsState.filters = collectFilters();
    loadList(1);
  });
  document.getElementById("btnMtReset").addEventListener("click", resetFilters);
  document.getElementById("btnMtCancel").addEventListener("click", function () {
    closeModal("materialModalMask");
  });
  document.getElementById("btnMtModalClose").addEventListener("click", function () {
    closeModal("materialModalMask");
  });
  document.getElementById("btnMtSave").addEventListener("click", saveMaterial);

  // ABC 卡片点击 → 切换筛选（与下拉联动）
  document.querySelectorAll(".abc-card[data-abc]").forEach(function (card) {
    card.addEventListener("click", function () {
      materialsState.abcCard = card.dataset.abc;
      document.getElementById("fMtAbc").value = card.dataset.abc;
      syncAbcCards();
      materialsState.filters = collectFilters();
      loadList(1);
    });
  });
}

function collectFilters() {
  return {
    keyword: document.getElementById("fMtKeyword").value.trim(),
    category: document.getElementById("fMtCategory").value,
    abc_class: document.getElementById("fMtAbc").value,
    status: document.getElementById("fMtStatus").value,
  };
}

function resetFilters() {
  document.getElementById("fMtKeyword").value = "";
  document.getElementById("fMtCategory").value = "";
  document.getElementById("fMtAbc").value = "";
  document.getElementById("fMtStatus").value = "";
  materialsState.abcCard = "";
  syncAbcCards();
  materialsState.filters = {};
  loadList(1);
}

function syncAbcCards() {
  document.querySelectorAll(".abc-card[data-abc]").forEach(function (card) {
    card.classList.toggle("active", card.dataset.abc === materialsState.abcCard);
  });
}

/* ======================================================
 * API: 物料列表（筛选 + 分页 + ABC 汇总）
 * Method: GET    URL: /api/v1/materials
 * Backend: backend/routes/materials.py -> backend/services/material_service.py
 * ====================================================== */
// API-BEGIN: MATERIALS_LIST
function loadList(page) {
  materialsState.page = page || materialsState.page;
  var params = Object.assign({}, materialsState.filters, {
    page: materialsState.page,
    page_size: materialsState.pageSize,
  });
  API.get("/materials", params)
    .then(function (d) {
      renderAbcCards(d.abc_summary || {});
      renderList(d);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: MATERIALS_LIST

function renderAbcCards(s) {
  document.getElementById("abcACount").textContent = s.A || 0;
  document.getElementById("abcBCount").textContent = s.B || 0;
  document.getElementById("abcCCount").textContent = s.C || 0;
  document.getElementById("abcAllCount").textContent = (s.A || 0) + (s.B || 0) + (s.C || 0);
}

// ABC_BADGES 等公共徽章映射统一在 common.js 中定义，本页直接使用

function renderList(d) {
  var tbody = document.getElementById("materialsTbody");
  var items = d.items || [];
  if (!items.length) {
    tbody.innerHTML = emptyRow(12, "暂无物料档案，点击右上角「新增物料」创建");
    renderPagination(document.getElementById("materialsPagination"), d, null);
    return;
  }
  tbody.innerHTML = items
    .map(function (m) {
      return (
        "<tr>" +
        "<td>" + escapeHtml(m.material_code) + "</td>" +
        "<td>" + escapeHtml(m.material_name) + "</td>" +
        "<td>" + escapeHtml(m.category) + "</td>" +
        '<td class="text-secondary">' + escapeHtml(m.specification) + "</td>" +
        "<td>" + escapeHtml(m.unit) + "</td>" +
        "<td>" + statusBadge(m.abc_class, ABC_BADGES) + "</td>" +
        "<td>" + escapeHtml(m.material_type) + "</td>" +
        '<td class="num">' + fmtQty(m.safety_stock) + "</td>" +
        '<td class="num">' + m.purchase_lead_time + "</td>" +
        "<td>" + escapeHtml(m.default_warehouse) + "</td>" +
        "<td>" +
        (m.status === "active"
          ? '<span class="badge badge-green">启用</span>'
          : '<span class="badge badge-gray">停用</span>') +
        "</td>" +
        '<td class="table-actions">' +
        '<button class="btn btn-text btn-sm" data-act="edit" data-id="' + m.id + '">编辑</button>' +
        '<button class="btn btn-text btn-sm" data-act="del" data-id="' + m.id + '">删除</button>' +
        "</td>" +
        "</tr>"
      );
    })
    .join("");
  renderPagination(document.getElementById("materialsPagination"), d, loadList);

  tbody.querySelectorAll("button[data-act]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.dataset.act === "edit") {
        openModal(Number(b.dataset.id));
      } else if (b.dataset.act === "del") {
        deleteMaterial(Number(b.dataset.id));
      }
    });
  });
}

/* ---------------- 新增 / 编辑模态框 ---------------- */
function openModal(id) {
  materialsState.editingId = id;
  document.getElementById("materialModalTitle").textContent = id ? "编辑物料" : "新增物料";
  if (!id) {
    ["mtCode", "mtName", "mtSpec"].forEach(function (f) { document.getElementById(f).value = ""; });
    document.getElementById("mtCategory").value = "电子元器件";
    document.getElementById("mtUnit").value = "个";
    document.getElementById("mtAbc").value = "B";
    document.getElementById("mtType").value = "外购件";
    document.getElementById("mtSafety").value = "0";
    document.getElementById("mtLeadTime").value = "7";
    document.getElementById("mtWarehouse").value = "原材料仓";
    document.getElementById("mtStatus").value = "active";
    openModal("materialModalMask");
    return;
  }
  // 编辑：回显当前数据（列表数据已含全部字段）
  API.get("/materials", { page: 1, page_size: 500 })
    .then(function (d) {
      var m = (d.items || []).find(function (x) { return x.id === id; });
      if (!m) return toast("物料不存在", "error");
      document.getElementById("mtCode").value = m.material_code;
      document.getElementById("mtName").value = m.material_name;
      document.getElementById("mtCategory").value = m.category || "电子元器件";
      document.getElementById("mtSpec").value = m.specification || "";
      document.getElementById("mtUnit").value = m.unit || "个";
      document.getElementById("mtAbc").value = m.abc_class || "B";
      document.getElementById("mtType").value = m.material_type || "外购件";
      document.getElementById("mtSafety").value = m.safety_stock;
      document.getElementById("mtLeadTime").value = m.purchase_lead_time;
      document.getElementById("mtWarehouse").value = m.default_warehouse || "原材料仓";
      document.getElementById("mtStatus").value = m.status || "active";
      openModal("materialModalMask");
    })
    .catch(function (e) { toast(e.message, "error"); });
}

/* ======================================================
 * API: 新增 / 修改物料
 * Method: POST   URL: /api/v1/materials          （新增）
 * Method: PUT    URL: /api/v1/materials/{id}     （修改）
 * Backend: backend/routes/materials.py -> backend/services/material_service.py
 * 二次开发说明：金额/编码规则校验由后端统一执行，前端只做必填提示。
 * ====================================================== */
// API-BEGIN: MATERIALS_SAVE
function saveMaterial() {
  var data = {
    material_code: document.getElementById("mtCode").value.trim(),
    material_name: document.getElementById("mtName").value.trim(),
    category: document.getElementById("mtCategory").value,
    specification: document.getElementById("mtSpec").value.trim(),
    unit: document.getElementById("mtUnit").value,
    abc_class: document.getElementById("mtAbc").value,
    material_type: document.getElementById("mtType").value,
    safety_stock: Number(document.getElementById("mtSafety").value) || 0,
    purchase_lead_time: Number(document.getElementById("mtLeadTime").value) || 0,
    default_warehouse: document.getElementById("mtWarehouse").value,
    status: document.getElementById("mtStatus").value,
  };
  if (!data.material_code) return toast("请填写物料编码", "warning");
  if (!data.material_name) return toast("请填写物料名称", "warning");

  if (materialsState.editingId) {
    API.put("/materials/" + materialsState.editingId, data)
      .then(function () {
        toast("物料修改成功");
        closeModal("materialModalMask");
        loadList(materialsState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  } else {
    API.post("/materials", data)
      .then(function () {
        toast("物料新增成功");
        closeModal("materialModalMask");
        loadList(materialsState.page);
      })
      .catch(function (e) { toast(e.message, "error"); });
  }
}
// API-END: MATERIALS_SAVE

/* ======================================================
 * API: 删除物料（被库存/流水/单据/BOM 引用时后端返回 400 拒绝）
 * Method: DELETE URL: /api/v1/materials/{id}
 * Backend: backend/routes/materials.py -> backend/services/material_service.py
 * ====================================================== */
// API-BEGIN: MATERIALS_DELETE
function deleteMaterial(id) {
  if (!confirmAction("确定删除该物料吗？删除后不可恢复。")) return;
  API.delete("/materials/" + id)
    .then(function () {
      toast("物料删除成功");
      loadList(materialsState.page);
    })
    .catch(function (e) { toast(e.message, "error"); });
}
// API-END: MATERIALS_DELETE

document.addEventListener("DOMContentLoaded", initMaterials);
