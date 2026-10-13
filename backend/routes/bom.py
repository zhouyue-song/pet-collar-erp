# -*- coding: utf-8 -*-
# ============================================================
# BOM 接口（Route 层：只做参数接收与调用 Service）
# 业务逻辑见 backend/services/bom_service.py
# ============================================================
from flask import Blueprint

from services import bom_service
from utils.response import success

bp = Blueprint("bom", __name__)


# ======================================================
# API: BOM 产品列表（前端产品下拉选择用，has_parent 标记半成品）
# Method: GET
# URL: /api/v1/bom
# Frontend: frontend/js/bom.js, frontend/js/outbound.js
# ======================================================
# API-BEGIN: BOM_LIST
@bp.route("", methods=["GET"])
def list_bom():
    return success(bom_service.list_headers())
# API-END: BOM_LIST


# ======================================================
# API: 树形 BOM（产品 → 半成品 → 物料 多级结构）
# Method: GET
# URL: /api/v1/bom/{product_code}  例如 /api/v1/bom/P001
# Frontend: frontend/js/bom.js
# ======================================================
# API-BEGIN: BOM_TREE
@bp.route("/<product_code>", methods=["GET"])
def bom_tree(product_code):
    return success(bom_service.get_tree(product_code))
# API-END: BOM_TREE
