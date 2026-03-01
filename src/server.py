from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import base64
import cv2
import numpy as np
import uvicorn
import os
import asyncio

from src.new_pipeline import MangaPipeline
from src.translation.translate import MangaTranslator  # DeepL
from src.translation.gpt import GPTTranslator
from src.translation.utils import build_gpt_page_json
from src.translation.merge import merge_panels_and_translations

from dotenv import load_dotenv
load_dotenv()

REZE_OPENAI_API_KEY = os.getenv("REZE_OPENAI_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

# Load models once
pipeline = MangaPipeline(
    panel_model_path="models/best_109.pt",
    bubble_model_path="models/new_text_best.pt"
)

deepl = MangaTranslator(DEEPL_API_KEY)
gpt = GPTTranslator(model="gpt-5-mini", api_key=REZE_OPENAI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageRequest(BaseModel):
    screenshot: str  # Base64 string
    mode: Literal["simple", "deep"] = "simple"  


@app.post("/process-image")
def process_image(req: ImageRequest):
    try:
        # 1) Decode Base64 → OpenCV image
        header, encoded = req.screenshot.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # 2) Run panel → bubble → OCR detection pipeline
        page_result = pipeline.process_page(img)

        # 3) Convert to translation input format
        gpt_input_json = build_gpt_page_json(page_result["panels"])
        # 4) Choose translation engine based on mode
        if req.mode == "deep":
            print("[process-image] Using GPT deep translation")
            output = asyncio.run(gpt.translate_page(gpt_input_json))
        else:
            print("[process-image] Using DeepL simple translation")
            output = deepl.translate_panels_schema(gpt_input_json)

        print(output)
        # 5) Merge translations back into panels
        final_json = merge_panels_and_translations(page_result["panels"], output)

        return {"success": True, "result": final_json}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
