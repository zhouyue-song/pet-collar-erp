# -*- coding: utf-8 -*-
# ============================================================
# 请求参数校验工具
# 非法参数统一抛出 BizException（HTTP 400），由全局错误处理器返回 JSON
# ============================================================
from datetime import datetime

from utils.response import BizException


def require_str(data, key, label):
    """必填字符串：返回去除首尾空格后的值"""
    value = (data or {}).get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BizException(f"{label}不能为空")
    return str(value).strip()


def optional_str(data, key, default=""):
    """可选字符串"""
    value = (data or {}).get(key)
    if value is None:
        return default
    return str(value).strip()


def to_float(data, key, label, default=None, min_value=None, max_value=None):
    """数字校验：数量/单价等场景传 min_value=0 禁止负数"""
    value = (data or {}).get(key)
    if value is None or value == "":
        if default is not None:
            return default
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise BizException(f"{label}必须是数字")
    if min_value is not None and num < min_value:
        raise BizException(f"{label}不能小于 {min_value}")
    if max_value is not None and num > max_value:
        raise BizException(f"{label}不能大于 {max_value}")
    return num


def to_int(data, key, label, default=None, min_value=None, max_value=None):
    """整数校验：采购提前期等场景使用"""
    value = (data or {}).get(key)
    if value is None or value == "":
        if default is not None:
            return default
        return None
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise BizException(f"{label}必须是整数")
    if min_value is not None and num < min_value:
        raise BizException(f"{label}不能小于 {min_value}")
    if max_value is not None and num > max_value:
        raise BizException(f"{label}不能大于 {max_value}")
    return num


def to_date(data, key, label):
    """日期校验：格式 YYYY-MM-DD，返回 datetime.date"""
    value = (data or {}).get(key)
    if not value:
        raise BizException(f"{label}不能为空")
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise BizException(f"{label}格式错误，应为 YYYY-MM-DD")
