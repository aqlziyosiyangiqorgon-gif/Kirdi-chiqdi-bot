CREATE_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    balance REAL DEFAULT 0
);
"""

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('income', 'expense')) NOT NULL,
    monthly_limit REAL DEFAULT 0
);
"""

CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    type TEXT CHECK(type IN ('income', 'expense', 'transfer')) NOT NULL,
    category_id INTEGER,
    from_account_id INTEGER,
    to_account_id INTEGER,
    comment TEXT,
    is_anomaly INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id),
    FOREIGN KEY(from_account_id) REFERENCES accounts(id),
    FOREIGN KEY(to_account_id) REFERENCES accounts(id)
);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    full_name TEXT,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INIT_SCRIPTS = [
    CREATE_USERS_TABLE,
    CREATE_ACCOUNTS_TABLE,
    CREATE_CATEGORIES_TABLE,
    CREATE_TRANSACTIONS_TABLE
]

