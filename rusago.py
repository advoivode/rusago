import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
SPECIALIST_ADMIN_ID = 5979123966

# Этапы диалога
NAME, PHONE, COMMENT, PHOTO = range(4)

# === ОБРАБОТЧИКИ ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заявка отменена. Можете начать заново с команды /start")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Отправить заявку")],
        [KeyboardButton("Написать специалисту")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я готов принимать твои заявки. "
        "Выберите вариант ниже 👇",
        reply_markup=markup
    )

async def start_new_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Как вас зовут?")
    return NAME

async def handle_specialist_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_info = await context.bot.get_chat(SPECIALIST_ADMIN_ID)
    if chat_info.username:
        await update.message.reply_text(
            f"Чат со специалистом: t.me/{chat_info.username}"
        )
    else:
        await update.message.reply_text(
            "У специалиста нет публичного username. "
            "Отправьте заявку, чтобы он связался с вами."
        )
    return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Укажите номер телефона:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Введите ваш комментарий (или напишите 'Пропустить'):")
    return COMMENT

async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comment"] = update.message.text
    await update.message.reply_text("Отправьте фото документов (или напишите 'Пропустить'):")
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.lower() == 'пропустить':
        pass
    else:
        await update.message.reply_text("Пожалуйста, отправьте фото или напишите 'Пропустить'.")
        return PHOTO

    context.user_data["photo"] = photo_file_id
    user_username = update.message.from_user.username

    text = (
        f"📩 Новая заявка:\n"
        f"👤 Имя: {context.user_data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {context.user_data.get('phone', 'Не указан')}\n"
        f"💬 Комментарий: {context.user_data.get('comment', 'Не указан')}\n"
        f"🔗 Ник: {f'@{user_username}' if user_username else 'Не указан'}"
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id, text=text)
        if photo_file_id:
            await context.bot.send_photo(chat_id=admin_id, photo=photo_file_id)

    await start(update, context)
    return ConversationHandler.END

# === ОСНОВНАЯ ФУНКЦИЯ ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^Написать специалисту$"), handle_specialist_redirect))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Отправить заявку$"), start_new_request)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.Regex("(?i)пропустить"), get_photo)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("Бот запущен (polling)")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
