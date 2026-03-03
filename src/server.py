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
import time

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
gpt = GPTTranslator(model="gpt-4.1-mini", api_key=REZE_OPENAI_API_KEY)

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
        started_total = time.perf_counter()
        # 1) Decode Base64 → OpenCV image
        decode_started = time.perf_counter()
        header, encoded = req.screenshot.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        decode_ms = int((time.perf_counter() - decode_started) * 1000)

        # 2) Run panel → bubble → OCR detection pipeline
        page_result = pipeline.process_page(img)
        pipeline_timings = page_result.get("timings", {})

        # 3) Convert to translation input format
        prompt_build_started = time.perf_counter()
        gpt_input_json = build_gpt_page_json(page_result["panels"])
        prompt_build_ms = int((time.perf_counter() - prompt_build_started) * 1000)
        # 4) Choose translation engine based on mode
        translation_started = time.perf_counter()
        translation_metrics = {"mode": req.mode}
        if req.mode == "deep":
            print("[process-image] Using GPT deep translation")
            output = asyncio.run(gpt.translate_page(gpt_input_json))
            translation_metrics.update(gpt.last_metrics)
        else:
            print("[process-image] Using DeepL simple translation")
            output = deepl.translate_panels_schema(gpt_input_json)
            translation_metrics["latency_ms"] = int((time.perf_counter() - translation_started) * 1000)

        total_latency_ms = int((time.perf_counter() - started_total) * 1000)
        stage_metrics = {
            "base64_decode_ms": decode_ms,
            "panel_detect_ms": pipeline_timings.get("panel_detect_ms"),
            "bubble_detect_ms": pipeline_timings.get("bubble_detect_ms"),
            "ocr_total_ms": pipeline_timings.get("ocr_total_ms"),
            "ocr_per_crop_ms": pipeline_timings.get("ocr_per_crop_ms", []),
            "ocr_skipped_count": pipeline_timings.get("ocr_skipped_count", 0),
            "ocr_processed_count": pipeline_timings.get("ocr_processed_count", 0),
            "prompt_build_ms": prompt_build_ms,
            "llm_call_ms": translation_metrics.get("latency_ms"),
            "pipeline_total_ms": pipeline_timings.get("total_pipeline_ms"),
        }
        print(
            f"[process-image] stages={stage_metrics} "
            f"translation={translation_metrics} total_ms={total_latency_ms}"
        )

        # 5) Merge translations back into panels
        final_json = merge_panels_and_translations(page_result["panels"], output)

        return {
            "success": True,
            "result": final_json,
            "metrics": {
                "stages": stage_metrics,
                "translation": translation_metrics,
                "total_ms": total_latency_ms,
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
