#!/usr/bin/env python3
"""
Flask API 版本 - 適合部署到 Zeabur
可透過 HTTP 請求觸發發文

部署到 Zeabur 後，使用 cron-job.org 定時呼叫 API
"""

from flask import Flask, request, jsonify, render_template_string, make_response, redirect
import random
import os
import requests
from datetime import datetime
from shopify_client import ShopifyClient
from social_clients import FacebookClient, InstagramClient, ThreadsClient
from smart_selector import SmartSelector, is_adult_product
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
        .login-card h1 {
            font-size: 24px;
            margin-bottom: 8px;
            color: #333;
        }
        .login-card p {
            color: #666;
            margin-bottom: 24px;
        }
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #555;
        }
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transition: all 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .error.show {
            display: block;
        }
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
        // 檢查 URL 是否有 error 參數
        if (window.location.search.includes('error=1')) {
            document.getElementById('error').classList.add('show');
        }
    </script>
</body>
</html>
"""

# ============================================
# HTML 管理頁面模板
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
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        .header p {
            opacity: 0.9;
        }
        .logout-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        .stat-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-box h3 {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        .stat-box .number {
            font-size: 36px;
            font-weight: bold;
            color: #333;
        }
        .stat-box .detail {
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }
        .btn {
            display: inline-block;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #e0e0e0;
            color: #333;
        }
        .btn-secondary:hover {
            background: #d0d0d0;
        }
        .btn-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 20px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status.online {
            background: #c8e6c9;
            color: #2e7d32;
        }
        .result-box {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 16px;
            margin-top: 20px;
            display: none;
        }
        .result-box.show {
            display: block;
        }
        .result-box pre {
            white-space: pre-wrap;
            word-break: break-all;
            font-size: 13px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .loading.show {
            display: block;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #333;
        }
        .api-info {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }
        .api-info code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            word-break: break-all;
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #555;
        }
        .form-group select, .form-group input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        .checkbox-group {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <a href="/logout" class="logout-btn">登出</a>
    
    <div class="container">
        <div class="header">
            <h1>🎌 御用達 GOYOUTATI</h1>
            <p>社群自動發文系統（服飾專用）</p>
        </div>

        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 class="section-title" style="margin-bottom: 0;">📊 發文統計</h2>
                <span class="status online">● 系統運作中</span>
            </div>
            
            <div class="stat-box">
                <h3>👔 服飾</h3>
                <div class="number" id="fashion-remaining">-</div>
                <div class="detail">最新商品池 / 總數 <span id="fashion-total">-</span></div>
            </div>
            
            <div style="margin-top: 16px;">
                <button class="btn btn-secondary" onclick="loadStats()">🔄 重新整理</button>
            </div>
        </div>

        <div class="card">
            <h2 class="section-title">🚀 立即發文（服飾）</h2>
            
            <div class="form-group">
                <label>發文數量</label>
                <select id="post-count">
                    <option value="1">1 篇</option>
                    <option value="2">2 篇</option>
                    <option value="4">4 篇</option>
                    <option value="6">6 篇</option>
                    <option value="10">10 篇</option>
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

        <div class="card">
            <h2 class="section-title">⏰ 排程設定</h2>
            <p style="color: #666; margin-bottom: 16px;">使用 cron-job.org 設定自動發文排程</p>
            
            <div class="api-info">
                <p><strong>API 網址：</strong></p>
                <code id="api-url">載入中...</code>
                <p style="margin-top: 12px; font-size: 13px; color: #666;">
                    在 cron-job.org 建立排程，設定每天特定時間呼叫此網址
                </p>
            </div>
        </div>
    </div>

    <script>
        const BASE_URL = window.location.origin;
        
        // 載入統計
        async function loadStats() {
            try {
                const res = await fetch(`${BASE_URL}/api/stats`);
                const data = await res.json();
                
                if (data.success) {
                    document.getElementById('fashion-remaining').textContent = data.stats.fashion.remaining;
                    document.getElementById('fashion-total').textContent = data.stats.fashion.total;
                }
            } catch (e) {
                console.error('載入統計失敗', e);
            }
        }
        
        // 立即發文
        async function postNow() {
            const count = document.getElementById('post-count').value;
            const platforms = [];
            if (document.getElementById('platform-fb').checked) platforms.push('fb');
            if (document.getElementById('platform-ig').checked) platforms.push('ig');
            if (document.getElementById('platform-threads').checked) platforms.push('threads');
            
            if (platforms.length === 0) {
                alert('請至少選擇一個平台');
                return;
            }
            
            document.getElementById('loading').classList.add('show');
            document.getElementById('result-box').classList.remove('show');
            
            try {
                let url = `${BASE_URL}/api/post?count=${count}&platforms=${platforms.join(',')}&category=fashion`;
                
                const res = await fetch(url);
                const data = await res.json();
                
                document.getElementById('result-content').textContent = JSON.stringify(data, null, 2);
                document.getElementById('result-box').classList.add('show');
                
                // 重新載入統計
                loadStats();
            } catch (e) {
                document.getElementById('result-content').textContent = '發文失敗: ' + e.message;
                document.getElementById('result-box').classList.add('show');
            } finally {
                document.getElementById('loading').classList.remove('show');
            }
        }
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            // 顯示 cron-job 用的 API URL（需要帶 secret）
            fetch(`${BASE_URL}/api/get-secret-url`)
                .then(r => r.json())
                .then(d => {
                    document.getElementById('api-url').textContent = d.url;
                });
        });
    </script>
</body>
</html>
"""

