from deepl import Translator
from typing import Any, Dict, List, Tuple, Optional

class MangaTranslator:
    def __init__(self, auth_key: str):
        self.translator = Translator(auth_key)

    def translate(self, text: str, target_lang: str = "EN-US") -> str:
        if not text.strip():
            return ""
        try:
            result = self.translator.translate_text(text, target_lang=target_lang)
            return result.text
        except Exception as e:
            print(f"[Translation Error] {e}")
            return text  # fallback

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str = "EN-US",
        source_lang: Optional[str] = "JA",
    ) -> List[str]:
        """
        Batch translate texts. Returns a list of translated strings in the same order.
        Preserves empty/whitespace-only entries as "".
        """
        # Keep positions so we can re-insert empties without sending them to the API
        idx_map: List[int] = []
        to_send: List[str] = []
        out: List[str] = [""] * len(texts)

        for i, t in enumerate(texts):
            if t and t.strip():
                idx_map.append(i)
                to_send.append(t)
            else:
                out[i] = ""

        if not to_send:
            return out

        try:
            results = self.translator.translate_text(
                to_send,
                target_lang=target_lang,
                source_lang=source_lang,
            )

            # DeepL returns either a single result or a list depending on input
            if not isinstance(results, list):
                results = [results]

            for i, res in zip(idx_map, results):
                out[i] = res.text

            return out

        except Exception as e:
            print(f"[Batch Translation Error] {e}")
            # fallback: return originals (but still keep empties as "")
            for i in idx_map:
                out[i] = texts[i]
            return out

    def translate_panels_schema(
        self,
        data: Dict[str, Any],
        target_lang: str = "EN-US",
        source_lang: Optional[str] = "JA",
        overwrite_jp_with_tl: bool = False,
    ) -> Dict[str, Any]:
        """
        Transforms:
          {"jp": "..."} -> {"jp":"TL","en":"..."}
        for bubbles and outside_text in each panel.
        Mutates `data` in-place and also returns it.
        """

        # 1) Collect texts + references to their dict objects
        texts: List[str] = []
        refs: List[Tuple[Dict[str, Any], str]] = []  # (object_dict, key_name_where_text_was)

        for panel in data.get("panels", []):
            for bubble in panel.get("bubbles", []):
                jp = bubble.get("jp", "")
                texts.append(jp)
                refs.append((bubble, "jp"))

            for t in panel.get("outside_text", []):
                jp = t.get("jp", "")
                texts.append(jp)
                refs.append((t, "jp"))

        # 2) Batch translate
        translations = self.translate_batch(
            texts,
            target_lang=target_lang,
            source_lang=source_lang,
        )

        # 3) Write back in the exact schema you want
        for (obj, _), en in zip(refs, translations):
            if overwrite_jp_with_tl:
                obj["jp"] = "TL"
            # else: keep original jp untouched
            obj["en"] = en

        return data
