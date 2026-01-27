"""
社群平台 API 客戶端
支援 Facebook、Instagram、Threads 發文
"""

import requests
import time
from urllib.parse import urlencode

class FacebookClient:
    """Facebook Graph API 客戶端"""
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, page_id, access_token):
        """
        初始化 Facebook 客戶端
        
        Args:
            page_id: Facebook 粉絲專頁 ID
            access_token: Page Access Token
        """
        self.page_id = page_id
        self.access_token = access_token
        self.session = requests.Session()
    
    def post(self, message, image_url=None, link=None):
        """
        發布貼文
        
        Args:
            message: 貼文內容
            image_url: 圖片網址（選填）
            link: 連結（選填）
        
        Returns:
            API 回應
        """
        if image_url:
            # 發布含圖片的貼文
            return self._post_with_image(message, image_url)
        else:
            # 發布純文字貼文
            return self._post_text(message, link)
    
    def _post_text(self, message, link=None):
        """發布純文字貼文"""
        url = f"{self.BASE_URL}/{self.page_id}/feed"
        
        data = {
            'message': message,
            'access_token': self.access_token
        }
        
        if link:
            data['link'] = link
        
        response = self.session.post(url, data=data)
        response.raise_for_status()
        return response.json()
    
    def _post_with_image(self, message, image_url):
        """發布含圖片的貼文"""
        url = f"{self.BASE_URL}/{self.page_id}/photos"
        
        data = {
            'caption': message,
            'url': image_url,
            'access_token': self.access_token
        }
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Facebook API 錯誤: {error_detail}")
        return response.json()
    
    def get_page_info(self):
        """取得粉專資訊"""
        url = f"{self.BASE_URL}/{self.page_id}"
        params = {
            'fields': 'name,fan_count,link',
            'access_token': self.access_token
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def post_multiple_photos(self, message, image_urls):
        """
        發布多張圖片的貼文
        
        Args:
            message: 貼文內容
            image_urls: 圖片網址列表
        
        Returns:
            API 回應
        """
        # Step 1: 上傳每張圖片（unpublished）
        photo_ids = []
        for img_url in image_urls[:10]:  # FB 最多 10 張
            url = f"{self.BASE_URL}/{self.page_id}/photos"
            data = {
                'url': img_url,
                'published': 'false',
                'access_token': self.access_token
            }
            response = self.session.post(url, data=data)
            if not response.ok:
                error_detail = response.json() if response.text else response.text
                raise Exception(f"Facebook 上傳圖片錯誤: {error_detail}")
            photo_ids.append(response.json()['id'])
        
        # Step 2: 建立貼文並附加所有圖片
        url = f"{self.BASE_URL}/{self.page_id}/feed"
        data = {
            'message': message,
            'access_token': self.access_token
        }
        # 附加圖片 ID
        for i, photo_id in enumerate(photo_ids):
            data[f'attached_media[{i}]'] = f'{{"media_fbid":"{photo_id}"}}'
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Facebook API 錯誤: {error_detail}")
        return response.json()


class InstagramClient:
    """Instagram Graph API 客戶端"""
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, account_id, access_token):
        """
        初始化 Instagram 客戶端
        
        Args:
            account_id: Instagram Business Account ID
            access_token: Access Token (與 Facebook 共用)
        """
        self.account_id = account_id
        self.access_token = access_token
        self.session = requests.Session()
    
    def post(self, caption, image_url):
        """
        發布貼文 (Instagram 必須有圖片)
        
        Args:
            caption: 貼文內容
            image_url: 圖片網址 (必須是公開可存取的 URL)
        
        Returns:
            API 回應
        """
        # Step 1: 建立媒體容器
        container_id = self._create_container(image_url, caption)
        
        # Step 2: 等待處理完成
        self._wait_for_container(container_id)
        
        # Step 3: 發布
        return self._publish_container(container_id)
    
    def _create_container(self, image_url, caption):
        """建立媒體容器"""
        url = f"{self.BASE_URL}/{self.account_id}/media"
        
        data = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Instagram API 錯誤: {error_detail}")
        result = response.json()
        return result['id']
    
    def _wait_for_container(self, container_id, max_wait=60):
        """等待容器處理完成"""
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            'fields': 'status_code',
            'access_token': self.access_token
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = self.session.get(url, params=params)
            data = response.json()
            
            status = data.get('status_code')
            if status == 'FINISHED':
                return True
            elif status == 'ERROR':
                raise Exception(f"Instagram 媒體處理失敗")
            
            time.sleep(2)
        
        raise Exception("Instagram 媒體處理超時")
    
    def _publish_container(self, container_id):
        """發布容器"""
        url = f"{self.BASE_URL}/{self.account_id}/media_publish"
        
        data = {
            'creation_id': container_id,
            'access_token': self.access_token
        }
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Instagram 發布錯誤: {error_detail}")
        return response.json()
    
    def post_carousel(self, caption, image_urls):
        """
        發布輪播貼文 (多張圖片)
        
        Args:
            caption: 貼文內容
            image_urls: 圖片網址列表 (2-10 張)
        
        Returns:
            API 回應
        """
        if len(image_urls) < 2:
            # 只有一張圖，用普通貼文
            return self.post(caption, image_urls[0])
        
        if len(image_urls) > 10:
            image_urls = image_urls[:10]  # IG 輪播最多 10 張
        
        # 建立各個子容器
        children_ids = []
        for img_url in image_urls:
            url = f"{self.BASE_URL}/{self.account_id}/media"
            data = {
                'image_url': img_url,
                'is_carousel_item': 'true',
                'access_token': self.access_token
            }
            response = self.session.post(url, data=data)
            if not response.ok:
                error_detail = response.json() if response.text else response.text
                raise Exception(f"Instagram 輪播子項目錯誤: {error_detail}")
            children_ids.append(response.json()['id'])
        
        # 建立輪播容器
        url = f"{self.BASE_URL}/{self.account_id}/media"
        data = {
            'media_type': 'CAROUSEL',
            'caption': caption,
            'children': ','.join(children_ids),
            'access_token': self.access_token
        }
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Instagram 輪播容器錯誤: {error_detail}")
        carousel_id = response.json()['id']
        
        # 等待並發布
        self._wait_for_container(carousel_id)
        return self._publish_container(carousel_id)


