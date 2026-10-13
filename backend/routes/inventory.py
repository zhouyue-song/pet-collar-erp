# -*- coding: utf-8 -*-
# ============================================================
# 库存查询接口（Route 层：只做参数接收与调用 Service）
# ------------------------------------------------------------
# 注意：库存不允许前端直接修改，本模块只有查询接口；
# 库存变动通过 入库确认 / 出库确认 / 盘点调整 三个业务入口触发。
# ============================================================
from flask import Blueprint, request

from services import inventory_service
from utils.response import parse_pagination, success

bp = Blueprint("inventory", __name__)


# ======================================================
# API: 库存列表
# Method: GET
# URL: /api/v1/inventory
# 参数: material_code, material_name, warehouse, location,
#       abc_class, stock_status(LOW/NORMAL), page, page_size
# Frontend: frontend/js/inventory.js
# ======================================================
# API-BEGIN: INVENTORY_LIST
@bp.route("", methods=["GET"])
def list_inventory():
    args = request.args
    page, page_size = parse_pagination(args, default_page_size=50)
    data = inventory_service.list_inventory(
        material_code=args.get("material_code") or None,
        material_name=args.get("material_name") or None,
        warehouse=args.get("warehouse") or None,
        location=args.get("location") or None,
        abc_class=args.get("abc_class") or None,
        stock_status=args.get("stock_status") or None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: INVENTORY_LIST


# ======================================================
# API: 单个物料的库存明细（所有仓库/库位）
# Method: GET
# URL: /api/v1/inventory/{material_id}
# Frontend: frontend/js/inventory.js
# ======================================================
# API-BEGIN: INVENTORY_BY_MATERIAL
@bp.route("/<int:material_id>", methods=["GET"])
def inventory_by_material(material_id):
    return success(inventory_service.get_inventory_by_material(material_id))
# API-END: INVENTORY_BY_MATERIAL
