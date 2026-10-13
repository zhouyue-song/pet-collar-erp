# -*- coding: utf-8 -*-
# ============================================================
# 库存核心服务
# ------------------------------------------------------------
# 重要设计（全系统基石）：
#   所有库存变动必须调用 change_stock()，它同时完成：
#     1. 更新 Inventory（账面库存/可用库存/移动平均价/库存金额）
#     2. 生成 InventoryLedger（库存流水，before/after 留痕）
#   change_stock() 必须在调用方事务中使用：
#     调用方 commit → 库存与流水同时生效；
#     调用方 rollback → 全部回滚。
#   绝不出现"库存变了但流水没生成"的情况。
#
# 库存（quantity）不能由前端直接修改，前端只能通过
# 入库确认 / 出库确认 / 盘点调整 三个业务入口间接触发。
# ============================================================
from datetime import datetime

from sqlalchemy import func

from extensions import db
from models.inventory import Inventory
from models.ledger import InventoryLedger
from models.material import Material
from utils.response import BizException, paginate_dict


def get_or_create_inventory(material, warehouse, location=""):
    """按 物料+仓库+库位 获取库存记录，不存在则创建（初始为0）"""
    inv = Inventory.query.filter_by(
        material_id=material.id, warehouse=warehouse, location=location or ""
    ).first()
    if inv:
        return inv
    inv = Inventory(
        material_id=material.id,
        warehouse=warehouse,
        location=location or "",
        quantity=0,
        available_quantity=0,
        occupied_quantity=0,
        average_price=0,
        inventory_amount=0,
    )
    db.session.add(inv)
    db.session.flush()
    return inv


def change_stock(material, warehouse, location, change_qty, direction,
                 document_no, document_type, operator="", unit_price=None,
                 business_time=None, remark=""):
    """库存核心变动：更新 Inventory + 生成 InventoryLedger（必须在事务中调用）

    Args:
        material:      物料模型对象
        warehouse:     仓库
        location:      库位
        change_qty:    带符号变动量（IN 为正；OUT 为负；ADJUST 盘盈正/盘亏负）
        direction:     IN / OUT / ADJUST
        document_no:   单据编号（入库单号/出库单号/盘点单号等）
        document_type: INBOUND / OUTBOUND / STOCKTAKE / INIT
        operator:      经办人
        unit_price:    单价；不传或<=0时取库存当前移动平均价
        business_time: 业务时间（默认当前时间）
        remark:        备注
    """
    if not change_qty:
        return None  # 无变动不写流水

    inv = get_or_create_inventory(material, warehouse, location)

    before = inv.quantity or 0
    after = round(before + change_qty, 4)
    # 最后一道防线：不允许出现负库存
    if after < 0:
        raise BizException(
            f"{material.material_code} {material.material_name}库存不足，当前库存 {before}"
        )

    # 计价：未指定单价时使用库存移动平均价（出库/盘亏按平均成本出账）
    if unit_price is None or unit_price <= 0:
        unit_price = inv.average_price or 0

    # 入库：移动加权平均法更新单价
    if direction == "IN" and change_qty > 0:
        total_value = round((before or 0) * (inv.average_price or 0) + change_qty * unit_price, 6)
        inv.average_price = round(total_value / after, 6) if after else 0

    # 更新库存主表
    inv.quantity = after
    inv.available_quantity = round((inv.available_quantity or 0) + change_qty, 4)
    inv.inventory_amount = round(after * (inv.average_price or 0), 2)
    inv.updated_at = datetime.now()

    # TODO-EXTENSION:
    # occupied_quantity 预留用于"出库单提交时锁定库存、确认时释放"场景；
    # 当前简化实现：出库在确认时直接扣减，不经过占用状态。

    # 生成库存流水（任何库存变化必须留痕）
    ledger = InventoryLedger(
        document_no=document_no,
        document_type=document_type,
        material_id=material.id,
        warehouse=warehouse,
        location=inv.location,
        direction=direction,
        quantity=round(change_qty, 4),
        unit_price=round(unit_price, 4),
        amount=round(abs(change_qty) * unit_price, 2),
        before_quantity=before,
        after_quantity=after,
        operator=operator or "",
        remark=remark or "",
        business_time=business_time or datetime.now(),
    )
    db.session.add(ledger)
    db.session.flush()
    return ledger


