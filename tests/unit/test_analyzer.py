import pytest
from unittest.mock import patch, MagicMock
from analyzer.security_headers import SecurityHeadersAnalyzer
from analyzer.seo_checker import SEOChecker
from analyzer.scorer import calculate_quality_score


class TestSecurityHeaders:

    def _mock_response(self, headers: dict):
        mock_resp = MagicMock()
        mock_resp.headers = headers
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
        mock_cm.__exit__ = MagicMock(return_value=False)
        return mock_cm

    def test_missing_csp_returns_fail(self):
        analyzer = SecurityHeadersAnalyzer()
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.headers = {"x-frame-options": "DENY"}
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            results = analyzer.analyze("https://example.com")
            csp = next(r for r in results if r.check_name == "content_security_policy")
            assert csp.status == "fail"
            assert csp.severity == "high"

    def test_unsafe_inline_csp_returns_warn(self):
        analyzer = SecurityHeadersAnalyzer()
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.headers = {
                "content-security-policy": "default-src 'self'; script-src 'unsafe-inline'"
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            results = analyzer.analyze("https://example.com")
            csp = next(r for r in results if r.check_name == "content_security_policy")
            assert csp.status == "warn"

    def test_missing_hsts_returns_fail(self):
        analyzer = SecurityHeadersAnalyzer()
        with patch("httpx.Client") as mock_client:
            mock_resp = MagicMock()
            mock_resp.headers = {}
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

            results = analyzer.analyze("https://example.com")
            hsts = next(r for r in results if r.check_name == "hsts")
            assert hsts.status == "fail"


class TestSEOChecker:

    GOOD_HTML = """
    <html lang="tr">
    <head>
        <title>Harika Bir Başlık — Site Adı</title>
        <meta name="description"
              content="Bu sayfa hakkında detaylı ve açıklayıcı bir meta açıklama metni.">
        <link rel="canonical" href="https://example.com/sayfa">
    </head>
    <body>
        <h1>Ana Başlık</h1>
        <img src="foto.jpg" alt="Açıklama">
    </body>
    </html>
    """

    BAD_HTML = """
    <html>
    <head></head>
    <body>
        <h1>İlk Başlık</h1>
        <h1>İkinci Başlık</h1>
        <img src="foto.jpg">
    </body>
    </html>
    """

    def test_good_page_has_no_failures(self):
        checker = SEOChecker()
        results = checker.analyze(self.GOOD_HTML, "https://example.com")
        failed = [r for r in results if r.status == "fail"]
        assert len(failed) == 0

    def test_multiple_h1_returns_warn(self):
        checker = SEOChecker()
        results = checker.analyze(self.BAD_HTML, "https://example.com")
        h1 = next(r for r in results if r.check_name == "h1_tag")
        assert h1.status == "warn"

    def test_missing_alt_returns_fail(self):
        checker = SEOChecker()
        results = checker.analyze(self.BAD_HTML, "https://example.com")
        img = next(r for r in results if r.check_name == "image_alt_attributes")
        assert img.status == "fail"

    def test_missing_title_returns_fail(self):
        checker = SEOChecker()
        results = checker.analyze(self.BAD_HTML, "https://example.com")
        title = next(r for r in results if r.check_name == "title_tag")
        assert title.status == "fail"


class TestScorer:

    def _make_finding(self, category: str, status: str):
        f = MagicMock()
        f.category = category
        f.status = status
        return f

    def test_all_pass_returns_100(self):
        findings = [
            self._make_finding("security", "pass"),
            self._make_finding("seo", "pass"),
            self._make_finding("link", "pass"),
        ]
        score = calculate_quality_score(findings)
        assert score == 100.0

    def test_all_fail_returns_0(self):
        findings = [
            self._make_finding("security", "fail"),
            self._make_finding("seo", "fail"),
        ]
        score = calculate_quality_score(findings)
        assert score == 0.0

    def test_mixed_returns_middle_value(self):
        findings = [
            self._make_finding("security", "pass"),
            self._make_finding("security", "fail"),
        ]
        score = calculate_quality_score(findings)
        assert 0 < score < 100
