from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_reports_menu_keyboard() -> InlineKeyboardMarkup:
    """Hisobot va tahlil menyusi uchun Inline keyboard."""
    keyboard = [
        [InlineKeyboardButton(text="📅 Bugungi tahlil (vs Kecha)", callback_data="report_daily")],
        [InlineKeyboardButton(text="📆 Oylik tahlil (vs O'tgan oy)", callback_data="report_monthly")],
        [InlineKeyboardButton(text="🚨 Yirik xarajatlar (Anomaliyalar)", callback_data="report_anomalies")],
        [InlineKeyboardButton(text="💳 Hamyonlar qoldig'i", callback_data="report_wallets")],
        [InlineKeyboardButton(text="💡 AI Moliyaviy Maslahatchi (CFO)", callback_data="ai_financial_advice")],
        [InlineKeyboardButton(text="📄 PDF hisobotni yuklash", callback_data="download_pdf_report")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

