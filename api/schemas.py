from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 30
    max_depth: int = 2


class AnalyzeResponse(BaseModel):
    job_id: int
    status: str
    message: str


class FindingOut(BaseModel):
    category: str
    check_name: str
    severity: str
    status: str
    detail: str
    owasp_ref: Optional[str] = None


class ScenarioOut(BaseModel):
    name: str
    category: str
    preconditions: str
    steps: List[str]
    expected_result: str
    priority: str


class PageReport(BaseModel):
    url: str
    http_status: int
    page_type: str
    quality_score: float
    findings: List[FindingOut]
    scenarios: List[ScenarioOut]


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    target_url: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
