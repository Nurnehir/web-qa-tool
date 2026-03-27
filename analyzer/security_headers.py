import httpx
import re
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class HeaderCheckResult:
    check_name: str
    status: str      # "pass", "warn", "fail"
    severity: str    # "info", "low", "medium", "high", "critical"
    detail: str
    owasp_ref: str


class SecurityHeadersAnalyzer:
    """
    HTTP güvenlik başlıklarını OWASP A05:2021 referansıyla denetler.
    """

    def analyze(self, url: str) -> List[HeaderCheckResult]:
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                response = client.get(url)
                headers = {k.lower(): v for k, v in response.headers.items()}
        except httpx.RequestError as e:
            return [HeaderCheckResult(
                check_name="http_request", status="fail", severity="critical",
                detail=f"Sayfaya ulaşılamadı: {e}", owasp_ref="A05:2021"
            )]

        return [
            self._check_csp(headers),
            self._check_hsts(headers),
            self._check_x_frame_options(headers),
            self._check_x_content_type(headers),
            self._check_referrer_policy(headers),
            self._check_permissions_policy(headers),
        ]

    def _check_csp(self, headers: Dict) -> HeaderCheckResult:
        csp = headers.get("content-security-policy", "")
        if not csp:
            return HeaderCheckResult(
                check_name="content_security_policy", status="fail", severity="high",
                detail="Content-Security-Policy başlığı eksik. XSS saldırılarına karşı savunmasız.",
                owasp_ref="A05:2021"
            )
        if "unsafe-inline" in csp or "unsafe-eval" in csp:
            return HeaderCheckResult(
                check_name="content_security_policy", status="warn", severity="medium",
                detail=f"CSP mevcut ancak 'unsafe-inline' veya 'unsafe-eval' içeriyor: {csp[:100]}",
                owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="content_security_policy", status="pass", severity="info",
            detail="CSP başlığı mevcut ve güvenli.", owasp_ref="A05:2021"
        )

    def _check_hsts(self, headers: Dict) -> HeaderCheckResult:
        hsts = headers.get("strict-transport-security", "")
        if not hsts:
            return HeaderCheckResult(
                check_name="hsts", status="fail", severity="high",
                detail="HSTS başlığı eksik. HTTP downgrade saldırılarına karşı savunmasız.",
                owasp_ref="A05:2021"
            )
        match = re.search(r'max-age=(\d+)', hsts)
        if match and int(match.group(1)) < 15768000:
            return HeaderCheckResult(
                check_name="hsts", status="warn", severity="medium",
                detail=f"HSTS max-age çok kısa: {match.group(1)} saniye. En az 15768000 önerilir.",
                owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="hsts", status="pass", severity="info",
            detail=f"HSTS başlığı mevcut: {hsts}", owasp_ref="A05:2021"
        )

    def _check_x_frame_options(self, headers: Dict) -> HeaderCheckResult:
        xfo = headers.get("x-frame-options", "").upper()
        if not xfo:
            return HeaderCheckResult(
                check_name="x_frame_options", status="fail", severity="medium",
                detail="X-Frame-Options eksik. Clickjacking saldırılarına karşı savunmasız.",
                owasp_ref="A05:2021"
            )
        if xfo not in ("DENY", "SAMEORIGIN"):
            return HeaderCheckResult(
                check_name="x_frame_options", status="warn", severity="low",
                detail=f"X-Frame-Options geçersiz değer: {xfo}. 'DENY' veya 'SAMEORIGIN' olmalı.",
                owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="x_frame_options", status="pass", severity="info",
            detail=f"X-Frame-Options: {xfo}", owasp_ref="A05:2021"
        )

    def _check_x_content_type(self, headers: Dict) -> HeaderCheckResult:
        xcto = headers.get("x-content-type-options", "").lower()
        if xcto != "nosniff":
            return HeaderCheckResult(
                check_name="x_content_type_options", status="fail", severity="medium",
                detail="X-Content-Type-Options: nosniff eksik. MIME sniffing saldırılarına açık.",
                owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="x_content_type_options", status="pass", severity="info",
            detail="X-Content-Type-Options: nosniff mevcut.", owasp_ref="A05:2021"
        )

    def _check_referrer_policy(self, headers: Dict) -> HeaderCheckResult:
        rp = headers.get("referrer-policy", "")
        safe_values = {
            "no-referrer", "no-referrer-when-downgrade",
            "strict-origin", "strict-origin-when-cross-origin"
        }
        if not rp:
            return HeaderCheckResult(
                check_name="referrer_policy", status="warn", severity="low",
                detail="Referrer-Policy başlığı eksik. Hassas URL bilgisi sızdırılabilir.",
                owasp_ref="A05:2021"
            )
        if rp.lower() not in safe_values:
            return HeaderCheckResult(
                check_name="referrer_policy", status="warn", severity="low",
                detail=f"Referrer-Policy değeri güvenli değil: {rp}", owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="referrer_policy", status="pass", severity="info",
            detail=f"Referrer-Policy: {rp}", owasp_ref="A05:2021"
        )

    def _check_permissions_policy(self, headers: Dict) -> HeaderCheckResult:
        pp = headers.get("permissions-policy", "")
        if not pp:
            return HeaderCheckResult(
                check_name="permissions_policy", status="warn", severity="low",
                detail="Permissions-Policy başlığı eksik. Tarayıcı özelliklerine erişim kısıtlanmıyor.",
                owasp_ref="A05:2021"
            )
        return HeaderCheckResult(
            check_name="permissions_policy", status="pass", severity="info",
            detail=f"Permissions-Policy mevcut: {pp[:80]}", owasp_ref="A05:2021"
        )
