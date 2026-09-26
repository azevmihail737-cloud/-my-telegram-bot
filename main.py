import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "SotkaSV"
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "8759274321")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
DATA_FILE = os.path.join(os.path.dirname(__file__), "orders.json")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

if not TOKEN:
    raise RuntimeError("Задайте переменную окружения BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

PRODUCTS = {
    "1m": {"title": "App Store — 1 месяц", "price": "299 ₽"},
    "3m": {"title": "App Store — 3 месяца", "price": "799 ₽"},
    "12m": {"title": "App Store — 12 месяцев", "price": "2499 ₽"},
}

awaiting_payment: Dict[int, str] = {}
awaiting_key: Dict[int, str] = {}


def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path: str, value):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def get_user_label(user) -> str:
    return (user.username or user.first_name or "Без имени")


def load_orders() -> List[Dict]:
    data = load_json(DATA_FILE, [])
    return data if isinstance(data, list) else []


def save_orders(orders: List[Dict]):
    save_json(DATA_FILE, orders)


def pending_orders() -> List[Dict]:
    return [order for order in load_orders() if order.get("status") == "pending"]


def next_order_id(orders: List[Dict]) -> int:
    return max((int(order.get("id", 0)) for order in orders), default=0) + 1


def is_admin(user) -> bool:
    username_ok = (user.username or "").lower() == ADMIN_USERNAME.lower()
    id_ok = bool(ADMIN_USER_ID and str(user.id) == str(ADMIN_USER_ID))
    return username_ok or id_ok


def get_admin_chat_id() -> Optional[int]:
    config = load_json(SETTINGS_FILE, {})
    if ADMIN_CHAT_ID:
        return int(ADMIN_CHAT_ID)
    value = config.get("admin_chat_id")
    return int(value) if value else None


def set_admin_chat_id(chat_id: int):
    save_json(SETTINGS_FILE, {"admin_chat_id": chat_id})


def main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton("🛒 Купить App Store", callback_data="buy"))
    keyboard.add(
        types.InlineKeyboardButton("📋 Мои заявки", callback_data="my_orders"),
        types.InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
    )
    return keyboard


def products_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for key, product in PRODUCTS.items():
        keyboard.add(
            types.InlineKeyboardButton(
                f"{product['title']} · {product['price']}",
                callback_data=f"product:{key}",
            )
        )
    keyboard.add(types.InlineKeyboardButton("⬅️ Главное меню", callback_data="home"))
    return keyboard


def admin_keyboard():
    count = len(pending_orders())
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton(f"📥 Открытые ({count})", callback_data="admin:list"))
    keyboard.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin:stats"),
        types.InlineKeyboardButton("🔄 Обновить", callback_data="admin:menu"),
    )
    return keyboard


def pending_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    orders = pending_orders()
    if not orders:
        keyboard.add(types.InlineKeyboardButton("✅ Открытых заявок нет", callback_data="noop"))
    else:
        for order in orders:
            label = order.get("user_name") or order.get("username") or order.get("first_name") or "Без имени"
            keyboard.add(
                types.InlineKeyboardButton(
                    f"🟡 #{order['id']} · {order['product']} · {label}",
                    callback_data=f"admin:order:{order['id']}",
                )
            )
    keyboard.add(types.InlineKeyboardButton("⬅️ Админ-панель", callback_data="admin:menu"))
    return keyboard


def order_detail_keyboard(order_id: int):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ Принять", callback_data=f"admin:approve:{order_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin:reject:{order_id}"),
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ К заявкам", callback_data="admin:list"))
    return keyboard


def find_order(order_id: str):
    return next((o for o in load_orders() if str(o.get("id")) == str(order_id)), None)


def order_text(order: Dict) -> str:
    user_name = order.get("user_name") or order.get("username") or order.get("first_name") or "Без имени"
    if not str(user_name).startswith("@"):
        user_name = f"@{user_name}"
    return (
        f"<b>📩 Заявка #{order['id']}</b>\n\n"
        f"Покупатель: {user_name}\n"
        f"Имя: {order.get('first_name', '—')}\n"
        f"Товар: {order['product']}\n"
        f"Цена: {order['price']}\n"
        f"Дата: {order.get('created_at', '—')}\n"
        "Статус: 🟡 на рассмотрении"
    )


def notify_admin(order: Dict):
    chat_id = get_admin_chat_id()
    if not chat_id:
        try:
            admin_user = bot.get_chat(f"@{ADMIN_USERNAME}")
            chat_id = admin_user.id
        except Exception:
            print("Админ не найден по username. Уведомление не отправлено.")
            return

    caption = order_text(order)
    try:
        if order.get("proof_file_id"):
            bot.send_photo(chat_id, order["proof_file_id"], caption=caption, parse_mode="HTML")
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML")
        bot.send_message(chat_id, "Откройте /admin → «Открытые заявки», чтобы принять или отклонить заявку.")
    except Exception as error:
        print(f"Ошибка отправки уведомления админу: {error}")


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🛍️ <b>App Store Store</b>\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["admin", "adminchat"])
def admin(message):
    if not is_admin(message.from_user):
        bot.send_message(message.chat.id, "❌ Доступ запрещён.")
        return
    set_admin_chat_id(message.chat.id)
    bot.send_message(
        message.chat.id,
        "🔐 <b>Панель администратора</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "home")
def home(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "🛍️ <b>App Store Store</b>\nВыберите действие:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "📦 <b>Выберите тариф:</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=products_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("product:"))
def choose_product(call):
    key = call.data.split(":", 1)[1]
    product = PRODUCTS.get(key)
    if not product:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    awaiting_payment[call.from_user.id] = key
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"✅ <b>{product['title']}</b>\n💰 {product['price']}\n\n"
        "После оплаты отправьте сюда скриншот чека одним сообщением.",
        parse_mode="HTML",
    )


