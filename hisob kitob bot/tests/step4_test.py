import asyncio
import sys
from pathlib import Path

# Parent path ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import (
    init_db,
    add_account,
    get_account_by_id,
    add_transfer,
    get_connection
)

async def main():
    print("--- 4-BOSQICH (O'TKAZMALAR) TESTI BOSHLANDI ---")
    await init_db()
    
    TEST_USER_ID = 555444333
    
    # 1. Ikkita hamyon yaratish
    acc1_id = await add_account(TEST_USER_ID, "Uzcard", balance=1000000.0)
    acc2_id = await add_account(TEST_USER_ID, "Naqd", balance=200000.0)
    print(f"[+] Hamyonlar yaratildi:\n    - Uzcard (ID: {acc1_id}, Balans: 1,000,000.00 so'm)\n    - Naqd (ID: {acc2_id}, Balans: 200,000.00 so'm)")

    # 2. 300 000 so'm o'tkazma bajarish
    transfer_amount = 300000.0
    tx_id = await add_transfer(
        user_id=TEST_USER_ID,
        from_account_id=acc1_id,
        to_account_id=acc2_id,
        amount=transfer_amount,
        comment="Bankomatdan naqdlashtirish"
    )
    print(f"[+] O'tkazma muvaffaqiyatli bajarildi (Tranzaksiya ID: {tx_id})")

    # 3. Balanslarni tekshirish
    acc1_after = await get_account_by_id(acc1_id)
    acc2_after = await get_account_by_id(acc2_id)
    
    print(f"    - Uzcard yangi balans: {acc1_after['balance']:,.2f} so'm (Kutilgan: 700,000.00)")
    print(f"    - Naqd yangi balans: {acc2_after['balance']:,.2f} so'm (Kutilgan: 500,000.00)")

    assert acc1_after['balance'] == 700000.0, f"Uzcard balansi xato: {acc1_after['balance']}"
    assert acc2_after['balance'] == 500000.0, f"Naqd balansi xato: {acc2_after['balance']}"

    # 4. Transactions jadvalidan yozuvni tekshirish
    conn = await get_connection()
    try:
        async with conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            tx_data = dict(row)
            assert tx_data['type'] == 'transfer'
            assert tx_data['from_account_id'] == acc1_id
            assert tx_data['to_account_id'] == acc2_id
            assert tx_data['amount'] == 300000.0
            assert tx_data['comment'] == "Bankomatdan naqdlashtirish"
            print(f"[+] DB Yozuvi tekshirildi: Type='{tx_data['type']}', Amount={tx_data['amount']:,.2f}")
    finally:
        await conn.close()

    print("\n--- 4-BOSQICH TESTI MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    asyncio.run(main())
