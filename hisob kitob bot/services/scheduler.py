import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import DB_NAME, ADMIN_ID
from database.db_manager import get_all_active_user_ids
from services.pdf_generator import generate_monthly_pdf

logger = logging.getLogger(__name__)

async def send_monthly_pdf_reports(bot: Bot):
    """
    Barcha aktiv bot foydalanuvchilariga avtomatik monthly PDF hisobot yuboradi.
    """
    logger.info("Avtomatik oy yakuni PDF hisobotlarini yuborish boshlandi...")
    user_ids = await get_all_active_user_ids()


    period_str = datetime.now().strftime("%B %Y")

    for uid in user_ids:
        pdf_path = None
        try:
            pdf_path = await generate_monthly_pdf(uid, f"Foydalanuvchi #{uid}", period_str)
            doc_file = FSInputFile(pdf_path, filename=f"Oylik_Moliya_Hisoboti_{period_str}.pdf")
            
            await bot.send_document(
                chat_id=uid,
                document=doc_file,
                caption=f"🗓 **{period_str}** oyi yakunlandi! Siz uchun tayyorlangan avtomatik PDF moliya hisobotingiz."
            )
            logger.info(f"User {uid} uchun PDF hisobot yuborildi.")
        except Exception as e:
            logger.error(f"User {uid} uchun PDF hisobot yuborishda xatolik: {e}")
        finally:
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except Exception:
                    pass

async def check_and_send_monthly_report(bot: Bot):
    """
    Har kuni 23:59 da chaqiriladi. Faqat oyning oxirgi kuni bo'lsagina PDF yuboradi.
    Ertangi kun oyning 1-kuni bo'lsa — bugun oyning oxirgi kuni.
    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    if tomorrow.day == 1:
        logger.info(f"Bugun oyning oxirgi kuni ({today}). PDF hisobotlar yuboriladi.")
        await send_monthly_pdf_reports(bot)
    else:
        logger.debug(f"Bugun ({today}) oy oxiri emas. O'tkazib yuborildi.")

async def backup_database(bot: Bot):
    """
    Har kecha soat 00:00 da finance.db faylini admin'ning Telegram chatiga yuboradi.
    Koyeb konteyner qayta ishga tushganda baza yo'qolmasligi uchun zaxira.
    """
    if not ADMIN_ID or ADMIN_ID == 0:
        logger.warning("ADMIN_ID sozlanmagan. Baza zaxirasi yuborilmaydi.")
        return

    if not os.path.exists(DB_NAME):
        logger.error(f"Baza fayli topilmadi: {DB_NAME}")
        return

    try:
        today_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_filename = f"finance_backup_{today_str}.db"
        doc_file = FSInputFile(DB_NAME, filename=backup_filename)
        
        await bot.send_document(
            chat_id=ADMIN_ID,
            document=doc_file,
            caption=f"💾 Avtomatik baza zaxirasi\n📅 {today_str}\n📦 Hajmi: {os.path.getsize(DB_NAME):,} bayt"
        )
        logger.info(f"Baza zaxirasi ADMIN_ID={ADMIN_ID} ga yuborildi.")
    except Exception as e:
        logger.error(f"Baza zaxirasini yuborishda xatolik: {e}")

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    APScheduler obyekti yaratadi:
    1) Har kuni 23:59 — oylik PDF hisobot tekshiruvi
    2) Har kuni 00:00 — baza zaxirasi admin'ga yuboriladi
    """
    scheduler = AsyncIOScheduler()

    # 1. Oylik PDF hisobot (har kuni tekshiradi, faqat oy oxirida yuboradi)
    scheduler.add_job(
        check_and_send_monthly_report,
        trigger=CronTrigger(hour=23, minute=59),
        args=[bot],
        name="monthly_pdf_reports"
    )

    # 2. Har kechasi baza zaxirasi
    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=0, minute=0),
        args=[bot],
        name="daily_db_backup"
    )

    return scheduler

