# src/cleaning/outside_cleaner.py
import cv2
import numpy as np
from lama_cleaner.model_manager import ModelManager

# Load LaMa model once
lama = ModelManager(name="lama", device="cuda" if cv2.cuda.getCudaEnabledDeviceCount() > 0 else "cpu")

def clean_outside_text(image, bboxes):
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    # Combine all boxes into a single mask
    for (x1, y1, x2, y2) in bboxes:
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        mask[y1:y2, x1:x2] = 255

    # Lama expects RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Run LaMa
    cleaned_rgb = lama(image_rgb, mask)

    # Convert back to BGR for OpenCV pipeline
    cleaned_bgr = cv2.cvtColor(cleaned_rgb, cv2.COLOR_RGB2BGR)

    return cleaned_bgr
