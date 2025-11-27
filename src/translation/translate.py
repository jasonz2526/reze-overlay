# src/translation/translate.py

from deepl import Translator

class MangaTranslator:
    def __init__(self, auth_key: str):
        self.translator = Translator(auth_key)

    def translate(self, text: str, target_lang="EN-US"):
        if not text.strip():
            return ""
        try:
            result = self.translator.translate_text(
                text,
                target_lang=target_lang
            )
            return result.text
        except Exception as e:
            print(f"[Translation Error] {e}")
            return text  # fallback
