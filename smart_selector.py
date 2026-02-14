"""
智慧選擇器 - 從最新上架的前10個商品中隨機選擇（只發服飾類）
"""

import random


class SmartSelector:
    """最新商品選擇器"""
    
    def __init__(self, shopify_client, config):
        self.shopify = shopify_client
        self.config = config
        
        # 從設定取得系列列表
        self.souvenir_collections = getattr(config, 'SOUVENIR_COLLECTIONS', [])
        self.fashion_collections = getattr(config, 'FASHION_COLLECTIONS', [])
        
        # 追蹤上次發的類別
        self.last_category = None
    
    def get_next_product(self, category=None):
        """
        從最新上架的前10個服飾商品中隨機選擇
        
        Args:
            category: 忽略此參數，固定只發服飾
        
        Returns:
            (product, category) 或 (None, None)
        """
        # 固定只發服飾類
        selected_category = 'fashion'
        collections = self.fashion_collections
        print(f"   📊 從服飾最新 10 個商品中選擇")
        
        # get_products_from_multiple_collections 已按上架時間排序（新的優先）
        products = self.shopify.get_products_from_multiple_collections(collections)
        
        if not products:
            print(f"   ⚠️  沒有找到服飾商品")
            return None, None
        
        # 只取最新的前 10 個商品
        latest_products = products[:10]
        
        # 從最新 10 個中隨機選擇
        product = random.choice(latest_products)
        print(f"   ✅ 選擇商品: {product.get('title', 'Unknown')}（從最新 {len(latest_products)} 個中選出）")
        
        # 更新上次類別
        self.last_category = selected_category
        
        return product, selected_category
    
    def mark_as_posted(self, product, category):
        """標記為已發文（目前不需要追蹤）"""
        pass
    
    def get_stats(self):
        """取得統計資訊"""
        fashion_products = self.shopify.get_products_from_multiple_collections(self.fashion_collections)
        
        return {
            'souvenir': {
                'total': 0,
                'latest_10': 0,
                'round': 0,
                'posted_this_round': 0,
                'remaining': 0
            },
            'fashion': {
                'total': len(fashion_products),
                'latest_10': min(len(fashion_products), 10),
                'round': 1,
                'posted_this_round': 0,
                'remaining': min(len(fashion_products), 10)
            }
        }
