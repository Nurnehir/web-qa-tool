"""
LynxTest - Ana Uygulama

Cloudflare Browser Rendering API tabanlı,
Llama3 destekli otomatik web test senaryosu üretim aracı.

Kullanım:
    python main.py

Gereksinimler:
    - config.json dosyası (Cloudflare token ve ayarlar)
    - Ollama kurulu ve llama3 modeli indirilmiş olmalı
"""

import json
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Modülleri import et
from crawler import CloudflareCrawler, PageSaver
from analyzer import AnalyzerRunner
from llm.runner import LLMRunner
from reporter import JSONReporter, HTMLReporter


def _load_page_files(pages_dir: str = "output/pages") -> list:
    """Kaydedilmiş sayfa JSON kayıtlarını yükler."""
    pages = []
    if not os.path.isdir(pages_dir):
        return pages
    for filename in sorted(os.listdir(pages_dir)):
        if not (filename.startswith("page_") and filename.endswith(".json")):
            continue
        file_path = os.path.join(pages_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            payload["_file"] = filename
            pages.append(payload)
        except Exception:
            continue
    return pages


def _count_ui_elements(pages: list) -> dict:
    """Toplam form/button/input sayısını hesaplar."""
    import re

    forms = 0
    buttons = 0
    inputs = 0
    for page in pages:
        html = page.get("html") or ""
        if not html:
            continue
        forms += len(re.findall(r"<form\b", html, flags=re.IGNORECASE))
        buttons += len(re.findall(r"<button\b", html, flags=re.IGNORECASE))
        inputs += len(re.findall(r"<input\b", html, flags=re.IGNORECASE))
    return {"forms": forms, "buttons": buttons, "inputs": inputs}


def _build_crawl_graph(pages: list, target_url: str) -> dict:
    """Sayfalar arası basit crawl graph üretir."""
    import re

    target_host = (urlparse(target_url).hostname or "").lower().replace("www.", "")
    nodes = []
    edges = []
    url_to_node_id = {}

    for idx, page in enumerate(pages, start=1):
        page_url = page.get("url") or ""
        node_id = f"page_{idx:03d}"
        node = {
            "id": node_id,
            "url": page_url,
            "title": page.get("title", ""),
            "status_code": page.get("status_code", 0)
        }
        nodes.append(node)
        if page_url:
            url_to_node_id[page_url.rstrip("/")] = node_id

    for idx, page in enumerate(pages, start=1):
        source_id = f"page_{idx:03d}"
        source_url = page.get("url") or ""
        html = page.get("html") or ""
        if not source_url or not html:
            continue
        raw_links = re.findall(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE)
        seen = set()
        for raw_link in raw_links:
            if raw_link.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(source_url, raw_link).split("#")[0].rstrip("/")
            if not absolute or absolute in seen:
                continue
            seen.add(absolute)
            host = (urlparse(absolute).hostname or "").lower().replace("www.", "")
            if host != target_host:
                continue
            target_id = url_to_node_id.get(absolute)
            if not target_id:
                continue
            edges.append({
                "source": source_id,
                "target": target_id,
                "url": absolute
            })

    return {
        "website": target_url,
        "generated_at": datetime.now().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges)
        }
    }


def _build_discovered_links(pages: list, target_url: str) -> dict:
    """Taramada görülen linklerin özet listesini üretir."""
    import re

    target_host = (urlparse(target_url).hostname or "").lower().replace("www.", "")
    all_links = set()
    internal_links = set()
    external_links = set()

    for page in pages:
        source_url = page.get("url") or ""
        html = page.get("html") or ""
        if not source_url or not html:
            continue
        raw_links = re.findall(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE)
        for raw_link in raw_links:
            if raw_link.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(source_url, raw_link).split("#")[0].rstrip("/")
            if not absolute:
                continue
            all_links.add(absolute)
            host = (urlparse(absolute).hostname or "").lower().replace("www.", "")
            if host == target_host:
                internal_links.add(absolute)
            else:
                external_links.add(absolute)

    return {
        "website": target_url,
        "generated_at": datetime.now().isoformat(),
        "totals": {
            "all": len(all_links),
            "internal": len(internal_links),
            "external": len(external_links)
        },
        "links": {
            "internal": sorted(internal_links),
            "external": sorted(external_links)
        }
    }


