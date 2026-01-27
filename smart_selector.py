"""
智慧選擇器 - 隨機選擇商品發文
方案4：完全隨機，不追蹤已發文商品
"""

import random


class SmartSelector:
    """隨機商品選擇器"""
    
    def __init__(self, shopify_client, config):
        self.shopify = shopify_client
        self.config = config
        
        # 從設定取得系列列表
        self.souvenir_collections = getattr(config, 'SOUVENIR_COLLECTIONS', [])
        self.fashion_collections = getattr(config, 'FASHION_COLLECTIONS', [])
        
        # 追蹤上次發的類別（用於 1:1 交替）
        self.last_category = None
    
    def get_next_product(self, category=None):
        """
        隨機選擇下一個商品
        
        Args:
            category: 指定類別 ('souvenir' 或 'fashion')，None 為自動交替
        
        Returns:
            (product, category) 或 (None, None)
        """
        # 決定類別
        if category:
            selected_category = category
        else:
            # 1:1 交替
            if self.last_category == 'souvenir':
                selected_category = 'fashion'
            elif self.last_category == 'fashion':
                selected_category = 'souvenir'
            else:
                selected_category = random.choice(['souvenir', 'fashion'])
        
        # 取得商品
        if selected_category == 'souvenir':
            collections = self.souvenir_collections
            print(f"   📊 隨機選擇伴手禮商品")
        else:
            collections = self.fashion_collections
            print(f"   📊 隨機選擇服飾商品")
        
        products = self.shopify.get_products_from_multiple_collections(collections)
        
        if not products:
            print(f"   ⚠️  沒有找到 {selected_category} 商品")
            # 嘗試另一個類別
            other_category = 'fashion' if selected_category == 'souvenir' else 'souvenir'
            other_collections = self.fashion_collections if selected_category == 'souvenir' else self.souvenir_collections
            products = self.shopify.get_products_from_multiple_collections(other_collections)
            if products:
                selected_category = other_category
            else:
                return None, None
        
        # 隨機選擇一個商品
        product = random.choice(products)
        print(f"   ✅ 選擇商品: {product.get('title', 'Unknown')}")
        
        # 更新上次類別
        self.last_category = selected_category
        
        return product, selected_category
    
    def mark_as_posted(self, product, category):
        """標記為已發文（方案4不需要，保留空函數）"""
        pass
    
    def get_stats(self):
        """取得統計資訊"""
        souvenir_products = self.shopify.get_products_from_multiple_collections(self.souvenir_collections)
        fashion_products = self.shopify.get_products_from_multiple_collections(self.fashion_collections)
        
        return {
            'souvenir': {
                'total': len(souvenir_products),
                'round': 1,
                'posted_this_round': 0,
                'remaining': len(souvenir_products)
            },
            'fashion': {
                'total': len(fashion_products),
                'round': 1,
                'posted_this_round': 0,
                'remaining': len(fashion_products)
            }
        }
