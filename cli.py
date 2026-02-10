#!/usr/bin/env python3
"""
御用達 GOYOUTATI - 社群自動發文系統
自動從 Shopify 抓取商品，發布到 Facebook、Instagram、Threads

使用方式：
    python main.py --random              # 隨機選擇商品發文
    python main.py --collection 小倉山莊  # 指定系列發文
    python main.py --collection yokumoku --platforms fb,ig  # 只發 FB 和 IG
    python main.py --list-collections    # 列出所有系列
"""

import argparse
import random
import os
from datetime import datetime
from shopify_client import ShopifyClient
from social_clients import FacebookClient, InstagramClient, ThreadsClient
from config import Config

def load_config():
    """載入設定"""
    config = Config()
    if not config.validate():
        print("⚠️  設定不完整，請編輯 config.py 或設定環境變數")
        return None
    return config

def get_random_product(shopify, collection_handle=None):
    """隨機取得一個商品"""
    if collection_handle:
        products = shopify.get_products_from_collection(collection_handle)
    else:
        products = shopify.get_all_products()
    
    if not products:
        print("❌ 找不到任何商品")
        return None
    
    return random.choice(products)

def get_jpy_to_twd_rate():
    """
    取得日圓對台幣匯率
    使用免費 API，失敗時用預設值
    """
    import requests
    
    # 預設匯率（備用）
    DEFAULT_RATE = 0.22
    
    try:
        # 使用免費的 exchangerate-api
        url = "https://api.exchangerate-api.com/v4/latest/JPY"
        response = requests.get(url, timeout=5)
        if response.ok:
            data = response.json()
            rate = data.get('rates', {}).get('TWD', DEFAULT_RATE)
            return rate
    except:
        pass
    
    # 備用 API
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
    import re
    description = re.sub('<[^<]+?>', '', description)
    
    # 移除尺寸規格表（包含各種格式）
    # 移除 "📏 尺寸規格" 及後面的表格內容
    description = re.sub(r'📏\s*尺寸規格.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    # 移除 "尺寸規格" 標題及表格
    description = re.sub(r'尺寸規格\s*尺寸\s+衣長.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    # 移除單獨的尺寸表格（尺寸 衣長 身寬...開頭）
    description = re.sub(r'尺寸\s+衣長\s+身寬.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    # 移除尺寸表格（尺寸 腰圍 臀圍...開頭）
    description = re.sub(r'尺寸\s+腰圍\s+臀圍.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    # 移除其他常見的尺寸表頭
    description = re.sub(r'尺寸\s+總長\s+.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'尺寸\s+高度\s+.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 移除詰合內容表格
    description = re.sub(r'📦\s*詰合內容.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    description = re.sub(r'詰合內容\s*商品\s+過敏原.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 移除商品規格表格（商品 過敏原 賞味期限...）
    description = re.sub(r'商品\s+過敏原\s+賞味期限.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 移除內容量表格
    description = re.sub(r'內容量.*?(?=【|※|💰|$)', '', description, flags=re.DOTALL)
    
    # 清理多餘的空白和換行
    description = re.sub(r'\n{3,}', '\n\n', description)
    description = description.strip()
    
    # 修改注意事項文字
    description = description.replace('※不接受退換貨', '※不接受因個人原因退換貨')
    description = description.replace('※開箱請全程錄影', '※開箱請全程錄影保護消費者權益')
    
    # 截斷過長的描述
    description = description[:300] + '...' if len(description) > 300 else description
    
    # ============================================
    # 價格處理（Shopify 存的是日圓）
    # ============================================
    variants = product.get('variants', [])
    price_jpy_str = variants[0].get('price', '0') if variants else '0'
    
    try:
        price_jpy = float(price_jpy_str)
        if price_jpy > 0:
            # 取得匯率並計算台幣
            rate = get_jpy_to_twd_rate()
            price_twd = int(price_jpy * rate)
            
            # 格式化價格（加千位分隔符）
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
    image_url = image_urls[0] if image_urls else None  # 第一張圖（給 Threads 用）
    
    # 取得商品標籤和類型
    tags = product.get('tags', [])
    product_type = product.get('product_type', '')
    
    # ============================================
    # 動態產生品牌 Hashtag
    # ============================================
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
    
    # ============================================
    # 動態產生類型 Hashtag (KIDS/MENS/WOMENS)
    # ============================================
    type_tag = ''
    
    # 從 handle、tags、product_type 判斷
    all_text = f"{handle_lower} {product_type.lower()} {' '.join(tags).lower()}"
    
    if '兒童' in handle or 'kids' in all_text or 'キッズ' in title:
        type_tag = '#KIDS'
    elif '男裝' in handle or 'mens' in all_text or 'men' in all_text:
        type_tag = '#MENS'
    elif '女裝' in handle or 'womens' in all_text or 'women' in all_text or 'ladies' in all_text:
        type_tag = '#WOMENS'
    elif '作業服' in handle:
        type_tag = '#作業服'
    
    # ============================================
    # 組合 Hashtag (給 FB/IG 用)
    # ============================================
    base_tags = '#日本伴手禮 #日本代購 #GOYOUTATI #伴手禮推薦'
    hashtags = base_tags
    if brand_tag:
        hashtags += f' {brand_tag}'
    if type_tag:
        hashtags += f' {type_tag}'
    
    # ============================================
    # 生成貼文文字 - FB/IG 版本（有 hashtag）
    # ============================================
    post_text_with_tags = f"""Goyoutati - 日本伴手禮、服飾專賣店 ｜每日最新商品、補貨資訊
歡迎follow我，和日本同步最新產品資訊

✨ {title}

{description}

{price_line}
🛒 立即購買：{product_url}

{hashtags}
"""
    
    # ============================================
    # 生成貼文文字 - Threads 版本（無 hashtag）
    # ============================================
    post_text_no_tags = f"""Goyoutati - 日本伴手禮、服飾專賣店 ｜每日最新商品、補貨資訊
歡迎follow我，和日本同步最新產品資訊

✨ {title}

{description}

{price_line}
🛒 立即購買：{product_url}
"""
    
    return {
        'text': post_text_with_tags,           # FB/IG 用（有 hashtag）
        'text_no_tags': post_text_no_tags,     # Threads 用（無 hashtag）
        'image_url': image_url,                 # 第一張圖
        'image_urls': image_urls,               # 所有圖片
        'product_url': product_url,
        'title': title
    }

def post_to_platforms(content, platforms, config):
    """發布到各平台"""
    results = {}
    
    if 'fb' in platforms:
        print("📘 發布到 Facebook...")
        try:
            fb = FacebookClient(
                page_id=config.FB_PAGE_ID,
                access_token=config.FB_ACCESS_TOKEN
            )
            # FB 用有 hashtag 的版本，多張圖片
            image_urls = content.get('image_urls', [])
            if len(image_urls) > 1:
                # 多張圖片
                result = fb.post_multiple_photos(
                    message=content['text'],
                    image_urls=image_urls
                )
            else:
                # 單張圖片
                result = fb.post(
                    message=content['text'],
                    image_url=content['image_url'],
                    link=content['product_url']
                )
            results['facebook'] = {'success': True, 'post_id': result.get('id')}
            print(f"   ✅ 成功！Post ID: {result.get('id')}")
        except Exception as e:
            results['facebook'] = {'success': False, 'error': str(e)}
            print(f"   ❌ 失敗：{e}")
    
    if 'ig' in platforms:
        print("📸 發布到 Instagram...")
        try:
            ig = InstagramClient(
                account_id=config.IG_ACCOUNT_ID,
                access_token=config.IG_ACCESS_TOKEN
            )
            # IG 用有 hashtag 的版本
            image_urls = content.get('image_urls', [])
            if len(image_urls) > 1:
                # 多張圖片用輪播貼文（最多 10 張）
                result = ig.post_carousel(
                    caption=content['text'],
                    image_urls=image_urls[:10]
                )
            else:
                # 單張圖片
                result = ig.post(
                    caption=content['text'],
                    image_url=content['image_url']
                )
            results['instagram'] = {'success': True, 'post_id': result.get('id')}
            print(f"   ✅ 成功！Post ID: {result.get('id')}")
        except Exception as e:
            results['instagram'] = {'success': False, 'error': str(e)}
            print(f"   ❌ 失敗：{e}")
    
    if 'threads' in platforms:
        print("🧵 發布到 Threads...")
        try:
            threads = ThreadsClient(
                user_id=config.THREADS_USER_ID,
                access_token=config.THREADS_ACCESS_TOKEN
            )
            # Threads 用無 hashtag 的版本，多張圖片
            image_urls = content.get('image_urls', [])
            if len(image_urls) > 1:
                # 多張圖片用輪播貼文
                result = threads.post_carousel(
                    text=content.get('text_no_tags', content['text']),
                    image_urls=image_urls[:20]  # Threads 輪播最多 20 張
                )
            else:
                # 單張圖片
                result = threads.post(
                    text=content.get('text_no_tags', content['text']),
                    image_url=content['image_url']
                )
            results['threads'] = {'success': True, 'post_id': result.get('id')}
            print(f"   ✅ 成功！Post ID: {result.get('id')}")
        except Exception as e:
            results['threads'] = {'success': False, 'error': str(e)}
            print(f"   ❌ 失敗：{e}")
    
    return results

def list_collections(shopify):
    """列出所有系列"""
    collections = shopify.get_collections()
    print("\n📦 可用的商品系列：\n")
    for col in collections:
        print(f"  • {col['title']} (handle: {col['handle']})")
    print()

def main():
    parser = argparse.ArgumentParser(description='御用達社群自動發文系統')
    parser.add_argument('--random', action='store_true', help='隨機選擇商品')
    parser.add_argument('--collection', '-c', type=str, help='指定系列 (使用 handle 或名稱)')
    parser.add_argument('--platforms', '-p', type=str, default='fb,ig,threads',
                        help='發布平台 (逗號分隔: fb,ig,threads)')
    parser.add_argument('--list-collections', action='store_true', help='列出所有系列')
    parser.add_argument('--dry-run', action='store_true', help='測試模式，不實際發文')
    parser.add_argument('--product-id', type=str, help='指定特定商品 ID')
    
    # 智慧選擇相關參數
    parser.add_argument('--smart', action='store_true', 
                        help='智慧選擇模式：1:1 交替伴手禮和服飾，新上架優先')
    parser.add_argument('--category', type=str, choices=['souvenir', 'fashion'],
                        help='指定類別 (souvenir=伴手禮, fashion=服飾)')
    parser.add_argument('--count', type=int, default=1,
                        help='一次發幾篇文章 (預設 1)')
    parser.add_argument('--stats', action='store_true', help='顯示發文統計')
    parser.add_argument('--reset', type=str, choices=['souvenir', 'fashion'],
                        help='重置特定類別的輪次標籤')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🎌 御用達 GOYOUTATI - 社群自動發文系統")
    print("=" * 50)
    print()
    
    # 載入設定
    config = load_config()
    if not config:
        return
    
    # 初始化 Shopify 客戶端
    shopify = ShopifyClient(
        store_url=config.SHOPIFY_STORE_URL,
        access_token=config.SHOPIFY_ACCESS_TOKEN
    )
    
    # 列出系列
    if args.list_collections:
        list_collections(shopify)
        return
    
    # 顯示統計
    if args.stats:
        from smart_selector import SmartSelector
        selector = SmartSelector(shopify, config)
        stats = selector.get_stats()
        
        print("📊 發文統計：")
        print()
        print("🍪 伴手禮：")
        print(f"   總數: {stats['souvenir']['total']} 個商品")
        print(f"   目前輪次: 第 {stats['souvenir']['round']} 輪")
        print(f"   本輪已發: {stats['souvenir']['posted_this_round']} 篇")
        print(f"   本輪剩餘: {stats['souvenir']['remaining']} 篇")
        print()
        print("👔 服飾：")
        print(f"   總數: {stats['fashion']['total']} 個商品")
        print(f"   目前輪次: 第 {stats['fashion']['round']} 輪")
        print(f"   本輪已發: {stats['fashion']['posted_this_round']} 篇")
        print(f"   本輪剩餘: {stats['fashion']['remaining']} 篇")
        return
    
    # 重置輪次
    if args.reset:
        from smart_selector import SmartSelector
        selector = SmartSelector(shopify, config)
        category_name = '伴手禮' if args.reset == 'souvenir' else '服飾'
        print(f"🔄 重置 {category_name} 的輪次標籤...")
        if selector.reset_round(args.reset):
            print(f"   ✅ 成功重置 {category_name} 的標籤")
        else:
            print(f"   ❌ 重置失敗")
        return
    
    # 智慧選擇模式
    if args.smart:
        from smart_selector import SmartSelector
        selector = SmartSelector(shopify, config)
        platforms = [p.strip().lower() for p in args.platforms.split(',')]
        
        print(f"🧠 智慧選擇模式：計劃發 {args.count} 篇文章")
        print()
        
        for i in range(args.count):
            print(f"\n{'='*40}")
            print(f"📝 第 {i+1}/{args.count} 篇")
            print(f"{'='*40}")
            
            # 取得下一個商品
            product, category = selector.get_next_product(args.category)
            
            if not product:
                print("❌ 沒有可發布的商品了")
                break
            
            category_name = '伴手禮' if category == 'souvenir' else '服飾'
            print(f"   類別: {category_name}")
            print(f"   商品: {product.get('title')}")
            
            # 生成貼文內容
            content = generate_post_content(product, config)
            
            # 顯示預覽
            print(f"\n📝 貼文預覽：")
            print("-" * 40)
            preview = content.get('text_no_tags', content['text'])
            if len(preview) > 200:
                print(preview[:200] + "...")
            else:
                print(preview)
            print("-" * 40)
            
            image_urls = content.get('image_urls', [])
            print(f"🖼️  圖片: {len(image_urls)} 張")
            
            if args.dry_run:
                print(f"\n⚠️  測試模式 - 不會實際發文")
                print(f"   預計發布平台: {', '.join(platforms)}")
            else:
                print(f"\n🚀 發布到: {', '.join(platforms)}")
                results = post_to_platforms(content, platforms, config)
                
                # 顯示結果
                all_success = True
                for platform, result in results.items():
                    status = "✅" if result['success'] else "❌"
                    print(f"   {platform}: {status}")
                    if not result['success']:
                        all_success = False
                
                # 標記已發文
                if all_success:
                    if selector.mark_as_posted(product, category):
                        print(f"   🏷️  已標記為已發文")
                    else:
                        print(f"   ⚠️  標記失敗")
        
        print("\n" + "=" * 50)
        print("✨ 全部完成！")
        
        # 顯示最新統計
        stats = selector.get_stats()
        print(f"\n📊 發文後統計：")
        print(f"   伴手禮: 第 {stats['souvenir']['round']} 輪，剩餘 {stats['souvenir']['remaining']} 篇")
        print(f"   服飾: 第 {stats['fashion']['round']} 輪，剩餘 {stats['fashion']['remaining']} 篇")
        return
    
    # 原本的選擇模式
    product = None
    
    if args.product_id:
        print(f"🔍 取得指定商品: {args.product_id}")
        product = shopify.get_product_by_id(args.product_id)
    elif args.collection:
        print(f"🔍 從系列 [{args.collection}] 隨機選擇商品...")
        product = get_random_product(shopify, args.collection)
    elif args.random:
        print("🎲 從所有商品隨機選擇...")
        product = get_random_product(shopify)
    else:
        parser.print_help()
        return
    
    if not product:
        print("❌ 無法取得商品")
        return
    
    print(f"\n📦 選中商品: {product.get('title')}")
    
    # 生成貼文內容
    content = generate_post_content(product, config)
    
    print("\n📝 貼文預覽（FB/IG 版本，有 hashtag）：")
    print("-" * 40)
    print(content['text'])
    print("-" * 40)
    
    print("\n📝 貼文預覽（Threads 版本，無 hashtag）：")
    print("-" * 40)
    print(content.get('text_no_tags', content['text']))
    print("-" * 40)
    
    image_urls = content.get('image_urls', [])
    if image_urls:
        print(f"\n🖼️  圖片數量: {len(image_urls)} 張")
        for i, url in enumerate(image_urls[:5], 1):
            print(f"   {i}. {url[:50]}...")
        if len(image_urls) > 5:
            print(f"   ... 還有 {len(image_urls) - 5} 張")
    
    # 發布
    platforms = [p.strip().lower() for p in args.platforms.split(',')]
    
    if args.dry_run:
        print("\n⚠️  測試模式 - 不會實際發文")
        print(f"   預計發布平台: {', '.join(platforms)}")
        if len(image_urls) > 1:
            print(f"   FB/IG/Threads: 多圖貼文（{len(image_urls)} 張）")
        else:
            print(f"   FB/IG/Threads: 單圖貼文")
    else:
        print(f"\n🚀 開始發布到: {', '.join(platforms)}")
        results = post_to_platforms(content, platforms, config)
        
        print("\n📊 發布結果：")
        for platform, result in results.items():
            status = "✅ 成功" if result['success'] else "❌ 失敗"
            print(f"   {platform}: {status}")
    
    print("\n✨ 完成！")

if __name__ == '__main__':
    main()
