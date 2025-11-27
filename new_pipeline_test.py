from src.new_pipeline import MangaPipeline
from src.translation.translate import MangaTranslator
from src.translation.gpt import GPTTranslator
import json
import os
from dotenv import load_dotenv

load_dotenv()

REZE_OPENAI_API_KEY = os.getenv("REZE_OPENAI_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

def get_sorted_text(region):
    """Sort OCR words inside a bubble or text box."""
    words = region["ocr"]
    if not words:
        return ""

    total_width = sum(w["box"][2] - w["box"][0] for w in words)
    total_height = sum(w["box"][3] - w["box"][1] for w in words)
    is_vertical = total_height > total_width

    if is_vertical:
        # Vertical text → right→left, top→bottom
        words = sorted(words, key=lambda w: (-w["box"][2], w["box"][1]))
    else:
        # Horizontal text → top→bottom, left→right
        words = sorted(words, key=lambda w: (w["box"][1], w["box"][0]))

    return "".join(w["text"] for w in words)


def build_gpt_page_json(panels):
    """
    Converts OCR output into the JSON format expected by GPTTranslator.
    Includes both bubbles and outside_text.
    """

    def get_sorted_text(region):
        ocr_list = region["ocr"]
        if not ocr_list:
            return ""

        total_width = sum(w["box"][2] - w["box"][0] for w in ocr_list)
        total_height = sum(w["box"][3] - w["box"][1] for w in ocr_list)
        is_vertical = total_height > total_width

        if is_vertical:
            ocr_sorted = sorted(ocr_list, key=lambda w: (-w["box"][2], w["box"][1]))
        else:
            ocr_sorted = sorted(ocr_list, key=lambda w: (w["box"][1], w["box"][0]))

        return "".join([w["text"] for w in ocr_sorted])

    page = {"panels": []}

    for p_idx, panel in enumerate(panels, start=1):

        new_panel = {
            "panel_id": p_idx,
            "bubbles": [],
            "outside_text": []
        }

        # bubbles
        for b_idx, bubble in enumerate(panel["bubbles"], start=1):
            jp_text = get_sorted_text(bubble)
            new_panel["bubbles"].append({
                "bubble_id": b_idx,
                "jp": jp_text
            })
        # outside text 
        for t_idx, region in enumerate(panel["outside_text"], start=1):
            jp_text = get_sorted_text(region)
            new_panel["outside_text"].append({
                "text_id": t_idx,
                "jp": jp_text
            })

        page["panels"].append(new_panel)

    return page


def main():

    pipeline = MangaPipeline(
        panel_model_path="models/best_109.pt",
        bubble_model_path="models/new_text_best.pt"
    )
    deepl = MangaTranslator(DEEPL_API_KEY)
    gpt = GPTTranslator(model="gpt-5-mini", api_key=REZE_OPENAI_API_KEY)

    image_path = "/Users/jasonzhao/reze-overlay/images/0026.jpg"
    result = pipeline.process_page(image_path)
    panels = result["panels"]

    gpt_page_json = build_gpt_page_json(panels)
    gpt_output = gpt.translate_page(gpt_page_json)

    # Make lookup table for GPT translations
    gpt_lookup = {}

    for p in gpt_output["panels"]:
        pid = p["panel_id"]

        # ---- bubbles ----
        for b in p.get("bubbles", []):
            gpt_lookup[(pid, "bubble", b["bubble_id"])] = b["en"]

        # ---- outside text ----
        for t in p.get("outside_text", []):
            gpt_lookup[(pid, "text", t["text_id"])] = t["en"]


    print("\n=== TRANSLATION COMPARISON ===\n")

    for p_idx, panel in enumerate(panels, start=1):
        print(f"\n===== PANEL {p_idx} =====")

        # ------------------------------
        # BUBBLES
        # ------------------------------
        for b_idx, bubble in enumerate(panel["bubbles"], start=1):
            jp = get_sorted_text(bubble)
            deepl_en = deepl.translate(jp)

            gpt_en = gpt_lookup.get((p_idx, "bubble", b_idx), "<missing>")

            print(f"\nBubble {b_idx}:")
            print(f"JP: {jp}")
            print(f"GPT   → {gpt_en}")
            print(f"DeepL → {deepl_en}")

        # ------------------------------
        # OUTSIDE TEXT
        # ------------------------------
        for t_idx, text in enumerate(panel["outside_text"], start=1):
            jp = get_sorted_text(text)
            deepl_en = deepl.translate(jp)

            gpt_en = gpt_lookup.get((p_idx, "text", t_idx), "<missing>")

            print(f"\nOutside Text {t_idx}:")
            print(f"JP: {jp}")
            print(f"GPT   → {gpt_en}")
            print(f"DeepL → {deepl_en}")


if __name__ == "__main__":
    main()