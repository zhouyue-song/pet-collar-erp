# -*- coding: utf-8 -*-
# ============================================================
# 单据编号生成器
# 规则：前缀 + 日期(YYYYMMDD) + 当日3位流水号
# 例如：RK20260929001（采购入库）/ CK20260929001（生产领料）/ PD20260929001（库存盘点）
# ============================================================
from datetime import date, datetime

from extensions import db


def generate_doc_no(prefix, model, field_name):
    """生成单据编号

    Args:
        prefix:     编号前缀，入库 RK / 出库 CK / 盘点 PD
        model:      单据模型类（如 InboundOrder）
        field_name: 编号字段名（如 "inbound_no"），用于查重
    """
    today_str = datetime.now().strftime("%Y%m%d")
    today_start = datetime.combine(date.today(), datetime.min.time())

    # 当日已创建单据数量 + 1 作为流水号
    count = model.query.filter(model.created_at >= today_start).count()
    seq = count + 1

    # 查重兜底：编号已存在（如并发、数据残留）则顺延
    while True:
        doc_no = f"{prefix}{today_str}{seq:03d}"
        exists = db.session.query(model.id).filter(
            getattr(model, field_name) == doc_no
        ).first()
        if not exists:
            return doc_no
        seq += 1
