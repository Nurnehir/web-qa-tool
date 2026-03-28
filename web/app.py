"""
LynxTest Flask Web Uygulaması

Tek sayfalık web arayüzü ile URL analizi ve test senaryosu üretimi.
Server-Sent Events (SSE) ile canlı ilerleme gösterimi.
"""

import json
import os
import sys
import queue
import threading
from datetime import datetime
from flask import Flask, render_template, request, Response, jsonify, stream_with_context

# Proje kök dizinini ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import CloudflareCrawler, PageSaver
from analyzer import AnalyzerRunner
from llm.runner import LLMRunner
from reporter import JSONReporter, HTMLReporter

app = Flask(__name__)

# Global durum değişkenleri
analysis_status = {
    "running": False,
    "current_step": 0,
    "total_steps": 4,
    "message": "",
    "progress": 0,
    "error": None,
    "completed": False,
    "results": None
}

# SSE mesaj kuyruğu
message_queue = queue.Queue()


def load_config():
    """Konfigürasyon dosyasını yükler."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def send_event(step: int, title: str, status: str, progress: int, message: str, data: dict = None):
    """SSE mesajı gönderir."""
    event_data = {
        "step": step,
        "title": title,
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "data": data or {}
    }
    message_queue.put(json.dumps(event_data, ensure_ascii=False))


def clear_output_folder():
    """Output klasörünü temizler."""
    output_dirs = ["output/pages", "output/analysis", "output/scenarios"]
    for dir_path in output_dirs:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), dir_path)
        if os.path.exists(full_path):
            for file in os.listdir(full_path):
                if file.endswith(".json"):
                    os.remove(os.path.join(full_path, file))


def run_analysis(target_url: str, max_pages: int):
    """
    Analiz işlemini arka planda çalıştırır.
    
    Args:
        target_url: Analiz edilecek URL
        max_pages: Maksimum sayfa sayısı
    """
    global analysis_status
    
    try:
        config = load_config()
        if not config:
            send_event(0, "Hata", "error", 0, "config.json dosyası bulunamadı!")
            analysis_status["error"] = "config.json bulunamadı"
            analysis_status["running"] = False
            return
        
        # Output klasörünü temizle
        clear_output_folder()
        
        # ═══════════════════════════════════════════════════════════
        # ADIM 1: CRAWLING
        # ═══════════════════════════════════════════════════════════
        analysis_status["current_step"] = 1
        send_event(1, "Web Sitesi Taranıyor", "running", 5, "Cloudflare Browser Rendering başlatılıyor...")
        
        crawler = CloudflareCrawler(
            token=config["cloudflare_token"],
            account_id=config["cloudflare_account_id"]
        )
        
        # Crawl başlat
        send_event(1, "Web Sitesi Taranıyor", "running", 10, f"Tarama başlatıldı: {target_url}")
        
        crawl_result = crawler.crawl(target_url=target_url, max_pages=max_pages)
        
        if not crawl_result:
            send_event(1, "Web Sitesi Taranıyor", "error", 15, "Tarama başarısız!")
            analysis_status["error"] = "Crawling başarısız"
            analysis_status["running"] = False
            return
        
        # Sayfaları kaydet
        saver = PageSaver()
        saved_pages = saver.save_pages(crawl_result)
        
        if not saved_pages:
            send_event(1, "Web Sitesi Taranıyor", "error", 20, "Sayfa kaydedilemedi!")
            analysis_status["error"] = "Sayfa kaydedilemedi"
            analysis_status["running"] = False
            return
        
        send_event(1, "Web Sitesi Taranıyor", "completed", 25, 
                   f"✓ Tarama tamamlandı: {len(saved_pages)} sayfa bulundu",
                   {"pages_count": len(saved_pages)})
        
        # ═══════════════════════════════════════════════════════════
        # ADIM 2: STATİK ANALİZ
        # ═══════════════════════════════════════════════════════════
        analysis_status["current_step"] = 2
        send_event(2, "Statik Analiz", "running", 30, "Güvenlik, Link ve SEO analizi başlatılıyor...")
        
        analyzer = AnalyzerRunner()
        analysis_files = analyzer.run()
        
        send_event(2, "Statik Analiz", "completed", 50,
                   f"✓ Analiz tamamlandı: {len(analysis_files)} sayfa analiz edildi",
                   {"analyzed_count": len(analysis_files)})
        
        # ═══════════════════════════════════════════════════════════
        # ADIM 3: LLM İLE SENARYO ÜRETİMİ
        # ═══════════════════════════════════════════════════════════
        analysis_status["current_step"] = 3
        send_event(3, "Test Senaryosu Üretimi", "running", 55, "Llama3 ile test senaryoları üretiliyor...")
        
        llm_runner = LLMRunner(
            ollama_url=config.get("ollama_url", "http://localhost:11434"),
            model=config.get("ollama_model", "llama3")
        )
        
        # Ollama kontrolü
        if not llm_runner.ollama_client.is_available():
            send_event(3, "Test Senaryosu Üretimi", "warning", 60, 
                       "⚠️ Ollama sunucusuna erişilemiyor. Senaryo üretimi atlanıyor.")
            scenario_files = []
        else:
            scenario_files = llm_runner.run()
            send_event(3, "Test Senaryosu Üretimi", "completed", 75,
                       f"✓ Senaryo üretimi tamamlandı: {len(scenario_files)} dosya oluşturuldu",
                       {"scenarios_count": len(scenario_files)})
        
        # ═══════════════════════════════════════════════════════════
        # ADIM 4: RAPORLAMA
        # ═══════════════════════════════════════════════════════════
        analysis_status["current_step"] = 4
        send_event(4, "Rapor Oluşturma", "running", 80, "JSON ve HTML raporları hazırlanıyor...")
        
        # JSON rapor
        json_reporter = JSONReporter()
        json_report_path = json_reporter.generate()
        
        # HTML rapor
        html_reporter = HTMLReporter()
        html_report_path = html_reporter.generate()
        
        send_event(4, "Rapor Oluşturma", "completed", 100,
                   "✓ Raporlar hazır!",
                   {"json_report": json_report_path, "html_report": html_report_path})
        
        # ═══════════════════════════════════════════════════════════
        # TAMAMLANDI
        # ═══════════════════════════════════════════════════════════
        
        # Rapor verilerini oku
        try:
            with open(json_report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        except:
            report_data = {}
        
        analysis_status["completed"] = True
        analysis_status["results"] = {
            "pages_count": len(saved_pages),
            "analyzed_count": len(analysis_files),
            "scenarios_count": len(scenario_files) if scenario_files else 0,
            "summary": report_data.get("summary", {}),
            "json_report": json_report_path,
            "html_report": html_report_path
        }
        
        send_event(0, "İşlem Tamamlandı", "success", 100, 
                   "🎉 Tüm işlemler başarıyla tamamlandı!",
                   analysis_status["results"])
        
    except Exception as e:
        send_event(0, "Hata", "error", 0, f"❌ Beklenmeyen hata: {str(e)}")
        analysis_status["error"] = str(e)
    
    finally:
        analysis_status["running"] = False


@app.route("/")
def index():
    """Ana sayfa."""
    config = load_config()
    default_url = config.get("target_url", "") if config else ""
    default_max_pages = config.get("max_pages", 10) if config else 10
    
    return render_template("index.html", 
                           default_url=default_url,
                           default_max_pages=default_max_pages)


@app.route("/analyze", methods=["POST"])
def analyze():
    """Analiz işlemini başlatır."""
    global analysis_status
    
    if analysis_status["running"]:
        return jsonify({"error": "Bir analiz zaten devam ediyor"}), 400
    
    data = request.get_json()
    target_url = data.get("url", "").strip()
    max_pages = int(data.get("max_pages", 10))
    
    if not target_url:
        return jsonify({"error": "URL gerekli"}), 400
    
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url
    
    # Durumu sıfırla
    analysis_status = {
        "running": True,
        "current_step": 0,
        "total_steps": 4,
        "message": "",
        "progress": 0,
        "error": None,
        "completed": False,
        "results": None
    }
    
    # Kuyruğu temizle
    while not message_queue.empty():
        try:
            message_queue.get_nowait()
        except:
            break
    
    # Arka plan thread'i başlat
    thread = threading.Thread(target=run_analysis, args=(target_url, max_pages))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "url": target_url})


@app.route("/stream")
def stream():
    """Server-Sent Events stream'i."""
    def generate():
        while True:
            try:
                # Kuyruktan mesaj al (5 saniye timeout)
                message = message_queue.get(timeout=5)
                yield f"data: {message}\n\n"
                
                # Tamamlandıysa döngüden çık
                data = json.loads(message)
                if data.get("status") in ["success", "error"] and data.get("step") == 0:
                    break
                    
            except queue.Empty:
                # Heartbeat gönder
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/status")
def status():
    """Mevcut analiz durumunu döner."""
    return jsonify(analysis_status)


