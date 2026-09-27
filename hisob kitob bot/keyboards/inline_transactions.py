from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_categories_inline_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxatini inline tugmalarda chiqaradi (2 tadan har qatorda)."""
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            text=f"📁 {cat['name']}",
            callback_data=f"tx_cat_{cat['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_accounts_inline_keyboard(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Hamyonlar ro'yxatini inline tugmalarda chiqaradi (2 tadan har qatorda)."""
    buttons = []
    row = []
    for acc in accounts:
        row.append(InlineKeyboardButton(
            text=f"💳 {acc['name']} ({acc['balance']:,.0f})",
            callback_data=f"tx_acc_{acc['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
