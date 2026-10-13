# -*- coding: utf-8 -*-
# ============================================================
# 库存盘点单据：stocktake_orders（主表）+ stocktake_items（明细）
# ------------------------------------------------------------
# 业务流程：
#   创建盘点任务（系统保存当前账面库存快照）
#   → 工作人员填写实盘数量
#   → 系统自动计算差异（actual - system）并判定 盘盈/盘亏/正常
#   → 提交审核 → 确认调整（事务内：更新 Inventory + 生成 ADJUST 流水）
# ------------------------------------------------------------
# 注意：盘点不能直接覆盖数据库库存，必须先产生差异记录，
# 经过「确认调整」后才允许修改库存。
# ============================================================
from datetime import datetime

from extensions import db

# 盘点单状态
STOCKTAKE_STATUS_LABELS = {
    "DRAFT": "草稿",
    "COUNTING": "盘点中",
    "PENDING_REVIEW": "待审核",
    "COMPLETED": "已完成",
}

# 差异类型
DIFFERENCE_LABELS = {
    "NORMAL": "正常",
    "SURPLUS": "盘盈",
    "SHORTAGE": "盘亏",
}

# 调整状态
ADJUSTMENT_LABELS = {
    "PENDING": "待调整",
    "ADJUSTED": "已调整",
    "SKIPPED": "无差异",
}


class StocktakeOrder(db.Model):
    """库存盘点单主表"""

    __tablename__ = "stocktake_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stocktake_no = db.Column(db.String(50), unique=True, nullable=False, index=True, comment="盘点单号")
    warehouse = db.Column(db.String(50), default="", comment="盘点仓库")
    stocktake_type = db.Column(db.String(20), default="FULL", comment="盘点类型: FULL/SAMPLE/CYCLE")
    operator = db.Column(db.String(50), default="", comment="盘点人")
    stocktake_date = db.Column(db.Date, default=datetime.now().date, index=True, comment="盘点日期")
    status = db.Column(db.String(20), default="DRAFT", index=True, comment="状态: DRAFT/COUNTING/PENDING_REVIEW/COMPLETED")
    remark = db.Column(db.String(200), default="", comment="备注")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    items = db.relationship("StocktakeItem", backref="order", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        """转为字典；include_items=True 时携带明细"""
        items = self.items
        data = {
            "id": self.id,
            "stocktake_no": self.stocktake_no,
            "warehouse": self.warehouse or "",
            "stocktake_type": self.stocktake_type or "FULL",
            "operator": self.operator or "",
            "stocktake_date": self.stocktake_date.strftime("%Y-%m-%d") if self.stocktake_date else None,
            "status": self.status,
            "status_label": STOCKTAKE_STATUS_LABELS.get(self.status, self.status),
            "remark": self.remark or "",
            "item_count": len(items),
            "difference_count": sum(1 for i in items if i.difference_quantity not in (None, 0)),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in items]
        return data


class StocktakeItem(db.Model):
    """库存盘点单明细（创建时保存账面库存快照）"""

    __tablename__ = "stocktake_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stocktake_order_id = db.Column(db.Integer, db.ForeignKey("stocktake_orders.id"), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True)
    location = db.Column(db.String(50), default="", comment="库位(创建时快照)")
    system_quantity = db.Column(db.Float, default=0, comment="系统账面库存(创建时快照)")
    actual_quantity = db.Column(db.Float, nullable=True, comment="实盘数量")
    difference_quantity = db.Column(db.Float, nullable=True, comment="差异数量 = 实盘 - 系统")
    difference_type = db.Column(db.String(10), default="NORMAL", comment="差异类型: NORMAL/SURPLUS/SHORTAGE")
    difference_reason = db.Column(db.String(200), default="", comment="差异原因")
    adjustment_status = db.Column(db.String(10), default="PENDING", comment="调整状态: PENDING/ADJUSTED/SKIPPED")

    material = db.relationship("Material", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "stocktake_order_id": self.stocktake_order_id,
            "material_id": self.material_id,
            "material_code": self.material.material_code if self.material else None,
            "material_name": self.material.material_name if self.material else None,
            "specification": self.material.specification if self.material else None,
            "unit": self.material.unit if self.material else None,
            "location": self.location or "",
            "system_quantity": self.system_quantity or 0,
            "actual_quantity": self.actual_quantity if self.actual_quantity is not None else None,
            "difference_quantity": self.difference_quantity if self.difference_quantity is not None else None,
            "difference_type": self.difference_type,
            "difference_type_label": DIFFERENCE_LABELS.get(self.difference_type, self.difference_type or ""),
            "difference_reason": self.difference_reason or "",
            "adjustment_status": self.adjustment_status,
            "adjustment_status_label": ADJUSTMENT_LABELS.get(self.adjustment_status, self.adjustment_status or ""),
        }
