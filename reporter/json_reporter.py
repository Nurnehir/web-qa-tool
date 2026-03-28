"""
JSON Rapor Oluşturucu

Tüm sayfa, analiz ve senaryo verilerini
tek bir birleşik JSON raporuna dönüştürür.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List


class JSONReporter:
    """
    Birleşik JSON rapor oluşturan sınıf.
    
    Tüm pages, analysis ve scenarios klasörlerini okuyarak
    tek bir output/report.json dosyası üretir.
    """
    
    def __init__(
        self,
        pages_dir: str = "output/pages",
        analysis_dir: str = "output/analysis",
        scenarios_dir: str = "output/scenarios",
        output_file: str = "output/report.json"
    ):
        """
        JSONReporter sınıfını başlatır.
        
        Args:
            pages_dir: Sayfa JSON dosyalarının bulunduğu klasör
            analysis_dir: Analiz sonuçlarının bulunduğu klasör
            scenarios_dir: Senaryo dosyalarının bulunduğu klasör
            output_file: Çıktı rapor dosyası yolu
        """
        self.pages_dir = pages_dir
        self.analysis_dir = analysis_dir
        self.scenarios_dir = scenarios_dir
        self.output_file = output_file
    
    def generate(self) -> str:
        """
        Birleşik JSON raporu oluşturur.
        
        Returns:
            Oluşturulan rapor dosyasının yolu
        """
        print("[JSON_REPORTER] Rapor oluşturuluyor...")
        
        # Tüm verileri topla
        pages_data = self._load_all_pages()
        analysis_data = self._load_all_analysis()
        scenarios_data = self._load_all_scenarios()
        
        # Verileri birleştir
        report = self._merge_data(pages_data, analysis_data, scenarios_data)
        
        # Özet istatistikler ekle
        report["summary"] = self._generate_summary(report)
        
        # Meta bilgiler
        report["meta"] = {
            "generated_at": datetime.now().isoformat(),
            "tool": "LynxTest",
            "version": "1.0.0"
        }
        
        # Raporu kaydet
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[JSON_REPORTER] Rapor kaydedildi: {self.output_file}")
        return self.output_file
    
    def _load_all_pages(self) -> Dict[str, Any]:
        """Tüm sayfa verilerini yükler."""
        data = {}
        
        try:
            for filename in sorted(os.listdir(self.pages_dir)):
                if filename.endswith(".json") and filename.startswith("page_"):
                    filepath = os.path.join(self.pages_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        page_data = json.load(f)
                        # Büyük HTML/Markdown içeriklerini rapordan çıkar
                        page_data.pop("html", None)
                        page_data["markdown"] = page_data.get("markdown", "")[:500] + "..." if page_data.get("markdown") else ""
                        data[filename] = page_data
        except Exception as e:
            print(f"[JSON_REPORTER] UYARI: Sayfa verileri yüklenemedi - {str(e)}")
        
        return data
    
    def _load_all_analysis(self) -> Dict[str, Any]:
        """Tüm analiz verilerini yükler."""
        data = {}
        
        try:
            for filename in sorted(os.listdir(self.analysis_dir)):
                if filename.endswith("_analysis.json"):
                    filepath = os.path.join(self.analysis_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data[filename] = json.load(f)
        except Exception as e:
            print(f"[JSON_REPORTER] UYARI: Analiz verileri yüklenemedi - {str(e)}")
        
        return data
    
    def _load_all_scenarios(self) -> Dict[str, Any]:
        """Tüm senaryo verilerini yükler."""
        data = {}
        
        try:
            for filename in sorted(os.listdir(self.scenarios_dir)):
                if filename.endswith("_scenarios.json"):
                    filepath = os.path.join(self.scenarios_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data[filename] = json.load(f)
        except Exception as e:
            print(f"[JSON_REPORTER] UYARI: Senaryo verileri yüklenemedi - {str(e)}")
        
        return data
    
    def _merge_data(
        self,
        pages: Dict[str, Any],
        analysis: Dict[str, Any],
        scenarios: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tüm verileri sayfa bazında birleştirir.
        
        Args:
            pages: Sayfa verileri
            analysis: Analiz verileri
            scenarios: Senaryo verileri
            
        Returns:
            Birleştirilmiş rapor
        """
        report = {
            "pages": []
        }
        
        # Her sayfa için verileri birleştir
        for page_file, page_data in pages.items():
            page_num = page_file.replace("page_", "").replace(".json", "")
            analysis_file = f"page_{page_num}_analysis.json"
            scenario_file = f"page_{page_num}_scenarios.json"
            
            page_entry = {
                "id": int(page_num),
                "url": page_data.get("url", ""),
                "title": page_data.get("title", ""),
                "status_code": page_data.get("status_code", 0),
                "has_content": bool(page_data.get("markdown")),
                "analysis": analysis.get(analysis_file, {}),
                "scenarios": scenarios.get(scenario_file, {}).get("scenarios", [])
            }
            
            report["pages"].append(page_entry)
        
        return report
    
    def _generate_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rapor özeti oluşturur.
        
        Args:
            report: Birleştirilmiş rapor
            
        Returns:
            Özet istatistikler
        """
        pages = report.get("pages", [])
        
        # Temel istatistikler
        total_pages = len(pages)
        pages_with_content = sum(1 for p in pages if p.get("has_content"))
        
        # Güvenlik skorları
        security_scores = []
        seo_scores = []
        overall_scores = []
        total_broken_links = 0
        total_scenarios = 0
        
        for page in pages:
            analysis = page.get("analysis", {})
            
            if analysis:
                # Güvenlik
                headers = analysis.get("headers", {})
                if headers.get("score") is not None:
                    security_scores.append(headers["score"])
                
                # SEO
                seo = analysis.get("seo", {})
                if seo.get("score") is not None:
                    seo_scores.append(seo["score"])
                
                # Genel skor
                overall = analysis.get("overall_score", {})
                if overall.get("score") is not None:
                    overall_scores.append(overall["score"])
                
                # Kırık linkler
                total_broken_links += len(analysis.get("broken_links", []))
            
            # Senaryolar
            total_scenarios += len(page.get("scenarios", []))
        
        # Ortalama hesapla
        avg_security = round(sum(security_scores) / len(security_scores), 1) if security_scores else 0
        avg_seo = round(sum(seo_scores) / len(seo_scores), 1) if seo_scores else 0
        avg_overall = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0
        
        # Grade hesapla
        def get_grade(score):
            if score >= 80: return "A"
            if score >= 60: return "B"
            if score >= 40: return "C"
            return "D"
        
        return {
            "total_pages": total_pages,
            "pages_analyzed": pages_with_content,
            "pages_skipped": total_pages - pages_with_content,
            "total_broken_links": total_broken_links,
            "total_scenarios": total_scenarios,
            "average_scores": {
                "security": avg_security,
                "seo": avg_seo,
                "overall": avg_overall
            },
            "grades": {
                "security": get_grade(avg_security),
                "seo": get_grade(avg_seo),
                "overall": get_grade(avg_overall)
            }
        }
