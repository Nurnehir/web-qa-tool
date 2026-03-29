# Web QA Tool - Makale/Bildiri Hazırlık Düzeltme Planı

Bu doküman, mevcut pipeline çıktısındaki kritik eksikleri gidermek ve çalışmayı akademik olarak savunulabilir hale getirmek için hazırlanmıştır.

## 1) Mevcut Durum Özeti (29 Mart 2026 Çalıştırması)

- Taranan URL sayısı: `50`
- Analiz edilen sayfa: `3`
- HTML içeriği olmayan/atlanan sayfa: `47`
- Senaryo üretilen dosya: `3`
- Örnek skorlar:
  - `https://www.wikipedia.org/`: genel `45.0`, güvenlik `0.0`, link `100.0`, SEO `62.5`
  - `https://en.wikipedia.org/`: genel `39.5`, güvenlik `0.0`, link `97.5`, SEO `50.0`

Bu haliyle sonuçlar bir "pilot/ön çalışma" seviyesinde; ana deney sonucu olarak sunmak metodolojik olarak zayıf kalır.

## 2) Kritik Problemler ve Etkileri

## 2.1 Kapsam ve Temsiliyet Problemi

Sorun:
- `50` URL bulunmasına rağmen yalnızca `3` sayfada analiz var.
- `47` sayfa "HTML içeriği yok" diye atlanmış.

Etki:
- Örneklem yanlılığı oluşur.
- Domain performansına ilişkin sonuçlar genellenemez.

## 2.2 Güvenlik Başlıklarında Ölçüm Güvenilirliği Problemi

Sorun:
- `output/pages/page_*.json` içinde `headers` alanı boş (`{}`/`null`) görünüyor.
- Buna rağmen raporda "7 başlığın 7'si eksik" şeklinde kesin sonuç üretiliyor.

Etki:
- "Eksik" ile "ölçülemedi" karışıyor.
- Güvenlik skorları sistematik olarak düşük çıkıyor (false negative riski).

## 2.3 Link Kırıklığı Ölçümünde Yanlış Sınıflandırma

Sorun:
- `429`, `timeout`, `503` gibi geçici/altyapı kaynaklı durumlar "kırık link" olarak toplanıyor.
- Tek denemeyle karar veriliyor.

Etki:
- Broken link oranı şişebilir.
- Zaman/koşul bağımlı gürültü metriklere girer.

## 2.4 URL Normalizasyon ve Crawl Kalitesi Problemi

Sorun:
- Çıktıda `//domain` ve `.../wiki/Main_Page/wiki/...` benzeri anormal URL örnekleri var.
- Link extraction + join aşamasında URL kalite kontrolü yetersiz.

Etki:
- Yapay 404 artışı.
- Link sağlığı metriği gerçeği yansıtmaz.

## 2.5 SEO Değerlendirmesinde Bağlam Eksikliği

Sorun:
- Tek tip kural seti tüm sitelere uygulanıyor.
- Wiki gibi bilgi sitelerinde bazı "eksik" etiketler kritik olmayabilir.

Etki:
- Skor yorumları bağlam dışı olabilir.
- Makalede "neden bu kural" sorusuna savunma zayıflar.

## 2.6 LLM Senaryo Kalitesi ve Doğrulanabilirlik Problemi

Sorun:
- LLM çıktıları analiz bulgularını tekrar ediyor; doğrulama adımları zaman zaman araç bağımlı ve zayıf.
- Üretilen senaryolar için kalite metrikleri yok.

Etki:
- Senaryoların pratik test değerini ölçmek zor.
- Makalede LLM katkısı nicel kanıtla desteklenemiyor.

## 3) Kod Bazında Düzeltme Planı (Dosya Bazlı)

## 3.1 Crawler ve Sayfa Kaydı

Hedef dosyalar:
- `crawler/client.py`
- `crawler/page_saver.py`

