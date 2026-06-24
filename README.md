# LynxTest

**Cloudflare Browser Rendering API & Llama3 destekli otomatik web QA aracı.**

Bir web sitesini tarar, güvenlik/link/SEO analizi yapar ve Llama3 ile test senaryoları üretir. CLI ile çalışır, opsiyonel Flask web arayüzü de vardır.

---

## Nasıl Çalışır?

Araç 4 adımı sırayla çalıştırır:

```
URL girişi
    │
    ▼
[1] TARAMA (Cloudflare Browser Rendering API)
    • JavaScript render ederek tüm sayfaları keşfeder
    • HTML + Markdown formatında output/pages/ klasörüne kaydeder
    │
    ▼
[2] STATİK ANALİZ
    • Güvenlik başlıkları (CSP, HSTS, X-Frame-Options, vb.)
    • Kırık link tespiti (HTTP durum kodları)
    • SEO kontrolleri (meta tag, başlık, canonical, vb.)
    │
    ▼
[3] TEST SENARYOSU ÜRETİMİ (Ollama / Llama3)
    • Her sayfa için analiz verisini prompt'a dönüştürür
    • LLM'den test case'ler üretir, output/scenarios/ klasörüne kaydeder
    │
    ▼
[4] RAPORLAMA
    • JSON ve HTML rapor (output/report.json, output/report.html)
    • Akademik temiz raporlar (report_clean.json/html, summary_table_clean.csv)
    • Crawl grafı, link listesi, sayfa indeksi
```

---

## Gereksinimler

| Bileşen | Detay |
|---|---|
| Python | 3.9+ |
| Cloudflare hesabı | Browser Rendering API etkin olmalı |
| Ollama | Yerel kurulu, llama3 modeli indirilmiş |

> **Cloudflare Browser Rendering API** ücretli bir özelliktir. Hesabınızda etkin olup olmadığını Cloudflare panelinden kontrol edin.

---

## Kurulum

### 1. Repoyu klonla

```bash
git clone <repo-url>
cd web-qa-tool
```

### 2. Sanal ortam oluştur ve bağımlılıkları yükle

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Konfigürasyon dosyasını hazırla

```bash
cp config.example.json config.json
```

`config.json` dosyasını açıp şu alanları doldur:

```json
{
  "cloudflare_token": "YOUR_CLOUDFLARE_API_TOKEN",
  "cloudflare_account_id": "YOUR_CLOUDFLARE_ACCOUNT_ID",
  "target_url": "https://example.com/",
  "ollama_model": "llama3",
  "ollama_url": "http://localhost:11434",
  "max_pages": 50,
  "crawl_depth": 3,
  "include_subdomains": true,
  "include_external_links": false,
  "crawl_formats": ["html", "markdown"],
  "render": true,
  "fallback_fetch_skipped": true,
  "fallback_timeout": 15.0,
  "quiet_mode": true,
  "max_links_per_page": 150,
  "check_asset_links": false,
  "link_max_retries": 1,
  "scenario_max_pages": 10
}
```

**Zorunlu alanlar:**

- `cloudflare_token` — Cloudflare API token'ı ([panelden al](https://dash.cloudflare.com/profile/api-tokens))
- `cloudflare_account_id` — Cloudflare hesap ID'si (panel URL'sinde görünür)
- `target_url` — Taranacak web sitesinin tam URL'si

### 4. Ollama ve Llama3 kurulumu

```bash
# Ollama'yı kur (macOS)
brew install ollama

# Llama3 modelini indir
ollama pull llama3

# Ollama'yı başlat (arka planda çalışmalı)
ollama serve
```

---

## Çalıştırma

### CLI (Komut Satırı)

```bash
python main.py
```

Tarama başlar, terminal'de adım adım ilerleme görürsün. İşlem bitince `output/` klasöründe raporlar hazır olur.

### Web Arayüzü (Flask)

```bash
python web/app.py
```

