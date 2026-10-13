# -*- coding: utf-8 -*-
# ============================================================
# 采购入库接口（Route 层：只做参数接收/校验与调用 Service）
# 业务逻辑见 backend/services/inbound_service.py
# ============================================================
from flask import Blueprint, request

from services import inbound_service
from utils.response import parse_pagination, success
from utils.validators import to_date

bp = Blueprint("inbound", __name__)


# ======================================================
# API: 采购入库单列表
# Method: GET
# URL: /api/v1/inbound
# 参数: inbound_no, purchase_order_no, supplier, warehouse,
#       inbound_date, status, page, page_size
# Frontend: frontend/js/inbound.js
# ======================================================
# API-BEGIN: INBOUND_LIST
@bp.route("", methods=["GET"])
def list_inbound():
    args = request.args
    page, page_size = parse_pagination(args)
    data = inbound_service.list_orders(
        inbound_no=args.get("inbound_no") or None,
        purchase_order_no=args.get("purchase_order_no") or None,
        supplier=args.get("supplier") or None,
        warehouse=args.get("warehouse") or None,
        inbound_date=to_date(args, "inbound_date", "入库日期") if args.get("inbound_date") else None,
        status=args.get("status") or None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: INBOUND_LIST


# ======================================================
# API: 采购入库单详情（含明细）
# Method: GET
# URL: /api/v1/inbound/{id}
# Frontend: frontend/js/inbound.js
# ======================================================
# API-BEGIN: INBOUND_DETAIL
@bp.route("/<int:order_id>", methods=["GET"])
def get_inbound(order_id):
    return success(inbound_service.get_order(order_id).to_dict(include_items=True))
# API-END: INBOUND_DETAIL


# ======================================================
# API: 创建采购入库单（DRAFT 草稿，自动生成单号，不修改库存）
# Method: POST
# URL: /api/v1/inbound
# Frontend: frontend/js/inbound.js
# 二次开发说明：可在此替换为真实 ERP 后端接口
# ======================================================
# API-BEGIN: INBOUND_CREATE
@bp.route("", methods=["POST"])
def create_inbound():
    data = request.get_json(silent=True) or {}
    return success(inbound_service.create_order(data), "入库单创建成功")
# API-END: INBOUND_CREATE


# ======================================================
# API: 编辑入库单（仅 DRAFT，保存草稿不修改库存）
# Method: PUT
# URL: /api/v1/inbound/{id}
# Frontend: frontend/js/inbound.js
# ======================================================
# API-BEGIN: INBOUND_UPDATE
@bp.route("/<int:order_id>", methods=["PUT"])
def update_inbound(order_id):
    data = request.get_json(silent=True) or {}
    return success(inbound_service.update_order(order_id, data), "保存成功")
# API-END: INBOUND_UPDATE


# ======================================================
# API: 提交审核（DRAFT → PENDING，不修改库存）
# Method: POST
# URL: /api/v1/inbound/{id}/submit
# Frontend: frontend/js/inbound.js
# ======================================================
# API-BEGIN: INBOUND_SUBMIT
@bp.route("/<int:order_id>/submit", methods=["POST"])
def submit_inbound(order_id):
    return success(inbound_service.submit_order(order_id), "提交审核成功")
# API-END: INBOUND_SUBMIT


# ======================================================
# API: 确认入库（PENDING → COMPLETED，事务内增加库存并生成流水）
# Method: POST
# URL: /api/v1/inbound/{id}/confirm
# Frontend: frontend/js/inbound.js
# ======================================================
# API-BEGIN: INBOUND_CONFIRM
@bp.route("/<int:order_id>/confirm", methods=["POST"])
def confirm_inbound(order_id):
    return success(inbound_service.confirm_order(order_id), "入库成功")
# API-END: INBOUND_CONFIRM
