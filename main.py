from datetime import datetime
import asyncio
from threading import Thread
import telebot
from telebot import types
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

from config import BOT_TOKEN, OWNER_ID, API_ID, API_HASH, SESSION_STRING
from ai_reply import get_ai_reply, clear_history
from keep_alive import keep_alive
from storage import save_message as store, get_message, delete_from_cache

bot = telebot.TeleBot(BOT_TOKEN)
user_client = None
if API_ID and API_HASH and SESSION_STRING:
    try:
        user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    except Exception as e:
        print(f"Userbot ulanmadi: {e}")
CHANNEL = "@umarjonovs"


# ── Yordamchi funksiyalar ────────────────────────────────────────────────────

def get_sender(message):
    u = message.from_user
    name = f"{u.first_name or ''} {u.last_name or ''}".strip()
    username = f"@{u.username}" if u.username else ""
    return f"{name} {username}".strip()

def get_chat_name(message):
    return message.chat.title or message.chat.first_name or "Private"

def extract_media(message):
    if message.photo:
        return "photo", message.photo[-1].file_id
    elif message.video:
        return "video", message.video.file_id
    elif message.audio:
        return "audio", message.audio.file_id
    elif message.voice:
        return "voice", message.voice.file_id
    elif message.document:
        return "document", message.document.file_id
    elif message.sticker:
        return "sticker", message.sticker.file_id
    elif message.video_note:
        return "video_note", message.video_note.file_id
    return None, None

def send_media_to_owner(media_type, file_id, caption):
    try:
        if media_type == "photo":
            bot.send_photo(OWNER_ID, file_id, caption=caption, parse_mode="HTML")
        elif media_type == "video":
            bot.send_video(OWNER_ID, file_id, caption=caption, parse_mode="HTML")
        elif media_type == "audio":
            bot.send_audio(OWNER_ID, file_id, caption=caption, parse_mode="HTML")
        elif media_type == "voice":
            bot.send_voice(OWNER_ID, file_id, caption=caption, parse_mode="HTML")
        elif media_type == "document":
            bot.send_document(OWNER_ID, file_id, caption=caption, parse_mode="HTML")
        elif media_type == "sticker":
            bot.send_message(OWNER_ID, caption, parse_mode="HTML")
            bot.send_sticker(OWNER_ID, file_id)
        elif media_type == "video_note":
            bot.send_video_note(OWNER_ID, file_id)
            bot.send_message(OWNER_ID, caption, parse_mode="HTML")
        else:
            bot.send_message(OWNER_ID, caption, parse_mode="HTML")
    except Exception as e:
        bot.send_message(OWNER_ID, f"{caption}\n\n⚠️ Xatolik: {e}", parse_mode="HTML")

def save_any_message(message):
    media_type, file_id = extract_media(message)
    data = {
        "text": message.text or message.caption or "",
        "from": get_sender(message),
        "date": datetime.fromtimestamp(message.date).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_title": get_chat_name(message),
        "media_type": media_type,
        "file_id": file_id,
    }
    store(message.chat.id, message.message_id, data)
    return data


# ── Obuna tekshirish ─────────────────────────────────────────────────────────

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

def check_sub(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📢 Kanalga obuna bo'lish", url="https://t.me/umarjonovs"),
            types.InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")
        )
        bot.send_message(
            message.chat.id,
            "⚠️ Botdan foydalanish uchun avval kanalga obuna bo'ling!",
            reply_markup=markup
        )
        return False
    return True


