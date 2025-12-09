# src/translation/utils.py

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
