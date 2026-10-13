# -*- coding: utf-8 -*-
# ============================================================
# 采购入库单据：inbound_orders（主表）+ inbound_items（明细）
# ------------------------------------------------------------
# 业务规则（重要）：
#   创建 / 保存草稿 / 提交审核：都不修改库存；
#   只有「确认入库」才真正增加库存（事务内：更新 Inventory
#   + 生成 InventoryLedger + 单据置为 COMPLETED，见 inbound_service）。
# ============================================================
from datetime import datetime

from extensions import db

# 入库单状态
INBOUND_STATUS_LABELS = {
    "DRAFT": "草稿",
    "PENDING": "待审核",
    "COMPLETED": "已完成",
    "REJECTED": "已驳回",
}


class InboundOrder(db.Model):
    """采购入库单主表"""

    __tablename__ = "inbound_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    inbound_no = db.Column(db.String(50), unique=True, nullable=False, index=True, comment="入库单号")
    purchase_order_no = db.Column(db.String(50), default="", comment="采购订单号")
    supplier = db.Column(db.String(100), default="", comment="供应商")
    warehouse = db.Column(db.String(50), default="", comment="仓库")
    inbound_date = db.Column(db.Date, default=datetime.now().date, index=True, comment="入库日期")
    operator = db.Column(db.String(50), default="", comment="经办人")
    status = db.Column(db.String(20), default="DRAFT", index=True, comment="状态: DRAFT/PENDING/COMPLETED/REJECTED")
    remark = db.Column(db.String(200), default="", comment="备注")
    total_amount = db.Column(db.Float, default=0, comment="总金额")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    items = db.relationship("InboundItem", backref="order", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        """转为字典；include_items=True 时携带明细"""
        data = {
            "id": self.id,
            "inbound_no": self.inbound_no,
            "purchase_order_no": self.purchase_order_no or "",
            "supplier": self.supplier or "",
            "warehouse": self.warehouse or "",
            "inbound_date": self.inbound_date.strftime("%Y-%m-%d") if self.inbound_date else None,
            "operator": self.operator or "",
            "status": self.status,
            "status_label": INBOUND_STATUS_LABELS.get(self.status, self.status),
            "remark": self.remark or "",
            "total_amount": self.total_amount or 0,
            "item_count": len(self.items),
            "total_quantity": sum(i.inbound_quantity or 0 for i in self.items),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items]
        return data


class InboundItem(db.Model):
    """采购入库单明细"""

    __tablename__ = "inbound_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    inbound_order_id = db.Column(db.Integer, db.ForeignKey("inbound_orders.id"), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True)
    purchase_quantity = db.Column(db.Float, default=0, comment="采购数量")
    received_quantity = db.Column(db.Float, default=0, comment="已入库数量(确认入库时自动累加)")
    inbound_quantity = db.Column(db.Float, default=0, comment="本次入库数量")
    unit_price = db.Column(db.Float, default=0, comment="单价")
    amount = db.Column(db.Float, default=0, comment="金额")
    location = db.Column(db.String(50), default="", comment="库位")

    material = db.relationship("Material", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "inbound_order_id": self.inbound_order_id,
            "material_id": self.material_id,
            "material_code": self.material.material_code if self.material else None,
            "material_name": self.material.material_name if self.material else None,
            "specification": self.material.specification if self.material else None,
            "unit": self.material.unit if self.material else None,
            "purchase_quantity": self.purchase_quantity or 0,
            "received_quantity": self.received_quantity or 0,
            "inbound_quantity": self.inbound_quantity or 0,
            "unit_price": self.unit_price or 0,
            "amount": self.amount or 0,
            "location": self.location or "",
        }
