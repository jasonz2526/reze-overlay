from prev.pipeline import MangaPipeline
from src.translation.translate import MangaTranslator
import json
from dotenv import load_dotenv
import os

load_dotenv()
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

def main():
    pipeline = MangaPipeline("models/bubble_detector_best.pt")
    translator = MangaTranslator(DEEPL_API_KEY)

    image_path = "images/testv2.jpg"

    result = pipeline.process_page(image_path=image_path)
    print("\n=== RAW OCR RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    pipeline.visualize_result(result, image_path)

    # Sort text inside each bubble (right-to-left for vertical bubbles)
    def get_sorted_text(bubble):
        ocr_list = bubble["ocr"]
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

    translated_output = {
        "bubbles": [],
        "outside_text": []
    }

    for i, bubble in enumerate(result["bubbles"], start=1):
        original_text = get_sorted_text(bubble)
        translated_text = translator.translate(original_text)

        print(f"Bubble {i}: {original_text}  -->  {translated_text}")

        translated_output["bubbles"].append({
            "id": i,
            "original": original_text,
            "translated": translated_text,
            "bbox": bubble["bbox"] if "bbox" in bubble else None
        })

    print("\n=== OUTSIDE TEXT ===")
    for i, region in enumerate(result["outside_text"], start=1):
        original_text = get_sorted_text(region)
        translated_text = translator.translate(original_text)

        print(f"Outside {i}: {original_text}  -->  {translated_text}")

        translated_output["outside_text"].append({
            "id": i,
            "original": original_text,
            "translated": translated_text,
            "bbox": region["bbox"] if "bbox" in region else None
        })

    # for debugging or next step
    print("\n=== FINAL TRANSLATED OUTPUT ===")
    print(json.dumps(translated_output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
