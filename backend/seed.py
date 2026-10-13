# -*- coding: utf-8 -*-
# ============================================================
# 演示数据种子脚本
# ------------------------------------------------------------
# 运行方式（在项目根目录）：
#   python backend/seed.py
# 作用：重建数据库并生成完整演示数据（可重复执行，覆盖旧数据）
#
# 生成的演示数据与首页数字完全对应：
#   物料 32 种 / 今日入库 8 单 / 今日出库 6 单 / 待盘点 3 单
#   库存预警：M101 28/30 库存不足；M201 42/40 正常；M301 15/25 库存不足
#
# 数据口径说明：
#   已完工生产领料合计 145 套（今日 80 + 前 3 天 65）
#   全部库存变动均通过 services 层真实业务接口产生库存流水，
#   不存在直接修改库存的数据（期初建账走 INIT 流水）。
# ============================================================
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# 保证在项目根目录执行 python backend/seed.py 时也能正常导入 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from extensions import db
from models.bom import BOMHeader, BOMItem
from models.inbound import InboundOrder
from models.inventory import Inventory
from models.ledger import InventoryLedger
from models.material import Material
from models.outbound import OutboundOrder
from models.stocktake import StocktakeOrder
from services import (
    dashboard_service,
    inbound_service,
    inventory_service,
    material_service,
    outbound_service,
    stocktake_service,
)

TODAY = date.today()

# 每个仓库统一使用一个库位（演示数据从简；二次开发可扩展库位管理）
LOCATION = {"原材料仓": "A区-01", "半成品仓": "B区-01", "成品仓": "C区-01"}

# ------------------------------------------------------------
# 一、物料档案 32 种
# (编码, 名称, 分类, 规格型号, 单位, ABC, 物料类型, 安全库存, 采购提前期, 默认仓库)
# 分类：电子元器件/结构件/电池电源/包装材料/辅料配件/半成品/成品
# ------------------------------------------------------------
MATERIALS = [
    # --- 电子元器件（外购件） ---
    ("M101", "心率PPG传感器", "电子元器件", "MAX30102", "个", "A", "外购件", 30, 7, "原材料仓"),
    ("M102", "血氧传感器模块", "电子元器件", "MAX86178", "个", "A", "外购件", 30, 7, "原材料仓"),
    ("M103", "加速度传感器", "电子元器件", "LIS3DH", "个", "B", "外购件", 15, 7, "原材料仓"),
    ("M104", "温度传感器", "电子元器件", "DS18B20", "个", "B", "外购件", 25, 5, "原材料仓"),
    ("M105", "主控MCU芯片", "电子元器件", "ESP32-C3", "个", "A", "外购件", 10, 10, "原材料仓"),
    # --- 电池电源（外购件） ---
    ("M201", "聚合物锂电池", "电池电源", "3.7V/800mAh", "个", "A", "外购件", 40, 10, "原材料仓"),
    ("M202", "电池保护板", "电池电源", "IP5306", "个", "B", "外购件", 20, 7, "原材料仓"),
    ("M203", "无线充电线圈", "电池电源", "5W/1.5A", "个", "B", "外购件", 12, 7, "原材料仓"),
    ("M204", "Type-C充电接口", "电池电源", "16P母座", "个", "B", "外购件", 12, 5, "原材料仓"),
    ("M205", "电源管理芯片", "电池电源", "TP4056", "个", "B", "外购件", 25, 7, "原材料仓"),
    # --- 结构件（外购件） ---
    ("M301", "项圈外壳组件", "结构件", "ABS+TPU注塑", "套", "B", "外购件", 25, 10, "原材料仓"),
    ("M302", "不锈钢卡扣", "结构件", "316L不锈钢", "个", "C", "外购件", 30, 7, "原材料仓"),
    ("M303", "防水密封圈", "结构件", "食品级硅胶", "个", "C", "外购件", 25, 5, "原材料仓"),
    ("M304", "显示屏模组", "结构件", "0.96寸OLED", "个", "A", "外购件", 10, 7, "原材料仓"),
    # --- 包装材料（外购件） ---
    ("M401", "产品包装盒", "包装材料", "定制彩盒", "个", "C", "外购件", 100, 5, "原材料仓"),
    ("M402", "产品说明书", "包装材料", "中文版", "个", "C", "外购件", 100, 3, "原材料仓"),
    ("M403", "防静电袋", "包装材料", "ESD防静电", "个", "C", "外购件", 100, 3, "原材料仓"),
    ("M404", "电池警示贴纸", "包装材料", "定制印刷", "张", "C", "外购件", 100, 3, "原材料仓"),
    ("M405", "质检合格标签", "包装材料", "合格证", "张", "C", "外购件", 100, 3, "原材料仓"),
    ("M406", "五层瓦楞外箱", "包装材料", "可装20套", "个", "C", "外购件", 50, 5, "原材料仓"),
    ("M407", "不锈钢螺丝", "包装材料", "M1.6×4", "个", "C", "外购件", 200, 3, "原材料仓"),
    ("M408", "防震泡棉垫", "包装材料", "EVA防震", "片", "C", "外购件", 100, 3, "原材料仓"),
    # --- 辅料配件（外购件） ---
    ("M501", "项圈织带", "辅料配件", "尼龙织带", "条", "A", "外购件", 40, 7, "原材料仓"),
    ("M502", "蓝牙天线", "辅料配件", "2.4GHz", "个", "B", "外购件", 12, 7, "原材料仓"),
    ("M503", "蜂鸣器", "辅料配件", "8Ω/85dB", "个", "B", "外购件", 12, 5, "原材料仓"),
    ("M504", "麦克风组件", "辅料配件", "MEMS数字", "个", "B", "外购件", 15, 7, "原材料仓"),
    ("M505", "触控按键模组", "辅料配件", "电容式触控", "个", "B", "外购件", 15, 5, "原材料仓"),
    # --- 半成品 / 成品（自制件） ---
    ("M601", "项圈主控板PCBA", "半成品", "六层板", "块", "A", "自制件", 15, 3, "半成品仓"),
    ("M602", "传感器集成板", "半成品", "四层板", "块", "A", "自制件", 15, 3, "半成品仓"),
    ("M603", "电源管理板", "半成品", "双层板", "块", "B", "自制件", 15, 3, "半成品仓"),
    ("M604", "智能宠物项圈Pro", "成品", "P001成品", "套", "A", "自制件", 10, 1, "成品仓"),
    ("M605", "智能宠物项圈标准版", "成品", "P002成品", "套", "B", "自制件", 10, 1, "成品仓"),
]

