import os
import tempfile
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from database.db_manager import (
    get_accounts,
    get_categories,
    get_category_by_name,
    add_transaction,
    get_account_by_id
)
from handlers.transactions import check_and_format_limit_warning
from services.voice_service import process_voice_with_gemini

router = Router()

@router.message(F.voice)
async def process_voice_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # 1. Hamyonlar va Kategoriyalarni bazadan olish
    accounts = await get_accounts(user_id)
    if not accounts:
        await message.answer("❌ Ovozli xabar kiritish uchun sizda kamida 1 ta hamyon bo'lishi kerak. **⚙️ Sozlamalar** bo'limidan hamyon qo'shing.")
        return

    categories = await get_categories(user_id)
    if not categories:
        await message.answer("❌ Ovozli xabar kiritish uchun sizda kamida 1 ta bo'lim bo'lishi kerak. **⚙️ Sozlamalar** bo'limidan bo'lim qo'shing.")
        return

    status_msg = await message.answer("🎙 **Ovoz qayta ishlanmoqda (Gemini 2.5 Flash)...**", parse_mode="Markdown")
    
    temp_path = None
    try:
        # 2. Ovozli xabarni yuklab olish (.ogg)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
            temp_path = tmp_file.name

        file_info = await bot.get_file(message.voice.file_id)
        await bot.download_file(file_info.file_path, destination=temp_path)

        # 3. Gemini 2.5 Flash orqali transkripsiya va tahlil (bitta so'rovda)
        parsed_data = await process_voice_with_gemini(temp_path, categories, accounts)
        transcribed_text = parsed_data.get("transcribed_text", "")
        action = parsed_data.get("action", "transaction")

        # --- OVOZLI BUYRUQLAR (SIRI/ALISA REJIMI) ---
        if action == "balance":
            total_net = sum(a['balance'] for a in accounts)
            text = f"🎙 _\"{transcribed_text}\"_\n\n💰 **Kassa va Hamyonlar Balansi:**\n\n"
            for acc in accounts:
                text += f"🔹 **{acc['name']}**: `{acc['balance']:,.2f} so'm`\n"
            text += f"\n💵 **Jami balans:** **{total_net:,.2f} so'm**"
            await status_msg.edit_text(text, parse_mode="Markdown")
            return

        elif action == "report_monthly":
            from database.db_manager import get_period_comparison, get_category_comparison
            from keyboards.inline_reports import get_reports_menu_keyboard
            comp = await get_period_comparison(user_id, period='month')
            cat_comp = await get_category_comparison(user_id, period='month')
            inc = comp["income"]
            exp = comp["expense"]
            inc_icon = "🔺" if inc["is_increase"] else "🔻"
            exp_icon = "🔺" if exp["is_increase"] else "🔻"

            text = (
                f"🎙 _\"{transcribed_text}\"_\n\n"
                "📆 **1 Oylik Tahlil (Bu oy vs O'tgan oy):**\n\n"
                f"📥 **Kirim:** **{inc['current']:,.2f} so'm** ({inc_icon} {inc['percent']:.1f}%)\n"
                f"📤 **Chiqim:** **{exp['current']:,.2f} so'm** ({exp_icon} {exp['percent']:.1f}%)\n\n"
                "📊 **Asosiy xarajat bo'limlari:**\n"
            )
            if cat_comp:
                for c in cat_comp[:5]:
                    text += f"• **{c['category_name']}**: {c['current']:,.2f} so'm\n"
            else:
                text += "_Bo'limlar bo'yicha xarajatlar yo'q._"

            await status_msg.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
            return

        elif action == "report_daily":
            from database.db_manager import get_period_comparison
            from keyboards.inline_reports import get_reports_menu_keyboard
            comp = await get_period_comparison(user_id, period='day')
            inc = comp["income"]
            exp = comp["expense"]
            inc_icon = "🔺" if inc["is_increase"] else "🔻"
            exp_icon = "🔺" if exp["is_increase"] else "🔻"

            text = (
                f"🎙 _\"{transcribed_text}\"_\n\n"
                "📅 **Bugungi Tahlil:**\n\n"
                f"📥 **Kirim:** **{inc['current']:,.2f} so'm** ({inc_icon} {inc['percent']:.1f}%)\n"
                f"📤 **Chiqim:** **{exp['current']:,.2f} so'm** ({exp_icon} {exp['percent']:.1f}%)"
            )
            await status_msg.edit_text(text, reply_markup=get_reports_menu_keyboard(), parse_mode="Markdown")
            return

        elif action == "wallets":
            text = f"🎙 _\"{transcribed_text}\"_\n\n💳 **Hamyonlaringiz:**\n\n"
            for a in accounts:
                text += f"• **{a['name']}**: `{a['balance']:,.2f} so'm`\n"
            await status_msg.edit_text(text, parse_mode="Markdown")
            return

        elif action == "advice":
            from services.voice_service import get_financial_advice
            from database.db_manager import get_category_comparison, get_period_comparison

            user_name = message.from_user.full_name or "Foydalanuvchi"
            comp = await get_period_comparison(user_id, period='month')
            cat_comp = await get_category_comparison(user_id, period='month')

            inc_total = comp["income"]["current"]
            exp_total = comp["expense"]["current"]
            cat_list = [{"name": c["category_name"], "spent": c["current"]} for c in (cat_comp or [])]
            acc_list = [{"name": a["name"], "balance": a["balance"]} for a in (accounts or [])]

            advice_text = await get_financial_advice(
                user_name=user_name,
                total_income=inc_total,
                total_expense=exp_total,
                categories_summary=cat_list,
                accounts_summary=acc_list
            )
            await status_msg.edit_text(
                f"🎙 _\"{transcribed_text}\"_\n\n💡 **AI Moliyaviy Maslahatchi (CFO):**\n\n{advice_text}",
                parse_mode="Markdown"
            )
            return

        elif action in ("settings", "reports_menu"):
            from keyboards.inline_reports import get_reports_menu_keyboard
            from keyboards.inline_settings import get_settings_keyboard
            from config import ADMIN_IDS
            if action == "settings":
                is_adm = (user_id in ADMIN_IDS)
                await status_msg.edit_text(
                    f"🎙 _\"{transcribed_text}\"_\n\n⚙️ **Sozlamalar bo'limi:**",
                    reply_markup=get_settings_keyboard(is_admin=is_adm),
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(
                    f"🎙 _\"{transcribed_text}\"_\n\n📊 **Hisobotlar menyusi:**",
                    reply_markup=get_reports_menu_keyboard(),
                    parse_mode="Markdown"
                )
            return

        # --- TRANZAKSIYA MANTIQI ---
        if not parsed_data or parsed_data.get("amount", 0) <= 0:
            await status_msg.edit_text(
                f"🎙 **Ovozli xabar matni:**\n_\"{transcribed_text}\"_\n\n"
                "❌ **Ovozdan buyruq yoki summa aniqlanmadi.**\n"
                "Masalan:\n"
                "• *'Balansni ko'rsat'*\n"
                "• *'1 oylik hisobotni ber'*\n"
                "• *'Oziq-ovqatga 50 ming ketdi'*",
                parse_mode="Markdown"
            )
            return

        tx_type = parsed_data.get("type", "expense")
        amount = float(parsed_data.get("amount", 0))
        comment = parsed_data.get("comment", transcribed_text)

        # 5. Kategoriya moslashtirish (Fuzzy & Semantic)
        cat_name = parsed_data.get("category_name")
        target_cat = None
        
        type_cats = [c for c in categories if c.get("type") == tx_type]
        if not type_cats:
            type_cats = categories

        if cat_name:
            # Aniq nom bo'yicha
            target_cat = await get_category_by_name(user_id, cat_name, tx_type)
            # Qisman moslik bo'yicha (masalan: "Transport" va "Yo'l kira / Transport")
            if not target_cat:
                for c in type_cats:
                    if cat_name.lower() in c["name"].lower() or c["name"].lower() in cat_name.lower():
                        target_cat = c
                        break
            
        if not target_cat:
            # Agar 'Boshqa' degan bo'lim bo'lsa shuni, bo'lmasa ro'yxatdagi 1-bo'limni olamiz
            other_cat = next((c for c in type_cats if "boshqa" in c["name"].lower()), None)
            target_cat = other_cat if other_cat else type_cats[0]
            tx_type = target_cat.get("type", tx_type)

        # 6. Hamyon moslashtirish (Fallback)
        acc_name = parsed_data.get("account_name")
        target_acc = None
        
        if acc_name:
            for acc in accounts:
                if acc_name.lower() in acc["name"].lower() or acc["name"].lower() in acc_name.lower():
                    target_acc = acc
                    break
        if not target_acc:
            target_acc = accounts[0]  # Standart 1-hamyon

        # 7. Bazaga saqlash va limit tekshirish
        category_id = target_cat["id"]
        account_id = target_acc["id"]

        await add_transaction(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            category_id=category_id,
            account_id=account_id,
            comment=comment
        )

        acc_updated = await get_account_by_id(account_id)
        new_balance = acc_updated["balance"] if acc_updated else 0.0

        warning_msg = ""
        if tx_type == "expense":
            warning_msg = await check_and_format_limit_warning(user_id, category_id, target_cat["name"])

        type_title = "📥 Kirim" if tx_type == "income" else "📤 Chiqim"
        
        await status_msg.edit_text(
            f"🎙 **Ovozli xabar qabul qilindi!**\n\n"
            f"🗣 _\"{transcribed_text}\"_\n\n"
            f"✅ **{type_title} saqlandi:**\n"
            f"💵 Summa: **{amount:,.2f} so'm**\n"
            f"📁 Bo'lim: **{target_cat['name']}**\n"
            f"💳 Hamyon: **{target_acc['name']}** (Qoldiq: **{new_balance:,.2f} so'm**)"
            f"{warning_msg}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# =========================================================================
# 1. CHEK VA CLICK/PAYME SKRINSHOTLARINI AVTOMATIK O'QISH (OCR + GEMINI)
# =========================================================================

@router.message(F.photo)
async def process_receipt_photo(message: Message, bot: Bot):
    """
    Foydalanuvchi do'kon cheki, Payme, Click yoki Uzum skrinshotini yuborganda
    Gemini 2.5 Flash multimodal orqali summani, do'kon nomini va bo'limni o'qiydi.
    """
    from services.voice_service import process_receipt_image

    user_id = message.from_user.id
    accounts = await get_accounts(user_id)
    if not accounts:
        await message.answer("❌ Chek kiritish uchun sizda kamida 1 ta hamyon bo'lishi kerak.")
        return

    categories = await get_categories(user_id)
    if not categories:
        await message.answer("❌ Chek kiritish uchun sizda kamida 1 ta bo'lim bo'lishi kerak.")
        return

    status_msg = await message.answer("🧾 **Chek tahlil qilinmoqda (Gemini Vision)...**", parse_mode="Markdown")

    temp_path = None
    try:
        # Eng yuqori sifatli rasmni yuklab olamiz
        photo = message.photo[-1]
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            temp_path = tmp_file.name

        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_info.file_path, destination=temp_path)

        # Gemini 2.5 Flash multimodal chekni o'qiydi
        receipt_data = await process_receipt_image(temp_path, categories, accounts)

        amount = float(receipt_data.get("amount", 0))
        if amount <= 0:
            await status_msg.edit_text(
                "❌ **Chek yoki skrinshotdan to'lov summasi aniqlanmadi.**\n"
                "Iltimos, chek ravshan tushirilgan rasm yuboring.",
                parse_mode="Markdown"
            )
            return

        tx_type = receipt_data.get("type", "expense")
        comment = receipt_data.get("comment", "Chek orqali to'lov")

        # Kategoriya moslashtirish
        cat_name = receipt_data.get("category_name", "")
        type_cats = [c for c in categories if c.get("type") == tx_type]
        if not type_cats:
            type_cats = categories

        target_cat = None
        if cat_name:
            target_cat = await get_category_by_name(user_id, cat_name, tx_type)
            if not target_cat:
                for c in type_cats:
                    if cat_name.lower() in c["name"].lower() or c["name"].lower() in cat_name.lower():
                        target_cat = c
                        break

        if not target_cat:
            other_cat = next((c for c in type_cats if "boshqa" in c["name"].lower()), None)
            target_cat = other_cat if other_cat else type_cats[0]
            tx_type = target_cat.get("type", tx_type)

        # Hamyon moslashtirish
        acc_name = receipt_data.get("account_name")
        target_acc = None
        if acc_name:
            for acc in accounts:
                if acc_name.lower() in acc["name"].lower() or acc["name"].lower() in acc_name.lower():
                    target_acc = acc
                    break
        if not target_acc:
            target_acc = accounts[0]

        category_id = target_cat["id"]
        account_id = target_acc["id"]

        # Tranzaksiyani saqlash
        await add_transaction(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            category_id=category_id,
            account_id=account_id,
            comment=comment
        )

        acc_updated = await get_account_by_id(account_id)
        new_balance = acc_updated["balance"] if acc_updated else 0.0

        warning_msg = ""
        if tx_type == "expense":
            warning_msg = await check_and_format_limit_warning(user_id, category_id, target_cat["name"])

        type_title = "📥 Kirim" if tx_type == "income" else "📤 Chiqim"

        await status_msg.edit_text(
            f"🧾 **Chek muvaffaqiyatli saqlandi!**\n\n"
            f"✅ **{type_title} kiritildi:**\n"
            f"💵 Summa: **{amount:,.2f} so'm**\n"
            f"🏪 Izoh: **{comment}**\n"
            f"📁 Bo'lim: **{target_cat['name']}**\n"
            f"💳 Hamyon: **{target_acc['name']}** (Qoldiq: **{new_balance:,.2f} so'm**)"
            f"{warning_msg}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Chekni o'qishda xatolik: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# =========================================================================
# 2. AI MOLIYAVIY MASLAHATCHI (SHAXSIY CFO)
# =========================================================================

@router.callback_query(F.data == "ai_financial_advice")
async def trigger_ai_financial_advice(callback: CallbackQuery):
    """Foydalanuvchiga uning xarajatlari asosida AI shaxsiy maslahat beradi."""
    from services.voice_service import get_financial_advice
    from database.db_manager import get_category_comparison, get_period_comparison

    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or "Foydalanuvchi"

    status_msg = await callback.message.answer("🧠 **AI Maslahatchi xarajatlaringizni tahlil qilmoqda...**", parse_mode="Markdown")
    await callback.answer()

    try:
        comp = await get_period_comparison(user_id, period='month')
        cat_comp = await get_category_comparison(user_id, period='month')
        accounts = await get_accounts(user_id)

        inc_total = comp["income"]["current"]
        exp_total = comp["expense"]["current"]

        cat_list = [{"name": c["category_name"], "spent": c["current"]} for c in (cat_comp or [])]
        acc_list = [{"name": a["name"], "balance": a["balance"]} for a in (accounts or [])]

        advice_text = await get_financial_advice(
            user_name=user_name,
            total_income=inc_total,
            total_expense=exp_total,
            categories_summary=cat_list,
            accounts_summary=acc_list
        )

        await status_msg.edit_text(
            f"💡 **AI Moliyaviy Maslahatchi (CFO):**\n\n{advice_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Tahlilda xatolik: {e}")

