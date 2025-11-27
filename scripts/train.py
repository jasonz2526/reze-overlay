from ultralytics import YOLO

model = YOLO("yolov8s.pt")

# Train the model
model.train(
    data="../data/bubbles-v3/data.yaml",
    epochs=30,
    imgsz=1024,
    batch=8,
    device="cpu",
    project="bubbles-training_v3",
    name="yolo_model_v3",
    mixup=0.0
)