"""
設定檔 - 請填入你的 API 金鑰

方法一：建立 .env 檔案（推薦）
方法二：設定系統環境變數
"""

import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

class Config:
    """API 設定"""
    
    # ============================================
    # Shopify 設定
    # ============================================
    # 你的商店網址
    SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL', 'https://goyoutati.com')
    
    # Shopify Admin API Access Token
    # 取得方式：Shopify 後台 → Settings → Apps and sales channels → Develop apps
    SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN', '')
    
    # ============================================
    # Facebook 設定
    # ============================================
    # Facebook 粉絲專頁 ID
    # 取得方式：粉專 → 關於 → Page ID 或從 URL 取得
    FB_PAGE_ID = os.getenv('FB_PAGE_ID', '')
    
    # Facebook Page Access Token
    # 取得方式：Meta Developer → 你的 App → Tools → Graph API Explorer
    # 權限需求：pages_manage_posts, pages_read_engagement
    FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN', '')
    
    # ============================================
    # Instagram 設定
    # ============================================
    # Instagram Business Account ID
    # 取得方式：透過 Facebook Graph API 查詢
    IG_ACCOUNT_ID = os.getenv('IG_ACCOUNT_ID', '')
    
    # Instagram Access Token (與 Facebook 共用)
    # 權限需求：instagram_basic, instagram_content_publish
    IG_ACCESS_TOKEN = os.getenv('IG_ACCESS_TOKEN', '')
    
    # ============================================
    # Threads 設定
    # ============================================
    # Threads User ID
    THREADS_USER_ID = os.getenv('THREADS_USER_ID', '')
    
    # Threads Access Token
    # 取得方式：Meta Developer → Threads API
    # 權限需求：threads_basic, threads_content_publish
    THREADS_ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN', '')
    
    # ============================================
    # 貼文設定
    # ============================================
    # 預設 hashtags
    DEFAULT_HASHTAGS = [
        '#御用達',
        '#日本伴手禮',
        '#日本代購',
        '#GOYOUTATI',
        '#日本甜點',
        '#伴手禮推薦'
    ]
    
    # 貼文模板（可自訂）
    POST_TEMPLATE = """✨ {title}

{description}

💰 NT$ {price}
🛒 立即購買：{product_url}

{hashtags}
"""
    
    # ============================================
    # 商品系列設定（新增系列只要在這裡加一行）
    # ============================================
    # 日本伴手禮系列
    SOUVENIR_COLLECTIONS = os.getenv('SOUVENIR_COLLECTIONS', 
        '小倉山莊,YOKUMOKU,砂糖奶油樹,坂角總本舖,神戶風月堂,銀座菊廼舍,資生堂PARLOUR,虎屋羊羹,FRANCAIS,COCORIS,Gateau Festa Harada,The maple mania 楓糖男孩'
    ).split(',')
    SOUVENIR_COLLECTIONS = [c.strip() for c in SOUVENIR_COLLECTIONS if c.strip()]
    
    # 日本服飾系列
    FASHION_COLLECTIONS = os.getenv('FASHION_COLLECTIONS',
        "Human Made,X-girl,BAPE Men's,BAPE Women's,BAPE kids,work man 作業服,work man 男裝,work man 女裝,work man 兒童"
    ).split(',')
    FASHION_COLLECTIONS = [c.strip() for c in FASHION_COLLECTIONS if c.strip()]
    
    # 發文標籤前綴
    SOUVENIR_POSTED_TAG = '伴手禮已發-輪次'
    FASHION_POSTED_TAG = '服飾已發-輪次'
    
    def validate(self):
        """驗證設定是否完整"""
        errors = []
        
        if not self.SHOPIFY_ACCESS_TOKEN:
            errors.append("缺少 SHOPIFY_ACCESS_TOKEN")
        
        # 至少需要一個社群平台的設定
        has_social = any([
            self.FB_PAGE_ID and self.FB_ACCESS_TOKEN,
            self.IG_ACCOUNT_ID and self.IG_ACCESS_TOKEN,
            self.THREADS_USER_ID and self.THREADS_ACCESS_TOKEN
        ])
        
        if not has_social:
            errors.append("至少需要設定一個社群平台 (FB/IG/Threads)")
        
        if errors:
            print("⚠️  設定驗證失敗：")
            for error in errors:
                print(f"   • {error}")
            return False
        
        return True
    
    def show_status(self):
        """顯示設定狀態"""
        print("\n📋 設定狀態：")
        print(f"   Shopify: {'✅' if self.SHOPIFY_ACCESS_TOKEN else '❌'}")
        print(f"   Facebook: {'✅' if (self.FB_PAGE_ID and self.FB_ACCESS_TOKEN) else '❌'}")
        print(f"   Instagram: {'✅' if (self.IG_ACCOUNT_ID and self.IG_ACCESS_TOKEN) else '❌'}")
        print(f"   Threads: {'✅' if (self.THREADS_USER_ID and self.THREADS_ACCESS_TOKEN) else '❌'}")
        print()


# ============================================
# 系列對應表（方便使用中文名稱）
# ============================================
COLLECTION_MAPPING = {
    # 伴手禮系列
    '小倉山莊': '小倉山莊',
    'yokumoku': 'yokumoku',
    '砂糖奶油樹': '砂糖奶油樹',
    '坂角總本舖': '坂角總本舖',
    '神戶風月堂': '神戶風月堂',
    '銀座菊廼舍': '銀座菊廼舍',
    '資生堂parlour': '資生堂parlour',
    '虎屋羊羹': '虎屋羊羹',
    'francais': 'francais',
    'cocoris': 'cocoris',
    'harada': 'gateau-festa-harada',
    '楓糖男孩': 'the-maple-mania-楓糖男孩',
    
    # 服飾系列
    'human-made': 'human-made-1',
    'x-girl': 'x-girl',
    'bape': 'bape',
    'workman': 'workman-作業服',
    'workman-男裝': 'workman-男裝',
    'workman-女裝': 'workman-女裝',
    'workman-兒童': 'workman-兒童',
}
