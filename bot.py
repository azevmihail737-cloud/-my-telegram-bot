import asyncio
import os
from decimal import Decimal, InvalidOperation

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# ============================================================
# НАСТРОЙКИ БОТА
# ============================================================

# Токен НЕ нужно вставлять сюда.
# Bothost передаёт его автоматически.
BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
    or os.getenv("API_TOKEN")
)

# ============================================================
# ВАШ TELEGRAM ID
# ============================================================
# ВПИШИТЕ СЮДА СВОЙ ID вместо 123456789
# Например: ADMIN_ID = 987654321
ADMIN_ID = 8759274321

# ============================================================
# Остальной код ниже менять не нужно
# ============================================================
SHOP_NAME = os.getenv("SHOP_NAME", "SHOP")
DB_PATH = "shop.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в переменных окружения Bothost")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID не задан. Укажите Telegram ID администратора в переменных окружения Bothost.")

router = Router()


# ---------- DB ----------

async def db_execute(sql, params=(), fetchone=False, fetchall=False, commit=False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        if commit:
            await db.commit()
        if fetchone:
            return await cur.fetchone()
        if fetchall:
            return await cur.fetchall()
        return cur


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'WAITING_PAYMENT',
            payment_file_id TEXT,
            buyer_key TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        INSERT OR IGNORE INTO settings(key, value)
        VALUES ('payment_details', 'Укажите реквизиты в админ-панели');
        """)
        await db.commit()


async def get_setting(key):
    row = await db_execute(
        "SELECT value FROM settings WHERE key = ?", (key,), fetchone=True
    )
    return row["value"] if row else ""


async def set_setting(key, value):
    await db_execute(
        """INSERT INTO settings(key,value) VALUES(?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
        (key, value),
        commit=True,
    )


# ---------- Helpers ----------

def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
    ])


def back_kb(callback="home"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback)]
    ])


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="🛍 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="📁 Категории", callback_data="admin_categories")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="admin_payment")],
        [InlineKeyboardButton(text="⬅️ В магазин", callback_data="home")],
    ])


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def safe_edit(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)


# ---------- FSM ----------

class AdminStates(StatesGroup):
    waiting_key = State()
    waiting_payment_details = State()
    waiting_category_name = State()
    waiting_product_name = State()
    waiting_product_price = State()


# ---------- User ----------

@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"🛍 <b>{SHOP_NAME}</b>\n\nВыберите действие:",
        reply_markup=main_kb()
    )


@router.callback_query(F.data == "home")
async def home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await safe_edit(
        call.message,
        f"🛍 <b>{SHOP_NAME}</b>\n\nВыберите действие:",
        main_kb()
    )


@router.callback_query(F.data == "buy")
async def categories(call: CallbackQuery):
    rows = await db_execute(
        "SELECT * FROM categories WHERE active=1 ORDER BY id",
        fetchall=True
    )
    await call.answer()
    if not rows:
        await safe_edit(call.message, "🛒 Сейчас товары отсутствуют.", back_kb())
        return

    kb = [
        [InlineKeyboardButton(text=r["name"], callback_data=f"cat:{r['id']}")]
        for r in rows
    ]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="home")])
    await safe_edit(call.message, "🛒 <b>Выберите категорию:</b>",
                    InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith("cat:"))
async def products(call: CallbackQuery):
    category_id = int(call.data.split(":")[1])
    rows = await db_execute(
        """SELECT * FROM products
           WHERE category_id=? AND active=1 ORDER BY id""",
        (category_id,),
        fetchall=True
    )
    await call.answer()

    kb = [
        [InlineKeyboardButton(
            text=f"{r['name']} — {money(r['price'])}",
            callback_data=f"prod:{r['id']}"
        )]
        for r in rows
    ]
    kb.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="buy")])

    text = "🛍 <b>Выберите товар:</b>" if rows else "В этой категории пока нет товаров."
    await safe_edit(call.message, text, InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith("prod:"))
