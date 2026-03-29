"""
Analyzer Runner - Analiz Orkestratörü

Tüm checker modüllerini çalıştırır ve sonuçları birleştirir.
Her sayfa için analiz JSON dosyası üretir.
"""

import json
import os
from typing import Dict, Any, List
from .header_checker import HeaderChecker
from .link_checker import LinkChecker
from .seo_checker import SEOChecker


class AnalyzerRunner:
    """
    Tüm analiz modüllerini orkestre eden sınıf.
    
    Her sayfa için header, link ve SEO analizlerini çalıştırır,
    sonuçları birleştirip output/analysis/ klasörüne kaydeder.
    """
    
    def __init__(self, pages_dir: str = "output/pages", analysis_dir: str = "output/analysis"):
        """
        AnalyzerRunner sınıfını başlatır.
        
        Args:
            pages_dir: Sayfa JSON dosyalarının bulunduğu klasör
            analysis_dir: Analiz sonuçlarının kaydedileceği klasör
        """
        self.pages_dir = pages_dir
        self.analysis_dir = analysis_dir
        
        # Checker'ları başlat
        self.header_checker = HeaderChecker()
        self.link_checker = LinkChecker()
        self.seo_checker = SEOChecker()
        
        # Çıktı klasörünü oluştur
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Çıktı klasörünün var olduğundan emin olur."""
        if not os.path.exists(self.analysis_dir):
            os.makedirs(self.analysis_dir)
            print(f"[ANALYZER] Klasör oluşturuldu: {self.analysis_dir}")
    
    def run(self) -> List[str]:
        """
        Tüm sayfa dosyaları için analiz çalıştırır.
        
        Returns:
            Oluşturulan analiz dosyalarının listesi
        """
        saved_files = []
        page_files = self._get_page_files()
        
        if not page_files:
            print("[ANALYZER] UYARI: Analiz edilecek sayfa bulunamadı.")
            return saved_files
        
        print(f"[ANALYZER] {len(page_files)} sayfa analiz edilecek...")
        print("=" * 50)
        
        for index, page_file in enumerate(page_files, start=1):
            try:
                print(f"\n[ANALYZER] [{index}/{len(page_files)}] Analiz ediliyor: {os.path.basename(page_file)}")
                
                # Sayfa verisini oku
                page_data = self._load_page(page_file)
                
                if not page_data:
                    print(f"[ANALYZER] HATA: Sayfa okunamadı: {page_file}")
                    continue
                
                # HTML içeriği yoksa atla
                if not page_data.get("html"):
                    analysis_result = self._build_skipped_analysis(page_data, "skipped_no_html")
                    analysis_file = self._save_analysis(analysis_result, page_file)
                    saved_files.append(analysis_file)
                    print(
                        f"[ANALYZER] ATLANDI: HTML içeriği yok - "
                        f"{page_data.get('url', 'Bilinmeyen URL')} "
                        f"(neden: {analysis_result.get('skip_reason', 'bilinmiyor')})"
                    )
                    continue
                
                # Analiz yap
                analysis_result = self._analyze_page(page_data)
                
                # Sonucu kaydet
                analysis_file = self._save_analysis(analysis_result, page_file)
                saved_files.append(analysis_file)
                
                # Özet yazdır
                self._print_summary(analysis_result)
                
            except Exception as e:
                print(f"[ANALYZER] HATA: {page_file} - {str(e)}")
        
        print("\n" + "=" * 50)
        print(f"[ANALYZER] Toplam {len(saved_files)} sayfa analizi tamamlandı.")
        
        return saved_files
    
    def _get_page_files(self) -> List[str]:
        """
        Sayfa dosyalarının listesini döner.
        
        Returns:
            Sıralı dosya yolları listesi
        """
        try:
            files = [
                os.path.join(self.pages_dir, f)
                for f in os.listdir(self.pages_dir)
                if f.endswith(".json") and f.startswith("page_")
            ]
            return sorted(files)
        except Exception as e:
            print(f"[ANALYZER] HATA: Dosya listesi alınamadı - {str(e)}")
            return []
    
    def _load_page(self, file_path: str) -> Dict[str, Any]:
        """
        Sayfa JSON dosyasını okur.
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Sayfa verisi
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ANALYZER] HATA: Dosya okunamadı - {str(e)}")
            return {}
    
    def _analyze_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tek bir sayfa için tüm analizleri çalıştırır.
        
        Args:
            page_data: Sayfa verisi
            
        Returns:
            Birleştirilmiş analiz sonucu
        """
        url = page_data.get("url", "")
        html = page_data.get("html", "")
        headers = page_data.get("headers", {})
        
        print(f"  → URL: {url[:60]}...")
        
        # Header analizi
        print("  → Güvenlik başlıkları kontrol ediliyor...")
        header_result = self.header_checker.check(url, cached_headers=headers if headers else None)
        
        # Link analizi (sadece dahili sayfalar için, dış linkler için atla)
        print("  → Linkler kontrol ediliyor...")
        link_result = self.link_checker.check(url, html)
        
        # SEO analizi
        print("  → SEO analizi yapılıyor...")
        seo_result = self.seo_checker.check(url, html)
        
        # Sonuçları birleştir
        analysis = {
            "url": url,
            "analyzed_at": self._get_timestamp(),
            "analysis_status": "analyzed",
            "headers": {
                "summary": header_result.get("summary", {}),
                "score": header_result.get("percentage"),
                "found": len(header_result.get("headers_found", {})),
                "missing": len(header_result.get("headers_missing", [])),
                "measurement_status": header_result.get("measurement_status", "not_measured"),
                "error_type": header_result.get("error_type"),
                "details": header_result.get("details", []),
                "recommendations": self.header_checker.get_recommendations(header_result)
            },
            "broken_links": [
                {
                    "url": bl["url"],
                    "error": bl["error"],
                    "category": bl.get("category"),
                    "status_code": bl.get("status_code"),
                    "attempts": bl.get("attempts", 1)
                }
                for bl in link_result.get("broken_links", [])
            ],
            "links_summary": self.link_checker.get_summary(link_result),
            "seo": self.seo_checker.get_summary(seo_result),
            "seo_details": {
                "title": seo_result.get("title", {}),
                "meta_description": seo_result.get("meta_description", {}),
                "headings": seo_result.get("headings", {}),
                "images": seo_result.get("images", {}),
                "meta_tags": seo_result.get("meta_tags", {}),
                "canonical": seo_result.get("canonical", {}),
                "open_graph": seo_result.get("open_graph", {}),
                "issues": seo_result.get("issues", []),
                "warnings": seo_result.get("warnings", []),
                "passed": seo_result.get("passed", [])
            },
            "overall_score": self._calculate_overall_score(header_result, link_result, seo_result)
        }
        
        return analysis

    def _build_skipped_analysis(self, page_data: Dict[str, Any], status: str) -> Dict[str, Any]:
        """Analiz edilemeyen sayfalar için minimum kayıt üretir."""
        reason = (
            page_data.get("no_html_reason")
            or page_data.get("crawl_record_error")
            or "unknown"
        )
        return {
            "url": page_data.get("url", ""),
            "analyzed_at": self._get_timestamp(),
            "analysis_status": status,
            "skip_reason": reason,
            "headers": {
                "summary": {},
                "score": None,
                "found": 0,
                "missing": 0,
                "measurement_status": "not_measured",
                "error_type": "not_applicable",
                "details": [],
                "recommendations": []
            },
            "broken_links": [],
            "links_summary": {
                "total_links": 0,
                "checked": 0,
                "broken": 0,
                "broken_strict": 0,
                "server_error": 0,
                "rate_limited": 0,
                "transient_network": 0,
                "client_error": 0,
                "unknown_error": 0,
                "working": 0,
                "skipped": 0,
                "health_percentage": None,
                "strict_health_percentage": None
            },
            "seo": {},
            "seo_details": {},
            "overall_score": {
                "score": None,
                "grade": None,
                "status": "Analiz edilemedi",
                "confidence": "low",
                "breakdown": {
                    "security": None,
                    "links": None,
                    "seo": None
                }
            }
        }
    
    def _calculate_overall_score(self, header_result: Dict, link_result: Dict, seo_result: Dict) -> Dict[str, Any]:
        """
        Genel skor hesaplar.
        
        Args:
            header_result: Başlık analizi sonucu
            link_result: Link analizi sonucu
            seo_result: SEO analizi sonucu
            
        Returns:
            Genel skor bilgileri
        """
        # Ölçüm yapılamayan güvenlik sonuçlarını skora zorla 0 olarak katma.
        header_score = header_result.get("percentage")
        header_measured = header_result.get("measurement_status") == "measured"
        
        link_summary = self.link_checker.get_summary(link_result)
        # Link skoru için kalıcı kırıkları temel al.
        link_score = link_summary.get("strict_health_percentage", 100)
        
        seo_score = seo_result.get("percentage", 0)

        weighted_parts = []
        if header_measured and header_score is not None:
            weighted_parts.append((header_score, 0.4))
        weighted_parts.append((link_score, 0.2))
        weighted_parts.append((seo_score, 0.4))

        weight_sum = sum(weight for _, weight in weighted_parts)
        overall = sum(score * weight for score, weight in weighted_parts) / weight_sum if weight_sum else 0

        measured_ratio = len(weighted_parts) / 3
        if measured_ratio >= 1:
            confidence = "high"
        elif measured_ratio >= 0.67:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Değerlendirme
        if overall >= 80:
            grade = "A"
            status = "Mükemmel"
        elif overall >= 60:
            grade = "B"
            status = "İyi"
        elif overall >= 40:
            grade = "C"
            status = "Orta"
        else:
            grade = "D"
            status = "Geliştirmeli"
        
        return {
            "score": round(overall, 1),
            "grade": grade,
            "status": status,
            "confidence": confidence,
            "breakdown": {
                "security": round(header_score, 1) if header_score is not None else None,
                "links": round(link_score, 1),
                "seo": round(seo_score, 1)
            }
        }
    
    def _save_analysis(self, analysis: Dict[str, Any], page_file: str) -> str:
        """
        Analiz sonucunu JSON dosyasına kaydeder.
        
        Args:
            analysis: Analiz sonucu
            page_file: Kaynak sayfa dosyası
            
        Returns:
            Kaydedilen dosya yolu
        """
        # Dosya adını belirle (page_001.json -> page_001_analysis.json)
        page_name = os.path.basename(page_file).replace(".json", "")
        analysis_file = os.path.join(self.analysis_dir, f"{page_name}_analysis.json")
        
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"  → Kaydedildi: {analysis_file}")
        return analysis_file
    
    def _print_summary(self, analysis: Dict[str, Any]) -> None:
        """Analiz özetini konsola yazdırır."""
        overall = analysis.get("overall_score", {})
        headers = analysis.get("headers", {})
        links = analysis.get("links_summary", {})
        seo = analysis.get("seo", {})
        
        print(f"  ────────────────────────────────────")
        print(f"  │ Genel Skor: {overall.get('score', 0)}% ({overall.get('grade', 'N/A')})")
        if headers.get("measurement_status") == "measured":
            print(f"  │ Güvenlik: {headers.get('score', 0)}% ({headers.get('found', 0)}/{headers.get('found', 0) + headers.get('missing', 0)} başlık)")
        else:
            print(f"  │ Güvenlik: Ölçülemedi")
        print(f"  │ Linkler: {links.get('strict_health_percentage', links.get('health_percentage', 100))}% ({links.get('broken_strict', links.get('broken', 0))} kalıcı kırık)")
        print(f"  │ SEO: {seo.get('score', 0)}% ({seo.get('grade', 'N/A')})")
        print(f"  ────────────────────────────────────")
    
    def _get_timestamp(self) -> str:
        """Şu anki zaman damgasını döner."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def analyze_single_page(self, page_file: str) -> Dict[str, Any]:
        """
        Tek bir sayfa için analiz çalıştırır (kaydetmeden).
        
        Args:
            page_file: Sayfa dosya yolu
            
        Returns:
            Analiz sonucu
        """
        page_data = self._load_page(page_file)
        if page_data:
            return self._analyze_page(page_data)
        return {}
