"""
Ollama API İstemcisi

Yerel Ollama sunucusuyla iletişim kurarak
LLM'den yanıt alır.
"""

import httpx
from typing import Optional, Dict, Any


class OllamaClient:
    """
    Ollama API ile iletişim kuran sınıf.
    
    Yerel Ollama sunucusuna istek atarak
    LLM'den test senaryoları üretir.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        """
        OllamaClient sınıfını başlatır.
        
        Args:
            base_url: Ollama sunucu adresi
            model: Kullanılacak model adı
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.generate_url = f"{self.base_url}/api/generate"
        self.chat_url = f"{self.base_url}/api/chat"
    
    def generate(self, prompt: str, temperature: float = 0.4, max_tokens: int = 1536) -> Optional[str]:
        """
        Verilen prompt için LLM'den yanıt üretir.
        
        Args:
            prompt: Gönderilecek prompt
            temperature: Yaratıcılık seviyesi (0-1) - Orta = daha çeşitli
            max_tokens: Maksimum yanıt token sayısı - Orta = 3-4 senaryo
            
        Returns:
            LLM yanıtı veya None
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_k": 20,  # Biraz arttırdık (çeşitlilik için)
                "top_p": 0.92,  # Biraz arttırdık
                "repeat_penalty": 1.1,
                "num_ctx": 3072  # Arttırdık (3-4 senaryo sığsın)
            }
        }
        
        try:
            print(f"[OLLAMA] İstek gönderiliyor ({self.model})...")
            
            # LLM yanıtı uzun sürebilir, timeout yüksek tutuldu
            with httpx.Client(timeout=300.0) as client:
                response = client.post(self.generate_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("response", "")
                    
                    # İstatistikler
                    total_duration = data.get("total_duration", 0) / 1e9  # nanosaniye -> saniye
                    eval_count = data.get("eval_count", 0)
                    
                    print(f"[OLLAMA] Yanıt alındı ({eval_count} token, {total_duration:.1f} saniye)")
                    return result
                else:
                    print(f"[OLLAMA] HTTP hatası: {response.status_code}")
                    print(f"[OLLAMA] Yanıt: {response.text[:200]}")
                    return None
                    
        except httpx.ConnectError:
            print("[OLLAMA] HATA: Ollama sunucusuna bağlanılamadı!")
            print("[OLLAMA] Ollama'nın çalıştığından emin olun: ollama serve")
            return None
        except httpx.TimeoutException:
            print("[OLLAMA] HATA: İstek zaman aşımına uğradı (5 dakika)")
            return None
        except Exception as e:
            print(f"[OLLAMA] Beklenmeyen hata: {str(e)}")
            return None
    
    def chat(self, messages: list, temperature: float = 0.7) -> Optional[str]:
        """
        Chat formatında LLM'den yanıt alır.
        
        Args:
            messages: Mesaj listesi [{"role": "user", "content": "..."}]
            temperature: Yaratıcılık seviyesi
            
        Returns:
            LLM yanıtı veya None
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            print(f"[OLLAMA] Chat isteği gönderiliyor ({self.model})...")
            
            with httpx.Client(timeout=300.0) as client:
                response = client.post(self.chat_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    result = message.get("content", "")
                    print(f"[OLLAMA] Chat yanıtı alındı")
                    return result
                else:
                    print(f"[OLLAMA] HTTP hatası: {response.status_code}")
                    return None
                    
        except httpx.ConnectError:
            print("[OLLAMA] HATA: Ollama sunucusuna bağlanılamadı!")
            return None
        except Exception as e:
            print(f"[OLLAMA] Beklenmeyen hata: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """
        Ollama sunucusunun erişilebilir olup olmadığını kontrol eder.
        
        Returns:
            True eğer sunucu erişilebilirse
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> list:
        """
        Kullanılabilir modelleri listeler.
        
        Returns:
            Model adları listesi
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return [m["name"] for m in models]
                return []
        except:
            return []
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Kullanılan model hakkında bilgi alır.
        
        Returns:
            Model bilgileri veya None
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model}
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        except:
            return None
