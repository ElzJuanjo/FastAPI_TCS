import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from src.infra.config.settings import get_settings
from src.infra.config.mail_profiles import get_mail_profile
from src.infra.adapters.receipt_adapter import generate_receipt_pdf_bytes

logger = logging.getLogger("email")
settings = get_settings()

# Template engine
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..",
    "templates",
)
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _get_buyer_full_name(order) -> str:
    parts = []
    if order.first_name:
        parts.append(order.first_name)
    if order.middle_name:
        parts.append(order.middle_name)
    if order.last_name_1:
        parts.append(order.last_name_1)
    if order.last_name_2:
        parts.append(order.last_name_2)
    return " ".join(parts) if parts else "Sin nombre"


def _get_attendee_full_name(attendee) -> str:
    parts = []
    if attendee.first_name:
        parts.append(attendee.first_name)
    if attendee.middle_name:
        parts.append(attendee.middle_name)
    if attendee.last_name_1:
        parts.append(attendee.last_name_1)
    if attendee.last_name_2:
        parts.append(attendee.last_name_2)
    return " ".join(parts) if parts else "Sin nombre"


async def send_payment_confirmation_email(payment) -> bool:
    try:
        order = payment.order
        buyer_name = _get_buyer_full_name(order)

        # Perfil dinámico (tickets / attendees / camp): credenciales, sender y logo
        mail_profile = get_mail_profile(order)

        # Determinar tipo de evento por contenido de la orden
        has_camp = bool(order.camp_enrollments)
        has_tickets = bool(order.tickets)

        # Datos para template
        if has_camp:
            # ---- CAMP ----
            enrollments_data = []
            for e in order.camp_enrollments:
                enrollment_detail = {
                    "child_name": f"{e.child_first_name} {e.child_last_name}",
                    "age_group": e.age_group,
                    "enrollment_type": e.enrollment_type,
                    "unit_price": e.unit_price,
                }
                if e.camp_week and e.enrollment_type == "WEEK":
                    enrollment_detail["week_label"] = e.camp_week.label or f"Semana {e.camp_week.week_number}"
                    enrollment_detail["start_date"] = e.camp_week.start_date.isoformat()
                    enrollment_detail["end_date"] = e.camp_week.end_date.isoformat()
                elif e.camp_package and e.enrollment_type == "PACKAGE":
                    enrollment_detail["package_label"] = e.camp_package.label or e.camp_package.code
                elif e.enrollment_type == "DAY" and e.individual_date:
                    enrollment_detail["individual_date"] = e.individual_date.isoformat()
                enrollments_data.append(enrollment_detail)

            template = jinja_env.get_template("email_paid_camp.html")
            html_body = template.render(
                order=order,
                enrollments=enrollments_data,
                logo_url=mail_profile.logo_url,
                formatted_total=f"{order.total_amount:,.2f}",
            )

        elif has_tickets:
            # ---- TEATRO/CINE ----
            tickets_data = []
            for t in order.tickets:
                tickets_data.append({
                    "day": t.day.isoformat(),
                    "seats": t.seats,
                    "amount": t.amount,
                })

            template = jinja_env.get_template("email_paid_theater.html")
            html_body = template.render(
                order=order,
                tickets=tickets_data,
                logo_url=mail_profile.logo_url,
                formatted_total=f"{order.total_amount:,.2f}",
            )

        else:
            # ---- CARRERAS (legacy) ----
            attendees_data = [
                {
                    "name": _get_attendee_full_name(a),
                    "shirt_size": a.shirt_size or "No especificada",
                }
                for a in order.attendees
            ]

            template = jinja_env.get_template("email_paid.html")
            html_body = template.render(
                order=order,
                attendees=attendees_data,
                logo_url=mail_profile.logo_url,
                formatted_total=f"{order.total_amount:,.2f}",
            )

        # Generar PDF
        pdf_bytes = generate_receipt_pdf_bytes(
            order=order,
            payment=payment,
            buyer_name=buyer_name,
        )

        # Construir email
        msg = MIMEMultipart()
        msg["Subject"] = f"✓ Confirmación de Pago - Orden #{order.id}"
        msg["From"] = mail_profile.default_sender
        msg["To"] = order.email

        msg.attach(MIMEText(html_body, "html"))

        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"Comprobante_{order.id}.pdf",
        )
        msg.attach(pdf_attachment)

        # Enviar con credenciales del perfil correspondiente
        await aiosmtplib.send(
            msg,
            hostname=settings.MAIL_SERVER,
            port=settings.MAIL_PORT,
            username=mail_profile.username,
            password=mail_profile.password,
            use_tls=settings.MAIL_USE_SSL,
            start_tls=settings.MAIL_USE_TLS,
        )

        logger.info(
            f"Email enviado para orden {order.id} "
            f"(perfil={mail_profile.kind})"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error enviando correo orden {payment.order.id}: {str(e)}",
            exc_info=True,
        )
        return False
