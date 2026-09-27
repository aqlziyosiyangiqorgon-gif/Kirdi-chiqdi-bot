import re
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

async def process_voice_with_gemini(
    file_path: str,
    user_categories: List[Dict[str, Any]],
    user_accounts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Google Gemini 2.5 Flash multimodal modeli orqali o'zbek tilidagi audio faylni to'g'ridan-to'g'ri
    tahlil qiladi: ham aniq transkripsiya qiladi, ham moliya ma'lumotlarini (summa, tur, bo'lim, hamyon, izoh)
    bitta so'rovda JSON qilib qaytaradi.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY sozlanmagan. Iltimos .env faylga GEMINI_API_KEY kiriting.")

    cat_names = [c["name"] for c in user_categories]
    acc_names = [a["name"] for a in user_accounts]

    system_instruction = (
        "Siz O'zbekiston moliyaviy muhitini, o'zbek tili fonetikasi, shevalari va so'zlashuv uslubini chuqur tushunadigan shaxsiy moliya assistentisiz (Siri/Alisa kabi).\n"
        "Foydalanuvchi Telegram orqali O'ZBEK TILIDA audio ovozli xabar yuboradi (audio/ogg).\n\n"
        "VAZIFANGIZ:\n"
        "Ovozdan 2 ta holatdan birini aniqlang:\n\n"
        "HOLAT 1: BOTNI BOSHQARISH BUYRUQLARI (action):\n"
        "Foydalanuvchi moliya kiritmayapti, balki ma'lumot yoki hisobot so'rayapti:\n"
        "- 'balansni ko'rsat', 'qancha pulim bor', 'kassada nima bor', 'balans' -> action: 'balance'\n"
        "- '1 oylik hisobotni ber', 'oylik hisobot', 'bu oylik rasxodlar', 'oylik tahlil' -> action: 'report_monthly'\n"
        "- 'bugungi hisobot', 'bugun qancha ketdi', 'kunlik hisobot' -> action: 'report_daily'\n"
        "- 'katta xarajatlar', 'anomaliyalar', 'yirik chiqimlar' -> action: 'report_anomalies'\n"
        "- 'hamyonlarimni ko'rsat', 'hamyonlar' -> action: 'wallets'\n"
        "- 'maslahat ber', 'qanday tejashim mumkin', 'moliyaviy maslahat', 'maslahatchi' -> action: 'advice'\n"
        "- 'sozlamalar', 'sozlamalarni och', 'menyuni och' -> action: 'settings'\n"
        "- 'hisobotlar', 'hisobot menyusi' -> action: 'reports_menu'\n\n"
        "HOLAT 2: TRANZAKSIYA (action: 'transaction'):\n"
        "Foydalanuvchi xarajat yoki tushum qilyapti (masalan: 'oziq-ovqatga 50 ming ketdi', 'oylik tushdi 4 million'):\n"
        "- amount: aniq summa float (50 ming -> 50000, 1.5 mln -> 1500000)\n"
        "- type: 'expense' (chiqim qildim, ketdi, sarfladim, to'ladim, oldim) yoki 'income' (tushdi, kirdi, oylik, daromad)\n"
        "- category_name: berilgan ro'yxatdan eng mos bo'lim nomi\n"
        "- account_name: eslatilgan hamyon yoki null\n"
        "- comment: xarajat/kirim maqsadi haqida qisqa izoh\n\n"
        "Har doim transcribed_text ga sof o'zbek adabiy tilida aytilgan gapni yozing."
    )

    user_prompt = (
        f"Mavjud bo'limlar (kategoriyalar): {json.dumps(cat_names, ensure_ascii=False)}\n"
        f"Mavjud hamyonlar: {json.dumps(acc_names, ensure_ascii=False)}\n\n"
        "Audioni tahlil qiling va qat'iy quyidagi JSON formatida qaytaring:\n"
        "Agar BUYRUQ bo'lsa:\n"
        '{"action": "balance" | "report_monthly" | "report_daily" | "report_anomalies" | "wallets" | "advice" | "settings" | "reports_menu", "transcribed_text": "gap"}\n\n'
        "Agar TRANZAKSIYA bo'lsa:\n"
        '{"action": "transaction", "transcribed_text": "gap", "amount": 50000.0, "type": "expense" | "income", "category_name": "...", "account_name": "...", "comment": "..."}'
    )

    def _call_gemini():
        client = genai.Client(api_key=GEMINI_API_KEY)
        uploaded_file = client.files.upload(file=file_path, mime_type="audio/ogg")
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    uploaded_file,
                    user_prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            return response.text
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                logger.warning(f"Gemini uploaded file delete error: {e}")

    try:
        raw_result = await asyncio.to_thread(_call_gemini)
        clean_text = raw_result.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

        data = json.loads(clean_text)
        return data
    except Exception as e:
        logger.error(f"Gemini voice processing error: {e}")
        raise RuntimeError(f"Ovozni qayta ishlashda xatolik yuz berdi: {e}")

