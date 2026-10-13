# -*- coding: utf-8 -*-
# ============================================================
# BOM 服务：产品列表 / 树形展开 / 叶子物料展平
# ------------------------------------------------------------
# 说明：本服务在阶段四（生产领料）提前实现，因为出库单
# 需要按 BOM 自动生成物料需求；阶段六为其补充路由层。
# ============================================================
from extensions import db
from models.bom import BOMHeader, BOMItem
from models.material import Material
from utils.response import BizException

# 树形展开最大层级（防止 BOM 数据异常导致无限递归）
MAX_LEVEL = 10


def get_header(product_code, status="active"):
    """按产品编码取 BOM 头（默认取最新 active 版本）"""
    q = BOMHeader.query.filter_by(product_code=product_code)
    if status:
        q = q.filter_by(status=status)
    return q.order_by(BOMHeader.id.desc()).first()


def _items_of(header):
    """某 BOM 头的明细（按 id 稳定排序）"""
    if not header:
        return []
    return BOMItem.query.filter_by(bom_id=header.id).order_by(BOMItem.id.asc()).all()


def list_headers():
    """BOM 产品列表（has_parent=True 表示它是其他产品的半成品子项）"""
    headers = BOMHeader.query.order_by(BOMHeader.product_code.asc()).all()
    parent_codes = {row[0] for row in db.session.query(BOMItem.material_code).distinct().all()}
    items = []
    for h in headers:
        d = h.to_dict()
        d["has_parent"] = h.product_code in parent_codes
        items.append(d)
    return {"items": items}


def _node_name(code):
    """节点名称与类型：优先物料档案 → 其次 BOM 头（半成品）"""
    material = Material.query.filter_by(material_code=code).first()
    if material:
        return material.material_name, "material"
    header = get_header(code)
    if header:
        return header.product_name, "semi"
    return code, "unknown"


def get_tree(product_code):
    """树形 BOM（GET /api/v1/bom/{product_code} 的返回结构）

    结构示例：
    {
      "product_code": "P001", "product_name": "智能宠物健康监测项圈",
      "version": "V1.0", "status": "active",
      "tree": {"code": "P001", "name": "...", "quantity": 1, "unit": "套",
               "level": 0, "type": "product", "children": [...]}
    }
    """
    header = get_header(product_code)
    if not header:
        raise BizException(f"产品 {product_code} 的 BOM 不存在", 404)

    def build(code, quantity, unit, level, path):
        if code in path or level > MAX_LEVEL:
            return None  # 环保护 / 深度保护
        name, node_type = _node_name(code)
        node = {
            "code": code,
            "name": name,
            "type": "product" if level == 0 else node_type,
            "quantity": quantity,
            "unit": unit or "个",
            "level": level,
            "children": [],
        }
        child_header = get_header(code)
        for item in _items_of(child_header):
            child = build(item.material_code, item.quantity or 0, item.unit, level + 1, path | {code})
            if child:
                node["children"].append(child)
        return node

    return {
        "product_code": header.product_code,
        "product_name": header.product_name,
        "version": header.version,
        "status": header.status,
        "tree": build(product_code, 1, "套", 0, set()),
    }


def flatten_product(product_code):
    """展平产品 BOM 为叶子物料清单（生产领料出库用）

    Returns:
        [{"material": <Material>, "usage": 单套用量, "unit": "个"}, ...]
    需求数量 = usage × 生产数量
    同一物料在多条分支出现时用量自动累加。
    """
    header = get_header(product_code)
    if not header:
        raise BizException(f"产品 {product_code} 的 BOM 不存在", 404)

    result = {}

    def walk(code, multiplier, path):
        if code in path or multiplier <= 0:
            return
        child_header = get_header(code)
        for item in _items_of(child_header):
            qty = (item.quantity or 0) * multiplier
            if get_header(item.material_code):
                # 半成品：继续下钻
                walk(item.material_code, qty, path | {code})
            else:
                # 叶子物料：必须在物料档案中存在
                material = Material.query.filter_by(material_code=item.material_code).first()
                if not material:
                    raise BizException(f"BOM 物料 {item.material_code} 在物料档案中不存在")
                if item.material_code in result:
                    result[item.material_code]["usage"] = round(result[item.material_code]["usage"] + qty, 4)
                else:
                    result[item.material_code] = {
                        "material": material,
                        "usage": round(qty, 4),
                        "unit": item.unit or material.unit or "个",
                    }

    walk(product_code, 1, set())
    if not result:
        raise BizException(f"产品 {product_code} 的 BOM 展开失败，请检查 BOM 配置")
    return list(result.values())
