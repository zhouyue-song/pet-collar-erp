# -*- coding: utf-8 -*-
# ============================================================
# 路由注册中心
# ------------------------------------------------------------
# 新增模块步骤（详见 README「模块新增方法」）：
#   1. backend/services/ 下新建 xxx_service.py（业务逻辑）
#   2. backend/routes/ 下新建 xxx.py（Blueprint，只做参数校验与调用 Service）
#   3. 在本文件 import 并注册
# ============================================================
from routes.bom import bp as bom_bp
from routes.dashboard import bp as dashboard_bp
from routes.inbound import bp as inbound_bp
from routes.inventory import bp as inventory_bp
from routes.ledger import bp as ledger_bp
from routes.materials import bp as materials_bp
from routes.outbound import bp as outbound_bp
from routes.stocktake import bp as stocktake_bp


def register_blueprints(app):
    """注册所有业务模块 Blueprint（URL 统一前缀 /api/v1/xxx）"""
    app.register_blueprint(dashboard_bp, url_prefix="/api/v1/dashboard")
    app.register_blueprint(materials_bp, url_prefix="/api/v1/materials")
    app.register_blueprint(inventory_bp, url_prefix="/api/v1/inventory")
    app.register_blueprint(inbound_bp, url_prefix="/api/v1/inbound")
    app.register_blueprint(outbound_bp, url_prefix="/api/v1/outbound")
    app.register_blueprint(stocktake_bp, url_prefix="/api/v1/stocktakes")
    app.register_blueprint(ledger_bp, url_prefix="/api/v1/ledger")
    app.register_blueprint(bom_bp, url_prefix="/api/v1/bom")

    # TODO-EXTENSION:
    # 后续新增模块（如 生产工单、采购订单、权限管理）时在此登记

    # TODO-EXTENSION:
    # 后续新增模块（如 生产工单、采购订单、权限管理）时在此登记
