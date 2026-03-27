"""
Cloudflare Browser Rendering API — çoklu sayfa tarama.

Strateji:
  1. Başlangıç URL'ini /crawl ile render et
  2. HTML'den aynı domain linkleri çıkar (BeautifulSoup)
  3. Her linki sırayla /crawl ile render et (max_pages limitine kadar)
  4. Her istek arasında kısa bekleme (rate limit koruması)
"""
import httpx
import os
import time
import re
from dataclasses import dataclass, field
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


@dataclass
class CrawledPage:
    url: str
    content: str       # HTML'den türetilmiş düz metin
    html: str          # Ham HTML
    status_code: int
    links: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CloudflareCrawler:
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
    REQUEST_DELAY = 1.5   # İstekler arası bekleme (saniye) — rate limit koruması

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not self.api_token or not self.account_id:
            raise ValueError("CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID tanımlı değil")

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    @property
    def _endpoint(self):
        return f"{self.BASE_URL}/{self.account_id}/browser-rendering/crawl"

    def crawl(self, target_url: str, max_depth: int = 2,
              max_pages: int = 30) -> List[CrawledPage]:
        """
        Hedef siteyi breadth-first tarar.
        Her sayfa Cloudflare ile render edilir (JS dahil).
        """
        base_domain = urlparse(target_url).netloc
        visited: Set[str] = set()
        # Kuyruk: (url, derinlik)
        queue = [(target_url, 0)]
        results = []

        with httpx.Client(timeout=60.0) as client:
            while queue and len(results) < max_pages:
                url, depth = queue.pop(0)
                normalized = self._normalize_url(url)
                if normalized in visited:
                    continue
                visited.add(normalized)

                print(f"[Cloudflare] Taranıyor ({len(results)+1}/{max_pages}): {url}")
                page = self._render_page(client, url)

                if page is None:
                    continue

                results.append(page)

                # Daha derin tarama: bu sayfanın linklerini kuyruğa ekle
                if depth < max_depth and page.html:
                    links = self._extract_links(page.html, url, base_domain)
                    page.links = links
                    for link in links:
                        if self._normalize_url(link) not in visited:
                            queue.append((link, depth + 1))

                # Rate limit koruması
                if queue and len(results) < max_pages:
                    time.sleep(self.REQUEST_DELAY)

        print(f"[Cloudflare] Tamamlandı: {len(results)} sayfa tarandı")
        return results

    def _render_page(self, client: httpx.Client, url: str) -> Optional[CrawledPage]:
        """Tek bir sayfayı Cloudflare ile render eder."""
        try:
            resp = client.post(
                self._endpoint,
                json={"url": url},
                headers=self._headers,
            )
            resp.raise_for_status()
            job_id = resp.json().get("result")
            if not job_id:
                return None

            result = self._wait_for_job(client, job_id)
            if not result:
                return None

            # Tamamlanan ilk kaydı al
            records = result.get("records", [])
            completed = [r for r in records if r.get("status") == "completed"]
            if not completed:
                return None

            rec = completed[0]
            html = rec.get("html", "")
            meta = rec.get("metadata", {})

            return CrawledPage(
                url=rec.get("url", url),
                content=self._html_to_text(html),
                html=html,
                status_code=meta.get("status", 200),
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"[WARN] Rate limit — 10 saniye bekleniyor...")
                time.sleep(10)
                return self._render_page(client, url)  # Bir kez yeniden dene
            print(f"[WARN] HTTP hatası {url}: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"[WARN] Hata {url}: {e}")
            return None

    def _wait_for_job(self, client: httpx.Client, job_id: str,
                      max_wait: int = 60) -> Optional[dict]:
        """Cloudflare job tamamlanana kadar bekler."""
        endpoint = f"{self.BASE_URL}/{self.account_id}/browser-rendering/crawl/{job_id}"
        deadline = time.time() + max_wait

        while time.time() < deadline:
            try:
                resp = client.get(endpoint, headers=self._headers)
                resp.raise_for_status()
                data = resp.json().get("result", {})
                status = data.get("status", "")

                if status == "completed":
                    return data
                if status == "failed":
                    print(f"[WARN] Job başarısız: {job_id}")
                    return None

                time.sleep(2)
            except Exception:
                time.sleep(2)

        print(f"[WARN] Job zaman aşımı: {job_id}")
        return None

    def _normalize_url(self, url: str) -> str:
        """
        URL'yi normalleştirir — aynı sayfanın farklı yazımlarını birleştirir.
        Örnekler:
          books.toscrape.com        → books.toscrape.com/
          books.toscrape.com/       → books.toscrape.com/
          books.toscrape.com/index.html → books.toscrape.com/
          foo.com/bar/index.html    → foo.com/bar/
        """
        parsed = urlparse(url)
        path = parsed.path or "/"
        # /index.html veya /index.htm → üst dizin
        if path.endswith(("/index.html", "/index.htm")):
            path = path[: path.rfind("/") + 1]
        # Trailing slash — her zaman sonunda slash olsun
        if not path.endswith("/"):
            path = path + "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _extract_links(self, html: str, base_url: str, base_domain: str) -> List[str]:
        """HTML'den aynı domain'e ait linkleri çıkarır."""
        soup = BeautifulSoup(html, "lxml")
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https") and parsed.netloc == base_domain:
                # Fragment ve query string'i temizle (tekrar ziyareti önler)
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean not in links:
                    links.append(clean)
        return links[:20]  # Sayfa başına max 20 link

    def _html_to_text(self, html: str) -> str:
        """Basit HTML → düz metin."""
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', html)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<[^>]+>', '', html)
        html = re.sub(r'\n{3,}', '\n\n', html)
        return html.strip()
