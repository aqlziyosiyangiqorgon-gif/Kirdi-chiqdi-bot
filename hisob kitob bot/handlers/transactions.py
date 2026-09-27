import re
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db_manager import (
    get_accounts,
    get_categories,
    get_category_by_name,
    get_category_by_id,
    get_account_by_id,
    add_transaction,
    get_category_monthly_spent
)
from keyboards.default_nav import get_main_keyboard, get_cancel_keyboard
from keyboards.inline_transactions import (
    get_categories_inline_keyboard,
    get_accounts_inline_keyboard
)
from states.transaction_states import TransactionSG

router = Router()

async def check_and_format_limit_warning(user_id: int, category_id: int, category_name: str) -> str:
    """Oylik limit holatini tekshiradi va ogohlantirish matnini shakllantiradi."""
    cat = await get_category_by_id(category_id)
    if not cat or cat.get('type') != 'expense':
        return ""
    
    monthly_limit = cat.get('monthly_limit', 0.0)
    if monthly_limit <= 0:
        return ""
    
    total_spent = await get_category_monthly_spent(user_id, category_id)
    percentage = (total_spent / monthly_limit) * 100
    
    if percentage >= 100:
        return (
            f"\n\n🚨 **DIQQAT!** '{category_name}' bo'limi uchun belgilangan oylik limit tugadi!\n"
            f"Jami sarflandi: **{total_spent:,.2f} so'm** / Limit: **{monthly_limit:,.2f} so'm**"
        )
    elif percentage >= 80:
        remaining = monthly_limit - total_spent
        return (
            f"\n\n⚠️ **OGOHLANTIRISH:** '{category_name}' bo'limi limitining **{percentage:.0f}%** qismi sarflandi!\n"
            f"Qoldiq limit: **{remaining:,.2f} so'm** (Jami: {total_spent:,.2f} / {monthly_limit:,.2f} so'm)"
        )
    return ""

