import json
from pydantic import BaseModel, Field, ValidationError
from typing import List
from config import CLIENT
import difflib
import re

# ================= 1. 结构锁死：Pydantic 严格约束模型 =================
# 定义每一条新闻必须长什么样，多一个字段、少一个字段、类型不对，系统直接拒收！
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
        model="Qwen/Qwen2.5-32B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1 # 极低的温度，锁死创造力
    )
    content = response.choices[0].message.content
    return content if content and len(content) > 10 else "【系统提示】深度解析获取超时。"

def process_news(indexed_news):

    print("🧠 [选题总监] 正在审视全网资讯池，挑选热点...")

    # 构建数据库，供后续精确查找使用
    news_db = {item["id"]: item for item in indexed_news}
    target_count = 10
    final_news_list = []
    seen_titles = set()

    # ================= 第 1 步：选题总监 (只看标题，盲选 ID) =================
    # 给 AI 的清单里【绝对不含原文】，从物理层面杜绝内容串行
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
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role": "user", "content": selection_prompt}],
            response_format={"type": "json_object"}, 
            temperature=0.0, # 选品需要严谨，温度设为0
            max_tokens=1000
        )
        match1 = re.search(r"\{[\s\S]*\}", response1.choices[0].message.content)
        selected_ids = json.loads(match1.group(0))["selected_ids"]
        
        # 防止 AI 没选满，做个截断
        selected_ids = selected_ids[:target_count] 
        print(f"✅ [选题总监] 成功锁定 {len(selected_ids)} 个热点 ID: {selected_ids}")

    except Exception as e:
        print(f"❌ 选题失败: {e}")
        return []

    print("🧠 [深度编辑] 正在加载这几篇报道的完整原文进行精写...")

    # ================= 第 2 步：深度编辑 (引入时间戳与全中文翻译) =================
    import datetime
    # 获取当下的真实日期，告诉 AI 今天是哪一天
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

    editing_pool_text = "\n".join(editing_pool_data)

    detail_prompt = f"""
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
    {editing_pool_text}
    
    """

    try:
        response2 = CLIENT.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role": "user", "content": detail_prompt}],
            response_format={"type": "json_object"}, 
            temperature=0.1,
            max_tokens=2500
        )
        
        raw_content = response2.choices[0].message.content
        match2 = re.search(r"\{[\s\S]*\}", raw_content)
        
        # 增加安全校验：如果抓到了 JSON 格式才解析
        if match2:
            try:
                parsed_data = json.loads(match2.group(0))
            except Exception as e:
                print(f"❌ JSON 格式损坏无法解析。错误: {e}")
                print(f"⚠️ AI 原始返回内容: {raw_content}")
                parsed_data = {}
        else:
            print("❌ AI 返回的内容中找不到 JSON 结构！")
            print(f"⚠️ AI 原始返回内容: {raw_content}")
            parsed_data = {}

        # ================= 第 3 步：完美组装 =================
        for ai_item in parsed_data.get("items", []):
            news_id = ai_item.get("id")
            if news_id in news_db:
                original_data = news_db[news_id]
                
                # 【关键修复】：接收 AI 翻译好的中文标题，而不是死板地照抄英文原标题
                new_title = ai_item.get("title", original_data["title"]) 

                # Difflib 智能去重 (保持不变)
                is_duplicate = False
                for seen_title in seen_titles:
                    if difflib.SequenceMatcher(None, new_title, seen_title).ratio() > 0.65:
                        is_duplicate = True; break
                
                if not is_duplicate:
                    final_news_list.append({
                        "title": new_title, 
                        "summary": ai_item.get("summary", "")[:400], # 配合长文，放宽长度
                        "source": original_data["source"], 
                        "url": original_data["url"]        
                    })
                    seen_titles.add(new_title)

    except Exception as e:
        print(f"❌ 精写失败: {e}")

    # ================= 分类与长文逻辑 (保持不变) =================
    foreign_keywords = ["路透", "reuters", "bbc", "国内热点(谷歌)"]
    # domestic_keywords = ["人民网", "36氪", "第一财经", "界面新闻", "澎湃新闻", "少数派", "百度热点", "知乎热榜", "网易新闻", "搜狐"]

    for news in final_news_list:
        source_name = news["source"].lower()
        news["is_foreign"] = any(kw in source_name for kw in foreign_keywords)
        if news.get("is_foreign", False):
            # 假设你的 get_deep_translation 函数在外面定义好了
            # news["full_text"] = get_deep_translation(news["title"], news["source"]) 
            pass

    final_news_list.sort(key=lambda x: x.get("is_foreign", False))
    return final_news_list
