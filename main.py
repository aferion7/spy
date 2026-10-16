import os
import re
from datetime import datetime
from threading import Thread
from dotenv import load_dotenv

from flask import Flask
from telethon import TelegramClient, events
from telethon.tl.functions.stories import (
    GetPeerStoriesRequest,
    GetPinnedStoriesRequest,
    GetStoriesArchiveRequest,
    GetStoriesByIDRequest
)
from telethon.tl import types

# ====================== SOZLAMALAR ======================
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")          # ixtiyoriy (faqat bot sifatida ishlatmoqchi bo‘lsangiz)
OWNER_ID = int(os.getenv("OWNER_ID"))

# Session nomi (spy_session.session fayli bo‘ladi)
SESSION_NAME = "spy_session"

# Yuklab olish papkalari
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/stories", exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/disappearing", exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/private", exist_ok=True)

# ====================== FLASK KEEP-ALIVE ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ====================== MESSAGE CACHE (sizdagi kod) ======================
message_cache = {}

def save_message(chat_id, msg_id, data):
    message_cache[(chat_id, msg_id)] = data

def get_message(chat_id, msg_id):
    return message_cache.get((chat_id, msg_id))

def delete_from_cache(chat_id, msg_id):
    return message_cache.pop((chat_id, msg_id), None)

# ====================== TELETHON CLIENT ======================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ====================== YORDAMCHI FUNKSIYALAR ======================

async def download_user_stories(peer, include_archive=False, include_pinned=True):
    """Foydalanuvchi/kanal hikoyalarini yuklab olish"""
    try:
        entity = await client.get_entity(peer)
        username = getattr(entity, "username", None) or str(entity.id)
        folder = f"{DOWNLOAD_DIR}/stories/{username}"
        os.makedirs(folder, exist_ok=True)

        stories_list = []

        # Aktiv hikoyalar
        result = await client(GetPeerStoriesRequest(peer=entity))
        if result.stories and result.stories.stories:
            stories_list.extend(result.stories.stories)

        # Pinned hikoyalar
        if include_pinned:
            try:
                pinned = await client(GetPinnedStoriesRequest(peer=entity, offset_id=0, limit=100))
                if pinned.stories:
                    stories_list.extend(pinned.stories)
            except Exception:
                pass

        # Arxiv
        if include_archive:
            offset = 0
            while True:
                try:
                    archive = await client(GetStoriesArchiveRequest(
                        peer=entity, offset_id=offset, limit=100
                    ))
                    if not archive.stories:
                        break
                    stories_list.extend(archive.stories)
                    offset = archive.stories[-1].id
                except Exception:
                    break

        downloaded = 0
        for story in stories_list:
            if not getattr(story, "media", None):
                continue
            story_id = story.id
            file_path = f"{folder}/story_{story_id}"
            path = await client.download_media(story.media, file=file_path)
            if path:
                downloaded += 1
                print(f"[STORY] Yuklandi: {path}")

        return downloaded
    except Exception as e:
        print(f"[STORY ERROR] {e}")
        return 0


async def download_story_by_link(link: str):
    """https://t.me/username/s/123 formatidagi linkni yuklab olish"""
    match = re.search(r"t\.me/(?:c/)?([\w\d_+-]+)/s/(\d+)", link)
    if not match:
        return None

    username_or_id, story_id = match.groups()
    story_id = int(story_id)

    try:
        if username_or_id.isdigit():
            peer = int(f"-100{username_or_id}") if len(username_or_id) > 10 else int(username_or_id)
        else:
            peer = username_or_id

        result = await client(GetStoriesByIDRequest(peer=peer, id=[story_id]))
        if result.stories:
            story = result.stories[0]
            path = await client.download_media(
                story.media,
                file=f"{DOWNLOAD_DIR}/stories/story_{story_id}"
            )
            return path
    except Exception as e:
        print(f"[STORY LINK ERROR] {e}")
    return None


