# web.py
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
import asyncio

# Создаем WSGI-совместимое приложение Flask.
server = Flask(__name__)

# Получаем токен бота из переменной окружения.
TOKEN = os.getenv("BOT_TOKEN")

# Импортируем объект `app` из файла rusago.py.
from rusago import app as bot_app

@server.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    """
    Принимает запросы от Telegram и обрабатывает их.
    """
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

@server.route('/')
def index():
    return "Бот работает!"

if __name__ == '__main__':
    # Эта часть будет запускаться только при локальном запуске,
    # но не на Render. Render будет использовать Gunicorn.
    port = int(os.environ.get('PORT', 8000))
    asyncio.run(bot_app.initialize())
    asyncio.run(bot_app.start())
    # Запускаем Flask-сервер
    server.run(host="0.0.0.0", port=port)
