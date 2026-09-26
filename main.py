import os

import telebot

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(
    func=lambda message: True,
    content_types=[
        "text",
        "audio",
        "document",
        "photo",
        "sticker",
        "video",
        "video_note",
        "voice",
        "location",
        "contact",
        "venue",
        "animation",
        "dice",
        "poll",
    ],
)
def repeat_message(message):
    """Копирует любое сообщение обратно пользователю без добавления подписи."""
    bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )


print("Бот запущен!")
bot.infinity_polling()
