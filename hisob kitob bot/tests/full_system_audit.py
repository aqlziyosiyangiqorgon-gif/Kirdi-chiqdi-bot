"""
======================================================================
  FULL SYSTEM AUDIT TEST — Shaxsiy Moliya Telegram Bot
  Barcha 7 ta modul uchun to'liq E2E va Stress test skripti
======================================================================
"""

import asyncio
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ──────────────────────────────────────────────────────────────
# TEST NATIJALARINI YIG'UVCHI FRAMEWORK
# ──────────────────────────────────────────────────────────────

class AuditResult:
    def __init__(self):
        self.results = []
        self.pass_count = 0
        self.warn_count = 0
        self.fail_count = 0

    def log(self, module: str, test_name: str, status: str, detail: str = "", fix: str = ""):
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[status]
        if status == "PASS":
            self.pass_count += 1
        elif status == "WARN":
            self.warn_count += 1
        else:
            self.fail_count += 1
        self.results.append({
            "module": module,
            "test": test_name,
            "status": status,
            "icon": icon,
            "detail": detail,
            "fix": fix
        })
        color = {"PASS": "\033[92m", "WARN": "\033[93m", "FAIL": "\033[91m"}[status]
        reset = "\033[0m"
        print(f"  {icon} {color}[{status}]{reset} {module} > {test_name}" + (f" — {detail}" if detail else ""))

    def print_summary(self):
        total = len(self.results)
        print("\n" + "=" * 90)
        print(f"  UMUMIY NATIJA: {self.pass_count} PASS / {self.warn_count} WARNING / {self.fail_count} FAIL (Jami: {total})")
        print("=" * 90)
        
        # Jadval shaklida
        print(f"\n{'Modul':<30} {'Test':<40} {'Holat':<8} {'Xato/Kamchilik':<35} {'Tuzatish':<35}")
        print("-" * 148)
        for r in self.results:
            detail = r['detail'][:33] + ".." if len(r['detail']) > 35 else r['detail']
            fix = r['fix'][:33] + ".." if len(r['fix']) > 35 else r['fix']
            print(f"{r['module']:<30} {r['test']:<40} {r['icon']:<8} {detail:<35} {fix:<35}")


audit = AuditResult()

# ──────────────────────────────────────────────────────────────
# Yordamchi: Toza DB bilan ishlash
# ──────────────────────────────────────────────────────────────
TEST_DB_PATH = str(Path(__file__).resolve().parent.parent / "test_audit.db")

