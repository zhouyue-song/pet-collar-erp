# -*- coding: utf-8 -*-
# ============================================================
# 库存流水接口（Route 层：只做参数接收与调用 Service）
# 业务逻辑见 backend/services/ledger_service.py
# ============================================================
from flask import Blueprint, request

from services import ledger_service
from utils.response import parse_pagination, success
from utils.validators import to_date

bp = Blueprint("ledger", __name__)


# ======================================================
# API: 库存流水列表（含出入库统计汇总）
# Method: GET
# URL: /api/v1/ledger
# 参数: start_date, end_date, material_code, warehouse,
#       document_type, page, page_size
# Frontend: frontend/js/ledger.js
# ======================================================
# API-BEGIN: LEDGER_LIST
@bp.route("", methods=["GET"])
def list_ledgers():
    args = request.args
    page, page_size = parse_pagination(args, default_page_size=20)
    data = ledger_service.list_ledgers(
        start_date=to_date(args, "start_date", "开始日期") if args.get("start_date") else None,
        end_date=to_date(args, "end_date", "结束日期") if args.get("end_date") else None,
        material_code=args.get("material_code") or None,
        warehouse=args.get("warehouse") or None,
        document_type=args.get("document_type") or None,
        page=page,
        page_size=page_size,
    )
    return success(data)
# API-END: LEDGER_LIST