async def product_card(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    row = await db_execute(
        """SELECT p.*, c.name AS category_name
           FROM products p JOIN categories c ON c.id=p.category_id
           WHERE p.id=? AND p.active=1""",
        (product_id,),
        fetchone=True
    )
    await call.answer()

    if not row:
        await safe_edit(call.message, "❌ Товар недоступен.", back_kb("buy"))
        return

    text = (
        f"🛍 <b>{row['name']}</b>\n\n"
        f"Категория: {row['category_name']}\n"
        f"Цена: <b>{money(row['price'])}</b>\n\n"
        "Цифровой товар будет выдан после подтверждения оплаты."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить", callback_data=f"order:{row['id']}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{row['category_id']}")]
    ])
    await safe_edit(call.message, text, kb)


@router.callback_query(F.data.startswith("order:"))
async def create_order(call: CallbackQuery):
    product_id = int(call.data.split(":")[1])
    p = await db_execute(
        "SELECT * FROM products WHERE id=? AND active=1",
        (product_id,), fetchone=True
    )
    if not p:
        await call.answer("Товар недоступен", show_alert=True)
        return

    cur = await db_execute(
        """INSERT INTO orders(user_id,username,first_name,product_id,product_name,amount)
           VALUES(?,?,?,?,?,?)""",
        (
            call.from_user.id,
            call.from_user.username,
            call.from_user.first_name,
            p["id"], p["name"], p["price"]
        ),
        commit=True
    )
    order_id = cur.lastrowid
    details = await get_setting("payment_details")
    await call.answer()

    text = (
        f"💳 <b>Заказ №{order_id}</b>\n\n"
        f"Товар: <b>{p['name']}</b>\n"
        f"Сумма: <b>{money(p['price'])}</b>\n\n"
        f"<b>Реквизиты для оплаты:</b>\n{details}\n\n"
        "После оплаты нажмите кнопку ниже и отправьте скриншот чека."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить / отправить чек",
                              callback_data=f"pay:{order_id}")],
        [InlineKeyboardButton(text="⬅️ В магазин", callback_data="home")]
    ])
    await safe_edit(call.message, text, kb)


@router.callback_query(F.data.startswith("pay:"))
async def payment_prompt(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    order = await db_execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, call.from_user.id), fetchone=True
    )
    await call.answer()
    if not order:
        await safe_edit(call.message, "❌ Заказ не найден.", back_kb())
        return

    await safe_edit(
        call.message,
        f"🧾 <b>Заказ №{order_id}</b>\n\n"
        "Отправьте сюда <b>скриншот чека</b> одним изображением.",
        back_kb("home")
    )


@router.message(F.photo)
async def receive_receipt(message: Message):
    # Берём последний незавершённый заказ пользователя.
    order = await db_execute(
        """SELECT * FROM orders
           WHERE user_id=? AND status='WAITING_PAYMENT'
           ORDER BY id DESC LIMIT 1""",
        (message.from_user.id,), fetchone=True
    )
    if not order:
        return

    file_id = message.photo[-1].file_id
    await db_execute(
        "UPDATE orders SET payment_file_id=?, status='PENDING_REVIEW' WHERE id=?",
        (file_id, order["id"]),
        commit=True
    )

    await message.answer(
        f"✅ <b>Заявка №{order['id']} отправлена на проверку.</b>\n\n"
        "Ожидайте подтверждения оплаты."
    )

    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    buyer_name = message.from_user.full_name or "без имени"
    admin_text = (
        f"📦 <b>Новый заказ №{order['id']}</b>\n\n"
        f"Товар: {order['product_name']}\n"
        f"Сумма: {money(order['amount'])}\n"
        f"Покупатель: {buyer_name} ({username})\n"
        f"Telegram ID: <code>{order['user_id']}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Открыть заказ",
                              callback_data=f"vieworder:{order['id']}")]
    ])
    await message.bot.send_photo(
        ADMIN_ID, file_id, caption=admin_text, reply_markup=kb
    )


# ---------- Admin ----------

