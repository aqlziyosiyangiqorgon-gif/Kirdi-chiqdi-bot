import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db_manager import init_db
from handlers import start, settings, transactions, transfer, voice, reports, admin

logging.basicConfig(level=logging.INFO)

async def health_check(request):
    """Render Web Service uchun liveness health-check endpoint."""
    return web.Response(text="Telegram Bot is alive and running 24/7!", status=200)

async def start_web_server():
    """Render portida veb-serverni fonda yurgizish."""
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[+] Web-server {port}-portda muvaffaqiyatli ishga tushirildi (Render health check).")

async def main():
    # 0. Render Web Service portini ochish (24/7 o'chib qolmasligi uchun)
    await start_web_server()

    # 1. Database initializatsiyasi
    await init_db()
    print("[+] Ma'lumotlar bazasi va jadvallar tayyor.")

    # 2. Bot va Dispatcher obyektlari
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Routerlarni ulash
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(transactions.router)
    dp.include_router(transfer.router)
    dp.include_router(voice.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)

    # 4. Schedulerni sozlash va ishga tushirish
    from services.scheduler import setup_scheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    print("[+] Schedulerni ishga tushirildi (Avtomatik oylik hisobotlar).")

    print("[+] Telegram bot ishga tushdi...")
    
    # 5. Polling tayyorlash va eski yangilanishlarni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("[-] Bot to'xtatildi.")

