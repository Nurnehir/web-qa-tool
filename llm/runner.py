"""
LLM Senaryo Üretici Runner

Tüm analiz edilmiş sayfalar için LLM'den
test senaryoları üretir ve kaydeder.
"""

import json
import os
from typing import Dict, Any, List
from .prompt_builder import PromptBuilder
from .ollama_client import OllamaClient
from .scenario_parser import ScenarioParser


class LLMRunner:
    """
    LLM senaryo üretim sürecini yöneten sınıf.
    
    Analiz edilmiş her sayfa için prompt oluşturur,
    LLM'den senaryo üretir ve output/scenarios/ klasörüne kaydeder.
    """
    
    def __init__(
        self,
        pages_dir: str = "output/pages",
        analysis_dir: str = "output/analysis",
        scenarios_dir: str = "output/scenarios",
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3",
        verbose: bool = True,
        scenario_max_pages: int = 0
    ):
        """
        LLMRunner sınıfını başlatır.
        
        Args:
            pages_dir: Sayfa JSON dosyalarının bulunduğu klasör
            analysis_dir: Analiz sonuçlarının bulunduğu klasör
            scenarios_dir: Senaryo çıktılarının kaydedileceği klasör
            ollama_url: Ollama sunucu adresi
            model: Kullanılacak LLM modeli
        """
        self.pages_dir = pages_dir
        self.analysis_dir = analysis_dir
        self.scenarios_dir = scenarios_dir
        self.verbose = verbose
        try:
            self.scenario_max_pages = int(scenario_max_pages)
        except (TypeError, ValueError):
            self.scenario_max_pages = 0
        
        # Bileşenleri başlat
        self.prompt_builder = PromptBuilder()
        self.ollama_client = OllamaClient(base_url=ollama_url, model=model, verbose=verbose)
        self.scenario_parser = ScenarioParser()
        
        # Çıktı klasörünü oluştur
        self._ensure_directory()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
    
    def _ensure_directory(self) -> None:
        """Çıktı klasörünün var olduğundan emin olur."""
        if not os.path.exists(self.scenarios_dir):
            os.makedirs(self.scenarios_dir)
            self._log(f"[LLM] Klasör oluşturuldu: {self.scenarios_dir}")
    
    def run(self) -> List[str]:
        """
        Tüm analiz edilmiş sayfalar için senaryo üretir.
        
        Returns:
            Oluşturulan senaryo dosyalarının listesi
        """
        saved_files = []
        
        # Önce Ollama'nın erişilebilir olduğunu kontrol et
        if not self.ollama_client.is_available():
            print("[LLM] HATA: Ollama sunucusuna erişilemiyor!")
            print("[LLM] Lütfen Ollama'nın çalıştığından emin olun.")
            return saved_files
        
        # Kullanılabilir modelleri kontrol et
        models = self.ollama_client.list_models()
        if not models:
            print("[LLM] UYARI: Yüklü model bulunamadı. 'ollama pull llama3' komutunu çalıştırın.")
            return saved_files
        
        self._log(f"[LLM] Kullanılabilir modeller: {', '.join(models)}")
        
        # Analiz dosyalarını bul
        analysis_files = self._get_analysis_files()
        
        if not analysis_files:
            print("[LLM] UYARI: Analiz dosyası bulunamadı.")
            return saved_files

        analysis_files = self._prioritize_analysis_files(analysis_files)
        if self.scenario_max_pages and self.scenario_max_pages > 0:
            analysis_files = analysis_files[: self.scenario_max_pages]
        
        print(
            f"[LLM] {len(analysis_files)} sayfa için senaryo üretilecek..."
            f" (scenario_max_pages={self.scenario_max_pages})"
        )
        if self.verbose:
            print("=" * 50)
        
        for index, analysis_file in enumerate(analysis_files, start=1):
            try:
                self._log(f"\n[LLM] [{index}/{len(analysis_files)}] İşleniyor: {os.path.basename(analysis_file)}")
                
                # Sayfa dosyasını bul
                page_file = self._get_page_file(analysis_file)
                
                if not page_file or not os.path.exists(page_file):
                    print(f"[LLM] HATA: Sayfa dosyası bulunamadı: {page_file}")
                    continue
                
                # Prompt oluştur
                prompt = self.prompt_builder.build_from_files(page_file, analysis_file)
                
                if not prompt:
                    print("[LLM] HATA: Prompt oluşturulamadı")
                    continue
                
                token_estimate = self.prompt_builder.get_token_estimate(prompt)
                self._log(f"[LLM] Prompt hazır (~{token_estimate} token)")
                
                # LLM'den yanıt al
                llm_response = self.ollama_client.generate(prompt)
                
                if not llm_response:
                    print("[LLM] HATA: LLM yanıtı alınamadı")
                    continue
                
                # Yanıtı ayrıştır
                parsed = self.scenario_parser.parse(llm_response)
                
                if parsed["parse_success"]:
                    self._log(f"[LLM] {len(parsed['scenarios'])} senaryo üretildi")
                    # Sonucu kaydet
                    scenario_file = self._save_scenarios(parsed, analysis_file)
                    saved_files.append(scenario_file)
                else:
                    print(f"[LLM] UYARI: Ayrıştırma sorunu - {parsed.get('error', 'Bilinmeyen hata')}")
                    continue
                
                # Özet yazdır
                if self.verbose:
                    self._print_summary(parsed)
                
            except Exception as e:
                print(f"[LLM] HATA: {analysis_file} - {str(e)}")
        
        if self.verbose:
            print("\n" + "=" * 50)
        print(f"[LLM] Toplam {len(saved_files)} senaryo dosyası oluşturuldu.")
        
        return saved_files

    def _prioritize_analysis_files(self, analysis_files: List[str]) -> List[str]:
        """
        Analiz dosyalarını risk seviyesine göre sıralar (yüksekten düşüğe).
        Risk = 100 - overall_score.
        """
        scored = []
        for path in analysis_files:
            risk = 100.0
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                overall = data.get("overall_score", {}).get("score")
                if overall is not None:
                    risk = max(0.0, 100.0 - float(overall))
                else:
                    # Skor yoksa (ör. ölçüm eksik) yüksek öncelik ver.
                    risk = 100.0
            except Exception:
                risk = 100.0
            scored.append((risk, path))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]
    
    def _get_analysis_files(self) -> List[str]:
        """
        Analiz dosyalarının listesini döner.
        
        Returns:
            Sıralı dosya yolları listesi
        """
        try:
            files = []
            for f in sorted(os.listdir(self.analysis_dir)):
                if not f.endswith("_analysis.json"):
                    continue
                path = os.path.join(self.analysis_dir, f)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    status = data.get("analysis_status")
                    if status in ("analyzed", None):
                        files.append(path)
                except Exception:
                    continue
            return files
        except Exception as e:
            print(f"[LLM] HATA: Dosya listesi alınamadı - {str(e)}")
            return []
    
    def _get_page_file(self, analysis_file: str) -> str:
        """
        Analiz dosyasına karşılık gelen sayfa dosyasını bulur.
        
        Args:
            analysis_file: Analiz dosyası yolu
            
        Returns:
            Sayfa dosyası yolu
        """
        # page_001_analysis.json -> page_001.json
        base_name = os.path.basename(analysis_file)
        page_name = base_name.replace("_analysis.json", ".json")
        return os.path.join(self.pages_dir, page_name)
    
    def _save_scenarios(self, parsed: Dict[str, Any], analysis_file: str) -> str:
        """
        Senaryo verilerini JSON dosyasına kaydeder.
        
        Args:
            parsed: Ayrıştırılmış senaryo verisi
            analysis_file: Kaynak analiz dosyası
            
        Returns:
            Kaydedilen dosya yolu
        """
        # Dosya adını belirle (page_001_analysis.json -> page_001_scenarios.json)
        base_name = os.path.basename(analysis_file)
        scenario_name = base_name.replace("_analysis.json", "_scenarios.json")
        scenario_file = os.path.join(self.scenarios_dir, scenario_name)
        
        # URL'yi analiz dosyasından al
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis_data = json.load(f)
            url = analysis_data.get("url", "Bilinmeyen URL")
        except:
            url = "Bilinmeyen URL"
        
        # Kaydet
        output = {
            "url": url,
            "scenarios": parsed.get("scenarios", []),
            "parse_success": parsed.get("parse_success", False),
            "scenario_count": len(parsed.get("scenarios", []))
        }
        
        with open(scenario_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        self._log(f"[LLM] Kaydedildi: {scenario_file}")
        return scenario_file
    
    def _print_summary(self, parsed: Dict[str, Any]) -> None:
        """Senaryo özetini konsola yazdırır."""
        scenarios = parsed.get("scenarios", [])
        
        if not scenarios:
            print("[LLM] Senaryo üretilemedi")
            return
        
        print(f"  ────────────────────────────────────")
        for s in scenarios[:3]:  # İlk 3 senaryoyu göster
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", "medium"), "⚪")
            print(f"  │ {priority_emoji} {s.get('title', 'Başlıksız')[:45]}")
        
        if len(scenarios) > 3:
            print(f"  │ ... ve {len(scenarios) - 3} senaryo daha")
        print(f"  ────────────────────────────────────")
    
    def generate_single(self, page_file: str, analysis_file: str) -> Dict[str, Any]:
        """
        Tek bir sayfa için senaryo üretir (kaydetmeden).
        
        Args:
            page_file: Sayfa dosya yolu
            analysis_file: Analiz dosya yolu
            
        Returns:
            Ayrıştırılmış senaryo verisi
        """
        prompt = self.prompt_builder.build_from_files(page_file, analysis_file)
        
        if not prompt:
            return {"error": "Prompt oluşturulamadı", "scenarios": []}
        
        llm_response = self.ollama_client.generate(prompt)
        
        if not llm_response:
            return {"error": "LLM yanıtı alınamadı", "scenarios": []}
        
        return self.scenario_parser.parse(llm_response)