Yapılacaklar:
1. Crawl yanıtındaki `status`, `error`, `fetch_reason`, `content_type` benzeri alanları sakla.
2. `page_saver` içinde ham `headers` yanında `headers_source` alanı ekle:
   - `from_crawl_record`
   - `fetched_later`
   - `missing`
3. HTML yoksa sebep kodu sakla (`no_html_reason`) ve rapora taşı.
4. Sayfa başına `fetch_timestamp` ekle.

Beklenen kazanım:
- "Neden analiz edilmedi" net raporlanır.
- Ölçülemedi/eksik ayrımı mümkün olur.

## 3.2 Header Checker Güvenilirlik İyileştirmesi

Hedef dosya:
- `analyzer/header_checker.py`

Yapılacaklar:
1. `check()` sonucuna `measurement_status` ekle:
   - `measured`
   - `not_measured`
2. `headers` boş ise doğrudan "eksik" demek yerine önce aktif fetch dene.
3. `HEAD` başarısız olursa kontrollü `GET` fallback yap.
4. Başlıklar alınamazsa `error_type` üret (`timeout`, `connect_error`, `blocked`, `unknown`).
5. Skor hesaplamasında `not_measured` sayfaları ayrı tut:
   - güvenlik skoru = sadece `measured` sayfalarda hesaplanmalı.

Beklenen kazanım:
- Güvenlik metrikleri savunulabilir hale gelir.

## 3.3 Link Checker Sınıflandırma ve Retry

Hedef dosya:
- `analyzer/link_checker.py`

Yapılacaklar:
1. Sonuç sınıfları ekle:
   - `broken_strict` (kalıcı: 404/410 vb.)
   - `server_error` (5xx)
   - `rate_limited` (429)
   - `transient_network` (timeout/connect)
2. `429`, timeout, 5xx için en az `2-3` retry + backoff.
3. Nihai raporda tek "broken" yerine çoklu metrik ver.
4. URL canonicalization katmanı ekle:
   - fragment kaldır (`#...`)
   - gereksiz slash düzelt
   - aynı URL tekrarlarını tekilleştir

Beklenen kazanım:
- False positive düşer, metrik kalitesi artar.

## 3.4 Analyzer Orkestrasyonu ve Skorlama

Hedef dosya:
- `analyzer/runner.py`

Yapılacaklar:
1. Sayfa bazlı `analysis_status` alanı ekle:
   - `analyzed`
   - `skipped_no_html`
   - `failed_runtime`
2. Genel skor hesaplamasında geçersiz metrikleri hariç tut.
3. Skor yanında `confidence` alanı ekle:
   - Örn. ölçülen sinyal oranına göre `low/medium/high`
4. Link skorunu `broken_strict` üzerinden ayrı hesapla.

Beklenen kazanım:
- Tek sayı yerine güvenilirlik ile birlikte skor sunumu.

## 3.5 Reporter Katmanında Akademik Raporlama

Hedef dosyalar:
- `reporter/json_reporter.py`
- `reporter/html_reporter.py`
- `reporter/templates/report.html.j2`

Yapılacaklar:
1. Özet bölümüne veri kalitesi metrikleri ekle:
   - `fetch_success_rate`
   - `html_availability_rate`
   - `analysis_coverage_rate`
   - `header_measurement_rate`
2. Link metriğini ayrıştır:
   - `broken_strict_total`
   - `rate_limited_total`
   - `transient_error_total`
3. "Threats to validity" bölümü ekle (otomatik kısa açıklama).
4. Çalıştırma konfigürasyonunu rapora göm (`config snapshot`).

Beklenen kazanım:
- Makale tabloları rapordan doğrudan türetilebilir.

## 3.6 LLM Senaryo Üretimi Kalite Katmanı

Hedef dosyalar:
- `llm/runner.py`
- `llm/prompt_builder.py`
- `llm/scenario_parser.py`
- `prompts/scenario_template.txt`

