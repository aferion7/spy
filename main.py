import asyncio
from threading import Thread
from datetime import datetime

import telebot
from telebot import types

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SESSION_STRING
from ai_reply import get_ai_reply, clear_history
from keep_alive import keep_alive

bot = telebot.TeleBot(BOT_TOKEN)

# ── O'chirilgan xabarlarni ushlash ──────────────────────────────────────────

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'voice'])
def save_message(message):
    """Barcha xabarlarni xotirada saqlash"""
    from storage import save_message as store
    data = {
        "text": message.text or message.caption or "",
        "from": f"{message.from_user.first_name or ''} @{message.from_user.username or ''}".strip(),
        "date": datetime.fromtimestamp(message.date).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_title": message.chat.title or message.chat.first_name or "Private",
        "media": None,
        "media_type": None,
    }
    store(message.chat.id, message.message_id, data)

    # AI javob — faqat private chat
    if message.chat.type == "private" and message.text:
        reply = get_ai_reply(message.chat.id, message.text)
        bot.send_message(message.chat.id, reply)


# ── Tahrirlangan xabarlar ────────────────────────────────────────────────────

@bot.edited_message_handler(content_types=['text', 'photo', 'video', 'document'])
def on_edited(message):
    from storage import get_message, save_message as store
    chat_id = message.chat.id
    old = get_message(chat_id, message.message_id)

    old_text = old["text"] if old else "_(saqlanmagan)_"
    new_text = message.text or message.caption or "_(matn yo'q)_"
    time_now = datetime.now().strftime("%H:%M:%S")
    sender = f"{message.from_user.first_name or ''} @{message.from_user.username or ''}".strip()
    chat_title = message.chat.title or message.chat.first_name or "Private"

    report = (
        f"✏️ <b>Xabar tahrirlandi</b>\n"
        f"👤 <b>Kim:</b> {sender}\n"
        f"💬 <b>Chat:</b> {chat_title}\n"
        f"🕐 <b>Vaqt:</b> {time_now}\n\n"
        f"📌 <b>Eski matn:</b>\n{old_text}\n\n"
        f"🔄 <b>Yangi matn:</b>\n{new_text}"
    )
    bot.send_message(OWNER_ID, report, parse_mode="HTML")

    if old:
        old["text"] = new_text
        store(chat_id, message.message_id, old)


# ── Secretary Mode — business xabarlar ──────────────────────────────────────

@bot.business_message_handler(content_types=['text'])
def on_business_message(message):
    from storage import save_message as store
    data = {
        "text": message.text or "",
        "from": f"{message.from_user.first_name or ''} @{message.from_user.username or ''}".strip(),
        "date": datetime.fromtimestamp(message.date).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_title": message.chat.title or message.chat.first_name or "Private",
        "media": None,
        "media_type": None,
    }
    store(message.chat.id, message.message_id, data)

    # AI javob
    reply = get_ai_reply(message.chat.id, message.text)
    bot.send_message(
        message.chat.id,
        reply,
        business_connection_id=message.business_connection_id
    )


@bot.edited_business_message_handler(content_types=['text'])
def on_business_edited(message):
    from storage import get_message, save_message as store
    chat_id = message.chat.id
    old = get_message(chat_id, message.message_id)

    old_text = old["text"] if old else "_(saqlanmagan)_"
    new_text = message.text or "_(matn yo'q)_"
    time_now = datetime.now().strftime("%H:%M:%S")
    sender = f"{message.from_user.first_name or ''} @{message.from_user.username or ''}".strip()

    report = (
        f"✏️ <b>Business xabar tahrirlandi</b>\n"
        f"👤 <b>Kim:</b> {sender}\n"
        f"🕐 <b>Vaqt:</b> {time_now}\n\n"
        f"📌 <b>Eski matn:</b>\n{old_text}\n\n"
        f"🔄 <b>Yangi matn:</b>\n{new_text}"
    )
    bot.send_message(OWNER_ID, report, parse_mode="HTML")

    if old:
        old["text"] = new_text
        store(chat_id, message.message_id, old)


@bot.deleted_business_messages_handler()
def on_business_deleted(update):
    from storage import delete_from_cache
    time_now = datetime.now().strftime("%H:%M:%S")

    for msg_id in update.message_ids:
        old = delete_from_cache(update.chat.id, msg_id)
        if not old:
            continue

        report = (
            f"🗑 <b>Business xabar o'chirildi</b>\n"
            f"👤 <b>Kim:</b> {old['from']}\n"
            f"💬 <b>Chat:</b> {old.get('chat_title', '?')}\n"
            f"📅 <b>Yuborilgan:</b> {old['date']}\n"
            f"🕐 <b>O'chirilgan:</b> {time_now}\n\n"
        )
        if old["text"]:
            report += f"📝 <b>Matn:</b>\n{old['text']}"

        bot.send_message(OWNER_ID, report, parse_mode="HTML")


# ── /reset komandasi ─────────────────────────────────────────────────────────

@bot.message_handler(commands=['reset'])
def on_reset(message):
    clear_history(message.chat.id)
    bot.reply_to(message, "✅ Suhbat tarixi tozalandi.")


# ── Start ────────────────────────────────────────────────────────────────────

def start_polling():
    bot.infinity_polling()

def main():
    keep_alive()
    bot.send_message(OWNER_ID, "✅ <b>Spy bot ishga tushdi!</b>", parse_mode="HTML")
    print("✅ Bot ishga tushdi!")
    start_polling()


if __name__ == "__main__":
    main()
