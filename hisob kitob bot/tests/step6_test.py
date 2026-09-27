import asyncio
import sys
from pathlib import Path

# Parent path ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import (
    init_db,
    add_account,
    add_category,
    add_transaction,
    get_period_comparison,
    get_category_comparison,
    detect_and_mark_anomalies,
    get_recent_anomalies
)

async def main():
    print("--- 6-BOSQICH (ANALYTICS ENGINE & ANOMALIES) TESTI BOSHLANDI ---")
    await init_db()
    
    TEST_USER_ID = 666777888
    
    # 1. Hamyon va bo'limlar yaratish
    acc_id = await add_account(TEST_USER_ID, "Karta", balance=5000000.0)
    cat_exp1 = await add_category(TEST_USER_ID, "Tushlik", cat_type="expense", monthly_limit=0.0)
    cat_exp2 = await add_category(TEST_USER_ID, "Texnika", cat_type="expense", monthly_limit=0.0)
    cat_inc = await add_category(TEST_USER_ID, "Oylik", cat_type="income", monthly_limit=0.0)
    
    # 2. Oddiy xarajatlar kiritish (O'rtacha ~30,000 so'm shakllantirish uchun)
    tx1 = await add_transaction(TEST_USER_ID, 25000.0, "expense", cat_exp1, acc_id, comment="Tushlik 1")
    tx2 = await add_transaction(TEST_USER_ID, 35000.0, "expense", cat_exp1, acc_id, comment="Tushlik 2")
    tx3 = await add_transaction(TEST_USER_ID, 30000.0, "expense", cat_exp1, acc_id, comment="Tushlik 3")
    
    # Kirim kiritish
    await add_transaction(TEST_USER_ID, 3000000.0, "income", cat_inc, acc_id, comment="Oylik maosh")
    
    print("[+] Boshlang'ich tranzaksiyalar saqlandi.")
    
    # 3. Anomaliya bo'lmagan xarajatni tekshirish (50,000 so'm < 3*AVG)
    tx_normal = await add_transaction(TEST_USER_ID, 50000.0, "expense", cat_exp1, acc_id, comment="Kichik xarajat")
    is_anom1 = await detect_and_mark_anomalies(TEST_USER_ID, tx_normal, 50000.0)
    print(f"[+] 50,000 so'm anomaliyami?: {is_anom1} (Kutilgan: False)")
    assert is_anom1 is False
    
    # 4. Yirik anomal xarajat kiritish (500,000 so'm >= 3*30,000 va >= 100,000)
    tx_large = await add_transaction(TEST_USER_ID, 500000.0, "expense", cat_exp2, acc_id, comment="Telefon")
    is_anom2 = await detect_and_mark_anomalies(TEST_USER_ID, tx_large, 500000.0)
    print(f"[+] 500,000 so'm anomaliyami?: {is_anom2} (Kutilgan: True)")
    assert is_anom2 is True

    # 5. Anomaliyalarni bazadan olish
    anomalies = await get_recent_anomalies(TEST_USER_ID, days=30)
    print(f"[+] Topilgan anomaliyalar soni: {len(anomalies)}")
    assert len(anomalies) >= 1
    assert anomalies[0]["amount"] == 500000.0

    # 6. Davrlar taqqoslamasini tekshirish (Bugungi vs Kechagi / Oylik)
    daily_comp = await get_period_comparison(TEST_USER_ID, period='day')
    monthly_comp = await get_period_comparison(TEST_USER_ID, period='month')
    print(f"[+] Daily comparison: {daily_comp}")
    print(f"[+] Monthly comparison: {monthly_comp}")
    assert daily_comp["expense"]["current"] > 0
    assert daily_comp["income"]["current"] == 3000000.0

    # 7. Kategoriyalar bo'yicha taqqoslama
    cat_comp = await get_category_comparison(TEST_USER_ID, period='month')
    print(f"[+] Category comparison count: {len(cat_comp)}")
    assert len(cat_comp) >= 2

    print("\n--- 6-BOSQICH TESTLARI MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    asyncio.run(main())
