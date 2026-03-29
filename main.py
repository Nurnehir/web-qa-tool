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

# Modülleri import et
from crawler import CloudflareCrawler, PageSaver
from analyzer import AnalyzerRunner
from llm.runner import LLMRunner
from reporter import JSONReporter, HTMLReporter


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
        verbose=verbose_mode
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
    
    # HTML rapor
    html_reporter = HTMLReporter()
    html_report_path = html_reporter.generate()
    
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


if __name__ == "__main__":
    main()
