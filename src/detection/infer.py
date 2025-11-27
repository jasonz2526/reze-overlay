from ultralytics import YOLO
import cv2

def detect_bubbles(image_path: str, model_path: str):
    model = YOLO(model_path)
    results = model(image_path)
    return results

if __name__ == "__main__":
    img_path = "../../data/manga-bubbles/images/val/sample.png"
    model_path = "../../models/best.pt"
    res = detect_bubbles(img_path, model_path)
    print(res)