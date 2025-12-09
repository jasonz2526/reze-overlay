import json
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI
import asyncio

class GPTTranslator:
    """
    Context-aware manga translation engine.
    Now supports both:
    - panel → bubbles
    - panel → outside_text
    """

    def __init__(self, model: str = "gpt-5-mini", api_key: Optional[str] = None):
        self.api_key = api_key
        if not self.api_key:
            raise RuntimeError("Missing OpenAI API key")

        #self.client = OpenAI(api_key=self.api_key)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_retries = 3

    # Prompt builder
    def _build_prompt(self, page_json: Dict[str, Any]) -> str:
        schema = """
{
  "panels": [
    {
      "panel_id": <int>,
      "bubbles": [
        {
          "bubble_id": <int>,
          "jp": "<original>",
          "en": "<translation>"
        }
      ],
      "outside_text": [
        {
          "text_id": <int>,
          "jp": "<original>",
          "en": "<translation>"
        }
      ]
    }
  ]
}
"""

        return f"""
You are a professional manga translator.

Translate the following manga page into natural English while preserving:
- humor
- tone
- emotional nuance
- character voice
- trailing ellipses (…)
- dramatic pauses
- manga-typical implied meaning, but do NOT add meaning

DO NOT:
- reorder items
- merge bubbles
- remove punctuation
- add explanations
- add honorifics unless necessary

Return ONLY valid JSON in this exact schema:

{schema}

Here is the page to translate:

{json.dumps(page_json, ensure_ascii=False, indent=2)}
"""
    # Extract text safely from OpenAI response
    async def _call_llm(self, prompt: str) -> str:
        response = await self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        # Find the assistant "output_text" block
        for block in response.output:
            if block.type == "message":
                for item in block.content:
                    if item.type == "output_text":
                        return item.text

        raise ValueError(
            "No output_text found in response.\n"
            + json.dumps(response.model_dump(), indent=2, ensure_ascii=False)
        )

    # Validate & parse returned JSON
    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text.strip())
        except Exception:
            return None

    # Public API — translate full page
    async def translate_page(self, page_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        page_json must be your panel output:
        {
          "panels": [
             {
               "bbox": [...],
               "bubbles": [...],
               "outside_text": [...]
             }
          ]
        }
        """
        prompt = self._build_prompt(page_json)

        for attempt in range(self.max_retries):
            raw = await self._call_llm(prompt)
            parsed = self._safe_json_parse(raw)

            if parsed and "panels" in parsed:
                return parsed

            print(f"[WARN] JSON parse failed on attempt {attempt+1}. Retrying...")
            await asyncio.sleep(0.4)

        raise ValueError("LLM failed to output valid JSON.")

    # Flatten for evaluation later
    @staticmethod
    def flatten(translated_json: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Converts nested structure into a flat list for:
        - diffing with official translations
        - evaluation datasets
        - debugging
        """
        rows = []

        for panel in translated_json.get("panels", []):
            pid = panel["panel_id"]

            # bubbles
            for b in panel.get("bubbles", []):
                rows.append({
                    "type": "bubble",
                    "panel_id": pid,
                    "id": b["bubble_id"],
                    "jp": b["jp"],
                    "en": b["en"],
                })

            # outside text
            for t in panel.get("outside_text", []):
                rows.append({
                    "type": "outside",
                    "panel_id": pid,
                    "id": t["text_id"],
                    "jp": t["jp"],
                    "en": t["en"],
                })

        return rows
