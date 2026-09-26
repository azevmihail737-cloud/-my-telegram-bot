import json
import os
from typing import Dict, List

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN", "7919305289:AAEi0Fh_kT_8-N8V5qZ9W_xY2A3B4C5D6E7")
ADMIN_USERNAME = "SotkaSV"
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
DATA_FILE = os.path.join(os.path.dirname(__file__), "orders.json")

if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

bot = telebot.TeleBot(TOKEN)

# Тарифы App Store
KEYS = {
    "1m": {"title": "App Store — 1 месяц", "price": "299 ₽"},
    "3m": {"title": "App Store — 3 месяца", "price": "799 ₽"},
    "12m": {"title": "App Store — 12 месяцев", "price": "2499 ₽"},
}

# Храним, какой пользователь сейчас ждёт фото оплаты
awaiting_payment = {}


def load_orders() -> List[Dict]:
    """Загружает заказы из файла"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_orders(orders: List[Dict]):
    """Сохраняет заказы в файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def get_pending_orders():
    """Получает все открытые заявки"""
    return [o for o in load_orders() if o.get("status") == "new"]


def is_admin(user) -> bool:
    """Проверяет, является ли пользователь админом"""
    username = (user.username or "").lower()
    return username == ADMIN_USERNAME.lower()


def build_main_menu():
    """Главное меню"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🛒 Купить App Store", callback_data="buy_key"),
        types.InlineKeyboardButton("📋 Мои заявки", callback_data="my_orders"),
    )
    return keyboard


def build_key_menu():
    """Меню с выбором тарифов"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for key, info in KEYS.items():
        keyboard.add(
            types.InlineKeyboardButton(
                f"{info['title']} — {info['price']}",
                callback_data=f"plan_{key}",
            )
        )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return keyboard


def build_admin_menu():
    """Меню админа"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    pending = get_pending_orders()
    count = len(pending)
    button_text = f"📌 Открытые заявки ({count})"
    keyboard.add(types.InlineKeyboardButton(button_text, callback_data="admin_open_requests"))
    return keyboard


def build_pending_requests_keyboard():
    """Меню с открытыми заявками"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    pending = get_pending_orders()
    
    if not pending:
        keyboard.add(types.InlineKeyboardButton("✅ Нет открытых заявок", callback_data="noop"))
        return keyboard

    for order in pending:
        label = f"#{order['id']} — {order['product']} | {order['user_name']}"
        keyboard.add(types.InlineKeyboardButton(label, callback_data=f"admin_order_{order['id']}"))
    
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu"))
    return keyboard


def get_order_by_id(order_id: str):
    """Получает заказ по ID"""
    for order in load_orders():
        if str(order.get("id")) == str(order_id):
            return order
    return None


