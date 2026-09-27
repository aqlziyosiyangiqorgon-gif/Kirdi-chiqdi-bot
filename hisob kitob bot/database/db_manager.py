import re
from typing import List, Dict, Any, Optional
import aiosqlite
import asyncpg
from config import DB_NAME, DATABASE_URL

_pg_pool: Optional[asyncpg.Pool] = None

def is_pg() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))

async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        # Neon connection pool
        _pg_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
    return _pg_pool

async def get_sqlite_conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_NAME)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn

async def init_db() -> None:
    """Jadvallarni yaratadi."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                full_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                balance DOUBLE PRECISION DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                type VARCHAR(10) CHECK(type IN ('income', 'expense')) NOT NULL,
                monthly_limit DOUBLE PRECISION DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                type VARCHAR(10) CHECK(type IN ('income', 'expense', 'transfer')) NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                from_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
                to_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
                comment TEXT,
                is_anomaly INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
    else:
        from database.models import INIT_SCRIPTS
        conn = await get_sqlite_conn()
        try:
            for script in INIT_SCRIPTS:
                await conn.execute(script)
            await conn.commit()
        finally:
            await conn.close()

async def add_account(user_id: int, name: str, balance: float = 0.0) -> int:
    """Yangi hamyon qo'shadi."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO accounts (user_id, name, balance) VALUES ($1, $2, $3) RETURNING id",
                user_id, name, balance
            )
    else:
        conn = await get_sqlite_conn()
        try:
            cur = await conn.execute(
                "INSERT INTO accounts (user_id, name, balance) VALUES (?, ?, ?)",
                (user_id, name, balance)
            )
            await conn.commit()
            return cur.lastrowid
        finally:
            await conn.close()

async def get_accounts(user_id: int) -> List[Dict[str, Any]]:
    """Foydalanuvchi hamyonlarini oladi."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, user_id, name, balance FROM accounts WHERE user_id = $1 ORDER BY id",
                user_id
            )
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                "SELECT id, user_id, name, balance FROM accounts WHERE user_id = ? ORDER BY id",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            await conn.close()

async def add_category(user_id: int, name: str, cat_type: str, monthly_limit: float = 0.0) -> int:
    """Kategoriya qo'shadi."""
    if cat_type not in ('income', 'expense'):
        raise ValueError("Category type must be 'income' or 'expense'")
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO categories (user_id, name, type, monthly_limit) VALUES ($1, $2, $3, $4) RETURNING id",
                user_id, name, cat_type, monthly_limit
            )
    else:
        conn = await get_sqlite_conn()
        try:
            cur = await conn.execute(
                "INSERT INTO categories (user_id, name, type, monthly_limit) VALUES (?, ?, ?, ?)",
                (user_id, name, cat_type, monthly_limit)
            )
            await conn.commit()
            return cur.lastrowid
        finally:
            await conn.close()