def _build_page_index(pages: list) -> dict:
    """Sayfaların hızlı indeksini üretir."""
    items = []
    for idx, page in enumerate(pages, start=1):
        items.append({
            "id": idx,
            "file": f"page_{idx:03d}.json",
            "url": page.get("url", ""),
            "title": page.get("title", ""),
            "status_code": page.get("status_code", 0),
            "has_content": bool(page.get("html"))
        })
    return {
        "generated_at": datetime.now().isoformat(),
        "total_pages": len(items),
        "pages": items
    }


def _write_additional_outputs(
    target_url: str,
    duration_seconds: float,
    crawl_result: dict,
    json_report_path: str
) -> None:
    """
    Ek çıktı dosyalarını üretir:
    - crawl_phase1.json
    - crawl_phase1_summary.txt
    - discovered_links.json
    - page_index.json
    - crawl_graph.json
    - report.json içine summary_table alanı
    """
    output_dir = os.path.dirname(json_report_path) or "output"
    os.makedirs(output_dir, exist_ok=True)

    pages = _load_page_files()
    ui_counts = _count_ui_elements(pages)
    crawl_graph = _build_crawl_graph(pages, target_url)
    discovered_links = _build_discovered_links(pages, target_url)
    page_index = _build_page_index(pages)

    # Crawl Phase-1 JSON
    phase1_json_path = os.path.join(output_dir, "crawl_phase1.json")
    phase1_payload = {
        "website": target_url,
        "generated_at": datetime.now().isoformat(),
        "crawl_time_seconds": round(duration_seconds, 2),
        "total_pages": len(pages),
        "crawl_result": crawl_result
    }
    with open(phase1_json_path, "w", encoding="utf-8") as f:
        json.dump(phase1_payload, f, ensure_ascii=False, indent=2)

    # Crawl Graph JSON
    crawl_graph_path = os.path.join(output_dir, "crawl_graph.json")
    with open(crawl_graph_path, "w", encoding="utf-8") as f:
        json.dump(crawl_graph, f, ensure_ascii=False, indent=2)

    # Discovered links JSON
    discovered_links_path = os.path.join(output_dir, "discovered_links.json")
    with open(discovered_links_path, "w", encoding="utf-8") as f:
        json.dump(discovered_links, f, ensure_ascii=False, indent=2)

    # Page index JSON
    page_index_path = os.path.join(output_dir, "page_index.json")
    with open(page_index_path, "w", encoding="utf-8") as f:
        json.dump(page_index, f, ensure_ascii=False, indent=2)

    # report.json içerisine Summary Table alanı ekle
    report_data = {}
    try:
        with open(json_report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    except Exception:
        report_data = {}

    summary = report_data.get("summary", {})
    summary_row = {
        "website": target_url,
        "total_pages": int(summary.get("total_pages", len(pages)) or 0),
        "crawl_time": f"{duration_seconds:.1f}s",
        "broken_links": int(summary.get("total_broken_links", 0) or 0),
        "forms": ui_counts["forms"],
        "buttons": ui_counts["buttons"],
        "inputs": ui_counts["inputs"]
    }
    report_data["summary_table"] = [summary_row]
    report_data.setdefault("summary", {})
    report_data["summary"]["summary_table"] = [summary_row]

    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # Phase-1 summary TXT
    phase1_summary_path = os.path.join(output_dir, "crawl_phase1_summary.txt")
    with open(phase1_summary_path, "w", encoding="utf-8") as f:
        f.write("Summary Table:\n")
        f.write("website | total_pages | crawl_time | broken_links | forms | buttons | inputs\n")
        f.write(
            f"{summary_row['website']} | {summary_row['total_pages']} | {summary_row['crawl_time']} | "
            f"{summary_row['broken_links']} | {summary_row['forms']} | {summary_row['buttons']} | {summary_row['inputs']}\n"
        )


def load_config(config_path: str = "config.json") -> dict:
    """
    Konfigürasyon dosyasını yükler.
    
    Args:
        config_path: Konfigürasyon dosyası yolu
        
    Returns:
        Konfigürasyon sözlüğü
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[HATA] Konfigürasyon dosyası bulunamadı: {config_path}")
        print("[BİLGİ] Lütfen config.json dosyasını oluşturun.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[HATA] Konfigürasyon dosyası geçersiz JSON: {e}")
        sys.exit(1)


def print_banner():
    """Başlık banner'ını yazdırır."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗  ██╗   ██╗███╗   ██╗██╗  ██╗████████╗███████╗███████╗  ║
║   ██║  ╚██╗ ██╔╝████╗  ██║╚██╗██╔╝╚══██╔══╝██╔════╝██╔════╝  ║
║   ██║   ╚████╔╝ ██╔██╗ ██║ ╚███╔╝    ██║   █████╗  ███████╗  ║
║   ██║    ╚██╔╝  ██║╚██╗██║ ██╔██╗    ██║   ██╔══╝  ╚════██║  ║
║   ███████╗██║   ██║ ╚████║██╔╝ ██╗   ██║   ███████╗███████║  ║
║   ╚══════╝╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝  ║
║                                                               ║
║   Cloudflare Browser Rendering & Llama3 Destekli             ║
║   Otomatik Web Test Senaryosu Üretim Aracı                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_step(step_num: int, title: str):
    """Adım başlığını yazdırır."""
    print(f"\n{'='*60}")
    print(f"  ADIM {step_num}: {title}")
    print(f"{'='*60}\n")


def main():
    """Ana uygulama fonksiyonu."""
    start_time = datetime.now()

    # Konfigürasyonu yükle
    config = load_config()
    quiet_mode = config.get("quiet_mode", True)
    verbose_mode = not quiet_mode
    if not quiet_mode:
        print_banner()
    
    print(f"[BİLGİ] Hedef URL: {config['target_url']}")
    print(f"[BİLGİ] Maksimum sayfa: {config['max_pages']}")
    print(f"[BİLGİ] LLM Modeli: {config['ollama_model']}")
    
    # ═══════════════════════════════════════════════════════════
    # ADIM 1: CRAWLING
    # ═══════════════════════════════════════════════════════════
    print_step(1, "WEB SİTESİ TARAMA (Cloudflare Browser Rendering)")
    
    crawler = CloudflareCrawler(
        token=config["cloudflare_token"],
        account_id=config["cloudflare_account_id"],
        verbose=verbose_mode
    )
    
    crawl_result = crawler.crawl(
        target_url=config["target_url"],
        max_pages=config["max_pages"],
        depth=config.get("crawl_depth", 3),
        include_subdomains=config.get("include_subdomains", True),
        include_external_links=config.get("include_external_links", False),
        formats=config.get("crawl_formats", ["html", "markdown"]),
        render=config.get("render", True)
    )
    
    if not crawl_result:
        print("[HATA] Tarama başarısız! İşlem sonlandırılıyor.")
        sys.exit(1)
    
    # Sayfaları kaydet
    saver = PageSaver(
        fallback_fetch_skipped=config.get("fallback_fetch_skipped", True),
        fallback_timeout=config.get("fallback_timeout", 15.0),
        verbose=verbose_mode
    )
    saver.clear_output()  # Önceki verileri temizle
    
    # Analiz ve senaryo klasörlerini de temizle
    for folder in ["output/analysis", "output/scenarios"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".json"):
                    os.remove(os.path.join(folder, f))
            if verbose_mode:
                print(f"[MAIN] Klasör temizlendi: {folder}")
    
    saved_pages = saver.save_pages(crawl_result)
    
    if not saved_pages:
        print("[HATA] Sayfa kaydedilemedi! İşlem sonlandırılıyor.")
        sys.exit(1)
    
    print(f"\n[OK] Tarama tamamlandı: {len(saved_pages)} sayfa kaydedildi")
    
    # ═══════════════════════════════════════════════════════════
    # ADIM 2: STATİK ANALİZ
    # ═══════════════════════════════════════════════════════════
    print_step(2, "STATİK ANALİZ (Güvenlik, Link, SEO)")
    
    analyzer = AnalyzerRunner(
        verbose=verbose_mode,
        link_checker_options={
            "max_links_per_page": config.get("max_links_per_page", 150),
            "check_asset_links": config.get("check_asset_links", False),
            "max_retries": config.get("link_max_retries", 1)
        }
    )
    analysis_files = analyzer.run()
    analyzed_count = 0
    skipped_count = 0
    for analysis_file in analysis_files:
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            status = data.get("analysis_status")
            if status in ("analyzed", None):
                analyzed_count += 1
            else:
                skipped_count += 1
        except Exception:
            continue
    
    if not analysis_files:
        print("[UYARI] Hiçbir sayfa analiz edilemedi.")
    else:
        print(f"\n[OK] Analiz tamamlandı: {analyzed_count} analiz edildi, {skipped_count} atlandı")
    
    # ═══════════════════════════════════════════════════════════
    # ADIM 3: LLM İLE SENARYO ÜRETİMİ
    # ═══════════════════════════════════════════════════════════
    print_step(3, "TEST SENARYOSU ÜRETİMİ (Llama3)")
    
    llm_runner = LLMRunner(
        ollama_url=config["ollama_url"],
        model=config["ollama_model"],
        verbose=verbose_mode,
        scenario_max_pages=config.get("scenario_max_pages", 0)
    )
    
    scenario_files = llm_runner.run()
    
    if not scenario_files:
        print("[UYARI] Test senaryosu üretilemedi.")
    else:
        print(f"\n[OK] Senaryo üretimi tamamlandı: {len(scenario_files)} dosya oluşturuldu")
    
    # ═══════════════════════════════════════════════════════════
    # ADIM 4: RAPORLAMA
    # ═══════════════════════════════════════════════════════════
    print_step(4, "RAPOR OLUŞTURMA")
    
    # JSON rapor
    json_reporter = JSONReporter()
    json_report_path = json_reporter.generate()

    # Ek çıktı dosyaları + Summary Table alanı
    elapsed_for_exports = (datetime.now() - start_time).total_seconds()
    _write_additional_outputs(
        target_url=config["target_url"],
        duration_seconds=elapsed_for_exports,
        crawl_result=crawl_result,
        json_report_path=json_report_path
    )
    
    # HTML rapor
    html_reporter = HTMLReporter()
    html_report_path = html_reporter.generate()

    # Terminal için global metrik özeti (quiet_mode'da da görünür)
    summary = {}
    try:
        with open(json_report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        summary = report_data.get("summary", {})
    except Exception:
        summary = {}
    
    # ═══════════════════════════════════════════════════════════
    # ÖZET
    # ═══════════════════════════════════════════════════════════
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("  İŞLEM TAMAMLANDI!")
    print("="*60)
    print(f"""
    📊 ÖZET
    ─────────────────────────────────────
    • Taranan sayfa sayısı  : {len(saved_pages)}
    • Analiz edilen sayfa   : {analyzed_count}
    • Atlanan sayfa         : {skipped_count}
    • Üretilen senaryo      : {len(scenario_files)} dosya
    • Toplam süre           : {duration:.1f} saniye
    
    📁 ÇIKTI DOSYALARI
    ─────────────────────────────────────
    • JSON Rapor : {json_report_path}
    • HTML Rapor : {html_report_path}
    
    💡 HTML raporu tarayıcıda açmak için:
       start {html_report_path.replace('/', chr(92))}
    """)

    if summary:
        avg = summary.get("average_scores", {})
        dq = summary.get("data_quality", {})
        print("    🔎 METRİK ÖZETİ")
        print("    ─────────────────────────────────────")
        print(f"    • Ortalama Güvenlik : {avg.get('security', 0)}%")
        print(f"    • Ortalama SEO      : {avg.get('seo', 0)}%")
        print(f"    • Ortalama Genel    : {avg.get('overall', 0)}%")
        print(f"    • Kalıcı Kırık Link : {summary.get('total_broken_strict', 0)}")
        print(f"    • Rate Limited      : {summary.get('total_rate_limited', 0)}")
        print(f"    • Geçici Ağ Hatası  : {summary.get('total_transient_network', 0)}")
        print(f"    • Coverage          : {dq.get('analysis_coverage_rate', 0)}%")


if __name__ == "__main__":
    main()
