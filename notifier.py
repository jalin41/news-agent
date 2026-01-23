import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, SMTP_PORT, RECEIVER_EMAILS # 引入新的列表变量

def send_email(html_content):
    print("📧 [Notifier] 正在准备群发邮件...")
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    # 【修改点1】：将列表用逗号拼接成字符串，用于在收件人栏显示
    msg['To'] = ", ".join(RECEIVER_EMAILS) 
    msg['Subject'] = "📰 今日要闻总览"

    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # 【修改点2】：直接把 RECEIVER_EMAILS 列表传给 sendmail 函数，SMTP 会自动群发
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_string())
        
        server.quit()
        print(f"✅ [Notifier] 邮件已成功群发至 {len(RECEIVER_EMAILS)} 个邮箱！")
    except Exception as e:
        print(f"❌ [Notifier] 邮件发送失败: {e}")