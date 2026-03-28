"""
Kırık Link Tespit Modülü

Sayfadaki tüm linkleri kontrol ederek
erişilemeyen veya hata dönen linkleri tespit eder.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set
from urllib.parse import urljoin, urlparse
import asyncio


class LinkChecker:
    """
    Sayfa içindeki linkleri kontrol eden sınıf.
    
    Tüm <a href>, <img src>, <link href>, <script src>
    elementlerini tarar ve erişilebilirliklerini test eder.
    """
    
    # Kontrol edilecek element ve attribute çiftleri
    LINK_SELECTORS = [
        ("a", "href"),
        ("img", "src"),
        ("link", "href"),
        ("script", "src"),
        ("iframe", "src"),
        ("video", "src"),
        ("audio", "src"),
        ("source", "src")
    ]
    
    # Atlanacak protokoller
    SKIP_PROTOCOLS = ["mailto:", "tel:", "javascript:", "data:", "#"]
    
    def __init__(self, timeout: float = 5.0, max_concurrent: int = 10):
        """
        LinkChecker sınıfını başlatır.
        
        Args:
            timeout: Her link için zaman aşımı (saniye)
            max_concurrent: Eşzamanlı istek sayısı
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
    
    def check(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Sayfa HTML'indeki tüm linkleri kontrol eder.
        
        Args:
            url: Sayfa URL'si (göreceli linkleri çözmek için)
            html_content: Sayfa HTML içeriği
            
        Returns:
            Link analiz sonucu
        """
        result = {
            "url": url,
            "total_links": 0,
            "checked_links": 0,
            "broken_links": [],
            "working_links": [],
            "skipped_links": [],
            "error": None
        }
        
        if not html_content:
            result["error"] = "HTML içeriği boş"
            return result
        
        # Linkleri çıkar
        links = self._extract_links(url, html_content)
        result["total_links"] = len(links["all"])
        result["skipped_links"] = links["skipped"]
        
        # Kontrol edilecek linkleri filtrele
        links_to_check = links["to_check"]
        
        if not links_to_check:
            return result
        
        # Linkleri kontrol et
        print(f"[LINK_CHECKER] {len(links_to_check)} link kontrol ediliyor...")
        checked = self._check_links_sync(links_to_check)
        
        result["checked_links"] = len(checked)
        
        for link_result in checked:
            if link_result["is_broken"]:
                result["broken_links"].append(link_result)
            else:
                result["working_links"].append({
                    "url": link_result["url"],
                    "status_code": link_result["status_code"]
                })
        
        return result
    
    def _extract_links(self, base_url: str, html_content: str) -> Dict[str, List]:
        """
        HTML içeriğinden tüm linkleri çıkarır.
        
        Args:
            base_url: Baz URL (göreceli linkleri çözmek için)
            html_content: HTML içeriği
            
        Returns:
            Kategorize edilmiş linkler
        """
        result = {
            "all": [],
            "to_check": [],
            "skipped": []
        }
        
        seen_urls: Set[str] = set()
        
        try:
            soup = BeautifulSoup(html_content, "lxml")
            
            for tag_name, attr_name in self.LINK_SELECTORS:
                for element in soup.find_all(tag_name):
                    link = element.get(attr_name)
                    
                    if not link:
                        continue
                    
                    # Boşlukları temizle
                    link = link.strip()
                    
                    if not link:
                        continue
                    
                    # Atlanacak protokolleri kontrol et
                    should_skip = False
                    for protocol in self.SKIP_PROTOCOLS:
                        if link.startswith(protocol):
                            should_skip = True
                            result["skipped"].append({
                                "url": link,
                                "reason": f"{protocol} protokolü atlandı"
                            })
                            break
                    
                    if should_skip:
                        continue
                    
                    # Göreceli URL'yi mutlak URL'ye çevir
                    absolute_url = urljoin(base_url, link)
                    
                    # Tekrarları atla
                    if absolute_url in seen_urls:
                        continue
                    
                    seen_urls.add(absolute_url)
                    result["all"].append({
                        "url": absolute_url,
                        "tag": tag_name,
                        "original": link
                    })
                    
                    # Sadece HTTP/HTTPS linklerini kontrol et
                    parsed = urlparse(absolute_url)
                    if parsed.scheme in ["http", "https"]:
                        result["to_check"].append(absolute_url)
                    else:
                        result["skipped"].append({
                            "url": absolute_url,
                            "reason": f"Desteklenmeyen protokol: {parsed.scheme}"
                        })
            
        except Exception as e:
            print(f"[LINK_CHECKER] HTML parse hatası: {str(e)}")
        
        return result
    
    def _check_links_sync(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Linkleri senkron olarak kontrol eder.
        
        Args:
            urls: Kontrol edilecek URL listesi
            
        Returns:
            Kontrol sonuçları
        """
        results = []
        
        # User-Agent ekleyerek bot korumasını aşmaya çalış
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            for url in urls:
                result = self._check_single_link(client, url)
                results.append(result)
        
        return results
    
    def _check_single_link(self, client: httpx.Client, url: str) -> Dict[str, Any]:
        """
        Tek bir linki kontrol eder.
        
        Args:
            client: HTTP istemcisi
            url: Kontrol edilecek URL
            
        Returns:
            Link kontrol sonucu
        """
        result = {
            "url": url,
            "status_code": None,
            "is_broken": False,
            "error": None
        }
        
        try:
            # Önce HEAD dene (daha hızlı)
            response = client.head(url)
            result["status_code"] = response.status_code
            
            # HEAD 405/403 dönerse GET ile tekrar dene
            if response.status_code in [403, 405]:
                try:
                    response = client.get(url)
                    result["status_code"] = response.status_code
                except:
                    pass  # HEAD sonucunu kullan
            
            # Sadece gerçek hatalar için kırık işaretle
            # 2xx ve 3xx başarılı sayılır
            if response.status_code >= 400:
                result["is_broken"] = True
                result["error"] = f"HTTP {response.status_code}"
                
        except httpx.TimeoutException:
            result["is_broken"] = True
            result["error"] = "Zaman aşımı"
        except httpx.ConnectError:
            result["is_broken"] = True
            result["error"] = "Bağlantı hatası"
        except httpx.TooManyRedirects:
            result["is_broken"] = True
            result["error"] = "Çok fazla yönlendirme"
        except Exception as e:
            result["is_broken"] = True
            result["error"] = str(e)[:100]
        
        return result
    
    def get_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Link kontrolü özeti üretir.
        
        Args:
            result: check() metodunun döndürdüğü sonuç
            
        Returns:
            Özet bilgiler
        """
        broken_count = len(result.get("broken_links", []))
        total = result.get("total_links", 0)
        checked = result.get("checked_links", 0)
        
        return {
            "total_links": total,
            "checked": checked,
            "broken": broken_count,
            "working": checked - broken_count,
            "skipped": len(result.get("skipped_links", [])),
            "health_percentage": round(((checked - broken_count) / checked * 100), 1) if checked > 0 else 100
        }
