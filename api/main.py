from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db, init_db
from db import models
from api.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    JobStatusResponse, PageReport, FindingOut, ScenarioOut
)
from db import crud
from orchestrator.pipeline import run_analysis

app = FastAPI(
    title="Web QA Tool",
    description="Otomatik web test senaryosu üretim aracı — Playwright + llama3",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    """Uygulama başladığında SQLite tablolarını oluşturur."""
    init_db()


@app.post("/analyze", response_model=AnalyzeResponse)
def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Yeni bir analiz işi başlatır.
    İş arka planda çalışır; hemen job_id döner.
    """
    job = crud.create_job(db, target_url=str(request.url))
    background_tasks.add_task(
        run_analysis,
        job_id=job.id,
        target_url=str(request.url),
        max_depth=request.max_depth,
        max_pages=request.max_pages,
    )
    return AnalyzeResponse(
        job_id=job.id,
        status="pending",
        message=f"Analiz başlatıldı. Durum için: GET /status/{job.id}",
    )


@app.get("/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: int, db: Session = Depends(get_db)):
    """İş durumunu sorgular."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        target_url=job.target_url,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error_message,
    )


@app.get("/report/{job_id}")
def get_report(job_id: int, db: Session = Depends(get_db)):
    """Tamamlanmış analiz raporunu döndürür."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    if job.status != models.JobStatus.DONE:
        raise HTTPException(
            status_code=202,
            detail=f"Rapor henüz hazır değil. Durum: {job.status.value}",
        )

    pages_out = []
    for page in job.pages:
        pages_out.append(PageReport(
            url=page.url,
            http_status=page.http_status or 0,
            page_type=page.page_type or "unknown",
            quality_score=page.quality_score or 0.0,
            findings=[
                FindingOut(
                    category=f.category,
                    check_name=f.check_name,
                    severity=f.severity.value,
                    status=f.status,
                    detail=f.detail,
                    owasp_ref=f.owasp_ref,
                )
                for f in page.findings
            ],
            scenarios=[
                ScenarioOut(
                    name=s.scenario_name,
                    category=s.category or "",
                    preconditions=s.preconditions or "",
                    steps=s.steps or [],
                    expected_result=s.expected_result or "",
                    priority=s.priority.value,
                )
                for s in page.scenarios
            ],
        ))

    return {
        "job_id": job.id,
        "target_url": job.target_url,
        "status": job.status.value,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "total_pages": len(pages_out),
        "pages": pages_out,
    }


@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    """Tüm işleri listeler."""
    jobs = db.query(models.Job).order_by(models.Job.id.desc()).limit(50).all()
    return [
        {
            "job_id": j.id,
            "target_url": j.target_url,
            "status": j.status.value,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]
