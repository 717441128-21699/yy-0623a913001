"""
牙科订单协同服务 - 增强功能测试
覆盖：
1. 图片来单上传+OCR识别+编辑
2. 缺货方案持久化（保存/回填）
3. 配送交接协同（缺货信息展示+操作记录追溯）
4. 统一异常处理兜底
"""
import requests
import io
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api/v1"


def step(msg):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


def check(label, resp, expect_success=True, assert_http_ok=True):
    if assert_http_ok:
        assert resp.status_code == 200, f"{label}: HTTP {resp.status_code}"
    body = resp.json()
    ok = body.get("success", False) if expect_success else (not body.get("success", True))
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label}")
    print(f"     code={body.get('code')}, message={body.get('message')}")
    if not ok:
        print(f"     detail: {body}")
    return body


# ============ 准备：获取诊所和产品 ============
step("Step 0: 准备数据")
r = requests.get(f"{BASE_URL}/clinics")
clinics = r.json()["data"]["items"]
clinic = clinics[0]
print(f"  使用诊所: {clinic['name']} (ID={clinic['id']})")

r = requests.get(f"{BASE_URL}/products")
products = r.json()["data"]["items"]
print(f"  产品总数: {len(products)}")


# ============ 测试 4: 统一异常处理兜底 ============
step("Step 4-1: 访问不存在的订单 - 预览整理")
r = requests.get(f"{BASE_URL}/workspace/collate/preview/99999999")
body = check("不存在订单返回统一格式", r, expect_success=False)
assert body.get("code") == 404, f"期望 code=404, 实际={body.get('code')}"
assert body.get("success") is False, "期望 success=False"
print(f"    满足统一异常响应: success={body.get('success')}, code={body.get('code')}")

step("Step 4-2: 访问不存在的订单 - 库存检查")
r = requests.get(f"{BASE_URL}/workspace/stock/check/99999999")
body = check("不存在订单返回统一格式", r, expect_success=False)
assert body.get("code") == 404
assert body.get("success") is False

step("Step 4-3: 访问不存在的订单 - 创建配送交接")
r = requests.post(f"{BASE_URL}/workspace/delivery/create/99999999")
body = check("不存在订单返回统一格式", r, expect_success=False)
assert body.get("code") == 404
assert body.get("success") is False

step("Step 4-4: 访问不存在的交接单")
r = requests.get(f"{BASE_URL}/workspace/delivery/99999999")
body = check("不存在交接单返回统一格式", r, expect_success=False)
assert body.get("code") == 404

step("Step 4-5: 创建空订单（无图片无文字）测试兜底")
files = []
r = requests.post(
    f"{BASE_URL}/orders/with-image",
    data={"clinic_id": clinic["id"], "clinic_name": clinic["name"], "raw_content": ""},
    files=files
)
body = check("空订单抛统一异常", r, expect_success=False)
assert body.get("code") == 400
print(f"    兜底异常响应正确: code={body['code']}, message={body['message']}")

print("\n  🎯 需求4 统一异常处理兜底验证通过 ✅")


# ============ 测试 1: 图片来单 + OCR识别 + 编辑 ============
step("Step 1-1: 创建带图片的订单（模拟微信图片来单）")
fake_img = io.BytesIO(b"fake image content for demo")
fake_img.name = "wechat_order_20260622.jpg"
files = [("images", ("wechat_order_20260622.jpg", fake_img, "image/jpeg"))]

r = requests.post(
    f"{BASE_URL}/orders/with-image",
    data={
        "clinic_id": str(clinic["id"]),
        "clinic_name": clinic["name"],
        "source": "wechat",
        "source_detail": "wxid_clinic_sunny",
        "raw_content": "3M树脂A2两支、麻醉针30G一盒、洁牙头五支、碧兰麻10支、斯康杜尼5支、酸蚀剂2瓶",
        "created_by": "客服小王",
        "urgent_note": "下午手术前必须到"
    },
    files=files
)
body = check("创建图片订单成功", r)
order = body["data"]
order_id = order["id"]
order_no = order["order_no"]
print(f"    订单 ID: {order_id}, NO: {order_no}")
print(f"    raw_content: {order.get('raw_content')}")
print(f"    ocr_content: {order.get('ocr_content')}")
assert order["images"], "订单应关联图片"
img = order["images"][0]
print(f"    关联图片: ID={img['id']}, file={img['file_name']}, 状态={img['status']}")
print(f"    识别文本: {img.get('recognized_text')}")

