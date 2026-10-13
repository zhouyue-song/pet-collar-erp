# -*- coding: utf-8 -*-
# ============================================================
# 物料档案接口（Route 层：只做参数接收/校验与调用 Service）
# 业务逻辑见 backend/services/material_service.py
# ============================================================
from flask import Blueprint, request

from services import material_service
from utils.response import parse_pagination, success

bp = Blueprint("materials", __name__)


# ======================================================
# API: 物料列表
# Method: GET
# URL: /api/v1/materials
# 参数: keyword, category, abc_class, status, page, page_size
# Frontend: frontend/js/materials.js
# ======================================================
# API-BEGIN: MATERIAL_LIST
@bp.route("", methods=["GET"])
def list_materials():
    args = request.args
    page, page_size = parse_pagination(args)
    data = material_service.list_materials(
        keyword=args.get("keyword") or None,
        category=args.get("category") or None,
        abc_class=args.get("abc_class") or None,
        status=args.get("status") or None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: MATERIAL_LIST


# ======================================================
# API: 物料详情
# Method: GET
# URL: /api/v1/materials/{id}
# Frontend: frontend/js/materials.js
# ======================================================
# API-BEGIN: MATERIAL_DETAIL
@bp.route("/<int:material_id>", methods=["GET"])
def get_material(material_id):
    return success(material_service.get_material(material_id).to_dict())
# API-END: MATERIAL_DETAIL


# ======================================================
# API: 新增物料
# Method: POST
# URL: /api/v1/materials
# Frontend: frontend/js/materials.js
# ======================================================
# API-BEGIN: MATERIAL_CREATE
@bp.route("", methods=["POST"])
def create_material():
    data = request.get_json(silent=True) or {}
    return success(material_service.create_material(data), "创建成功")
# API-END: MATERIAL_CREATE


# ======================================================
# API: 修改物料
# Method: PUT
# URL: /api/v1/materials/{id}
# Frontend: frontend/js/materials.js
# ======================================================
# API-BEGIN: MATERIAL_UPDATE
@bp.route("/<int:material_id>", methods=["PUT"])
def update_material(material_id):
    data = request.get_json(silent=True) or {}
    return success(material_service.update_material(material_id, data), "修改成功")
# API-END: MATERIAL_UPDATE


# ======================================================
# API: 删除物料（已被业务数据引用时返回 400）
# Method: DELETE
# URL: /api/v1/materials/{id}
# Frontend: frontend/js/materials.js
# ======================================================
# API-BEGIN: MATERIAL_DELETE
@bp.route("/<int:material_id>", methods=["DELETE"])
def delete_material(material_id):
    material_service.delete_material(material_id)
    return success(None, "删除成功")
# API-END: MATERIAL_DELETE