async def download_private_post(link: str):
    """
    Maxfiy yoki ochiq kanal postini link orqali yuklab olish
    Qo‘llab-quvvatlanadigan formatlar:
    - https://t.me/c/1234567890/42
    - https://t.me/username/42
    """
    match_private = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    match_public = re.search(r"t\.me/([\w\d_]+)/(\d+)", link)

    try:
        if match_private:
            channel_id = int(f"-100{match_private.group(1)}")
            msg_id = int(match_private.group(2))
            entity = channel_id
        elif match_public:
            username = match_public.group(1)
            msg_id = int(match_public.group(2))
            entity = await client.get_entity(username)
        else:
            return None

        message = await client.get_messages(entity, ids=msg_id)
        if not message or not message.media:
            return None

        path = await client.download_media(message, file=f"{DOWNLOAD_DIR}/private/")
        if path:
            await client.send_file(
                "me",
                path,
                caption=f"📥 Maxfiy/ochiq post yuklandi\n🔗 Link: {link}"
            )
        return path
    except Exception as e:
        print(f"[PRIVATE POST ERROR] {e}")
        return None


# ====================== EVENT HANDLERLAR ======================

# 1. O‘chib ketuvchi (View Once / TTL) medialarni avtomatik saqlash
@client.on(events.NewMessage(incoming=True))
async def save_disappearing_media(event):
    message = event.message
    if not message.media:
        return

    ttl = getattr(message.media, "ttl_seconds", None)

    # View-once yoki TTL li media
    if ttl is None and not isinstance(message.media, types.MessageMediaUnsupported):
        return

    try:
        sender = await event.get_sender()
        chat = await event.get_chat()

        sender_name = getattr(sender, "first_name", "") or getattr(sender, "title", "Unknown")
        chat_title = getattr(chat, "title", None) or getattr(chat, "username", str(chat.id))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{DOWNLOAD_DIR}/disappearing/{chat_title}_{sender_name}_{timestamp}"

        path = await client.download_media(message, file=filename)
        if path:
            caption = (
                f"🔒 O‘chib ketuvchi media saqlandi!\n"
                f"Chat: {chat_title}\n"
                f"Yuboruvchi: {sender_name}\n"
                f"TTL: {ttl} soniya\n"
                f"Vaqt: {timestamp}"
            )
            await client.send_file("me", path, caption=caption)
            print(f"[DISAPPEARING] Saqlandi: {path}")
    except Exception as e:
        print(f"[DISAPPEARING ERROR] {e}")


# 2. /story buyrug‘i — foydalanuvchi hikoyalarini yuklash
@client.on(events.NewMessage(pattern=r'^/story(?:\s+(.+))?$'))
async def cmd_story(event):
    if event.sender_id != OWNER_ID:
        return

    arg = event.pattern_match.group(1)
    if not arg:
        await event.reply("Ishlatish: `/story username` yoki `/story https://t.me/user/s/123`")
        return

    await event.reply("⏳ Hikoyalar yuklanmoqda...")

    # Agar to‘liq link bo‘lsa
    if "/s/" in arg:
        path = await download_story_by_link(arg.strip())
        if path:
            await event.reply(f"✅ Hikoya yuklandi:\n`{path}`")
        else:
            await event.reply("❌ Hikoyani yuklab bo‘lmadi.")
    else:
        count = await download_user_stories(arg.strip())
        await event.reply(f"✅ {count} ta hikoya yuklandi.")


# 3. /get buyrug‘i — maxfiy/ochiq postni link orqali yuklash
@client.on(events.NewMessage(pattern=r'^/get(?:\s+(.+))?$'))
async def cmd_get_post(event):
    if event.sender_id != OWNER_ID:
        return

    link = event.pattern_match.group(1)
    if not link:
        await event.reply("Ishlatish: `/get https://t.me/c/1234567890/42`")
        return

    await event.reply("⏳ Post yuklanmoqda...")
    path = await download_private_post(link.strip())
    if path:
        await event.reply(f"✅ Yuklandi:\n`{path}`")
    else:
        await event.reply("❌ Yuklab bo‘lmadi.\nSiz shu kanal a’zosi ekanligingizni tekshiring.")


# 4. /start buyrug‘i
@client.on(events.NewMessage(pattern=r'^/start$'))
async def cmd_start(event):
    if event.sender_id != OWNER_ID:
        return
    text = (
        "🤖 **Spy Bot ishga tushdi!**\n\n"
        "Buyruqlar:\n"
        "• `/story username` — hikoyalarni yuklash\n"
        "• `/story https://t.me/user/s/123` — bitta hikoyani yuklash\n"
        "• `/get https://t.me/c/.../42` — maxfiy postni yuklash\n\n"
        "O‘chib ketuvchi rasmlar avtomatik Saved Messages ga saqlanadi."
    )
    await event.reply(text)


# ====================== ISHGA TUSHIRISH ======================
if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    keep_alive()
    client.start()
    print("Bot ishlayapti!")
   client.run_until_disconnected()