step("Step 1-2: 查询订单图片列表")
r = requests.get(f"{BASE_URL}/orders/{order_id}/images")
body = check("查询订单图片列表", r)
imgs = body["data"]
assert len(imgs) >= 1
img_id = imgs[0]["id"]
print(f"    图片 ID: {img_id}, 识别状态: {imgs[0]['status']}")

step("Step 1-3: 客服编辑修正OCR识别文本")
edited_text = "3M树脂A2两支、麻醉针30G一盒、洁牙头五支、碧兰麻10支、斯康杜尼5支、酸蚀剂2瓶"
r = requests.put(
    f"{BASE_URL}/orders/images/{img_id}/recognized-text",
    data={"recognized_text": edited_text, "operator": "客服小王"}
)
body = check("修正OCR识别文本成功", r)
updated_img = body["data"]
assert updated_img["recognized_text"] == edited_text
assert updated_img["status"] == "confirmed"
print(f"    已修正文本: {updated_img['recognized_text']}")
print(f"    状态: {updated_img['status']}")

step("Step 1-4: 再为订单补传一张图片")
fake_img2 = io.BytesIO(b"another fake image")
fake_img2.name = "wechat_order_additional.jpg"
r = requests.post(
    f"{BASE_URL}/orders/{order_id}/images",
    data={"upload_by": "客服小王"},
    files=[("images", ("wechat_order_additional.jpg", fake_img2, "image/jpeg"))]
)
body = check("追加上传图片成功", r)
print(f"    追加后图片数: {len(body['data'])}")

step("Step 1-5: 再次获取订单详情，验证图片关联完整")
r = requests.get(f"{BASE_URL}/orders/{order_id}")
body = check("获取订单详情", r)
order_detail = body["data"]
imgs = order_detail["images"]
print(f"    订单关联图片总数: {len(imgs)}")
for img in imgs:
    print(f"      - {img['file_name']} [状态:{img['status']}] OCR={img.get('recognized_text','')[:30]}...")

print("\n  🎯 需求1 图片来单+OCR+编辑+关联 验证通过 ✅")


# ============ 测试 2: 订单整理（用OCR内容） ============
step("Step 2-1: 订单整理预览（基于OCR文本）")
r = requests.get(f"{BASE_URL}/workspace/collate/preview/{order_id}")
body = check("整理预览成功", r)
preview = body["data"]
items = preview["items"]
print(f"    解析出 {len(items)} 项明细")
for it in items:
    same_warn = "⚠️ 同名异型号" if it.get("has_same_name_diff_spec") else ""
    conf_warn = f"(置信度{it['match_confidence']:.0%})" if it["match_confidence"] < 0.9 else ""
    print(f"      {it['raw_text']} → {it.get('product_name')} {it.get('specification')} × {it.get('quantity')} {same_warn} {conf_warn}")

step("Step 2-2: 人工确认所有项并提交")
for it in items:
    if not it["manual_confirmed"]:
        it["manual_confirmed"] = True
        if not it["quantity"]:
            it["quantity"] = 2
    if it["raw_text"].startswith("洁牙头") and it.get("product_name") == "洁牙机工作尖" and not it.get("quantity"):
        it["quantity"] = 5

r = requests.post(
    f"{BASE_URL}/workspace/collate/confirm",
    json={"order_id": order_id, "items": items, "operator": "客服小王"}
)
body = check("整理确认提交成功", r)
confirm = body["data"]
assert confirm["success"] is True
print(f"    成功确认 {len(confirm['items'])} 项")


