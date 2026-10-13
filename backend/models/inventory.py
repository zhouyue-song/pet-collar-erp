# -*- coding: utf-8 -*-
# ============================================================
# 库存表 inventories
# ------------------------------------------------------------
# 重要：quantity（账面库存）不能由前端直接修改，
# 所有库存变动必须通过 services/inventory_service.py 的
# change_stock() 完成（同时生成库存流水）。
# ============================================================
from datetime import datetime

from extensions import db


class Inventory(db.Model):
    """库存（物料 + 仓库 + 库位 维度）"""

    __tablename__ = "inventories"
    __table_args__ = (
        db.UniqueConstraint("material_id", "warehouse", "location", name="uq_inventory_material_wh_loc"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True, comment="物料ID")
    warehouse = db.Column(db.String(50), default="", nullable=False, comment="仓库")
    location = db.Column(db.String(50), default="", comment="库位")
    quantity = db.Column(db.Float, default=0, comment="账面库存")
    available_quantity = db.Column(db.Float, default=0, comment="可用库存")
    occupied_quantity = db.Column(db.Float, default=0, comment="占用库存(已锁定)")
    average_price = db.Column(db.Float, default=0, comment="移动加权平均单价")
    inventory_amount = db.Column(db.Float, default=0, comment="库存金额")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    material = db.relationship("Material", lazy="joined")

    def to_dict(self):
        """转为字典（含物料基础信息）"""
        return {
            "id": self.id,
            "material_id": self.material_id,
            "material_code": self.material.material_code if self.material else None,
            "material_name": self.material.material_name if self.material else None,
            "specification": self.material.specification if self.material else None,
            "unit": self.material.unit if self.material else None,
            "abc_class": self.material.abc_class if self.material else None,
            "safety_stock": self.material.safety_stock if self.material else 0,
            "warehouse": self.warehouse,
            "location": self.location,
            "quantity": self.quantity or 0,
            "available_quantity": self.available_quantity or 0,
            "occupied_quantity": self.occupied_quantity or 0,
            "average_price": self.average_price or 0,
            "inventory_amount": self.inventory_amount or 0,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
