from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import List, Set
import re


@dataclass
class CrawledPage:
    url: str
    content: str      # Markdown/düz metin içerik
    html: str         # Ham HTML
    status_code: int
    links: List[str]
    error: str = None


class PlaywrightCrawler:
    """
    Yerel headless Chromium ile web tarama.
    Cloudflare API'si gerekmez — tamamen yereldir.
    """

    def crawl(self, target_url: str, max_depth: int = 2,
              max_pages: int = 30) -> List[CrawledPage]:
        base_domain = urlparse(target_url).netloc
        visited: Set[str] = set()
        to_visit = [(target_url, 0)]
        results = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()

            while to_visit and len(results) < max_pages:
                url, depth = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                try:
                    response = page.goto(url, wait_until="networkidle", timeout=30000)
                    status_code = response.status if response else 0
                    html = page.content()
                    markdown = self._html_to_text(html)

                    # Sayfadaki aynı domain linkleri bul
                    links = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.href)"
                    )
                    same_domain_links = [
                        lnk for lnk in links
                        if urlparse(lnk).netloc == base_domain
                        and lnk not in visited
                    ]

                    results.append(CrawledPage(
                        url=url, content=markdown, html=html,
                        status_code=status_code,
                        links=same_domain_links
                    ))

                    if depth < max_depth:
                        for link in same_domain_links[:10]:
                            if link not in visited:
                                to_visit.append((link, depth + 1))

                except Exception as e:
                    print(f"[WARN] Sayfa atlandı: {url} — {e}")
                    results.append(CrawledPage(
                        url=url, content="", html="",
                        status_code=0, links=[], error=str(e)
                    ))

            browser.close()

        return results

    def _html_to_text(self, html: str) -> str:
        """Basit HTML → düz metin dönüşümü."""
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', html)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<[^>]+>', '', html)
        html = re.sub(r'\n{3,}', '\n\n', html)
        return html.strip()