def get_config():
    """取得設定"""
    return Config()

def get_shopify_client(config):
    """取得 Shopify 客戶端"""
    return ShopifyClient(
        store_url=config.SHOPIFY_STORE_URL,
        access_token=config.SHOPIFY_ACCESS_TOKEN
    )

def get_jpy_to_twd_rate():
    """
    取得日圓對台幣匯率
    使用免費 API，失敗時用預設值
    """
    DEFAULT_RATE = 0.22
    
    try:
        url = "https://api.exchangerate-api.com/v4/latest/JPY"
        response = requests.get(url, timeout=5)
        if response.ok:
            data = response.json()
            rate = data.get('rates', {}).get('TWD', DEFAULT_RATE)
            return rate
    except:
        pass
    
    try:
        url = "https://open.er-api.com/v6/latest/JPY"
        response = requests.get(url, timeout=5)
        if response.ok:
            data = response.json()
            rate = data.get('rates', {}).get('TWD', DEFAULT_RATE)
            return rate
    except:
        pass
    
    return DEFAULT_RATE

def generate_post_content(product, config):
    """生成貼文內容"""
    title = product.get('title', '')
    description = product.get('body_html', '')
    
    # 移除 HTML 標籤
    description = re.sub('<[^<]+?>', '', description)
    
    # 移除尺寸規格表
    description = re.sub(r'📏\s*尺寸規格.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸規格\s*尺寸\s+衣長.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸\s+衣長\s+身寬.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸\s+腰圍\s+臀圍.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸\s+總長\s+.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸\s+高度\s+.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 移除詰合內容表格
    description = re.sub(r'📦\s*詰合內容.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'詰合內容\s*商品\s+過敏原.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'商品\s+過敏原\s+賞味期限.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'內容量.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 清理多餘的空白和換行
    description = re.sub(r'\n{3,}', '\n\n', description)
    description = description.strip()
    
    # 修改注意事項文字
    description = description.replace('※不接受退換貨', '※不接受因個人原因退換貨')
    description = description.replace('※開箱請全程錄影', '※開箱請全程錄影保護消費者權益')
    
    # 截斷過長的描述
    description = description[:300] + '...' if len(description) > 300 else description
    
    # 價格處理（Shopify 存的是日圓）
    variants = product.get('variants', [])
    price_jpy_str = variants[0].get('price', '0') if variants else '0'
    
    try:
        price_jpy = float(price_jpy_str)
        if price_jpy > 0:
            rate = get_jpy_to_twd_rate()
            price_twd = int(price_jpy * rate)
            price_jpy_formatted = f"{int(price_jpy):,}"
            price_twd_formatted = f"{price_twd:,}"
            price_line = f"💰 ¥{price_jpy_formatted}（約NT${price_twd_formatted}）\n含日本至台灣運費"
        else:
            price_line = "💰 價格請詢價"
    except:
        price_line = "💰 價格請詢價"
    
    # 商品連結
    handle = product.get('handle', '')
    product_url = f"{config.SHOPIFY_STORE_URL}/products/{handle}"
    
    # 取得所有圖片
    images = product.get('images', [])
    image_urls = [img.get('src') for img in images if img.get('src')]
    image_url = image_urls[0] if image_urls else None
    
    # 取得商品標籤和類型
    tags = product.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    product_type = product.get('product_type', '')
    
    # 動態產生品牌 Hashtag
    brand_tag = ''
    handle_lower = handle.lower()
    title_lower = title.lower()
    
    if 'bape' in handle_lower or 'bape' in title_lower:
        brand_tag = '#BAPE'
    elif 'workman' in handle_lower or 'workman' in title_lower:
        brand_tag = '#WORKMAN'
    elif 'human-made' in handle_lower or 'human made' in title_lower:
        brand_tag = '#HUMANMADE'
    elif 'x-girl' in handle_lower or 'x-girl' in title_lower:
        brand_tag = '#XGIRL'
    elif 'yokumoku' in handle_lower:
        brand_tag = '#YOKUMOKU'
    elif '小倉山莊' in handle or '小倉山莊' in title:
        brand_tag = '#小倉山莊'
    elif '砂糖奶油樹' in handle or '砂糖奶油樹' in title:
        brand_tag = '#砂糖奶油樹'
    elif '坂角' in handle or '坂角' in title:
        brand_tag = '#坂角總本舖'
    elif '風月堂' in handle or '風月堂' in title:
        brand_tag = '#神戶風月堂'
    elif '虎屋' in handle or '虎屋' in title:
        brand_tag = '#虎屋羊羹'
    elif '資生堂' in handle or '資生堂' in title:
        brand_tag = '#資生堂PARLOUR'
    elif 'francais' in handle_lower or 'français' in title_lower:
        brand_tag = '#FRANCAIS'
    elif 'cocoris' in handle_lower:
        brand_tag = '#COCORIS'
    elif 'harada' in handle_lower or 'ハラダ' in title:
        brand_tag = '#GateauFestaHarada'
    elif 'maple' in handle_lower or '楓糖' in title:
        brand_tag = '#楓糖男孩'
    elif '菊廼舍' in handle or '菊廼舍' in title:
        brand_tag = '#銀座菊廼舍'
    elif 'adidas' in handle_lower or 'adidas' in title_lower:
        brand_tag = '#adidas'
    
    # 動態產生類型 Hashtag
    type_tag = ''
    all_text = f"{handle_lower} {product_type.lower()} {' '.join(tags).lower()}"
    
    if '兒童' in handle or 'kids' in all_text or 'キッズ' in title:
        type_tag = '#KIDS'
    elif '男裝' in handle or 'mens' in all_text or 'men' in all_text:
        type_tag = '#MENS'
    elif '女裝' in handle or 'womens' in all_text or 'women' in all_text or 'ladies' in all_text:
        type_tag = '#WOMENS'
    elif '作業服' in handle:
        type_tag = '#作業服'
    
    # 組合 Hashtag
    base_tags = '#日本服飾 #日本代購 #GOYOUTATI #日本潮流'
    hashtags = base_tags
    if brand_tag:
        hashtags += f' {brand_tag}'
    if type_tag:
        hashtags += f' {type_tag}'
    
    # 生成貼文文字 - FB/IG 版本（有 hashtag）
    post_text_with_tags = f"""Goyoutati - 日本伴手禮、服飾專賣店 ｜每日最新商品、補貨資訊
歡迎follow我，和日本同步最新產品資訊

✨ {title}

{description}

{price_line}
🛒 立即購買：{product_url}

{hashtags}
"""
    
    # 生成貼文文字 - Threads 版本（無 hashtag）
    post_text_no_tags = f"""Goyoutati - 日本伴手禮、服飾專賣店 ｜每日最新商品、補貨資訊
歡迎follow我，和日本同步最新產品資訊

✨ {title}

{description}

{price_line}
🛒 立即購買：{product_url}
"""
    
    return {
        'text': post_text_with_tags,
        'text_no_tags': post_text_no_tags,
        'image_url': image_url,
        'image_urls': image_urls,
        'product_url': product_url,
        'title': title
    }

def post_to_platforms(content, platforms, config):
    """發布到各平台（貼文 + 限動）"""
    results = {}
    
    # 預先處理限動圖片（加模糊背景）
    story_image_url = None
    if content.get('image_url'):
        print("[限動] 正在處理圖片（加模糊背景）...")
        story_image_url = create_story_image_url(content['image_url'])
    
    # Facebook 貼文
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
        
        # Facebook 限動（使用處理過的圖片）
        try:
            if story_image_url:
                story_result = fb.post_story(story_image_url)
                results['facebook_story'] = {'success': True, 'post_id': story_result.get('post_id')}
        except Exception as e:
            results['facebook_story'] = {'success': False, 'error': str(e)}
    
    # Instagram 貼文
    if 'ig' in platforms and config.IG_ACCOUNT_ID and config.IG_ACCESS_TOKEN:
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
        
        # Instagram 限動（使用處理過的圖片）
        try:
            if story_image_url:
                story_result = ig.post_story(story_image_url)
                results['instagram_story'] = {'success': True, 'post_id': story_result.get('id')}
        except Exception as e:
            results['instagram_story'] = {'success': False, 'error': str(e)}
    
    # Threads 貼文（Threads 沒有限動功能）
    if 'threads' in platforms and config.THREADS_USER_ID and config.THREADS_ACCESS_TOKEN:
        try:
            threads = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)
            # Threads 只發單圖（輪播圖容易出錯）
            result = threads.post(content.get('text_no_tags', content['text']), content['image_url'])
            results['threads'] = {'success': True, 'post_id': result.get('id')}
        except Exception as e:
            results['threads'] = {'success': False, 'error': str(e)}
    
    return results

@app.route('/')
def index():
    """首頁 - 檢查登入狀態"""
    api_secret = os.getenv('API_SECRET')
    
    # 檢查 Cookie 是否有正確的 secret
    cookie_secret = request.cookies.get('auth_secret')
    
    if api_secret and cookie_secret == api_secret:
        # 已登入，顯示管理頁面
        return render_template_string(ADMIN_HTML)
    
    # 未登入，顯示登入頁面
    return render_template_string(LOGIN_HTML)

@app.route('/login', methods=['POST'])
def login():
    """登入處理"""
    api_secret = os.getenv('API_SECRET')
    provided_secret = request.form.get('secret', '')
    
    if api_secret and provided_secret == api_secret:
        # 登入成功，設定 Cookie
        response = make_response(redirect('/'))
        response.set_cookie('auth_secret', provided_secret, max_age=60*60*24*30, httponly=True)  # 30 天
        return response
    
    # 登入失敗
    return redirect('/?error=1')

@app.route('/logout')
def logout():
    """登出"""
    response = make_response(redirect('/'))
    response.delete_cookie('auth_secret')
    return response

def check_auth():
    """檢查是否已登入（用於內部 API）"""
    api_secret = os.getenv('API_SECRET')
    cookie_secret = request.cookies.get('auth_secret')
    return api_secret and cookie_secret == api_secret

@app.route('/api/stats')
def api_stats():
    """內部 API - 發文統計（需登入）"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)
    
    stats = selector.get_stats()
    
    return jsonify({
        'success': True,
        'stats': {
            'souvenir': {
                'name': '伴手禮',
                'total': stats['souvenir']['total'],
                'round': stats['souvenir']['round'],
                'posted_this_round': stats['souvenir']['posted_this_round'],
                'remaining': stats['souvenir']['remaining']
            },
            'fashion': {
                'name': '服飾',
                'total': stats['fashion']['total'],
                'round': stats['fashion']['round'],
                'posted_this_round': stats['fashion']['posted_this_round'],
                'remaining': stats['fashion']['remaining']
            }
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/post')
def api_post():
    """內部 API - 發文（需登入）"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)
    
    count = min(int(request.args.get('count', 1)), 10)
    category = 'fashion'  # 固定只發服飾
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]
    
    posted = []
    
    for i in range(count):
        product, cat = selector.get_next_product(category)
        
        if not product:
            break
        
        content = generate_post_content(product, config)
        results = post_to_platforms(content, platforms, config)
        
        all_success = all(r.get('success') for r in results.values()) if results else False
        if all_success:
            selector.mark_as_posted(product, cat)
        
        posted.append({
            'title': product.get('title'),
            'category': '服飾',
            'platforms': results,
            'marked': all_success
        })
    
    return jsonify({
        'success': len(posted) > 0,
        'count': len(posted),
        'posts': posted,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/get-secret-url')
def api_get_secret_url():
    """取得帶 secret 的 API URL（給 cron-job 用）"""
    if not check_auth():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    api_secret = os.getenv('API_SECRET', '')
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        'url': f"{base_url}/post/smart?secret={api_secret}"
    })

