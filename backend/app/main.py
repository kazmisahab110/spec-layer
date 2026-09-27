import json
import os
import shutil
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException
from app.orchestrator.pipeline import run_pipeline
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Spec Layer API",
    description="Visual product and equipment intelligence API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://spec-layer.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Spec Layer API is running",
    }


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image.",
        )

    suffix = os.path.splitext(file.filename or "")[1] or ".jpg"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        result = run_pipeline(temp_path)

        clean_sources = []
        for index, source in enumerate(result.get("search_results", []), start=1):
            clean_sources.append({
                "source_id": index,
                "title": source.get("title"),
                "url": source.get("url"),
                "score": source.get("score"),
            })

        device = result.get("device", {})

        return {
            "device": {
                "device_type": device.get("device_type"),
                "manufacturer": device.get("manufacturer"),
                "model": device.get("model"),
                "uncertainties": device.get("uncertainties", []),
            },
            "sources": clean_sources,
            "analysis": result.get("analysis", {}),
        }

    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=502,
            detail=f"An AI stage returned invalid JSON: {error}",
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
    finally:
        file.file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
