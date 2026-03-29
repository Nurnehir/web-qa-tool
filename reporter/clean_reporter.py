"""
Akademik kullanım için temiz rapor üretici.

Kaynak output/report.json verisini:
- hedef domain'e filtreler
- http/https duplicate sayfaları tekilleştirir
- metrikleri yeniden hesaplar
- clean JSON/HTML/CSV çıktıları üretir
"""

import csv
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


class CleanReporter:
    def __init__(
        self,
        source_json: str = "output/report.json",
        pages_dir: str = "output/pages",
        output_json: str = "output/report_clean.json",
        output_html: str = "output/report_clean.html",
        output_csv: str = "output/summary_table_clean.csv",
    ):
        self.source_json = source_json
        self.pages_dir = pages_dir
        self.output_json = output_json
        self.output_html = output_html
        self.output_csv = output_csv

    def generate(self, target_url: str) -> Dict[str, str]:
        print("[CLEAN_REPORTER] Clean rapor oluşturuluyor...")
        report = self._load_source()
        if not report:
            print("[CLEAN_REPORTER] HATA: Kaynak rapor yüklenemedi")
            return {}

        clean_report = self._build_clean_report(report, target_url)
        self._write_json(clean_report)
        self._write_csv(clean_report)
        self._write_html(clean_report)
        print(f"[CLEAN_REPORTER] JSON kaydedildi: {self.output_json}")
        print(f"[CLEAN_REPORTER] HTML kaydedildi: {self.output_html}")
        print(f"[CLEAN_REPORTER] CSV kaydedildi: {self.output_csv}")
        return {
            "json": self.output_json,
            "html": self.output_html,
            "csv": self.output_csv,
        }

    def _load_source(self) -> Dict[str, Any]:
        try:
            with open(self.source_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _canonical_host(self, url: str) -> str:
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    def _canonical_page_key(self, url: str) -> str:
        parsed = urlparse(url)
        host = self._canonical_host(url)
        path = parsed.path or "/"
        path = path.rstrip("/") or "/"
        query = parsed.query or ""
        return f"{host}{path}?{query}"

    def _page_quality_rank(self, page: Dict[str, Any]) -> Tuple[int, int, float]:
        analysis = page.get("analysis", {}) or {}
        status = analysis.get("analysis_status")
        analyzed = 1 if status == "analyzed" else 0
        has_content = 1 if page.get("has_content") else 0
        overall = float((analysis.get("overall_score") or {}).get("score") or 0)
        return analyzed, has_content, overall

    def _merge_scenarios(self, base: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged = list(base or [])
        seen = set()
        for s in merged:
            key = (str(s.get("title", "")).strip().lower(), str(s.get("expected", "")).strip().lower())
            seen.add(key)
        for s in incoming or []:
            key = (str(s.get("title", "")).strip().lower(), str(s.get("expected", "")).strip().lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append(s)
        return merged

    def _select_and_dedupe_pages(self, pages: List[Dict[str, Any]], target_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        target_host = self._canonical_host(target_url)
        selected: Dict[str, Dict[str, Any]] = {}
        excluded_external = 0
        duplicate_removed = 0

        for page in pages:
            page_url = page.get("url", "")
            if self._canonical_host(page_url) != target_host:
                excluded_external += 1
                continue
            key = self._canonical_page_key(page_url)
            existing = selected.get(key)
            if not existing:
                selected[key] = page
                continue
            duplicate_removed += 1
            # Daha kaliteli kaydı koru, senaryoları birleştir.
            keep = existing
            other = page
            if self._page_quality_rank(page) > self._page_quality_rank(existing):
                keep = page
                other = existing
            keep["scenarios"] = self._merge_scenarios(keep.get("scenarios", []), other.get("scenarios", []))
            selected[key] = keep

        clean_pages = sorted(selected.values(), key=lambda p: p.get("url", ""))
        return clean_pages, {"excluded_external_pages": excluded_external, "removed_duplicates": duplicate_removed}

    def _compute_metrics(self, pages: List[Dict[str, Any]], target_host: str) -> Dict[str, Any]:
        total_pages = len(pages)
        analyzed_pages = 0
        skipped_pages = 0
        total_scenarios = 0
        security_scores: List[float] = []
        seo_scores: List[float] = []
        overall_scores: List[float] = []

        broken_real = 0
        access_restricted = 0
        transient_network = 0
        rate_limited = 0

        for page in pages:
            analysis = page.get("analysis", {}) or {}
            if analysis.get("analysis_status") == "analyzed":
                analyzed_pages += 1
            else:
                skipped_pages += 1

            headers = analysis.get("headers", {}) or {}
            seo = analysis.get("seo", {}) or {}
            overall = analysis.get("overall_score", {}) or {}
            if headers.get("score") is not None:
                security_scores.append(float(headers.get("score", 0)))
            if seo.get("score") is not None:
                seo_scores.append(float(seo.get("score", 0)))
            if overall.get("score") is not None:
                overall_scores.append(float(overall.get("score", 0)))

            total_scenarios += len(page.get("scenarios", []) or [])

            for item in analysis.get("broken_links", []) or []:
                link_url = item.get("url", "")
                if self._canonical_host(link_url) != target_host:
                    continue
                code = int(item.get("status_code") or 0)
                category = item.get("category")
                if category == "rate_limited" or code == 429:
                    rate_limited += 1
                    continue
                if category == "transient_network":
                    transient_network += 1
                    continue
                if code in (401, 403):
                    access_restricted += 1
                    continue
                if category == "broken_strict" or code in (404, 410):
                    broken_real += 1

        avg_security = round(sum(security_scores) / len(security_scores), 1) if security_scores else 0
        avg_seo = round(sum(seo_scores) / len(seo_scores), 1) if seo_scores else 0
        avg_overall = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0
        coverage = round((analyzed_pages / total_pages) * 100, 1) if total_pages else 0

        if avg_overall >= 80:
            final_grade = "A"
        elif avg_overall >= 60:
            final_grade = "B"
        elif avg_overall >= 40:
            final_grade = "C"
        else:
            final_grade = "D"

        return {
            "total_pages": total_pages,
            "pages_analyzed": analyzed_pages,
            "pages_skipped": skipped_pages,
            "total_scenarios": total_scenarios,
            "average_scores": {
                "security": avg_security,
                "seo": avg_seo,
                "overall": avg_overall,
            },
            "coverage_percentage": coverage,
            "broken_links": {
                "real_broken": broken_real,
                "access_restricted_401_403": access_restricted,
                "transient_network": transient_network,
                "rate_limited": rate_limited,
            },
            "final_grade": final_grade,
        }

    def _build_summary_table_row(
        self,
        source: Dict[str, Any],
        target_url: str,
        metrics: Dict[str, Any],
        pages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        existing = {}
        source_rows = source.get("summary_table") or (source.get("summary", {}) or {}).get("summary_table") or []
        if source_rows:
            existing = source_rows[0]
        forms, buttons, inputs = self._compute_ui_counts_from_raw_pages(target_url)
        if forms == 0 and buttons == 0 and inputs == 0:
            forms = existing.get("forms", 0)
            buttons = existing.get("buttons", 0)
            inputs = existing.get("inputs", 0)
        crawl_time = existing.get("crawl_time", "n/a")
        if crawl_time == "n/a":
            generated_at = (source.get("meta", {}) or {}).get("generated_at", "")
            crawl_time = generated_at[:19].replace("T", " ") if generated_at else "n/a"
        return {
            "website": target_url,
            "total_pages": len(pages),
            "crawl_time": crawl_time,
            "broken_links": metrics["broken_links"]["real_broken"],
            "forms": forms,
            "buttons": buttons,
            "inputs": inputs,
        }

    def _compute_ui_counts_from_raw_pages(self, target_url: str) -> Tuple[int, int, int]:
        if not os.path.isdir(self.pages_dir):
            return 0, 0, 0
        target_host = self._canonical_host(target_url)
        best_by_key: Dict[str, Dict[str, Any]] = {}
        for filename in sorted(os.listdir(self.pages_dir)):
            if not (filename.startswith("page_") and filename.endswith(".json")):
                continue
            path = os.path.join(self.pages_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    page = json.load(f)
            except Exception:
                continue
            page_url = page.get("url", "")
            if self._canonical_host(page_url) != target_host:
                continue
            key = self._canonical_page_key(page_url)
            current = best_by_key.get(key)
            if not current:
                best_by_key[key] = page
                continue
            if len(page.get("html", "") or "") > len(current.get("html", "") or ""):
                best_by_key[key] = page

        forms = 0
        buttons = 0
        inputs = 0
        for page in best_by_key.values():
            html = page.get("html", "") or ""
            if not html:
                continue
            forms += len(re.findall(r"<form\\b", html, flags=re.IGNORECASE))
            buttons += len(re.findall(r"<button\\b", html, flags=re.IGNORECASE))
            inputs += len(re.findall(r"<input\\b", html, flags=re.IGNORECASE))
        return forms, buttons, inputs

    def _build_clean_report(self, source: Dict[str, Any], target_url: str) -> Dict[str, Any]:
        source_pages = source.get("pages", []) or []
        target_host = self._canonical_host(target_url)
        clean_pages, filter_stats = self._select_and_dedupe_pages(source_pages, target_url)
        metrics = self._compute_metrics(clean_pages, target_host)
        summary_table = [self._build_summary_table_row(source, target_url, metrics, clean_pages)]

        return {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "tool": "LynxTest",
                "type": "academic_clean_report",
                "source_report": self.source_json,
            },
            "filters": {
                "target_domain": target_host,
                **filter_stats,
            },
            "summary": metrics,
            "summary_table": summary_table,
            "pages": clean_pages,
        }

    def _write_json(self, payload: Dict[str, Any]) -> None:
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _write_csv(self, payload: Dict[str, Any]) -> None:
        rows = payload.get("summary_table", [])
        headers = ["website", "total_pages", "crawl_time", "broken_links", "forms", "buttons", "inputs"]
        with open(self.output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in headers})

    def _write_html(self, payload: Dict[str, Any]) -> None:
        summary = payload.get("summary", {})
        broken = summary.get("broken_links", {})
        summary_row = (payload.get("summary_table") or [{}])[0]
        pages = payload.get("pages", [])
        generated = (payload.get("meta", {}) or {}).get("generated_at", "")
        title_time = generated[:19].replace("T", " ") if generated else "-"

        page_rows = []
        scenario_sections = []
        for p in pages:
            analysis = p.get("analysis", {}) or {}
            overall = (analysis.get("overall_score") or {}).get("score")
            security = (analysis.get("headers") or {}).get("score")
            seo = (analysis.get("seo") or {}).get("score")
            page_rows.append(
                f"<tr><td>{p.get('url','')}</td><td>{overall if overall is not None else '-'}</td>"
                f"<td>{security if security is not None else '-'}</td><td>{seo if seo is not None else '-'}</td></tr>"
            )
            scenarios = p.get("scenarios", []) or []
            if scenarios:
                items = []
                for s in scenarios[:8]:
                    items.append(
                        f"<li><strong>{s.get('title','')}</strong> "
                        f"({s.get('type','unknown')}, {s.get('priority','medium')})<br>"
                        f"<span>{s.get('expected','')}</span></li>"
                    )
                scenario_sections.append(
                    f"<div class='card'><h3>{p.get('title') or p.get('url')}</h3><ul>{''.join(items)}</ul></div>"
                )

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Academic Clean Report</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f5f7fb; color: #1f2937; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    .hero {{ background: linear-gradient(135deg, #0f172a, #1d4ed8); color: white; padding: 20px; border-radius: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }}
    .card {{ background: white; border-radius: 10px; padding: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-top: 14px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 14px; }}
    th {{ background: #eff6ff; }}
    h2 {{ margin-top: 24px; }}
    ul {{ margin: 0; padding-left: 20px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>Academic Clean Crawl Report</h1>
      <p>Generated: {title_time}</p>
      <p>Final Overall Score: {summary.get('average_scores', {}).get('overall', 0)} ({summary.get('final_grade', 'D')})</p>
    </div>

    <h2>Özet Tablo</h2>
    <table>
      <thead><tr><th>website</th><th>total_pages</th><th>crawl_time</th><th>broken_links</th><th>forms</th><th>buttons</th><th>inputs</th></tr></thead>
      <tbody><tr>
        <td>{summary_row.get('website','')}</td>
        <td>{summary_row.get('total_pages',0)}</td>
        <td>{summary_row.get('crawl_time','n/a')}</td>
        <td>{summary_row.get('broken_links',0)}</td>
        <td>{summary_row.get('forms',0)}</td>
        <td>{summary_row.get('buttons',0)}</td>
        <td>{summary_row.get('inputs',0)}</td>
      </tr></tbody>
    </table>

    <div class="grid">
      <div class="card"><strong>Toplam Senaryo</strong><div>{summary.get('total_scenarios', 0)}</div></div>
      <div class="card"><strong>Toplam Sayfa</strong><div>{summary.get('total_pages', 0)}</div></div>
      <div class="card"><strong>Analiz Edilen</strong><div>{summary.get('pages_analyzed', 0)}</div></div>
      <div class="card"><strong>Coverage</strong><div>{summary.get('coverage_percentage', 0)}%</div></div>
      <div class="card"><strong>Güvenlik Ort.</strong><div>{summary.get('average_scores', {}).get('security', 0)}%</div></div>
      <div class="card"><strong>SEO Ort.</strong><div>{summary.get('average_scores', {}).get('seo', 0)}%</div></div>
    </div>

    <h2>Kırık Link Özeti</h2>
    <table>
      <thead><tr><th>Gerçek Kırık (404/410)</th><th>Erişim Kısıtlı (401/403)</th><th>Geçici Ağ</th><th>Rate Limited</th></tr></thead>
      <tbody><tr>
        <td>{broken.get('real_broken', 0)}</td>
        <td>{broken.get('access_restricted_401_403', 0)}</td>
        <td>{broken.get('transient_network', 0)}</td>
        <td>{broken.get('rate_limited', 0)}</td>
      </tr></tbody>
    </table>

    <h2>Sayfa Bazlı Skorlar</h2>
    <table>
      <thead><tr><th>URL</th><th>Overall</th><th>Security</th><th>SEO</th></tr></thead>
      <tbody>{''.join(page_rows) if page_rows else '<tr><td colspan="4">Veri yok</td></tr>'}</tbody>
    </table>

    <h2>Test Senaryoları</h2>
    {''.join(scenario_sections) if scenario_sections else "<div class='card'>Senaryo bulunamadı</div>"}
  </div>
</body>
</html>"""
        with open(self.output_html, "w", encoding="utf-8") as f:
            f.write(html)
