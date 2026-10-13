# -*- coding: utf-8 -*-
# ============================================================
# 库存流水表 inventory_ledgers
# ------------------------------------------------------------
# 系统最重要的设计之一：任何库存变化都必须生成一条流水记录，
# 由 services/inventory_service.py 的 change_stock() 统一保证。
# quantity 为带符号的变动量：
#   IN    +20  入库
#   OUT   -20  出库
#   ADJUST -2  盘亏 / +2 盘盈
# 恒等式：before_quantity + quantity = after_quantity
# ============================================================
from datetime import datetime

from extensions import db

# 流水方向
DIRECTION_LABELS = {
    "IN": "入库",
    "OUT": "出库",
    "ADJUST": "库存调整",
}

# 单据类型
DOCUMENT_TYPE_LABELS = {
    "INBOUND": "采购入库",
    "OUTBOUND": "生产领料",
    "STOCKTAKE": "库存盘点",
    "INIT": "期初建账",
}


class InventoryLedger(db.Model):
    """库存流水"""

    __tablename__ = "inventory_ledgers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_no = db.Column(db.String(50), index=True, comment="单据编号")
    document_type = db.Column(db.String(20), index=True, comment="单据类型: INBOUND/OUTBOUND/STOCKTAKE/INIT")
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True, comment="物料ID")
    warehouse = db.Column(db.String(50), default="", comment="仓库")
    location = db.Column(db.String(50), default="", comment="库位")
    direction = db.Column(db.String(10), nullable=False, comment="方向: IN/OUT/ADJUST")
    quantity = db.Column(db.Float, nullable=False, default=0, comment="变动数量(带符号)")
    unit_price = db.Column(db.Float, default=0, comment="单价")
    amount = db.Column(db.Float, default=0, comment="金额")
    before_quantity = db.Column(db.Float, default=0, comment="变动前库存")
    after_quantity = db.Column(db.Float, default=0, comment="变动后库存")
    operator = db.Column(db.String(50), default="", comment="经办人")
    remark = db.Column(db.String(200), default="", comment="备注")
    business_time = db.Column(db.DateTime, default=datetime.now, index=True, comment="业务时间")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    material = db.relationship("Material", lazy="joined")

    def to_dict(self):
        """转为字典（含物料信息）"""
        return {
            "id": self.id,
            "document_no": self.document_no,
            "document_type": self.document_type,
            "document_type_label": DOCUMENT_TYPE_LABELS.get(self.document_type, self.document_type or ""),
            "material_id": self.material_id,
            "material_code": self.material.material_code if self.material else None,
            "material_name": self.material.material_name if self.material else None,
            "warehouse": self.warehouse,
            "location": self.location,
            "direction": self.direction,
            "direction_label": DIRECTION_LABELS.get(self.direction, self.direction or ""),
            "quantity": self.quantity or 0,
            "unit_price": self.unit_price or 0,
            "amount": self.amount or 0,
            "before_quantity": self.before_quantity or 0,
            "after_quantity": self.after_quantity or 0,
            "operator": self.operator,
            "remark": self.remark,
            "business_time": self.business_time.strftime("%Y-%m-%d %H:%M:%S") if self.business_time else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