@app.route("/results")
def results():
    """Son analiz sonuçlarını döner - yeni UI formatında."""
    if not analysis_status["completed"]:
        return jsonify({"error": "Henüz tamamlanmış bir analiz yok"}), 404
    
    result_data = analysis_status.get("results", {})
    summary = result_data.get("summary", {})
    
    # Summary içindeki nested yapıyı çöz
    average_scores = summary.get("average_scores", {})
    grades = summary.get("grades", {})
    
    # Yeni UI formatında sonuçlar
    return jsonify({
        "total_pages": summary.get("total_pages", result_data.get("pages_count", 0)),
        "analyzed_pages": summary.get("pages_analyzed", result_data.get("analyzed_count", 0)),
        "total_scenarios": summary.get("total_scenarios", 0),
        "total_broken_links": summary.get("total_broken_links", 0),
        "security_score": average_scores.get("security", 0),
        "seo_score": average_scores.get("seo", 0),
        "overall_score": average_scores.get("overall", 0),
        "security_grade": grades.get("security", "F"),
        "seo_grade": grades.get("seo", "F"),
        "overall_grade": grades.get("overall", "C")
    })


@app.route("/report")
def report():
    """HTML raporunu döner."""
    report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "report.html")
    
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    
    return "Rapor bulunamadı", 404


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗  ██╗   ██╗███╗   ██╗██╗  ██╗████████╗███████╗███████╗  ║
║   ██║  ╚██╗ ██╔╝████╗  ██║╚██╗██╔╝╚══██╔══╝██╔════╝██╔════╝  ║
║   ██║   ╚████╔╝ ██╔██╗ ██║ ╚███╔╝    ██║   █████╗  ███████╗  ║
║   ██║    ╚██╔╝  ██║╚██╗██║ ██╔██╗    ██║   ██╔══╝  ╚════██║  ║
║   ███████╗██║   ██║ ╚████║██╔╝ ██╗   ██║   ███████╗███████║  ║
║   ╚══════╝╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝  ║
║                                                               ║
║                    🌐 Web Arayüzü                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    print("[SERVER] http://localhost:5000 adresinde çalışıyor...")
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
