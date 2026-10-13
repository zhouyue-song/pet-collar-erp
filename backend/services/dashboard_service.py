# -*- coding: utf-8 -*-
# ============================================================
# Dashboard 汇总服务
# ------------------------------------------------------------
# 首页所有数据均来自本接口（前端不硬编码任何业务数字）：
#   库存物料数量 / 今日入库单数量 / 今日出库单数量 /
#   待盘点任务数 / 库存预警列表与预警数量 / 库存总金额
# ============================================================
from datetime import date

from sqlalchemy import func

from extensions import db
from models.inbound import InboundOrder
from models.inventory import Inventory
from models.material import Material
from models.outbound import OutboundOrder
from models.stocktake import StocktakeOrder

# 预警监控系数：库存低于 安全库存 × 该系数 的物料进入监控列表
# （低于安全库存=库存不足；高于安全库存但低于监控线=正常，仅提示关注）
WARNING_RATIO = 1.2


def get_summary():
    """首页汇总数据"""
    today = date.today()

    material_count = Material.query.filter_by(status="active").count()
    today_inbound_count = InboundOrder.query.filter(InboundOrder.inbound_date == today).count()
    today_outbound_count = OutboundOrder.query.filter(OutboundOrder.outbound_date == today).count()
    pending_stocktake_count = StocktakeOrder.query.filter(
        StocktakeOrder.status.in_(["COUNTING", "PENDING_REVIEW"])
    ).count()

    # 各物料总库存（跨仓库汇总）
    totals = {
        mid: round(q or 0, 4)
        for mid, q in db.session.query(Inventory.material_id, func.sum(Inventory.quantity))
        .group_by(Inventory.material_id)
        .all()
    }

    # 库存预警监控列表
    warnings = []
    materials = Material.query.filter(
        Material.status == "active", Material.safety_stock > 0
    ).all()
    for m in materials:
        current = totals.get(m.id, 0)
        if current < (m.safety_stock or 0) * WARNING_RATIO:
            warnings.append({
                "material_code": m.material_code,
                "material_name": m.material_name,
                "abc_class": m.abc_class,
                "current_stock": current,
                "safety_stock": m.safety_stock,
                "status": "库存不足" if current < m.safety_stock else "正常",
            })
    # 按 当前库存/安全库存 比值升序：最紧急的排最前
    warnings.sort(key=lambda w: w["current_stock"] / w["safety_stock"])
    warning_count = sum(1 for w in warnings if w["status"] == "库存不足")

    total_amount = round(
        db.session.query(func.coalesce(func.sum(Inventory.inventory_amount), 0)).scalar() or 0, 2
    )

    # TODO-EXTENSION:
    # 后续可在此增加：月度出入库趋势、ABC 分类金额占比、
    # 库存周转率、呆滞物料分析等图表数据
    return {
        "material_count": material_count,
        "today_inbound_count": today_inbound_count,
        "today_outbound_count": today_outbound_count,
        "pending_stocktake_count": pending_stocktake_count,
        "warning_count": warning_count,
        "warnings": warnings,
        "total_inventory_amount": total_amount,
    }
