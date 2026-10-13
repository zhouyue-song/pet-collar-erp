# -*- coding: utf-8 -*-
# ============================================================
# BOM 物料清单：bom_headers（产品）+ bom_items（结构明细）
# ------------------------------------------------------------
# 产品：P001 智能宠物健康监测项圈
# 半成品：A100~A500（也是 bom_headers 记录，供树形展开）
# 物料：M101~M505（bom_items 叶子节点）
# 支持多版本（version 字段），默认取 status=active 的最新版本
# ============================================================
from datetime import datetime

from extensions import db


class BOMHeader(db.Model):
    """BOM 头：产品 / 半成品"""

    __tablename__ = "bom_headers"
    __table_args__ = (
        db.UniqueConstraint("product_code", "version", name="uq_bom_product_version"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_code = db.Column(db.String(50), nullable=False, index=True, comment="产品编码")
    product_name = db.Column(db.String(100), default="", comment="产品名称")
    version = db.Column(db.String(20), default="V1.0", comment="版本号")
    status = db.Column(db.String(20), default="active", comment="状态: active/inactive")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    items = db.relationship("BOMItem", backref="bom", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "product_code": self.product_code,
            "product_name": self.product_name or "",
            "version": self.version or "V1.0",
            "status": self.status or "active",
            "item_count": len(self.items),
        }


class BOMItem(db.Model):
    """BOM 明细：parent_code 下的一个子项（material_code）"""

    __tablename__ = "bom_items"
    __table_args__ = (
        db.UniqueConstraint("bom_id", "parent_code", "material_code", name="uq_bom_item_parent_child"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bom_id = db.Column(db.Integer, db.ForeignKey("bom_headers.id"), nullable=False, index=True)
    parent_code = db.Column(db.String(50), nullable=False, comment="父项编码")
    material_code = db.Column(db.String(50), nullable=False, comment="子项编码(物料或半成品)")
    quantity = db.Column(db.Float, default=1, comment="单位用量")
    unit = db.Column(db.String(20), default="个", comment="单位")
    level = db.Column(db.Integer, default=1, comment="层级(相对本 BOM 头)")

    def to_dict(self):
        return {
            "id": self.id,
            "bom_id": self.bom_id,
            "parent_code": self.parent_code,
            "material_code": self.material_code,
            "quantity": self.quantity or 0,
            "unit": self.unit or "个",
            "level": self.level or 1,
        }
