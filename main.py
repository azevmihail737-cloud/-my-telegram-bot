from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "ТВОЙ_ТОКЕН"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Подключиться", callback_data="connect")],
        [InlineKeyboardButton("⚡ Купить", callback_data="buy")],
        [InlineKeyboardButton("🔒 Моя подписка", callback_data="subscription")],
        [
            InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
            InlineKeyboardButton("ℹ️ Информация", callback_data="info")
        ],
        [InlineKeyboardButton("📖 Язык", callback_data="language")],
        [InlineKeyboardButton("💬 Поддержка", callback_data="support")],
        [InlineKeyboardButton("📢 Новости", callback_data="news")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    with open("test.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=(
                "⚡ <b>Привет, {}</b>\n\n"
                "🔒 <b>Ваша подписка активна</b>\n"
                "📱 Устройства: 2/2\n\n"
                "Добро пожаловать! Выберите действие ниже."
            ).format(update.effective_user.first_name),
            parse_mode="HTML",
            reply_markup=reply_markup
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
