from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db_manager import get_accounts, get_account_by_id, add_transfer
from keyboards.default_nav import get_main_keyboard, get_cancel_keyboard
from keyboards.inline_transfer import get_source_accounts_keyboard, get_target_accounts_keyboard
from states.transfer_states import TransferSG

router = Router()

@router.message(F.text == "🔄 O'tkazma")
async def start_transfer_flow(message: Message, state: FSMContext):
    user_id = message.from_user.id
    accounts = await get_accounts(user_id)
    
    if len(accounts) < 2:
        await message.answer(
            "❌ **O'tkazma qilish uchun sizda kamida 2 ta hamyon bo'lishi kerak.**\n\n"
            "Yangi hamyon qo'shish uchun **⚙️ Sozlamalar** -> **💳 Hamyonlarim** menyusiga o'ting.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    await state.set_state(TransferSG.waiting_for_source_account)
    await message.answer(
        "🔄 **Hamyonlararo o'tkazma**\n\n"
        "Mablag' qaysi hamyondan yechib olinsin (Jo'natuvchi hamyon)?",
        reply_markup=get_source_accounts_keyboard(accounts),
        parse_mode="Markdown"
    )

@router.callback_query(TransferSG.waiting_for_source_account, F.data.startswith("tr_src_"))
async def process_source_account_selection(callback: CallbackQuery, state: FSMContext):
    source_acc_id = int(callback.data.replace("tr_src_", ""))
    await state.update_data(source_acc_id=source_acc_id)
    
    user_id = callback.from_user.id
    accounts = await get_accounts(user_id)
    
    await state.set_state(TransferSG.waiting_for_target_account)
    await callback.message.edit_text(
        "📥 Mablag' qaysi hamyonga o'tkazilsin (Qabul qiluvchi hamyon)?",
        reply_markup=get_target_accounts_keyboard(accounts, exclude_account_id=source_acc_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(TransferSG.waiting_for_target_account, F.data.startswith("tr_tgt_"))
async def process_target_account_selection(callback: CallbackQuery, state: FSMContext):
    target_acc_id = int(callback.data.replace("tr_tgt_", ""))
    await state.update_data(target_acc_id=target_acc_id)
    await state.set_state(TransferSG.waiting_for_amount)
    
    await callback.message.delete()
    await callback.message.answer(
        "💵 **O'tkazma summasi va ixtiyoriy izohni kiriting**\n\n"
        "Masalan: `100000` yoki `100000 karta to'ldirish`:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(TransferSG.waiting_for_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    
    try:
        amount = float(parts[0].replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Iltimos, musbat raqam shaklida summa kiriting (masalan: `100000`):")
        return

    comment = parts[1].strip() if len(parts) > 1 else None
    
    data = await state.get_data()
    user_id = message.from_user.id
    source_acc_id = data["source_acc_id"]
    target_acc_id = data["target_acc_id"]

    src_acc = await get_account_by_id(source_acc_id)
    src_bal = src_acc["balance"] if src_acc else 0.0
    if amount > src_bal:
        src_name = src_acc["name"] if src_acc else "Hamyon"
        await message.answer(
            f"❌ **O'tkazma uchun mablag' yetarli emas!**\n\n"
            f"💳 Hamyon: **{src_name}**\n"
            f"💵 Hozirgi balans: **{src_bal:,.2f} so'm**\n"
            f"O'tkazmoqchi bo'lgan summa: **{amount:,.2f} so'm**\n\n"
            "Iltimos, mavjud balansdan kamroq summa kiriting:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return

    # DB o'tkazmasi
    await add_transfer(
        user_id=user_id,
        from_account_id=source_acc_id,
        to_account_id=target_acc_id,
        amount=amount,
        comment=comment
    )
    await state.clear()
    
    from_acc = await get_account_by_id(source_acc_id)
    to_acc = await get_account_by_id(target_acc_id)
    
    from_name = from_acc["name"] if from_acc else "Hamyon 1"
    from_bal = from_acc["balance"] if from_acc else 0.0
    to_name = to_acc["name"] if to_acc else "Hamyon 2"
    to_bal = to_acc["balance"] if to_acc else 0.0
    
    comment_str = f"\nIzoh: _{comment}_" if comment else ""
    
    await message.answer(
        f"✅ **O'tkazma muvaffaqiyatli amalga oshirildi!**\n\n"
        f"📤 Qayerdan: **{from_name}** (Yangi balans: **{from_bal:,.2f} so'm**)\n"
        f"📥 Qayerga: **{to_name}** (Yangi balans: **{to_bal:,.2f} so'm**)\n"
        f"💵 Summa: **{amount:,.2f} so'm**"
        f"{comment_str}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
