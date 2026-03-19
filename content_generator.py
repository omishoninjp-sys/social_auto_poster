"""
content_generator.py
多類型貼文生成器

支援三種貼文類型：
  product  - 商品介紹（原有邏輯，不呼叫 Claude API）
  opinion  - 觀點文（Claude 生成，帶犀利觀點，引發討論）
  wishlist - 許願互動文（Claude 生成，CTA 讓讀者留言）

使用方式：
  from content_generator import build_post_content, get_today_post_type
  post_type = get_today_post_type()
  content   = build_post_content(product, config, post_type=post_type)
"""

import os
import re
import requests
from datetime import datetime

# ============================================================
# 每日發文類型排班
# 0=週一 … 6=週日
# ============================================================
POST_SCHEDULE = {
    0: 'product',    # 週一：商品介紹
    1: 'opinion',    # 週二：觀點文
    2: 'product',    # 週三：商品介紹
    3: 'wishlist',   # 週四：許願互動
    4: 'product',    # 週五：商品介紹
    5: 'opinion',    # 週六：觀點文
    6: 'product',    # 週日：商品介紹
}

# Webhook 觸發的新商品永遠用 product 類型（新上架就是要曝光商品）
WEBHOOK_POST_TYPE = 'product'


def get_today_post_type() -> str:
    """根據今天星期幾，回傳應該發的貼文類型"""
    return POST_SCHEDULE[datetime.now().weekday()]


# ============================================================
# 工具函式
# ============================================================

def _strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html or '')


def _get_price_line(product: dict) -> str:
    """計算價格並格式化"""
    DEFAULT_RATE = 0.22
    variants = product.get('variants', [])
    price_jpy_str = variants[0].get('price', '0') if variants else '0'
    try:
        price_jpy = float(price_jpy_str)
        if price_jpy > 0:
            rate = _fetch_jpy_twd_rate(DEFAULT_RATE)
            price_twd = int(price_jpy * rate)
            return f"💰 ¥{int(price_jpy):,}（約NT${price_twd:,}）"
    except Exception:
        pass
    return "💰 價格請詢價"


def _fetch_jpy_twd_rate(default: float) -> float:
    for url in [
        "https://api.exchangerate-api.com/v4/latest/JPY",
        "https://open.er-api.com/v6/latest/JPY",
    ]:
        try:
            r = requests.get(url, timeout=5)
            if r.ok:
                return r.json().get('rates', {}).get('TWD', default)
        except Exception:
            pass
    return default


def _get_brand_hashtag(product: dict) -> str:
    """從商品 handle / title 自動抽品牌 hashtag"""
    handle = product.get('handle', '').lower()
    title  = product.get('title', '')
    checks = [
        ('bape',        '#BAPE'),
        ('workman',     '#WORKMAN'),
        ('human-made',  '#HumanMade'),
        ('human made',  '#HumanMade'),
        ('x-girl',      '#Xgirl'),
        ('yokumoku',    '#YOKUMOKU'),
        ('adidas',      '#adidas'),
        ('nike',        '#Nike'),
        ('uniqlo',      '#UNIQLO'),
        ('muji',        '#MUJI'),
        ('小倉山莊',    '#小倉山莊'),
        ('砂糖奶油樹',  '#砂糖奶油樹'),
        ('坂角',        '#坂角總本舖'),
        ('風月堂',      '#神戶風月堂'),
        ('虎屋',        '#虎屋羊羹'),
        ('資生堂',      '#資生堂PARLOUR'),
        ('菊廼舍',      '#銀座菊廼舍'),
        ('楓糖',        '#楓糖男孩'),
    ]
    combined = f"{handle} {title.lower()}"
    for kw, tag in checks:
        if kw in combined:
            return tag
    return ''


def _get_images(product: dict):
    imgs = product.get('images', [])
    urls = [i.get('src') for i in imgs if i.get('src')]
    return urls


_SERVICE_URL = (
    'https://goyoutati.com/pages/'
    '%E6%97%A5%E6%9C%AC%E4%BB%A3%E8%B3%BC-%E4%B8%80%E6%A2%9D%E9%80%A3%E7%B5%90-%E9%80%81%E5%88%B0%E4%BD%A0%E5%AE%B6'
)

_SERVICE_BODY = """🇯🇵 看到喜歡的日本商品，貼上連結就能買！
GOYOUTATI 御用達幫你代購，空運含稅直送台灣。

📦 服務流程
1️⃣ 貼上任意日本商品連結，或直接在本站下單
2️⃣ 我們代購並集運至台灣倉（免費存放最長 1 個月）
3️⃣ 到倉 Email 通知 → 確認運費 → 到府配送

✅ 含稅含關稅，無隱藏費用
✅ 業界最低，每公斤1,000円日幣約台幣200
✅ 無最低出貨重量，1KG也能出貨"""


# ============================================================
# Claude API 呼叫
# ============================================================

def _call_claude(prompt: str, system: str = '') -> str | None:
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        print("[content_generator] ⚠️  未設定 ANTHROPIC_API_KEY，跳過 Claude 生成")
        return None

    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    body = {
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 600,
        'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            json=body, headers=headers, timeout=30
        )
        r.raise_for_status()
        return r.json()['content'][0]['text'].strip()
    except Exception as e:
        print(f"[content_generator] Claude API 錯誤: {e}")
        return None


# ============================================================
# 各類型文案生成
# ============================================================