class ThreadsClient:
    """Threads API 客戶端"""
    
    BASE_URL = "https://graph.threads.net/v1.0"
    
    def __init__(self, user_id, access_token):
        """
        初始化 Threads 客戶端
        
        Args:
            user_id: Threads User ID
            access_token: Threads Access Token
        """
        self.user_id = user_id
        self.access_token = access_token
        self.session = requests.Session()
    
    def post(self, text, image_url=None, link_attachment=None):
        """
        發布貼文
        
        Args:
            text: 貼文內容
            image_url: 圖片網址（選填）
            link_attachment: 連結（選填）
        
        Returns:
            API 回應
        """
        # Step 1: 建立容器
        container_id = self._create_container(text, image_url, link_attachment)
        
        # Step 2: 等待處理
        self._wait_for_container(container_id)
        
        # Step 3: 發布
        return self._publish(container_id)
    
    def _create_container(self, text, image_url=None, link_attachment=None):
        """建立貼文容器"""
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        
        data = {
            'text': text,
            'access_token': self.access_token
        }
        
        if image_url:
            data['media_type'] = 'IMAGE'
            data['image_url'] = image_url
        else:
            data['media_type'] = 'TEXT'
        
        if link_attachment:
            data['link_attachment'] = link_attachment
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Threads API 錯誤: {error_detail}")
        return response.json()['id']
    
    def _wait_for_container(self, container_id, max_wait=60):
        """等待容器處理完成"""
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            'fields': 'status',
            'access_token': self.access_token
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = self.session.get(url, params=params)
            data = response.json()
            
            status = data.get('status')
            if status == 'FINISHED':
                return True
            elif status == 'ERROR':
                raise Exception("Threads 媒體處理失敗")
            
            time.sleep(2)
        
        raise Exception("Threads 媒體處理超時")
    
    def _publish(self, container_id):
        """發布貼文"""
        url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
        
        data = {
            'creation_id': container_id,
            'access_token': self.access_token
        }
        
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Threads 發布錯誤: {error_detail}")
        return response.json()
    
    def post_carousel(self, text, image_urls):
        """
        發布輪播貼文 (多張圖片)
        
        Args:
            text: 貼文內容
            image_urls: 圖片網址列表 (最多 20 張)
        
        Returns:
            API 回應
        """
        if len(image_urls) < 2:
            # 只有一張圖，用普通貼文
            return self.post(text=text, image_url=image_urls[0] if image_urls else None)
        
        if len(image_urls) > 20:
            image_urls = image_urls[:20]  # Threads 輪播最多 20 張
        
        # Step 1: 建立各個子容器
        children_ids = []
        for img_url in image_urls:
            url = f"{self.BASE_URL}/{self.user_id}/threads"
            data = {
                'media_type': 'IMAGE',
                'image_url': img_url,
                'is_carousel_item': 'true',
                'access_token': self.access_token
            }
            response = self.session.post(url, data=data)
            if not response.ok:
                error_detail = response.json() if response.text else response.text
                raise Exception(f"Threads 輪播子項目錯誤: {error_detail}")
            children_ids.append(response.json()['id'])
        
        # Step 2: 建立輪播容器
        url = f"{self.BASE_URL}/{self.user_id}/threads"
        data = {
            'media_type': 'CAROUSEL',
            'text': text,
            'children': ','.join(children_ids),
            'access_token': self.access_token
        }
        response = self.session.post(url, data=data)
        if not response.ok:
            error_detail = response.json() if response.text else response.text
            raise Exception(f"Threads 輪播容器錯誤: {error_detail}")
        carousel_id = response.json()['id']
        
        # Step 3: 等待處理完成
        self._wait_for_container(carousel_id)
        
        # Step 4: 發布
        return self._publish(carousel_id)
    
    def get_user_profile(self):
        """取得用戶資訊"""
        url = f"{self.BASE_URL}/{self.user_id}"
        params = {
            'fields': 'username,threads_profile_picture_url,threads_biography',
            'access_token': self.access_token
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()


# 測試函數
def test_clients():
    """測試各客戶端（需要有效的 API 金鑰）"""
    print("請在 config.py 中設定 API 金鑰後進行測試")


if __name__ == '__main__':
    test_clients()
