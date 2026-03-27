"""
Cloudflare Browser Rendering API — async crawl (başlat → sonuç bekle).

Gerçek API davranışı:
  POST /crawl           → job_id döner
  GET  /crawl/{job_id} → status: pending | running | completed
"""
import httpx
import os
import time
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CrawledPage:
    url: str
    content: str       # Markdown/düz metin (HTML'den türetilir)
    html: str          # Ham HTML
    status_code: int
    links: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CloudflareCrawler:
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts"

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
    def _base(self):
        return f"{self.BASE_URL}/{self.account_id}/browser-rendering"

    def crawl(self, target_url: str, max_depth: int = 2,
              max_pages: int = 30) -> List[CrawledPage]:
        """
        Hedef siteyi tarar ve CrawledPage listesi döndürür.
        Cloudflare async çalışır: önce job başlatılır, sonra sonuç beklenir.
        """
        with httpx.Client(timeout=30.0) as client:
            # 1. Crawl işini başlat
            resp = client.post(
                f"{self._base}/crawl",
                json={"url": target_url},
                headers=self._headers,
            )
            resp.raise_for_status()
            job_id = resp.json()["result"]
            print(f"[Cloudflare] Crawl başlatıldı: {job_id}")

            # 2. Tamamlanmasını bekle (max 120 sn)
            result = self._wait_for_job(client, job_id, max_wait=120)

        return self._parse_records(result.get("records", []))

    def _wait_for_job(self, client: httpx.Client, job_id: str,
                      max_wait: int = 120) -> dict:
        """Job tamamlanana kadar polling yapar."""
        deadline = time.time() + max_wait
        interval = 3

        while time.time() < deadline:
            resp = client.get(
                f"{self._base}/crawl/{job_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json().get("result", {})
            status = data.get("status", "")
            print(f"[Cloudflare] Durum: {status} "
                  f"({data.get('finished', 0)}/{data.get('total', 0)} sayfa)")

            if status == "completed":
                return data
            if status == "failed":
                raise RuntimeError(f"Cloudflare crawl başarısız: {data}")

            time.sleep(interval)

        raise RuntimeError(f"Cloudflare crawl zaman aşımı ({max_wait}s)")

    def _parse_records(self, records: list) -> List[CrawledPage]:
        """Ham kayıtları CrawledPage listesine dönüştürür."""
        pages = []
        for rec in records:
            if rec.get("status") == "skipped":
                continue

            html = rec.get("html", "")
            meta = rec.get("metadata", {})
            pages.append(CrawledPage(
                url=rec.get("url", ""),
                content=self._html_to_text(html),
                html=html,
                status_code=meta.get("status", 0),
                links=[],   # Cloudflare yanıtında link listesi yok — HTML'den çıkarılacak
            ))
        return pages

    def _html_to_text(self, html: str) -> str:
        """Basit HTML → düz metin dönüşümü."""
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', html)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<[^>]+>', '', html)
        html = re.sub(r'\n{3,}', '\n\n', html)
        return html.strip()
