# -*- coding: utf-8 -*-
# ============================================================
# 物料档案服务
# ============================================================
from sqlalchemy import or_

from extensions import db
from models.bom import BOMItem
from models.inbound import InboundItem
from models.inventory import Inventory
from models.ledger import InventoryLedger
from models.material import Material
from models.outbound import OutboundItem
from models.stocktake import StocktakeItem
from utils.response import BizException, paginate_dict
from utils.validators import optional_str, require_str, to_float, to_int

ABC_CLASSES = ("A", "B", "C")
MATERIAL_TYPES = ("外购件", "自制件", "委外件")
STATUSES = ("active", "inactive")


def list_materials(keyword=None, category=None, abc_class=None, status=None,
                   page=1, page_size=20):
    """物料列表（keyword 模糊匹配 编码/名称）"""
    q = Material.query
    if keyword:
        q = q.filter(or_(
            Material.material_code.like(f"%{keyword}%"),
            Material.material_name.like(f"%{keyword}%"),
        ))
    if category:
        q = q.filter(Material.category == category)
    if abc_class:
        q = q.filter(Material.abc_class == abc_class.upper())
    if status:
        q = q.filter(Material.status == status)

    total = q.count()
    rows = q.order_by(Material.id.asc()).offset((page - 1) * page_size).limit(page_size).all()

    # ABC 分类汇总（前端 ABC 分类统计卡片用）
    abc_summary = {
        "A": Material.query.filter_by(abc_class="A").count(),
        "B": Material.query.filter_by(abc_class="B").count(),
        "C": Material.query.filter_by(abc_class="C").count(),
    }
    return {**paginate_dict([r.to_dict() for r in rows], total, page, page_size),
            "abc_summary": abc_summary}


def get_material(material_id):
    """按 ID 查询物料"""
    m = db.session.get(Material, material_id)
    if not m:
        raise BizException("物料不存在", 404)
    return m


def _validate_payload(data):
    """校验并整理物料字段"""
    material_code = require_str(data, "material_code", "物料编码")
    material_name = require_str(data, "material_name", "物料名称")
    category = optional_str(data, "category", "原材料")
    specification = optional_str(data, "specification")
    unit = optional_str(data, "unit", "个")
    abc_class = optional_str(data, "abc_class", "C").upper()
    if abc_class not in ABC_CLASSES:
        raise BizException("ABC分类只能是 A/B/C")
    material_type = optional_str(data, "material_type", "外购件")
    if material_type not in MATERIAL_TYPES:
        raise BizException(f"物料类型只能是 {'/'.join(MATERIAL_TYPES)}")
    safety_stock = to_float(data, "safety_stock", "安全库存", default=0, min_value=0)
    purchase_lead_time = to_int(data, "purchase_lead_time", "采购提前期", default=0, min_value=0)
    default_warehouse = optional_str(data, "default_warehouse")
    status = optional_str(data, "status", "active")
    if status not in STATUSES:
        raise BizException("状态只能是 active/inactive")

    return {
        "material_code": material_code,
        "material_name": material_name,
        "category": category,
        "specification": specification,
        "unit": unit,
        "abc_class": abc_class,
        "material_type": material_type,
        "safety_stock": safety_stock,
        "purchase_lead_time": purchase_lead_time,
        "default_warehouse": default_warehouse,
        "status": status,
    }


def create_material(data):
    """新增物料"""
    values = _validate_payload(data)
    if Material.query.filter_by(material_code=values["material_code"]).first():
        raise BizException(f"物料编码 {values['material_code']} 已存在")
    m = Material(**values)
    db.session.add(m)
    db.session.commit()
    return m.to_dict()


def update_material(material_id, data):
    """修改物料"""
    m = get_material(material_id)
    values = _validate_payload(data)
    dup = Material.query.filter(
        Material.material_code == values["material_code"],
        Material.id != material_id,
    ).first()
    if dup:
        raise BizException(f"物料编码 {values['material_code']} 已被其他物料使用")
    for key, val in values.items():
        setattr(m, key, val)
    db.session.commit()
    return m.to_dict()


def delete_material(material_id):
    """删除物料（已被业务数据引用时禁止删除）"""
    m = get_material(material_id)
    refs = [
        ("库存记录", Inventory.query.filter_by(material_id=material_id).count()),
        ("库存流水", InventoryLedger.query.filter_by(material_id=material_id).count()),
        ("采购入库明细", InboundItem.query.filter_by(material_id=material_id).count()),
        ("生产领料明细", OutboundItem.query.filter_by(material_id=material_id).count()),
        ("盘点明细", StocktakeItem.query.filter_by(material_id=material_id).count()),
        ("BOM 明细", BOMItem.query.filter_by(material_code=m.material_code).count()),
    ]
    for label, count in refs:
        if count:
            raise BizException(f"该物料已被{label}引用（{count}条），不能删除")

    # TODO-EXTENSION:
    # 生产环境建议改为软删除（status=inactive + deleted_at 标记），保留历史可追溯性
    db.session.delete(m)
    db.session.commit()
    return None
