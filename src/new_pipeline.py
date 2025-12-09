import cv2
from ultralytics import YOLO
from src.ocr.manga_ocr import OCRReader
import os
import numpy as np

class MangaPipeline:
    def __init__(self, panel_model_path, bubble_model_path):
        print("Loading panel model…")
        self.panel_detector = YOLO(panel_model_path)

        print("Loading bubble/text model…")
        self.bubble_detector = YOLO(bubble_model_path)

        print("Initializing OCR…")
        self.ocr = OCRReader()


    def process_page(self, image):
        # If already a NumPy image, use it directly
        if isinstance(image, np.ndarray):
            img = image
        else:
            # otherwise assume it's a path
            img = cv2.imread(image)

        if img is None:
            raise ValueError("Failed to load image (bad path or bad input array).")
        h, w = img.shape[:2]

        # DETECT PANELS
        panel_results = self.panel_detector(img)[0]
        panels = []

        for b in panel_results.boxes:
            cls = int(b.cls[0])
            if cls != 0:
                continue # (Not using Class 1 Text here, only Class 0 panels)

            x1, y1, x2, y2 = b.xyxy[0].tolist()
            conf = float(b.conf[0])

            panels.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "bubbles": [],
                "outside_text": []
            })

        # Gets rid of overlapping panels, then sorts (WIP, sorting is hard)
        panels = dedupe_panels_by_containment(panels, containment_thresh=0.75)
        panels = sort_panels_reading_order_two_page(panels, w, h, rtl=True)

        # Bubble + Text Detection
        bubble_results = self.bubble_detector(img)[0]
        boxes = bubble_results.boxes

        filtered_boxes = []
        max_area = 0.08 * w * h  # 8% of page area

        for b in boxes:
            x1, y1, x2, y2 = b.xyxy[0]
            area = (x2 - x1) * (y2 - y1)
            if area < max_area:
                filtered_boxes.append(b) # No massive boxes allowed

        bubble_entries = []
        for b in filtered_boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            raw_cls = int(b.cls[0])
            label = "bubble" if raw_cls == 1 else "outside"
            conf = float(b.conf[0])

            crop = img[int(y1):int(y2), int(x1):int(x2)]
            ocr_output = self.ocr.read_text(crop)

            bubble_entries.append({
                "bbox": [x1, y1, x2, y2],
                "label": label,
                "confidence": conf,
                "ocr": ocr_output
            })

        # Assign every bubble/text to its closest respective panel
        for entry in bubble_entries:
            bx = entry["bbox"]
            bubble_area = (bx[2] - bx[0]) * (bx[3] - bx[1])

            best_panel = None
            best_ratio = 0
            best_distance = float("inf")
            closest_panel = None

            for p in panels:
                px1, py1, px2, py2 = p["bbox"]

                # Overlap ratio
                overlap = box_overlap(bx, p["bbox"])
                ratio = overlap / bubble_area

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_panel = p

                # Compute center distance (for fallback)
                bx_center = (bx[0] + bx[2]) / 2
                by_center = (bx[1] + bx[3]) / 2
                px_center = (px1 + px2) / 2
                py_center = (py1 + py2) / 2

                dist = (bx_center - px_center) ** 2 + (by_center - py_center) ** 2
                if dist < best_distance:
                    best_distance = dist
                    closest_panel = p

            # Primary Case: Most the bubble is in panel
            if best_ratio > 0.3 and best_panel:
                target_panel = best_panel

            # Secondary: Just choose the closest panel
            else:
                target_panel = closest_panel

            if entry["label"] == "bubble":
                target_panel["bubbles"].append(entry)
            else:
                target_panel["outside_text"].append(entry)
        
        for panel in panels:
            # 1. Merge lists to check for overlaps across categories
            combined_regions = panel["bubbles"] + panel["outside_text"]

            # 2. Dedupe based on coordinates
            unique_regions = dedupe_by_coordinates(combined_regions, iou_thresh=0.6)

            # 3. Sort the clean list by reading order
            sorted_unique_regions = sort_bubbles_inside_panel(unique_regions)

            # 4. Split back into specific lists
            panel["bubbles"] = [
                r for r in sorted_unique_regions if r["label"] == "bubble"
            ]
            panel["outside_text"] = [
                r for r in sorted_unique_regions if r["label"] != "bubble"
            ]

        return {
            "panels": panels
        }


    def visualize_result(self, result, image_path, save_path="/Users/jasonzhao/reze-overlay/images"): # DEBUG METHOD
        """Draw panels, bubbles, and outside text boxes on an image."""
        img = cv2.imread(image_path)

        panels = result["panels"]

        PANEL_COLOR = (255, 128, 0)
        BUBBLE_COLOR = (0, 255, 0)
        OUTSIDE_COLOR = (0, 0, 255)

        for p_idx, panel in enumerate(panels, start=1):
            x1, y1, x2, y2 = map(int, panel["bbox"])

            cv2.rectangle(img, (x1, y1), (x2, y2), PANEL_COLOR, 2)

            cv2.putText(img, f"P{p_idx}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, PANEL_COLOR, 2)

            for b_idx, bubble in enumerate(panel["bubbles"], start=1):
                bx1, by1, bx2, by2 = map(int, bubble["bbox"])

                cv2.rectangle(img, (bx1, by1), (bx2, by2), BUBBLE_COLOR, 2)
                cv2.putText(img, f"P{p_idx}-B{b_idx}", (bx1, by1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, BUBBLE_COLOR, 2)

            for t_idx, region in enumerate(panel["outside_text"], start=1):
                tx1, ty1, tx2, ty2 = map(int, region["bbox"])

                cv2.rectangle(img, (tx1, ty1), (tx2, ty2), OUTSIDE_COLOR, 2)
                cv2.putText(img, f"P{p_idx}-O{t_idx}", (tx1, ty1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, OUTSIDE_COLOR, 2)

        if save_path is None:
            save_path = image_path.replace(".jpg", "_debug.jpg")
        else:
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            debug_filename = f"{name}_debug_panel{ext}"
            save_path = os.path.join(save_path, debug_filename)

        cv2.imwrite(save_path, img)
        print(f"[✓] Visualization saved to {save_path}")
        

        return save_path
    
def get_centroid(bbox):
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

def is_point_in_box(point, box):
    px, py = point
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2

def sort_panels_reading_order(panels, rtl=True, col_overlap_ratio=0.4):
    """
    Improved manga panel ordering heuristic:
    1. Group by rows (via vertical center proximity).
    2. Sort rows TTB.
    3. Inside each row, sort subgroups (vertical stacks) before crossing horizontally.
    """

    if not panels:
        return []

    enriched = []
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        enriched.append({
            "data": p,
            "x_center": (x1 + x2)/2,
            "y_center": (y1 + y2)/2,
            "w": x2 - x1,
            "h": y2 - y1,
            "x1": x1, "x2": x2,
            "y1": y1, "y2": y2
        })

    # Average panel height
    avg_h = sum(e["h"] for e in enriched) / len(enriched)
    row_tol = avg_h * col_overlap_ratio

    # Group panels into reading rows 
    enriched.sort(key=lambda e: e["y_center"])
    rows = []

    for p in enriched:
        placed = False
        for row in rows:
            # Compare to row vertical center
            row_avg_y = sum(e["y_center"] for e in row) / len(row)
            if abs(p["y_center"] - row_avg_y) <= row_tol:
                row.append(p)
                placed = True
                break
        if not placed:
            rows.append([p])

    # Sort rows Top To Bottom
    rows.sort(key=lambda row: min(p["y_center"] for p in row))

    def vertical_groups(row):
        row = sorted(row, key=lambda p: p["x_center"], reverse=rtl)
        groups = []
        for p in row:
            placed = False
            for g in groups:
                # If horizontally close, likely stacked vertically
                if abs(p["x_center"] - g[0]["x_center"]) < p["w"] * 0.5:
                    g.append(p)
                    placed = True
                    break
            if not placed:
                groups.append([p])

        # sort each group vertically (TTB)
        for g in groups:
            g.sort(key=lambda p: p["y_center"])

        # keep groups in RTL order
        return groups

    # Build Final Ordering
    final = []
    for row in rows:
        groups = vertical_groups(row)

        # extend groups in the correct reading direction
        for g in groups:
            final.extend([p["data"] for p in g])

    return final


def sort_panels_reading_order_two_page(panels, img_width, img_height, rtl=True, col_overlap_ratio=0.):
    """
    Enhanced panel sorter:
    - If width > height → treat as two-page spread.
      Process RIGHT page first, then LEFT page.
    - Otherwise → use normal sort_panels_reading_order.
    """

    # --- CASE 1: Single Page ---
    if img_height >= img_width:
        return sort_panels_reading_order(panels, rtl=rtl, col_overlap_ratio=col_overlap_ratio)

    # --- CASE 2: Two-Page Spread (Right page first) ---
    mid_x = img_width / 2

    right_panels = [p for p in panels if p["bbox"][0] >= mid_x * 0.9]   # mostly right half
    left_panels  = [p for p in panels if p["bbox"][2] <= mid_x * 1.1]   # mostly left half

    # safety fallback: anything ambiguous goes to nearest side
    for p in panels:
        if p not in right_panels and p not in left_panels:
            x_center = (p["bbox"][0] + p["bbox"][2]) / 2
            if x_center > mid_x:
                right_panels.append(p)
            else:
                left_panels.append(p)

    # --- Sort RIGHT page panels FIRST (because manga RTL) ---
    right_sorted = sort_panels_reading_order(right_panels, rtl=True, col_overlap_ratio=col_overlap_ratio)

    # --- Sort LEFT page panels SECOND ---
    left_sorted = sort_panels_reading_order(left_panels, rtl=True, col_overlap_ratio=col_overlap_ratio)

    # Final reading order: RIGHT → LEFT
    return right_sorted + left_sorted


def sort_bubbles_inside_panel(bubbles):
    """
    Sorts bubbles specifically within the context of a single panel.
    Standard Manga Rule: Top-Right to Bottom-Left.
    """
    if not bubbles:
        return []
        
    # We use a weighted score: Y is dominant, X is secondary.
    # Score = Y_coordinate - (X_coordinate / weight)
    # The weight determines how much "Rightness" overcomes "Downness".
    
    # However, a simpler strict row approach often works best for text:
    bubbles_with_meta = []
    for b in bubbles:
        x1, y1, x2, y2 = b["bbox"]
        bubbles_with_meta.append({
            "data": b,
            "cy": (y1 + y2) / 2,
            "cx": (x1 + x2) / 2,
            "h": y2 - y1
        })

    # Sort bubbles by Y first
    bubbles_with_meta.sort(key=lambda x: x["cy"])
    
    rows = []
    current_row = []
    
    if bubbles_with_meta:
        current_row = [bubbles_with_meta[0]]
        
        for b in bubbles_with_meta[1:]:
            last = current_row[-1]
            # If vertical centers are close, they are on the same line
            if abs(b["cy"] - last["cy"]) < (last["h"] * 0.5):
                current_row.append(b)
            else:
                # Sort the completed row RTL
                current_row.sort(key=lambda x: -x["cx"])
                rows.append(current_row)
                current_row = [b]
        
        # Sort and append final row
        current_row.sort(key=lambda x: -x["cx"])
        rows.append(current_row)
        
    final_bubbles = [b["data"] for row in rows for b in row]
    return final_bubbles

def box_overlap(a, b):
    """Compute intersection area between two boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    
    return (ix2 - ix1) * (iy2 - iy1)

def dedupe_by_coordinates(regions, iou_thresh=0.6):
    """
    Remove duplicates based strictly on overlapping coordinates (IoU).
    Prioritizes larger boxes.
    """
    # 1. Define Area and IoU helpers
    def get_area(b):
        x1, y1, x2, y2 = b["bbox"]
        return (x2 - x1) * (y2 - y1)

    def get_iou(b1, b2):
        # Coordinates of the intersection rectangle
        x1 = max(b1["bbox"][0], b2["bbox"][0])
        y1 = max(b1["bbox"][1], b2["bbox"][1])
        x2 = min(b1["bbox"][2], b2["bbox"][2])
        y2 = min(b1["bbox"][3], b2["bbox"][3])

        # If they don't overlap, area is 0
        if x2 < x1 or y2 < y1:
            return 0.0

        intersection_area = (x2 - x1) * (y2 - y1)
        
        area1 = get_area(b1)
        area2 = get_area(b2)
        union_area = area1 + area2 - intersection_area

        if union_area == 0: return 0.0
        return intersection_area / union_area

    # 2. Sort by Area (Descending) 
    # We keep the larger box when an overlap occurs.
    regions_sorted = sorted(regions, key=get_area, reverse=True)

    kept_regions = []

    for current in regions_sorted:
        is_duplicate = False
        
        for kept in kept_regions:
            # PURE COORDINATE CHECK
            # If they overlap significantly, current is a duplicate
            if get_iou(current, kept) > iou_thresh:
                is_duplicate = True
                break
        
        if not is_duplicate:
            kept_regions.append(current)

    return kept_regions


def dedupe_panels_by_containment(panels, iou_thresh=0.5, containment_thresh=0.75):
    """
    Applies NMS based on confidence, prioritizing IoU, but also checks for high
    containment (IoA) to eliminate smaller boxes fully contained within larger, 
    more confident ones.
    """
    if not panels:
        return []

    def get_area(p):
        x1, y1, x2, y2 = p["bbox"]
        return (x2 - x1) * (y2 - y1)

    # 1. Sort by CONFIDENCE (highest first) - The most confident box is the 'keeper'
    panels_sorted = sorted(panels, key=lambda p: p["confidence"], reverse=True)

    keep = []
    
    while panels_sorted:
        # Pick the most confident remaining box
        current = panels_sorted.pop(0)
        keep.append(current)
        
        remaining = []
        current_area = get_area(current)

        for other in panels_sorted:
            # Calculate IoU for general overlap check
            # (Requires an IoU helper function, same logic as before)
            # We'll use a simplified containment check for this example:

            # Get Intersection Area
            xA = max(current["bbox"][0], other["bbox"][0])
            yA = max(current["bbox"][1], other["bbox"][1])
            xB = min(current["bbox"][2], other["bbox"][2])
            yB = min(current["bbox"][3], other["bbox"][3])
            interArea = max(0, xB - xA) * max(0, yB - yA)

            # Get Containment Ratio (IoA): Intersection Area / Area of the smaller box ('other')
            other_area = get_area(other)
            
            # Use IoA to check if the smaller box ('other') is largely contained
            containment_ratio = interArea / other_area if other_area > 0 else 0

            # --- DEDUPLICATION LOGIC ---
            # If the smaller box ('other') is highly contained within the current (more confident) box, discard it.
            if containment_ratio < containment_thresh:
                remaining.append(other)
            # else: containment_ratio >= 0.75, so 'other' is a duplicate detection
            # contained within 'current', and we discard it.
        
        panels_sorted = remaining

    return keep
