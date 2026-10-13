# -*- coding: utf-8 -*-
# ============================================================
# Flask 应用入口（应用工厂模式）
# 启动：python backend/app.py
# API 地址：http://127.0.0.1:5000/api/v1
# ------------------------------------------------------------
# 架构规范：Route（参数校验）→ Service（业务逻辑）→ Model → Database
# 新增模块时不要把所有接口写在本文件，见 README「模块新增方法」
# ============================================================
import os

from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import cors, db
from routes import register_blueprints
from utils.response import BizException, fail

# 前端静态文件目录（部署模式下由 Flask 一并托管，见 create_app 末尾）
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
)


def create_app(config_class=None):
    """应用工厂：便于测试与多人协作（每个模块独立注册）"""
    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    # 中文 JSON 不转义为 \uXXXX
    app.json.ensure_ascii = False

    # SQLite：确保数据库目录存在
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///"):
        db_dir = os.path.dirname(uri.replace("sqlite:///", ""))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # 扩展初始化
    db.init_app(app)
    # TODO-EXTENSION:
    # 后续接入登录鉴权后，可在此收紧跨域白名单：
    #   cors.init_app(app, resources={r"/api/*": {"origins": ["http://localhost:8000"]}})
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 注册各业务模块路由（routes/__init__.py 统一登记）
    register_blueprints(app)

    # --------------------------------------------------
    # 全局错误处理：所有异常统一返回 JSON 格式
    # --------------------------------------------------
    @app.errorhandler(BizException)
    def handle_biz_exception(e):
        """业务异常（service 层抛出）"""
        return fail(e.message, e.code, e.data)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """404 / 405 等 HTTP 异常"""
        return fail(e.description or "请求错误", e.code)

    @app.errorhandler(Exception)
    def handle_exception(e):
        """未处理异常：记录日志，对外隐藏细节"""
        app.logger.exception("未处理异常: %s", e)
        return fail("服务器内部错误，请查看后端日志", 500)

    # --------------------------------------------------
    # 前端页面托管（部署模式，与本地开发互不影响）
    #   本地开发：前端仍可用 python -m http.server 8000 单独运行；
    #   线上部署：由 Flask 同时提供页面与 API（同源，无跨域问题），
    #             访问 http://<域名>/ 即是系统首页。
    # 注：/api/v1/* 由上方蓝图优先匹配，不会进入本函数；
    #     这里额外做一次兜底判断，避免非法接口路径返回 HTML。
    # --------------------------------------------------
    @app.route("/", defaults={"filename": "index.html"})
    @app.route("/<path:filename>")
    def serve_frontend(filename):
        if filename.startswith("api/"):
            return fail("接口不存在", 404)
        return send_from_directory(FRONTEND_DIR, filename)

    # 首次启动自动建表
    # （重置数据库并填充演示数据请运行：python backend/seed.py）
    with app.app_context():
        db.create_all()

    return app


# 模块级应用实例：python backend/app.py 或 gunicorn 使用
app = create_app()


if __name__ == "__main__":
    # TODO-EXTENSION:
    # 生产环境请使用 gunicorn / waitress 等 WSGI 服务器部署，
    # 并保持 FLASK_DEBUG=0（默认已关闭）
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