async def get_categories(user_id: int, cat_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Kategoriyalar ro'yxatini oladi."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            if cat_type:
                rows = await conn.fetch(
                    "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = $1 AND type = $2 ORDER BY id",
                    user_id, cat_type
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = $1 ORDER BY id",
                    user_id
                )
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            if cat_type:
                async with conn.execute(
                    "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = ? AND type = ? ORDER BY id",
                    (user_id, cat_type)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with conn.execute(
                    "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = ? ORDER BY id",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            await conn.close()

async def get_category_by_name(user_id: int, name: str, cat_type: str) -> Optional[Dict[str, Any]]:
    """Kategoriya nomi bo'yicha qidiradi (case-insensitive)."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = $1 AND type = $2 AND LOWER(name) = LOWER($3)",
                user_id, cat_type, name
            )
            return dict(row) if row else None
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE user_id = ? AND type = ? AND LOWER(name) = LOWER(?)",
                (user_id, cat_type, name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        finally:
            await conn.close()

async def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, name, type, monthly_limit FROM categories WHERE id = $1",
                category_id
            )
            return dict(row) if row else None
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute("SELECT id, user_id, name, type, monthly_limit FROM categories WHERE id = ?", (category_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        finally:
            await conn.close()

async def get_account_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, name, balance FROM accounts WHERE id = $1",
                account_id
            )
            return dict(row) if row else None
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute("SELECT id, user_id, name, balance FROM accounts WHERE id = ?", (account_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        finally:
            await conn.close()

async def add_transaction(
    user_id: int,
    amount: float,
    tx_type: str,
    category_id: int,
    account_id: int,
    comment: Optional[str] = None
) -> int:
    """Tranzaksiya qo'shadi va hamyon balansini yangilaydi."""
    if tx_type not in ('income', 'expense'):
        raise ValueError("Transaction type must be 'income' or 'expense'")
    
    from_acc = account_id if tx_type == 'expense' else None
    to_acc = account_id if tx_type == 'income' else None

    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                tx_id = await conn.fetchval(
                    """
                    INSERT INTO transactions (user_id, amount, type, category_id, from_account_id, to_account_id, comment)
                    VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
                    """,
                    user_id, amount, tx_type, category_id, from_acc, to_acc, comment
                )
                if tx_type == 'expense':
                    await conn.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, account_id)
                else:
                    await conn.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, account_id)
                return tx_id
    else:
        conn = await get_sqlite_conn()
        try:
            await conn.execute("BEGIN TRANSACTION;")
            cursor = await conn.execute(
                """
                INSERT INTO transactions (user_id, amount, type, category_id, from_account_id, to_account_id, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, amount, tx_type, category_id, from_acc, to_acc, comment)
            )
            tx_id = cursor.lastrowid
            if tx_type == 'expense':
                await conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            else:
                await conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            await conn.commit()
            return tx_id
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

async def get_category_monthly_spent(user_id: int, category_id: int) -> float:
    """Joriy oy davomida belgilangan kategoriya bo'yicha sarflangan jami summa."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE user_id = $1 AND category_id = $2 AND type = 'expense'
                AND date_trunc('month', created_at) = date_trunc('month', CURRENT_TIMESTAMP)
                """,
                user_id, category_id
            )
            return float(val or 0.0)
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM transactions
                WHERE user_id = ? AND category_id = ? AND type = 'expense'
                AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
                """,
                (user_id, category_id)
            ) as cursor:
                row = await cursor.fetchone()
                return float(row['total']) if row else 0.0
        finally:
            await conn.close()

async def add_transfer(
    user_id: int,
    from_account_id: int,
    to_account_id: int,
    amount: float,
    comment: Optional[str] = None
) -> int:
    """Hamyonlararo o'tkazmani bajaradi."""
    if from_account_id == to_account_id:
        raise ValueError("O'z-o'ziga o'tkazma qilish mumkin emas.")

    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND user_id = $3", amount, from_account_id, user_id)
                await conn.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2 AND user_id = $3", amount, to_account_id, user_id)
                tx_id = await conn.fetchval(
                    """
                    INSERT INTO transactions (user_id, amount, type, category_id, from_account_id, to_account_id, comment)
                    VALUES ($1, $2, 'transfer', NULL, $3, $4, $5) RETURNING id
                    """,
                    user_id, amount, from_account_id, to_account_id, comment
                )
                return tx_id
    else:
        conn = await get_sqlite_conn()
        try:
            await conn.execute("BEGIN TRANSACTION;")
            await conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?", (amount, from_account_id, user_id))
            await conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?", (amount, to_account_id, user_id))
            cursor = await conn.execute(
                """
                INSERT INTO transactions (user_id, amount, type, category_id, from_account_id, to_account_id, comment)
                VALUES (?, ?, 'transfer', NULL, ?, ?, ?)
                """,
                (user_id, amount, from_account_id, to_account_id, comment)
            )
            tx_id = cursor.lastrowid
            await conn.commit()
            return tx_id
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

async def get_period_comparison(user_id: int, period: str = 'day') -> Dict[str, Any]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            if period == 'day':
                curr_c = "created_at::date = CURRENT_DATE"
                prev_c = "created_at::date = CURRENT_DATE - INTERVAL '1 day'"
            else:
                curr_c = "date_trunc('month', created_at) = date_trunc('month', CURRENT_TIMESTAMP)"
                prev_c = "date_trunc('month', created_at) = date_trunc('month', CURRENT_TIMESTAMP - INTERVAL '1 month')"

            curr_inc = float(await conn.fetchval(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'income' AND {curr_c}", user_id) or 0.0)
            prev_inc = float(await conn.fetchval(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'income' AND {prev_c}", user_id) or 0.0)
            curr_exp = float(await conn.fetchval(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'expense' AND {curr_c}", user_id) or 0.0)
            prev_exp = float(await conn.fetchval(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'expense' AND {prev_c}", user_id) or 0.0)
    else:
        conn = await get_sqlite_conn()
        try:
            if period == 'day':
                curr_c = "date(created_at, 'localtime') = date('now', 'localtime')"
                prev_c = "date(created_at, 'localtime') = date('now', 'localtime', '-1 day')"
            else:
                curr_c = "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
                prev_c = "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime', '-1 month')"

            async with conn.execute(f"SELECT COALESCE(SUM(amount), 0) as val FROM transactions WHERE user_id = ? AND type = 'income' AND {curr_c}", (user_id,)) as cur:
                curr_inc = float((await cur.fetchone())['val'])
            async with conn.execute(f"SELECT COALESCE(SUM(amount), 0) as val FROM transactions WHERE user_id = ? AND type = 'income' AND {prev_c}", (user_id,)) as cur:
                prev_inc = float((await cur.fetchone())['val'])
            async with conn.execute(f"SELECT COALESCE(SUM(amount), 0) as val FROM transactions WHERE user_id = ? AND type = 'expense' AND {curr_c}", (user_id,)) as cur:
                curr_exp = float((await cur.fetchone())['val'])
            async with conn.execute(f"SELECT COALESCE(SUM(amount), 0) as val FROM transactions WHERE user_id = ? AND type = 'expense' AND {prev_c}", (user_id,)) as cur:
                prev_exp = float((await cur.fetchone())['val'])
        finally:
            await conn.close()

    def calc_percent(curr: float, prev: float) -> float:
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return ((curr - prev) / prev) * 100.0

    return {
        "income": {"current": curr_inc, "previous": prev_inc, "percent": abs(calc_percent(curr_inc, prev_inc)), "is_increase": curr_inc >= prev_inc},
        "expense": {"current": curr_exp, "previous": prev_exp, "percent": abs(calc_percent(curr_exp, prev_exp)), "is_increase": curr_exp >= prev_exp}
    }

async def get_category_comparison(user_id: int, period: str = 'month') -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            if period == 'day':
                curr_c = "t.created_at::date = CURRENT_DATE"
                prev_c = "t.created_at::date = CURRENT_DATE - INTERVAL '1 day'"
            else:
                curr_c = "date_trunc('month', t.created_at) = date_trunc('month', CURRENT_TIMESTAMP)"
                prev_c = "date_trunc('month', t.created_at) = date_trunc('month', CURRENT_TIMESTAMP - INTERVAL '1 month')"

            query = f"""
            SELECT c.id, c.name,
                COALESCE(SUM(CASE WHEN {curr_c} THEN t.amount ELSE 0 END), 0) as current_spent,
                COALESCE(SUM(CASE WHEN {prev_c} THEN t.amount ELSE 0 END), 0) as previous_spent
            FROM categories c
            LEFT JOIN transactions t ON t.category_id = c.id AND t.user_id = c.user_id AND t.type = 'expense'
            WHERE c.user_id = $1 AND c.type = 'expense'
            GROUP BY c.id, c.name
            HAVING COALESCE(SUM(CASE WHEN {curr_c} THEN t.amount ELSE 0 END), 0) > 0 
                OR COALESCE(SUM(CASE WHEN {prev_c} THEN t.amount ELSE 0 END), 0) > 0
            ORDER BY current_spent DESC
            """
            rows = await conn.fetch(query, user_id)
            result = []
            for r in rows:
                curr = float(r['current_spent'])
                prev = float(r['previous_spent'])
                pct = 100.0 if prev == 0 and curr > 0 else (((curr - prev) / prev) * 100.0 if prev > 0 else 0.0)
                result.append({"category_name": r['name'], "current": curr, "previous": prev, "percent": abs(pct), "is_increase": curr >= prev})
            return result
    else:
        conn = await get_sqlite_conn()
        try:
            if period == 'day':
                curr_cond = "date(t.created_at, 'localtime') = date('now', 'localtime')"
                prev_cond = "date(t.created_at, 'localtime') = date('now', 'localtime', '-1 day')"
            else:
                curr_cond = "strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
                prev_cond = "strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime', '-1 month')"

            query = f"""
            SELECT c.id, c.name,
                COALESCE(SUM(CASE WHEN {curr_cond} THEN t.amount ELSE 0 END), 0) as current_spent,
                COALESCE(SUM(CASE WHEN {prev_cond} THEN t.amount ELSE 0 END), 0) as previous_spent
            FROM categories c
            LEFT JOIN transactions t ON t.category_id = c.id AND t.user_id = c.user_id AND t.type = 'expense'
            WHERE c.user_id = ? AND c.type = 'expense'
            GROUP BY c.id, c.name
            HAVING current_spent > 0 OR previous_spent > 0
            ORDER BY current_spent DESC
            """
            async with conn.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    curr = float(row['current_spent'])
                    prev = float(row['previous_spent'])
                    pct = 100.0 if prev == 0 and curr > 0 else (((curr - prev) / prev) * 100.0 if prev > 0 else 0.0)
                    result.append({"category_name": row['name'], "current": curr, "previous": prev, "percent": abs(pct), "is_increase": curr >= prev})
                return result
        finally:
            await conn.close()

async def detect_and_mark_anomalies(user_id: int, transaction_id: int, amount: float) -> bool:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            avg_amount = await conn.fetchval(
                """
                SELECT COALESCE(AVG(amount), 0) FROM transactions
                WHERE user_id = $1 AND type = 'expense' AND id != $2
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                """,
                user_id, transaction_id
            )
            avg_amount = float(avg_amount or 0.0)
            if avg_amount > 0 and amount >= (3 * avg_amount) and amount >= 100000.0:
                await conn.execute("UPDATE transactions SET is_anomaly = 1 WHERE id = $1", transaction_id)
                return True
            return False
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                """
                SELECT COALESCE(AVG(amount), 0) as avg_amount FROM transactions
                WHERE user_id = ? AND type = 'expense' AND id != ?
                AND created_at >= datetime('now', '-30 days', 'localtime')
                """,
                (user_id, transaction_id)
            ) as cursor:
                row = await cursor.fetchone()
                avg_amount = float(row['avg_amount']) if row else 0.0
            if avg_amount > 0 and amount >= (3 * avg_amount) and amount >= 100000.0:
                await conn.execute("UPDATE transactions SET is_anomaly = 1 WHERE id = ?", (transaction_id,))
                await conn.commit()
                return True
            return False
        finally:
            await conn.close()

async def get_recent_anomalies(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.id, t.amount, t.comment, t.created_at, c.name as category_name, a.name as account_name
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.from_account_id = a.id
                WHERE t.user_id = $1 AND t.is_anomaly = 1 AND t.type = 'expense'
                AND t.created_at >= CURRENT_TIMESTAMP - ($2 || ' days')::INTERVAL
                ORDER BY t.created_at DESC
                """,
                user_id, str(days)
            )
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            query = """
            SELECT t.id, t.amount, t.comment, t.created_at, c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.from_account_id = a.id
            WHERE t.user_id = ? AND t.is_anomaly = 1 AND t.type = 'expense'
            AND t.created_at >= datetime('now', '-' || ? || ' days', 'localtime')
            ORDER BY t.created_at DESC
            """
            async with conn.execute(query, (user_id, days)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            await conn.close()

async def get_detailed_transactions(user_id: int, tx_type: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            type_filter = f"AND t.type = '{tx_type}'" if tx_type else "AND t.type IN ('income', 'expense')"
            query = f"""
            SELECT t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON CASE 
                WHEN t.type = 'expense' THEN t.from_account_id 
                ELSE t.to_account_id END = a.id
            WHERE t.user_id = $1 {type_filter}
            AND t.created_at >= CURRENT_TIMESTAMP - ($2 || ' days')::INTERVAL
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query, user_id, str(days))
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            type_filter = f"AND t.type = '{tx_type}'" if tx_type else "AND t.type IN ('income', 'expense')"
            query = f"""
            SELECT t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON CASE 
                WHEN t.type = 'expense' THEN t.from_account_id 
                ELSE t.to_account_id END = a.id
            WHERE t.user_id = ? {type_filter}
            AND t.created_at >= datetime('now', '-' || ? || ' days', 'localtime')
            ORDER BY t.created_at DESC
            """
            async with conn.execute(query, (user_id, days)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            await conn.close()

async def register_or_update_user(user_id: int, full_name: str, username: Optional[str] = None) -> None:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, full_name, username, last_active)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    username = EXCLUDED.username,
                    last_active = CURRENT_TIMESTAMP
                """,
                user_id, full_name, username
            )
    else:
        conn = await get_sqlite_conn()
        try:
            await conn.execute(
                """
                INSERT INTO users (user_id, full_name, username, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    username = excluded.username,
                    last_active = CURRENT_TIMESTAMP
                """,
                (user_id, full_name, username)
            )
            await conn.commit()
        finally:
            await conn.close()

async def get_all_users() -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.user_id, u.full_name, u.username, u.created_at, u.last_active,
                       COUNT(t.id) as total_tx,
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) as total_income,
                       COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) as total_expense
                FROM users u
                LEFT JOIN transactions t ON u.user_id = t.user_id
                GROUP BY u.user_id, u.full_name, u.username, u.created_at, u.last_active
                ORDER BY u.last_active DESC
                """
            )
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                """
                SELECT u.user_id, u.full_name, u.username, u.created_at, u.last_active,
                       COUNT(t.id) as total_tx,
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) as total_income,
                       COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) as total_expense
                FROM users u
                LEFT JOIN transactions t ON u.user_id = t.user_id
                GROUP BY u.user_id
                ORDER BY u.last_active DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            await conn.close()

async def get_global_stats() -> Dict[str, Any]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
            tx_row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as tx_count,
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
                    COALESCE(SUM(CASE WHEN type = 'transfer' THEN amount ELSE 0 END), 0) as total_transfers
                FROM transactions
                """
            )
            total_balance = await conn.fetchval("SELECT COALESCE(SUM(balance), 0) FROM accounts") or 0.0
            return {
                "user_count": user_count,
                "tx_count": tx_row["tx_count"],
                "total_income": float(tx_row["total_income"]),
                "total_expense": float(tx_row["total_expense"]),
                "total_transfers": float(tx_row["total_transfers"]),
                "total_balance": float(total_balance)
            }
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute("SELECT COUNT(*) as count FROM users") as cur:
                user_count = (await cur.fetchone())['count']
            async with conn.execute(
                """
                SELECT 
                    COUNT(*) as tx_count,
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
                    COALESCE(SUM(CASE WHEN type = 'transfer' THEN amount ELSE 0 END), 0) as total_transfers
                FROM transactions
                """
            ) as cur:
                tx_stats = dict(await cur.fetchone())
            async with conn.execute("SELECT COALESCE(SUM(balance), 0) as total_bal FROM accounts") as cur:
                total_balance = (await cur.fetchone())['total_bal']
            return {
                "user_count": user_count,
                "tx_count": tx_stats["tx_count"],
                "total_income": float(tx_stats["total_income"]),
                "total_expense": float(tx_stats["total_expense"]),
                "total_transfers": float(tx_stats["total_transfers"]),
                "total_balance": float(total_balance)
            }
        finally:
            await conn.close()

async def get_recent_all_transactions(limit: int = 20) -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            query = """
            SELECT t.id, t.user_id, t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name,
                   u.full_name as user_name, u.username as user_handle
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN users u ON t.user_id = u.user_id
            ORDER BY t.created_at DESC
            LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            query = """
            SELECT t.id, t.user_id, t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name,
                   u.full_name as user_name, u.username as user_handle
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN users u ON t.user_id = u.user_id
            ORDER BY t.created_at DESC
            LIMIT ?
            """
            async with conn.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        finally:
            await conn.close()

async def get_category_comparison_all(user_id: int, period: str = 'month') -> Dict[str, List[Dict[str, Any]]]:
    result = {"income": [], "expense": []}
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            curr_c = "date_trunc('month', t.created_at) = date_trunc('month', CURRENT_TIMESTAMP)"
            prev_c = "date_trunc('month', t.created_at) = date_trunc('month', CURRENT_TIMESTAMP - INTERVAL '1 month')"

            for cat_type in ("income", "expense"):
                query = f"""
                SELECT c.id, c.name,
                    COALESCE(SUM(CASE WHEN {curr_c} THEN t.amount ELSE 0 END), 0) as current_spent,
                    COALESCE(SUM(CASE WHEN {prev_c} THEN t.amount ELSE 0 END), 0) as previous_spent
                FROM categories c
                LEFT JOIN transactions t ON t.category_id = c.id AND t.user_id = c.user_id AND t.type = '{cat_type}'
                WHERE c.user_id = $1 AND c.type = '{cat_type}'
                GROUP BY c.id, c.name
                HAVING COALESCE(SUM(CASE WHEN {curr_c} THEN t.amount ELSE 0 END), 0) > 0 
                    OR COALESCE(SUM(CASE WHEN {prev_c} THEN t.amount ELSE 0 END), 0) > 0
                ORDER BY current_spent DESC
                """
                rows = await conn.fetch(query, user_id)
                for r in rows:
                    curr = float(r['current_spent'])
                    prev = float(r['previous_spent'])
                    pct = 100.0 if prev == 0 and curr > 0 else (((curr - prev) / prev) * 100.0 if prev > 0 else 0.0)
                    result[cat_type].append({"category_name": r['name'], "current": curr, "previous": prev, "percent": abs(pct), "is_increase": curr >= prev})
        return result
    else:
        conn = await get_sqlite_conn()
        try:
            curr_cond = "strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
            prev_cond = "strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime', '-1 month')"

            for cat_type in ("income", "expense"):
                query = f"""
                SELECT c.id, c.name,
                    COALESCE(SUM(CASE WHEN {curr_cond} THEN t.amount ELSE 0 END), 0) as current_spent,
                    COALESCE(SUM(CASE WHEN {prev_cond} THEN t.amount ELSE 0 END), 0) as previous_spent
                FROM categories c
                LEFT JOIN transactions t ON t.category_id = c.id AND t.user_id = c.user_id AND t.type = '{cat_type}'
                WHERE c.user_id = ? AND c.type = '{cat_type}'
                GROUP BY c.id, c.name
                HAVING current_spent > 0 OR previous_spent > 0
                ORDER BY current_spent DESC
                """
                async with conn.execute(query, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        curr = float(row['current_spent'])
                        prev = float(row['previous_spent'])
                        pct = 100.0 if prev == 0 and curr > 0 else (((curr - prev) / prev) * 100.0 if prev > 0 else 0.0)
                        result[cat_type].append({"category_name": row['name'], "current": curr, "previous": prev, "percent": abs(pct), "is_increase": curr >= prev})
            return result
        finally:
            await conn.close()

async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT u.user_id, u.full_name, u.username, u.created_at, u.last_active,
                       COUNT(t.id) as tx_count,
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) as total_income,
                       COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) as total_expense
                FROM users u
                LEFT JOIN transactions t ON u.user_id = t.user_id
                WHERE u.user_id = $1
                GROUP BY u.user_id, u.full_name, u.username, u.created_at, u.last_active
                """,
                user_id
            )
            if not row:
                return None
            data = dict(row)
            accs = await conn.fetch("SELECT id, name, balance FROM accounts WHERE user_id = $1", user_id)
            accounts = [dict(a) for a in accs]
            data["accounts"] = accounts
            data["total_balance"] = sum(a["balance"] for a in accounts)
            return data
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute(
                """
                SELECT u.user_id, u.full_name, u.username, u.created_at, u.last_active,
                       COUNT(t.id) as tx_count,
                       COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) as total_income,
                       COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) as total_expense
                FROM users u
                LEFT JOIN transactions t ON u.user_id = t.user_id
                WHERE u.user_id = ?
                GROUP BY u.user_id
                """,
                (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                data = dict(row)

            async with conn.execute("SELECT id, name, balance FROM accounts WHERE user_id = ?", (user_id,)) as cur:
                accounts = [dict(r) for r in await cur.fetchall()]

            data["accounts"] = accounts
            data["total_balance"] = sum(a["balance"] for a in accounts)
            return data
        finally:
            await conn.close()

async def get_user_transactions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            query = """
            SELECT t.id, t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name,
                   a_from.name as from_acc_name,
                   a_to.name as to_acc_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.id
            WHERE t.user_id = $1
            ORDER BY t.created_at DESC
            LIMIT $2
            """
            rows = await conn.fetch(query, user_id, limit)
            return [dict(r) for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            query = """
            SELECT t.id, t.amount, t.type, t.comment, t.created_at,
                   c.name as category_name,
                   a_from.name as from_acc_name,
                   a_to.name as to_acc_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a_from ON t.from_account_id = a_from.id
            LEFT JOIN accounts a_to ON t.to_account_id = a_to.id
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            LIMIT ?
            """
            async with conn.execute(query, (user_id, limit)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            await conn.close()

async def get_all_active_user_ids() -> List[int]:
    """Barcha aktiv foydalanuvchilar IDlarini qaytaradi."""
    if is_pg():
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT user_id FROM accounts")
            return [r["user_id"] for r in rows]
    else:
        conn = await get_sqlite_conn()
        try:
            async with conn.execute("SELECT DISTINCT user_id FROM accounts") as cur:
                rows = await cur.fetchall()
                return [r["user_id"] for r in rows]
        finally:
            await conn.close()
