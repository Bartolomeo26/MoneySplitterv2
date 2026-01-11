from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import date, datetime
from typing import List
import csv
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models import Session, Participant, Expense
from storage import storage
from settlement import calculate_settlement
from utils import format_currency, parse_currency, format_currency_input

app = FastAPI(title="Where is my money?")
templates = Jinja2Templates(directory="templates")

templates.env.filters['format_currency'] = format_currency
templates.env.filters['format_currency_input'] = format_currency_input


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/session/create")
async def create_session(session_name: str = Form(...)):
    session = Session(name=session_name)
    storage.create_session(session)
    return RedirectResponse(url=f"/session/{session.id}", status_code=303)


@app.get("/session/{session_id}", response_class=HTMLResponse)
async def view_session(request: Request, session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    settlement = calculate_settlement(session)

    return templates.TemplateResponse("session.html", {
        "request": request,
        "session": session,
        "settlement": settlement
    })


@app.post("/session/{session_id}/participant/add")
async def add_participant(request: Request,
                          session_id: str,
                          participant_name: str = Form(...)):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    if session.read_only:
        raise HTTPException(status_code=403,
                            detail="Sesja jest tylko do odczytu")

    try:
        participant = Participant(name=participant_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    session.participants.append(participant)
    storage.update_session(session)

    settlement = calculate_settlement(session)

    participants_html = templates.get_template(
        "partials/participants_list.html").render(request=request,
                                                  session=session,
                                                  settlement=settlement)

    expense_form_html = templates.get_template(
        "partials/expense_form.html").render(request=request,
                                             session=session,
                                             settlement=settlement)

    expense_form_oob = expense_form_html.replace(
        '<div id="expense-form-section">',
        '<div id="expense-form-section" hx-swap-oob="true">', 1)

    combined_html = participants_html + expense_form_oob

    return HTMLResponse(content=combined_html)


@app.post("/session/{session_id}/expense/add")
async def add_expense(request: Request,
                      session_id: str,
                      title: str = Form(...),
                      amount: str = Form(...),
                      expense_date: str = Form(...),
                      payer_id: str = Form(...),
                      beneficiary_ids: List[str] = Form(...)):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    if session.read_only:
        raise HTTPException(status_code=403,
                            detail="Sesja jest tylko do odczytu")

    try:
        amount_minor = parse_currency(amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount_minor <= 0:
        raise HTTPException(status_code=400,
                            detail="Kwota musi być większa od 0")

    participant_ids = {p.id for p in session.participants}
    if payer_id not in participant_ids:
        raise HTTPException(status_code=400,
                            detail="Płatnik musi być uczestnikiem sesji")

    for bid in beneficiary_ids:
        if bid not in participant_ids:
            raise HTTPException(
                status_code=400,
                detail="Wszyscy beneficjenci muszą być uczestnikami sesji")

    try:
        parsed_date = date.fromisoformat(expense_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nieprawidłowa data")

    try:
        expense = Expense(title=title,
                          amount_minor=amount_minor,
                          date=parsed_date,
                          payer_id=payer_id,
                          beneficiary_ids=beneficiary_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    session.expenses.append(expense)
    storage.update_session(session)

    settlement = calculate_settlement(session)

    return templates.TemplateResponse("partials/expenses_and_settlement.html",
                                      {
                                          "request": request,
                                          "session": session,
                                          "settlement": settlement
                                      })


@app.post("/session/{session_id}/toggle-readonly")
async def toggle_readonly(session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    session.read_only = not session.read_only
    storage.update_session(session)

    return {"read_only": session.read_only}


@app.get("/session/{session_id}/export/csv")
async def export_csv(session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    settlement = calculate_settlement(session)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Where is my money? - Eksport sesji"])
    writer.writerow([f"Sesja: {session.name}"])
    writer.writerow(
        [f"Data utworzenia: {session.created_at.strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])

    writer.writerow(["UCZESTNICY"])
    writer.writerow(["Imię"])
    for participant in session.participants:
        writer.writerow([participant.name])
    writer.writerow([])

    writer.writerow(["WYDATKI"])
    writer.writerow(["Data", "Tytuł", "Kwota", "Płatnik", "Beneficjenci"])

    participant_map = {p.id: p.name for p in session.participants}

    for expense in session.expenses:
        beneficiaries_names = ", ".join(
            [participant_map[bid] for bid in expense.beneficiary_ids])
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'), expense.title,
            format_currency(expense.amount_minor),
            participant_map[expense.payer_id], beneficiaries_names
        ])
    writer.writerow([])

    writer.writerow(["ROZLICZENIE - SALDA"])
    writer.writerow(["Uczestnik", "Saldo"])
    for balance in settlement.balances:
        writer.writerow(
            [balance.participant_name,
             format_currency(balance.balance_minor)])
    writer.writerow([])

    writer.writerow(["ROZLICZENIE - PŁATNOŚCI"])
    writer.writerow(["Od", "Do", "Kwota"])
    for payment in settlement.payments:
        writer.writerow([
            payment.from_participant_name, payment.to_participant_name,
            format_currency(payment.amount_minor)
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition":
            f"attachment; filename=rozliczenie_{session.name.replace(' ', '_')}.csv"
        })


@app.get("/session/{session_id}/export/pdf")
async def export_pdf(session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
                            detail="Sesja nie została znaleziona")

    settlement = calculate_settlement(session)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    try:
        pdfmetrics.registerFont(
            TTFont('DejaVuSans',
                   '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(
            TTFont('DejaVuSans-Bold',
                   '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        font_name = 'DejaVuSans'
        font_name_bold = 'DejaVuSans-Bold'
    except:
        font_name = 'Helvetica'
        font_name_bold = 'Helvetica-Bold'

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        fontName=font_name_bold,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        fontName=font_name_bold,
        textColor=colors.HexColor('#374151'),
        spaceAfter=10,
        spaceBefore=14,
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
    )

    elements.append(Paragraph("Where is my money?", title_style))
    elements.append(Paragraph(f"Sesja: {session.name}", normal_style))
    elements.append(
        Paragraph(
            f"Data utworzenia: {session.created_at.strftime('%Y-%m-%d %H:%M')}",
            normal_style))
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Uczestnicy", heading_style))
    participant_data = [["Imię"]]
    for participant in session.participants:
        participant_data.append([participant.name])

    participant_table = Table(participant_data, colWidths=[15 * cm])
    participant_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]))
    elements.append(participant_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Wydatki", heading_style))
    participant_map = {p.id: p.name for p in session.participants}

    expense_data = [["Data", "Tytuł", "Kwota", "Płatnik", "Beneficjenci"]]
    for expense in session.expenses:
        beneficiaries_names = ", ".join(
            [participant_map[bid] for bid in expense.beneficiary_ids])
        expense_data.append([
            expense.date.strftime('%Y-%m-%d'), expense.title,
            format_currency(expense.amount_minor),
            participant_map[expense.payer_id], beneficiaries_names
        ])

    expense_table = Table(
        expense_data, colWidths=[2.5 * cm, 4 * cm, 2.5 * cm, 3 * cm, 3 * cm])
    expense_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]))
    elements.append(expense_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Rozliczenie - Salda", heading_style))
    balance_data = [["Uczestnik", "Saldo"]]
    for balance in settlement.balances:
        balance_data.append(
            [balance.participant_name,
             format_currency(balance.balance_minor)])

    balance_table = Table(balance_data, colWidths=[10 * cm, 5 * cm])
    balance_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]))
    elements.append(balance_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Rozliczenie - Płatności", heading_style))
    payment_data = [["Od", "Do", "Kwota"]]
    for payment in settlement.payments:
        payment_data.append([
            payment.from_participant_name, payment.to_participant_name,
            format_currency(payment.amount_minor)
        ])

    if len(payment_data) == 1:
        payment_data.append(["Brak płatności do wykonania", "", ""])

    payment_table = Table(payment_data, colWidths=[5 * cm, 5 * cm, 5 * cm])
    payment_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]))
    elements.append(payment_table)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            f"attachment; filename=rozliczenie_{session.name.replace(' ', '_')}.pdf"
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
