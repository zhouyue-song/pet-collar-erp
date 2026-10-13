# -*- coding: utf-8 -*-
# ============================================================
# 库存盘点服务
# ------------------------------------------------------------
# 业务流程：
#   创建盘点任务（系统保存当前账面库存快照到明细 system_quantity）
#   → 填写实盘数量（系统自动计算差异：actual - system）
#   → 差异判定：=0 正常 / >0 盘盈 / <0 盘亏
#   → 提交审核（PENDING_REVIEW）
#   → 确认调整（事务内：更新 Inventory + 生成 ADJUST 流水）
# ------------------------------------------------------------
# 重要：盘点时不能直接覆盖数据库库存，
# 必须先产生差异记录，经「确认调整」后才允许修改库存。
# ============================================================
from datetime import datetime, time

from extensions import db
from models.inventory import Inventory
from models.stocktake import STOCKTAKE_STATUS_LABELS, StocktakeItem, StocktakeOrder
from services import inventory_service
from utils.document_no import generate_doc_no
from utils.response import BizException, paginate_dict
from utils.validators import optional_str, require_str, to_date, to_float

STOCKTAKE_TYPES = {"FULL": "全盘", "SAMPLE": "重点抽盘", "CYCLE": "循环盘点"}


def list_orders(stocktake_no=None, warehouse=None, status=None,
                stocktake_date=None, page=1, page_size=20):
    """盘点单列表（筛选 + 分页）"""
    q = StocktakeOrder.query
    if stocktake_no:
        q = q.filter(StocktakeOrder.stocktake_no.like(f"%{stocktake_no}%"))
    if warehouse:
        q = q.filter(StocktakeOrder.warehouse == warehouse)
    if status:
        q = q.filter(StocktakeOrder.status == status)
    if stocktake_date:
        q = q.filter(StocktakeOrder.stocktake_date == stocktake_date)

    total = q.count()
    rows = q.order_by(StocktakeOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return paginate_dict([r.to_dict() for r in rows], total, page, page_size)


def get_order(order_id):
    """按 ID 查询盘点单"""
    order = db.session.get(StocktakeOrder, order_id)
    if not order:
        raise BizException("盘点单不存在", 404)
    return order


def _snapshot_items(order):
    """生成盘点明细快照：该仓库所有库存记录（保存当前账面库存与库位）"""
    rows = (
        Inventory.query.filter_by(warehouse=order.warehouse)
        .order_by(Inventory.material_id.asc())
        .all()
    )
    if not rows:
        raise BizException(f"仓库「{order.warehouse}」暂无库存记录，无法创建盘点任务")
    for row in rows:
        item = StocktakeItem(
            stocktake_order_id=order.id,
            material_id=row.material_id,
            location=row.location or "",
            system_quantity=row.quantity or 0,
            actual_quantity=None,
            difference_quantity=None,
            difference_type="NORMAL",
            difference_reason="",
            adjustment_status="PENDING",
        )
        db.session.add(item)


def _compute_difference(item, actual_quantity):
    """计算差异：actual - system，自动判定 正常/盘盈/盘亏"""
    item.actual_quantity = actual_quantity
    diff = round(actual_quantity - (item.system_quantity or 0), 4)
    item.difference_quantity = diff
    if diff == 0:
        item.difference_type = "NORMAL"
    elif diff > 0:
        item.difference_type = "SURPLUS"
    else:
        item.difference_type = "SHORTAGE"


def create_order(data):
    """创建盘点任务：自动生成盘点表快照，状态 COUNTING（盘点中）

    注意：此步骤不修改库存，只保存当时的账面库存快照。
    """
    warehouse = require_str(data, "warehouse", "盘点仓库")
    stocktake_type = optional_str(data, "stocktake_type", "FULL")
    if stocktake_type not in STOCKTAKE_TYPES:
        raise BizException(f"盘点类型只能是 {'/'.join(STOCKTAKE_TYPES.keys())}")

    order = StocktakeOrder(
        stocktake_no=generate_doc_no("PD", StocktakeOrder, "stocktake_no"),
        warehouse=warehouse,
        stocktake_type=stocktake_type,
        operator=optional_str(data, "operator"),
        stocktake_date=to_date(data, "stocktake_date", "盘点日期"),
        remark=optional_str(data, "remark"),
        status="DRAFT",
    )
    db.session.add(order)
    db.session.flush()
    # 系统保存当前账面库存快照
    _snapshot_items(order)
    order.status = "COUNTING"
    db.session.commit()
    return get_order(order.id).to_dict(include_items=True)


def update_order(order_id, data):
    """盘点录入（仅 COUNTING）：填写实盘数量与差异原因，自动计算差异"""
    order = get_order(order_id)
    if order.status != "COUNTING":
        raise BizException(
            f"当前状态为「{STOCKTAKE_STATUS_LABELS.get(order.status, order.status)}」，只有盘点中状态可以录入"
        )

    if data.get("operator") is not None:
        order.operator = optional_str(data, "operator")
    if data.get("remark") is not None:
        order.remark = optional_str(data, "remark")

    for it in data.get("items") or []:
        item = db.session.get(StocktakeItem, it.get("id"))
        if not item or item.stocktake_order_id != order.id:
            raise BizException("盘点明细数据异常，请刷新后重试")
        actual = to_float(it, "actual_quantity", "实盘数量", min_value=0)
        if actual is None:
            raise BizException("实盘数量不能为空")
        _compute_difference(item, actual)
        item.difference_reason = optional_str(it, "difference_reason", "")

    db.session.commit()
    return get_order(order.id).to_dict(include_items=True)


def submit_order(order_id):
    """提交审核：COUNTING → PENDING_REVIEW（差异确认完成，待审核）"""
    order = get_order(order_id)
    if order.status == "PENDING_REVIEW":
        raise BizException("该盘点单已提交审核，请勿重复提交")
    if order.status != "COUNTING":
        raise BizException(
            f"当前状态为「{STOCKTAKE_STATUS_LABELS.get(order.status, order.status)}」，不能提交审核"
        )
    # 全部明细必须已录入实盘数量
    unfilled = [i for i in order.items if i.actual_quantity is None]
    if unfilled:
        raise BizException(
            f"还有 {len(unfilled)} 项物料未录入实盘数量（如 {unfilled[0].material.material_code}），不能提交审核"
        )
    order.status = "PENDING_REVIEW"
    db.session.commit()
    return get_order(order.id).to_dict(include_items=True)


def adjust_order(order_id):
    """确认调整：PENDING_REVIEW → COMPLETED（唯一真正修改库存的入口）

    事务保证：
      对差异 ≠ 0 的明细：更新 Inventory（按差异调整）+ 生成 ADJUST 流水
      → 单据置 COMPLETED
    任何一步失败，整体回滚。
    """
    order = get_order(order_id)
    if order.status == "COMPLETED":
        raise BizException("该盘点任务已经完成，不能重复调整")
    if order.status != "PENDING_REVIEW":
        raise BizException(
            f"当前状态为「{STOCKTAKE_STATUS_LABELS.get(order.status, order.status)}」，盘点任务尚未提交审核，不能调整"
        )

    try:
        for item in order.items:
            diff = item.difference_quantity
            if diff in (None, 0):
                item.adjustment_status = "SKIPPED"  # 无差异
                continue
            # 核心：按盘点差异调整库存 + 生成 ADJUST 流水
            inventory_service.change_stock(
                material=item.material,
                warehouse=order.warehouse,
                location=item.location,
                change_qty=diff,  # 盘盈为正、盘亏为负
                direction="ADJUST",
                document_no=order.stocktake_no,
                document_type="STOCKTAKE",
                operator=order.operator,
                unit_price=None,  # 按库存移动平均价调整金额
                business_time=datetime.combine(order.stocktake_date, time.min) if order.stocktake_date else datetime.now(),
                remark=item.difference_reason or order.remark,
            )
            item.adjustment_status = "ADJUSTED"
        order.status = "COMPLETED"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return get_order(order.id).to_dict(include_items=True)
