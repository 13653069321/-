import requests
import json
import os

# -------------------------- 核心配置项 --------------------------
#7005106440989838336   绍宋
#7414011485757639704   冒姓琅琊
BOOK_ID = "7005106440989838336"
CATALOG_API_URL = "https://bk.yydjtc.cn/api/book"
DOWNLOAD_API_URL = "https://bk.yydjtc.cn/api/content"
SAVE_DIR = "D:\\文件"
BATCH_SIZE = 5  # 小批量请求（避免API限制）

# 确保保存目录存在
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
    print(f"✅ 创建保存目录：{SAVE_DIR}")

def get_chapter_catalog():
    """获取目录列表（保留项索引顺序）"""
    print("===== 1. 查询小说目录 =====")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Referer": "https://bk.yydjtc.cn/",
        }
        params = {"book_id": BOOK_ID}
        response = requests.get(CATALOG_API_URL, params=params, headers=headers, timeout=10, verify=False)
        
        if response.status_code != 200:
            print(f"❌ 目录查询失败，状态码：{response.status_code}")
            return None
        
        catalog_data = response.json()
        all_item_ids = catalog_data["data"]["data"]["allItemIds"]
        print(f"✅ 目录查询成功！共{len(all_item_ids)}个列表项（索引0-{len(all_item_ids)-1}）")
        return all_item_ids
    except Exception as e:
        print(f"❌ 目录查询异常：{str(e)}")
        return None

def test_single_id(item_id, catalog_idx):
    """测试单个ID是否能返回内容"""
    print(f"\n📌 测试单个ID：列表项{catalog_idx} → item_id={item_id}")
    params = {
        "tab": "批量",
        "book_id": BOOK_ID,
        "item_ids": str(item_id)
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    }
    try:
        response = requests.get(DOWNLOAD_API_URL, params=params, headers=headers, timeout=10, verify=False)
        response.encoding = "utf-8"
        result = json.loads(response.text.strip())
        
        print(f"   API原始返回：{json.dumps(result, ensure_ascii=False)[:500]}...")
        chapters = result.get("data", {}).get("chapters", [])
        
        if chapters:
            chap_title = chapters[0].get("title", "无标题")
            print(f"   ✅ 单个ID测试成功 → 章节标题：{chap_title}")
            return chapters[0]
        else:
            print(f"   ❌ 单个ID测试失败 → 无章节内容返回")
            return None
    except Exception as e:
        print(f"   ❌ 单个ID测试异常：{str(e)}")
        return None

