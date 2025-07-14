# main.py (FastAPI backend for OpenAI DALL·E)
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import openai
import uuid
import base64

# === Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
GALLERY_DIR = Path("gallery")
GALLERY_DIR.mkdir(exist_ok=True)

app = FastAPI()

# CORS для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 1. Генерация изображения ===
@app.post("/generate-image", response_class=HTMLResponse)
async def generate_image(prompt: str = Form(...)):
    try:
        # Запрос к DALL·E (v3)
        response = openai.images.generate(
            model="dall-e-3",  # можно "dall-e-2" если ключ без доступа к третьей версии
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format="b64_json"
        )
        img_b64 = response.data[0].b64_json
        img_bytes = base64.b64decode(img_b64)
        img_id = str(uuid.uuid4())
        img_path = GALLERY_DIR / f"{img_id}.png"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        img_url = f"/gallery-img/{img_id}.png"
        return f'<img src="{img_url}" alt="AI" style="max-width:300px;border-radius:14px;"><br><span style="color:#6c3;">Готово!</span>'
    except Exception as e:
        return f"<span style='color:#a63;'>Ошибка: {e}</span>"

# === 2. Галерея изображений ===
@app.get("/gallery", response_class=HTMLResponse)
async def gallery():
    imgs = sorted(GALLERY_DIR.glob("*.png"), reverse=True)
    html = "".join([f'<img src="/gallery-img/{img.name}" alt="AI">' for img in imgs[:10]])
    return html

# === 3. Статика: отдаём изображения ===
@app.get("/gallery-img/{filename}")
async def gallery_img(filename: str):
    img_path = GALLERY_DIR / filename
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return HTMLResponse("Not found", status_code=404)
