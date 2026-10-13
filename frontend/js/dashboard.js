/* ============================================================
 * dashboard.js — 数据总览页逻辑
 * ------------------------------------------------------------
 * 数据来源（全部走统一 API 模块，页面不硬编码任何业务数字）：
 *   1. GET /api/v1/dashboard/summary  —— KPI 统计卡 + 库存预警列表
 *   2. GET /api/v1/ledger             —— 近7天流水，前端按天聚合画出入库趋势
 * 图表规范：柱状图 2 系列（入库 #2563eb / 出库 #f59e0b），
 *   带图例 + 柱顶数值标签（琥珀色对比度偏低的补偿）+ 悬浮提示，
 *   细柱 + 弱化坐标轴，文字一律使用灰色文字色（不随系列颜色）。
 * ============================================================ */

var trendChart = null; // ECharts 实例（窗口 resize 复用）

/** 页面初始化：公共布局 + 数据加载 */
function initDashboard() {
  initPage();
  loadSummary();
  loadTrend();

  document.getElementById("btnRefreshDash").addEventListener("click", function () {
    loadSummary();
    loadTrend();
  });

  window.addEventListener("resize", function () {
    if (trendChart) trendChart.resize();
  });
}

/* ======================================================
 * API: 首页汇总（KPI 卡片 + 库存预警）
 * Method: GET    URL: /api/v1/dashboard/summary
 * Backend: backend/routes/dashboard.py
 *          -> backend/services/dashboard_service.py
 * 二次开发说明：后端汇总接口新增字段时，前端在此补充展示即可，
 *              业务数字严禁写死在前端。
 * ====================================================== */
// API-BEGIN: DASHBOARD_SUMMARY
function loadSummary() {
  API.get("/dashboard/summary")
    .then(function (d) {
      document.getElementById("statMaterials").textContent = d.material_count;
      document.getElementById("statInbound").textContent = d.today_inbound_count;
      document.getElementById("statOutbound").textContent = d.today_outbound_count;
      document.getElementById("statStocktake").textContent = d.pending_stocktake_count;
      renderWarnings(d.warnings || []);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: DASHBOARD_SUMMARY

/** 渲染右侧库存预警列表（库存不足红色高亮，正常灰色） */
function renderWarnings(list) {
  var box = document.getElementById("warningList");
  if (!list.length) {
    box.innerHTML = '<div class="table-empty"><i class="fa-regular fa-bell-slash"></i>暂无预警物料</div>';
    return;
  }
  box.innerHTML = list
    .map(function (w) {
      var low = w.status === "库存不足";
      return (
        '<div class="warning-item' + (low ? " low" : "") + '">' +
        '<div class="w-icon"><i class="fa-solid ' + (low ? "fa-triangle-exclamation" : "fa-circle-check") + '"></i></div>' +
        '<div class="w-info">' +
        '<div class="w-name">' + escapeHtml(w.material_name) + "</div>" +
        '<div class="w-code">' + escapeHtml(w.material_code) + " · " + escapeHtml(w.abc_class) + "类</div>" +
        "</div>" +
        '<div class="w-nums">当前 <b class="' + (low ? "text-danger" : "") + '">' + fmtQty(w.current_stock) + "</b> / 安全 " + fmtQty(w.safety_stock) + "<br>" +
        '<span class="badge ' + (low ? "badge-red" : "badge-gray") + '">' + escapeHtml(w.status) + "</span></div>" +
        "</div>"
      );
    })
    .join("");
}

/* ======================================================
 * API: 近7天库存流水（前端按天 + 方向聚合出出入库趋势）
 * Method: GET    URL: /api/v1/ledger?start_date=&end_date=&page_size=500
 * Backend: backend/routes/ledger.py -> backend/services/ledger_service.py
 * 二次开发说明：如需月度趋势，把 7 天改为 30 天并加时间粒度切换即可。
 * ====================================================== */
// API-BEGIN: LEDGER_TREND
function loadTrend() {
  var today = new Date();
  var endDate = fmtDate(today);
  var startDate = fmtDate(new Date(today.getTime() - 6 * 86400000));

  API.get("/ledger", { start_date: startDate, end_date: endDate, page_size: 500 })
    .then(function (d) {
      aggregateTrend(d.items || []);
    })
    .catch(function (e) {
      toast(e.message, "error");
    });
}
// API-END: LEDGER_TREND

/** 把流水按 日期+方向 聚合为 7 天柱状图数据 */
function aggregateTrend(rows) {
  var days = [];
  var today = new Date();
  for (var i = 6; i >= 0; i--) {
    days.push(fmtDate(new Date(today.getTime() - i * 86400000)));
  }
  var dayLabels = days.map(function (d) {
    return d.slice(5); // MM-DD
  });

  var inMap = {};
  var outMap = {};
  rows.forEach(function (r) {
    var day = (r.business_time || "").slice(0, 10);
    if (days.indexOf(day) === -1) return;
    if (r.direction === "IN") {
      inMap[day] = (inMap[day] || 0) + Math.abs(r.quantity || 0);
    } else if (r.direction === "OUT") {
      outMap[day] = (outMap[day] || 0) + Math.abs(r.quantity || 0);
    }
    // ADJUST / INIT 不进入出入库趋势
  });

  var inData = days.map(function (d) { return inMap[d] || 0; });
  var outData = days.map(function (d) { return outMap[d] || 0; });
  renderTrendChart(dayLabels, inData, outData);
}

/** ECharts 柱状图渲染（2 系列分组柱：入库蓝 / 出库琥珀） */
function renderTrendChart(dayLabels, inData, outData) {
  var el = document.getElementById("trendChart");
  if (!el || typeof echarts === "undefined") return;
  if (!trendChart) trendChart = echarts.init(el);

  trendChart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      valueFormatter: function (v) { return v + " 件"; },
    },
    legend: {
      data: ["入库", "出库"],
      top: 0,
      right: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: "#6b7280", fontSize: 12 },
    },
    grid: { left: 8, right: 8, top: 34, bottom: 0, containLabel: true },
    xAxis: {
      type: "category",
      data: dayLabels,
      axisLine: { lineStyle: { color: "#e5e7eb" } },
      axisTick: { show: false },
      axisLabel: { color: "#6b7280", fontSize: 12 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#6b7280", fontSize: 12 },
      splitLine: { lineStyle: { color: "#f0f2f5" } },
    },
    series: [
      {
        name: "入库",
        type: "bar",
        barWidth: 14,
        barGap: 2, // 相邻系列柱之间 2px 间隙
        itemStyle: { color: "#2563eb", borderRadius: [4, 4, 0, 0] },
        // 柱顶直接标注数值（琥珀色对比度偏低的补偿：身份不单靠颜色）
        label: {
          show: true,
          position: "top",
          color: "#6b7280",
          fontSize: 10,
          formatter: function (p) { return p.value > 0 ? p.value : ""; },
        },
        data: inData,
      },
      {
        name: "出库",
        type: "bar",
        barWidth: 14,
        barGap: 2,
        itemStyle: { color: "#f59e0b", borderRadius: [4, 4, 0, 0] },
        label: {
          show: true,
          position: "top",
          color: "#6b7280",
          fontSize: 10,
          formatter: function (p) { return p.value > 0 ? p.value : ""; },
        },
        data: outData,
      },
    ],
  });
}

document.addEventListener("DOMContentLoaded", initDashboard);
