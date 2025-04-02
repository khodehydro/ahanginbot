import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto
from aiogram.utils import executor
from flask import Flask
from threading import Thread

TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_1 = "@YourChannel1"  # آیدی کانال اول
CHANNEL_2 = "@YourChannel2"  # آیدی کانال دوم

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
conn = sqlite3.connect("playlists.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    name TEXT,
    cover TEXT,
    description TEXT,
    UNIQUE(channel_id, name)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS playlist_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    playlist_name TEXT,
    file_id TEXT,
    FOREIGN KEY (channel_id, playlist_name) REFERENCES playlists(channel_id, name)
)
""")
conn.commit()

async def is_user_member(user_id):
    try:
        chat_member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        chat_member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        return chat_member1.status in ["member", "administrator", "creator"] and chat_member2.status in ["member", "administrator", "creator"]
    except Exception:
        return False

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    if not await is_user_member(message.from_user.id):
        await message.reply(f"❌ برای استفاده از ربات، ابتدا در دو کانال زیر عضو شوید:\n1️⃣ {CHANNEL_1}\n2️⃣ {CHANNEL_2}")
        return
    await message.reply("✅ خوش آمدید! می‌توانید از ربات استفاده کنید.")

@dp.message_handler(commands=["newplaylist"])
async def create_playlist(message: types.Message):
    if not await is_user_member(message.from_user.id):
        await message.reply("❌ لطفاً ابتدا در کانال‌ها عضو شوید.")
        return
    name = message.get_args()
    channel_id = message.chat.id
    if not name:
        await message.reply("نام پلی‌لیست را وارد کنید. مثال: /newplaylist Rock")
        return
    try:
        cursor.execute("INSERT INTO playlists (channel_id, name) VALUES (?, ?)", (channel_id, name))
        conn.commit()
        await message.reply(f"پلی‌لیست '{name}' ایجاد شد.")
    except sqlite3.IntegrityError:
        await message.reply("این پلی‌لیست قبلاً وجود دارد.")

@dp.message_handler(commands=["addsong"])
async def add_song(message: types.Message):
    if not await is_user_member(message.from_user.id):
        await message.reply("❌ لطفاً ابتدا در کانال‌ها عضو شوید.")
        return
    if not message.reply_to_message or not message.reply_to_message.audio:
        await message.reply("روی یک آهنگ ریپلای کنید و دستور را وارد نمایید.")
        return
    file_id = message.reply_to_message.audio.file_id
    playlist_name = message.get_args()
    channel_id = message.chat.id
    cursor.execute("INSERT INTO playlist_songs (channel_id, playlist_name, file_id) VALUES (?, ?, ?)", (channel_id, playlist_name, file_id))
    conn.commit()
    await message.reply(f"آهنگ به پلی‌لیست '{playlist_name}' اضافه شد.")

@dp.message_handler(commands=["playlist"])
async def get_playlist(message: types.Message):
    if not await is_user_member(message.from_user.id):
        await message.reply("❌ لطفاً ابتدا در کانال‌ها عضو شوید.")
        return
    name = message.get_args()
    channel_id = message.chat.id
    cursor.execute("SELECT file_id FROM playlist_songs WHERE channel_id = ? AND playlist_name = ?", (channel_id, name))
    songs = cursor.fetchall()
    cursor.execute("SELECT cover, description FROM playlists WHERE channel_id = ? AND name = ?", (channel_id, name))
    playlist_info = cursor.fetchone()

    if not songs:
        await message.reply("این پلی‌لیست خالی است یا وجود ندارد.")
        return

    media = [types.InputMediaAudio(song[0]) for song in songs]
    if playlist_info and playlist_info[0]:
        media.insert(0, InputMediaPhoto(playlist_info[0], caption=playlist_info[1] or ""))
    await bot.send_media_group(message.chat.id, media)

app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
