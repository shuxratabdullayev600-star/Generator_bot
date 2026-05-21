"""
license_bot.py  —  Telegram Bot версия генератора лицензий
===========================================================
Запускается на ПК, управляется с телефона через Telegram.

Установка:
    pip install python-telegram-bot

Запуск:
    python license_bot.py
"""

import json
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# ══════════════════════════════════════════════════════════════
#  НАСТРОЙКИ — ЗАПОЛНИ ПЕРЕД ЗАПУСКОМ
# ══════════════════════════════════════════════════════════════

BOT_TOKEN   = "8893688202:AAH8z_F95xED8RRqE9qqUKXfHWYcq7Nq76s"   # получить у @BotFather
ALLOWED_IDS = [5419292269]                   # список Telegram ID кто может пользоваться
                                   # оставь пустым [] чтобы разрешить всем
                                   # пример: [123456789, 987654321]

# ══════════════════════════════════════════════════════════════
#  ЛОГИКА (не изменена из оригинала)
# ══════════════════════════════════════════════════════════════

_XOR_KEY = 73

def _encrypt(data: dict) -> bytes:
    s = json.dumps(data, ensure_ascii=False)
    return bytes([b ^ _XOR_KEY for b in s.encode("utf-8")])

def create_license(hwid: str, owner: str, days: int) -> tuple[bytes, str]:
    """Возвращает (байты файла, дата истечения)."""
    expiry = datetime.now() + timedelta(days=days)
    data = {
        "hwid":   hwid.strip().upper(),
        "owner":  owner.strip(),
        "expiry": expiry.strftime("%Y-%m-%d"),
    }
    return _encrypt(data), expiry.strftime("%d.%m.%Y")

PLANS = {
    "7 kun — sinov":        7,
    "30 kun — standart":   30,
    "90 kun — chorak":     90,
    "180 kun — yarim yil": 180,
    "365 kun — bir yil":   365,
    "730 kun — ikki yil":  730,
}

# ══════════════════════════════════════════════════════════════
#  СОСТОЯНИЯ ДИАЛОГА
# ══════════════════════════════════════════════════════════════

ASK_HWID, ASK_OWNER, ASK_PLAN, ASK_DAYS = range(4)

# ── Логирование ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
#  ПРОВЕРКА ДОСТУПА
# ══════════════════════════════════════════════════════════════

def is_allowed(user_id: int) -> bool:
    if not ALLOWED_IDS:
        return True
    return user_id in ALLOWED_IDS

# ══════════════════════════════════════════════════════════════
#  ХЕНДЛЕРЫ
# ══════════════════════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Sizda ruxsat yo'q.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔐 *Litsenziya Generator*\n\n"
        "Yangi litsenziya yaratish uchun /new buyrug'ini yuboring.\n"
        "Yordam uchun /help.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Buyruqlar:*\n\n"
        "/new — yangi litsenziya yaratish\n"
        "/cancel — bekor qilish\n"
        "/start — boshlash\n\n"
        "Jarayon:\n"
        "1. PC ID kiriting\n"
        "2. Tashkilot nomini kiriting\n"
        "3. Muddatni tanlang\n"
        "4. license.dat faylini oling",
        parse_mode="Markdown"
    )

async def new_license(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Sizda ruxsat yo'q.")
        return ConversationHandler.END

    await update.message.reply_text(
        "💻 *1-qadam: PC ID*\n\n"
        "Mijozning PC ID sini yuboring:\n"
        "_(masalan: A93C0CBAC446)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_HWID

async def got_hwid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    hwid = update.message.text.strip()
    if len(hwid) < 4:
        await update.message.reply_text(
            "PC ID juda qisqa. Qaytadan kiriting:")
        return ASK_HWID

    ctx.user_data["hwid"] = hwid.upper()

    await update.message.reply_text(
        f"✅ PC ID qabul qilindi: `{hwid.upper()}`\n\n"
        "🏢 *2-qadam: Tashkilot*\n\n"
        "Tashkilot yoki mijoz nomini yuboring:",
        parse_mode="Markdown"
    )
    return ASK_OWNER

async def got_owner(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    owner = update.message.text.strip()
    if not owner:
        await update.message.reply_text("Nom bo'sh bo'lmasin. Qaytadan:")
        return ASK_OWNER

    ctx.user_data["owner"] = owner

    # Клавиатура с тарифами
    keyboard = [[plan] for plan in PLANS.keys()]
    keyboard.append(["✏️ O'zim kiritaman"])

    await update.message.reply_text(
        f"✅ Tashkilot: *{owner}*\n\n"
        "📅 *3-qadam: Muddat*\n\n"
        "Tezkor tarifni tanlang yoki o'zingiz kiriting:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                          one_time_keyboard=True)
    )
    return ASK_PLAN

async def got_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "✏️ O'zim kiritaman":
        await update.message.reply_text(
            "Kunlar sonini kiriting (masalan: 180):",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_DAYS

    if text in PLANS:
        days = PLANS[text]
        ctx.user_data["days"] = days
        return await _generate(update, ctx)

    await update.message.reply_text("Iltimos, ro'yxatdan tanlang:")
    return ASK_PLAN

async def got_days(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Noto'g'ri son. Musbat son kiriting (masalan: 90):")
        return ASK_DAYS

    ctx.user_data["days"] = days
    return await _generate(update, ctx)

async def _generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Создаёт license.dat и отправляет файл."""
    hwid  = ctx.user_data["hwid"]
    owner = ctx.user_data["owner"]
    days  = ctx.user_data["days"]

    try:
        file_bytes, expiry = create_license(hwid, owner, days)

        # Сохраняем во временный файл
        tmp_path = f"license_{hwid[:8]}.dat"
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)

        caption = (
            f"✅ *Litsenziya yaratildi!*\n\n"
            f"🖥 PC ID:       `{hwid}`\n"
            f"🏢 Tashkilot:  {owner}\n"
            f"📅 Muddat:     {days} kun\n"
            f"⏳ Tugash:     {expiry}\n\n"
            f"📎 Faylni dastur papkasiga soling."
        )

        with open(tmp_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="license.dat",
                caption=caption,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

        # Удаляем временный файл
        os.remove(tmp_path)

        logger.info(f"Litsenziya yaratildi: {hwid} / {owner} / {days} kun")

    except Exception as e:
        await update.message.reply_text(
            f"Xato yuz berdi: {e}",
            reply_markup=ReplyKeyboardRemove()
        )

    ctx.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "Bekor qilindi.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Noma'lum buyruq. /help ga qarang.")

# ══════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════

def main():
    if BOT_TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("=" * 50)
        print("XATO: BOT_TOKEN ni to'ldiring!")
        print("@BotFather dan token oling va")
        print("license_bot.py faylida BOT_TOKEN ga yozing.")
        print("=" * 50)
        return

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_license)],
        states={
            ASK_HWID:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_hwid)],
            ASK_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_owner)],
            ASK_PLAN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_plan)],
            ASK_DAYS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_cmd))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("=" * 50)
    print("Bot ishga tushdi!")
    print("Telegramda /start yuboring.")
    print("To'xtatish uchun: Ctrl+C")
    print("=" * 50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
