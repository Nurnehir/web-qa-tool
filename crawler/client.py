"""
Cloudflare Browser Rendering API istemcisi.

Bu modül Cloudflare /crawl API'ye POST isteği atarak
hedef sitenin tüm sayfalarını tarar.
"""

import httpx
import time
from typing import Optional


class CloudflareCrawler:
    """
    Cloudflare Browser Rendering API ile web sitelerini tarayan sınıf.
    
    Cloudflare crawl API asenkron çalışır:
    1. POST ile crawl işi başlatılır, task_id döner
    2. GET ile task_id kullanarak sonuç alınır
    
    Attributes:
        token (str): Cloudflare API token
        account_id (str): Cloudflare hesap ID'si
        base_url (str): API endpoint base URL
    """
    
    def __init__(self, token: str, account_id: str):
        """
        CloudflareCrawler sınıfını başlatır.
        
        Args:
            token: Cloudflare API token
            account_id: Cloudflare hesap ID'si
        """
        self.token = token
        self.account_id = account_id
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"
    
    def crawl(self, target_url: str, max_pages: int = 50) -> Optional[dict]:
        """
        Hedef URL'yi tarar ve tüm sayfaları döner.
        
        Args:
            target_url: Taranacak web sitesinin URL'si
            max_pages: Taranacak maksimum sayfa sayısı
            
        Returns:
            Sayfa verileri içeren dict veya hata durumunda None
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Adım 1: Crawl işini başlat
        task_id = self._start_crawl(target_url, max_pages, headers)
        if not task_id:
            return None
        
        # Adım 2: Sonucu bekle ve al
        result = self._get_crawl_result(task_id, headers)
        return result
    
    def _start_crawl(self, target_url: str, max_pages: int, headers: dict) -> Optional[str]:
        """
        Crawl işini başlatır ve task_id döner.
        
        Args:
            target_url: Taranacak URL
            max_pages: Maksimum sayfa sayısı
            headers: HTTP başlıkları
            
        Returns:
            Task ID veya None
        """
        # Dokümantasyona göre tam payload
        payload = {
            "url": target_url,
            "limit": max_pages,
            "depth": 3,
            "formats": ["html", "markdown"],
            "render": True,
            "options": {
                "includeSubdomains": False,
                "includeExternalLinks": False
            }
        }
        
        try:
            print(f"[CRAWLER] Tarama başlatılıyor: {target_url}")
            print(f"[CRAWLER] Maksimum sayfa: {max_pages}, Derinlik: 3")
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/crawl",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        task_id = data.get("result")
                        print(f"[CRAWLER] Crawl işi başlatıldı. Task ID: {task_id}")
                        return task_id
                    else:
                        errors = data.get("errors", [])
                        print(f"[CRAWLER] API hatası: {errors}")
                        return None
                else:
                    print(f"[CRAWLER] HTTP hatası: {response.status_code}")
                    print(f"[CRAWLER] Yanıt: {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            print("[CRAWLER] HATA: İstek zaman aşımına uğradı.")
            return None
        except httpx.ConnectError:
            print("[CRAWLER] HATA: Bağlantı kurulamadı.")
            return None
        except Exception as e:
            print(f"[CRAWLER] Beklenmeyen hata: {str(e)}")
            return None
    
    def _get_crawl_result(self, task_id: str, headers: dict, max_attempts: int = 60, wait_seconds: int = 5) -> Optional[dict]:
        """
        Crawl sonucunu alır. İş tamamlanana kadar bekler.
        
        Args:
            task_id: Crawl iş ID'si
            headers: HTTP başlıkları
            max_attempts: Maksimum deneme sayısı
            wait_seconds: Denemeler arası bekleme süresi (saniye)
            
        Returns:
            Crawl sonucu veya None
        """
        print(f"[CRAWLER] Sonuç bekleniyor (maks {max_attempts * wait_seconds} saniye)...")
        
        try:
            with httpx.Client(timeout=60.0) as client:
                for attempt in range(1, max_attempts + 1):
                    # İlk sorgularda limit=1 ile hafif sorgu yap (dokümantasyon önerisi)
                    check_url = f"{self.base_url}/crawl/{task_id}"
                    if attempt < max_attempts - 5:
                        check_url += "?limit=1"
                    
                    response = client.get(check_url, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            result = data.get("result", {})
                            status = result.get("status", "")
                            
                            # Terminal durumları kontrol et
                            if status == "completed":
                                # Son sorgu - tüm verileri al
                                if "?limit=1" in check_url:
                                    full_response = client.get(
                                        f"{self.base_url}/crawl/{task_id}",
                                        headers=headers
                                    )
                                    if full_response.status_code == 200:
                                        full_data = full_response.json()
                                        result = full_data.get("result", {})
                                
                                records = result.get("records", [])
                                print(f"[CRAWLER] Tarama tamamlandı! {len(records)} sayfa bulundu.")
                                # records'u pages olarak da ekle (uyumluluk için)
                                result["pages"] = records
                                return result
                                
                            elif status in ["errored", "cancelled_due_to_timeout", 
                                           "cancelled_due_to_limits", "cancelled_by_user"]:
                                print(f"[CRAWLER] Tarama başarısız: {status}")
                                return None
                                
                            elif status == "running":
                                # Progress bilgisi varsa göster
                                total = result.get("total", 0)
                                finished = result.get("finished", 0)
                                print(f"[CRAWLER] İşleniyor... {finished}/{total} sayfa (deneme {attempt}/{max_attempts})")
                                time.sleep(wait_seconds)
                            else:
                                print(f"[CRAWLER] Bilinmeyen durum: {status}, bekleniyor...")
                                time.sleep(wait_seconds)
                        else:
                            errors = data.get("errors", [])
                            print(f"[CRAWLER] API hatası: {errors}")
                            return None
                    elif response.status_code == 404:
                        print(f"[CRAWLER] Task henüz hazır değil, bekleniyor... (deneme {attempt}/{max_attempts})")
                        time.sleep(wait_seconds)
                    else:
                        print(f"[CRAWLER] HTTP hatası: {response.status_code}")
                        return None
                
                print("[CRAWLER] HATA: Maksimum bekleme süresi aşıldı.")
                return None
                
        except Exception as e:
            print(f"[CRAWLER] Sonuç alınırken hata: {str(e)}")
            return None
    
    def _extract_domain(self, url: str) -> str:
        """
        URL'den domain adını çıkarır.
        
        Args:
            url: Tam URL
            
        Returns:
            Domain adı (örn: example.com)
        """
        url = url.replace("https://", "").replace("http://", "")
        domain = url.split("/")[0]
        return domain
