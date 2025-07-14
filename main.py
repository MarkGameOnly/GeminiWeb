import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uuid, base64, sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta
import openai
import httpx

# === .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CRYPTOPAY_API_KEY = os.getenv("CRYPTOPAY_API_KEY")

# === Глобальные переменные ===
GALLERY_DIR = Path("gallery")
GALLERY_DIR.mkdir(exist_ok=True)
FREE_LIMIT = 5  # Бесплатных генераций

openai.api_key = OPENAI_API_KEY
openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

# === DB (SQLite) ===
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    is_subscribed INTEGER DEFAULT 0,
    subscription_expires TEXT,
    usage_count INTEGER DEFAULT 0
)
""")
conn.commit()

# === FastAPI ===
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ==== Вспомогательные функции ====
def is_subscribed(user_id: str) -> bool:
    cursor.execute("SELECT is_subscribed, subscription_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row: return False
    sub, exp = row
    if sub and exp:
        return datetime.strptime(exp, "%Y-%m-%d") >= datetime.now()
    return False

def increment_usage(user_id: str):
    cursor.execute("UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_usage(user_id: str):
    cursor.execute("SELECT usage_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def ensure_user(user_id: str):
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, usage_count) VALUES (?, ?)", (user_id, 0))
        conn.commit()

# ==== CryptoBot invoice ====
async def create_invoice(user_id, amount=1):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOPAY_API_KEY}
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": "Подписка Gemini AI",
        "payload": str(user_id),
        "allow_comments": False,
        "allow_anonymous": False
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json()
        if "result" in data and "pay_url" in data["result"]:
            return data["result"]["pay_url"]
        return None

# ==== Эндпоинты ====

@app.post("/generate-image", response_class=HTMLResponse)
async def generate_image(prompt: str = Form(...), user_id: str = Form(...)):
    ensure_user(user_id)
    if not is_subscribed(user_id) and get_usage(user_id) >= FREE_LIMIT:
        return HTMLResponse(f"""<b>🔐 Лимит бесплатных генераций исчерпан.<br>
        <a href="/pay?user_id={user_id}" target="_blank">Купить подписку</a></b>""")
    try:
        response = await openai_client.images.generate(
            model="dall-e-3", prompt=prompt, n=1,
            size="1024x1024", response_format="b64_json"
        )
        img_b64 = response.data[0].b64_json
        img_bytes = base64.b64decode(img_b64)
        img_id = str(uuid.uuid4())
        img_path = GALLERY_DIR / f"{img_id}.png"
        with open(img_path, "wb") as f: f.write(img_bytes)
        increment_usage(user_id)
        img_url = f"/gallery-img/{img_id}.png"
        return f'<img src="{img_url}" alt="AI" style="max-width:300px;border-radius:14px;"><br><span style="color:#6c3;">Готово!</span>'
    except Exception as e:
        print("Ошибка генерации:", e)
        return f"<span style='color:#a63;'>Ошибка: {e}</span>"

@app.get("/gallery", response_class=HTMLResponse)
async def gallery():
    imgs = sorted(GALLERY_DIR.glob("*.png"), reverse=True)
    html = "".join([f'<img src="/gallery-img/{img.name}" alt="AI">' for img in imgs[:10]])
    return html

@app.get("/gallery-img/{filename}")
async def gallery_img(filename: str):
    img_path = GALLERY_DIR / filename
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return HTMLResponse("Not found", status_code=404)

@app.get("/pay")
async def pay(user_id: str):
    pay_url = await create_invoice(user_id)
    if not pay_url:
        return HTMLResponse("❌ Не удалось создать ссылку на оплату. Попробуйте позже.", status_code=500)
    return RedirectResponse(pay_url)

@app.post("/cryptobot")
async def cryptobot_webhook(request: Request):
    data = await request.json()
    print("Webhook от CryptoBot:", data)
    if data.get("status") == "paid":
        user_id = str(data.get("payload"))
        expires = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cursor.execute(
            "UPDATE users SET is_subscribed=1, subscription_expires=? WHERE user_id=?",
            (expires, user_id)
        )
        conn.commit()
        print(f"✅ Активирована подписка для пользователя {user_id}")
    return {"ok": True}

@app.get("/")
async def index():
    return HTMLResponse("""
    <h1>Gemini AI Generator + CryptoBot Test</h1>
    <ul>
        <li>POST /generate-image (prompt, user_id)</li>
        <li>GET /gallery</li>
        <li>GET /gallery-img/{filename}</li>
        <li>GET /pay?user_id=123</li>
        <li>POST /cryptobot (webhook для оплаты)</li>
    </ul>
    """)
