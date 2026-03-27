"""
Web QA Tool - Proje Durum Raporu PDF Uretici
Calistir: python generate_report.py
"""
from fpdf import FPDF, XPos, YPos
from datetime import datetime


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "Web QA Tool - Proje Durum Raporu",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Sayfa {self.page_no()}  |  {datetime.today().strftime('%d.%m.%Y')}", align="C")

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(52, 73, 94)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, f"  {title}",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def sub_title(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(52, 73, 94)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, text)

    def check_row(self, label, detail, done=True):
        icon = "[TAMAM]" if done else "[KALDI]"
        color = (39, 174, 96) if done else (192, 57, 43)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*color)
        self.cell(20, 6, icon)
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "B", 9)
        self.cell(58, 6, label)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, detail)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Helvetica", "", 10)

# Giris
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 6,
    "Bu rapor, Otomatik Web Test Senaryosu Uretim Araci projesinin mevcut durumunu,\n"
    "tamamlanan ve tamamlanmasi gereken kisimlari ozetlemektedir.\n"
    "Tarih: " + datetime.today().strftime("%d.%m.%Y")
)

# 1. Mimari
pdf.section_title("1. Sistem Mimarisi")
pdf.body(
    "Sistem 6 katmandan olusmaktadir:\n"
    "  Katman 1  db/            : SQLite veritabani, SQLAlchemy ORM\n"
    "  Katman 2  crawler/       : Cloudflare Browser Rendering API + Playwright fallback\n"
    "  Katman 3  analyzer/      : Guvenlik, SEO, kirik link, skor hesaplama\n"
    "  Katman 4  llm_engine/    : Ollama + llama3, Jinja2 prompt sablonlari\n"
    "  Katman 5  orchestrator/  : Tum katmanlari birlestiren pipeline\n"
    "  Katman 6  api/           : FastAPI REST API"
)

# 2. Yapildi
pdf.section_title("2. Yapildi")

