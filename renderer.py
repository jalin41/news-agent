import re

HTML_WRAPPER = """
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 650px; margin: 0 auto; color: #333; line-height: 1.6;">
    <div style="padding: 0 5px;">
        {news_content}
    </div>
    <p style="text-align: center; color: #999; font-size: 12px; margin-top: 50px; border-top: 1px dashed #eee; padding-top: 15px;">本早报由 AI 自动生成，仅供内部参考</p>
</div>
"""

# 统一的新闻卡片模板
NEWS_ITEM = """
<div style="margin-bottom: 22px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0;">
    <h2 style="font-size: 16px; color: #1a1a1a; margin: 0 0 6px 0; line-height: 1.4;">{title}</h2>

    <div style="font-size: 14px; color: #444; line-height: 1.6; text-align: justify; margin-bottom: 8px;">
        {content_body}
    </div>

    <div style="font-size: 12px; color: #888;">
        <span style="font-size: 11px; font-weight: bold; padding: 2px 5px; border-radius: 3px; margin-right: 8px; {source_style}">{source}</span>
        {footer_link}
    </div>
</div>
"""

def render_html(news_data):
    news_html = ""
    
    for news in news_data:
        is_foreign = news.get("is_foreign", False)
        
        # ================= 1. 决定正文内容与标签样式 =================
        if is_foreign:
            # 外网标签：红色
            source_style = "background: #fdf2f2; color: #c53030;"
            # 如果 AI 写出了长文就用长文，没写出来就用摘要
            if news.get("full_text"):
                content_body = re.sub(r'\n+', '<br><br>', news["full_text"].strip())
            else:
                content_body = news["summary"]
        else:
            # 国内标签：蓝色
            source_style = "background: #eef2f6; color: #4a6fa5;"
            content_body = news["summary"]

        # ================= 2. 决定底部链接 (强制物理隔离) =================
        if is_foreign:
            # 只要是外网新闻，绝对不给超链接，直接替换为声明
            footer_link = '<span style="color: #999;">🛡️ 外网已破除限制，全文由 AI 智能编译</span>'
        else:
            # 只有国内新闻才给跳转链接
            footer_link = f'<a href="{news["url"]}" target="_blank" style="color: #1a73e8; font-weight: bold; text-decoration: none;">🔗 点击阅读原文</a>'
            
        news_html += NEWS_ITEM.format(
            title=news["title"],
            source=news["source"],
            source_style=source_style,
            content_body=content_body,
            footer_link=footer_link
        )
        
    return HTML_WRAPPER.format(news_content=news_html)