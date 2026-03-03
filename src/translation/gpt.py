import json
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI
import asyncio
import re
from src.translation.utils import (
    build_compact_gpt_input,
    reconstruct_gpt_output_from_compact,
)

class GPTTranslator:
    """
    Context-aware manga translation engine.
    Now supports both:
    - panel → bubbles
    - panel → outside_text
    """

    def __init__(self, model: str, api_key: Optional[str] = None):
        self.api_key = api_key
        if not self.api_key:
            raise RuntimeError("Missing OpenAI API key")

        #self.client = OpenAI(api_key=self.api_key)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_retries = 2
        self.last_metrics: Dict[str, Any] = {}

    # Prompt builder
    def _build_prompt(self, compact_json: Dict[str, Any]) -> str:
        ids = [row["i"] for row in compact_json.get("l", []) if isinstance(row, dict) and "i" in row]
        return f"""
You are a professional manga translator.

Translate each Japanese line into natural English while preserving tone, nuance, voice,
and punctuation. Lines are already in manga reading order. Use nearby lines for context, but translate each line independently.

STRICT OUTPUT CONTRACT (must follow exactly):
1) Return a single JSON object only (no markdown/code fences).
2) Top-level key must be "l".
3) "l" must be an array of objects with exactly keys:
   - "i": id (string)
   - "e": English translation (string)
4) Keep the same ids and order as input.
5) Do not add/remove rows.
6) Do not add explanations.

Return ONLY strict JSON with this exact compact schema:
{{
  "l": [
    {{"i": "p1b1", "e": "<translation>"}}
  ]
}}

Input ids in order (must match exactly):
{json.dumps(ids, ensure_ascii=False)}

Here is the page to translate:

{json.dumps(compact_json, ensure_ascii=False, separators=(",", ":"))}
"""
    # Extract text safely from OpenAI response
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        started = time.perf_counter()
        response = await self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage", None)

        usage_dict = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "latency_ms": elapsed_ms,
            "model": self.model,
        }

        # Find the assistant "output_text" block
        for block in response.output:
            if block.type == "message":
                for item in block.content:
                    if item.type == "output_text":
                        return {"text": item.text, "usage": usage_dict}

        raise ValueError(
            "No output_text found in response.\n"
            + json.dumps(response.model_dump(), indent=2, ensure_ascii=False)
        )

    # Validate & parse returned JSON
    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        def try_load(candidate: str) -> Optional[Dict[str, Any]]:
            try:
                parsed = json.loads(candidate)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None

        try:
            # Fast path: already strict JSON
            parsed = json.loads(text.strip())
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

        # Strip markdown code fences if present.
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fenced:
            parsed = try_load(fenced.group(1).strip())
            if parsed is not None:
                return parsed

        # Try to extract the first balanced JSON object from noisy text.
        start = text.find("{")
        if start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == "\"":
                        in_str = False
                else:
                    if ch == "\"":
                        in_str = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            candidate = text[start:i + 1]
                            parsed = try_load(candidate)
                            if parsed is not None:
                                return parsed
                            break

        return None

    def _normalize_compact_output(
        self, parsed: Dict[str, Any], expected_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Accept mild schema drift and normalize into:
        {"l":[{"i":"...","e":"..."}]}
        """
        if not isinstance(parsed, dict):
            return None

        raw_lines = parsed.get("l")
        if raw_lines is None:
            raw_lines = parsed.get("lines")
        if raw_lines is None:
            return None
        if not isinstance(raw_lines, list):
            return None

        expected_set = set(expected_ids)
        normalized_by_id: Dict[str, str] = {}

        for row in raw_lines:
            if not isinstance(row, dict):
                continue

            rid = row.get("i", row.get("id"))
            if not isinstance(rid, str):
                continue
            if rid not in expected_set:
                continue
            if rid in normalized_by_id:
                continue

            en = row.get("e", row.get("en", row.get("text", row.get("translation", ""))))
            if en is None:
                en = ""
            if not isinstance(en, str):
                en = str(en)

            normalized_by_id[rid] = en.strip()

        if not normalized_by_id:
            return None

        normalized_lines = []
        for rid in expected_ids:
            normalized_lines.append({"i": rid, "e": normalized_by_id.get(rid, "<missing>")})

        return {"l": normalized_lines}

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
        prompt_started = time.perf_counter()
        compact_input = build_compact_gpt_input(page_json)
        prompt = self._build_prompt(compact_input)
        prompt_build_ms = int((time.perf_counter() - prompt_started) * 1000)
        last_usage = {}
        expected_ids = [
            row["i"]
            for row in compact_input.get("l", [])
            if isinstance(row, dict) and "i" in row
        ]

        for attempt in range(self.max_retries):
            call_result = await self._call_llm(prompt)
            raw = call_result["text"]
            last_usage = call_result.get("usage", {})
            parsed = self._safe_json_parse(raw)
            normalized = self._normalize_compact_output(parsed, expected_ids) if parsed else None

            if normalized and isinstance(normalized.get("l"), list):
                self.last_metrics = {
                    **last_usage,
                    "attempts": attempt + 1,
                    "protocol": "compact-v1",
                    "input_lines": len(compact_input.get("l", [])),
                    "prompt_build_ms": prompt_build_ms,
                }
                return reconstruct_gpt_output_from_compact(page_json, normalized)

            print(f"[WARN] JSON parse failed on attempt {attempt+1}. Retrying...")
            await asyncio.sleep(0.4)

        self.last_metrics = {
            **last_usage,
            "attempts": self.max_retries,
            "protocol": "compact-v1",
            "failed": True,
            "prompt_build_ms": prompt_build_ms,
        }

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
