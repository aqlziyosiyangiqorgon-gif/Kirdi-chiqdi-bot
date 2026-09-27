from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_settings_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Sozlamalar asosiy menyusi."""
    keyboard = [
        [InlineKeyboardButton(text="💳 Hamyonlarim", callback_data="settings_accounts")],
        [InlineKeyboardButton(text="📁 Bo'limlarim", callback_data="settings_categories")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="🛡️ Admin Panel", callback_data="admin_menu")])
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_accounts_keyboard() -> InlineKeyboardMarkup:
    """Hamyonlar ro'yxati menyusi."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Hamyon qo'shish", callback_data="add_account")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_menu_keyboard() -> InlineKeyboardMarkup:
    """Bo'limlar turlari va qo'shish menyusi."""
    keyboard = [
        [
            InlineKeyboardButton(text="📥 Kirim bo'limlari", callback_data="cats_income"),
            InlineKeyboardButton(text="📤 Chiqim bo'limlari", callback_data="cats_expense")
        ],
        [InlineKeyboardButton(text="➕ Bo'lim qo'shish", callback_data="add_category")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cat_type_select_keyboard() -> InlineKeyboardMarkup:
    """Yangi bo'lim turini tanlash inline menyusi."""
    keyboard = [
        [
            InlineKeyboardButton(text="📥 Kirim", callback_data="cat_type_income"),
            InlineKeyboardButton(text="📤 Chiqim", callback_data="cat_type_expense")
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