# ── /start ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def on_start(message):
    if not check_sub(message):
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Kanal", url="https://t.me/umarjonovs"),
        types.InlineKeyboardButton("🔗 Profilga ulash yo'riqnomasi", url="https://t.me/umarjonovs"),
    )

    bot.send_message(
        message.chat.id,
        f"👋 <b>Salom, {message.from_user.first_name}!</b>\n\n"
        f"🤖 Bu bot sizning Telegram profilingizga ulanib, quyidagi imkoniyatlarni beradi:\n\n"
        f"🗑 <b>O'chirilgan xabarlar</b> — kimdir xabar o'chirsa, siz ko'rasiz\n"
        f"✏️ <b>Tahrirlangan xabarlar</b> — eski va yangi versiyasini ko'rasiz\n"
        f"👁 <b>O'chib ketuvchi media</b> — bir marta ko'riladigan rasm/video saqlanadi\n"
        f"🤖 <b>AI avtomatik javob</b> — siz yo'q paytda sun'iy intellekt javob beradi\n\n"
        f"⚙️ <b>Profilga ulash tartibi:</b>\n"
        f"1️⃣ Telegram → <b>Settings</b>\n"
        f"2️⃣ <b>Telegram Business</b>\n"
        f"3️⃣ <b>Chat Automation</b>\n"
        f"4️⃣ Bot username kiriting: <code>@{bot.get_me().username}</code>\n\n"
        f"✅ Ulangach bot avtomatik ishlaydi!",
        reply_markup=markup,
        parse_mode="HTML"
    )


# ── Obuna callback ────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def on_check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Rahmat! Obuna tasdiqlandi.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        on_start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali obuna bo'lmadingiz!", show_alert=True)


# ── Oddiy xabarlar ───────────────────────────────────────────────────────────

@bot.message_handler(content_types=[
    'text', 'photo', 'video', 'audio', 'voice',
    'document', 'sticker', 'video_note'
])
def on_message(message):
    if message.text and message.text.startswith('/'):
        return
    if not check_sub(message):
        return
    save_any_message(message)


# ── Tahrirlangan xabarlar ────────────────────────────────────────────────────

@bot.edited_message_handler(content_types=[
    'text', 'photo', 'video', 'audio', 'voice', 'document'
])
def on_edited(message):
    chat_id = message.chat.id
    old = get_message(chat_id, message.message_id)

    old_text = old["text"] if old else "_(saqlanmagan)_"
    new_text = message.text or message.caption or "_(matn yo'q)_"
    time_now = datetime.now().strftime("%H:%M:%S")
    media_type, file_id = extract_media(message)

    report = (
        f"✏️ <b>Xabar tahrirlandi</b>\n"
        f"👤 <b>Kim:</b> {get_sender(message)}\n"
        f"💬 <b>Chat:</b> {get_chat_name(message)}\n"
        f"🕐 <b>Vaqt:</b> {time_now}\n\n"
        f"📌 <b>Eski matn:</b>\n{old_text}\n\n"
        f"🔄 <b>Yangi matn:</b>\n{new_text}"
    )

    if file_id:
        send_media_to_owner(media_type, file_id, report)
    else:
        bot.send_message(OWNER_ID, report, parse_mode="HTML")

    if old:
        old["text"] = new_text
        store(chat_id, message.message_id, old)


# ── Business xabarlar ────────────────────────────────────────────────────────

@bot.business_message_handler(content_types=[
    'text', 'photo', 'video', 'audio', 'voice',
    'document', 'sticker', 'video_note'
])
def on_business_message(message):
    save_any_message(message)

    if message.text:
        try:
            connection = bot.get_business_connection(message.business_connection_id)
            if connection.user.id == OWNER_ID:
                reply = get_ai_reply(message.chat.id, message.text)
                bot.send_message(
                    message.chat.id,
                    reply,
                    business_connection_id=message.business_connection_id
                )
        except Exception as e:
            print(f"Business connection xatolik: {e}")


# ── Business tahrirlangan ────────────────────────────────────────────────────