import os
import re
from datetime import datetime
from threading import Thread
from dotenv import load_dotenv

from flask import Flask
from telethon import TelegramClient, events
from telethon.tl.functions.stories import (
    GetPeerStoriesRequest,
    GetPinnedStoriesRequest,
    GetStoriesArchiveRequest,
    GetStoriesByIDRequest
)
from telethon.tl import types

# ====================== SOZLAMALAR ======================
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")          # ixtiyoriy (faqat bot sifatida ishlatmoqchi bo‘lsangiz)
OWNER_ID = int(os.getenv("OWNER_ID"))

# Session nomi (spy_session.session fayli bo‘ladi)
SESSION_NAME = "spy_session"

# Yuklab olish papkalari
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/stories", exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/disappearing", exist_ok=True)
os.makedirs(f"{DOWNLOAD_DIR}/private", exist_ok=True)

# ====================== FLASK KEEP-ALIVE ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ====================== MESSAGE CACHE (sizdagi kod) ======================
message_cache = {}

def save_message(chat_id, msg_id, data):
    message_cache[(chat_id, msg_id)] = data

def get_message(chat_id, msg_id):
    return message_cache.get((chat_id, msg_id))

def delete_from_cache(chat_id, msg_id):
    return message_cache.pop((chat_id, msg_id), None)

# ====================== TELETHON CLIENT ======================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ====================== YORDAMCHI FUNKSIYALAR ======================

async def download_user_stories(peer, include_archive=False, include_pinned=True):
    """Foydalanuvchi/kanal hikoyalarini yuklab olish"""
    try:
        entity = await client.get_entity(peer)
        username = getattr(entity, "username", None) or str(entity.id)
        folder = f"{DOWNLOAD_DIR}/stories/{username}"
        os.makedirs(folder, exist_ok=True)

        stories_list = []

        # Aktiv hikoyalar
        result = await client(GetPeerStoriesRequest(peer=entity))
        if result.stories and result.stories.stories:
            stories_list.extend(result.stories.stories)

        # Pinned hikoyalar
        if include_pinned:
            try:
                pinned = await client(GetPinnedStoriesRequest(peer=entity, offset_id=0, limit=100))
                if pinned.stories:
                    stories_list.extend(pinned.stories)
            except Exception:
                pass

        # Arxiv
        if include_archive:
            offset = 0
            while True:
                try:
                    archive = await client(GetStoriesArchiveRequest(
                        peer=entity, offset_id=offset, limit=100
                    ))
                    if not archive.stories:
                        break
                    stories_list.extend(archive.stories)
                    offset = archive.stories[-1].id
                except Exception:
                    break

        downloaded = 0
        for story in stories_list:
            if not getattr(story, "media", None):
                continue
            story_id = story.id
            file_path = f"{folder}/story_{story_id}"
            path = await client.download_media(story.media, file=file_path)
            if path:
                downloaded += 1
                print(f"[STORY] Yuklandi: {path}")

        return downloaded
    except Exception as e:
        print(f"[STORY ERROR] {e}")
        return 0


async def download_story_by_link(link: str):
    """https://t.me/username/s/123 formatidagi linkni yuklab olish"""
    match = re.search(r"t\.me/(?:c/)?([\w\d_+-]+)/s/(\d+)", link)
    if not match:
        return None

    username_or_id, story_id = match.groups()
    story_id = int(story_id)

    try:
        if username_or_id.isdigit():
            peer = int(f"-100{username_or_id}") if len(username_or_id) > 10 else int(username_or_id)
        else:
            peer = username_or_id

        result = await client(GetStoriesByIDRequest(peer=peer, id=[story_id]))
        if result.stories:
            story = result.stories[0]
            path = await client.download_media(
                story.media,
                file=f"{DOWNLOAD_DIR}/stories/story_{story_id}"
            )
            return path
    except Exception as e:
        print(f"[STORY LINK ERROR] {e}")
    return None


