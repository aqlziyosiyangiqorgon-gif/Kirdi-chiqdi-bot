import asyncio
import os
from database.db_manager import init_db, add_account, get_accounts, add_category, get_categories

async def main():
    print("--- 1-BOSQICH TESTI BOSHLANDI ---")
    
    # 1. Bazani reinitialize qilish
    await init_db()
    print("[+] Ma'lumotlar bazasi va jadvallar muvaffaqiyatli yaratildi.")
    
    TEST_USER_ID = 123456789
    
    # 2. Hamyon qo'shish
    acc_id = await add_account(user_id=TEST_USER_ID, name="Naqd", balance=100000.0)
    print(f"[+] Hamyon qo'shildi (ID: {acc_id})")
    
    # 3. Kategoriya qo'shish
    cat_id = await add_category(user_id=TEST_USER_ID, name="Do‘kon", cat_type="expense", monthly_limit=500000.0)
    print(f"[+] Kategoriya qo'shildi (ID: {cat_id})")
    
    # 4. Hamyonlarni o'qish
    accounts = await get_accounts(user_id=TEST_USER_ID)
    print("\n--- Foydalanuvchi Hamyonlari ---")
    for acc in accounts:
        print(f"ID: {acc['id']} | Nomi: {acc['name']} | Balans: {acc['balance']:,.2f}")
        
    # 5. Kategoriyalarni o'qish
    categories = await get_categories(user_id=TEST_USER_ID, cat_type="expense")
    print("\n--- Chiqim Kategoriyalari ---")
    for cat in categories:
        print(f"ID: {cat['id']} | Nomi: {cat['name']} | Turi: {cat['type']} | Limit: {cat['monthly_limit']:,.2f}")
        
    print("\n--- TEST MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    asyncio.run(main())
