# YOLOv8 training script
from ultralytics import YOLO

def train_model(data_yaml: str, model_name: str = "yolov8n.pt", epochs: int = 60, imgsz: int = 640):
    model = YOLO(model_name)
    model.train(data=data_yaml, epochs=epochs, imgsz=imgsz)
    return model

if __name__ == "__main__":
    train_model("../../data.yaml")
