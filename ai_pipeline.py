import json
from pydantic import BaseModel, Field, ValidationError
from typing import List
from config import CLIENT
import difflib

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

def process_news(news_text):
    import re
    import json
    from pydantic import ValidationError

    print("🧠 [AI] 正在启动增量累加抓取机制...")

    max_retries = 3         # 最多尝试 3 次
    target_count = 10       # 最终目标条数
    accumulated_news = []   # 全局新闻累加池
    seen_titles = set()     # 全局去重指纹库
    
    for attempt in range(max_retries):
        needed_count = target_count - len(accumulated_news)
        if needed_count <= 0:
            break # 已经满了，直接跳出

        print(f"🔄 第 {attempt + 1} 次生成，当前已有 {len(accumulated_news)} 条，还需补抓 {needed_count} 条...")
        
        # 温度随重试次数升高，激发AI寻找新维度的内容
        current_temperature = 0.1 * attempt 

        # 动态 Prompt：每次只向 AI 索要剩余的数量
        master_prompt = f"""
        你是立足于【中国大陆】的顶级媒体总编，并且来自中国杭州。请从资讯池中，以你的视角筛选出当下 {needed_count} 条最有影响力的新闻。

        【自适应选品算法 (核心规则)】：
        1. 顺应大势（热力加权）：先评估今日大盘趋势。如果今天科技圈爆发大事件，允许科技新闻占据 4-5 条；如果今天政策密集，则倾向于政经。完全按新闻的“炸裂程度”排座次。
        2. 广度保底（拒绝盲区）：无论某个领域多热，【政经政策、金融资本、硬核科技、民生社会、国际地缘】这 5 大领域，每个领域【至少必须保留 1 条】的席位，确保读者视野没有绝对盲区。
        3. 绝对时效：必须且只能挑选【今日最新】（过去24小时内）发生的新闻！严禁收录两天前或更久以前的旧闻、冷饭，哪怕它再轰动！
        4. 优中选优：同一热点事件只选深度最好的一篇。

        【选品红线（热度为王）】：
        1. 唯一标准：按新闻的“炸裂程度”、“公众讨论热度”和“影响力”来排座次。什么是全网都在关注的大事，就选什么！
        2. 领域不限：无论是国家政策、民生大案、科技巨变、金融崩盘还是国际冲突，只要足够火爆、足够重大，全部入选。
        3. 国际新闻只看关联：国际新闻（如美国大选、中东局势）只选那些“对中国产生直接影响”的事件，绝不选美国人自己的国内八卦。
        4. 地方新闻白名单：对于地方新闻，优先收录【杭州】和【浙江】的本地新闻。最好不要收录其他城市的纯地方性琐事（除非该事件已引发全国舆论轰动）。
        5. 凑满机制：必须且只能选出 {needed_count} 条。即使今天大盘平淡，也要矮子里拔将军，选出当天相对最热的新闻凑满数量。

        【JSON 模板】：
        {{
          "items": [
            {{
              "title": "新闻标题",
              "summary": "80-100字深度摘要",
              "is_foreign": true/false,
              "source": "媒体",
              "url": "原文链接"
            }}
          ]
        }}
        原始数据：{news_text}
        """

        try:
            response = CLIENT.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct",
                messages=[{"role": "user", "content": master_prompt}],
                response_format={"type": "json_object"}, 
                temperature=current_temperature,
                max_tokens=2500
            )
            
            raw_response = response.choices[0].message.content
            match = re.search(r"\{[\s\S]*\}", raw_response)
            clean_json = match.group(0) if match else "{}"
            parsed_data = json.loads(clean_json)
            
            valid_news_list = NewsList(**parsed_data)
            validated_items = valid_news_list.items

            # 【核心逻辑】：遍历新抓取的数据，不重复的才塞入累加池
            for item in validated_items:
                news_dict = item.model_dump() if hasattr(item, 'model_dump') else item
                new_title = news_dict["title"]
                
                # 智能查重：将新标题与池子里所有旧标题做对比
                is_duplicate = False
                for seen_title in seen_titles:
                    # 计算相似度（大于 0.65 判定为同一条新闻的不同写法）
                    similarity = difflib.SequenceMatcher(None, new_title, seen_title).ratio()
                    if similarity > 0.65:
                        is_duplicate = True
                        break # 一旦发现相似，立刻标记为重复并停止检查
                
                # 只有非重复的新闻，才允许进入累加池
                if not is_duplicate:
                    accumulated_news.append(news_dict)
                    seen_titles.add(new_title) # 现在完整保存标题，用于下次对比
                
                # 一旦累加池满了 10 条，立刻停止吸收
                if len(accumulated_news) >= target_count:
                    break

        except Exception as e:
            print(f"❌ 第 {attempt + 1} 次抓取出错: {e}")

    print(f"✅ 最终成功汇聚 {len(accumulated_news)} 条独家新闻。")

    # === 后续的分类与长文补充 (保持不变) ===
    foreign_keywords = ["路透", "reuters", "联合早报", "zaobao", "bbc"]
    domestic_keywords = ["人民网", "36氪", "第一财经", "界面新闻", "澎湃新闻", "少数派", "国内热点"]
    
    for news in accumulated_news:
        source_name = news.get("source", "").lower()
        if any(kw in source_name for kw in domestic_keywords):
            news["is_foreign"] = False
        if any(kw in source_name for kw in foreign_keywords):
            news["is_foreign"] = True
            
        if news.get("is_foreign", False):
            news["full_text"] = get_deep_translation(news["title"], news["source"])

    # 优先展示外媒深度文章
    accumulated_news.sort(key=lambda x: x.get("is_foreign", False))

    return accumulated_news
