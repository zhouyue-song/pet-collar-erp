# -*- coding: utf-8 -*-
# ============================================================
# 统一 API 响应工具
# ------------------------------------------------------------
# 成功：{"code": 200, "message": "success", "data": {...}}
# 失败：{"code": 400, "message": "错误信息", "data": null}（HTTP 状态码与 code 一致）
# ============================================================
from flask import jsonify


class BizException(Exception):
    """业务异常：service 层抛出，由 app.py 全局错误处理器转换为统一 JSON 响应"""

    def __init__(self, message, code=400, data=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


def success(data=None, message="success"):
    """成功响应"""
    return jsonify({"code": 200, "message": message, "data": data})


def fail(message="操作失败", code=400, data=None):
    """失败响应（HTTP 状态码与业务 code 保持一致）"""
    return jsonify({"code": code, "message": message, "data": data}), code


def parse_pagination(args, default_page_size=20, max_page_size=500):
    """从 request.args 解析分页参数，非法值自动回退默认"""
    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(args.get("page_size", default_page_size))
        page_size = min(max(1, page_size), max_page_size)
    except (TypeError, ValueError):
        page_size = default_page_size
    return page, page_size


def paginate_dict(items, total, page, page_size):
    """组装统一分页数据结构"""
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }
