# -*- coding: utf-8 -*-
# ============================================================
# 物料档案表 materials
# ============================================================
from datetime import datetime

from extensions import db

# 物料状态
MATERIAL_STATUS = {
    "active": "启用",
    "inactive": "停用",
}


class Material(db.Model):
    """物料档案"""

    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_code = db.Column(db.String(50), unique=True, nullable=False, index=True, comment="物料编码")
    material_name = db.Column(db.String(100), nullable=False, comment="物料名称")
    category = db.Column(db.String(50), default="", comment="物料分类")
    specification = db.Column(db.String(200), default="", comment="规格型号")
    unit = db.Column(db.String(20), default="个", comment="计量单位")
    abc_class = db.Column(db.String(5), default="C", comment="ABC分类: A/B/C")
    material_type = db.Column(db.String(20), default="外购件", comment="物料类型: 外购件/自制件/委外件")
    safety_stock = db.Column(db.Float, default=0, comment="安全库存")
    purchase_lead_time = db.Column(db.Integer, default=0, comment="采购提前期(天)")
    default_warehouse = db.Column(db.String(50), default="", comment="默认仓库")
    status = db.Column(db.String(20), default="active", comment="状态: active/inactive")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        """转为字典（JSON 序列化）"""
        return {
            "id": self.id,
            "material_code": self.material_code,
            "material_name": self.material_name,
            "category": self.category or "",
            "specification": self.specification or "",
            "unit": self.unit or "个",
            "abc_class": self.abc_class or "C",
            "material_type": self.material_type or "外购件",
            "safety_stock": self.safety_stock or 0,
            "purchase_lead_time": self.purchase_lead_time or 0,
            "default_warehouse": self.default_warehouse or "",
            "status": self.status or "active",
            "status_label": MATERIAL_STATUS.get(self.status, self.status),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