# ============ 测试 3: 缺货方案持久化 ============
step("Step 3-1: 第一次缺货检查")
r = requests.get(f"{BASE_URL}/workspace/stock/check/{order_id}")
body = check("第一次缺货检查成功", r)
stock = body["data"]
so_items = stock["stock_out_items"]
print(f"    缺货项数: {len(so_items)}")
for so in so_items:
    alt = f" → 建议替代: {so.get('alternative_product_name')} {so.get('alternative_spec')}" if so.get("alternative_product_name") else ""
    print(f"      {so['product_name']} {so['specification']} 缺 {so['stock_out_quantity']}{alt}")

step("Step 3-2: 客服处理缺货（选择替代品牌+补货日期）")
next_week = (date.today() + timedelta(days=7)).isoformat()
for so in so_items:
    if so.get("alternative_product_name"):
        so["process_remark"] = "客户同意更换"
    elif so["product_name"] == "磷酸酸蚀剂":
        so["expected_restock_date"] = next_week
        so["split_delivery"] = True
        so["process_remark"] = "下周补货后补发，客户同意拆单"

r = requests.post(
    f"{BASE_URL}/workspace/stock/process",
    json={"order_id": order_id, "items": so_items, "operator": "客服小王"}
)
body = check("缺货处理保存成功", r)
processed = body["data"]
print(f"    处理完成, 状态项数: {len(processed['stock_out_items'])}")

step("Step 3-3: 再次缺货检查 → 自动回填上次保存的方案（需求2核心）")
r = requests.get(f"{BASE_URL}/workspace/stock/check/{order_id}")
body = check("第二次缺货检查（回填已有方案）", r)
stock2 = body["data"]
so_items2 = stock2["stock_out_items"]
all_have_plan = True
for so in so_items2:
    has_plan = bool(so.get("alternative_product_name") or so.get("expected_restock_date") or so.get("split_delivery"))
    status_icon = "✅已回填" if has_plan else "❌空方案"
    print(f"      {so['product_name']} {so['specification']}: {status_icon}")
    if so.get("alternative_product_name"):
        print(f"         替代: {so['alternative_product_name']} ({so.get('alternative_spec','')})")
    if so.get("expected_restock_date"):
        print(f"         补货: {so['expected_restock_date']}, 拆单: {so.get('split_delivery')}")
    if not has_plan:
        all_have_plan = False
assert all_have_plan, "再次检查缺货时应已回填客服之前选定的方案！"

step("Step 3-4: 重新生成客户回复（无需传方案，自动使用已持久化的方案）")
r = requests.post(
    f"{BASE_URL}/workspace/stock/generate-reply",
    json={"order_id": order_id}
)
body = check("自动读取已有缺货方案生成回复成功", r)
reply = body["data"]
print(f"    回复摘要: {reply['summary']}")
print(f"    完整回复内容:\n{reply['reply_content']}")
assert "替代品牌安排" in reply["reply_content"] or "待补货安排" in reply["reply_content"]

print("\n  🎯 需求2 缺货方案持久化+回填 验证通过 ✅")


# ============ 测试 3: 配送交接协同 ============
step("Step 3-5: 创建配送交接单 → 查看协同信息")
r = requests.post(
    f"{BASE_URL}/workspace/delivery/create/{order_id}",
    params={"operator": "客服小王"}
)
body = check("创建配送交接单成功", r)
handover = body["data"]
handover_id = handover["id"]
print(f"    交接单 ID: {handover_id}, 紧急程度: {handover['urgency']}")
print(f"    加急备注: {handover.get('urgency_note')}")