async def process_receipt_image(
    image_path: str,
    user_categories: List[Dict[str, Any]],
    user_accounts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Google Gemini 2.5 Flash multimodal orqali chek, Payme, Click, Uzum Bank
    yoki to'lov skrinshotini o'qib, summa, bo'lim, hamyon va izohni chiqaradi.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY sozlanmagan.")

    cat_names = [c["name"] for c in user_categories]
    acc_names = [a["name"] for a in user_accounts]

    system_instruction = (
        "Siz O'zbekistondagi to'lov tizimlari (Click, Payme, Uzum Bank, Anorbank va b.) skrinshotlari "
        "hamda savdo do'koni cheklarini (Korzinka, Havas, Makro, dorixona, yoqilg'i quyish) "
        "100% aniqlik bilan o'qiydigan professional moliyaviy audit assistentisiz.\n\n"
        "VAZIFANGIZ:\n"
        "Rasm / chekdan quyidagi ma'lumotlarni ajratib oling:\n"
        "1. amount: To'langan yoki qabul qilingan yakuniy summa (faqat musbat son float, masalan 45000.0).\n"
        "2. type: 'expense' (xarid, chiqim, to'lov) yoki 'income' (kartaga tushgan pul, kiruvchi o'tkazma).\n"
        "3. category_name: Mavjud bo'limlar ichidan eng mos kelgani (masalan Korzinka -> Oziq-ovqat, Benzin -> Transport). Mos topilmasa 'Boshqa'.\n"
        "4. account_name: Agar skrinshotda karta yoki hamyon ko'rsatilgan bo'lsa ro'yxatdagi hamyon nomi, aks holda null.\n"
        "5. comment: Magazin / to'lov qabul qiluvchi nomi va qisqa izoh (masalan: 'Korzinka xaridi', 'Payme orqali to'lov', 'Benzin quyish')."
    )

    user_prompt = (
        f"Mavjud bo'limlar: {json.dumps(cat_names, ensure_ascii=False)}\n"
        f"Mavjud hamyonlar: {json.dumps(acc_names, ensure_ascii=False)}\n\n"
        "Chek yoki skrinshotni tahlil qiling va qat'iy quyidagi JSON formatida javob bering:\n"
        "{\n"
        '  "amount": 50000.0,\n'
        '  "type": "expense",\n'
        '  "category_name": "Mos bo\'lim",\n'
        '  "account_name": "Hamyon yoki null",\n'
        '  "comment": "Qisqa izoh"\n'
        "}"
    )

    def _call_gemini():
        client = genai.Client(api_key=GEMINI_API_KEY)
        ext = image_path.lower().split('.')[-1]
        mime_type = 'image/png' if ext == 'png' else 'image/jpeg'
        uploaded_file = client.files.upload(file=image_path, mime_type=mime_type)
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    uploaded_file,
                    user_prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            return response.text
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                logger.warning(f"Gemini receipt file delete error: {e}")

    try:
        raw_result = await asyncio.to_thread(_call_gemini)
        clean_text = raw_result.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
        data = json.loads(clean_text)
        return data
    except Exception as e:
        logger.error(f"Gemini receipt processing error: {e}")
        raise RuntimeError(f"Chekni o'qishda xatolik yuz berdi: {e}")

async def get_financial_advice(
    user_name: str,
    total_income: float,
    total_expense: float,
    categories_summary: List[Dict[str, Any]],
    accounts_summary: List[Dict[str, Any]]
) -> str:
    """
    Foydalanuvchining real oylik xarajat va daromadlari asosida
    shaxsiy professional moliyaviy tahlil va tejash bo'yicha aniq maslahat beradi.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY sozlanmagan.")

    cat_text = "\n".join([f"- {c['name']}: {c['spent']:,.0f} so'm" for c in categories_summary])
    acc_text = "\n".join([f"- {a['name']}: {a['balance']:,.0f} so'm" for a in accounts_summary])

    prompt = (
        f"Foydalanuvchi: {user_name}\n"
        f"Oylik jami kirim: {total_income:,.0f} so'm\n"
        f"Oylik jami chiqim: {total_expense:,.0f} so'm\n"
        f"Hamyonlar qoldig'i:\n{acc_text}\n\n"
        f"Bo'limlar bo'yicha xarajatlar:\n{cat_text}\n\n"
        "Vazifangiz: Shaxsiy moliyaviy maslahatchi (CFO) sifatida foydalanuvchiga do'stona, aniq va professional maslahat bering:\n"
        "1. Xarajatlarning qaysi biri eng ko'p cho'ntakni teshyapti (tahlil).\n"
        "2. Keyingi oyda 10-20% tejash uchun 3 ta amaliy qadam.\n"
        "3. Moliyaviy xavfsizlik (zaxira jamg'arma) bo'yicha qisqa tavsiya.\n"
        "Javob o'zbek tilida, chiroyli formatda (emoji va punktlar bilan) bo'lsin."
    )

    def _call_gemini():
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        return response.text

    try:
        return await asyncio.to_thread(_call_gemini)
    except Exception as e:
        logger.error(f"Gemini advisor error: {e}")
        return "Hozirda tahlil qilishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring."