# ------------------------------------------------------------
# 二、期初建账（30 天前，INIT 流水，移动平均价以此为准）
# (物料编码, 仓库, 期初数量, 期初单价)
# ------------------------------------------------------------
OPENINGS = [
    # 原材料仓（27 种）
    ("M101", "原材料仓", 130, 8.5),
    ("M102", "原材料仓", 160, 7.8),
    ("M103", "原材料仓", 150, 3.2),
    ("M104", "原材料仓", 175, 2.5),
    ("M105", "原材料仓", 145, 12.5),
    ("M201", "原材料仓", 140, 9.2),
    ("M202", "原材料仓", 140, 2.1),
    ("M203", "原材料仓", 135, 3.5),
    ("M204", "原材料仓", 135, 0.8),
    ("M205", "原材料仓", 155, 1.6),
    ("M301", "原材料仓", 75, 6.5),
    ("M302", "原材料仓", 300, 0.8),
    ("M303", "原材料仓", 145, 0.3),
    ("M304", "原材料仓", 140, 15.5),
    ("M401", "原材料仓", 350, 1.2),
    ("M402", "原材料仓", 350, 0.5),
    ("M403", "原材料仓", 300, 0.2),
    ("M404", "原材料仓", 300, 0.1),
    ("M405", "原材料仓", 280, 0.1),
    ("M406", "原材料仓", 200, 2.5),
    ("M407", "原材料仓", 700, 0.05),
    ("M408", "原材料仓", 450, 0.4),
    ("M501", "原材料仓", 160, 2.8),
    ("M502", "原材料仓", 140, 1.5),
    ("M503", "原材料仓", 140, 0.9),
    ("M504", "原材料仓", 150, 3.8),
    ("M505", "原材料仓", 150, 2.2),
    # 半成品仓（5 种）
    ("M201", "半成品仓", 10, 9.2),
    ("M301", "半成品仓", 5, 6.5),
    ("M601", "半成品仓", 30, 28.0),
    ("M602", "半成品仓", 25, 15.0),
    ("M603", "半成品仓", 20, 12.0),
    # 成品仓（2 种）
    ("M604", "成品仓", 40, 58.0),
    ("M605", "成品仓", 15, 45.0),
]

