# src/cleaning/bubble_cleaner.py

import cv2
import numpy as np

def clean_bubble_region(image, bbox):
    x1, y1, x2, y2 = map(int, bbox)
    crop = image[y1:y2, x1:x2].copy()

    # grayscale
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # threshold to detect text
    _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # dilate to cover strokes
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # inpaint
    cleaned = cv2.inpaint(crop, mask, 3, cv2.INPAINT_TELEA)

    return cleaned, mask
