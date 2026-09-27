from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, ADMIN_IDS
from database.db_manager import get_accounts, add_account, get_categories, add_category
from keyboards.default_nav import get_main_keyboard, get_cancel_keyboard
from keyboards.inline_settings import (
    get_settings_keyboard,
    get_accounts_keyboard,
    get_categories_menu_keyboard,
    get_cat_type_select_keyboard
)
from states.settings_states import AddAccountSG, AddCategorySG

router = Router()

# --- SOZLAMALAR MENYUSI ---

@router.message(F.text == "⚙️ Sozlamalar")
async def open_settings(message: Message):
    is_adm = (message.from_user.id in ADMIN_IDS)
    await message.answer(
        "⚙️ **Sozlamalar bo'limi**\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=get_settings_keyboard(is_admin=is_adm),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "settings_main")
async def settings_main_callback(callback: CallbackQuery):
    is_adm = (callback.from_user.id in ADMIN_IDS)
    await callback.message.edit_text(
        "⚙️ **Sozlamalar bo'limi**\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=get_settings_keyboard(is_admin=is_adm),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "settings_back")
async def settings_back_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Bosh menyudasiz.", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Amal bekor qilindi.", reply_markup=get_main_keyboard())
    await callback.answer()

# --- HAMYONLAR BOSHQARUVI ---

@router.callback_query(F.data == "settings_accounts")
async def list_accounts_callback(callback: CallbackQuery):
    accounts = await get_accounts(user_id=callback.from_user.id)
    if not accounts:
        text = "💳 Sizda hali hamyonlar yo'q. Yangi hamyon qo'shing."
    else:
        text = "💳 **Sizning hamyonlaringiz:**\n\n"
        for acc in accounts:
            text += f"• **{acc['name']}**: {acc['balance']:,.2f} so'm\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_accounts_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_account")
async def start_add_account(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddAccountSG.waiting_for_name)
    await callback.message.delete()
    await callback.message.answer(
        "💳 **Yangi hamyon nomini kiriting** (masalan: `Naqd` yoki `Uzcard`):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddAccountSG.waiting_for_name)
async def process_account_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Hamyon nomi bo'sh bo'lishi mumkin emas. Qayta kiriting:")
        return
    await state.update_data(account_name=name)
    await state.set_state(AddAccountSG.waiting_for_balance)
    await message.answer(
        f"Hamyon nomi: **{name}**\n\nEndi boshlang'ich qoldiq summasini kiriting (masalan: `500000` yoki `0`):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(AddAccountSG.waiting_for_balance)
async def process_account_balance(message: Message, state: FSMContext):
    try:
        balance = float(message.text.strip().replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Iltimos, faqat raqamlardan iborat summa kiriting (masalan: 500000 yoki 0):")
        return
    
    data = await state.get_data()
    acc_name = data.get("account_name")
    
    await add_account(user_id=message.from_user.id, name=acc_name, balance=balance)
    await state.clear()
    
    await message.answer(
        f"✅ **Muvaffaqiyatli saqlandi!**\n\nHamyon: **{acc_name}**\nBoshlang'ich balans: **{balance:,.2f} so'm**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# --- BO'LIMLAR (KATEGORIYALAR) BOSHQARUVI ---

@router.callback_query(F.data == "settings_categories")
async def list_categories_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📁 **Bo'limlar boshqaruvi**\n\nKirim yoki chiqim bo'limlarini ko'rish yoki yangi bo'lim qo'shish uchun tugmalardan birini bosing:",
        reply_markup=get_categories_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cats_income")
async def list_income_cats_callback(callback: CallbackQuery):
    cats = await get_categories(user_id=callback.from_user.id, cat_type="income")
    if not cats:
        text = "📥 Sizda hali kirim bo'limlari yo'q."
    else:
        text = "📥 **Kirim bo'limlaringiz:**\n\n"
        for c in cats:
            text += f"• **{c['name']}**\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_categories_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cats_expense")
async def list_expense_cats_callback(callback: CallbackQuery):
    cats = await get_categories(user_id=callback.from_user.id, cat_type="expense")
    if not cats:
        text = "📤 Sizda hali chiqim bo'limlari yo'q."
    else:
        text = "📤 **Chiqim bo'limlaringiz:**\n\n"
        for c in cats:
            limit_str = f" (Oylik limit: {c['monthly_limit']:,.2f} so'm)" if c['monthly_limit'] > 0 else ""
            text += f"• **{c['name']}**{limit_str}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_categories_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "add_category")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategorySG.waiting_for_type)
    await callback.message.edit_text(
        "📁 **Yangi bo'lim turini tanlang:**",
        reply_markup=get_cat_type_select_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(AddCategorySG.waiting_for_type, F.data.in_({"cat_type_income", "cat_type_expense"}))
async def process_category_type(callback: CallbackQuery, state: FSMContext):
    cat_type = "income" if callback.data == "cat_type_income" else "expense"
    await state.update_data(cat_type=cat_type)
    await state.set_state(AddCategorySG.waiting_for_name)
    
    type_label = "Kirim" if cat_type == "income" else "Chiqim"
    await callback.message.delete()
    await callback.message.answer(
        f"📁 Bo'lim turi: **{type_label}**\n\nEndi bo'lim nomini kiriting (masalan: `Oylik` yoki `Do'kon`):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddCategorySG.waiting_for_name)
async def process_category_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Bo'lim nomi bo'sh bo'lishi mumkin emas. Qayta kiriting:")
        return
    
    data = await state.get_data()
    cat_type = data.get("cat_type")
    await state.update_data(category_name=name)
    
    if cat_type == "expense":
        await state.set_state(AddCategorySG.waiting_for_limit)
        await message.answer(
            f"Chiqim bo'limi: **{name}**\n\nOylik limit belgilaysizmi? Summani kiriting yoki limit bo'lmasa **0** deb yuboring:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Income category doesn't require a monthly limit
        await add_category(user_id=message.from_user.id, name=name, cat_type="income", monthly_limit=0.0)
        await state.clear()
        await message.answer(
            f"✅ **Muvaffaqiyatli saqlandi!**\n\nKirim bo'limi: **{name}**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

@router.message(AddCategorySG.waiting_for_limit)
async def process_category_limit(message: Message, state: FSMContext):
    try:
        monthly_limit = float(message.text.strip().replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Iltimos, faqat raqamlardan iborat summa kiriting (masalan: 500000 yoki 0):")
        return
    
    data = await state.get_data()
    cat_name = data.get("category_name")
    
    await add_category(user_id=message.from_user.id, name=cat_name, cat_type="expense", monthly_limit=monthly_limit)
    await state.clear()
    
    limit_text = f"**{monthly_limit:,.2f} so'm**" if monthly_limit > 0 else "Limit belgilanmadi"
    await message.answer(
        f"✅ **Muvaffaqiyatli saqlandi!**\n\nChiqim bo'limi: **{cat_name}**\nOylik limit: {limit_text}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
