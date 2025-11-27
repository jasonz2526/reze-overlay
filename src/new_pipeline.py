import cv2
from ultralytics import YOLO
from src.ocr.manga_ocr import OCRReader
import os

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

# NOTE: Your panel entries must include "confidence" for this to work correctly!

class MangaPipeline:
    def __init__(self, panel_model_path, bubble_model_path):
        print("Loading panel model…")
        self.panel_detector = YOLO(panel_model_path)

        print("Loading bubble/text model…")
        self.bubble_detector = YOLO(bubble_model_path)

        print("Initializing OCR…")
        self.ocr = OCRReader()


    def process_page(self, image_path):
        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        # --- DETECT PANELS ---
        panel_results = self.panel_detector(img)[0]
        panels = []

        for b in panel_results.boxes:
            cls = int(b.cls[0])      # ← class ID from model
            if cls != 0:
                continue              # ← ONLY keep class 0 panels

            x1, y1, x2, y2 = b.xyxy[0].tolist()
            conf = float(b.conf[0])

            panels.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "bubbles": [],
                "outside_text": []
            })

        panels = dedupe_panels_by_containment(panels, containment_thresh=0.75)
        # Sort panels top-to-bottom, then left-to-right
        panels = sort_panels_reading_order(panels, rtl=True)

        # --- DETECT BUBBLES + OUTSIDE TEXT ---
        bubble_results = self.bubble_detector(img)[0]
        boxes = bubble_results.boxes

        filtered_boxes = []
        max_area = 0.04 * w * h  # 4% of page area

        for b in boxes:
            x1, y1, x2, y2 = b.xyxy[0]
            area = (x2 - x1) * (y2 - y1)
            if area < max_area:
                filtered_boxes.append(b)

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

        # --- ASSIGN EACH BUBBLE/TEXT TO THE BEST PANEL ---
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

            # === PRIMARY CASE: normal panel overlap ===
            if best_ratio > 0.3 and best_panel:
                target_panel = best_panel

            # === FALLBACK: assign to nearest panel ===
            else:
                target_panel = closest_panel

            # === (IMPORTANT) append while still inside loop! ===
            if entry["label"] == "bubble":
                target_panel["bubbles"].append(entry)
            else:
                target_panel["outside_text"].append(entry)
        
        for panel in panels:
            # 1. MERGE lists to check for overlaps across categories
            # We assume your entries have a "label" key ("bubble" or "outside")
            combined_regions = panel["bubbles"] + panel["outside_text"]

            # 2. DEDUPE based on coordinates only
            # iou_thresh=0.6 is a good sweet spot. 
            # If > 60% of the box overlaps a larger one, it's gone.
            unique_regions = dedupe_by_coordinates(combined_regions, iou_thresh=0.6)

            # 3. SORT the clean list by reading order
            # (It is more efficient to sort once before splitting)
            sorted_unique_regions = sort_bubbles_inside_panel(unique_regions)

            # 4. SPLIT back into specific lists (if you still need them separate)
            panel["bubbles"] = [
                r for r in sorted_unique_regions if r["label"] == "bubble"
            ]
            panel["outside_text"] = [
                r for r in sorted_unique_regions if r["label"] != "bubble" # e.g. "outside"
            ]

        # Return result
        return {
            "panels": panels
        }


    def visualize_result(self, result, image_path, save_path="/Users/jasonzhao/reze-overlay/images"):
        """Draw panels, bubbles, and outside text boxes on an image."""
        img = cv2.imread(image_path)

        panels = result["panels"]

        # Colors (BGR)
        PANEL_COLOR = (255, 128, 0)   # Orange/Blue-ish
        BUBBLE_COLOR = (0, 255, 0)    # Green
        OUTSIDE_COLOR = (0, 0, 255)   # Red

        # Draw panels
        for p_idx, panel in enumerate(panels, start=1):
            x1, y1, x2, y2 = map(int, panel["bbox"])

            # Panel rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), PANEL_COLOR, 2)

            # Panel label
            cv2.putText(img, f"P{p_idx}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, PANEL_COLOR, 2)

            # Draw bubbles inside panel
            for b_idx, bubble in enumerate(panel["bubbles"], start=1):
                bx1, by1, bx2, by2 = map(int, bubble["bbox"])

                cv2.rectangle(img, (bx1, by1), (bx2, by2), BUBBLE_COLOR, 2)
                cv2.putText(img, f"P{p_idx}-B{b_idx}", (bx1, by1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, BUBBLE_COLOR, 2)

            # Draw outside-text inside panel
            for t_idx, region in enumerate(panel["outside_text"], start=1):
                tx1, ty1, tx2, ty2 = map(int, region["bbox"])

                cv2.rectangle(img, (tx1, ty1), (tx2, ty2), OUTSIDE_COLOR, 2)
                cv2.putText(img, f"P{p_idx}-O{t_idx}", (tx1, ty1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, OUTSIDE_COLOR, 2)

        # Save
        if save_path is None:
            save_path = image_path.replace(".jpg", "_debug.jpg")
        else:
            # Ensure save_path is a directory
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            debug_filename = f"{name}_debug_panel{ext}"
            save_path = os.path.join(save_path, debug_filename)  # "/images/001_debug.jpg"

        cv2.imwrite(save_path, img)
        print(f"[✓] Visualization saved to {save_path}")
        

        return save_path
    
def get_centroid(bbox):
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

def is_point_in_box(point, box):
    px, py = point
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2

def sort_panels_reading_order(panels, rtl=True, col_overlap_ratio=0.6):
    """
    Sorts panels using a hybrid approach:
    1. Groups panels into vertical columns based on horizontal overlap.
    2. Sorts the columns RTL/LTR based on the top-most panel's position.
    3. Sorts panels within the column TTB.
    """
    if not panels:
        return []

    # 1. Add metadata
    panel_items = []
    for p in panels:
        x1, y1, x2, y2 = p["bbox"]
        panel_items.append({
            "data": p,
            "x_min": x1,
            "x_max": x2,
            "y_min": y1,
            "width": x2 - x1
        })
    
    # --- Helper Functions ---
    def panels_in_same_column(p1, p2):
        """Check if two panels are vertically stacked in the same column"""
        overlap_start = max(p1["x_min"], p2["x_min"])
        overlap_end = min(p1["x_max"], p2["x_max"])
        overlap = max(0, overlap_end - overlap_start)
        
        # Must have significant horizontal overlap
        min_width = min(p1["width"], p2["width"])
        return overlap > min_width * col_overlap_ratio

    def get_column_group(start_panel, remaining):
        """Find all panels in the same vertical column as start_panel"""
        column = [start_panel]
        changed = True
        
        while changed:
            changed = False
            for panel in remaining[:]:
                # Check for shared column membership
                if any(panels_in_same_column(panel, col_panel) for col_panel in column):
                    column.append(panel)
                    remaining.remove(panel)
                    changed = True
        
        # Crucial: Sort panels within the column TTB
        return sorted(column, key=lambda x: x["y_min"]) 
    
    # 2. Group panels into columns
    remaining = panel_items.copy()
    groups = []
    
    while remaining:
        # Start with the topmost and rightmost panel still remaining (RTL start)
        remaining.sort(key=lambda x: (x["y_min"], -x["x_min"] if rtl else x["x_min"]))
        start = remaining.pop(0)
        column = get_column_group(start, remaining)
        groups.append(column)
    
    # 3. Sort column groups by reading direction
    def group_sort_key(group):
        """
        Sort key for groups based on the TOPMOST panel's position.
        This forces column sorting first.
        """
        top_panel = min(group, key=lambda x: x["y_min"])
        
        if rtl:
            # Sort by X (Right-to-Left) primarily, then Y (Top-to-Bottom)
            return (-top_panel["x_min"], top_panel["y_min"])
        else:
            return (top_panel["x_min"], top_panel["y_min"])
    
    groups.sort(key=group_sort_key)
    
    # 4. Flatten groups into final panel order
    sorted_panels = []
    for group in groups:
        # Group panels are already sorted TTB from Step 2
        sorted_panels.extend([p["data"] for p in group])
    
    return sorted_panels

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
