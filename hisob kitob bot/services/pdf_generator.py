import os
import re
import tempfile
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database.db_manager import (
    get_period_comparison,
    get_category_comparison_all,
    get_recent_anomalies,
    get_accounts,
    get_detailed_transactions
)

# Shriftlarni ro'yxatdan o'tkazish (O'zbekcha harflar va chiroyli shrift)
FONT_NAME = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

try:
    if os.path.exists('C:/Windows/Fonts/arial.ttf') and os.path.exists('C:/Windows/Fonts/arialbd.ttf'):
        pdfmetrics.registerFont(TTFont('ArialApp', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('ArialApp-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        FONT_NAME = 'ArialApp'
        FONT_BOLD = 'ArialApp-Bold'
except Exception:
    pass

def clean_text_for_pdf(text: Optional[str]) -> str:
    """Emoji va maxsus belgilarni tozalaydi, kvadrat bo'lib chiqishini oldini oladi."""
    if not text:
        return ""
    # Emojilarni va maxsus simvollarni tozalash (faqat oddiy matn va harflarni qoldirish)
    cleaned = re.sub(r'[^\w\s\-\.,\'\"\(\)\:\+\/\?\!\%\@]', '', text, flags=re.UNICODE)
    return cleaned.strip()

UZ_MONTHS = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
}

def get_uz_period_str() -> str:
    now = datetime.now()
    return f"{UZ_MONTHS.get(now.month, 'Davr')} {now.year}"

async def generate_monthly_pdf(user_id: int, user_name: str, period_str: Optional[str] = None) -> str:
    """
    Foydalanuvchining oylik moliya hisobotini professional PDF formatida shakllantiradi.
    """
    if not period_str or any(en in period_str for en in ("September", "October", "November", "December", "January", "February", "March", "April", "May", "June", "July", "August")):
        period_str = get_uz_period_str()

    display_name = user_name.strip() if user_name and user_name.strip() and user_name != "." else f"Foydalanuvchi #{user_id}"
    display_name = clean_text_for_pdf(display_name) or f"Foydalanuvchi #{user_id}"

    # 1. Bazadan barcha ma'lumotlarni yig'ish
    comp = await get_period_comparison(user_id, period='month')
    cat_all = await get_category_comparison_all(user_id, period='month')
    anomalies = await get_recent_anomalies(user_id, days=30)
    accounts = await get_accounts(user_id)
    detailed_txs = await get_detailed_transactions(user_id, days=30)

    total_inc = comp["income"]["current"]
    total_exp = comp["expense"]["current"]
    net_diff = total_inc - total_exp
    total_wallets = sum(a["balance"] for a in accounts) if accounts else 0.0

    # 2. PDF Hujjatini sozlash
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"Moliya_Hisoboti_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    # Stillar
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_CENTER,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER,
        spaceAfter=12
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_LEFT
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
        alignment=TA_LEFT
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_LEFT
    )

    elements = []

    # Sarlavha
    elements.append(Paragraph("SHAXSIY MOLIYA HISOBOTI", title_style))
    elements.append(Paragraph(f"Foydalanuvchi: <b>{display_name}</b> &nbsp;|&nbsp; Davr: <b>{period_str}</b> &nbsp;|&nbsp; Generatsiya vaqti: {datetime.now().strftime('%d.%m.%Y %H:%M')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=12))

    # 1. Umumiy Ko'rsatkichlar Kartasi
    elements.append(Paragraph("1. Oylik Umumiy Ko'rsatkichlar", section_heading))
    
    net_diff_color = '#16A34A' if net_diff >= 0 else '#DC2626'
    net_diff_sign = '+' if net_diff >= 0 else ''

    summary_data = [
        [
            Paragraph("<b>Jami Kirim</b>", th_style),
            Paragraph("<b>Jami Chiqim</b>", th_style),
            Paragraph("<b>Oylik Farq (Daromad)</b>", th_style),
            Paragraph("<b>Kassadagi Pul</b>", th_style)
        ],
        [
            Paragraph(f"<font color='#16A34A'>+ {total_inc:,.2f} so'm</font>", td_bold),
            Paragraph(f"<font color='#DC2626'>- {total_exp:,.2f} so'm</font>", td_bold),
            Paragraph(f"<font color='{net_diff_color}'><b>{net_diff_sign}{net_diff:,.2f} so'm</b></font>", td_bold),
            Paragraph(f"<b>{total_wallets:,.2f} so'm</b>", td_bold)
        ]
    ]

    summary_table = Table(summary_data, colWidths=[130, 130, 135, 135])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # 2. Hamyonlar va Kassa Holati
    if accounts:
        elements.append(Paragraph("2. Hamyonlar va Kassa Qoldig'i", section_heading))
        acc_table_data = [[Paragraph("<b>Hamyon Nomi</b>", th_style), Paragraph("<b>Mavjud Balans</b>", th_style)]]
        for acc in accounts:
            clean_acc = clean_text_for_pdf(acc['name']) or "Asosiy hamyon"
            acc_table_data.append([
                Paragraph(clean_acc, td_style),
                Paragraph(f"{acc['balance']:,.2f} so'm", td_bold)
            ])
        acc_table = Table(acc_table_data, colWidths=[330, 200])
        acc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(acc_table)
        elements.append(Spacer(1, 10))

    # 3. Kirim Bo'limlari
    inc_cats = cat_all.get("income", [])
    if inc_cats:
        elements.append(Paragraph("3. Kirim Manbalari (Bo'limlar kesimida)", section_heading))
        inc_data = [[
            Paragraph("<b>Bo'lim Nomi</b>", th_style),
            Paragraph("<b>Summa</b>", th_style),
            Paragraph("<b>O'tgan Oyga Nisbatan</b>", th_style)
        ]]
        for cat in inc_cats:
            clean_cat = clean_text_for_pdf(cat['category_name'])
            inc_data.append([
                Paragraph(clean_cat, td_style),
                Paragraph(f"<font color='#16A34A'>+ {cat['current']:,.2f} so'm</font>", td_bold),
                Paragraph(f"+{cat['percent']:.1f}%", td_style)
            ])
        inc_table = Table(inc_data, colWidths=[230, 170, 130])
        inc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#A7F3D0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1FAE5')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(inc_table)
        elements.append(Spacer(1, 10))

    # 4. Chiqim Bo'limlari
    exp_cats = cat_all.get("expense", [])
    if exp_cats:
        elements.append(Paragraph("4. Xarajatlar (Bo'limlar kesimida)", section_heading))
        exp_data = [[
            Paragraph("<b>Bo'lim Nomi</b>", th_style),
            Paragraph("<b>Summa</b>", th_style),
            Paragraph("<b>O'tgan Oyga Nisbatan</b>", th_style)
        ]]
        for cat in exp_cats:
            clean_cat = clean_text_for_pdf(cat['category_name'])
            icon_str = f"<font color='#DC2626'>+{cat['percent']:.1f}%</font>" if cat['is_increase'] else f"<font color='#16A34A'>-{cat['percent']:.1f}%</font>"
            exp_data.append([
                Paragraph(clean_cat, td_style),
                Paragraph(f"{cat['current']:,.2f} so'm", td_bold),
                Paragraph(icon_str, td_style)
            ])
        exp_table = Table(exp_data, colWidths=[230, 170, 130])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(exp_table)
        elements.append(Spacer(1, 10))

    # 5. Oxirgi Amaliyotlar Ro'yxati (Batafsil - Sabablar bilan)
    if detailed_txs:
        elements.append(Paragraph("5. Barcha Amaliyotlar Jurnali (Oxirgi amallar)", section_heading))
        tx_table_data = [[
            Paragraph("<b>Sana</b>", th_style),
            Paragraph("<b>Tur</b>", th_style),
            Paragraph("<b>Bo'lim</b>", th_style),
            Paragraph("<b>Sabab / Izoh</b>", th_style),
            Paragraph("<b>Summa</b>", th_style)
        ]]
        for tx in detailed_txs[:30]:  # Eng so'nggi 30 ta amaliyot
            date_str = str(tx.get('created_at', ''))[:16]
            is_inc = tx.get('type') == 'income'
            type_label = "<font color='#16A34A'>Kirim</font>" if is_inc else "<font color='#DC2626'>Chiqim</font>"
            cat_name = clean_text_for_pdf(tx.get('category_name') or "—")
            comment = clean_text_for_pdf(tx.get('comment') or "—")
            amt = tx.get('amount', 0.0)
            amt_str = f"+{amt:,.0f} so'm" if is_inc else f"-{amt:,.0f} so'm"
            amt_color = '#16A34A' if is_inc else '#DC2626'

            tx_table_data.append([
                Paragraph(date_str, td_style),
                Paragraph(type_label, td_bold),
                Paragraph(cat_name, td_style),
                Paragraph(comment, td_style),
                Paragraph(f"<font color='{amt_color}'><b>{amt_str}</b></font>", td_bold)
            ])

        tx_table = Table(tx_table_data, colWidths=[80, 50, 110, 180, 110])
        tx_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(tx_table)
        elements.append(Spacer(1, 10))

    # 6. Kutilmagan Yirik Xarajatlar (Anomaliyalar)
    if anomalies:
        elements.append(Paragraph("6. Kutilmagan Yirik Xarajatlar (Anomaliyalar)", section_heading))
        anom_table_data = [[
            Paragraph("<b>Sana</b>", th_style),
            Paragraph("<b>Bo'lim</b>", th_style),
            Paragraph("<b>Summa</b>", th_style),
            Paragraph("<b>Sabab</b>", th_style)
        ]]
        for anom in anomalies:
            date_str = str(anom.get('created_at', ''))[:10]
            cat_n = clean_text_for_pdf(anom.get('category_name') or "Noma'lum")
            comm = clean_text_for_pdf(anom.get('comment') or "-")
            anom_table_data.append([
                Paragraph(date_str, td_style),
                Paragraph(cat_n, td_style),
                Paragraph(f"<font color='#DC2626'>{anom['amount']:,.2f} so'm</font>", td_bold),
                Paragraph(comm, td_style)
            ])

        anom_table = Table(anom_table_data, colWidths=[90, 130, 140, 170])
        anom_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF2F2')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#FCA5A5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(anom_table)

    # Hujjatni yaratish
    doc.build(elements)
    return pdf_path