# ------------------------------------------------------------
# 三、BOM 物料清单（产品 P001 + 半成品 A100~A500）
# 结构：P001 → A100~A500（各×1）→ 物料（27 种叶子）
# 注：BOM 为演示主数据，由本脚本直接生成；
#     TODO-EXTENSION: BOM 维护界面（增删改/版本管理）二期实现
# ------------------------------------------------------------
BOMS = {
    "P001": ("智能宠物健康监测项圈Pro", [
        ("A100", 1, "套"), ("A200", 1, "套"), ("A300", 1, "套"),
        ("A400", 1, "套"), ("A500", 1, "套"),
    ]),
    "A100": ("传感监测模组", [
        ("M101", 1, "个"), ("M102", 1, "个"), ("M103", 1, "个"),
        ("M104", 1, "个"), ("M105", 1, "个"),
    ]),
    "A200": ("电源管理模组", [
        ("M201", 1, "个"), ("M202", 1, "个"), ("M203", 1, "个"),
        ("M204", 1, "个"), ("M205", 1, "个"),
    ]),
    "A300": ("外壳结构组件", [
        ("M301", 1, "套"), ("M302", 2, "个"), ("M303", 1, "个"),
        ("M407", 4, "个"), ("M501", 1, "条"),
    ]),
    "A400": ("显示交互模组", [
        ("M304", 1, "个"), ("M502", 1, "个"), ("M503", 1, "个"),
        ("M504", 1, "个"), ("M505", 1, "个"),
    ]),
    "A500": ("包装组件", [
        ("M401", 1, "个"), ("M402", 1, "个"), ("M403", 1, "个"),
        ("M404", 1, "张"), ("M405", 1, "张"), ("M406", 1, "个"),
        ("M408", 2, "片"),
    ]),
}

# ------------------------------------------------------------
# 四、采购入库单 10 单
# delta：相对今天的天数（0=今天，负数=过去）
# 今日 8 单（IN-1~IN-8：6 已完成 + 1 待审核 + 1 草稿）
# 历史 2 单（IN-9 已完成 / IN-10 已驳回）
# 说明：创建/保存/提交均不改变库存，只有「确认入库」才改变库存。
# ------------------------------------------------------------
INBOUNDS = [
    {"po": "CG20260901", "supplier": "深圳华强电子", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "传感器批量到货",
     "items": [("M101", 30, 8.5), ("M102", 30, 7.8), ("M201", 25, 9.2)]},
    {"po": "CG20260902", "supplier": "东莞富达精密", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "结构件到货",
     "items": [("M301", 50, 6.5), ("M302", 100, 0.8), ("M303", 60, 0.3)]},
    {"po": "CG20260903", "supplier": "深圳华强电子", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "芯片与电池补货",
     "items": [("M101", 13, 8.5), ("M103", 20, 3.2), ("M104", 20, 2.5),
               ("M105", 15, 12.5), ("M201", 12, 9.2)]},
    {"po": "CG20260904", "supplier": "东莞富达精密", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "五金螺丝补充",
     "items": [("M301", 30, 6.5), ("M407", 300, 0.05), ("M501", 80, 2.8)]},
    {"po": "CG20260905", "supplier": "深圳赛格电子", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "电源与声学器件",
     "items": [("M202", 30, 2.1), ("M203", 25, 3.5), ("M204", 25, 0.8),
               ("M205", 20, 1.6), ("M304", 20, 15.5), ("M502", 20, 1.5),
               ("M503", 20, 0.9), ("M504", 15, 3.8), ("M505", 15, 2.2)]},
    {"po": "CG20260906", "supplier": "广州包装制品", "warehouse": "原材料仓", "delta": 0,
     "status": "COMPLETED", "operator": "张伟", "remark": "包材批量到货",
     "items": [("M401", 200, 1.2), ("M402", 200, 0.5), ("M403", 200, 0.2),
               ("M404", 200, 0.1), ("M405", 200, 0.1), ("M406", 100, 2.5),
               ("M408", 300, 0.4)]},
    {"po": "CG20260907", "supplier": "深圳华强电子", "warehouse": "原材料仓", "delta": 0,
     "status": "PENDING", "operator": "张伟", "remark": "待质检，未确认入库",
     "items": [("M105", 20, 12.5), ("M304", 20, 15.5)]},
    {"po": "CG20260908", "supplier": "东莞富达精密", "warehouse": "原材料仓", "delta": 0,
     "status": "DRAFT", "operator": "张伟", "remark": "待补充明细",
     "items": [("M302", 50, 0.8), ("M303", 40, 0.3)]},
    {"po": "CG20260898", "supplier": "深圳赛格电子", "warehouse": "原材料仓", "delta": -2,
     "status": "COMPLETED", "operator": "张伟", "remark": "历史补货",
     "items": [("M103", 15, 3.2), ("M104", 10, 2.5), ("M205", 10, 1.6)]},
    {"po": "CG20260897", "supplier": "广州包装制品", "warehouse": "原材料仓", "delta": -3,
     "status": "REJECTED", "operator": "张伟", "remark": "包装盒印刷色差，验收不合格",
     "items": [("M401", 100, 1.2), ("M402", 100, 0.5)]},
]

