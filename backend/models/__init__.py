# -*- coding: utf-8 -*-
# ============================================================
# 模型注册中心
# 所有模型必须在此导入，否则 db.create_all() 无法建表
# 新增模型步骤（详见 README「模块新增方法」）：
#   1. 在本目录新建 xxx.py
#   2. 在此文件 import 该模型
# ============================================================
from models.bom import BOMHeader, BOMItem
from models.inbound import InboundItem, InboundOrder
from models.inventory import Inventory
from models.ledger import InventoryLedger
from models.material import Material
from models.outbound import OutboundItem, OutboundOrder
from models.stocktake import StocktakeItem, StocktakeOrder

__all__ = [
    "Material",
    "Inventory",
    "InventoryLedger",
    "InboundOrder",
    "InboundItem",
    "OutboundOrder",
    "OutboundItem",
    "StocktakeOrder",
    "StocktakeItem",
    "BOMHeader",
    "BOMItem",
]
