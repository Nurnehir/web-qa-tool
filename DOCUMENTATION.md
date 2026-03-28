# 🔍 LynxTest - Kapsamlı Proje Dokümantasyonu

> **Cloudflare Browser Rendering & Llama3 Destekli Otomatik Web Test Senaryosu Üretim Aracı**

---

## 📋 İçindekiler

1. [Proje Özeti](#-proje-özeti)
2. [Ne Yapıyor?](#-ne-yapıyor)
3. [Sistem Mimarisi](#-sistem-mimarisi)
4. [Dizin Yapısı](#-dizin-yapısı)
5. [Çalışma Akışı (Pipeline)](#-çalışma-akışı-pipeline)
6. [Modüller ve Dosyalar](#-modüller-ve-dosyalar)
7. [Konfigürasyon](#-konfigürasyon)
8. [Bağımlılıklar](#-bağımlılıklar)
9. [Kullanım](#-kullanım)
10. [Çıktılar](#-çıktılar)

---

## 🎯 Proje Özeti

**LynxTest**, bir web sitesini otomatik olarak tarayıp analiz eden ve yapay zeka kullanarak test senaryoları üreten bir QA (Quality Assurance) aracıdır.

### Temel Özellikler:
- 🌐 **Cloudflare Browser Rendering API** ile JavaScript rendered sayfaları dahil tüm siteyi tarama
- 🔒 **Güvenlik Analizi** - OWASP standartlarına göre HTTP güvenlik başlıkları kontrolü
- 🔗 **Link Kontrolü** - Kırık link tespiti
- 📊 **SEO Analizi** - Arama motoru optimizasyonu kontrolleri
- 🤖 **AI Test Senaryosu Üretimi** - Llama3 ile otomatik test case üretimi
- 📝 **Raporlama** - JSON ve HTML formatında detaylı raporlar
- 🖥️ **Web Arayüzü** - Flask tabanlı kullanıcı dostu arayüz

---

## 🔄 Ne Yapıyor?

### Basit Anlatımla:

```
                    ┌─────────────────┐
                    │  Web Sitesi     │
                    │  (örn: xyz.com) │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LYNXTEST                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ADIM 1: TARAMA (Cloudflare)                                    │
│  ─────────────────────────                                      │
│  • Tüm sayfaları keşfeder (max 50 sayfa)                        │
│  • HTML ve Markdown olarak kaydeder                             │
│  • JavaScript'i render eder                                      │
│                                                                  │
│  ADIM 2: ANALİZ                                                 │
│  ─────────────                                                  │
│  • Güvenlik başlıkları (CSP, HSTS, X-Frame-Options vb.)        │
│  • Kırık linkler                                                │
│  • SEO (Title, Meta, H1, Alt tags vb.)                         │
│                                                                  │
│  ADIM 3: TEST SENARYOSU ÜRETİMİ (Llama3)                       │
│  ──────────────────────────────────────                         │
│  • Her sayfa için özel test senaryoları                         │
│  • Bulunan sorunlara göre prioritize edilmiş                    │
│                                                                  │
│  ADIM 4: RAPORLAMA                                              │
│  ────────────────                                               │
│  • JSON rapor (makine okunabilir)                               │
│  • HTML rapor (görsel, tarayıcıda açılabilir)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  📊 ÇIKTI                     │
              │  • output/report.html        │
              │  • output/report.json        │
              │  • Test senaryoları          │
              │  • Güvenlik skorları         │
              │  • SEO skorları              │
              └──────────────────────────────┘
```

---

## 🏗️ Sistem Mimarisi

```
┌────────────────────────────────────────────────────────────────────────┐
│                           LynxTest Mimarisi                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│   │   CRAWLER    │    │   ANALYZER   │    │     LLM      │            │
│   │   Modülü     │───▶│    Modülü    │───▶│    Modülü    │            │
│   └──────────────┘    └──────────────┘    └──────────────┘            │
│          │                   │                   │                     │
│          │                   │                   │                     │
│          ▼                   ▼                   ▼                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│   │ Cloudflare   │    │ HeaderChecker│    │ OllamaClient │            │
│   │ Browser API  │    │ LinkChecker  │    │ PromptBuilder│            │
│   │              │    │ SEOChecker   │    │ ScenarioParser           │
│   └──────────────┘    └──────────────┘    └──────────────┘            │
│                                                                        │
│                              │                                         │
│                              ▼                                         │
│                    ┌──────────────────┐                               │
│                    │     REPORTER     │                               │
│                    │      Modülü      │                               │
│                    │ ──────────────── │                               │
│                    │ • JSONReporter   │                               │
│                    │ • HTMLReporter   │                               │
│                    └──────────────────┘                               │
│                              │                                         │
│                              ▼                                         │
│                    ┌──────────────────┐                               │
│                    │       WEB        │                               │
│                    │  Flask Arayüzü   │                               │
│                    │  (Opsiyonel)     │                               │
│                    └──────────────────┘                               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Dizin Yapısı

```
lynxTest/
│
├── 📄 main.py                    # Ana uygulama - Pipeline orkestratörü
├── 📄 config.json                # Ayarlar (API token, URL, model vb.)
├── 📄 requirements.txt           # Python bağımlılıkları
│
├── 📂 crawler/                   # 🌐 Web Tarama Modülü
│   ├── __init__.py               #   Modül tanımları
│   ├── client.py                 #   Cloudflare API istemcisi
│   └── page_saver.py             #   Sayfa kaydetme işlemleri
│
├── 📂 analyzer/                  # 🔍 Analiz Modülü
│   ├── __init__.py               #   Modül tanımları
│   ├── runner.py                 #   Analiz orkestratörü
│   ├── header_checker.py         #   HTTP güvenlik başlıkları kontrolü
│   ├── link_checker.py           #   Kırık link tespiti
│   └── seo_checker.py            #   SEO analizi
│
├── 📂 llm/                       # 🤖 Yapay Zeka Modülü
│   ├── __init__.py               #   Modül tanımları
│   ├── runner.py                 #   LLM senaryo üretim orkestratörü
│   ├── ollama_client.py          #   Ollama API istemcisi
│   ├── prompt_builder.py         #   Prompt oluşturucu
│   └── scenario_parser.py        #   LLM çıktısını ayrıştırıcı
│
├── 📂 reporter/                  # 📝 Raporlama Modülü
│   ├── __init__.py               #   Modül tanımları
│   ├── json_reporter.py          #   JSON rapor oluşturucu
│   ├── html_reporter.py          #   HTML rapor oluşturucu
│   └── templates/
│       └── report.html.j2        #   HTML rapor şablonu (Jinja2)
│
├── 📂 prompts/                   # 💬 LLM Prompt Şablonları
│   └── scenario_template.txt     #   Test senaryosu üretim prompt'u
│
├── 📂 web/                       # 🖥️ Web Arayüzü Modülü
│   ├── __init__.py               #   Modül tanımları
│   ├── app.py                    #   Flask uygulaması
│   └── templates/
│       └── index.html            #   Web arayüzü (SSE destekli)
│
└── 📂 output/                    # 📤 Çıktı Klasörü (otomatik oluşturulur)
    ├── pages/                    #   Taranan sayfa verileri (JSON)
    │   ├── page_001.json
    │   ├── page_002.json
    │   └── ...
    ├── analysis/                 #   Analiz sonuçları (JSON)
    │   ├── page_001_analysis.json
    │   └── ...
    ├── scenarios/                #   Üretilen test senaryoları (JSON)
    │   ├── page_001_scenarios.json
    │   └── ...
    ├── report.json               #   Birleşik JSON rapor
    └── report.html               #   Görsel HTML rapor
```

---

## ⚡ Çalışma Akışı (Pipeline)

### ADIM 1: Web Sitesi Tarama (Crawler)

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRAWLER MODÜLÜ                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CloudflareCrawler.crawl() çağrılır                          │
│     │                                                            │
│     ├── POST /crawl → Task ID alınır                            │
│     │   • URL, max_pages, depth parametreleri gönderilir        │
│     │   • render: true (JavaScript render edilir)               │
│     │                                                            │
│     ├── GET /crawl/{task_id} → Sonuç beklenir                   │
│     │   • Status: running → completed bekle                     │
│     │   • Progress: 5/10, 8/10... şeklinde ilerleme             │
│     │                                                            │
│     └── Sonuç: HTML + Markdown içeren sayfa listesi             │
│                                                                  │
│  2. PageSaver.save_pages() çağrılır                             │
│     │                                                            │
│     ├── Her sayfa için page_XXX.json oluşturulur                │
│     │   • URL, HTML, Markdown, Headers, Status Code             │
│     │                                                            │
│     └── output/pages/ klasörüne kaydedilir                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Cloudflare Browser Rendering API Avantajları:**
- JavaScript ile render edilen içeriği alabilir (SPA, React, Vue vb.)
- Bot korumasını aşar
- Markdown formatında temiz içerik döner
- Asenkron çalışır, uzun süren taramalar için idealdir

---

### ADIM 2: Statik Analiz (Analyzer)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYZER MODÜLÜ                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Her sayfa için 3 farklı analiz yapılır:                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. HEADER CHECKER (Güvenlik Başlıkları)                  │   │
│  │    ─────────────────────────────────────                 │   │
│  │    Kontrol edilen OWASP başlıkları:                      │   │
│  │    • Content-Security-Policy (CSP) - XSS koruması        │   │
│  │    • Strict-Transport-Security (HSTS) - HTTPS zorlaması  │   │
│  │    • X-Frame-Options - Clickjacking koruması             │   │
│  │    • X-Content-Type-Options - MIME sniffing koruması     │   │
│  │    • X-XSS-Protection - Tarayıcı XSS filtresi            │   │
│  │    • Referrer-Policy - Referrer kontrolü                 │   │
│  │    • Permissions-Policy - Tarayıcı özellik kısıtlaması   │   │
│  │                                                          │   │
│  │    Çıktı: Skor (0-100%), eksik başlık listesi            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. LINK CHECKER (Kırık Link Tespiti)                     │   │
│  │    ────────────────────────────────                      │   │
│  │    Taranan elementler:                                   │   │
│  │    • <a href="...">      - Linkler                       │   │
│  │    • <img src="...">     - Görseller                     │   │
│  │    • <link href="...">   - CSS/Favicons                  │   │
│  │    • <script src="...">  - JavaScript dosyaları          │   │
│  │    • <iframe src="...">  - Iframe'ler                    │   │
│  │                                                          │   │
│  │    Yapılan işlem:                                        │   │
│  │    • HEAD request atılır                                 │   │
│  │    • 4XX/5XX → Kırık link                                │   │
│  │    • Timeout → Kırık link                                │   │
│  │                                                          │   │
│  │    Çıktı: Kırık link listesi, health percentage          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. SEO CHECKER (SEO Analizi)                             │   │
│  │    ────────────────────────                              │   │
│  │    Kontrol edilen öğeler:                                │   │
│  │    • Title etiketi (30-60 karakter ideal)                │   │
│  │    • Meta description (120-160 karakter ideal)           │   │
│  │    • H1 etiketi (1 adet olmalı)                          │   │
│  │    • Görsel alt etiketleri (accessibility)               │   │
│  │    • Viewport meta (mobil uyumluluk)                     │   │
│  │    • Canonical URL (duplicate content)                   │   │
│  │    • Open Graph etiketleri (sosyal medya)                │   │
│  │                                                          │   │
│  │    Çıktı: Skor (0-100%), issues, warnings, passed        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Birleştirilmiş Skor Hesaplama:                                 │
│  ─────────────────────────────                                  │
│  Genel Skor = (Güvenlik × %40) + (Linkler × %20) + (SEO × %40) │
│                                                                  │
│  Notlandırma:                                                   │
│  • A: 80-100% (Mükemmel)                                        │
│  • B: 60-79%  (İyi)                                             │
│  • C: 40-59%  (Orta)                                            │
│  • D: 0-39%   (Geliştirmeli)                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### ADIM 3: Test Senaryosu Üretimi (LLM)

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLM MODÜLÜ                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PROMPT BUILDER                                              │
│     ───────────────                                             │
│     Sayfa verisi + Analiz sonuçları → Prompt                    │
│                                                                  │
│     Prompt içeriği:                                             │
│     • Sayfa URL'si                                              │
│     • Markdown içeriği (kısaltılmış)                            │
│     • Güvenlik durumu (CSP, HSTS vb.)                           │
│     • SEO durumu (H1, Meta vb.)                                 │
│     • Kırık link sayısı                                         │
│     • Test senaryosu üretim talimatları                         │
│                                                                  │
│  2. OLLAMA CLIENT                                               │
│     ─────────────                                               │
│     Yerel Ollama sunucusuna istek:                              │
│     • Model: llama3                                             │
│     • Temperature: 0.4 (tutarlı ama çeşitli)                    │
│     • Max tokens: 1536                                          │
│     • Timeout: 5 dakika                                         │
│                                                                  │
│  3. SCENARIO PARSER                                             │
│     ───────────────                                             │
│     LLM çıktısını yapılandırılmış JSON'a dönüştürür:            │
│                                                                  │
│     LLM Çıktısı (ham metin):                                    │
│     ```json                                                     │
│     [                                                           │
│       {                                                         │
│         "scenario_id": 1,                                       │
│         "title": "CSP başlığının eksikliğini test et",          │
│         "steps": ["Adım 1", "Adım 2", ...],                     │
│         "expected": "Beklenen sonuç",                           │
│         "priority": "high"                                      │
│       }                                                         │
│     ]                                                           │
│     ```                                                         │
│                                                                  │
│     Ayrıştırma işlemleri:                                       │
│     • JSON bloğunu çıkar                                        │
│     • Her senaryoyu doğrula                                     │
│     • Boş/geçersiz adımları temizle                             │
│     • Önceliği normalize et (high/medium/low)                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Örnek Üretilen Test Senaryosu:**

```json
{
  "scenario_id": 1,
  "title": "Content Security Policy başlığının eksikliğini test et",
  "steps": [
    "Chrome DevTools'u aç (F12)",
    "Network tab'ına git",
    "Sayfayı yenile (Ctrl+R)",
    "Response Headers'da 'content-security-policy' ara",
    "Başlığın mevcut olmadığını doğrula"
  ],
  "expected": "CSP başlığı eksik olduğu için XSS saldırılarına açık",
  "priority": "high"
}
```

---

### ADIM 4: Raporlama (Reporter)

```
┌─────────────────────────────────────────────────────────────────┐
│                     REPORTER MODÜLÜ                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. JSON REPORTER                                               │
│     ─────────────                                               │
│     Tüm verileri birleştirir:                                   │
│     • pages/ → analysis/ → scenarios/ eşleştirme                │
│     • Genel istatistikler hesaplama                             │
│     • Meta bilgiler ekleme                                      │
│                                                                  │
│     Çıktı: output/report.json                                   │
│     {                                                           │
│       "meta": { "generated_at": "...", "tool": "LynxTest" },    │
│       "summary": {                                              │
│         "total_pages": 10,                                      │
│         "pages_analyzed": 10,                                   │
│         "total_broken_links": 3,                                │
│         "total_scenarios": 35,                                  │
│         "average_scores": {                                     │
│           "security": 45.5,                                     │
│           "seo": 72.3,                                          │
│           "overall": 58.9                                       │
│         },                                                      │
│         "grades": {                                             │
│           "security": "C",                                      │
│           "seo": "B",                                           │
│           "overall": "C"                                        │
│         }                                                       │
│       },                                                        │
│       "pages": [...]                                            │
│     }                                                           │
│                                                                  │
│  2. HTML REPORTER                                               │
│     ─────────────                                               │
│     Jinja2 şablonu ile görsel rapor:                            │
│     • Özet kartları (sayfa sayısı, skorlar, notlar)             │
│     • Skor dağılım grafikleri                                   │
│     • Sayfa bazlı detaylar (expandable)                         │
│     • Güvenlik başlık durumları                                 │
│     • Kırık link listesi                                        │
│     • Test senaryoları (renkli öncelik gösterimi)               │
│                                                                  │
│     Çıktı: output/report.html                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Modüller ve Dosyalar

### 1. CRAWLER Modülü (`crawler/`)

| Dosya | Açıklama |
|-------|----------|
| `__init__.py` | Modül export'ları: `CloudflareCrawler`, `PageSaver` |
| `client.py` | Cloudflare Browser Rendering API istemcisi. POST ile tarama başlatır, GET ile sonuç alır. Asenkron polling mekanizması. |
| `page_saver.py` | Taranan sayfaları JSON formatında `output/pages/` klasörüne kaydeder. HTML'den Markdown dönüşümü yapabilir. |

### 2. ANALYZER Modülü (`analyzer/`)

| Dosya | Açıklama |
|-------|----------|
| `__init__.py` | Modül export'ları: `HeaderChecker`, `LinkChecker`, `SEOChecker`, `AnalyzerRunner` |
| `runner.py` | Orkestratör. Tüm checker'ları çalıştırır, sonuçları birleştirir, `output/analysis/` klasörüne kaydeder. |
| `header_checker.py` | OWASP referanslı 7 güvenlik başlığını kontrol eder. Her başlık için severity (high/medium/low) tanımı. |
| `link_checker.py` | HTML içindeki tüm linkleri (a, img, link, script, iframe, video, audio, source) kontrol eder. HEAD request ile erişilebilirlik testi. |
| `seo_checker.py` | Title, meta description, H1, img alt, viewport, canonical, Open Graph kontrolü. Google SEO önerilerine uygun ideal değerler. |

### 3. LLM Modülü (`llm/`)

| Dosya | Açıklama |
|-------|----------|
| `__init__.py` | Modül export'ları: `PromptBuilder`, `OllamaClient`, `ScenarioParser`, `LLMRunner` |
| `runner.py` | Orkestratör. Her analiz dosyası için prompt oluşturur, LLM'e gönderir, sonucu ayrıştırıp `output/scenarios/` klasörüne kaydeder. |
| `prompt_builder.py` | Sayfa ve analiz verilerini şablona yerleştirerek LLM prompt'u oluşturur. Token tahmini yapar. |
| `ollama_client.py` | Yerel Ollama API ile iletişim. generate() ve chat() metodları. Model listesi ve erişilebilirlik kontrolü. |
| `scenario_parser.py` | LLM'in döndürdüğü metinden JSON bloğunu çıkarır. Senaryoları doğrular ve normalize eder. Fallback olarak metin ayrıştırma. |

### 4. REPORTER Modülü (`reporter/`)

| Dosya | Açıklama |
|-------|----------|
| `__init__.py` | Modül export'ları: `JSONReporter`, `HTMLReporter` |
| `json_reporter.py` | Tüm pages, analysis, scenarios verilerini birleştirip tek JSON rapor oluşturur. Özet istatistikler hesaplar. |
| `html_reporter.py` | JSON raporunu Jinja2 şablonuyla birleştirip görsel HTML rapor üretir. |
| `templates/report.html.j2` | HTML rapor şablonu. Responsive tasarım, expandable sayfa kartları, renkli skorlar. |

### 5. PROMPTS Klasörü (`prompts/`)

| Dosya | Açıklama |
|-------|----------|
| `scenario_template.txt` | LLM'e gönderilecek prompt şablonu. Placeholder'lar: `{url}`, `{markdown_content}`, `{csp_status}`, `{hsts_status}`, `{broken_links}`, `{title}`, `{h1_count}` vb. |

### 6. WEB Modülü (`web/`)

| Dosya | Açıklama |
|-------|----------|
| `__init__.py` | Flask app export'u |
| `app.py` | Flask web uygulaması. SSE (Server-Sent Events) ile canlı ilerleme gösterimi. REST endpoint'leri: `/analyze`, `/stream`, `/status`, `/results`, `/report` |
| `templates/index.html` | Modern, animasyonlu web arayüzü. URL girişi, ilerleme göstergesi, sonuç kartları. |

### 7. Ana Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `main.py` | CLI entry point. Banner, adım adım çalıştırma, özet gösterimi. Tüm modülleri orkestre eder. |
| `config.json` | Ayarlar: Cloudflare token/account_id, hedef URL, Ollama URL/model, max_pages |
| `requirements.txt` | Python bağımlılıkları |

---

## ⚙️ Konfigürasyon

`config.json` dosyası:

```json
{
  "cloudflare_token": "cfat_XXXXX...",       // Cloudflare API Token
  "cloudflare_account_id": "abc123...",       // Cloudflare Account ID
  "target_url": "https://example.com/",       // Taranacak site
  "ollama_model": "llama3",                   // Kullanılacak LLM modeli
  "ollama_url": "http://localhost:11434",     // Ollama sunucu adresi
  "max_pages": 50                             // Maksimum taranacak sayfa
}
```

### Cloudflare API Token Alma:
1. [Cloudflare Dashboard](https://dash.cloudflare.com) → API Tokens
2. Create Token → Custom Token
3. Permissions: Account → Workers Browser Rendering → Read
4. Token'ı `config.json`'a yapıştır

### Ollama Kurulumu:
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows (installer indir)
# https://ollama.ai/download

# Llama3 modelini indir
ollama pull llama3

# Ollama'yı başlat
ollama serve
```

---

## 📚 Bağımlılıklar

`requirements.txt`:

| Paket | Açıklama |
|-------|----------|
| `httpx` | Modern HTTP istemcisi (async destekli, timeout yönetimi) |
| `beautifulsoup4` | HTML ayrıştırma (link ve SEO analizi için) |
| `lxml` | Hızlı HTML/XML parser (BeautifulSoup backend) |
| `markdownify` | HTML → Markdown dönüşümü |
| `ollama` | Ollama Python SDK (opsiyonel, httpx ile doğrudan API kullanılıyor) |
| `jinja2` | HTML şablon motoru (rapor oluşturma) |
| `flask` | Web framework (web arayüzü) |

```bash
# Kurulum
pip install -r requirements.txt
```

---

## 🚀 Kullanım

### CLI ile Çalıştırma:

```bash
# config.json'u düzenle
# Sonra çalıştır:
python main.py
```

**Çıktı:**
```
╔═══════════════════════════════════════════════════════════════╗
║   ██╗  ██╗   ██╗███╗   ██╗██╗  ██╗████████╗███████╗███████╗  ║
║   ██║  ╚██╗ ██╔╝████╗  ██║╚██╗██╔╝╚══██╔══╝██╔════╝██╔════╝  ║
║   ██║   ╚████╔╝ ██╔██╗ ██║ ╚███╔╝    ██║   █████╗  ███████╗  ║
║   ██║    ╚██╔╝  ██║╚██╗██║ ██╔██╗    ██║   ██╔══╝  ╚════██║  ║
║   ███████╗██║   ██║ ╚████║██╔╝ ██╗   ██║   ███████╗███████║  ║
║   ╚══════╝╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝  ║
╚═══════════════════════════════════════════════════════════════╝

============================================================
  ADIM 1: WEB SİTESİ TARAMA (Cloudflare Browser Rendering)
============================================================
[CRAWLER] Tarama başlatılıyor: https://example.com
[CRAWLER] Tarama tamamlandı! 10 sayfa bulundu.

============================================================
  ADIM 2: STATİK ANALİZ (Güvenlik, Link, SEO)
============================================================
[ANALYZER] 10 sayfa analiz edilecek...

============================================================
  ADIM 3: TEST SENARYOSU ÜRETİMİ (Llama3)
============================================================
[LLM] 10 sayfa için senaryo üretilecek...

============================================================
  ADIM 4: RAPOR OLUŞTURMA
============================================================
[JSON_REPORTER] Rapor kaydedildi: output/report.json
[HTML_REPORTER] Rapor kaydedildi: output/report.html

============================================================
  İŞLEM TAMAMLANDI!
============================================================

    📊 ÖZET
    ─────────────────────────────────────
    • Taranan sayfa sayısı  : 10
    • Analiz edilen sayfa   : 10
    • Üretilen senaryo      : 35 dosya
    • Toplam süre           : 45.3 saniye

    📁 ÇIKTI DOSYALARI
    ─────────────────────────────────────
    • JSON Rapor : output/report.json
    • HTML Rapor : output/report.html
```

### Web Arayüzü ile Çalıştırma:

```bash
# Web sunucusunu başlat
cd web
python app.py

# veya
python -m web.app
```

Tarayıcıda: `http://localhost:5000`

---

## 📤 Çıktılar

### 1. Sayfa Verileri (`output/pages/page_XXX.json`)

```json
{
  "url": "https://example.com/about",
  "html": "<html>...</html>",
  "markdown": "# About Us\n\nWe are a company...",
  "status_code": 200,
  "headers": {
    "content-type": "text/html",
    "strict-transport-security": "max-age=31536000"
  },
  "title": "About Us - Example",
  "last_modified": "2024-01-15T10:30:00Z"
}
```

### 2. Analiz Sonuçları (`output/analysis/page_XXX_analysis.json`)

```json
{
  "url": "https://example.com/about",
  "analyzed_at": "2024-03-28T15:30:00",
  "headers": {
    "summary": {
      "csp": false,
      "hsts": true,
      "x_frame_options": true,
      "x_content_type_options": false,
      "x_xss_protection": false,
      "referrer_policy": false,
      "permissions_policy": false
    },
    "score": 28.6,
    "found": 2,
    "missing": 5,
    "recommendations": [...]
  },
  "broken_links": [
    {"url": "https://example.com/old-page", "error": "HTTP 404"}
  ],
  "links_summary": {
    "total_links": 25,
    "checked": 20,
    "broken": 1,
    "working": 19,
    "health_percentage": 95.0
  },
  "seo": {
    "title": "About Us - Example",
    "title_length": 20,
    "meta_description": true,
    "h1_count": 1,
    "missing_alts": 2,
    "total_images": 5,
    "score": 75.0,
    "grade": "B"
  },
  "overall_score": {
    "score": 58.9,
    "grade": "C",
    "status": "Orta",
    "breakdown": {
      "security": 28.6,
      "links": 95.0,
      "seo": 75.0
    }
  }
}
```

### 3. Test Senaryoları (`output/scenarios/page_XXX_scenarios.json`)

```json
{
  "url": "https://example.com/about",
  "scenarios": [
    {
      "scenario_id": 1,
      "title": "CSP başlığının eksikliğini test et",
      "steps": [
        "Chrome DevTools'u aç (F12)",
        "Network tab'ına git",
        "Sayfayı yenile",
        "Response Headers'da CSP ara",
        "Başlığın olmadığını doğrula"
      ],
      "expected": "XSS saldırılarına karşı savunmasız",
      "priority": "high"
    },
    {
      "scenario_id": 2,
      "title": "Kırık linki doğrula",
      "steps": [
        "/old-page linkine tıkla",
        "404 hata sayfası gözlemle"
      ],
      "expected": "Sayfa 404 döner",
      "priority": "medium"
    }
  ],
  "parse_success": true,
  "scenario_count": 2
}
```

### 4. Birleşik Rapor (`output/report.json`)

Tüm sayfa, analiz ve senaryo verilerinin birleşimi + genel istatistikler.

### 5. HTML Rapor (`output/report.html`)

Tarayıcıda açılabilir görsel rapor. Örnek görünüm:

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 LynxTest Raporu                                             │
│  Oluşturulma: 2024-03-28 15:30:00                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │    10    │  │    10    │  │    3     │  │    35    │        │
│  │  Toplam  │  │ Analiz   │  │  Kırık   │  │   Test   │        │
│  │  Sayfa   │  │ Edilen   │  │  Link    │  │ Senaryo  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  📊 Skor Dağılımı                                               │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │ Güvenlik: 45%  │ SEO: 72%       │ Genel: 59%    │          │
│  └────────────────┴────────────────┴────────────────┘          │
│                                                                  │
│  📄 Sayfa Detayları                                             │
│  ─────────────────                                              │
│  ▼ About Us - Example                              [C] 3 senaryo│
│    │ Güvenlik: 28% │ Linkler: 95% │ SEO: 75%                   │
│    │                                                            │
│    │ 🔒 Güvenlik Başlıkları                                    │
│    │ ✅ HSTS  ✅ X-Frame  ❌ CSP  ❌ X-Content...              │
│    │                                                            │
│    │ 🧪 Test Senaryoları                                       │
│    │ 🔴 CSP başlığının eksikliğini test et                     │
│    │ 🟡 Kırık linki doğrula                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Teknik Detaylar

### Asenkron Crawling Mekanizması

Cloudflare API asenkron çalışır:
1. `POST /crawl` → `task_id` döner
2. `GET /crawl/{task_id}?limit=1` → Status kontrolü (hafif sorgu)
3. Status `completed` olunca → `GET /crawl/{task_id}` → Tüm sonuçlar

```
Timeline:
─────────────────────────────────────────────────────────────────
0s      POST /crawl ─────► task_id: "abc123"
        │
5s      GET /crawl/abc123?limit=1 ─► status: "running" (2/10)
        │
10s     GET /crawl/abc123?limit=1 ─► status: "running" (5/10)
        │
15s     GET /crawl/abc123?limit=1 ─► status: "running" (8/10)
        │
20s     GET /crawl/abc123?limit=1 ─► status: "completed"
        │
        GET /crawl/abc123 ─────────► records: [10 sayfa verisi]
─────────────────────────────────────────────────────────────────
```

### LLM Prompt Engineering

Prompt şablonu, LLM'in tutarlı ve yapılandırılmış çıktı üretmesi için optimize edilmiştir:

1. **Context**: Sayfa URL'si, içeriği, güvenlik/SEO durumu
2. **Rules**: Spesifik senaryo, steps formatı, priority belirleme
3. **Format**: Tek JSON array, belirli alanlar (scenario_id, title, steps, expected, priority)
4. **Examples**: Şablonda örnek senaryolar

### Error Handling

Her modül kendi hata yönetimini yapar:
- Network hataları (timeout, connection error)
- Parse hataları (invalid JSON, missing fields)
- API hataları (rate limit, auth error)
- Graceful degradation (bir adım başarısız olsa bile devam)

---

## 📝 Özet

**LynxTest**, web sitelerini kapsamlı şekilde analiz eden ve yapay zeka ile test senaryoları üreten güçlü bir araçtır.

| Özellik | Açıklama |
|---------|----------|
| **Tarama** | Cloudflare Browser Rendering ile JavaScript-rendered sayfalar dahil |
| **Güvenlik** | OWASP standartlarına göre 7 kritik HTTP başlığı kontrolü |
| **SEO** | Google önerilerine uygun title, meta, heading, image analizi |
| **Link Kontrolü** | Tüm asset'lerin erişilebilirlik testi |
| **AI Test Üretimi** | Llama3 ile sayfa bazlı özelleştirilmiş test senaryoları |
| **Raporlama** | JSON (API için) ve HTML (görsel) rapor çıktıları |
| **Web UI** | Flask tabanlı, SSE ile canlı ilerleme gösteren arayüz |

---

**Geliştirici:** Mehmet  
**Versiyon:** 1.0.0  
**Lisans:** MIT

---

*Bu dokümantasyon, projenin tüm yapısını ve işleyişini detaylı şekilde açıklamaktadır. Sorularınız için issue açabilirsiniz.*
