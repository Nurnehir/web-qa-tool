"""
HTML Rapor Oluşturucu

JSON raporunu Jinja2 şablonuyla birleştirerek
görsel HTML rapor üretir.
"""

import json
import os
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any


class HTMLReporter:
    """
    Görsel HTML rapor oluşturan sınıf.
    
    JSON raporunu okur ve Jinja2 şablonuyla
    birleştirerek output/report.html dosyası üretir.
    """
    
    def __init__(
        self,
        json_report: str = "output/report.json",
        template_dir: str = "reporter/templates",
        template_file: str = "report.html.j2",
        output_file: str = "output/report.html"
    ):
        """
        HTMLReporter sınıfını başlatır.
        
        Args:
            json_report: JSON rapor dosyası yolu
            template_dir: Jinja2 şablon klasörü
            template_file: Şablon dosya adı
            output_file: Çıktı HTML dosyası yolu
        """
        self.json_report = json_report
        self.template_dir = template_dir
        self.template_file = template_file
        self.output_file = output_file
    
    def generate(self) -> str:
        """
        HTML raporu oluşturur.
        
        Returns:
            Oluşturulan rapor dosyasının yolu
        """
        print("[HTML_REPORTER] HTML rapor oluşturuluyor...")
        
        # JSON raporunu yükle
        report_data = self._load_json_report()
        
        if not report_data:
            print("[HTML_REPORTER] HATA: JSON rapor yüklenemedi")
            return ""
        
        # Jinja2 şablonunu yükle
        try:
            env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True
            )
            template = env.get_template(self.template_file)
        except Exception as e:
            print(f"[HTML_REPORTER] HATA: Şablon yüklenemedi - {str(e)}")
            return ""
        
        # Şablonu render et
        try:
            html_content = template.render(**report_data)
        except Exception as e:
            print(f"[HTML_REPORTER] HATA: Şablon render edilemedi - {str(e)}")
            return ""
        
        # HTML dosyasını kaydet
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"[HTML_REPORTER] Rapor kaydedildi: {self.output_file}")
            return self.output_file
            
        except Exception as e:
            print(f"[HTML_REPORTER] HATA: Dosya yazılamadı - {str(e)}")
            return ""
    
    def _load_json_report(self) -> Dict[str, Any]:
        """
        JSON raporunu yükler.
        
        Returns:
            Rapor verisi
        """
        try:
            with open(self.json_report, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[HTML_REPORTER] HATA: JSON rapor bulunamadı: {self.json_report}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[HTML_REPORTER] HATA: JSON ayrıştırma hatası - {str(e)}")
            return {}
        except Exception as e:
            print(f"[HTML_REPORTER] HATA: Dosya okunamadı - {str(e)}")
            return {}
    
    def generate_from_data(self, report_data: Dict[str, Any]) -> str:
        """
        Veriden doğrudan HTML rapor oluşturur.
        
        Args:
            report_data: Rapor verisi
            
        Returns:
            Oluşturulan rapor dosyasının yolu
        """
        try:
            env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True
            )
            template = env.get_template(self.template_file)
            html_content = template.render(**report_data)
            
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return self.output_file
            
        except Exception as e:
            print(f"[HTML_REPORTER] HATA: {str(e)}")
            return ""
