import os
import shutil
import tempfile
from unittest import result

from fastapi import FastAPI, File, UploadFile, HTTPException
from app.orchestrator.pipeline import run_pipeline


app = FastAPI(
    title="Spec Layer API",
    description="Visual equipment intelligence and maintenance API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Spec Layer API is running"
    }


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    # Only accept images
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image."
        )

    suffix = os.path.splitext(file.filename or "")[1] or ".jpg"
    temp_path = None

    try:
        # Save the uploaded image temporarily.
        # Qwen expects an image file path.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        result = run_pipeline(temp_path)

        # Return only the information the frontend actually needs.
        # Do not expose raw manual text or device-specific label identifiers.
        clean_sources = []

        for index, source in enumerate(result.get("search_results", []), start=1):
            clean_sources.append({
            "source_id": index,
            "title": source.get("title"),
            "url": source.get("url"),
            "score": source.get("score")
        })

        device = result.get("device", {})

        return {
            "device": {
                "device_type": device.get("device_type"),
                "manufacturer": device.get("manufacturer"),
                "model": device.get("model"),
                "uncertainties": device.get("uncertainties", [])
            },
            "sources": clean_sources,
            "analysis": result.get("analysis", {})
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        file.file.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)