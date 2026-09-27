from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin panel bosh menyusi."""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar ro'yxati", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="📊 Umumiy Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="💾 Baza Zaxirasi (.db)", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_users_keyboard(users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Faqat userlar ro'yxati tugmalari — har biri ustiga bosiladigan."""
    keyboard = []
    for u in users:
        name = u.get('full_name') or f"User #{u['user_id']}"
        tx_c = u.get('total_tx', 0)
        btn_text = f"👤 {name} ({tx_c} ta amal)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_u_{u['user_id']}")])

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyuga", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Bitta foydalanuvchi profilidagi orqaga qaytish tugmasi."""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Foydalanuvchilar ro'yxatiga", callback_data="admin_users")],
        [InlineKeyboardButton(text="🏠 Asosiy Admin Menyu", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Admin panel orqaga qaytish tugmasi."""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Admin Menyuga", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
