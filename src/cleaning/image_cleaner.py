# src/cleaning/image_cleaner.py

import cv2
from cleaning.bubble_cleaner import clean_bubble_region
from cleaning.outside_cleaner import clean_outside_text

class ImageCleaner:
    def __init__(self):
        pass

    def clean_page(self, image_path, panels):
        """
        panels = [
          {
            "panel_id": 1,
            "bubbles": [{bbox: [...], ...}],
            "outside_text": [{bbox: [...], ...}]
          }
        ]
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Unable to read image {image_path}")

        # STEP 1 - Clean bubble text (simple white bubble inpainting)
        for panel in panels:
            for bubble in panel["bubbles"]:
                bbox = bubble["bbox"]
                cleaned_crop, mask = clean_bubble_region(image, bbox)

                x1, y1, x2, y2 = map(int, bbox)
                image[y1:y2, x1:x2] = cleaned_crop

        # STEP 2 - Clean outside text (LaMa deep inpainting)
        all_outside_bboxes = []
        for panel in panels:
            for region in panel["outside_text"]:
                all_outside_bboxes.append(region["bbox"])

        if len(all_outside_bboxes) > 0:
            image = clean_outside_text(image, all_outside_bboxes)

        return image

    def save_cleaned_page(self, image, output_path):
        cv2.imwrite(output_path, image)
        return output_path
