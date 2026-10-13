# -*- coding: utf-8 -*-
# ============================================================
# 生产领料出库服务
# ------------------------------------------------------------
# 业务流程：
#   创建出库单（选择生产工单/产品/生产数量 → 按 BOM 自动生成物料需求）
#   → 提交时检查库存：available_quantity >= outbound_quantity
#     （库存不足返回 HTTP 400 + {available, required}）
#   → 确认出库（事务内：扣减 Inventory + 生成 OUT 流水）
# ============================================================
from datetime import datetime, time

from extensions import db
from models.inventory import Inventory
from models.outbound import OUTBOUND_STATUS_LABELS, OutboundItem, OutboundOrder
from services import bom_service, inventory_service
from utils.document_no import generate_doc_no
from utils.response import BizException, paginate_dict
from utils.validators import optional_str, require_str, to_date, to_float


def list_orders(outbound_no=None, production_order_no=None, department=None,
                warehouse=None, outbound_date=None, status=None,
                page=1, page_size=20):
    """出库单列表（筛选 + 分页）"""
    q = OutboundOrder.query
    if outbound_no:
        q = q.filter(OutboundOrder.outbound_no.like(f"%{outbound_no}%"))
    if production_order_no:
        q = q.filter(OutboundOrder.production_order_no.like(f"%{production_order_no}%"))
    if department:
        q = q.filter(OutboundOrder.department.like(f"%{department}%"))
    if warehouse:
        q = q.filter(OutboundOrder.warehouse == warehouse)
    if outbound_date:
        q = q.filter(OutboundOrder.outbound_date == outbound_date)
    if status:
        q = q.filter(OutboundOrder.status == status)

    total = q.count()
    rows = q.order_by(OutboundOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return paginate_dict([r.to_dict() for r in rows], total, page, page_size)


def get_order(order_id):
    """按 ID 查询出库单"""
    order = db.session.get(OutboundOrder, order_id)
    if not order:
        raise BizException("出库单不存在", 404)
    return order


def get_order_detail(order_id):
    """详情：附加每个明细的当前可用库存（前端红色预警展示用）"""
    order = get_order(order_id)
    data = order.to_dict(include_items=True)
    for it in data["items"]:
        it["available_quantity"] = inventory_service.get_available(it["material_id"], order.warehouse)
    return data


def _check_stock(order):
    """库存校验：任一明细可用库存 < 本次出库数量即报错

    失败返回（与需求规格一致）：
      HTTP 400
      {"code": 400, "message": "M101 心率PPG传感器库存不足",
       "data": {"available": 20, "required": 30}}
    """
    for item in order.items:
        qty = item.outbound_quantity or 0
        if qty <= 0:
            continue
        available = inventory_service.get_available(item.material_id, order.warehouse)
        if available < qty:
            raise BizException(
                f"{item.material.material_code} {item.material.material_name}库存不足",
                data={"available": available, "required": qty},
            )


def create_order(data):
    """创建出库单：按 BOM 自动生成物料需求明细，状态 DRAFT（不修改库存）

    明细字段：
      bom_quantity      = BOM 单位用量
      required_quantity = BOM 单位用量 × 生产数量
      outbound_quantity = 默认等于需求数量（可编辑）
    """
    production_order_no = require_str(data, "production_order_no", "生产工单号")
    product_code = require_str(data, "product_code", "产品编码")
    production_quantity = to_float(data, "production_quantity", "生产数量", default=0, min_value=0)
    if production_quantity <= 0:
        raise BizException("生产数量必须大于 0")
    warehouse = require_str(data, "warehouse", "仓库")

    # BOM 展平（BOM 不存在 / 物料档案缺失 会在此抛业务异常）
    leaves = bom_service.flatten_product(product_code)
    bom_header = bom_service.get_header(product_code)

    order = OutboundOrder(
        outbound_no=generate_doc_no("CK", OutboundOrder, "outbound_no"),
        production_order_no=production_order_no,
        product_code=product_code,
        product_name=bom_header.product_name if bom_header else product_code,
        production_quantity=production_quantity,
        department=optional_str(data, "department"),
        warehouse=warehouse,
        outbound_date=to_date(data, "outbound_date", "出库日期"),
        operator=optional_str(data, "operator"),
        remark=optional_str(data, "remark"),
        status="DRAFT",
    )
    db.session.add(order)
    db.session.flush()

    for leaf in leaves:
        material = leaf["material"]
        required = round(leaf["usage"] * production_quantity, 4)
        # 库位默认取该物料在该仓库的第一个库存库位
        inv_row = Inventory.query.filter_by(material_id=material.id, warehouse=warehouse).first()
        item = OutboundItem(
            outbound_order_id=order.id,
            material_id=material.id,
            bom_quantity=leaf["usage"],
            required_quantity=required,
            outbound_quantity=required,
            location=inv_row.location if inv_row else "",
        )
        db.session.add(item)

    db.session.commit()
    return get_order_detail(order.id)


def update_order(order_id, data):
    """编辑出库单（仅 DRAFT）：主表字段 + 明细本次出库数量/库位"""
    order = get_order(order_id)
    if order.status != "DRAFT":
        raise BizException(f"当前状态为「{OUTBOUND_STATUS_LABELS.get(order.status, order.status)}」，只有草稿状态可以编辑")

    if "production_quantity" in data and data.get("production_quantity") not in (None, ""):
        production_quantity = to_float(data, "production_quantity", "生产数量", min_value=0)
        if production_quantity <= 0:
            raise BizException("生产数量必须大于 0")
        order.production_quantity = production_quantity
    if data.get("department") is not None:
        order.department = optional_str(data, "department")
    if data.get("operator") is not None:
        order.operator = optional_str(data, "operator")
    if data.get("remark") is not None:
        order.remark = optional_str(data, "remark")
    if data.get("outbound_date"):
        order.outbound_date = to_date(data, "outbound_date", "出库日期")

    # 明细：只允许修改 本次出库数量 / 库位（需求数量由 BOM 决定，不可改）
    for it in data.get("items") or []:
        item = db.session.get(OutboundItem, it.get("id"))
        if not item or item.outbound_order_id != order.id:
            raise BizException("明细数据异常，请刷新后重试")
        item.outbound_quantity = to_float(it, "outbound_quantity", "本次出库数量", default=0, min_value=0)
        item.location = optional_str(it, "location", item.location)

    db.session.commit()
    return get_order_detail(order.id)


def submit_order(order_id):
    """提交审核：DRAFT → PENDING，提交前必须通过库存检查（不修改库存）"""
    order = get_order(order_id)
    if order.status != "DRAFT":
        raise BizException(f"当前状态为「{OUTBOUND_STATUS_LABELS.get(order.status, order.status)}」，只有草稿可以提交审核")
    if not order.items:
        raise BizException("出库明细不能为空")
    _check_stock(order)
    order.status = "PENDING"
    db.session.commit()
    return get_order_detail(order.id)


def confirm_order(order_id):
    """确认出库：PENDING → COMPLETED（唯一真正扣减库存的入口）

    事务保证：
      库存校验 → 扣减 Inventory → 生成 OUT 流水 → 单据置 COMPLETED
    任何一步失败，整体回滚。
    """
    order = get_order(order_id)
    if order.status == "COMPLETED":
        raise BizException("该出库单已经完成，不能重复出库")
    if order.status != "PENDING":
        raise BizException(f"当前状态为「{OUTBOUND_STATUS_LABELS.get(order.status, order.status)}」，请先提交审核")

    try:
        # 确认前再次校验（提交与确认之间库存可能被其他单据消耗）
        _check_stock(order)
        for item in order.items:
            qty = item.outbound_quantity or 0
            if qty <= 0:
                continue
            inventory_service.change_stock(
                material=item.material,
                warehouse=order.warehouse,
                location=item.location,
                change_qty=-qty,
                direction="OUT",
                document_no=order.outbound_no,
                document_type="OUTBOUND",
                operator=order.operator,
                unit_price=None,  # 出库按库存移动平均价出账
                business_time=datetime.combine(order.outbound_date, time.min) if order.outbound_date else datetime.now(),
                remark=order.remark,
            )
        order.status = "COMPLETED"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return get_order_detail(order.id)
