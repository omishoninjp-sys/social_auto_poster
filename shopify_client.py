"""
Shopify API 客戶端
負責從 Shopify 商店抓取商品資料
"""

import requests
from urllib.parse import urljoin, quote
import json

class ShopifyClient:
    """Shopify API 客戶端"""
    
    def __init__(self, store_url, access_token=None):
        """
        初始化客戶端
        
        Args:
            store_url: 商店網址 (例如 https://goyoutati.com)
            access_token: Shopify Admin API access token (選填，用於存取完整資料)
        """
        self.store_url = store_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        
        if access_token:
            # 使用 Admin API
            self.session.headers.update({
                'X-Shopify-Access-Token': access_token,
                'Content-Type': 'application/json'
            })
    
    def _make_request(self, endpoint, params=None):
        """發送 API 請求"""
        if self.access_token:
            # Admin API (需要 access token)
            url = f"{self.store_url}/admin/api/2024-10/{endpoint}"
        else:
            # Storefront API (公開)
            url = f"{self.store_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 請求失敗: {e}")
            return None
    
    def get_all_products(self, limit=250):
        """
        取得所有商品
        
        Args:
            limit: 每頁商品數量 (最大 250)
        
        Returns:
            商品列表
        """
        endpoint = 'products.json'
        params = {'limit': limit}
        
        all_products = []
        
        while True:
            data = self._make_request(endpoint, params)
            if not data or 'products' not in data:
                break
            
            products = data['products']
            all_products.extend(products)
            
            # 檢查是否有下一頁
            if len(products) < limit:
                break
            
            # 用最後一個商品的 ID 作為 since_id
            params['since_id'] = products[-1]['id']
        
        return all_products
    
    def get_collections(self):
        """
        取得所有系列
        
        Returns:
            系列列表
        """
        # 先嘗試 Admin API
        if self.access_token:
            # Custom collections
            custom = self._make_request('custom_collections.json', {'limit': 250})
            # Smart collections
            smart = self._make_request('smart_collections.json', {'limit': 250})
            
            collections = []
            if custom and 'custom_collections' in custom:
                collections.extend(custom['custom_collections'])
            if smart and 'smart_collections' in smart:
                collections.extend(smart['smart_collections'])
            
            return collections
        
        # Storefront 方式（解析網頁）
        return self._get_collections_from_storefront()
    
    def _get_collections_from_storefront(self):
        """從 Storefront 取得系列列表"""
        # 預設的系列列表（根據網站結構）
        collections = [
            {'title': '小倉山莊', 'handle': '小倉山莊'},
            {'title': 'YOKUMOKU', 'handle': 'yokumoku'},
            {'title': '砂糖奶油樹', 'handle': '砂糖奶油樹'},
            {'title': '坂角總本舖', 'handle': '坂角總本舖'},
            {'title': '神戶風月堂', 'handle': '神戶風月堂'},
            {'title': '銀座菊廼舍', 'handle': '銀座菊廼舍'},
            {'title': '資生堂PARLOUR', 'handle': '資生堂parlour'},
            {'title': '虎屋羊羹', 'handle': '虎屋羊羹'},
            {'title': 'FRANÇAIS', 'handle': 'francais'},
            {'title': 'COCORIS', 'handle': 'cocoris'},
            {'title': 'Gateau Festa Harada', 'handle': 'gateau-festa-harada'},
            {'title': 'The maple mania 楓糖男孩', 'handle': 'the-maple-mania-楓糖男孩'},
            {'title': 'Human Made', 'handle': 'human-made-1'},
            {'title': 'X-girl', 'handle': 'x-girl'},
            {'title': 'BAPE', 'handle': 'bape'},
            {'title': 'WORKMAN 作業服', 'handle': 'workman-作業服'},
            {'title': 'WORKMAN 男裝', 'handle': 'workman-男裝'},
            {'title': 'WORKMAN 女裝', 'handle': 'workman-女裝'},
            {'title': 'WORKMAN 兒童', 'handle': 'workman-兒童'},
        ]
        return collections
    
    def get_products_from_collection(self, collection_handle, limit=250):
        """
        取得指定系列的商品
        
        Args:
            collection_handle: 系列的 handle
            limit: 商品數量限制
        
        Returns:
            商品列表
        """
        if self.access_token:
            # Admin API 方式
            # 先取得 collection ID
            collections = self.get_collections()
            collection_id = None
            
            for col in collections:
                if col.get('handle') == collection_handle:
                    collection_id = col.get('id')
                    break
            
            if collection_id:
                # 使用 products.json 並用 collection_id 過濾，這樣可以取得完整商品資料（包含 variants）
                endpoint = 'products.json'
                data = self._make_request(endpoint, {'collection_id': collection_id, 'limit': limit})
                if data and 'products' in data:
                    return data['products']
        
        # Storefront 方式（使用公開的 JSON endpoint）
        encoded_handle = quote(collection_handle, safe='')
        url = f"{self.store_url}/collections/{encoded_handle}/products.json"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('products', [])
        except Exception as e:
            print(f"取得系列商品失敗: {e}")
            return []
    
    def get_product_by_id(self, product_id):
        """
        取得特定商品
        
        Args:
            product_id: 商品 ID
        
        Returns:
            商品資料
        """
        if self.access_token:
            endpoint = f'products/{product_id}.json'
            data = self._make_request(endpoint)
            if data and 'product' in data:
                return data['product']
        
        # Storefront 不支援直接用 ID 查詢
        return None
    
    def get_product_by_handle(self, handle):
        """
        透過 handle 取得商品
        
        Args:
            handle: 商品的 URL handle
        
        Returns:
            商品資料
        """
        encoded_handle = quote(handle, safe='')
        url = f"{self.store_url}/products/{encoded_handle}.json"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('product')
        except Exception as e:
            print(f"取得商品失敗: {e}")
            return None
    
    def add_tag_to_product(self, product_id, new_tag):
        """
        為商品新增標籤
        
        Args:
            product_id: 商品 ID
            new_tag: 要新增的標籤
        
        Returns:
            是否成功
        """
        if not self.access_token:
            print("需要 Admin API Token 才能新增標籤")
            return False
        
        # 先取得商品目前的標籤
        product = self.get_product_by_id(product_id)
        if not product:
            return False
        
        current_tags = product.get('tags', '')
        if isinstance(current_tags, list):
            tag_list = current_tags
        else:
            tag_list = [t.strip() for t in current_tags.split(',') if t.strip()]
        
        # 如果標籤已存在，不重複新增
        if new_tag in tag_list:
            return True
        
        # 新增標籤
        tag_list.append(new_tag)
        new_tags = ', '.join(tag_list)
        
        # 更新商品（使用較新的 API 版本）
        url = f"{self.store_url}/admin/api/2024-10/products/{product_id}.json"
        payload = {
            'product': {
                'id': product_id,
                'tags': new_tags
            }
        }
        
        try:
            response = self.session.put(url, json=payload, timeout=30)
            if not response.ok:
                print(f"新增標籤失敗: {response.status_code} - {response.text}")
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"新增標籤失敗: {e}")
            return False
    
    def remove_tags_with_prefix(self, product_id, prefix):
        """
        移除商品中符合前綴的標籤
        
        Args:
            product_id: 商品 ID
            prefix: 標籤前綴
        
        Returns:
            是否成功
        """
        if not self.access_token:
            print("需要 Admin API Token 才能移除標籤")
            return False
        
        product = self.get_product_by_id(product_id)
        if not product:
            return False
        
        current_tags = product.get('tags', '')
        if isinstance(current_tags, list):
            tag_list = current_tags
        else:
            tag_list = [t.strip() for t in current_tags.split(',') if t.strip()]
        
        # 過濾掉符合前綴的標籤
        new_tag_list = [t for t in tag_list if not t.startswith(prefix)]
        
        if len(new_tag_list) == len(tag_list):
            # 沒有變化
            return True
        
        new_tags = ', '.join(new_tag_list)
        
        url = f"{self.store_url}/admin/api/2024-10/products/{product_id}.json"
        payload = {
            'product': {
                'id': product_id,
                'tags': new_tags
            }
        }
        
        try:
            response = self.session.put(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"移除標籤失敗: {e}")
            return False
    
    def get_products_from_multiple_collections(self, collection_names, limit=250):
        """
        取得多個系列的商品（按上架時間排序，新的優先）
        
        Args:
            collection_names: 系列名稱列表
            limit: 商品數量限制
        
        Returns:
            商品列表（按上架時間排序）
        """
        all_products = []
        seen_ids = set()
        
        for name in collection_names:
            # 尋找對應的 handle
            handle = self._find_collection_handle(name)
            if not handle:
                continue
            
            products = self.get_products_from_collection(handle, limit)
            for p in products:
                if p['id'] not in seen_ids:
                    seen_ids.add(p['id'])
                    all_products.append(p)
        
        # 按上架時間排序（新的優先）
        all_products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return all_products
    
    def _find_collection_handle(self, name):
        """
        根據系列名稱找到對應的 handle
        
        Args:
            name: 系列名稱
        
        Returns:
            handle 字串
        """
        # 名稱對應表
        name_to_handle = {
            '小倉山莊': '小倉山莊',
            'YOKUMOKU': 'yokumoku',
            '砂糖奶油樹': '砂糖奶油樹',
            '坂角總本舖': '坂角總本舖',
            '神戶風月堂': '神戶風月堂',
            '銀座菊廼舍': '銀座菊廼舍',
            '資生堂PARLOUR': '資生堂parlour',
            '虎屋羊羹': '虎屋羊羹',
            'FRANCAIS': 'francais',
            'COCORIS': 'cocoris',
            'Gateau Festa Harada': 'gateau-festa-harada',
            'The maple mania 楓糖男孩': 'the-maple-mania-楓糖男孩',
            'Human Made': 'human-made-1',
            'X-girl': 'x-girl',
            "BAPE Men's": 'bape',
            "BAPE Women's": 'bape',
            "BAPE kids": 'bape',
            'work man 作業服': 'workman-作業服',
            'work man 男裝': 'workman-男裝',
            'work man 女裝': 'workman-女裝',
            'work man 兒童': 'workman-兒童',
        }
        
        # 先嘗試直接對應
        if name in name_to_handle:
            return name_to_handle[name]
        
        # 嘗試忽略大小寫
        for key, value in name_to_handle.items():
            if key.lower() == name.lower():
                return value
        
        # 嘗試用名稱作為 handle
        return name.lower().replace(' ', '-')


# 測試用
if __name__ == '__main__':
    # 測試 Storefront API（無需 token）
    client = ShopifyClient('https://goyoutati.com')
    
    print("📦 取得系列列表...")
    collections = client.get_collections()
    for col in collections[:5]:
        print(f"   • {col['title']}")
    
    print("\n📦 取得 YOKUMOKU 系列商品...")
    products = client.get_products_from_collection('yokumoku')
    for p in products[:3]:
        print(f"   • {p['title']}")
