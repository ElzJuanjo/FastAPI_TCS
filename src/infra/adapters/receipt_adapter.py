import os
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from src.infra.config.mail_profiles import get_mail_profile

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..",
    "templates",
)
STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..",
    "static",
)

jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def generate_receipt_pdf_bytes(order, payment, buyer_name: str) -> bytes:
    # Logo dinámico según perfil (tickets vs attendees)
    mail_profile = get_mail_profile(order)
    logo_path = os.path.join(STATIC_DIR, mail_profile.logo_filename)
    if not os.path.exists(logo_path):
        logo_path = None

    # Determinar referencia de transacción según gateway
    if payment.gateway == "PLACETOPAY":
        transaction_id = payment.placetopay_request_id or "N/A"
        gateway_label = "PlaceToPay"
    else:
        transaction_id = payment.wompi_transaction_id or "N/A"
        gateway_label = "Wompi"

    has_tickets = bool(order.tickets)

    if has_tickets:
        tickets_data = []
        for t in order.tickets:
            tickets_data.append({
                "day": t.day.isoformat(),
                "seats": t.seats,
                "amount": t.amount,
            })

        template = jinja_env.get_template("receipt_pdf_theater.html")
        html = template.render(
            order=order,
            transaction_id=transaction_id,
            gateway_label=gateway_label,
            payment_date=payment.created_at.strftime("%d/%m/%Y %H:%M"),
            total_amount=f"{order.total_amount:,.2f}",
            tickets=tickets_data,
            buyer_name=buyer_name,
            logo_path=logo_path,
        )
    else:
        # Legacy: carreras
        attendees_data = []
        for a in order.attendees:
            parts = [a.first_name or ""]
            if a.middle_name:
                parts.append(a.middle_name)
            if a.last_name_1:
                parts.append(a.last_name_1)
            if a.last_name_2:
                parts.append(a.last_name_2)
            attendees_data.append({
                "name": " ".join(parts),
                "shirt_size": a.shirt_size or "N/A",
            })

        template = jinja_env.get_template("receipt_pdf.html")
        html = template.render(
            order=order,
            wompi_transaction_id=transaction_id,
            payment_date=payment.created_at.strftime("%d/%m/%Y %H:%M"),
            total_amount=f"{order.total_amount:,.2f}",
            attendees=attendees_data,
            buyer_name=buyer_name,
            logo_path=logo_path,
        )

    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf)

    if pisa_status.err:
        raise Exception("Error generando el PDF del comprobante")

    return pdf.getvalue()