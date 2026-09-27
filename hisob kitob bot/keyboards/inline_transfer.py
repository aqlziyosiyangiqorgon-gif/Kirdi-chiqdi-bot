from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_source_accounts_keyboard(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Jo'natuvchi hamyonlar ro'yxati menyusi (2 tadan har qatorda)."""
    buttons = []
    row = []
    for acc in accounts:
        row.append(InlineKeyboardButton(
            text=f"📤 {acc['name']} ({acc['balance']:,.0f})",
            callback_data=f"tr_src_{acc['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_target_accounts_keyboard(accounts: List[Dict[str, Any]], exclude_account_id: int) -> InlineKeyboardMarkup:
    """Qabul qiluvchi hamyonlar ro'yxati menyusi (jo'natuvchi hamyon chiqarib tashlangan)."""
    buttons = []
    row = []
    for acc in accounts:
        if acc['id'] == exclude_account_id:
            continue
        row.append(InlineKeyboardButton(
            text=f"📥 {acc['name']} ({acc['balance']:,.0f})",
            callback_data=f"tr_tgt_{acc['id']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_fsm")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