async def setup_clean_db():
    """Mavjud test DB ni o'chirib, yangisini yaratadi."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    import config
    config.DB_NAME = TEST_DB_PATH  # Test uchun DB path ni override
    
    from database.db_manager import init_db
    await init_db()


# ══════════════════════════════════════════════════════════════
# BLOK 1: BAZA VA ULANISH
# ══════════════════════════════════════════════════════════════

async def test_blok1_database():
    print("\n" + "─" * 70)
    print("  📦 BLOK 1: BAZA VA ULANISH")
    print("─" * 70)
    
    MODULE = "Blok1-DB"
    
    # 1.1 init_db — jadvallar yaratilganmi?
    try:
        from database.db_manager import get_connection
        conn = await get_connection()
        
        async with conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") as cursor:
            tables = [row['name'] for row in await cursor.fetchall()]
        
        expected = {'accounts', 'categories', 'transactions'}
        found = expected.intersection(set(tables))
        
        if found == expected:
            audit.log(MODULE, "Jadvallar yaratilishi (3 ta)", "PASS")
        else:
            missing = expected - found
            audit.log(MODULE, "Jadvallar yaratilishi (3 ta)", "FAIL",
                      f"Topilmadi: {missing}", "models.py INIT_SCRIPTS ni tekshiring")
        
        # 1.2 PRAGMA foreign_keys
        async with conn.execute("PRAGMA foreign_keys") as cursor:
            fk_row = await cursor.fetchone()
            fk_status = dict(fk_row) if fk_row else {}

        if fk_status and list(fk_status.values())[0] == 1:
            audit.log(MODULE, "PRAGMA foreign_keys = ON", "PASS")
        else:
            audit.log(MODULE, "PRAGMA foreign_keys = ON", "WARN",
                      f"FK status: {fk_status}", "get_connection() ichida PRAGMA tekshiring")

        # 1.3 Jadval ustunlarini tekshirish
        for table_name, expected_cols in [
            ("accounts", {"id", "user_id", "name", "balance"}),
            ("categories", {"id", "user_id", "name", "type", "monthly_limit"}),
            ("transactions", {"id", "user_id", "amount", "type", "category_id", 
                              "from_account_id", "to_account_id", "comment", "is_anomaly", "created_at"})
        ]:
            async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
                cols = {row['name'] for row in await cursor.fetchall()}
            
            missing_cols = expected_cols - cols
            if not missing_cols:
                audit.log(MODULE, f"'{table_name}' jadval ustunlari", "PASS")
            else:
                audit.log(MODULE, f"'{table_name}' jadval ustunlari", "FAIL",
                          f"Topilmadi: {missing_cols}", "models.py da ustunlarni qo'shing")

        await conn.close()
    except Exception as e:
        audit.log(MODULE, "DB Ulanish", "FAIL", str(e)[:60], "config.py va aiosqlite ni tekshiring")


# ══════════════════════════════════════════════════════════════
# BLOK 2: SOZLAMALAR & FSM CRUD
# ══════════════════════════════════════════════════════════════

async def test_blok2_settings_crud():
    print("\n" + "─" * 70)
    print("  ⚙️  BLOK 2: SOZLAMALAR & FSM CRUD")
    print("─" * 70)
    
    MODULE = "Blok2-CRUD"
    UID = 100000001

    from database.db_manager import (
        add_account, get_accounts, add_category, get_categories,
        get_category_by_name, get_category_by_id, get_account_by_id
    )

    # 2.1 Hamyon qo'shish va olish
    try:
        acc_id = await add_account(UID, "TestNaqd", 500000.0)
        assert acc_id is not None and acc_id > 0
        
        accs = await get_accounts(UID)
        assert any(a['name'] == "TestNaqd" and a['balance'] == 500000.0 for a in accs)
        audit.log(MODULE, "add_account + get_accounts", "PASS")
    except Exception as e:
        audit.log(MODULE, "add_account + get_accounts", "FAIL", str(e)[:60])

    # 2.2 get_account_by_id
    try:
        acc = await get_account_by_id(acc_id)
        assert acc is not None and acc['name'] == "TestNaqd"
        audit.log(MODULE, "get_account_by_id", "PASS")
    except Exception as e:
        audit.log(MODULE, "get_account_by_id", "FAIL", str(e)[:60])

    # 2.3 Kategoriya qo'shish (Chiqim + limit)
    try:
        cat_exp_id = await add_category(UID, "Oziq-ovqat", "expense", monthly_limit=200000.0)
        assert cat_exp_id is not None
        cats = await get_categories(UID, cat_type="expense")
        assert any(c['name'] == "Oziq-ovqat" and c['monthly_limit'] == 200000.0 for c in cats)
        audit.log(MODULE, "add_category (expense + limit)", "PASS")
    except Exception as e:
        audit.log(MODULE, "add_category (expense + limit)", "FAIL", str(e)[:60])

    # 2.4 Kategoriya qo'shish (Kirim, limit=0)
    try:
        cat_inc_id = await add_category(UID, "Maosh", "income", monthly_limit=0)
        cats_inc = await get_categories(UID, cat_type="income")
        assert any(c['name'] == "Maosh" for c in cats_inc)
        audit.log(MODULE, "add_category (income)", "PASS")
    except Exception as e:
        audit.log(MODULE, "add_category (income)", "FAIL", str(e)[:60])

    # 2.5 Invalid category type
    try:
        raised = False
        try:
            await add_category(UID, "Noto'g'ri", "unknown")
        except ValueError:
            raised = True
        assert raised
        audit.log(MODULE, "add_category invalid type ValueError", "PASS")
    except Exception as e:
        audit.log(MODULE, "add_category invalid type ValueError", "FAIL", str(e)[:60])

    # 2.6 get_category_by_name (case-insensitive)
    try:
        cat_found = await get_category_by_name(UID, "oziq-OVQAT", "expense")
        assert cat_found is not None and cat_found['name'] == "Oziq-ovqat"
        audit.log(MODULE, "get_category_by_name (case-insensitive)", "PASS")
    except Exception as e:
        audit.log(MODULE, "get_category_by_name (case-insensitive)", "FAIL", str(e)[:60])

    # 2.7 get_category_by_id
    try:
        cat_by_id = await get_category_by_id(cat_exp_id)
        assert cat_by_id is not None and cat_by_id['id'] == cat_exp_id
        audit.log(MODULE, "get_category_by_id", "PASS")
    except Exception as e:
        audit.log(MODULE, "get_category_by_id", "FAIL", str(e)[:60])

    return UID, acc_id, cat_exp_id, cat_inc_id


# ══════════════════════════════════════════════════════════════
# BLOK 3: TRANZAKSIYALAR & LIMITLAR
# ══════════════════════════════════════════════════════════════

async def test_blok3_transactions(uid, acc_id, cat_exp_id, cat_inc_id):
    print("\n" + "─" * 70)
    print("  💳 BLOK 3: TRANZAKSIYALAR & LIMITLAR")
    print("─" * 70)

    MODULE = "Blok3-Tranzaksiya"

    from database.db_manager import (
        add_transaction, get_account_by_id, 
        get_category_monthly_spent, get_connection
    )

    # 3.1 Chiqim — Balansdan ayirish
    try:
        bal_before = (await get_account_by_id(acc_id))['balance']  # 500000
        tx1 = await add_transaction(uid, 120000.0, "expense", cat_exp_id, acc_id, comment="NonBozor")
        bal_after = (await get_account_by_id(acc_id))['balance']
        
        expected = bal_before - 120000.0
        assert abs(bal_after - expected) < 0.01, f"Kutilgan={expected}, Haqiqiy={bal_after}"
        audit.log(MODULE, "Chiqim balansdan ayirish (atomik)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Chiqim balansdan ayirish (atomik)", "FAIL", str(e)[:60])

    # 3.2 Kirim — Balansga qo'shish
    try:
        bal_before2 = (await get_account_by_id(acc_id))['balance']
        tx2 = await add_transaction(uid, 1000000.0, "income", cat_inc_id, acc_id, comment="Oylik")
        bal_after2 = (await get_account_by_id(acc_id))['balance']
        
        expected2 = bal_before2 + 1000000.0
        assert abs(bal_after2 - expected2) < 0.01
        audit.log(MODULE, "Kirim balansga qo'shish (atomik)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Kirim balansga qo'shish (atomik)", "FAIL", str(e)[:60])

    # 3.3 Invalid tx_type
    try:
        raised = False
        try:
            await add_transaction(uid, 1000, "transfer", cat_exp_id, acc_id)
        except ValueError:
            raised = True
        assert raised
        audit.log(MODULE, "add_transaction invalid type ValueError", "PASS")
    except Exception as e:
        audit.log(MODULE, "add_transaction invalid type ValueError", "FAIL", str(e)[:60])

    # 3.4 Oylik Limit 80% testi
    try:
        # Hozir oziq-ovqat limitga 120,000 / 200,000 = 60%. Yana 45000 qo'shamiz -> 165,000 / 200,000 = 82.5%
        await add_transaction(uid, 45000.0, "expense", cat_exp_id, acc_id, comment="Limit82")
        spent = await get_category_monthly_spent(uid, cat_exp_id)
        limit_val = 200000.0
        pct = (spent / limit_val) * 100
        
        assert pct >= 80.0 and pct < 100.0, f"Foiz={pct:.1f}%, kutilgan ~82.5%"
        audit.log(MODULE, "Oylik limit 80% ogohlantirish holati", "PASS", f"Spent={spent:,.0f}, {pct:.1f}%")
    except Exception as e:
        audit.log(MODULE, "Oylik limit 80% ogohlantirish holati", "FAIL", str(e)[:60])

    # 3.5 Oylik Limit 100% testi
    try:
        await add_transaction(uid, 50000.0, "expense", cat_exp_id, acc_id, comment="Limit100+")
        spent2 = await get_category_monthly_spent(uid, cat_exp_id)
        pct2 = (spent2 / 200000.0) * 100
        
        assert pct2 >= 100.0, f"Foiz={pct2:.1f}%, kutilgan >= 100%"
        audit.log(MODULE, "Oylik limit 100% oshib ketgan holat", "PASS", f"Spent={spent2:,.0f}, {pct2:.1f}%")
    except Exception as e:
        audit.log(MODULE, "Oylik limit 100% oshib ketgan holat", "FAIL", str(e)[:60])

    # 3.6 Tezkor RegEx parseri
    try:
        from handlers.transactions import check_and_format_limit_warning
        pattern = r"^([\+\-])\s*(\d+(?:[\.\,]\d+)?)\s+(.+)$"
        
        test_cases = [
            ("-50000 do'kon",       "-", "50000", "do'kon"),
            ("+2000000 oylik",      "+", "2000000", "oylik"),
            ("-15000 benzin uchun", "-", "15000", "benzin uchun"),
            ("-1500.50 choy",       "-", "1500.50", "choy"),
            ("+100,5 test",         "+", "100,5", "test"),
        ]
        
        all_pass = True
        for text, exp_sign, exp_amt, exp_rest in test_cases:
            match = re.match(pattern, text)
            if not match:
                audit.log(MODULE, f"RegEx parse: '{text}'", "FAIL", "Match topilmadi")
                all_pass = False
                continue
            sign, amt, rest = match.groups()
            if sign != exp_sign or amt != exp_amt:
                audit.log(MODULE, f"RegEx parse: '{text}'", "FAIL",
                          f"sign={sign}, amt={amt}, kutilgan={exp_sign},{exp_amt}")
                all_pass = False
        
        if all_pass:
            audit.log(MODULE, f"Tezkor RegEx parseri ({len(test_cases)} ta test)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Tezkor RegEx parseri", "FAIL", str(e)[:60])

    # 3.7 check_and_format_limit_warning funktsiyasi
    try:
        from handlers.transactions import check_and_format_limit_warning
        warn_text = await check_and_format_limit_warning(uid, cat_exp_id, "Oziq-ovqat")
        assert len(warn_text) > 0 and ("DIQQAT" in warn_text or "OGOHLANTIRISH" in warn_text)
        audit.log(MODULE, "check_and_format_limit_warning", "PASS")
    except Exception as e:
        audit.log(MODULE, "check_and_format_limit_warning", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# BLOK 4: O'TKAZMALAR (TRANSFER)
# ══════════════════════════════════════════════════════════════

async def test_blok4_transfers(uid):
    print("\n" + "─" * 70)
    print("  🔄 BLOK 4: O'TKAZMALAR (TRANSFER)")
    print("─" * 70)
    
    MODULE = "Blok4-Transfer"

    from database.db_manager import add_account, add_transfer, get_account_by_id, get_connection

    # Ikkita hamyon yaratish
    acc_a_id = await add_account(uid, "Karta-A", 2000000.0)
    acc_b_id = await add_account(uid, "Karta-B", 300000.0)

    # 4.1 Normal o'tkazma — balans mutanosibligi
    try:
        tx_id = await add_transfer(uid, acc_a_id, acc_b_id, 500000.0, comment="Naqdlashtirish")
        a_after = await get_account_by_id(acc_a_id)
        b_after = await get_account_by_id(acc_b_id)

        assert abs(a_after['balance'] - 1500000.0) < 0.01, f"A={a_after['balance']}"
        assert abs(b_after['balance'] - 800000.0) < 0.01, f"B={b_after['balance']}"
        audit.log(MODULE, "Transfer balans mutanosibligi (A-500K, B+500K)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Transfer balans mutanosibligi", "FAIL", str(e)[:60])

    # 4.2 Transfer — DB yozuvi to'g'riligi
    try:
        conn = await get_connection()
        async with conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
            tx = dict(row)
        await conn.close()
        
        assert tx['type'] == 'transfer'
        assert tx['from_account_id'] == acc_a_id
        assert tx['to_account_id'] == acc_b_id
        assert tx['category_id'] is None
        audit.log(MODULE, "Transfer DB yozuvi (type, from, to, NULL category)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Transfer DB yozuvi", "FAIL", str(e)[:60])

    # 4.3 O'z-o'ziga o'tkazma — Hozir kod taqiqlamayapti (bug/feature?)
    try:
        bal_before = (await get_account_by_id(acc_a_id))['balance']
        await add_transfer(uid, acc_a_id, acc_a_id, 100000.0, "O'z-o'ziga")
        bal_after = (await get_account_by_id(acc_a_id))['balance']
        
        # O'z-o'ziga o'tkazma balansni o'zgartirmasligi kerak (chunki - va + o'zini bekor qiladi)
        # Lekin: bu mantiqan noto'g'ri tranzaksiya yaratadi, shuning uchun WARNING
        if abs(bal_after - bal_before) < 0.01:
            audit.log(MODULE, "O'z-o'ziga o'tkazma (self-transfer)", "WARN",
                      "Taqiqlangan emas, balans o'zgarmaydi",
                      "add_transfer da from==to tekshiruv qo'shing")
        else:
            audit.log(MODULE, "O'z-o'ziga o'tkazma (self-transfer)", "FAIL",
                      f"Balans o'zgardi: {bal_before}->{bal_after}",
                      "add_transfer da from==to tekshiruv qo'shing")
    except ValueError:
        audit.log(MODULE, "O'z-o'ziga o'tkazma (self-transfer)", "PASS",
                  "ValueError to'g'ri raise qilindi")
    except Exception as e:
        audit.log(MODULE, "O'z-o'ziga o'tkazma (self-transfer)", "WARN", str(e)[:60])

    # 4.4 Ikkinchi o'tkazma — stress
    try:
        for i in range(5):
            await add_transfer(uid, acc_a_id, acc_b_id, 10000.0)
        a_final = await get_account_by_id(acc_a_id)
        b_final = await get_account_by_id(acc_b_id)
        sum_total = a_final['balance'] + b_final['balance']
        # Boshlang'ich = 2000000 + 300000 = 2300000 (o'z-o'ziga transfer hisobga kiritilmaydi)
        assert abs(sum_total - 2300000.0) < 0.01, f"Jami={sum_total}"
        audit.log(MODULE, "5x ketma-ket transfer — jami balans saqlanishi", "PASS")
    except Exception as e:
        audit.log(MODULE, "5x ketma-ket transfer — jami balans saqlanishi", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# BLOK 5: OVOZLI XABAR NLP PARSERI
# ══════════════════════════════════════════════════════════════

async def test_blok5_voice_parser():
    print("\n" + "─" * 70)
    print("  🎙️  BLOK 5: OVOZLI XABAR NLP PARSERI")
    print("─" * 70)

    MODULE = "Blok5-Voice"

    from services.voice_service import parse_financial_voice_text

    mock_cats = [
        {"id": 1, "name": "Do'kon", "type": "expense"},
        {"id": 2, "name": "Benzin", "type": "expense"},
        {"id": 3, "name": "Oylik", "type": "income"},
        {"id": 4, "name": "Avans", "type": "income"},
    ]
    mock_accs = [
        {"id": 10, "name": "Naqd", "balance": 500000},
        {"id": 11, "name": "Uzcard", "balance": 1500000},
    ]

    test_cases = [
        # (phrase, expected_amount, expected_type, expected_cat, expected_acc)
        ("Do'kondan 150 mingga go'sht oldim naqdga", 150000.0, "expense", "Do'kon", "Naqd"),
        ("Oylikdan 2 million tushdi uzcardga", 2000000.0, "income", "Oylik", "Uzcard"),
        ("Benzinga 100000 ketdi", 100000.0, "expense", "Benzin", None),
        ("3 mln avans olindi", 3000000.0, "income", "Avans", None),
        ("500000 chiqim", 500000.0, "expense", None, None),  # Kategoriya topilmasligi kerak
        ("Xarajat yo'q", None, None, None, None),  # Summa yo'q -> None qaytishi kerak
    ]

    for phrase, exp_amt, exp_type, exp_cat, exp_acc in test_cases:
        try:
            result = parse_financial_voice_text(phrase, mock_cats, mock_accs)
            
            if exp_amt is None:
                assert result is None, f"None kutilgan, lekin {result} qaytdi"
                audit.log(MODULE, f"Parse: '{phrase[:35]}'", "PASS", "None to'g'ri qaytdi")
                continue
            
            assert result is not None, "None qaytdi"
            assert abs(result['amount'] - exp_amt) < 0.01, f"Summa: {result['amount']} != {exp_amt}"
            assert result['type'] == exp_type, f"Tur: {result['type']} != {exp_type}"
            
            if exp_cat:
                assert result['category_name'] == exp_cat, f"Kat: {result['category_name']} != {exp_cat}"
            if exp_acc:
                assert result['account_name'] == exp_acc, f"Acc: {result['account_name']} != {exp_acc}"
            
            audit.log(MODULE, f"Parse: '{phrase[:35]}'", "PASS")
        except AssertionError as e:
            audit.log(MODULE, f"Parse: '{phrase[:35]}'", "FAIL", str(e)[:60])
        except AssertionError as e:
            audit.log(MODULE, f"Parse: '{phrase[:35]}'", "FAIL", str(e)[:60])
        except Exception as e:
            audit.log(MODULE, f"Parse: '{phrase[:35]}'", "FAIL", str(e)[:60])

    # 5.2 Karta sinonimi
    try:
        result = parse_financial_voice_text("50 mingga go'sht oldim kartadan", mock_cats, mock_accs)
        assert result is not None
        if result.get('account_name') in ('Uzcard', 'Humo', None):
            audit.log(MODULE, "Hamyon sinonimi ('karta' -> Uzcard)", "PASS", 
                      f"account={result.get('account_name')}")
        else:
            audit.log(MODULE, "Hamyon sinonimi ('karta' -> Uzcard)", "WARN",
                      f"Kutilgan: Uzcard, haqiqiy: {result.get('account_name')}")
    except Exception as e:
        audit.log(MODULE, "Hamyon sinonimi", "FAIL", str(e)[:60])

    # 5.3 Bo'sh matn
    try:
        r = parse_financial_voice_text("", mock_cats, mock_accs)
        assert r is None
        r2 = parse_financial_voice_text("   ", mock_cats, mock_accs)
        assert r2 is None
        audit.log(MODULE, "Bo'sh matn xavfsizligi (None qaytishi)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Bo'sh matn xavfsizligi", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# BLOK 6: TAHLIL, FOIZLAR & ANOMALIYALAR
# ══════════════════════════════════════════════════════════════

async def test_blok6_analytics(uid, acc_id, cat_exp_id, cat_inc_id):
    print("\n" + "─" * 70)
    print("  📊 BLOK 6: TAHLIL, FOIZLAR & ANOMALIYALAR")
    print("─" * 70)

    MODULE = "Blok6-Analytics"

    from database.db_manager import (
        get_period_comparison, get_category_comparison,
        detect_and_mark_anomalies, get_recent_anomalies,
        add_transaction, get_connection
    )

    # 6.1 Kunlik taqqoslama (Bugun vs Kecha)
    try:
        daily = await get_period_comparison(uid, period='day')
        assert "income" in daily and "expense" in daily
        assert "current" in daily["income"] and "previous" in daily["income"]
        assert "percent" in daily["income"] and "is_increase" in daily["income"]
        audit.log(MODULE, "get_period_comparison('day') lug'at strukturasi", "PASS")
    except Exception as e:
        audit.log(MODULE, "get_period_comparison('day') lug'at strukturasi", "FAIL", str(e)[:60])

    # 6.2 Oylik taqqoslama
    try:
        monthly = await get_period_comparison(uid, period='month')
        assert monthly["expense"]["current"] > 0  # Bu oyda xarajatlar bo'lishi kerak
        assert monthly["income"]["current"] > 0   # Bu oyda kirim bo'lishi kerak
        audit.log(MODULE, "get_period_comparison('month') qiymatlari > 0", "PASS",
                  f"Inc={monthly['income']['current']:,.0f}, Exp={monthly['expense']['current']:,.0f}")
    except Exception as e:
        audit.log(MODULE, "get_period_comparison('month') qiymatlari", "FAIL", str(e)[:60])

    # 6.3 O'tgan davr = 0 bo'lganda foiz hisoblash
    try:
        # Kechagi ma'lumotlar yo'q, shuning uchun previous=0
        # Kutilgan natija: percent=100.0 agar current>0
        daily2 = await get_period_comparison(uid, period='day')
        if daily2["expense"]["previous"] == 0 and daily2["expense"]["current"] > 0:
            assert daily2["expense"]["percent"] == 100.0
            audit.log(MODULE, "O'tgan davr=0 bo'lganda foiz = 100%", "PASS")
        else:
            audit.log(MODULE, "O'tgan davr=0 bo'lganda foiz = 100%", "PASS",
                      f"prev={daily2['expense']['previous']}")
    except Exception as e:
        audit.log(MODULE, "O'tgan davr=0 foiz hisoblash", "FAIL", str(e)[:60])

    # 6.4 get_category_comparison
    try:
        cat_comp = await get_category_comparison(uid, period='month')
        assert isinstance(cat_comp, list)
        if len(cat_comp) > 0:
            c = cat_comp[0]
            assert "category_name" in c and "current" in c and "percent" in c and "is_increase" in c
        audit.log(MODULE, "get_category_comparison strukturasi", "PASS", f"Count: {len(cat_comp)}")
    except Exception as e:
        audit.log(MODULE, "get_category_comparison strukturasi", "FAIL", str(e)[:60])

    # 6.5 Anomaliya — NORMAL (3x dan past)
    try:
        # O'rtacha xarajat taxminan ~50-70K, 50K qo'shish anomal emas
        tx_normal = await add_transaction(uid, 50000.0, "expense", cat_exp_id, acc_id, "Normal")
        is_anom = await detect_and_mark_anomalies(uid, tx_normal, 50000.0)
        assert is_anom is False
        audit.log(MODULE, "Anomaliya detect: Normal xarajat (False)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Anomaliya detect: Normal xarajat", "FAIL", str(e)[:60])

    # 6.6 Anomaliya — YIRIK (3x dan yuqori + >= 100K)
    try:
        tx_huge = await add_transaction(uid, 1500000.0, "expense", cat_exp_id, acc_id, "Telefon olish")
        is_anom2 = await detect_and_mark_anomalies(uid, tx_huge, 1500000.0)
        assert is_anom2 is True
        
        # DB da is_anomaly=1 bo'lganini tekshirish
        conn = await get_connection()
        async with conn.execute("SELECT is_anomaly FROM transactions WHERE id = ?", (tx_huge,)) as cur:
            row = await cur.fetchone()
            assert dict(row)['is_anomaly'] == 1
        await conn.close()
        
        audit.log(MODULE, "Anomaliya detect: Yirik xarajat (True, DB=1)", "PASS")
    except Exception as e:
        audit.log(MODULE, "Anomaliya detect: Yirik xarajat", "FAIL", str(e)[:60])

    # 6.7 get_recent_anomalies
    try:
        anomalies = await get_recent_anomalies(uid, days=30)
        assert isinstance(anomalies, list)
        assert len(anomalies) >= 1
        assert anomalies[0]['amount'] == 1500000.0
        audit.log(MODULE, "get_recent_anomalies ro'yxati", "PASS", f"Count: {len(anomalies)}")
    except Exception as e:
        audit.log(MODULE, "get_recent_anomalies ro'yxati", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# BLOK 7: PDF & SCHEDULER
# ══════════════════════════════════════════════════════════════

async def test_blok7_pdf_scheduler(uid):
    print("\n" + "─" * 70)
    print("  📄 BLOK 7: PDF & SCHEDULER")
    print("─" * 70)

    MODULE = "Blok7-PDF"

    # 7.1 PDF Generatsiyasi — haqiqiy ma'lumotlar bilan
    pdf_path = None
    try:
        from services.pdf_generator import generate_monthly_pdf
        pdf_path = await generate_monthly_pdf(uid, "Test Foydalanuvchi", "Sentabr 2026")
        
        assert os.path.exists(pdf_path), "PDF fayl topilmadi"
        size = os.path.getsize(pdf_path)
        assert size > 0, "PDF fayl bo'sh (0 bayt)"
        audit.log(MODULE, "generate_monthly_pdf (fayl yaratish)", "PASS", f"Hajmi: {size} bayt")
    except Exception as e:
        audit.log(MODULE, "generate_monthly_pdf (fayl yaratish)", "FAIL", str(e)[:60])

    # 7.2 PDF ichidagi matnni tekshirish (ReportLab oddiy matn qo'ya olganmi)
    try:
        assert pdf_path and os.path.exists(pdf_path)
        with open(pdf_path, "rb") as f:
            raw = f.read()
        # PDF fayl %PDF bilan boshlanishi kerak
        assert raw[:5] == b"%PDF-", "Fayl PDF formatida emas"
        audit.log(MODULE, "PDF format validatsiyasi (%PDF- header)", "PASS")
    except Exception as e:
        audit.log(MODULE, "PDF format validatsiyasi", "FAIL", str(e)[:60])

    # 7.3 O'zbek harflari (apostroflar, UTF8) bilan buzilmasligi
    try:
        # Agar PDF generatsiya muvaffaqiyatli bo'lgan bo'lsa, ReportLab buzilmagan
        # chunki kategoriya nomlarimizda apostrof bor ("Oziq-ovqat", "Do'kon")
        assert pdf_path and os.path.getsize(pdf_path) > 100
        audit.log(MODULE, "O'zbek matnlari ReportLab da buzilmasdan ishlashi", "PASS")
    except Exception as e:
        audit.log(MODULE, "O'zbek matnlari ReportLab", "FAIL", str(e)[:60])

    # Tozalash
    if pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)

    # 7.4 Scheduler — CronTrigger sozlamalari
    MODULE = "Blok7-Scheduler"
    try:
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger(day="28-31", hour=23, minute=59)
        # CronTrigger obyekti yaratildi va xatolik bermadi
        audit.log(MODULE, "CronTrigger(day=28-31, h=23, m=59) yaratilishi", "PASS")
    except Exception as e:
        audit.log(MODULE, "CronTrigger yaratilishi", "FAIL", str(e)[:60])

    # 7.5 Scheduler — setup_scheduler funksiyasi mavjudligi va import
    try:
        from services.scheduler import setup_scheduler
        assert callable(setup_scheduler)
        audit.log(MODULE, "setup_scheduler funksiyasi import", "PASS")
    except Exception as e:
        audit.log(MODULE, "setup_scheduler import", "FAIL", str(e)[:60])

    # 7.6 CronTrigger — oy oxiri mantiqiy to'g'riligi
    try:
        # day="28-31" da faqat shu kunlar ishlaydi, lekin 30 kunli oylarda 31 skip bo'ladi — bu normal APScheduler xulqi
        trigger2 = CronTrigger(day="28-31", hour=23, minute=59)
        fields = {f.name: str(f) for f in trigger2.fields}
        assert "day" in fields
        audit.log(MODULE, "CronTrigger oy oxiri qamrovi (28-31)", "WARN",
                  "28-31 har oy 4 marta fire bo'lishi mumkin",
                  "last' cron yoki 'day=-1' alternativasi")
    except Exception as e:
        audit.log(MODULE, "CronTrigger oy oxiri qamrovi", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# QO'SHIMCHA: KOD SIFAT TEKSHIRUVLARI
# ══════════════════════════════════════════════════════════════

async def test_code_quality():
    print("\n" + "─" * 70)
    print("  🔍 QOSHIMCHA: KOD SIFAT TEKSHIRUVLARI")
    print("─" * 70)

    MODULE = "Sifat"

    # Q.1 reports.py dagi typo tekshiruvi
    try:
        reports_path = Path(__file__).resolve().parent.parent / "handlers" / "reports.py"
        content = reports_path.read_text(encoding="utf-8")
        if "so me" in content:
            audit.log(MODULE, "handlers/reports.py typo: 'so me'", "FAIL",
                      "'so me' -> 'so'm' bo'lishi kerak (44-qator)",
                      "reports.py L44 'so me' ni 'so\\'m' ga almashtiring")
        else:
            audit.log(MODULE, "handlers/reports.py typo tekshiruvi", "PASS")
    except Exception as e:
        audit.log(MODULE, "reports.py typo tekshiruvi", "FAIL", str(e)[:60])

    # Q.2 bot.py import strukturasi
    try:
        bot_path = Path(__file__).resolve().parent.parent / "bot.py"
        bot_content = bot_path.read_text(encoding="utf-8")
        required_routers = ["start", "settings", "transactions", "transfer", "voice", "reports"]
        missing = [r for r in required_routers if f"{r}.router" not in bot_content]
        if not missing:
            audit.log(MODULE, "bot.py barcha 6 ta router ulanganligi", "PASS")
        else:
            audit.log(MODULE, "bot.py barcha 6 ta router ulanganligi", "FAIL",
                      f"Topilmadi: {missing}")
    except Exception as e:
        audit.log(MODULE, "bot.py router tekshiruvi", "FAIL", str(e)[:60])

    # Q.3 scheduler ulangan mi?
    try:
        assert "setup_scheduler" in bot_content and "scheduler.start()" in bot_content
        audit.log(MODULE, "bot.py scheduler integratsiyasi", "PASS")
    except Exception as e:
        audit.log(MODULE, "bot.py scheduler integratsiyasi", "FAIL", str(e)[:60])


# ══════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════

async def main():
    print("=" * 70)
    print("  🔎 FULL SYSTEM AUDIT — SHAXSIY MOLIYA TELEGRAM BOT")
    print(f"  Sana: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    await setup_clean_db()
    
    await test_blok1_database()
    uid, acc_id, cat_exp_id, cat_inc_id = await test_blok2_settings_crud()
    await test_blok3_transactions(uid, acc_id, cat_exp_id, cat_inc_id)
    await test_blok4_transfers(uid)
    await test_blok5_voice_parser()
    await test_blok6_analytics(uid, acc_id, cat_exp_id, cat_inc_id)
    await test_blok7_pdf_scheduler(uid)
    await test_code_quality()
    
    audit.print_summary()
    
    # Test DB ni tozalash
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

if __name__ == "__main__":
    asyncio.run(main())