@bot.edited_business_message_handler(content_types=[
    'text', 'photo', 'video', 'audio', 'voice', 'document'
])
def on_business_edited(message):
    chat_id = message.chat.id
    old = get_message(chat_id, message.message_id)

    old_text = old["text"] if old else "_(saqlanmagan)_"
    new_text = message.text or message.caption or "_(matn yo'q)_"
    time_now = datetime.now().strftime("%H:%M:%S")
    media_type, file_id = extract_media(message)

    report = (
        f"✏️ <b>Business xabar tahrirlandi</b>\n"
        f"👤 <b>Kim:</b> {get_sender(message)}\n"
        f"🕐 <b>Vaqt:</b> {time_now}\n\n"
        f"📌 <b>Eski matn:</b>\n{old_text}\n\n"
        f"🔄 <b>Yangi matn:</b>\n{new_text}"
    )

    if file_id:
        send_media_to_owner(media_type, file_id, report)
    else:
        bot.send_message(OWNER_ID, report, parse_mode="HTML")

    if old:
        old["text"] = new_text
        store(chat_id, message.message_id, old)


# ── Business o'chirilgan ─────────────────────────────────────────────────────

@bot.deleted_business_messages_handler()
def on_business_deleted(update):
    time_now = datetime.now().strftime("%H:%M:%S")

    for msg_id in update.message_ids:
        old = delete_from_cache(update.chat.id, msg_id)
        if not old:
            continue

        report = (
            f"🗑 <b>Xabar o'chirildi</b>\n"
            f"👤 <b>Kim:</b> {old['from']}\n"
            f"💬 <b>Chat:</b> {old.get('chat_title', '?')}\n"
            f"📅 <b>Yuborilgan:</b> {old['date']}\n"
            f"🕐 <b>O'chirilgan:</b> {time_now}\n\n"
        )
        if old["text"]:
            report += f"📝 <b>Matn:</b>\n{old['text']}"

        if old.get("file_id") and old.get("media_type") != "sticker":
            send_media_to_owner(old["media_type"], old["file_id"], report)
        elif old.get("file_id") and old.get("media_type") == "sticker":
            bot.send_message(OWNER_ID, report, parse_mode="HTML")
            bot.send_sticker(OWNER_ID, old["file_id"])
        else:
            bot.send_message(OWNER_ID, report, parse_mode="HTML")


# ── /reset ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['reset'])
def on_reset(message):
    clear_history(message.chat.id)
    bot.reply_to(message, "✅ Suhbat tarixi tozalandi.")


# ── Telethon — o'chib ketuvchi media ────────────────────────────────────────

async def start_userbot():
    await user_client.start()
    print("✅ Userbot ulandi!")

    @user_client.on(events.NewMessage(incoming=True))
    async def on_user_message(event):
        msg = event.message

        # O'chib ketuvchi media tekshirish
        if not msg.media:
            return

        ttl = getattr(msg.media, 'ttl_seconds', None)
        if not ttl:
            return

        # Mediani yuklab olish
        try:
            sender = await event.get_sender()
            chat = await event.get_chat()

            sender_name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
            username = f"@{sender.username}" if getattr(sender, 'username', None) else ""
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Private"
            time_now = datetime.now().strftime("%H:%M:%S")

            caption = (
                f"👁 <b>O'chib ketuvchi media!</b>\n"
                f"👤 <b>Kim:</b> {sender_name} {username}\n"
                f"💬 <b>Chat:</b> {chat_title}\n"
                f"🕐 <b>Vaqt:</b> {time_now}"
            )

            media_bytes = await user_client.download_media(msg.media, bytes)

            if isinstance(msg.media, MessageMediaPhoto):
                bot.send_photo(OWNER_ID, media_bytes, caption=caption, parse_mode="HTML")
            else:
                bot.send_document(OWNER_ID, media_bytes, caption=caption, parse_mode="HTML")

        except Exception as e:
            bot.send_message(OWNER_ID, f"👁 O'chib ketuvchi media keldi, yuklab bo'lmadi: {e}")

    await user_client.run_until_disconnected()


def run_userbot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_userbot())


# ── Start ────────────────────────────────────────────────────────────────────

def main():
    keep_alive()

    # Userbot alohida threadda
    t = Thread(target=run_userbot)
    def run_userbot():
    if not user_client:
        print("Userbot o'chirilgan — SESSION_STRING yo'q")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_userbot())


if __name__ == "__main__":
    main()