async def download_private_post(link: str):
    """
    Maxfiy yoki ochiq kanal postini link orqali yuklab olish
    Qo‘llab-quvvatlanadigan formatlar:
    - https://t.me/c/1234567890/42
    - https://t.me/username/42
    """
    match_private = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    match_public = re.search(r"t\.me/([\w\d_]+)/(\d+)", link)

    try:
        if match_private:
            channel_id = int(f"-100{match_private.group(1)}")
            msg_id = int(match_private.group(2))
            entity = channel_id
        elif match_public:
            username = match_public.group(1)
            msg_id = int(match_public.group(2))
            entity = await client.get_entity(username)
        else:
            return None

        message = await client.get_messages(entity, ids=msg_id)
        if not message or not message.media:
            return None

        path = await client.download_media(message, file=f"{DOWNLOAD_DIR}/private/")
        if path:
            await client.send_file(
                "me",
                path,
                caption=f"📥 Maxfiy/ochiq post yuklandi\n🔗 Link: {link}"
            )
        return path
    except Exception as e:
        print(f"[PRIVATE POST ERROR] {e}")
        return None


# ====================== EVENT HANDLERLAR ======================

# 1. O‘chib ketuvchi (View Once / TTL) medialarni avtomatik saqlash
@client.on(events.NewMessage(incoming=True))
async def save_disappearing_media(event):
    message = event.message
    if not message.media:
        return

    ttl = getattr(message.media, "ttl_seconds", None)

    # View-once yoki TTL li media
    if ttl is None and not isinstance(message.media, types.MessageMediaUnsupported):
        return

    try:
        sender = await event.get_sender()
        chat = await event.get_chat()

        sender_name = getattr(sender, "first_name", "") or getattr(sender, "title", "Unknown")
        chat_title = getattr(chat, "title", None) or getattr(chat, "username", str(chat.id))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{DOWNLOAD_DIR}/disappearing/{chat_title}_{sender_name}_{timestamp}"

        path = await client.download_media(message, file=filename)
        if path:
            caption = (
                f"🔒 O‘chib ketuvchi media saqlandi!\n"
                f"Chat: {chat_title}\n"
                f"Yuboruvchi: {sender_name}\n"
                f"TTL: {ttl} soniya\n"
                f"Vaqt: {timestamp}"
            )
            await client.send_file("me", path, caption=caption)
            print(f"[DISAPPEARING] Saqlandi: {path}")
    except Exception as e:
        print(f"[DISAPPEARING ERROR] {e}")


# 2. /story buyrug‘i — foydalanuvchi hikoyalarini yuklash
@client.on(events.NewMessage(pattern=r'^/story(?:\s+(.+))?$'))
async def cmd_story(event):
    if event.sender_id != OWNER_ID:
        return

    arg = event.pattern_match.group(1)
    if not arg:
        await event.reply("Ishlatish: `/story username` yoki `/story https://t.me/user/s/123`")
        return

    await event.reply("⏳ Hikoyalar yuklanmoqda...")

    # Agar to‘liq link bo‘lsa
    if "/s/" in arg:
        path = await download_story_by_link(arg.strip())
        if path:
            await event.reply(f"✅ Hikoya yuklandi:\n`{path}`")
        else:
            await event.reply("❌ Hikoyani yuklab bo‘lmadi.")
    else:
        count = await download_user_stories(arg.strip())
        await event.reply(f"✅ {count} ta hikoya yuklandi.")


# 3. /get buyrug‘i — maxfiy/ochiq postni link orqali yuklash
@client.on(events.NewMessage(pattern=r'^/get(?:\s+(.+))?$'))
async def cmd_get_post(event):
    if event.sender_id != OWNER_ID:
        return

    link = event.pattern_match.group(1)
    if not link:
        await event.reply("Ishlatish: `/get https://t.me/c/1234567890/42`")
        return

    await event.reply("⏳ Post yuklanmoqda...")
    path = await download_private_post(link.strip())
    if path:
        await event.reply(f"✅ Yuklandi:\n`{path}`")
    else:
        await event.reply("❌ Yuklab bo‘lmadi.\nSiz shu kanal a’zosi ekanligingizni tekshiring.")


# 4. /start buyrug‘i
@client.on(events.NewMessage(pattern=r'^/start$'))
async def cmd_start(event):
    if event.sender_id != OWNER_ID:
        return
    text = (
        "🤖 **Spy Bot ishga tushdi!**\n\n"
        "Buyruqlar:\n"
        "• `/story username` — hikoyalarni yuklash\n"
        "• `/story https://t.me/user/s/123` — bitta hikoyani yuklash\n"
        "• `/get https://t.me/c/.../42` — maxfiy postni yuklash\n\n"
        "O‘chib ketuvchi rasmlar avtomatik Saved Messages ga saqlanadi."
    )
    await event.reply(text)


# ====================== ISHGA TUSHIRISH ======================
if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    keep_alive()
    client.start()
    print("Bot ishlayapti!")
    client.run_until_disconnected()
