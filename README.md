# GeminiITM — Генерация изображений + CryptoBot

## Быстрый старт

1. Клонируй проект или скопируй папку.
2. Установи зависимости:
   pip install -r requirements.txt

3. Создай .env рядом:
   OPENAI_API_KEY=sk-...
   CRYPTOPAY_API_KEY=...

4. Запусти backend:
   python launch.py

5. Перейди в браузере:
   http://127.0.0.1:8000

## Endpoints (API)
- POST /api/generate-image
- GET /api/gallery
- GET /api/gallery-img/{filename}
- GET /api/pay?user_id=xxx
- POST /api/cryptobot

## Галерея — всё хранится в папке gallery/
