"""
智慧選擇器 - 從全店最新上架的前20個商品中隨機選擇（不分系列）
自動排除成人相關商品（含 adult 或 18+ 標籤）
"""

import random

# 成人商品標籤（有這些 tag 的商品不會被發到社群）
ADULT_TAGS = {'adult', '18+', '成人'}


def is_adult_product(product):
    """
    檢查商品是否為成人商品
    
    Args:
        product: Shopify 商品資料
    
    Returns:
        True = 成人商品（應排除），False = 一般商品
    """
    tags = product.get('tags', '')
    if isinstance(tags, str):
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]
    elif isinstance(tags, list):
        tag_list = [t.strip().lower() for t in tags if t.strip()]
    else:
        tag_list = []
    
    return bool(ADULT_TAGS & set(tag_list))


class SmartSelector:
    """最新商品選擇器"""
    
    def __init__(self, shopify_client, config):
        self.shopify = shopify_client
        self.config = config
        self.last_category = None
    
    def get_next_product(self, category=None):
        """
        從全店最新上架的前20個商品中隨機選擇（不分系列）
        自動排除成人相關商品
        
        Returns:
            (product, category) 或 (None, None)
        """
        print(f"   📊 從全店最新商品中選擇（不分系列，排除成人商品）")
        
        # 直接抓全店商品（Shopify API 預設按建立時間排序）
        all_products = self.shopify.get_all_products(limit=250)
        
        if not all_products:
            print(f"   ⚠️  沒有找到任何商品")
            return None, None
        
        # 按上架時間排序（新的優先）
        all_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 只取最新的前 20 個
        latest_products = all_products[:20]
        
        # 過濾掉成人商品
        safe_products = [p for p in latest_products if not is_adult_product(p)]
        
        filtered_count = len(latest_products) - len(safe_products)
        if filtered_count > 0:
            print(f"   🔞 已排除 {filtered_count} 個成人商品")
        
        if not safe_products:
            print(f"   ⚠️  過濾後沒有可發布的商品")
            return None, None
        
        # 從安全商品中隨機選擇
        product = random.choice(safe_products)
        print(f"   ✅ 選擇商品: {product.get('title', 'Unknown')}（從 {len(safe_products)} 個安全商品中選出，全店共 {len(all_products)} 個）")
        
        self.last_category = 'fashion'
        return product, 'fashion'
    
    def mark_as_posted(self, product, category):
        """標記為已發文（目前不需要追蹤）"""
        pass
    
    def get_stats(self):
        """取得統計資訊"""
        all_products = self.shopify.get_all_products(limit=250)
        total = len(all_products) if all_products else 0
        
        # 計算安全商品數量
        if all_products:
            all_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            latest = all_products[:20]
            safe_count = len([p for p in latest if not is_adult_product(p)])
        else:
            safe_count = 0
        
        return {
            'souvenir': {
                'total': 0,
                'latest_10': 0,
                'round': 0,
                'posted_this_round': 0,
                'remaining': 0
            },
            'fashion': {
                'total': total,
                'latest_10': safe_count,
                'round': 1,
                'posted_this_round': 0,
                'remaining': safe_count
            }
        }
