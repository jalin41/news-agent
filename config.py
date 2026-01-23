import os
from openai import OpenAI

# ================= 1. AI API 配置 =================
# 请填入你重置后的新 Key
API_KEY = os.getenv("API_KEY", "你的本地测试KEY")
BASE_URL = "https://api.siliconflow.cn/v1"

# 初始化全局 AI 客户端
CLIENT = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ================= 2. 邮箱配置 =================
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "你的默认发件箱")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "你的本地授权码") 

RECEIVER_EMAILS = os.getenv("RECEIVER_EMAILS", "email1@test.com,email2@test.com").split(",")

# ================= 3. 目标 RSS 源 (全领域覆盖版) =================
RSS_FEEDS = {
    # 【政经定调】
    "人民网时政": "http://www.people.com.cn/rss/politics.xml",
    
    # 【科技商业】
    "36氪": "https://36kr.com/feed",

    # 【金融与社会民生】(这几个换成了极度稳定的节点)
    "第一财经(金融)": [
        "https://rsshub.rssforever.com/yicai/latest", # 节点A (不稳定时会被跳过)
        "https://rsshub.app/yicai/latest",            # 节点B (官方源)
        "https://hub.slarker.me/yicai/latest"         # 节点C (私有备用)
    ],
    "界面新闻(社会)": [
        "https://rsshub.rssforever.com/jiemian/lists/45",
        "https://rsshub.app/jiemian/lists/45",
        "https://hub.slarker.me/jiemian/lists/45"
    ],
    # "三联生活周刊(文化)": [
    #     "https://hub.slarker.me/lifeweek/channel/all", # 极速私有节点
    #     "https://rss.shab.fun/lifeweek/channel/all",   # 备用节点 B
    #     "https://rsshub.app/lifeweek/channel/all"      # 官方节点 C
    # ],

    
    # 澎湃新闻的官方合作直连源：国内最权威的社会、民生深度调查（极稳）
    "澎湃新闻(社会与思想)": [
        "https://rsshub.rssforever.com/thepaper/channel/25950",
        "https://rsshub.app/thepaper/channel/25950",
        "https://hub.slarker.me/thepaper/channel/25950"
    ],
    
    "国内热点(大盘聚合)": ["https://news.google.com/rss/headlines/section/topic/NATION?hl=zh-CN&gl=CN&ceid=CN:zh-Hans"],

    # 2. 少数派(科技与现代生活)：最顶级的数字生活、社会趋势深度媒体，官方源完全开放，极度稳定。
    "少数派(深度视点)": ["https://sspai.com/feed"],

    # 【国际视野】
    "路透社(全球)": [
        "https://news.yahoo.com/rss/world",
        "https://rsshub.rssforever.com/reuters/world", # 节点A
        "https://rsshub.app/reuters/world",            # 节点B (官方节点)
        "https://hub.slarker.me/reuters/world"         # 节点C (私有备用节点)
    ],
    "联合早报(国际)": [
        "https://rsshub.rssforever.com/zaobao/realtime/world",
        "https://rsshub.app/zaobao/realtime/world",
        "https://hub.slarker.me/zaobao/realtime/world"
    ],
    "BBC(中文网)": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"
}
