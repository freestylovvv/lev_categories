import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

import config
import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

router = Dispatcher(storage=MemoryStorage())


class AddSneaker(StatesGroup):
    brand = State()
    model = State()
    size = State()
    price = State()
    description = State()
    photo = State()


class SearchState(StatesGroup):
    query = State()


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👟 Каталог")],
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="🏷 Бренды")],
            [KeyboardButton(text="➕ Добавить товар")],
        ],
        resize_keyboard=True
    )


def brands_kb(brands):
    buttons = [[InlineKeyboardButton(text=b, callback_data=f"brand:{b}")] for b in brands]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message):
    total = await db.count_sneakers()
    await message.answer(
        f"👋 <b>Добро пожаловать в магазин кроссовок!</b>\n\n"
        f"📦 Моделей в каталоге: <b>{total}</b>\n\n"
        f"Выберите действие в меню ниже 👇",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "👟 Каталог")
async def show_catalog(message: Message):
    items = await db.get_all_sneakers()
    if not items:
        await message.answer("😕 Каталог пуст. Добавьте первый товар.")
        return

    await message.answer(f"👟 Показано моделей: <b>{len(items)}</b>", parse_mode="HTML")

    for item in items[:20]:
        caption = (
            f"<b>{item['brand']} {item['model']}</b>\n"
            f"📏 Размеры: {item['size'] or '—'}\n"
            f"💰 Цена: <b>{item['price']:.0f} ₽</b>\n"
            f"📝 {item['description'] or 'Без описания'}"
        )
        try:
            await message.answer_photo(photo=item["photo_id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logging.warning("Ошибка отправки фото: %s", e)


@router.message(F.text == "🏷 Бренды")
async def show_brands(message: Message):
    brands = await db.get_brands()
    if not brands:
        await message.answer("Список брендов пуст.")
        return
    await message.answer("Выберите бренд 👇", reply_markup=brands_kb(brands))


@router.callback_query(F.data.startswith("brand:"))
async def brand_callback(cb: CallbackQuery):
    brand = cb.data.split(":", 1)[1]
    items = await db.get_sneakers_by_brand(brand)
    await cb.message.answer(f"🏷 <b>{brand}</b>: {len(items)} моделей", parse_mode="HTML")
    for item in items[:20]:
        caption = (
            f"<b>{item['brand']} {item['model']}</b>\n"
            f"📏 Размеры: {item['size'] or '—'}\n"
            f"💰 Цена: <b>{item['price']:.0f} ₽</b>"
        )
        try:
            await cb.message.answer_photo(photo=item["photo_id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logging.warning("Ошибка: %s", e)
    await cb.answer()


@router.message(F.text == "🔍 Поиск")
async def ask_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await message.answer("Введите название бренда или модели:")


@router.message(SearchState.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    items = await db.search_sneakers(message.text.strip())
    if not items:
        await message.answer("😔 Ничего не найдено.", reply_markup=main_menu())
        return
    await message.answer(f"🔍 Найдено: <b>{len(items)}</b>", parse_mode="HTML")
    for item in items[:20]:
        caption = (
            f"<b>{item['brand']} {item['model']}</b>\n"
            f"📏 Размеры: {item['size'] or '—'}\n"
            f"💰 Цена: <b>{item['price']:.0f} ₽</b>"
        )
        try:
            await message.answer_photo(photo=item["photo_id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logging.warning("Ошибка: %s", e)
    await message.answer("Готово!", reply_markup=main_menu())


@router.message(F.text == "➕ Добавить товар")
async def add_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Только для админов.")
        return
    await state.set_state(AddSneaker.brand)
    await message.answer(
        "Введите <b>бренд</b> (например, Nike):",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )


@router.message(AddSneaker.brand)
async def add_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text.strip())
    await state.set_state(AddSneaker.model)
    await message.answer("Введите <b>модель</b> (например, Air Max 90):", parse_mode="HTML")


@router.message(AddSneaker.model)
async def add_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text.strip())
    await state.set_state(AddSneaker.size)
    await message.answer("Введите <b>размеры</b> через запятую (40,41,42):", parse_mode="HTML")


@router.message(AddSneaker.size)
async def add_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text.strip())
    await state.set_state(AddSneaker.price)
    await message.answer("Введите <b>цену</b> (только число):", parse_mode="HTML")


@router.message(AddSneaker.price)
async def add_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите цену числом:")
        return
    await state.update_data(price=price)
    await state.set_state(AddSneaker.description)
    await message.answer("Введите <b>описание</b> или «-» чтобы пропустить:", parse_mode="HTML")


@router.message(AddSneaker.description)
async def add_description(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(description="" if text == "-" else text)
    await state.set_state(AddSneaker.photo)
    await message.answer("📸 Отправьте фото кроссовок:")


@router.message(AddSneaker.photo, F.photo)
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id

    await db.add_sneaker(
        brand=data["brand"], model=data["model"],
        size=data.get("size", ""), price=data["price"],
        description=data.get("description", ""), photo_id=photo_id,
    )

    caption = (
        f"🆕 <b>{data['brand']} {data['model']}</b>\n"
        f"📏 Размеры: {data.get('size') or '—'}\n"
        f"💰 Цена: <b>{data['price']:.0f} ₽</b>\n"
        f"📝 {data.get('description') or 'Без описания'}"
    )

    try:
        await message.bot.send_photo(
            chat_id=config.CATALOG_CHANNEL_ID,
            photo=photo_id, caption=caption, parse_mode="HTML"
        )
        await message.answer("✅ Товар добавлен и опубликован!", reply_markup=main_menu())
    except Exception as e:
        logging.exception("Ошибка публикации: %s", e)
        await message.answer(f"⚠️ Ошибка: {e}", reply_markup=main_menu())

    await state.clear()


@router.message(AddSneaker.photo)
async def add_photo_invalid(message: Message):
    await message.answer("⚠️ Нужно отправить фото.")


@router.channel_post(F.photo)
@router.message(F.photo, F.chat.id == config.SOURCE_GROUP_ID)
async def auto_from_group(message: Message):
    if message.chat.id != config.SOURCE_GROUP_ID:
        return
    caption = message.caption or ""
    parts = [p.strip() for p in caption.split("|")]
    if len(parts) < 4:
        return
    try:
        brand, model, size = parts[0], parts[1], parts[2]
        price = float(parts[3].replace(",", ".").strip())
        description = parts[4] if len(parts) > 4 else ""
    except (ValueError, IndexError):
        return

    photo_id = message.photo[-1].file_id
    await db.add_sneaker(brand=brand, model=model, size=size,
                         price=price, description=description, photo_id=photo_id)

    new_caption = (
        f"🆕 <b>{brand} {model}</b>\n"
        f"📏 Размеры: {size}\n"
        f"💰 Цена: <b>{price:.0f} ₽</b>\n"
        f"📝 {description or 'Без описания'}"
    )
    try:
        await message.bot.send_photo(
            chat_id=config.CATALOG_CHANNEL_ID,
            photo=photo_id, caption=new_caption, parse_mode="HTML"


        )
    except Exception as e:
        logging.exception("Ошибка: %s", e)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ /start — старт\n/help — справка\n/stats — статистика\n\n"
        "<b>Формат поста в группе-источнике:</b>\n"
        "<code>Бренд | Модель | Размеры | Цена | Описание</code>",
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    total = await db.count_sneakers()
    brands = await db.get_brands()
    await message.answer(
        f"📊 Товаров: <b>{total}</b>\nБрендов: <b>{len(brands)}</b>",
        parse_mode="HTML"
    )


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN не указан в .env")
    await db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🤖 Бот запущен!")
    await router.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен (Ctrl+C).")