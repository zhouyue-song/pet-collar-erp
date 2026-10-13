# -*- coding: utf-8 -*-
# ============================================================
# 扩展实例（在 app.py 中 init_app 初始化，避免循环导入）
# ============================================================
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()   # 数据库 ORM
cors = CORS()       # 跨域支持

# TODO-EXTENSION:
# 后续可在此增加：
#   migrate = Migrate()   # 数据库迁移（表结构变更管理）
#   jwt = JWTManager()    # 登录鉴权
#   cache = Cache()       # 缓存