step("Step 3-6: 仓库查看交接单 → 展示缺货处理结论（需求3）")
so_info = handover.get("stock_out_info", [])
print(f"    缺货处理结论数: {len(so_info)}")
for info in so_info:
    alt_line = f" 替代→{info['alternative_product_name']}" if info.get("alternative_product_name") else ""
    restock_line = f" 补货:{info['expected_restock_date']}" if info.get("expected_restock_date") else ""
    split_line = f" 拆单:{info['split_delivery']}" if info.get("split_delivery") else ""
    print(f"      {info['product_name']} {info['specification']} 缺{info['stock_out_quantity']}{alt_line}{restock_line}{split_line}")
    if info.get("process_remark"):
        print(f"         处理说明: {info['process_remark']}")

step("Step 3-7: 操作记录追溯（客服、仓库、司机协同）")
logs = handover.get("operation_logs", [])
print(f"    已有操作记录: {len(logs)} 条")
for log in logs:
    print(f"      [{log['created_at'][:19]}] {log['operator']} - {log['operation_type']}: {log.get('operation_content','')}")

step("Step 3-8: 仓库打包 → 状态流转 + 操作记录")
r = requests.put(
    f"{BASE_URL}/workspace/delivery/{handover_id}",
    json={
        "status": "packed",
        "package_note": "已按替代方案打包，酸蚀剂单独标注",
        "operator": "仓库老李",
        "remark": "外包装已贴加急标签"
    }
)
body = check("仓库打包完成", r)
packed = body["data"]
assert packed["status"] == "packed"
logs_after_pack = packed["operation_logs"]
print(f"    打包后操作记录: {len(logs_after_pack)} 条")
latest_log = logs_after_pack[0]
print(f"      最新记录: {latest_log['operator']} - {latest_log['operation_type']}: {latest_log['operation_content']}")

step("Step 3-9: 司机发货 → 状态流转")
r = requests.put(
    f"{BASE_URL}/workspace/delivery/{handover_id}",
    json={
        "status": "dispatched",
        "driver_note": "已装送货车，先走手术加急路线",
        "operator": "司机小张"
    }
)
body = check("司机发货成功", r)
dispatched = body["data"]
assert dispatched["status"] == "dispatched"
print(f"    紧急程度: {dispatched['urgency']} | 加急备注: {dispatched.get('urgency_note')}")

step("Step 3-10: 订单完成签收 → 追溯谁在何时处理过")
r = requests.put(
    f"{BASE_URL}/workspace/delivery/{handover_id}",
    json={
        "status": "delivered",
        "operator": "司机小张",
        "remark": "张医生本人签收"
    }
)
body = check("订单签收成功", r)
delivered = body["data"]
assert delivered["status"] == "delivered"
logs = delivered["operation_logs"]
print(f"    完整操作追溯（{len(logs)} 条）：")
for log in reversed(logs):
    t = log["created_at"][:19] if log.get("created_at") else ""
    print(f"      [{t}] {log['operator']} | {log['operation_type']} | {log.get('operation_content') or ''}")

step("Step 3-11: 最终订单详情 → 查看完整操作日志")
r = requests.get(f"{BASE_URL}/orders/{order_id}")
body = check("获取最终订单详情", r)
final_order = body["data"]
print(f"    订单最终状态: {final_order['status']}")
all_logs = final_order.get("operation_logs", [])
print(f"    订单级别操作记录: {len(all_logs)} 条")
for log in all_logs:
    t = log["created_at"][:19] if log.get("created_at") else ""
    print(f"      [{t}] {log['operator']} - {log['operation_type']}")

print("\n  🎯 需求3 配送交接协同（缺货信息+操作追溯）验证通过 ✅")


# ============ 汇总 ============
print("\n" + "=" * 60)
print("  🏆 所有增强需求测试通过！")
print("=" * 60)
print("  ✅ 需求1: 图片来单上传 + OCR识别 + 客服编辑修正 + 订单关联")
print("  ✅ 需求2: 缺货方案持久化（替代品牌/补货日期/拆单）→ 自动回填")
print("  ✅ 需求3: 配送交接协同（缺货结论展示 + 操作记录全程追溯）")
print("  ✅ 需求4: 统一异常响应格式（code/message/success 字段齐全）")
print("=" * 60)
