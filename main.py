import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):

    text = (
        f"⚡ <b>Привет, {message.from_user.first_name}!</b>\n\n"
        "🔒 Подписка активна\n"
        "📅 До: 03.02.2027\n"
        "📱 Устройства: 2/2\n\n"
        "Выберите действие:"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        types.InlineKeyboardButton(
            "👋 Привет",
            callback_data="hello"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🔗 Подключиться",
            callback_data="connect"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⚡ Купить",
            callback_data="buy"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🔒 Моя подписка",
            callback_data="subscription"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "👥 Рефералы",
            callback_data="referrals"
        ),
        types.InlineKeyboardButton(
            "ℹ️ Информация",
            callback_data="info"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            callback_data="support"
        )
    )

    # Картинка test.png должна лежать рядом с main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_dir, "test.png")

    with open(image_path, "rb") as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: True)
def buttons(call):

    if call.data == "hello":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "👋 <b>Привет!</b>\n\n"
            "Добро пожаловать в наш бот! 😊",
            parse_mode="HTML"
        )

    elif call.data == "connect":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🔗 <b>Подключение</b>\n\n"
            "Здесь будет инструкция по подключению.",
            parse_mode="HTML"
        )

    elif call.data == "buy":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "⚡ <b>Покупка подписки</b>\n\n"
            "Здесь появятся тарифы.",
            parse_mode="HTML"
        )

    elif call.data == "subscription":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🔒 <b>Моя подписка</b>\n\n"
            "📅 До: 03.02.2027\n"
            "📱 Устройства: 2/2",
            parse_mode="HTML"
        )

    elif call.data == "referrals":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "👥 <b>Реферальная система</b>\n\n"
            "Ваша реферальная ссылка появится здесь.",
            parse_mode="HTML"
        )

    elif call.data == "info":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "ℹ️ <b>Информация</b>\n\n"
            "Добро пожаловать! Здесь будет информация о сервисе.",
            parse_mode="HTML"
        )

    elif call.data == "support":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "💬 <b>Поддержка</b>\n\n"
            "Напишите нам, если у вас возникли вопросы.",
            parse_mode="HTML"
        )


print("Бот запущен!")

bot.infinity_polling()
