"""
LLM istemcisi — Ollama üzerinden llama3 kullanır.

Kurulum:
  1. https://ollama.com adresinden Ollama'yı indirin ve kurun
  2. Terminal'de: ollama pull llama3
  3. Ollama otomatik olarak localhost:11434 üzerinde çalışır

Ollama, OpenAI uyumlu API sunar — openai paketi ile direkt kullanılır.
"""
import os
import json
import re
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
jinja_env = Environment(loader=FileSystemLoader(PROMPT_DIR))


class LLMClient:
    """
    Ollama / llama3 ile test senaryosu üretir.
    .env'deki OLLAMA_BASE_URL ve OLLAMA_MODEL ile yapılandırılır.
    """

    def __init__(self):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        # Ollama OpenAI uyumlu API sunar; api_key zorunlu ama değeri önemli değil
        self.client = OpenAI(base_url=base_url, api_key="ollama")

    def _build_prompt(self, page_url: str, page_type: str, page_type_label: str,
                      markdown_content: str, findings: List, quality_score: float) -> str:
        template_name = f"{page_type}.j2"
        try:
            template = jinja_env.get_template(template_name)
        except Exception:
            template = jinja_env.get_template("base_prompt.j2")

        return template.render(
            page_url=page_url,
            page_type=page_type,
            page_type_label=page_type_label,
            markdown_content=markdown_content,
            findings=findings,
            quality_score=quality_score,
        )

    def generate_scenarios(self, page_url: str, page_type: str,
                           markdown_content: str, findings: List,
                           quality_score: float) -> Dict[str, Any]:
        from llm_engine.page_classifier import PAGE_TYPES
        page_type_label = PAGE_TYPES.get(page_type, "Genel sayfa")

        prompt = self._build_prompt(
            page_url, page_type, page_type_label,
            markdown_content, findings, quality_score
        )

        for attempt in range(2):
            try:
                raw = self._call_api(prompt)
                return self._parse_response(raw)
            except (json.JSONDecodeError, KeyError) as e:
                if attempt == 1:
                    raise RuntimeError(f"LLM geçerli JSON döndürmedi: {e}\nHam yanıt: {raw[:200]}")
                print(f"[WARN] JSON parse hatası, yeniden deneniyor... ({e})")

    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """Ham LLM yanıtını JSON'a dönüştürür."""
        # ```json ... ``` bloku içinde gelebilir
        cleaned = re.sub(r'```json\s*|\s*```', '', raw).strip()
        # İlk { ile son } arasını al
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)
