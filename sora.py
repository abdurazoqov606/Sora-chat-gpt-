import asyncio
import logging
import sqlite3
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- KUTUBXONALAR ---
import g4f  # Chat uchun
import yt_dlp # Yuklash uchun
from gradio_client import Client # VIDEO YASASH UCHUN

# --- SOZLAMALAR ---
BOT_TOKEN = "8246378380:AAHsa6DjVrXZwXZODaPnbX98GlyI4Hx9Z8Q"
ADMIN_ID = 8426582765
FOUNDER_LINK = "https://www.instagram.com/abdurazoqov_edits?igsh=cGs1aGh1bGp5eWN3"
FOUNDER_NAME = "abdurazoqov_edits"

# Loglar
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# --- BAZA (Admin uchun) ---
def db_start():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
    con.commit()
    con.close()

def add_user(user_id):
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users VALUES (?)", (user_id,))
        con.commit()
    except:
        pass
    con.close()

def get_all_users():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    cur.execute("SELECT id FROM users")
    return cur.fetchall()

# --- STATES ---
class BotStates(StatesGroup):
    chatting = State()
    gen_image = State()
    gen_video = State()
    downloading = State()
    broadcasting = State()

# --- TUGMALAR ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🎬 Video yasash (AI)", callback_data="mode_video"),
         InlineKeyboardButton(text="🖼 Rasm yasash (AI)", callback_data="mode_image")],
        [InlineKeyboardButton(text="📥 Video Yuklash", callback_data="mode_download")],
        [InlineKeyboardButton(text="💬 Chat (Savol-Javob)", callback_data="mode_chat")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")]
    ])

# --- HANDLERS (ADMIN) ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Admin Panel", reply_markup=admin_menu())

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_ask(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id == ADMIN_ID:
        await callback.message.answer("Xabarni yuboring:")
        await state.set_state(BotStates.broadcasting)

@dp.message(BotStates.broadcasting)
async def broadcast_send(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()
        count = 0
        await message.answer("Yuborilmoqda...")
        for user in users:
            try:
                await message.copy_to(user[0])
                count += 1
                await asyncio.sleep(0.05)
            except: pass
        await message.answer(f"✅ {count} kishiga yuborildi.")
        await state.clear()

# --- HANDLERS (USER) ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    txt = (
        f"<b>Botga xush kelibsiz! 👋</b>\n\n"
        f"Men quyidagilarni bajara olaman:\n"
        f"🎥 <b>Matndan Video yasash (AI)</b>\n"
        f"🖼 <b>Rasm chizish</b>\n"
        f"📥 <b>Video yuklash (Insta/TikTok)</b>\n\n"
        f"👨‍💻 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
    )
    await message.answer(txt, reply_markup=main_menu(), disable_web_page_preview=True)

@dp.callback_query(lambda c: c.data.startswith("mode_"))
async def mode_handler(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]
    if mode == "video":
        await state.set_state(BotStates.gen_video)
        await callback.message.answer("🎬 <b>Video yasash</b>\nIngliz tilida g'oya yozing (masalan: <i>A cat eating pizza</i>):")
    elif mode == "image":
        await state.set_state(BotStates.gen_image)
        await callback.message.answer("🖼 <b>Rasm yasash</b>\nG'oyani yozing:")
    elif mode == "download":
        await state.set_state(BotStates.downloading)
        await callback.message.answer("📥 Link yuboring:")
    elif mode == "chat":
        await state.set_state(BotStates.chatting)
        await callback.message.answer("💬 Savolingizni yozing:")
    await callback.answer()

# --- FUNKSIYALAR ---

# 1. HAQIQIY VIDEO YASASH (HuggingFace orqali Bepul)
@dp.message(BotStates.gen_video)
async def make_video(message: types.Message):
    prompt = message.text
    msg = await message.answer("⏳ <b>Video generatsiya qilinmoqda...</b>\nBu jarayon 1-2 daqiqa vaqt oladi. Iltimos kuting.")
    
    try:
        # HuggingFace dagi bepul ModelScope modeliga ulanish
        client = Client("damo-vilab/modelscope-text-to-video-synthesis")
        
        # Videoni generatsiya qilish (Blocking call, shuning uchun thread kerak bo'lishi mumkin, lekin Renderda ishlaydi)
        # API bizga vaqtinchalik fayl yo'lini qaytaradi
        result = client.predict(prompt, fn_index=0)
        
        video_file = FSInputFile(result)
        caption = f"🎬 <b>Video Tayyor!</b>\n📝 Promt: {prompt}\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
        
        await msg.delete()
        await message.answer_video(video_file, caption=caption, parse_mode="HTML")
        
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: Server band yoki promt juda murakkab.\nXato: {e}")

# 2. RASM YASASH (Pollinations - Bepul)
@dp.message(BotStates.gen_image)
async def make_image(message: types.Message):
    prompt = message.text
    url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
    caption = f"🖼 <b>Rasm Tayyor!</b>\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
    await message.answer_photo(url, caption=caption, parse_mode="HTML")

# 3. CHAT (G4F - Bepul)
@dp.message(BotStates.chatting)
async def chat_ai(message: types.Message):
    wait = await message.answer("🤔...")
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": message.text}]
        )
        await wait.delete()
        await message.answer(f"{response}\n\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>", disable_web_page_preview=True)
    except:
        await wait.edit_text("❌ Tizimda xatolik.")

# 4. YUKLOVCHI
@dp.message(BotStates.downloading)
async def downloader(message: types.Message):
    url = message.text
    wait = await message.answer("⏳ Yuklanmoqda...")
    try:
        ydl_opts = {'format': 'best', 'outtmpl': 'vid.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        vid = FSInputFile(filename)
        cap = f"📥 <b>Yuklandi!</b>\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
        await message.answer_video(vid, caption=cap, parse_mode="HTML")
        os.remove(filename)
        await wait.delete()
    except:
        await wait.edit_text("❌ Link xato.")

# --- MAIN ---
async def main():
    db_start()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())