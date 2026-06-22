import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000/api/v1"


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_full_workflow():
    print_section("牙科订单协同服务 - 完整流程演示")

    headers = {"Content-Type": "application/json"}

    print_section("步骤1: 获取诊所列表")
    resp = requests.get(f"{BASE_URL}/clinics")
    clinics = resp.json()["data"]["items"]
    print(f"获取到 {len(clinics)} 个诊所:")
    for c in clinics:
        print(f"  [{c['id']}] {c['name']} - {c['contact_person']}")
    clinic_id = clinics[0]["id"]
    clinic_name = clinics[0]["name"]

    print_section("步骤2: 获取产品列表（查看同名不同规格）")
    resp = requests.get(f"{BASE_URL}/products", params={"keyword": "纳米树脂"})
    products = resp.json()["data"]["items"]
    print(f"搜索'纳米树脂'找到 {len(products)} 个产品（同名不同规格示例）:")
    for p in products:
        print(f"  [{p['id']}] {p['brand']} {p['name']} {p['specification']} - 库存:{p['stock']}")

    print_section("步骤3: 创建订单 (微信来单)")
    order_data = {
        "clinic_id": clinic_id,
        "clinic_name": clinic_name,
        "source": "wechat",
        "source_detail": "wx_zhangsan",
        "raw_content": "3M树脂A2两支、麻醉针30G一盒、洁牙头五支、碧兰麻10支、斯康杜尼5支、酸蚀剂2瓶",
        "customer_remark": "请尽快发货，今天下午有手术",
        "urgent_note": "下午手术前必须到",
        "status": "pending_c"
    }
    resp = requests.post(f"{BASE_URL}/orders", params={"created_by": "客服小王"}, json=order_data)
    order = resp.json()["data"]
    order_id = order["id"]
    order_no = order["order_no"]
    print(f"订单创建成功:")
    print(f"  订单号: {order_no}")
    print(f"  诊所: {order['clinic_name']}")
    print(f"  来源: {order['source']}")
    print(f"  原始内容: {order['raw_content']}")
    print(f"  紧急备注: {order['urgent_note']}")
    print(f"  当前状态: {order['status']}")

    print_section("步骤4: 订单整理 - 预整理（自动识别+防错提示）")
    resp = requests.get(f"{BASE_URL}/workspace/collate/preview/{order_id}")
    collate_preview = resp.json()["data"]
    print(f"预整理结果:")
    print(f"  警告信息: {collate_preview['warnings']}")
    print(f"\n  明细项:")
    for idx, item in enumerate(collate_preview["items"]):
        print(f"\n  [{idx+1}] 原始文本: {item['raw_text']}")
        print(f"      匹配产品: {item['product_name']} {item['specification']}")
        print(f"      品牌: {item['brand']}, 数量: {item['quantity']}{item['unit']}")
        print(f"      匹配度: {item['match_confidence']:.0%}")
        print(f"      已自动确认: {item['manual_confirmed']}")
        if item['has_same_name_diff_spec']:
            print(f"      ⚠️  存在同名不同规格: {len(item['same_name_products'])} 个")
            for alt in item['same_name_products']:
                print(f"         - {alt['brand']} {alt['specification']} (ID:{alt['id']})")
        if item['remark']:
            print(f"      备注: {item['remark']}")

    print_section("步骤5: 人工确认后提交整理结果")

    quantity_fixes = {
        "3M树脂A2两支": 2,
        "麻醉针30G一盒": 1,
        "洁牙头五支": 5,
    }

    for item in collate_preview["items"]:
        item["manual_confirmed"] = True
        if item["quantity"] is None and item["raw_text"] in quantity_fixes:
            item["quantity"] = quantity_fixes[item["raw_text"]]
        if item["quantity"] is None:
            item["quantity"] = 1

    confirm_data = {
        "order_id": order_id,
        "items": collate_preview["items"],
        "operator": "客服小王"
    }
    resp = requests.post(f"{BASE_URL}/workspace/collate/confirm", json=confirm_data)
    result = resp.json()
    print(f"整理提交结果: {result['message']}")
    print(f"  成功: {result['data']['success']}")

    print_section("步骤6: 查看订单（已生成订单项）")
    resp = requests.get(f"{BASE_URL}/orders/{order_id}")
    order = resp.json()["data"]
    print(f"订单状态: {order['status']}")
    print(f"整理人: {order['collated_by']}")
    print(f"整理时间: {order['collated_at']}")
    print(f"\n订单项:")
    for item in order["items"]:
        print(f"  [{item['id']}] {item['product_name']} {item['product_spec']} × {item['quantity']}{item['unit']}")

    print_section("步骤7: 缺货检查")
    resp = requests.get(f"{BASE_URL}/workspace/stock/check/{order_id}")
    stock_result = resp.json()["data"]
    print(f"是否缺货: {stock_result['has_stock_out']}")
    if stock_result["all_in_stock_items"]:
        print(f"\n✅ 有货商品:")
        for item in stock_result["all_in_stock_items"]:
            print(f"  {item['product_name']} {item['specification']} × {item['quantity']} (库存:{item['stock_available']})")
    if stock_result["stock_out_items"]:
        print(f"\n❌ 缺货商品:")
        for item in stock_result["stock_out_items"]:
            print(f"\n  {item['product_name']} {item['specification']}")
            print(f"    需求: {item['required_quantity']}, 库存: {item['stock_available']}, 缺货: {item['stock_out_quantity']}")
            if item['alternative_product_name']:
                print(f"    💡 建议替代: {item['alternative_product_name']} {item['alternative_spec']}")

    print_section("步骤8: 处理缺货（选择方案）")
    stock_items = stock_result["stock_out_items"]
    print(f"缺货商品数量: {len(stock_items)}")

    stock_items[0]["alternative_product_id"] = 4
    stock_items[0]["alternative_product_name"] = "碧兰麻"
    stock_items[0]["alternative_spec"] = "1.7ml/支"
    stock_items[0]["process_remark"] = "客户同意换碧兰麻替代斯康杜尼"

    stock_items[1]["expected_restock_date"] = str(date.today())
    stock_items[1]["process_remark"] = "客户愿意等酸蚀剂补货，下周一起补发"

    process_data = {
        "order_id": order_id,
        "items": stock_items,
        "operator": "客服小王"
    }
    resp = requests.post(f"{BASE_URL}/workspace/stock/process", json=process_data)
    result = resp.json()
    print(f"库存处理结果: {result['message']}")

    print_section("步骤9: 生成给诊所的回复")
    reply_data = {
        "order_id": order_id,
        "stock_out_items": stock_items
    }
    resp = requests.post(f"{BASE_URL}/workspace/stock/generate-reply", json=reply_data)
    reply = resp.json()["data"]
    print(f"回复摘要: {reply['summary']}")
    print(f"\n回复内容:")
    print("-" * 60)
    print(reply["reply_content"])
    print("-" * 60)

    print_section("步骤10: 创建配送交接单")
    resp = requests.post(f"{BASE_URL}/workspace/delivery/create/{order_id}")
    handover = resp.json()["data"]
    print(f"交接单创建成功 (ID: {handover['id']})")
    print(f"  紧急程度: {handover['urgency']}")
    print(f"  加急说明: {handover['urgency_note']}")
    print(f"  物品总数: {handover['total_items']}")
    print(f"  状态: {handover['status']}")
    print(f"\n  物品清单:")
    for line in handover["items_summary"].split("\n"):
        print(f"    {line}")

    print_section("步骤11: 仓库视图 - 待打包列表")
    resp = requests.get(f"{BASE_URL}/workspace/delivery/warehouse/list")
    warehouse_list = resp.json()["data"]["items"]
    print(f"仓库待处理: {len(warehouse_list)} 单")
    for h in warehouse_list:
        urgency_tag = "🔴" if h['urgency'] == 'urgent_surgery' else "🟠" if h['urgency'] == 'urgent_today' else "🟢"
        print(f"  {urgency_tag} [{h['id']}] {h['order_no']} - {h['clinic_name']}")
        print(f"     {h['urgency_note']}")

    print_section("步骤12: 更新配送信息（仓库打包完成）")
    update_data = {
        "package_note": "已核对物品，洁牙头换为啄木鸟P1，注意告知客户",
        "driver_note": "朝阳区建国路88号，张医生 13800138001",
        "status": "packed",
        "operator": "仓库老李"
    }
    resp = requests.put(f"{BASE_URL}/workspace/delivery/{handover['id']}", json=update_data)
    result = resp.json()
    print(f"更新结果: {result['message']}")

    print_section("步骤13: 司机视图 - 待配送列表")
    resp = requests.get(f"{BASE_URL}/workspace/delivery/driver/list")
    driver_list = resp.json()["data"]["items"]
    print(f"司机待配送: {len(driver_list)} 单")
    for h in driver_list:
        urgency_tag = "🔴" if h['urgency'] == 'urgent_surgery' else "🟠" if h['urgency'] == 'urgent_today' else "🟢"
        print(f"  {urgency_tag} [{h['id']}] {h['clinic_name']}")
        print(f"     {h['urgency_note']}")
        print(f"     司机备注: {h['driver_note']}")

    print_section("步骤14: 查看加急统计")
    resp = requests.get(f"{BASE_URL}/workspace/delivery/statistics/urgency")
    stats = resp.json()["data"]
    print(f"当前待处理加急统计:")
    print(f"  🔴 手术加急: {stats.get('urgent_surgery', 0)} 单")
    print(f"  🟠 今日加急: {stats.get('urgent_today', 0)} 单")
    print(f"  🟢 常规配送: {stats.get('normal', 0)} 单")
    print(f"  ⚪ 下次批次: {stats.get('next_batch', 0)} 单")

    print_section("步骤15: 司机发货、签收完成")
    update_data = {
        "status": "dispatched",
        "operator": "司机老赵"
    }
    resp = requests.put(f"{BASE_URL}/workspace/delivery/{handover['id']}", json=update_data)
    print(f"发货: {resp.json()['message']}")

    update_data = {
        "status": "delivered",
        "operator": "张医生"
    }
    resp = requests.put(f"{BASE_URL}/workspace/delivery/{handover['id']}", json=update_data)
    print(f"签收: {resp.json()['message']}")

    print_section("步骤16: 查看最终订单状态")
    resp = requests.get(f"{BASE_URL}/orders/{order_id}")
    order = resp.json()["data"]
    print(f"订单号: {order['order_no']}")
    print(f"当前状态: {order['status']}")
    print(f"整理人: {order['collated_by']}")
    print(f"库存确认人: {order['stock_checked_by']}")
    print(f"配送安排人: {order['delivery_arranged_by']}")

    print_section("✅ 完整流程演示完成!")


if __name__ == "__main__":
    try:
        test_full_workflow()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请先启动服务:")
        print("   1. 安装依赖: pip install -r requirements.txt")
        print("   2. 初始化数据: python init_data.py")
        print("   3. 启动服务: python main.py")
        print("   4. 运行测试: python test_demo.py")
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
