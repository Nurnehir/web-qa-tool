"""
Senaryo Ayrıştırma Modülü

LLM'den gelen ham metin yanıtını
yapılandırılmış JSON formatına dönüştürür.
"""

import json
import re
from typing import Dict, Any, List, Optional


class ScenarioParser:
    """
    LLM çıktısını yapılandırılmış senaryolara dönüştüren sınıf.
    
    Ham metin içinden JSON bloklarını çıkarır,
    doğrular ve standart formata dönüştürür.
    """
    
    def __init__(self):
        """ScenarioParser sınıfını başlatır."""
        pass
    
    def parse(self, llm_response: str) -> Dict[str, Any]:
        """
        LLM yanıtını ayrıştırarak senaryolar üretir.
        
        Args:
            llm_response: LLM'den gelen ham metin
            
        Returns:
            Yapılandırılmış senaryo verisi
        """
        result = {
            "raw_response": llm_response,
            "scenarios": [],
            "parse_success": False,
            "error": None
        }
        
        if not llm_response:
            result["error"] = "LLM yanıtı boş"
            return result
        
        # JSON bloğunu bul
        json_content = self._extract_json(llm_response)
        
        if json_content:
            try:
                scenarios = json.loads(json_content)
                
                # Liste değilse listeye çevir
                if isinstance(scenarios, dict):
                    scenarios = [scenarios]
                
                # Her senaryoyu doğrula ve normalize et
                validated_scenarios = []
                for i, scenario in enumerate(scenarios, start=1):
                    validated = self._validate_scenario(scenario, i)
                    if validated:
                        validated_scenarios.append(validated)
                
                result["scenarios"] = validated_scenarios
                result["parse_success"] = len(validated_scenarios) > 0
                
                if not validated_scenarios:
                    result["error"] = "Geçerli senaryo bulunamadı"
                    
            except json.JSONDecodeError as e:
                result["error"] = f"JSON ayrıştırma hatası: {str(e)}"
                # Fallback: metin olarak ayrıştırmayı dene
                fallback_scenarios = self._parse_as_text(llm_response)
                if fallback_scenarios:
                    result["scenarios"] = fallback_scenarios
                    result["parse_success"] = True
                    result["error"] = None
        else:
            # JSON bulunamadı, metin olarak ayrıştırmayı dene
            fallback_scenarios = self._parse_as_text(llm_response)
            if fallback_scenarios:
                result["scenarios"] = fallback_scenarios
                result["parse_success"] = True
            else:
                result["error"] = "JSON bloğu bulunamadı ve metin ayrıştırılamadı"
        
        return result
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Metinden JSON bloğunu çıkarır.
        Birden fazla JSON bloğu varsa hepsini birleştirir.
        
        Args:
            text: Ham metin
            
        Returns:
            JSON string veya None
        """
        import re
        
        # Önce tüm ```json ... ``` bloklarını bul
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', text)
        
        if len(json_blocks) > 1:
            # Birden fazla blok var - hepsini birleştir
            print(f"[PARSER] {len(json_blocks)} ayrı JSON bloğu tespit edildi, birleştiriliyor...")
            all_scenarios = []
            
            for block in json_blocks:
                try:
                    parsed = json.loads(block)
                    if isinstance(parsed, list):
                        all_scenarios.extend(parsed)
                    elif isinstance(parsed, dict):
                        all_scenarios.append(parsed)
                except json.JSONDecodeError:
                    continue
            
            if all_scenarios:
                print(f"[PARSER] Toplam {len(all_scenarios)} senaryo birleştirildi")
                return json.dumps(all_scenarios)
        
        elif len(json_blocks) == 1:
            # Tek blok var - direkt döndür
            try:
                json.loads(json_blocks[0])
                return json_blocks[0]
            except:
                pass
        
        # Fallback: Diğer pattern'leri dene
        patterns = [
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
            r'\[\s*\{[\s\S]*\}\s*\]',        # Doğrudan JSON dizisi
            r'\{[\s\S]*\}'                    # Tek JSON objesi
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                json_str = match.group(1) if match.lastindex else match.group(0)
                try:
                    json.loads(json_str)
                    return json_str
                except:
                    continue
        
        return None
    
    def _validate_scenario(self, scenario: dict, index: int) -> Optional[Dict[str, Any]]:
        """
        Senaryoyu doğrular ve normalize eder.
        
        Args:
            scenario: Ham senaryo verisi
            index: Senaryo indeksi
            
        Returns:
            Doğrulanmış senaryo veya None
        """
        if not isinstance(scenario, dict):
            return None
        
        # Zorunlu alanları kontrol et
        title = scenario.get("title") or scenario.get("baslik") or scenario.get("name")
        if not title:
            return None
        
        # Markdown işaretlerini temizle
        title = str(title).strip().replace("**", "").replace("*", "")
        
        # Adımları al
        steps = scenario.get("steps") or scenario.get("adimlar") or scenario.get("test_steps") or []
        if isinstance(steps, str):
            steps = [steps]
        
        # KALITE KONTROLÜ: Steps içinde metadata varsa temizle
        cleaned_steps = []
        for step in steps:
            step_str = str(step).strip()
            
            # Boş veya çok kısa adımları atla
            if not step_str or len(step_str) < 3:
                continue
            
            # Metadata pattern'leri atla
            if any(pattern in step_str for pattern in ["Title:", "Steps:", "Expected:", "Priority:", "*", "---"]):
                continue
            
            # Markdown temizle
            step_str = step_str.replace("**", "").replace("*", "")
            cleaned_steps.append(step_str)
        
        # En az 2 geçerli adım olmalı
        if len(cleaned_steps) < 2:
            print(f"[PARSER] UYARI: Senaryo '{title}' geçersiz steps içeriyor, atlandı")
            return None
        
        # Beklenen sonucu al
        expected = (
            scenario.get("expected") or 
            scenario.get("beklenen") or 
            scenario.get("expected_result") or
            scenario.get("beklenen_sonuc") or
            "Beklenen sonuç belirtilmedi"
        )
        
        # Önceliği al ve normalize et
        priority = str(scenario.get("priority") or scenario.get("oncelik") or "medium").lower()
        if priority not in ["high", "medium", "low", "yüksek", "orta", "düşük"]:
            priority = "medium"
        
        # Türkçe öncelikleri İngilizce'ye çevir
        priority_map = {"yüksek": "high", "orta": "medium", "düşük": "low"}
        priority = priority_map.get(priority, priority)
        
        return {
            "scenario_id": scenario.get("scenario_id") or scenario.get("id") or index,
            "title": title,
            "steps": cleaned_steps,
            "expected": str(expected).strip(),
            "priority": priority
        }
    
    def _parse_as_text(self, text: str) -> List[Dict[str, Any]]:
        """
        JSON bulunamazsa metni senaryo olarak ayrıştırmayı dener.
        
        Args:
            text: Ham metin
            
        Returns:
            Senaryo listesi
        """
        scenarios = []
        
        # Senaryo başlıklarını bul
        # Patterns: "Senaryo 1:", "1.", "Test Case 1:", vb.
        scenario_patterns = [
            r'(?:Senaryo|Test|Test Case|Scenario)\s*(\d+)[:\s]*(.*?)(?=(?:Senaryo|Test|Test Case|Scenario)\s*\d+|$)',
            r'(\d+)\.\s*(.*?)(?=\d+\.|$)'
        ]
        
        for pattern in scenario_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            
            if matches:
                for i, match in enumerate(matches, start=1):
                    if len(match) >= 2:
                        scenario_id = match[0]
                        content = match[1].strip()
                        
                        if content:
                            # İçerikten adımları çıkarmayı dene
                            steps = re.findall(r'[-•*]\s*(.+)', content)
                            if not steps:
                                # Cümle/paragraf fallback'i ile en az 2 aksiyon adımı üretmeyi dene
                                parts = [p.strip() for p in re.split(r'[.\n]+', content) if p.strip()]
                                steps = parts[:4]
                            # Tek adımlı/generic senaryoları ele
                            if len(steps) < 2:
                                continue
                            
                            scenarios.append({
                                "scenario_id": int(scenario_id) if scenario_id.isdigit() else i,
                                "title": content[:100].split('\n')[0].strip(),
                                "steps": steps[:5],
                                "expected": "Başarıyla tamamlanmalı",
                                "priority": "medium"
                            })
                
                if scenarios:
                    break
        
        return scenarios[:5]  # Maksimum 5 senaryo
    
    def format_scenarios(self, scenarios: List[Dict[str, Any]]) -> str:
        """
        Senaryoları okunabilir metin formatına dönüştürür.
        
        Args:
            scenarios: Senaryo listesi
            
        Returns:
            Formatlanmış metin
        """
        if not scenarios:
            return "Senaryo bulunamadı."
        
        output = []
        for s in scenarios:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s["priority"], "⚪")
            
            output.append(f"\n{priority_emoji} Senaryo {s['scenario_id']}: {s['title']}")
            output.append("  Adımlar:")
            for i, step in enumerate(s["steps"], start=1):
                output.append(f"    {i}. {step}")
            output.append(f"  Beklenen: {s['expected']}")
        
        return "\n".join(output)