def download_by_catalog_index(start_idx, end_idx, all_item_ids):
    """核心：保留原文换行 + 严格按列表项索引顺序"""
    print(f"\n===== 2. 按目录列表项 {start_idx}-{end_idx} 下载（保留原文换行） =====")
    
    # 提取列表项对应的item_id
    target_list = []
    for idx in range(start_idx, end_idx + 1):
        item_id = all_item_ids[idx]
        target_list.append({
            "catalog_idx": idx,
            "item_id": item_id,
            "chapter": None
        })
    print(f"📌 待下载列表（共{len(target_list)}个）：")
    for item in target_list:
        print(f"   列表项{item['catalog_idx']} → item_id={item['item_id']}")

    # 小批量请求
    all_returned_chaps = {}
    batches = [target_list[i:i+BATCH_SIZE] for i in range(0, len(target_list), BATCH_SIZE)]
    for batch_num, batch in enumerate(batches):
        batch_ids = [str(item["item_id"]) for item in batch]
        batch_idxs = [item["catalog_idx"] for item in batch]
        print(f"\n📌 批量{batch_num+1}：请求列表项{batch_idxs} → ID={batch_ids}")
        
        params = {
            "tab": "批量",
            "book_id": BOOK_ID,
            "item_ids": ",".join(batch_ids)
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
        }
        try:
            response = requests.get(DOWNLOAD_API_URL, params=params, headers=headers, timeout=10, verify=False)
            response.encoding = "utf-8"
            result = json.loads(response.text.strip())
            
            if result.get("code") == 200:
                returned_chaps = result.get("data", {}).get("chapters", [])
                for chap in returned_chaps:
                    chap_id = str(chap.get("itemId"))
                    all_returned_chaps[chap_id] = chap
                print(f"   ✅ 批量{batch_num+1}返回{len(returned_chaps)}个章节")
            else:
                print(f"   ❌ 批量{batch_num+1}返回错误：{result.get('msg')}")
        except Exception as e:
            print(f"   ❌ 批量{batch_num+1}异常：{str(e)}")

    # 匹配章节（批量失败则单ID兜底）
    print(f"\n📌 匹配章节（批量失败则单ID兜底）：")
    for item in target_list:
        catalog_idx = item["catalog_idx"]
        item_id = item["item_id"]
        item_id_str = str(item_id)
        
        if item_id_str in all_returned_chaps:
            item["chapter"] = all_returned_chaps[item_id_str]
            chap_title = item["chapter"].get("title", "无标题")
            print(f"   ✅ 列表项{catalog_idx} → 批量匹配到：{chap_title}")
        else:
            single_chap = test_single_id(item_id, catalog_idx)
            if single_chap:
                item["chapter"] = single_chap
                print(f"   ✅ 列表项{catalog_idx} → 单ID兜底匹配到：{single_chap.get('title')}")
            else:
                print(f"   ❌ 列表项{catalog_idx} → 批量+单ID都失败（已占位）")

    # 格式化文本（核心修改：保留原文换行）
    novel_text = ""
    for item in target_list:
        catalog_idx = item["catalog_idx"]
        chap = item["chapter"]
        
        if chap:
            title = chap.get("title", f"列表项{catalog_idx}")
            # ========== 关键修改：保留原文换行 ==========
            # 1. 只替换转义的\n为实际换行（恢复原文换行）
            # 2. 只清理每行开头/结尾的空格，保留行内单个空格
            # 3. 保留空行，符合原文排版
            content = chap.get("content", "")
            # 先替换转义换行符为实际换行
            content = content.replace("\\n", "\n")
            # 按行处理：清理每行首尾空格，保留行内空格和换行
            lines = content.split("\n")
            cleaned_lines = [line.strip() for line in lines]
            # 重新拼接，恢复换行（空行也保留）
            content = "\n".join(cleaned_lines)
            # ===========================================
        else:
            title = f"【缺失章节】目录列表项{catalog_idx}"
            content = f"⚠️ 该列表项无内容（item_id={item['item_id']}）\n⚠️ 批量+单ID请求均失败"
        
        # 按列表项顺序拼接
        novel_text += f"【{title}（目录列表项{catalog_idx}）】\n\n"
        novel_text += content
        novel_text += "\n\n" + "="*80 + "\n\n"

    # 保存文件
    file_name = f"冒姓琅琊_列表项{start_idx}-{end_idx}_保留换行.txt"
    save_path = os.path.join(SAVE_DIR, file_name)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(novel_text)

    # 结果总结
    success_count = len([x for x in target_list if x["chapter"] is not None])
    fail_count = len(target_list) - success_count
    print(f"\n✅ 下载完成！成功{success_count}个，失败{fail_count}个")
    print(f"📁 保存路径：{save_path}")
    if fail_count > 0:
        fail_indexes = [x["catalog_idx"] for x in target_list if x["chapter"] is None]
        print(f"⚠️ 失败列表项索引：{fail_indexes}")
    return success_count > 0

def get_user_input_range(all_item_ids_len):
    """交互获取列表项索引范围"""
    print(f"\n===== 3. 输入目录列表项索引范围 =====")
    print(f"提示：目录共有{all_item_ids_len}个列表项，索引0-{all_item_ids_len-1}")
    
    while True:
        try:
            start = int(input("请输入起始列表项索引（如130）："))
            if 0 <= start < all_item_ids_len:
                break
            print(f"❌ 请输入0-{all_item_ids_len-1}之间的数字！")
        except ValueError:
            print("❌ 请输入纯数字！")
    
    while True:
        try:
            end = int(input("请输入结束列表项索引（如145）："))
            if start <= end < all_item_ids_len:
                break
            print(f"❌ 请输入{start}-{all_item_ids_len-1}之间的数字！")
        except ValueError:
            print("❌ 请输入纯数字！")
    
    return start, end

# -------------------------- 主执行流程 --------------------------
if __name__ == "__main__":
    all_item_ids = get_chapter_catalog()
    if not all_item_ids:
        print("\n❌ 流程终止：目录查询失败")
        exit()
    
    start_idx, end_idx = get_user_input_range(len(all_item_ids))
    
    success = download_by_catalog_index(start_idx, end_idx, all_item_ids)
    if not success:
        print("\n❌ 流程终止：所有列表项下载失败")
        exit()
    
    print("\n🎉 全部完成！打开D:\\文件查看保留换行的小说文本")