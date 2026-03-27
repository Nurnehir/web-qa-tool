from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List


@dataclass
class SEOCheckResult:
    check_name: str
    status: str      # pass, warn, fail
    severity: str
    detail: str


class SEOChecker:
    """HTML'i analiz ederek SEO ve erişilebilirlik sorunlarını bulur."""

    def analyze(self, html: str, url: str) -> List[SEOCheckResult]:
        soup = BeautifulSoup(html, "lxml")
        results = [
            self._check_title(soup),
            self._check_meta_description(soup),
            self._check_h1(soup),
            self._check_canonical(soup, url),
            self._check_robots_meta(soup),
            self._check_lang(soup),
        ]
        results.extend(self._check_images(soup))
        results.extend(self._check_og_tags(soup))
        return results

    def _check_title(self, soup) -> SEOCheckResult:
        tag = soup.find("title")
        if not tag or not tag.text.strip():
            return SEOCheckResult("title_tag", "fail", "high",
                                  "<title> etiketi eksik veya boş.")
        length = len(tag.text.strip())
        if length < 10:
            return SEOCheckResult("title_tag", "warn", "medium",
                                  f"<title> çok kısa: {length} karakter. 50-60 karakter önerilir.")
        if length > 70:
            return SEOCheckResult("title_tag", "warn", "low",
                                  f"<title> çok uzun: {length} karakter. Google kısaltabilir.")
        return SEOCheckResult("title_tag", "pass", "info",
                              f"<title> uygun uzunlukta: {length} karakter.")

    def _check_meta_description(self, soup) -> SEOCheckResult:
        meta = soup.find("meta", attrs={"name": "description"})
        if not meta or not meta.get("content", "").strip():
            return SEOCheckResult("meta_description", "fail", "high",
                                  "<meta name='description'> eksik.")
        length = len(meta["content"].strip())
        if length < 50:
            return SEOCheckResult("meta_description", "warn", "medium",
                                  f"Meta description çok kısa: {length} karakter.")
        if length > 170:
            return SEOCheckResult("meta_description", "warn", "low",
                                  f"Meta description çok uzun: {length} karakter.")
        return SEOCheckResult("meta_description", "pass", "info",
                              f"Meta description uygun: {length} karakter.")

    def _check_h1(self, soup) -> SEOCheckResult:
        h1_tags = soup.find_all("h1")
        count = len(h1_tags)
        if count == 0:
            return SEOCheckResult("h1_tag", "fail", "high", "Sayfada <h1> etiketi yok.")
        if count > 1:
            return SEOCheckResult("h1_tag", "warn", "medium",
                                  f"Sayfada {count} adet <h1> var. Yalnızca 1 tane olmalı.")
        h1_text = h1_tags[0].text.strip()
        if len(h1_text) < 5:
            return SEOCheckResult("h1_tag", "warn", "medium", f"<h1> çok kısa: '{h1_text}'")
        return SEOCheckResult("h1_tag", "pass", "info",
                              f"<h1> mevcut: '{h1_text[:60]}'")

    def _check_canonical(self, soup, url: str) -> SEOCheckResult:
        canonical = soup.find("link", rel="canonical")
        if not canonical:
            return SEOCheckResult("canonical_url", "warn", "medium",
                                  "Canonical URL etiketi eksik. Duplicate content sorunu olabilir.")
        return SEOCheckResult("canonical_url", "pass", "info",
                              f"Canonical URL mevcut: {canonical.get('href', '')[:80]}")

    def _check_images(self, soup) -> List[SEOCheckResult]:
        images = soup.find_all("img")
        missing = [img for img in images if not img.get("alt")]
        total = len(images)
        if missing:
            return [SEOCheckResult(
                "image_alt_attributes", "fail", "medium",
                f"{total} görselin {len(missing)} tanesinde 'alt' özelliği eksik."
            )]
        return [SEOCheckResult("image_alt_attributes", "pass", "info",
                               f"Tüm {total} görselde 'alt' mevcut.")]

    def _check_og_tags(self, soup) -> List[SEOCheckResult]:
        results = []
        for prop in ["og:title", "og:description", "og:image"]:
            tag = soup.find("meta", property=prop)
            key = f"og_tag_{prop.replace(':', '_')}"
            if not tag or not tag.get("content", "").strip():
                results.append(SEOCheckResult(key, "warn", "low",
                                              f"Open Graph etiketi eksik: {prop}"))
            else:
                results.append(SEOCheckResult(key, "pass", "info", f"{prop} mevcut."))
        return results

    def _check_robots_meta(self, soup) -> SEOCheckResult:
        robots = soup.find("meta", attrs={"name": "robots"})
        if robots:
            content = robots.get("content", "").lower()
            if "noindex" in content:
                return SEOCheckResult("robots_meta", "warn", "high",
                                      f"Sayfa noindex: '{content}'. Arama motorları indekslemeyecek.")
        return SEOCheckResult("robots_meta", "pass", "info", "Robots meta normal.")

    def _check_lang(self, soup) -> SEOCheckResult:
        html_tag = soup.find("html")
        if not html_tag or not html_tag.get("lang"):
            return SEOCheckResult("html_lang", "warn", "medium",
                                  "<html lang=''> özelliği eksik.")
        return SEOCheckResult("html_lang", "pass", "info",
                              f"Dil tanımlı: lang='{html_tag['lang']}'")
