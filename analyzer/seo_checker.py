"""
SEO Analiz Modülü

Web sayfalarının SEO uyumluluğunu kontrol eder:
- Title etiketi varlığı ve uzunluğu
- Meta description varlığı ve uzunluğu
- H1 etiketi kullanımı
- Görsel alt etiketleri
- Meta robots etiketi
- Canonical URL
- Open Graph etiketleri
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional


class SEOChecker:
    """
    Sayfa SEO analizini yapan sınıf.
    
    Google SEO önerilerine göre temel kontrolleri gerçekleştirir.
    """
    
    # SEO önerileri için ideal değerler
    IDEAL_TITLE_LENGTH = (30, 60)  # Min, Max
    IDEAL_DESCRIPTION_LENGTH = (120, 160)  # Min, Max
    IDEAL_H1_COUNT = 1
    
    def __init__(self):
        """SEOChecker sınıfını başlatır."""
        pass
    
    def check(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Sayfa HTML'ini SEO açısından analiz eder.
        
        Args:
            url: Sayfa URL'si
            html_content: Sayfa HTML içeriği
            
        Returns:
            SEO analiz sonucu
        """
        result = {
            "url": url,
            "title": None,
            "meta_description": None,
            "headings": {},
            "images": {},
            "meta_tags": {},
            "issues": [],
            "warnings": [],
            "passed": [],
            "score": 0,
            "max_score": 0,
            "error": None
        }
        
        if not html_content:
            result["error"] = "HTML içeriği boş"
            return result
        
        try:
            soup = BeautifulSoup(html_content, "lxml")
            
            # Title kontrolü
            self._check_title(soup, result)
            
            # Meta description kontrolü
            self._check_meta_description(soup, result)
            
            # Heading (H1-H6) kontrolü
            self._check_headings(soup, result)
            
            # Görsel alt etiket kontrolü
            self._check_images(soup, result)
            
            # Diğer meta etiketleri
            self._check_meta_tags(soup, result)
            
            # Canonical URL kontrolü
            self._check_canonical(soup, url, result)
            
            # Open Graph kontrolü
            self._check_open_graph(soup, result)
            
            # Skor hesapla
            self._calculate_score(result)
            
        except Exception as e:
            result["error"] = f"HTML parse hatası: {str(e)}"
        
        return result
    
    def _check_title(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Title etiketini kontrol eder."""
        result["max_score"] += 2
        
        title_tag = soup.find("title")
        
        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()
            title_length = len(title_text)
            
            result["title"] = {
                "text": title_text,
                "length": title_length,
                "exists": True
            }
            
            result["score"] += 1
            result["passed"].append("Title etiketi mevcut")
            
            # Uzunluk kontrolü
            min_len, max_len = self.IDEAL_TITLE_LENGTH
            if min_len <= title_length <= max_len:
                result["score"] += 1
                result["passed"].append(f"Title uzunluğu ideal ({title_length} karakter)")
            elif title_length < min_len:
                result["warnings"].append(f"Title çok kısa ({title_length} karakter, önerilen: {min_len}-{max_len})")
            else:
                result["warnings"].append(f"Title çok uzun ({title_length} karakter, önerilen: {min_len}-{max_len})")
        else:
            result["title"] = {"text": None, "length": 0, "exists": False}
            result["issues"].append("Title etiketi eksik veya boş")
    
    def _check_meta_description(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Meta description etiketini kontrol eder."""
        result["max_score"] += 2
        
        meta_desc = soup.find("meta", attrs={"name": "description"})
        
        if meta_desc and meta_desc.get("content"):
            desc_text = meta_desc["content"].strip()
            desc_length = len(desc_text)
            
            result["meta_description"] = {
                "text": desc_text,
                "length": desc_length,
                "exists": True
            }
            
            result["score"] += 1
            result["passed"].append("Meta description mevcut")
            
            # Uzunluk kontrolü
            min_len, max_len = self.IDEAL_DESCRIPTION_LENGTH
            if min_len <= desc_length <= max_len:
                result["score"] += 1
                result["passed"].append(f"Meta description uzunluğu ideal ({desc_length} karakter)")
            elif desc_length < min_len:
                result["warnings"].append(f"Meta description çok kısa ({desc_length} karakter, önerilen: {min_len}-{max_len})")
            else:
                result["warnings"].append(f"Meta description çok uzun ({desc_length} karakter, önerilen: {min_len}-{max_len})")
        else:
            result["meta_description"] = {"text": None, "length": 0, "exists": False}
            result["issues"].append("Meta description eksik")
    
    def _check_headings(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Heading etiketlerini (H1-H6) kontrol eder."""
        result["max_score"] += 2
        
        headings = {}
        for i in range(1, 7):
            tag_name = f"h{i}"
            elements = soup.find_all(tag_name)
            headings[tag_name] = {
                "count": len(elements),
                "texts": [el.get_text(strip=True)[:100] for el in elements[:5]]  # İlk 5 heading'in ilk 100 karakteri
            }
        
        result["headings"] = headings
        
        # H1 kontrolü
        h1_count = headings["h1"]["count"]
        if h1_count == self.IDEAL_H1_COUNT:
            result["score"] += 2
            result["passed"].append("Tam olarak 1 adet H1 etiketi mevcut")
        elif h1_count == 0:
            result["issues"].append("H1 etiketi eksik")
        elif h1_count > 1:
            result["score"] += 1
            result["warnings"].append(f"Birden fazla H1 etiketi mevcut ({h1_count} adet)")
    
    def _check_images(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Görsellerin alt etiketlerini kontrol eder."""
        result["max_score"] += 1
        
        images = soup.find_all("img")
        total_images = len(images)
        images_without_alt = []
        images_with_empty_alt = []
        images_with_alt = []
        
        for img in images:
            src = img.get("src", "")[:100]
            alt = img.get("alt")
            
            if alt is None:
                images_without_alt.append(src)
            elif alt.strip() == "":
                images_with_empty_alt.append(src)
            else:
                images_with_alt.append({"src": src, "alt": alt[:50]})
        
        result["images"] = {
            "total": total_images,
            "with_alt": len(images_with_alt),
            "without_alt": len(images_without_alt),
            "empty_alt": len(images_with_empty_alt),
            "missing_alt_examples": images_without_alt[:5]  # İlk 5 örnek
        }
        
        missing_alt_count = len(images_without_alt) + len(images_with_empty_alt)
        
        if total_images == 0:
            result["score"] += 1
            result["passed"].append("Sayfada görsel yok (kontrol gerekmiyor)")
        elif missing_alt_count == 0:
            result["score"] += 1
            result["passed"].append(f"Tüm görsellerde ({total_images}) alt etiketi mevcut")
        else:
            if missing_alt_count <= total_images * 0.2:  # %20'den az eksikse uyarı
                result["warnings"].append(f"{missing_alt_count}/{total_images} görselde alt etiketi eksik")
            else:
                result["issues"].append(f"{missing_alt_count}/{total_images} görselde alt etiketi eksik")
    
    def _check_meta_tags(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Diğer önemli meta etiketlerini kontrol eder."""
        meta_tags = {}
        
        # Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        meta_tags["viewport"] = {
            "exists": viewport is not None,
            "content": viewport.get("content") if viewport else None
        }
        
        # Robots
        robots = soup.find("meta", attrs={"name": "robots"})
        meta_tags["robots"] = {
            "exists": robots is not None,
            "content": robots.get("content") if robots else None
        }
        
        # Charset
        charset = soup.find("meta", attrs={"charset": True})
        if not charset:
            charset = soup.find("meta", attrs={"http-equiv": "Content-Type"})
        meta_tags["charset"] = {
            "exists": charset is not None
        }
        
        # Language
        html_tag = soup.find("html")
        meta_tags["lang"] = {
            "exists": html_tag is not None and html_tag.get("lang") is not None,
            "value": html_tag.get("lang") if html_tag else None
        }
        
        result["meta_tags"] = meta_tags
        
        # Viewport kontrolü
        result["max_score"] += 1
        if meta_tags["viewport"]["exists"]:
            result["score"] += 1
            result["passed"].append("Viewport meta etiketi mevcut (mobil uyumluluk)")
        else:
            result["issues"].append("Viewport meta etiketi eksik (mobil uyumluluk sorunu)")
    
    def _check_canonical(self, soup: BeautifulSoup, page_url: str, result: Dict[str, Any]) -> None:
        """Canonical URL kontrolü yapar."""
        canonical = soup.find("link", attrs={"rel": "canonical"})
        
        result["canonical"] = {
            "exists": canonical is not None,
            "url": canonical.get("href") if canonical else None
        }
        
        if canonical:
            result["passed"].append("Canonical URL tanımlanmış")
        else:
            result["warnings"].append("Canonical URL tanımlanmamış (duplicate content riski)")
    
    def _check_open_graph(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Open Graph etiketlerini kontrol eder."""
        og_tags = {}
        
        important_og = ["og:title", "og:description", "og:image", "og:url", "og:type"]
        
        for og_name in important_og:
            og_tag = soup.find("meta", attrs={"property": og_name})
            og_tags[og_name] = {
                "exists": og_tag is not None,
                "content": og_tag.get("content")[:100] if og_tag and og_tag.get("content") else None
            }
        
        result["open_graph"] = og_tags
        
        # En az 3 OG etiketi varsa geçti say
        og_count = sum(1 for v in og_tags.values() if v["exists"])
        if og_count >= 3:
            result["passed"].append(f"Open Graph etiketleri mevcut ({og_count}/5)")
        elif og_count > 0:
            result["warnings"].append(f"Bazı Open Graph etiketleri eksik ({og_count}/5)")
        else:
            result["warnings"].append("Open Graph etiketleri eksik (sosyal medya paylaşımı etkilenir)")
    
    def _calculate_score(self, result: Dict[str, Any]) -> None:
        """Toplam SEO skorunu hesaplar."""
        if result["max_score"] > 0:
            result["percentage"] = round((result["score"] / result["max_score"]) * 100, 1)
        else:
            result["percentage"] = 0
        
        # Genel değerlendirme
        if result["percentage"] >= 80:
            result["grade"] = "A"
            result["status"] = "Mükemmel"
        elif result["percentage"] >= 60:
            result["grade"] = "B"
            result["status"] = "İyi"
        elif result["percentage"] >= 40:
            result["grade"] = "C"
            result["status"] = "Orta"
        else:
            result["grade"] = "D"
            result["status"] = "Geliştirmeli"
    
    def get_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        SEO analizi özeti üretir.
        
        Args:
            result: check() metodunun döndürdüğü sonuç
            
        Returns:
            Özet bilgiler
        """
        return {
            "title": result.get("title", {}).get("text"),
            "title_length": result.get("title", {}).get("length", 0),
            "meta_description": result.get("meta_description", {}).get("exists", False),
            "h1_count": result.get("headings", {}).get("h1", {}).get("count", 0),
            "missing_alts": result.get("images", {}).get("without_alt", 0) + result.get("images", {}).get("empty_alt", 0),
            "total_images": result.get("images", {}).get("total", 0),
            "issues_count": len(result.get("issues", [])),
            "warnings_count": len(result.get("warnings", [])),
            "score": result.get("percentage", 0),
            "grade": result.get("grade", "N/A")
        }
