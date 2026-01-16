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
from aiohttp import web # Render uchun server

# --- KUTUBXONALAR (Xatolik bo'lsa, bot to'xtamasligi uchun try-except) ---
try:
    import g4f
except ImportError:
    g4f = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from gradio_client import Client

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

# --- BAZA (Xotirada ishlaydi, Renderda fayl o'chib ketishi mumkin) ---
# Oddiy ro'yxatdan foydalanamiz (Crash bo'lmasligi uchun)
users_db = set()

def add_user(user_id):
    users_db.add(user_id)

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

# --- RENDER UCHUN WEB SERVER (Keep Alive) ---
async def health_check(request):
    return web.Response(text="Bot ishlab turibdi!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render avtomatik PORT beradi, bo'lmasa 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- HANDLERS ---
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

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"👑 Admin Panel\nFoydalanuvchilar (taxminiy): {len(users_db)}\n\nReklama uchun matn yoki rasm yuboring.")
        # Oddiy qilib, keyingi xabarni reklama deb hisoblaymiz
        global admin_mode
        admin_mode = True

# --- VIDEO YASASH (Graduo/HuggingFace) ---
@dp.message(BotStates.gen_video)
async def make_video(message: types.Message):
    prompt = message.text
    msg = await message.answer("⏳ <b>Video generatsiya qilinmoqda...</b>\nBu jarayon 2-3 daqiqa vaqt oladi. Server band bo'lishi mumkin.")
    
    try:
        # Bepul modelga ulanish (ModelScope)
        client = Client("damo-vilab/modelscope-text-to-video-synthesis")
        result = client.predict(prompt, fn_index=0)
        
        video_file = FSInputFile(result)
        caption = f"🎬 <b>Video Tayyor!</b>\n📝 Promt: {prompt}\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
        
        await msg.delete()
        await message.answer_video(video_file, caption=caption, parse_mode="HTML")
        
    except Exception as e:
        await msg.edit_text(f"❌ Kechirasiz, bepul video serverlar band yoki javob bermayapti.\n\nXato: {e}")

# --- RASM YASASH ---
@dp.message(BotStates.gen_image)
async def make_image(message: types.Message):
    prompt = message.text
    url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
    caption = f"🖼 <b>Rasm Tayyor!</b>\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
    await message.answer_photo(url, caption=caption, parse_mode="HTML")

# --- CHAT ---
@dp.message(BotStates.chatting)
async def chat_ai(message: types.Message):
    wait = await message.answer("🤔...")
    try:
        if g4f:
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.default,
                messages=[{"role": "user", "content": message.text}]
            )
            await wait.delete()
            await message.answer(f"{response}\n\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>", disable_web_page_preview=True)
        else:
            await wait.edit_text("AI moduli o'rnatilmagan.")
    except Exception as e:
        await wait.edit_text(f"❌ Xatolik: {e}")

# --- YUKLOVCHI ---
@dp.message(BotStates.downloading)
async def downloader(message: types.Message):
    url = message.text
    wait = await message.answer("⏳ Yuklanmoqda...")
    try:
        if yt_dlp:
            ydl_opts = {'format': 'best', 'outtmpl': 'vid.%(ext)s', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            vid = FSInputFile(filename)
            cap = f"📥 <b>Yuklandi!</b>\n👤 Asoschi: <a href='{FOUNDER_LINK}'>{FOUNDER_NAME}</a>"
            await message.answer_video(vid, caption=cap, parse_mode="HTML")
            os.remove(filename)
            await wait.delete()
        else:
            await wait.edit_text("Yuklovchi modul ishlamayapti.")
    except:
        await wait.edit_text("❌ Link xato.")

# --- MAIN ---
async def main():
    # Avval Web Serverni ishga tushiramiz (Render o'chirmasligi uchun)
    await start_web_server()
    
    print("Bot va Server ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