def get_available(material_id, warehouse):
    """查询某物料在某仓库的可用库存合计（领料出库库存校验用）"""
    total = db.session.query(func.coalesce(func.sum(Inventory.available_quantity), 0)).filter_by(
        material_id=material_id, warehouse=warehouse
    ).scalar()
    return round(total or 0, 4)


def get_total_by_material(material_ids):
    """按物料汇总所有仓库的总库存 {material_id: total}（库存预警用）"""
    if not material_ids:
        return {}
    rows = (
        db.session.query(Inventory.material_id, func.sum(Inventory.quantity))
        .filter(Inventory.material_id.in_(list(material_ids)))
        .group_by(Inventory.material_id)
        .all()
    )
    return {mid: round(q or 0, 4) for mid, q in rows}


def stock_status_of(total, safety_stock):
    """库存状态判定：总库存 < 安全库存 → LOW（库存不足）"""
    if safety_stock and total < safety_stock:
        return "LOW"
    return "NORMAL"


def _with_status(row, totals):
    """为库存记录附加按物料汇总后的库存状态"""
    total = totals.get(row.material_id, row.quantity or 0)
    status = stock_status_of(total, row.material.safety_stock if row.material else 0)
    d = row.to_dict()
    d["stock_status"] = status
    d["stock_status_label"] = "库存不足" if status == "LOW" else "正常"
    d["total_quantity_all_warehouse"] = total
    return d


def list_inventory(material_code=None, material_name=None, warehouse=None,
                   location=None, abc_class=None, stock_status=None,
                   page=1, page_size=20):
    """库存列表（筛选 + 分页 + 汇总）

    stock_status 筛选基于"物料在所有仓库的总库存"判断：
      LOW(库存不足) / NORMAL(正常)
    """
    q = Inventory.query.join(Material, Inventory.material_id == Material.id)
    if material_code:
        q = q.filter(Material.material_code.like(f"%{material_code}%"))
    if material_name:
        q = q.filter(Material.material_name.like(f"%{material_name}%"))
    if warehouse:
        q = q.filter(Inventory.warehouse == warehouse)
    if location:
        q = q.filter(Inventory.location.like(f"%{location}%"))
    if abc_class:
        q = q.filter(Material.abc_class == abc_class)

    # 汇总（基于筛选后的全集）
    summary = {
        "material_count": q.with_entities(func.count(func.distinct(Inventory.material_id))).scalar() or 0,
        "total_quantity": round(q.with_entities(func.coalesce(func.sum(Inventory.quantity), 0)).scalar() or 0, 4),
        "total_amount": round(q.with_entities(func.coalesce(func.sum(Inventory.inventory_amount), 0)).scalar() or 0, 2),
    }

    if stock_status:
        # stock_status 需在物料总库存维度判断，取筛选后全集再内存过滤分页
        rows_all = q.all()
        totals = get_total_by_material({r.material_id for r in rows_all})
        rows_all = [
            r for r in rows_all
            if stock_status_of(totals.get(r.material_id, 0), r.material.safety_stock if r.material else 0) == stock_status
        ]
        total = len(rows_all)
        rows = rows_all[(page - 1) * page_size: page * page_size]
        totals = get_total_by_material({r.material_id for r in rows})
    else:
        total = q.count()
        rows = (
            q.order_by(Inventory.material_id.asc(), Inventory.warehouse.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        totals = get_total_by_material({r.material_id for r in rows})

    items = [_with_status(r, totals) for r in rows]
    return {**paginate_dict(items, total, page, page_size), "summary": summary}


def get_inventory_by_material(material_id):
    """查询单个物料在所有仓库的库存记录"""
    material = db.session.get(Material, material_id)
    if not material:
        raise BizException("物料不存在", 404)
    rows = Inventory.query.filter_by(material_id=material_id).all()
    totals = get_total_by_material({material_id})
    return {
        "material": material.to_dict(),
        "items": [_with_status(r, totals) for r in rows],
    }
