# -*- coding: utf-8 -*-
# ============================================================
# 全局配置
# ------------------------------------------------------------
# 切换数据库只需要修改 DATABASE_URL 环境变量（或项目根目录 .env 文件）：
#   SQLite（默认）：不配置即可，自动使用 database/erp.db
#   MySQL：
#     DATABASE_URL=mysql+pymysql://root:密码@127.0.0.1:3306/erp_db?charset=utf8mb4
# ============================================================
import os

from dotenv import load_dotenv

# 加载项目根目录 .env 文件（不存在时静默跳过）
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))   # backend/ 目录
PROJECT_ROOT = os.path.dirname(BASE_DIR)                # 项目根目录


class Config:
    """应用配置"""

    # --------------------------------------------------
    # 数据库：默认 SQLite；设置 DATABASE_URL 即切换 MySQL
    # --------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(PROJECT_ROOT, "database", "erp.db")
    )

    # 关闭对象修改追踪（节省内存）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MySQL 连接池预检，避免长时间空闲后断线（SQLite 下无副作用）
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # TODO-EXTENSION:
    # 后续可在此增加：SECRET_KEY、JWT 过期时间、Redis 缓存地址等配置