@router.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_orders")
async def admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    rows = await db_execute(
        """SELECT * FROM orders
           WHERE status IN ('PENDING_REVIEW','WAITING_KEY')
           ORDER BY id DESC""",
        fetchall=True
    )
    kb = [
        [InlineKeyboardButton(
            text=f"№{r['id']} — {r['product_name']} — {money(r['amount'])}",
            callback_data=f"vieworder:{r['id']}"
        )] for r in rows
    ]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")])
    await call.answer()
    await safe_edit(
        call.message,
        "📦 <b>Активные заказы</b>" if rows else "📦 <b>Активных заказов нет.</b>",
        InlineKeyboardMarkup(inline_keyboard=kb)
    )


@router.callback_query(F.data == "admin")
async def admin_home(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()
    await safe_edit(call.message, "⚙️ <b>Админ-панель</b>", admin_kb())


@router.callback_query(F.data.startswith("vieworder:"))
async def view_order(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    order_id = int(call.data.split(":")[1])
    o = await db_execute("SELECT * FROM orders WHERE id=?", (order_id,), fetchone=True)
    await call.answer()

    if not o:
        await safe_edit(call.message, "Заказ не найден.", back_kb("admin_orders"))
        return

    username = f"@{o['username']}" if o["username"] else "нет username"
    text = (
        f"📦 <b>Заказ №{o['id']}</b>\n\n"
        f"Товар: {o['product_name']}\n"
        f"Сумма: <b>{money(o['amount'])}</b>\n"
        f"Покупатель: {username}\n"
        f"Telegram ID: <code>{o['user_id']}</code>\n"
        f"Статус: <b>{o['status']}</b>"
    )
    buttons = []
    if o["status"] == "PENDING_REVIEW":
        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить",
                                  callback_data=f"approve:{o['id']}")],
            [InlineKeyboardButton(text="❌ Отменить",
                                  callback_data=f"cancel:{o['id']}")],
        ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_orders")])

    # Показываем чек отдельным сообщением, если он есть.
    if o["payment_file_id"]:
        await call.message.answer_photo(
            o["payment_file_id"],
            caption=f"🧾 Чек заказа №{o['id']}"
        )
    await safe_edit(call.message, text, InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("approve:"))