# ------------------------------------------------------------
# 五、生产领料出库单 10 单
# 全部按产品 P001 的 BOM 自动生成物料需求（需求 = BOM 用量 × 生产数量）
# 已完工 7 单合计 145 套：今日 80（20+25+15+20）+ 前 3 天 65（25+15+25）
# 今日 6 单（OUT-1~OUT-6：4 已完成 + 2 待审核）
# OUT-10 草稿（生产 50 套）：提交时 M101 库存不足（28 < 50）会被拒绝，
#   可作为「库存不足 → HTTP 400 提示」的课堂演示用例。
# ------------------------------------------------------------
OUTBOUNDS = [
    {"po": "SC20260901", "qty": 20, "delta": 0, "status": "COMPLETED",
     "department": "生产一部", "remark": "9月第1批生产计划"},
    {"po": "SC20260902", "qty": 25, "delta": 0, "status": "COMPLETED",
     "department": "生产一部", "remark": "9月第2批生产计划"},
    {"po": "SC20260903", "qty": 15, "delta": 0, "status": "COMPLETED",
     "department": "生产二部", "remark": "9月第3批生产计划"},
    {"po": "SC20260904", "qty": 20, "delta": 0, "status": "COMPLETED",
     "department": "生产二部", "remark": "9月第4批生产计划"},
    {"po": "SC20260905", "qty": 5, "delta": 0, "status": "PENDING",
     "department": "生产一部", "remark": "加急小批量，待审核"},
    {"po": "SC20260906", "qty": 8, "delta": 0, "status": "PENDING",
     "department": "生产二部", "remark": "样品试制，待审核"},
    {"po": "SC20260815", "qty": 25, "delta": -3, "status": "COMPLETED",
     "department": "生产一部", "remark": "8月生产计划"},
    {"po": "SC20260820", "qty": 15, "delta": -2, "status": "COMPLETED",
     "department": "生产一部", "remark": "8月追加计划"},
    {"po": "SC20260825", "qty": 25, "delta": -1, "status": "COMPLETED",
     "department": "生产二部", "remark": "8月备货计划"},
    {"po": "SC20260910", "qty": 50, "delta": -1, "status": "DRAFT",
     "department": "生产一部", "remark": "演示数据：提交时 M101 库存不足(28<50)被拒"},
]

