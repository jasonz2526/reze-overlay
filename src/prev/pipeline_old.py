import cv2
from ultralytics import YOLO
from src.ocr.paddle_ocr import OCRReader
import os

class MangaPipeline:
    def __init__(self, yolo_model_path):
        print("Loading YOLO model…")
        self.detector = YOLO(yolo_model_path)

        print("Loading PaddleOCR…")
        self.ocr = OCRReader()

    def process_page(self, image_path):
        img = cv2.imread(image_path)

        yolov8_results = self.detector(img)[0]
        detections = yolov8_results.boxes.data.tolist()

        bubble_regions = []
        general_text_regions = []

        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            cls = int(cls)

            crop = img[int(y1):int(y2), int(x1):int(x2)]

            ocr_output = self.ocr.read_text(crop)

            region_dict = {
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "class": cls,
                "ocr": ocr_output
            }

            if cls == 0:  # bubble class
                bubble_regions.append(region_dict)
            else:         # text outside bubbles
                general_text_regions.append(region_dict)

        return {
            "bubbles": bubble_regions,
            "outside_text": general_text_regions
        }

    def visualize_result(self, result, image_path):
        img = cv2.imread(image_path)

        for region in result["bubbles"]:
            x1, y1, x2, y2 = map(int, region["bbox"])
            cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), 2)

        for region in result["outside_text"]:
            x1, y1, x2, y2 = map(int, region["bbox"])
            cv2.rectangle(img, (x1,y1), (x2,y2), (255,0,0), 2)

        out_path = f"{image_path}_output.jpg"
        cv2.imwrite(out_path, img)
        return out_path
