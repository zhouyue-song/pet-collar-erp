# -*- coding: utf-8 -*-
# ============================================================
# 库存流水服务
# ------------------------------------------------------------
# 流水由 change_stock() 统一生成，本服务只负责查询与统计，
# 不提供任何直接写流水的入口。
# ============================================================
from datetime import datetime, time

from sqlalchemy import func

from extensions import db
from models.ledger import InventoryLedger
from models.material import Material
from utils.response import paginate_dict


def list_ledgers(start_date=None, end_date=None, material_code=None,
                 warehouse=None, document_type=None, page=1, page_size=20):
    """库存流水列表（筛选 + 分页 + 出入库统计汇总）

    start_date / end_date: YYYY-MM-DD（按业务时间 business_time 过滤）
    """
    q = InventoryLedger.query.join(Material, InventoryLedger.material_id == Material.id)
    if start_date:
        q = q.filter(InventoryLedger.business_time >= datetime.combine(start_date, time.min))
    if end_date:
        q = q.filter(InventoryLedger.business_time <= datetime.combine(end_date, time.max))
    if material_code:
        q = q.filter(Material.material_code.like(f"%{material_code}%"))
    if warehouse:
        q = q.filter(InventoryLedger.warehouse == warehouse)
    if document_type:
        q = q.filter(InventoryLedger.document_type == document_type)

    # 出入库统计（基于筛选后的全集，供前端统计卡片使用）
    def _sum(direction, col):
        return round(
            q.filter(InventoryLedger.direction == direction)
            .with_entities(func.coalesce(func.sum(col), 0))
            .scalar() or 0, 4
        )

    summary = {
        "in_quantity": _sum("IN", InventoryLedger.quantity),        # 入库数量合计
        "out_quantity": abs(_sum("OUT", InventoryLedger.quantity)), # 出库数量合计
        "adjust_quantity": _sum("ADJUST", InventoryLedger.quantity),# 调整数量合计(带符号)
        "in_amount": round(_sum("IN", InventoryLedger.amount), 2),  # 入库金额合计
        "out_amount": round(_sum("OUT", InventoryLedger.amount), 2),# 出库金额合计
    }

    total = q.count()
    rows = (
        q.order_by(InventoryLedger.business_time.desc(), InventoryLedger.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        **paginate_dict([r.to_dict() for r in rows], total, page, page_size),
        "summary": summary,
    }
