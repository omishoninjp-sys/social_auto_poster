"""
智慧商品選擇器
負責按照 1:1 比例選擇伴手禮和服飾商品
支援輪次管理，避免重複發文
"""

from shopify_client import ShopifyClient


class SmartSelector:
    """智慧商品選擇器"""
    
    def __init__(self, shopify_client, config):
        """
        初始化選擇器
        
        Args:
            shopify_client: ShopifyClient 實例
            config: 設定物件
        """
        self.shopify = shopify_client
        self.config = config
        
        # 從設定取得系列列表
        self.souvenir_collections = config.SOUVENIR_COLLECTIONS
        self.fashion_collections = config.FASHION_COLLECTIONS
        
        # 標籤前綴
        self.souvenir_tag_prefix = config.SOUVENIR_POSTED_TAG
        self.fashion_tag_prefix = config.FASHION_POSTED_TAG
        
        # 追蹤目前類型（用於 1:1 交替）
        self._last_type = None
    
    def get_next_product(self, category=None):
        """
        取得下一個要發文的商品
        
        Args:
            category: 指定類別 ('souvenir' 或 'fashion')，None 為自動交替
        
        Returns:
            (商品, 類別) 或 (None, None)
        """
        if category:
            # 指定類別
            if category == 'souvenir':
                product = self._get_next_souvenir()
                return (product, 'souvenir') if product else (None, None)
            elif category == 'fashion':
                product = self._get_next_fashion()
                return (product, 'fashion') if product else (None, None)
        
        # 自動交替 1:1
        if self._last_type == 'souvenir':
            # 上次是伴手禮，這次發服飾
            product = self._get_next_fashion()
            if product:
                self._last_type = 'fashion'
                return (product, 'fashion')
            # 服飾沒了，發伴手禮
            product = self._get_next_souvenir()
            if product:
                self._last_type = 'souvenir'
                return (product, 'souvenir')
        else:
            # 上次是服飾或是第一次，這次發伴手禮
            product = self._get_next_souvenir()
            if product:
                self._last_type = 'souvenir'
                return (product, 'souvenir')
            # 伴手禮沒了，發服飾
            product = self._get_next_fashion()
            if product:
                self._last_type = 'fashion'
                return (product, 'fashion')
        
        return (None, None)
    
    def _get_next_souvenir(self):
        """取得下一個伴手禮商品"""
        return self._get_next_product_by_type(
            collections=self.souvenir_collections,
            tag_prefix=self.souvenir_tag_prefix,
            category_name='伴手禮'
        )
    
    def _get_next_fashion(self):
        """取得下一個服飾商品"""
        return self._get_next_product_by_type(
            collections=self.fashion_collections,
            tag_prefix=self.fashion_tag_prefix,
            category_name='服飾'
        )
    
    def _get_next_product_by_type(self, collections, tag_prefix, category_name):
        """
        根據類型取得下一個商品
        
        Args:
            collections: 系列列表
            tag_prefix: 標籤前綴
            category_name: 類別名稱（用於顯示）
        
        Returns:
            商品或 None
        """
        # 取得該類別的所有商品
        products = self.shopify.get_products_from_multiple_collections(collections)
        
        if not products:
            print(f"   ⚠️  {category_name} 類別沒有商品")
            return None
        
        # 找出目前的輪次
        current_round = self._get_current_round(products, tag_prefix)
        current_tag = f"{tag_prefix}{current_round}"
        
        print(f"   📊 {category_name} 目前輪次: {current_round}")
        
        # 找出本輪還沒發過的商品（按上架時間排序，新的優先）
        for product in products:
            tags = self._get_product_tags(product)
            if current_tag not in tags:
                print(f"   ✅ 找到未發過的{category_name}商品")
                return product
        
        # 本輪全部發完了，進入下一輪
        print(f"   🔄 {category_name} 本輪發完，進入第 {current_round + 1} 輪")
        
        # 重置：移除所有輪次標籤，開始新一輪
        # （這裡不實際移除，而是增加新輪次）
        next_tag = f"{tag_prefix}{current_round + 1}"
        
        # 返回第一個商品（最新上架）
        return products[0] if products else None
    
    def _get_current_round(self, products, tag_prefix):
        """
        取得目前的輪次
        
        Args:
            products: 商品列表
            tag_prefix: 標籤前綴
        
        Returns:
            輪次數字
        """
        max_round = 1
        
        for product in products:
            tags = self._get_product_tags(product)
            for tag in tags:
                if tag.startswith(tag_prefix):
                    try:
                        round_num = int(tag.replace(tag_prefix, ''))
                        max_round = max(max_round, round_num)
                    except ValueError:
                        pass
        
        return max_round
    
    def _get_product_tags(self, product):
        """
        取得商品的標籤列表
        
        Args:
            product: 商品資料
        
        Returns:
            標籤列表
        """
        tags = product.get('tags', '')
        if isinstance(tags, list):
            return tags
        return [t.strip() for t in tags.split(',') if t.strip()]
    
    def mark_as_posted(self, product, category):
        """
        標記商品已發文
        
        Args:
            product: 商品資料
            category: 類別 ('souvenir' 或 'fashion')
        
        Returns:
            是否成功
        """
        product_id = product.get('id')
        if not product_id:
            return False
        
        # 決定標籤前綴
        if category == 'souvenir':
            tag_prefix = self.souvenir_tag_prefix
        else:
            tag_prefix = self.fashion_tag_prefix
        
        # 取得目前輪次
        if category == 'souvenir':
            products = self.shopify.get_products_from_multiple_collections(self.souvenir_collections)
        else:
            products = self.shopify.get_products_from_multiple_collections(self.fashion_collections)
        
        current_round = self._get_current_round(products, tag_prefix)
        
        # 檢查是否所有商品都已有本輪標籤（需要進入下一輪）
        current_tag = f"{tag_prefix}{current_round}"
        all_posted = True
        for p in products:
            if p['id'] != product_id:  # 排除當前商品
                tags = self._get_product_tags(p)
                if current_tag not in tags:
                    all_posted = False
                    break
        
        # 如果其他商品都發過了，這個商品要標記為下一輪
        if all_posted:
            new_tag = f"{tag_prefix}{current_round + 1}"
        else:
            new_tag = current_tag
        
        print(f"   🏷️  新增標籤: {new_tag}")
        return self.shopify.add_tag_to_product(product_id, new_tag)
    
    def get_stats(self):
        """
        取得發文統計
        
        Returns:
            統計資訊字典
        """
        # 伴手禮統計
        souvenir_products = self.shopify.get_products_from_multiple_collections(self.souvenir_collections)
        souvenir_round = self._get_current_round(souvenir_products, self.souvenir_tag_prefix)
        souvenir_current_tag = f"{self.souvenir_tag_prefix}{souvenir_round}"
        souvenir_posted = sum(1 for p in souvenir_products if souvenir_current_tag in self._get_product_tags(p))
        
        # 服飾統計
        fashion_products = self.shopify.get_products_from_multiple_collections(self.fashion_collections)
        fashion_round = self._get_current_round(fashion_products, self.fashion_tag_prefix)
        fashion_current_tag = f"{self.fashion_tag_prefix}{fashion_round}"
        fashion_posted = sum(1 for p in fashion_products if fashion_current_tag in self._get_product_tags(p))
        
        return {
            'souvenir': {
                'total': len(souvenir_products),
                'round': souvenir_round,
                'posted_this_round': souvenir_posted,
                'remaining': len(souvenir_products) - souvenir_posted
            },
            'fashion': {
                'total': len(fashion_products),
                'round': fashion_round,
                'posted_this_round': fashion_posted,
                'remaining': len(fashion_products) - fashion_posted
            }
        }
    
    def reset_round(self, category):
        """
        重置特定類別的輪次（移除所有輪次標籤）
        
        Args:
            category: 'souvenir' 或 'fashion'
        
        Returns:
            是否成功
        """
        if category == 'souvenir':
            products = self.shopify.get_products_from_multiple_collections(self.souvenir_collections)
            tag_prefix = self.souvenir_tag_prefix
        else:
            products = self.shopify.get_products_from_multiple_collections(self.fashion_collections)
            tag_prefix = self.fashion_tag_prefix
        
        success = True
        for product in products:
            result = self.shopify.remove_tags_with_prefix(product['id'], tag_prefix)
            if not result:
                success = False
        
        return success


# 測試函數
if __name__ == '__main__':
    from config import Config
    
    config = Config()
    shopify = ShopifyClient(config.SHOPIFY_STORE_URL, config.SHOPIFY_ACCESS_TOKEN)
    selector = SmartSelector(shopify, config)
    
    print("📊 發文統計：")
    stats = selector.get_stats()
    print(f"\n伴手禮：")
    print(f"   總數: {stats['souvenir']['total']}")
    print(f"   目前輪次: {stats['souvenir']['round']}")
    print(f"   本輪已發: {stats['souvenir']['posted_this_round']}")
    print(f"   本輪剩餘: {stats['souvenir']['remaining']}")
    
    print(f"\n服飾：")
    print(f"   總數: {stats['fashion']['total']}")
    print(f"   目前輪次: {stats['fashion']['round']}")
    print(f"   本輪已發: {stats['fashion']['posted_this_round']}")
    print(f"   本輪剩餘: {stats['fashion']['remaining']}")
