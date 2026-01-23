from scraper import get_news
from ai_pipeline import process_news
from renderer import render_html
from notifier import send_email
import opencc # 引入转换神器

def main():
    print("======== 🚀 新闻自动化系统启动 ========")
    
    # 1. 抓取
    news_text = get_news()
    if not news_text:
        return
        
    # 2. AI 处理
    news_data = process_news(news_text)
    
    # 3. 渲染
    html_content = render_html(news_data)
    
    # 4. 【终极防御】全站繁体强制转简体
    print("🔄 正在进行物理级繁简转换...")
    # 之前是 't2s.json'，现在去掉后缀，改为 't2s'
    converter = opencc.OpenCC('t2s') 
    final_html = converter.convert(html_content)
    
    # 5. 发送
    send_email(final_html)
    
    print("======== 🎉 系统运行完美结束 ========")

if __name__ == "__main__":
    main()