# -*- coding: utf-8 -*-
# ============================================================
# 生产领料出库单据：outbound_orders（主表）+ outbound_items（明细）
# ------------------------------------------------------------
# 业务流程：
#   创建出库单 → 选择生产工单/产品/数量 → 按 BOM 自动生成物料需求
#   → 提交时检查库存（available_quantity >= outbound_quantity）
#   → 确认出库（事务内：扣减 Inventory + 生成 OUT 流水）。
# ============================================================
from datetime import datetime

from extensions import db

# 出库单状态
OUTBOUND_STATUS_LABELS = {
    "DRAFT": "草稿",
    "PENDING": "待审核",
    "COMPLETED": "已完成",
    "REJECTED": "已驳回",
}


class OutboundOrder(db.Model):
    """生产领料出库单主表"""

    __tablename__ = "outbound_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    outbound_no = db.Column(db.String(50), unique=True, nullable=False, index=True, comment="出库单号")
    production_order_no = db.Column(db.String(50), default="", comment="生产工单号")
    product_code = db.Column(db.String(50), default="", comment="产品编码")
    product_name = db.Column(db.String(100), default="", comment="产品名称")
    production_quantity = db.Column(db.Float, default=0, comment="计划生产数量")
    department = db.Column(db.String(50), default="", comment="领料部门")
    warehouse = db.Column(db.String(50), default="", comment="仓库")
    outbound_date = db.Column(db.Date, default=datetime.now().date, index=True, comment="出库日期")
    operator = db.Column(db.String(50), default="", comment="经办人")
    status = db.Column(db.String(20), default="DRAFT", index=True, comment="状态: DRAFT/PENDING/COMPLETED/REJECTED")
    remark = db.Column(db.String(200), default="", comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    items = db.relationship("OutboundItem", backref="order", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        """转为字典；include_items=True 时携带明细"""
        data = {
            "id": self.id,
            "outbound_no": self.outbound_no,
            "production_order_no": self.production_order_no or "",
            "product_code": self.product_code or "",
            "product_name": self.product_name or "",
            "production_quantity": self.production_quantity or 0,
            "department": self.department or "",
            "warehouse": self.warehouse or "",
            "outbound_date": self.outbound_date.strftime("%Y-%m-%d") if self.outbound_date else None,
            "operator": self.operator or "",
            "status": self.status,
            "status_label": OUTBOUND_STATUS_LABELS.get(self.status, self.status),
            "remark": self.remark or "",
            "item_count": len(self.items),
            "total_quantity": sum(i.outbound_quantity or 0 for i in self.items),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items]
        return data


class OutboundItem(db.Model):
    """生产领料出库单明细（由 BOM 自动生成）"""

    __tablename__ = "outbound_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    outbound_order_id = db.Column(db.Integer, db.ForeignKey("outbound_orders.id"), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True)
    bom_quantity = db.Column(db.Float, default=0, comment="BOM单位用量")
    required_quantity = db.Column(db.Float, default=0, comment="需求数量 = BOM单位用量 × 生产数量")
    outbound_quantity = db.Column(db.Float, default=0, comment="本次出库数量")
    location = db.Column(db.String(50), default="", comment="库位")

    material = db.relationship("Material", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "outbound_order_id": self.outbound_order_id,
            "material_id": self.material_id,
            "material_code": self.material.material_code if self.material else None,
            "material_name": self.material.material_name if self.material else None,
            "specification": self.material.specification if self.material else None,
            "unit": self.material.unit if self.material else None,
            "bom_quantity": self.bom_quantity or 0,
            "required_quantity": self.required_quantity or 0,
            "outbound_quantity": self.outbound_quantity or 0,
            "location": self.location or "",
        }
