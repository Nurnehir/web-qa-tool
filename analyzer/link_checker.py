"""
Kırık Link Tespit Modülü

Sayfadaki tüm linkleri kontrol ederek
erişilemeyen veya hata dönen linkleri tespit eder.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set
from urllib.parse import urljoin, urlparse
import re
import time


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
    
    def __init__(
        self,
        timeout: float = 5.0,
        max_concurrent: int = 10,
        max_retries: int = 2,
        max_links_per_page: int = 0,
        check_asset_links: bool = True,
        verbose: bool = True
    ):
        """
        LinkChecker sınıfını başlatır.
        
        Args:
            timeout: Her link için zaman aşımı (saniye)
            max_concurrent: Eşzamanlı istek sayısı
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.max_links_per_page = max_links_per_page
        self.check_asset_links = check_asset_links
        self.verbose = verbose
    
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
        if self.max_links_per_page and len(links_to_check) > self.max_links_per_page:
            overflow = links_to_check[self.max_links_per_page:]
            links_to_check = links_to_check[:self.max_links_per_page]
            result["skipped_links"].extend(
                {"url": u, "reason": "max_links_per_page limiti"} for u in overflow
            )
        
        if not links_to_check:
            return result
        
        # Linkleri kontrol et
        if self.verbose:
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
            
            selectors = self.LINK_SELECTORS if self.check_asset_links else [("a", "href")]
            for tag_name, attr_name in selectors:
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
                    absolute_url = self._normalize_url(absolute_url)
                    if not absolute_url:
                        result["skipped"].append({
                            "url": link,
                            "reason": "Geçersiz URL"
                        })
                        continue
                    
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

    def _normalize_url(self, raw_url: str) -> str:
        """
        URL'yi canonical forma yakınlaştırır.

        - fragment kaldırılır
        - path içindeki çoklu slash'lar tek slash'a düşürülür
        - scheme ve host normalize edilir
        """
        try:
            parsed = urlparse(raw_url)
            if not parsed.scheme or not parsed.netloc:
                return ""

            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()

            path = parsed.path or "/"
            path = re.sub(r"/{2,}", "/", path)
            if not path.startswith("/"):
                path = "/" + path

            query = parsed.query
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            return normalized
        except Exception:
            return ""
    
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
            "error": None,
            "category": "unknown",
            "attempts": 0
        }
        
        for attempt in range(1, self.max_retries + 2):
            result["attempts"] = attempt
            try:
                # Önce HEAD dene (daha hızlı)
                response = client.head(url)
                result["status_code"] = response.status_code

                # HEAD 405/403 dönerse GET ile tekrar dene
                if response.status_code in [403, 405]:
                    try:
                        response = client.get(url)
                        result["status_code"] = response.status_code
                    except Exception:
                        pass  # HEAD sonucunu kullan

                status = response.status_code
                if status < 400:
                    result["is_broken"] = False
                    result["category"] = "ok"
                    return result

                if status in (404, 410):
                    result["is_broken"] = True
                    result["category"] = "broken_strict"
                    result["error"] = f"HTTP {status}"
                    return result

                if status == 429:
                    result["is_broken"] = True
                    result["category"] = "rate_limited"
                    result["error"] = "HTTP 429"
                    if attempt <= self.max_retries:
                        time.sleep(0.4 * attempt)
                        continue
                    return result

                if 500 <= status < 600:
                    result["is_broken"] = True
                    result["category"] = "server_error"
                    result["error"] = f"HTTP {status}"
                    if attempt <= self.max_retries:
                        time.sleep(0.4 * attempt)
                        continue
                    return result

                # Diğer 4xx hataları
                result["is_broken"] = True
                result["category"] = "client_error"
                result["error"] = f"HTTP {status}"
                return result

            except httpx.TimeoutException:
                result["is_broken"] = True
                result["category"] = "transient_network"
                result["error"] = "Zaman aşımı"
                if attempt <= self.max_retries:
                    time.sleep(0.4 * attempt)
                    continue
                return result
            except httpx.ConnectError:
                result["is_broken"] = True
                result["category"] = "transient_network"
                result["error"] = "Bağlantı hatası"
                if attempt <= self.max_retries:
                    time.sleep(0.4 * attempt)
                    continue
                return result
            except httpx.TooManyRedirects:
                result["is_broken"] = True
                result["category"] = "client_error"
                result["error"] = "Çok fazla yönlendirme"
                return result
            except Exception as e:
                result["is_broken"] = True
                result["category"] = "unknown"
                result["error"] = str(e)[:100]
                if attempt <= self.max_retries:
                    time.sleep(0.4 * attempt)
                    continue
                return result
        
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

        broken_links = result.get("broken_links", [])
        strict_broken = sum(1 for item in broken_links if item.get("category") == "broken_strict")
        server_errors = sum(1 for item in broken_links if item.get("category") == "server_error")
        rate_limited = sum(1 for item in broken_links if item.get("category") == "rate_limited")
        transient = sum(1 for item in broken_links if item.get("category") == "transient_network")
        client_other = sum(1 for item in broken_links if item.get("category") == "client_error")
        unknown = sum(1 for item in broken_links if item.get("category") == "unknown")
        
        return {
            "total_links": total,
            "checked": checked,
            "broken": broken_count,
            "broken_strict": strict_broken,
            "server_error": server_errors,
            "rate_limited": rate_limited,
            "transient_network": transient,
            "client_error": client_other,
            "unknown_error": unknown,
            "working": checked - broken_count,
            "skipped": len(result.get("skipped_links", [])),
            "health_percentage": round(((checked - broken_count) / checked * 100), 1) if checked > 0 else 100,
            "strict_health_percentage": round(((checked - strict_broken) / checked * 100), 1) if checked > 0 else 100
        }