Tarayıcıda [http://localhost:5000](http://localhost:5000) adresini aç. Arayüzden URL ve sayfa sayısı girerek analizi başlatabilirsin. İlerleme Server-Sent Events (SSE) ile canlı olarak gösterilir.

---

## Konfigürasyon Parametreleri

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `cloudflare_token` | — | Cloudflare API token (zorunlu) |
| `cloudflare_account_id` | — | Cloudflare hesap ID (zorunlu) |
| `target_url` | — | Taranacak URL (zorunlu) |
| `ollama_model` | `"llama3"` | Kullanılacak LLM modeli |
| `ollama_url` | `"http://localhost:11434"` | Ollama sunucu adresi |
| `max_pages` | `50` | Taranacak maksimum sayfa sayısı |
| `crawl_depth` | `3` | Tarama derinliği |
| `include_subdomains` | `true` | Alt domain'leri dahil et |
| `include_external_links` | `false` | Dış linkleri dahil et |
| `render` | `true` | JavaScript render etsin mi |
| `quiet_mode` | `true` | ASCII banner'ı gizle |
| `max_links_per_page` | `150` | Sayfa başına kontrol edilecek max link |
| `check_asset_links` | `false` | CSS/JS/resim linklerini de kontrol et |
| `link_max_retries` | `1` | Kırık link kontrolünde tekrar deneme sayısı |
| `scenario_max_pages` | `10` | LLM senaryo üretilecek max sayfa (0 = tümü) |
| `fallback_fetch_skipped` | `true` | Atlanan sayfaları direkt HTTP ile dene |
| `fallback_timeout` | `15.0` | Fallback HTTP timeout (saniye) |

---

## Çıktı Dosyaları

Tüm çıktılar `output/` klasörüne yazılır:

```
output/
├── pages/                      # Ham sayfa verileri (page_001.json, ...)
├── analysis/                   # Sayfa başına analiz sonuçları
├── scenarios/                  # LLM'in ürettiği test senaryoları
├── report.json                 # Tam JSON rapor
├── report.html                 # Görsel HTML rapor
├── report_clean.json           # Akademik temiz JSON rapor
├── report_clean.html           # Akademik temiz HTML rapor
├── summary_table_clean.csv     # Özet tablo (CSV)
├── crawl_phase1.json           # Tarama istatistikleri
├── crawl_graph.json            # Sayfalar arası bağlantı grafı
├── discovered_links.json       # İç/dış link listesi
└── page_index.json             # Sayfa indeksi
```

HTML raporunu tarayıcıda açmak için:

```bash
open output/report.html        # macOS
start output\report.html       # Windows
```

---

## Proje Yapısı

```
web-qa-tool/
├── main.py                     # CLI giriş noktası
├── config.json                 # Konfigürasyon (git'e ekleme)
├── config.example.json         # Konfigürasyon şablonu
├── requirements.txt            # Python bağımlılıkları
│
├── crawler/                    # Cloudflare crawl modülü
│   ├── client.py               # CloudflareCrawler sınıfı
│   └── page_saver.py           # Sayfa kayıt işlemleri
│
├── analyzer/                   # Statik analiz modülleri
│   ├── runner.py               # Analiz koordinatörü
│   ├── header_checker.py       # Güvenlik başlıkları
│   ├── link_checker.py         # Kırık link kontrolü
│   └── seo_checker.py          # SEO kontrolleri
│
├── llm/                        # LLM entegrasyonu
│   ├── runner.py               # Senaryo üretim koordinatörü
│   ├── ollama_client.py        # Ollama API istemcisi
│   ├── prompt_builder.py       # Prompt oluşturucu
│   └── scenario_parser.py      # LLM çıktı ayrıştırıcı
│
├── reporter/                   # Rapor üreticiler
│   ├── json_reporter.py        # JSON rapor
│   ├── html_reporter.py        # HTML rapor
│   └── clean_reporter.py       # Akademik temiz rapor
│
├── web/                        # Flask web arayüzü
│   └── app.py                  # Web sunucusu (port 5000)
│
├── prompts/
│   └── scenario_template.txt   # LLM prompt şablonu
│
└── output/                     # Üretilen çıktılar (git'e ekleme)
```

---

## Sık Karşılaşılan Sorunlar

**`config.json dosyası bulunamadı` hatası**
→ `config.example.json`'ı `config.json` olarak kopyalayıp bilgilerini doldur.

**`[CRAWLER] HTTP hatası: 401`**
→ Cloudflare token'ın yanlış veya süresi dolmuş. Yeni token oluştur.

**`[CRAWLER] HTTP hatası: 403`**
→ Hesabında Browser Rendering API etkin değil. Cloudflare panelinden kontrol et.

**Ollama'ya erişilemiyor / senaryo üretilemiyor**
→ `ollama serve` komutunun çalıştığından emin ol. Web arayüzü bu durumda senaryo adımını atlayarak devam eder.

**Tarama çok yavaş / timeout**
→ `max_pages` değerini düşür veya `crawl_depth` değerini azalt.
