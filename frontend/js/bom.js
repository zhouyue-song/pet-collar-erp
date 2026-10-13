/* ============================================================
 * bom.js — BOM 产品结构页逻辑
 * ------------------------------------------------------------
 * 左侧：BOM 产品/组件列表；点击后右侧展示树形结构，
 * 底部同步展示单件产品物料汇总（BOM 扁平展开，与后端算法一致）。
 * 树节点类型：product 产品(蓝) / semi 半成品(橙) / material 物料(绿)
 * ============================================================ */

var bomState = {
  products: [],
  currentCode: "",
  materialMap: {}, // material_code -> 物料档案（汇总表补全字段用）
};

/* ---------------- 页面初始化 ---------------- */
function initBom() {
  initPage();
  loadProductList();
  loadMaterials();
}

/* ======================================================
 * API: 物料档案（BOM 汇总表补全规格/类型/ABC/仓库字段用）
 * Method: GET    URL: /api/v1/materials?page_size=500
 * Backend: backend/routes/materials.py -> backend/services/material_service.py
 * ====================================================== */
// API-BEGIN: BOM_MATERIALS
function loadMaterials() {
  API.get("/materials", { page_size: 500 })
    .then(function (d) {
      var map = {};
      (d.items || []).forEach(function (m) {
        map[m.material_code] = m;
      });
      bomState.materialMap = map;
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: BOM_MATERIALS

/* ======================================================
 * API: BOM 产品列表
 * Method: GET    URL: /api/v1/bom
 * Backend: backend/routes/bom.py -> backend/services/bom_service.py
 * ====================================================== */
// API-BEGIN: BOM_LIST
function loadProductList() {
  API.get("/bom")
    .then(function (d) {
      bomState.products = d.items || [];
      renderProductList();
      // 默认选中第一个产品
      if (bomState.products.length && !bomState.currentCode) {
        selectProduct(bomState.products[0].product_code);
      }
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: BOM_LIST

function renderProductList() {
  var box = document.getElementById("bomProductList");
  if (!bomState.products.length) {
    box.innerHTML = '<div class="table-empty"><i class="fa-regular fa-folder-open"></i>暂无 BOM 数据</div>';
    return;
  }
  box.innerHTML = bomState.products
    .map(function (p) {
      var active = p.product_code === bomState.currentCode ? " active" : "";
      return (
        '<div class="bom-product-item' + active + '" data-code="' + escapeHtml(p.product_code) + '">' +
        '<i class="fa-solid ' + (p.has_parent ? "fa-gears text-warning" : "fa-cube text-primary") + '"></i>' +
        "<div>" +
        '<div class="text-bold">' + escapeHtml(p.product_code) + " " + escapeHtml(p.product_name) + "</div>" +
        '<div class="text-muted" style="font-size:12px;">版本 ' + escapeHtml(p.version || "") +
        (p.has_parent ? " · 半成品" : " · 产品") + "</div>" +
        "</div>" +
        "</div>"
      );
    })
    .join("");
  box.querySelectorAll(".bom-product-item").forEach(function (el) {
    el.addEventListener("click", function () {
      selectProduct(el.dataset.code);
    });
  });
}

/* ======================================================
 * API: 树形 BOM（产品 → 半成品 → 物料 多级结构）
 * Method: GET    URL: /api/v1/bom/{product_code}
 * Backend: backend/routes/bom.py -> backend/services/bom_service.py
 * ====================================================== */
// API-BEGIN: BOM_TREE
function selectProduct(code) {
  bomState.currentCode = code;
  renderProductList();
  API.get("/bom/" + code)
    .then(function (d) {
      renderTree(d);
      renderFlatten(d.tree);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: BOM_TREE

var BOM_TYPE_ICONS = {
  product: { icon: "fa-cube", cls: "product" },
  semi: { icon: "fa-gears", cls: "semi" },
  material: { icon: "fa-microchip", cls: "material" },
  unknown: { icon: "fa-question", cls: "material" },
};

var BOM_TYPE_LABELS = { product: "产品", semi: "半成品", material: "物料", unknown: "未知" };

/** 递归渲染树节点（可折叠） */
function renderTree(d) {
  document.getElementById("bomTreeTitle").textContent =
    "BOM 结构树 · " + d.product_code + " " + d.product_name;
  document.getElementById("bomTreeMeta").textContent = "版本 " + (d.version || "-");
  var box = document.getElementById("bomTree");
  box.innerHTML = renderTreeNode(d.tree, 0);
  box.querySelectorAll(".bom-tree-toggle").forEach(function (t) {
    t.addEventListener("click", function () {
      var children = t.closest(".bom-tree-node").querySelector(":scope > .bom-tree-children");
      if (!children) return;
      var open = children.style.display !== "none";
      children.style.display = open ? "none" : "";
      t.innerHTML = open ? '<i class="fa-solid fa-plus"></i>' : '<i class="fa-solid fa-minus"></i>';
    });
  });
}

function renderTreeNode(node, depth) {
  var type = node.type || "unknown";
  var icon = BOM_TYPE_ICONS[type] || BOM_TYPE_ICONS.unknown;
  var hasChildren = node.children && node.children.length;
  var html = '<div class="bom-tree-node">';
  html += '<div class="bom-tree-row">';
  html +=
    '<button class="bom-tree-toggle' + (hasChildren ? "" : " leaf") + '">' +
    (hasChildren ? '<i class="fa-solid fa-minus"></i>' : "") +
    "</button>";
  html += '<span class="bom-tree-icon ' + icon.cls + '"><i class="fa-solid ' + icon.icon + '"></i></span>';
  html +=
    "<span>" + escapeHtml(node.name || node.code) +
    '<span class="bom-node-code">' + escapeHtml(node.code) + "</span></span>";
  html += '<span class="badge badge-gray" style="margin-left:6px;">' + BOM_TYPE_LABELS[type] + "</span>";
  html += '<span class="bom-tree-qty">' + fmtQty(node.quantity) + " " + escapeHtml(node.unit || "") + "</span>";
  html += "</div>";
  if (hasChildren) {
    html += '<div class="bom-tree-children">';
    node.children.forEach(function (c) {
      html += renderTreeNode(c, depth + 1);
    });
    html += "</div>";
  }
  html += "</div>";
  return html;
}

/** 底部：单件产品物料汇总（flattenBomTree 见 common.js，与后端一致；
 *  规格/类型/ABC/仓库由物料档案接口按编码补全） */
function renderFlatten(tree) {
  var leaves = flattenBomTree(tree);
  var tbody = document.getElementById("bomFlattenTbody");
  if (!leaves.length) {
    tbody.innerHTML = emptyRow(9, "该 BOM 没有展开出物料明细");
    return;
  }
  tbody.innerHTML = leaves
    .map(function (leaf, i) {
      var m = bomState.materialMap[leaf.code] || {};
      var abc = m.abc_class ? statusBadge(m.abc_class, ABC_BADGES) : "--";
      return (
        "<tr>" +
        '<td class="num text-secondary">' + (i + 1) + "</td>" +
        "<td>" + escapeHtml(leaf.code) + "</td>" +
        "<td>" + escapeHtml(leaf.name || m.material_name || "") + "</td>" +
        '<td class="text-secondary">' + escapeHtml(m.specification || "--") + "</td>" +
        "<td>" + escapeHtml(leaf.unit) + "</td>" +
        '<td class="num text-bold">' + fmtQty(leaf.usage) + "</td>" +
        "<td>" + escapeHtml(m.material_type || "--") + "</td>" +
        "<td>" + abc + "</td>" +
        "<td>" + escapeHtml(m.default_warehouse || "--") + "</td>" +
        "</tr>"
      );
    })
    .join("");
}

document.addEventListener("DOMContentLoaded", initBom);
