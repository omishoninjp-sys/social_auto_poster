#!/usr/bin/env python3
"""
Flask API 版本 - 適合部署到 Zeabur
Webhook 驅動：Shopify 有新商品時自動發文，不需要 cron-job
"""

from flask import Flask, request, jsonify, render_template_string, make_response, redirect
import random
import os
import hmac
import hashlib
import base64
import threading
import time
import requests
from datetime import datetime
from shopify_client import ShopifyClient
from social_clients import FacebookClient, InstagramClient, ThreadsClient
from smart_selector import SmartSelector, is_adult_product, TARGET_COLLECTION_ID
from config import Config
from image_utils import create_story_image_url
import re

app = Flask(__name__)

# ============================================
# 登入頁面模板
# ============================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登入 - 御用達 GOYOUTATI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .login-card h1 { font-size: 24px; margin-bottom: 8px; color: #333; }
        .login-card p { color: #666; margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; text-align: left; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 500; color: #555; }
        .form-group input {
            width: 100%; padding: 12px 16px; border: 2px solid #e0e0e0;
            border-radius: 8px; font-size: 16px; transition: border-color 0.3s;
        }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .btn {
            width: 100%; padding: 14px 28px; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; transition: all 0.3s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        .error {
            background: #ffebee; color: #c62828; padding: 12px;
            border-radius: 8px; margin-bottom: 20px; display: none;
        }
        .error.show { display: block; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>🎌 御用達 GOYOUTATI</h1>
        <p>社群自動發文系統</p>
        <div class="error" id="error">密鑰錯誤，請重試</div>
        <form method="POST" action="/login">
            <div class="form-group">
                <label>API 密鑰</label>
                <input type="password" name="secret" placeholder="請輸入密鑰" required>
            </div>
            <button type="submit" class="btn">登入</button>
        </form>
    </div>
    <script>
        if (window.location.search.includes('error=1')) {
            document.getElementById('error').classList.add('show');
        }
    </script>
</body>
</html>
"""

# ============================================
# HTML 管理頁面模板（加入 Webhook 狀態區塊）
# ============================================
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>御用達 GOYOUTATI - 社群自動發文系統</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .card {
            background: white; border-radius: 16px; padding: 24px;
            margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.9; }
        .logout-btn {
            position: fixed; top: 20px; right: 20px;
            background: rgba(255,255,255,0.2); color: white; border: none;
            padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px;
            text-decoration: none;
        }
        .logout-btn:hover { background: rgba(255,255,255,0.3); }
        .stat-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-radius: 12px; padding: 20px; text-align: center;
        }
        .stat-box h3 { font-size: 14px; color: #666; margin-bottom: 8px; }
        .stat-box .number { font-size: 36px; font-weight: bold; color: #333; }
        .stat-box .detail { font-size: 12px; color: #888; margin-top: 4px; }
        .btn {
            display: inline-block; padding: 14px 28px; border: none;
            border-radius: 8px; font-size: 16px; font-weight: 600;
            cursor: pointer; transition: all 0.3s; text-decoration: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
        .btn-secondary { background: #e0e0e0; color: #333; }
        .btn-secondary:hover { background: #d0d0d0; }
        .btn-group { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-top: 20px; }
        .status {
            display: inline-block; padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        }
        .status.online { background: #c8e6c9; color: #2e7d32; }
        .status.info { background: #e3f2fd; color: #1565c0; }
        .result-box {
            background: #f5f5f5; border-radius: 8px; padding: 16px;
            margin-top: 20px; display: none;
        }
        .result-box.show { display: block; }
        .result-box pre { white-space: pre-wrap; word-break: break-all; font-size: 13px; }
        .loading { display: none; text-align: center; padding: 20px; }
        .loading.show { display: block; }
        .spinner {
            border: 3px solid #f3f3f3; border-top: 3px solid #667eea;
            border-radius: 50%; width: 30px; height: 30px;
            animation: spin 1s linear infinite; margin: 0 auto 10px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #333; }
        .webhook-box {
            background: #f0f9ff; border: 1px solid #bfdbfe;
            border-radius: 10px; padding: 18px; margin-top: 12px;
        }
        .webhook-box code {
            display: block; background: #1e293b; color: #7dd3fc;
            padding: 12px 16px; border-radius: 8px; font-size: 13px;
            word-break: break-all; margin: 10px 0; user-select: all;
        }
        .webhook-box ol { padding-left: 20px; color: #444; font-size: 14px; line-height: 2; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 500; color: #555; }
        .form-group select, .form-group input {
            width: 100%; padding: 10px 12px; border: 1px solid #ddd;
            border-radius: 8px; font-size: 14px;
        }
        .checkbox-group { display: flex; gap: 16px; flex-wrap: wrap; }
        .checkbox-group label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
        .log-box {
            background: #1e293b; color: #94a3b8; border-radius: 10px;
            padding: 16px; font-size: 12px; font-family: monospace;
            max-height: 200px; overflow-y: auto; margin-top: 12px;
        }
        .log-box .ok { color: #86efac; }
        .log-box .err { color: #fca5a5; }
        .log-box .info { color: #7dd3fc; }
        .badge {
            background: #f3f4f6; border-radius: 6px; padding: 3px 8px;
            font-size: 12px; color: #6b7280; margin-left: 6px;
        }
    </style>
</head>
<body>
    <a href="/logout" class="logout-btn">登出</a>

    <div class="container">
        <div class="header">
            <h1>🎌 御用達 GOYOUTATI</h1>
            <p>社群自動發文系統 — Webhook 驅動</p>
        </div>

        <!-- Webhook 狀態 -->
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <h2 class="section-title" style="margin-bottom:0;">🔔 Webhook 自動發文</h2>
                <span class="status online">● 監聽中</span>
            </div>
            <p style="color:#555; font-size:14px; margin-bottom:12px;">
                系列有新商品加入時，Shopify 會自動通知此服務並立刻發文，無需 cron-job。
            </p>
            <div class="webhook-box">
                <strong style="font-size:14px;">📋 Shopify 後台設定步驟</strong>
                <ol>
                    <li>前往 <strong>Settings → Notifications → Webhooks</strong></li>
                    <li>點選 <strong>Create webhook</strong></li>
                    <li>Event 選 <strong>Product creation</strong></li>
                    <li>Format 選 <strong>JSON</strong></li>
                    <li>URL 填入以下網址：</li>
                </ol>
                <code id="webhook-url">載入中...</code>
                <p style="font-size:12px; color:#64748b; margin-top:4px;">
                    ⚠️ 若有設定 <code style="background:#e2e8f0;padding:1px 4px;border-radius:3px;">SHOPIFY_WEBHOOK_SECRET</code>，系統會自動驗證簽名。
                </p>
            </div>
        </div>

        <!-- 發文記錄 -->
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h2 class="section-title" style="margin-bottom:0;">📋 最近 Webhook 記錄</h2>
                <button class="btn btn-secondary" style="padding:6px 14px;font-size:13px;" onclick="loadLog()">🔄 重新整理</button>
            </div>
            <div class="log-box" id="log-box">
                <span class="info">等待載入...</span>
            </div>
        </div>

        <!-- 手動發文 -->
        <div class="card">
            <h2 class="section-title">🚀 手動發文（備用）</h2>
            <p style="color:#666; font-size:13px; margin-bottom:16px;">Webhook 是主要模式，這裡可手動觸發測試。</p>

            <div class="form-group">
                <label>發文數量</label>
                <select id="post-count">
                    <option value="1">1 篇</option>
                    <option value="2">2 篇</option>
                    <option value="4">4 篇</option>
                </select>
            </div>
            <div class="form-group">
                <label>發布平台</label>
                <div class="checkbox-group">
                    <label><input type="checkbox" id="platform-fb" checked> Facebook</label>
                    <label><input type="checkbox" id="platform-ig" checked> Instagram</label>
                    <label><input type="checkbox" id="platform-threads" checked> Threads</label>
                </div>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" onclick="postNow()">🚀 立即發文</button>
            </div>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>發文中，請稍候...</p>
            </div>
            <div class="result-box" id="result-box">
                <strong>發文結果：</strong>
                <pre id="result-content"></pre>
            </div>
        </div>
    </div>

    <script>
        const BASE_URL = window.location.origin;

        // 載入 Webhook URL
        fetch(`${BASE_URL}/api/get-secret-url`)
            .then(r => r.json())
            .then(d => { document.getElementById('webhook-url').textContent = d.webhook_url; });

        // 載入發文記錄
        async function loadLog() {
            try {
                const res = await fetch(`${BASE_URL}/api/webhook-log`);
                const data = await res.json();
                const box = document.getElementById('log-box');
                if (!data.logs || data.logs.length === 0) {
                    box.innerHTML = '<span class="info">尚無記錄</span>';
                    return;
                }
                box.innerHTML = data.logs.map(l => {
                    const cls = l.success ? 'ok' : 'err';
                    const icon = l.success ? '✅' : '❌';
                    return `<div class="${cls}">${icon} [${l.time}] ${l.title} → ${l.platforms}</div>`;
                }).join('');
                box.scrollTop = box.scrollHeight;
            } catch(e) {
                document.getElementById('log-box').innerHTML = '<span class="err">載入失敗</span>';
            }
        }

        // 手動發文
        async function postNow() {
            const count = document.getElementById('post-count').value;
            const platforms = [];
            if (document.getElementById('platform-fb').checked) platforms.push('fb');
            if (document.getElementById('platform-ig').checked) platforms.push('ig');
            if (document.getElementById('platform-threads').checked) platforms.push('threads');
            if (platforms.length === 0) { alert('請至少選擇一個平台'); return; }

            document.getElementById('loading').classList.add('show');
            document.getElementById('result-box').classList.remove('show');

            try {
                const res = await fetch(`${BASE_URL}/api/post?count=${count}&platforms=${platforms.join(',')}`);
                const data = await res.json();
                document.getElementById('result-content').textContent = JSON.stringify(data, null, 2);
                document.getElementById('result-box').classList.add('show');
                loadLog();
            } catch(e) {
                document.getElementById('result-content').textContent = '發文失敗: ' + e.message;
                document.getElementById('result-box').classList.add('show');
            } finally {
                document.getElementById('loading').classList.remove('show');
            }
        }

        document.addEventListener('DOMContentLoaded', loadLog);
    </script>
</body>
</html>
"""

# ============================================
# 記憶體中的 Webhook 發文記錄（重啟後清空）
# ============================================
webhook_log = []  # [{'time', 'title', 'platforms', 'success'}]
MAX_LOG = 50

# ============================================
# 去重機制
# 同一個商品 handle 在 DEDUP_TTL 秒內不重複發文
# ============================================
recently_posted = {}      # { handle: timestamp }
DEDUP_TTL = 3600          # 1 小時
DEDUP_LOCK = threading.Lock()


def is_duplicate(product):
    """回傳 True 表示近期已發過，應跳過"""
    handle = product.get('handle') or str(product.get('id', ''))
    now = time.time()
    with DEDUP_LOCK:
        # 清理過期記錄
        for k in [k for k, ts in recently_posted.items() if now - ts > DEDUP_TTL]:
            del recently_posted[k]
        if handle in recently_posted:
            elapsed = int(now - recently_posted[handle])
            print(f"[去重] ⏭️  {handle} 在 {elapsed} 秒前已發過，跳過")
            return True
        return False


def mark_posted_dedup(product):
    """發文成功後，把 handle 記錄到去重表"""
    handle = product.get('handle') or str(product.get('id', ''))
    with DEDUP_LOCK:
        recently_posted[handle] = time.time()


def append_log(title, platforms_result):
    """記錄發文結果"""
    success = any(r.get('success') for r in platforms_result.values()) if platforms_result else False
    platform_names = ', '.join(
        f"{k}{'✓' if v.get('success') else '✗'}"
        for k, v in platforms_result.items()
    )
    webhook_log.append({
        'time': datetime.now().strftime('%m/%d %H:%M'),
        'title': title[:30],
        'platforms': platform_names,
        'success': success
    })
    if len(webhook_log) > MAX_LOG:
        webhook_log.pop(0)


def get_config():
    return Config()


def get_shopify_client(config):
    return ShopifyClient(
        store_url=config.SHOPIFY_STORE_URL,
        access_token=config.SHOPIFY_ACCESS_TOKEN
    )


def get_jpy_to_twd_rate():
    DEFAULT_RATE = 0.22
    for url in [
        "https://api.exchangerate-api.com/v4/latest/JPY",
        "https://open.er-api.com/v6/latest/JPY"
    ]:
        try:
            r = requests.get(url, timeout=5)
            if r.ok:
                return r.json().get('rates', {}).get('TWD', DEFAULT_RATE)
        except:
            pass
    return DEFAULT_RATE


def generate_post_content(product, config):
    """
    生成貼文內容
    文案主打「一條連結，送到你家」服務
    hashtag 從商品標題 / tags 自動抽關鍵字
    """
    title   = product.get('title', '')
    handle  = product.get('handle', '')
    images  = product.get('images', [])
    image_urls = [img.get('src') for img in images if img.get('src')]
    image_url  = image_urls[0] if image_urls else None

    tags = product.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    product_type = product.get('product_type', '')

    # ── 價格 ────────────────────────────────────────────────
    variants = product.get('variants', [])
    price_jpy_str = variants[0].get('price', '0') if variants else '0'
    try:
        price_jpy = float(price_jpy_str)
        if price_jpy > 0:
            rate      = get_jpy_to_twd_rate()
            price_twd = int(price_jpy * rate)
            price_line = f"💰 ¥{int(price_jpy):,}（約NT${price_twd:,}）\n含關稅，出貨前補運費（每公斤¥1,000／約NT$200）"
        else:
            price_line = "💰 價格請詢價"
    except:
        price_line = "💰 價格請詢價"

    product_url = 'https://goyoutati.com/pages/%E6%97%A5%E6%9C%AC%E4%BB%A3%E8%B3%BC-%E4%B8%80%E6%A2%9D%E9%80%A3%E7%B5%90-%E9%80%81%E5%88%B0%E4%BD%A0%E5%AE%B6'

    # ── Hashtag：基礎 + 從標題/tags 自動抽關鍵字 ────────────
    handle_lower = handle.lower()
    title_lower  = title.lower()
    all_text     = f"{title_lower} {handle_lower} {product_type.lower()} {' '.join(tags).lower()}"

    # 品牌 tag
    brand_tag = ''
    for kw, t in [
        ('bape',        '#BAPE'),
        ('workman',     '#WORKMAN'),
        ('human-made',  '#HumanMade'),
        ('human made',  '#HumanMade'),
        ('x-girl',      '#Xgirl'),
        ('yokumoku',    '#YOKUMOKU'),
        ('adidas',      '#adidas'),
        ('nike',        '#Nike'),
        ('uniqlo',      '#UNIQLO'),
        ('無印',         '#無印良品'),
        ('muji',        '#MUJI'),
    ]:
        if kw in all_text:
            brand_tag = t
            break
    for kw, t in [
        ('小倉山莊', '#小倉山莊'), ('砂糖奶油樹', '#砂糖奶油樹'),
        ('坂角',    '#坂角總本舖'), ('風月堂',    '#神戶風月堂'),
        ('虎屋',    '#虎屋羊羹'),  ('資生堂',    '#資生堂PARLOUR'),
        ('菊廼舍',  '#銀座菊廼舍'), ('楓糖',     '#楓糖男孩'),
    ]:
        if kw in title or kw in handle:
            brand_tag = t
            break

    # 商品類型 tag（從標題關鍵字抓）
    keyword_tags = []
    keyword_map = [
        # 服飾
        ('外套',   '#外套'), ('夾克',  '#夾克'), ('連帽',   '#連帽'),
        ('T恤',    '#T恤'),  ('Tシャツ','#Tシャツ'), ('褲',  '#褲裝'),
        ('裙',     '#裙裝'), ('包包',  '#包包'), ('鞋',     '#鞋款'),
        # 家電 / 3C
        ('美容儀', '#美容儀'), ('掃地機', '#掃地機器人'), ('空氣清淨', '#空氣清淨機'),
        ('耳機',   '#耳機'),  ('戒指',  '#智慧戒指'),  ('相機',    '#相機'),
        ('電動牙刷','#電動牙刷'),
        # 食品
        ('巧克力', '#巧克力'), ('餅乾',  '#日本餅乾'), ('羊羹', '#和菓子'),
        ('甜點',   '#日本甜點'),
    ]
    for kw, t in keyword_map:
        if kw in title or kw in all_text:
            keyword_tags.append(t)
            if len(keyword_tags) >= 2:
                break

    # ── 固定服務文案 ─────────────────────────────────────────
    service_body = """🇯🇵 看到喜歡的日本商品，貼上連結就能買！
GOYOUTATI 御用達幫你代購，空運含稅直送台灣。

📦 服務流程
1️⃣ 貼上任意日本商品連結，或直接在本站下單
2️⃣ 我們代購並集運至台灣倉（免費存放最長 1 個月）
3️⃣ 到倉 Email 通知 → 確認運費 → 到府配送

✅ 含稅含關稅，無隱藏費用
✅ 業界最低，每公斤1,000円日幣約台幣200
✅ 無最低出貨重量，1KG也能出貨
✅ 無台灣端派送費"""

    # ── 組合貼文（FB / IG 版，含 hashtag）──────────────────
    post_text_with_tags = f"""✨ {title}

{service_body}

{price_line}
🛒 立即購買：{product_url}
"""

    # ── Threads 版（無 hashtag，截到 500 字）────────────────
    post_text_no_tags = f"""✨ {title}

{service_body}

{price_line}
🛒 立即購買：{product_url}
"""
    if len(post_text_no_tags) > 500:
        post_text_no_tags = post_text_no_tags[:497] + '...'

    return {
        'text':         post_text_with_tags,
        'text_no_tags': post_text_no_tags,
        'image_url':    image_url,
        'image_urls':   image_urls,
        'product_url':  product_url,
        'title':        title
    }

def post_to_platforms(content, platforms, config):
    """發布到各平台（貼文 + 限動）"""
    results = {}

    story_image_url = None
    if content.get('image_url'):
        print("[限動] 正在處理圖片...")
        story_image_url = create_story_image_url(content['image_url'])

    if 'fb' in platforms and config.FB_PAGE_ID and config.FB_ACCESS_TOKEN:
        try:
            fb = FacebookClient(config.FB_PAGE_ID, config.FB_ACCESS_TOKEN)
            image_urls = content.get('image_urls', [])
            if len(image_urls) > 1:
                result = fb.post_multiple_photos(content['text'], image_urls)
            else:
                result = fb.post(content['text'], content['image_url'], content['product_url'])
            results['facebook'] = {'success': True, 'post_id': result.get('id')}
        except Exception as e:
            results['facebook'] = {'success': False, 'error': str(e)}
        try:
            if story_image_url:
                story_result = fb.post_story(story_image_url)
                results['facebook_story'] = {'success': True, 'post_id': story_result.get('post_id')}
        except Exception as e:
            results['facebook_story'] = {'success': False, 'error': str(e)}

    if 'ig' in platforms and config.IG_ACCOUNT_ID and config.IG_ACCESS_TOKEN:
        if not content.get('image_url'):
            results['instagram'] = {'success': False, 'error': '商品無圖片，跳過 IG'}
            print("[IG] ⚠️  商品無圖片，跳過 Instagram")
        else:
            try:
                ig = InstagramClient(config.IG_ACCOUNT_ID, config.IG_ACCESS_TOKEN)
                image_urls = content.get('image_urls', [])
                if len(image_urls) > 1:
                    result = ig.post_carousel(content['text'], image_urls[:10])
                else:
                    result = ig.post(content['text'], content['image_url'])
                results['instagram'] = {'success': True, 'post_id': result.get('id')}
            except Exception as e:
                results['instagram'] = {'success': False, 'error': str(e)}
        try:
            if story_image_url:
                story_result = ig.post_story(story_image_url)
                results['instagram_story'] = {'success': True, 'post_id': story_result.get('id')}
        except Exception as e:
            results['instagram_story'] = {'success': False, 'error': str(e)}

    if 'threads' in platforms and config.THREADS_USER_ID and config.THREADS_ACCESS_TOKEN:
        try:
            threads = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)
            threads_text = content.get('text_no_tags', content['text'])
            # Threads 最多 500 字元
            if len(threads_text) > 500:
                threads_text = threads_text[:497] + '...'
            result = threads.post(threads_text, content['image_url'])
            results['threads'] = {'success': True, 'post_id': result.get('id')}
        except Exception as e:
            results['threads'] = {'success': False, 'error': str(e)}

    return results


# ============================================
# 驗證 Shopify Webhook 簽名
# ============================================
def verify_shopify_webhook(request):
    """
    驗證 Shopify 送來的 Webhook 是否合法
    需要在 .env 設定 SHOPIFY_WEBHOOK_SECRET
    （從 Shopify Admin > Settings > Notifications > Webhooks 取得）
    """
    webhook_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')
    if not webhook_secret:
        # 未設定 secret，跳過驗證（不建議）
        print("[Webhook] ⚠️  未設定 SHOPIFY_WEBHOOK_SECRET，跳過簽名驗證")
        return True

    shopify_hmac = request.headers.get('X-Shopify-Hmac-Sha256', '')
    raw_body = request.get_data()

    computed = base64.b64encode(
        hmac.new(webhook_secret.encode('utf-8'), raw_body, hashlib.sha256).digest()
    ).decode('utf-8')

    return hmac.compare_digest(computed, shopify_hmac)


# ============================================
# Webhook 背景發文處理
# ============================================
def handle_new_product_async(product):
    """
    收到新商品 Webhook 後的背景處理邏輯：
    1. 等待 Shopify 完成 collection membership 更新
    2. 確認商品在目標系列中
    3. 過濾成人商品
    4. 發文
    """
    title = product.get('title', 'Unknown')
    product_id = product.get('id')

    print(f"[Webhook] 收到新商品：{title} (ID: {product_id})")

    # ── 去重：同一 handle 1 小時內只發一次 ──────────────────
    if is_duplicate(product):
        return

    # 等待 Shopify 後台處理 collection 關聯（通常 1~3 秒）
    time.sleep(5)

    config = get_config()
    shopify = get_shopify_client(config)

    # 確認商品是否在目標系列中
    products_in_collection = shopify.get_products_by_collection_id(TARGET_COLLECTION_ID, limit=250)
    ids_in_collection = {p['id'] for p in products_in_collection}

    if product_id not in ids_in_collection:
        print(f"[Webhook] ⏭️  商品不在目標系列（ID: {TARGET_COLLECTION_ID}），跳過：{title}")
        return

    # 過濾成人商品
    if is_adult_product(product):
        print(f"[Webhook] 🔞 成人商品，跳過：{title}")
        return

    # ── 先佔位，防止其他執行緒同時進來 ──────────────────────
    mark_posted_dedup(product)

    print(f"[Webhook] ✅ 確認商品在系列中，準備發文：{title}")

    content = generate_post_content(product, config)
    platforms = ['fb', 'ig', 'threads']
    results = post_to_platforms(content, platforms, config)

    # 記錄結果
    append_log(title, results)

    for platform, result in results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"[Webhook] {status} {platform}：{result.get('post_id') or result.get('error')}")


# ============================================
# 路由
# ============================================

@app.route('/')
def index():
    api_secret = os.getenv('API_SECRET')
    cookie_secret = request.cookies.get('auth_secret')
    if api_secret and cookie_secret == api_secret:
        return render_template_string(ADMIN_HTML)
    return render_template_string(LOGIN_HTML)


@app.route('/login', methods=['POST'])
def login():
    api_secret = os.getenv('API_SECRET')
    provided_secret = request.form.get('secret', '')
    if api_secret and provided_secret == api_secret:
        response = make_response(redirect('/'))
        response.set_cookie('auth_secret', provided_secret, max_age=60*60*24*30, httponly=True)
        return response
    return redirect('/?error=1')


@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('auth_secret')
    return response


def check_auth():
    api_secret = os.getenv('API_SECRET')
    cookie_secret = request.cookies.get('auth_secret')
    return api_secret and cookie_secret == api_secret


# ============================================
# 🔔 主要 Webhook 端點
# ============================================
@app.route('/webhook/product-created', methods=['POST'])
def webhook_product_created():
    """
    Shopify Webhook 接收端點
    - Event: Product creation
    - Shopify 設定路徑: Settings → Notifications → Webhooks
    - 建議設定 SHOPIFY_WEBHOOK_SECRET 以驗證來源
    """
    # 驗證簽名
    if not verify_shopify_webhook(request):
        print("[Webhook] ❌ 簽名驗證失敗，拒絕請求")
        return jsonify({'error': 'Invalid signature'}), 401

    product = request.get_json(silent=True)
    if not product:
        return jsonify({'error': 'No product data'}), 400

    # Shopify 要求在 5 秒內回應，所以立刻回 200，背景處理
    thread = threading.Thread(target=handle_new_product_async, args=(product,))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'message': '已收到，背景處理中'}), 200


