"""
Cloudflare Browser Rendering API ile tarama — opsiyonel.
CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID .env'de tanımlıysa kullanılır,
yoksa PlaywrightCrawler otomatik olarak devreye girer (bkz. orchestrator/pipeline.py).
"""
import httpx
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CrawledPage:
    url: str
    content: str
    html: str
    status_code: int
    links: List[str]
    error: Optional[str] = None


class CloudflareCrawler:
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts"

    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if not self.api_token or not self.account_id:
            raise ValueError("CLOUDFLARE_API_TOKEN ve CLOUDFLARE_ACCOUNT_ID tanımlı değil")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def crawl(self, target_url: str, max_depth: int = 2,
              max_pages: int = 30) -> List[CrawledPage]:
        endpoint = f"{self.BASE_URL}/{self.account_id}/browser-rendering/crawl"
        payload = {
            "url": target_url,
            "maxDepth": max_depth,
            "maxPages": max_pages,
            "renderJs": True,
            "outputFormat": "markdown",
            "followLinks": True,
            "sameDomainOnly": True,
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(endpoint, json=payload, headers=self._headers())
                response.raise_for_status()
                data = response.json()

            if not data.get("success"):
                raise RuntimeError(f"Cloudflare API hatası: {data.get('errors', [])}")

            return [
                CrawledPage(
                    url=p["url"],
                    content=p.get("content", ""),
                    html=p.get("html", ""),
                    status_code=p.get("statusCode", 0),
                    links=p.get("links", [])
                )
                for p in data["result"]["pages"]
            ]
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP hatası: {e.response.status_code} — {e.response.text}")
        except httpx.TimeoutException:
            raise RuntimeError("Cloudflare API zaman aşımı")