# ------------------------------------------------------------
# 六、库存盘点单 4 单
# ST-1 已完成（M104 盘亏 3 / M405 盘盈 5，已生成 ADJUST 流水）
# ST-2 盘点中 / ST-3、ST-4 待复核 → 待盘点任务 3 单
# ------------------------------------------------------------
STOCKTAKES = [
    {"warehouse": "原材料仓", "type": "FULL", "delta": -2, "operator": "李丽",
     "remark": "月度例行盘点",
     "fill_overrides": {"M104": -3, "M405": 5},
     "reasons": {"M104": "传感器端子氧化报废（盘亏）", "M405": "贴纸清点溢出（盘盈）"},
     "adjust": True},
    {"warehouse": "原材料仓", "type": "SAMPLE", "delta": 0, "operator": "李丽",
     "remark": "重点物料抽查（演示：未录入实盘，可直接体验录入）"},
    {"warehouse": "半成品仓", "type": "FULL", "delta": 0, "operator": "赵敏",
     "remark": "半成品仓月度盘点",
     "fill_overrides": {"M201": 2, "M301": -1},
     "reasons": {"M201": "线边库存转回（盘盈）", "M301": "线边领用补录差异（盘亏）"}},
    {"warehouse": "原材料仓", "type": "CYCLE", "delta": 0, "operator": "李丽",
     "remark": "循环盘点（账实一致，待复核）",
     "fill_all": True},
]


