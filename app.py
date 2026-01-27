#!/usr/bin/env python3
"""
Flask API 版本 - 適合部署到 Zeabur
可透過 HTTP 請求觸發發文

部署到 Zeabur 後，使用 cron-job.org 定時呼叫 API
"""

from flask import Flask, request, jsonify
import random
import os
import requests
from datetime import datetime
from shopify_client import ShopifyClient
from social_clients import FacebookClient, InstagramClient, ThreadsClient
from smart_selector import SmartSelector
from config import Config
import re

app = Flask(__name__)

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
    base_tags = '#日本伴手禮 #日本代購 #GOYOUTATI #伴手禮推薦'
    hashtags = base_tags
    if brand_tag:
        hashtags += f' {brand_tag}'
    if type_tag:
        hashtags += f' {type_tag}'
    
    # 生成貼文文字 - FB/IG 版本（有 hashtag）
    post_text_with_tags = f"""✨ {title}

{description}

{price_line}
🛒 立即購買：{product_url}

{hashtags}
"""
    
    # 生成貼文文字 - Threads 版本（無 hashtag）
    post_text_no_tags = f"""✨ {title}

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
    """發布到各平台"""
    results = {}
    
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
    
    if 'threads' in platforms and config.THREADS_USER_ID and config.THREADS_ACCESS_TOKEN:
        try:
            threads = ThreadsClient(config.THREADS_USER_ID, config.THREADS_ACCESS_TOKEN)
            image_urls = content.get('image_urls', [])
            if len(image_urls) > 1:
                result = threads.post_carousel(content.get('text_no_tags', content['text']), image_urls[:20])
            else:
                result = threads.post(content.get('text_no_tags', content['text']), content['image_url'])
            results['threads'] = {'success': True, 'post_id': result.get('id')}
        except Exception as e:
            results['threads'] = {'success': False, 'error': str(e)}
    
    return results

@app.route('/')
def index():
    """首頁"""
    return jsonify({
        'service': '御用達 GOYOUTATI - 社群自動發文 API',
        'endpoints': {
            '/post/smart': 'GET - 智慧發文（1:1 伴手禮/服飾交替）',
            '/post/random': 'GET - 隨機發布',
            '/stats': 'GET - 發文統計',
            '/health': 'GET - 健康檢查'
        }
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

@app.route('/post/smart')
def post_smart():
    """
    智慧發文（1:1 伴手禮/服飾交替，新上架優先）
    
    Query params:
    - count: 發幾篇（預設 1，最多 10）
    - category: 指定類別（souvenir/fashion，選填）
    - platforms: 平台，逗號分隔（選填）
    - secret: API 密鑰（建議設定）
    """
    # 驗證 API 密鑰
    api_secret = os.getenv('API_SECRET')
    if api_secret:
        provided_secret = request.args.get('secret')
        if provided_secret != api_secret:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    config = get_config()
    shopify = get_shopify_client(config)
    selector = SmartSelector(shopify, config)
    
    count = min(int(request.args.get('count', 1)), 10)
    category = request.args.get('category')
    platforms_str = request.args.get('platforms', 'fb,ig,threads')
    platforms = [p.strip() for p in platforms_str.split(',')]
    
    posted = []
    
    for i in range(count):
        # 取得下一個商品
        product, cat = selector.get_next_product(category)
        
        if not product:
            break
        
        # 生成貼文
        content = generate_post_content(product, config)
        
        # 發布
        results = post_to_platforms(content, platforms, config)
        
        # 標記已發文
        all_success = all(r.get('success') for r in results.values())
        if all_success:
            selector.mark_as_posted(product, cat)
        
        posted.append({
            'title': product.get('title'),
            'category': '伴手禮' if cat == 'souvenir' else '服飾',
            'platforms': results,
            'marked': all_success
        })
    
    return jsonify({
        'success': len(posted) > 0,
        'count': len(posted),
        'posts': posted,
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
    
    product = random.choice(products)
    
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
