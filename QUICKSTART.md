# 🎌 御用達 GOYOUTATI - 本機版快速啟動指南

## 📦 Step 1：解壓縮並進入資料夾

```bash
cd social_auto_poster
```

---

## 📦 Step 2：安裝 Python 套件

```bash
pip install -r requirements.txt
```

---

## 📦 Step 3：建立 .env 檔案

複製範本：
```bash
copy .env.example .env
```

然後編輯 `.env` 檔案，填入你的 API 金鑰：

```env
# Shopify
SHOPIFY_STORE_URL=https://goyoutati.com
SHOPIFY_ACCESS_TOKEN=你的Shopify_Admin_API_Token

# Facebook (御用達-光頭哥)
FB_PAGE_ID=112472061526867
FB_ACCESS_TOKEN=你的FB_Page_Token

# Instagram
IG_ACCOUNT_ID=17841445371664210
IG_ACCESS_TOKEN=你的IG_Token

# Threads
THREADS_USER_ID=25704560162488549
THREADS_ACCESS_TOKEN=你的Threads_Token
```

---

## 🧪 Step 4：測試模式（不會實際發文）

```bash
# 隨機選商品，預覽貼文內容
python main.py --random --dry-run

# 從 YOKUMOKU 系列選商品
python main.py --collection yokumoku --dry-run

# 列出所有可用系列
python main.py --list-collections
```

---

## 🚀 Step 5：實際發文

```bash
# 隨機商品 → 發到 FB + IG + Threads
python main.py --random

# 指定系列
python main.py --collection 小倉山莊

# 只發到特定平台
python main.py --random --platforms fb
python main.py --random --platforms fb,ig
python main.py --random --platforms threads
```

---

## ⏰ Step 6：排程自動發文（選用）

```bash
# 預設排程：每天 10:00, 14:00, 18:00
python scheduler.py

# 自訂時間
python scheduler.py --times 09:00,12:00,18:00,21:00

# 每 4 小時發一次
python scheduler.py --interval 4

# 只用特定系列
python scheduler.py --collections yokumoku,小倉山莊
```

---

## 📋 可用的系列 (Collection)

### 伴手禮
| 名稱 | handle |
|------|--------|
| 小倉山莊 | `小倉山莊` |
| YOKUMOKU | `yokumoku` |
| 砂糖奶油樹 | `砂糖奶油樹` |
| 坂角總本舖 | `坂角總本舖` |
| 神戶風月堂 | `神戶風月堂` |
| 銀座菊廼舍 | `銀座菊廼舍` |
| 資生堂PARLOUR | `資生堂parlour` |
| 虎屋羊羹 | `虎屋羊羹` |
| FRANÇAIS | `francais` |
| COCORIS | `cocoris` |
| Gateau Festa Harada | `gateau-festa-harada` |
| 楓糖男孩 | `the-maple-mania-楓糖男孩` |

### 服飾
| 名稱 | handle |
|------|--------|
| Human Made | `human-made-1` |
| X-girl | `x-girl` |
| BAPE | `bape` |
| WORKMAN 作業服 | `workman-作業服` |
| WORKMAN 男裝 | `workman-男裝` |
| WORKMAN 女裝 | `workman-女裝` |
| WORKMAN 兒童 | `workman-兒童` |

---

## ⚠️ 常見問題

### Q: Instagram 發文失敗？
- 圖片必須是公開 URL（Shopify CDN 的圖片應該沒問題）
- 確認 IG 帳號是「商業帳號」

### Q: Token 過期？
- FB/IG Token 約 60 天過期
- Threads Token 也會過期
- 需要回到 Meta Developer 重新產生

### Q: 要換發到其他粉專？
修改 `.env` 中的 `FB_PAGE_ID`：
- 御用達-光頭哥：`112472061526867`
- 御用達-日本跨境電商：`292351400632577`

---

## 🎯 測試順序建議

1. 先用 `--dry-run` 確認能抓到商品
2. 單獨測試 `--platforms fb` 
3. 單獨測試 `--platforms ig`
4. 單獨測試 `--platforms threads`
5. 全部一起 `--platforms fb,ig,threads`

---

測試成功後，告訴我！我們再部署到 Zeabur 🚀
