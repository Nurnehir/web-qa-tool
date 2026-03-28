"""
Prompt Oluşturma Modülü

Sayfa verilerini ve analiz sonuçlarını
prompt şablonuna yerleştirerek LLM'e gönderilecek
prompt'u hazırlar.
"""

import os
from typing import Dict, Any, Optional


class PromptBuilder:
    """
    LLM için prompt oluşturan sınıf.
    
    Şablon dosyasını okur ve sayfa verilerini yerleştirerek
    nihai prompt'u üretir.
    """
    
    def __init__(self, template_path: str = "prompts/scenario_template.txt"):
        """
        PromptBuilder sınıfını başlatır.
        
        Args:
            template_path: Prompt şablon dosyasının yolu
        """
        self.template_path = template_path
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """
        Şablon dosyasını okur.
        
        Returns:
            Şablon içeriği
        """
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"[PROMPT_BUILDER] HATA: Şablon dosyası bulunamadı: {self.template_path}")
            return self._get_default_template()
        except Exception as e:
            print(f"[PROMPT_BUILDER] HATA: Şablon okunamadı - {str(e)}")
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Varsayılan şablonu döner."""
        return """Sen deneyimli bir QA test mühendisisin.
Aşağıdaki web sayfası için test senaryoları üret.

SAYFA URL: {url}

SAYFA İÇERİĞİ:
{markdown_content}

GÜVENLİK DURUMU:
- CSP: {csp_status}
- HSTS: {hsts_status}

SEO DURUMU:
- Başlık: {title}
- H1 Sayısı: {h1_count}

3-5 adet test senaryosu üret. JSON formatında yanıt ver:
```json
[
  {{
    "scenario_id": 1,
    "title": "Senaryo başlığı",
    "steps": ["Adım 1", "Adım 2"],
    "expected": "Beklenen sonuç",
    "priority": "high"
  }}
]
```"""
    
    def build(self, page_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> str:
        """
        Sayfa ve analiz verilerinden prompt oluşturur.
        
        Args:
            page_data: Sayfa verisi (page_XXX.json)
            analysis_data: Analiz verisi (page_XXX_analysis.json)
            
        Returns:
            Hazırlanmış prompt
        """
        # Markdown içeriğini daha agresif kısalt (hız için)
        markdown = page_data.get("markdown", "")
        if len(markdown) > 1500:  # 3000'den 1500'e düşürdük
            markdown = markdown[:1500] + "\n\n... [içerik kısaltıldı]"
        
        # Güvenlik başlıkları
        headers_summary = analysis_data.get("headers", {}).get("summary", {})
        
        # SEO verileri
        seo = analysis_data.get("seo", {})
        
        # Kırık linkler - sadece sayı bildir (detay verme, daha hızlı)
        broken_links = analysis_data.get("broken_links", [])
        if broken_links:
            broken_links_text = f"{len(broken_links)} adet kırık link tespit edildi"
        else:
            broken_links_text = "Kırık link bulunamadı"
        
        # Şablona değerleri yerleştir
        prompt = self.template.format(
            url=page_data.get("url", "Bilinmeyen URL"),
            markdown_content=markdown,
            csp_status="Mevcut ✓" if headers_summary.get("csp") else "Eksik ✗",
            hsts_status="Mevcut ✓" if headers_summary.get("hsts") else "Eksik ✗",
            xframe_status="Mevcut ✓" if headers_summary.get("x_frame_options") else "Eksik ✗",
            xcontent_status="Mevcut ✓" if headers_summary.get("x_content_type_options") else "Eksik ✗",
            broken_links=broken_links_text,
            title=seo.get("title", "Başlık yok"),
            title_length=seo.get("title_length", 0),
            meta_description_status="Mevcut ✓" if seo.get("meta_description") else "Eksik ✗",
            h1_count=seo.get("h1_count", 0),
            missing_alts=seo.get("missing_alts", 0)
        )
        
        return prompt
    
    def build_from_files(self, page_file: str, analysis_file: str) -> Optional[str]:
        """
        Dosyalardan okuyarak prompt oluşturur.
        
        Args:
            page_file: Sayfa JSON dosyası yolu
            analysis_file: Analiz JSON dosyası yolu
            
        Returns:
            Hazırlanmış prompt veya None
        """
        import json
        
        try:
            with open(page_file, "r", encoding="utf-8") as f:
                page_data = json.load(f)
            
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis_data = json.load(f)
            
            return self.build(page_data, analysis_data)
            
        except FileNotFoundError as e:
            print(f"[PROMPT_BUILDER] HATA: Dosya bulunamadı - {str(e)}")
            return None
        except Exception as e:
            print(f"[PROMPT_BUILDER] HATA: Dosya okunamadı - {str(e)}")
            return None
    
    def get_token_estimate(self, prompt: str) -> int:
        """
        Prompt'un yaklaşık token sayısını hesaplar.
        
        Basit tahmin: ortalama 4 karakter = 1 token
        
        Args:
            prompt: Prompt metni
            
        Returns:
            Tahmini token sayısı
        """
        return len(prompt) // 4
