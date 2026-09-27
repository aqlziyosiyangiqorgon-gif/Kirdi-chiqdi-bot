import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from config import ADMIN_IDS, DB_NAME
from database.db_manager import (
    get_all_users,
    get_global_stats,
    get_user_profile,
    get_user_transactions
)
from keyboards.inline_admin import (
    get_admin_menu_keyboard,
    get_admin_users_keyboard,
    get_user_detail_keyboard,
    get_admin_back_keyboard
)

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
@router.callback_query(F.data == "admin_menu")
async def show_admin_panel(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, Message):
            # Hech narsa ko'rsatmaslik yoki xavfsiz javob
            await event.answer("Buyruq topilmadi.")
        else:
            await event.answer("⛔ Ruxsat berilmagan!", show_alert=True)
        return

    stats = await get_global_stats()
    text = (
        "🛡️ **ADMIN BOSHQARUV PANELI**\n"
        "────────────────────────\n"
        f"👥 Foydalanuvchilar: **{stats['user_count']} nafar**\n"
        f"📝 Jami amaliyotlar: **{stats['tx_count']} ta**\n"
        f"💵 Tizimdagi aylanma: **{(stats['total_income'] + stats['total_expense']):,.0f} so'm**\n"
        "────────────────────────\n"
        "Kuzatmoqchi bo'lgan bo'limingizni tanlang:"
    )

    if isinstance(event, Message):
        await event.answer(text, reply_markup=get_admin_menu_keyboard(), parse_mode="Markdown")
    else:
        await event.message.edit_text(text, reply_markup=get_admin_menu_keyboard(), parse_mode="Markdown")
        await event.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan!", show_alert=True)
        return

    users = await get_all_users()
    if not users:
        await callback.message.edit_text(
            "👥 Hali ro'yxatdan o'tgan foydalanuvchilar yo'q.",
            reply_markup=get_admin_back_keyboard()
        )
        await callback.answer()
        return

    text = (
        "👥 **Foydalanuvchilar ro'yxati**\n\n"
        "Harakatlarini ko'rish uchun kerakli foydalanuvchini tanlang:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_users_keyboard(users),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_u_"))
async def admin_user_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan!", show_alert=True)
        return

    target_id = int(callback.data.replace("admin_u_", ""))
    profile = await get_user_profile(target_id)
    if not profile:
        await callback.answer("❌ Foydalanuvchi ma'lumotlari topilmadi!", show_alert=True)
        return

    txs = await get_user_transactions(target_id, limit=8)

    handle = f" (@{profile['username']})" if profile.get('username') else ""
    created = str(profile.get('created_at', ''))[:10]
    last_act = str(profile.get('last_active', ''))[:16]

    text = (
        f"👤 **Foydalanuvchi:** {profile['full_name']}{handle}\n"
        f"🆔 ID: `{profile['user_id']}`\n"
        f"📅 Qo'shilgan: {created} | 🕒 Faollik: {last_act}\n"
        "────────────────────────\n"
        f"📥 Jami Kirim: **+{profile['total_income']:,.0f} so'm**\n"
        f"📤 Jami Chiqim: **-{profile['total_expense']:,.0f} so'm**\n"
    )

    # Hamyonlar qoldig'i
    if profile.get("accounts"):
        text += "💳 **Hamyonlari:**\n"
        for acc in profile["accounts"]:
            text += f"   • {acc['name']}: `{acc['balance']:,.0f} so'm`\n"
        text += f"   💰 Jami qoldiq: **{profile['total_balance']:,.0f} so'm**\n"

    text += "────────────────────────\n"
    text += "📋 **Oxirgi harakatlari:**\n"

    if not txs:
        text += "   _Hali amaliyotlar mavjud emas._"
    else:
        for i, t in enumerate(txs, 1):
            is_inc = (t['type'] == 'income')
            icon = "🟢 +" if is_inc else "🔴 -"
            amt = t.get('amount', 0.0)
            cat = t.get('category_name') or "O'tkazma"
            comment = f" — _{t['comment']}_" if t.get('comment') else ""
            date_s = str(t.get('created_at', ''))[5:16]

            text += f"{i}. {icon}**{amt:,.0f}** so'm | {cat}{comment} `({date_s})`\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_user_detail_keyboard(target_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan!", show_alert=True)
        return

    stats = await get_global_stats()
    text = (
        "📊 **TIZIMNING TO'LIQ STATISTIKASI**\n"
        "────────────────────────\n"
        f"👥 Foydalanuvchilar: **{stats['user_count']} nafar**\n"
        f"📝 Barcha amallar: **{stats['tx_count']} ta**\n"
        f"📥 Jami kiritilgan: **+{stats['total_income']:,.0f} so'm**\n"
        f"📤 Jami sarflangan: **-{stats['total_expense']:,.0f} so'm**\n"
        f"🔄 O'tkazmalar: **{stats['total_transfers']:,.0f} so'm**\n"
        f"💰 Hamyonlardagi jami mablag': **{stats['total_balance']:,.0f} so'm**\n"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_backup")
async def admin_download_backup(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan!", show_alert=True)
        return

    if not os.path.exists(DB_NAME):
        await callback.answer("❌ Baza fayli topilmadi!", show_alert=True)
        return

    status = await callback.message.answer("⏳ Baza fayli jo'natilmoqda...")
    try:
        doc = FSInputFile(DB_NAME, filename=f"finance_backup_{os.path.basename(DB_NAME)}")
        await callback.message.answer_document(
            document=doc,
            caption=f"💾 **To'liq baza zaxirasi (.db)**\n📦 Hajmi: {os.path.getsize(DB_NAME):,} bayt",
            parse_mode="Markdown"
        )
        await status.delete()
        await callback.answer("✅ Baza fayli yuborildi!")
    except Exception as e:
        await status.edit_text(f"❌ Xatolik: {e}")

@router.callback_query(F.data == "admin_close")
async def admin_close_panel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()
