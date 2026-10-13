# -*- coding: utf-8 -*-
# ============================================================
# 库存盘点接口（Route 层：只做参数接收/校验与调用 Service）
# 业务逻辑见 backend/services/stocktake_service.py
# ============================================================
from flask import Blueprint, request

from services import stocktake_service
from utils.response import parse_pagination, success
from utils.validators import to_date

bp = Blueprint("stocktakes", __name__)


# ======================================================
# API: 盘点单列表
# Method: GET
# URL: /api/v1/stocktakes
# 参数: stocktake_no, warehouse, status, stocktake_date, page, page_size
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_LIST
@bp.route("", methods=["GET"])
def list_stocktakes():
    args = request.args
    page, page_size = parse_pagination(args)
    data = stocktake_service.list_orders(
        stocktake_no=args.get("stocktake_no") or None,
        warehouse=args.get("warehouse") or None,
        status=args.get("status") or None,
        stocktake_date=to_date(args, "stocktake_date", "盘点日期") if args.get("stocktake_date") else None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: STOCKTAKE_LIST


# ======================================================
# API: 创建盘点任务（自动生成盘点表：保存当前账面库存快照）
# Method: POST
# URL: /api/v1/stocktakes
# 请求体: {warehouse, stocktake_type(FULL/SAMPLE/CYCLE),
#          stocktake_date, operator, remark}
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_CREATE
@bp.route("", methods=["POST"])
def create_stocktake():
    data = request.get_json(silent=True) or {}
    return success(stocktake_service.create_order(data), "盘点任务创建成功，盘点表已生成")
# API-END: STOCKTAKE_CREATE


# ======================================================
# API: 盘点单详情（含盘点表快照明细）
# Method: GET
# URL: /api/v1/stocktakes/{id}
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_DETAIL
@bp.route("/<int:order_id>", methods=["GET"])
def get_stocktake(order_id):
    return success(stocktake_service.get_order(order_id).to_dict(include_items=True))
# API-END: STOCKTAKE_DETAIL


# ======================================================
# API: 盘点录入（仅 COUNTING：填写实盘数量，自动计算盘盈盘亏）
# Method: PUT
# URL: /api/v1/stocktakes/{id}
# 请求体: {operator?, remark?, items: [{id, actual_quantity, difference_reason}]}
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_UPDATE
@bp.route("/<int:order_id>", methods=["PUT"])
def update_stocktake(order_id):
    data = request.get_json(silent=True) or {}
    return success(stocktake_service.update_order(order_id, data), "盘点数据已保存")
# API-END: STOCKTAKE_UPDATE


# ======================================================
# API: 提交审核（COUNTING → PENDING_REVIEW，差异确认完成）
# Method: POST
# URL: /api/v1/stocktakes/{id}/submit
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_SUBMIT
@bp.route("/<int:order_id>/submit", methods=["POST"])
def submit_stocktake(order_id):
    return success(stocktake_service.submit_order(order_id), "提交审核成功")
# API-END: STOCKTAKE_SUBMIT


# ======================================================
# API: 确认调整（PENDING_REVIEW → COMPLETED，
#      事务内按差异调整库存并生成 ADJUST 流水）
# Method: POST
# URL: /api/v1/stocktakes/{id}/adjust
# Frontend: frontend/js/stocktake.js
# ======================================================
# API-BEGIN: STOCKTAKE_ADJUST
@bp.route("/<int:order_id>/adjust", methods=["POST"])
def adjust_stocktake(order_id):
    return success(stocktake_service.adjust_order(order_id), "库存调整完成")
# API-END: STOCKTAKE_ADJUST
