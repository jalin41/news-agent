import json
from pydantic import BaseModel, Field, ValidationError
from typing import List
from config import CLIENT
import difflib
import re
import datetime

# ================= 1. 结构锁死：Pydantic 严格约束模型 =================
class NewsItem(BaseModel):
    title: str = Field(..., max_length=50, description="新闻标题")
    summary: str = Field(..., min_length=20, max_length=250, description="新闻摘要")
    is_foreign: bool = Field(..., description="是否为外媒")
    source: str = Field(..., description="媒体来源")
    url: str = Field(..., description="原文链接")
    full_text: str = Field(default="", description="外媒长文解析")

class NewsList(BaseModel):
    items: List[NewsItem]

# ======================================================================

def get_deep_translation(title, source):
    """【文风锁死】外网长文专栏生成器"""
    prompt = f"""
    你是《经济学人》主编。请为这篇外媒报道写一段200字左右的中文专栏复盘。
    事件：{title} (来源:{source})

    【模仿范文风格】：
    "当美联储宣布维持利率不变时，华尔街的狂欢戛然而止。这不仅是鲍威尔对通胀数据的妥协，更是对全球资本流向的一次重新洗牌。短期内，新兴市场货币将承受重压..."
    
    【强制要求】：绝不废话，句句带肉，全部用标准简体中文。
    """
    response = CLIENT.chat.completions.create(
        model="Qwen/Qwen3.5-122B-A10B",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1 
    )
    content = response.choices[0].message.content
    return content if content and len(content) > 10 else "【系统提示】深度解析获取超时。"