@app.route('/health')
def health():
    """健康檢查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stats')
def stats():
    """發文統計"""
    api_secret = os.getenv('API_SECRET')
    if api_secret:
        provided_secret = request.args.get('secret')
        if provided_secret != api_secret:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)
    
    stats = selector.get_stats()
    
    return jsonify({
        'success': True,
        'stats': {
            'fashion': {
                'name': '服飾',
                'total': stats['fashion']['total'],
                'round': stats['fashion']['round'],
                'posted_this_round': stats['fashion']['posted_this_round'],
                'remaining': stats['fashion']['remaining']
            }
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/post/smart')
def post_smart():
    """
    智慧發文（只發服飾）
    背景執行，立刻回應
    
    Query params:
    - count: 發幾篇（預設 1，最多 10）
    - platforms: 平台，逗號分隔（選填）
    - secret: API 密鑰（建議設定）
    """
    import threading
    
    # 驗證 API 密鑰
    api_secret = os.getenv('API_SECRET')
    if api_secret:
        provided_secret = request.args.get('secret')
        if provided_secret != api_secret:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    count = min(int(request.args.get('count', 1)), 10)
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]
    
    # 背景執行發文
    def do_post():
        config = get_config()
        shopify = get_shopify_client(config)
        selector = SmartSelector(shopify, config)
        
        for i in range(count):
            product, cat = selector.get_next_product('fashion')
            
            if not product:
                print(f"[背景發文] 沒有找到商品")
                break
            
            print(f"[背景發文] 開始發文: {product.get('title')}")
            
            content = generate_post_content(product, config)
            results = post_to_platforms(content, platforms, config)
            
            # 印出結果
            for platform, result in results.items():
                if result.get('success'):
                    print(f"[背景發文] ✅ {platform} 成功")
                else:
                    print(f"[背景發文] ❌ {platform} 失敗: {result.get('error')}")
    
    # 啟動背景執行緒
    thread = threading.Thread(target=do_post)
    thread.start()
    
    # 立刻回應
    return jsonify({
        'success': True,
        'message': '發文請求已收到，背景執行中',
        'count': count,
        'category': '服飾',
        'platforms': platforms,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/post/random')
def post_random():
    """
    隨機發布貼文（GET 請求，方便 cron-job.org 呼叫）
    
    Query params:
    - collection: 系列 handle（選填）
    - platforms: 平台，逗號分隔（選填）
    - secret: API 密鑰（建議設定）
    """
    api_secret = os.getenv('API_SECRET')
    if api_secret:
        provided_secret = request.args.get('secret')
        if provided_secret != api_secret:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    config = get_config()
    shopify = get_shopify_client(config)
    
    collection = request.args.get('collection')
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]
    
    # 取得商品
    if collection:
        products = shopify.get_products_from_collection(collection)
    else:
        products = shopify.get_all_products()
    
    if not products:
        return jsonify({
            'success': False,
            'error': '找不到商品'
        }), 404
    
    # 過濾掉成人商品
    safe_products = [p for p in products if not is_adult_product(p)]
    if not safe_products:
        return jsonify({
            'success': False,
            'error': '過濾成人商品後沒有可發布的商品'
        }), 404

    product = random.choice(safe_products)
    
    # 生成貼文
    content = generate_post_content(product, config)
    
    # 發布
    results = post_to_platforms(content, platforms, config)
    
    success_count = sum(1 for r in results.values() if r.get('success'))
    
    return jsonify({
        'success': success_count > 0,
        'product': {
            'title': product.get('title'),
            'handle': product.get('handle')
        },
        'platforms': results,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