def send_to_admin(message_text, photo_file_id=None):
    """Отправляет сообщение админу"""
    if ADMIN_CHAT_ID:
        try:
            if photo_file_id:
                bot.send_photo(int(ADMIN_CHAT_ID), photo_file_id, caption=message_text, parse_mode="HTML")
            else:
                bot.send_message(int(ADMIN_CHAT_ID), message_text, parse_mode="HTML")
            return
        except Exception as e:
            print(f"Ошибка отправки админу (по CHAT_ID): {e}")

    # Пытаемся отправить по username
    try:
        admin_user = bot.get_chat(f"@{ADMIN_USERNAME}")
        admin_chat_id = admin_user.id

        if photo_file_id:
            bot.send_photo(admin_chat_id, photo_file_id, caption=message_text, parse_mode="HTML")
        else:
            bot.send_message(admin_chat_id, message_text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки админу (по username): {e}")


# ======================== HANDLERS ========================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name or "Друг"
    bot.send_message(
        message.chat.id,
        f"🛍️ Привет, {user_name}!\n\nДобро пожаловать в App Store Bot\n\nВыберите действие:",
        reply_markup=build_main_menu(),
    )


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    """Обработчик команды /admin"""
    if not is_admin(message.from_user):
        bot.send_message(
            message.chat.id,
            "❌ У вас нет доступа к админ-панели.\n\n"
            f"Админ: @{ADMIN_USERNAME}"
        )
        return

    bot.send_message(
        message.chat.id,
        "🔐 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=build_admin_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(commands=["help"])
def cmd_help(message):
    """Обработчик команды /help"""
    bot.send_message(
        message.chat.id,
        "<b>🛍️ App Store Bot</b>\n\n"
        "<b>Как купить:</b>\n"
        "1. Нажмите '<b>Купить App Store</b>'\n"
        "2. Выберите тариф\n"
        "3. Отправьте скриншот оплаты\n"
        "4. Админ рассмотрит заявку\n"
        "5. Получите ключ\n\n"
        "<b>Тарифы:</b>\n"
        "📅 1 месяц — 299 ₽\n"
        "📅 3 месяца — 799 ₽\n"
        "📅 12 месяцев — 2499 ₽\n\n"
        f"<b>Админ:</b> @{ADMIN_USERNAME}",
        parse_mode="HTML"
    )


# ======================== CALLBACK HANDLERS ========================

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def callback_main_menu(call):
    """Возврат в главное меню"""
    bot.edit_message_text(
        "🛍️ Выберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_main_menu(),
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "buy_key")
def callback_buy_key(call):
    """Меню покупки"""
    bot.edit_message_text(
        "📦 <b>Выберите тариф App Store:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_key_menu(),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def callback_plan(call):
    """Выбор тарифа"""
    product_key = call.data.split("_", 1)[1]
    product = KEYS.get(product_key)

    if not product:
        bot.answer_callback_query(call.id, "❌ Тариф не найден", show_alert=True)
        return

    user_id = call.from_user.id
    awaiting_payment[user_id] = product_key

    bot.answer_callback_query(call.id, "✅ Тариф выбран")
    bot.send_message(
        call.message.chat.id,
        f"<b>✅ Вы выбрали:</b> {product['title']}\n"
        f"<b>💰 Цена:</b> {product['price']}\n\n"
        "<b>📸 Отправьте скриншот оплаты</b>\n"
        "После этого заявка уйдёт админу на рассмотрение.",
        parse_mode="HTML"
    )


@bot.message_handler(content_types=["photo", "document"])
def handle_payment_photo(message):
    """Обработка фото оплаты"""
    user_id = message.from_user.id
    if user_id not in awaiting_payment:
        return

    product_key = awaiting_payment.pop(user_id)
    product = KEYS[product_key]

    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
    elif message.document:
        photo_file_id = message.document.file_id

    orders = load_orders()
    order_id = str(len(orders) + 1)

    new_order = {
        "id": order_id,
        "user_id": str(message.from_user.id),
        "user_name": message.from_user.username or message.from_user.first_name or "Без имени",
        "user_first_name": message.from_user.first_name or "Без имени",
        "product": product["title"],
        "price": product["price"],
        "photo_file_id": photo_file_id,
        "status": "new",
        "created_at": str(message.date),
    }

    orders.append(new_order)
    save_orders(orders)

    bot.send_message(
        message.chat.id,
        "✅ <b>Заявка отправлена</b>\n\n"
        "Ваша заявка отправлена админу на рассмотрение.\n"
        "Проверьте статус в меню 'Мои заявки'\n"
        "⏱️ Время обработки: обычно 1-2 часа",
        parse_mode="HTML",
        reply_markup=build_main_menu()
    )

    admin_text = (
        f"<b>📩 НОВАЯ ЗАЯВКА НА APP STORE</b>\n\n"
        f"<b>ID заявки:</b> #{order_id}\n"
        f"<b>Пользователь:</b> @{message.from_user.username or 'без username'}\n"
        f"<b>Имя:</b> {message.from_user.first_name}\n"
        f"<b>Тариф:</b> {product['title']}\n"
        f"<b>Цена:</b> {product['price']}\n"
        f"<b>Статус:</b> 🟡 Ожидает подтверждения"
    )

    send_to_admin(admin_text, photo_file_id)


@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def callback_my_orders(call):
    """Показать мои заявки"""
    orders = load_orders()
    user_orders = [o for o in orders if str(o.get("user_id")) == str(call.from_user.id)]

    if not user_orders:
        bot.edit_message_text(
            "📋 <b>Мои заявки</b>\n\n"
            "У вас пока нет заявок.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id)
        return

    text = "📋 <b>Ваши заявки:</b>\n\n"
    for order in user_orders:
        status_text = {
            "new": "🟡 На рассмотрении",
            "approved": "✅ Принята (ключ отправлен)",
            "rejected": "❌ Отклонена",
        }.get(order.get("status"), "❓ Неизвестно")

        text += f"<b>#{order['id']}</b> — {order['product']}\n{status_text}\n\n"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "admin_menu")
def callback_admin_menu(call):
    """Вернуться в меню админа"""
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "❌ Нет доступа", show_alert=True)
        return

    bot.edit_message_text(
        "🔐 <b>Админ-панель</b>\n\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_admin_menu(),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "admin_open_requests")
def callback_admin_open_requests(call):
    """Показать открытые заявки"""
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "❌ Нет доступа", show_alert=True)
        return

    pending = get_pending_orders()
    count = len(pending)

    bot.edit_message_text(
        f"📌 <b>Открытые заявки ({count})</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_pending_requests_keyboard(),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_order_"))
def callback_admin_order(call):
    """Показать детали заявки"""
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "❌ Нет доступа", show_alert=True)
        return

    order_id = call.data.replace("admin_order_", "")
    order = get_order_by_id(order_id)

    if not order:
        bot.answer_callback_query(call.id, "❌ Заявка не найдена", show_alert=True)
        return

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ Принять", callback_data=f"approve_{order_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}"),
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_open_requests"))

    caption = (
        f"<b>📩 Детали заявки #{order['id']}</b>\n\n"
        f"<b>Пользователь:</b> @{order['user_name']}\n"
        f"<b>Имя:</b> {order.get('user_first_name', 'N/A')}\n"
        f"<b>Тариф:</b> {order['product']}\n"
        f"<b>Цена:</b> {order['price']}\n"
        f"<b>Статус:</b> 🟡 Ожидает рассмотрения"
    )

    if order.get("photo_file_id"):
        try:
            bot.edit_message_media(
                types.InputMediaPhoto(order["photo_file_id"], caption=caption, parse_mode="HTML"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
            bot.answer_callback_query(call.id)
            return
        except Exception:
            pass

    bot.edit_message_text(
        caption,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def callback_approve(call):
    """Принять заявку"""
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "❌ Нет доступа", show_alert=True)
        return

    order_id = call.data.replace("approve_", "")
    orders = load_orders()

    for order in orders:
        if str(order.get("id")) == str(order_id):
            order["status"] = "approved"
            save_orders(orders)

            # Отправляем уведомление пользователю
            bot.send_message(
                order["user_id"],
                f"✅ <b>Ваша заявка #{order_id} ПРИНЯТА!</b>\n\n"
                f"<b>Тариф:</b> {order['product']}\n"
                f"<b>Цена:</b> {order['price']}\n\n"
                "🎉 Ключ будет отправлен вам в ближайшее время.\n"
                "Спасибо за покупку!",
                parse_mode="HTML",
                reply_markup=build_main_menu()
            )
            break

    bot.answer_callback_query(call.id, "✅ Заявка принята и пользователю отправлено уведомление")
    bot.edit_message_text(
        f"✅ <b>Заявка #{order_id} принята</b>\n\n"
        "Пользователю отправлено уведомление.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def callback_reject(call):
    """Отклонить заявку"""
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "❌ Нет доступа", show_alert=True)
        return

    order_id = call.data.replace("reject_", "")
    orders = load_orders()

    for order in orders:
        if str(order.get("id")) == str(order_id):
            order["status"] = "rejected"
            save_orders(orders)

            # Отправляем уведомление пользователю
            bot.send_message(
                order["user_id"],
                f"❌ <b>Ваша заявка #{order_id} была отклонена.</b>\n\n"
                f"<b>Тариф:</b> {order['product']}\n\n"
                "Если у вас есть вопросы, напишите администратору.\n"
                f"Админ: @{ADMIN_USERNAME}",
                parse_mode="HTML",
                reply_markup=build_main_menu()
            )
            break

    bot.answer_callback_query(call.id, "❌ Заявка отклонена и пользователю отправлено уведомление")
    bot.edit_message_text(
        f"❌ <b>Заявка #{order_id} отклонена</b>\n\n"
        "Пользователю отправлено уведомление.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "noop")
def callback_noop(call):
    """Пустой обработчик"""
    bot.answer_callback_query(call.id)


print("✅ Бот запущен и готов к работе!")
print(f"📱 Админ: @{ADMIN_USERNAME}")
print("💰 Тарифы: 1м (299₽), 3м (799₽), 12м (2499₽)")

if __name__ == "__main__":
    bot.infinity_polling()