async def save_and_respond(message: Message, state: FSMContext, comment: str):
    """Tranzaksiyani saqlaydi va javob beradi."""
    data = await state.get_data()
    user_id = message.from_user.id
    tx_type = data["tx_type"]
    category_id = data["category_id"]
    account_id = data["account_id"]
    amount = data["amount"]

    tx_id = await add_transaction(
        user_id=user_id,
        amount=amount,
        tx_type=tx_type,
        category_id=category_id,
        account_id=account_id,
        comment=comment
    )
    await state.clear()

    cat_data = await get_category_by_id(category_id)
    acc_data = await get_account_by_id(account_id)
    
    cat_name = cat_data["name"] if cat_data else "Bo'lim"
    acc_name = acc_data["name"] if acc_data else "Hamyon"
    new_balance = acc_data["balance"] if acc_data else 0.0
    
    warning_msg = ""
    if tx_type == "expense":
        warning_msg = await check_and_format_limit_warning(user_id, category_id, cat_name)
        from database.db_manager import detect_and_mark_anomalies
        if await detect_and_mark_anomalies(user_id, tx_id, amount):
            warning_msg += "\n\n🚨 **YIRIK XARAJAT (ANOMALIYA):** Ushbu xarajat sizning o'rtacha xarajatingizdan 3 barobar yuqori!"

    type_str = "📥 Kirim" if tx_type == "income" else "📤 Chiqim"
    
    await message.answer(
        f"✅ **{type_str} muvaffaqiyatli saqlandi!**\n\n"
        f"Summa: **{amount:,.2f} so'm**\n"
        f"Bo'lim: **{cat_name}**\n"
        f"Sabab: _{comment}_\n"
        f"Hamyon: **{acc_name}** (Yangi balans: **{new_balance:,.2f} so'm**)"
        f"{warning_msg}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# --- FSM OQIMI: QO'LDA KIRITISH ---

@router.message(F.text.in_({"➕ Kirim", "➖ Chiqim"}))
async def start_transaction_flow(message: Message, state: FSMContext):
    user_id = message.from_user.id
    tx_type = "income" if message.text == "➕ Kirim" else "expense"
    
    accounts = await get_accounts(user_id)
    if not accounts:
        await message.answer(
            "❌ Sizda hali birorta ham hamyon yo'q.\nAvval **⚙️ Sozlamalar** bo'limidan hamyon qo'shing.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return
        
    categories = await get_categories(user_id, cat_type=tx_type)
    if not categories:
        type_str = "kirim" if tx_type == "income" else "chiqim"
        await message.answer(
            f"❌ Sizda hali {type_str} bo'limlari yo'q.\nAvval **⚙️ Sozlamalar** bo'limidan {type_str} bo'limini qo'shing.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    await state.update_data(tx_type=tx_type)
    await state.set_state(TransactionSG.waiting_for_category)
    
    type_title = "Kirim" if tx_type == "income" else "Chiqim"
    await message.answer(
        f"📝 **{type_title} kiritish**\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=get_categories_inline_keyboard(categories),
        parse_mode="Markdown"
    )

@router.callback_query(TransactionSG.waiting_for_category, F.data.startswith("tx_cat_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.replace("tx_cat_", ""))
    await state.update_data(category_id=category_id)
    
    accounts = await get_accounts(callback.from_user.id)
    await state.set_state(TransactionSG.waiting_for_account)
    
    await callback.message.edit_text(
        "💳 **Qaysi hamyonni tanlaysiz?**",
        reply_markup=get_accounts_inline_keyboard(accounts),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(TransactionSG.waiting_for_account, F.data.startswith("tx_acc_"))
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    account_id = int(callback.data.replace("tx_acc_", ""))
    await state.update_data(account_id=account_id)
    await state.set_state(TransactionSG.waiting_for_amount)
    
    await callback.message.delete()
    await callback.message.answer(
        "💵 **Summani kiriting** (faqat raqam):\n\nMasalan: `50000`",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(TransactionSG.waiting_for_amount)
async def process_amount_input(message: Message, state: FSMContext):
    text = message.text.strip()
    
    try:
        amount = float(text.replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, faqat musbat raqam kiriting (masalan: `50000`):")
        return

    data = await state.get_data()
    user_id = message.from_user.id
    account_id = data["account_id"]
    tx_type = data["tx_type"]

    if tx_type == "expense":
        acc_data = await get_account_by_id(account_id)
        current_bal = acc_data["balance"] if acc_data else 0.0
        if amount > current_bal:
            acc_name = acc_data["name"] if acc_data else "Hamyon"
            await message.answer(
                f"❌ **Mablag' yetarli emas!**\n\n"
                f"💳 Hamyon: **{acc_name}**\n"
                f"💵 Hozirgi balans: **{current_bal:,.2f} so'm**\n"
                f"Siz kiritmoqchi bo'lgan summa: **{amount:,.2f} so'm**\n\n"
                "Iltimos, balansdan oshmaydigan summa kiriting:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="Markdown"
            )
            return

    await state.update_data(amount=amount)
    await state.set_state(TransactionSG.waiting_for_comment)

    cat_data = await get_category_by_id(data["category_id"])
    cat_name = cat_data["name"] if cat_data else "Bo'lim"
    
    await message.answer(
        f"📝 **Sabab/izoh yozing:**\n\n"
        f"({cat_name} bo'limiga {amount:,.0f} so'm — nima uchun?)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TransactionSG.waiting_for_comment)
async def process_comment_input(message: Message, state: FSMContext):
    comment = message.text.strip()
    if not comment:
        await message.answer("❌ Iltimos, sabab/izoh yozing:")
        return
    
    await save_and_respond(message, state, comment)

# --- TEZKOR MATN PARSERI (FAST PARSER) ---

@router.message(F.text.regexp(r"^([\+\-])\s*(\d+(?:[\.\\,]\d+)?)\s+(.+)$"))
async def fast_text_parser(message: Message):
    """
    Qisqa matn parseri:
    -50000 do'kon un va yog'
    +2000000 oylik avans
    """
    match = re.match(r"^([\+\-])\s*(\d+(?:[\.\,]\d+)?)\s+(.+)$", message.text.strip())
    if not match:
        return

    sign, amount_str, rest = match.groups()
    tx_type = "income" if sign == "+" else "expense"
    
    try:
        amount = float(amount_str.replace(" ", "").replace(",", "."))
        if amount <= 0:
            return
    except ValueError:
        return

    user_id = message.from_user.id
    
    # Rest qismini ajratish: birinchi so'z - kategoriya nomi, qolgani - izoh
    rest_parts = rest.strip().split(maxsplit=1)
    cat_name_candidate = rest_parts[0]
    comment = rest_parts[1] if len(rest_parts) > 1 else rest.strip()

    # Kategoriya qidirish (avval 1-so'z bo'yicha, bo'lmasa to'liq rest bo'yicha)
    cat = await get_category_by_name(user_id, cat_name_candidate, tx_type)
    if not cat and len(rest_parts) > 1:
        cat = await get_category_by_name(user_id, rest.strip(), tx_type)
        if cat:
            comment = rest.strip()

    if not cat:
        type_str = "kirim" if tx_type == "income" else "chiqim"
        await message.answer(
            f"❌ **'{cat_name_candidate}'** nomli {type_str} bo'limi topilmadi.\n"
            f"Iltimos, nomini to'g'ri yozing yoki **⚙️ Sozlamalar** bo'limidan ushbu bo'limni qo'shing.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    accounts = await get_accounts(user_id)
    if not accounts:
        await message.answer(
            "❌ Sizda hali birorta ham hamyon yo'q.\nAvval **⚙️ Sozlamalar** bo'limidan hamyon qo'shing.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    target_account = accounts[0]
    account_id = target_account["id"]

    if tx_type == "expense" and amount > target_account["balance"]:
        await message.answer(
            f"❌ **Mablag' yetarli emas!**\n\n"
            f"💳 Hamyon: **{target_account['name']}**\n"
            f"💵 Balans: **{target_account['balance']:,.2f} so'm**\n"
            f"Kerakli summa: **{amount:,.2f} so'm**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    tx_id = await add_transaction(
        user_id=user_id,
        amount=amount,
        tx_type=tx_type,
        category_id=cat["id"],
        account_id=account_id,
        comment=comment
    )

    acc_data = await get_account_by_id(account_id)
    new_balance = acc_data["balance"] if acc_data else 0.0
    
    warning_msg = ""
    if tx_type == "expense":
        warning_msg = await check_and_format_limit_warning(user_id, cat["id"], cat["name"])
        from database.db_manager import detect_and_mark_anomalies
        if await detect_and_mark_anomalies(user_id, tx_id, amount):
            warning_msg += "\n\n🚨 **YIRIK XARAJAT (ANOMALIYA):** Ushbu xarajat sizning o'rtacha xarajatingizdan 3 barobar yuqori!"

    type_str = "📥 Kirim" if tx_type == "income" else "📤 Chiqim"

    await message.answer(
        f"⚡ **Tezkor {type_str} saqlandi!**\n\n"
        f"Summa: **{amount:,.2f} so'm**\n"
        f"Bo'lim: **{cat['name']}**\n"
        f"Sabab: _{comment}_\n"
        f"Hamyon: **{target_account['name']}** (Yangi balans: **{new_balance:,.2f} so'm**)"
        f"{warning_msg}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
