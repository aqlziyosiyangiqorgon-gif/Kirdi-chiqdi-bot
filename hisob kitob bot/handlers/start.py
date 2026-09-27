from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from keyboards.default_nav import get_main_keyboard
from database.db_manager import (
    get_categories, get_accounts, add_category, add_account, register_or_update_user
)

router = Router()


# Standart kategoriyalar (emoji + nom)
DEFAULT_CATEGORIES = {
    "income": [
        "🎮 O'yinlar",
        "💰 Oylik",
    ],
    "expense": [
        "🛒 Do'kon",
        "🚕 Yo'l kira",
        "🏪 Bozor",
        "🏠 Kommunal to'lovlar",
        "📱 Telefon",
        "📺 Obunalar",
        "🍽 Ovqatlanish",
        "🌐 Internet",
        "🤲 Xayriya",
        "🤍 ASMO",
    ]
}

DEFAULT_ACCOUNT = "💳 Asosiy hamyon"

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start buyrug'i — kategoriyalar va hamyon avtomatik yaratiladi."""
    await state.clear()
    user_id = message.from_user.id

    # Foydalanuvchini bazaga yozish/yangilash
    await register_or_update_user(
        user_id=user_id,
        full_name=message.from_user.full_name or "Noma'lum",
        username=message.from_user.username
    )

    # Agar foydalanuvchida hali kategoriya yo'q bo'lsa — standartlarni qo'shamiz
    existing_cats = await get_categories(user_id)
    if not existing_cats:
        for cat_name in DEFAULT_CATEGORIES["income"]:
            await add_category(user_id, cat_name, "income")
        for cat_name in DEFAULT_CATEGORIES["expense"]:
            await add_category(user_id, cat_name, "expense")

    # Agar hamyon yo'q bo'lsa — standart hamyon yaratamiz
    existing_accs = await get_accounts(user_id)
    if not existing_accs:
        await add_account(user_id, DEFAULT_ACCOUNT, 0.0)

    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}! 👋\n"
        "Shaxsiy moliya va hisob-kitob botiga xush kelibsiz.\n\n"
        "✅ Kategoriyalar va hamyon tayyor!\n"
        "Boshlash uchun quyidagi menyulardan birini tanlang:",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("cancel"))
@router.message(F.text == "❌ Bekor qilish")
async def cmd_cancel(message: Message, state: FSMContext):
    """FSM holatini bekor qilish handleri."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await message.answer(
        "Amal bekor qilindi.",
        reply_markup=get_main_keyboard()
    )