pdf.sub_title("Altyapi & Kurulum")
for label, detail in [
    ("Python 3.11 ortami", "Sanal ortam, requirements.txt, tum bagimliliklar kuruldu"),
    ("Cloudflare API", "Token alindi, .env kaydedildi, test edildi (aktif ve calisiyor)"),
    ("Ollama + llama3", "Kuruldu, ~4.7 GB model indirildi ve test edildi"),
    ("Playwright Chromium", "Indirildi, Cloudflare yoksa fallback olarak devreye giriyor"),
    ("SQLite", "Sunucu gerektirmiyor, uygulama baslarken tablolar otomatik olusturuluyor"),
    ("README.md", "Sifirdan kurulum kilavuzu yazildi (5 adimda kurulum)"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("Veritabani Katmani (db/)")
for label, detail in [
    ("models.py", "4 tablo: Job, Page, Finding, TestScenario"),
    ("session.py", "SQLite baglantisi, init_db() otomatik tablo olusturma"),
    ("crud.py", "Kaydet/sorgula fonksiyonlari, string->enum donusum hatasi duzeltildi"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("Crawler Katmani (crawler/)")
for label, detail in [
    ("cloudflare_client.py",
     "Async job: POST->poll->sonuc | Breadth-first coklu sayfa tarama\n"
     "                              URL normalizasyon (/index.html->/)\n"
     "                              Rate limit korumasi (1.5s bekleme, 429'da retry)"),
    ("playwright_client.py", "Yerel headless Chromium, Cloudflare olmadan calisir"),
    ("url_manager.py", "Ziyaret takibi, tekrar taramayi onleme"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("Analiz Katmani (analyzer/)")
for label, detail in [
    ("security_headers.py",
     "6 OWASP A05:2021 kontrolu: CSP, HSTS, X-Frame-Options,\n"
     "                              X-Content-Type, Referrer-Policy, Permissions-Policy\n"
     "                              Domain basina bir kez calisir (tum sayfalar paylasar)"),
    ("seo_checker.py",
     "10 SEO/erisebilirlik kontrolu: title, meta desc, h1, canonical,\n"
     "                              lang, robots meta, img alt, og:title/desc/image"),
    ("link_checker.py",
     "asyncio + aiohttp ile paralel kirik link tespiti (10 eszamanli istek)"),
    ("scorer.py",
     "Agirlikli kalite skoru (0-100): Guvenlik %40, SEO %30, Link %20, Erisebilirlik %10"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("LLM Katmani (llm_engine/)")
for label, detail in [
    ("page_classifier.py",
     "9 sayfa tipi: login, register, payment, listing, product_detail,\n"
     "                              contact_form, search, admin, generic\n"
     "                              Hata duzeltme: form varsa contact_form yanlisligi giderildi"),
    ("llm_client.py",
     "Ollama/llama3 istemcisi (OpenAI uyumlu API)\n"
     "                              Jinja2 ile sayfa tipine gore prompt secimi\n"
     "                              JSON parse hatasinda 2 deneme hakki"),
    ("base_prompt.j2", "Tum sayfa tipleri icin genel prompt sablonu"),
    ("login_page.j2",
     "Login sayfalari icin ozellestirilmis prompt\n"
     "                              (SQL injection, brute force, bos form, uzun girdi vb.)"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("Orkestrator & API")
for label, detail in [
    ("pipeline.py",
     "Senkron pipeline (Celery/Redis yok):\n"
     "                              1.Crawl -> 2.Analiz -> 3.Skor -> 4.LLM senaryo"),
    ("api/main.py",
     "4 endpoint: POST /analyze, GET /status/{id}, GET /report/{id}, GET /jobs"),
    ("api/schemas.py", "Pydantic giris/cikis modelleri"),
]:
    pdf.check_row(label, detail, done=True)

pdf.sub_title("Testler")
pdf.check_row("test_analyzer.py", "SecurityHeaders, SEOChecker, Scorer birim testleri", done=True)

# 3. Analizler
pdf.section_title("3. Calistirilan Analizler")
pdf.body("Sistem asagidaki sitelerde basariyla calistirildi ve sonuclar dogrulandi:")
pdf.ln(2)

widths = [65, 22, 28, 28, 35]
headers = ["Site", "Sayfa", "Senaryo", "Bulgu", "Durum"]
pdf.set_font("Helvetica", "B", 9)
pdf.set_fill_color(189, 195, 199)
for col, w in zip(headers, widths):
    pdf.cell(w, 7, col, border=1, fill=True)
pdf.ln()

pdf.set_font("Helvetica", "", 9)
rows = [
    ("books.toscrape.com", "5", "27", "85", "Basarili"),
    ("demoblaze.com", "2", "6", "17", "Basarili"),
]
for i, row in enumerate(rows):
    pdf.set_fill_color(255, 255, 255) if i % 2 == 0 else pdf.set_fill_color(245, 245, 245)
    for val, w in zip(row, widths):
        pdf.cell(w, 6, val, border=1, fill=True)
    pdf.ln()

pdf.ln(2)
pdf.set_font("Helvetica", "I", 8)
pdf.set_text_color(120, 120, 120)
pdf.multi_cell(0, 5,
    "Not: testphp.vulnweb.com erisim hatasi nedeniyle test edilemedi.\n"
    "demoblaze.com SPA oldugu icin bazi sayfalar (cart) tam render edilemedi.")
pdf.set_text_color(0, 0, 0)

# 4. Teknik Kalanlar
pdf.section_title("4. Teknik Kalanlar (Dusuk Oncelik)")
pdf.body("Sistem calismaktadir. Asagidakiler ek iyilestirmelerdir, zorunlu degildir.")
pdf.ln(2)

for label, detail, priority in [
    ("Prompt sablonlari",
     "register.j2, payment.j2, listing.j2, product_detail.j2\n"
     "Su an base_prompt.j2 kullaniliyor, sayfa tipine ozel yoksa genel prompt gidiyor",
     "Orta"),
    ("PDF / Excel export",
     "Raporlarin dosya olarak indirilebilmesi\n"
     "Su an JSON formatinda API'den aliniyor",
     "Dusuk"),
    ("Crawler & LLM testleri",
     "Birim testleri sadece analyzer icin yazildi\n"
     "Crawler ve LLM katmanlari icin test eksik",
     "Orta"),
]:
    self_x = pdf.get_x()
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(192, 57, 43)
    pdf.cell(20, 6, "[KALDI]")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(55, 6, label)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(20, 6, f"[{priority}]")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, detail)
    pdf.ln(1)

# 5. Akademik Kalanlar
pdf.section_title("5. Akademik Kalanlar (Bildiri icin Zorunlu)")
pdf.body(
    "Asagidaki adimlar teknik degil, akademik degerlendirme asamasidir.\n"
    "Bunlar olmadan bildiri tamamlanamaz:"
)

akademik = [
    (
        "1. En Az 3 Farkli Sitede Test (Bolum 8.1)",
        "Sistem en az 3 farkli web sitesinde calistirilmali ve su tablo doldurulmalidir:\n\n"
        "  Kolonlar: Site | Sayfa Sayisi | Guvenlik Sorunlari | Kirik Link |\n"
        "            SEO Sorunlari | Ort. Kalite Skoru | Sure | Senaryo Sayisi\n\n"
        "  books.toscrape.com -> TAMAM (5 sayfa, 27 senaryo, 85 bulgu)\n"
        "  Baska 2 site secilip calistirilmali (login+urun+form iceren siteler onerilir)"
    ),
    (
        "2. Mevcut Araclarla Karsilastirma (Bolum 8.2)",
        "Ayni site uzerinde asagidaki araclar calistirilmali ve sonuclar karsilastirilmali:\n\n"
        "  - OWASP ZAP (ucretsiz indir: zaproxy.org) -> guvenlik taramasi\n"
        "  - Google Lighthouse (Chrome DevTools -> Lighthouse) -> SEO/performans\n"
        "  - Screaming Frog (ucretsiz 500 URL limiti) -> link/SEO taramasi\n\n"
        "  Karsilastirilacak ozellikler:\n"
        "  Otomatik tarama | Guvenlik analizi | SEO analizi |\n"
        "  LLM tabanli test uretimi | Entegre akis"
    ),
    (
        "3. Senaryo Kalite Degerlendirmesi (Bolum 8.3)",
        "Uretilen test senaryolari 5 kisi tarafindan bagimsiz puanlanmali (1-5 arasi):\n\n"
        "  Kriterler:\n"
        "  - Ilgililik      : Senaryo sayfayla alakali mi?\n"
        "  - Uygulanabilirlik: Senaryo gercekten calistirilabilir mi?\n"
        "  - Kapsam         : Onemli test noktalarini kapsıyor mu?\n"
        "  - Netlik         : Adimlar anlasilir mi?\n"
        "  - Ozgunluk       : Sayfaya ozel mi, sablondan farkli mi?\n\n"
        "  Degerlendiriciler arasi uyum: Cohen's Kappa veya Fleiss' Kappa hesaplanmali.\n"
        "  Bu, bildiri icin guclu metodolojik katki saglar."
    ),
]

for baslik, aciklama in akademik:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(192, 57, 43)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, f"  {baslik}",
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    pdf.ln(1)
    pdf.multi_cell(0, 6, aciklama)

# 6. API & Baslatma
pdf.add_page()
pdf.section_title("6. Sistemi Calistirma")

pdf.sub_title("Baslatma (2 terminal)")
pdf.set_font("Courier", "", 8)
pdf.set_fill_color(30, 30, 30)
pdf.set_text_color(180, 255, 180)
pdf.multi_cell(0, 5,
    "# Terminal 1 - API\n"
    "cd web-qa-tool\n"
    "source .venv/bin/activate\n"
    "uvicorn api.main:app --reload --port 8000\n\n"
    "# Terminal 2 - LLM (llama3)\n"
    "ollama serve",
    fill=True
)
pdf.set_text_color(0, 0, 0)

pdf.ln(3)
pdf.sub_title("Analiz Baslat & Sorgula")
pdf.set_font("Courier", "", 8)
pdf.set_fill_color(30, 30, 30)
pdf.set_text_color(180, 255, 180)
pdf.multi_cell(0, 5,
    '# Analiz baslat\n'
    'curl -X POST http://localhost:8000/analyze \\\n'
    '  -H "Content-Type: application/json" \\\n'
    '  -d \'{"url": "https://hedefsite.com", "max_pages": 5}\'\n\n'
    '# Durum sorgula\n'
    'curl http://localhost:8000/status/1\n\n'
    '# Raporu al\n'
    'curl http://localhost:8000/report/1\n\n'
    '# Swagger UI (tarayici)\n'
    'http://localhost:8000/docs',
    fill=True
)
pdf.set_text_color(0, 0, 0)

pdf.ln(3)
pdf.sub_title("Git Commit Gecmisi")
commits = [
    ("616a1f8", "feat: initial project scaffold - all layers implemented"),
    ("1ebfe56", "fix: update CloudflareCrawler to match real async API"),
    ("fac98bf", "fix: enum conversion in crud + add README with setup guide"),
    ("20264c9", "feat: multi-page crawling with Cloudflare"),
    ("513648d", "fix: URL deduplication and domain-level security headers"),
    ("8f03a6d", "fix: page classifier priority order and listing detection"),
]
pdf.set_font("Courier", "", 9)
for sha, msg in commits:
    pdf.set_text_color(52, 152, 219)
    pdf.cell(20, 6, sha)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, msg, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(0, 0, 0)

# Kaydet
out = "/home/user/web-qa-tool/proje_durum_raporu.pdf"
pdf.output(out)
print(f"PDF olusturuldu: {out}")
