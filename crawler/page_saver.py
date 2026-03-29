"""
Sayfa kaydetme modülü.

Cloudflare API'den gelen sayfa verilerini
output/pages/ klasörüne JSON formatında kaydeder.
"""

import json
import os
from typing import List, Dict, Any
from markdownify import markdownify as md
import httpx
import re


class PageSaver:
    """
    Taranan sayfaları JSON dosyası olarak kaydeden sınıf.
    
    Attributes:
        output_dir (str): Sayfa JSON dosyalarının kaydedileceği klasör
    """
    
    def __init__(
        self,
        output_dir: str = "output/pages",
        fallback_fetch_skipped: bool = True,
        fallback_timeout: float = 15.0
    ):
        """
        PageSaver sınıfını başlatır.
        
        Args:
            output_dir: Çıktı klasörü yolu
        """
        self.output_dir = output_dir
        self.fallback_fetch_skipped = fallback_fetch_skipped
        self.fallback_timeout = fallback_timeout
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Çıktı klasörünün var olduğundan emin olur."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"[PAGE_SAVER] Klasör oluşturuldu: {self.output_dir}")
    
    def save_pages(self, crawl_result: dict) -> List[str]:
        """
        Crawl sonucundaki tüm sayfaları ayrı JSON dosyalarına kaydeder.
        
        Args:
            crawl_result: Cloudflare API'den dönen crawl sonucu
            
        Returns:
            Kaydedilen dosya yollarının listesi
        """
        saved_files = []
        # API "records" veya "pages" döndürebilir
        pages = crawl_result.get("pages", crawl_result.get("records", []))
        
        if not pages:
            print("[PAGE_SAVER] UYARI: Kaydedilecek sayfa bulunamadı.")
            return saved_files
        
        print(f"[PAGE_SAVER] {len(pages)} sayfa kaydediliyor...")
        
        for index, page in enumerate(pages, start=1):
            try:
                page_data = self._format_page_data(page)
                file_path = self._save_single_page(page_data, index)
                saved_files.append(file_path)
                print(f"[PAGE_SAVER] Kaydedildi: {file_path}")
            except Exception as e:
                print(f"[PAGE_SAVER] HATA: Sayfa {index} kaydedilemedi - {str(e)}")
        
        print(f"[PAGE_SAVER] Toplam {len(saved_files)} sayfa başarıyla kaydedildi.")
        return saved_files
    
    def _format_page_data(self, page: dict) -> Dict[str, Any]:
        """
        Sayfa verisini standart formata dönüştürür.
        
        API'den markdown gelirse kullanır, yoksa HTML'den oluşturur.
        
        Args:
            page: Ham sayfa verisi
            
        Returns:
            Formatlanmış sayfa verisi
        """
        html_content = page.get("html", "")
        markdown_content = page.get("markdown", "")
        
        # API markdown döndürmediyse HTML'den oluştur
        if not markdown_content and html_content:
            try:
                markdown_content = md(html_content, heading_style="ATX", strip=['script', 'style'])
            except Exception as e:
                print(f"[PAGE_SAVER] UYARI: Markdown dönüşümü başarısız - {str(e)}")
                markdown_content = ""
        
        # Metadata varsa kullan
        metadata = page.get("metadata", {})
        raw_headers = page.get("headers", {})
        status_code = metadata.get("status", page.get("statusCode", 200))

        # Cloudflare kaydı skipped/no-html ise düz HTTP fallback dene.
        if (
            self.fallback_fetch_skipped
            and not html_content
            and page.get("status") == "skipped"
            and page.get("url")
        ):
            fallback = self._fallback_fetch_page(page.get("url"))
            if fallback.get("html"):
                html_content = fallback.get("html", "")
                raw_headers = fallback.get("headers", {}) or raw_headers
                status_code = fallback.get("status_code", status_code)
                if not metadata.get("title") and fallback.get("title"):
                    metadata["title"] = fallback.get("title")
                if not metadata.get("lastModified") and fallback.get("last_modified"):
                    metadata["lastModified"] = fallback.get("last_modified")
                if fallback.get("content_type"):
                    metadata["contentType"] = fallback.get("content_type")
                # markdown fallback üret
                if not markdown_content:
                    try:
                        markdown_content = md(html_content, heading_style="ATX", strip=['script', 'style'])
                    except Exception:
                        markdown_content = ""
                # fallback ile veri alındıysa crawl status'u overridden olarak işaretle
                page["status"] = "fallback_completed"

        no_html_reason = self._infer_no_html_reason(page, metadata, status_code, html_content)
        headers_source = "from_crawl_record" if raw_headers else "missing"
        if page.get("status") == "fallback_completed" and raw_headers:
            headers_source = "fetched_later"
        
        return {
            "url": page.get("url", metadata.get("url", "")),
            "html": html_content,
            "markdown": markdown_content,
            "status_code": status_code,
            "headers": raw_headers,
            "headers_source": headers_source,
            "title": metadata.get("title", ""),
            "last_modified": metadata.get("lastModified", ""),
            "content_type": metadata.get("contentType") or raw_headers.get("content-type"),
            "crawl_record_status": page.get("status"),
            "crawl_record_error": page.get("error"),
            "crawl_record_reason": page.get("reason"),
            "no_html_reason": no_html_reason,
            "crawl_metadata": metadata
        }

    def _fallback_fetch_page(self, url: str) -> Dict[str, Any]:
        """Cloudflare skipped kayıtları için doğrudan HTTP GET fallback."""
        result = {
            "html": "",
            "headers": {},
            "status_code": None,
            "title": "",
            "last_modified": "",
            "content_type": ""
        }
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
            with httpx.Client(timeout=self.fallback_timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
            text = response.text or ""
            content_type = response.headers.get("content-type", "")
            if text and ("html" in content_type.lower() or "<html" in text.lower()):
                result["html"] = text
            result["headers"] = dict(response.headers)
            result["status_code"] = response.status_code
            result["content_type"] = content_type
            result["last_modified"] = response.headers.get("last-modified", "")
            result["title"] = self._extract_title(text)
        except Exception:
            return result
        return result

    def _extract_title(self, html: str) -> str:
        """Basit regex ile title çıkarır."""
        if not html:
            return ""
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()[:200]

    def _infer_no_html_reason(
        self,
        page: Dict[str, Any],
        metadata: Dict[str, Any],
        status_code: int,
        html_content: str
    ) -> str:
        """HTML içeriği olmayan kayıtlar için olası nedeni üretir."""
        if html_content:
            return ""

        if page.get("error"):
            return f"crawl_error:{page.get('error')}"

        content_type = metadata.get("contentType", "")
        if content_type and "html" not in content_type.lower():
            return f"non_html_content_type:{content_type}"

        if status_code >= 400:
            return f"http_status:{status_code}"

        if page.get("status"):
            return f"record_status:{page.get('status')}"

        return "html_missing_unknown"
    
    def _save_single_page(self, page_data: Dict[str, Any], index: int) -> str:
        """
        Tek bir sayfayı JSON dosyasına kaydeder.
        
        Args:
            page_data: Sayfa verisi
            index: Sayfa indeksi (dosya adı için)
            
        Returns:
            Kaydedilen dosyanın yolu
        """
        # Dosya adı formatı: page_001.json, page_002.json, ...
        file_name = f"page_{index:03d}.json"
        file_path = os.path.join(self.output_dir, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def clear_output(self) -> None:
        """Çıktı klasöründeki tüm JSON dosyalarını temizler."""
        try:
            for file_name in os.listdir(self.output_dir):
                if file_name.endswith(".json"):
                    file_path = os.path.join(self.output_dir, file_name)
                    os.remove(file_path)
            print(f"[PAGE_SAVER] Çıktı klasörü temizlendi: {self.output_dir}")
        except Exception as e:
            print(f"[PAGE_SAVER] HATA: Klasör temizlenemedi - {str(e)}")
    
    def get_saved_pages(self) -> List[str]:
        """
        Kaydedilmiş sayfa dosyalarının listesini döner.
        
        Returns:
            Dosya yollarının sıralı listesi
        """
        try:
            files = [
                os.path.join(self.output_dir, f)
                for f in os.listdir(self.output_dir)
                if f.endswith(".json") and f.startswith("page_")
            ]
            return sorted(files)
        except Exception as e:
            print(f"[PAGE_SAVER] HATA: Dosya listesi alınamadı - {str(e)}")
            return []