# ============================================
# 內部 API（需登入）
# ============================================

@app.route('/api/webhook-log')
def api_webhook_log():
    """取得最近 Webhook 發文記錄"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    return jsonify({'success': True, 'logs': list(reversed(webhook_log))})


@app.route('/api/post')
def api_post():
    """手動觸發發文（需登入）"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)

    count = min(int(request.args.get('count', 1)), 10)
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]

    posted = []
    for i in range(count):
        product, cat = selector.get_next_product('fashion')
        if not product:
            break
        content = generate_post_content(product, config)
        results = post_to_platforms(content, platforms, config)
        append_log(product.get('title', ''), results)
        posted.append({
            'title': product.get('title'),
            'platforms': results
        })

    return jsonify({
        'success': len(posted) > 0,
        'count': len(posted),
        'posts': posted,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/get-secret-url')
def api_get_secret_url():
    """取得 Webhook URL 與 cron URL"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    api_secret = os.getenv('API_SECRET', '')
    base_url = request.host_url.rstrip('/')

    return jsonify({
        'webhook_url': f"{base_url}/webhook/product-created",
        'manual_url': f"{base_url}/post/smart?secret={api_secret}"
    })


@app.route('/api/stats')
def api_stats():
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)
    stats = selector.get_stats()

    return jsonify({
        'success': True,
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# 公開端點
# ============================================

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'mode': 'webhook-driven',
        'target_collection_id': TARGET_COLLECTION_ID,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/post/smart')
def post_smart():
    """備用：手動 HTTP 觸發發文（可繼續用 cron-job 呼叫，或手動測試）"""
    api_secret = os.getenv('API_SECRET')
    if api_secret:
        provided_secret = request.args.get('secret')
        if provided_secret != api_secret:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    count = min(int(request.args.get('count', 1)), 10)
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]

    def do_post():
        config = get_config()
        shopify = get_shopify_client(config)
        selector = SmartSelector(shopify, config)
        for i in range(count):
            product, cat = selector.get_next_product('fashion')
            if not product:
                break
            content = generate_post_content(product, config)
            results = post_to_platforms(content, platforms, config)
            append_log(product.get('title', ''), results)
            for platform, result in results.items():
                status = "✅" if result.get('success') else "❌"
                print(f"[手動發文] {status} {platform}")

    thread = threading.Thread(target=do_post)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': '發文請求已收到，背景執行中',
        'count': count,
        'platforms': platforms,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"🔔 Webhook 端點：http://0.0.0.0:{port}/webhook/product-created")
    app.run(host='0.0.0.0', port=port, debug=debug)
