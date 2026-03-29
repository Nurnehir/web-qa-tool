"""
HTTP Güvenlik Başlıkları Kontrolü

OWASP referanslı güvenlik başlıklarını kontrol eder:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
"""

import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class HeaderChecker:
    """
    HTTP güvenlik başlıklarını kontrol eden sınıf.
    
    OWASP Secure Headers Project referanslarına göre
    kritik güvenlik başlıklarını denetler.
    """
    
    # Kontrol edilecek güvenlik başlıkları ve açıklamaları
    SECURITY_HEADERS = {
        "content-security-policy": {
            "name": "Content-Security-Policy (CSP)",
            "description": "XSS ve veri enjeksiyonu saldırılarını önler",
            "severity": "high"
        },
        "strict-transport-security": {
            "name": "Strict-Transport-Security (HSTS)",
            "description": "HTTPS kullanımını zorunlu kılar",
            "severity": "high"
        },
        "x-frame-options": {
            "name": "X-Frame-Options",
            "description": "Clickjacking saldırılarını önler",
            "severity": "medium"
        },
        "x-content-type-options": {
            "name": "X-Content-Type-Options",
            "description": "MIME type sniffing'i engeller",
            "severity": "medium"
        },
        "x-xss-protection": {
            "name": "X-XSS-Protection",
            "description": "Tarayıcı XSS filtrelerini etkinleştirir (eski)",
            "severity": "low"
        },
        "referrer-policy": {
            "name": "Referrer-Policy",
            "description": "Referrer bilgisinin paylaşımını kontrol eder",
            "severity": "low"
        },
        "permissions-policy": {
            "name": "Permissions-Policy",
            "description": "Tarayıcı özelliklerinin kullanımını kısıtlar",
            "severity": "low"
        }
    }
    
    def __init__(self, timeout: float = 10.0):
        """
        HeaderChecker sınıfını başlatır.
        
        Args:
            timeout: HTTP istek zaman aşımı (saniye)
        """
        self.timeout = timeout
    
    def check(self, url: str, cached_headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Verilen URL için güvenlik başlıklarını kontrol eder.
        
        Args:
            url: Kontrol edilecek URL
            cached_headers: Önceden alınmış başlıklar (varsa)
            
        Returns:
            Güvenlik başlıkları analiz sonucu
        """
        result = {
            "url": url,
            "headers_found": {},
            "headers_missing": [],
            "score": 0,
            "max_score": len(self.SECURITY_HEADERS),
            "details": [],
            "measurement_status": "not_measured",
            "error_type": None,
            "error": None
        }
        
        # Başlıkları al
        headers = cached_headers if cached_headers else None
        if not headers:
            headers = self._fetch_headers(url)
        
        if headers is None:
            result["error"] = "Başlıklar alınamadı"
            result["error_type"] = "unavailable"
            result["percentage"] = None
            result["summary"] = {
                "csp": None,
                "hsts": None,
                "x_frame_options": None,
                "x_content_type_options": None,
                "x_xss_protection": None,
                "referrer_policy": None,
                "permissions_policy": None
            }
            # Ölçüm yapılamadığı için başlıkları eksik saymayız.
            return result
        result["measurement_status"] = "measured"
        
        # Başlıkları küçük harfe çevir (case-insensitive karşılaştırma için)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Her güvenlik başlığını kontrol et
        for header_key, header_info in self.SECURITY_HEADERS.items():
            if header_key in headers_lower:
                result["headers_found"][header_key] = {
                    "value": headers_lower[header_key],
                    "name": header_info["name"],
                    "status": "present"
                }
                result["score"] += 1
                result["details"].append({
                    "header": header_info["name"],
                    "status": "✓ Mevcut",
                    "value": headers_lower[header_key][:100],  # İlk 100 karakter
                    "severity": header_info["severity"]
                })
            else:
                result["headers_missing"].append({
                    "key": header_key,
                    "name": header_info["name"],
                    "description": header_info["description"],
                    "severity": header_info["severity"]
                })
                result["details"].append({
                    "header": header_info["name"],
                    "status": "✗ Eksik",
                    "value": None,
                    "severity": header_info["severity"],
                    "recommendation": header_info["description"]
                })
        
        # Özet bilgiler
        result["summary"] = {
            "csp": "content-security-policy" in headers_lower,
            "hsts": "strict-transport-security" in headers_lower,
            "x_frame_options": "x-frame-options" in headers_lower,
            "x_content_type_options": "x-content-type-options" in headers_lower,
            "x_xss_protection": "x-xss-protection" in headers_lower,
            "referrer_policy": "referrer-policy" in headers_lower,
            "permissions_policy": "permissions-policy" in headers_lower
        }
        
        # Yüzde hesapla
        result["percentage"] = round((result["score"] / result["max_score"]) * 100, 1)
        
        return result
    
    def _fetch_headers(self, url: str) -> Optional[Dict[str, str]]:
        """
        URL'den HTTP başlıklarını alır.
        
        Args:
            url: Başlıkları alınacak URL
            
        Returns:
            Başlık sözlüğü veya None
        """
        try:
            # URL'nin geçerli olup olmadığını kontrol et
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print(f"[HEADER_CHECKER] Geçersiz URL: {url}")
                return None
            
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                # Önce HEAD ile dene.
                response = client.head(url)
                if response.status_code in (405, 501, 403):
                    # Bazı sunucular HEAD'e izin vermez; GET fallback.
                    response = client.get(url)
                return dict(response.headers) if response.headers else None
                
        except httpx.TimeoutException:
            print(f"[HEADER_CHECKER] Zaman aşımı: {url}")
            return None
        except httpx.ConnectError:
            print(f"[HEADER_CHECKER] Bağlantı hatası: {url}")
            return None
        except Exception as e:
            print(f"[HEADER_CHECKER] Hata ({url}): {str(e)}")
            return None
    
    def get_recommendations(self, result: Dict[str, Any]) -> list:
        """
        Eksik başlıklar için öneriler üretir.
        
        Args:
            result: check() metodunun döndürdüğü sonuç
            
        Returns:
            Öneri listesi
        """
        recommendations = []
        
        for missing in result.get("headers_missing", []):
            severity = missing["severity"]
            priority = "🔴 Yüksek" if severity == "high" else ("🟡 Orta" if severity == "medium" else "🟢 Düşük")
            
            recommendations.append({
                "priority": priority,
                "header": missing["name"],
                "action": f"{missing['name']} başlığını ekleyin",
                "reason": missing["description"]
            })
        
        return recommendations