# ============================================================
# 种子数据生成入口
# ============================================================
def seed():
    app = create_app()
    with app.app_context():
        print("正在重建数据库 ...")
        db.drop_all()
        db.create_all()

        # ---------- 1. 物料档案（走 material_service 真实接口） ----------
        print("生成物料档案 32 种 ...")
        mat_ids = {}
        for code, name, category, spec, unit, abc, mtype, safety, lead, wh in MATERIALS:
            m = material_service.create_material({
                "material_code": code,
                "material_name": name,
                "category": category,
                "specification": spec,
                "unit": unit,
                "abc_class": abc,
                "material_type": mtype,
                "safety_stock": safety,
                "purchase_lead_time": lead,
                "default_warehouse": wh,
                "status": "active",
            })
            mat_ids[code] = m["id"]
        materials = {code: db.session.get(Material, mid) for code, mid in mat_ids.items()}

        # ---------- 2. BOM 结构（产品 + 半成品，直接写主数据） ----------
        print("生成 BOM 结构（P001 + A100~A500） ...")
        for code, (name, items) in BOMS.items():
            header = BOMHeader(product_code=code, product_name=name,
                               version="V1.0", status="active")
            db.session.add(header)
            db.session.flush()
            for child_code, qty, unit in items:
                db.session.add(BOMItem(
                    bom_id=header.id,
                    parent_code=code,
                    material_code=child_code,
                    quantity=qty,
                    unit=unit,
                    level=1,
                ))
        db.session.commit()

        # ---------- 3. 期初建账（INIT 流水，一次事务整体提交） ----------
        print("生成期初库存与 INIT 流水 ...")
        init_time = datetime.combine(TODAY - timedelta(days=30), time(9, 0))
        for code, wh, qty, price in OPENINGS:
            inventory_service.change_stock(
                material=materials[code],
                warehouse=wh,
                location=LOCATION[wh],
                change_qty=qty,
                direction="IN",
                document_no=f"INIT-{code}",
                document_type="INIT",
                operator="系统管理员",
                unit_price=price,
                business_time=init_time,
                remark="期初建账",
            )
        # 半成品仓 M204 无期初结存，建一条 0 库存记录供盘点演示（无差异行）
        db.session.add(Inventory(
            material_id=mat_ids["M204"], warehouse="半成品仓",
            location=LOCATION["半成品仓"], quantity=0,
            available_quantity=0, occupied_quantity=0,
            average_price=0.8, inventory_amount=0,
        ))
        db.session.commit()

        # ---------- 4. 采购入库（走 inbound_service 完整业务流程） ----------
        print("生成采购入库单 10 单 ...")
        for data in INBOUNDS:
            order = inbound_service.create_order({
                "purchase_order_no": data["po"],
                "supplier": data["supplier"],
                "warehouse": data["warehouse"],
                "inbound_date": (TODAY + timedelta(days=data["delta"])).isoformat(),
                "operator": data["operator"],
                "remark": data["remark"],
                "items": [{
                    "material_id": mat_ids[code],
                    "purchase_quantity": qty,
                    "inbound_quantity": qty,
                    "unit_price": price,
                    "location": LOCATION[data["warehouse"]],
                } for code, qty, price in data["items"]],
            })
            if data["status"] == "PENDING":
                inbound_service.submit_order(order["id"])
            elif data["status"] == "COMPLETED":
                inbound_service.submit_order(order["id"])
                inbound_service.confirm_order(order["id"])  # 唯一真正入库存的入口
            elif data["status"] == "REJECTED":
                row = db.session.get(InboundOrder, order["id"])
                row.status = "REJECTED"  # 历史驳回单（未入库存）
                db.session.commit()

        # ---------- 5. 生产领料（走 outbound_service 完整业务流程） ----------
        print("生成生产领料出库单 10 单 ...")
        for data in OUTBOUNDS:
            order = outbound_service.create_order({
                "production_order_no": data["po"],
                "product_code": "P001",
                "production_quantity": data["qty"],
                "department": data["department"],
                "warehouse": "原材料仓",
                "outbound_date": (TODAY + timedelta(days=data["delta"])).isoformat(),
                "operator": "王强",
                "remark": data["remark"],
            })
            if data["status"] == "PENDING":
                outbound_service.submit_order(order["id"])
            elif data["status"] == "COMPLETED":
                outbound_service.submit_order(order["id"])
                outbound_service.confirm_order(order["id"])  # 唯一真正出库存的入口

        # ---------- 6. 库存盘点（走 stocktake_service 完整业务流程） ----------
        print("生成库存盘点单 4 单 ...")
        for data in STOCKTAKES:
            order = stocktake_service.create_order({
                "warehouse": data["warehouse"],
                "stocktake_type": data["type"],
                "stocktake_date": (TODAY + timedelta(days=data["delta"])).isoformat(),
                "operator": data["operator"],
                "remark": data["remark"],
            })
            overrides = data.get("fill_overrides") or {}
            if data.get("fill_all") or overrides:
                items = []
                for it in order["items"]:
                    actual = round((it["system_quantity"] or 0) + overrides.get(it["material_code"], 0), 4)
                    items.append({
                        "id": it["id"],
                        "actual_quantity": actual,
                        "difference_reason": (data.get("reasons") or {}).get(it["material_code"], ""),
                    })
                stocktake_service.update_order(order["id"], {"items": items})
                stocktake_service.submit_order(order["id"])
                if data.get("adjust"):
                    stocktake_service.adjust_order(order["id"])  # 唯一真正调整库存的入口

        # ---------- 7. 数据校验输出 ----------
        print()
        print("=" * 62)
        print("演示数据生成完成！")
        print("=" * 62)
        print(f"物料档案   : {Material.query.count()} 种（A/B/C 分类齐全）")
        print(f"BOM 结构   : {BOMHeader.query.count()} 个（产品 1 + 半成品 5）")
        print(f"库存记录   : {Inventory.query.count()} 条（原材料仓 27 / 半成品仓 6 / 成品仓 2）")
        print(f"库存流水   : {InventoryLedger.query.count()} 条（含 INIT/INBOUND/OUTBOUND/STOCKTAKE）")
        print(f"采购入库单 : {InboundOrder.query.count()} 单")
        print(f"生产领料单 : {OutboundOrder.query.count()} 单")
        print(f"库存盘点单 : {StocktakeOrder.query.count()} 单")
        print("-" * 62)
        s = dashboard_service.get_summary()
        print(f"首页校验   : 物料 {s['material_count']} / 今日入库 {s['today_inbound_count']} "
              f"/ 今日出库 {s['today_outbound_count']} / 待盘点 {s['pending_stocktake_count']}")
        print(f"库存预警   : 共 {s['warning_count']} 种不足")
        for w in s["warnings"]:
            print(f"    {w['material_code']} {w['material_name']}: "
                  f"{w['current_stock']}/{w['safety_stock']} {w['status']}")
        print("=" * 62)
        print("下一步：python backend/app.py 启动后端，")
        print("        然后 python -m http.server 8000 --directory frontend 启动前端")
        print("        访问 http://localhost:8000 登录演示系统")


if __name__ == "__main__":
    seed()
