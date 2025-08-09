# web.py
import os
from rusago import app

# Получаем порт из переменной окружения Render.
PORT = int(os.environ.get('PORT', 8000))

# Эта функция запускает приложение в режиме вебхука
# Render будет использовать эту функцию как точку входа.
if __name__ == '__main__':
    # Вставьте ваш URL-адрес из Render
    # Например: https://your-app-name.onrender.com
    WEBHOOK_URL = "https://rusago-bot.onrender.com/" + os.getenv("BOT_TOKEN")
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=os.getenv("BOT_TOKEN"),
        webhook_url=WEBHOOK_URL
    )
