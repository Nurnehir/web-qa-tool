import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


@dataclass
class LinkCheckResult:
    url: str
    status_code: int
    is_broken: bool
    error: str = None


class LinkChecker:
    """
    Sayfadaki tüm linkleri paralel olarak kontrol eder.
    """

    def __init__(self, concurrency: int = 10):
        self.concurrency = concurrency

    def extract_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            absolute = urljoin(base_url, href)
            if urlparse(absolute).scheme in ("http", "https"):
                links.append(absolute)
        return list(set(links))

    def check_links(self, html: str, base_url: str) -> List[LinkCheckResult]:
        """Senkron wrapper."""
        links = self.extract_links(html, base_url)
        if not links:
            return []
        return asyncio.run(self._check_all(links))

    async def _check_all(self, urls: List[str]) -> List[LinkCheckResult]:
        sem = asyncio.Semaphore(self.concurrency)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "WebQATool/1.0 LinkChecker"}
        ) as session:
            tasks = [self._check_one(session, sem, url) for url in urls]
            return await asyncio.gather(*tasks)

    async def _check_one(self, session, sem, url: str) -> LinkCheckResult:
        async with sem:
            try:
                async with session.head(url, allow_redirects=True) as resp:
                    return LinkCheckResult(
                        url=url, status_code=resp.status,
                        is_broken=resp.status >= 400
                    )
            except aiohttp.ClientConnectorError:
                return LinkCheckResult(url=url, status_code=0,
                                       is_broken=True, error="Bağlantı kurulamadı")
            except asyncio.TimeoutError:
                return LinkCheckResult(url=url, status_code=0,
                                       is_broken=True, error="Zaman aşımı")
            except Exception as e:
                return LinkCheckResult(url=url, status_code=0,
                                       is_broken=True, error=str(e))
