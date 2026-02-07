"""
圖片處理工具
用於生成限動用的 9:16 圖片（模糊背景）
"""

import requests
import os
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
import base64


def create_story_image(image_url, target_width=1080, target_height=1920):
    """
    將圖片轉換為限動格式（9:16），加上模糊背景
    
    Args:
        image_url: 原始圖片 URL
        target_width: 目標寬度（預設 1080）
        target_height: 目標高度（預設 1920）
    
    Returns:
        Base64 編碼的圖片字串，或 None（失敗時）
    """
    try:
        # 下載原始圖片
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # 開啟圖片
        original = Image.open(BytesIO(response.content))
        
        # 轉換為 RGB（避免 PNG 透明度問題）
        if original.mode in ('RGBA', 'P'):
            original = original.convert('RGB')
        
        # 計算縮放比例（讓圖片寬度符合目標寬度）
        scale = target_width / original.width
        new_width = target_width
        new_height = int(original.height * scale)
        
        # 如果縮放後高度超過目標高度，改用高度縮放
        if new_height > target_height:
            scale = target_height / original.height
            new_height = target_height
            new_width = int(original.width * scale)
        
        # 縮放原始圖片
        resized = original.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 建立模糊背景
        # 先將原圖放大填滿整個畫布，然後模糊
        bg_scale = max(target_width / original.width, target_height / original.height)
        bg_width = int(original.width * bg_scale)
        bg_height = int(original.height * bg_scale)
        
        background = original.resize((bg_width, bg_height), Image.Resampling.LANCZOS)
        
        # 裁切到目標大小
        left = (bg_width - target_width) // 2
        top = (bg_height - target_height) // 2
        background = background.crop((left, top, left + target_width, top + target_height))
        
        # 套用模糊效果
        background = background.filter(ImageFilter.GaussianBlur(radius=30))
        
        # 降低背景亮度（讓主圖更突出）
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.6)
        
        # 將主圖貼到背景中央
        x = (target_width - new_width) // 2
        y = (target_height - new_height) // 2
        background.paste(resized, (x, y))
        
        # 轉換為 Base64
        buffer = BytesIO()
        background.save(buffer, format='JPEG', quality=90)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
    except Exception as e:
        print(f"[限動] 圖片處理失敗: {e}")
        return None


def upload_image_to_imgbb(base64_image):
    """
    上傳 Base64 圖片到 ImgBB
    
    Args:
        base64_image: Base64 編碼的圖片
    
    Returns:
        圖片 URL 或 None
    """
    # 從環境變數取得 API Key
    api_key = os.getenv('IMGBB_API_KEY')
    
    if not api_key:
        print("[限動] 警告: 未設定 IMGBB_API_KEY，無法上傳處理後的圖片")
        return None
    
    try:
        url = "https://api.imgbb.com/1/upload"
        
        data = {
            'key': api_key,
            'image': base64_image,
        }
        
        response = requests.post(url, data=data, timeout=60)
        
        if response.ok:
            result = response.json()
            if result.get('success'):
                image_url = result['data']['url']
                print(f"[限動] 圖片上傳成功: {image_url[:60]}...")
                return image_url
            else:
                print(f"[限動] ImgBB 回傳失敗: {result}")
        else:
            print(f"[限動] ImgBB HTTP 錯誤: {response.status_code} - {response.text[:200]}")
        
        return None
        
    except Exception as e:
        print(f"[限動] 上傳圖片失敗: {e}")
        return None


def create_story_image_url(image_url):
    """
    將原始圖片轉換為限動格式並上傳，返回新的 URL
    
    Args:
        image_url: 原始圖片 URL
    
    Returns:
        限動格式圖片的 URL，或原始 URL（失敗時）
    """
    # 檢查是否有設定 IMGBB_API_KEY
    if not os.getenv('IMGBB_API_KEY'):
        print("[限動] 未設定 IMGBB_API_KEY，跳過圖片處理，使用原圖")
        return image_url
    
    # 生成限動圖片
    base64_image = create_story_image(image_url)
    
    if not base64_image:
        print("[限動] 圖片處理失敗，使用原圖")
        return image_url
    
    # 上傳到圖床
    new_url = upload_image_to_imgbb(base64_image)
    
    if new_url:
        return new_url
    else:
        print("[限動] 圖片上傳失敗，使用原圖")
        return image_url


# 測試
if __name__ == '__main__':
    test_url = "https://cdn.shopify.com/s/files/1/0578/2340/0554/files/S__26771461_0.jpg"
    result = create_story_image_url(test_url)
    print(f"結果: {result}")