def _generate_opinion_text(product: dict) -> str | None:
    """
    觀點文：帶犀利觀點、引發討論，不直接推銷
    返回純文字（無 hashtag、無價格、無 URL）
    """
    title  = product.get('title', '')
    handle = product.get('handle', '').lower()

    # 根據品類選擇切入角度，讓 prompt 更精準
    if any(k in handle for k in ['yokumoku', '小倉山莊', '砂糖', '坂角', '風月堂', '虎屋', '資生堂', '菊廼舍', '楓糖']):
        angle_hint = "台灣買不到或買很貴的理由、日本當地人怎麼看這個品牌"
    else:
        angle_hint = "台灣代購比直接在台灣買便宜多少、這商品在日本有什麼台灣沒有的版本"

    system = (
        "你是一個住在台灣的日本代購達人，對日本品牌、文化有深入了解，"
        "說話直接、有觀點、偶爾帶點幽默，像在跟朋友聊天。用繁體中文寫作。"
    )
    prompt = f"""幫我寫一篇脆（Threads）的觀點型貼文，以這個日本商品為主角。

商品名稱：{title}

切入角度（擇一或混搭）：{angle_hint}

規則：
- 核心是「有觀點的評論」，不是商品介紹
- 語氣直接、有態度，但不失親切
- 結尾自然帶出「有人想買嗎？」或「想代購留言」的意思，不要太直白推銷
- 不要出現 hashtag、price、URL
- 不超過 380 字
- 直接輸出文章本文，不要有標題或前言"""

    return _call_claude(prompt, system)


def _generate_wishlist_text(product: dict) -> str | None:
    """
    許願互動文：以商品為引子，讓讀者留言說想代購什麼
    返回純文字（無 hashtag、無價格、無 URL）
    """
    title = product.get('title', '')

    system = (
        "你是一個台灣的日本代購達人，說話輕鬆像朋友聊天。用繁體中文寫作。"
    )
    prompt = f"""幫我寫一篇脆（Threads）的互動型貼文，以這個日本商品為引子。

商品名稱：{title}

規則：
- 以這個商品帶出話題（例如「今天幫客人代購了XX，讓我想到...」）
- 自然引導讀者說出自己想代購的商品
- 結尾要有明確的留言 CTA，例如「你有什麼想從日本帶回來的？」
- 語氣輕鬆、像在聊天，不要太商業感
- 不要出現 hashtag、URL
- 不超過 280 字
- 直接輸出文章本文，不要有標題或前言"""

    return _call_claude(prompt, system)


# ============================================================
# 主要對外函式
# ============================================================

def build_post_content(product: dict, config, post_type: str = 'product') -> dict:
    """
    根據 post_type 生成完整的貼文內容字典。
    
    回傳格式與原本 generate_post_content() 相同，可直接傳給 post_to_platforms()：
    {
        'text':         str,   # FB / IG 版（含 hashtag）
        'text_no_tags': str,   # Threads 版（無 hashtag）
        'image_url':    str,
        'image_urls':   list,
        'product_url':  str,
        'title':        str,
        'post_type':    str,   # 新增，方便 logging
    }
    """
    title      = product.get('title', '')
    image_urls = _get_images(product)
    image_url  = image_urls[0] if image_urls else None
    price_line = _get_price_line(product)
    brand_tag  = _get_brand_hashtag(product)
    base_tags  = '#日本代購 #日本伴手禮 #GOYOUTATI'
    hashtags   = f"{base_tags} {brand_tag}".strip() if brand_tag else base_tags

    # ── opinion / wishlist：用 Claude 生成主體文 ──────────
    if post_type == 'opinion':
        body = _generate_opinion_text(product)
        if not body:
            print(f"[content_generator] opinion 生成失敗，改用 product 類型")
            post_type = 'product'

    if post_type == 'wishlist':
        body = _generate_wishlist_text(product)
        if not body:
            print(f"[content_generator] wishlist 生成失敗，改用 product 類型")
            post_type = 'product'

    # ── product（含 fallback）：固定服務文案 ─────────────
    if post_type == 'product':
        body = f"✨ {title}\n\n{_SERVICE_BODY}"

    # ── 組合最終貼文 ──────────────────────────────────────
    if post_type in ('opinion', 'wishlist'):
        # 觀點 / 許願文：body 已包含主體，結尾加短版引導
        footer_fb_ig = (
            f"\n\n{price_line}\n"
            f"🛒 代購諮詢：{_SERVICE_URL}\n\n"
            f"{hashtags}"
        )
        footer_threads = (
            f"\n\n{price_line}\n"
            f"🛒 代購諮詢：{_SERVICE_URL}"
        )
        text_fb_ig = f"{body}{footer_fb_ig}"
        text_threads = f"{body}{footer_threads}"

    else:  # product
        footer = (
            f"\n\n{price_line}\n"
            f"含關稅，出貨前補運費（每公斤¥1,000／約NT$200）\n"
            f"🛒 立即購買：{_SERVICE_URL}"
        )
        text_fb_ig  = f"{body}{footer}\n\n{hashtags}"
        text_threads = f"{body}{footer}"

    # Threads 500 字上限
    if len(text_threads) > 500:
        text_threads = text_threads[:497] + '...'

    return {
        'text':         text_fb_ig,
        'text_no_tags': text_threads,
        'image_url':    image_url,
        'image_urls':   image_urls,
        'product_url':  _SERVICE_URL,
        'title':        title,
        'post_type':    post_type,
    }
