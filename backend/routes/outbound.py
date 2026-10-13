# -*- coding: utf-8 -*-
# ============================================================
# 生产领料出库接口（Route 层：只做参数接收/校验与调用 Service）
# 业务逻辑见 backend/services/outbound_service.py
# ============================================================
from flask import Blueprint, request

from services import outbound_service
from utils.response import parse_pagination, success
from utils.validators import to_date

bp = Blueprint("outbound", __name__)


# ======================================================
# API: 生产领料出库单列表
# Method: GET
# URL: /api/v1/outbound
# 参数: outbound_no, production_order_no, department, warehouse,
#       outbound_date, status, page, page_size
# Frontend: frontend/js/outbound.js
# ======================================================
# API-BEGIN: OUTBOUND_LIST
@bp.route("", methods=["GET"])
def list_outbound():
    args = request.args
    page, page_size = parse_pagination(args)
    data = outbound_service.list_orders(
        outbound_no=args.get("outbound_no") or None,
        production_order_no=args.get("production_order_no") or None,
        department=args.get("department") or None,
        warehouse=args.get("warehouse") or None,
        outbound_date=to_date(args, "outbound_date", "出库日期") if args.get("outbound_date") else None,
        status=args.get("status") or None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: OUTBOUND_LIST


# ======================================================
# API: 生产领料出库单详情（含明细与当前可用库存）
# Method: GET
# URL: /api/v1/outbound/{id}
# Frontend: frontend/js/outbound.js
# ======================================================
# API-BEGIN: OUTBOUND_DETAIL
@bp.route("/<int:order_id>", methods=["GET"])
def get_outbound(order_id):
    return success(outbound_service.get_order_detail(order_id))
# API-END: OUTBOUND_DETAIL


# ======================================================
# API: 创建生产领料出库单（按 BOM 自动生成物料需求，DRAFT）
# Method: POST
# URL: /api/v1/outbound
# 请求体: {production_order_no, product_code, production_quantity,
#          department, warehouse, outbound_date, operator, remark}
# Frontend: frontend/js/outbound.js
# 二次开发说明：可在此替换为真实 ERP 后端接口
# ======================================================
# API-BEGIN: OUTBOUND_CREATE
@bp.route("", methods=["POST"])
def create_outbound():
    data = request.get_json(silent=True) or {}
    return success(outbound_service.create_order(data), "出库单创建成功，已按 BOM 生成物料需求")
# API-END: OUTBOUND_CREATE


# ======================================================
# API: 编辑出库单（仅 DRAFT，可调整本次出库数量/库位）
# Method: PUT
# URL: /api/v1/outbound/{id}
# Frontend: frontend/js/outbound.js
# ======================================================
# API-BEGIN: OUTBOUND_UPDATE
@bp.route("/<int:order_id>", methods=["PUT"])
def update_outbound(order_id):
    data = request.get_json(silent=True) or {}
    return success(outbound_service.update_order(order_id, data), "保存成功")
# API-END: OUTBOUND_UPDATE


# ======================================================
# API: 提交审核（DRAFT → PENDING，提交前检查库存，
#      库存不足返回 400 + {available, required}）
# Method: POST
# URL: /api/v1/outbound/{id}/submit
# Frontend: frontend/js/outbound.js
# ======================================================
# API-BEGIN: OUTBOUND_SUBMIT
@bp.route("/<int:order_id>/submit", methods=["POST"])
def submit_outbound(order_id):
    return success(outbound_service.submit_order(order_id), "提交审核成功")
# API-END: OUTBOUND_SUBMIT


# ======================================================
# API: 确认出库（PENDING → COMPLETED，事务内扣减库存并生成 OUT 流水）
# Method: POST
# URL: /api/v1/outbound/{id}/confirm
# Frontend: frontend/js/outbound.js
# ======================================================
# API-BEGIN: OUTBOUND_CONFIRM
@bp.route("/<int:order_id>/confirm", methods=["POST"])
def confirm_outbound(order_id):
    return success(outbound_service.confirm_order(order_id), "出库成功")
# API-END: OUTBOUND_CONFIRM
