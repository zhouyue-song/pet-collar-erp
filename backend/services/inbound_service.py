# -*- coding: utf-8 -*-
# ============================================================
# 采购入库服务
# ------------------------------------------------------------
# 业务规则（重要）：
#   创建入库单 / 保存草稿 / 提交审核：都不修改库存；
#   只有「确认入库」才真正增加库存。
#   确认入库必须通过数据库事务执行：
#     更新 Inventory → 生成 InventoryLedger → 单据置 COMPLETED
#   任何一步失败，整个事务回滚（不会出现库存变了但没流水）。
# ============================================================
from datetime import datetime, time

from extensions import db
from models.inbound import INBOUND_STATUS_LABELS, InboundItem, InboundOrder
from models.material import Material
from services import inventory_service
from utils.document_no import generate_doc_no
from utils.response import BizException, paginate_dict
from utils.validators import optional_str, require_str, to_date, to_float


def list_orders(inbound_no=None, purchase_order_no=None, supplier=None,
                warehouse=None, inbound_date=None, status=None,
                page=1, page_size=20):
    """入库单列表（支持筛选 + 分页）"""
    q = InboundOrder.query
    if inbound_no:
        q = q.filter(InboundOrder.inbound_no.like(f"%{inbound_no}%"))
    if purchase_order_no:
        q = q.filter(InboundOrder.purchase_order_no.like(f"%{purchase_order_no}%"))
    if supplier:
        q = q.filter(InboundOrder.supplier.like(f"%{supplier}%"))
    if warehouse:
        q = q.filter(InboundOrder.warehouse == warehouse)
    if inbound_date:
        q = q.filter(InboundOrder.inbound_date == inbound_date)
    if status:
        q = q.filter(InboundOrder.status == status)

    total = q.count()
    rows = q.order_by(InboundOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return paginate_dict([r.to_dict() for r in rows], total, page, page_size)


def get_order(order_id):
    """按 ID 查询入库单"""
    order = db.session.get(InboundOrder, order_id)
    if not order:
        raise BizException("入库单不存在", 404)
    return order


def _get_material(material_id):
    material = db.session.get(Material, material_id)
    if not material:
        raise BizException(f"物料 ID {material_id} 不存在")
    return material


def _validate_header(data):
    """校验主表字段"""
    return {
        "purchase_order_no": optional_str(data, "purchase_order_no"),
        "supplier": require_str(data, "supplier", "供应商"),
        "warehouse": require_str(data, "warehouse", "仓库"),
        "inbound_date": to_date(data, "inbound_date", "入库日期"),
        "operator": optional_str(data, "operator"),
        "remark": optional_str(data, "remark"),
    }


def _validate_items(data):
    """校验明细行（数量/单价不能为负数），金额由服务端重新计算"""
    items = data.get("items") or []
    if not items:
        raise BizException("入库明细不能为空")
    cleaned = []
    for idx, it in enumerate(items, 1):
        material = _get_material(it.get("material_id"))
        purchase_quantity = to_float(it, "purchase_quantity", f"第{idx}行采购数量", default=0, min_value=0)
        received_quantity = to_float(it, "received_quantity", f"第{idx}行已入库数量", default=0, min_value=0)
        inbound_quantity = to_float(it, "inbound_quantity", f"第{idx}行本次入库数量", default=0, min_value=0)
        unit_price = to_float(it, "unit_price", f"第{idx}行单价", default=0, min_value=0)
        cleaned.append({
            "item_id": it.get("id"),
            "material": material,
            "purchase_quantity": purchase_quantity,
            "received_quantity": received_quantity,
            "inbound_quantity": inbound_quantity,
            "unit_price": unit_price,
            "amount": round(inbound_quantity * unit_price, 2),
            "location": optional_str(it, "location"),
        })
    return cleaned


def _apply_items(order, cleaned):
    """重建明细：有 id 更新 / 无 id 新增 / 提交列表中不存在的删除"""
    keep_ids = set()
    for it in cleaned:
        if it["item_id"]:
            item = db.session.get(InboundItem, it["item_id"])
            if not item or item.inbound_order_id != order.id:
                raise BizException("明细数据异常，请刷新后重试")
        else:
            item = InboundItem(inbound_order_id=order.id, material_id=it["material"].id)
            db.session.add(item)
            db.session.flush()
        keep_ids.add(item.id)
        item.material_id = it["material"].id
        item.purchase_quantity = it["purchase_quantity"]
        item.received_quantity = it["received_quantity"]
        item.inbound_quantity = it["inbound_quantity"]
        item.unit_price = it["unit_price"]
        item.amount = it["amount"]
        item.location = it["location"]
    # 删除被移除的明细行
    for old in list(order.items):
        if old.id not in keep_ids:
            db.session.delete(old)
    order.total_amount = round(sum(i.amount or 0 for i in order.items), 2)


def create_order(data):
    """创建入库单：自动生成单号 RK20260929001，状态 DRAFT，不修改库存"""
    header = _validate_header(data)
    order = InboundOrder(
        inbound_no=generate_doc_no("RK", InboundOrder, "inbound_no"),
        status="DRAFT",
        **header,
    )
    db.session.add(order)
    db.session.flush()
    _apply_items(order, _validate_items(data))
    db.session.commit()
    return get_order(order.id).to_dict(include_items=True)


def update_order(order_id, data):
    """编辑入库单（仅 DRAFT 草稿状态允许编辑，保存草稿不修改库存）"""
    order = get_order(order_id)
    if order.status != "DRAFT":
        raise BizException(f"当前状态为「{INBOUND_STATUS_LABELS.get(order.status, order.status)}」，只有草稿状态可以编辑")
    header = _validate_header(data)
    for key, val in header.items():
        setattr(order, key, val)
    _apply_items(order, _validate_items(data))
    db.session.commit()
    return get_order(order_id).to_dict(include_items=True)


def submit_order(order_id):
    """提交审核：DRAFT → PENDING（不修改库存）"""
    order = get_order(order_id)
    if order.status != "DRAFT":
        raise BizException(f"当前状态为「{INBOUND_STATUS_LABELS.get(order.status, order.status)}」，只有草稿可以提交审核")
    if not order.items:
        raise BizException("入库明细不能为空")
    order.status = "PENDING"
    db.session.commit()
    return get_order(order_id).to_dict(include_items=True)


def confirm_order(order_id):
    """确认入库：PENDING → COMPLETED（唯一真正修改库存的入口）

    事务保证：
      更新 Inventory → 生成 InventoryLedger → 单据置 COMPLETED
    任何一步失败，整体回滚。
    """
    order = get_order(order_id)
    if order.status == "COMPLETED":
        raise BizException("该入库单已经完成，不能重复入库")
    if order.status != "PENDING":
        raise BizException(f"当前状态为「{INBOUND_STATUS_LABELS.get(order.status, order.status)}」，请先提交审核")

    try:
        for item in order.items:
            if item.inbound_quantity <= 0:
                raise BizException(
                    f"{item.material.material_code} {item.material.material_name} 本次入库数量必须大于 0"
                )
            # 核心：更新库存 + 生成流水（IN 方向）
            inventory_service.change_stock(
                material=item.material,
                warehouse=order.warehouse,
                location=item.location,
                change_qty=item.inbound_quantity,
                direction="IN",
                document_no=order.inbound_no,
                document_type="INBOUND",
                operator=order.operator,
                unit_price=item.unit_price,
                business_time=datetime.combine(order.inbound_date, time.min) if order.inbound_date else datetime.now(),
                remark=order.remark,
            )
            # 已入库数量自动累加
            item.received_quantity = round((item.received_quantity or 0) + item.inbound_quantity, 4)
        order.status = "COMPLETED"
        db.session.commit()
    except Exception:
        # 任何一步失败：整个事务回滚，库存与流水都不会生效
        db.session.rollback()
        raise
    return get_order(order_id).to_dict(include_items=True)
