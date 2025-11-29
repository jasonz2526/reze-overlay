def merge_panels_and_translations(detector_panels, gpt_output):
    """
    Merge YOLO/OCR panel structure with GPT translation output.

    detector_panels: list of panels from your pipeline
    gpt_output: { "panels": [...] } from GPTTranslator

    Returns:
        { "panels": [ ... merged panels ... ] }
    """

    # -----------------------------------------------------------
    # 1. Build lookup tables from GPT output
    # -----------------------------------------------------------
    gpt_bubble_lookup = {
        (p["panel_id"], b["bubble_id"]): b
        for p in gpt_output.get("panels", [])
        for b in p.get("bubbles", [])
    }

    gpt_outside_lookup = {
        (p["panel_id"], t["text_id"]): t
        for p in gpt_output.get("panels", [])
        for t in p.get("outside_text", [])
    }

    # -----------------------------------------------------------
    # 2. Merge into one structure
    # -----------------------------------------------------------
    merged = []

    for p_idx, det_panel in enumerate(detector_panels, start=1):
        merged_panel = {
            "panel_id": p_idx,
            "bbox": det_panel["bbox"],
            "bubbles": [],
            "outside_text": []
        }

        # ---------- Merge bubbles ----------
        for b_idx, bubble in enumerate(det_panel.get("bubbles", []), start=1):
            key = (p_idx, b_idx)
            if key in gpt_bubble_lookup:
                trans = gpt_bubble_lookup[key]
                merged_panel["bubbles"].append({
                    "bubble_id": b_idx,
                    "bbox": bubble["bbox"],
                    "jp": trans["jp"],
                    "en": trans["en"]
                })
            else:
                # Fallback: if GPT missed one
                merged_panel["bubbles"].append({
                    "bubble_id": b_idx,
                    "bbox": bubble["bbox"],
                    "jp": bubble.get("ocr_text", ""),  # or get_sorted_text()
                    "en": "<missing>"
                })

        # ---------- Merge outside text ----------
        for t_idx, text_entry in enumerate(det_panel.get("outside_text", []), start=1):
            key = (p_idx, t_idx)
            if key in gpt_outside_lookup:
                trans = gpt_outside_lookup[key]
                merged_panel["outside_text"].append({
                    "text_id": t_idx,
                    "bbox": text_entry["bbox"],
                    "jp": trans["jp"],
                    "en": trans["en"]
                })
            else:
                merged_panel["outside_text"].append({
                    "text_id": t_idx,
                    "bbox": text_entry["bbox"],
                    "jp": text_entry.get("ocr_text", ""),
                    "en": "<missing>"
                })

        merged.append(merged_panel)

    return {"panels": merged}
