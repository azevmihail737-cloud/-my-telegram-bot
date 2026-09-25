import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)


# =========================
# ГЛАВНЫЙ ЭКРАН
# =========================

def main_menu(message):
    user = message.from_user
    name = user.first_name or "друг"

    text = (
        f"⚡ Привет, <b>{name}</b>\n\n"
        f"🔒 Активна до <b>03.02.2027</b> • <b>132 дн.</b>\n"
        f"📱 Устройства <b>2/2</b>\n\n"
        f"Выберите действие:"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)

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
            "📖 Язык",
            callback_data="language"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            callback_data="support"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Новости",
            callback_data="news"
        )
    )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    main_menu(message)


# =========================
# КНОПКА "ПОДКЛЮЧИТЬСЯ"
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "connect")
def connect(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "🔗 Получить конфигурацию",
            callback_data="get_config"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "🔗 <b>Подключение</b>\n\n"
        "Выберите способ подключения:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# КОНФИГУРАЦИЯ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "get_config")
def get_config(call):
    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "🔐 Здесь позже будет выдаваться ссылка "
        "или конфигурация для подключения."
    )


# =========================
# КУПИТЬ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        types.InlineKeyboardButton(
            "1 месяц — 199 ₽",
            callback_data="buy_1"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "3 месяца — 499 ₽",
            callback_data="buy_3"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "12 месяцев — 1499 ₽",
            callback_data="buy_12"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "⚡ <b>Покупка подписки</b>\n\n"
        "Выберите срок подписки:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# МОЯ ПОДПИСКА
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "subscription")
def subscription(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "🔗 Подключиться",
            callback_data="connect"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "🔒 <b>Моя подписка</b>\n\n"
        "Статус: 🟢 Активна\n"
        "Активна до: <b>03.02.2027</b>\n"
        "Осталось: <b>132 дня</b>\n"
        "Устройства: <b>2/2</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# РЕФЕРАЛЫ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "referrals")
def referrals(call):
    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "👥 <b>Реферальная программа</b>\n\n"
        "Приглашайте друзей и получайте бонусы.\n\n"
        "Ваша реферальная ссылка появится здесь.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=back_button()
    )


# =========================
# ИНФОРМАЦИЯ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "info")
def info(call):
    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "ℹ️ <b>Информация</b>\n\n"
        "🚀 Быстрый и удобный сервис\n"
        "🔒 Защищённое соединение\n"
        "📱 Поддержка нескольких устройств\n\n"
        "По всем вопросам обращайтесь в поддержку.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=back_button()
    )


# =========================
# ЯЗЫК
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "language")
def language(call):
    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "📖 <b>Язык</b>\n\n"
        "🇷🇺 Русский\n"
        "🇬🇧 English\n\n"
        "Выберите язык:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=back_button()
    )


# =========================
# ПОДДЕРЖКА
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "support")
def support(call):
    bot.answer_callback_query(call.id)

    bot.edit_message_text(
        "💬 <b>Поддержка</b>\n\n"
        "Если у вас возникли проблемы, "
        "напишите нашему администратору.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=back_button()
    )


# =========================
# НОВОСТИ
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "news")
def news(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Открыть канал",
            url="https://t.me/marseilles_shop"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    bot.edit_message_text(
        "📢 <b>Новости</b>\n\n"
        "Следите за новостями и обновлениями "
        "в нашем Telegram-канале.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# НАЗАД
# =========================

def back_button():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    )

    return keyboard


@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.answer_callback_query(call.id)

    user = call.from_user
    name = user.first_name or "друг"

    text = (
        f"⚡ Привет, <b>{name}</b>\n\n"
        f"🔒 Активна до <b>03.02.2027</b> • <b>132 дн.</b>\n"
        f"📱 Устройства <b>2/2</b>\n\n"
        f"Выберите действие:"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)

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
            "📖 Язык",
            callback_data="language"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "💬 Поддержка",
            callback_data="support"
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Новости",
            callback_data="news"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================
# ЗАПУСК
# =========================

print("Бот запущен!")
bot.infinity_polling()
