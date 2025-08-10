import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("Ошибка: переменная окружения BOT_TOKEN не установлена")
    exit(1)

ADMIN_IDS = [5979123966, 939518066]
SPECIALIST_ADMIN_ID = 939518066

# Этапы диалога
NAME, PHONE, COMMENT, PHOTO = range(4)
MIN_PHOTOS = 4

# === ОБРАБОТЧИКИ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет главное меню с кнопками."""
    keyboard = [
        [KeyboardButton("Отправить заявку")],
        [KeyboardButton("Написать специалисту")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я готов принимать твои заявки. Выбери вариант ниже 👇",
        reply_markup=markup
    )
    # Завершаем любой активный диалог, чтобы начать новый
    return ConversationHandler.END

async def start_new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает новый диалог для отправки заявки."""
    context.user_data.clear()
    context.user_data["photos"] = []
    await update.message.reply_text(
        "Как вас зовут?", 
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def handle_specialist_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает кнопку 'Написать специалисту'."""
    chat_info = await context.bot.get_chat(SPECIALIST_ADMIN_ID)
    if chat_info.username:
        await update.message.reply_text(
            f"Чат со специалистом: t.me/{chat_info.username}"
        )
    else:
        await update.message.reply_text(
            "У специалиста нет публичного username. Отправьте заявку, чтобы он связался с вами."
        )
    return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет имя и запрашивает телефон."""
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Укажите номер телефона:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет телефон и запрашивает комментарий."""
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Введите ваш комментарий (или напишите 'Пропустить'):")
    return COMMENT

async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет комментарий и запрашивает фото."""
    comment = update.message.text
    context.user_data["comment"] = comment if comment.lower() != 'пропустить' else 'Нет комментария'
    await update.message.reply_text(
        f"Отправьте не менее {MIN_PHOTOS} фото. Вы можете отправить их одной группой или по одному. "
        "После того, как отправите все фото, нажмите 'Готово'."
    )
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет фото и отображает кнопку 'Готово' при достижении MIN_PHOTOS."""
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        context.user_data.setdefault("photos", []).append(photo_file_id)

    current_photos_count = len(context.user_data.get("photos", []))
    
    if current_photos_count >= MIN_PHOTOS:
        keyboard = [[KeyboardButton("Готово")]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Получено {current_photos_count} фото. Нажмите 'Готово' для завершения.",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            f"Получено {current_photos_count}/{MIN_PHOTOS} фото. Отправьте ещё фото."
        )
    
    return PHOTO

async def finalize_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет заявку администраторам и завершает диалог."""
    photos = context.user_data.get("photos", [])
    
    if len(photos) < MIN_PHOTOS:
        await update.message.reply_text(
            f"Необходимо отправить не менее {MIN_PHOTOS} фото. "
            f"Вы отправили только {len(photos)}. Пожалуйста, отправьте ещё фото."
        )
        return PHOTO

    user_username = update.effective_user.username or 'Не указан'
    user_id = update.effective_user.id
    
    text = (
        f"📩 Новая заявка:\n"
        f"👤 Имя: {context.user_data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {context.user_data.get('phone', 'Не указан')}\n"
        f"💬 Комментарий: {context.user_data.get('comment', 'Не указан')}\n"
        f"🔗 Пользователь: <a href='tg://user?id={user_id}'>{user_username}</a>"
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=text,
            parse_mode='HTML'
        )
        if photos:
            try:
                media_group = [InputMediaPhoto(media=photo_id) for photo_id in photos]
                await context.bot.send_media_group(chat_id=admin_id, media=media_group)
            except Exception as e:
                logger.error(f"Не удалось отправить медиагруппу: {e}")
                for photo_id in photos:
                    await context.bot.send_photo(chat_id=admin_id, photo=photo_id)

    await update.message.reply_text(
        "Спасибо! Ваша заявка успешно отправлена.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    
    await start(update, context)
    return ConversationHandler.END

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Сначала добавляем обработчики, которые не должны прерываться ConversationHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^Написать специалисту$"), handle_specialist_redirect))
    
    # Затем добавляем сам ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Отправить заявку$"), start_new_request),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
            PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(filters.Regex("(?i)^Готово$"), finalize_request)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", start), # При /cancel возвращаемся в главное меню
            MessageHandler(filters.Regex("^Отправить заявку$"), start_new_request),
        ],
    )
    app.add_handler(conv_handler)
    
    logger.info("Бот запущен (polling)")
    # Запуск бота в режиме Webhook для Render
    PORT = int(os.environ.get("PORT", "8080"))
    app.run_webhook(listen="0.0.0.0",
                    port=PORT,
                    url_path=TOKEN,
                    webhook_url=os.environ.get("WEBHOOK_URL", ""))

if __name__ == "__main__":
    main()
