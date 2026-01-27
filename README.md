# 🎌 御用達 GOYOUTATI - 社群自動發文系統

自動從 Shopify 商店抓取商品，發布到 Facebook、Instagram、Threads。

## ✨ 功能

- 📦 隨機選擇商品或指定系列
- 📱 支援 Facebook、Instagram、Threads
- ⏰ 支援排程自動發文
- 🖼️ 自動包含商品圖片
- 🔗 自動生成購買連結

## 📋 前置需求

### 1. Shopify Admin API

1. 前往 Shopify 後台 → Settings → Apps and sales channels
2. 點選「Develop apps」
3. 建立新 App，啟用 Admin API
4. 複製 Access Token

**需要的權限：**
- `read_products` - 讀取商品
- `write_products` - 寫入商品（用於標記已發文）
- `read_product_listings`

### 2. Meta Developer App (FB/IG/Threads)

1. 前往 [Meta Developer](https://developers.facebook.com/)
2. 建立新 App → Business 類型
3. 新增產品：Facebook Login, Instagram Graph API, Threads API

**Facebook 設定：**
```
1. Settings → Basic → 取得 App ID 和 App Secret
2. Tools → Graph API Explorer
3. 選擇你的 App 和粉專
4. 新增權限：pages_manage_posts, pages_read_engagement
5. Generate Access Token → 取得 Page Access Token
```

**Instagram 設定：**
```
1. 確保你的 Instagram 帳號是「商業帳號」或「創作者帳號」
2. 在 Facebook 粉專設定中連結 Instagram 帳號
3. 透過 Graph API 取得 Instagram Business Account ID
4. 新增權限：instagram_basic, instagram_content_publish
```

**Threads 設定：**
```
1. 在 Meta Developer 中新增 Threads API
2. 設定 Threads 存取權限
3. 新增權限：threads_basic, threads_content_publish
4. 取得 Threads User ID 和 Access Token
```

### 3. 取得各平台 ID

**取得 Facebook Page ID：**
```bash
# 方法一：從粉專 URL
https://www.facebook.com/goyoutatiJP/
# 按「關於」→ Page ID

# 方法二：使用 Graph API
curl "https://graph.facebook.com/v19.0/me/accounts?access_token=YOUR_TOKEN"
```

**取得 Instagram Business Account ID：**
```bash
curl "https://graph.facebook.com/v19.0/YOUR_PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN"
```

**取得 Threads User ID：**
```bash
curl "https://graph.threads.net/v1.0/me?access_token=YOUR_THREADS_TOKEN"
```

## 🚀 安裝

```bash
# 1. 複製專案
cd social_auto_poster

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定 API 金鑰
# 編輯 config.py 或設定環境變數
```

## ⚙️ 設定

編輯 `config.py` 或設定環境變數：

```bash
# Shopify
export SHOPIFY_STORE_URL="https://goyoutati.com"
export SHOPIFY_ACCESS_TOKEN="shpat_xxxxx"

# Facebook
export FB_PAGE_ID="your_page_id"
export FB_ACCESS_TOKEN="your_token"

# Instagram
export IG_ACCOUNT_ID="your_ig_business_account_id"
export IG_ACCESS_TOKEN="your_token"

# Threads
export THREADS_USER_ID="your_threads_user_id"
export THREADS_ACCESS_TOKEN="your_threads_token"
```

## 📖 使用方式

### 🧠 智慧選擇模式（推薦）

自動 1:1 交替發布伴手禮和服飾，新上架優先，不重複發文。

```bash
# 智慧發文 1 篇（自動交替伴手禮/服飾）
python main.py --smart

# 智慧發文 10 篇（5 伴手禮 + 5 服飾）
python main.py --smart --count 10

# 只發伴手禮
python main.py --smart --category souvenir

# 只發服飾
python main.py --smart --category fashion

# 測試模式（不實際發文）
python main.py --smart --count 10 --dry-run

# 查看發文統計
python main.py --stats

# 重置伴手禮輪次（全部重新發一輪）
python main.py --reset souvenir
```

### 基本用法

```bash
# 隨機選擇商品發文到所有平台
python main.py --random

# 從指定系列選擇商品
python main.py --collection yokumoku

# 只發到特定平台
python main.py --random --platforms fb,ig

# 測試模式（不實際發文）
python main.py --random --dry-run

# 列出所有系列
python main.py --list-collections
```

### 排程自動發文

```bash
# 使用預設排程（每天 10:00, 14:00, 18:00）
python scheduler.py

# 自訂發文時間
python scheduler.py --times 09:00,12:00,18:00,21:00

# 每 4 小時發一次
python scheduler.py --interval 4

# 只從特定系列發文
python scheduler.py --collections yokumoku,小倉山莊

# 立即執行一次（測試用）
python scheduler.py --once
```

### 可用系列

**伴手禮系列：**
- `小倉山莊`
- `yokumoku`
- `砂糖奶油樹`
- `坂角總本舖`
- `神戶風月堂`
- `銀座菊廼舍`
- `資生堂parlour`
- `虎屋羊羹`
- `francais`
- `cocoris`
- `gateau-festa-harada`
- `the-maple-mania-楓糖男孩`

**服飾系列：**
- `human-made-1`
- `x-girl`
- `bape`
- `workman-作業服`
- `workman-男裝`
- `workman-女裝`
- `workman-兒童`

### 新增系列

在 `.env` 檔案中修改：

```env
# 日本伴手禮系列（用逗號分隔）
SOUVENIR_COLLECTIONS=小倉山莊,YOKUMOKU,砂糖奶油樹,新系列名稱

# 日本服飾系列（用逗號分隔）
FASHION_COLLECTIONS=Human Made,X-girl,BAPE Men's,新系列名稱
```

## 🔧 部署到伺服器

### 使用 cron-job.org（推薦）

1. 將專案部署到 Zeabur 或其他雲端平台
2. 建立一個 API endpoint 來觸發發文
3. 在 cron-job.org 設定排程呼叫該 endpoint

### 使用 systemd（Linux 伺服器）

```bash
# 建立 service 檔案
sudo nano /etc/systemd/system/goyoutati-poster.service
```

```ini
[Unit]
Description=GOYOUTATI Social Auto Poster
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/social_auto_poster
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 啟動服務
sudo systemctl enable goyoutati-poster
sudo systemctl start goyoutati-poster

# 查看狀態
sudo systemctl status goyoutati-poster
```

## 📝 貼文模板自訂

編輯 `config.py` 中的 `POST_TEMPLATE`：

```python
POST_TEMPLATE = """✨ {title}

{description}

💰 NT$ {price}
🛒 立即購買：{product_url}

{hashtags}
"""
```

可用變數：
- `{title}` - 商品名稱
- `{description}` - 商品描述
- `{price}` - 價格
- `{product_url}` - 商品連結
- `{hashtags}` - Hashtags

## ⚠️ 注意事項

1. **Instagram 圖片要求**
   - 圖片必須是公開可存取的 URL
   - 支援 JPEG、PNG 格式
   - 建議尺寸：1080x1080 (方形) 或 1080x1350 (直式)

2. **API 速率限制**
   - Facebook/Instagram：每小時約 200 次
   - Threads：每天約 250 則貼文
   - 建議發文間隔至少 1 小時

3. **Token 過期**
   - Short-lived token 有效期約 1 小時
   - Long-lived token 有效期約 60 天
   - 建議使用 Long-lived token 並定期更新

## 🐛 疑難排解

**Q: Instagram 發文失敗？**
- 確認圖片 URL 是公開可存取的
- 確認帳號已連結到 Facebook 粉專
- 確認帳號是商業帳號

**Q: Token 過期了？**
```bash
# 延長 Token 有效期
curl "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

**Q: 如何測試 API 連線？**
```python
python -c "from social_clients import FacebookClient; fb = FacebookClient('PAGE_ID', 'TOKEN'); print(fb.get_page_info())"
```

## 📄 License

MIT License

## 👨‍💻 作者

近江商人株式會社
