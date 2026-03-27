from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Float, Enum, JSON
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class JobStatus(enum.Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class Job(Base):
    """Bir analiz işini temsil eder."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    target_url = Column(String(2048), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    pages = relationship("Page", back_populates="job")


class Page(Base):
    """Crawl edilen her sayfa."""
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    html_content = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)
    page_type = Column(String(50), nullable=True)   # login, form, listing vs.
    quality_score = Column(Float, nullable=True)    # 0–100
    crawled_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="pages")
    findings = relationship("Finding", back_populates="page")
    scenarios = relationship("TestScenario", back_populates="page")


class FindingSeverity(enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(Base):
    """Statik analiz bulgusu — bir sayfada tespit edilen sorun."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    category = Column(String(50), nullable=False)    # security, seo, link, accessibility
    check_name = Column(String(100), nullable=False)
    severity = Column(Enum(FindingSeverity), default=FindingSeverity.INFO)
    status = Column(String(10), nullable=False)      # pass, warn, fail
    detail = Column(Text, nullable=True)
    owasp_ref = Column(String(50), nullable=True)

    page = relationship("Page", back_populates="findings")


class ScenarioPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TestScenario(Base):
    """LLM tarafından üretilen test senaryosu."""
    __tablename__ = "test_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    scenario_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)     # functional, security, boundary, ux
    preconditions = Column(Text, nullable=True)
    steps = Column(JSON, nullable=True)
    expected_result = Column(Text, nullable=True)
    priority = Column(Enum(ScenarioPriority), default=ScenarioPriority.MEDIUM)
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="scenarios")
