import feedparser
import random
import re
from config import RSS_FEEDS

def get_news():
    print("🕷️ [Scraper] 正在抓取新闻源...")

    feedparser.USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    raw_news = []
    
    for source_name, url_list in RSS_FEEDS.items():
        # 如果配置里是单个字符串（旧版），兼容转成列表
        if isinstance(url_list, str):
            url_list = [url_list]
            
        success = False
        # 【核心逻辑】：挨个尝试备用节点
        for url in url_list:
            try:
                feed = feedparser.parse(url)
                # 检查是否真的抓到了有效数据 (防止虽然没报错，但返回了 403 页面)
                if feed.entries and len(feed.entries) > 0:
                    for entry in feed.entries[:10]:
                        raw_summary = entry.get('summary', entry.get('description', ''))
                        clean_summary = re.sub(r'<[^<]+?>', '', raw_summary)[:200]
                        raw_news.append(f"【{source_name}】{entry.title}\n原文:{clean_summary}\n链接:{entry.get('link', '')}\n")
                    
                    print(f"✅ {source_name} 抓取成功 (使用节点: {url[:30]}...)")
                    success = True
                    break # 成功了就跳出内部循环，抓下一家媒体
                else:
                    raise Exception("返回数据为空，节点可能已被拦截")
            except Exception as e:
                # 默默忽略这个节点的错误，继续试下一个
                continue 
        
        # 如果所有备用节点都试过了还是不行，才宣告失败
        if not success:
            print(f"⚠️ {source_name} 所有备用节点均失效。")
            
    print(f"✅ [Scraper] 抓取结束，正在洗牌...")
    random.shuffle(raw_news)
    return "\n".join(raw_news)