Yapılacaklar:
1. Prompt'a "kanıt satırı" zorunluluğu ekle (hangi bulgudan türedi?).
2. Senaryo şemasına alanlar ekle:
   - `evidence`
   - `preconditions`
   - `assertions`
   - `false_positive_risk`
3. Ayrıştırma sonrası validasyon ekle (boş/tekrarlı senaryo filtreleme).
4. Senaryo kalite metrikleri üret:
   - `scenario_precision_proxy`
   - `actionability_score`

Beklenen kazanım:
- LLM katkısı ölçülebilir hale gelir.

## 4) Makale İçeriğinde Mutlaka Olması Gereken Bölümler

1. Problem tanımı ve hedef.
2. Veri toplama metodolojisi (crawler ayarları, kısıtlar, dışlama kriterleri).
3. Ölçüm tanımları (security/link/seo metriklerinin açık formülü).
4. Geçerlilik tehditleri:
   - internal validity (ölçüm hataları)
   - external validity (genellenebilirlik)
   - construct validity (metrik gerçekten neyi ölçüyor?)
5. Tekrarlanabilirlik:
   - versiyonlar
   - config
   - çalıştırma tarihi/saati
   - ortam bilgisi
6. Sonuçlar + belirsizlik:
   - ortalama
   - dağılım
   - run-to-run varyans
7. LLM senaryo katkısı için ayrı değerlendirme.

## 5) Deney Tasarımı (Minimum Akademik Güç)

1. Aynı konfigürasyonla en az `3` bağımsız koşu.
2. Her koşuda aynı metrik seti.
3. Karşılaştırmalı tablo:
   - mevcut sürüm (baseline)
   - iyileştirilmiş sürüm (improved)
4. İstatistik:
   - ortalama
   - standart sapma
   - göreli iyileşme yüzdesi

## 6) Önerilen Rapor Metrikleri (Kesin)

- `discovered_pages`
- `fetched_pages`
- `fetch_success_rate`
- `html_pages`
- `html_availability_rate`
- `analyzed_pages`
- `analysis_coverage_rate`
- `header_measured_pages`
- `header_measurement_rate`
- `security_score_mean_measured_only`
- `links_broken_strict_total`
- `links_rate_limited_total`
- `links_transient_total`
- `seo_score_mean`
- `llm_scenarios_total`
- `llm_scenarios_validated_total`

## 7) "Done" Kriterleri (Bu Çalışma Bitti Sayılmadan Önce)

1. `analysis_coverage_rate >= 0.80` (veya açıkça gerekçelendirilmiş alt eşik).
2. `header_measurement_rate >= 0.90`.
3. Link sınıfları ayrıştırılmış ve raporlanmış olmalı.
4. Aynı veri setinde 3 koşunun varyansı raporda verilmeli.
5. LLM senaryolarının en az bir kalite metriği raporda olmalı.
6. Makale "Threats to Validity" bölümü eksiksiz yazılmış olmalı.

## 8) Uygulama Sırası (Pragmatik Sprint Planı)

Sprint 1 (Doğruluk):
- Header ölçüm statüsü
- Link retry + sınıflandırma
- URL canonicalization

Sprint 2 (Kapsam):
- Crawl sonucu neden kodları
- analiz coverage artırımı
- rapora veri kalitesi metrikleri

Sprint 3 (Akademik paket):
- 3 koşu deneyi
- karşılaştırmalı tablolar
- makale metninde geçerlilik + sınırlılıklar

## 9) Kısa Sonuç

Mevcut çıktının en büyük problemi, ölçüm güvenilirliği ve kapsam oranının düşük olmasıdır. Önce ölçüm doğruluğu (header/link), sonra coverage, en son LLM kalite ve akademik raporlama tamamlanmalıdır. Bu sıra takip edilirse çalışma "demo" seviyesinden "yayınlanabilir teknik rapor" seviyesine çıkar.