def process_news(indexed_news):
    print("🧠 [选题总监] 正在审视全网资讯池，挑选热点...")

    news_db = {item["id"]: item for item in indexed_news}
    target_count = 10
    final_news_list = []
    seen_titles = set()

    # ================= 第 1 步：选题总监 =================
    title_only_pool = "\n".join([f"[ID:{item['id']}] 媒体:{item['source']} | 标题:{item['title']}" for item in indexed_news])

    selection_prompt = f"""
    你是立足于【中国大陆】的顶级媒体总编，并且来自中国杭州。
    请从以下纯标题资讯池中，选出 {target_count} 条最具影响力的重磅新闻。

    【选品红线】：
    1. 唯一标准：按新闻的“炸裂程度”、“公众讨论热度”排座次。
    2. 广度保底：政经政策、金融资本、硬核科技、民生社会、国际地缘这 5 大领域，每个领域至少保留 1 条。
    3. 地方新闻：优先杭州和浙江，忽略其他城市的纯地方琐事。
    4. 重复新闻：同一事件只选一条。
    5. 比例控制（严厉执行）：为了照顾中国内地读者，以国内新闻优先。

    【JSON 模板】：
    {{
      "selected_ids": [填入选中的 {target_count} 个ID数字]
    }}

    资讯池：
    {title_only_pool}
    """

    try:
        response1 = CLIENT.chat.completions.create(
            model="Qwen/Qwen3.5-122B-A10B",
            messages=[{"role": "user", "content": selection_prompt}],
            response_format={"type": "json_object"}, 
            temperature=0.0,
            max_tokens=8192
        )
        match1 = re.search(r"\{[\s\S]*\}", response1.choices[0].message.content)
        selected_ids = json.loads(match1.group(0))["selected_ids"]
        selected_ids = selected_ids[:target_count] 
        print(f"✅ [选题总监] 成功锁定 {len(selected_ids)} 个热点 ID: {selected_ids}")
    except Exception as e:
        print(f"❌ 选题失败: {e}")
        return []

    print("🧠 [深度编辑] 正在分批加载原文进行精写...")

    # ================= 第 2 步：深度编辑 (分批处理版) =================
    today_str = datetime.datetime.now().strftime("%Y年%m月%d日") 
    foreign_keywords = ["路透", "reuters", "bbc"]
    editing_pool_data = []

    for sid in selected_ids:
        if sid in news_db:
            item = news_db[sid]
            source_name = item["source"].lower()
            is_foreign = any(kw in source_name for kw in foreign_keywords)
            task_type = "【外网特稿：需300字长文】" if is_foreign else "【国内简讯：需100字】"
            editing_pool_data.append(f"[ID:{item['id']}] 任务:{task_type} | 标题:{item['title']} | 原文:{item['original_summary']}")

    # 把 Prompt 改为基础模板，后续循环内拼接文本
    detail_prompt_template = f"""
    你是资深主笔。当前真实时间是：{today_str}。请为以下新闻撰写摘要。
    
    【核心命令】：
    1. 全中文输出：如果原文是英文，必须将“标题”和“摘要”精准翻译为中文。
    2. 时间校准：严禁出现 2023 等过时年份！结合今日日期（{today_str}）进行表达。
    3. 差异化字数：国内简讯100字；外网特稿300-400字，要把受限无法访问的原文讲透。

    【标准示范（Few-Shot 极度重要）】：
    输入示例 1 (国内)：
    [ID:1] 任务:【国内简讯：需100字】 | 标题: 央行降准0.5个百分点 | 完整原文: 昨天，央行宣布将于2026年1月5日下调存款准备金率0.5个百分点，预计释放长期资金约1万亿元...
    输出示例 1：
    {{
      "id": 1,
      "title": "央行开年首次降准，释放万亿资金",
      "summary": "重磅！1月25日（昨日），中国人民银行宣布下调金融机构存款准备金率0.5个百分点。此次降准为2026年首次，预计向市场释放长期流动性约1万亿元。此举旨在提振市场信心，巩固经济回升势头，为A股春季行情注入强心剂。"
    }}

    输入示例 2 (外媒)：
    [ID:2] 任务:【外网特稿：需300字长文】 | 标题: Apple drops Vision Pro 2 | 完整原文: Cupertino, Sunday. Apple unveiled the next generation of its spatial computing headset...
    输出示例 2：
    {{
      "id": 2,
      "title": "苹果突发发布Vision Pro 2：重量减半，算力翻倍",
      "summary": "【深度解析】当地时间1月25日（周日），苹果公司在库比蒂诺毫无预警地发布了第二代空间计算头显 Vision Pro 2。据路透社报道，本次更新解决了上一代最大的痛点：佩戴重量。通过采用新型碳钛合金材料，整机重量从 650克骤降至 350克。同时，搭载全新的 M4 芯片使图形算力提升了120%。\n\n此次定价策略也出现重大转变，起售价下调至 2499美元（约合人民币1.8万元），比初代便宜了整整1000美元。这标志着苹果正式将空间计算从“开发者实验”推向“大众消费时代”。华尔街分析师预计，该设备将于2026年2月中旬在全球同步发售。"
    }}

    【强制 JSON 格式规范】（极其重要）：
    1. 根节点必须是 "items"！
    2. 字段名必须严格保持为纯英文（"id", "title", "summary"），绝对禁止使用中文键名！
    3. "id" 的值必须是原始的纯数字 ID，绝对禁止填入任务标签！

    【容错机制】（防崩溃必看）：
    如果发现某条新闻的标题或原文包含大量乱码、错别字或无法理解的乱码（如 gnore、肬 等），请不要强行解析！请直接在 summary 字段填入：“[原文损坏，已过滤]”，绝对禁止破坏 JSON 括号结构！

    【JSON 输出模板】（必须完全遵守）：
    {{
      "items": [
        {{
          "id": 123, 
          "title": "这里写中文标题",
          "summary": "这里写深度文案"
        }}
      ]
    }}

    待精写新闻：
    """

    parsed_items = []
    batch_size = 5  # 每次喂给 AI 5 条新闻

    for i in range(0, len(editing_pool_data), batch_size):
        batch_data = editing_pool_data[i:i + batch_size]
        batch_count = len(batch_data)
        
        # 【新增】：给 AI 下达极其强烈的物理数量约束
        strict_command = f"\n\n【死命令】：下方共有 {batch_count} 条新闻，你必须在 JSON 的 items 数组里输出正好 {batch_count} 个对象，少一条或合并都会导致系统崩溃！\n\n"
        
        batch_prompt = detail_prompt_template + strict_command + "\n".join(batch_data)
        
        try:
            print(f"⏳ 正在精写第 {i+1} 到 {min(i+batch_size, len(editing_pool_data))} 条新闻...")
            response2 = CLIENT.chat.completions.create(
                model="Qwen/Qwen3.5-122B-A10B",
                messages=[{"role": "user", "content": batch_prompt}],
                response_format={"type": "json_object"}, 
                temperature=0.1,
                top_p=0.8,
                frequency_penalty=0.5,
                max_tokens=8192  # 放开截断限制
            )
            
            raw_content = response2.choices[0].message.content
            match2 = re.search(r"\{[\s\S]*\}", raw_content)
            
            if match2:
                try:
                    batch_parsed = json.loads(match2.group(0))
                    items = batch_parsed.get("items", [])
                    if isinstance(items, dict): items = [items]
                    parsed_items.extend(items)
                except Exception as e:
                    print(f"❌ 批次 JSON 格式损坏。错误: {e}")
                    print(f"⚠️ 原始内容: {raw_content}")
            else:
                print("❌ 本批次找不到 JSON 结构！")
                print(f"⚠️ 原始内容: {raw_content}")

        except Exception as e:
            print(f"❌ 批次请求失败跳过。错误: {e}")
            continue

    # ================= 第 3 步：完美组装 =================
    for ai_item in parsed_items:
        if not isinstance(ai_item, dict):
            continue
            
        news_id = ai_item.get("id")
        if news_id in news_db:
            original_data = news_db[news_id]
            new_title = ai_item.get("title", original_data["title"]) 

            # Difflib 智能去重
            is_duplicate = False
            for seen_title in seen_titles:
                if difflib.SequenceMatcher(None, new_title, seen_title).ratio() > 0.65:
                    is_duplicate = True; break
            
            if not is_duplicate:
                final_news_list.append({
                    "title": new_title, 
                    "summary": ai_item.get("summary", "")[:400], 
                    "source": original_data["source"], 
                    "url": original_data["url"]        
                })
                seen_titles.add(new_title)

    # ================= 分类逻辑 =================
    for news in final_news_list:
        source_name = news["source"].lower()
        news["is_foreign"] = any(kw in source_name for kw in foreign_keywords)

    final_news_list.sort(key=lambda x: x.get("is_foreign", False))
    return final_news_list
