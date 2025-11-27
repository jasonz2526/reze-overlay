import cv2
from ultralytics import YOLO
from src.ocr.manga_ocr import OCRReader

class MangaPipeline:
    def __init__(self, yolo_model_path):
        print("Loading YOLO model…")
        self.detector = YOLO(yolo_model_path)
        print("Initializing OCR...")
        self.ocr = OCRReader()
    
    def process_page_full_ocr(self, image_path):
        img = cv2.imread(image_path)
        ocr_output = self.ocr.read_text(img)

        return {
            "full_page_text": ocr_output
        }

    def process_page(self, image_path):
        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        # Run YOLO
        yolov8_results = self.detector(img)[0]

        # Extract YOLO Boxes
        boxes = yolov8_results.boxes

        # ---- APPLY FILTERING HERE ----
        filtered_boxes = []
        max_area = 0.04 * w * h  # 4% of page area

        for b in boxes:
            x1, y1, x2, y2 = b.xyxy[0]
            area = (x2 - x1) * (y2 - y1)
            if area < max_area:
                filtered_boxes.append(b)
        # ------------------------------

        bubble_regions = []
        general_text_regions = []

        # OCR on FILTERED boxes
        for b in boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            conf = float(b.conf[0])
            cls = int(b.cls[0])

            crop = img[int(y1):int(y2), int(x1):int(x2)]
            ocr_output = self.ocr.read_text(crop)

            region_dict = {
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "class": cls,
                "ocr": ocr_output
            }

            if cls == 0:   # <-- bubble class based on your correction
                bubble_regions.append(region_dict)
            else:          # class 1 = outside text
                general_text_regions.append(region_dict)

        # Sort bubbles (RTL)
        bubble_regions.sort(
            key=lambda b: (
                -(b["bbox"][0] + b["bbox"][2]) / 2,
                (b["bbox"][1] + b["bbox"][3]) / 2
            )
        )

        return {
            "bubbles": bubble_regions,
            "outside_text": general_text_regions
        }

    def visualize_result(self, result, image_path, save_path=None):
        img = cv2.imread(image_path)
        for region in result["bubbles"]:
            x1, y1, x2, y2 = map(int, region["bbox"])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        for region in result["outside_text"]:
            x1, y1, x2, y2 = map(int, region["bbox"])
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)

        if save_path is None:
            save_path = f"{image_path}_output2.jpg"
        cv2.imwrite(save_path, img)
        return save_path
