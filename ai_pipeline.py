import json
from pydantic import BaseModel, Field, ValidationError
from typing import List
from config import CLIENT

# ================= 1. 结构锁死：Pydantic 严格约束模型 =================
# 定义每一条新闻必须长什么样，多一个字段、少一个字段、类型不对，系统直接拒收！
class NewsItem(BaseModel):
    title: str = Field(..., max_length=50, description="新闻标题")
    summary: str = Field(..., min_length=20, max_length=120, description="新闻摘要")
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

def process_news(news_text):
    import re # 确保引入了 re
    print("🧠 [AI] 正在通过 Pydantic 约束进行新闻处理...")
    
    # 【修复1：Prompt 结构严格对齐 Pydantic】
    master_prompt = f"""
    你是立足于【中国大陆】的顶级媒体总编。请从资讯池中，以中国人的视角精选出今日 10 条最具影响力的新闻。

    【自适应选品算法 (核心规则)】：
    1. 顺应大势（热力加权）：先评估今日大盘趋势。如果今天科技圈爆发大事件，允许科技新闻占据 5-6 条；如果今天政策密集，则倾向于政经。完全按新闻的“炸裂程度”排座次。
    2. 广度保底（拒绝盲区）：无论某个领域多热，【政经政策、金融资本、硬核科技、民生社会、国际地缘】这 5 大领域，每个领域【至少必须保留 1 条】的席位，确保读者视野没有绝对盲区。
    3. 优中选优：同一热点事件只选深度最好的一篇。

    【中国视角选品法则】：
    1. 大陆民生优先：优先选择影响中国老百姓“钱袋子”、“菜篮子”、“教育医疗”的国内政策与社会新闻。
    2. 国产金融与科技：科技和金融版块必须以国内大厂（腾讯、字节、阿里等）和 A股/国内宏观经济为主，不要满屏的欧美股市和美国AI。
    3. 国际新闻只看关联：国际新闻（如美国大选、中东局势）只选那些“对中国产生直接影响”的事件，绝不选美国人自己的国内八卦。

    【JSON 模板】：
    {{
      "items": [
        {{
          "title": "新闻标题",
          "summary": "80-100字深度摘要，讲透干货(限简体中文)",
          "is_foreign": true/false (来源含BBC/路透/早报必为true),
          "source": "媒体",
          "url": "原文链接"
        }}
      ]
    }}

    原始数据：{news_text}
    """

    response = CLIENT.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct",
        messages=[{"role": "user", "content": master_prompt}],
        response_format={"type": "json_object"}, 
        temperature=0.0
    )
    
    raw_response = response.choices[0].message.content
    
    # 【修复2：正则清洗润滑剂，剥离大模型顽固的 markdown 外衣】
    match = re.search(r"\{[\s\S]*\}", raw_response)
    clean_json = match.group(0) if match else "{}"

    try:
        parsed_data = json.loads(clean_json)
        # 严格验证
        valid_news_list = NewsList(**parsed_data)
        validated_items = valid_news_list.items
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"❌ Pydantic 验证失败，启动降级保护: {e}")
        # 【修复3：商业级兜底】如果严格验证失败，不要返回空，而是尽力抢救数据
        validated_items = parsed_data.get("items", []) 
        if not validated_items:
            return []

    # 物理去重防线
    unique_news = []
    seen_titles = set()
    for item in validated_items:
        # 兼容 Pydantic 对象或普通字典
        news_dict = item.model_dump() if hasattr(item, 'model_dump') else item
        title_fingerprint = news_dict["title"][:5] 
        if title_fingerprint not in seen_titles:
            unique_news.append(news_dict)
            seen_titles.add(title_fingerprint)

    # 商业级双向分类与长文补充
    foreign_keywords = ["bbc", "路透", "reuters", "纽约时报", "华尔街", "早报"]
    domestic_keywords = ["人民网", "新浪", "36氪", "第一财经", "界面新闻", "三联生活周刊"]
    
    for news in unique_news:
        source_name = news.get("source", "").lower()
        if any(kw in source_name for kw in domestic_keywords):
            news["is_foreign"] = False
        if any(kw in source_name for kw in foreign_keywords):
            news["is_foreign"] = True
            
        if news.get("is_foreign", False):
            news["full_text"] = get_deep_translation(news["title"], news["source"])

    unique_news.sort(key=lambda x: x.get("is_foreign", False))

    return unique_news