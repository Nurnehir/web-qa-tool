"""
Ana pipeline — Celery/Redis yoktur, senkron çalışır.
FastAPI'nin background task mekanizması ile arka planda yürütülür.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db import crud, models
from analyzer.security_headers import SecurityHeadersAnalyzer
from analyzer.link_checker import LinkChecker
from analyzer.seo_checker import SEOChecker
from analyzer.scorer import calculate_quality_score
from llm_engine.page_classifier import PageClassifier
from llm_engine.llm_client import LLMClient


def run_analysis(job_id: int, target_url: str,
                 max_depth: int = 2, max_pages: int = 30):
    """
    Bir analiz işinin tüm adımlarını sırayla çalıştırır.
    FastAPI BackgroundTasks ile çağrılır — request thread'ini bloklamaz.
    """
    db: Session = SessionLocal()

    try:
        # ── 1. Crawling ────────────────────────────────────────────────────────
        crud.update_job_status(db, job_id, models.JobStatus.CRAWLING)
        print(f"[JOB {job_id}] Crawling başlıyor: {target_url}")

        # Cloudflare token varsa onu dene, yoksa Playwright kullan
        try:
            from crawler.cloudflare_client import CloudflareCrawler
            crawler = CloudflareCrawler()
            print(f"[JOB {job_id}] Cloudflare crawler kullanılıyor")
        except ValueError:
            from crawler.playwright_client import PlaywrightCrawler
            crawler = PlaywrightCrawler()
            print(f"[JOB {job_id}] Playwright crawler kullanılıyor")

        crawled_pages = crawler.crawl(target_url, max_depth=max_depth, max_pages=max_pages)
        print(f"[JOB {job_id}] {len(crawled_pages)} sayfa tarandı")

        # ── 2. Sayfaları veritabanına kaydet ───────────────────────────────────
        page_records = []
        for cp in crawled_pages:
            page = crud.save_page(
                db=db, job_id=job_id, url=cp.url,
                html=cp.html, markdown=cp.content,
                http_status=cp.status_code
            )
            page_records.append((page, cp))

        # ── 3. Statik analiz ───────────────────────────────────────────────────
        crud.update_job_status(db, job_id, models.JobStatus.ANALYZING)
        security_analyzer = SecurityHeadersAnalyzer()
        link_checker = LinkChecker()
        seo_checker = SEOChecker()
        classifier = PageClassifier()

        for page_record, cp in page_records:
            if cp.error:
                continue
            print(f"[JOB {job_id}] Analiz: {cp.url}")
            all_findings = []

            # Güvenlik başlıkları
            for r in security_analyzer.analyze(cp.url):
                f = crud.save_finding(
                    db=db, page_id=page_record.id,
                    category="security", check_name=r.check_name,
                    severity=r.severity, status=r.status,
                    detail=r.detail, owasp_ref=r.owasp_ref
                )
                all_findings.append(f)

            # Kırık link kontrolü
            if cp.html:
                link_results = link_checker.check_links(cp.html, cp.url)
                broken = [l for l in link_results if l.is_broken]
                status = "fail" if broken else "pass"
                detail = (
                    f"{len(broken)} kırık link: " + ", ".join(l.url for l in broken[:5])
                    if broken else f"{len(link_results)} link kontrol edildi, kırık yok."
                )
                f = crud.save_finding(
                    db=db, page_id=page_record.id,
                    category="link", check_name="broken_links",
                    severity="medium" if broken else "info",
                    status=status, detail=detail
                )
                all_findings.append(f)

            # SEO
            if cp.html:
                for r in seo_checker.analyze(cp.html, cp.url):
                    f = crud.save_finding(
                        db=db, page_id=page_record.id,
                        category="seo", check_name=r.check_name,
                        severity=r.severity, status=r.status, detail=r.detail
                    )
                    all_findings.append(f)

            # Kalite skoru ve sayfa tipi
            page_record.quality_score = calculate_quality_score(all_findings)
            if cp.html:
                page_record.page_type = classifier.classify(cp.html, cp.url)
            db.commit()

        # ── 4. LLM — senaryo üretimi ───────────────────────────────────────────
        crud.update_job_status(db, job_id, models.JobStatus.GENERATING)

        try:
            llm_client = LLMClient()
            llm_available = True
        except Exception as e:
            print(f"[WARN] LLM başlatılamadı (Ollama çalışıyor mu?): {e}")
            llm_available = False

        if llm_available:
            for page_record, cp in page_records:
                if not cp.content or cp.error:
                    continue
                print(f"[JOB {job_id}] LLM senaryo üretimi: {cp.url}")

                db_findings = (
                    db.query(models.Finding)
                    .filter(models.Finding.page_id == page_record.id)
                    .all()
                )

                try:
                    result = llm_client.generate_scenarios(
                        page_url=cp.url,
                        page_type=page_record.page_type or "generic",
                        markdown_content=cp.content,
                        findings=db_findings,
                        quality_score=page_record.quality_score or 0,
                    )
                    for s in result.get("scenarios", []):
                        crud.save_scenario(
                            db=db, page_id=page_record.id,
                            name=s.get("name", "İsimsiz senaryo"),
                            category=s.get("category", "functional"),
                            preconditions=s.get("preconditions", ""),
                            steps=s.get("steps", []),
                            expected=s.get("expected_result", ""),
                            priority=s.get("priority", "medium"),
                        )
                except Exception as e:
                    print(f"[WARN] LLM hatası ({cp.url}): {e}")
                    continue

        # ── 5. İş tamamlandı ───────────────────────────────────────────────────
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        job.status = models.JobStatus.DONE
        job.completed_at = datetime.utcnow()
        db.commit()
        print(f"[JOB {job_id}] Tamamlandı!")

    except Exception as e:
        crud.update_job_status(db, job_id, models.JobStatus.FAILED)
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if job:
            job.error_message = str(e)
            db.commit()
        print(f"[JOB {job_id}] HATA: {e}")
        raise

    finally:
        db.close()
