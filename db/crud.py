from sqlalchemy.orm import Session
from . import models


def create_job(db: Session, target_url: str) -> models.Job:
    job = models.Job(target_url=target_url)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_status(db: Session, job_id: int, status: models.JobStatus):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if job:
        job.status = status
        db.commit()


def save_page(db: Session, job_id: int, url: str, html: str,
              markdown: str, http_status: int) -> models.Page:
    page = models.Page(
        job_id=job_id, url=url, html_content=html,
        markdown_content=markdown, http_status=http_status
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def save_finding(db: Session, page_id: int, category: str,
                 check_name: str, severity: str, status: str,
                 detail: str, owasp_ref: str = None) -> models.Finding:
    # severity string'i enum objesine çevir ("high" → FindingSeverity.HIGH)
    severity_enum = models.FindingSeverity(severity.lower())
    finding = models.Finding(
        page_id=page_id, category=category, check_name=check_name,
        severity=severity_enum, status=status, detail=detail, owasp_ref=owasp_ref
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def save_scenario(db: Session, page_id: int, name: str, category: str,
                  preconditions: str, steps: list,
                  expected: str, priority: str) -> models.TestScenario:
    priority_enum = models.ScenarioPriority(priority.lower())
    scenario = models.TestScenario(
        page_id=page_id, scenario_name=name, category=category,
        preconditions=preconditions, steps=steps,
        expected_result=expected, priority=priority_enum
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def get_job_with_details(db: Session, job_id: int) -> models.Job:
    return db.query(models.Job).filter(models.Job.id == job_id).first()
