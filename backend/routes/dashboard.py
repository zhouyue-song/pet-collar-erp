# -*- coding: utf-8 -*-
# ============================================================
# Dashboard 首页接口（Route 层：只做调用 Service）
# 业务逻辑见 backend/services/dashboard_service.py
# ============================================================
from flask import Blueprint

from services import dashboard_service
from utils.response import success

bp = Blueprint("dashboard", __name__)


# ======================================================
# API: 首页汇总（库存物料数/今日入库/今日出库/待盘点/库存预警）
# Method: GET
# URL: /api/v1/dashboard/summary
# Frontend: frontend/js/dashboard.js
# ======================================================
# API-BEGIN: DASHBOARD_SUMMARY
@bp.route("/summary", methods=["GET"])
def summary():
    return success(dashboard_service.get_summary())
# API-END: DASHBOARD_SUMMARY
