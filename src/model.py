import os
import io
import time
import base64
import logging
import asyncio
from typing import Optional, Tuple
from PIL import Image

from src.config import settings

logger = logging.getLogger("sd_model")

class SDTurboManager:
    def __init__(self):
        self.pipe = None
        self.is_loaded = False
        self.lock = asyncio.Lock()

    def load_model(self):
        if settings.MOCK_MODEL:
            logger.info("MOCK_MODEL=true: Skipping actual model load.")
            self.is_loaded = True
            return

        logger.info(f"Loading SD-Turbo model ({settings.MODEL_ID}) on CPU...")
        start_t = time.time()
        import torch
        from diffusers import AutoPipelineForText2Image

        try:
            torch.set_num_threads(int(os.getenv("THREADS", "2")))
        except Exception:
            pass

        self.pipe = AutoPipelineForText2Image.from_pretrained(
            settings.MODEL_ID,
            torch_dtype=torch.float32,
        )
        self.pipe.to("cpu")

        if hasattr(self.pipe, "safety_checker") and self.pipe.safety_checker is not None:
            self.pipe.safety_checker = None

        self.is_loaded = True
        logger.info(f"SD-Turbo model loaded successfully in {time.time() - start_t:.2f}s.")

    def generate_image(
        self,
        prompt: str,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Tuple[str, float]:
        start_t = time.time()
        steps = steps or settings.DEFAULT_STEPS
        guidance_scale = guidance_scale if guidance_scale is not None else settings.DEFAULT_GUIDANCE_SCALE
        width = width or settings.DEFAULT_WIDTH
        height = height or settings.DEFAULT_HEIGHT

        if settings.MOCK_MODEL or self.pipe is None:
            img = Image.new("RGB", (width, height), color=(40, 40, 45))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            latency_ms = (time.time() - start_t) * 1000
            return b64_str, latency_ms

        result = self.pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
        )
        image = result.images[0]

        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        latency_ms = (time.time() - start_t) * 1000
        return b64_str, latency_ms

model_manager = SDTurboManager()
