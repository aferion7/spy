import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, User
import telebot
from datetime import datetime

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SESSION_NAME
from storage import save_message, get_message, delete_from_cache
from ai_reply import get_ai_reply, clear_history
from keep_alive import keep_alive

bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
MY_ID = None


def format_sender(msg):
    if msg.sender:
        s = msg.sender
        name = f"{getattr(s, 'first_name', '') or ''} {getattr(s, 'last_name', '') or ''}".strip()
        username = f"@{s.username}" if getattr(s, 'username', None) else ""
        return f"{name} {username}".strip()
    return "Noma'lum"


def get_chat_title(chat):
    if hasattr(chat, 'title'):
        return chat.title
    elif hasattr(chat, 'first_name'):
        return f"{chat.first_name or ''} {chat.last_name or ''}".strip()
    return "Noma'lum chat"


# ── Yangi xabarlarni saqlash va AI javob ────────────────────────────────────

@client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    global MY_ID
    msg = event.message
    chat_id = event.chat_id
    chat = await event.get_chat()

    # Cachega saqlash
    data = {
        "text": msg.text or "",
        "from": format_sender(msg),
        "date": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
        "has_media": msg.media is not None,
        "media": None,
        "chat_title": get_chat_title(chat),
    }

    if msg.media:
        try:
            media_bytes = await client.download_media(msg.media, bytes)
            data["media"] = media_bytes
            data["media_type"] = (
                "photo" if isinstance(msg.media, MessageMediaPhoto) else "document"
            )
        except Exception:
            data["media_type"] = "unknown"

    save_message(chat_id, msg.id, data)

    # AI javob — faqat private chat, o'ziga emas
    is_private = isinstance(chat, User)
    is_not_me = chat_id != MY_ID
    has_text = bool(msg.text and msg.text.strip())

    if is_private and is_not_me and has_text:
        async with client.action(chat_id, "typing"):
            reply_text = get_ai_reply(chat_id, msg.text)
        await client.send_message(chat_id, reply_text)


# ── /reset komandasi ─────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern="/reset", incoming=True))
async def on_reset(event):
    if isinstance(await event.get_chat(), User):
        clear_history(event.chat_id)
        await event.reply("✅ Suhbat tarixi tozalandi.")


# ── Tahrirlangan xabarlar ────────────────────────────────────────────────────

@client.on(events.MessageEdited)
async def on_edited(event):
    msg = event.message
    chat_id = event.chat_id
    old = get_message(chat_id, msg.id)

    old_text = old["text"] if old else "_(saqlanmagan)_"
    new_text = msg.text or "_(matn yo'q)_"
    sender = format_sender(msg)
    chat_title = get_chat_title(await event.get_chat())
    time_now = datetime.now().strftime("%H:%M:%S")

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
        save_message(chat_id, msg.id, old)


# ── O'chirilgan xabarlar ─────────────────────────────────────────────────────

@client.on(events.MessageDeleted)
async def on_deleted(event):
    chat_id = event.chat_id
    time_now = datetime.now().strftime("%H:%M:%S")

    for msg_id in event.deleted_ids:
        old = delete_from_cache(chat_id, msg_id)
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

        if old.get("media"):
            try:
                if old.get("media_type") == "photo":
                    bot.send_photo(OWNER_ID, old["media"], caption=report, parse_mode="HTML")
                else:
                    bot.send_document(OWNER_ID, old["media"], caption=report, parse_mode="HTML")
                continue
            except Exception:
                pass

        bot.send_message(OWNER_ID, report, parse_mode="HTML")


# ── Start ────────────────────────────────────────────────────────────────────

async def main():
    global MY_ID
    keep_alive()
    await client.start()
    me = await client.get_me()
    MY_ID = me.id
    print(f"✅ Bot ishga tushdi! ID: {MY_ID}")
    bot.send_message(OWNER_ID, "✅ <b>Spy bot ishga tushdi!</b>", parse_mode="HTML")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
