# Web QA Tool — Otomatik Web Test Senaryosu Üretim Aracı

Cloudflare Browser Rendering ile web sitelerini tarar, güvenlik/SEO analizi yapar ve llama3 ile test senaryoları üretir.

---

## Kurulum (Sıfırdan)

### 1. Projeyi klonla

```bash
git clone https://github.com/nurnehir/web-qa-tool.git
cd web-qa-tool
git checkout claude/setup-web-test-tool-ZAdpn
```

### 2. Python sanal ortamını kur

```bash
python3 -m venv .venv

# Mac / Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### 3. .env dosyasını oluştur

```bash
cp .env.example .env
```

`.env` dosyasını aç ve şu bilgileri doldur:

```env
DATABASE_URL=sqlite:///./qa_tool.db

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3

CLOUDFLARE_API_TOKEN=buraya_token_gir
CLOUDFLARE_ACCOUNT_ID=buraya_account_id_gir

DEBUG=true
MAX_PAGES_PER_CRAWL=30
```

> **Cloudflare token almak için:**
> 1. cloudflare.com → My Profile → API Tokens → Create Token
> 2. Custom Token → Permissions: Account / Browser Rendering / Edit
> 3. Account ID: Cloudflare dashboard URL'inden (dash.cloudflare.com/**ID_BURAYA**/...)

### 4. Ollama ve llama3 kur

```bash
# Ollama indir: https://ollama.com

# Kurulumdan sonra:
ollama pull llama3
# ~4.7 GB indirir, 5-15 dakika sürer
```

### 5. Sistemi başlat

İki ayrı terminal aç:

**Terminal 1 — API:**
```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Ollama (llama3):**
```bash
ollama serve
```

---

## Kullanım

### Analiz başlat

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://hedefsite.com", "max_pages": 5}'
```

### Durum sorgula

```bash
curl http://localhost:8000/status/1
```

### Raporu al

```bash
curl http://localhost:8000/report/1
```

### Tüm işleri listele

```bash
curl http://localhost:8000/jobs
```

---

## Swagger UI

API çalışırken tarayıcıda aç:
```
http://localhost:8000/docs
```

---

## Mimari

```
web-qa-tool/
├── crawler/         ← Cloudflare Browser Rendering API (birincil)
│                      Playwright (Cloudflare yoksa fallback)
├── analyzer/        ← Güvenlik başlıkları (OWASP A05)
│                      SEO / meta etiket denetimi
│                      Kırık link tespiti
│                      Kalite skoru (0-100)
├── llm_engine/      ← Ollama + llama3 ile test senaryosu üretimi
│                      Jinja2 prompt şablonları (sayfa tipine göre)
├── orchestrator/    ← Tüm katmanları birleştiren pipeline
├── api/             ← FastAPI REST API
├── db/              ← SQLite veritabanı (dosya tabanlı, sunucu yok)
└── tests/           ← Birim testleri
```

---

## Testleri çalıştır

```bash
source .venv/bin/activate
pytest tests/ -v
```
