import pandas as pd
from datetime import datetime
import os
import json
import time
from playwright.sync_api import sync_playwright

# === 增强版配置 ===
# 我们保留官方源，因为用浏览器模拟访问时，官方源通常不会拦截
RSSHUB_DOMAINS = [
    "https://rsshub.app",
    "https://rsshub.feedly.cn",
    "https://rsshub.pseudoyu.com",
    "https://rsshub.mormm.com"
]

ROUTES = {
    "编辑推荐": "/xiaoyuzhou/editor_choice.json",
    "热门榜": "/xiaoyuzhou/ranking/hot.json",
    "锋芒榜": "/xiaoyuzhou/ranking/sharp.json",
    "新星榜": "/xiaoyuzhou/ranking/new.json"
}

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

# === 核心升级：用浏览器去“看”数据，而不是用脚本“抓” ===
def fetch_data_via_browser(browser, route):
    for domain in RSSHUB_DOMAINS:
        url = f"{domain}{route}"
        print(f"🕵️ 正在伪装访问: {url} ...")
        
        page = browser.new_page()
        try:
            # 访问页面，等待3秒让数据加载
            page.goto(url, timeout=30000)
            # RSSHub 返回的是纯文本 JSON，我们直接提取页面里的文字
            # 浏览器会自动把 JSON 放在 pre 标签或者 body 里
            content = page.inner_text("body")
            
            # 尝试解析 JSON
            data = json.loads(content)
            
            # 检查数据是否有效
            if 'items' in data:
                print("✅ 成功获取数据！")
                page.close()
                return data
            else:
                print("❌ 数据格式不对，尝试下一个...")
                
        except Exception as e:
            print(f"❌ 访问失败: {e}")
        
        page.close()
        
    print("⚠️ 所有线路均失败")
    return None

def process_data():
    all_data = []
    print("🚀 启动浏览器引擎...")
    
    with sync_playwright() as p:
        # 启动一个无头浏览器 (Headless Chrome)
        browser = p.chromium.launch(headless=True)
        
        for category, route in ROUTES.items():
            data = fetch_data_via_browser(browser, route)
            
            if data:
                items = data.get('items', [])
                for index, item in enumerate(items[:10]): 
                    all_data.append({
                        "日期": get_today_date(),
                        "榜单类型": category,
                        "排名": index + 1,
                        "播客标题": item.get('title', '无标题'),
                        "作者": item.get('author', {}).get('name', '未知'),
                        "链接": item.get('url', '')
                    })
            # 稍微休息一下，防止访问太快被发现
            time.sleep(2)
            
        browser.close()

    return pd.DataFrame(all_data)

def save_csv(df):
    filename = "xiaoyuzhou_data.csv"
    if os.path.exists(filename):
        df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    print("💾 数据已保存到 CSV")

def generate_chart_screenshot(df):
    if df.empty: return
    print("🎨 正在生成榜单长图...")
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; background: #f6f6f6; padding: 20px; width: 400px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .title {{ font-size: 24px; font-weight: bold; color: #333; }}
            .date {{ color: #888; font-size: 14px; margin-top: 5px; }}
            .card {{ background: white; border-radius: 12px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            .card-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; border-left: 4px solid #ff5e5e; padding-left: 10px; }}
            .row {{ display: flex; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
            .rank {{ font-size: 18px; font-weight: bold; color: #ff5e5e; width: 30px; }}
            .info {{ flex: 1; overflow: hidden; }}
            .p-title {{ font-size: 15px; font-weight: 500; color: #333; margin: 0 0 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .p-author {{ font-size: 12px; color: #999; margin: 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">小宇宙日报</div>
            <div class="date">{get_today_date()}</div>
        </div>
    """
    
    for category in ROUTES.keys():
        subset = df[df['榜单类型'] == category]
        if subset.empty: continue
        
        html += f'<div class="card"><div class="card-title">{category} Top 10</div>'
        for _, row in subset.iterrows():
            html += f"""
            <div class="row">
                <div class="rank">{row['排名']}</div>
                <div class="info">
                    <p class="p-title">{row['播客标题']}</p>
                    <p class="p-author">{row['作者']}</p>
                </div>
            </div>
            """
        html += '</div></body></html>'
    
    with open("temp_chart.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{os.getcwd()}/temp_chart.html")
        page.screenshot(path=f"daily_chart_{get_today_date()}.png", full_page=True)
        browser.close()
        print("📸 榜单截图完成")

def capture_homepage():
    print("📸 正在截取官网首页...")
    with sync_playwright() as p:
        iphone = p.devices['iPhone 12']
        browser = p.chromium.launch()
        context = browser.new_context(**iphone)
        page = context.new_page()
        try:
            page.goto("https://www.xiaoyuzhoufm.com/", timeout=60000)
            page.wait_for_timeout(5000)
            page.screenshot(path=f"homepage_{get_today_date()}.png")
            print("✅ 首页截图完成")
        except Exception as e:
            print(f"❌ 首页截图失败: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    try:
        df = process_data()
        if not df.empty:
            save_csv(df)
            generate_chart_screenshot(df)
            capture_homepage()
        else:
            raise Exception("❌ 所有线路均无法获取数据！")
    except Exception as e:
        print(f"Fatal Error: {e}")
        # 这里一定要抛出异常，让 GitHub Action 变红
        raise e
