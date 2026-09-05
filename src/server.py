import time
import logging
import asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.auth import verify_api_key, AuthenticationError
from src.model import model_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sd_server")
SERVER_START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up SD-Turbo inference server ({settings.MODEL_NAME})...")
    try:
        model_manager.load_model()
    except Exception as e:
        logger.error(f"Error loading model: {e}")
    yield
    logger.info("Shutting down SD-Turbo server...")

app = FastAPI(
    title="AS Cloud SD-Turbo Inference Node",
    description="Fast 1-step diffusion image generation powered by SD-Turbo on CPU",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt to generate image")
    n: Optional[int] = Field(default=1, ge=1, le=1)
    size: Optional[str] = Field(default="512x512", description="Image resolution (e.g. 512x512)")
    response_format: Optional[str] = Field(default="b64_json", description="'b64_json' or 'url'")

@app.get("/")
async def root():
    return {
        "name": f"AS Cloud - {settings.MODEL_NAME}",
        "status": "online",
        "model": settings.MODEL_NAME,
        "model_loaded": model_manager.is_loaded,
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "sd-turbo",
        "loaded": model_manager.is_loaded,
    }

@app.get("/v1/models")
async def list_models(dependencies: None = Depends(verify_api_key)):
    return {
        "object": "list",
        "data": [
            {
                "id": "sd-turbo",
                "object": "model",
                "created": int(SERVER_START_TIME),
                "owned_by": "stabilityai",
            }
        ],
    }

@app.post("/v1/images/generations")
async def generate_images(
    req: ImageGenerationRequest,
    dependencies: None = Depends(verify_api_key),
):
    if not model_manager.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"message": "SD-Turbo model is not yet loaded.", "type": "model_not_ready"}},
        )

    width = 512
    height = 512
    if "x" in (req.size or ""):
        try:
            parts = req.size.split("x")
            width = min(max(int(parts[0]), 256), 768)
            height = min(max(int(parts[1]), 256), 768)
        except Exception:
            width, height = 512, 512

    logger.info(f"Generating image for prompt: '{req.prompt}' (size: {width}x{height})")

    async with model_manager.lock:
        b64_str, latency_ms = await asyncio.to_thread(
            model_manager.generate_image,
            prompt=req.prompt,
            width=width,
            height=height,
        )

    logger.info(f"Generated image in {latency_ms:.1f}ms")

    item = {}
    if req.response_format == "url":
        item["url"] = f"data:image/png;base64,{b64_str}"
    else:
        item["b64_json"] = b64_str

    return {
        "created": int(time.time()),
        "data": [item],
        "latency_ms": round(latency_ms, 1),
    }
