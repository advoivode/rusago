import os
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# === УСТАНОВИТЕ ВАШ ТОКЕН ===
# Получаем токен из переменной окружения. Это безопасный способ.
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Ошибка: Переменная окружения BOT_TOKEN не установлена.")
    exit(1)

# Замените на реальные Telegram ID администраторов
ADMIN_IDS = [5979123966, 939518066]
# Специалист, который будет вести чат с клиентами
SPECIALIST_ADMIN_ID = 5979123966

# === Этапы диалога для заявки ===
NAME, PHONE, MESSAGE, PHOTO = range(4)

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отменяет текущий разговор.
    """
    await update.message.reply_text("Заявка отменена. Можете начать заново с команды /start")
    return ConversationHandler.END

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет приветственное сообщение и кнопки "Отправить заявку" и "Написать специалисту".
    """
    # Создаем клавиатуру с кнопками
    keyboard = [[KeyboardButton("Оставить заявку")], [KeyboardButton("Написать специалисту")]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "Привет! Я готов принимать твои заявки. Ты можешь выбрать один из вариантов ниже 👇",
        reply_markup=markup
    )

# Обработчик для кнопки "Оставить заявку"
async def start_new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает сбор данных для новой заявки.
    """
    await update.message.reply_text("Как вас зовут?")
    return NAME

# Обработчик для кнопки "Написать специалисту"
async def handle_specialist_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Перенаправляет пользователя в чат со специалистом.
    """
    chat_info = await context.bot.get_chat(SPECIALIST_ADMIN_ID)
    specialist_username = chat_info.username
    if specialist_username:
        await update.message.reply_text(
            "Вы будете перенаправлены в чат со специалистом. Пожалуйста, напишите ему напрямую.",
        )
        await update.message.reply_text(
            f"Чат со специалистом: t.me/{specialist_username}"
        )
    else:
        await update.message.reply_text(
            "К сожалению, у специалиста нет публичного имени пользователя Telegram. Пожалуйста, отправьте заявку, чтобы он мог с вами связаться."
        )
    return ConversationHandler.END

# Пошаговый сбор данных для заявки
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет имя пользователя и просит ввести телефон.
    """
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Укажите номер телефона:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет номер телефона и просит ввести комментарий.
    """
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Введите ваш комментарий (или напишите 'Пропустить'):")
    return MESSAGE

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет комментарий и просит отправить фото.
    """
    context.user_data["message"] = update.message.text
    await update.message.reply_text("Отправьте фото документов (или напишите 'Пропустить'):")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает фото, собирает все данные и отправляет админам.
    """
    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        await update.message.reply_text("Спасибо! Ваша заявка отправлена ✅")
    elif update.message.text and update.message.text.lower() == 'пропустить':
        await update.message.reply_text("Спасибо! Ваша заявка отправлена ✅")
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото или напишите 'Пропустить'.")
        return PHOTO

    context.user_data["photo"] = photo_file_id
    
    # Получаем никнейм пользователя, если он существует
    user_username = update.message.from_user.username

    # Формируем и отправляем уведомление админам
    text = (
        f"📩 Новая заявка:\n"
        f"👤 Имя: {context.user_data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {context.user_data.get('phone', 'Не указан')}\n"
        f"💬 Комментарий: {context.user_data.get('message', 'Не указан')}\n"
        f"🔗 Никнейм Telegram: {f'@{user_username}' if user_username else 'Не указан'}"
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id, text=text)
        if photo_file_id:
            await context.bot.send_photo(chat_id=admin_id, photo=photo_file_id)

    # Завершаем диалог и возвращаемся к началу
    await start(update, context)
    return ConversationHandler.END

# Пропуск фото
async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await get_photo(update, context)

# --- Настройка приложения ---
# Создаем объект ApplicationBuilder
app = ApplicationBuilder().token(TOKEN).build()

# Добавляем обработчики команд и кнопок на верхнем уровне
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^Написать специалисту$"), handle_specialist_redirect))

# Создаем и добавляем ConversationHandler для сбора заявки
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Оставить заявку$"), start_new_request)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)],
        PHOTO: [
            MessageHandler(filters.PHOTO, get_photo),
            MessageHandler(filters.TEXT & filters.Regex("(?i)пропустить"), skip_photo)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
app.add_handler(conv_handler)


# --- Запуск бота ---
if __name__ == '__main__':
    print("Бот запущен...")
    app.run_polling()
