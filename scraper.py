import feedparser
import random
import re
from datetime import datetime, timezone, timedelta
import time
from config import RSS_FEEDS

# 【新增】强力清洗函数：专门剔除标题里的网址、域名和奇怪后缀
def clean_noise(text):
    if not text:
        return ""
    
    # 1. 剔除标准网址 (http/https/www)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # 2. 剔除裸露的域名 (如 chinanews.com.cn, In.gov.cn, gx.xinhuanet.com)
    # 匹配规则：字母数字组合 + .com/.cn/.gov/.net + 可选的二级后缀
    text = re.sub(r'\b[a-zA-Z0-9-]+\.(com|cn|gov|net|org)(\.cn)?\b', '', text)
    
    # 3. 剔除常见的尾巴符号 (如 " - " 或 " | " 后面跟着空字符串)
    text = re.sub(r'\s+[-|]\s*$', '', text)
    
    # 4. 去除多余空格
    return text.strip()

def get_news():
    print("🕷️ [Scraper] 正在抓取并清洗数据...")

    # 设定时间防线：24小时
    time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
    time_limit_struct = time_limit.timetuple()

    raw_news = []
    
    for source_name, url_list in RSS_FEEDS.items():
        if isinstance(url_list, str): url_list = [url_list]
            
        success = False
        for url in url_list:
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    valid_count = 0
                    for entry in feed.entries[:30]: 
                        # 1. 时间过滤
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            if entry.published_parsed < time_limit_struct:
                                continue 
                        
                        # 2. 获取原始标题和摘要
                        raw_title = entry.title
                        raw_summary = entry.get('summary', entry.get('description', ''))
                        
                        # 【核心修复】：在这里调用清洗函数！
                        clean_title_text = clean_noise(raw_title)
                        
                        # 如果标题洗完之后空了（极少见），就用原标题兜底
                        if not clean_title_text: clean_title_text = raw_title

                        clean_summary_text = re.sub(r'<[^<]+?>', '', raw_summary)[:200]
                        
                        # 存入列表 (这里我们用 ID 模式的结构，方便后续处理)
                        # 注意：这里我们只存字符串，如果你已经改用了上一步的 ID 模式，请看下文的“适配版”
                        raw_news.append(f"【{source_name}】{clean_title_text}\n原文:{clean_summary_text}\n链接:{entry.get('link', '')}\n")
                        
                        valid_count += 1
                    
                    if valid_count > 0:
                        print(f"✅ {source_name} 抓取成功 ({valid_count}条)")
                        success = True
                        break 
            except Exception:
                continue 
        
        if not success:
            print(f"⚠️ {source_name} 暂无可用数据")
            
    print(f"✅ [Scraper] 清洗完毕，共 {len(raw_news)} 条。")
    random.shuffle(raw_news)
    
    # ========================================================
    # 如果你已经使用了“ID索引法”，请用下面这段代码替换 return 语句
    # ========================================================
    indexed_news = []
    for i, news_str in enumerate(raw_news):
        match = re.search(r"【(.*?)】(.*?)\n原文:(.*?)\n链接:(.*?)\n", news_str)
        if match:
            indexed_news.append({
                "id": i,
                "source": match.group(1),
                "title": match.group(2), # 这里拿到的已经是清洗干净的标题了
                "original_summary": match.group(3),
                "url": match.group(4)
            })
            
    return indexed_news
