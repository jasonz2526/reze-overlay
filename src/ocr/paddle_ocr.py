# src/ocr/paddle_ocr.py
import cv2
import numpy as np
from paddleocr import PaddleOCR

class OCRReader:
    def __init__(self, lang="japan"):

        # This loads BOTH detection + recognition models
        # "japan" enables Japanese vertical & horizontal models
        print("Loading PaddleOCR (Japanese)…")
        self.ocr = PaddleOCR(
            det_db_unclip_ratio=2.0,   # Helps curved manga bubbles
            det_db_box_thresh=0.4,     # Lower threshold → more text found
            use_angle_cls=True        # auto-rotate text
        )

    # -----------------------------------------------------
    # OPTIONAL: Upscale improves accuracy for manga text
    # -----------------------------------------------------
    def upscale(self, img, scale=1.8):
        h, w = img.shape[:2]
        return cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)

    # -----------------------------------------------------
    # OPTIONAL: Binarization reduces screentone noise
    # -----------------------------------------------------
    def denoise(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 5
        )
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

    # -----------------------------------------------------
    # Main OCR method
    # -----------------------------------------------------
    def read_text(self, bubble_crop):
        """
        Runs full detection + recognition inside a YOLO bubble crop.
        Returns list of:
        { "box": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "text": "...", "confidence": 0.93 }
        """

        # Step 1 — Improve input
        img = self.upscale(bubble_crop)
        img = self.denoise(img)

        # Step 2 — Full OCR
        ocr_result = self.ocr.predict(img)

        if not ocr_result or not ocr_result[0]:
            return []

        final = []

        for line in ocr_result[0]:
            poly, (text, conf) = line

            final.append({
                "box": poly,         # polygon of text line
                "text": text,
                "confidence": float(conf)
            })

        return final
