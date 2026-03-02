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


def build_compact_gpt_input(page_json):
    """
    Build a compact line-list payload for GPT:
    {
      "l": [
        {"i": "p1b1", "j": "<jp>"},
        {"i": "p1o1", "j": "<jp>"}
      ]
    }
    """
    compact = {"l": []}

    for panel in page_json.get("panels", []):
        pid = panel["panel_id"]

        for bubble in panel.get("bubbles", []):
            compact["l"].append({
                "i": f"p{pid}b{bubble['bubble_id']}",
                "j": bubble.get("jp", ""),
            })

        for outside in panel.get("outside_text", []):
            compact["l"].append({
                "i": f"p{pid}o{outside['text_id']}",
                "j": outside.get("jp", ""),
            })

    return compact


def reconstruct_gpt_output_from_compact(page_json, compact_output):
    """
    Reconstruct the original panel schema from compact GPT output.

    compact_output schema:
    {
      "l": [
        {"i": "p1b1", "e": "<en>"},
        ...
      ]
    }
    """
    en_lookup = {
        row.get("i"): row.get("e", "<missing>")
        for row in compact_output.get("l", [])
        if isinstance(row, dict) and "i" in row
    }

    reconstructed = {"panels": []}

    for panel in page_json.get("panels", []):
        pid = panel["panel_id"]
        new_panel = {
            "panel_id": pid,
            "bubbles": [],
            "outside_text": [],
        }

        for bubble in panel.get("bubbles", []):
            bid = bubble["bubble_id"]
            key = f"p{pid}b{bid}"
            new_panel["bubbles"].append({
                "bubble_id": bid,
                "jp": bubble.get("jp", ""),
                "en": en_lookup.get(key, "<missing>"),
            })

        for outside in panel.get("outside_text", []):
            tid = outside["text_id"]
            key = f"p{pid}o{tid}"
            new_panel["outside_text"].append({
                "text_id": tid,
                "jp": outside.get("jp", ""),
                "en": en_lookup.get(key, "<missing>"),
            })

        reconstructed["panels"].append(new_panel)

    return reconstructed
