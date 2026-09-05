import os
import time
import torch
from diffusers import AutoPipelineForText2Image

MODEL_ID = os.getenv("MODEL_ID", "stabilityai/sd-turbo")
print(f"Pre-downloading {MODEL_ID} to local cache...")
start_t = time.time()

pipe = AutoPipelineForText2Image.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
)
print(f"Successfully downloaded and cached {MODEL_ID} in {time.time() - start_t:.2f}s.")