async def approve_order(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    order_id = int(call.data.split(":")[1])
    o = await db_execute(
        "SELECT * FROM orders WHERE id=? AND status='PENDING_REVIEW'",
        (order_id,), fetchone=True
    )
    if not o:
        return await call.answer("Заказ уже обработан", show_alert=True)

    await db_execute(
        "UPDATE orders SET status='WAITING_KEY' WHERE id=?",
        (order_id,), commit=True
    )
    await state.set_state(AdminStates.waiting_key)
    await state.update_data(order_id=order_id)

    await call.answer()
    await safe_edit(
        call.message,
        f"🔑 <b>Заказ №{order_id}</b>\n\nВведите ключ для покупателя.\n"
        "Одним сообщением, без лишнего текста."
    )


@router.message(AdminStates.waiting_key)
async def receive_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    key = message.text.strip() if message.text else ""
    if not order_id or not key:
        return await message.answer("Введите ключ текстом.")

    o = await db_execute("SELECT * FROM orders WHERE id=?", (order_id,), fetchone=True)
    if not o:
        await state.clear()
        return await message.answer("Заказ не найден.")

    await db_execute(
        "UPDATE orders SET buyer_key=?, status='COMPLETED' WHERE id=?",
        (key, order_id), commit=True
    )

    await message.bot.send_message(
        o["user_id"],
        f"🎉 <b>Оплата подтверждена!</b>\n\n"
        f"Заказ №{order_id}\n"
        f"Товар: {o['product_name']}\n\n"
        f"🔑 <b>Ваш ключ:</b>\n<code>{key}</code>\n\n"
        "Спасибо за покупку!"
    )
    await state.clear()
    await message.answer(f"✅ Заказ №{order_id} закрыт, ключ отправлен покупателю.",
                         reply_markup=admin_kb())


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_order(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    order_id = int(call.data.split(":")[1])
    o = await db_execute(
        "SELECT * FROM orders WHERE id=? AND status='PENDING_REVIEW'",
        (order_id,), fetchone=True
    )
    if not o:
        return await call.answer("Заказ уже обработан", show_alert=True)

    await db_execute(
        "UPDATE orders SET status='CANCELLED' WHERE id=?",
        (order_id,), commit=True
    )
    await call.bot.send_message(
        o["user_id"],
        f"❌ Оплата по заказу №{order_id} не подтверждена.\n"
        "Если это ошибка, свяжитесь с администратором."
    )
    await call.answer("Заказ отменён")
    await admin_orders(call)


# ---------- Admin: categories ----------

@router.callback_query(F.data == "admin_categories")
async def admin_categories(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    rows = await db_execute("SELECT * FROM categories ORDER BY id", fetchall=True)
    kb = [
        [InlineKeyboardButton(
            text=f"{'🟢' if r['active'] else '🔴'} {r['name']}",
            callback_data=f"catadmin:{r['id']}"
        )] for r in rows
    ]
    kb.append([InlineKeyboardButton(text="➕ Добавить категорию",
                                    callback_data="add_category")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")])
    await call.answer()
    await safe_edit(call.message, "📁 <b>Категории</b>",
                    InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "add_category")
async def add_category(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_category_name)
    await call.answer()
    await safe_edit(call.message, "Введите название новой категории:")


@router.message(AdminStates.waiting_category_name)
async def save_category(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        return await message.answer("Название не может быть пустым.")
    await db_execute("INSERT INTO categories(name) VALUES(?)", (name,), commit=True)
    await state.clear()
    await message.answer("✅ Категория добавлена.", reply_markup=admin_kb())


@router.callback_query(F.data.startswith("catadmin:"))
async def category_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    category_id = int(call.data.split(":")[1])
    c = await db_execute("SELECT * FROM categories WHERE id=?", (category_id,), fetchone=True)
    if not c:
        return await call.answer("Категория не найдена", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Включить / 🔴 выключить",
                              callback_data=f"cat_toggle:{category_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_categories")]
    ])
    await call.answer()
    await safe_edit(call.message,
                    f"📁 <b>{c['name']}</b>\nСтатус: {'активна' if c['active'] else 'выключена'}",
                    kb)


@router.callback_query(F.data.startswith("cat_toggle:"))
async def category_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    category_id = int(call.data.split(":")[1])
    await db_execute(
        "UPDATE categories SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
        (category_id,), commit=True
    )
    await call.answer("Статус изменён")
    await admin_categories(call)


# ---------- Admin: products ----------

@router.callback_query(F.data == "admin_products")
async def admin_products(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    rows = await db_execute(
        """SELECT p.*, c.name category_name
           FROM products p JOIN categories c ON c.id=p.category_id
           ORDER BY c.id,p.id""",
        fetchall=True
    )
    kb = [
        [InlineKeyboardButton(
            text=f"{'🟢' if r['active'] else '🔴'} {r['name']} — {money(r['price'])}",
            callback_data=f"prodadmin:{r['id']}"
        )] for r in rows
    ]
    kb.append([InlineKeyboardButton(text="➕ Добавить товар",
                                    callback_data="add_product")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")])
    await call.answer()
    await safe_edit(call.message, "🛍 <b>Товары</b>",
                    InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data == "add_product")
async def add_product(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    cats = await db_execute("SELECT * FROM categories WHERE active=1 ORDER BY id",
                            fetchall=True)
    if not cats:
        return await call.answer("Сначала создайте категорию", show_alert=True)

    kb = [[InlineKeyboardButton(text=c["name"],
                                callback_data=f"newprodcat:{c['id']}")]
          for c in cats]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_products")])
    await call.answer()
    await safe_edit(call.message, "Выберите категорию товара:",
                    InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith("newprodcat:"))
async def product_category_selected(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    category_id = int(call.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminStates.waiting_product_name)
    await call.answer()
    await safe_edit(call.message, "Введите название товара:")


@router.message(AdminStates.waiting_product_name)
async def save_product_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        return await message.answer("Название не может быть пустым.")
    await state.update_data(product_name=name)
    await state.set_state(AdminStates.waiting_product_price)
    await message.answer("Введите цену в рублях, например: 4990")


@router.message(AdminStates.waiting_product_price)
async def save_product(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.replace(" ", "").replace(",", ".").strip()
    try:
        price = int(Decimal(raw))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        return await message.answer("Введите положительную цену целым числом, например 4990.")

    data = await state.get_data()

    # Если product_id есть — это редактирование цены.
    if data.get("product_id"):
        await db_execute(
            "UPDATE products SET price=? WHERE id=?",
            (price, data["product_id"]),
            commit=True
        )
        await state.clear()
        return await message.answer("✅ Цена изменена.", reply_markup=admin_kb())

    # Иначе создаём новый товар.
    await db_execute(
        "INSERT INTO products(category_id,name,price) VALUES(?,?,?)",
        (data["category_id"], data["product_name"], price),
        commit=True
    )
    await state.clear()
    await message.answer("✅ Товар добавлен.", reply_markup=admin_kb())


@router.callback_query(F.data.startswith("prodadmin:"))
async def product_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    product_id = int(call.data.split(":")[1])
    p = await db_execute(
        """SELECT p.*, c.name category_name
           FROM products p JOIN categories c ON c.id=p.category_id
           WHERE p.id=?""",
        (product_id,), fetchone=True
    )
    if not p:
        return await call.answer("Товар не найден", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Включить / 🔴 выключить",
                              callback_data=f"prod_toggle:{product_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену",
                              callback_data=f"prod_price:{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_products")]
    ])
    await call.answer()
    await safe_edit(
        call.message,
        f"🛍 <b>{p['name']}</b>\n"
        f"Категория: {p['category_name']}\n"
        f"Цена: {money(p['price'])}\n"
        f"Статус: {'активен' if p['active'] else 'выключен'}",
        kb
    )


@router.callback_query(F.data.startswith("prod_toggle:"))
async def product_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    product_id = int(call.data.split(":")[1])
    await db_execute(
        "UPDATE products SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
        (product_id,), commit=True
    )
    await call.answer("Статус изменён")
    await admin_products(call)


@router.callback_query(F.data.startswith("prod_price:"))
async def product_price_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    product_id = int(call.data.split(":")[1])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_product_price)
    await call.answer()
    await safe_edit(call.message, "Введите новую цену в рублях:")


# ---------- Admin: payment details ----------

@router.callback_query(F.data == "admin_payment")
async def admin_payment(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    details = await get_setting("payment_details")
    await call.answer()
    await safe_edit(
        call.message,
        f"💳 <b>Текущие реквизиты:</b>\n\n{details}\n\n"
        "Нажмите кнопку, чтобы изменить их.",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить реквизиты",
                                  callback_data="edit_payment")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")]
        ])
    )


@router.callback_query(F.data == "edit_payment")
async def edit_payment(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_payment_details)
    await call.answer()
    await safe_edit(
        call.message,
        "Отправьте новые платёжные реквизиты одним сообщением.\n\n"
        "Например:\n"
        "Карта: XXXX XXXX XXXX XXXX\n"
        "Получатель: Иван Иванов"
    )


@router.message(AdminStates.waiting_payment_details)
async def save_payment(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    details = message.text.strip()
    if not details:
        return await message.answer("Реквизиты не могут быть пустыми.")
    await set_setting("payment_details", details)
    await state.clear()
    await message.answer("✅ Реквизиты сохранены.", reply_markup=admin_kb())


async def main():
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Если у бота раньше был webhook, polling не получит сообщения.
    # Удаляем webhook перед запуском. Сам токен при этом остаётся в Bothost.
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        print(f"⚠️ Не удалось удалить webhook: {e}")

    # Проверяем токен и сразу показываем в логе, что бот действительно стартовал.
    me = await bot.get_me()
    print(f"✅ Bot started: @{me.username} (id={me.id})")
    print(f"✅ Admin ID: {ADMIN_ID}")

    dp = Dispatcher()
    dp.include_router(router)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
