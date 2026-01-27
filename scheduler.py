#!/usr/bin/env python3
"""
排程發文器
支援定時自動發文

使用方式：
    python scheduler.py                    # 使用預設排程（每天 10:00, 14:00, 18:00）
    python scheduler.py --times 10:00,18:00  # 自訂發文時間
    python scheduler.py --interval 4       # 每 4 小時發一次
    python scheduler.py --once             # 只執行一次
"""

import argparse
import time
import schedule
import random
from datetime import datetime
from main import load_config, get_random_product, generate_post_content, post_to_platforms
from shopify_client import ShopifyClient
from config import COLLECTION_MAPPING

# 排程設定
class SchedulerConfig:
    # 預設發文時間 (24小時制)
    DEFAULT_POST_TIMES = ['10:00', '14:00', '18:00']
    
    # 可用的系列列表（隨機選擇用）
    COLLECTIONS = list(COLLECTION_MAPPING.values())
    
    # 是否輪流使用不同系列
    ROTATE_COLLECTIONS = True
    
    # 發布的平台
    PLATFORMS = ['fb', 'ig', 'threads']

def scheduled_post(config, shopify, collections=None, platforms=None):
    """
    排程發文任務
    
    Args:
        config: 應用程式設定
        shopify: Shopify 客戶端
        collections: 可選的系列列表（None 表示全部商品）
        platforms: 發布平台列表
    """
    print(f"\n{'=' * 50}")
    print(f"⏰ 排程發文任務開始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 50}")
    
    try:
        # 選擇系列
        if collections:
            collection = random.choice(collections)
            print(f"📦 從系列 [{collection}] 選擇商品...")
            product = get_random_product(shopify, collection)
        else:
            print("🎲 從所有商品隨機選擇...")
            product = get_random_product(shopify)
        
        if not product:
            print("❌ 無法取得商品，跳過此次發文")
            return
        
        print(f"✅ 選中商品: {product.get('title')}")
        
        # 生成貼文內容
        content = generate_post_content(product, config)
        
        print("\n📝 貼文內容：")
        print("-" * 40)
        print(content['text'][:200] + "..." if len(content['text']) > 200 else content['text'])
        print("-" * 40)
        
        # 發布
        platforms = platforms or SchedulerConfig.PLATFORMS
        print(f"\n🚀 發布到: {', '.join(platforms)}")
        
        results = post_to_platforms(content, platforms, config)
        
        # 記錄結果
        success_count = sum(1 for r in results.values() if r.get('success'))
        print(f"\n📊 發布結果: {success_count}/{len(results)} 成功")
        
        for platform, result in results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {platform}")
        
    except Exception as e:
        print(f"❌ 發文失敗: {e}")
    
    print(f"\n{'=' * 50}\n")

def run_scheduler(post_times=None, interval_hours=None, collections=None, platforms=None, run_once=False):
    """
    運行排程器
    
    Args:
        post_times: 發文時間列表 (例如 ['10:00', '18:00'])
        interval_hours: 發文間隔（小時）
        collections: 系列列表
        platforms: 平台列表
        run_once: 是否只執行一次
    """
    print("🚀 御用達 - 社群自動發文排程器")
    print("=" * 50)
    
    # 載入設定
    config = load_config()
    if not config:
        print("❌ 設定載入失敗")
        return
    
    # 初始化 Shopify 客戶端
    shopify = ShopifyClient(
        store_url=config.SHOPIFY_STORE_URL,
        access_token=config.SHOPIFY_ACCESS_TOKEN
    )
    
    if run_once:
        # 立即執行一次
        scheduled_post(config, shopify, collections, platforms)
        return
    
    # 設定排程
    if interval_hours:
        print(f"📅 排程模式: 每 {interval_hours} 小時")
        schedule.every(interval_hours).hours.do(
            scheduled_post, config, shopify, collections, platforms
        )
    else:
        post_times = post_times or SchedulerConfig.DEFAULT_POST_TIMES
        print(f"📅 排程時間: {', '.join(post_times)}")
        
        for t in post_times:
            schedule.every().day.at(t).do(
                scheduled_post, config, shopify, collections, platforms
            )
    
    if collections:
        print(f"📦 使用系列: {', '.join(collections)}")
    else:
        print("📦 使用系列: 全部商品")
    
    platforms = platforms or SchedulerConfig.PLATFORMS
    print(f"📱 發布平台: {', '.join(platforms)}")
    
    print("\n⏳ 排程器已啟動，等待執行...")
    print("   (按 Ctrl+C 停止)\n")
    
    # 持續運行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分鐘檢查一次
    except KeyboardInterrupt:
        print("\n👋 排程器已停止")

def main():
    parser = argparse.ArgumentParser(description='御用達社群自動發文排程器')
    parser.add_argument('--times', '-t', type=str, 
                        help='發文時間 (逗號分隔，例如 10:00,14:00,18:00)')
    parser.add_argument('--interval', '-i', type=int, 
                        help='發文間隔（小時）')
    parser.add_argument('--collections', '-c', type=str, 
                        help='使用的系列 (逗號分隔)')
    parser.add_argument('--platforms', '-p', type=str, default='fb,ig,threads',
                        help='發布平台 (逗號分隔)')
    parser.add_argument('--once', action='store_true', 
                        help='只執行一次')
    
    args = parser.parse_args()
    
    # 解析參數
    post_times = args.times.split(',') if args.times else None
    collections = args.collections.split(',') if args.collections else None
    platforms = [p.strip().lower() for p in args.platforms.split(',')]
    
    run_scheduler(
        post_times=post_times,
        interval_hours=args.interval,
        collections=collections,
        platforms=platforms,
        run_once=args.once
    )

if __name__ == '__main__':
    main()
