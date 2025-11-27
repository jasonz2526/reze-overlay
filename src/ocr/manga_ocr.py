from manga_ocr import MangaOcr
import cv2
from PIL import Image

class OCRReader:
    def __init__(self):
        print("Loading MangaOCR...")
        self.ocr = MangaOcr()

    def preprocess_crop(self, crop):
        """Optional preprocessing to improve OCR accuracy."""
        crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        return Image.fromarray(crop_rgb)

    def read_text(self, crop):
        """
        Takes a cropped bubble image and returns a list of OCR results.
        Returns:
            [{"box": [0,0,w,h], "text": text, "confidence": 1.0}]
        """
        pil_img = self.preprocess_crop(crop)
        try:
            text = self.ocr(pil_img)
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

        h, w = crop.shape[:2]
        return [{
            "box": [0, 0, w, h],
            "text": text
        }]
