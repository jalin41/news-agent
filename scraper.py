import feedparser
import random
import re
from datetime import datetime, timezone, timedelta
import time
from config import RSS_FEEDS

def get_news():
    print("🕷️ [Scraper] 正在抓取新闻源并进行时效初筛...")

    # 设定时间防线：只允许过去 24 小时（1天）内的数据通过
    time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
    time_limit_struct = time_limit.timetuple()

    feedparser.USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    raw_news = []
    
    for source_name, url_list in RSS_FEEDS.items():
        if isinstance(url_list, str):
            url_list = [url_list]
            
        success = False
        for url in url_list:
            try:
                feed = feedparser.parse(url)
                if feed.entries and len(feed.entries) > 0:
                    valid_count = 0
                    
                    # 【修改1】：把 [:10] 放大到 [:30]，深挖鱼塘
                    for entry in feed.entries[:30]: 
                        
                        # 【修改2】：物理时间锁。如果新闻发布时间早于24小时前，直接扔掉
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            if entry.published_parsed < time_limit_struct:
                                continue # 跳过这条旧新闻，继续检查下一条
                                
                        raw_summary = entry.get('summary', entry.get('description', ''))
                        clean_summary = re.sub(r'<[^<]+?>', '', raw_summary)[:200]
                        raw_news.append(f"【{source_name}】{entry.title}\n原文:{clean_summary}\n链接:{entry.get('link', '')}\n")
                        valid_count += 1
                    
                    print(f"✅ {source_name} 抓取成功 (过滤出 {valid_count} 条24h内资讯)")
                    success = True
                    break 
                else:
                    raise Exception("返回数据为空")
            except Exception as e:
                continue 
        
        if not success:
            print(f"⚠️ {source_name} 所有备用节点均失效。")
            
    print(f"✅ [Scraper] 原始蓄水池共汇聚 {len(raw_news)} 条新鲜资讯，开始洗牌...")
    random.shuffle(raw_news)
    
    indexed_news = []
    for i, news_str in enumerate(raw_news):
        # 用正则从你原来的字符串里拆出各个部分
        match = re.search(r"【(.*?)】(.*?)\n原文:(.*?)\n链接:(.*?)\n", news_str)
        if match:
            indexed_news.append({
                "id": i,
                "source": match.group(1),
                "title": match.group(2),
                "original_summary": match.group(3),
                "url": match.group(4)
            })
            
    return indexed_news # 返回列表，而不是字符串
