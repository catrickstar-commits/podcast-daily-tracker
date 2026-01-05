import requests
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

# === 配置区 ===
# 榜单接口地址
URLS = {
    "编辑推荐": "https://rsshub.app/xiaoyuzhou/editor_choice.json",
    "热门榜": "https://rsshub.app/xiaoyuzhou/ranking/hot.json",
    "锋芒榜": "https://rsshub.app/xiaoyuzhou/ranking/sharp.json",
    "新星榜": "https://rsshub.app/xiaoyuzhou/ranking/new.json"
}

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

# 1. 获取数据
def fetch_data():
    all_data = []
    print("开始抓取数据...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for category, url in URLS.items():
        print(f"正在获取: {category}...")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                
                # 每个榜单只取前 10 名，防止图片太长
                for index, item in enumerate(items[:10]): 
                    all_data.append({
                        "日期": get_today_date(),
                        "榜单类型": category,
                        "排名": index + 1,
                        "播客标题": item.get('title', '无标题'),
                        "作者": item.get('author', {}).get('name', '未知'),
                        "链接": item.get('url', '')
                    })
            else:
                print(f"❌ {category} 抓取失败: {resp.status_code}")
        except Exception as e:
            print(f"❌ {category} 出错: {e}")
            
    return pd.DataFrame(all_data)

# 2. 保存 CSV
def save_csv(df):
    filename = "xiaoyuzhou_data.csv"
    if os.path.exists(filename):
        df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    print("✅ 数据已保存到 CSV")

# 3. 生成榜单截图 (因为榜单没有网页版，我们自己画一个网页来截图)
def generate_chart_screenshot(df):
    if df.empty: return
    
    print("正在生成榜单长图...")
    
    # 简单的 HTML 模板，模拟 App 样式
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; background: #f6f6f6; padding: 20px; width: 400px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .title {{ font-size: 24px; font-weight: bold; color: #333; }}
            .date {{ color: #888; font-size: 14px; margin-top: 5px; }}
            .card {{ background: white; border-radius: 12px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            .card-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; border-left: 4px solid #ff5e5e; padding-left: 10px; }}
            .row {{ display: flex; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
            .rank {{ font-size: 18px; font-weight: bold; color: #ff5e5e; width: 30px; }}
            .info {{ flex: 1; }}
            .p-title {{ font-size: 15px; font-weight: 500; color: #333; margin: 0 0 4px 0; }}
            .p-author {{ font-size: 12px; color: #999; margin: 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">小宇宙日报</div>
            <div class="date">{get_today_date()}</div>
        </div>
    """
    
    # 循环生成每个榜单的 HTML
    for category in URLS.keys():
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
        html += '</div>'
    
    html += "</body></html>"
    
    # 保存为临时网页
    with open("temp_chart.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # 截图
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # 加载本地网页
        page.goto(f"file://{os.getcwd()}/temp_chart.html")
        page.screenshot(path=f"daily_chart_{get_today_date()}.png", full_page=True)
        browser.close()
        print("✅ 榜单长图截图完成")

# 4. 截取官网首页 (这是真实网页截图)
def capture_homepage():
    print("正在截取官网首页...")
    with sync_playwright() as p:
        # 模拟手机浏览
        iphone = p.devices['iPhone 12']
        browser = p.chromium.launch()
        context = browser.new_context(**iphone)
        page = context.new_page()
        
        try:
            page.goto("https://www.xiaoyuzhoufm.com/", timeout=60000)
            page.wait_for_timeout(5000) # 等待加载
            page.screenshot(path=f"homepage_{get_today_date()}.png")
            print("✅ 首页截图完成")
        except Exception as e:
            print(f"❌ 首页截图失败: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # 执行所有步骤
    df = fetch_data()
    if not df.empty:
        save_csv(df)
        generate_chart_screenshot(df)
        capture_homepage()
    else:
        print("❌ 未获取到数据，跳过后续步骤")
