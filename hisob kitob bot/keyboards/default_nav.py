from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu Reply tugmalari."""
    keyboard = [
        [KeyboardButton(text="➕ Kirim"), KeyboardButton(text="➖ Chiqim")],
        [KeyboardButton(text="💰 Balans"), KeyboardButton(text="📊 Hisobot")],
        [KeyboardButton(text="🔄 O'tkazma"), KeyboardButton(text="⚙️ Sozlamalar")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish Reply tugmasi."""
    keyboard = [
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
