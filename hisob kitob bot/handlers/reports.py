from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.db_manager import (
    get_period_comparison,
    get_category_comparison,
    get_recent_anomalies,
    get_accounts,
    get_detailed_transactions
)
from keyboards.inline_reports import get_reports_menu_keyboard

router = Router()

@router.message(F.text == "💰 Balans")
async def show_balance_summary(message: Message):
    user_id = message.from_user.id
    accounts = await get_accounts(user_id)
    
    if not accounts:
        await message.answer(
            "💳 **Kassada ma'lumot yo'q.**\nSizda hali birorta ham hamyon mavjud emas.",
            parse_mode="Markdown"
        )
        return
        
    text = "💰 **Kassa va Hamyonlar Balansi**\n\n"
    total_net = 0.0
    for acc in accounts:
        text += f"🔹 **{acc['name']}**: `{acc['balance']:,.2f} so'm`\n"
        total_net += acc['balance']
        
    text += f"\n💵 **Jami kassadagi pul:** **{total_net:,.2f} so'm**"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📊 Hisobot")
async def open_reports_menu(message: Message):
    await message.answer(
        "📊 **Moliya Tahlili va Hisobotlar**\n\nQuyidagi tahlil turlaridan birini tanlang:",
        reply_markup=get_reports_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "report_daily")
async def process_daily_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    comp = await get_period_comparison(user_id, period='day')
    
    inc = comp["income"]
    exp = comp["expense"]
    
    # Indikatorlar
    # Kirim: oshsa 🔺 (yashil/yaxshi), kamaysa 🔻
    inc_icon = "🔺" if inc["is_increase"] else "🔻"
    # Chiqim: oshsa 🔺 (qizil/ogohlantirish), kamaysa 🔻 (yashil/tejamkorlik)
    exp_icon = "🔺" if exp["is_increase"] else "🔻"
    exp_status = "⚠️ Ko'paygan" if exp["is_increase"] else "✅ Tejamkorlik"
    
    text = (
        "📅 **Bugungi Tahlil (vs Kecha)**\n\n"
        f"📥 **Kirim:**\n"
        f"• Bugun: **{inc['current']:,.2f} so'm**\n"
        f"• Kecha: **{inc['previous']:,.2f} so'm**\n"
        f"• O'zgarish: {inc_icon} **{inc['percent']:.1f}%**\n\n"
        f"📤 **Chiqim ({exp_status}):**\n"
        f"• Bugun: **{exp['current']:,.2f} so'm**\n"
        f"• Kecha: **{exp['previous']:,.2f} so'm**\n"
        f"• O'zgarish: {exp_icon} **{exp['percent']:.1f}%**"
    )
    
    await callback.message.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "report_monthly")
async def process_monthly_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    comp = await get_period_comparison(user_id, period='month')
    cat_comp = await get_category_comparison(user_id, period='month')
    
    inc = comp["income"]
    exp = comp["expense"]
    
    inc_icon = "🔺" if inc["is_increase"] else "🔻"
    exp_icon = "🔺" if exp["is_increase"] else "🔻"
    
    text = (
        "📆 **Oylik Tahlil (Bu oy vs O'tgan oy)**\n\n"
        f"📥 **Jami Kirim:** **{inc['current']:,.2f} so'm** ({inc_icon} {inc['percent']:.1f}%)\n"
        f"📤 **Jami Chiqim:** **{exp['current']:,.2f} so'm** ({exp_icon} {exp['percent']:.1f}%)\n\n"
        "📊 **Bo'limlar Kesimidagi Xarajatlar:**\n"
    )
    
    if not cat_comp:
        text += "_Xarajat bo'limlari bo'yicha ma'lumot yo'q._"
    else:
        for c in cat_comp:
            icon = "🔺" if c["is_increase"] else "🔻"
            text += f"• **{c['category_name']}**: {c['current']:,.2f} so'm ({icon} {c['percent']:.1f}%)\n"

    # Batafsil tranzaksiya ro'yxati
    detailed = await get_detailed_transactions(user_id, days=30)
    if detailed:
        text += "\n📋 **Oxirgi amaliyotlar:**\n"
        for i, t in enumerate(detailed[:15], 1):
            icon = "📥" if t["type"] == "income" else "📤"
            cat = t.get("category_name") or "—"
            comment = t.get("comment") or "—"
            date = str(t["created_at"])[:10]
            text += f"{i}. {icon} **{t['amount']:,.0f}** — {cat} ({comment}) _{date}_\n"
            
    await callback.message.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "report_anomalies")
async def process_anomalies_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    anomalies = await get_recent_anomalies(user_id, days=30)
    
    text = "🚨 **Kutilmagan Yirik Xarajatlar (Oxirgi 30 kun)**\n\n"
    if not anomalies:
        text += "✅ Oxirgi 30 kunda g'ayritabiiy yirik xarajatlar kuzatilmadi."
    else:
        for a in anomalies:
            comment_str = f" ({a['comment']})" if a.get('comment') else ""
            date_str = str(a['created_at'])[:10]
            cat_name = a.get('category_name') or "Noma'lum"
            acc_name = a.get('account_name') or "Hamyon"
            text += f"• **{a['amount']:,.2f} so'm** — {cat_name}{comment_str}\n  _Sana: {date_str} | Hamyon: {acc_name}_\n\n"
            
    await callback.message.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "report_wallets")
async def process_wallets_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    accounts = await get_accounts(user_id)
    
    text = "💳 **Hamyonlar Qoldig'i va Umumiy Kapitalsiz**\n\n"
    total_net = sum(a['balance'] for a in accounts) if accounts else 0.0
    
    if not accounts:
        text += "_Sizda hali hamyonlar yo'q._"
    else:
        for acc in accounts:
            text += f"• **{acc['name']}**: {acc['balance']:,.2f} so'm\n"
        text += f"\n💰 **Jami Umumiy Balans:** **{total_net:,.2f} so'm**"
        
    await callback.message.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "download_pdf_report")
async def process_download_pdf(callback: CallbackQuery):
    import os
    from aiogram.types import FSInputFile
    from services.pdf_generator import generate_monthly_pdf
    from datetime import datetime
    
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    period_str = datetime.now().strftime("%B %Y")
    
    status_msg = await callback.message.answer("⏳ **PDF hisobot tayyorlanmoqda...**", parse_mode="Markdown")
    await callback.answer()
    
    pdf_path = None
    try:
        pdf_path = await generate_monthly_pdf(user_id, user_name, period_str)
        doc_file = FSInputFile(pdf_path, filename=f"Moliya_Hisoboti_{period_str}.pdf")
        
        await callback.message.answer_document(
            document=doc_file,
            caption=f"📄 **{period_str}** oyi bo'yicha to'liq moliya hisobotingiz tayyor bo'ldi!",
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ **PDF hisobot yaratishda xatolik:** {e}")
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass

