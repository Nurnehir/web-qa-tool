"""
Sayfa kaydetme modülü.

Cloudflare API'den gelen sayfa verilerini
output/pages/ klasörüne JSON formatında kaydeder.
"""

import json
import os
from typing import List, Dict, Any
from markdownify import markdownify as md


class PageSaver:
    """
    Taranan sayfaları JSON dosyası olarak kaydeden sınıf.
    
    Attributes:
        output_dir (str): Sayfa JSON dosyalarının kaydedileceği klasör
    """
    
    def __init__(self, output_dir: str = "output/pages"):
        """
        PageSaver sınıfını başlatır.
        
        Args:
            output_dir: Çıktı klasörü yolu
        """
        self.output_dir = output_dir
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
        
        return {
            "url": page.get("url", metadata.get("url", "")),
            "html": html_content,
            "markdown": markdown_content,
            "status_code": metadata.get("status", page.get("statusCode", 200)),
            "headers": page.get("headers", {}),
            "title": metadata.get("title", ""),
            "last_modified": metadata.get("lastModified", "")
        }
    
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