@bot.message_handler(content_types=["photo", "document"])
def payment_proof(message):
    key = awaiting_payment.pop(message.from_user.id, None)
    if not key:
        return
    product = PRODUCTS[key]
    orders = load_orders()
    user_name = message.from_user.username or message.from_user.first_name or "Без имени"
    order = {
        "id": next_order_id(orders),
        "user_id": message.from_user.id,
        "user_name": user_name,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "product": product["title"],
        "price": product["price"],
        "proof_file_id": message.photo[-1].file_id if message.photo else message.document.file_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    orders.append(order)
    save_orders(orders)
    bot.send_message(
        message.chat.id,
        f"✅ Заявка #{order['id']} отправлена на проверку.",
        reply_markup=main_keyboard(),
    )
    notify_admin(order)


@bot.callback_query_handler(func=lambda call: call.data == "my_orders")
def my_orders(call):
    orders = [o for o in load_orders() if str(o.get("user_id")) == str(call.from_user.id)]
    if not orders:
        text = "📋 <b>Мои заявки</b>\n\nЗаявок пока нет."
    else:
        statuses = {"pending": "🟡 на проверке", "approved": "✅ принята", "rejected": "❌ отклонена"}
        text = "📋 <b>Мои заявки</b>\n\n" + "\n\n".join(
            f"#{o['id']} · {o['product']}\n{statuses.get(o['status'], o['status'])}" for o in orders
        )
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_menu(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "ℹ️ Выберите тариф, оплатите его и отправьте скриншот чека.\n"
        "После проверки администратор отправит ключ.\n\n"
        f"Администратор: @{ADMIN_USERNAME}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin:menu")
def admin_menu(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "🔐 <b>Панель администратора</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin:list")
def admin_list(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        f"📥 <b>Открытые заявки: {len(pending_orders())}</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=pending_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin:stats")
def admin_stats(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    orders = load_orders()
    text = (
        f"📊 <b>Статистика</b>\n\nВсего: {len(orders)}\n"
        f"🟡 На проверке: {sum(o.get('status') == 'pending' for o in orders)}\n"
        f"✅ Принято: {sum(o.get('status') == 'approved' for o in orders)}\n"
        f"❌ Отклонено: {sum(o.get('status') == 'rejected' for o in orders)}"
    )
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin:order:"))
def admin_order(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    order_id = call.data.rsplit(":", 1)[1]
    order = find_order(order_id)
    if not order or order.get("status") != "pending":
        bot.answer_callback_query(call.id, "Заявка уже обработана", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        order_text(order),
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=order_detail_keyboard(int(order_id)),
    )
    if order.get("proof_file_id"):
        bot.send_photo(call.message.chat.id, order["proof_file_id"], caption="🧾 Скриншот оплаты")


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin:approve:"))
def approve(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    order_id = call.data.rsplit(":", 1)[1]
    order = find_order(order_id)
    if not order or order.get("status") != "pending":
        bot.answer_callback_query(call.id, "Заявка уже обработана", show_alert=True)
        return
    awaiting_key[call.from_user.id] = order_id
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"✅ Заявка #{order_id} подтверждена.\nТеперь пришлите ключ следующим сообщением.",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("admin:reject:"))
def reject(call):
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
        return
    order_id = call.data.rsplit(":", 1)[1]
    orders = load_orders()
    for order in orders:
        if str(order.get("id")) == order_id and order.get("status") == "pending":
            order["status"] = "rejected"
            save_orders(orders)
            bot.send_message(
                order["user_id"],
                f"❌ Заявка #{order_id} отклонена.\nПо вопросам: @{ADMIN_USERNAME}",
            )
            bot.answer_callback_query(call.id, "Заявка отменена")
            bot.edit_message_text(
                f"❌ Заявка #{order_id} отменена.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_keyboard(),
            )
            return
    bot.answer_callback_query(call.id, "Заявка уже обработана", show_alert=True)


@bot.message_handler(func=lambda message: message.from_user.id in awaiting_key and message.text)
def send_key(message):
    if not is_admin(message.from_user):
        return
    order_id = awaiting_key.pop(message.from_user.id)
    orders = load_orders()
    for order in orders:
        if str(order.get("id")) == str(order_id) and order.get("status") == "pending":
            order["status"] = "approved"
            order["key"] = message.text.strip()
            save_orders(orders)
            bot.send_message(
                order["user_id"],
                f"✅ Оплата заявки #{order_id} подтверждена!\n\n"
                f"🔑 Ваш ключ:\n<code>{order['key']}</code>",
                parse_mode="HTML",
            )
            bot.send_message(
                message.chat.id,
                f"✅ Ключ отправлен по заявке #{order_id}.",
                reply_markup=admin_keyboard(),
            )
            return


@bot.callback_query_handler(func=lambda call: call.data == "noop")
def noop(call):
    bot.answer_callback_query(call.id)


if __name__ == "__main__":
    print("Бот запущен")
    print(f"Админ username: @{ADMIN_USERNAME}")
    print(f"Админ user_id: {ADMIN_USER_ID}")
    print("Команды: /admin или /adminchat")
    bot.infinity_polling()
