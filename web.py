# web.py
import os
import logging
from flask import Flask, request, jsonify
from rusago import app as bot_app
from telegram import Update

# Создаем WSGI-совместимое приложение Flask.
# Gunicorn будет использовать этот объект 'server'.
server = Flask(__name__)

# Получаем порт из переменной окружения Render.
PORT = int(os.environ.get('PORT', 8000))
TOKEN = os.getenv("BOT_TOKEN")

@server.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    """
    Принимает запросы от Telegram и обрабатывает их.
    """
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        await bot_app.process_update(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Ошибка при обработке вебхука: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@server.route('/')
def index():
    return "Бот работает!"

if __name__ == '__main__':
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://your-render-app.onrender.com/{TOKEN}" # Замените на URL вашего сервиса Render
    )
