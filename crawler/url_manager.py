from sqlalchemy.orm import Session
from db import crud, models
from typing import List


class URLManager:
    """
    Hangi URL'lerin tarandığını takip eder.
    Aynı URL'nin iki kez işlenmesini önler.
    """

    def __init__(self, db: Session, job_id: int):
        self.db = db
        self.job_id = job_id
        self._visited: set = set()

    def is_visited(self, url: str) -> bool:
        return url in self._visited

    def mark_visited(self, url: str):
        self._visited.add(url)

    def save_page(self, url: str, html: str, markdown: str,
                  status_code: int) -> models.Page:
        self.mark_visited(url)
        return crud.save_page(
            db=self.db, job_id=self.job_id,
            url=url, html=html, markdown=markdown,
            http_status=status_code
        )

    def filter_new_urls(self, urls: List[str]) -> List[str]:
        return [u for u in urls if not self.is_visited(u)]
