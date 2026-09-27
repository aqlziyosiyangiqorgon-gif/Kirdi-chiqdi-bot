import os
import asyncio
import sys
from pathlib import Path

# Parent path ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import (
    init_db,
    add_account,
    add_category,
    add_transaction
)
from services.pdf_generator import generate_monthly_pdf

async def main():
    print("--- 7-BOSQICH (PDF GENERATION & SCHEDULER) TESTI BOSHLANDI ---")
    await init_db()
    
    TEST_USER_ID = 777111222
    
    # 1. Test ma'lumotlarini bazaga qo'shish
    acc_id = await add_account(TEST_USER_ID, "Humo Karta", balance=3500000.0)
    cat_exp = await add_category(TEST_USER_ID, "Bozorlik", cat_type="expense", monthly_limit=1000000.0)
    cat_inc = await add_category(TEST_USER_ID, "Frilans", cat_type="income", monthly_limit=0.0)
    
    await add_transaction(TEST_USER_ID, 250000.0, "expense", cat_exp, acc_id, comment="Haftalik oziq-ovqat")
    await add_transaction(TEST_USER_ID, 1200000.0, "income", cat_inc, acc_id, comment="Loyiha to'lovi")
    
    print("[+] Test foydalanuvchisi va tranzaksiyalari yaratildi.")

    # 2. PDF Hisobot yaratish
    pdf_path = await generate_monthly_pdf(TEST_USER_ID, "Alisher Navoiy", "Sentabr 2026")
    print(f"[+] PDF Generatsiya qilindi. Fayl manzili:\n    {pdf_path}")

    # 3. Assertlar
    assert os.path.exists(pdf_path), "PDF fayl yaratilmadi!"
    file_size = os.path.getsize(pdf_path)
    print(f"[+] PDF fayl hajmi: {file_size} bayt")
    assert file_size > 0, "PDF fayli bo'sh!"

    # 4. Vaqtinchalik faylni tozalash
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        print("[+] Test PDF fayli muvaffaqiyatli tozalandi.")

    print("\n--- 7-BOSQICH TESTLARI MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    asyncio.run(main())
