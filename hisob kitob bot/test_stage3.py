import asyncio
import re
from database.db_manager import (
    init_db,
    add_account,
    get_accounts,
    add_category,
    get_categories,
    add_transaction,
    get_category_monthly_spent,
    get_account_by_id,
    get_category_by_name
)

async def main():
    print("--- 3-BOSQICH TESTI BOSHLANDI ---")
    await init_db()
    
    TEST_USER_ID = 999888777
    
    # 1. Hamyon va Kategoriya yaratish
    acc_id = await add_account(TEST_USER_ID, "Uzcard", balance=1000000.0)
    cat_exp_id = await add_category(TEST_USER_ID, "Do'kon", cat_type="expense", monthly_limit=100000.0)
    cat_inc_id = await add_category(TEST_USER_ID, "Oylik", cat_type="income", monthly_limit=0.0)
    print(f"[+] Hamyon (ID: {acc_id}) va Kategoriyalar (Expense ID: {cat_exp_id}, Income ID: {cat_inc_id}) yaratildi.")
    
    # 2. Xarajat tranzaksiyasi qo'shish (85 000 so'm -> Limitning 85% i)
    tx_id1 = await add_transaction(TEST_USER_ID, 85000.0, "expense", cat_exp_id, acc_id, comment="Bozorlik")
    print(f"[+] Chiqim tranzaksiyasi saqlandi (ID: {tx_id1})")
    
    acc_after1 = await get_account_by_id(acc_id)
    spent1 = await get_category_monthly_spent(TEST_USER_ID, cat_exp_id)
    print(f"    - Yangi Balans: {acc_after1['balance']:,.2f} so'm (Kutilgan: 915,000.00)")
    print(f"    - Oy davomida sarflangan: {spent1:,.2f} so'm (Limit: 100,000.00 | 85%)")
    assert acc_after1['balance'] == 915000.0
    assert spent1 == 85000.0
    
    # 3. Yana Xarajat qo'shish (20 000 so'm -> Jami 105 000 so'm, Limit 105% oshdi)
    tx_id2 = await add_transaction(TEST_USER_ID, 20000.0, "expense", cat_exp_id, acc_id, comment="Non va sut")
    spent2 = await get_category_monthly_spent(TEST_USER_ID, cat_exp_id)
    print(f"    - Ikkinchi chiqimdan so'ng sarflangan: {spent2:,.2f} so'm (100% oshdi!)")
    assert spent2 == 105000.0

    # 4. Kirim tranzaksiyasi (500 000 so'm)
    tx_id3 = await add_transaction(TEST_USER_ID, 500000.0, "income", cat_inc_id, acc_id, comment="Bonus")
    acc_after3 = await get_account_by_id(acc_id)
    print(f"    - Kirimdan so'ng balans: {acc_after3['balance']:,.2f} so'm (Kutilgan: 1,395,000.00)")
    assert acc_after3['balance'] == 1395000.0

    # 5. Fast Parser RegEx tekshiruvi
    pattern = r"^([\+\-])\s*(\d+(?:[\.\,]\d+)?)\s+(.+)$"
    test_texts = [
        "-50000 do'kon",
        "+2000000 oylik",
        "-15000 do'kon non va sut"
    ]
    print("\n--- Tezkor Matn Parseri RegEx Testi ---")
    for text in test_texts:
        match = re.match(pattern, text)
        assert match is not None
        sign, amount_str, rest = match.groups()
        print(f"Match: '{text}' -> Ishora: '{sign}', Summa: '{amount_str}', Rest: '{rest}'")

    print("\n--- 3-BOSQICH TESTI MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    asyncio.run(main())
