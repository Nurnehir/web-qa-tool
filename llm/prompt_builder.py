"""
Prompt Oluşturma Modülü

Sayfa verilerini ve analiz sonuçlarını
prompt şablonuna yerleştirerek LLM'e gönderilecek
prompt'u hazırlar.
"""

import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse


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
        return """You are a senior QA test engineer.
Generate test scenarios for the webpage below.

PAGE URL: {url}

PAGE CONTENT:
{markdown_content}

SECURITY:
- CSP: {csp_status}
- HSTS: {hsts_status}

SEO:
- Title: {title}
- H1 Count: {h1_count}

Generate 2-3 scenarios. Return JSON only:
```json
[
  {{
    "scenario_id": 1,
    "title": "Scenario title",
    "steps": ["Step 1", "Step 2"],
    "expected": "Expected result",
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
        
        # Link özeti: kalıcı ve geçiciyi ayır
        links_summary = analysis_data.get("links_summary", {})
        strict_broken = links_summary.get("broken_strict", 0)
        transient = links_summary.get("transient_network", 0)
        client_error = links_summary.get("client_error", 0)
        rate_limited = links_summary.get("rate_limited", 0)
        if strict_broken or transient or client_error or rate_limited:
            broken_links_text = (
                f"strict={strict_broken}, transient={transient}, "
                f"client_error={client_error}, rate_limited={rate_limited}"
            )
        else:
            broken_links_text = "no problematic links found"
        
        # Şablona değerleri yerleştir
        page_url = page_data.get("url", "Bilinmeyen URL")
        path_lower = (urlparse(page_url).path or "").lower()
        title_lower = str(page_data.get("title", "")).lower()
        is_login_page = ("login" in path_lower) or ("sign in" in title_lower) or ("signin" in path_lower)
        login_page_hint = (
            "This is a login page. Include successful login, wrong password, and empty field validation scenarios."
            if is_login_page
            else "Not a login page."
        )
        prompt = self.template.format(
            url=page_url,
            markdown_content=markdown,
            login_page_hint=login_page_hint,
            csp_status="Present ✓" if headers_summary.get("csp") else "Missing ✗",
            hsts_status="Present ✓" if headers_summary.get("hsts") else "Missing ✗",
            xframe_status="Present ✓" if headers_summary.get("x_frame_options") else "Missing ✗",
            xcontent_status="Present ✓" if headers_summary.get("x_content_type_options") else "Missing ✗",
            broken_links=broken_links_text,
            title=seo.get("title", "No title"),
            title_length=seo.get("title_length", 0),
            meta_description_status="Present ✓" if seo.get("meta_description") else "Missing ✗",
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
